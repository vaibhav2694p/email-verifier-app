from __future__ import annotations

import asyncio
import smtplib
import socket
import uuid

import dns.resolver


class SmtpVerificationResult:
    def __init__(
        self,
        mailbox_exists: bool | None = None,
        catch_all: bool | None = None,
        error: str = "",
        mx_servers: list[str] | None = None,
    ) -> None:
        self.mailbox_exists = mailbox_exists
        self.catch_all = catch_all
        self.error = error
        self.mx_servers = mx_servers or []


def resolve_mx_servers(domain: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx_records = sorted(
            ((int(answer.preference), str(answer.exchange).rstrip("."))
             for answer in answers),
            key=lambda x: x[0],
        )
        return [server for _, server in mx_records]
    except Exception:
        return []


def verify_mailbox_smtp(
    email: str,
    domain: str,
    sender: str = "verifier@example.com",
    timeout: float = 10.0,
) -> SmtpVerificationResult:
    mx_servers = resolve_mx_servers(domain)
    if not mx_servers:
        return SmtpVerificationResult(
            mailbox_exists=None,
            error="No MX records found for domain",
        )

    for mx in mx_servers[:3]:
        try:
            result = _try_mx_server(email, mx, sender, timeout)
            if result.mailbox_exists is not None:
                result.mx_servers = mx_servers
                if result.mailbox_exists:
                    result.catch_all = _check_catch_all(
                        domain, mx, timeout=timeout
                    )
                return result
        except Exception as exc:
            continue

    return SmtpVerificationResult(
        mailbox_exists=None,
        error="Could not connect to any mail server",
        mx_servers=mx_servers,
    )


def _try_mx_server(
    email: str, mx: str, sender: str, timeout: float
) -> SmtpVerificationResult:
    try:
        server = smtplib.SMTP(timeout=timeout)
        server.set_debuglevel(0)
        server.connect(mx, 25)
        server.ehlo_or_helo_if_needed()

        if server.has_extn("STARTTLS"):
            try:
                server.starttls()
                server.ehlo()
            except Exception:
                pass

        code, _ = server.mail(sender)
        if code not in (250, 251):
            server.quit()
            return SmtpVerificationResult(
                mailbox_exists=None, error=f"Sender rejected: {code}"
            )

        code, msg = server.rcpt(email)
        server.quit()

        if code in (250, 251):
            return SmtpVerificationResult(mailbox_exists=True)
        elif code == 550:
            return SmtpVerificationResult(mailbox_exists=False, error="Mailbox not found")
        elif code in (450, 451, 452):
            return SmtpVerificationResult(
                mailbox_exists=None,
                error=f"Temporary failure (code {code})",
            )
        else:
            return SmtpVerificationResult(
                mailbox_exists=None,
                error=f"Unexpected response: {code} {msg}",
            )

    except (socket.timeout, smtplib.SMTPServerDisconnected, ConnectionRefusedError,
            OSError) as exc:
        return SmtpVerificationResult(
            mailbox_exists=None, error=str(exc)
        )
    except smtplib.SMTPConnectError as exc:
        return SmtpVerificationResult(
            mailbox_exists=None, error=f"Connection failed: {exc}"
        )
    except smtplib.SMTPException as exc:
        return SmtpVerificationResult(
            mailbox_exists=None, error=f"SMTP error: {exc}"
        )


def _check_catch_all(
    domain: str,
    mx: str,
    sender: str = "verifier@example.com",
    timeout: float = 10.0,
) -> bool | None:
    random_local = str(uuid.uuid4()).replace("-", "")[:12]
    test_email = f"{random_local}@{domain}"
    try:
        server = smtplib.SMTP(timeout=timeout)
        server.set_debuglevel(0)
        server.connect(mx, 25)
        server.ehlo_or_helo_if_needed()

        if server.has_extn("STARTTLS"):
            try:
                server.starttls()
                server.ehlo()
            except Exception:
                pass

        code, _ = server.mail(sender)
        if code not in (250, 251):
            server.quit()
            return None

        code, _ = server.rcpt(test_email)
        server.quit()
        return code in (250, 251)

    except Exception:
        return None
