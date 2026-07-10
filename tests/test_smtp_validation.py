import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from verifier.smtp_validator import (
    verify_smtp, _classify_smtp_response, _clean_smtp_session
)
from verifier.config import VerifierConfig
from verifier.models import SmtpStatus

class TestSmtpClassification:
    def test_accepted_250(self):
        status = _classify_smtp_response(250, "OK")
        assert status == SmtpStatus.ACCEPTED
    
    def test_accepted_251(self):
        status = _classify_smtp_response(251, "User not local")
        assert status == SmtpStatus.ACCEPTED
    
    def test_rejected_550(self):
        status = _classify_smtp_response(550, "User unknown")
        assert status == SmtpStatus.REJECTED
    
    def test_rejected_553(self):
        status = _classify_smtp_response(553, "Mailbox name not allowed")
        assert status == SmtpStatus.REJECTED
    
    def test_temporary_failure_450(self):
        status = _classify_smtp_response(450, "Try again later")
        assert status == SmtpStatus.GREYLISTED
    
    def test_greylisted(self):
        status = _classify_smtp_response(450, "Try again in 10 minutes")
        assert status == SmtpStatus.GREYLISTED
    
    def test_anti_verification(self):
        status = _classify_smtp_response(550, "Verify your email address")
        assert status == SmtpStatus.REJECTED

class TestSmtpVerification:
    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_smtp_accepted(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (250, b"OK")
        mock_server.noop.return_value = (250, b"OK")
        
        config = VerifierConfig(
            enable_smtp_check=True,
            verifier_email="verify@example.com",
            verifier_domain="example.com",
        )
        result = verify_smtp(
            "user@gmail.com", "gmail.com", "aspmx.l.google.com", config
        )
        assert result.status == SmtpStatus.ACCEPTED
    
    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_smtp_rejected(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (550, b"User unknown")
        mock_server.noop.return_value = (250, b"OK")
        
        config = VerifierConfig(
            enable_smtp_check=True,
            verifier_email="verify@example.com",
            verifier_domain="example.com",
        )
        result = verify_smtp(
            "nonexistent@gmail.com", "gmail.com", "aspmx.l.google.com", config
        )
        assert result.status == SmtpStatus.REJECTED
    
    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_smtp_connection_refused(self, MockSMTP):
        MockSMTP.side_effect = ConnectionRefusedError("Connection refused")
        
        config = VerifierConfig(
            enable_smtp_check=True,
            verifier_email="verify@example.com",
            verifier_domain="example.com",
        )
        result = verify_smtp(
            "cr-test-user@gmail.com", "gmail.com", "cr-test-mx.google.com", config
        )
        assert result.status == SmtpStatus.CONNECTION_BLOCKED

    def test_smtp_disabled(self):
        config = VerifierConfig(enable_smtp_check=False)
        result = verify_smtp(
            "user@gmail.com", "gmail.com", "aspmx.l.google.com", config
        )
        assert result.status == SmtpStatus.SMTP_DISABLED
