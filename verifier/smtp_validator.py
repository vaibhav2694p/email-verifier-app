import smtplib
import socket
import ssl
import time
import logging
import re
from typing import Optional, Tuple, List, Dict
from .models import SmtpResult, SmtpStatus, DnsResult
from .config import VerifierConfig
from .cache import TTLCache

logger = logging.getLogger(__name__)

USER_NOT_FOUND_PATTERN = re.compile(
    r'(?i).*550{1}.*(user|account|customer|mailbox|recipient|invalid|exist|verify).*'
)

GREYLIST_PATTERN = re.compile(
    r'(?i).*(try again|later|temporarily|greylist|greylisting|too fast|rate limit|slow down|wait).*'
)

ANTI_VERIFY_PATTERN = re.compile(
    r'(?i).*(verify|verification|confirm|captcha|blocked|blacklist|spam|policy).*'
)

_smtp_cache = TTLCache(default_ttl=1800)


def verify_smtp(
    email: str,
    domain: str,
    mx_host: str,
    config: VerifierConfig,
    verifier_email: Optional[str] = None,
    verifier_domain: Optional[str] = None,
) -> SmtpResult:
    if not config.enable_smtp_check:
        return SmtpResult(
            attempted=False,
            status=SmtpStatus.SMTP_DISABLED,
            error="SMTP check is disabled",
        )

    cache_key = f"smtp:{email}:{mx_host}:{config.smtp_port}"
    cached = _smtp_cache.get(cache_key)
    if cached is not None:
        return cached

    v_email = verifier_email or config.verifier_email
    v_domain = verifier_domain or config.verifier_domain

    if not v_email or not v_domain:
        return SmtpResult(
            attempted=False,
            status=SmtpStatus.SMTP_DISABLED,
            error="Verifier email/domain not configured",
        )

    start = time.monotonic()
    server = None

    try:
        server = smtplib.SMTP(
            host=mx_host,
            port=config.smtp_port,
            timeout=config.smtp_connection_timeout,
        )
        server.settimeout(config.smtp_response_timeout)

        ehlo_ok, ehlo_msg = _smtp_ehlo(server, v_domain, config.smtp_response_timeout)
        if not ehlo_ok:
            result = SmtpResult(
                attempted=True,
                status=SmtpStatus.CONNECTION_BLOCKED,
                mx_host=mx_host,
                port=config.smtp_port,
                response_time_ms=(time.monotonic() - start) * 1000,
                error=f"EHLO failed: {ehlo_msg}",
            )
            _smtp_cache.set(cache_key, result, ttl=config.smtp_cache_ttl)
            return result

        mail_ok, mail_msg = _smtp_mail_from(server, v_email, config.smtp_response_timeout)
        if not mail_ok:
            result = SmtpResult(
                attempted=True,
                status=SmtpStatus.CONNECTION_BLOCKED,
                mx_host=mx_host,
                port=config.smtp_port,
                response_time_ms=(time.monotonic() - start) * 1000,
                error=f"MAIL FROM failed: {mail_msg}",
            )
            _smtp_cache.set(cache_key, result, ttl=config.smtp_cache_ttl)
            return result

        code, msg = _smtp_rcpt_to(server, email, config.smtp_response_timeout)
        status = _classify_smtp_response(code, msg)

        result = SmtpResult(
            attempted=True,
            status=status,
            code=code,
            message=msg,
            mx_host=mx_host,
            port=config.smtp_port,
            response_time_ms=(time.monotonic() - start) * 1000,
        )
        _smtp_cache.set(cache_key, result, ttl=config.smtp_cache_ttl)
        return result

    except smtplib.SMTPConnectError as e:
        logger.debug("SMTP connect error to %s:%d: %s", mx_host, config.smtp_port, e)
        return SmtpResult(
            attempted=True,
            status=SmtpStatus.CONNECTION_BLOCKED,
            mx_host=mx_host,
            port=config.smtp_port,
            response_time_ms=(time.monotonic() - start) * 1000,
            error=f"Connection refused: {e}",
        )
    except (socket.timeout, TimeoutError) as e:
        logger.debug("SMTP timeout to %s:%d: %s", mx_host, config.smtp_port, e)
        return SmtpResult(
            attempted=True,
            status=SmtpStatus.TIMEOUT,
            mx_host=mx_host,
            port=config.smtp_port,
            response_time_ms=(time.monotonic() - start) * 1000,
            error=f"Timeout: {e}",
        )
    except smtplib.SMTPServerDisconnected as e:
        logger.debug("SMTP server disconnected from %s:%d: %s", mx_host, config.smtp_port, e)
        return SmtpResult(
            attempted=True,
            status=SmtpStatus.CONNECTION_BLOCKED,
            mx_host=mx_host,
            port=config.smtp_port,
            response_time_ms=(time.monotonic() - start) * 1000,
            error=f"Server disconnected: {e}",
        )
    except OSError as e:
        logger.debug("SMTP OS error to %s:%d: %s", mx_host, config.smtp_port, e)
        return SmtpResult(
            attempted=True,
            status=SmtpStatus.CONNECTION_BLOCKED,
            mx_host=mx_host,
            port=config.smtp_port,
            response_time_ms=(time.monotonic() - start) * 1000,
            error=f"Network error: {e}",
        )
    except Exception as e:
        logger.warning("SMTP unexpected error to %s:%d: %s", mx_host, config.smtp_port, e)
        return SmtpResult(
            attempted=True,
            status=SmtpStatus.CONNECTION_BLOCKED,
            mx_host=mx_host,
            port=config.smtp_port,
            response_time_ms=(time.monotonic() - start) * 1000,
            error=f"Unexpected error: {e}",
        )
    finally:
        if server is not None:
            _clean_smtp_session(server)


