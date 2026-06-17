from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from email_verifier.dns_checks import DnsVerifier
from email_verifier.email_checks import extract_domain, normalize_email, validate_email_format
from email_verifier.linkedin import build_linkedin_search_url
from email_verifier.name_extractor import extract_names_from_email
from email_verifier.professional_check import is_disposable_email, is_free_email, is_role_account
from email_verifier.smtp_check import verify_mailbox_smtp


@dataclass
class VerificationDetail:
    status: str
    valid: bool
    details: str = ""


FINAL_STATUS_MAP = {
    "OK": "✅ Send",
    "Catch-All": "⚠️ Send carefully",
    "Risky": "⚠️ Review first",
    "Invalid": "❌ Do not send",
    "Disposable": "❌ Do not send",
    "Unknown": "⚠️ Usually avoid",
    "Duplicate": "Remove",
}


@dataclass
class EnhancedVerificationResult:
    email: str
    domain: str

    format_check: VerificationDetail = field(default_factory=lambda: VerificationDetail("", False))
    professional_check: VerificationDetail = field(default_factory=lambda: VerificationDetail("", False))
    domain_check: VerificationDetail = field(default_factory=lambda: VerificationDetail("", False))
    mailbox_check: VerificationDetail = field(default_factory=lambda: VerificationDetail("", False))

    final_status: str = ""
    score: int = 0
    verification_date: str = ""
    verification_time: str = ""
    send_decision: str = ""

    first_name: str = ""
    last_name: str = ""
    full_name: str = ""

    mx_records_available: bool = False
    catch_all: bool | None = None
    provider_type: str = ""
    disposable_email: bool = False
    role_account: bool = False
    is_duplicate: bool = False
    smtp_response: str = ""
    smtp_status: str = ""
    linkedin_url: str = ""
    website_status: str = ""
    verification_source: str = "Real-Time"
    domain_exists: bool = False


def verify_single_email(
    email_address: str,
    seen_emails: set[str] | None = None,
) -> EnhancedVerificationResult:
    email = normalize_email(email_address)
    domain = extract_domain(email)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d-%b-%Y")
    time_str = now.strftime("%I:%M %p UTC")

    result = EnhancedVerificationResult(
        email=email,
        domain=domain,
        verification_date=date_str,
        verification_time=time_str,
    )

    if seen_emails is not None:
        if email in seen_emails:
            result.is_duplicate = True
            result.final_status = "Duplicate"
            result.send_decision = FINAL_STATUS_MAP["Duplicate"]
            return result
        seen_emails.add(email)

    format_valid, format_reason = validate_email_format(email)
    result.format_check = VerificationDetail(
        status="Valid" if format_valid else "Invalid",
        valid=format_valid,
        details=format_reason if not format_valid else "Email syntax is correct.",
    )

    if not format_valid:
        result.final_status = "Invalid"
        result.send_decision = FINAL_STATUS_MAP["Invalid"]
        return result

    is_free = is_free_email(domain)
    is_disposable = is_disposable_email(domain)
    result.disposable_email = is_disposable
    result.provider_type = "Free" if is_free else "Business"

    if is_disposable:
        result.professional_check = VerificationDetail(
            status="Invalid", valid=False,
            details="Domain is a disposable/temporary email provider.",
        )
    elif is_free:
        result.professional_check = VerificationDetail(
            status="Invalid", valid=False,
            details="Domain is a free webmail provider.",
        )
    else:
        result.professional_check = VerificationDetail(
            status="Valid", valid=True,
            details="Professional business domain.",
        )

    local_part = email.split("@")[0] if "@" in email else ""
    result.role_account = is_role_account(local_part)

    result.linkedin_url = build_linkedin_search_url(
        name=result.first_name or result.full_name, company="",
    )

    dns_verifier = DnsVerifier(timeout=5.0)
    dns_result = dns_verifier.verify_domain(domain) if domain else None

    domain_exists = False
    mx_available = False
    if dns_result and dns_result.exists:
        domain_exists = True
        mx_available = dns_result.mx.found
        result.mx_records_available = mx_available
        result.domain_exists = True

        result.domain_check = VerificationDetail(
            status="Valid", valid=True,
            details="Domain exists with valid DNS records.",
        )
    elif dns_result:
        result.domain_check = VerificationDetail(
            status="Invalid", valid=False,
            details=f"{dns_result.existence_status}. No valid DNS records.",
        )
    else:
        result.domain_check = VerificationDetail(
            status="Invalid", valid=False,
            details="Could not resolve domain.",
        )

    mx_found = dns_result and dns_result.mx.found
    result.mx_records_available = bool(mx_found)

    if not domain_exists or not mx_found:
        result.final_status = "Invalid"
        result.send_decision = FINAL_STATUS_MAP["Invalid"]
        result.mailbox_check = VerificationDetail(
            status="Invalid", valid=False,
            details="Cannot verify mailbox: domain or MX records missing.",
        )
        names = extract_names_from_email(email)
        result.first_name = names["first_name"]
        result.last_name = names["last_name"]
        result.full_name = names["full_name"]
        result.score = _calculate_score(result)
        return result

    smtp_result = verify_mailbox_smtp(email, domain)
    result.smtp_response = smtp_result.error or "Mail server responded"
    result.catch_all = smtp_result.catch_all

    if smtp_result.mailbox_exists is True:
        result.mailbox_check = VerificationDetail(
            status="Exists", valid=True,
            details="Mail server confirmed the mailbox exists.",
        )
        result.smtp_status = "Exists"
    elif smtp_result.mailbox_exists is False:
        result.mailbox_check = VerificationDetail(
            status="Not Found", valid=False,
            details=f"Mail server rejected the recipient: {smtp_result.error}",
        )
        result.smtp_status = "Not Found"
    elif smtp_result.error and ("timed out" in smtp_result.error.lower() or "timeout" in smtp_result.error.lower() or "connection" in smtp_result.error.lower() or "refused" in smtp_result.error.lower()):
        result.mailbox_check = VerificationDetail(
            status="Blocked", valid=False,
            details=f"SMTP connection blocked or timed out: {smtp_result.error}",
        )
        result.smtp_status = "Blocked"
    else:
        result.mailbox_check = VerificationDetail(
            status="Unknown", valid=False,
            details=f"Could not verify mailbox: {smtp_result.error or 'No response'}",
        )
        result.smtp_status = "Unknown"

    names = extract_names_from_email(email)
    result.first_name = names["first_name"]
    result.last_name = names["last_name"]
    result.full_name = names["full_name"]

    result.final_status = _determine_final_status(result)
    result.send_decision = FINAL_STATUS_MAP.get(result.final_status, "")
    result.score = _calculate_score(result)

    return result


def _determine_final_status(result: EnhancedVerificationResult) -> str:
    if result.is_duplicate:
        return "Duplicate"
    if not result.format_check.valid:
        return "Invalid"
    if not result.domain_exists or not result.mx_records_available:
        return "Invalid"
    if result.disposable_email:
        return "Disposable"
    if result.role_account:
        return "Risky"
    if result.catch_all is True:
        return "Catch-All"
    if result.smtp_status == "Exists":
        return "OK"
    return "Unknown"


def _calculate_score(result: EnhancedVerificationResult) -> int:
    score = 0
    if result.format_check.valid:
        score += 25
    if result.domain_exists:
        score += 20
    if result.mx_records_available:
        score += 20
    if not result.disposable_email:
        score += 10
    if result.smtp_status == "Exists":
        score += 25
    elif result.smtp_status == "Blocked" or result.smtp_status == "Unknown":
        score += 10
    return min(score, 100)
