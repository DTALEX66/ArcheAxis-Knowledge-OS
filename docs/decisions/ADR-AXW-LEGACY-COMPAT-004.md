# ADR-AXW-LEGACY-COMPAT-004 — 历史兼容与迁移保护

- **状态**：Accepted（Owner 任务包 v1 2026-08-11）
- **日期**：2026-08-12
- **决策**：旧名称（archeaxis-workspace、元枢、ArcheAxis OS）与旧任务包、历史蓝图、历史审计只保留 Legacy/Migration/Compatibility 语境；不删除历史；不无证据改名；不把历史能力冒充当前实现。
- **理由**：Owner 裁决"以整理为名删除历史任务、能力、候选、需求或名称映射"是禁止裁决。
- **后果**：命名迁移五阶段（文档→UI→打包→仓库→底层），每阶段有 prereq/backup/migration/alias/rollback/验证/deprecation window；至少保留两个稳定版本兼容 alias；不执行远端 rename 除非 Owner 授权 + NAME-READINESS 清单。
- **关联**：LEGACY_TO_ARCHEAXIS_NAMING_MIGRATION_V1.md、NAMING_CONTRACT_V1.md、AXW-1208

## 修订
| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-08-12 | 首次发布 |
