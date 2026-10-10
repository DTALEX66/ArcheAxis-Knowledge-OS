# Language Boundary Authority Index

> **2026-10-10 当前路由与状态**：产品执行 PAUSED_BY_OWNER，整体 PARTIAL；当前请求仅授权归档和权威/引用治理修复。旧“下一队列/未发布/两树不同”属于历史日期快照；上次源码已发布，本轮最新状态读 [修复回读](current/AAOS-AUTHORITY-REPAIR-20261010.md)。读取任何旧路径前先按 [路径身份路由](current/AAOS-AUTHORITY-ROUTES.json) 分类，不从文件名CURRENT、旧COMPLETE或旧grant推导授权。六项核心能力增量 FROZEN_BY_OWNER，不自动排队；V01暂停、FT01–04冻结。

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


Machine-local tool/model/material roots are resolved from the
[user-confirmed shared resource path index](SHARED_RESOURCE_PATH_INDEX.md),
never guessed from old taskpacks or PATH.

Current decisions: [project contract](../PROJECT_CONTRACT.yaml) and
[supersession ledger](../DECISION_SUPERSESSION_LEDGER.yaml), including SUP-020
and SUP-022 (the formal Tauri 2 + React/TypeScript/Vite host replaces SUP-021's
Avalonia shell priority; Rust Core and isolated Python boundaries are retained).
Execution: [active execution pointer](current/AAOS-ACTIVE-EXECUTION.json) resolves the selected UI task source and scoped progress. [R6 task package](authority/taskpack-0919-r6/EXECUTOR-START.md) and [M0](current/M0-DIRECTION-OVERRIDE-20260920.md) retain inherited constraints; their old whole-package sequence is frozen.
R5 and earlier packs are historical evidence only.
The 0906/0908/0910 ledgers retain their original historical evidence.
Historical baseline: [2026-09-03 normalization record](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md).
Its old G0 cutover instructions are superseded; its recorded evidence is retained.

| Responsibility | Current implementation target | Boundary |
| --- | --- | --- |
| Formal Windows desktop | Rust/Tauri 2 in `src-tauri/`, React/TypeScript/Vite in `frontend/` | UI and Core lifecycle through finite authenticated host commands; no direct SQL or duplicated business rules; no arbitrary paths/Shell |
| Preserved Avalonia reference | C#/Avalonia in `apps/ArcheAxis.Desktop/` | Behavior and recovery donor; preservation does not create a second default shell |
| vNext domain, jobs, storage and API | Rust in `crates/` | Separate vNext database; one authoritative writer |
| Parsing, OCR, ASR, model computation | Python in `services/python-workers/` | Isolated capabilities; no main database handle or human approval |
| Protocol | `packages/contracts/` | Generated TypeScript DTOs and actual Rust/Python output must pass the same contract; preserved C# consumers retain their own validation |
| Existing Green v0.6.14 | Legacy Python, React/Tauri | Recovery and behavior reference; existing data is not migrated by declaration |

The old G0 shadow-writer cutover route is superseded by SUP-003/006.
Rust may own a separate vNext database immediately. It may not write to the
legacy database. Migration requires a consistent read-only export, validated
staging import and recoverable activation. No dual write or live synchronization.

A language decision, build, fixture or inventory is not proof of completed
capability absorption. Inherited migration acceptance requirements remain defined by R6 A13 and
M0 P5: nonempty legacy-copy export, staged import, semantic difference/loss
accounting, identity-preserving restart/readback, and the separate P6 owner gate
for Green replacement/rollback. Historical T13 evidence is not a current gate.
No directory move substitutes for migration. Legacy schemas and aliases remain
compatible until their own tested migration; do not rename user databases.

Development state uses `scripts/runtime/dev.py` and `.project-local/`.
Product workspace selection is separate. Legacy `ARCHEAXIS_DATA_DIR` and
compatibility `COGNITIVE_DATA_DIR` are not development-cache settings.

See [runtime delivery](RUNTIME_DELIVERY_AUTHORITY_INDEX.md),
[directory ownership](DIRECTORY_AUTHORITY_INDEX.md) and
[naming rules](NAMING_ENCODING_CONVENTIONS.md).
