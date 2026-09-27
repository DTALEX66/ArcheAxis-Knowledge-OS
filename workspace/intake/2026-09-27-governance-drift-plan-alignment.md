# Anti-drift governance plan alignment (2026-09-27)

## Decision

The Owner-supplied "anti-drift governance executive plan"
(`Authority → CURRENT → Task Envelope → Machine Gate → Receipt`) is **accepted in
intent but not as written**. Its three-stage check intent (START / PRE-COMMIT /
PRE-INTEGRATION) and its parallel-worktree constraint are correct and already
supported by registered gates. Its artifacts are approximately sixty percent
duplication of the existing authority substrate, and three premises are factually
wrong.

Concretely: no new registry, schema, template, script or CI gate is created by
this intake. The alignment analysis and corrected designs live in
`docs/current/DSH-GOVERNANCE-ALIGNMENT-20260927.md`. `CURRENT` remains a real gap,
but it must be built as a **projection** whose every field points at a single
existing authority source, and it must not be written under `.project/**`.

Three premises must be corrected before any implementation:

1. There is no "receipt v3". `archeaxis.task-receipt/v1` (`schema_version` 1),
   the vNext journey receipt (which **requires** `schema_version` 2), and the
   release identity schema (2.0.0/3.0.0) are three unrelated schemas. The plan's
   negative test demanding that receipt v2 be rejected would break
   `scripts/ci/check_vnext_receipt.py`.
2. The plan's `base_commit` is already stale and lives on another branch.
3. "Task envelope template" is not a thing: the envelope schema forbids
   templates (`state` const `issued`, `additionalProperties: false`), and the
   template schema is explicitly non-authorizing (`E001_TASK_NOT_ISSUED`).

## Authority basis

- `docs/authority/AGENTS.vnext-governance.md` lines 9-24 (eight-tier priority;
  lower authority may narrow but not widen; authority order is not evidence
  rank) and lines 43-44 (stop conditions).
- `DIRECTORY_AUTHORITY.yaml` line 446-448 (`docs/**` is non-serial and admits the
  `owner` lane) and line 545 with line 558 (`.project/**` is a protected file,
  so any write there needs a remote grant regardless of the underlying rule).
- `.project/schemas/{task-envelope,task-template,task-receipt,authority-grant}.schema.json`.
- `.project/GATE-REGISTRY.yaml` (36 registered gate IDs; `task_rules`,
  `path_rules`, `risk_rules`).
- `.worklab/project-validation.v1.yaml` (changed-path to risk to gate mapping;
  AXC-060 unknown-path policy).

The Owner's current explicit instruction (priority tier 1) selected the
alignment-first route and is the basis for the two documents in this intake.

## Scope and evidence boundary

This intake is read-only analysis plus documentation. Nothing was executed: no
pytest, cargo, dotnet, wheel, CI, GUI or runtime check. No product status is
changed or upgraded. No file under `.project/**` was created. No existing
authority file was modified. Evidence is source and metadata level only.

Registered as an open item: `workspace/**` carries
`write_mode: maintenance-only-task-envelope` with lane `migration`, and the
repository currently has no issued envelope anywhere (`.project/tasks/issued/`
and `.project/leases/issued/` hold only README files). This intake note is
written under the tier-1 Owner instruction and is flagged for Owner
adjudication rather than silently treated as authorized.

## Concurrent-writer finding

A second writer was observed committing and pushing in this same checkout during
the session: `43c2cafa` appeared after the fetch that still showed `69a3baed`,
and a new `dsh-backend-r5` worktree appeared minutes later. Mitigation applied:
this branch now has its own worktree at
`.project-local/worktrees/dsh-governance-20260927`, and the main worktree was
returned to `codex/aaos-p3-ui-convergence-20260922`.

The repo declares a same-machine coordination backend at
`git-common-dir/archeaxis-agent/state.sqlite` (`DIRECTORY_AUTHORITY.yaml:569-577`)
but it does not exist, and no script under `scripts/**` references it. "No
concurrent writes" therefore has no machine enforcement today. See section 10 of
the alignment report.

## Open items for Owner decision

1. Digest normalization for authority files: canonical-LF versus `AAK-JCS-1`
   versus RFC 8785. Without choosing one, any cross-host projection drifts.
2. Where the `CURRENT` projection lives: ignored scratch versus a tracked path
   (the tracked option needs an issued envelope plus a new ownership rule).
3. Whether `mypy` becomes a registered gate (it currently is not).
4. Adjudication of the `workspace/intake/` write above.
5. Whether to implement the declared coordination backend, since "no concurrent
   writes" is currently unenforced. Not built by this intake.

## Rollback

Delete this file and `docs/current/DSH-GOVERNANCE-ALIGNMENT-20260927.md`, then
remove the branch worktree with
`git worktree remove .project-local/worktrees/dsh-governance-20260927`.
Deleting the remote branch is a separate destructive side effect requiring its
own authorization and was not performed.
