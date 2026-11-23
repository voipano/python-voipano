# Voipano Python SDK

[![Tests](https://github.com/voipano/python-voipano/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/voipano/python-voipano/actions/workflows/tests.yml)
[![PyPI Version](https://img.shields.io/pypi/v/voipano)](https://pypi.org/project/voipano/)
[![License](https://img.shields.io/github/license/voipano/python-voipano)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-EN%20%7C%20FA-blue)](README.md)

[فارسی](README.fa.md) · [Postman collection](docs/voipano-webservice.postman_collection.json) · [Security](SECURITY.md)

The official, synchronous Python SDK for the **Voipano Public Webservice API v1**, providing the documented **23 requests** from the Postman collection dated **2026-11-21**. Designed for ordinary Python, Django, Flask, FastAPI, and other Python applications; there is **no framework dependency**.

## Requirements

- Python **3.11+** (the oldest Python line still receiving official security fixes in November 2026).
- An active Voipano API token for your account.
- The [`requests`](https://pypi.org/project/requests/) HTTP library is installed automatically.

## Install

Install the published package from PyPI:

```bash
python -m pip install voipano
```

Set an environment variable in your application environment (do not commit credentials):

```dotenv
VOIPANO_API_TOKEN=your-private-token
# Optional when your token does not select a single service:
VOIPANO_SERVICE_ID=
```

There is **no configuration file, CLI setup, database migration, or framework integration** required for outgoing requests.

## Quick start

```python
from voipano import VoipanoClient

with VoipanoClient() as voipano:  # reads VOIPANO_API_TOKEN from the environment
    services = voipano.services.all()
    contacts = voipano.contacts.all({"search": "Ali", "page": 1, "per_page": 20})
    contact = voipano.contacts.find("contact-id")
    voipano.contacts.create({"primary_number": "09120000000", "first_name": "Ali"})
    voipano.contacts.update("contact-id", {"first_name": "Ali"})

    # These calls trigger REAL telecommunications operations and may incur costs:
    # voipano.calls.otp("09120000000", purpose="login")
    # voipano.calls.click_to_call("09120000000", "09121111111", timeout=30)
    # voipano.calls.secure_call("09120000000", "09121111111", retry_count=0)
```

If preferred, pass credentials directly: `VoipanoClient(token="your-private-token")`.

## Multi-service and multi-tenant requests

Each scoped client has its own token, service ID, and request ID configuration without changing the original client:

```python
client = VoipanoClient(token="your-private-token")
customer_client = client.with_token("customer-token").for_service("service-id")
reports = customer_client.call_reports.all({"page": 1})
traced = customer_client.with_request_id("my-request-id").services.all()
customer_client.close()
client.close()
```

Note: independently created clients manage their own HTTP sessions. Injected custom sessions are shared between scoped copies; manage their lifecycle yourself.

## API resource methods

| Resource | Methods |
| --- | --- |
| `client.services` | `all()` |
| `client.contacts` | `all(filters)`, `find(id)`, `create(data)`, `update(id, data)`, `update_put(id, data)`, `delete(id)`, `bulk_import(contacts, options)` |
| `client.contact_groups` | `all(filters)`, `create(data)`, `delete(id)` |
| `client.music_on_holds` | `all(filters)` |
| `client.call_reports` | `all(filters)` |
| `client.voicemail_inboxes` | `all(filters)` |
| `client.recordings` | `call(cdr_id, record_id, query)`, `download_call(cdr_id, record_id, path, query)`, `voicemail(id, context, mailbox, query)`, `download_voicemail(id, context, mailbox, path, query)` |
| `client.webhooks` | `get()`, `configure(settings)`, `route(event, settings)`, `configure_legacy(settings)` |
| `client.calls` | `otp(phone, options, **kwargs)`, `click_to_call(source, destination, options, **kwargs)`, `secure_call(source, destination, options, **kwargs)` |

The client preserves API JSON responses as Python dictionaries or lists, without guessing about response schemas. HTTP 204 and empty responses return `{}`. Optional list filters are passed as documented, including `client_ref`.

### Call recordings and voicemail audio

Use **streaming** downloads for large files; the destination **must not already exist**, and its parent folder must already exist:

```python
from pathlib import Path
from voipano import VoipanoClient

client = VoipanoClient()
recording = client.recordings.download_call(
    "cdr-id", "call-details-record-id", Path("private/audio/call.wav")
)
voicemail = client.recordings.download_voicemail(
    "vm-id", "default", "1001", Path("private/audio/message.wav")
)
client.close()
```

The binary `.call()` and `.voicemail()` methods return `bytes` and read the whole recording into memory; use them only for small files. Downloaded audio may contain personal information: store it outside a public/static directory, apply access controls, and follow applicable retention rules.

**Known collection ambiguity:** the example uses different `cdr_id` (path) and `call_details_record_id` (query) identifiers but describes them as the same ID. The SDK requires both parameters until the actual API contract is confirmed.

### Outgoing webhook configuration

```python
client.webhooks.configure({
    "endpoint_url": "https://your-domain.example/webhooks/voipano",
    "secret": "your-webhook-secret",
    "is_active": True,
})
client.webhooks.route("missed_call", {
    "endpoint_url": "https://your-domain.example/webhooks/missed-call",
    "is_active": True,
})
```

Supported event names: `ringing`, `hangup`, `missed_call`, `call_details_record`. POST `configure_legacy` exists for the documented compatibility alias; prefer PUT `configure` for new integrations.

### Incoming webhook verification: secure by default

**Do not accept incoming events without verification.** The supplied Postman collection does not specify the signature header, signing algorithm, canonical payload, or replay-defense procedure. `WebhookReceiver` rejects all requests by default. Only supply a custom `WebhookVerifier` after validating the true protocol against the server implementation. There is intentionally **no web server route, hardcoded HMAC algorithm, or accept-all mode**.

```python
from voipano import WebhookReceiver, WebhookVerificationError

receiver = WebhookReceiver()  # rejects all incoming requests until configured
# receiver.receive(raw_request_body, request_headers) -> raises WebhookVerificationError
```

## Errors and reliability

```python
from voipano import ValidationError, VoipanoClient

try:
    VoipanoClient().contacts.create({"primary_number": "09120000000"})
except ValidationError as error:
    print(error.status_code, error.request_id, error.errors)
```

`AuthenticationError` (401), `PermissionError` (403), `NotFoundError` (404), `ValidationError` (422), `RateLimitError` (429), and `ServerError` (5xx) derive from `ApiError`. Transport errors (`TransportError`) and invalid response formats (`UnexpectedResponseError`) are separate.

The SDK uses **Bearer authentication**, optional `X-Webservice-Service-Id`, and one UUID `X-Request-Id` per HTTP request. Redirects and automatic retries are disabled. **Never blindly retry OTP or call requests** after timeouts: `client_ref` is described as a tracking value, not a confirmed idempotency key. Do not log secrets or raw audio files.

Timeouts can be customized: `VoipanoClient(timeout=30, connect_timeout=10, base_url="https://voipano.com/api/v1/webservice")`. Optional `VOIPANO_BASE_URL` is supported for controlled staging environments. HTTP(S) only; production should use HTTPS.

## Testing and release

This repository includes offline tests that never start actual calls:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m build
python -m twine check dist/*
```

`.github/workflows/tests.yml` runs tests on Python 3.11-3.15. Pushes to `main` trigger `publish.yml`, where `python-semantic-release` determines whether a new version is needed from Conventional Commit messages.

When a release is created, its distributions are built, tested, validated, and published to PyPI through Trusted Publishing (OIDC).

The package is already published on [PyPI](https://pypi.org/project/voipano/). For future releases, merge reviewed changes into `main`. Do not manually create or move release tags, overwrite published versions, or commit credentials and build artifacts.

The Postman collection contains **no example JSON responses** and does not document inbound webhook signatures, rate limits or idempotency guarantees. Automated tests verify request contracts and the SDK's handling of mock responses; they do not establish live API compatibility.

## License

MIT. See [LICENSE](LICENSE).
