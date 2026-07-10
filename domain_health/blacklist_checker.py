from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import dns.exception
import dns.resolver


@dataclass
class BlacklistResult:
    checked: bool = False
    status: str = "Not Checked"
    listed_on: List[str] | None = None
    lookup_errors: List[str] | None = None
    last_checked: str = ""


def check_blacklists(domain: str, providers: List[str] | None = None, enabled: bool = False, timeout: int = 5) -> BlacklistResult:
    if not enabled:
        return BlacklistResult(checked=False, status="Disabled", listed_on=[], lookup_errors=[])
    providers = [p.strip() for p in (providers or []) if p.strip()]
    if not providers:
        return BlacklistResult(checked=False, status="No Providers", listed_on=[], lookup_errors=[])

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    listed: List[str] = []
    errors: List[str] = []
    for provider in providers:
        query = f"{domain}.{provider}"
        try:
            resolver.resolve(query, "A")
            listed.append(provider)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            continue
        except dns.exception.Timeout:
            errors.append(f"{provider}: timeout")
        except Exception as exc:
            errors.append(f"{provider}: {exc.__class__.__name__}")
    status = "Listed" if listed else "Clear"
    return BlacklistResult(True, status, listed, errors, datetime.now(timezone.utc).isoformat())
