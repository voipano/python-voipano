# Changelog

## [1.0.1] - 2026-11-22

- Publish the official PyPI distribution as `voipano`.
- Preserve compatibility with the existing Python import API.

## [1.0.0] - 2026-11-22

- Initial Python SDK for the Voipano Public Webservice API v1 (23 documented requests).
- Typed client with isolated token/service scopes and standard API exceptions.
- Contacts, contact groups, calls, OTP, reports, recordings, and outgoing webhook resources.
- Streamed, exclusive audio downloads with cleanup on errors.
- Fail-closed optional incoming webhook receiver; signing specification pending API verification.
- Offline endpoint-contract tests, Python 3.11+ support, CI, and PyPI Trusted Publishing workflow.
