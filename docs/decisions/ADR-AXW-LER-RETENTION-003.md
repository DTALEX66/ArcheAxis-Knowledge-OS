# ADR-AXW-LER-RETENTION-003 — LER 视觉/空间学习层永久保留

- **状态**：Accepted（Owner 任务包 v1 2026-08-11）
- **日期**：2026-08-12
- **决策**：LER（Learning Experience & Representation Layer）是正式产品层（P4），包括结构化基础、视觉教学、动态解释、互动实践、空间记忆、沉浸空间（3D/VR/AR）。所有高级视觉/空间能力以 `binding_long_term` 永久保留，但激活需来源/fallback/性能/无障碍/学习证据。
- **理由**：Owner 裁决"视觉/空间能力是正式学习层，不被删除"；deferred ≠ deleted。
- **后果**：Capability Atlas 为 LER/Visual/Animation/Simulation/Spatial/3D-VR-AR 建立独立 capability 族（CAP-0060~0080, 0160）；统一 manifest 必须含 EvidenceAnchor、来源、版本、资产许可、fallback、export、loss；Spatial Memory 用 engine-agnostic `SpatialMemoryPackage`；不预选 3D/VR 引擎。
- **关联**：LER_VISUAL_SPATIAL_LEARNING_V1.md、SYSTEM_MASTER_BLUEPRINT_V2.md、CAPABILITY_ATLAS_V2.yaml、AXW-1205

## 修订
| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-08-12 | 首次发布 |
