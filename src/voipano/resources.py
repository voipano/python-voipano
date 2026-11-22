"""Explicit resource wrappers for every endpoint in the 2026-11-21 collection."""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._http import Transport, _path_segment

Json = dict[str, Any] | list[Any]


def _required(value: str | int, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise ValueError(f"{label} must not be empty")
    return str(value)


class Resource:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def _get(self, path: str, filters: Mapping[str, Any] | None = None) -> Json:
        return self._transport.request("GET", path, filters)

    def _write(self, method: str, path: str, data: Mapping[str, Any]) -> Json:
        return self._transport.request(method, path, data)


class Services(Resource):
    def all(self) -> Json:
        return self._get("/services")


class Contacts(Resource):
    def all(self, filters: Mapping[str, Any] | None = None) -> Json:
        return self._get("/contacts", filters)

    def find(self, contact_id: str | int) -> Json:
        return self._get(f"/contacts/{_path_segment(contact_id)}")

    def create(self, data: Mapping[str, Any]) -> Json:
        return self._write("POST", "/contacts", data)

    def update(self, contact_id: str | int, data: Mapping[str, Any]) -> Json:
        """PATCH, modifying only provided fields (empty arrays may clear values)."""
        return self._write("PATCH", f"/contacts/{_path_segment(contact_id)}", data)

    def update_put(self, contact_id: str | int, data: Mapping[str, Any]) -> Json:
        """PUT, documented as a partial update alias, not full replacement."""
        return self._write("PUT", f"/contacts/{_path_segment(contact_id)}", data)

    def delete(self, contact_id: str | int) -> Json:
        return self._transport.request("DELETE", f"/contacts/{_path_segment(contact_id)}")

    def bulk_import(self, contacts: Sequence[Mapping[str, Any]], options: Mapping[str, Any] | None = None) -> Json:
        """Import 1..3000 contacts; performed as one request without retries."""
        if isinstance(contacts, (str, bytes)) or not isinstance(contacts, (list, tuple)) or not 1 <= len(contacts) <= 3000:
            raise ValueError("contacts must be a list/tuple of 1 to 3000 objects")
        if any(not isinstance(entry, Mapping) for entry in contacts):
            raise ValueError("each contact must be a mapping")
        data = dict(options or {})
        data["contacts"] = list(contacts)
        return self._write("POST", "/contacts/bulk-import", data)


class ContactGroups(Resource):
    def all(self, filters: Mapping[str, Any] | None = None) -> Json:
        return self._get("/contact-groups", filters)

    def create(self, data: Mapping[str, Any]) -> Json:
        return self._write("POST", "/contact-groups", data)

    def delete(self, group_id: str | int) -> Json:
        return self._transport.request("DELETE", f"/contact-groups/{_path_segment(group_id)}")


class MusicOnHolds(Resource):
    def all(self, filters: Mapping[str, Any] | None = None) -> Json:
        return self._get("/music-on-holds", filters)


class CallReports(Resource):
    def all(self, filters: Mapping[str, Any] | None = None) -> Json:
        return self._get("/call-reports", filters)


class VoicemailInboxes(Resource):
    def all(self, filters: Mapping[str, Any] | None = None) -> Json:
        return self._get("/voicemail-inboxes", filters)


class Recordings(Resource):
    """Binary read/download. Always supply both call-recording identifiers."""

    def call(self, cdr_id: str | int, call_details_record_id: str | int, query: Mapping[str, Any] | None = None) -> bytes:
        return self._transport.binary(
            f"/call-recordings/{_path_segment(cdr_id)}",
            {**dict(query or {}), "call_details_record_id": _required(call_details_record_id, "call_details_record_id")},
        )

    def download_call(
        self, cdr_id: str | int, call_details_record_id: str | int,
        destination: str | PathLike[str], query: Mapping[str, Any] | None = None,
    ) -> Path:
        return self._transport.download_to(
            f"/call-recordings/{_path_segment(cdr_id)}", destination,
            {**dict(query or {}), "call_details_record_id": _required(call_details_record_id, "call_details_record_id")},
        )

    def voicemail(self, unique_id: str | int, context: str, mailbox: str, query: Mapping[str, Any] | None = None) -> bytes:
        return self._transport.binary(
            f"/voicemail-recordings/{_path_segment(unique_id)}",
            {**dict(query or {}), "context": _required(context, "context"), "mailbox": _required(mailbox, "mailbox")},
        )

    def download_voicemail(
        self, unique_id: str | int, context: str, mailbox: str,
        destination: str | PathLike[str], query: Mapping[str, Any] | None = None,
    ) -> Path:
        return self._transport.download_to(
            f"/voicemail-recordings/{_path_segment(unique_id)}", destination,
            {**dict(query or {}), "context": _required(context, "context"), "mailbox": _required(mailbox, "mailbox")},
        )


class Webhooks(Resource):
    EVENTS = frozenset({"ringing", "hangup", "missed_call", "call_details_record"})

    def get(self) -> Json:
        return self._get("/call-events-webhook")

    def configure(self, settings: Mapping[str, Any]) -> Json:
        return self._write("PUT", "/call-events-webhook", settings)

    def route(self, event: str, settings: Mapping[str, Any]) -> Json:
        if event not in self.EVENTS:
            raise ValueError("Unsupported call event")
        return self._write("PUT", "/call-events-webhook", {**settings, "event": event})

    def configure_legacy(self, settings: Mapping[str, Any]) -> Json:
        """Legacy POST alias for PUT configure()."""
        return self._write("POST", "/call-events-webhook", settings)


class Calls(Resource):
    """These methods initiate REAL calls; the SDK never retries them."""

    def otp(self, phone_number: str, options: Mapping[str, Any] | None = None, **kwargs: Any) -> Json:
        return self._write("POST", "/call-otp", {**dict(options or {}), **kwargs, "phone_number": _required(phone_number, "phone_number")})

    def click_to_call(
        self, source: str, destination: str, options: Mapping[str, Any] | None = None, **kwargs: Any,
    ) -> Json:
        return self._write("POST", "/click-to-call", {
            **dict(options or {}), **kwargs, "call_source": _required(source, "call_source"), "call_destination": _required(destination, "call_destination"),
        })

    def secure_call(
        self, source: str, destination: str, options: Mapping[str, Any] | None = None, **kwargs: Any,
    ) -> Json:
        return self._write("POST", "/secure-call", {
            **dict(options or {}), **kwargs, "call_source": _required(source, "call_source"), "call_destination": _required(destination, "call_destination"),
        })
