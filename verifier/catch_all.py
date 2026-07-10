import random
import string
import hashlib
import time
import logging
import smtplib
import socket
from typing import Optional, Tuple
from .models import CatchAllResult, CatchAllStatus, SmtpResult, SmtpStatus
from .config import VerifierConfig
from .cache import TTLCache

logger = logging.getLogger(__name__)

_catch_all_cache = TTLCache(default_ttl=86400)

KNOWN_CATCH_ALL_SKIP = {
    "gmail.com", "googlemail.com", "hotmail.com", "outlook.com",
    "yahoo.com", "live.com", "aol.com", "msn.com",
}


def detect_catch_all(
    domain: str,
    mx_host: str,
    config: VerifierConfig,
    target_email: Optional[str] = None,
) -> CatchAllResult:
    if _is_known_catch_all_skip(domain):
        return CatchAllResult(
            status=CatchAllStatus.NOT_CATCH_ALL,
            confidence=1.0,
            tested=True,
            test_domain=domain,
        )

    cache_key = f"catchall:{domain}"
    cached = _catch_all_cache.get(cache_key)
    if cached is not None:
        return cached

    v_email = config.verifier_email
    v_domain = config.verifier_domain

    if not v_email or not v_domain:
        result = CatchAllResult(
            status=CatchAllStatus.UNKNOWN,
            confidence=0.0,
            tested=False,
            test_domain=domain,
        )
        _catch_all_cache.set(cache_key, result, ttl=config.catch_all_cache_ttl)
        return result

    random_email = _generate_random_email(domain)
    code, msg = _smtp_probe(
        email=random_email,
        mx_host=mx_host,
        port=config.smtp_port,
        verifier_email=v_email,
        verifier_domain=v_domain,
        connection_timeout=config.smtp_connection_timeout,
        response_timeout=config.smtp_response_timeout,
    )

    if code == 0:
        result = CatchAllResult(
            status=CatchAllStatus.UNKNOWN,
            confidence=0.0,
            tested=True,
            random_email_accepted=False,
            test_domain=domain,
        )
        _catch_all_cache.set(cache_key, result, ttl=config.catch_all_cache_ttl)
        return result

    if code in (250, 251):
        result = CatchAllResult(
            status=CatchAllStatus.CATCH_ALL,
            confidence=0.85,
            tested=True,
            random_email_accepted=True,
            test_domain=domain,
        )
        _catch_all_cache.set(cache_key, result, ttl=config.catch_all_cache_ttl)
        return result

    if code in (550, 551, 552, 553):
        result = CatchAllResult(
            status=CatchAllStatus.NOT_CATCH_ALL,
            confidence=0.9,
            tested=True,
            random_email_accepted=False,
            test_domain=domain,
        )
        _catch_all_cache.set(cache_key, result, ttl=config.catch_all_cache_ttl)
        return result

    if code in (450, 451, 452):
        result = CatchAllResult(
            status=CatchAllStatus.UNKNOWN,
            confidence=0.3,
            tested=True,
            random_email_accepted=False,
            test_domain=domain,
        )
        _catch_all_cache.set(cache_key, result, ttl=config.catch_all_cache_ttl)
        return result

    result = CatchAllResult(
        status=CatchAllStatus.UNKNOWN,
        confidence=0.1,
        tested=True,
        random_email_accepted=False,
        test_domain=domain,
    )
    _catch_all_cache.set(cache_key, result, ttl=config.catch_all_cache_ttl)
    return result


def _generate_random_email(domain: str, length: int = 15) -> str:
    chars = string.ascii_lowercase + string.digits
    random_part = "".join(random.choices(chars, k=length))
    return f"{random_part}@{domain}"


def _is_known_catch_all_skip(domain: str) -> bool:
    normalized = domain.lower().strip()
    if normalized in KNOWN_CATCH_ALL_SKIP:
        return True
    parts = normalized.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in KNOWN_CATCH_ALL_SKIP:
            return True
    return False


def _smtp_probe(
    email: str,
    mx_host: str,
    port: int,
    verifier_email: str,
    verifier_domain: str,
    connection_timeout: int,
    response_timeout: int,
) -> Tuple[int, str]:
    server = None
    try:
        server = smtplib.SMTP(
            host=mx_host,
            port=port,
            timeout=connection_timeout,
        )
        server.settimeout(response_timeout)

        code, msg = server.ehlo(verifier_domain)
        if code != 250:
            try:
                code, msg = server.helo(verifier_domain)
            except Exception:
                return 0, "EHLO/HELO failed"

        code, msg = server.mail(verifier_email)
        if code != 250:
            return 0, f"MAIL FROM rejected: {code}"

        code, msg = server.rcpt(email)
        decoded = msg.decode("utf-8", errors="replace") if isinstance(msg, bytes) else str(msg)
        return code, decoded

    except smtplib.SMTPRecipientsRefused as e:
        first_recipient = list(e.recipients.values())[0]
        code = first_recipient[0]
        msg = first_recipient[1].decode("utf-8", errors="replace") if isinstance(first_recipient[1], bytes) else str(first_recipient[1])
        return code, msg
    except (socket.timeout, TimeoutError):
        return 0, "Connection timeout"
    except smtplib.SMTPConnectError:
        return 0, "Connection refused"
    except smtplib.SMTPServerDisconnected:
        return 0, "Server disconnected"
    except OSError as e:
        return 0, f"Network error: {e}"
    except Exception as e:
        return 0, f"Unexpected error: {e}"
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass
