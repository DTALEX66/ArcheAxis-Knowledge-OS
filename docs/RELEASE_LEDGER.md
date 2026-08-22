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
| `v0.5.0` | yes | yes | yes | 2026-08-09 | Public stable Release; exact-SHA qualification, installer lifecycle, asset allowlist, checksum and identity readback passed. |
| `v0.6.0` | yes | no | — | — | Historical unpublished tag at `0b633a6`; preserved by the immutable-tag policy. |
| `v0.6.1` | yes | no | — | — | Historical unpublished tag at `f75021c`; Release run `32586776986` failed because the public identity was injected after the CI candidate installer had been built. Preserved. |
| `v0.6.2` | yes | no | — | — | Historical unpublished tag at `8c649be`; Release run `32588200482` rebuilt the installer but the installed runtime rejected schema v3 identity, exposing producer/consumer contract drift. Preserved. |
| `v0.6.3` | yes | no | — | — | Historical unpublished tag at `61b226a`; Release run `32590345393` passed the identity-bound NSIS lifecycle, then the ZIP lifecycle compared a non-normalized expected Python path to the canonical CIM path. Preserved. |
| `v0.6.4` | yes | no | — | — | Historical unpublished tag at `5a71ffa`; Release run `32592474961` passed path and identity checks, then the ZIP verifier hit the same nondeterministic `CloseMainWindow()` race previously fixed for NSIS. Preserved; remediation proceeded as `v0.6.5`. |
| `v0.6.5` | yes | no | — | — | Historical unpublished tag at `809cd5d`; exact-SHA CI run `32593904745` passed. Release run `32594767473` passed the identity-bound NSIS lifecycle and exact-window ZIP shutdown, then exposed a verifier-only Portable database readback path error: it checked `data/data/archeaxis.sqlite` although the canonical resolver writes `data/archeaxis.sqlite`. Preserved; remediation proceeded as `v0.6.6`. |
| `v0.6.6` | yes | draft | no | unpublished | Historical unpublished tag at `b6c92bd`; exact-SHA CI run `32596718833` passed. Release run `32597563772` passed all three Windows lifecycle gates and uploaded the draft asset set, then the final lock readback interpolated `"$entry.Name"` as an object string plus literal suffix instead of the property value. Preserved; remediation proceeds as `v0.6.7`. |

## v0.4.4 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.4.4>
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
    "ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30839451084"
  }
}
```

Asset hashes are valid and cross-check, but the provenance field points at
the wrong run (the Release workflow run instead of the verification CI). Per
project policy this historical tag/Release is preserved and **not** edited
in place; the defect is recorded here. Future releases must use schema v2
with `verification_ci_run_id` / `release_run_id` kept distinct.

## v0.5.0 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.5.0>
- Release run: `31277061510`
- Verification (merge-SHA Full Qualification) run: `31276290892`
- Tag target commit: `fe977577da53dafa4528da908898995ba316b53a`
- Tag target tree: `3219c3fba0298d475fcd197c506b06d89422fda9`
- Published assets (4), all present in `SHA256SUMS.txt` and re-hashed after download:

| Asset | Provider SHA-256 digest |
| --- | --- |
| `ArcheAxis.OS-Windows-x64-setup.exe` | `142a56e8fff2bdcb0ef5d78f287e0f500eafe58f0e3f9ba1f0db73c28bb58239` |
| `cognitive_loop_os-0.5.0-py3-none-any.whl` | `5ec1c460096f06376636e18379cbac44b06038c8203e39a8f106258c165018a1` |
| `release-identity.json` | `aaf4cc157bde171b6670a5d8dcb7f7d7314361d8ff264bb6ef56a2126d8983b1` |
| `SHA256SUMS.txt` | `7df2637e185e8fe8d2d4be193f95527e984117ffb9ac83d60362ac5e66341deb` |

The downloaded `release-identity.json` is schema v2 and binds the public
release to the exact commit/tree, verification CI run `31276290892`, and
release workflow run `31277061510`. The source manifest intentionally remains
`unreleased / development / public=false`; that is a source-truth placeholder,
not a contradiction of the verified artifact identity.

## v0.4.0 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.4.0>
- Published 2026-07-30. Readback found the public installer name did not
  match its checksum-manifest name and an extra public payload was absent
  from the manifest. Retained as historical evidence; no rewrite.

## Policy

- Never rewrite an existing tag, Release, or published asset.
- Every future release: exact-SHA full qualification; identity schema v3;
  `verification_ci_run_id` ≠ `release_run_id`; asset allowlist + provider
  digest + downloaded SHA-256 recompute; install/start/restart/exit/uninstall
  evidence.
- **Signature decision (recorded 2026-08-15, AXC-060)**: releases are
  deliberately **not code-signed** (no commercial certificate; private/local
  distribution channel). Integrity is carried by SHA-256SUMS.txt + provider
  digests + release-identity.json binding tag→exact commit/tree→verification
  CI run. If a public/enterprise channel is ever added, re-evaluate
  Authenticode signing as a separate owner decision before publishing there.
- Source manifest line is `0.6.7`, `unreleased`, `development`, `public=false`;
  public artifact identity is recorded separately in the verified Release.
