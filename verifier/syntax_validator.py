import importlib.util
import re
import unicodedata
from typing import Optional, Tuple

from .models import SyntaxResult

LOCAL_MAX = 64
DOMAIN_MAX = 254
LABEL_MAX = 63
TOTAL_MAX = 254
TLD_MIN = 2
TLD_MAX = 63

LOCAL_CHARS = re.compile(
    r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+$'
)

DOMAIN_CHARS = re.compile(
    r'^[a-zA-Z0-9.-]+$'
)

try:
    IDNA_AVAILABLE = importlib.util.find_spec("idna") is not None
except (ImportError, ValueError):
    IDNA_AVAILABLE = False


def _punycode_domain(domain: str) -> Tuple[Optional[str], Optional[str]]:
    """Attempt to convert an IDN domain to punycode ASCII.

    Returns (ascii_domain, None) on success or (None, error_message) on failure.
    """
    try:
        domain.encode("ascii")
        return domain, None
    except UnicodeEncodeError:
        pass

    if not IDNA_AVAILABLE:
        return None, "IDN domain detected but 'idna' package is not installed"

    try:
        ascii_domain = domain.encode("idna").decode("ascii")
        return ascii_domain, None
    except Exception as exc:
        return None, f"Failed to encode IDN domain: {exc}"


def _is_valid_unicode_local(local: str) -> bool:
    """Check that every character in the local part is permissible per a
    simplified-but-thorough reading of RFC 5322.

    Allowed: ASCII printable (excluding specials that require quoting),
    plus any Unicode category L* (letter), N* (number), or M* (mark).
    Underscore, dot, hyphen, plus, percent, and ampersand are explicitly
    allowed (common mailbox conventions).  Space and control characters are
    rejected.  Every other special is rejected unless quoted.
    """
    for ch in local:
        cp = ord(ch)
        if cp < 0x20 or cp == 0x7F:
            return False
        if ch in (' ', '\t', '\n', '\r'):
            return False
        cat = unicodedata.category(ch)
        if cat.startswith(('L', 'N', 'M')):
            continue
        if ch in ('.', '_', '-', '+', '%', '!', '#', '$', '&', "'", '*', '/', '=', '?', '^', '`', '{', '|', '}', '~'):
            continue
        return False
    return True


def validate_domain_syntax(domain: str) -> Tuple[bool, str]:
    """Validate the domain part of an email address independently.

    Returns (is_valid, error_message).
    """
    if not domain:
        return False, "Domain is empty"

    if len(domain) > DOMAIN_MAX:
        return False, f"Domain exceeds maximum length of {DOMAIN_MAX} characters ({len(domain)} given)"

    if ".." in domain:
        return False, "Domain contains consecutive dots"

    if domain.startswith('.') or domain.startswith('-'):
        return False, "Domain must not start with a dot or hyphen"

    if domain.endswith('.') or domain.endswith('-'):
        return False, "Domain must not end with a dot or hyphen"

    if not DOMAIN_CHARS.match(domain):
        return False, "Domain contains invalid characters"

    dot_index = domain.rfind('.')
    if dot_index == -1:
        return False, "Domain must contain at least one dot (TLD required)"

    tld = domain[dot_index + 1:]
    if len(tld) < TLD_MIN:
        return False, f"TLD is too short ({len(tld)} chars, minimum {TLD_MIN})"
    if len(tld) > TLD_MAX:
        return False, f"TLD is too long ({len(tld)} chars, maximum {TLD_MAX})"

    labels = domain.split('.')
    for i, label in enumerate(labels):
        if not label:
            return False, "Domain contains an empty label (consecutive dots)"
        if len(label) > LABEL_MAX:
            return False, f"Domain label '{label}' exceeds {LABEL_MAX} characters ({len(label)} given)"
        if label.startswith('-'):
            return False, f"Domain label '{label}' must not start with a hyphen"
        if label.endswith('-'):
            return False, f"Domain label '{label}' must not end with a hyphen"
        if i == len(labels) - 1 and label.isdigit():
            return False, "TLD must not be purely numeric"

    return True, ""


