from __future__ import annotations

import re
from typing import Dict, List

from verifier.config import VerifierConfig
from verifier.pipeline import VerificationPipeline


def generate_email_patterns(first_name: str, last_name: str, domain: str) -> List[Dict[str, str]]:
    first = _clean_name(first_name)
    last = _clean_name(last_name)
    domain = domain.strip().lower().replace("@", "")
    if not first or not domain:
        return []
    f = first[0]
    last_initial = last[0] if last else ""
    patterns = [
        ("first", f"{first}@{domain}"),
        ("last", f"{last}@{domain}" if last else ""),
        ("first.last", f"{first}.{last}@{domain}" if last else ""),
        ("firstlast", f"{first}{last}@{domain}" if last else ""),
        ("f.last", f"{f}.{last}@{domain}" if last else ""),
        ("firstl", f"{first}{last_initial}@{domain}" if last_initial else ""),
        ("flast", f"{f}{last}@{domain}" if last else ""),
    ]
    seen = set()
    result = []
    for pattern, email in patterns:
        if email and email not in seen:
            seen.add(email)
            result.append({"pattern": pattern, "email": email})
    return result


def verify_generated_patterns(first_name: str, last_name: str, domain: str, config: VerifierConfig | None = None) -> List[Dict[str, str]]:
    pipeline = VerificationPipeline(config or VerifierConfig())
    rows = []
    for candidate in generate_email_patterns(first_name, last_name, domain):
        result = pipeline.verify(candidate["email"], company_domain=domain)
        rows.append({
            "generated_email": candidate["email"],
            "pattern": candidate["pattern"],
            "verification_status": result.verification_status,
            "confidence": result.confidence_level,
            "recommended_action": result.recommended_action,
        })
    return rows


def _clean_name(value: str) -> str:
    return re.sub(r"[^a-z]", "", (value or "").strip().lower())
