# AAOS 跨执行者交接包（2026-10-01）

状态：`AUDITED / PARTIAL`。本文件是导航和交接，不替代 `AGENTS.md`、R6 TaskPack、`R6-STATE.json` 或 M0 方向覆盖。根 `AUTHORITY.md` 未发现，记录为 `AUTHORITY_REFERENCE_MISSING`；请从 `docs/CONFIGURATION_AUTHORITY_INDEX.md` 进入权威链。清理任务已暂停；不得删除、迁移或整理缓存、历史文档、数据库、恢复包，不访问 E/F 盘。

## 先读顺序

1. `AGENTS.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`docs/authority/taskpack-0919-r6/EXECUTOR-START.md`、`TASKS.json`、`TASKPACK.md`、`docs/current/R6-STATE.json`、`R6-EXECUTION.md`、`M0-DIRECTION-OVERRIDE-20260920.md`。
2. `docs/current/AAOS-ALL-TASKS-LEDGER-20261001.json` 与 `AAOS-OPEN-WORK-REGISTER-20261001.md`。270 个唯一来源键、17 组来源，包含历史任务追踪；目录项不伪装成新任务，来源级审计不等于运行闭环。
3. UI：`AAOS-UI-COVERAGE-MATRIX-20261001.md`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`、`AAOS-UI-ASSET-MANIFEST-20261001.json`、`AAOS-UI-NAVIGATION-IA-20261001.md`、`AAOS-UI-BACKEND-MAP-20261001.md`、`AAOS-UI-HANDOFF-20261001.md`。
4. `AAOS-ERRORS-BLOCKERS-20261001.md`；交给 DSH 与 MiniMax Design 的独立提示词位于 `docs/current/agent-prompts/`。

## 来源边界

用户提供的 12 张产品母版及 11 张品牌视觉位于 `D:/All projects/UI套件/`；UI 提示词位于 `D:/All projects/UI套件/11_CODEX_UI开发提示词/02_ArcheAxis_AAOS_UI开发提示词_CODEX.md`。9 月 28 日整合包和 9 月 30 日 UI 包位于 `D:/All projects/Record/`；9 月 29 日规划归档位于 `docs/history/planning-blueprint-absorption/2026-09-29/`；10 月 1 日三项目资料的 AAOS 摘录位于 `docs/history/external-inputs/2026-10-01/`。这些文件提供需求、候选、证据，不能越过当前 Authority。附件真实后端交接：`C:/Users/ALEX/.codex/attachments/94f7489e-e267-4906-8fff-7a9c2689a11f/已粘贴的文本.txt`；仅在授权任务范围内读取，不复制私人状态。

两份 `Record` ZIP 的原样副本与 SHA-256 收据在 `docs/history/external-taskpacks/2026-10-01/`；来源原件未改动，包内指令仍属资料。UI 套件原图继续从用户指定路径读取，项目部署资产及引用索引见 `AAOS-UI-ASSET-MANIFEST-20261001.json`。

## 当前交付事实

正式 Desktop 是 `apps/ArcheAxis.Desktop/`（Avalonia），Core 是独立 Rust；`frontend/`、旧 Green 等是历史或行为参考。原 Green 中已安装阶段候选 `AAOS-v18a00075-20261001-x64`，启动入口 `D:/All projects/ArcheAxis.Knowledge.Green-x64/启动星环知识-AAOS-18a00075.vbs`。它证明该阶段 Native UI/Core 可启动，**不是本次新源码的安装版本，也不是完整视觉或真实后端闭环验收**。当前 UI 隔离工作树是 `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/aaos-ui-phase2-integrate`，分支 `codex/aaos-ui-phase2-20261001`；PR #156 为 Draft。正式根 `D:/All projects/ArcheAxis-Knowledge-OS` 的 `codex/Audit` 有用户未知修改和历史未跟踪文件，不能覆盖、清理或据此宣称两棵树 HEAD 一致。

## 执行顺序与写集

优先正式 UI 母版逐页落地；随后最小必要治理；最后真实后端加前端的最短完整多格式闭环。UI 所需真实 Core 合同可同步实现。DSH 另建后端分支，MiniMax Design 从 UI 分支复制独立设计分支；同一文件仅一个 writer。品牌资产应保留原始路径、部署路径、SHA、许可证和引用索引；不能使用的配图按母版重制，图标保持可维护矢量。外部设计软件是否具备 Git/代码/本地文件写入能力，现场验证后再声称。每个任务以源码、构建、原生界面、真实 Core 回读、精确远端 SHA/CI 的相应证据标记，不跨级推断。
