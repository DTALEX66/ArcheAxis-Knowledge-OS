# 文档导航

> **2026-10-10 当前路由与状态**：产品执行 PAUSED_BY_OWNER，整体 PARTIAL；当前请求仅授权归档和权威/引用治理修复。旧“下一队列/未发布/两树不同”属于历史日期快照；上次源码已发布，本轮最新状态读 [修复回读](current/AAOS-AUTHORITY-REPAIR-20261010.md)。读取任何旧路径前先按 [路径身份路由](current/AAOS-AUTHORITY-ROUTES.json) 分类，不从文件名CURRENT、旧COMPLETE或旧grant推导授权。六项核心能力增量 FROZEN_BY_OWNER，不自动排队；V01暂停、FT01–04冻结。

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


先从 [文档权威索引](DOCUMENTATION_AUTHORITY_INDEX.md) 判断文件的当前、冻结、参考或历史身份。文件名中的 CURRENT、状态快照或旧审计数字不等于实时产品证据。

## 当前执行与职责

- [项目规则](../AGENTS.md)、[项目契约](../PROJECT_CONTRACT.yaml)、[取代台账](../DECISION_SUPERSESSION_LEDGER.yaml)。
- [当前活动指针](current/AAOS-ACTIVE-EXECUTION.json) → [UI 优先任务来源](taskpacks/aaos-ui-first-20261009/TASKPACK.md) → [当前执行进度](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。[AAOS-01 Q台账](current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)只记录继承Q工作流；R6/M0合同与回执保留，其整包顺序不自动执行。
- [产品定位](PRODUCT_POSITIONING.md)：产品边界和术语；[未来蓝图](FUTURE_EXECUTION_BLUEPRINT.md) 是长期候选方向，不代表当前完成度。
- [当前架构职责](architecture/CURRENT_ARCHITECTURE.md)：正式 Tauri 2 + React/TypeScript/Vite、Rust Core、隔离 Python workers 与 legacy 边界；源码职责不等于安装态验证。
- [语言权威](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)、[目录权威](DIRECTORY_AUTHORITY_INDEX.md)、[运行交付权威](RUNTIME_DELIVERY_AUTHORITY_INDEX.md)：职责、路径和迁移约束。
- [9 月 27 日后端整合](current/SEPTEMBER-BACKEND-INTEGRATION-20260927.md)、[文档与分支清理读回](current/SEPTEMBER-CONSOLIDATION-READBACK-20260927.md)：带日期的交付证据；后续操作仍须读取实时 Git/CI。

## 操作与参考

- 根目录 [README](../README.md)：安装、启动和验证入口，须区分正式 vNext 与 legacy 恢复方式。
- [Obsidian-Assistance 吸收记录](ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md)、`bc-lines/`、`three-project-analysis/`：能力演进和项目边界参考。
- [导入设计](architecture/imported-designs/reference-deliveries/archeaxis-2026/)：原始蓝图与校验清单，不是实现证明。

## 历史证据

- [PROJECT_STATUS](PROJECT_STATUS.md)、[9 月 3 日 normalization](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)：历史快照，不能作为当前队列或 GitHub Research 完成度。
- [HERMES_SLEEP_LOOP_ENGINE](HERMES_SLEEP_LOOP_ENGINE.md)：历史工作流参考，不是当前项目执行入口或原生 agent 状态操作授权。
- [历史归档与去重记录](history/DOCUMENT-CONSOLIDATION-20260927.md)：原文、路径、哈希、消费者和回退。
- 根目录旧 handoff/summary、旧 TaskPack 与收据保留其原日期和 SHA；不能从历史恢复被当前 UI 优先任务冻结的旧整包执行路线；R6/M0 仅保留继承约束。
