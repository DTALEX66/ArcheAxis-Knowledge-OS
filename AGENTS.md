# AGENTS.md - 星环知识系统（ArcheAxis Knowledge）Operating Guide

> **2026-10-22 最新UI决定**：Owner明确“不要再维护旧版界面了，全面接入STITCH界面啊（这才是新版界面）”。Stitch为唯一新版，22页中心布局沿已接收设计语言接入，复用原业务合同和状态；不保留并行旧布局偏好，不以新壳代替中心页面迁移。当前本地验证与未完成资格见[唯一执行记录](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)最新段，不能把源码覆盖当实际Core/原生/安装验收。

> **2026-10-22 最新范围收敛**：Owner明确开源池、第三方API和软件特色兼容等可选扩展“这些都是后期内置市场里的了”，要求“不要无限增加，无限扩展”。本期优先已接收Stitch UI与已有核心业务接通、必要修复和验收；仅沿现有合同保留专业扩展接口约定，不启动市场、扩展包、通用运行时或逐软件特色开发。库存与兼容矩阵不是自动执行队列，也不是本期必须清零的门槛。详细决定见[第十八节](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md#十八后期内置市场与本期范围收敛2026-10-22)；它覆盖下文旧分片中扩大本期扩展范围的解释，历史证据与未完成状态保留。

> **2026-10-19 历史路由与决定**：Owner 明确恢复当前产品任务，并要求今天停止额度监控；状态 RUNNING_BY_OWNER / PARTIAL。今天不查询额度、不因额度阈值停工。活动指针及唯一 UI 执行记录保存范围与实测；旧暂停仅为历史时点。六项增量仍冻结，V01 暂停、FT01–04 冻结。Owner 后继明确允许覆盖 `D:\All projects\ArcheAxis.Knowledge.Green-x64` 的程序安装，具体范围、备份与资格条件见活动指针 `green_update_authorization`；公开发布和真实用户数据覆盖仍未授权。文件身份及旧路径按 [路由登记](docs/current/AAOS-AUTHORITY-ROUTES.json) 核对。

> **2026-10-21 最新执行优先级**：Owner后继明确“全部按照新的UI进行打通”，要求结合审计修复漂移、更新任务与交接，按已接收Stitch界面前后端同步并行接通全部现有业务页面和共用壳。先前前端暂缓／后端优先及更早前端先行均为历史顺序；当前按UI-P01—24与BE-P01—15并行、同候选CL-01—07/J1—J6统一验收。分片仍由[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)的`execution_priority_overlay`选择，配合[完整接手提示词](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)读取；原任务ID及唯一执行记录不变，不据交接整理宣称产品完成。共享checkout单writer，独立writer隔离worktree，冻结/数据/发布边界不变。

> **2026-10-22 最新额度与交付规则**：Owner明确新增Codex订阅监控；剩余≤20%时完成已启动的当前任务/可验证单元，随后停止新任务，整理会话、后续任务和完整交接，上传本轮公开任务文件并核实本地/远端SHA一致。实际heartbeat为`aaos`，ACTIVE、每30分钟；额度读数及触发状态以活动指针中的最新观测为准。此决定覆盖旧15%及10/19停监控说明；未知额度不当0，私人原文/凭据/运行库不上传，Git/网络拒绝不得绕过。监控本身不授权新增产品开发、合并、发布或替换Green。详细规则见[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)的`execution_control.allowance_guard`。

> 全局执行标准（跨软件跨项目）：见 WORK-LAB `00-governance/global-execution-standard.md`（执行生命周期：理解→扫技能→分片→执行→验证→落地；全局边界：E盘禁访/数据不外溢/官方优先/全功率）。
> 经验教训铁律（核实优先/治理最小化/官方优先）：见本项目 `LESSONS_LEARNED.md`。

This file is the public, sanitized operating configuration for agent work inside
this repository. It describes how to work on ArcheAxis Knowledge — a local-first,
evidence-driven, bidirectional Human–AI Learning & Trusted-Knowledge Workspace —
without exposing credentials, private keys, tokens, machine-specific secrets, or
personal files. Config authority is indexed in `docs/CONFIGURATION_AUTHORITY_INDEX.md`.

## 1. Project Mission

用户提到“闭环／最短闭环／最快闭环／完整闭环／全链路跑通”时，必须先读唯一规范 [最快最短完整闭环定义](docs/truth/CLOSED_LOOP_DEFINITION.md)（`AAOS-SHORTEST-COMPLETE-LOOP-V2`），再读活动指针与实际进度。不得缩成单文件导入加一次模型回答；全面非企业知识库特色、免费外部检索、本地与云端模型均按该定义验收。该定义是目标，不是已完成声明。

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
(ArcheAxis Knowledge / 星环知识系统).

Legacy systems (Knowledge-Base, Inspiration-Research, Cognitive-OS, Obsidian)
exist as compatibility surfaces only; current routing, capability truth and
migration history are documented under `docs/truth/` and `workspace/intake/`.

> 后继 Owner 决定的接续路由（2026-10-19）：上文及继承 M0 中 Marketplace 延期是原规划时点。Owner 已明确选中内置能力目录、管理及分期接入，现读[决定第九节](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)与活动指针；这不整体激活通用 Agent Runtime、公开分发/支付或其他冻结项。关键对话出处见[冻结摘录与映射](docs/history/owner-dialogue-20261019/README.md)，共享路径仍只由原索引/manifest解析。

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
New layout/architecture follow the new task; cosmic is the default for new or invalid preferences; preserve valid saved preferences.
blueprint, blueprint-light, black and white remain switchable themes. All themes share
the new layout; each theme uses consistent semantic colors throughout the UI.
The inherited AAOS-01 package is `docs/authority/taskpack-1004-aaos01/`;
its Q00-Q15 progress alone remains in
the inherited `docs/history/repository-consolidation-20261019/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`. It does not define a
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
in historical `docs/history/repository-consolidation-20261019/current/R6-EXECUTION.md` and `docs/history/repository-consolidation-20261019/current/R6-STATE.json`. R5 remains
historical source material and its receipts retain their own SHAs. R6 preserves
the Rust canonical writer, fixed shared-resource paths, and the no-release boundary;
Local Green qualification is separate from publication. Preserve unknown private
state and user assets; destructive cleanup needs an exact reviewed path list.
At low remaining account-wide Codex allowance, prepare the handoff and publish only
verified, task-owned changes under the owner's current authorization.

The inherited priority overlay is `docs/history/repository-consolidation-20261019/current/M0-DIRECTION-OVERRIDE-20260920.md`
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
