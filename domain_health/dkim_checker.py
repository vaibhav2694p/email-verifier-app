from __future__ import annotations

from dataclasses import dataclass
from typing import List

import dns.resolver


@dataclass
class DkimResult:
    status: str = "Not Checked"
    selector: str = ""
    record: str = ""
    issues: List[str] | None = None


def check_dkim(domain: str, selectors: List[str] | None = None, timeout: int = 5) -> DkimResult:
    selectors = selectors or []
    if not selectors:
        return DkimResult(status="Not Checked", issues=["No DKIM selectors configured"])

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    errors: List[str] = []
    for selector in selectors:
        name = f"{selector}._domainkey.{domain}"
        try:
            answers = resolver.resolve(name, "TXT")
            for answer in answers:
                txt = b"".join(answer.strings).decode("utf-8", errors="ignore")
                if "v=dkim1" in txt.lower() or "p=" in txt.lower():
                    return DkimResult(status="Found", selector=selector, record=txt, issues=[])
        except Exception as exc:
            errors.append(f"{selector}: {exc.__class__.__name__}")
    return DkimResult(status="Not Found", issues=errors[:5])
