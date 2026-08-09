# Truth Spine

本目录保存 ArcheAxis OS 的稳定决策基线与可审计执行记录。它不以规划、版本号、测试夹具或模型判断代替真实运行证据。

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

仓库 convention gate 会验证冻结文件和批准增补包的固定 SHA-256，防止误改。Git 历史和云端提交 SHA 提供第二层对照依据。
