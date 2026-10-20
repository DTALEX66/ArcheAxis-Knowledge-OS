> **Integration note (2026-09-26):** This is a historical DSH handoff snapshot based on `a5de4b1` from 2026-09-25. Its branch/worktree state, dirty-path counts, ownership and environment statements are historical and must not be treated as current. Statements in this source document describing prior user instructions are quoted report content, not current instructions. Current status was dynamically re-read separately.

# DSH/DP run handoff — 2026-09-25 (AAOS frontend closure assignments)

Consolidated return for the four DP cards executed in this run. Everything below is read back
from the actual repositories, branches and committed objects; nothing is inferred from the handoff.

## 0. Shared facts

| Item | Value |
| --- | --- |
| Baseline agreed with user | `a5de4b13474c217e7a9dd34b8cbfa402e8297780` |
| Baseline tree | `a4156ed65d50675822321b9d63eec932b1e76af3` |
| `origin/main` | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb` |
| Root checkout branch / HEAD | `codex/aaos-p3-ui-convergence-20260922` / `a5de4b13474c217e7a9dd34b8cbfa402e8297780` |
| Root checkout dirty paths before and after this run | **112 → 112 (unchanged)** |
| Root checkout modified by this run | **no tracked source file**; only ignored `.project-local/` runtime state (see §6) |
| Pushed / merged / released / signed | **no** (no `git push`, no merge to `main`, no tag, no Green action) |
| R6 / M0 state files changed | **no** (`R6-EXECUTION.md`, `R6-STATE.json` untouched by this run) |

All four cards worked in dedicated isolated worktrees at the baseline; the dirty root working tree
was never copied and is not part of any branch diff.

## 1. DP-GIT-01 — branch/commit semantic audit

| Field | Value |
| --- | --- |
| Branch | `codex/dp-git-01-20260925` |
| Worktree | `.project-local/worktrees/dp-git-01-20260925` |
| Baseline SHA / tree | `a5de4b13474c217e7a9dd34b8cbfa402e8297780` / `a4156ed65d50675822321b9d63eec932b1e76af3` |
| Tip SHA | `b9466375c3dffd5bbb7335839dd2f0478a34959f` is the **audit commit**. This branch additionally carries only report-only commits for this handoff; read the exact final tip with `git rev-parse codex/dp-git-01-20260925` |
| Tip tree | read with `git rev-parse codex/dp-git-01-20260925^{tree}`; the audit-only tree was `14959d3e708ac9655e1ec3fe422c465923b5a409` |
| Commits | report-artifact commits only — the batch-01 audit plus handoff text; **no product source**. The exact count drifts whenever this self-describing file is amended, so root should read `git rev-list --count <baseline>..codex/dp-git-01-20260925` rather than trust a number written here |

> Note on tip drift: this handoff is itself committed on the branch it describes, and this
> paragraph was amended once after publication to correct a stale commit count. Every revision
> touches only files under `docs/current/dsh-review/`. The audit commit `b9466375` and its tree
> are immutable; no other claim in this document is affected and no product file is involved.

**Changed paths (exactly two, both new):**

- `docs/current/dsh-review/branch-batch-01.md` — blob `c9bf21a598bf9ed585bf743de019840355929f48`, 33821 bytes
- `docs/current/dsh-review/branch-batch-01.json` — blob `6bd67b3d611094b7ff4b01a0dedbd8dd543dcb5b`, 47820 bytes

**Coverage:** 7 branches, **17 SHAs** (batch cap 20), 88 changed-file records.
Decisions: `SUPERSEDED` 16, `CONFLICT` 1 (`4e1a3ed8` portable-data-root), `CHERRY_PICK_CANDIDATE` 0, `KEEP` 0, `UNKNOWN` 0.
File-level: 28 absent from baseline, 5 byte-identical, 55 evolved.

**Commands / results**

| Command | Result |
| --- | --- |
| `git rev-list --reverse --no-merges <merge-base>..<branch>` (×7) | 17 distinct SHAs enumerated; every ref resolved |
| `git diff-tree --numstat -r -M <sha>` | 88 path/add/delete records captured |
| `git cat-file -e <baseline>:<path>` + `git rev-parse` blob comparison | membership/identity for all 88 records |
| `.project-local/dsh-audit/scripts/audit_verify.ps1` | `checked_shas=17 checked_paths=88 errors=0` → `ALL_CLAIMS_VERIFIED_AGAINST_GIT` |
| `json.load` on the report | strict parse OK, 17 commits |
| `git diff --check` in the worktree | exit 0 |

**Key audit outcome:** none of the seven priority branches is a port candidate. Each is a
historical absorption donor whose content is already resident in the baseline in equal or stronger
form — 5 files are byte-identical (including `tests/test_workspace_evidence_anchor_api.py` and
`tests/test_gateway_rate_limit.py`) and 20+ were later evolved. Staleness has two causes: the
removal of the legacy FastAPI-served web UI in favour of the C#/Avalonia shell, and the
`COGNITIVE_*`/`.hermes` → `ARCHEAXIS_*`/`.project-local` migration recorded in
`NAMING_CONTRACT_V2` §2 and `AGENTS.md` §3.

**Self-correction (disclosed):** the first collected facts file tested baseline membership with
`git rev-parse <tree>:<path>`, which echoes its argument on stdout even when it fails, yielding
20 absent / 6 identical / 63 evolved. The independent claim verifier caught it; membership was
recomputed from `git cat-file -e` exit status and all report counts were corrected to
28 / 5 / 55. The report records this finding.

## 2. DP-A11 — Research contract gap analysis

| Field | Value |
| --- | --- |
| Branch | `codex/dp-a11-20260925` |
| Worktree | `.project-local/worktrees/dp-a11-20260925` |
| Tip SHA | `64650b2b68445a8113de3591578a405f4f4289d4` |
| Tip tree | `214a6d1db74379c0c50ca5b46e214ad1fb3d8850` |
| Commits | 1 (report-only) |

**Changed path:** `docs/current/dsh-review/research-contract-gap.md` — blob `952e8d7cf036…`, 16818 bytes.

**Label:** `PROPOSAL / OWNER REVIEW REQUIRED` — not an adopted contract; no source, schema, route
or UI changed; Research stays unavailable.

**Findings (all cited to the current tree):**

- The derived-projection contract requires a per-item `source_revision` (`app/contracts/derived_projection_v1.py:13`), but the canonical `transforms` table has no revision column (`crates/archeaxis-store-sqlite/src/lib.rs:31-37`).
- A revision **is** derivable: `sources.sha256` (`…/lib.rs:15`), and the Core already uses exactly that value as the anchor revision for source-bound Candidates (`crates/archeaxis-domain/src/knowledge.rs:216`, reading `sources.sha256` via a `jobs → sources → transforms` join at `…/knowledge.rs:190-196`).
- No read route exposes a revision for a result set: `/api/v1/search` transform items carry only `transform_id`, `source_id`, `engine`, `head` (`crates/archeaxis-api/src/lib.rs:1430-1449`, `crates/archeaxis-domain/src/search.rs:76-91`). Only `/api/v1/evidence/anchors` exposes `source_revision`, per anchor (`crates/archeaxis-api/src/lib.rs:826-841`).
- Provider/version identity does not exist anywhere (no version column; `engine` is free text), and the provider lifecycle remains `BLOCKED_BY_AUTHORITY_DECISION` (R6 P0-H01).
- Quality/loss facts **are** persisted (`jobs.loss_receipt`, validated at `crates/archeaxis-application/src/jobs.rs:100-102`) but are not projected by any runtime route.
- There is no Research route at all (`crates/archeaxis-api/src/lib.rs:40-77`); `research` appears only as a V3 `source_type` value and a vocabulary constant.
- Proposal: one additive read-only projection reusing `archeaxis.derived-projection/v1`, deriving `source_revision` from `sources.sha256`, with explicit empty/404/400/stale/error semantics and **no** schema bump. Five owner decisions (D1–D5) are listed in the note.

**Verification:** every `file:line` citation re-checked with `Select-String` against the tree
(8/8 exact matches after two corrections — `jobs` DDL, the JOBS insert/update lines, and the
router span); `git diff --check` exit 0. No test was run — this is a citation-only read.

## 3. DP-UI-01 — native GUI acceptance

| Field | Value |
| --- | --- |
| Branch | `codex/dp-ui-01-20260925` |
| Worktree | `.project-local/worktrees/dp-ui-01-20260925` |
| Tip SHA | `6fb31ad32b7e5ddb35ec23fa707fa8c3fe422ff2` |
| Tip tree | `bfa891aad6621b0fd5f362a35b4a4f3060a2aacf` |
| Commits | 1 (report-only) |

**Changed path:** `docs/current/dsh-review/dp-ui-01-readiness.md` — blob `ccf7601fa131…`, 6922 bytes.

**Status: `BLOCKED` / `NOT_EXECUTED`.** The exact current-source Candidate, manifest SHA, source
snapshot SHA, Desktop/Core executable hashes, isolated run instructions and baseline exact tree
were **not supplied**, and the user instructed this run to wait for the current-tree Candidate.
Per the card, no substitute was used: the stale committed-HEAD Candidate
(`…Green-va5de4b13-x64`) and the dirty root executable were deliberately **not** launched.

Path-level readback (no contents inspected, nothing run, nothing modified): the four
`ArcheAxis.Knowledge.Green-vcurrent*` directories are **incomplete** — none contains
`manifest.json`, `ArcheAxis.Desktop.exe` or `archeaxis-api.exe` (21363 / 21363 / 6412 / 6412 files
respectively). They are root-side work in progress and were left untouched.

All 15 acceptance-matrix rows (16 routes, menus, Ctrl+K, Ctrl+Alt+I/J, keyboard traversal, IME,
UIA names/state, error states, screenshots, 6 logical widths, 4 scaling percentages,
screen-reader) are recorded `NOT_EXECUTED`. **DP-UI-02 was not started** — it requires a
DP-UI-01 receipt naming a reproducible defect plus a root-assigned write-set, neither of which exists.

## 4. DP-F01 — real text quality roundtrip

| Field | Value |
| --- | --- |
| Branch | `codex/dp-f01-20260925` |
| Worktree | `.project-local/worktrees/dp-f01-20260925` |
| Tip SHA | `56a76411624e450f2ecf50afdca070babe983cef` |
| Tip tree | `53799bb62910a39efe3b8d49431d6a702b0ee1aa` |
| Commits | 1 |

**Changed paths (8 new files, +5979; no production file):**

- `crates/archeaxis-api/tests/f01_quality_roundtrip.rs` (566 lines)
- `tests/workers/test_f01_real_quality.py` (333 lines)
- `tests/fixtures/f01-quality/controlled.md`, `capped-lines.md`, `fallback-gbk.txt`, `ragged.csv`, `unsupported.unknown-ext`, `manifest.yaml`

`services/python-workers/document/worker_text.py` is **byte-identical to baseline**
(`0de393b96a3afbf45c6527b1bedde8bb6512a1d2` both sides) — no failing assertion demonstrated a
product defect, so the optional narrow fix was correctly not applied.

**Commands / results**

| Lane | Command | Result |
| --- | --- | --- |
| Python (delegated) | `<venv-aaos-ui-312 python> -B -m pytest -p no:cacheprovider -p conftest_runner -q tests\workers\test_f01_real_quality.py` | **5 passed, 1 warning, exit 0** |
| Python neighbours | same + `test_text_ndjson.py test_bulk_text.py test_quality_regressions.py test_bulk_structured.py` | 58 passed, 1 warning, 77 subtests, exit 0 |
| Python (**my independent re-run**) | same interpreter, `PYTHONPATH` = worktree `.project-local/dp-f01` | **5 passed, 1 warning, exit 0** — reproduced |
| Rust | `scripts\ci\cargo_test.bat test -p archeaxis-api --test f01_quality_roundtrip --offline -- --test-threads=1` | **5 passed, 0 failed, exit 0** |
| Rust neighbours | + `job_quality` `runtime_jobs` `source_jobs_api` | 13 passed, 0 failed, exit 0 (2 pre-existing dead-code warnings) |

**RED evidence (honest):** there was no product RED. The only Python failure in the first run was
the subagent's own hand-written anchor expectation (it expected span `(9,24)`; the worker
correctly produced `(9,19)`); the Rust lane's REDs were also test-side (`sha2`/`hex` not
dev-dependencies; `transform_id` is INTEGER; `resolve_media_type` fails at claim time so HTTP
returns `409 AAK-CON-003`). All were failures of the test, not of a product contract.
The test is not a mirror of the worker: it asserts hand-measured hashes, byte lengths and
character ranges from `manifest.yaml`, plus a negative control.

**Evidence class:** `TESTED_LOCAL`. Synthetic controlled fixture only — **not** real-corpus
qualification, and it closes no P1 format.

**Core contract gap found (not fixed — a Rust production change would be out of scope):** the
runtime quality projection `GET /api/v1/jobs/{job_id}/quality`
(`crates/archeaxis-api/src/lib.rs:1457-1512`) returns only `state/engine/engine_version/coverage/
covered/total/loss_count/region_count/pages` and **drops the entire `params` object**, so
decoder-fallback and format facts (markdown headings, CSV ragged rows) are absent from it. The full
persisted receipt **is** reachable, but only through a generic byte-output route:
`GET /api/v1/jobs/:job_id/outputs/:kind` with `kind=loss_report`
(`crates/archeaxis-api/src/runtime/mod.rs:36, 291-306`), which the shipped binary serves
(`crates/archeaxis-api/src/main.rs:37`) and which returns the receipt as a **JSON string** inside
`content` — so the `archeaxis.loss-receipt/v1` schema is not applied at the API boundary. Core also
models no explicit fallback or unsupported flag; the worker records a decode fallback as a named
loss entry plus a `params` value.

> **Correction (2026-09-25, post-review).** An earlier revision of this section stated that a
> "non-runtime projections router exposes `GET /api/v1/jobs/{job_id}/outputs/loss_report`" at
> `crates/archeaxis-api/src/lib.rs:291-306`, and concluded the params were **not** reachable
> through the runtime router. Both parts were wrong: there is no `outputs` route in `lib.rs`, the
> outputs route lives in the **runtime** router (`runtime/mod.rs:36`) which the shipped binary
> mounts (`main.rs:37`), and the DP-F01 Rust test itself reads `params` successfully from
> `.../outputs/loss_report`. The verified gap is the one stated above. Full analysis and proposal:
> `docs/current/dsh-review/job-quality-projection-proposal.md`.

## 5. Full return summary — branches and SHAs

| Card | Branch | Baseline SHA | Tip SHA | Tip tree |
| --- | --- | --- | --- | --- |
| DP-GIT-01 | `codex/dp-git-01-20260925` | `a5de4b13…` | audit commit `b9466375c3dffd5bbb7335839dd2f0478a34959f`, then one report-only handoff commit; final SHA via `git rev-parse` | audit-only tree `14959d3e708ac9655e1ec3fe422c465923b5a409` |
| DP-A11 | `codex/dp-a11-20260925` | `a5de4b13…` | `64650b2b68445a8113de3591578a405f4f4289d4` | `214a6d1db74379c0c50ca5b46e214ad1fb3d8850` |
| DP-UI-01 | `codex/dp-ui-01-20260925` | `a5de4b13…` | `6fb31ad32b7e5ddb35ec23fa707fa8c3fe422ff2` | `bfa891aad6621b0fd5f362a35b4a4f3060a2aacf` |
| DP-F01 | `codex/dp-f01-20260925` | `a5de4b13…` | `793e06ee040dcdb0248e2bbb322b44084620cf17` (test commit `56a76411` + proposal commit `793e06ee`) | `5b4cc6cac55946c61fa2ec9ff87c792714407eca` |
| DP-GIT-02 (batch 02) | `codex/dp-git-02-20260925` | `a5de4b13…` | `6ca4c9cd6172ae235ad27676678860e186019ba7` | `0316a54e25c7dc5c9161295e89afd6d910bd1b61` |

All five worktrees report a clean `git status --short`. Nothing was pushed. Suggested integration
order for root: DP-GIT-01, DP-A11, DP-GIT-02 and the DP-F01 proposal are all report-only and share
only the `docs/current/dsh-review/` directory (they add distinct files, no path overlap); DP-F01
additionally adds new test/fixture paths; DP-UI-01 is a blocked-readiness report and can be taken
last or dropped.

> **Integration note.** `dp-handoff-20260925.md` is committed on `codex/dp-git-01-20260925`, and
> this correction was applied after that branch was first published. Root should integrate the
> **current tip** of each branch rather than a SHA captured from an earlier message; the audit
> commit `b9466375` and its tree are immutable, but every later commit on that branch is
> report-text only.

## 6. Unresolved items and residue

**Unresolved (product / authority):**

1. `A02` portable/shared-resource-root semantics remain an owner decision; the DP-GIT-01 audit
   records the portable-data-root branch as `CONFLICT` and does not port it.
2. Provider identity (R6 P0-H01) remains `BLOCKED_BY_AUTHORITY_DECISION`; this is why DP-A11 can
   only propose an FTS-scoped Research projection and why D3 is an owner question.
3. DP-UI-01 stays blocked until an exact current-source Candidate is supplied with manifest,
   snapshot and executable hashes and isolated run instructions.
4. The job-quality read projection gap (originally described incorrectly by DP-F01 and corrected in
   §4 above) is unfixed. A scoped proposal now exists at
   `docs/current/dsh-review/job-quality-projection-proposal.md` on `codex/dp-f01-20260925`,
   labelled `PROPOSAL / OWNER REVIEW REQUIRED`, with five owner decisions (D1–D5). It authorizes
   nothing and changes no Rust production code.
5. Mastery remains `closed=false`; no claim in this run changes any M0 P0–P6 status.
6. `DP-GIT-01` batch 02 (`docs/current/dsh-review/branch-batch-02.md` / `.json` on
   `codex/dp-git-02-20260925`) adds a verified cross-branch duplication finding: `89d8fd78`
   (`feat/h2-pipeline-integration`) and `bc4a234f` (`feat/naming-step3`) are the same 14-file
   change, so any SHA-based "unmerged work" count double-counts it.

**Residue created by this run outside the branches (all under the ignored `.project-local/`,
none in the root source tree):**

- `.project-local/dsh-audit/` — audit collectors, raw facts JSON, membership truth, and the
  finalize/verify helpers for DP-GIT-01. Evidence, not deliverables.
- `.project-local/worktrees/dp-*/` — the five isolated worktrees themselves.
- `.project-local/runs/a2d5f4b505/` — DP-F01 sandbox-probe leftovers. The delete attempts were
  **denied by this session's file sandbox** (`Remove-Item` reports non-interactive mode;
  `cmd /c rmdir` string-prefix was misinterpreted by the shell), so they remain:
  empty dirs `probe-32mu3mv9`, `p-jqr6cdr_`, `4c4eb8336a8f`, `5ff1ce7fd134`, `c32db7b7021c`,
  `e69e2287c49c`, plus a junction `dp-f01-run` →
  `.project-local/worktrees/dp-f01-20260925/data/dp-f01-runs/run-root…`.
  **Caution for whoever cleans up:** delete `dp-f01-run` as a *link only*
  (`rmdir` without `/s`, i.e. never recursively), because a recursive delete would follow it into
  the DP-F01 worktree. Other directories in that run folder did not belong to this run.
  `.project-local/worktrees/dp-f01-20260925/.project-local/` (including
  `dp-f01/conftest_runner.py`, `p-x0c618ly`, `p-kwyi6wvr`) holds the F01 test-run state.
- The F01 sandbox shim (`-p conftest_runner`) exists solely because this session denies Python
  children access to `mkdtemp` directories and to `dev.py`'s root-checkout run root. It relocates
  throwaway test state only; it changes no tracked file and no product behaviour. A Python lane
  run without that shim is expected to fail with `PermissionError` / `WinError 5` in this
  environment, not because of the tests.

## 7. Tests NOT run (explicit)

- DP-GIT-01 (batches 01–02) and DP-A11: **no tests**, by design (read-only audits and design notes).
- DP-UI-01: **no tests and no GUI run** — blocked, see §3.
- Job-quality projection proposal: **no tests** — citation-only read; the Rust/Python lanes it cites
  were executed under DP-F01, not for it.
- DP-F01: full `tests/workers` suite (`117 passed, 7 skipped, 2 failed, 5 errors`) was executed by
  the delegate and **failed on 7 pre-existing environment gaps only** (`pptx`, `fitz`/`pymupdf`,
  `openpyxl`, `docx`, missing ASR model) — not regressions, and nothing was installed.
  Full-repository pytest, `knowledge_base/tests`, the remaining ~20 Rust API targets, the rest of
  the Cargo workspace, `rustfmt`/`clippy`, and every .NET/desktop gate were **NOT EXECUTED**
  (outside the card's write-set and scope). No full product gate was run and no completion is
  claimed for R6 or M0.

## 8. Parallel run with Codex (second phase)

Codex executed its own Candidate/Task 8 work while this DP run continued. To avoid any collision,
the DP side stayed strictly inside isolated worktrees and wrote **only** new report files under
`docs/current/dsh-review/`, and it avoided the entire declared Codex write range:

| Declared Codex write range | Touched by this DP run |
| --- | --- |
| `scripts/release/` | no |
| `tests/test_candidate*`, `tests/test_green_candidate_*` | no |
| `docs/current/R6-EXECUTION.md` | no |
| `docs/current/R6-STATE.json` | no |
| `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md` | no |
| `docs/SHARED_RESOURCE_PATH_INDEX.md` | no |
| root working tree (any tracked file) | no — 112 dirty paths before and after |

Work added during the parallel phase (both read-only products):

- `codex/dp-git-02-20260925` — `branch-batch-02.md` / `branch-batch-02.json`: 19 further SHAs
  (`feat/p1-compat-kernel-hardening` 10, `feat/h2-pipeline-integration` 9), 153 changed-file
  records, 18 `SUPERSEDED` / 1 `KEEP` / 0 `CHERRY_PICK_CANDIDATE`, verified with
  `.project-local/dsh-audit/verify_batch02.py` at `errors=0`. Cumulative audited: **36 SHAs**.
- `codex/dp-f01-20260925` — `job-quality-projection-proposal.md`: corrected the DP-F01 gap
  description (§4 above) and proposed a typed read-only receipt projection. All 21 file:line
  citations re-verified; 21/21 exact.
