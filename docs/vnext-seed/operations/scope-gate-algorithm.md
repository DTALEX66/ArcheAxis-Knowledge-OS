# Scope gate: fail-closed algorithm

AGENTS.md and CODEOWNERS guide people; they are not authorization boundaries.
Every pull request is authorized by one immutable issued envelope and its
authority grants added in a protected metadata-only activation commit. A
template, a local coordination lock or anything edited in the pull-request
head never grants authority.

## Evaluation order

1. Resolve subject base `P`, activation commit `I`, current PR base and subject
   head; fail when any identity is missing. Verify `parent(I)=P` and that `I`
   only added the exact issued envelope and its referenced grants.
2. Require one canonical task ID in the envelope, branch metadata and PR body;
   aliases or mismatches fail.
3. Read Project Contract, Directory Authority, Program graph, schemas, issued
   envelope and grants with `git show`. Only
   `.project/tasks/issued/<plan-id>/<task-id>/<issuance-id>.json` is considered;
   never scan or fall back to `.task-template.yaml`.
4. Recompute from `P` the authority manifest, consumed-interface manifest and
   Program graph digest. Validate schema versions, full SHAs/tree, issuance,
   not-before/expiry, assignee, already-satisfied machine and artifact inputs,
   merged dependency receipts and grant coverage. Reject a template,
   placeholder, unresolved external wait, expired/revoked grant or
   local-lock-only claim.
5. Reject self-expansion: the PR head may not edit its envelope, grants,
   Program graph or authority to authorize itself.
6. Compare `I` to the current base. Reject authority/interface/dependency
   changes or overlapping paths; only proven-disjoint base advancement may be
   accepted without a new issuance.
7. Compute create/modify/delete/rename/chmod with rename detection. Validate both
   sides of a rename.
   - For `execution_mode: qualification-no-diff`, require an empty diff from
     activation commit `I` to subject head, an empty operation/path scope, zero
     file/line/binary limits and no authority grant. Run the checkout read-only;
     logs and receipts go only to job scratch or an external attestation. A
     discovered defect fails or blocks this slice and returns to a newly issued
     implementation slice in the owning lane.
   - For a PR-32 implementation slice, recompute the AAK-JCS-1 digest of the
     protected `LEGACY_MANIFEST.yaml`, select exactly one `asset_id` whose
     decision is `retire` and status is `approved`, and require its census to
     contain exact paths without glob metacharacters. Recompute the selected
     entry and complete path-set digests at `P`, deterministically partition the
     sorted paths into at most 25 paths, and require the issued
     `manifest_scope.expanded_paths` and `scope.allowed_paths` to be identical.
     A pseudo path, unmatched path, wrong part, stale manifest or digest mismatch
     never grants scope.
8. Normalize repository-relative paths; reject absolute paths, `..`, case
   collisions, escaping symlinks, submodule changes and unexpected executable
   bits.
9. Apply directory rules in this order: deny, exact path, highest count of
   literal path segments, then longest literal prefix. This authority
   precedence is unchanged by overlays. After selecting the unique authority
   rule, independently match every `protected_resource_overrides.rules` entry
   and `protected_files` entry against the changed path. An override never
   changes the selected owner or lane; it adds its protected resource and
   serial-grant requirement. Thus a nested capability-pack `uv.lock` remains
   owned by its more-specific directory rule while `**/uv.lock` always adds
   `dependency-locks-and-versions`. Any overlay ambiguity, remaining authority
   ambiguity or unknown path fails; the envelope cannot create authority.
10. Require exactly one execution lane in the issued envelope. A selected rule
    with `execution_lane` matches only exact equality; a selected rule with
    `execution_lanes` matches only when the envelope lane is a listed member.
    The two rule fields are mutually exclusive, lanes do not inherit from an
    owner or parent rule, and a writable rule with neither field is invalid.
    Deny-only rules may omit a lane. Reject a mismatch before validating the
    operation, allowed/forbidden paths, Program ceiling and
    file/line/binary/effort limits.
