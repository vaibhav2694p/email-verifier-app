from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class VerifyRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=320)
    smtp_check: bool = False
    catch_all_check: bool = False
    domain_reputation_check: bool = False
    ai_explanation: bool = False
    company_domain: Optional[str] = None


class VerifyResponse(BaseModel):
    email: str
    status: str
    score: int
    reason: str
    recommended_action: str
    result: Dict[str, Any]


class BulkVerifyRequest(BaseModel):
    emails: List[str] = Field(..., min_length=1, max_length=100000)
    smtp_check: bool = False
    catch_all_check: bool = False
    webhook_url: Optional[str] = None

    @field_validator("emails")
    @classmethod
    def no_empty_emails(cls, value: List[str]) -> List[str]:
        if not any(str(v).strip() for v in value):
            raise ValueError("At least one non-empty email is required")
        return value


class BulkJobResponse(BaseModel):
    job_id: str
    status: str


class WebhookTestRequest(BaseModel):
    url: str
    secret: Optional[str] = None


class DomainHealthResponse(BaseModel):
    domain: str
    health: Dict[str, Any]
