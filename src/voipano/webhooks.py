"""Framework-independent incoming webhook interface (fail closed by default).

The Postman collection does not document signing headers, canonical payload,
secret derivation, timestamp tolerance or replay protection. This module must
not invent a signature scheme; users should supply a verifier once confirmed.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Protocol

from .exceptions import WebhookVerificationError


class WebhookVerifier(Protocol):
    def verify(self, body: bytes, headers: Mapping[str, str]) -> bool:
        """Validate signature AND replay controls against Voipano's real protocol."""
        ...


class RejectAllVerifier:
    def verify(self, body: bytes, headers: Mapping[str, str]) -> bool:
        return False


class WebhookReceiver:
    def __init__(self, verifier: WebhookVerifier | None = None) -> None:
        self.verifier = verifier if verifier is not None else RejectAllVerifier()

    def receive(self, body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        if not isinstance(body, bytes):
            raise TypeError("Webhook body must be raw bytes")
        if not self.verifier.verify(body, headers):
            raise WebhookVerificationError("Webhook verification failed")
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError) as exc:
            raise WebhookVerificationError("Invalid webhook JSON") from exc
        if not isinstance(payload, dict):
            raise WebhookVerificationError("Webhook JSON must be an object")
        return payload