11. Require the issued grants to cover every serial resource selected either by
    the authority rule, a protected-resource override or `protected_files`.
    Duplicate references to the same resource collapse to one required grant;
    conflicting override results fail. The Git-common-dir database is checked
    separately only for local coordination.
12. Run secret, vendor-state, generated-drift and database-writer boundary
    checks.
13. Form the candidate union from `task_rules[program_task_id]`, every matching
    path rule and the risk rule. Record each candidate's source, rule reference
    and pre-execution decision in `selection_trace`. A candidate may be
    `NOT_APPLICABLE` only when the trusted selector proves that decision from
    the issued slice, normalized diff and cited evidence; an Agent assertion,
    runner absence or failed setup is not such proof.
14. Freeze a GatePlan whose `gates` array is exactly the de-duplicated candidates
    marked `SELECTED_REQUIRED`. It contains no optional or non-applicable gate.
    Run every listed gate against the exact subject head; every result must be
    `PASS`.
15. Generate an external exact-SHA receipt and validate it against the envelope,
    grants, GatePlan, subject tree and artifacts. The `vnext-required`
    aggregation job runs with `if: always()` and fails if a selected gate is
    absent, skipped, cancelled, blocked, timed out, failed or reported as
    non-applicable.

The Gate Registry semantic validator also requires the `task_rules` key set to
equal the 39 canonical Program IDs in the protected Program graph and every
referenced gate ID to resolve exactly once. For a multi-slice Program, each
slice traces every Program candidate. Program completion requires at least one
exact-SHA `PASS` for every Program task-rule gate across the accepted child
receipts; per-slice `NOT_APPLICABLE` entries cannot erase that Program-level
coverage obligation.

## Stable rejection codes

`E001_TASK_NOT_ISSUED`, `E002_TASK_EXPIRED`, `E004_AUTHORITY_CHANGED`,
`E009_UNKNOWN_AUTHORITY_PATH`,
`E005_STALE_BASE_OVERLAP`, `E010_PATH_NOT_ALLOWED`, `E011_PATH_FORBIDDEN`,
`E012_GRANT_MISSING`, `E013_GRANT_EXPIRED`, `E014_GRANT_MISMATCH`,
`E015_ENVELOPE_SELF_EXPANSION`, `E016_CHANGE_LIMIT_EXCEEDED`,
`E017_GENERATED_FILE_HAND_EDITED`, `E018_VENDOR_STATE_COMMITTED`,
`E019_DB_WRITER_BOUNDARY`, `E020_UNDECLARED_CONTRACT_CHANGE`,
`E021_RECEIPT_MISSING`, `E022_REQUIRED_GATE_SKIPPED`,
`E023_SYMLINK_ESCAPE`, `E024_SECRET_RISK`, `E025_SUBMODULE_CHANGE`,
`E026_QUALIFICATION_DIFF`, `E027_MANIFEST_SCOPE_MISMATCH`.

## First hostile fixtures

- Edit an unauthorized normal path.
- Present a template, null/placeholder field or local coordination lock as an
  issued task or remote grant.
- Reuse an old receipt against a different issuance, base, head or GatePlan.
- Widen `allowed_paths` in the same PR.
- Modify OpenAPI without a contract grant; then use an expired grant.
- Add `sqlite3`/`aiosqlite` to Python or Microsoft.Data.Sqlite to Avalonia.
- Add rusqlite/sqlx-sqlite outside the store crate.
- Skip a required component job through path filtering.
- Commit `.codex`, `.dsh`, `.hermes`, database/WAL/SHM or credential fixtures.
- Create a rename or symlink that enters a denied path.
- Commit a product or test change from a qualification-no-diff slice.
- Present PR-32 with a pseudo path, glob-bearing approved entry, stale manifest
  digest, omitted partition or expanded path not present in the selected entry.
- Prove four disjoint worktrees pass concurrently and an overlap fails.

The ruleset requires exactly two stable checks: `vnext-scope-gate` and
`vnext-required`, current-base strictness, pull requests and squash merge.
Personal Owner mode needs zero independent approvals but no bypass. Team mode
later adds one approval, CODEOWNER review and last-push approval without
changing this protocol.
