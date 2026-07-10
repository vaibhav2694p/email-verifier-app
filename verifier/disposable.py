import json
from pathlib import Path
from typing import Set, Optional
import logging
from .cache import TTLCache

logger = logging.getLogger(__name__)

_disposable_cache: Optional[Set[str]] = None
_disposable_file_cache = TTLCache(default_ttl=86400)

BUILTIN_DISPOSABLE = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com",
    "temp-mail.org", "yopmail.com", "tempmail.com",
    "throwawaymail.com", "getnada.com", "maildrop.cc",
    "guerrillamailblock.com", "grr.la", "mailnesia.com",
    "tempail.com", "tempmailo.com", "discard.email",
    "burnermail.io", "ephemeral.email", "throwaway.email",
    "mailslurp.com", "yopmail.fr", "jetable.org",
    "trashmail.com", "trashmail.me", "trashmail.net",
    "mailnull.com", "mailzilla.com", "mailshell.com",
    "mailsiphon.com", "tempalias.com", "tempr.email",
    "mytemp.email", "emailondeck.com", "33mail.com",
    "20minutemail.com", "fakeinbox.com",
    "discardmail.com", "discardmail.fr",
    "disposableaddress.com", "disposableinbox.com",
    "disposemail.com", "disposableemailaddresses.emailmiser.com",
    "temp-mail.io", "tempmail.eu", "tempmailfree.com",
    "throwawayemailaddress.com", "tmpmail.net",
}


def load_disposable_domains() -> Set[str]:
    global _disposable_cache
    if _disposable_cache is not None:
        return _disposable_cache

    cached = _disposable_file_cache.get("__all__")
    if cached is not None:
        _disposable_cache = cached
        return _disposable_cache

    domains = set(BUILTIN_DISPOSABLE)
    file_domains = _load_from_file()
    domains.update(file_domains)

    _disposable_cache = domains
    _disposable_file_cache.set("__all__", domains)
    return _disposable_cache


def is_disposable(domain: str) -> bool:
    normalized = domain.lower().strip()
    domains = load_disposable_domains()
    if normalized in domains:
        return True
    parts = normalized.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in domains:
            return True
    return False


def _load_from_file() -> Set[str]:
    data_dir = Path(__file__).parent.parent / "data"
    file_path = data_dir / "disposable_domains.txt"
    domains: Set[str] = set()

    if not file_path.exists():
        logger.debug("Disposable domains file not found at %s", file_path)
        return domains

    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line.lower())
        logger.info("Loaded %d disposable domains from file", len(domains))
    except Exception as e:
        logger.warning("Failed to load disposable domains from %s: %s", file_path, e)

    return domains


def update_disposable_list(domains: Set[str]):
    global _disposable_cache
    merged = set(BUILTIN_DISPOSABLE)
    merged.update(domains)
    _disposable_cache = merged
    _disposable_file_cache.set("__all__", merged)
