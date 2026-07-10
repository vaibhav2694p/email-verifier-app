import pytest
from unittest.mock import patch, MagicMock
from verifier.catch_all import detect_catch_all, _generate_random_email, _is_known_catch_all_skip
from verifier.config import VerifierConfig
from verifier.models import CatchAllStatus

class TestCatchAllDetection:
    def test_known_skip_domains(self):
        assert _is_known_catch_all_skip("gmail.com") is True
        assert _is_known_catch_all_skip("yahoo.com") is True
        assert _is_known_catch_all_skip("example.com") is False
    
    def test_random_email_generation(self):
        email = _generate_random_email("test.com")
        assert email.endswith("@test.com")
        local = email.split("@")[0]
        assert len(local) == 15
        assert local.isalnum()
    
    @patch('verifier.catch_all._smtp_probe')
    def test_catch_all_detected(self, mock_probe):
        mock_probe.return_value = (250, "OK")
        config = VerifierConfig(enable_smtp_check=True, verifier_email="verify@test.com", verifier_domain="test.com")
        result = detect_catch_all("example.com", "mx.example.com", config)
        assert result.status == CatchAllStatus.CATCH_ALL
    
    @patch('verifier.catch_all._smtp_probe')
    def test_not_catch_all(self, mock_probe):
        mock_probe.return_value = (550, "User unknown")
        config = VerifierConfig(enable_smtp_check=True, verifier_email="verify@test.com", verifier_domain="test.com")
        result = detect_catch_all("not-catchall-test.com", "mx.not-catchall-test.com", config)
        assert result.status == CatchAllStatus.NOT_CATCH_ALL
    
    def test_skip_known_providers(self):
        config = VerifierConfig(enable_smtp_check=True)
        result = detect_catch_all("gmail.com", "aspmx.l.google.com", config)
        assert result.status == CatchAllStatus.NOT_CATCH_ALL