def _classify_smtp_response(code: int, message: str) -> SmtpStatus:
    if code in (250, 251):
        return SmtpStatus.ACCEPTED
    if code in (550, 551, 552, 553):
        if USER_NOT_FOUND_PATTERN.match(f"{code} {message}"):
            return SmtpStatus.REJECTED
        return SmtpStatus.REJECTED
    if code in (450, 451, 452):
        if GREYLIST_PATTERN.match(message):
            return SmtpStatus.GREYLISTED
        if ANTI_VERIFY_PATTERN.match(message):
            return SmtpStatus.CONNECTION_BLOCKED
        return SmtpStatus.TEMPORARY_FAILURE
    if code in (421,):
        if GREYLIST_PATTERN.match(message):
            return SmtpStatus.GREYLISTED
        return SmtpStatus.TEMPORARY_FAILURE
    return SmtpStatus.UNKNOWN


def _smtp_ehlo(server: smtplib.SMTP, domain: str, timeout: int) -> Tuple[bool, str]:
    try:
        code, msg = server.ehlo(domain)
        if code == 250:
            return True, msg.decode("utf-8", errors="replace") if isinstance(msg, bytes) else str(msg)
        server.helo(domain)
        code2, msg2 = server.ehlo(domain)
        if code2 == 250:
            return True, msg2.decode("utf-8", errors="replace") if isinstance(msg2, bytes) else str(msg2)
        decoded = msg.decode("utf-8", errors="replace") if isinstance(msg, bytes) else str(msg)
        return False, f"EHLO returned {code}: {decoded}"
    except Exception as e:
        return False, str(e)


def _smtp_mail_from(server: smtplib.SMTP, email: str, timeout: int) -> Tuple[bool, str]:
    try:
        code, msg = server.mail(email)
        decoded = msg.decode("utf-8", errors="replace") if isinstance(msg, bytes) else str(msg)
        if code == 250:
            return True, decoded
        return False, f"MAIL FROM returned {code}: {decoded}"
    except Exception as e:
        return False, str(e)


def _smtp_rcpt_to(server: smtplib.SMTP, email: str, timeout: int) -> Tuple[int, str]:
    try:
        code, msg = server.rcpt(email)
        decoded = msg.decode("utf-8", errors="replace") if isinstance(msg, bytes) else str(msg)
        return code, decoded
    except smtplib.SMTPRecipientsRefused as e:
        first_recipient = list(e.recipients.values())[0]
        code = first_recipient[0]
        msg = first_recipient[1].decode("utf-8", errors="replace") if isinstance(first_recipient[1], bytes) else str(first_recipient[1])
        return code, msg
    except Exception as e:
        return 0, str(e)


def _clean_smtp_session(server: smtplib.SMTP):
    try:
        server.quit()
    except Exception:
        try:
            server.close()
        except Exception:
            pass


def verify_smtp_for_domain(
    email: str,
    domain: str,
    mx_records: List[Dict],
    config: VerifierConfig,
) -> SmtpResult:
    if not config.enable_smtp_check:
        return SmtpResult(
            attempted=False,
            status=SmtpStatus.SMTP_DISABLED,
            error="SMTP check is disabled",
        )

    if not mx_records:
        return SmtpResult(
            attempted=False,
            status=SmtpStatus.NOT_ATTEMPTED,
            error="No MX records to test",
        )

    sorted_mx = sorted(mx_records, key=lambda r: r.get("priority", 100))
    attempts = min(len(sorted_mx), config.smtp_max_attempts)

    for i in range(attempts):
        mx_host = sorted_mx[i].get("host", "")
        if not mx_host:
            continue

        result = verify_smtp(
            email=email,
            domain=domain,
            mx_host=mx_host,
            config=config,
        )

        if result.status in (
            SmtpStatus.ACCEPTED,
            SmtpStatus.REJECTED,
            SmtpStatus.CATCH_ALL,
        ):
            return result

        if result.status in (SmtpStatus.CONNECTION_BLOCKED, SmtpStatus.TIMEOUT):
            logger.debug(
                "SMTP %s failed for %s, trying next MX",
                mx_host,
                email,
            )
            continue

        if result.status in (SmtpStatus.TEMPORARY_FAILURE, SmtpStatus.GREYLISTED):
            return result

    last_result = SmtpResult(
        attempted=True,
        status=SmtpStatus.CONNECTION_BLOCKED,
        error="All MX servers failed or blocked",
    )
    return last_result
