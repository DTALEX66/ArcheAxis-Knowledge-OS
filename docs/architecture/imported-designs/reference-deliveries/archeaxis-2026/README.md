# ArcheAxis 2026 Reference Deliveries

> **状态：外部设计与验收参考，非当前实现、非运行时依赖、非可直接执行任务。**
>
> 本目录保留用户提供的原始交付，以支持未来的设计追溯。当前可验证能力以 `docs/PROJECT_STATUS.md`、实际代码、测试和 Git 历史为准；可执行任务以 `docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`、批准增补与 `docs/truth/EXECUTION_STATUS_LOG.md` 为准。

## 使用边界

- 不解压、导入、执行、安装或自动吸收本目录的任何交付内容。
- 不将文件中提及的项目、模型、数据集、脚本、Schema 或状态表视为当前仓库的合同或授权。
- 任一候选能力必须先经历 Research / quarantine、许可证与来源核验、最小 TaskPack、独立测试、审核和回滚设计。
- `ArcheAxis_OS_MCS_Phase5_v0.1.0.zip` 只作为“受治理最小闭环”的验收参考；不得作为第二套数据库、API 或 Worker 引入。

## 已归档文件与完整性

| 文件 | SHA-256 | 用途 |
| --- | --- | --- |
| `ArcheAxis OS Overview.docx` | `b4437158ad8f08dbbfe79a08212666056ce0347169f3bd7d8c8a46b8a3efb8b5` | 产品北极星、业务域和阶段边界 |
| `ArcheAxis OS V3.0 Blueprint.docx` | `7169d7f9a111803e14d34d50935f6ca028bbfe5d81ab24dc11663c12393fbee1` | 模块化单体、领域/API/Worker 和渐进迁移蓝图 |
| `ArcheAxis OS V3.1 Documentation.docx` | `e82075555f0a538f9495ead713d80de0af9994d30ee0ce450b4204af470b3c80` | 事实/工作对象/投影、命令、Outbox、恢复和安全深化规范 |
| `Cognitive_Loop_OS_GoogleResearch_500AI_Delivery_v1.0.zip` | `029056323290a0dfc8d2cd4b809fe44bac21bba84d223cd582ed94216ba550f0` | Research-to-Practice 候选资产与验收材料 |
| `ArcheAxis_OS_MCS_Phase5_v0.1.0.zip` | `ce94e63ae551ee65d60aaf9315d90a148c184fcc4da8b5cf8df79c2bc3a28c05` | Phase 5 受治理最低闭环验收参考 |
| `ArcheAxis_OS_MCS_Phase5_v0.1.0.sha256` | — | 用户提供的 MCS zip 校验记录；与上列 zip 一致 |
| [`planning-2026-08-09/`](planning-2026-08-09/) | 见目录内 `ORIGINAL_SOURCE_MANIFEST.sha256` 与 `REPOSITORY_COPY_MANIFEST.sha256` | ArcheAxis Workspace 原始蓝图、规划、v3/v4 任务包与 2026-08-10 handoff；仅作来源追溯 |

## 已吸收的稳定决策

这些交付中可复用且已被收敛到仓库规划的原则，见 [`../../../../FUTURE_EXECUTION_BLUEPRINT.md`](../../../../FUTURE_EXECUTION_BLUEPRINT.md)：模块化单体、候选默认、审核门、追加式事实、版本/审计、命令幂等、事务 outbox、可恢复 worker、结构化可编辑教学资产，以及 2D 优先的空间记忆。冻结任务和批准增补的权威顺序见 [`../../../../truth/AUTHORITY_CONTRACT.md`](../../../../truth/AUTHORITY_CONTRACT.md)。
