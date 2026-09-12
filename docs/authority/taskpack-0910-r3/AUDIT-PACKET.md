# Online audit packet — ArcheAxis Knowledge, 0910 taskpack

> 中文说明：本文件是给**只能看到仓库内容**的线上审计者准备的单一入口。它只写**实测过的数字**，
> 并明确标出哪些主张**无法只靠仓库复核**、需要什么才能复核。权威状态仍在 `EXECUTION.md`（台账）
> 与 `STATE.json`；本文件是这三者的索引与摘要，不是新的权威。

Audience: an auditor reading **only this repository** — a cloned checkout, no access to the
executor's machine, its ignored receipts, or its shell history. Every number below was measured;
where a measurement could not be reproduced from tracked files, that is said explicitly rather
than glossed over.

## 1. How to use this file

1. Read §2 for what the pack asked for and where each slice stands.
2. Run §3 — four commands, roughly five minutes — and compare against the expected results there.
3. Read §5 before believing any claim: it lists what the repository alone can and cannot prove.
4. Read §6 for the limitations already known and recorded, and §7 for the claims the executor
   **overturned against themselves** during this work.

## 2. What this repository is, and where the pack stands

The product is a local-first knowledge and learning workspace: a **Rust Core** that owns the SQLite
database and is its only writer, **isolated Python workers** talking to it through a stdio NDJSON
protocol, a thin C#/Avalonia desktop shell, and project-side surfaces added during this work (a host
panel, an MCP server, a candidate-bundle builder, a folder-ingestion driver). Nothing here calls
out to the network at runtime.

| Slice | Status | What actually holds it open |
| --- | --- | --- |
| R00–R09, R11 | IMPLEMENTED_PENDING_AUDIT | nothing on the executor's side; the independent audit decides |
| R10 | IN_PROGRESS | mounting the panel inside the **immutable** DeepTutor host body: an owner decision |
| R12 | IN_PROGRESS | reclaiming the inert 6.877 GiB: **per-path authorization**; nothing has been deleted |
| R13 | IN_PROGRESS | installer, code signing, uninstaller, clean-machine start-up. The candidate bundle, its commit-bound digests and the stop/restore instructions landed here |
| R14, R16 | TODO | the **independent** gates. This repository prepares evidence and never signs them |
| R15 | IN_PROGRESS | the format matrix: **0 complete / 14 partial / 2 custody-only** |

## 3. Verify it yourself

### 3.1 Clone it where the measurement is valid

```bash
git clone --no-hardlinks <remote> /tmp/archeaxis-audit && cd /tmp/archeaxis-audit
```

Two things matter here, both measured: clone **outside** the repository (a checkout placed inside
`.project-local/` inherits a surrounding runtime tree and 112 legacy tests fail for that reason
alone), and use `--no-hardlinks` when the destination is on another volume (a plain `--local` clone
fails there with `Improper link`, quietly enough that a later command may run in the wrong
directory).

### 3.2 Gates

```bash
python -X utf8 scripts/check_evidence_index.py        # 17 slices, 80 tracked pointers, 3 receipts
python -X utf8 scripts/check_architecture.py
python -X utf8 scripts/check_language_boundaries.py   # DB owner = crates/ only; protocol major 1
python -X utf8 scripts/check_path_conventions.py      # 1723/1792 owned (96.15%), 69 unowned recorded
python -X utf8 scripts/check_worker_reachability.py   # 12 workers, 10 routed, 2 exempted with a reason
python -X utf8 scripts/check_format_matrix.py         # 0 complete / 14 partial / 2 custody-only
python -X utf8 scripts/check_taskpack_integrity.py    # see the caveat below
python -X utf8 scripts/check_repository_conventions.py --source worktree
```

Six of those exit 0 **from a clone**. `check_taskpack_integrity.py` exits 1 there **by design**: it
attributes the two live progress files against the install snapshot under
`.project-local/runs/taskpack-0910-shipped/`, which is an ignored receipt no clone has, and it
refuses to attribute the divergence rather than guessing. `check_repository_conventions.py` reports
**exactly two lines** — two frozen pack JSON files without a trailing newline — and that is its
steady state, not a new defect.

### 3.3 The recorded commands, executed

```bash
python -X utf8 scripts/check_evidence_commands.py                 # lists all 21, runs none
python -X utf8 scripts/check_evidence_commands.py --run --execute-heavy   # runs all 21
```

