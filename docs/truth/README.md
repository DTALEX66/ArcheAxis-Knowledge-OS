# Truth Spine

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](../current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](../taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


本目录保存 ArcheAxis Knowledge 的稳定决策基线与可审计执行记录。它不以规划、版本号、测试夹具或模型判断代替真实运行证据。

## 当前执行权威（2026-10-09 覆盖）

- **当前活动指针**为 [`AAOS-ACTIVE-EXECUTION`](../current/AAOS-ACTIVE-EXECUTION.json)，解析新UI任务来源和UI进度；[`AAOS-01 任务书`](../authority/taskpack-1004-aaos01/01_完整执行任务书.md)的有效合同与原Q证据继承，不自动排队整个旧包。
- **前一个任务包**为 [`R6 Executor Start`](../authority/taskpack-0919-r6/EXECUTOR-START.md)：R6 的约束、证据规则与回执按继承保留，进度见 [`R6-EXECUTION`](../current/R6-EXECUTION.md) 与 [`R6-STATE`](../current/R6-STATE.json)；[`M0`](../current/M0-DIRECTION-OVERRIDE-20260920.md) 优先级覆盖仍作继承约束。
  本页原先只列 R6 为"当前活动基础包"，该读法已过期；以 `AGENTS.md` 为准更正，R6 的历史记录不改写。
- **继承 AAOS-01（Q00—Q15）范围台账入口**：[`AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`](../current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)；同名旧台账已归档并保留兼容入口，不再新增第二份状态真值。任务包与进度账本不是两份并行账本：前者是任务源，后者是这条工作流的进度记录。
- [`CURRENT_STATE_TRUTH.md`](CURRENT_STATE_TRUTH.md) 保留 2026-08-09 的真值方法与当时状态；其旧任务顺序和阶段状态是 **HISTORICAL / SUPERSEDED**，不能作为当前执行队列。
- [`AUTHORITY_CONTRACT.md`](AUTHORITY_CONTRACT.md) 保留 2026-08-09 的权威顺序快照；其把旧冻结包列为当前唯一任务源的规则已被 **HISTORICAL / SUPERSEDED**。原文保留，不据此覆盖平台指令、用户当前明确决定或当前活动指针。
- [`ARCHITECTURE_FINAL.md`](ARCHITECTURE_FINAL.md) 保留 2026-08-14 的架构收敛提案。**其中"当前正式桌面壳以 C#/Avalonia 为准"一句已被取代**：产品主线为 Tauri 2 + React/TypeScript/Vite（`frontend/`、`src-tauri/`）＋ Rust Core 单写者，Avalonia 桌面（`apps/ArcheAxis.Desktop`）作为行为/组件供体并冻结。机器可核的取代记录：[`DECISION_SUPERSESSION_LEDGER.yaml`](../../DECISION_SUPERSESSION_LEDGER.yaml) **SUP-021 → SUP-022**（`supersedes` 指向正式壳优先级，`reason` 记录 2026-10-04 业主裁决）；冻结与复用证据见 [`AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`](../current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)（"审计件断言纠正与 Avalonia 供体冻结"一节）：`src-tauri/src/main.rs` 直接内含 `desktop/src-tauri` 的生命周期实现，`frontend/src/components/AaosIcon.tsx` 首行注明几何逐字复用。原文保留，不据此恢复 Avalonia 作为主线。
- [`check_r6_taskpack_authority.py`](../../scripts/maintenance/check_r6_taskpack_authority.py) 只校验 R6 权威包的冻结身份；它**不校验全部 2026-08 冻结文档和增补包的 SHA-256**。旧包的 `.sha256` 文件和 Git 历史是历史完整性依据，不应误称为当前仓库 convention gate 的覆盖范围。

## 权威顺序

发生冲突时，按以下顺序处理：

1. 系统与开发者规则；
2. 用户当前明确指令；
3. 全局及项目 `AGENTS.md`；
4. 本目录已经批准的稳定真相；
5. 冻结任务基线；
6. 历史 TaskPack、蓝图、handoff 和导入设计资料。

## 文件

- [`FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`](FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md)：冻结的任务定义、依赖和验收标准。后续执行不得修改。
- [`FROZEN_EXECUTION_BASELINE_v1_2026-08-09.sha256`](FROZEN_EXECUTION_BASELINE_v1_2026-08-09.sha256)：冻结文件的 SHA-256。
- [`EXECUTION_STATUS_LOG.md`](EXECUTION_STATUS_LOG.md)：只追加的进度、证据、阻塞和偏差记录。
- [`../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`](../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md)：供 DeepSeek 长任务执行的控制协议。
- [`../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`](../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md)：用户批准的网页知识摄取原始强制增补包；不改写冻结 v1。
- [`../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`](../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md)：用户最新批准的能力优先全知识生命周期增补；较新解释允许替换 Crawl4AI/Spider 品牌，但不允许删除其能力 profile。
- [`../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.sha256`](../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.sha256)：能力优先增补包的冻结 SHA-256。

## 冻结规则

冻结基线的任务 ID、描述、依赖、边界和验收条件不得被后续状态更新覆盖或改写。发现新的事实时：

1. 在 `EXECUTION_STATUS_LOG.md` 追加证据；
2. 如原任务不可执行，追加 `DEVIATION` 或 `BLOCKED`，保留原文；
3. 如确需新任务，先追加 `CHANGE_PROPOSAL`；
4. 只有用户明确批准新基线时，才新增版本文件；不得替换 v1。

当前 gate 的覆盖范围以 `scripts/maintenance/check_r6_taskpack_authority.py` 为准：它校验 R6 权威包身份，**不校验全部 2026-08 冻结文档和增补包的 SHA-256**。旧版全量哈希门禁说明是 2026-08 状态记录，已由 R6/M0 执行权威取代；冻结原文与 `.sha256` 收据仍保留作历史来源证据。Git 历史和云端提交 SHA 提供额外对照依据。

独立细项基线和旧来源处置的派生追溯见 [H01](../current/AAOS-H01-SOURCE-TRACE-20261009.md)。原包及旧台账字节保留；未知语义覆盖与实施资格分别为 UNVERIFIED / UNKNOWN。

## UI深化设计增量 · 2026-10-10

[设计吸收与原任务验收增量](../current/AAOS-UI-DESIGN-INCREMENT-20261010.md)：用户指定两份TXT原件已按字节归档，新设计沿当前权威链进入既有UI切片；不可变TaskPack和产品实现资格分开。
