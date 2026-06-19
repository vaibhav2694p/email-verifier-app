from __future__ import annotations

from email_validator import EmailNotValidError, validate_email

from safe_email_check.exceptions import SafeEmailError
from safe_email_check.types import EmailCheckResult


def validate_email_address(
    email: str,
    *,
    check_deliverability: bool = True,
    allow_display_name: bool = False,
    test_environment: bool = False,
) -> EmailCheckResult:
    try:
        info = validate_email(
            email,
            check_deliverability=check_deliverability,
            allow_display_name=allow_display_name,
            test_environment=test_environment,
            allow_quoted_local=False,
            allow_domain_literal=False,
            strict=True,
        )

        return EmailCheckResult(
            original=email,
            normalized_email=info.normalized,
            local_part=info.local_part,
            domain=info.domain,
            ascii_email=getattr(info, "ascii_email", None),
            ascii_domain=getattr(info, "ascii_domain", None),
            display_name=getattr(info, "display_name", None),
            deliverability_checked=check_deliverability,
            is_deliverable=True if check_deliverability else None,
        )

    except EmailNotValidError as e:
        raise SafeEmailError(str(e))


def validate_signup_email(
    email: str,
    allow_display_name: bool = False,
) -> EmailCheckResult:
    return validate_email_address(
        email,
        check_deliverability=True,
        allow_display_name=allow_display_name,
    )


def validate_login_email(
    email: str,
    allow_display_name: bool = False,
) -> EmailCheckResult:
    return validate_email_address(
        email,
        check_deliverability=False,
        allow_display_name=allow_display_name,
    )
