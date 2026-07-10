from __future__ import annotations

from .models import VerificationResult


def classify_result(result: VerificationResult) -> VerificationResult:
    """Final deterministic classifier. Scoring explains quality; this sets status/action."""
    status = "Unknown"
    action = "Manual Review"
    reason = result.reason or "Verification completed with available public signals"

    if result.is_duplicate:
        status, action, reason = "Duplicate", "Manual Review", "Duplicate of first normalized occurrence"
    elif not result.syntax_valid:
        status, action, reason = "Syntax Error", "Correct Typo First", result.syntax_error or "Invalid email syntax"
    elif not result.domain:
        status, action, reason = "No Domain", "Do Not Send", "No domain part found"
    elif result.null_mx:
        status, action, reason = "Invalid", "Do Not Send", "Domain publishes Null MX and does not accept email"
    elif result.dns_status == "NXDomain":
        status, action, reason = "Invalid", "Do Not Send", "Domain does not exist"
    elif result.mx_status in ("NoAnswer", "NoNameservers") and not result.mx_records:
        status, action, reason = "No MX", "Do Not Send", "No valid mail route found"
    elif result.abuse_address:
        status, action, reason = "Abuse", "Do Not Send", result.abuse_reason or "Abuse/system mailbox"
    elif result.disposable:
        status, action, reason = "Disposable", "Do Not Send", "Disposable email provider"
    elif result.confirmed_trap:
        status, action, reason = "Do Not Mail", "Do Not Send", "Confirmed trap from configured trusted dataset"
    elif result.toxic_risk == "High":
        status, action, reason = "Toxic Risk", "Do Not Send", "High toxic-risk signals"
    elif result.spam_trap_risk == "High":
        status, action, reason = "Spam Trap Risk", "Manual Review", "High spam-trap risk signals"
    elif result.mailbox_full:
        status, action, reason = "Mailbox Full", "Retry Later", "SMTP indicated mailbox full"
    elif result.greylisting_detected:
        status, action, reason = "Greylisted", "Retry Later", "SMTP indicated greylisting or temporary deferral"
    elif result.temporary_failure:
        status, action, reason = "Temporary Failure", "Retry Later", "SMTP temporary failure or timeout"
    elif result.smtp_blocked or result.smtp_port_blocked:
        status, action, reason = "SMTP Blocked", "Provider Protected", "SMTP verification unavailable or blocked"
    elif result.catch_all == "Catch-All":
        status, action, reason = "Catch-All", "Catch-All: Send Carefully", "Domain appears to accept random recipients"
    elif result.role_based:
        status, action, reason = "Role Account", "Role Account: Review First", "Shared role mailbox"
    elif result.mailbox_rejected:
        status, action, reason = "Invalid", "Do Not Send", "SMTP permanently rejected mailbox"
    elif result.mailbox_accepted and result.catch_all != "Catch-All" and result.verification_score >= 70:
        status, action, reason = "Valid", "Safe to Send", "SMTP accepted recipient and no major risks were found"
    elif result.syntax_valid and result.mx_records and result.verification_score >= 50:
        status, action, reason = "Likely Valid", "Send with Caution", "Valid syntax, domain, and MX; mailbox verification is inconclusive or unavailable"
    else:
        status, action = "Unknown", "Manual Review"

    result.verification_status = status
    result.recommended_action = action
    result.reason = reason
    result.do_not_mail = result.do_not_mail or action == "Do Not Send"
    result.deliverability_score = result.verification_score
    return result
