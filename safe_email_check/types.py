from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmailCheckResult:
    original: str
    normalized_email: str
    local_part: str
    domain: str
    ascii_email: str | None
    ascii_domain: str | None
    display_name: str | None
    deliverability_checked: bool
    is_deliverable: bool | None
