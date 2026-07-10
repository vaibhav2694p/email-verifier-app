import re
from typing import Tuple

from .exceptions import SyntaxError as EmailSyntaxError


def normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise EmailSyntaxError(detail="Email must be a string")

    email = email.strip()
    if not email:
        raise EmailSyntaxError(detail="Email is empty")

    email = email.lower()

    at_count = email.count("@")
    if at_count == 0:
        raise EmailSyntaxError(detail="Email must contain an '@' symbol")
    if at_count != 1:
        raise EmailSyntaxError(detail=f"Email contains {at_count} '@' symbols, expected 1")

    parts = email.split("@")
    if len(parts) != 2:
        raise EmailSyntaxError(detail="Email must have exactly one local part and one domain separated by '@'")

    local_part, domain = parts

    if not local_part:
        raise EmailSyntaxError(detail="Local part cannot be empty")
    if not domain:
        raise EmailSyntaxError(detail="Domain cannot be empty")

    try:
        local_part.encode("ascii")
    except UnicodeEncodeError:
        pass

    try:
        domain.encode("ascii")
    except UnicodeEncodeError:
        import idna
        try:
            domain = domain.encode("idna").decode("ascii")
        except (UnicodeError, idna.core.IDNAError) as e:
            raise EmailSyntaxError(detail=f"Failed to encode IDN domain: {e}")

    email = f"{local_part}@{domain}"

    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        raise EmailSyntaxError(detail="Email does not match expected pattern")

    return email


def normalize_domain(domain: str) -> str:
    if not isinstance(domain, str):
        raise EmailSyntaxError(message="Domain must be a string", detail="Expected str, got non-string")

    domain = domain.strip().lower()
    if not domain:
        raise EmailSyntaxError(message="Domain is empty", detail="Domain cannot be empty")

    if domain.startswith("http://"):
        domain = domain[7:]
    elif domain.startswith("https://"):
        domain = domain[8:]

    if domain.startswith("www."):
        domain = domain[4:]

    if "@" in domain:
        domain = domain.split("@")[-1]

    if "/" in domain:
        domain = domain.split("/")[0]

    if domain.startswith("@"):
        domain = domain[1:]

    if domain.endswith("."):
        domain = domain.rstrip(".")

    try:
        domain.encode("ascii")
    except UnicodeEncodeError:
        import idna
        try:
            domain = domain.encode("idna").decode("ascii")
        except (UnicodeError, idna.core.IDNAError) as e:
            raise EmailSyntaxError(message="Failed to encode IDN domain", detail=str(e))

    return domain


def split_email(email: str) -> Tuple[str, str]:
    email = email.strip().lower()

    at_count = email.count("@")
    if at_count == 0:
        raise EmailSyntaxError(message="Invalid email", detail="Email must contain an '@' symbol")
    if at_count != 1:
        raise EmailSyntaxError(message="Invalid email", detail=f"Email contains {at_count} '@' symbols, expected 1")

    local_part, domain = email.split("@", 1)

    if not local_part:
        raise EmailSyntaxError(message="Invalid email", detail="Local part cannot be empty")
    if not domain:
        raise EmailSyntaxError(message="Invalid email", detail="Domain cannot be empty")

    return local_part, domain
