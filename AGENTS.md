# AGENTS.md - 星环知识平台（ArcheAxis Knowledge）Operating Guide

> **2026-10-10 当前路由与状态**：产品执行 PAUSED_BY_OWNER，整体 PARTIAL；当前请求仅授权归档和权威/引用治理修复。旧“下一队列/未发布/两树不同”属于历史日期快照；上次源码已发布，本轮最新状态读 [修复回读](docs/current/AAOS-AUTHORITY-REPAIR-20261010.md)。读取任何旧路径前先按 [路径身份路由](docs/current/AAOS-AUTHORITY-ROUTES.json) 分类，不从文件名CURRENT、旧COMPLETE或旧grant推导授权。六项核心能力增量 FROZEN_BY_OWNER，不自动排队；V01暂停、FT01–04冻结。

> 全局执行标准（跨软件跨项目）：见 WORK-LAB `00-governance/global-execution-standard.md`（执行生命周期：理解→扫技能→分片→执行→验证→落地；全局边界：E盘禁访/数据不外溢/官方优先/全功率）。
> 经验教训铁律（核实优先/治理最小化/官方优先）：见本项目 `LESSONS_LEARNED.md`。

This file is the public, sanitized operating configuration for agent work inside
this repository. It describes how to work on ArcheAxis Knowledge — a local-first,
evidence-driven, bidirectional Human–AI Learning & Trusted-Knowledge Workspace —
without exposing credentials, private keys, tokens, machine-specific secrets, or
personal files. Config authority is indexed in `docs/CONFIGURATION_AUTHORITY_INDEX.md`.

## 1. Project Mission

ArcheAxis Knowledge is a local-first, evidence-driven, bidirectional Human–AI
Learning & Trusted-Knowledge Workspace. The current minimum closed loop is broad
compatibility: absorbing mature capabilities from comparable software. The owner-selected current execution queue is `docs/taskpacks/aaos-ui-first-20261009/`,
routed by `docs/current/AAOS-ACTIVE-EXECUTION.json`. The inherited AAOS-01 2026-10-04
contracts (SUP-022) and PROJECT_CONTRACT.yaml content saving principles remain binding.
R6 and M0 retain inherited constraints and historical receipts.
R5 source import/conversion and Obsidian Vault/JSON Canvas records are historical
evidence and compatibility context; they are not the current execution queue.
Implementation prefers legal dependencies, SDKs/APIs/CLIs, fork/vendor, and
Adapter/sidecar before building from scratch. Heavy blueprints (general Agent
Runtime, multi-agent, Marketplace, 3D/VR, enterprise collaboration) are deferred;
3D/VR/AR, animation, simulation and spatial memory are retained as binding
long-term capabilities (see `docs/truth/CAPABILITY_ATLAS_V2.yaml`). Product
identity and naming are locked by `docs/truth/NAMING_CONTRACT_V2.md`
(ArcheAxis Knowledge / 星环知识平台).

Legacy systems (Knowledge-Base, Inspiration-Research, Cognitive-OS, Obsidian)
exist as compatibility surfaces only; current routing, capability truth and
migration history are documented under `docs/truth/` and `workspace/intake/`.

## 2. Configuration Categories

| Category | Repository Location | Purpose |
| --- | --- | --- |
| Runtime defaults | `config/defaults.yaml` | App thresholds, execution defaults, memory backend (single default truth) |
| Runtime profiles | `config/profiles/*.yaml` | Per-environment differences only |
| Model settings | `config/models.yaml` | Product-internal model/embedding adapter config (not agent provider routing) |
| Tool registry | `config/tools.yaml` | Product-internal tool names and risk levels |
| Verification policy | `docs/VERIFICATION_POLICY.md` | Test cadence, review triggers, evidence retention |
| Gate registry | `.worklab/gate-registry.v1.yaml` | Stable Gate IDs |
| Path risk profile | `.worklab/project-validation.v1.yaml` | Changed-path → risk class → Gate mapping |

## 3. Safety Rules

