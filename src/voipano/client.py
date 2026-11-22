"""Public, typed, synchronous client for the Voipano API."""

from __future__ import annotations

from typing import Any, Mapping

import requests

from ._http import Transport
from .resources import (
    CallReports, Calls, ContactGroups, Contacts, MusicOnHolds,
    Recordings, Services, VoicemailInboxes, Webhooks,
)


class VoipanoClient:
    """Official Voipano Public API v1 client.

    ``VoipanoClient()`` reads VOIPANO_API_TOKEN and optionally VOIPANO_SERVICE_ID
    and VOIPANO_BASE_URL from the process environment.

    Scoped copies from ``with_token``, ``for_service`` or ``with_request_id``
    do not modify the original client.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str | None = None,
        service_id: str | None = None,
        timeout: float = 30,
        connect_timeout: float = 10,
        session: requests.Session | None = None,
        _transport: Transport | None = None,
    ) -> None:
        self._transport = _transport or Transport(
            token,
            base_url=base_url,
            service_id=service_id,
            timeout=timeout,
            connect_timeout=connect_timeout,
            session=session,
        )

    @property
    def services(self) -> Services:
        return Services(self._transport)

    @property
    def contacts(self) -> Contacts:
        return Contacts(self._transport)

    @property
    def contact_groups(self) -> ContactGroups:
        return ContactGroups(self._transport)

    @property
    def music_on_holds(self) -> MusicOnHolds:
        return MusicOnHolds(self._transport)

    @property
    def call_reports(self) -> CallReports:
        return CallReports(self._transport)

    @property
    def voicemail_inboxes(self) -> VoicemailInboxes:
        return VoicemailInboxes(self._transport)

    @property
    def recordings(self) -> Recordings:
        return Recordings(self._transport)

    @property
    def webhooks(self) -> Webhooks:
        return Webhooks(self._transport)

    @property
    def calls(self) -> Calls:
        return Calls(self._transport)

    def with_token(self, token: str) -> VoipanoClient:
        return VoipanoClient(_transport=self._transport.copy(token=token))

    def for_service(self, service_id: str) -> VoipanoClient:
        return VoipanoClient(_transport=self._transport.copy(service_id=service_id))

    def with_request_id(self, request_id: str) -> VoipanoClient:
        return VoipanoClient(_transport=self._transport.copy(request_id=request_id))

    def request(self, method: str, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        """Advanced access to a documented JSON endpoint."""
        return self._transport.request(method, path, params)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> VoipanoClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()
