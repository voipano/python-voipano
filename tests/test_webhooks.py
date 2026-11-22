from __future__ import annotations

import pytest

from voipano import WebhookReceiver, WebhookVerificationError


class TestVerifier:
    def verify(self, body: bytes, headers: dict[str, str]) -> bool:
        return headers.get("X-Test") == "valid"


def test_webhook_denied_by_default():
    with pytest.raises(WebhookVerificationError):
        WebhookReceiver().receive(b'{"event":"ringing"}', {})


def test_custom_verifier_json_object_only():
    recv = WebhookReceiver(TestVerifier())
    assert recv.receive(b'{"event":"ringing"}', {"X-Test": "valid"}) == {"event": "ringing"}
    with pytest.raises(WebhookVerificationError):
        recv.receive(b'[]', {"X-Test": "valid"})
    with pytest.raises(WebhookVerificationError):
        recv.receive(b'bad', {"X-Test": "valid"})
    with pytest.raises(WebhookVerificationError):
        recv.receive(b'{"ok":true}', {"X-Test": "invalid"})
