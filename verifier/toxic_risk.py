from __future__ import annotations

from typing import List, Tuple

from .models import VerificationResult


def assess_toxic_risk(result: VerificationResult) -> Tuple[str, List[str], str, str, str]:
    """Transparent toxic-risk model using only observed/configured signals."""
    signals: List[str] = []

    if result.disposable:
        signals.append("Disposable domain")
    if result.abuse_address or result.do_not_mail:
        signals.append("Abuse or do-not-mail mailbox")
    if result.smtp_status.lower() == "rejected" or result.mailbox_rejected:
        signals.append("SMTP hard rejection")
    if result.domain_blacklisted:
        signals.append("Domain listed on configured blacklist")
    if result.spam_trap_risk == "High":
        signals.append("High spam-trap risk")
    if result.role_based:
        signals.append("Role account")
    if result.null_mx or result.dns_status == "NXDomain":
        signals.append("Invalid mail route")

    if any(s in signals for s in ("Abuse or do-not-mail mailbox", "SMTP hard rejection")) or len(signals) >= 4:
        return "High", signals, "heuristic", "Medium", "Unknown"
    if len(signals) >= 2:
        return "Medium", signals, "heuristic", "Medium", "Unknown"
    if signals:
        return "Low", signals, "heuristic", "Low", "Unknown"
    return "Unknown", [], "heuristic", "Low", "Unknown"
