# AAOS 未完成任务收敛与逐项处置（2026-10-01）

状态：`SOURCE_AUDIT_COMPLETE / PRODUCT_ACCEPTANCE_PARTIAL`。`AAOS-ALL-TASKS-LEDGER-20261001.json` 的 270 条来源键已全部映射到 `AAOS-ALL-TASKS-DISPOSITION-20261001.csv`，一键一行、无重复。CSV 保留来源、ID、标题、原审计判定、现阶段执行队列、映射 R6 ID 和证据入口；完整原要求/验收仍在 JSON 总账。这里的队列归属是当前执行建议，不修改 R6/M0 权威，不将“未发现完成证据”写成“从未实现”。

| 处置队列 | 条数 | 当前动作 |
| --- | ---: | --- |
| `UI_FRONTEND` | 52 | 优先逐页母版/改进方案、导航、资产、主题、交互、原生 Green 验收；与真实 Core 状态绑定。 |
| `LIGHT_GOVERNANCE` | 9 | 最小状态、精确 SHA、来源及验收记录对齐；避免另造 Authority。 |
| `BACKEND_FRONTEND_LOOP` | 54 | 在独立后端分支按 M0/R6 跑真实多格式、证据、学习、机器纠错和重启闭环。 |
| `OWNER_GATE` | 4 | 需 Owner 决定资源根、Green/发布资格等；未决定前保持 BLOCKED。 |
| `CANDIDATE_REVIEW` | 25 | 开源库/历史吸收候选，仅在具体缺口出现时核版本、许可证、适配和运行证据，不等于必装任务。 |
| `DEFERRED_BLUEPRINT` | 13 | 保持只读规划与导航可发现性，M0 期间不启动重型能力。 |
| `HISTORY_TRACE_ONLY` | 107 | 仅追踪旧任务 ID 与 supersession，经 R6/M0 复核，不作为 107 项新工单。 |
| `PAUSED_BY_USER` | 5 | 清理、迁移及相关处置暂停；缓存、历史、数据库和恢复包保持原样。 |
| `NOT_ADOPTED` | 1 | 外部提案未采纳，不执行跨项目写入。 |
| **合计** | **270** | 115 项在三个执行队列，4 项 Owner 关卡；其余为候选、延期、历史、暂停或未采纳。 |

## 执行入口与防漂移

1. UI 先读 `AAOS-NAVIGATION-STRUCTURE-REVIEW-20261001.md`、覆盖矩阵、资产清单及用户指定的 `D:/All projects/UI套件/` 产品母版。母版是对照基线，允许 MiniMax 提出更优设计；逐页说明改变原因并验证真实交互。`UI_FRONTEND` 中跨后端事项需与 DSH 的合同对齐，不可静默伪造。
2. 轻量治理仅更新现有 R6/M0 账本和证据入口；不恢复清理任务或增加新审批层。
3. 后端闭环按 `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`、R6 `TASKS.json` 与本 CSV 的来源映射执行。对每项以精确源码/运行/真实输入证据关闭；`TESTED_LOCAL` 仍须判断是否覆盖完整验收。
4. 具体阻塞见 `AAOS-ERRORS-BLOCKERS-20261001.md`，两段跨软件提示词见 `docs/current/agent-prompts/`。最新 Git/CI/原生运行状态必须动态回读；CSV 是 2026-10-01 审计快照。

**尚未完成的是产品实施与逐项真实验收，不是任务来源整理。** 未能用当前证据关闭的条目继续保持 `OPEN_OR_RECHECK_WITH_REAL_EVIDENCE`；只有实际完成后才更新对应当前 Authority 状态。