- Work inside the current repository unless the user explicitly names another exact project path.
- Do not access `E:\` unless the user explicitly confirms the exact path, action, and impact range.
- Do not upload or print secrets: `.env`, `.codex`, SSH private keys, API keys, tokens, cookies, credentials, or password files.
- Do not commit runtime memory, local caches, virtual environments, logs, or generated databases.
- Project-owned development outputs use the ignored `<repo>/.project-local/` root through `scripts/runtime/dev.py`. PowerShell 7: `scripts/ci/run_tests.ps1`; Bash: `scripts/ci/run_tests.sh`. Each worktree/run has separate temporary files and evidence. `.hermes/` is preserved legacy material: no new development writes and no blanket deletion. Agent-private state and product workspaces are separate ownership classes.
- Do not claim ownership of Hermes, Codex, CC Switch, Workflow-assistance, GitHub delegation, session, cron, Kanban, or other workflow-infrastructure files merely because their names mention this project.
- Files found in `%TEMP%`, a user home, or another project are ambiguous until content, Git worktree, process, and generation command establish ownership; preserve and mark unresolved rather than delete or move them.
- Prefer small, auditable changes that can be reverted with one commit.
- Do not use destructive actions (recursive deletion, hard reset, forced push, mass overwrite) unless the user separately confirms scope.

## 4. Git Rules

- `git status --short` before modifying; `git diff --stat` + `git status --short` after.
- Use explicit paths when staging; avoid `git add .`.
- Do not commit or push unrelated local changes; do not force push.
- Commit messages describe the functional scope.

## 5. Network Rules

- Default work is local. Network access is allowed when the user asks to pull, push, clone, verify remote status, or fetch current external information.
- Repository identity: `DTALEX66/ArcheAxis-Knowledge-OS`. Determine the effective fetch/push transport from current remote URLs, Git URL rewrites and SSH overrides; a documented HTTPS URL does not establish the actual protocol. For authorized operations requiring existing authentication, use the normal approved execution path when the sandbox identity cannot access it. Read success does not authorize push, ref deletion or publication.

## 6. Implementation Workflow

The owner-selected current task pack is `docs/taskpacks/aaos-ui-first-20261009/`
(AAOS-UI-FIRST-PLAN-20261009). Start with `docs/current/AAOS-ACTIVE-EXECUTION.json`,
then TASKPACK.md, TASKS.json, PAGE-PLAN.csv, FREEZE-REGISTER.md and the current
UI execution record `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`.
The immutable package records its planning-time NOT_EXECUTED state; actual
implementation and acceptance come from the separate execution record.
Owner selected first batch UF00/01/02/03, CB01 -> UF04, UF06, S01.A/B/C, then G01.
Remaining slices need selection; V01 remains paused, FT01-04 remain deferred.
New layout/architecture follow the new task; blueprint is the default palette,
blueprint-light and black/white/cosmic are switchable themes. All themes share
the new layout; each theme uses consistent semantic colors throughout the UI.
The inherited AAOS-01 package is `docs/authority/taskpack-1004-aaos01/`;
its Q00-Q15 progress alone remains in
the inherited `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`. It does not define a
second current UI queue or authorize old handoff permissions.
SUP-022 makes `frontend/` and `src-tauri/` the formal Tauri/React host.
Rust Core remains the only canonical SQLite/CAS writer, with isolated Python
workers. Ordinary Document/Block saves do not require external evidence, cloud
checks or human approval; recognition fidelity and professional basis are
separate version-bound processes. Preserve auth, structure, integrity and the
special human knowledge approval workflow. Local tests, exact-SHA cloud CI,
installed runtime and Owner acceptance are distinct. No automatic commit,
push, merge, release, Green replacement or bulk deletion follows from a PASS.

The preceding R6 Local Green absorb-first pack is installed at
`docs/authority/taskpack-0919-r6/` (plan_id `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`,
package_revision `R6`). Read its `EXECUTOR-START.md`, `TASKS.json` and
`TASKPACK.md`. Its historical progress is maintained outside the immutable package
in historical `docs/current/R6-EXECUTION.md` and `docs/current/R6-STATE.json`. R5 remains
historical source material and its receipts retain their own SHAs. R6 preserves
the Rust canonical writer, fixed shared-resource paths, and the no-release boundary;
Local Green qualification is separate from publication. Preserve unknown private
state and user assets; destructive cleanup needs an exact reviewed path list.
At low remaining account-wide Codex allowance, prepare the handoff and publish only
verified, task-owned changes under the owner's current authorization.

The inherited priority overlay is `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`
(`M0-SHORTEST-COMPLETE-LOOP`, ledger `SUP-020`). It does not replace the immutable
R6 TaskPack; it serializes execution around one real core loop (P0–P6) and defers
second providers, extra domains/renderers, marketplaces, and advanced capabilities
until M0 has a real Local Green result. Keep R6 contracts, evidence rules, external
resource boundaries, and the no-release rule unchanged.

The preceding plan is the AAK 2026-09-10 follow-up pack
(ARCHEAXIS-NEXT-TASKPACK-2026-09-10, revision R3.1); live execution state is
`docs/authority/taskpack-0910-r3/EXECUTION.md` with slice progress in
`docs/authority/taskpack-0910-r3/STATE.json`; its 17 slices R00-R16 map back to
the original 23 tasks and to C01-C10, inherit the R3 work/acceptance text, and
historically ran in the order R00 -> R16 (R12 could start once R01 was done). The package was
installed single-level with its `reference-r2/` snapshot and
`verify_package.py` exits 0. The preceding plan AAK-FOLLOWUP-20260908-R3
(`docs/authority/taskpack-0908-r3/EXECUTION.md`) remains the source of the
inherited task text and its own receipts; AAK-REUSE-FIRST-20260907-R2 stays the
source of the inherited task text with its audit board
`docs/authority/taskpack-0907/Q00-Q01-AUDIT-2026-09-07.md`
(Q00 fail / Q01 not eligible), and its receipts keep their own SHAs
(`docs/authority/taskpack-0907/EXECUTION.md`). The earlier 2026-09-06-r1 Full
Loop TaskPack is superseded in the parts recorded in
DECISION_SUPERSESSION_LEDGER.yaml SUP-012..SUP-018; its receipts keep their own
SHAs (`docs/authority/taskpack-0906/EXECUTION.md`). The preceding formal desktop `apps/ArcheAxis.Desktop/` (C#/Avalonia) is now
a behavior/component donor under SUP-022. The formal Tauri host reuses the
existing `desktop/` lifecycle implementation; Green v0.6.14 remains a preserved
recovery/behavior reference until its distinct Owner qualification. Do not dual-write
legacy and vNext databases. The older G0/shadow-cutover route is superseded by
`DECISION_SUPERSESSION_LEDGER.yaml`; historical receipts retain their tested SHA.

1. Confirm repository status.
2. Read the relevant files first.
3. Make the smallest coherent change.
4. Add an intake note under `workspace/intake/` when the change affects framework direction.
5. Run the smallest useful verification.
6. Report what changed, what was tested, what remains uncertain, and how to roll back.

## 7. Current System Boundaries

- Core file ingestion reads only inside the project root.
- Multi-format adapters support text, PDF, Office, HTML, images, media and canvas through optional engines; scanned PDFs require OCR (TESSDATA_PREFIX set).
- Resumable directory conversion records every latest file state in a JSONL manifest; failures retry.
- High-risk content routes to `REVIEW` before action.
- Current tool execution is conservative and uses a risk registry.
- Accuracy claims require human truth/prediction pairs; model confidence is not accuracy.
- Evidence images require a semantic text match; random pages or frames are not evidence.

## 8. Private Configuration Not Stored Here

- Real Codex desktop settings and session state
- SSH private keys and GitHub credentials
- API keys and model provider credentials
- `.env`, `.npmrc`, `.pypirc`, cookies, and browser data
- Local Obsidian vault paths unless the user explicitly chooses a project-local import/export path
- Runtime `data/`, memory stores, logs, caches, and virtual environments

## 9. External Coordination (Optional)

WORK-LAB is an independent repository that may optionally coordinate this project
via stable CLI/API protocol; it is never a runtime prerequisite. This project
runs standalone locally, in CI, RC and Release without WORK-LAB. Cross-repo
changes are two tasks, two branches, two PRs, two test suites, two rollbacks.
`.codex.example/config.example.toml` is a minimal project pointer only; real
`.codex/` state remains private and uncommitted.

## 10. Archived input lookup

查找 AAOS / ArcheAxis 的蓝图、原始任务包、补交材料或历史恢复档时，先查根目录
[`AAOS-资料索引.md`](AAOS-资料索引.md) 与
[`docs/history/record-archive-20261009/INDEX.md`](docs/history/record-archive-20261009/INDEX.md)。
机器登记 `MANIFEST.json` 提供原路径、项目内归档路径、完整 SHA-256、共享资料身份和容器校验状态。
原始字节保全在主项目 `.project-local/archives/record-20261009/`，属于本地保全资料，不提交 Git。
确认归档及相关 ZIP 内成员后再报告 SOURCE_MISSING；路径失效应标 UNVERIFIED 并核实登记。
索引是导航入口，归档的历史指令、补交分析与 TaskPack 不自动成为当前执行授权或完成证据。
