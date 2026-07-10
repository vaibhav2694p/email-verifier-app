import logging
import time
from typing import Any, Dict, List, Optional

from domain_health import check_domain_health

from .abuse_detector import detect_abuse_address
from .ai_scorer import generate_ai_explanation
from .catch_all import detect_catch_all
from .classifier import classify_result
from .config import VerifierConfig
from .disposable import is_disposable
from .dns_validator import check_domain_reachable, validate_dns
from .greylist_handler import apply_greylist_analysis
from .models import PipelineStage, VerificationResult
from .mx_provider import classify_provider
from .normalizer import normalize_domain, normalize_email, split_email
from .role_detector import detect_role_account
from .scoring import calculate_verification_score
from .smtp_validator import verify_smtp_for_domain
from .spamtrap_risk import assess_spam_trap_risk
from .syntax_validator import validate_syntax
from .toxic_risk import assess_toxic_risk
from .typo_detector import detect_typo

logger = logging.getLogger(__name__)


class VerificationPipeline:
    """Multi-layer email verification pipeline."""

    def __init__(self, config: Optional[VerifierConfig] = None):
        self.config = config or VerifierConfig()

    def verify(self, email: str, company_domain: Optional[str] = None) -> VerificationResult:
        result = VerificationResult(original_email=email)
        start_time = time.monotonic()

        stage = self._stage_normalize(email, result)
        result.stage_results.append(stage)

        if not stage.success:
            self._stage_scoring(result)
            self._stage_classifier(result)
            result.processing_time_ms = round((time.monotonic() - start_time) * 1000, 2)
            return result

        stage = self._stage_syntax(result)
        result.stage_results.append(stage)

        if not result.syntax_valid:
            self._stage_scoring(result)
            self._stage_classifier(result)
            result.processing_time_ms = round((time.monotonic() - start_time) * 1000, 2)
            return result

        stage = self._stage_typo(result)
        result.stage_results.append(stage)

        stage = self._stage_dns(result)
        result.stage_results.append(stage)

        stage = self._stage_domain_health(result)
        result.stage_results.append(stage)

        dns_fatal = result.dns_status in ("NXDomain",) or (result.mx_status in ("NoAnswer", "NXDomain") and not result.domain)
        has_mx = bool(result.mx_records) and not result.null_mx

        if dns_fatal or (not has_mx and not result.null_mx and result.dns_status == "NXDomain"):
            self._stage_scoring(result)
            self._stage_classifier(result)
            result.processing_time_ms = round((time.monotonic() - start_time) * 1000, 2)
            return result

        stage = self._stage_provider(result)
        result.stage_results.append(stage)

        stage = self._stage_disposable(result)
        result.stage_results.append(stage)

        stage = self._stage_free_provider(result)
        result.stage_results.append(stage)

        stage = self._stage_role(result)
        result.stage_results.append(stage)

        stage = self._stage_abuse(result)
        result.stage_results.append(stage)

        if self.config.enable_smtp_check and has_mx:
            stage = self._stage_smtp(result)
            result.stage_results.append(stage)

            stage = self._stage_greylist(result)
            result.stage_results.append(stage)

            if self.config.enable_smtp_check:
                stage = self._stage_catch_all(result)
                result.stage_results.append(stage)

        stage = self._stage_website(result)
        result.stage_results.append(stage)

        stage = self._stage_company_match(result, company_domain)
        result.stage_results.append(stage)

        stage = self._stage_risk(result)
        result.stage_results.append(stage)

        stage = self._stage_scoring(result)
        result.stage_results.append(stage)

        stage = self._stage_classifier(result)
        result.stage_results.append(stage)

        if self.config.enable_ai_scoring:
            stage = self._stage_ai_explanation(result)
            result.stage_results.append(stage)

        result.processing_time_ms = round((time.monotonic() - start_time) * 1000, 2)
        return result

    def _stage_normalize(self, email: str, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            normalized = normalize_email(email)
            local_part, domain = split_email(normalized)
            result.normalized_email = normalized
            result.cleaned_email = normalized
            result.local_part = local_part
            result.domain = domain
            result.root_domain = _root_domain(domain)
            result.idn_domain_text = domain
            result.punycode_domain = domain.encode("idna").decode("ascii") if domain else ""
            return PipelineStage(
                name="normalize",
                success=True,
                data={"normalized_email": normalized, "local_part": local_part, "domain": domain},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Normalization failed for %s: %s", email, e)
            error_msg = str(e)
            try:
                parts = email.strip().split("@", 1)
                if len(parts) == 2:
                    result.local_part, result.domain = parts
            except Exception:
                pass
            return PipelineStage(
                name="normalize",
                success=False,
                error=error_msg,
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_syntax(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            email_to_check = result.normalized_email or f"{result.local_part}@{result.domain}"
            syn = validate_syntax(email_to_check)
            result.syntax_valid = syn.is_valid
            result.syntax_error = syn.error
            result.syntax_error_code = _syntax_error_code(syn.error)
            result.idn_domain = syn.idn_domain
            result.punycode_domain = syn.punycode_domain or result.punycode_domain
            if syn.normalized_email:
                result.normalized_email = syn.normalized_email
            if syn.local_part:
                result.local_part = syn.local_part
            if syn.domain:
                result.domain = syn.domain
            return PipelineStage(
                name="syntax",
                success=syn.is_valid,
                data={"is_valid": syn.is_valid, "error": syn.error},
                error=syn.error if not syn.is_valid else "",
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Syntax validation error for %s: %s", result.normalized_email, e)
            result.syntax_valid = False
            result.syntax_error = str(e)
            return PipelineStage(
                name="syntax",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_typo(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            if not result.domain:
                return PipelineStage(
                    name="typo",
                    success=False,
                    error="No domain to check",
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            typo = detect_typo(result.domain)
            result.domain_typo = typo.is_possible_typo
            result.suggested_email = typo.suggested_email
            result.suggested_domain = typo.suggested_domain
            return PipelineStage(
                name="typo",
                success=True,
                data={"is_typo": typo.is_possible_typo, "suggested": typo.suggested_domain},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Typo detection error for %s: %s", result.domain, e)
            return PipelineStage(
                name="typo",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_dns(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            if not result.domain:
                return PipelineStage(
                    name="dns",
                    success=False,
                    error="No domain to resolve",
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            dns = validate_dns(result.domain, self.config)
            result.dns_status = dns.status.value if hasattr(dns.status, 'value') else str(dns.status)
            result.mx_records = str([(r.get("host", ""), r.get("priority", 0)) for r in dns.mx_records]) if dns.mx_records else ""
            result.mx_priorities = ", ".join(str(r.get("priority", 0)) for r in dns.mx_records) if dns.mx_records else ""
            result.primary_mx = dns.primary_mx
            result.mx_provider = dns.mx_provider
            result.null_mx = dns.null_mx
            result.a_records = ", ".join(dns.a_records)
            result.aaaa_records = ", ".join(dns.aaaa_records)
            result.cname_records = ", ".join(dns.cname_records)
            result.dns_error = dns.dns_error
            result.dns_response_time_ms = dns.dns_response_time_ms
            result.dns_resolver_used = dns.resolver_used
            result.mx_status = "Resolved" if dns.has_mx or dns.null_mx else result.dns_status
            return PipelineStage(
                name="dns",
                success=dns.status in ("Resolved",) or dns.null_mx,
                data={
                    "status": result.dns_status,
                    "mx_count": len(dns.mx_records),
                    "null_mx": dns.null_mx,
                },
                error=dns.dns_error,
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("DNS validation error for %s: %s", result.domain, e)
            result.dns_status = "Error"
            result.mx_status = "Error"
            return PipelineStage(
                name="dns",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_provider(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            mx_list = _parse_mx_records(result.mx_records)
            provider = classify_provider(mx_list, result.domain)
            provider_name = provider.value if hasattr(provider, 'value') else str(provider)
            result.mx_provider = provider_name
            result.mail_hosting_provider = provider_name
            result.email_provider = result.domain
            result.provider_category = provider_name
            result.corporate_email = provider_name not in ("Free/Public", "Unknown", "")
            result.provider_confidence = 0.9 if provider_name != "Unknown" else 0.2
            return PipelineStage(
                name="provider",
                success=True,
                data={"provider": provider_name},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Provider classification error for %s: %s", result.domain, e)
            return PipelineStage(
                name="provider",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_disposable(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            if not result.domain:
                return PipelineStage(
                    name="disposable",
                    success=False,
                    error="No domain to check",
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            disposable = is_disposable(result.domain)
            result.disposable = disposable
            if disposable:
                result.disposable_provider = result.domain
                result.disposable_category = "Temporary Email"
                result.disposable_dataset_match = result.domain
                result.disposable_risk = "High"
            else:
                result.disposable_risk = "Low"
            return PipelineStage(
                name="disposable",
                success=True,
                data={"disposable": disposable},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Disposable check error for %s: %s", result.domain, e)
            return PipelineStage(
                name="disposable",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_free_provider(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            from .mx_provider import ProviderType, is_free_provider
            if result.mx_provider == ProviderType.FREE_PUBLIC.value:
                result.free_public_email = True
            elif result.domain:
                result.free_public_email = is_free_provider(result.domain)
            else:
                result.free_public_email = False
            result.corporate_email = bool(result.domain) and not result.free_public_email
            if result.free_public_email:
                result.provider_category = "Free/Public"
                result.email_provider = result.domain
            return PipelineStage(
                name="free_provider",
                success=True,
                data={"free_public": result.free_public_email},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Free provider check error for %s: %s", result.domain, e)
            return PipelineStage(
                name="free_provider",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_role(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            email_to_check = result.normalized_email or f"{result.local_part}@{result.domain}"
            is_role, category, risk = detect_role_account(email_to_check)
            result.role_based = is_role
            result.role_category = category
            result.role_prefix = result.local_part.lower() if is_role else ""
            result.role_risk = "Medium" if is_role else "Low"
            result.engagement_risk = "Medium" if is_role else "Low"
            return PipelineStage(
                name="role",
                success=True,
                data={"is_role": is_role, "category": category, "risk": risk},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Role detection error for %s: %s", result.normalized_email, e)
            return PipelineStage(
                name="role",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_smtp(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            if not result.primary_mx:
                return PipelineStage(
                    name="smtp",
                    success=False,
                    error="No MX host available",
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            mx_list = _parse_mx_records(result.mx_records)
            smtp = verify_smtp_for_domain(
                email=result.normalized_email or f"{result.local_part}@{result.domain}",
                domain=result.domain,
                mx_records=mx_list,
                config=self.config,
            )
            result.smtp_attempted = smtp.attempted
            result.smtp_status = smtp.status.value if hasattr(smtp.status, 'value') else str(smtp.status)
            result.smtp_code = smtp.code
            result.smtp_message = smtp.message
            result.smtp_connected = bool(smtp.mx_host) and result.smtp_status not in ("connection_blocked", "timeout")
            result.smtp_mx_host = smtp.mx_host
            result.smtp_response_time_ms = smtp.response_time_ms
            result.smtp_blocked = result.smtp_status in ("connection_blocked",)
            result.smtp_port_blocked = result.smtp_status in ("connection_blocked",)
            result.mailbox_accepted = result.smtp_status == "accepted"
            result.mailbox_rejected = result.smtp_status == "rejected"
            result.mailbox_full = smtp.code in (452, 552) or "full" in (smtp.message or "").lower()
            result.smtp_inconclusive = result.smtp_status in ("unknown", "timeout", "temporary_failure", "connection_blocked")
            result.mailbox_evidence = _mailbox_evidence(result)
            return PipelineStage(
                name="smtp",
                success=smtp.status in ("accepted", "rejected"),
                data={
                    "status": result.smtp_status,
                    "code": smtp.code,
                },
                error=smtp.error,
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("SMTP verification error for %s: %s", result.normalized_email, e)
            result.smtp_attempted = True
            result.smtp_status = "error"
            return PipelineStage(
                name="smtp",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_catch_all(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            if not result.primary_mx:
                return PipelineStage(
                    name="catch_all",
                    success=False,
                    error="No MX host for catch-all test",
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            ca = detect_catch_all(
                domain=result.domain,
                mx_host=result.primary_mx,
                config=self.config,
                target_email=result.normalized_email or f"{result.local_part}@{result.domain}",
            )
            result.catch_all = ca.status.value if hasattr(ca.status, 'value') else str(ca.status)
            result.catch_all_tested = ca.tested
            result.catch_all_confidence = ca.confidence
            result.catch_all_notes = "Random recipient accepted" if ca.random_email_accepted else "Random recipient not accepted"
            return PipelineStage(
                name="catch_all",
                success=ca.tested,
                data={
                    "status": result.catch_all,
                    "confidence": ca.confidence,
                    "tested": ca.tested,
                },
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Catch-all detection error for %s: %s", result.domain, e)
            return PipelineStage(
                name="catch_all",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_abuse(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            is_abuse, category, do_not_mail, reason = detect_abuse_address(result.normalized_email or result.original_email)
            result.abuse_address = is_abuse
            result.abuse_category = category
            result.do_not_mail = do_not_mail
            result.abuse_reason = reason
            return PipelineStage("abuse", True, {"abuse": is_abuse, "category": category}, duration_ms=round((time.monotonic() - start) * 1000, 2))
        except Exception as e:
            return PipelineStage("abuse", False, error=str(e), duration_ms=round((time.monotonic() - start) * 1000, 2))

    def _stage_greylist(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            apply_greylist_analysis(result)
            return PipelineStage("greylist", True, {"greylisted": result.greylisting_detected, "retry_required": result.retry_required}, duration_ms=round((time.monotonic() - start) * 1000, 2))
        except Exception as e:
            return PipelineStage("greylist", False, error=str(e), duration_ms=round((time.monotonic() - start) * 1000, 2))

    def _stage_domain_health(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        if not (self.config.enable_domain_monitoring or self.config.enable_blacklist_check) or not result.domain:
            return PipelineStage("domain_health", True, {"checked": False}, duration_ms=round((time.monotonic() - start) * 1000, 2))
        try:
            health = check_domain_health(result.domain, self.config)
            for key, value in health.items():
                if hasattr(result, key):
                    setattr(result, key, value)
            return PipelineStage("domain_health", True, health, duration_ms=round((time.monotonic() - start) * 1000, 2))
        except Exception as e:
            return PipelineStage("domain_health", False, error=str(e), duration_ms=round((time.monotonic() - start) * 1000, 2))

    def _stage_risk(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            risk, signals, source, confidence, confirmed = assess_spam_trap_risk(result)
            result.spam_trap_risk = risk
            result.spam_trap_signals = signals
            result.spam_trap_data_source = source
            result.spam_trap_confidence = confidence
            result.confirmed_trap = confirmed
            toxic, toxic_signals, toxic_source, toxic_confidence, fraud = assess_toxic_risk(result)
            result.toxic_risk = toxic
            result.toxic_signals = toxic_signals
            result.toxic_risk_source = toxic_source
            result.toxic_confidence = toxic_confidence
            result.fraud_risk = fraud
            return PipelineStage("risk", True, {"spam_trap_risk": risk, "toxic_risk": toxic}, duration_ms=round((time.monotonic() - start) * 1000, 2))
        except Exception as e:
            return PipelineStage("risk", False, error=str(e), duration_ms=round((time.monotonic() - start) * 1000, 2))

    def _stage_classifier(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            classify_result(result)
            return PipelineStage("classifier", True, {"status": result.verification_status, "action": result.recommended_action}, duration_ms=round((time.monotonic() - start) * 1000, 2))
        except Exception as e:
            return PipelineStage("classifier", False, error=str(e), duration_ms=round((time.monotonic() - start) * 1000, 2))

    def _stage_ai_explanation(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            generate_ai_explanation(result)
            return PipelineStage("ai_explanation", True, {"ai_quality_score": result.ai_quality_score}, duration_ms=round((time.monotonic() - start) * 1000, 2))
        except Exception as e:
            return PipelineStage("ai_explanation", False, error=str(e), duration_ms=round((time.monotonic() - start) * 1000, 2))

    def _stage_website(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            if not result.domain:
                return PipelineStage(
                    name="website",
                    success=False,
                    error="No domain to check",
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            reachable, status_str, url = check_domain_reachable(result.domain)
            result.domain_active = reachable
            result.website_status = status_str
            return PipelineStage(
                name="website",
                success=reachable,
                data={"reachable": reachable, "status": status_str},
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Website reachability check error for %s: %s", result.domain, e)
            return PipelineStage(
                name="website",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_company_match(self, result: VerificationResult, company_domain: Optional[str]) -> PipelineStage:
        start = time.monotonic()
        try:
            if not company_domain:
                result.company_domain_match = None
                return PipelineStage(
                    name="company_match",
                    success=True,
                    data={"match": None, "reason": "No company domain provided"},
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
            normalized_company = normalize_domain(company_domain) if company_domain else ""
            user_domain = result.domain.lower().strip() if result.domain else ""
            match = user_domain == normalized_company.lower().strip() if normalized_company and user_domain else False
            result.company_domain_match = match
            return PipelineStage(
                name="company_match",
                success=True,
                data={
                    "company_domain": normalized_company,
                    "user_domain": user_domain,
                    "match": match,
                },
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.debug("Company domain match error: %s", e)
            return PipelineStage(
                name="company_match",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _stage_scoring(self, result: VerificationResult) -> PipelineStage:
        start = time.monotonic()
        try:
            calculate_verification_score(result)
            return PipelineStage(
                name="scoring",
                success=True,
                data={
                    "score": result.verification_score,
                    "status": result.verification_status,
                    "confidence": result.confidence_level,
                    "risk": result.risk_level,
                },
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as e:
            logger.error("Scoring failed: %s", e)
            result.verification_score = 0
            result.verification_status = "Unknown"
            result.confidence_level = "Low"
            result.risk_level = "High"
            return PipelineStage(
                name="scoring",
                success=False,
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )


def _parse_mx_records(mx_str: str) -> List[Dict[str, Any]]:
    if not mx_str:
        return []
    try:
        import ast
        raw = ast.literal_eval(mx_str)
        if isinstance(raw, list):
            return [{"host": h, "priority": p} for h, p in raw]
    except Exception:
        pass
    return []


def _root_domain(domain: str) -> str:
    parts = (domain or "").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _syntax_error_code(error: str) -> str:
    text = (error or "").lower()
    if "@" in text:
        return "invalid_at_count"
    if "local" in text:
        return "invalid_local_part"
    if "domain" in text:
        return "invalid_domain"
    if "length" in text or "too long" in text:
        return "length_limit"
    return "syntax_error" if error else ""


def _mailbox_evidence(result: VerificationResult) -> str:
    if result.mailbox_accepted:
        return "Accepted"
    if result.mailbox_rejected:
        return "Rejected"
    if result.greylisting_detected:
        return "Temporary Failure"
    if result.smtp_blocked:
        return "SMTP Blocked"
    if result.smtp_inconclusive:
        return "Unknown"
    return "Unknown"
