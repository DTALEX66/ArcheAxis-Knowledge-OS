# System Boundary — archeaxis-workspace

> 本文件描述当前边界（重新生成于 2026-08-19，对齐 HEAD c83225b）。远期设计见
> `docs/FUTURE_EXECUTION_BLUEPRINT.md`；旧端点数、测试数和“完成度”不作为能力证明。

## 当前拓扑

| 区域 | 当前角色 | 状态 |
|---|---|---|
| archeaxis-workspace | 唯一开发目标；FastAPI + SQLite(WAL) 由 `app.main` 在端口 8000 统一提供 | 可运行；已含学习引擎、证据链、联邦知识 API |
| 学习引擎（app/knowledge） | BKT/双轴掌握/Teach-Back/蒸馏/技能演化/闭环编排/学习者画像/路径推荐 | 已实现（后端 170+ 测试） |
| 证据与治理（app/evidence + promotion + machine_knowledge） | Anchor/Bundle/状态机（candidate→verified/rejected/deprecated） | 已实现 |
| 摄取链（app/ingestion） | multi_format + web(raw-first) + OCR(RapidOCR/Tesseract) + ASR(SenseVoice) + 噪声过滤 + 质量门 | 已实现；多格式实测见 reports/current/INGESTION_REALITY_MATRIX.json |
| 联邦知识 API（app/federation） | TP-20260819：批量 Candidate 提交（幂等）/Receipt/Verified 回读（分页）/hash readback/外置资产索引 | 已实现（tests/test_federation_v1.py 5 通过） |
| 前端（frontend/src/spaces） | 六空间；Learning 空间真实数据，其余 5 个为占位符 | PARTIAL |
| Tauri 桌面壳（src-tauri） | ✅ debug+release 构建成功（7.9-11.7MB）+ 启动冒烟通过；安装包待 R6 | PASS |
| WORK-LAB / DESIGN-LAB | 独立仓库；仅通过本仓库稳定 API/契约协作，非运行时依赖 | 边界成立 |

## 当前 Core 边界

### 已有链路（真实，非声明）

```text
原件/来源 → 格式检测(magika) → 多格式转化(+OCR/ASR/噪声过滤/质量门)
→ 证据锚定(anchor/时间码) → Candidate(候选, 默认不进可信)
→ 人工复核/交叉验证 → Verified Knowledge
→ Human Learning Assets（due_queue/mastery/teach_back/path）
→ AI Assets（machine_knowledge/promotion/skill_assets）
→ 带证据检索 → 导出(exchange) → 重启回读(迁移)
```

### 联邦边界（TP-20260819）

- ArcheAxis 拥有：KnowledgeQueryV1 / KnowledgeProjectionV1 / CandidateSubmissionV1 /
  CandidateReceiptV1 / EvidenceIntakeV1 / LearningRecordV1 / ProvenanceRecordV1 / RightsRecordV1。
- AI 内容默认只进 Candidate，**绝不自动升级为 Verified**（人工复核门槛）。
- 外置资产只登记 Record（URI/hash/source/rights/extraction/derived_ids），**不复制大原件进仓库**。

## 数据与合同方向

以下对象是仓库内合同方向，不代表外部系统已经联通：

- IntakeCard / EngineeringContract
- ContextPack / TaskPack
- Federation V1 契约（app/contracts/federation_v1.py）——WORK-LAB/DESIGN-LAB 经 API 调用，不得直写本仓核心表

## 统一状态词

PASS / PARTIAL / FAIL / NOT_EXECUTED / BLOCKED。禁止用 DONE 代替证据状态；
完成声明必须绑定 Exact SHA + 证据路径。当前 HEAD：c83225b。
