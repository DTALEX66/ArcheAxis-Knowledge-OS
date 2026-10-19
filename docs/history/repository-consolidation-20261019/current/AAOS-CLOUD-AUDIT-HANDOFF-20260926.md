# Cloud audit handoff — AAOS DSH session, 2026-09-26

Single entry point for an external auditor (including a cloud-hosted GPT) that
has **only the GitHub repository** and no access to the developer machine.

Everything cited here is verifiable from the repository alone, except the one
item explicitly marked **local-only** at the end.

## 1. What to read, in order

| # | Path | What it establishes |
| --- | --- | --- |
| 1 | `docs/current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md` | Session log D-1…D-6: every change, its evidence level, decisions, errors and remaining gaps |
| 2 | `docs/history/branch-donors/README.md` | Branch-consolidation record: per-branch criterion, archived files, recovery tips, cloud-readback table |
| 3 | `docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` | Pre-existing structured disposition of all 33 branch records (the authority the audit was checked against) |
| 4 | `config/desktop/routes-v1.json` + `app/contracts/desktop_routes_v1.py` + `packages/contracts/v1/desktop-routes.schema.json` | The route contract after reconciliation |
| 5 | `tests/test_axr060_completion_audit.py` | The release-surface / receipt boundary and its nine regressions |

## 2. Exact state to audit

A document cannot record the SHA of the commit that contains it. To avoid a
self-referencing commit loop, the four identities below are kept separate.

