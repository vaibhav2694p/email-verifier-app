import pytest
from verifier.syntax_validator import validate_syntax, validate_domain_syntax

class TestEmailSyntaxValidation:
    def test_valid_simple_email(self):
        result = validate_syntax("user@example.com")
        assert result.is_valid is True
        assert result.local_part == "user"
        assert result.domain == "example.com"
    
    def test_valid_email_with_dots(self):
        result = validate_syntax("first.last@example.com")
        assert result.is_valid is True
    
    def test_valid_email_with_plus(self):
        result = validate_syntax("user+tag@example.com")
        assert result.is_valid is True
    
    def test_empty_email(self):
        result = validate_syntax("")
        assert result.is_valid is False
    
    def test_no_at_sign(self):
        result = validate_syntax("userexample.com")
        assert result.is_valid is False
    
    def test_duplicate_at_sign(self):
        result = validate_syntax("user@@example.com")
        assert result.is_valid is True
    
    def test_empty_local_part(self):
        result = validate_syntax("@example.com")
        assert result.is_valid is False
    
    def test_empty_domain(self):
        result = validate_syntax("user@")
        assert result.is_valid is False
    
    def test_consecutive_dots_in_local(self):
        result = validate_syntax("user..name@example.com")
        assert result.is_valid is False
    
    def test_leading_dot_in_local(self):
        result = validate_syntax(".user@example.com")
        assert result.is_valid is False
    
    def test_trailing_dot_in_local(self):
        result = validate_syntax("user.@example.com")
        assert result.is_valid is False
    
    def test_domain_no_tld(self):
        result = validate_syntax("user@localhost")
        assert result.is_valid is False
    
    def test_long_local_part(self):
        result = validate_syntax("a" * 65 + "@example.com")
        assert result.is_valid is False
    
    def test_long_total_address(self):
        result = validate_syntax("a" * 64 + "@" + "b" * 64 + ".com")
        assert result.is_valid is False
        assert "exceeds" in result.error
    
    def test_domain_label_too_long(self):
        result = validate_syntax("user@" + "a" * 64 + ".com")
        assert result.is_valid is False
    
    def test_whitespace_stripped(self):
        result = validate_syntax("  user@example.com  ")
        assert result.is_valid is True
        assert result.normalized_email == "user@example.com"
    
    def test_lowercase_domain(self):
        result = validate_syntax("user@EXAMPLE.COM")
        assert result.is_valid is True
        assert result.domain == "example.com"
    
    def test_idn_domain(self):
        result = validate_syntax("user@münchen.de")
        assert result.is_valid is True
        assert result.idn_domain is True
    
    def test_invalid_chars(self):
        result = validate_syntax("user name@example.com")
        assert result.is_valid is False
    
    def test_valid_numeric_local(self):
        result = validate_syntax("123@example.com")
        assert result.is_valid is True
    
    def test_domain_with_hyphen(self):
        result = validate_syntax("user@my-domain.com")
        assert result.is_valid is True
    
    def test_domain_starts_with_hyphen(self):
        result = validate_syntax("user@-example.com")
        assert result.is_valid is False
    
    def test_tld_numeric(self):
        result = validate_syntax("user@example.123")
        assert result.is_valid is False

class TestDomainSyntax:
    def test_valid_domain(self):
        valid, error = validate_domain_syntax("example.com")
        assert valid is True
    
    def test_empty_domain(self):
        valid, error = validate_domain_syntax("")
        assert valid is False
    
    def test_no_tld(self):
        valid, error = validate_domain_syntax("localhost")
        assert valid is False
