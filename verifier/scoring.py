from typing import List, Tuple, Optional
from .models import (
    VerificationResult, VerificationStatus, ConfidenceLevel,
    RiskLevel, SyntaxResult, DnsResult, SmtpResult, CatchAllResult,
    CatchAllStatus,
)


def calculate_verification_score(result: VerificationResult) -> VerificationResult:
    score = 0
    reasons = []
    failed = []
    inconclusive = []

    if result.syntax_valid:
        score += 15
        reasons.append("+15: Valid email syntax")
    else:
        reasons.append("+0: Invalid email syntax")
        failed.append("syntax")

    dns_resolved = result.dns_status in ("Resolved",)
    mx_found = result.mx_status in ("Resolved",) and bool(result.mx_records)
    null_mx = result.null_mx

    if dns_resolved:
        score += 10
        reasons.append("+10: DNS resolved")
    else:
        reasons.append("+0: DNS not resolved")
        failed.append("dns")

    if mx_found and not null_mx:
        score += 15
        reasons.append("+15: MX records found")
    elif null_mx:
        score -= 20
        reasons.append("-20: Null MX record detected")
        failed.append("null_mx")
    else:
        reasons.append("+0: No MX records found")
        failed.append("mx")

    if result.mx_provider and result.mx_provider not in ("Unknown", "Null MX (No Email)", "A/AAAA Fallback", ""):
        score += 5
        reasons.append(f"+5: {result.mx_provider} provider detected")

    smtp_status = result.smtp_status.lower() if isinstance(result.smtp_status, str) else ""
    if result.smtp_attempted:
        if smtp_status == "accepted":
            score += 20
            reasons.append("+20: SMTP accepted")
        elif smtp_status == "rejected":
            score -= 25
            reasons.append("-25: SMTP rejected")
            failed.append("smtp")
        elif smtp_status in ("temporary_failure", "greylisted"):
            score -= 5
            reasons.append("-5: SMTP temporary failure")
            inconclusive.append("smtp")
        elif smtp_status == "connection_blocked":
            reasons.append("+0: SMTP connection blocked")
            failed.append("smtp")

    catch_all_status = result.catch_all
    if catch_all_status == "Catch-All":
        score -= 10
        reasons.append("-10: Catch-all detected")
        failed.append("catch_all")
    elif catch_all_status in ("Not Tested", "Unknown"):
        inconclusive.append("catch_all")

    if result.domain_active:
        score += 5
        reasons.append("+5: Domain active (website reachable)")

    if result.disposable:
        reasons.append("+0: Disposable domain detected (score capped at 15)")

    if result.free_public_email:
        reasons.append("+0: Free/public email provider (score capped at 40)")

    if result.role_based:
        penalty = -10
        category = result.role_category
        from .role_detector import get_risk_adjustment
        adj = get_risk_adjustment(category)
        penalty = adj if adj != 0 else -10
        score += penalty
        reasons.append(f"{penalty}: Role-based account ({category})")

    if result.domain_typo:
        score -= 15
        reasons.append("-15: Domain typo detected")
        failed.append("typo")

    cmp = result.company_domain_match
    if cmp is True:
        score += 10
        reasons.append("+10: Company domain matches")
    elif cmp is False:
        score -= 10
        reasons.append("-10: Company domain mismatch")
        failed.append("company_domain_mismatch")

    if hasattr(result, "spf_record") and result.spf_record:
        score += 3
        reasons.append("+3: SPF record found")
    if hasattr(result, "dmarc_record") and result.dmarc_record:
        score += 3
        reasons.append("+3: DMARC record found")

    if not result.syntax_valid:
        score = min(score, 0)

    if result.disposable:
        score = min(score, 15)

    if not mx_found and not null_mx:
        score = min(score, 20)

    if null_mx:
        score = min(score, 10)

    score = max(0, min(100, score))

    result.verification_score = score
    result.score_reasons = reasons
    result.failed_checks = failed
    result.inconclusive_checks = inconclusive

    status = _determine_status(score, result)
    result.verification_status = status.value if hasattr(status, 'value') else status

    result.confidence_level = _determine_confidence(result).value if hasattr(_determine_confidence(result), 'value') else _determine_confidence(result)
    result.risk_level = _determine_risk_level(score, result).value if hasattr(_determine_risk_level(score, result), 'value') else _determine_risk_level(score, result)

    return result


def _determine_status(score: int, result: VerificationResult) -> VerificationStatus:
    if not result.syntax_valid:
        return VerificationStatus.SYNTAX_ERROR

    if result.mx_status in ("NoAnswer", "NXDomain", "NoNameservers", "Timeout", "Error") or (result.dns_status in ("NXDomain",) and not result.mx_records):
        return VerificationStatus.NO_MAIL_SERVER

    catch_all_status = result.catch_all
    if catch_all_status == "Catch-All":
        return VerificationStatus.CATCH_ALL

    if result.role_based and score < 50:
        return VerificationStatus.ROLE_BASED

    if score >= 90:
        return VerificationStatus.VALID
    if score >= 70:
        return VerificationStatus.LIKELY_VALID
    if score >= 40:
        return VerificationStatus.RISKY
    if score > 0:
        return VerificationStatus.INVALID

    return VerificationStatus.INVALID


def _determine_confidence(result: VerificationResult) -> ConfidenceLevel:
    checks_performed = 0
    checks_succeeded = 0

    if result.smtp_attempted:
        checks_performed += 1
        if result.smtp_status.lower() in ("accepted", "rejected"):
            checks_succeeded += 1

    if result.dns_status != "Not Checked":
        checks_performed += 1
        if result.dns_status in ("Resolved", "NXDomain", "NoAnswer"):
            checks_succeeded += 1

    if result.catch_all not in ("Not Tested", "Unknown"):
        checks_performed += 1
        if result.catch_all in ("Catch-All", "Not Catch-All"):
            checks_succeeded += 1

    if checks_performed == 0:
        return ConfidenceLevel.VERY_LOW

    ratio = checks_succeeded / checks_performed

    if ratio >= 0.9 and checks_performed >= 2:
        return ConfidenceLevel.HIGH
    if ratio >= 0.7:
        return ConfidenceLevel.MEDIUM
    if ratio >= 0.4:
        return ConfidenceLevel.LOW

    return ConfidenceLevel.VERY_LOW


def _determine_risk_level(score: int, result: VerificationResult) -> RiskLevel:
    if result.null_mx:
        return RiskLevel.CRITICAL
    if result.catch_all == "Catch-All":
        return RiskLevel.HIGH
    if not result.syntax_valid:
        return RiskLevel.CRITICAL
    if score <= 20:
        return RiskLevel.CRITICAL
    if score <= 40:
        return RiskLevel.HIGH
    if score <= 60:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _build_score_reasons(result: VerificationResult, score: int) -> List[str]:
    return result.score_reasons


def _build_failed_checks(result: VerificationResult) -> List[str]:
    return result.failed_checks


def _build_inconclusive_checks(result: VerificationResult) -> List[str]:
    return result.inconclusive_checks
