"""Public exceptions raised by the Voipano client."""

from __future__ import annotations

from typing import Any


class VoipanoError(Exception):
    """Base class for SDK errors."""


class ApiError(VoipanoError):
    """An HTTP error response from Voipano (including unexpected redirects)."""

    def __init__(
        self,
        message: str,
        status_code: int,
        request_id: str | None = None,
        errors: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.errors = errors if errors is not None else {}


class AuthenticationError(ApiError):
    """HTTP 401."""


class PermissionError(ApiError):
    """HTTP 403; unrelated to built-in PermissionError."""


class NotFoundError(ApiError):
    """HTTP 404."""


class ValidationError(ApiError):
    """HTTP 422."""


class RateLimitError(ApiError):
    """HTTP 429."""


class ServerError(ApiError):
    """HTTP 5xx."""


class TransportError(VoipanoError):
    """Network, TLS or timeout failure (request outcome may be unknown)."""


class UnexpectedResponseError(VoipanoError):
    """The server did not return the expected JSON or binary response."""


class WebhookVerificationError(VoipanoError):
    """Incoming webhook rejected; signature scheme is not yet documented."""
