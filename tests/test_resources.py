from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import FakeResponse


# Every one of the 23 Postman requests, including method aliases, must be covered.
CASES = [
    ("GET", "/services", lambda c: c.services.all()),
    ("GET", "/contacts", lambda c: c.contacts.all({"page": 1})),
    ("GET", "/contacts/contact-1", lambda c: c.contacts.find("contact-1")),
    ("POST", "/contacts", lambda c: c.contacts.create({"primary_number": "09120000000"})),
    ("PATCH", "/contacts/contact-1", lambda c: c.contacts.update("contact-1", {"first_name": "Ali"})),
    ("PUT", "/contacts/contact-1", lambda c: c.contacts.update_put("contact-1", {"first_name": "Ali"})),
    ("DELETE", "/contacts/contact-1", lambda c: c.contacts.delete("contact-1")),
    ("POST", "/contacts/bulk-import", lambda c: c.contacts.bulk_import([{"primary_number": "09120000000"}])),
    ("GET", "/contact-groups", lambda c: c.contact_groups.all()),
    ("POST", "/contact-groups", lambda c: c.contact_groups.create({"name": "VIP"})),
    ("DELETE", "/contact-groups/group-1", lambda c: c.contact_groups.delete("group-1")),
    ("GET", "/music-on-holds", lambda c: c.music_on_holds.all()),
    ("GET", "/call-reports", lambda c: c.call_reports.all()),
    ("GET", "/voicemail-inboxes", lambda c: c.voicemail_inboxes.all()),
    ("GET", "/call-recordings/cdr-1", lambda c: c.recordings.call("cdr-1", "detail-1")),
    ("GET", "/voicemail-recordings/vm-1", lambda c: c.recordings.voicemail("vm-1", "default", "1001")),
    ("GET", "/call-events-webhook", lambda c: c.webhooks.get()),
    ("PUT", "/call-events-webhook", lambda c: c.webhooks.configure({"is_active": False})),
    ("PUT", "/call-events-webhook", lambda c: c.webhooks.route("missed_call", {"is_active": True})),
    ("POST", "/call-events-webhook", lambda c: c.webhooks.configure_legacy({"is_active": True})),
    ("POST", "/call-otp", lambda c: c.calls.otp("09120000000", purpose="login")),
    ("POST", "/click-to-call", lambda c: c.calls.click_to_call("09120000000", "09121111111")),
    ("POST", "/secure-call", lambda c: c.calls.secure_call("09120000000", "09121111111", retry_count=0)),
]


def test_all_documented_endpoints_match_postman(client, session):
    collection = json.loads((Path(__file__).resolve().parents[1] / "docs/voipano-webservice.postman_collection.json").read_text(encoding="utf-8"))
    documented = []
    for category in collection["item"]:
        for entry in category["item"]:
            request = entry["request"]
            documented.append((request["method"], request["url"]["raw"].split("?", 1)[0].replace("{{api_base_url}}", "")))
    normalized = [(m, p.replace("{{contact_id}}", "contact-1").replace("{{contact_group_id}}", "group-1")
                   .replace("{{cdr_id}}", "cdr-1").replace("{{voicemail_unique_id}}", "vm-1")) for m, p in documented]
    assert sorted(normalized) == sorted((m, p) for m, p, _ in CASES)
    for method, path, invoke in CASES:
        session.queue(FakeResponse(body=b"audio", headers={"Content-Type": "audio/wav"}) if "recordings/" in path else FakeResponse())
        invoke(client)
        called_method, url, kwargs = session.calls[-1]
        assert called_method == method
        assert url.endswith(path)
        assert kwargs["allow_redirects"] is False
    assert len(session.calls) == 23


def test_required_immutable_fields(client, session):
    client.calls.otp("09120000000", {"phone_number": "OVERRIDE", "purpose": "login"})
    assert session.calls[-1][2]["json"]["phone_number"] == "09120000000"
    client.webhooks.route("missed_call", {"event": "hangup"})
    assert session.calls[-1][2]["json"]["event"] == "missed_call"
    session.queue(FakeResponse(body=b"RIFF", headers={"Content-Type": "audio/wav"}))
    client.recordings.call("cdr", "detail", {"call_details_record_id": "wrong"})
    assert session.calls[-1][2]["params"]["call_details_record_id"] == "detail"


def test_bulk_import_validation(client, session):
    for invalid in ([], ["wrong"], [{}] * 3001, "wrong"):
        with pytest.raises(ValueError):
            client.contacts.bulk_import(invalid)
    assert not session.calls


def test_webhook_event_rejected(client, session):
    with pytest.raises(ValueError):
        client.webhooks.route("nonexistent", {"is_active": True})
    assert not session.calls


@pytest.mark.parametrize("call", [
    lambda c: c.calls.otp(""),
    lambda c: c.calls.click_to_call("", "09121111111"),
    lambda c: c.calls.secure_call("09120000000", ""),
    lambda c: c.recordings.call("cdr", ""),
    lambda c: c.recordings.voicemail("vm", "", "1001"),
    lambda c: c.recordings.voicemail("vm", "default", ""),
])
def test_required_api_fields_checked_before_network(client, session, call):
    with pytest.raises(ValueError):
        call(client)
    assert session.calls == []
