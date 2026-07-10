from __future__ import annotations

from .models import VerificationResult

GREYLIST_TEXT = ("greylist", "try again", "try later", "temporar", "rate limit", "defer")
TEMP_CODES = {421, 450, 451, 452}


def apply_greylist_analysis(result: VerificationResult) -> VerificationResult:
    message = (result.smtp_message or "").lower()
    code = int(result.smtp_code or 0)
    status = (result.smtp_status or "").lower()

    is_temp = code in TEMP_CODES or status in {"temporary_failure", "greylisted", "timeout"}
    is_grey = is_temp and any(token in message for token in GREYLIST_TEXT)

    result.greylisting_detected = is_grey
    result.smtp_greylisted = is_grey
    result.temporary_failure = is_temp
    result.retry_required = is_temp
    result.final_smtp_status = result.smtp_status
    if is_temp and not result.reason:
        result.reason = "SMTP temporary failure; retry later"
    return result
