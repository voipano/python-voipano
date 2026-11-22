"""Strict no-network fake transport used by the entire unit suite."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import pytest

from voipano import VoipanoClient


class FakeResponse:
    def __init__(
        self, status: int = 200, *, body: bytes = b'{"ok":true}',
        headers: dict[str, str] | None = None, fail_stream: bool = False,
    ) -> None:
        self.status_code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self._data = body
        self.raw = object()
        self._content_consumed = False
        self.fail_stream = fail_stream
        self.closed = False

    @property
    def content(self) -> bytes:
        self._content_consumed = True
        return self._data

    def json(self) -> Any:
        return json.loads(self.content)

    def iter_content(self, chunk_size: int = 1024) -> Iterable[bytes]:
        for start in range(0, len(self._data), chunk_size):
            if self.fail_stream and start > 0:
                raise OSError("broken stream")
            yield self._data[start:start + chunk_size]

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.responses: list[FakeResponse | Exception] = []
        self.closed = False

    def queue(self, item: FakeResponse | Exception) -> None:
        self.responses.append(item)

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0) if self.responses else FakeResponse()
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def client(session: FakeSession) -> VoipanoClient:
    return VoipanoClient(token="sample-token", session=session)