| Environment | Result |
| --- | --- |
| this working tree, toolchain present | **20 PASS / 1 NOT_RUN / 0 FAIL** (the one not-run is the bundle builder refusing a dirty tree by design) |
| a fresh clone | **7 PASS / 13 NOT_RUN / 0 FAIL** — every skip names a prerequisite: nothing built yet, no Rust toolchain, no install snapshot |

A command that is not run is never counted as a pass, and a placeholder command (`<bundle>`) is
never executed. The Rust commands need **three** environment variables —
`ARCHEAXIS_MSVC_VCVARS`, `ARCHEAXIS_RUST_TOOLCHAINS`, `ARCHEAXIS_PYTHON`; without the third, the
worker-backed tests panic inside cargo with `expect("use project dev.py")`.

### 3.4 The two suites

```bash
scripts/ci/cargo_test.bat --workspace --offline                    # Rust
python -X utf8 scripts/runtime/dev.py --pytest tests -q            # Python
```

| Suite | This working tree | A clone outside the repository |
| --- | --- | --- |
| Rust workspace | 77 groups, **180 passed, 0 failed** | 77 groups, **180 passed, 0 failed** (built there from scratch) |
| Python suite | **2623 passed, 7 skipped, 0 failed** | **2599 passed, 31 skipped, 0 failed** |

Skips are not decoration: in a clone, `tools/tesseract/tessdata/` does not exist because it is
**gitignored by design** (`.gitignore:48`), so the OCR-dependent Python tests skip and three
OCR-dependent Rust tests print a reason and return early. **cargo counts an early return as
passed** — so "180 passed" in such a checkout means "nothing failed", not "OCR ran". Run it with
`-- --nocapture` to see the reason.

## 4. What was delivered here, commit by commit

**Capability (eight slices):** the unseen-example evaluation R11 owed, including two real defects
the full suite found (`240485a`); a **real MCP client** driving a project-side MCP surface that
exposes four tools and **no human review action** (`4d7e0bd`); the **PDF reading order**, decided
and reported, allowed only to reorder (`f65f13d`); the **candidate bundle that verifies itself**,
bound to a commit by digest (`4e548bc`); the **OCR reading order**, which needed a *split* along the
gutter rather than a sort (`807bbb8`); the cross-format finding escalated as one decision instead of
five format fixes (`dc03f66`); the **fresh-checkout verification** (`87675e9`); and **folder
ingestion** with a resumable JSONL manifest (`dc7f3f8`).

**Verification work (six rounds, no product code):** the consolidated summary (`7752d04`); the
first **execution** of every recorded evidence command, which found two defects (`adc49dc`); that
audit becoming a tracked checker (`b81c789`, `ab8570f`); the checker learning to report a **missing
prerequisite instead of a failure** (`8f63d9f`); the correction of the executor's own clone
conclusion (`4ae8431`); the last clone failure becoming a **named skip** (`08f4c40`); the Rust
suite verified in a clone plus the declared traineddata prerequisite (`46de83e`); the summary
extended to cover those rounds (`96b649e`); and the newest probe wired into the recorded commands
(`c789192`).

The ledger `EXECUTION.md` carries **91 rows**, one per work unit, each with its commands, its
receipts and its limitations. The evidence index carries **80 tracked pointers** so a fresh
checkout can re-check every slice, plus **3 receipts** that are ignored and therefore pointers
rather than evidence.

## 5. What the repository alone can and cannot prove

| Claim | Provable from the repository? | How, or what is missing |
| --- | --- | --- |
| The gates pass | **Yes**, six of seven from a clone | §3.2; the seventh needs the ignored install snapshot |
| The recorded commands run | **Yes**, the ones whose prerequisites are present | §3.3; each skip names what was missing |
| The Rust suite passes | **Yes** | §3.4, including a clone built from scratch |
| The Python suite passes | **Yes, minus documented skips** | §3.4; OCR tests skip without the gitignored traineddata |
| OCR actually recognised text | **Only partly** | the engine and the traineddata are local; the receipts are ignored logs |
| A capability's *quality* | **No** | quality needs human truth pairs; no accuracy claim is made anywhere |
| The 6.877 GiB reclaim | **No** | the candidates are ignored local directories; the manifest is tracked, the deletion is not authorised |
| The install snapshot attribution | **No** | the snapshot is an ignored receipt; the gate refuses rather than guessing |
| CI (GitHub Actions) | **No** | CI was not run during this work, and no CI receipt is claimed |

