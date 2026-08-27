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
| `v0.6.7` | yes | yes | yes | 2026-08-22 21:50:57 | Historical public stable Release at `347d9f9`; exact-SHA CI, three Windows lifecycle gates, schema v3 identity, provider digests, checksum allowlist and independent downloaded-asset readback passed. |
| `v0.6.8` | yes | yes | yes | 2026-08-23 00:45:26 | Historical public stable Release at `93e58a3`; six-space/source/AI closed-loop update and independent 9-asset readback passed. |
| `v0.6.9` | yes | yes | yes | 2026-08-23 06:48:11 | Historical public stable Release at `de5b5ba`; Recovery Shell, thin frontend and risk-selected CI update; exact-SHA CI, three Windows lifecycle gates and workflow public-asset readback passed. |
| `v0.6.10` | yes | yes | yes | 2026-08-23 21:02:53 | Historical public stable Release at `3428a65`; real Activity Dock actions, raw-first E2E correction and latest-SHA CI recovery; exact-SHA CI, three Windows lifecycle gates and workflow public-asset readback passed. |
| `v0.6.11` | yes | yes | yes | 2026-08-27 13:45:33 | Current public stable Release at `86cecc7`; R2 truth/safety/product-base closure, DeepTutor local-model golden flow, exact-SHA CI `33076417510`, three Windows lifecycle gates and Release workflow `33077810146` public-asset readback passed. |

## v0.6.11 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.11>
- Tag commit: `86cecc7272152ef334869f61aae1f4d5ce82679b`
- Source tree: `fe389f6a43d8295ffcc8109eaeced9436e361b03`
- Verification exact-SHA CI: `33076417510`（success；15 required jobs 全通过）
- Release workflow: `33077810146`（success）
- Published: `2026-08-27T13:45:33Z`; public, non-draft, non-prerelease
- Public assets: 9；Release workflow 已完成 draft/public 双阶段下载、provider digest、checksum allowlist 与三分发生命周期读回
- Local independent readback: 9/9 全资产下载；provider digest、`SHA256SUMS.txt` 8 payload、schema v3 identity、tag/commit/tree、verification/release run 与 dependency locks 全部匹配
- DeepTutor v1.5.17 + Ollama `qwen3:8b`: online doctor required checks PASS；Chromium 教学、答题反馈、无效答案恢复和 reload readback PASS，console 0 error
- Public provider SHA-256: Setup `f758f014…`；Green `4cf56787…`；Portable `17d81aaa…`；完整 9 资产值由 machine-readable receipt 保存
- Machine-readable receipt: `reports/release/v0.6.11/release-evidence.json`

## v0.6.10 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.10>
- Tag commit: `3428a65cf6445918365f76b114cc11630d9640bb`
- Source tree: `828ffe3039b65d1b2fccf9c9348233342818cea1`
- Verification exact-SHA CI: `32665051446` (success)
- Release workflow: `32665840172` (success; distinct from verification CI)
- Published: `2026-08-23T21:02:53Z`; public, non-draft, non-prerelease
- Public assets: 9; Release workflow download readback and all three distribution lifecycles PASS
- Local extra readback: 3/9 small metadata assets; provider SHA-256 digests matched. Large Windows payloads were not redundantly downloaded locally.

Machine-readable receipt: `reports/release/v0.6.10/release-evidence.json`.

## v0.6.9 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.9>
- Tag commit: `de5b5ba6efde2f306d029725c046b56d91226e4c`
- Source tree: `199eb5473c38e7d73ec078f7135d39bb756ce9be`
- Verification exact-SHA CI: `32622348279` (success)
- Release workflow: `32623033058` (success)
- Published: `2026-08-23T06:48:11Z`; public, non-draft, non-prerelease
- Public assets: 9; Release workflow download readback and lifecycle PASS
- Local extra readback: 6/9 digest matches; large Windows downloads stopped by Owner

Machine-readable receipt: `reports/release/v0.6.9/release-evidence.json`.

## v0.6.8 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.8>
- Tag commit: `93e58a3b2c537dd348903dd2296933e0cfb5a503`
- Source tree: `545eaa7ef62bab9e92e55a9ef598012bb368680a`
- Verification exact-SHA CI: `32607097436` (success)
- Release workflow: `32607789507` (success; distinct from verification CI)
- Published: `2026-08-23T00:45:26Z`; public, non-draft, non-prerelease
- Independent readback: 9 assets downloaded; all provider SHA-256 digests matched;
  `SHA256SUMS.txt` covered the other 8 payloads exactly.

