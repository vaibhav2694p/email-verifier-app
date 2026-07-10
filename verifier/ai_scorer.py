from __future__ import annotations

from .models import VerificationResult


def generate_ai_explanation(result: VerificationResult) -> VerificationResult:
    """Optional explanation layer over deterministic signals. It does not invent facts."""
    positives = result.score_reasons or []
    negatives = result.failed_checks or []
    inconclusive = result.inconclusive_checks or []
    score = result.verification_score

    result.ai_quality_score = score
    limitations = []
    if not result.smtp_attempted:
        limitations.append("SMTP verification was not attempted")
    if result.smtp_blocked or result.smtp_port_blocked:
        limitations.append("SMTP was blocked by the environment or provider")
    if result.catch_all == "Catch-All":
        limitations.append("Catch-all domains cannot prove individual mailbox ownership")
    if result.spam_trap_risk != "Unknown" and not result.confirmed_trap:
        limitations.append("Spam-trap output is risk-based, not a confirmed trap")

    result.notes = " | ".join(filter(None, [
        f"Recommended action: {result.recommended_action}",
        f"Positive signals: {len(positives)}",
        f"Negative signals: {len(negatives)}",
        f"Inconclusive signals: {len(inconclusive)}",
        "Data limitations: " + "; ".join(limitations) if limitations else "Data limitations: none from checked signals",
    ]))
    return result
