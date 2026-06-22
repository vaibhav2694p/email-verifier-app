import pytest
from utils.email_checks import (
    validate_and_normalize_email,
    extract_email_domain,
    is_public_email_domain,
    is_disposable_domain,
    is_role_based_email,
)
from utils.domain_checks import clean_domain
from utils.scoring import calculate_verification_score


def test_public_email_scoring():
    email = "random@gmail.com"
    normalized = validate_and_normalize_email(email)
    domain = extract_email_domain(normalized)
    score = calculate_verification_score(
        normalized_email=normalized,
        domain=domain,
        has_mx=True,
        website_active=True,
        email_provider="Google Workspace",
        company_match=False,
        is_role_based=False,
        is_disposable=False,
        is_public_email=True,
    )
    assert score <= 45, f"Public email scored {score}, expected <= 45"


def test_nonexistent_domain():
    email = "fake@nonexistent-domain-test-xyz.com"
    try:
        normalized = validate_and_normalize_email(email)
    except ValueError:
        normalized = email
    domain = extract_email_domain(normalized)
    score = calculate_verification_score(
        normalized_email=normalized,
        domain=domain,
        has_mx=False,
        website_active=False,
        email_provider="Unknown/Other",
        company_match=None,
        is_role_based=False,
        is_disposable=False,
        is_public_email=False,
    )
    assert score <= 20, f"Nonexistent domain scored {score}, expected <= 20"


def test_role_based_email():
    email = "info@company.com"
    normalized = validate_and_normalize_email(email)
    domain = extract_email_domain(normalized)
    score = calculate_verification_score(
        normalized_email=normalized,
        domain=domain,
        has_mx=True,
        website_active=True,
        email_provider="Unknown/Other",
        company_match=True,
        is_role_based=True,
        is_disposable=False,
        is_public_email=False,
    )
    assert score < 90, f"Role-based email scored {score}, expected < 90"


def test_high_score_conditions():
    email = "user@company.com"
    normalized = validate_and_normalize_email(email)
    domain = extract_email_domain(normalized)
    score = calculate_verification_score(
        normalized_email=normalized,
        domain=domain,
        has_mx=True,
        website_active=True,
        email_provider="Google Workspace",
        company_match=True,
        is_role_based=False,
        is_disposable=False,
        is_public_email=False,
    )
    assert score >= 80, f"Ideal email scored {score}, expected >= 80"


def test_company_mismatch():
    email = "user@different.com"
    normalized = validate_and_normalize_email(email)
    domain = extract_email_domain(normalized)
    score = calculate_verification_score(
        normalized_email=normalized,
        domain=domain,
        has_mx=True,
        website_active=True,
        email_provider="Unknown/Other",
        company_match=False,
        is_role_based=False,
        is_disposable=False,
        is_public_email=False,
    )
    assert score <= 50, f"Company mismatch scored {score}, expected <= 50"


def test_invalid_email():
    email = "invalid-email"
    with pytest.raises(ValueError):
        validate_and_normalize_email(email)
    score = calculate_verification_score(
        normalized_email=email,
        domain="",
        has_mx=False,
        website_active=False,
        email_provider="Unknown/Other",
        company_match=None,
        is_role_based=False,
        is_disposable=False,
        is_public_email=False,
    )
    assert score <= 20, f"Invalid email scored {score}, expected <= 20 (no MX cap)"


def test_disposable_email():
    email = "test@mailinator.com"
    normalized = validate_and_normalize_email(email)
    domain = extract_email_domain(normalized)
    score = calculate_verification_score(
        normalized_email=normalized,
        domain=domain,
        has_mx=True,
        website_active=True,
        email_provider="Unknown/Other",
        company_match=None,
        is_role_based=False,
        is_disposable=True,
        is_public_email=False,
    )
    assert score <= 10, f"Disposable email scored {score}, expected <= 10"


def test_clean_domain():
    test_cases = [
        ("https://www.company.com/path", "company.com"),
        ("HTTP://WWW.EXAMPLE.CO.UK:8080/", "example.co.uk"),
        ("sub.domain.com", "sub.domain.com"),
        ("", ""),
        ("   test.com   ", "test.com"),
        ("https://user:pass@example.com", "example.com"),
    ]
    for input_val, expected in test_cases:
        result = clean_domain(input_val)
        assert result == expected, f"clean_domain('{input_val}') = '{result}', expected '{expected}'"


def test_extract_email_domain():
    assert extract_email_domain("vaibhav@safebooksglobal.com") == "safebooksglobal.com"
    assert extract_email_domain("test@sub.domain.co.uk") == "sub.domain.co.uk"
    assert extract_email_domain("invalid-email") == ""
    assert extract_email_domain("") == ""
