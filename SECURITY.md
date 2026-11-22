# Security Policy

The Voipano Python SDK is designed to avoid exposing secrets or invoking duplicate operations through automatic retries. Use TLS, protect API tokens, store recordings privately, and do not log raw audio or credentials.

## Reporting a vulnerability

Please use your repository's private **Security → Report a vulnerability** mechanism (GitHub Security Advisories), or contact Voipano through its official support channel. Do not disclose exploitable vulnerabilities publicly before coordinating remediation.

## Webhook verification

The 2026-11-21 Postman collection does not document the signature scheme for incoming webhooks. Therefore the optional receiver **rejects all requests by default**. Do not treat incoming events as authenticated until you have confirmed a verifier with signature and replay protections.

## Support

This SDK targets Python 3.11+ and follows the actively supported Python versions. Security updates and advisories are handled through GitHub releases.
