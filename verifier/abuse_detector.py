import json
from pathlib import Path
from typing import Dict, Tuple

_BUILT_IN_PREFIXES: Dict[str, str] = {
    "abuse": "Abuse Reporting",
    "postmaster": "System Mailbox",
    "hostmaster": "Technical Contact",
    "webmaster": "Technical Contact",
    "security": "Security Contact",
    "fraud": "Complaint Contact",
    "phishing": "Complaint Contact",
    "spam": "Complaint Contact",
    "complaints": "Complaint Contact",
    "privacy": "Legal Contact",
    "legal": "Legal Contact",
    "dmca": "Legal Contact",
    "noreply": "No-Reply",
    "no-reply": "No-Reply",
    "donotreply": "No-Reply",
    "do-not-reply": "No-Reply",
    "mailer-daemon": "System Mailbox",
}

_CACHE: Dict[str, str] | None = None


def _load_prefixes() -> Dict[str, str]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    prefixes = dict(_BUILT_IN_PREFIXES)
    path = Path(__file__).resolve().parent.parent / "data" / "abuse_prefixes.json"
    try:
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                prefixes.update({str(k).lower(): str(v) for k, v in loaded.items()})
    except Exception:
        pass

    _CACHE = prefixes
    return prefixes


def detect_abuse_address(email: str) -> Tuple[bool, str, bool, str]:
    """Return (is_abuse, category, do_not_mail, reason)."""
    local = (email or "").split("@", 1)[0].strip().lower()
    local = local.replace("_", "-")
    prefix = local.split("+", 1)[0].split(".", 1)[0]
    prefixes = _load_prefixes()

    if local in prefixes:
        category = prefixes[local]
    elif prefix in prefixes:
        category = prefixes[prefix]
    else:
        return False, "", False, ""

    return True, category, True, f"{local} is a {category.lower()} mailbox"
