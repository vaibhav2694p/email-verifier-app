from __future__ import annotations

import pytest

from safe_email_check import (
    SafeEmailError,
    validate_email_address,
    validate_login_email,
    validate_signup_email,
)

KNOWN_GOOD_DOMAIN = "gmail.com"


def test_valid_normal_email() -> None:
    result = validate_login_email("user@gmail.com")
    assert result.normalized_email == "user@gmail.com"
    assert result.local_part == "user"
    assert result.domain == "gmail.com"
    assert result.deliverability_checked is False


def test_normalized_casing() -> None:
    result = validate_login_email("User@Gmail.COM")
    assert result.domain == "gmail.com"
    assert result.normalized_email.endswith("@gmail.com")


def test_invalid_email_syntax() -> None:
    with pytest.raises(SafeEmailError, match="@-sign"):
        validate_login_email("not-an-email")


def test_unicode_email() -> None:
    result = validate_login_email("üser@gmail.com")
    assert result.local_part == "üser"
    assert result.domain == "gmail.com"
    assert result.deliverability_checked is False


def test_display_name_allowed() -> None:
    result = validate_email_address(
        "User <test@gmail.com>", allow_display_name=True, check_deliverability=False
    )
    assert result.display_name == "User"
    assert result.normalized_email == "test@gmail.com"


def test_display_name_rejected_by_default() -> None:
    with pytest.raises(SafeEmailError, match="display name"):
        validate_login_email("User <test@gmail.com>")


def test_localhost_rejected_by_default() -> None:
    with pytest.raises(SafeEmailError, match="should have a period"):
        validate_login_email("user@localhost")


def test_localhost_allowed_in_test_env() -> None:
    result = validate_email_address(
        "user@localhost.localdomain", test_environment=True, check_deliverability=False
    )
    assert result.domain == "localhost.localdomain"


def test_login_validation_skips_dns() -> None:
    result = validate_login_email("user@gmail.com")
    assert result.deliverability_checked is False
    assert result.is_deliverable is None


def test_signup_validation_checks_dns() -> None:
    result = validate_signup_email("user@gmail.com")
    assert result.deliverability_checked is True
    assert result.is_deliverable is True


def test_domain_without_mx_raises_error() -> None:
    with pytest.raises(SafeEmailError):
        validate_signup_email("user@nonexistent-domain-test-xyz.com")


def test_quoted_local_part_rejected() -> None:
    with pytest.raises(SafeEmailError, match="Quoting"):
        validate_login_email('"quoted"@gmail.com')


def test_domain_literal_rejected() -> None:
    with pytest.raises(SafeEmailError, match="bracketed IP"):
        validate_login_email("user@[192.168.1.1]")


def test_no_score_generated() -> None:
    result = validate_login_email("user@gmail.com")
    assert not hasattr(result, "score")
    assert not hasattr(result, "verification_score")


def test_login_returns_no_dns_info() -> None:
    result = validate_login_email("user@gmail.com")
    assert result.deliverability_checked is False
    assert result.is_deliverable is None
    assert result.normalized_email == "user@gmail.com"


def test_signup_rejects_bad_domain() -> None:
    with pytest.raises(SafeEmailError, match="does not exist"):
        validate_signup_email("user@thiscertainlydoesnotexist123456.com")


def test_signup_accepts_deliverable_domain() -> None:
    result = validate_signup_email(f"test@{KNOWN_GOOD_DOMAIN}")
    assert result.is_deliverable is True
    assert result.deliverability_checked is True
