# AXW-020R — Existing Object Reuse & Migration Matrix

> 任务：`AXW-020R`（H1，依赖 `AXW-H0-EXIT`）
>
> 目标：映射 H1 域对象（SourceRecord、Claim、Evidence、LearningArtifact、MasterySignal、Job、Outbox、Receipt）到现有实现，**禁止平行重建**。

## 1. 复用原则

H1 引入 RawAsset / Import / Conversion / Derived 时，**不得**为已在仓库中存在的对象新建平行实现。下表是权威映射；任何新能力必须复用对应现有对象/表/适配器，只有缺失的语义才新增。

## 2. 对象复用矩阵

| H1 域对象 | 现有契约/模型 | 现有存储 | 现有适配器 | 复用决策 |
|---|---|---|---|---|
| SourceRecord | `SourceRecordV1`（app/contracts/v1.py:73） | kb_documents + source_record 迁移 | app/adapters/source_record.py | 复用；RawAsset 作为其"原件字节"扩展 |
| Claim | `ClaimV1`（:91） | research/graph 迁移 | app/adapters/claim.py | 复用 |
| Evidence | `EvidenceV1`（:114） | research/evidence 迁移 | app/adapters/evidence.py | 复用；EvidenceAnchor 作为其 locator 扩展 |
| LearningArtifact | `LearningArtifactV1`（:175） | knowledge/learning 迁移 | app/adapters/learning_artifact.py | 复用 |
| MasterySignal | `MasterySignalV1`（:139） | mastery_signals_v1 | app/adapters/mastery_signal.py | 复用 |
| MachineKnowledge | `MachineKnowledgeUnitV1`（:203） | machine_knowledge_candidates_v1 | app/adapters/machine_knowledge.py | 复用 |
| Job | （SQLite workspace_jobs_v1） | app/workspace/job_outbox.py | workspace service | 复用；无独立 V1 类，用 service 函数 |
| Outbox | （SQLite workspace_outbox_v1） | app/workspace/job_outbox.py | workspace service | 复用 |
| Receipt | （SQLite workspace_command_receipts_v1） | app/workspace/job_outbox.py | workspace service | 复用 |

## 3. 禁止平行重建

- 不新建 `SourceRecordV2` 或 `ClaimV2`；扩展复用 `SourceRecordV1`/`ClaimV1`。
- 不新建第二套 Job/Outbox/Receipt 存储；`workspace_*_v1` 表 + job_outbox.py 是唯一作者。
- 不复制 KB/Research/Knowledge 的领域表；所有 H1 派生对象落在 RawAsset/Derived 新表，但其来源引用现有对象 ID。

## 4. 新增 vs 复用判定

| 场景 | 判定 |
|---|---|
| 需要"原件不可变字节 + 哈希" | **新增** RawAsset 表/合同（AXW-020A）——现有 SourceRecord 存派生文本，无原件字节 |
| 需要"导入批次/转换运行/派生块/LossReport" | **新增** Import/Conversion/Derived（AXW-020B）——现有无此概念 |
| 需要"页/块/字符/区域锚点" | **新增** EvidenceAnchor（AXW-020C）——现有 Evidence 只有文本 locator |
| Job/Outbox/Receipt 持久化 | **复用** workspace_*_v1 + job_outbox.py（AXW-021A 直接复用） |

## 5. 一致性校验

AXW-020R 的验收以"不平行重建"为准：任何 PR 若引入与上表重叠的新对象/表，必须在本矩阵登记并解释为何无法复用现有项。重叠而无登记即 fail-closed。

## 6. 证据

- 本矩阵的现有对象存在性由源码（contracts/v1.py、adapters/*、workspace/job_outbox.py）验证。
- 复用路径的集成由 H1 各任务（020A/020B/020C/021A）的实际实现与测试证明。
