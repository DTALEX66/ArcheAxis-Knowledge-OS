# 2026-09-29 规划蓝图与云端对标归档审计

## 归档定位

本目录保存 2026-09-29 的历史规划/能力池汇总包、接手与云端对标报告、最终判断报告原件，以及 ZIP 全部内容的可检索副本。原始输入保留逐字节副本；外部 `Record` 源文件未移动或删除。完整性证据见 [ARCHIVE_MANIFEST.json](ARCHIVE_MANIFEST.json)。

**分类：历史审计快照与参考索引，不是新执行权威。** 本材料本身要求保留 R6/M0 执行序列，不修改不可变 TaskPack。当前执行仍以仓库 [AGENTS.md](../../../../AGENTS.md)、[PROJECT_CONTRACT.yaml](../../../../PROJECT_CONTRACT.yaml)、[DECISION_SUPERSESSION_LEDGER.yaml](../../../../DECISION_SUPERSESSION_LEDGER.yaml)、[R6 immutable TaskPack](../../../authority/taskpack-0919-r6/TASKPACK.md)、[M0 priority overlay](../../../current/M0-DIRECTION-OVERRIDE-20260920.md) 及 live [R6 execution](../../../current/R6-EXECUTION.md)/[R6 state](../../../current/R6-STATE.json) 为准。

## 本次权威读回

- 仓库 `R6-STATE.json` 当前记录：`overall_status=IN_PROGRESS`、`release_status=FROZEN`。任务 A00–A16 中存在 `TESTED_LOCAL_PARTIAL`、`BLOCKED_BY_OWNER_DECISION` 等状态；不得总结为已完成或可发布。
- 该 live state 的 `updated_at=2026-09-26T15:31:00+08:00`、`subject_sha=2994efa08d3e4f6ea561831fd4088d6d1b290cdd`。这些是状态文件记录的日期与证据 SHA，不是本次 HEAD 或当前远端/CI 证明。
- 本次本地仓库读回：branch=codex/Audit，HEAD=43c2cafa1bfe57a862e90c5a77dc16832264babd；这是本地工作区读回，不代表远端已发布。审计开始时工作区已有 UI 改动及未跟踪历史材料。
- 报告中的云端 `main=d8f99a6357405054f1f9ee66eb2f88d36f7f5143` 是报告审计时快照；与 R6 state 的 subject SHA、测试 SHA、制品哈希和当前 live refs 分开保存。报告中的 GitHub/CI/PR/分支结论必须在使用时重新读回。

## 内容分层与对标

| 材料 | 审计分类 | 使用边界 |
| --- | --- | --- |
| R6 TaskPack 与 M0 | 当前绑定执行权威 | 任务定义、执行顺序与验收状态以仓内不可变包和 live 台账为准 |
| 97 条来源基线、369 项 OSS 研究池 | 历史来源/候选供体索引 | 不代表逐条审查、选择、吸收或集成；不删除源项目能力，只供后续按 M0 门槛评估 |
| 47 项供应链清单、11 项吸收记录 | 供应链/吸收状态快照 | `CURRENT` 或 disposition 不是已集成证据；报告指出汇总应为 `CURRENT=11 + REFERENCE=1`，不是 `CURRENT=12`，47 项总数不变 |
| 16 项能力 Atlas、17 项需求追踪 | 长期能力与追踪映射 | 长期能力目标不改变 R6/M0 优先级，也不自动成为当前验收条件 |
| 9/29 R6/M0 CSV 与两份判断/对标报告 | 日期绑定状态/审计快照 | 保留其原始观察时间、SHA 与限制；不覆写当前状态、不将快照重新标记为 live |
| Scientific Intelligence 等新增方向 | 提案/候选 | 不能作为已批准架构或已集成功能；先遵从当前项目决策与验收门槛 |

## 原始材料异常与限制

1. `AAOS_最终判断报告_2026-09-29.md` 在约第 203 行再次开始“接手与云端对标报告”，属于拼接复合文件。为保留来源与哈希，按原样归档；不要将其误读为一篇连续、独立的判断报告，也不在此处静默拆改。
2. 云端对标报告自述无法验证本机完整 GUI、真实模型、非空 Legacy 迁移、Green 安装/回滚及全部历史原件；本归档不补造这些证据。
3. 总包所含来源表和池是索引快照，不证明所有原始历史来源实物已经齐全归档。
4. 本报告只做权威交叉审计与材料归档，不改变任务状态、供应链裁决或 release 状态。

## 过时文档清理结论

仓库 `docs/DOCUMENTATION_AUTHORITY_INDEX.md` 已将 18 份旧计划/旧交接列为执行上已 superseded，但明确要求保留作证据，并规定迁移/删除前必须具备逐路径哈希与引用清单、兼容链接更新和回归验证。只读扫描发现这 18 份文档及根目录 `HERMES_HANDOFF.md` 仍有仓内引用；其中 `docs/current/UI_V3_PRODUCT_ROADMAP.md` 有未提交用户修改。故本轮不删除或移动这些文件，也不碰 `.project-local`、Green 用户数据或混合来源历史目录。候选路径、哈希、引用规则和状态见 [OBSOLETE_DOCS_CLEANUP_AUDIT.md](OBSOLETE_DOCS_CLEANUP_AUDIT.md)。

## 恢复/回滚

本归档为新增文件。若需撤销，按 `ARCHIVE_MANIFEST.json` 逐文件删除本归档新增路径，并从 `docs/DOCUMENTATION_AUTHORITY_INDEX.md` 移除本归档链接；原 `Record` 文件未动。不要对整段 `docs/history/` 做递归清理。
