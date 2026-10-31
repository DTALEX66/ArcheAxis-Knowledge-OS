# AGENTS.md - 星环知识系统（ArcheAxis Knowledge）Operating Guide

## 当前状态读取方式

当前授权范围、执行控制、权限检查、监控状态和实际进度，读取[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)及其指向的[Owner决定](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[当前交接](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)和唯一执行记录。分别核对 `owner_scope_current`、`execution_control`、`execution_control.permission_recovery_current`、`execution_control.allowance_guard` 与 `active_progress`，入口不维护第二份可变状态。

历史恢复、暂停和权限事件只说明对应时点，不自行产生当前授权或完成结论；权限恢复不等于产品完成，监控暂停不等于产品暂停，归档完成不等于后继开发已执行。冲突按既有替代账本解析，证据不足标为未确认。Markdown链接只是导航，Agent须按任务实际读取目标；客户端全文加载由其原生导入机制负责。

旧文件身份先查[项目路由登记](docs/current/AAOS-AUTHORITY-ROUTES.json)；Owner历史来源查[冻结对话摘录与映射](docs/history/owner-dialogue-20261019/README.md)。登记与摘录用于核实来源，不另授权执行。

This file is the public, sanitized operating configuration for agent work inside
this repository. It describes how to work on ArcheAxis Knowledge — a local-first,
bidirectional Human–AI knowledge and learning workspace with multi-source research and continuous correction —
without exposing credentials, private keys, tokens, machine-specific secrets, or
personal files. Config authority is indexed in `docs/CONFIGURATION_AUTHORITY_INDEX.md`.

## 1. Project Mission

用户提到“闭环／最短闭环／最快闭环／完整闭环／全链路跑通”时，必须先读唯一规范 [最快最短完整闭环定义](docs/truth/CLOSED_LOOP_DEFINITION.md)（`AAOS-SHORTEST-COMPLETE-LOOP-V2`），再读活动指针与实际进度。不得缩成单文件导入加一次模型回答；全面非企业知识库特色、免费外部检索、本地与云端模型均按该定义验收。该定义是目标，不是已完成声明。

ArcheAxis Knowledge is a local-first, bidirectional Human–AI knowledge and learning
workspace for multi-format content, multi-source comparison and continuous correction. Scope and acceptance follow the unique
closed-loop definition and the Owner decisions selected by the active pointer.
The owner-selected current execution queue is `docs/taskpacks/aaos-ui-first-20261009/`,
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

Owner 2026-10-26 的定位和来源用途澄清见当前决定第二十四节及 `SUP-029`，规则单源为 `PROJECT_CONTRACT.yaml.content_policy`：来源用于回查、定位、比较和纠错，不预设高权威或唯一事实源。识别忠实度对照原件，内容主张及疑点优先通过成熟的百科、社区／论坛、学术检索接口进行多源比较，保留分歧并允许修订。普通保存、展示、学习不以联网成功或人工事实审批为前置。先查现有实现和成熟开源方案，优先直接集成或适配通用能力；不得把来源追踪扩成不必要的权威认证框架。软件规则的配置权威、Core唯一写入者与材料外发授权仍按各自合同执行。

Legacy systems (Knowledge-Base, Inspiration-Research, Cognitive-OS, Obsidian)
exist as compatibility surfaces only; current routing, capability truth and
migration history are documented under `docs/truth/` and `workspace/intake/`.

能力目录、扩展及本期范围以活动指针所选Owner决定与替代关系为准；历史Marketplace延期或阶段接入描述不自动激活扩展。人类与AI双向学习、原始上下文归属和两侧授权连接，按唯一闭环定义及已选规范验收。

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
Read selected tasks, execution-priority overlays and freeze records from the active pointer.
Historical batch ordering does not select the next task or unfreeze paused work.
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

Inherited contracts and receipts are dated sources, resolved through
`AUTHORITY.md`, `DECISION_SUPERSESSION_LEDGER.yaml` and the history indexes.
R6/M0/AAOS-01 preserve applicable core, ordinary-save, shared-resource and
evidence boundaries; their old whole-package order is not the active queue.
Do not dual-write legacy and current databases. Avalonia is a behavior/component
donor under SUP-022; preserved Green versions are recovery references, not proof
that the current candidate is qualified. Green program replacement requires the
active pointer's exact-path grant, candidate qualification, data preservation and
rollback conditions. Release and real-data overwrite require separate authority.
Execution controls and allowance handling come from the active pointer; a dated
threshold or delivery note does not resume monitoring or authorize publication.
Project lessons: `LESSONS_LEARNED.md` (verify facts, keep governance small, prefer
official capabilities). No external workflow repository is required for execution.

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