def validate_syntax(email: str) -> SyntaxResult:
    """Validate email syntax with comprehensive checks.

    Performs the following checks in order:
      1.  Leading/trailing whitespace removal
      2.  Lowercase domain normalization
      3.  Duplicate @ detection
      4.  Empty local part
      5.  Empty domain
      6.  Consecutive dots
      7.  Leading or trailing dots in local part
      8.  Leading or trailing dots or hyphens in domain
      9.  Invalid characters (RFC 5322 simplified)
      10. Domain-label length limits (max 63 per label)
      11. Total-address length limits (max 254)
      12. Local part length limits (max 64)
      13. Domain has at least one dot (TLD exists)
      14. TLD length (2-63 chars)
      15. TLD must not be purely numeric

    Returns a SyntaxResult with is_valid, error, local_part, domain,
    normalized_email, idn_domain, and punycode_domain fields populated.
    """
    result = SyntaxResult(is_valid=False)

    # ------------------------------------------------------------------
    # 0. Guard: must be a string
    # ------------------------------------------------------------------
    if not isinstance(email, str):
        result.error = "Email must be a string"
        return result

    # ------------------------------------------------------------------
    # 1. Leading / trailing whitespace removal
    # ------------------------------------------------------------------
    original_email = email
    email = email.strip()

    if not email:
        result.error = "Email is empty"
        return result

    if email != original_email:
        email = email.strip()

    # ------------------------------------------------------------------
    # 3. Duplicate @ detection
    # ------------------------------------------------------------------
    at_count = email.count("@")
    if at_count == 0:
        result.error = "Email must contain an '@' symbol"
        return result
    if at_count != 1:
        result.error = f"Email contains {at_count} '@' symbols; exactly 1 is required"
        return result

    local_part, domain = email.split("@", 1)

    # ------------------------------------------------------------------
    # 4. Empty local part
    # ------------------------------------------------------------------
    if not local_part:
        result.error = "Local part is empty"
        return result

    # ------------------------------------------------------------------
    # 5. Empty domain
    # ------------------------------------------------------------------
    if not domain:
        result.error = "Domain is empty"
        return result

    # ------------------------------------------------------------------
    # 2. Lowercase domain normalization
    # ------------------------------------------------------------------
    domain = domain.lower()

    # ------------------------------------------------------------------
    # 6. Consecutive dots (local and domain)
    # ------------------------------------------------------------------
    if ".." in local_part:
        result.error = "Local part must not contain consecutive dots"
        return result
    if ".." in domain:
        result.error = "Domain must not contain consecutive dots"
        return result

    # ------------------------------------------------------------------
    # 7. Leading or trailing dots in local part
    # ------------------------------------------------------------------
    if local_part.startswith("."):
        result.error = "Local part must not start with a dot"
        return result
    if local_part.endswith("."):
        result.error = "Local part must not end with a dot"
        return result

    # ------------------------------------------------------------------
    # 8. Leading or trailing dots or hyphens in domain
    # ------------------------------------------------------------------
    if domain.startswith('.') or domain.startswith('-'):
        result.error = "Domain must not start with a dot or hyphen"
        return result
    if domain.endswith('.') or domain.endswith('-'):
        result.error = "Domain must not end with a dot or hyphen"
        return result

    # ------------------------------------------------------------------
    # 9. IDN domains using punycode
    # ------------------------------------------------------------------
    idn_domain = False
    punycode_domain = ""
    try:
        domain.encode("ascii")
    except UnicodeEncodeError:
        idn_domain = True
        ascii_domain, punycode_err = _punycode_domain(domain)
        if punycode_err:
            result.error = punycode_err
            return result
        punycode_domain = ascii_domain
        domain = ascii_domain

    # ------------------------------------------------------------------
    # 10. Invalid characters
    # ------------------------------------------------------------------
    if not _is_valid_unicode_local(local_part):
        result.error = "Local part contains invalid characters"
        return result
    if not DOMAIN_CHARS.match(domain):
        result.error = "Domain contains invalid characters"
        return result

    # ------------------------------------------------------------------
    # 12. Local part length limits (max 64)
    # ------------------------------------------------------------------
    if len(local_part) > LOCAL_MAX:
        result.error = f"Local part exceeds maximum length of {LOCAL_MAX} characters ({len(local_part)} given)"
        return result

    # ------------------------------------------------------------------
    # 11. Total address length limits (max 254)
    # ------------------------------------------------------------------
    total_len = len(local_part) + 1 + len(domain)
    if total_len > TOTAL_MAX:
        result.error = f"Total email length exceeds {TOTAL_MAX} characters ({total_len} given)"
        return result

    # ------------------------------------------------------------------
    # 13. Domain has at least one dot (TLD exists)
    # ------------------------------------------------------------------
    if "." not in domain:
        result.error = "Domain must contain at least one dot (TLD required)"
        return result

    # ------------------------------------------------------------------
    # 14. TLD length (2-63 chars)
    # ------------------------------------------------------------------
    dot_index = domain.rfind(".")
    tld = domain[dot_index + 1:]
    if len(tld) < TLD_MIN:
        result.error = f"TLD is too short ({len(tld)} chars, minimum {TLD_MIN})"
        return result
    if len(tld) > TLD_MAX:
        result.error = f"TLD is too long ({len(tld)} chars, maximum {TLD_MAX})"
        return result

    if tld.isdigit():
        result.error = "TLD must not be purely numeric"
        return result

    # ------------------------------------------------------------------
    # 10. Domain-label length limits (max 63 per label)
    # ------------------------------------------------------------------
    labels = domain.split(".")
    for label in labels:
        if not label:
            result.error = "Domain contains an empty label"
            return result
        if len(label) > LABEL_MAX:
            result.error = f"Domain label '{label}' exceeds {LABEL_MAX} characters ({len(label)} given)"
            return result
        if label.startswith("-"):
            result.error = f"Domain label '{label}' must not start with a hyphen"
            return result
        if label.endswith("-"):
            result.error = f"Domain label '{label}' must not end with a hyphen"
            return result

    # ------------------------------------------------------------------
    # Build normalized email
    # ------------------------------------------------------------------
    normalized = f"{local_part}@{domain}"
    result.is_valid = True
    result.error = ""
    result.local_part = local_part
    result.domain = domain
    result.normalized_email = normalized
    result.idn_domain = idn_domain
    result.punycode_domain = punycode_domain
    return result
