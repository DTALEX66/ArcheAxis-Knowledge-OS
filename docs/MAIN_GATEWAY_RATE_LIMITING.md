# Main Gateway Rate Limiting

The main FastAPI gateway applies a process-local sliding-window limiter before credential validation and again to an authenticated identity after a successful validation. The pre-auth reservation is released for valid credentials, while failed authentication keeps consuming the directly observed peer bucket. This bounds repeated API-key-file and HMAC validation work as well as route execution.

## Policies

`config/settings.yaml` defines one shared window and three request budgets:

- `ordinary_read`: `GET`, `HEAD`, and other non-mutating gateway requests.
- `sensitive_write`: `POST`, `PUT`, `PATCH`, and `DELETE` requests.
- `auth_token`: `/auth/token`, independently of method.

The write and token budgets must both be lower than the ordinary-read budget. Production configuration fails fast if rate limiting is disabled or any limit/trusted-proxy entry is invalid. A rejected request returns HTTP 429 with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and a deterministic JSON policy/retry payload. Responses never contain bucket keys, API keys, bearer tokens, or authenticated subjects.

## Identity and proxy trust

- API keys use a one-way SHA-256 bucket identifier derived from the authenticated credential. Raw keys are not stored in limiter state. Requests that send both `Authorization` and `X-API-Key` are rejected before authentication, so the credential used for authentication can never differ from the credential used for bucketing.
- JWTs use a one-way bucket identifier derived from the authenticated subject and remain separate from API-key buckets.
- Anonymous and failed-authentication requests use the directly observed socket peer address.
- When no trusted-proxy policy matches the direct peer, requests carrying `X-Forwarded-For`, `Forwarded`, or `X-Real-IP` are rejected. Rejecting rather than merely ignoring them remains fail closed even if an outer ASGI server has already rewritten `request.client`.
- Every early 400 rejection occurs only after a rate-limit reservation. Ambiguous credentials consume the observed-peer bucket. Because `request.client` is not trustworthy once untrusted proxy headers may have been processed externally, all such proxy-header rejections share a fixed opaque per-policy bucket instead of using attacker-controlled identity data. Repeated rejection traffic therefore reaches the same deterministic 429 boundary without trusting the spoofed header or rewritten peer.
- `X-Forwarded-For` is considered only when the directly connected peer matches an explicit IP/CIDR in `rate_limit.trusted_proxies`. The chain is parsed from the trusted edge toward the client; malformed chains fail closed to the directly observed peer. `Forwarded` and `X-Real-IP` are never used as identity sources.

The supported launch command must disable Uvicorn's own proxy rewriting so the application receives the socket peer unchanged:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Do not enable Uvicorn `--proxy-headers` in front of this application. Proxy identity ownership belongs to this gateway's explicit `trusted_proxies` policy; enabling a second trust layer outside the application destroys the original peer evidence before the gateway can evaluate it. The repository's CLI, Docker images, Compose service, PM2 configuration, and Windows/POSIX launch scripts all disable Uvicorn proxy-header rewriting, and targeted tests enforce those executable entrypoints rather than relying only on documentation.

Configure trusted proxies only when the gateway is actually reachable exclusively through those proxies. Trusting an address range that untrusted clients can occupy permits identity spoofing.

`max_buckets_per_policy` places a hard bound on each policy's identity map. Once the map is full, previously unseen identities fail closed with 429 and are not allocated. Identities with no activity for a complete window are reclaimed before new allocation.

Environment overrides are available as `COGNITIVE_RATE_LIMIT_ENABLED`, `COGNITIVE_RATE_LIMIT_WINDOW_SECONDS`, `COGNITIVE_RATE_LIMIT_READ`, `COGNITIVE_RATE_LIMIT_WRITE`, `COGNITIVE_RATE_LIMIT_TOKEN`, `COGNITIVE_RATE_LIMIT_MAX_BUCKETS`, and comma-separated `COGNITIVE_TRUSTED_PROXIES`.

## Deployment limitation

This limiter is intentionally in memory and process-local. Counters are not shared between Uvicorn/Gunicorn workers, containers, or hosts, and restart clears all windows. Therefore a deployment with multiple workers has an effective aggregate budget up to the sum of each worker's independent budget. This implementation must not be described or operated as a distributed rate limiter. Deployments requiring a global budget need a separately reviewed shared backend or enforcement at a trusted gateway/proxy.
