# System Boundary — ArcheAxis Knowledge v0.6.7

> 当前逐项状态以 `docs/current/AXR_060_COMPLETION_AUDIT_2026-08-23.md`
> 为准。实时 HEAD、tree、dirty、origin/main 与 CI 由
> `scripts/generate_current_reports.py` 生成到忽略的 `.hermes/task-artifacts/`；
> 本文不嵌入会因提交自身而过期的 SHA。

## 当前拓扑

| 区域 | 当前角色 | 状态 |
|---|---|---|
| archeaxis-workspace | FastAPI + SQLite(WAL) 的规范后端线 | `TESTED_LOCAL`（定向）；当前变更 exact-SHA CI 待执行 |
| 学习引擎（app/knowledge） | BKT/双轴掌握/Teach-Back/学习投影 | `TESTED_LOCAL`；完整安装版旅程待执行 |
| 证据与治理（app/evidence + promotion + machine_knowledge） | Anchor/Bundle/显式审核状态机 | `TESTED_LOCAL`；全账本 append-only 白名单仍 PARTIAL |
| 摄取链（app/ingestion） | raw-first、SHA-256、ConversionRun、锚点和 LossReport | Golden PDF `TESTED_LOCAL`；Tier A 完整矩阵未执行 |
| 联邦知识 API（app/federation） | Candidate/Receipt/Review/Verified/hash readback | `TESTED_LOCAL` |
| 前端（frontend/src/spaces） | 六空间读取真实 API；Learning 具备交互 | `PARTIAL`；六空间 browser E2E 未执行 |
| Tauri 桌面壳（src-tauri） | Supervisor、失败保活、retry、限制型 CSP | 基础生命周期 `RELEASE_PUBLISHED`；完整 Recovery `PARTIAL` |
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
完成声明必须绑定 Exact SHA + 证据路径；当前源码 SHA 只从生成器与 Git 读取。
