# 仓库陈旧资料集中归档

Owner 于 2026-10-19 要求将过时、冗余资料及不再使用的目录实际迁出原位置。本目录保全迁移前原字节；[MANIFEST.json](MANIFEST.json) 逐项登记原路径、归档位置、SHA-256、大小、源码基准及当前替代入口。

本轮迁移完整性、实际命令、源状态、时间、退出码与保留失败见 [VALIDATION.json](VALIDATION.json)。归档迁移 PASS 不提升产品状态；本地布局四项失败及 H01 旧运行证据缺失仍明确保留。

| 归档分区 | 内容 |
| --- | --- |
| `root/` | 根目录旧完成报告、计划、故障说明及旧运行边界快照 |
| `current/` | 旧阶段台账、旧交接、审计、版本绑定收据、旧派发与分支评审 |
| `legacy-docs/` | docs 根下旧交接、摘要、项目状态与工作流说明 |
| `truth-snapshots/` | 已被替代的旧状态、裁决与架构快照 |
| `legacy-taskpacks/` | 已取代的 2026-08 阶段任务包及冻结增补原件 |
| `navigation-before/`、`source-identities/` | 精简前导航、进度及资格所绑定的原始来源字节 |
| `directories/` | 旧任务包目录、superpowers 旧计划、OSUI 静态设计供体及 verified-knowledge 历史证据 |

当前资料只从 [活动指针](../../current/AAOS-ACTIVE-EXECUTION.json)、[接手入口](../../current/AAOS-AGENT-HANDOFF-CURRENT.md) 和 [文档职责索引](../../DOCUMENTATION_AUTHORITY_INDEX.md) 导航。旧路径不留占位文件；查旧材料用迁移清单和 `scripts/maintenance/authority_routes.py --resolve <原路径>`。历史引用不转为新权限；M0/R6 等来源中仍被当前合同继承的约束继续有效。

归档原文不重新排版，也不改写其中的日期、旧路径、失败结论或测试数量。相对链接的原始基址见 `original_path`；按清单先查迁移目标，再查当前职责索引，不能把历史路径当成当前入口。

**归档脚本状态：NOT_EXECUTED / NOT_EXECUTABLE。** 这里的旧脚本可能按原目录层级推导工作区，禁止从归档直接启动；如需恢复某项能力，先按当前合同移植并独立验证。OSUI 仅为静态视觉参考，不是产品运行入口。

仍由构建、打包或回归直接消费的 `app/`、`shared/`、`knowledge_base/`、`inspiration_research/`、`desktop/`、`apps/ArcheAxis.Desktop/`、`shared-contracts/` 保持现有位置，受原维护边界约束。它们不能因名称旧而视为可删除冗余；本次不改变运行架构、依赖或冻结范围。
