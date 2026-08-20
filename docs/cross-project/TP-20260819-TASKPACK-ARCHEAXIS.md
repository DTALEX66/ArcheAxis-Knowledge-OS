# ArcheAxis-Knowledge-OS 任务包（TP-20260819 联邦 · ArcheAxis 部分）

> 来源：TP-20260819-TRI-PROJECT-FEDERATION-V2（2026-08-19）。本文件为 ArcheAxis 执行子集。基线 main：9def792acaf。执行器：ArcheAxis 侧 Agent（WORK-LAB 推送本任务包供检测）。

## 状态约定

PASS / PARTIAL / FAIL / NOT_EXECUTED / BLOCKED。禁止用 DONE 代替证据状态。所有完成声明绑定 Exact SHA + 证据路径。不自动 commit/push（需人工批准）。

## 唯一定位（不可漂移）

本地优先、证据驱动、人机双向重型学习与可信知识治理系统。包含人类学习工作空间 + AI 学习 + Candidate/Review/Verified + 可信知识编译能力。不得变成 AI-only 知识库/RAG/Agent Runtime/模型网关。

## AA-P0（修复任务）

- [ ] AA-P0-001 重新生成当前状态：SYSTEM_BOUNDARY.md/产品计划与真实 HEAD 一致，旧阶段/旧执行器不作为当前事实
- [ ] AA-P0-002 稳定跨项目知识 API：批量 Candidate Submission / 幂等键 / 权限身份 / Candidate Receipt / Verified 回读 / 分页错误码速率版本协商 / 来源版权可信度 / hash readback
- [ ] AA-P0-003 保留人类学习核心：新机器接口必须验证人类学习 Workspace 未降级，AI 内容默认只进 Candidate

## AA-P1

- [ ] AA-P1-001 外置资产索引：Design assets 的 ExternalAssetRecord（URI/hash/media/source/rights/extraction/derived IDs），不复制大原件进 Git
- [ ] AA-P1-002 未完成摄取能力真实状态：PDF/Office/Markdown/图片OCR/音频ASR/视频/URL 逐项 PASS/PARTIAL/FAIL/NOT_EXECUTED/BLOCKED

## 联邦角色（§6.1）

ArcheAxis 拥有：KnowledgeQueryV1 / KnowledgeProjectionV1 / CandidateSubmissionV1 / CandidateReceiptV1 / EvidenceIntakeV1 / LearningRecordV1 / ProvenanceRecordV1 / RightsRecordV1

## E2E 参与（§11）

- E2E-001 人类学习闭环（Learning Record → Evidence → Candidate → Review → Verified → Readback）
- E2E-003 受治理生产的知识查询/Candidate Receipt 环节

## 知识迁移试点（§12，ArcheAxis 侧）

- 接收 3 个试点对象（WORK-LAB 治理规则 / DESIGN-LAB MethodCard / 外置 SourceRecord）
- 提供 Candidate ID / 提交回执 / ArcheAxis 回读 / 编译产物引用

## 交付文件（reports/current/）

- CLOUD_BASELINE / FEDERATION_MIGRATION_REPORT / FEDERATION_MIGRATION_STATUS / EXACT_SHA_VERIFICATION / CONTRACT_CONFORMANCE / REMAINING_HUMAN_GATES
- KNOWLEDGE_API_CONFORMANCE.json / CANDIDATE_ROUNDTRIP_PROOF.json / HUMAN_AI_LEARNING_PARITY_AUDIT.md / INGESTION_REALITY_MATRIX.json

## 人工批准点（§16）

commit/push/迁移/Secret/证据等级提升/全量反向迁移——均需人工批准。
