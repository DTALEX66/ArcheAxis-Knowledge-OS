# Current Reality — 2026-09-01 Field Reconciliation

> Scope: current-state navigation and evidence reconciliation only. This record
> does not alter frozen task packs, immutable releases, historical receipts, or
> the public version number.

## Authoritative live identities

| Subject | Field fact | Evidence class |
| --- | --- | --- |
| Canonical branch | `main` = `origin/main` = `0bb6e253dc3b9e16a7524f92a3d56f2cc6aba0c0` at capture | Git readback |
| Current published release | `v0.6.14`, published 2026-08-29; GitHub release exposes Setup, Green, Portable, wheel, identity, manifest, SBOM, notices and checksums (9 assets) | GitHub release readback |
| Local Green runtime | `D:\All projects\ArcheAxis.Knowledge.Green-x64`; identity is `v0.6.14` | Local identity readback |
| Green hotfix | `media_adapter.py` and `multi_format.py` in Green were hash-read back after deployment from commit `0bb6e25`; the Green UI bundle already matched the tested source bundle | Local module/hash readback |
| Main CI for hotfix | GitHub Actions CI run `33512729294` is bound to `0bb6e25` and failed in two Windows-unit tests because the Linux OS test job had not installed a Vite entrypoint; format, wheel, lint and browser gates succeeded | Exact-SHA CI failed; test-fixture repair required |

## What the evidence does and does not prove

- The Green deployment/import readback proves the two patched Python modules are
  present in the named Green runtime. It does **not** prove a full interactive
  installed-runtime journey; that still requires a controlled Windows launch
  and product-path readback on the same tree.
- The previously recorded targeted backend, frontend build and Chromium smoke
  evidence belongs to `0bb6e25`; exact-SHA cloud CI is a separate delivery
  layer. Run `33512729294` is a failure, caused by a test fixture that did not
  provide the entrypoint required by the Windows branch it exercises; a fresh
  exact-SHA CI run remains required after that fixture is repaired.
- `v0.6.14` is the latest published release. It stays immutable for this work:
  the hotfix is a maintenance commit on `main`, not a new version, tag, asset
  set or Release.

## Reconciled current policy

- Canonical Windows product shell: `frontend/` plus root `src-tauri/`.
- DeepTutor is a replaceable learning sidecar/authority projection. The R2
  task-pack statement calling it a product base is retained as historical task
  context and does not override the later single-shell consolidation contract.
- AXW-1205 through AXW-1210 are completed document-governance deliverables;
  their existence does not claim that their dependent long-horizon product
  capabilities are implemented.
- Backup/export has verified implementation evidence, so `REQ-BACKUP-001` is
  `in_progress`, consistent with CAP-0140. Synchronization and publication
  remain future scope.

## Next evidence obligations

1. Repair the isolated Vite-entrypoint test fixture and read the resulting
   exact-SHA CI run; do not infer success from the unrelated passing gates.
2. Run a controlled Green Windows product-path smoke on `0bb6e25` and retain
   the result under project-local `.hermes/task-artifacts/`.
3. Execute the current-sha Tier-A matrix rather than promoting historic
   single-format evidence into all-format support.
4. Continue the human-learning and ecosystem work as independently evidenced
   increments; neither upstream branding nor historical task-pack wording can
   promote a capability by itself.
