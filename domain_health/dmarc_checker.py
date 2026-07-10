from __future__ import annotations

from dataclasses import dataclass
from typing import List

import dns.exception
import dns.resolver


@dataclass
class DmarcResult:
    record: str = ""
    policy: str = ""
    status: str = "Not Found"
    reporting_addresses: List[str] | None = None
    issues: List[str] | None = None


def check_dmarc(domain: str, timeout: int = 5) -> DmarcResult:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(f"_dmarc.{domain}", "TXT")
        records = []
        for answer in answers:
            txt = b"".join(answer.strings).decode("utf-8", errors="ignore")
            if txt.lower().startswith("v=dmarc1"):
                records.append(txt)
        if not records:
            return DmarcResult(status="Not Found", issues=["No DMARC record found"])

        record = records[0]
        parts = {p.split("=", 1)[0].strip().lower(): p.split("=", 1)[1].strip() for p in record.split(";") if "=" in p}
        policy = parts.get("p", "none").lower()
        reporting = []
        for key in ("rua", "ruf"):
            if parts.get(key):
                reporting.extend([v.strip() for v in parts[key].split(",") if v.strip()])

        issues: List[str] = []
        if len(records) > 1:
            issues.append("Multiple DMARC records found")
        if policy == "none":
            issues.append("DMARC policy is monitoring-only")
        return DmarcResult(record=record, policy=policy, status="Pass" if not issues else "Warning", reporting_addresses=reporting, issues=issues)
    except dns.resolver.NXDOMAIN:
        return DmarcResult(status="NXDomain", issues=["Domain does not exist"])
    except dns.resolver.NoAnswer:
        return DmarcResult(status="Not Found", issues=["No DMARC answer"])
    except dns.exception.Timeout:
        return DmarcResult(status="Timeout", issues=["DNS timeout"])
    except Exception as exc:
        return DmarcResult(status="Error", issues=[str(exc)])
