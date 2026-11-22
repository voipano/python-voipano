"""Synchronous HTTP transport for Voipano Public API v1.

Requests are never retried and redirects are never followed: write operations
may start real telephone calls and the API does not document idempotency.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote, urlsplit

import requests

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
)

DEFAULT_BASE_URL = "https://voipano.com/api/v1/webservice"
STATUS_ERRORS: dict[int, type[ApiError]] = {
    401: AuthenticationError,
    403: PermissionError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}


def _clean_header(value: str, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{label} must be a nonempty string")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{label} contains invalid control characters")
    return value


def _valid_timeout(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return float(value)


def _validate_url(base_url: str) -> str:
    if not isinstance(base_url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in base_url):
        raise ValueError("base_url must be a valid absolute HTTP(S) URL")
    try:
        parts = urlsplit(base_url)
        valid = (
            parts.scheme.lower() in ("http", "https")
            and bool(parts.hostname)
            and not parts.username
            and not parts.password
            and not parts.query
            and not parts.fragment
        )
        _ = parts.port  # Reject invalid port numbers
    except ValueError as exc:
        raise ValueError("base_url must be a valid absolute HTTP(S) URL") from exc
    if not valid:
        raise ValueError("base_url must be a valid absolute HTTP(S) URL without query, fragment or credentials")
    return base_url.rstrip("/")


def _path_segment(value: str | int) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Resource ID must be a string or integer")
    part = str(value)
    if not part.strip() or part in (".", "..") or any(ord(c) < 32 or ord(c) == 127 for c in part):
        raise ValueError("Invalid resource ID")
    return quote(part, safe="")


def _query(params: Mapping[str, Any] | None) -> dict[str, Any]:
    return {key: value for key, value in (params or {}).items() if value is not None and value != ""}


def _error(response: requests.Response, body: bytes | None = None) -> ApiError:
    payload: Any = {}
    try:
        payload = json.loads(body if body is not None else response.content)
    except (ValueError, UnicodeError):
        pass
    if not isinstance(payload, dict):
        payload = {}
    message = payload.get("message") or payload.get("error")
    if not isinstance(message, str):
        message = f"Voipano API returned HTTP {response.status_code}."
    errors = payload.get("errors", {})
    error_type = STATUS_ERRORS.get(response.status_code)
    if error_type is None:
        error_type = ServerError if response.status_code >= 500 else ApiError
    return error_type(message, response.status_code, response.headers.get("X-Request-Id"), errors)


def _ensure_binary(response: requests.Response) -> None:
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type in ("application/json", "text/html") or content_type.endswith("+json"):
        raise UnexpectedResponseError(f"Expected audio/binary response, got {content_type}")


class Transport:
    """Low-level client. Scoped copies have isolated configuration and sessions."""

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str | None = None,
        service_id: str | None = None,
        timeout: float = 30,
        connect_timeout: float = 10,
        request_id: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.token = _clean_header(
            token if token is not None else os.getenv("VOIPANO_API_TOKEN", ""),
            "token",
        )
        self.base_url = _validate_url(base_url if base_url is not None else os.getenv("VOIPANO_BASE_URL", DEFAULT_BASE_URL))
        self.service_id = _clean_header(
            service_id if service_id is not None else os.getenv("VOIPANO_SERVICE_ID", ""),
            "service_id", allow_empty=True,
        )
        self.timeout = _valid_timeout(timeout, "timeout")
        self.connect_timeout = _valid_timeout(connect_timeout, "connect_timeout")
        self.request_id = _clean_header(request_id, "request_id") if request_id is not None else None
        self._own_session = session is None
        self._session = session if session is not None else requests.Session()

    def copy(self, **changes: Any) -> Transport:
        data: dict[str, Any] = {
            "token": self.token,
            "base_url": self.base_url,
            "service_id": self.service_id,
            "timeout": self.timeout,
            "connect_timeout": self.connect_timeout,
            "request_id": self.request_id,
        }
        data.update(changes)
        # For injected test/custom sessions, retain the injection; default clients
        # get new sessions to prevent accidental cross-tenant session mutation.
        if not self._own_session:
            data["session"] = self._session
        return Transport(**data)

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    def _send(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        binary: bool = False,
    ) -> requests.Response:
        method = method.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Unsupported HTTP method")
        if not path.startswith("/") or path.startswith("//") or "?" in path or "#" in path:
            raise ValueError("path must begin with one slash and must not contain a query or fragment")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "*/*" if binary else "application/json",
            "X-Request-Id": self.request_id or str(uuid.uuid4()),
            "User-Agent": "voipano-python/1.0.0",
        }
        if self.service_id.strip():
            headers["X-Webservice-Service-Id"] = self.service_id
        kwargs: dict[str, Any] = {
            "headers": headers,
            "timeout": (self.connect_timeout, self.timeout),
            "allow_redirects": False,
            "stream": binary,
        }
        if method == "GET":
            kwargs["params"] = _query(params)
        elif method != "DELETE":
            headers["Content-Type"] = "application/json"
            kwargs["json"] = dict(params or {})
        try:
            return self._session.request(method, self.base_url + path, **kwargs)
        except requests.RequestException as exc:
            raise TransportError("Could not connect to Voipano API. The outcome of a write may be unknown.") from exc

    @staticmethod
    def _raise_status(response: requests.Response, *, streamed: bool = False) -> None:
        if response.status_code >= 300:
            if streamed:
                # Streamed errors: only inspect the first 8192 bytes.
                chunks = []
                size = 0
                for chunk in response.iter_content(chunk_size=2048):
                    chunks.append(chunk[: max(0, 8192 - size)])
                    size += len(chunk)
                    if size >= 8192:
                        break
                raise _error(response, b"".join(chunks))
            raise _error(response)

    def request(self, method: str, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        response = self._send(method, path, params)
        try:
            self._raise_status(response)
            if response.status_code == 204 or not response.content.strip():
                return {}
            try:
                data = response.json()
            except ValueError as exc:
                raise UnexpectedResponseError("Expected JSON response") from exc
            if not isinstance(data, (dict, list)):
                raise UnexpectedResponseError("Expected JSON object or array")
            return data
        finally:
            response.close()

    def binary(self, path: str, query: Mapping[str, Any] | None = None) -> bytes:
        response = self._send("GET", path, query, binary=True)
        try:
            self._raise_status(response, streamed=True)
            _ensure_binary(response)
            return response.content
        except requests.RequestException as exc:
            raise TransportError("Recording response could not be read") from exc
        finally:
            response.close()

    def download_to(self, path: str, destination: str | os.PathLike[str], query: Mapping[str, Any] | None = None) -> Path:
        target = Path(destination)
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Refusing to overwrite existing file: {target}")
        if not target.parent.is_dir():
            raise ValueError("Destination parent directory must exist")
        response = self._send("GET", path, query, binary=True)
        temp_path: Path | None = None
        try:
            self._raise_status(response, streamed=True)
            _ensure_binary(response)
            fd, name = tempfile.mkstemp(prefix=".voipano-", dir=target.parent)
            temp_path = Path(name)
            with os.fdopen(fd, "wb") as tmp:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        tmp.write(chunk)
            target_created = False
            try:
                with target.open("xb") as dst:
                    target_created = True
                    with temp_path.open("rb") as src:
                        while True:
                            chunk = src.read(65536)
                            if not chunk:
                                break
                            dst.write(chunk)
            except Exception:
                if target_created:
                    target.unlink(missing_ok=True)
                raise
            return target
        except requests.RequestException as exc:
            raise TransportError("Recording download failed") from exc
        finally:
            response.close()
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
