# Package status — ARCHEAXIS-NEXT-TASKPACK-2026-09-10

Status: **INSTALLED AND VERIFIED** (2026-09-11).

## Provenance

| Item | Value |
| --- | --- |
| Owner-supplied archive | `D:\All projects\ARCHEAXIS-NEXT-TASKPACK-2026-09-10.zip` (109,438 bytes) |
| Definition copy | `D:\All projects\ARCHEAXIS-NEXT-TASKPACK-2026-09-10.md`, 12,830 bytes, sha256 prefix `50ab667a85dddf61` |
| Installed at | `docs/authority/taskpack-0910-r3/` (single level, 24 files) |
| Reference snapshot | `reference-r2/` — 15 inherited R2 files, read-only historical material, not a second active plan |
| Package revision | R3.1, 17 slices R00–R16 |

`TASKPACK.md` here is byte-identical to the owner-supplied definition
(12,830 bytes, same sha256 prefix).

## Verification

```
python -X utf8 docs/authority/taskpack-0910-r3/verify_package.py
PASS: hashes, 17 task dependencies, all 23 original tasks retained
exit 0
```

UTF-8 mode is required on this machine: the verifier calls
`Path.read_text()` without an explicit encoding and the Windows locale here
defaults to GBK, which fails on the UTF-8 `TASKS.json`
(`UnicodeDecodeError: 'gbk' codec can't decode byte 0x80`). The frozen package
file was **not** modified; the encoding is supplied by the interpreter mode.

Verification scope and semantics: `MANIFEST.json` hashes 23 files, and that set
**includes `EXECUTION.md` and `STATE.json`**, which the package itself designates
as the progress files (`进度写 EXECUTION.md 及 STATE.json`). The integrity check
therefore applies to the **as-shipped** package state: it passed at install time
(exit 0, above). After progress is recorded, a re-run reports exactly those two
progress files as changed - by design, not as tampering.

Reproduction without the owner ZIP: the as-shipped bytes are preserved at
`.project-local/runs/taskpack-0910-shipped/` (ignored), and their sha256 values
match the manifest entries (`EXECUTION.md 67bc856eaf0a`, `STATE.json
e4f5e42013d4`); the other 21 files still match in place.

Package verification proves file integrity and dependency validity only. It is
not a product audit or an implementation claim.

## Registration

- Active entry: `docs/authority/taskpack-0910-r3/EXECUTION.md`; slice progress
  in `STATE.json`; `TASKS.json` stays the frozen plan definition.
- SUP-018 in `DECISION_SUPERSESSION_LEDGER.yaml` records the supersession of the
  R3-0908 active-plan status (historical receipts unchanged).
- `AGENTS.md` §6, `docs/DOCUMENTATION_AUTHORITY_INDEX.md` and
  `docs/CONFIGURATION_AUTHORITY_INDEX.md` resolve to this entry.
- Intake note: `workspace/intake/2026-09-10-next-taskpack-0910.md`.
- Baseline review at registration: `R00-BASELINE-REVIEW.md`.

## Boundaries honoured during install

No product code changed, no Windows cleanup, no `.hermes` access, no E: access,
no credentials used, no publishing.
