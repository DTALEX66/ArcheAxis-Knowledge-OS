# Task issuance, activation and Program closure

`TASK-GRAPH.yaml` contains 39 stable Program nodes. A Program node is a scope
ceiling and dependency milestone, not an authorization. Agents execute one or
more short-lived child slices materialized just in time.

## Bootstrap boundary

PR-00 through PR-03 precede the trusted scope gate and cannot be certified by a
gate that does not yet exist. They run serially under one Owner/Integrator,
existing branch protection, an exact manually reviewed path manifest and no
direct push. After PR-03 merges, run the new validator on `main`, replay the
bootstrap manifests and hostile fixtures, and emit a bootstrap qualification
attestation. PR-04 is the first Program that must use the full issued-envelope
protocol. Do not retroactively claim PR-00 through PR-03 were automatically
protected.

## JIT slice materialization

1. Require completion receipts for every Program dependency and all external
   machine/artifact/right prerequisites.
2. Select one behavior, one execution lane and at most one serial resource
   family. A Program listed as a task train always splits. A single-slice
   candidate also splits when forecast work exceeds 25 files, 16 effective
   hours, 48 elapsed hours, one lane or one serial resource family.
3. Use `<program-id>-S<nn>` for a child, for example `PR-05-S01`. A true
   single-slice task may use its Program ID unchanged.
4. The child `scope.allowed_paths` must be a subset of the Program ceiling.
   It must declare the indexed Program acceptance/evidence atoms it covers.
5. Materialize a strict issued envelope; templates never authorize work.

Every blueprint slice not listed in `qualification_no_diff.slice_refs`
materializes as `execution_mode: implementation`. A listed qualification slice
materializes with an empty write scope, zero repository file/line/binary limits,
no authority grant and a read-only checkout. It may read fixed tests and exact
artifacts and write job-local scratch or external attestations only. It never
fixes production code, tests, fixtures or packaging: a defect makes the slice
`FAIL` or `BLOCKED`, then the Owner issues a separate implementation slice and
reruns qualification against a new exact identity.

The complete non-authorizing split catalogue is
`.project/EXECUTION-SLICE-BLUEPRINTS.yaml`. A materializer must still resolve
exact paths, operations, atom coverage, gates, current identities,
`not_before`, machine requirements and artifact inputs. It must reject an
issued task whose Program, blueprint slice or graph digest does not match.

Do not issue a slice or hold a grant while waiting for a clean Windows host,
legacy database copy, network credential, GPU, licensed component, human
approval or exact-byte candidate. Satisfy the resource gate first, then grant a
short grant and local coordination lock.

## Activation without a self-referential SHA

Let `P` be the protected commit the Owner reviewed before issuance. The issued
envelope stores `subject_base_sha: P`, its tree, the authority-manifest digest,
the consumed-interface manifest and the protected Program-graph digest.

The Owner creates one metadata-only commit `I`, whose only changes are the new
immutable envelope and its authority grants, and whose parent is `P`. CI derives
`activation_sha: I` from Git history; the envelope never attempts to contain
the SHA of the commit that contains itself. The task branch starts at `I`.

If the protected base advances, automatic refresh is allowed only when the
authority manifest, consumed interfaces, dependencies and every changed path
remain disjoint. Otherwise the Owner issues a new envelope and issuance ID.

## Grant versus coordination lock

An authority grant at
`.project/leases/issued/<plan-id>/<task-id>/<issuance-id>/<grant-id>.json` is a protected-branch record
that CI can verify. It binds task, issuance, envelope digest, holder, subject
base, protected resources and expiration. The semantic validator also requires
`issued_at < expires_at`, `not_before <= issued_at`, no later matching
revocation record and complete resource coverage. Revocation is an immutable
`.project/leases/revocations/<grant-id>.json`; never rewrite the activation
commit or original grant.

`git-common-dir/archeaxis-agent/state.sqlite` is only an atomic same-machine
coordination lock shared by worktrees. Losing or editing it cannot grant remote
merge authority.

## Program completion

Program acceptance atoms are addressed in declaration order as `PR-xx:A01`,
`A02`, and evidence atoms as `PR-xx:E01`, `E02`. Every child envelope binds the
Program graph digest and declares the atoms it covers. The Program aggregator
requires exact-SHA PASS receipts whose union covers every atom, with no open
failure or superseded issuance. Only a Program completion receipt unlocks a
downstream Program; a successful child does not.

PR-31 has at least four slices: preflight/freeze, candidate A, candidate B and
aggregate decision. Qualification may not edit the tests used to qualify its
candidate. All four PR-31 slices are qualification-no-diff; input freezes and
decisions are external attestations rather than repository edits.

## PR-32 digest-bound manifest scope

PR-32 has no static or pseudo Program path. Its implementation scope exists only
after the materializer reads the protected `LEGACY_MANIFEST.yaml` at subject
base `P`, verifies its AAK-JCS-1 digest and selects exactly one entry by
`asset_id`. The entry must have `decision: retire`, `status: approved`, an Owner
approval receipt and a census-expanded `source.paths` list containing exact
repository paths only; a wildcard-bearing or unmatched entry is ineligible.

The materializer hashes the selected entry and the complete normalized exact
path set, sorts that set by normalized path bytes, and partitions it into
chunks of at most 25. Each deletion slice binds the manifest, entry, complete
path-set and chunk digests, part index/count, Owner approval and subject base in
`manifest_scope`; its `scope.allowed_paths` must equal that chunk exactly. CI
repeats the expansion from `P`. Missing or additional paths, changed manifests,
pseudo paths, globs, collisions and incomplete partitions fail closed. An entry
larger than 25 files therefore becomes several slices without changing the 39
Program nodes.

PR-32 retirement preflight and final clean-clone/reachability checks are
qualification-no-diff. Only the digest-bound aggregate slices may modify or
delete repository files, and their authority grants are acquired after all
Owner and resource prerequisites are satisfied.

## Receipt causality

The gate first validates identity, authority, scope and limits. It then forms a
candidate union from the Program's `task_rules`, matching path rules and risk
rule. `selection_trace` records each candidate and the trusted pre-execution
decision. `NOT_APPLICABLE` is permitted only in that trace with concrete
evidence; it is not a required-gate result and cannot mean that a runner was
missing, setup failed or an Agent chose not to run a check.

The frozen GatePlan `gates` array contains only the de-duplicated candidates
selected as required. Every listed gate must return `PASS`. CI then creates an
external attestation over the exact subject head/tree, and `vnext-required`
verifies the selection trace, GatePlan, job conclusions, receipt and artifact
identities. An absent, skipped, cancelled, timed-out, blocked, failed or
non-applicable result for a selected gate makes the overall receipt non-PASS.

Every one of the 39 Program IDs has one Gate Registry task rule. A child slice
must trace every candidate in its parent Program rule. The Program aggregator
requires at least one accepted exact-SHA `PASS` for each such gate across the
child receipts, in addition to complete acceptance/evidence atom coverage; a
series of per-slice non-applicable decisions cannot silently remove a Program
gate.

The canonical receipt cannot be committed into the head it attests, because
that would change the head. Its `receipt_payload_sha256` is computed after
removing only that field under `AAK-JCS-1`, so it is not a self-hash. A later metadata-only audit task may copy the
attestation into `reports/`, but that copy is not the authority for the original
head.