Receipts written to `.project-local/runs/` are **ignored by design** and are therefore **not
online**: an auditor sees them only as pointers in `R14-EVIDENCE-INDEX.json`, and re-derives the
numbers by running the commands above.

## 6. Known limitations, recorded rather than hidden

- **Pack integrity** cannot be verified in a clone (ignored install snapshot); the gate exits 1 and
  says why.
- **OCR evidence** can only be produced where `tools/tesseract/tessdata/` is installed (gitignored);
  elsewhere 3 Rust tests early-return and 24 Python tests skip.
- **69 tracked paths (3.85%) have no owner** in `DIRECTORY_AUTHORITY.yaml`; they are listed in
  `R15-PATH-DISPOSITION.json` and have **no write lane**. Closing that needs the protected
  governance file to change — an owner decision.
- **1246 legacy assets** (6 legacy roots) are inventoried and every one is still
  `INVENTORIED_NOT_SEMANTICALLY_REVIEWED`; no root may claim absorption.
- **The format matrix has zero complete groups**: 14 partial, 2 custody-only (legacy binary Office
  and professional formats).
- **`.hermes`** (≈42.9 GiB, 718k files per the R12 census) is read-only legacy, untracked, and
  untouched; **nothing has been deleted anywhere** in this work.
- **No accuracy or training claim** is made. Recogniser confidence is a review aid, the search
  receipt explicitly says a task receipt is a measurement fact, and the unseen evaluation signs no
  PASS for retrieval.

## 7. Claims the executor made and then overturned

Kept here on purpose: an auditor should calibrate trust on the corrections, not only on the
successes.

1. **"A clone runs the Python suite green."** Asserted for several rounds; it had been measured in
   the working tree. In a clone it was 2599 passed / 1 failed, and the one failure was a test whose
   subject cannot exist without the ignored install snapshot — now a **named skip**.
2. **"The 112 clone failures come from untracked local test assets."** Wrong. Round 99 cloned the
   same commit **outside** the repository and measured 2599 passed / 1 failed: the failures were an
   artefact of placing the clone **inside** `.project-local`, where the surrounding runtime tree
   answers the legacy path lookups.
3. **"The cargo commands need two environment variables."** They need three: without
   `ARCHEAXIS_PYTHON` the worker-backed tests panic, which briefly read as a regression in three
   packages that pass cleanly once it is set.
4. **"The unseen evaluation is unseen."** It had been destroyed by this repository's own
   documentation: a ledger row and a handoff section quoted two held-out values, and the probe
   counted its **own source file** as a tracked file. The corpus was rotated, the values were
   removed from every tracked document, and the test suite now enforces the property.

## 8. Open items, each needing an owner decision

1. **Structure addressing** — should `archeaxis.worker-response/v1` carry a second addressing kind
   (page, slide, sheet, node, cue) beside the canonical line anchors the Core validates today? One
   decision unblocks **five** matrix rows (F05, F07, F08, F09, F12).
2. **R12** — per-path authorisation to delete the inert 6.877 GiB (root `target/` and
   `.project-local/cache`); the manifest already lists the post-deletion checks.
3. **R10** — mount the project-side panel inside the external DeepTutor body.
4. **R14/R16** — run the independent audits.
5. **R13** — installer, code signing, uninstaller, clean-machine start-up.
6. **F02/F03** — fetching a URL means reaching the network on purpose: a policy decision, today
   recorded as "only a saved snapshot can be read".

## 9. Where the detail lives (all tracked)

| File | What it holds |
| --- | --- |
| `EXECUTION.md` | the ledger: 91 rows, each with commands, receipts, limitations and rollback |
| `STATE.json` | per-slice status and the evidence narrative behind it |
| `HANDOFF-2026-09-11.md` | the consolidated summary, the verification recipe and the lessons |
| `R14-EVIDENCE-INDEX.json` | 17 slices, 80 tracked pointers, 3 receipts, and each slice's limitations |
| `R15-FORMAT-STATUS.json` | the 16 format groups, their status and their named gaps |
| `R15-PATH-DISPOSITION.json` | the path measurement at its own commit: 96.15% owned, the 69 listed, the legacy inventory |
| `WORKER-REACHABILITY.json` | every capability worker, routed or exempted with a recorded reason |
| the checkers themselves | `scripts/check_*.py`, and `scripts/check_evidence_commands.py` which runs the recorded commands |

Authority note: `EXECUTION.md` + `STATE.json` are the live record; this packet, like the handoff,
is an index into them and adds no authority of its own.
