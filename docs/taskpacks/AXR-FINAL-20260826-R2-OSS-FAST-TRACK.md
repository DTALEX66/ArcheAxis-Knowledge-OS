# ArcheAxis Knowledge 最终执行任务包（R2 OSS 快速成品化）

- TaskPack ID：`AXR-FINAL-20260826-R2-OSS-FAST-TRACK`
- 产品：`ArcheAxis Knowledge｜星环知识平台`
- Owner 输入：2026-08-27 会话附件（原文件名 `ceshi/ARCHEAXIS-FINAL-TASKPACK-2026-08-25.md`）
- 原审计基线：`main@bf0c48396c751647ac76ee4578bc38f44888a23e`
- 安装基线：`main@e8571b9d`（包含 Linux Chromium socket-path 修复，CI run 32986477421 success）
- 状态：`IN_EXECUTION`
- 取代：`AXR-FINAL-20260825-R1`；冲突条款以本文件为准
- 边界：只修改 ArcheAxis；外部产品通过 adapter/sidecar/downstream product shell 接入，不能写核心真值

> 本文件是 Owner 附件的仓内执行版。附件原始内容仍是裁决来源；这里保留不可漂移的对象语义、任务 DAG、依赖、证据门与 OSS 快速成品化增补，避免把聊天附件误当已执行事实。

## 1. 产品与真值边界

ArcheAxis 是本地优先、原件保全、证据可追溯的人机双向重型学习与可信知识治理系统。唯一真值对象为：

- `Source / RawAsset`：原件、版本、rights、fixity；
- `Anchor / Annotation`：页码、文本、区域、时间段和源版本定位；
- `Claim / Evidence / KnowledgeUnit`：候选、复核、验证、争议、废止和来源链；
- `HumanLearningState`：人的理解、记忆、迁移和长期掌握；
- `MachineCompetenceState`：机器基于真实任务收据获得的能力；
- `LearningEvent / DistillationCandidate / EvaluationReceipt`：教学、实践、失败和纠错事件。

DeepTutor 负责完整学习产品体验；其 KB、Memory、向量索引、Book 指纹和 session 只是可删除、可重建投影。Docling、sqlite-vec、py-fsrs、faster-whisper 是窄 adapter/sidecar。任何上游、LLM、客户端、检索命中或用户掌握均不能直接写 verified knowledge 或提升机器 K。

## 2. 状态语义

知识状态：`candidate -> reviewed -> verified | contested | superseded | rejected`。`verified` 必须引用授权 verification receipt，且允许因新证据降级、争议、撤销或 supersede。

MachineCompetence V2 返回“最高已达到等级”：

`NONE -> K0_RAW -> K1_INDEXED -> K2_STRUCTURED -> K3_REASONABLE -> K4_PROCEDURAL -> K5_CALLABLE -> K6_VERIFIED -> K7_ADAPTIVE -> K8_TRANSFERABLE`。

无原始来源为 `NONE`；V1 无法证明的旧值为 `UNMIGRATED`，不得静默升级。HumanLearning 与 MachineCompetence 永久分离。

## 3. OSS 产品路线

```text
DeepTutor downstream product shell
               |
     ArcheAxisAuthorityAdapter
               |
 Source / Anchor / Claim / Evidence
 HumanLearning / MachineCompetence truth
               |
Docling + sqlite-vec + py-fsrs + faster-whisper
```

采用规则：锁 `upstream_repo/tag/commit/archive_sha256/SPDX/NOTICE/patches/data_scope/network_scope/install/update/rollback/last_verified/evidence_level`；禁止 `main/latest` 作为发布证据。AGPL/GPL 默认外置进程；模型代码、权重、训练数据分别审查。

## 4. 最终任务 DAG

