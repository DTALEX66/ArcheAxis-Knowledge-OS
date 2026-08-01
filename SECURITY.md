# Security Policy

## Supported versions

Security fixes are developed against the current `main` branch and the newest
published release, when one exists. The historical `v0.4.0` release is retained
for provenance but does not have complete checksum payload coverage. It must
not be treated as a fully integrity-verified distribution.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, personal
data, or private paths. Use GitHub's private security-advisory reporting for
this repository. If that facility is unavailable, open a minimal public issue
asking the maintainer to enable a private reporting channel, without including
the vulnerability details.

Include the affected version or commit, impact, reproduction preconditions,
and the smallest non-sensitive proof available. Never attach real credentials,
database contents, personal Vault data, or executable payloads.

## Release-security boundary

A successful build or CI run alone does not prove a public release. Release
claims require an exact main-commit tag, the required exact-SHA CI, an explicit
asset allowlist, checksum-manifest coverage, provider asset inventory readback,
downloaded SHA-256 verification, release-identity provenance, and installer
lifecycle verification. No release artifact is claimed to be cryptographically
signed unless a separate, verifiable signature and trust chain are published.
