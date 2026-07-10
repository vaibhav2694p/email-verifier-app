import json
from pathlib import Path
from typing import Optional, Tuple, Dict
from .models import ProviderType

BUILTIN_ROLE_PREFIXES = {
    "info", "sales", "support", "admin", "contact", "billing",
    "accounts", "finance", "hr", "careers", "jobs", "marketing",
    "office", "help", "webmaster", "noreply", "no-reply",
    "security", "privacy", "legal", "hello", "service",
    "enquiry", "enquiries", "feedback", "abuse", "postmaster",
    "hostmaster", "sysadmin", "root",
    "mailerdaemon", "mailer-daemon", "devnull", "spam", "junk",
    "bounce", "nobody", "daemon", "recruitment", "recruiting",
    "press", "media", "advertising", "promo", "promotions",
    "accountspayable", "accountsreceivable", "invoice",
    "humanresources", "compliance", "operations", "logistics",
    "procurement", "reception", "frontdesk", "switchboard",
    "donotreply", "do-not-reply", "notifications", "notify",
    "alerts", "updates", "newsletter",
}

_ROLE_CATEGORY_MAP: Dict[str, str] = {
    "info": "general",
    "sales": "commercial",
    "support": "general",
    "admin": "administrative",
    "contact": "general",
    "billing": "financial",
    "accounts": "financial",
    "finance": "financial",
    "hr": "personnel",
    "careers": "personnel",
    "jobs": "personnel",
    "marketing": "commercial",
    "office": "administrative",
    "help": "general",
    "webmaster": "technical",
    "noreply": "automated",
    "no-reply": "automated",
    "security": "security",
    "privacy": "security",
    "legal": "legal",
    "hello": "general",
    "service": "general",
    "enquiry": "general",
    "enquiries": "general",
    "feedback": "general",
    "abuse": "security",
    "postmaster": "technical",
    "hostmaster": "technical",
    "sysadmin": "technical",
    "root": "technical",
    "mailerdaemon": "automated",
    "mailer-daemon": "automated",
    "devnull": "technical",
    "spam": "security",
    "junk": "security",
    "bounce": "automated",
    "nobody": "technical",
    "daemon": "technical",
    "recruitment": "personnel",
    "recruiting": "personnel",
    "press": "media",
    "media": "media",
    "advertising": "commercial",
    "promo": "commercial",
    "promotions": "commercial",
    "accountspayable": "financial",
    "accountsreceivable": "financial",
    "invoice": "financial",
    "humanresources": "personnel",
    "compliance": "legal",
    "operations": "administrative",
    "logistics": "operations",
    "procurement": "operations",
    "reception": "general",
    "frontdesk": "general",
    "switchboard": "general",
    "donotreply": "automated",
    "do-not-reply": "automated",
    "notifications": "automated",
    "notify": "automated",
    "alerts": "automated",
    "updates": "automated",
    "newsletter": "commercial",
}

_ROLE_RISK_ADJUSTMENTS: Dict[str, int] = {
    "general": -5,
    "commercial": -3,
    "financial": -2,
    "personnel": -4,
    "administrative": -3,
    "technical": -2,
    "automated": -8,
    "security": -2,
    "legal": -3,
    "media": -3,
    "operations": -3,
}


def _load_role_prefixes_from_file() -> Optional[set]:
    data_dir = Path(__file__).parent.parent / "data"
    file_path = data_dir / "role_prefixes.json"

    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, list):
            return set(item.lower().strip() for item in data if isinstance(item, str))
        if isinstance(data, dict) and "prefixes" in data:
            prefixes = data["prefixes"]
            if isinstance(prefixes, list):
                return set(item.lower().strip() for item in prefixes if isinstance(item, str))
    except Exception:
        pass
    return None


def _get_all_role_prefixes() -> set:
    file_prefixes = _load_role_prefixes_from_file()
    if file_prefixes is not None:
        merged = set(BUILTIN_ROLE_PREFIXES)
        merged.update(file_prefixes)
        return merged
    return set(BUILTIN_ROLE_PREFIXES)


def detect_role_account(email: str) -> Tuple[bool, str, int]:
    if "@" not in email:
        return False, "", 0

    local_part = email.split("@")[0].lower().strip()

    if local_part in _ROLE_CATEGORY_MAP:
        category = _ROLE_CATEGORY_MAP[local_part]
        risk = _ROLE_RISK_ADJUSTMENTS.get(category, 0)
        return True, category, risk

    prefixes = _get_all_role_prefixes()
    if local_part in prefixes:
        category = get_role_category(local_part)
        risk = get_risk_adjustment(category)
        return True, category, risk

    for prefix in prefixes:
        if local_part.startswith(prefix + ".") or local_part.startswith(prefix + "-") or local_part.startswith(prefix + "_"):
            category = get_role_category(prefix)
            risk = get_risk_adjustment(category)
            return True, category, risk

    return False, "", 0


def get_role_category(local_part: str) -> str:
    normalized = local_part.lower().strip()
    return _ROLE_CATEGORY_MAP.get(normalized, "general")


def get_risk_adjustment(category: str) -> int:
    return _ROLE_RISK_ADJUSTMENTS.get(category, 0)
