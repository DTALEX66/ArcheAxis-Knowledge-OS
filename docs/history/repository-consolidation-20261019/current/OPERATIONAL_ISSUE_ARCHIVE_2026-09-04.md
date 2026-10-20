# Operational Issue Archive — Historical Diagnostic Snapshot (2026-09-04)

> **Frozen dated diagnostic snapshot (2026-09-25).** The issue statuses,
> release/CI SHAs, G0 gates, desktop-shell assumptions and “current facts” links
> below describe the 2026-09-04 state. R6/M0 and current authority indexes
> supersede those execution/status claims. Reuse root-cause notes only after
> checking current source and evidence. This archive is not a live triage queue,
> runtime receipt, or permission to clean/move data.

## Safe reuse of this historical archive

1. Start with `AGENTS.md`, the documentation authority index, R6 TaskPack,
   M0 overlay, and current R6 execution/state.
2. Confirm the live path, SHA, process and evidence layer before acting.
3. Treat linked G0/adoption records and every status in this file as dated
   evidence; they do not define current blockers or execution order.
4. Record new observations in the current append-only execution log; do not
   rewrite historical failures.

## Issues recorded at the 2026-09-04 snapshot

| ID | Symptom and confirmed root cause | First safe diagnostic | Required durable remedy / evidence | Status and authority |
| --- | --- | --- | --- | --- |
| OP-001 | Exact SHA `9217c510` CI `33667525835` failed fail-closed. Lint found an unannotated legacy-name occurrence and four generated schema files without final LF. Wheel smoke's fake `tesseract` emitted no version string; the OCR resolver correctly rejected it, returning an error object rather than `text`. The corrective SHA `af216e3` run `33786524094` passed its selected gates. | Re-read exact source SHA and job conclusions; distinguish selected-gate results from skipped qualification jobs. | Retain OCR identity regression and bind any present qualification claim to exact-SHA current receipts. | **STATUS AT 2026-09-04: SELECTED REPAIR VERIFIED; FULL QUALIFICATION OPEN**. Current qualification: [R6 execution](R6-EXECUTION.md) / [R6 state](R6-STATE.json). |
| OP-002 | A successful path-selected CI or a local suite was previously treated as a broad qualification signal. Skipped, failed or unbound jobs cannot prove Windows, browser, wheel, installer or all-format behavior. | Read exact SHA and each job conclusion. | Bind qualification claims to the current R6 required gates and named evidence layer. | **STATUS AT 2026-09-04: OPEN**. Current status: [R6 execution](R6-EXECUTION.md) / [R6 state](R6-STATE.json). |
| OP-003 | Multi-format proof was narrowed accidentally to PDF. The 2026-09-04 fixture plan listed web, screenshot OCR, image, TXT/MD, Office, PDF, Canvas, WAV and MP4. | Reconfirm fixture ownership/rights and SHA under the current TaskPack before any use. | Qualify real format behavior only through current R6/M0 evidence and permitted resources. | **STATUS AT 2026-09-04: PARTIAL**. The old corpus/G0 plan is historical; current acceptance is in [R6 execution](R6-EXECUTION.md). |
| OP-004 | Windows build failures were caused by toolchain environment assembly, not Rust source: MSVC `cl.exe` was absent until the VS developer environment was loaded, and a batch `%PATH%` expansion before `VsDevCmd` discarded the loaded path. | In PowerShell 7, preflight the shared Rust, Cargo and VS developer environment before invoking a build; do not assume PATH inheritance. | Keep the toolchain setup explicit and record the command/environment boundary in project-local evidence. A successful build still needs separate Green runtime evidence. | **RECURRENCE PREVENTED IN BUILD PATH; runtime remains PARTIAL**. [Runtime delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md), [execution log](../truth/EXECUTION_STATUS_LOG.md). |
| OP-005 | Silent Green startup has not been qualified. Windows Script Host errors (`800A0408` invalid character and a path interpreted as `D:\\All` without a file extension) show an argument/quoting boundary failure, not a frontend capability failure. | Read the exact `启动星环知识.vbs` contents and its caller argument construction without launching desktop automation or touching Green `data`. | Add a regression for paths containing spaces; invoke only through the VBS route, then record executable path, API/status and user-visible result. | **OPEN**. [Runtime delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md), [Current Reality](CURRENT_REALITY_2026-09-01.md). |
| OP-006 | UI drift was caused by stale source/token and loading assumptions in the legacy Green React/Tauri surface. A browser/source check does not prove what an installed Green window loaded. | For Green maintenance only, check the legacy `frontend/` source and exact asset path; for vNext UI, use `apps/ArcheAxis.Desktop/` and its native evidence. | Keep the offline black/white default and bind current vNext UI claims to Avalonia route/runtime evidence; bind Green claims to its exact deployed executable. | **STATUS AT 2026-09-04: LEGACY SOURCE FIXED; GREEN RUNTIME PARTIAL**. [Runtime delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md), [R6 UI coverage](AAOS-UI-SUITE-COVERAGE-20260923.md). |
| OP-007 | Raw-first web ingestion tests failed after product behavior changed because they still stubbed retired `convert_url` behavior and attempted live example URLs. Screenshot capture also treated a parent process exit code `0` as success before its child wrote a PNG. | Verify the test seam writes a raw original through `RawAssetStore`, and require a non-empty screenshot file before success. | Preserve raw-first production behavior, keep `SafeHTTP` unchanged, and fail closed after bounded readiness polling. | **LOCAL REGRESSION COVERAGE EXISTS; exact-SHA qualification OPEN**. [Execution log](../truth/EXECUTION_STATUS_LOG.md). |
| OP-008 | Repository cleanup has repeatedly risked deleting useful runtime/build/worktree data. `.playwright-cli/`, `.hermes/`, `src-tauri/target`, Green `data` and Git objects have different ownership and retention rules. | Classify one exact path by owner, data class, process/worktree dependency and consumer before any action. | Follow current directory/project authority and exact-path migration/deletion gates. | **HISTORICAL SAFETY OBSERVATION; current boundary is in** [Directory authority](../DIRECTORY_AUTHORITY_INDEX.md) **and** [AGENTS](../../AGENTS.md). The normalization record is a frozen dated snapshot. |
| OP-009 | Authority links can resolve while their factual text is stale. The static index tests pass, but the prior Current Reality CI baseline stopped at `db13d056`; this archive and the current record now route to `9217c510` and its unresolved repair. | Run local-link resolution for every `*index*.md`, then compare each current-state CI/Green claim to its named receipt. | Keep a single current record, append chronology rather than rewriting history, and add a regression whenever a new authority entry is introduced. | **LINKS VERIFIED; factual reconciliation PARTIAL**. [Documentation authority](../DOCUMENTATION_AUTHORITY_INDEX.md), [execution log](../truth/EXECUTION_STATUS_LOG.md). |
| OP-010 | Local repository convention checks reported 44 non-Windows files as CRLF/mixed although Git objects and `.gitattributes` require LF. Root cause: the machine-wide `core.autocrlf=true` had left stale checkout bytes; Git status hid it because normalized index content still matched. | Inspect `git ls-files --eol` and `git check-attr -a -- <path>`; never normalize Windows command suffixes. | For each tracked `eol=lf` path, reject unstaged content and lone CR first, then normalize only CRLF bytes to LF. Keep `.bat`, `.cmd` and `.ps1` at their declared CRLF policy; the local repository config now fixes `core.autocrlf=false` and `core.eol=lf`; rerun the convention checker. | **LOCAL NORMALIZATION VERIFIED**. [Normalization state](REPOSITORY_NORMALIZATION_STATE_2026-09-03.md), [configuration authority](../CONFIGURATION_AUTHORITY_INDEX.md). |

## Non-negotiable boundaries

- No new version, tag, installer or GitHub Release for this maintenance work.
- Do not inspect, copy, move, delete or clean `ArcheAxis.Knowledge.Green-x64/data`.
- The vNext Rust Core is the canonical writer for its separate vNext database.
  Never dual-write legacy truth; legacy migration and Green/data operations
  remain gated by current R6 authority and applicable Owner decisions.
- Shared tool/model libraries are inputs to explicit preflight, not proof that
  a pipeline or installed runtime has passed.

## Evidence and archive routing

- Current facts and gates: [R6 execution](R6-EXECUTION.md), [R6 state](R6-STATE.json), and [M0 direction](M0-DIRECTION-OVERRIDE-20260920.md).
- Dated 2026-09-04 facts: [Current Reality](CURRENT_REALITY_2026-09-01.md) and the [G0 gap snapshot](AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md).
- Chronology and prior root-cause detail: [Execution status log](../truth/EXECUTION_STATUS_LOG.md).
- Historical handoffs remain history; do not move them until the directory
  authority and a hash/reference-compatible migration permit it.
