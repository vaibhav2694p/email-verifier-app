from __future__ import annotations

import dns.resolver


def check_bimi(domain: str, timeout: int = 5) -> str:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(f"default._bimi.{domain}", "TXT")
        for answer in answers:
            txt = b"".join(answer.strings).decode("utf-8", errors="ignore")
            if txt.lower().startswith("v=bimi1"):
                return "Found"
        return "Not Found"
    except Exception:
        return "Not Found"
