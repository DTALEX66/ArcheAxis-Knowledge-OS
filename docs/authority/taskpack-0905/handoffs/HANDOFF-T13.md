# HANDOFF — T13 旧能力全面吸收与非空数据迁移验证（CODEX）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：高（最高风险）· 目标代理：CODEX
依赖：T03/T05/T06/T09/T14 与 **T17 盘点台账（DeepSeek 线产出，见 docs/authority/legacy/ 与 LEGACY_MANIFEST.yaml）**

## 目标
- 将 T17 判定可吸收的全部能力接入对应 T03–T12 目标模块，逐项核验（不因已复制代码标完成）；
- 实现非空旧 schema→staging 新库语义映射、差异和回滚；真实用户数据切换单独验收；
- 原库哈希不变；知识/关系/附件/学习记录映射可审阅；不以空库导出证明迁移；
  未知格式保留原件并明确能力缺失；可吸收资产无无主项；未吸收项不计全面合并完成。

## 上下文
- 旧库基线：legacy v0.6.14（frozen commit c202c5b5），唯一旧库写者=legacy Python；
  Rust 只经 consistent snapshot → read-only export → staging import → Owner activation 接收（SUP-006）。
- 已有 dry-run 报告：reports/vnext/legacy-dryrun-2026-09-04.json（17/17 迁移、用户知识表为空→dry-run 真实验证）。
- 数据源（只读副本）：D:\All projects\ArcheAxis.Knowledge.Green-x64\data（40.7MB，含真实原件/学习内容样例）与仓库 dev data。
- crates/archeaxis-migration 骨架在；旧库实现在 legacy app/shared（maintenance-only）。

## 允许路径（任务包 T13）
crates/archeaxis-migration/**、integrations/legacy/**、services/python-workers/compat/**、
LEGACY_MANIFEST.yaml、tests/migration/**。

## 验收（任务包 T13）
- 原库哈希不变；知识/关系/附件/学习记录映射可审阅；
- 不以空库导出证明迁移；未知格式保留原件并明确能力缺失；
- 可吸收资产无无主项；每项目标代码/接口/样例/验收齐全。

## 环境事实
- 真实用户数据切换需用户另行授权，不在自动执行范围；本任务用只读副本 + dry-run + staging 库验证；
- 迁移测试在 .hermes/task-runtime/ 副本上执行，绝不触碰 Green 真实 data 的写路径。

## 切片建议
1. 差异清单→映射矩阵（知识/关系/附件/学习/任务/研究）；2. staging 导入+差异报告+回滚；
3. 非空副本端到端 dry-run（对照 dryrun-2026-09-04 基线）；4. 能力吸收逐项核验关闭（对照 T17 台账）。

## 输出契约
每切片：原库哈希不变证据、映射可审阅产物、回滚验证、SHA；收据 docs/authority/taskpack-0905/T13/。
