import pytest

from verifier.normalizer import normalize_domain, normalize_email, split_email


class TestNormalizeEmail:
    def test_lowercase(self):
        assert normalize_email("User@Example.COM") == "user@example.com"

    def test_strip_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_single_at(self):
        assert normalize_email("user@example.com") == "user@example.com"

    def test_empty(self):
        with pytest.raises(Exception):
            normalize_email("")

    def test_no_at(self):
        with pytest.raises(Exception):
            normalize_email("userexample.com")

class TestSplitEmail:
    def test_normal(self):
        local, domain = split_email("user@example.com")
        assert local == "user"
        assert domain == "example.com"

    def test_no_at(self):
        with pytest.raises(Exception):
            split_email("userexample.com")

class TestNormalizeDomain:
    def test_strips_protocol(self):
        assert normalize_domain("https://example.com") == "example.com"

    def test_strips_www(self):
        assert normalize_domain("www.example.com") == "example.com"

    def test_strips_trailing_slash(self):
        assert normalize_domain("example.com/") == "example.com"

    def test_strips_at(self):
        assert normalize_domain("user@example.com") == "example.com"
