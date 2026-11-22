from __future__ import annotations

from pathlib import Path

import pytest

from voipano import ServerError, UnexpectedResponseError
from conftest import FakeResponse


def test_audio_bytes(client, session):
    session.queue(FakeResponse(body=b"RIFF123", headers={"Content-Type": "audio/wav"}))
    assert client.recordings.call("cdr", "detail") == b"RIFF123"
    method, _, kw = session.calls[-1]
    assert method == "GET" and kw["stream"] is True
    assert kw["headers"]["Accept"] == "*/*"


@pytest.mark.parametrize("type_", ["application/json", "application/problem+json", "text/html"])
def test_unexpected_file_response(client, session, type_):
    session.queue(FakeResponse(body=b'{"ok":true}', headers={"Content-Type": type_}))
    with pytest.raises(UnexpectedResponseError):
        client.recordings.voicemail("vm-1", "default", "1001")


def test_stream_file_exclusive_and_clean(client, session, tmp_path):
    session.queue(FakeResponse(body=b"RIFF" + b"X" * 100000, headers={"Content-Type": "audio/wav"}))
    path = client.recordings.download_call("cdr", "detail", tmp_path / "one.wav")
    assert path.read_bytes() == b"RIFF" + b"X" * 100000
    assert not list(tmp_path.glob(".voipano-*"))
    with pytest.raises(FileExistsError):
        client.recordings.download_call("cdr", "detail", path)
    assert len(session.calls) == 1


def test_download_api_error_leaves_no_file(client, session, tmp_path):
    session.queue(FakeResponse(500, body=b'{"message":"failed"}'))
    with pytest.raises(ServerError, match="failed"):
        client.recordings.download_voicemail("vm", "default", "1001", tmp_path / "bad.wav")
    assert list(tmp_path.iterdir()) == []


def test_broken_stream_cleans_temp(client, session, tmp_path):
    session.queue(FakeResponse(body=b"a" * 200000, headers={"Content-Type": "audio/wav"}, fail_stream=True))
    with pytest.raises(OSError, match="broken stream"):
        client.recordings.download_call("cdr", "detail", tmp_path / "bad.wav")
    assert list(tmp_path.iterdir()) == []


def test_reject_missing_parent(client, session, tmp_path):
    with pytest.raises(ValueError, match="parent"):
        client.recordings.download_call("cdr", "detail", tmp_path / "absent" / "new.wav")
    assert session.calls == []


def test_reject_error_stream_over_8192_bytes(client, session, tmp_path):
    session.queue(FakeResponse(403, body=b"BAD" * 5000, headers={"Content-Type": "application/json"}))
    from voipano import PermissionError
    with pytest.raises(PermissionError):
        client.recordings.download_call("cdr", "detail", tmp_path / "bad.wav")
    assert list(tmp_path.iterdir()) == []
