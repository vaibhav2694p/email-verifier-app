from __future__ import annotations

from typing import List, Tuple

from .models import VerificationResult

SUSPICIOUS_LOCAL_PATTERNS = (
    "test", "tester", "seed", "trap", "spamtrap", "honeypot", "blackhole",
    "nobody", "unknown", "invalid", "fake", "sample", "example",
)


def assess_spam_trap_risk(result: VerificationResult) -> Tuple[str, List[str], str, str, bool]:
    """Risk-based spam-trap assessment. Never confirms a trap without trusted data."""
    signals: List[str] = []
    local = (result.local_part or "").lower()

    if any(token in local for token in SUSPICIOUS_LOCAL_PATTERNS):
        signals.append("Suspicious local-part pattern")
    if result.role_based:
        signals.append("Role account")
    if result.abuse_address:
        signals.append("Abuse/system mailbox")
    if result.disposable:
        signals.append("Disposable domain")
    if result.dns_status in ("NXDomain", "NoAnswer") or result.mx_status in ("NXDomain", "NoAnswer"):
        signals.append("Invalid or inactive domain")
    if result.catch_all == "Catch-All":
        signals.append("Catch-all domain")
    if result.domain_blacklisted:
        signals.append("Domain listed on configured blacklist")

    if len(signals) >= 4:
        return "High", signals, "heuristic", "Medium", False
    if len(signals) >= 2:
        return "Medium", signals, "heuristic", "Medium", False
    if signals:
        return "Low", signals, "heuristic", "Low", False
    return "Unknown", [], "heuristic", "Low", False