| Asset | Provider and downloaded SHA-256 |
| --- | --- |
| `ArcheAxis.Knowledge-v0.6.8-Windows-x64-Green.zip` | `9a7b6c70fce906203a7474f56794784e8dc8b6a6a2ff1d8541f4469e89c1411b` |
| `ArcheAxis.Knowledge-v0.6.8-Windows-x64-Portable.zip` | `173c0b7a5e5bc8062faabb760fe686909eb9a2b029c21cbfb8e08e6b17ace019` |
| `ArcheAxis.Knowledge-v0.6.8-Windows-x64-Setup.exe` | `132d40a70f2ee1c82a1e57285aa7de57d987a3427d9d0c81952d76e4bc6fa3fc` |
| `archeaxis_workspace-0.6.8-py3-none-any.whl` | `0cd48e51340882543b1c4259ec28a18c99d913195aceccaea6aea058e4724667` |
| `release-identity.json` | `e721f4ec63e03497c4f7ad412ea41b35992becaf49c0f40303f80d7a1785e28d` |
| `release-manifest.json` | `2fa2df150cbab003f2a270d8e0570e4ab152693bd3529c20f69dc315ee717644` |
| `SBOM.cdx.json` | `a774cb6ef31f2b9ddc61aefe0e450310e3345880ca093bbb3063b346c7b88296` |
| `SHA256SUMS.txt` | `7fe4e0694720d2edf9a0cae602a25a67c4d08f759c74a9263a5ac86a74cf3ee7` |
| `THIRD_PARTY_NOTICES.txt` | `4ed609a56d846bda3f2bd55948cd6b7096319ea68a41b8845317bc8e4141fb47` |

Downloaded `release-identity.json` is schema v3 and binds the public release to
the exact tag/commit/tree, verification CI and Release run. Its dependency-lock
hashes matched local `uv.lock`, `frontend/package-lock.json`, and
`src-tauri/Cargo.lock`. The complete machine-readable receipt is
`reports/release/v0.6.8/release-evidence.json`.

## v0.6.7 release evidence

- GitHub Release URL: <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.7>
- Tag commit: `347d9f957b0509185df8c64e0578061a1ce2f9e3`
- Source tree: `ad150aad19c1ebe2766c3c1954ded8e5edd49b13`
- Verification exact-SHA CI: `32599003326` (success)
- Release workflow: `32599851308` (success; distinct from verification CI)
- Published: `2026-08-22T21:50:57Z`; public, non-draft, non-prerelease
- Independent readback: 9 assets downloaded; all provider SHA-256 digests matched;
  `SHA256SUMS.txt` covered the other 8 payloads exactly.

| Asset | Provider and downloaded SHA-256 |
| --- | --- |
| `ArcheAxis.Knowledge-v0.6.7-Windows-x64-Green.zip` | `044f48b489aaca115b4318ea806ddfb6e84cbbd91a478144f6b4e1bc71cbcea3` |
| `ArcheAxis.Knowledge-v0.6.7-Windows-x64-Portable.zip` | `416b735fddcd032dfc4280c9824a37cac682cc392a9bcb016b4a866efaa9fef1` |
| `ArcheAxis.Knowledge-v0.6.7-Windows-x64-Setup.exe` | `521d7d7c913682f0ef80b37f5bd333afc1abab8ac56043daee6ec98ac9989fd3` |
| `archeaxis_workspace-0.6.7-py3-none-any.whl` | `5b592f7a2aa72f970944e926e22fdf49d2a1dfc988275091cc4b32b11ef1a6c8` |
| `release-identity.json` | `2d82b2e69baa247c06d4aa78abf4c9e91ba8ad7603d6f6bf2d46e6660af09ca1` |
| `release-manifest.json` | `d5d39c8d44e98ffba6de736f7d5154f51fca42e19f54234eafd63e32c1d031d3` |
| `SBOM.cdx.json` | `e51644adf13fb78c27acdbd8312f2016e1d69e7e60613343f8020577e0499af8` |
| `SHA256SUMS.txt` | `66945349746b00a094b9f1c02584d1d233283db90a0e031f2b50f1269bb8c6a4` |
| `THIRD_PARTY_NOTICES.txt` | `b68e40ae34b96c4537c0a8144049513245e07232b536e698c0fadc166e7f97f9` |

Downloaded `release-identity.json` is schema v3 and binds the public release to
the exact tag/commit/tree, verification CI and Release run. Its dependency-lock
hashes matched local `uv.lock`, `frontend/package-lock.json`, and
`src-tauri/Cargo.lock`.

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
- Source manifest line is `0.6.8`, `unreleased`, `development`, `public=false`;
  public artifact identity is recorded separately in the verified Release.
