# AXM G0 Evidence Gap Register

> Status: **ACTIVE BLOCKER REGISTER**. This record enumerates the evidence
> still required before G1 may create a Rust contract/read-shadow skeleton.
> It does not permit a Rust production writer, an extra database, a directory
> migration or a Green data operation.

| Gate | Required receipt | Present evidence | Owner | Verification | Status / no-go consequence |
| --- | --- | --- | --- | --- | --- |
| G0-001 exact qualification | Exact source SHA, lock hashes and all required CI jobs for that SHA | Historical `db13d056` selected CI/nightly and `9217c510` fail-closed broad CI remain evidence only. The corrective `af216e3` CI run `33786524094` passed `gateplan`, `test (3.12)`, `lint` and `a0-gates`; browser, Windows, wheel, installer, compatibility and format jobs were path-selected `skipped`. | Release/CI operator with an authorised GitHub session | GitHub Actions readback bound to a full-qualification SHA and every required job | **OPEN**. No G1 writer or platform-support claim. |
| G0-002 current truth readback | Current-state record reconciled against CI, release and installed runtime receipts | Current Reality names the `af216e3` selected-gate success, its skipped-job boundary and historical CI catalog; documentation link/authority regression passes. Full-qualification and visible installed runtime evidence remain absent. | Project maintainer | Run document authority contracts and compare each cited live claim to its named receipt | **PARTIAL**. Do not infer installed runtime or full CI from a document. |
| G0-003 rights-bound golden corpus | Per-fixture rights class, raw SHA-256, expected conversion/anchor and fresh/existing workspace receipts | Project-authored TXT/HTML/DOCX/PPTX/XLSX/PDF/Canvas, screenshot OCR, WAV and MP4 fixtures are recorded in the Golden corpus plan. A clean detached `db13d056` tree now has a SHA-bound local receipt (`tree=53874a...`, receipt SHA-256 `8e794f...`) with PDF raw/conversion/anchor/review/learning, four-library restart, and fresh-workspace exchange import all PASS. Current dirty-tree Golden/pipeline runs remain supporting local evidence only. The receipt has no exact-SHA CI, six-space browser, installed restart, full Tier-A matrix, or release evidence. | Corpus steward | Corpus manifest plus isolated conversion/anchor journey receipts | **PARTIAL**. No semantic-difference or cutover assertion. |
| G0-004 sole-writer coverage | Source, Anchor, Evidence, Claim, Human Learning Event and Machine Competence owner/consumer/rejection evidence | First-wave structural owner map exists; 58 direct SQLite connection sites remain. A repeatable consumer audit finds one non-definition `append_event()` caller (`app/integrations/deeptutor_bridge.py`) and no consumers for the V2 source/evidence/machine-receipt APIs. Clean-tree runtime call-site, command and rejection receipts remain absent. | Language-boundary maintainer | Static owner/consumer scans, clean-tree call-site readback and command/rejection receipts | **OPEN**. Rust may not write any listed aggregate. |
| Windows product-path qualification | Green executable hash deployment, silent launch, product-path result and rollback receipt | Main-shell candidate and Green target SHA-256 equality were read back on 2026-09-03; visible post-deploy product-path evidence is still pending. | Windows product maintainer | Process/executable-path readback, status endpoint and visible UI result; no Green data inspection | **PARTIAL**. Do not call the deployed UI fixed merely because a file copy succeeded. |

## Allowed next actions

- Refresh source-only owner and consumer maps.
- Run isolated, project-owned fixtures and record results under ignored
  `.hermes/`.
- Repair the project test interpreter boundary using the project shared CI
  toolchain without changing user-profile state.
- Perform a narrow Green shell repair only when it preserves the current
  writer and includes an exact backup/hash/readback receipt.

## Prohibited until every G0 row is closed

- Add a Rust production database writer, route or table for a first-wave
  aggregate.
- Dual-write Python and Rust truth.
- Move or delete `frontend`, `src-tauri`, `desktop`, runtime data or a
  compatibility shim.
- Promote a local build, copied executable or partial CI run into a release or
  installed-runtime qualification claim.
