"""Official Voipano Public API v1 Python SDK."""

from .client import VoipanoClient
from .exceptions import (
    ApiError,
    AuthenticationError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
    TransportError,
    UnexpectedResponseError,
    ValidationError,
    VoipanoError,
    WebhookVerificationError,
)
from .webhooks import RejectAllVerifier, WebhookReceiver, WebhookVerifier

__version__ = "1.0.1"
Voipano = VoipanoClient

__all__ = [
    "Voipano", "VoipanoClient", "VoipanoError", "ApiError",
    "AuthenticationError", "PermissionError", "NotFoundError",
    "ValidationError", "RateLimitError", "ServerError", "TransportError",
    "UnexpectedResponseError", "WebhookVerificationError", "WebhookVerifier",
    "RejectAllVerifier", "WebhookReceiver",
]
