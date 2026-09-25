# DSH/DP non-frontend run handoff — 2026-09-25 (DP-NF-01 … DP-NF-07)

- Baseline (agreed): `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
- Baseline tree: `ce69abf1493481591534979be1223b1a447fc9bb`
- `origin/main`: `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`
- Root checkout during the whole run: `codex/aaos-p3-ui-convergence-20260922` @ `a9ead3e1`,
  **112 dirty paths before and after** — no tracked root file was written by this run.
- Pushed / merged / released / signed / Green-touched: **no**
- R6 / M0 state files changed: **no**; release remains `FROZEN`, overall `IN_PROGRESS`

Each task used its own worktree and branch at the exact baseline; each wrote only its permitted paths.

## 1. Per-task return

| Task | Branch | Tip SHA | Tip tree | Deliverable |
| --- | --- | --- | --- | --- |
| DP-NF-01 | `codex/dp-nf-01-20260925` | `d670559e4095d39f32bd515fbbf38a2c681b0829` | `2451c6cc7cad52d3612342558b715e8117027d2f` | `branch-batch-03.md/.json` + NF-03 final SHA review |
| DP-NF-02 | `codex/dp-nf-02-20260925` | `7844f3677be713e07fa1eeea448ba4475a7f4695` | `3d554300f0dc5251a935cfe87a7cb07c9ff52a95` | `p0-h01-host-lifecycle-proposal-20260925.md` |
| DP-NF-03 | `codex/dp-nf-03-20260925` | `3121cd974a6735d15969add899d288f718646a28` | `c3cd34d9a2b382edb2c484a5ed49e6a1e57ad3c4` | `tests/workers/test_p1_quality_matrix.py` + `tests/fixtures/p1-quality/` + 1 production fix |
| DP-NF-04 | `codex/dp-nf-04-20260925` | `373a03d2586acc2a0e61877c0f4a6c6604659bcc` | `7bbad6f3df14c32c6092876c6f257df072d591da` | `p2-search-course-gap-20260925.md` |
| DP-NF-05 | `codex/dp-nf-05-20260925` | `c1649137e77a99197e6ed8de13e4931a33432a51` | `48bbe37e73eb1a8513e308790a7b4c52e7242986` | `crates/archeaxis-domain/tests/machine_loop_restart.rs` |
| DP-NF-06 | `codex/dp-nf-06-20260925` | `046354535fd0250fe73babd9b0a0b39b39a00af0` | `a2428f33f7a4466a5a793cd91780d0ffa663d168` | `p5-backup-dirty-diff-review-20260925.md`, `p6-current13-candidate-readback-20260925.md` |
| DP-NF-07 | `codex/dp-nf-07-20260925` | `c858e10fc4b3cd066248abffed3bc3b7ac82a36d` | `c0fe38a52181676b0fab6f83eb7c4df1cf427d10` | `september-repo-language-data-gap-20260925.md` |

Every worktree reported a clean `git status --short` at its commit. No remote `dp-nf-*` branch exists
(nothing pushed).

## 2. DP-NF-01 — branch audit batch 03

16 SHAs across 7 previously uncovered branches (`agent/phase5-research-knowledge-governance`,
`fix/desktop-close-request-destroy`, `work/tp12-facades`, `chore/naming-repo-refs`,
`docs/verification-summary-2026-08-09`, `audit/unreleased-real-version`, `feat/absorption-adopt-now`).
107 changed-file records: **12 absent / 24 byte-identical / 71 evolved**.
Decisions: **`SUPERSEDED` 16**, `CHERRY_PICK_CANDIDATE` 0, `CONFLICT` 0, `UNKNOWN` 0.
Cumulative audited across batches 01–03: **52 SHAs**.

- Strongest absorption evidence yet: the **3,163,428-byte Magika `model.onnx`** is byte-identical to
  the baseline (blob `c9f1e0ab383e…`), as are its LICENSE/config; all eight ADOPT-NOW modules are
  resident.
- Donor archive covers 5 of the 12 absent paths; the other 7 are legacy container/web scaffolding or a
  dated ledger (inventory only — nothing restored, moved or deleted).
- `feat/absorption-roadmap-r0` (6 SHAs) was **deferred** to keep the batch inside the 15–20 cap and is
  nominated first for batch 04.
- Verification: `verify_batch03.py` → `errors=0`; JSON strict-parse; `git diff --check` exit 0.

## 3. DP-NF-02 — P0-H01 provider lifecycle proposal

`PROPOSAL / OWNER DECISION REQUIRED`. Verified boundary: the shipped Core calls `Executor::open`
(`main.rs:35-39`) with one default worker and **no extra routes**; the route table is seeded with
exactly `text.extract` (`executor.rs:36`) and dispatch fails explicitly otherwise
(`executor.rs:77-80`). `open_routes` is called only by `Executor::open` with an empty extra list and
by 12 test files — **never by the host**. `shared/provider_routing.py` has **zero** references in
`crates/**/*.rs` and **zero** in the Desktop C#, whose own UI text already states plugins/models/
sidecar are not on an authoritative readiness projection. Proposal defines publisher, generation
identity, installed-vs-enabled, health receipt (incl. `not_run`/`unknown`), ordered fallback, atomic
publish + crash recovery, replace/disable, startup readback, permissions, additive migration, 6 owner
decisions and 10 proposed acceptance tests. All 14 citations verified. No production file touched.

## 4. DP-NF-05, DP-NF-06, DP-NF-07 in brief

- **DP-NF-05** — added exactly one file, 163 lines, no production change. Coverage gap identified:
  no machine-side test had ever performed a human `modified` review and then tried to bind; the
  superseded row keeps `status='accepted'` forever, so only `is_knowledge_active` catches it. The new
  test **passed first run** → reported honestly as *"boundary already enforced; no test existed"*, and
  kept as a regression. Domain suite 13/14 groups green; API neighbours green.
- **DP-NF-06** — P5: reviewed the **678+/100− uncommitted** backup/migration diff in the root tree
  (not an old HEAD). `backup.rs` replaces count-only verification with schema-catalog equality,
  whole-schema table enumeration, typed per-table content digests and a stable read view; migration
  hardens identifier quoting, parameterises `pragma_table_info`, uses `create_new` export and stops
  skipping zero-row tables. Gaps recorded (workspace identity = owner decision; real Legacy semantic
  diff blocked on authorised input; two proposed follow-up test cards). **No test was run**, by design.
  P6: verifier readback of `current13-20260925` → `ok=true` with runtime+workers+provenance required,
  21,474 files, `problems=[]`, exit 0; manifest `source_commit`/`source_tree` equal the declared
  baseline; Desktop/Core/runtime exe and zip hashes recorded.
- **DP-NF-07** — retracted two initial findings after byte-level checks (the
  `DIRECTORY_AUTHORITY_INDEX` "mojibake" was a console artefact; 0 active docs fail strict UTF-8, and
  the naming-term hits sit in the naming authority's own prohibition tables). Material finding: **11
  untracked subtrees + 3 loose files migrated into `docs/history/` have no AX-DIR-010 classification
  row, and 8 of 11 are referenced by no authority index**; there is no `docs/history/README.md`; 8
  untracked `.patch` files sit beside 1 tracked file with no generation provenance. Ownership stays
  **UNKNOWN**; 33 root untracked entries classified; 5 normative gaps `G-01`…`G-05` with suggested
  owner and rollback. Nothing moved, deleted, renamed or re-indexed.

## 5. DP-NF-03 — P1 quality matrix (13 files, +5952/−4)

Completed in an independent worktree/subagent. **The one production change is reviewed and
endorsed here:**

`services/python-workers/document/worker_text.py` (+18/−4) — `_delimited_facts` reported
`header[:32]` with **no marker**, so a 33-column CSV presented a partial header as the whole one:
the only cap in the format facts lacking a `*_capped` flag. The fix adds `HEADER_CAP = 32`, a
`header_capped` fact and a note naming the cut. I verified it is **additive and non-breaking**: the
existing consumers (`tests/workers/test_f01_real_quality.py:278`,
`tests/text_format_facts.py:127`) assert only the `header` *value*, and no test anywhere pins the
exact key set of the format facts. The change is inside DP-NF-03's declared allowance ("only when a
failing test demonstrates a defect"), and RED was shown as `KeyError: 'header_capped'`.

Also added: `tests/workers/test_p1_quality_matrix.py` (11 tests) and 9 byte-exact fixtures plus
`manifest.yaml` and a **directory-scoped `.gitattributes`** (`* -text`) with a comment explaining
that the repository root's `* text=auto eol=lf` would otherwise rewrite the CRLF fixtures git stores
(measured: 15003→10002 and 24→21 bytes). Scope confirmed: it is inside the fixture directory and
affects nothing else.

Evidence: new file 11 passed / exit 0; with F01 and 13 neighbouring targets **165 passed, 2 skipped,
79 subtests, 0 warnings**; a wider sweep showed 2 failures + 4 errors, all from optional engines
absent in that venv (`pptx`, `openpyxl`, `pymupdf`) — pre-existing, not regressions.
**Evidence class `TESTED_LOCAL_SYNTHETIC` only**; not real-corpus qualification, closes no P1 format.

Three findings from this task, two of which are **mainline-relevant** and are routed to root rather
than acted on here:

1. **`worker_text` BOM asymmetry (not fixed, invariant pinned).** A UTF-8 BOM followed by non-UTF-8
   bytes hits `raw.decode("utf-8-sig")` with no handler, so the documented GBK fallback is
   unreachable and the job fails (`AAK-WORKER-003`), while the *same bytes without the BOM* succeed
   with a recorded GBK loss. The test accepts either arm but never a success without a recorded
   loss. Whether to extend the fallback to BOM documents is a product decision.
2. **Repo-wide `.gitattributes` normalizes CRLF.** `* text=auto eol=lf` silently rewrites CRLF
   fixture content on commit. Any byte-exact CRLF fixture anywhere in this repo needs its own
   scoped `.gitattributes`. Worth a repository-level note.
3. **Windows MAX_PATH.** A staged `input/<sha256>` under a deep pytest run root reached 275 chars →
   `FileNotFoundError`/`ERROR_PATH_NOT_FOUND`, which is easily mistaken for a sandbox denial. Run
   roots must stay short.

## 6. Findings that need root/owner attention

### NF-F1 (material, mainline) — a baseline test asserts a contract the code does not honour

At the **committed baseline**, `crates/archeaxis-domain/tests/backup_safety.rs:95`
`verify_counts_rejects_sqlite_integrity_failure_even_when_counts_match` **fails**. The test deletes an
index row from `sqlite_master` under `PRAGMA writable_schema=ON` and asserts
`backup::verify_counts(&source_db, &other_db).is_err()` (line 115). The implementation compares schema
catalog entries, table names and per-table row digests — **all of which remain equal** — so it returns
`Ok(true)` and the assertion panics.

Two facts make this worth an owner look:

1. It is **pre-existing at the baseline**, not caused by any DP change, and DP-NF-05 proved it by
   removing its own added file and reproducing the failure with a clean tree.
2. The mainline's **dirty working tree removes that test** (the committed baseline has 6 tests in that
   file; the dirty version has a different 10, without it) while changing `validate_workspace` to
   require **all** `PRAGMA integrity_check` rows to equal `["ok"]`. Deleting a failing test alongside a
   mechanism change is exactly the kind of move that needs a recorded decision.

**Recommended root action:** decide which side is authoritative and record it — either
(a) `verify_counts` must return `Err` on catalog-integrity damage (then keep a test like the removed
one), or (b) `verify_counts` returns `Ok(false)` for mismatch and the integrity claim moves to
`validate_workspace` (then the removed test is replaced by an equivalent one, not silently dropped).
Either way the *coverage* should survive the rewrite. **This is a decision, so it is not implemented
here.**

### NF-F2 (governance) — `docs/history/` classification gap
See §4 (DP-NF-07, `G-01`…`G-05`). Ownership remains UNKNOWN; exact path list is in that report.

### NF-F3 (cross-report audit false positive; disposition: no correction)
The earlier R-08 claim that `branch-batch-01.md` §6 was wrong is retracted. The donor archive index
`docs/history/donor-branch-assets/README.md` explicitly lists `requirements-ci-adapters.txt`, its
original blob SHA prefix `e215c62a6e99560e`, and 243-byte size. Absence at the baseline root path does
not mean absence from the donor archive. Batch 01 §6 is correct; no correction commit is warranted.
The cross-check correction is recorded in `branch-batch-03.md` §5 (R-08).

## 7. Tests not run (explicit)

| Task | Not run |
| --- | --- |
| DP-NF-01, NF-02, NF-04, NF-07 | no tests at all — read-only audits/proposals |
| DP-NF-05 | full `--workspace` suite; the other ~18 Rust API targets; all Python/desktop/Avalonia/archive suites (change was one test file, no production code) |
| DP-NF-06 (P5) | `cargo test`/`check`/`fmt` on the dirty files — deliberately, to avoid a shared Cargo target while the mainline is active. Therefore every "covered" line there means *a test exists*, **not** *the test passes* |
| DP-NF-06 (P6) | the `--require-current-source` recross-check returned `ok=false` under concurrent editing and is recorded `NOT_EXECUTED`, not as a Candidate defect |
| DP-NF-03 | see §5 |

No full product gate was run. Nothing in this run promotes any R6/M0 task; in particular P4 stays
`PARTIAL`, P5 stays `TESTED_LOCAL_PARTIAL`, P2 stays `TESTED_LOCAL_PARTIAL`, P6 stays at Candidate
readback only, and A16 remains an owner gate.

## 8. Boundary compliance

- No Green content read, no install/replacement, no release, no signing, no upload, no push, no
  `main` merge, no branch cleanup, no history move/delete.
- No `E:`/`F:` access; no private session store, user profile, or other-project access.
- The mainline's dirty files (Avalonia, `api/lib.rs`, domain `anchor/backup/knowledge/learning`,
  migration, R6 docs, Candidate builders) were **read for review only** in DP-NF-06 and otherwise left
  alone; none was re-implemented, copied, overwritten or rewritten on a DP branch.
- `docs/current/R6-*`, the UI plan/coverage doc and `docs/SHARED_RESOURCE_PATH_INDEX.md` were not
  modified.