| Role | Value | How to obtain |
| --- | --- | --- |
| Remote ref to read | `origin/codex/aaos-p3-ui-convergence-20260922` | `git rev-parse origin/codex/aaos-p3-ui-convergence-20260922` |
| Current tip | read live; deliberately not pinned here | `git rev-parse HEAD` |
| Code state this handoff's code claims were tested on | `0db29842` (full qualification) and `60740800` / `a473267a` (earlier targeted runs) | see the run table |
| `main` | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb` | **not** updated; integration `BLOCKED_BY_OWNER` |

Status of the latest handoff view, by evidence class:

| Class | Items |
| --- | --- |
| **Verified** | the `4270f25f` `test (3.12)` failure and its fix, reproduced in a cloud-equivalent clone (before: 5 ids named / after: 12 passed) |
| **Verified (exact SHA)** | run `36242930810` on `0db29842`: 18 jobs pass, `wheel-smoke` fails |
| **Inherited, not re-measured by this document** | the local full-suite result quoted in §6 |
| **ROOT CAUSE FOUND (2026-09-26)** | `wheel-smoke` — the wheel was never installed; see §2.2 |
| **BLOCKED** | `main` integration; native GUI/UIA/screenshot acceptance |

### 2.1 Historical run snapshots (each scoped to its own source SHA)

These are observations of *the source SHA in the row*, not of the current tip.
Push-triggered runs classify by changed path, so a docs-only change correctly
skips `test`.

| Run | Source SHA | Conclusion | Jobs that ran |
| --- | --- | --- | --- |
| [36239548637](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36239548637) | `14a2788c` | success | `gateplan`, `lint`, `test (3.12)`, `a0-gates` |
| [36240789632](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36240789632) | `a473267a` | success | `gateplan`, `lint`, `test (3.12)`, `contracts-vnext`, `a0-gates` |
| [36240789707](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36240789707) | `a473267a` | success | `vnext-ci/cargo-test` |
| [36241709088](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36241709088) | `fde023c5` | success | `gateplan`, `lint`, `a0-gates` (docs-only: `test` correctly SKIPPED) |
| [36242037128](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36242037128) | `60740800` | success | `gateplan`, `lint`, `a0-gates` (docs-only) |
| [36242496590](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36242496590) | `4270f25f` | **failure** | `test (3.12)` ran and failed; see §2.3 |
| [36242930810](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36242930810) | `0db29842` | **failure (18/20)** | forced full qualification; see §2.2 |

**Scope limit that must not be lost:** the five push-triggered runs above ran only
`gateplan`, `lint`, `test (3.12)`, `contracts-vnext` and `a0-gates`. On those
SHEs the remaining gates — `rust-vnext`, `desktop-vnext`, `desktop-build`,
`installer-lifecycle`, `wheel-smoke`, `security-targeted`, `format-targeted`,
`workers-vnext`, `migration-targeted`, `browser-smoke`, `windows-runtime-smoke`,
`green-candidate-vnext`, `py-compat` — **were skipped and are not verified by
them**, on those source SHAs. They were first executed for this branch by the
`0db29842` forced run below, which is why the two statements are not in conflict:
skipped on the push runs, executed on the forced run.

### 2.2 Forced full qualification at `0db29842` (workflow_dispatch, `force_full=true`)

Run [36242930810](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36242930810) executed the gates the push-triggered runs skip.

| Result | Jobs |
| --- | --- |
| **success (18)** | `gateplan`, `lint`, `test (3.12)`, `contracts-vnext`, `rust-vnext`, `desktop-vnext`, `desktop-build`, `desktop-fast`, `workers-vnext`, `migration-targeted`, `security-targeted`, `format-targeted`, `browser-smoke`, `windows-runtime-smoke`, `green-candidate-vnext`, `installer-lifecycle`, `py-compat (3.11)`, `py-compat (3.13)` |
| **failure (1)** | `wheel-smoke` |
| **failure (aggregate)** | `a0-gates` — fails only because `wheel-smoke` failed |

This evidence belongs to source `0db29842` and to that run's job set only. It does
not transfer to a later tip automatically; §9 of the continuation pack requires
diffing before inheriting it.

**`wheel-smoke`: OPEN / ROOT_CAUSE_UNVERIFIED.** The job asserts required wheel
members (`app/release-manifest.json`, `app/research/github.py`,
`shared/research_store.py`, `shared/core_schema.py`, `shared/migration_runner.py`,
…) and that no cache or test artifact is packaged
(`.github/workflows/ci.yml`, step "Smoke-test installed runtime outside
repository", `assert not missing` / `assert not forbidden`).

Two things are established and one is not:

- Established: this branch had **no earlier `wheel-smoke` baseline** — the gate
  never ran on it before this forced run.
- Established: no commit in this session touched any asserted member; the changes
  are `app/capability/store.py`, test files, `config/desktop/routes-v1.json`, the
  route contract, `.worklab/project-validation.v1.yaml` and documentation.
- **Not established: causation.** "This session did not edit those files" bounds
  the change set; it does not prove the gate was already red. The introducing
  commit is unknown pending a same-conditions reproduction. An earlier draft of
  this section asserted "pre-existing, not caused by this session"; that claim is
  withdrawn here.

**Evidence identity, resolved.** A review reported a conflict between job
metadata ("Verify wheel contents succeeded, Verify shared import failed") and the
log ("member AssertionError"). Checked at attempt level
(`/runs/36242930810/attempts/1/jobs`): step 6 "Build wheel from locked backend" =
success, step 7 "Install wheel with locked runtime dependencies" = success, and
**only step 8 "Smoke-test installed runtime outside repository" = failure**. There
was no step-name divergence; the "member AssertionError" text came from reading
the *printed body of the workflow script* rather than the failure output, which is
how a printed `assert not missing` line can be mistaken for a raised one.

The failing statement is `ci.yml` line 404, the 16th line of that step's heredoc,
matching the log's `File "<stdin>", line 16`:

```python
assert installed_version("archeaxis-workspace") == load_release_manifest()["product"]["version"]
```

**Corrected 2026-09-26.** An earlier revision of this section concluded that "the
failure is a version mismatch between the installed distribution and the manifest
inside the wheel". That inference came from matching the traceback's
`File "<stdin>", line 16` to the assertion line; the assertion line is correct, but
the inferred cause was not measured. It has since been measured and **does not
hold**: a wheel built from the exact tracked source at `0db29842` carries
`METADATA` `Version: 0.6.14` *and* `app/release-manifest.json`
`product.version` `0.6.14`, so the two values the assertion compares agree inside
the artifact, and installing that wheel into a clean CPython 3.12 environment
resolves exactly one `archeaxis_workspace-0.6.14.dist-info` and satisfies the
assertion. The same holds for the current tip. See `R6-EXECUTION.md`,
"wheel-smoke: artifact hypothesis refuted, source-shadowing defect found and
fixed — 2026-09-26", for the harnesses and result files.

What was checked, and what remains:

- `pyproject.toml` = `0.6.14`, `app/release-manifest.json` product.version
  = `0.6.14`, and `tests/test_release_manifest.py:62` asserts the two agree.
- The version is **static**: no `[build-system]` dynamic version, no
  `setuptools_scm`/git-describe derivation, and no build-time writer of
  `app/release-manifest.json` exists anywhere in the tree.
- A real, independent defect in this gate **was** found and reproduced: the job's
  first step publishes `PYTHONPATH=<checkout root>` through `GITHUB_ENV`, which
  persists into the later steps, so "Smoke-test installed runtime outside
  repository" imported the checkout rather than the installed wheel, and its guard
  tested a `sys.path` entry's basename against the string `knowledge_base`, which
  cannot detect a checkout root. That is fixed, together with a regression test.

Status: **ROOT CAUSE FOUND, 2026-09-26.** The job log is readable with an authenticated
token, and it shows the wheel was **never installed**. The build step's setuptools
`egg_info` writes `archeaxis_workspace.egg-info` into the checkout, and the job's first
step leaks `PYTHONPATH=<checkout root>` through `GITHUB_ENV` into the install step, so
pip reported the just-built wheel as already installed and skipped it:

```
./.project-local/task-runtime/wheel-smoke/dist/archeaxis_workspace-0.6.14-py3-none-any.whl
is already installed with the same version as the provided wheel. Use --force-reinstall to force an installation of the wheel.
```

The smoke step then resolved `app`, `shared` and `knowledge_base` from the checkout, and
the version assertion compared the checkout's egg-info against the checkout's own
manifest. The original log records only `File "<stdin>", line 16, in <module>` followed by
`AssertionError`, because that assertion carried no message — which is why no pair of
values was ever recoverable from it. Both leaks are now closed, the install uses
`--no-deps --force-reinstall`, and the assertion prints both observed values on failure.
See `R6-EXECUTION.md`, "wheel-smoke root cause FOUND: the wheel was never installed —
2026-09-26". What remains unproven is whether the *installed* wheel itself satisfies the
smoke step, which that gate is only now able to test.


### 2.3 The `test (3.12)` failure at `4270f25f` and its fix

`docs/current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md` restated the tip SHAs of
deleted branches. This repository's `test_axr060_completion_audit` requires every
40-hex identifier under `docs/current/` to resolve to a real object, and a deleted
branch's tip does not exist in a fresh checkout, so `test (3.12)` failed there.
Reproduced and fixed against a cloud-equivalent clone (`git clone --no-local`
plus a full ref fetch), not reasoned about:

```
before: FAILED tests/test_axr060_completion_audit.py — 5 ids named
after : 12 passed
```

The checkpoint now names the five branches without restating their SHAs; the full
identifiers remain in `docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`,
which the test's own receipt classifier exempts by declared schema.

### 2.4 Where each claim belongs

| Claim type | Lives in |
| --- | --- |
| Current code identity | this section, resolved live |
| Historical test evidence | §2.1, bound to its source SHA |
| Full-qualification evidence | §2.2, bound to `0db29842` |
| Unreleased / unreachable object ids | structured historical receipts under `docs/current/*.json` (declared audit schemas), referenced rather than restated |
| Running session log | `docs/current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md` |


## 3. What changed, and how to audit each change

### 3.1 `install_builtin` accepted only one class identity — commit `caf4ab3c`

`app/capability/store.py` decided a manifest was already parsed with
`isinstance(manifest, PluginManifest)`. A manifest from a second import of the
same module is a different class object for the same contract, so a valid
manifest was pushed back through `load_manifest_from_mapping()` and rejected by
jsonschema as "not of type 'object'".

Audit it: `tests/test_axw_cap503_builtin.py::test_store_accepts_manifest_from_a_second_module_identity`
re-imports the module under a second name and asserts the split identity is real
(`not isinstance(...)`) while the store still accepts it.

### 3.2 Release-surface / receipt boundary — commit `14a2788c`

The shipped `_is_audit_receipt` exempted files by sniffing the first 600
characters for a marker, with **no path restriction**, and applied that to every
surface including `SYSTEM_BOUNDARY.md`. A receipt marker inside a locked surface
therefore hid a forged id from the scan.

Audit it: `tests/test_axr060_completion_audit.py` now classifies by path first
(`_receipt_schema_of`), admits only an exact `schema_version` from an allowlist,
and carries nine regressions A, A2, B, C, D, E, E2, F, G. Run:

```
git grep -n "_LOCKED_SURFACES\|_RECEIPT_SCHEMAS\|_receipt_schema_of" tests/test_axr060_completion_audit.py
```

The negative control is reproducible: add a fake 40-hex id to
`SYSTEM_BOUNDARY.md` in a scratch checkout and the test fails naming it.

### 3.3 GatePlan classified contract-bearing docs as prose — same commit

`docs/PROJECT_STATUS.md` and the authority indexes are read and asserted on by
contract tests, yet matched only `docs-mechanical` (`static`). `.worklab/project-validation.v1.yaml`
now has `contract-bearing-docs` with **exact paths only** (a broad glob would
force the primary suite onto every prose change).

Audit it: `tests/test_ci_classifier.py::test_contract_bearing_docs_require_the_primary_suite`
asserts `py-primary` for `docs/PROJECT_STATUS.md` and its absence for
`docs/current/R6-EXECUTION.md`.

### 3.4 Route contract named an endpoint Core never served — commit `a473267a`

`config/desktop/routes-v1.json` declared `machine_assets -> /api/v1/machine/assets`.
`crates/archeaxis-api/src/lib.rs` has never declared that path. R6-EXECUTION.md
had already recorded the mismatch and the decision not to add a speculative call;
the manifest was simply never reconciled.

Reconciled to `machine_growth -> /api/v1/machine/tasks/{task_id}` (the route Core
does serve, the only machine endpoint the desktop calls). Pydantic contract, JSON
Schema and the bulk schema matrix were updated with it.

Audit it:

```
grep -n 'machine' config/desktop/routes-v1.json
grep -n '\.route(' crates/archeaxis-api/src/lib.rs
```

and `tests/test_desktop_routes_v1.py::test_every_declared_core_endpoint_exists_in_the_router`,
which parses the real Axum router so a phantom endpoint cannot pass again.

### 3.5 Branch consolidation — commits `6a246486`, `fde023c5`, `60740800`

Local branches went **27 → 7**. Criterion: count the paths a branch *added*
relative to its merge-base, then check each with `git cat-file -e HEAD:<path>`.

Audit it from the cloud:

```
git branch -a
git merge-base --is-ancestor main HEAD && echo "main is an ancestor of HEAD"
git log --oneline origin/main..HEAD | wc -l
```

Archived branch-unique files are under `docs/history/branch-donors/` with a
README recording each source branch, tip SHA, reason and recovery command. The
seven survivors and their reasons are in that README.

**Deleting a branch removed no content**: every deleted tip is still present in
the repository and reachable with `git branch <name> <sha>`. Readback of
`GET /repos/DTALEX66/ArcheAxis-Knowledge-OS/commits/<sha>` returns 200 for
twelve of the thirteen archived tips — see the table in
`docs/history/branch-donors/README.md`.

## 4. Known defects left unfixed (auditable, deliberately not hidden)

| Item | State |
| --- | --- |
| `crates/archeaxis-api/tests/maintenance_cli.rs` | carries CRLF; flagged by `check_repository_conventions.py --source worktree`. Pre-existing, not touched by this session |
| `shared/provider_routing.py` | line-ending drift only (`git diff --numstat` empty); deliberately uncommitted |
| `docs/history/branch-donors/execution-reliability-20260926/` | pre-existing untracked content from an earlier session; preserved, not committed |
| Design reference assets | **Corrected.** An earlier revision said no design asset exists in the repository. That was too broad: `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/` contains six legacy V3 design documents and delivery archives plus that directory's own `README.md`. The exact file names are **not** restated here: they carry a superseded product name, and this handoff is an active surface that `scripts/check_repository_conventions.py` scans for it. The complete, byte-sized inventory lives on the declared historical surface `docs/history/legacy-design-assets/README.md`. What does **not** exist is anything literally named `DESIGN-SPEC` / `B10` / `B09`. Those documents are the legacy V3 design line, superseded by the current authority (C#/Avalonia, Chinese-first, black/white dark baseline), so they are reference material, not the active visual specification. Nothing was extracted from the `.docx`/`.zip` binaries in this session, and no substitute asset was generated |
| Route contract vs shell navigation | contract declares 7 page ids; the shell exposes 16 sections. Left `PROPOSED` because extending `page_id` (a closed `Literal`, with `routes` at `min_length=7`) means making `core_endpoint` optional — a contract semantics change needing an owner decision |
| `main` integration | **not done.** `origin/main` (`e3875db0`) is an ancestor of this head, i.e. a clean fast-forward is available, but this session had no merge authorisation. Marked `BLOCKED_BY_OWNER`. (Corrected 2026-09-26: an earlier revision transposed these figures as "0 ahead / 187 behind"; the live counts are **204 ahead / 0 behind**) |
| Native GUI / UIA / screenshots | not executed — no interactive desktop session. All GUI acceptance remains unverified |

## 5. Local-only items (not auditable from the cloud)

- Git objects reachable only from local refs that were never pushed. Verified:
  the `codex/recovery-shell-frontend` tip returns **422** from the GitHub commits
  API, and that branch was never pushed, so deleting the local ref makes it
  unrecoverable. This is the single archival tip not readable remotely. (Its
  exact SHA is not restated here: this repository's own `test_axr060` requires
  every 40-hex identifier in `docs/current/` to resolve to a real object in the
  checkout, and a local-only commit cannot. The SHA remains in
  `docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`, which is a
  declared audit receipt and therefore outside that scan.)
- `.project-local/` runtime evidence (run directories, test databases,
  screenshots) is git-ignored by design and therefore absent from the cloud.

## 6. Reproduce the local verification

```
.\scripts\ci\run_tests.ps1 tests/ integration-tests/ knowledge_base/tests/ -q --tb=line
.\.venv\Scripts\python.exe -B scripts/check_repository_conventions.py --source worktree
.\.venv\Scripts\python.exe -B scripts/ci/classify.py --paths docs/PROJECT_STATUS.md
```

Last local run: **3355 passed, 46 skipped, 0 failed**.

## 7. Navigation and format baselines established this round

Recorded so a later round starts from facts rather than re-deriving them.

### 7.1 Shell sections versus contract page ids

Two overlapping sets, not a subset relation — the "7 versus 16" difference is
**not** nine missing pages:

| Set | Count | Where |
| --- | --- | --- |
| Contract page ids | 7 | `config/desktop/routes-v1.json` |
| Native navigation sections | 16 | `CommandPaletteRoutes` in `MainWindow.axaml.cs` |

Both sides use the same identifier convention with one exception: a page id is
`snake_case` where its section is `kebab-case`, so `source_reader` ↔ `source-reader`
and `machine_growth` ↔ `machine-growth`. Normalising on `-` makes every manifest
page id resolve to a real section.

The nine sections without a page id are `home`, `capture`, `library`,
`original-editor`, `memory-map`, `evidence`, `research`, `plugins`, `models` —
navigation surfaces, local projections, or the recorded honest-unavailable
domains (`research`/`plugins`/`models`, already asserted not to call Core).

`tests/test_desktop_routes_v1.py::test_navigation_sections_and_contract_page_ids_are_distinct_sets`
pins this. Negative control verified: renaming `machine-growth` in the shell makes
it fail.

### 7.2 Format matrix: verified against the real route tables

`docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` is the authority
(`archeaxis.format-status/v1`, carried from the 0907 coverage file). Its own
validator passes:

```
python scripts/check_format_matrix.py --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json
-> 16 groups carried, 0 complete, 14 partial, 2 custody only;
   every claimed route exists in the Core and transport tables (11 core routes, 10 worker routes parsed)
```

So the matrix does not drift from the implementation: every route it claims is
really declared. `complete` is **0** — the honest current state.

Engine routing (`_ENGINES` in `app/ingestion/multi_format.py`) covers 14 format
keys: `pdf`, `docx`, `pptx`, `xlsx`, `csv`, `html`, `image`, `media_video`,
`media_audio`, `article`, `md`, `txt`, `canvas`, `rtf`, `odt`. Detection is
`detect_format` plus `detect_format_from_content`. `marker-pdf` is deliberately
**excluded** with its reason in the source (supply-chain ledger B003 is
REVIEW-BLOCK: Apache-2.0 code but modified OpenRAIL-M weights), so it must not
become a default engine — that exclusion is correct, not a gap.

Format contract tests pass (39 across `test_format_matrix`,
`test_format_execution_v1`, `test_text_format_facts`).

