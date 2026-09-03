# Operational Issue Archive — 2026-09-04

> Current triage record for failures that are likely to recur. This is not a
> release record, a runtime receipt, or permission to clean/move data. Each row
> names the authoritative evidence record and preserves `OPEN`, `PARTIAL`, or
> historical status rather than converting diagnosis into completion.

## Use this first

1. Confirm the path, SHA, process and evidence layer before changing anything.
2. Find the matching issue below; execute only its stated first diagnostic.
3. Read the linked authority record before a repair, migration, cleanup or
   delivery claim.
4. Record a new observation in the append-only execution log; do not rewrite
   historical failures.

## Active issues

| ID | Symptom and confirmed root cause | First safe diagnostic | Required durable remedy / evidence | Status and authority |
| --- | --- | --- | --- | --- |
| OP-001 | Exact SHA `9217c510` CI `33667525835` failed fail-closed. Lint found an unannotated legacy-name occurrence and four generated schema files without final LF. Wheel smoke's fake `tesseract` emitted no version string; the OCR resolver correctly rejected it, returning an error object rather than `text`. The corrective SHA `af216e3` run `33786524094` passed its selected gates. | Read the exact SHA and job conclusions; distinguish the corrected selected-gate result from skipped qualification jobs. | Retain the OCR identity regression, then bind a manually/full-selected exact-SHA result to browser, Windows, wheel, installer, compatibility and format gates. | **FAST REPAIR VERIFIED; FULL QUALIFICATION OPEN**. [Current Reality](CURRENT_REALITY_2026-09-01.md), [G0 gaps](AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md). |
| OP-002 | A successful path-selected CI or a local suite was previously treated as a broad qualification signal. It is not: skipped, failed or unbound jobs cannot prove Windows, browser, wheel, installer or all-format behavior. | Read the exact SHA and individual job conclusions; distinguish `skipped`, `success`, `failure` and `not run`. | One exact-SHA full-qualification receipt with required jobs explicitly concluded; preserve failures as evidence. | **OPEN**. [G0 gaps](AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md). |
| OP-003 | Multi-format proof has been narrowed accidentally to PDF. The fixture set includes web, screenshot OCR, image, TXT/MD, DOCX/PPTX/XLSX, PDF native/scanned, Canvas, WAV and MP4, but an installed all-format journey is not yet proven. | Start from the Golden corpus manifest and verify rights class plus raw SHA before conversion. | For each format retain raw asset, conversion/anchor, retry or rejected-write behavior and fresh/existing workspace readback; use local engines/models first and GPT only for final audit comparison. | **PARTIAL**. [Golden corpus plan](AXM_G0_GOLDEN_CORPUS_PLAN_2026-09-02.md), [G0 gaps](AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md). |
| OP-004 | Windows build failures were caused by toolchain environment assembly, not Rust source: MSVC `cl.exe` was absent until the VS developer environment was loaded, and a batch `%PATH%` expansion before `VsDevCmd` discarded the loaded path. | In PowerShell 7, preflight the shared Rust, Cargo and VS developer environment before invoking a build; do not assume PATH inheritance. | Keep the toolchain setup explicit and record the command/environment boundary in project-local evidence. A successful build still needs separate Green runtime evidence. | **RECURRENCE PREVENTED IN BUILD PATH; runtime remains PARTIAL**. [Runtime delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md), [execution log](../truth/EXECUTION_STATUS_LOG.md). |
| OP-005 | Silent Green startup has not been qualified. Windows Script Host errors (`800A0408` invalid character and a path interpreted as `D:\\All` without a file extension) show an argument/quoting boundary failure, not a frontend capability failure. | Read the exact `启动星环知识.vbs` contents and its caller argument construction without launching desktop automation or touching Green `data`. | Add a regression for paths containing spaces; invoke only through the VBS route, then record executable path, API/status and user-visible result. | **OPEN**. [Runtime delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md), [Current Reality](CURRENT_REALITY_2026-09-01.md). |
| OP-006 | UI drift was caused by stale source/token and loading assumptions: obsolete Linear-style purple values, network font import and an unstyled command-palette backdrop conflicted with the offline black/white baseline. A browser/source check does not prove the Tauri/Green WebView loaded the same assets. | Check the canonical `frontend/` source and the exact built asset path before changing CSS; do not infer runtime state from an old window or fallback page. | Keep black/white dark as the default, retain semantic status colors and reduced-motion behavior, and bind any Green visual claim to the deployed executable/product path. | **SOURCE FIXED; GREEN RUNTIME PARTIAL**. [UI roadmap](UI_V3_PRODUCT_ROADMAP.md), [Current Reality](CURRENT_REALITY_2026-09-01.md). |
| OP-007 | Raw-first web ingestion tests failed after product behavior changed because they still stubbed retired `convert_url` behavior and attempted live example URLs. Screenshot capture also treated a parent process exit code `0` as success before its child wrote a PNG. | Verify the test seam writes a raw original through `RawAssetStore`, and require a non-empty screenshot file before success. | Preserve raw-first production behavior, keep `SafeHTTP` unchanged, and fail closed after bounded readiness polling. | **LOCAL REGRESSION COVERAGE EXISTS; exact-SHA qualification OPEN**. [Execution log](../truth/EXECUTION_STATUS_LOG.md). |
| OP-008 | Repository cleanup has repeatedly risked deleting useful runtime/build/worktree data. `.playwright-cli/` was a verified two-file transient residue; `.hermes/`, `src-tauri/target`, Green `data` and Git objects are not equivalent cleanup targets. | Classify one exact path by owner, data class, process/worktree dependency and consumer before any action. | Only remove verified transient paths with pre/post conditions; directory moves require AX-DIR-010 inventory, compatibility tests, rollback and explicit deletion authorization. | **ACTIVE SAFETY BOUNDARY**. [Normalization state](REPOSITORY_NORMALIZATION_STATE_2026-09-03.md), [Directory authority](../DIRECTORY_AUTHORITY_INDEX.md). |
| OP-009 | Authority links can resolve while their factual text is stale. The static index tests pass, but the prior Current Reality CI baseline stopped at `db13d056`; this archive and the current record now route to `9217c510` and its unresolved repair. | Run local-link resolution for every `*index*.md`, then compare each current-state CI/Green claim to its named receipt. | Keep a single current record, append chronology rather than rewriting history, and add a regression whenever a new authority entry is introduced. | **LINKS VERIFIED; factual reconciliation PARTIAL**. [Documentation authority](../DOCUMENTATION_AUTHORITY_INDEX.md), [execution log](../truth/EXECUTION_STATUS_LOG.md). |
| OP-010 | Local repository convention checks reported 44 non-Windows files as CRLF/mixed although Git objects and `.gitattributes` require LF. Root cause: the machine-wide `core.autocrlf=true` had left stale checkout bytes; Git status hid it because normalized index content still matched. | Inspect `git ls-files --eol` and `git check-attr -a -- <path>`; never normalize Windows command suffixes. | For each tracked `eol=lf` path, reject unstaged content and lone CR first, then normalize only CRLF bytes to LF. Keep `.bat`, `.cmd` and `.ps1` at their declared CRLF policy; the local repository config now fixes `core.autocrlf=false` and `core.eol=lf`; rerun the convention checker. | **LOCAL NORMALIZATION VERIFIED**. [Normalization state](REPOSITORY_NORMALIZATION_STATE_2026-09-03.md), [configuration authority](../CONFIGURATION_AUTHORITY_INDEX.md). |

## Non-negotiable boundaries

- No new version, tag, installer or GitHub Release for this maintenance work.
- Do not inspect, copy, move, delete or clean `ArcheAxis.Knowledge.Green-x64/data`.
- Do not make Rust a production writer or start a directory move before every
  named G0 and AX-DIR prerequisite is closed.
- Shared tool/model libraries are inputs to explicit preflight, not proof that
  a pipeline or installed runtime has passed.

## Evidence and archive routing

- Current facts: [Current Reality](CURRENT_REALITY_2026-09-01.md).
- Gate status: [G0 evidence gaps](AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md).
- Chronology and prior root-cause detail: [Execution status log](../truth/EXECUTION_STATUS_LOG.md).
- Historical handoffs remain history; do not move them until the directory
  authority and a hash/reference-compatible migration permit it.
