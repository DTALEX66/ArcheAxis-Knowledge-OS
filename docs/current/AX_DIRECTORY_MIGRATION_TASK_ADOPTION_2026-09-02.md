# AX-DIR-MIG-R1 目录迁移与清理任务包纳入清单

> Source examined: `ARCHEAXIS-DIRECTORY-MIGRATION-CLEANUP-TASKPACK-2026-09-01.md`.
>
> Status: PLANNED, NOT STARTED. The source document is a migration proposal,
> not authority to move, delete, publish, or change project configuration.

## Adopted outcome, preserved boundaries

The desired outcome is adopted as a separate repository-layout convergence
track: one production Windows UI/desktop host, no duplicate tracked product
trees, clear ownership of governance integrations, and no project runtime data
outside the repository. It must not alter product-domain semantics, rewrite
the language architecture, touch user learning data, create a release, or
weaken the G0 single-writer freeze.

The following current constraints take precedence over the source proposal:

- Project rules currently require generated runtime state and evidence under
  ignored `.hermes/`; the proposed `.project-local/` destination is therefore
  **not authorised for creation or use** until a configuration-authority
  decision updates the owning project rules and every relevant launcher.
- The current tree has intentional maintenance changes. Directory migration
  requires a frozen, reviewed tree and cannot treat existing dirty paths as
  disposable duplication.
- The existing Green `v0.6.14` is the fixed Windows maintenance target. This
  track creates no version, tag, installer, GitHub Release, or replacement
  Green distribution.
- No command may delete `.hermes`, runtime data, a SQLite database, user
  material, a tracked directory, a compatibility shim, or a worktree until
  its own migration manifest, hashes, readback and explicitly authorised
  deletion gate are complete.

## Reconciled task decomposition

| Source task | Applicable ArcheAxis task | Status / prerequisite |
| --- | --- | --- |
| AX-DIR-000 | Establish an isolated migration writer and no-spill boundary. | BLOCKED_BY_POLICY. First make an explicit `.hermes` versus `.project-local` configuration-authority decision; do not create a second runtime root under ambiguous rules. |
| AX-DIR-010 | Produce a read-only path, hash, owner, reference and data-class inventory for every proposed source directory. | PENDING. It may start only from a frozen snapshot and must classify user/runtime data as `PRESERVE_USER_DATA`, never as deletion candidates. |
| AX-DIR-020 | Introduce a neutral project-governance contract and bounded launcher after the authority decision. | PENDING. No global Codex/Hermes/WORK-LAB configuration is in scope. |
| AX-DIR-030 | Move project-owned governance examples/task packs only after compatibility readers and reference tests exist. | PENDING. `.worklab` is currently a project gate registry, not evidence that WORK-LAB is a runtime dependency. |
| AX-DIR-040 | Consolidate `Inspiration-Research` into `inspiration_research` through a case-safe, hash-proven migration. | PENDING. Requires an exact file comparison, consumer/import inventory, wheel-from-temp import test and a reviewed staged tree. |
| AX-DIR-050 | Converge the Windows UI and Tauri host into one canonical path. | PENDING_AFTER_G1-001. The current edition/`#[path]` shared-source conflict must first be removed through a real shared crate; moving both trees first would preserve or obscure the defect. OSUI/desktop code is retained until a function-by-function production-use and test decision exists. |
| AX-DIR-060 | Rewrite current code/config/CI references after each proven move. | PENDING. Historical documents retain legacy-path wording and receive only a legacy-path annotation. |
| AX-DIR-070 | Migrate project-local ignored runtime/evidence data by copy, hash, readback, quarantine and restart proof. | BLOCKED_BY_POLICY_AND_RUNTIME. It additionally requires the relevant Green/runtime processes to be stopped normally and an explicit data-migration/delete gate; current Green data is never inspected or copied. |
| AX-DIR-080 | Execute the post-move multi-language, fresh-clone and Windows product matrix. | PENDING. It cannot be run against proposed `apps/windows/*` paths before those paths exist; exact-SHA full CI and installed-product evidence remain separate gates. |
| AX-DIR-090 | Delete superseded tracked directories and verified ignored residues. | BLOCKED_UNTIL_ALL_PRIOR_GATES. Exact manifests, hashes, fresh-clone results, rollback commit and explicit deletion authorisation are required; no wildcard or recursive cleanup is permitted. |

## Required sequencing with the language migration

```text
G0 evidence gates + configuration-authority decision
  -> AX-DIR-010 inventory
  -> AX-DIR-020/030 governance migration
  -> G1-001 shared crate and single desktop boundary
  -> AX-DIR-040 research-directory consolidation
  -> AX-DIR-050/060 UI + desktop move and reference rewrite
  -> AX-DIR-070 data copy/readback/quarantine
  -> AX-DIR-080 full qualification
  -> AX-DIR-090 explicit deletion
```

The directory migration must not be used to bypass G0. Conversely, G1 may
work on a normal shared crate without prematurely moving the root UI/desktop
directories.

## Pre-execution acceptance conditions

Before a write phase begins, all of these must be evidenced for its exact
snapshot:

1. A configuration-authority decision resolves `.hermes` versus
   `.project-local`, including launchers, test runners, ignores and rollback.
2. The source tree is frozen and the migration inventory binds every affected
   path to a hash, owner, data class, target, verification and rollback.
3. The production-use matrix distinguishes canonical source, tested component,
   dormant proposal, duplicate and user/runtime data for `frontend`, `OSUI`,
   `src-tauri`, `desktop`, `Inspiration-Research`, governance examples and
   task packs.
4. G0 has its required source/CI/corpus/runtime evidence; the current partial
   exact-SHA CI and component-only Green smoke are not sufficient.
5. The deletion phase has separate user authorisation after fresh-clone,
   multi-language tests and Windows product-path readback all pass.

## Release terminology reconciliation

The source task pack's final label `E5 RELEASED` is not a current release
instruction. For the present maintenance route, successful layout work is
reported as `LAYOUT_ACCEPTED_UNPUBLISHED`; any future tag, distribution or
GitHub Release remains a separate user-authorised action bound to its exact
SHA.

## Out of scope for this intake

This intake does not create `.project/` or `.project-local/`, create a branch
or worktree, move paths, rewrite references, run a deletion, migrate ignored
data, stop Green, modify global configuration, or publish a release. It makes
the requested work visible and dependency-correct without claiming the target
tree already exists.
