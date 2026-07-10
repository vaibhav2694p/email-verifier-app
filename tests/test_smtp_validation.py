import socket
from unittest.mock import MagicMock, patch

import verifier.smtp_validator as _smtp_val
from verifier.config import VerifierConfig
from verifier.models import SmtpStatus
from verifier.smtp_validator import (
    _classify_smtp_response,
    verify_smtp,
)


class TestSmtpClassification:
    """Tests for SMTP response classification."""

    def test_accepted_250(self):
        assert _classify_smtp_response(250, "OK") == SmtpStatus.ACCEPTED

    def test_accepted_251(self):
        assert _classify_smtp_response(251, "User not local") == SmtpStatus.ACCEPTED

    def test_rejected_550(self):
        assert _classify_smtp_response(550, "User unknown") == SmtpStatus.REJECTED

    def test_rejected_553(self):
        assert _classify_smtp_response(553, "Mailbox name not allowed") == SmtpStatus.REJECTED

    def test_temporary_failure_450(self):
        assert _classify_smtp_response(450, "Try again later") == SmtpStatus.GREYLISTED

    def test_greylisted(self):
        assert _classify_smtp_response(450, "Try again in 10 minutes") == SmtpStatus.GREYLISTED

    def test_anti_verification(self):
        assert _classify_smtp_response(550, "Verify your email address") == SmtpStatus.REJECTED


class TestSmtpVerification:
    """Tests for real SMTP verification with mocks."""

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_smtp_accepted(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (250, b"OK")

        config = VerifierConfig(
            enable_smtp_check=True,
            verifier_email="verify@example.com",
            verifier_domain="example.com",
        )
        result = verify_smtp("user@gmail.com", "gmail.com", "aspmx.l.google.com", config)
        assert result.status == SmtpStatus.ACCEPTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_smtp_rejected(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (550, b"User unknown")

        config = VerifierConfig(
            enable_smtp_check=True,
            verifier_email="verify@example.com",
            verifier_domain="example.com",
        )
        result = verify_smtp("nonexistent@gmail.com", "gmail.com", "aspmx.l.google.com", config)
        assert result.status == SmtpStatus.REJECTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_smtp_connection_refused(self, MockSMTP):
        MockSMTP.side_effect = ConnectionRefusedError("Connection refused")

        config = VerifierConfig(
            enable_smtp_check=True,
            verifier_email="verify@example.com",
            verifier_domain="example.com",
        )
        result = verify_smtp("cr@test.com", "test.com", "mx.test.com", config)
        assert result.status == SmtpStatus.CONNECTION_BLOCKED

    def test_smtp_disabled(self):
        config = VerifierConfig(enable_smtp_check=False)
        result = verify_smtp("user@gmail.com", "gmail.com", "aspmx.l.google.com", config)
        assert result.status == SmtpStatus.SMTP_DISABLED


class TestSmtpTestMode:
    """Tests for SMTP test mode (Mailpit / local test server)."""

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_mailpit_connection(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"Mailpit")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = _smtp_val.test_smtp_connection(
            config.test_smtp_host, config.test_smtp_port,
            config.test_smtp_use_tls, timeout=5,
        )
        assert result["connected"] is True
        assert result["host"] == "localhost"
        assert result["port"] == 1025

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_accepted(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (250, b"OK")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("accepted@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.ACCEPTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_rejected(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (550, b"User unknown")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("rejected@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.REJECTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_temporary_failure(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (451, b"Try again later")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("temporary@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.GREYLISTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_greylisted(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (450, b"Try again later")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("greylisted@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.GREYLISTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_catch_all(self, MockSMTP):
        mock_server = MagicMock()
        MockSMTP.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (250, b"OK")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("catchall@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.ACCEPTED

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_timeout(self, MockSMTP):
        MockSMTP.side_effect = socket.timeout("timed out")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("timeout@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.TIMEOUT

    @patch('verifier.smtp_validator.smtplib.SMTP')
    def test_local_smtp_connection_refused(self, MockSMTP):
        MockSMTP.side_effect = ConnectionRefusedError("Connection refused")

        config = VerifierConfig(
            enable_smtp_check=True,
            smtp_test_mode=True,
            test_smtp_host="localhost",
            test_smtp_port=1025,
            verifier_email="verifier@example.test",
            verifier_domain="example.test",
        )
        result = verify_smtp("anyone@example.test", "example.test", "localhost", config)
        assert result.status == SmtpStatus.CONNECTION_BLOCKED


class TestSmtpDisabledFallback:
    """Tests for SMTP disabled and port 25 blocked fallback."""

    def test_smtp_disabled_fallback(self):
        config = VerifierConfig(enable_smtp_check=False, smtp_test_mode=False)
        result = verify_smtp("user@example.com", "example.com", "mx.example.com", config)
        assert result.status == SmtpStatus.SMTP_DISABLED
        assert result.attempted is False

    def test_port_25_blocked_fallback(self):
        with patch('verifier.smtp_validator.check_port_25_available', return_value=False):
            config = VerifierConfig(
                enable_smtp_check=True,
                smtp_test_mode=False,
                verifier_email="verify@example.com",
                verifier_domain="example.com",
            )
            result = verify_smtp("user@example.com", "example.com", "mx.example.com", config)
            assert result.status == SmtpStatus.CONNECTION_BLOCKED

    def test_no_data_command_is_sent(self):
        """Verify that DATA command is never sent during SMTP verification."""
        mock_server = MagicMock()
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (250, b"OK")

        with patch('verifier.smtp_validator.smtplib.SMTP', return_value=mock_server):
            config = VerifierConfig(
                enable_smtp_check=True,
                verifier_email="verify@example.com",
                verifier_domain="example.com",
            )
            verify_smtp("no-data-test@example.com", "example.com", "mx.no-data.example.com", config)
            mock_server.data.assert_not_called()
            mock_server.sendmail.assert_not_called()

    def test_smtp_session_closes_cleanly(self):
        mock_server = MagicMock()
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.mail.return_value = (250, b"OK")
        mock_server.rcpt.return_value = (250, b"OK")

        with patch('verifier.smtp_validator.smtplib.SMTP', return_value=mock_server):
            config = VerifierConfig(
                enable_smtp_check=True,
                verifier_email="verify@example.com",
                verifier_domain="example.com",
            )
            verify_smtp("quit-test@example.com", "example.com", "mx.quit-test.example.com", config)
            mock_server.quit.assert_called_once()