| ID | P | 依赖 | 当前任务 |
|---|---:|---|---|
| AXR-000 | P0 | — | 安装本包；冻结 structural/local runtime/exact-SHA CI/installed Windows/public release Current Reality Matrix |
| AXR-010 | P0 | 000 | PDF.js 修复线、`isEvalSupported:false`、恶意 PDF；canonical SBOM；主壳/恢复壳身份分离 |
| AXR-020 | P0 | 000 | MachineCompetence V2/NONE；sqlite Row；`/tick` 禁止客户端自报真值；迁移/回滚 |
| AXR-030 | P0 | 010,020 | SourceObject/Anchor/Provenance V2；Web Annotation selector；PROV-O；OCFL-compatible export/validate |
| AXR-040 | P0 | 020,030 | DeepTutor 产品底座；AuthorityAdapter；六空间 UI Contract；真实学习黄金纵切 |
| AXR-050 | P1 | 030 | Docling/MarkItDown/faster-whisper 多格式 adapter bake-off |
| AXR-060 | P1 | 020,040 | append-only LearningEvent；FSRS/BKT 可重放；xAPI 2.0 profile export |
| AXR-070 | P1 | 020,030 | 人→AI 证据化蒸馏；至少 3 案例+1 反例；批准前不可调用 |
| AXR-080 | P1 | 040,060 | AI→人有锚点教学；DeepTutor 只提交 proposal/result/event |
| AXR-090 | P2/条件 | 070 | MemOS 可删除 runtime projection；仅量化瓶颈后考虑 Graphiti |
| AXR-100 | P1/运行阻断 | 040,050 | 持久化 Job/SSE/取消/retry/replay；ASR/WER/Anchor；Windows 恢复 |
| AXR-110 | P1 | 000,010 | OSS ledger、SBOM、NOTICE、rights、模型许可和历史资产减法 |
| AXR-120 | P1 | 070,080 | DESIGN-LAB 双向学习试点；本仓只实现 ArcheAxis 边界 |
| AXR-130 | P2 | 本期批准项 | Python/DB/security/frontend/Playwright/Tauri/Windows/SBOM/backup/exact-SHA Release 总门 |

波次：Safety(000/010/020) → Truth(030/060) → Product(040/050/100) → Bidirectional(070/080) → Projection(090/110) → Proof(120/130)。

## 5. 72 小时执行单与退出条件

1. 锁 DeepTutor 稳定版、Docling、sqlite-vec、py-fsrs、faster-whisper 的 tag/commit/hash/SPDX/数据目录；
2. Windows 专用 workspace 原样跑 DeepTutor：导入、引用问答、Quiz、Book/Notebook、退出和重启；
3. 公开 PDF/DOCX 建 SourceObject；Docling derivative 和 DeepTutor citation 映射 Anchor/v2；定位失败显示 `UNANCHORED`；
4. Quiz/teach-back 转 append-only LearningEvent，由 py-fsrs 生成队列；禁止 DeepTutor 提交 verified/Machine K；
5. 删除测试 KB/索引并从 ArcheAxis 重建，证明无第二真源。

仅当 DeepTutor 48 小时内不能在目标 Windows 完成原生黄金流程，且有安装失败证据，才允许退回 OpenTutor/现有壳。

## 6. 强制证据与 DONE

每项至少交付：task/base SHA、迁移前后 schema/hash、命令 exit code、测试层级、浏览器/Tauri 读回、失败路径、rollback、source/anchor/provenance fixtures、上游 commit/SPDX/SBOM、exact-SHA CI receipt。模型/解析器还记录权重 revision/hash/license、硬件、峰值内存、延迟和退出策略。

状态仅允许 `TODO / IN_PROGRESS / BLOCKED_RUNTIME / CONDITIONAL / DONE / REJECTED`。无 exact SHA + 真实 DB + 浏览器/Tauri + 失败/回滚证据，不得标 DONE。

## 7. 发布完成定义

首个可用阶段必须同时证明：普通 Windows 30 分钟内安装；真实 PDF/DOCX 原件/rights/hash/备份；Docling 精确 Anchor；DeepTutor 至少四项学习动作；Human/Machine 永久分离且伪造被拒；LearningEvent/FSRS 重放一致；provider/解析失败、源变化、STALE、取消、回滚可见；备份/恢复/卸载/SBOM/NOTICE；公开声明不高于最弱证据。

在此之前冻结 3D/VR/AR、第二 Tutor、第二图数据库、第二记忆引擎、通用 Planner 和现有壳的新通用页面。

## 8. 明确禁止

- 不得把 ArcheAxis 改成 Agent OS、普通 RAG、聊天主页或文件管理器；
- 不得让 DeepTutor、MemOS、Graphiti、Docling、LLM 或客户端成为第二真源；
- retrieval、模型自评、用户掌握、README 不能产生 verified knowledge/skill；
- 不得同时运行多个记忆/图/教学产品真源；
- 不得把历史 demo、路由 200、旧测试数字包装为产品闭环；
- 大模型权重、个人原件、私有会话和凭据不得提交 Git。
