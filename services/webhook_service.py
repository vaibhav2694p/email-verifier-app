from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Dict
from urllib.parse import urlparse

import requests


@dataclass
class WebhookDelivery:
    success: bool
    status_code: int = 0
    error: str = ""
    attempts: int = 0
    response_time_ms: float = 0.0


def sign_payload(payload: Dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(payload: Dict[str, Any], secret: str, signature: str) -> bool:
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature or "")


def deliver_webhook(url: str, payload: Dict[str, Any], secret: str, timeout: int = 10, max_attempts: int = 3, production: bool = False) -> WebhookDelivery:
    parsed = urlparse(url)
    if production and parsed.scheme != "https":
        return WebhookDelivery(False, error="Production webhooks must use HTTPS")
    headers = {
        "Content-Type": "application/json",
        "X-Email-Verifier-Signature": sign_payload(payload, secret),
    }
    last_error = ""
    start = time.monotonic()
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if 200 <= response.status_code < 300:
                return WebhookDelivery(True, response.status_code, attempts=attempt, response_time_ms=round((time.monotonic() - start) * 1000, 2))
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(min(attempt, 3))
    return WebhookDelivery(False, status_code=0, error=last_error, attempts=max_attempts, response_time_ms=round((time.monotonic() - start) * 1000, 2))
