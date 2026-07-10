from __future__ import annotations

from dataclasses import dataclass
from typing import List

import dns.exception
import dns.resolver


@dataclass
class SpfResult:
    record: str = ""
    status: str = "Not Found"
    issues: List[str] | None = None


def check_spf(domain: str, timeout: int = 5) -> SpfResult:
    issues: List[str] = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(domain, "TXT")
        records = []
        for answer in answers:
            txt = b"".join(answer.strings).decode("utf-8", errors="ignore")
            if txt.lower().startswith("v=spf1"):
                records.append(txt)
        if not records:
            return SpfResult(status="Not Found", issues=["No SPF TXT record found"])
        if len(records) > 1:
            issues.append("Multiple SPF records found")
        record = records[0]
        if "+all" in record.lower():
            issues.append("SPF uses permissive +all")
        if "~all" not in record.lower() and "-all" not in record.lower() and "?all" not in record.lower():
            issues.append("SPF has no explicit all mechanism")
        return SpfResult(record=record, status="Pass" if not issues else "Warning", issues=issues)
    except dns.resolver.NXDOMAIN:
        return SpfResult(status="NXDomain", issues=["Domain does not exist"])
    except dns.exception.Timeout:
        return SpfResult(status="Timeout", issues=["DNS timeout"])
    except Exception as exc:
        return SpfResult(status="Error", issues=[str(exc)])
