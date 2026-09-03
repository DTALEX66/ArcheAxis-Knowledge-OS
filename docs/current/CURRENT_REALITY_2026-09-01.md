# Current Reality — 2026-09-01 Field Reconciliation (refreshed 2026-09-04)

> Scope: current-state navigation and evidence reconciliation only. This record
> does not alter frozen task packs, immutable releases, historical receipts, or
> the public version number.

## Authoritative live identities

| Subject | Field fact | Evidence class |
| --- | --- | --- |
| Canonical branch | `main@9217c510b3b150fe9da72a437ad31df45db616c4` = `origin/main@9217c510b3b150fe9da72a437ad31df45db616c4` at the 2026-09-04 reconciliation capture | Git readback |
| Current published release | `v0.6.14`, published 2026-08-29; GitHub release exposes Setup, Green, Portable, wheel, identity, manifest, SBOM, notices and checksums (9 assets). The immutable [v0.6.14 release receipt](../../reports/release/v0.6.14/release-evidence.json) binds its tag, source, CI, Release workflow and assets. | GitHub release/API/workflow readback |
| Local Green runtime | `D:\All projects\ArcheAxis.Knowledge.Green-x64`; identity is `v0.6.14` | Local identity readback |
| Green in-place maintenance | Earlier `0bb6e25` media-module repair remains present; Green also carries the shared OCR-language and ASR-model discovery fixes. On 2026-09-03, the rebuilt primary shell carrying the offline monochrome frontend was hash-deployed in place: candidate and Green `ArcheAxis.exe` are `132f1c8ccc5344cd8b709826b79c59ba01cf59b919073fd36a67ec249c5a0538`; the prior EXE was backed up. A controlled visible product-path restart is still required before any installed-runtime claim. | Local module/hash readback; restart still pending |
| Main CI baseline | Exact SHA `9217c510` Actions run `33667525835` ran broad qualification but failed fail-closed: lint rejected a legacy-name placement and four generated schema final-newline violations; wheel smoke used a fake `tesseract` with no version identity, so the resolver returned an error object without `text`. The seven scoped repairs remain staged locally and are not a cloud result. | Exact-SHA CI failed; qualification remains open |

## What the evidence does and does not prove

- The Green deployment/import readback proves the two patched Python modules are
  present in the named Green runtime. It does **not** prove a full interactive
  installed-runtime journey; that still requires a controlled Windows launch
  and product-path readback on the same tree.
- The prior `0bb6e25` targeted backend, frontend build and Chromium smoke
  evidence remains historical evidence for that tree. `9217c510` has a newer
  exact-SHA CI result, but its fail-closed lint and wheel-smoke outcomes mean
  neither it nor the local staged repair proves a successful qualification.
- `v0.6.14` is the latest published release. It stays immutable for this work:
  the hotfix is a maintenance commit on `main`, not a new version, tag, asset
  set or Release.

## Reconciled current policy

- Canonical Windows product shell: `frontend/` plus root `src-tauri/`.
- 当前源码前端默认使用离线黑白深色 token；本地 Vite 浏览器已验证工作台、资料库导航与
  命令面板显隐，但该结果是 `TESTED_LOCAL/BUILT_LOCAL`，不替代 Tauri/Green WebView 或已安装产品路径验收。
- DeepTutor is a replaceable learning sidecar/authority projection. The R2
  task-pack statement calling it a product base is retained as historical task
  context and does not override the later single-shell consolidation contract.
- AXW-1205 through AXW-1210 are completed document-governance deliverables;
  their existence does not claim that their dependent long-horizon product
  capabilities are implemented.
- Backup/export has verified implementation evidence, so `REQ-BACKUP-001` is
  `in_progress`, consistent with CAP-0140. Synchronization and publication
  remain future scope.
- The language-and-boundary route is governed by the active
  [`AXM G0 migration freeze rules`](AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md):
  current Green maintenance remains allowed, while migration work is
  single-writer and rollback-first.
- The [`AXM G0 Golden corpus plan`](AXM_G0_GOLDEN_CORPUS_PLAN_2026-09-02.md)
  separates eligible repository fixtures from material that still lacks rights,
  privacy or raw-hash evidence; no user study material is part of the baseline.
- The first-wave [`AXM G0 owner map`](AXM_G0_OWNER_MAP_2026-09-02.md) records
  the present product-path writers and dormant V2 contracts. It is a read-only
  migration prerequisite, not proof that Rust or a V2 table is already live.
- The 2026-09-01 language audit is incorporated through the
  [`AXM language-audit task map`](AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md).
  Its G0 evidence gates remain blocking; its later Rust, sidecar and UI phases
  are ordered work, not current implementation claims.
- The binding lookup for present Python/React/Rust ownership, sidecar limits
  and the canonical runtime variable is the
  [`language boundary authority`](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md).
- The directory-convergence proposal is separately incorporated through the
  [`AX-DIR task map`](AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md).
  It is not started: its proposed runtime-root move conflicts with the current
  `.hermes` authority and must be decided before any directory, data or cleanup
  mutation can begin.
- The binding classification for source, compatibility, history, runtime and
  shared external-library paths is the
  [`directory authority`](../DIRECTORY_AUTHORITY_INDEX.md).
- The active cleanup/index/language sequence is maintained in the
  [`repository normalization state`](REPOSITORY_NORMALIZATION_STATE_2026-09-03.md).
  It records evidence requirements and does not authorize a deletion, move,
  writer cutover, Release or cloud-success claim by itself.
- The [`operational issue archive`](OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md)
  is the fast lookup route for recurring CI, toolchain, launcher, frontend and
  evidence failures. It classifies the evidence layer and links back to this
  record instead of promoting a diagnosis into proof of a fixed runtime.

## Next evidence obligations

1. Commit and push only the reviewed seven-file CI repair batch, then obtain a
   full-qualification exact-SHA CI result for the resulting SHA. Do not infer
   a green result from the staged diff or from successful individual jobs in
   the failed `9217c510` run.
2. Obtain controlled, exclusive Green Windows product-path smoke access and
   retain the result under project-local `.hermes/task-artifacts/`. The primary
   main-shell candidate has been hash-read-back into the existing Green
   `ArcheAxis.exe`. The silent VBS path currently has an open argument/quoting
   failure, so it must be repaired and verified before any launch-success
   claim; `/version` and `/workspace/api/status` availability do not replace a
   user-visible interaction/product-path result, and the active instance must not be
   interrupted merely to make an automation attachment easier. The browser-visible capture at
   `.hermes/task-artifacts/ui/green-static-fallback-20260902.png` is deliberately
   not that product-path result: it is the `http://127.0.0.1:8015/` static
   frontend fallback and visibly reports that its Core API is unavailable.
   `start.bat` itself delegates to the adjacent VBS launcher and therefore is
   not the source of a command-window host. The actual desktop executable must
   be checked through that VBS path when its existing user instance can be
   safely attached or restarted under explicit control.
3. Run fresh/existing workspace journey receipts for the recorded
   project-authored TXT/HTML/DOCX/PPTX/XLSX/PDF/Canvas, screenshot OCR, WAV and
   MP4 fixtures. Current local and Green component probes cover webpage,
   screenshot/image OCR, audio and video, but do not yet qualify an all-format
   installed runtime.
4. Continue the human-learning and ecosystem work as independently evidenced
   increments; neither upstream branding nor historical task-pack wording can
   promote a capability by itself.
