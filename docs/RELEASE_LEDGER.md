# Release Ledger

Read-only, historical account of every tag, GitHub Release, and published
asset. Dates and digests are read from Git/GitHub; a source entry never
proves publication by itself. This file does **not** mutate any tag or
Release — it records known truth and known defects so future releases carry
correct provenance.

## Version scheme

- `vX.Y.Z` tags exist in the Git history for every published or remediation
  attempt.
- A **GitHub Release** (public or draft) exists only for select tags.
- `app/release-manifest.json` is the source-of-truth manifest and remains
  `unreleased / public=false` until a verified release artifact is created.

## Tag and Release table

| Tag | Tag exists | GitHub Release | Public | Published (UTC) | Notes |
| --- | --- | --- | --- | --- | --- |
| `v0.4.0` | yes | yes | yes | 2026-07-30 | Historical. Readback found incomplete checksum payload coverage (public installer name vs manifest name mismatch; an extra public payload absent from manifest). Retained as evidence. |
| `v0.4.1` | yes | no | — | — | Remediation tag; no public Release. |
| `v0.4.2` | yes | draft | no | unpublished | Draft Release only; never published. |
| `v0.4.3` | yes | no | — | — | Remediation tag; no public Release. |
| `v0.4.4` | yes | yes | yes | 2026-08-03 | Current historical public stable Release. |
| `v0.5.0` | no | no | — | — | Current development version; no tag, no Release. |

## v0.4.4 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/Cognitive-Loop-OS/releases/tag/v0.4.4>
- Release run: `30839451084`
- Verification (exact-SHA CI) run: `30837105199`
- Published assets (4), all present in `SHA256SUMS.txt`:

| Asset | Provider SHA-256 digest |
| --- | --- |
| `ArcheAxis.OS-Windows-x64-setup.exe` | `d39677fa91752f99eeb4a372d4af80a7c769a37f4f92e863e178193d968ea93c` |
| `cognitive_loop_os-0.4.4-py3-none-any.whl` | `595fe6cd424964a0a8859591af8cce97741bd4c9bb91e578513b565f381d9dbc` |
| `release-identity.json` | `06ae73210df4a7be5902f07992e23637f7ea82ffebf19f93ab4c4783e3215dfb` |
| `SHA256SUMS.txt` | `5c71bfb4ede795269fae228b873c005078b8daf4a7a3e4f14f76e29265500174` |

- `targetCommitish: main`; downloaded SHA-256 payloads match the provider
  digests; asset hashes hold.

### Known provenance defect (recorded, not rewritten)

The published `release-identity.json` for `v0.4.4` is **schema v1** and its
`source.ci_run` / `source.ci_url` point to the **Release run** `30839451084`,
not the exact-SHA verification CI run `30837105199`:

```json
{
  "schema_version": "1.0.0",
  "source": {
    "commit": "f1117aebc19680513023bac6d20358ebfc7aabe6",
    "tree": "33db1766ba8e3a4e280c2bd587b8ac802d82fa72",
    "ci_run": 30839451084,
    "ci_url": "https://github.com/DTALEX66/Cognitive-Loop-OS/actions/runs/30839451084"
  }
}
```

Asset hashes are valid and cross-check, but the provenance field points at
the wrong run (the Release workflow run instead of the verification CI). Per
project policy this historical tag/Release is preserved and **not** edited
in place; the defect is recorded here. Future releases must use schema v2
with `verification_ci_run_id` / `release_run_id` kept distinct.

## v0.4.0 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/Cognitive-Loop-OS/releases/tag/v0.4.0>
- Published 2026-07-30. Readback found the public installer name did not
  match its checksum-manifest name and an extra public payload was absent
  from the manifest. Retained as historical evidence; no rewrite.

## Policy

- Never rewrite an existing tag, Release, or published asset.
- Every future release: exact-SHA full qualification; identity schema v2;
  `verification_ci_run_id` ≠ `release_run_id`; asset allowlist + provider
  digest + downloaded SHA-256 recompute; install/start/restart/exit/uninstall
  evidence.
- Current development line is `0.5.0`, `unreleased`, `development`,
  `public=false`.
