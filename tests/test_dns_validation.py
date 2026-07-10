from unittest.mock import MagicMock, patch

import dns.name
import dns.resolver

from verifier.dns_validator import classify_mx_provider, detect_null_mx, validate_dns
from verifier.models import DnsStatus


class TestDnsValidation:
    @patch('dns.resolver.Resolver.resolve')
    def test_valid_mx_records(self, mock_resolve):
        mock_mx1 = MagicMock()
        mock_mx1.preference = 10
        mock_mx1.exchange = "mx1.example.com."
        mock_mx2 = MagicMock()
        mock_mx2.preference = 20
        mock_mx2.exchange = "mx2.example.com."
        mock_resolve.return_value = [mock_mx1, mock_mx2]

        result = validate_dns("example.com")
        assert result.has_mx is True
        assert result.status == DnsStatus.RESOLVED
        assert len(result.mx_records) == 2

    @patch('dns.resolver.Resolver.resolve')
    def test_nxdomain(self, mock_resolve):
        mock_resolve.side_effect = dns.resolver.NXDOMAIN()
        result = validate_dns("nonexistent-domain-test-xyz.com")
        assert result.status == DnsStatus.NXDOMAIN
        assert result.has_mx is False

    @patch('dns.resolver.Resolver.resolve')
    def test_no_answer(self, mock_resolve):
        mock_resolve.side_effect = dns.resolver.NoAnswer()
        result = validate_dns("no-answer-test-xyz.com")
        assert result.status == DnsStatus.NO_ANSWER
        assert result.has_mx is False

    @patch('dns.resolver.Resolver.resolve')
    def test_timeout(self, mock_resolve):
        mock_resolve.side_effect = dns.exception.Timeout()
        result = validate_dns("slow-domain.com")
        assert result.status == DnsStatus.TIMEOUT
        assert result.has_mx is False

    @patch('dns.resolver.Resolver.resolve')
    def test_servfail(self, mock_resolve):
        mock_resolve.side_effect = dns.resolver.NoNameservers()
        result = validate_dns("broken-domain.com")
        assert result.status == DnsStatus.NO_NAMESERVERS
        assert result.has_mx is False

class TestNullMx:
    def test_null_mx_detected(self):
        mx_records = [{"priority": 0, "host": ""}]
        assert detect_null_mx(mx_records) is True

    def test_normal_mx(self):
        mx_records = [{"priority": 10, "host": "mx1.example.com"}]
        assert detect_null_mx(mx_records) is False

    def test_empty_records(self):
        assert detect_null_mx([]) is False

class TestMxProvider:
    def test_google_workspace(self):
        mx_records = [{"host": "aspmx.l.google.com", "priority": 10}]
        assert classify_mx_provider(mx_records) == "Google Workspace"

    def test_microsoft_365(self):
        mx_records = [{"host": "example-com.outlook.com", "priority": 0}]
        assert classify_mx_provider(mx_records) == "Microsoft 365"

    def test_unknown_provider(self):
        mx_records = [{"host": "mx.unknown-provider.com", "priority": 10}]
        assert classify_mx_provider(mx_records) == "Unknown"
