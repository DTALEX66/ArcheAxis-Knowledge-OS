# Truth Spine

本目录保存 ArcheAxis Knowledge 的稳定决策基线与可审计执行记录。它不以规划、版本号、测试夹具或模型判断代替真实运行证据。

## 当前执行权威（2026-09-26）

- 当前活动基础包为 [`R6 Executor Start`](../authority/taskpack-0919-r6/EXECUTOR-START.md)，实时进度见 [`R6-EXECUTION`](../current/R6-EXECUTION.md) 与 [`R6-STATE`](../current/R6-STATE.json)，优先级覆盖见 [`M0`](../current/M0-DIRECTION-OVERRIDE-20260920.md)。
- [`CURRENT_STATE_TRUTH.md`](CURRENT_STATE_TRUTH.md) 保留 2026-08-09 的真值方法与当时状态；其旧任务顺序和阶段状态是 **HISTORICAL / SUPERSEDED**，不能作为当前执行队列。
- [`AUTHORITY_CONTRACT.md`](AUTHORITY_CONTRACT.md) 保留 2026-08-09 的权威顺序快照；其把旧冻结包列为当前唯一任务源的规则已被 **HISTORICAL / SUPERSEDED**。原文保留，不据此覆盖当前 `AGENTS.md`、R6 与 M0 权威入口。
- [`ARCHITECTURE_FINAL.md`](ARCHITECTURE_FINAL.md) 保留 2026-08-14 的架构收敛提案；其中 Tauri/React 壳层图是历史方案，当前正式桌面壳以 C#/Avalonia 为准。
- [`check_r6_taskpack_authority.py`](../../scripts/maintenance/check_r6_taskpack_authority.py) 只校验 R6 权威包的冻结身份；它**不校验全部 2026-08 冻结文档和增补包的 SHA-256**。旧包的 `.sha256` 文件和 Git 历史是历史完整性依据，不应误称为当前仓库 convention gate 的覆盖范围。

## 权威顺序

发生冲突时，按以下顺序处理：

1. 系统与开发者规则；
2. 全局及项目 `AGENTS.md`；
3. 用户当前明确指令；
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
