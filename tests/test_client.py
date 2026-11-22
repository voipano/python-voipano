from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import requests

from voipano import (
    ApiError, AuthenticationError, NotFoundError, PermissionError,
    RateLimitError, ServerError, TransportError, UnexpectedResponseError,
    ValidationError, VoipanoClient,
)
from conftest import FakeResponse


BASE = "https://voipano.com/api/v1/webservice"


def test_headers_timeout_and_query(client, session):
    response = client.contacts.all({"search": "Ali", "page": 0, "enabled": False, "empty": "", "no": None})
    assert response == {"ok": True}
    method, url, kw = session.calls[-1]
    assert method == "GET" and url == BASE + "/contacts"
    assert kw["params"] == {"search": "Ali", "page": 0, "enabled": False}
    assert kw["headers"]["Authorization"] == "Bearer sample-token"
    assert kw["headers"]["Accept"] == "application/json"
    assert re.fullmatch(r"[0-9a-f-]{36}", kw["headers"]["X-Request-Id"])
    assert kw["timeout"] == (10.0, 30.0)
    assert kw["allow_redirects"] is False and kw["stream"] is False


def test_immutable_scoping_and_tracing(client, session):
    scoped = client.with_token("customer-secret").for_service("S1").with_request_id("request-x")
    scoped.services.all()
    kw = session.calls[-1][2]
    assert kw["headers"]["Authorization"] == "Bearer customer-secret"
    assert kw["headers"]["X-Webservice-Service-Id"] == "S1"
    assert kw["headers"]["X-Request-Id"] == "request-x"
    client.services.all()
    assert session.calls[-1][2]["headers"]["Authorization"] == "Bearer sample-token"
    assert "X-Webservice-Service-Id" not in session.calls[-1][2]["headers"]
    assert session.calls[-1][2]["headers"]["X-Request-Id"] != "request-x"


def test_from_environment(monkeypatch):
    monkeypatch.setenv("VOIPANO_API_TOKEN", "env-secret")
    monkeypatch.setenv("VOIPANO_SERVICE_ID", "s123")
    monkeypatch.setenv("VOIPANO_BASE_URL", "https://example.test/v1/")
    with VoipanoClient() as client:
        assert client._transport.token == "env-secret"
        assert client._transport.service_id == "s123"
        assert client._transport.base_url == "https://example.test/v1"


@pytest.mark.parametrize("bad", ["", "  ", "https://user:pass@example.com", "file:///etc/passwd", "http://example.com/?q=1", "https://example.com/#test", "https://example.com/\r\nX:bad", "https://example.com:99999"])
def test_reject_bad_base_url(bad):
    with pytest.raises(ValueError):
        VoipanoClient(token="ok", base_url=bad)


@pytest.mark.parametrize("kwargs", [
    {"token": ""}, {"token": "foo\r\nInjected: true"},
    {"token": "ok", "service_id": "bad\nValue"},
    {"token": "ok", "timeout": 0}, {"token": "ok", "connect_timeout": float("inf")},
])
def test_invalid_options(kwargs):
    with pytest.raises(ValueError):
        VoipanoClient(**kwargs)


@pytest.mark.parametrize("bad", ["", " ", "..", ".", "bad\nvalue", True, None])
def test_invalid_resource_id(client, bad):
    with pytest.raises(ValueError):
        client.contacts.find(bad)


def test_path_segment_encoded(client, session):
    client.contacts.find("hello/سلام")
    assert session.calls[-1][1] == BASE + "/contacts/hello%2F%D8%B3%D9%84%D8%A7%D9%85"


@pytest.mark.parametrize("method,path", [("TRACE", "/services"), ("GET", "//evil.com"), ("GET", "services"), ("GET", "/services?q=1"), ("GET", "/services#frag")])
def test_reject_unsafe_request(client, method, path):
    with pytest.raises(ValueError):
        client.request(method, path)


@pytest.mark.parametrize("status,exc", [
    (300, ApiError), (301, ApiError), (400, ApiError), (401, AuthenticationError),
    (403, PermissionError), (404, NotFoundError), (422, ValidationError),
    (429, RateLimitError), (500, ServerError), (503, ServerError),
])
def test_http_exceptions(client, session, status, exc):
    session.queue(FakeResponse(status, body=b'{"message":"invalid","errors":{"phone":["required"]}}', headers={"X-Request-Id": "server-request"}))
    with pytest.raises(exc) as caught:
        client.services.all()
    assert caught.value.status_code == status
    assert caught.value.request_id == "server-request"
    assert caught.value.errors == {"phone": ["required"]}
    assert str(caught.value) == "invalid"


def test_html_error(client, session):
    session.queue(FakeResponse(502, body=b"<html>bad gateway</html>"))
    with pytest.raises(ServerError, match="HTTP 502"):
        client.services.all()


@pytest.mark.parametrize("data", [b"garbage", b'"primitive"', b"123", b"false"])
def test_unexpected_success(client, session, data):
    session.queue(FakeResponse(body=data))
    with pytest.raises(UnexpectedResponseError):
        client.services.all()


def test_empty_and_array_success(client, session):
    session.queue(FakeResponse(204, body=b""))
    assert client.services.all() == {}
    session.queue(FakeResponse(body=b"[]"))
    assert client.services.all() == []


def test_transport_timeout_has_no_retry(client, session):
    session.queue(requests.Timeout("socket timeout"))
    with pytest.raises(TransportError, match="outcome"):
        client.calls.otp("09120000000")
    assert len(session.calls) == 1


def test_posts_not_retried(client, session):
    client.calls.click_to_call("09120000000", "09121111111", timeout=30)
    method, _, kwargs = session.calls[-1]
    assert method == "POST"
    assert kwargs["json"] == {"call_source": "09120000000", "call_destination": "09121111111", "timeout": 30}
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert len(session.calls) == 1


def test_instance_close_of_injected_session_does_not_close_it(client, session):
    client.close()
    assert not session.closed


def test_real_requests_prepared_request_adapter_no_network():
    """Verify actual requests serialization using a local adapter; never hit a socket."""
    from requests.adapters import BaseAdapter
    from requests import Response, Session

    class InMemoryAdapter(BaseAdapter):
        def __init__(self):
            self.requests = []

        def send(self, request, **_kwargs):
            self.requests.append(request)
            resp = Response()
            resp.status_code = 200
            resp._content = b'{"ok":true}'
            resp.headers["Content-Type"] = "application/json"
            resp.request = request
            resp.url = request.url
            return resp

        def close(self):
            pass

    sess = Session()
    adapter = InMemoryAdapter()
    sess.mount("https://", adapter)
    with VoipanoClient(token="test-token", session=sess) as client:
        assert client.contacts.all({"search": "سلام", "page": 1}) == {"ok": True}
        assert client.contacts.create({"primary_number": "09120000000"}) == {"ok": True}
    get, post = adapter.requests
    assert get.method == "GET"
    assert get.url == BASE + "/contacts?search=%D8%B3%D9%84%D8%A7%D9%85&page=1"
    assert get.headers["Authorization"] == "Bearer test-token"
    assert post.headers["Content-Type"] == "application/json"
    assert json.loads(post.body) == {"primary_number": "09120000000"}
    assert post.url == BASE + "/contacts"
    sess.close()
