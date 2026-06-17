from __future__ import annotations

from email_verifier.dns_checks import DomainVerification


def calculate_verification_score(
    format_valid: bool,
    dns_result: DomainVerification,
) -> int:
    score = 0
    if format_valid:
        score += 25
    if dns_result.exists:
        score += 20
    if dns_result.mx.found:
        score += 25
    if dns_result.spf.found:
        score += 15
    if dns_result.dmarc.found:
        score += 15
    return min(score, 100)


def build_notes(
    format_valid: bool,
    format_reason: str,
    dns_result: DomainVerification,
    name: str,
    company: str,
) -> str:
    notes: list[str] = []

    if not format_valid:
        notes.append(format_reason)

    if dns_result.domain:
        if dns_result.existence_status != "Exists":
            notes.append(f"Domain status: {dns_result.existence_status}")
        if dns_result.mx.status != "Valid":
            notes.append(f"MX: {dns_result.mx.status}")
        if dns_result.spf.status != "Present":
            notes.append(f"SPF: {dns_result.spf.status}")
        if dns_result.dmarc.status != "Present":
            notes.append(f"DMARC: {dns_result.dmarc.status}")
    else:
        notes.append("No domain available for DNS checks")

    if not name:
        notes.append("Missing name for LinkedIn search")
    if not company:
        notes.append("Missing company for LinkedIn search")

    return "; ".join(deduplicate(notes)) or "OK"


def deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped
