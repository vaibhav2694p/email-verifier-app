from __future__ import annotations

import os
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from domain_health import check_domain_health
from services.bulk_processor import BulkProcessor
from services.job_service import job_service
from services.webhook_service import deliver_webhook
from verifier.config import VerifierConfig
from verifier.pipeline import VerificationPipeline

from .auth import require_api_key
from .rate_limit import enforce_rate_limit
from .schemas import (
    BulkJobResponse,
    BulkVerifyRequest,
    DomainHealthResponse,
    VerifyRequest,
    VerifyResponse,
    WebhookTestRequest,
)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/health")
def health(request: Request) -> Dict[str, str]:
    enforce_rate_limit(request)
    return {"status": "ok", "service": "email-verifier-api"}


@router.post("/verify", response_model=VerifyResponse)
def verify_email(payload: VerifyRequest, request: Request) -> VerifyResponse:
    enforce_rate_limit(request)
    config = VerifierConfig.from_env()
    config.enable_smtp_check = payload.smtp_check
    config.enable_domain_monitoring = payload.domain_reputation_check
    config.enable_blacklist_check = payload.domain_reputation_check
    config.enable_ai_scoring = payload.ai_explanation
    result = VerificationPipeline(config).verify(payload.email, company_domain=payload.company_domain)
    return VerifyResponse(
        email=payload.email,
        status=result.verification_status.lower().replace(" ", "_"),
        score=result.verification_score,
        reason=result.reason or result.notes,
        recommended_action=result.recommended_action.lower().replace(" ", "_"),
        result=result.to_dict(),
    )


@router.post("/verify/bulk", response_model=BulkJobResponse)
def verify_bulk(payload: BulkVerifyRequest, request: Request, background_tasks: BackgroundTasks) -> BulkJobResponse:
    enforce_rate_limit(request)
    job_id = job_service.create_job({"total": len(payload.emails)})
    background_tasks.add_task(_run_bulk_job, job_id, payload)
    return BulkJobResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> Dict[str, Any]:
    enforce_rate_limit(request)
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    safe = dict(job)
    safe.pop("result", None)
    return safe


@router.get("/jobs/{job_id}/results")
def get_job_results(job_id: str, request: Request) -> Dict[str, Any]:
    enforce_rate_limit(request)
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job["status"], "results": job.get("result")}


@router.get("/domains/{domain}/health", response_model=DomainHealthResponse)
def domain_health(domain: str, request: Request) -> DomainHealthResponse:
    enforce_rate_limit(request)
    config = VerifierConfig.from_env()
    config.enable_domain_monitoring = True
    health = check_domain_health(domain, config)
    return DomainHealthResponse(domain=domain, health=health)


@router.post("/webhooks/test")
def test_webhook(payload: WebhookTestRequest, request: Request) -> Dict[str, Any]:
    enforce_rate_limit(request)
    secret = payload.secret or os.getenv("WEBHOOK_SECRET", "dev-secret")
    event = {"event": "webhook.test", "job_id": "job_test", "total": 0, "valid": 0, "invalid": 0, "catch_all": 0, "unknown": 0}
    delivery = deliver_webhook(payload.url, event, secret, production=os.getenv("APP_ENV", "development") == "production")
    return delivery.__dict__


def _run_bulk_job(job_id: str, payload: BulkVerifyRequest) -> None:
    try:
        job_service.update_job(job_id, status="running")
        config = VerifierConfig.from_env()
        config.enable_smtp_check = payload.smtp_check
        df = pd.DataFrame({"Email": payload.emails})
        result_df = BulkProcessor(config=config).process(df, "Email")
        results = result_df.to_dict(orient="records")
        job_service.update_job(job_id, status="completed", result=results)
        if payload.webhook_url:
            summary = {
                "event": "verification.completed",
                "job_id": job_id,
                "total": len(results),
                "valid": sum(1 for r in results if r.get("verification_status") == "Valid"),
                "invalid": sum(1 for r in results if r.get("verification_status") == "Invalid"),
                "catch_all": sum(1 for r in results if r.get("verification_status") == "Catch-All"),
                "unknown": sum(1 for r in results if r.get("verification_status") == "Unknown"),
                "download_url": "",
            }
            deliver_webhook(payload.webhook_url, summary, os.getenv("WEBHOOK_SECRET", "dev-secret"), production=os.getenv("APP_ENV", "development") == "production")
    except Exception as exc:
        job_service.update_job(job_id, status="failed", error=str(exc))
