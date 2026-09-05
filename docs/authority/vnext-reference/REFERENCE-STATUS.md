# Reference 状态说明

本目录保存历史与审计材料，目的是保留原因、证据和演进，不是让旧任务包重新与当前方案平票。

权威关系：

1. `MASTER-TASKPACK.md` 第 0 节和 `DECISION-LEDGER.yaml`：本包当前前向方案。
2. 仓库合并后的 Owner Decision/ADR：落盘后成为前向权威。
3. `ArcheAxis-Knowledge-vNext-Implementation-Decision-2026-09-04.md`：当前语言、产品和迁移边界的论证；其中旧任务编号、lease、签发和 receipt 协议已废止。
4. `ArcheAxis-Current-Project-Viability-and-Restart-Decision-2026-09-04.md`：现有项目去留与迁移边界。
5. `ARCHEAXIS-HISTORY-AUTHORITY-AND-SOURCE-REGISTRY-2026-09-04.md`：97 项来源总账和 supersession 依据。
6. `ARCHEAXIS-COMPLETE-REPAIR-AND-LANGUAGE-MIGRATION-PLAN-2026-09-04.md`：仍可用的问题清单与门禁；其中原地修复顺序、C# sole writer 或“G0 阻止隔离新库”等内容已被覆盖。

旧参考中出现的“Rust 逐聚合接管 legacy DB writer”、`authority lease`、
WORK-LAB/DESIGN-LAB 联动、旧 task path、旧任务编号或旧 receipt 字段均只解释演进，不得直接生成任务。当前实现
必须使用 MASTER、`DECISION-LEDGER.yaml` 与 `repo-seed/.project/` 中的新
database isolation、authority grant、JIT slice 和 external receipt 契约。

历史材料只能追加 `superseded_by`，不得删除、改写或用日期较新的普通 handoff 覆盖 Owner Decision。
