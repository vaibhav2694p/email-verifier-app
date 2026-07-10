from __future__ import annotations

from typing import Iterable, Set

from verifier.normalizer import normalize_email


class SuppressionService:
    def __init__(self, emails: Iterable[str] | None = None) -> None:
        self._emails: Set[str] = set()
        for email in emails or []:
            self.add(email)

    def add(self, email: str) -> None:
        try:
            self._emails.add(normalize_email(email))
        except Exception:
            self._emails.add((email or "").strip().lower())

    def contains(self, email: str) -> bool:
        try:
            normalized = normalize_email(email)
        except Exception:
            normalized = (email or "").strip().lower()
        return normalized in self._emails
