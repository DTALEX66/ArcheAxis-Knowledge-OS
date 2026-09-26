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

| Item | Value |
| --- | --- |
| Branch | `codex/aaos-p3-ui-convergence-20260922` |
| Head commit | `4270f25f906b9498775a61982c3db02de8fd465b` |
| `main` | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb` (**not** updated) |
| Local = remote | yes, verified by `git rev-parse` on both plus a GitHub commit readback |

> `4270f25f` is documentation-only. The code state to audit is `60740800`
> (route reconciliation) and `a473267a` (the `install_builtin` and boundary
> fixes); earlier commits in the same session are listed in the checkpoint log.

### CI runs (exact SHA)

| Run | SHA | Conclusion | Jobs that actually ran |
| --- | --- | --- | --- |
| [36239548637](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36239548637) | `14a2788c` | success | `gateplan`, `lint`, **`test (3.12)`**, `a0-gates` |
| [36240789632](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36240789632) | `a473267a` | success | `gateplan`, `lint`, **`test (3.12)`**, **`contracts-vnext`**, `a0-gates` |
| [36240789707](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36240789707) | `a473267a` | success | `vnext-ci/cargo-test` |
| [36241709088](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36241709088) | `fde023c5` | success | `gateplan`, `lint`, `a0-gates` (docs-only: `test` correctly SKIPPED) |
| [36242037128](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36242037128) | `60740800` | success | `gateplan`, `lint`, `a0-gates` (docs-only) |

**Read this honestly:** the jobs `rust-vnext`, `desktop-vnext`,
`desktop-build`, `installer-lifecycle`, `wheel-smoke`, `security-targeted`,
`format-targeted`, `workers-vnext`, `migration-targeted`, `browser-smoke`,
`windows-runtime-smoke`, `py-compat` were **SKIPPED** on this branch and are
therefore **not verified**. Python `test (3.12)` and `contracts-vnext` are the
lanes that actually ran.

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
| `DESIGN-SPEC` / `B10` / `B09` assets | **do not exist in the repository** → recorded `UNVERIFIED_REFERENCE`, no substitute generated |
| Route contract vs shell navigation | contract declares 7 page ids; the shell exposes 16 sections. Left `PROPOSED` because extending `page_id` (a closed `Literal`, with `routes` at `min_length=7`) means making `core_endpoint` optional — a contract semantics change needing an owner decision |
| `main` integration | **not done.** `origin/main` is an ancestor of this head (0 ahead / 187 behind), i.e. a clean fast-forward, but this session had no merge authorisation. Marked `BLOCKED_BY_OWNER` |
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

Last local run: **3353 passed, 46 skipped, 0 failed**.
