# 文档导航

文档按“当前事实、运行操作、设计参考、历史快照”区分。历史审计中的数字不能代替实时测试和 `/health`。

## 当前事实与未来方向

- [`truth/README.md`](truth/README.md)：Truth Spine、冻结任务基线、追加式执行状态与 DeepSeek 全量执行入口。
- [`PRODUCT_POSITIONING.md`](PRODUCT_POSITIONING.md)：ArcheAxis OS 对外产品定位、治理边界与术语。
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)：当前验证状态、已知限制和质量门禁。
- [`FUTURE_EXECUTION_BLUEPRINT.md`](FUTURE_EXECUTION_BLUEPRINT.md)：长期设计原则、候选轨道、延后项和进入执行门槛；不代表当前完成度。
- [`architecture/CURRENT_ARCHITECTURE.md`](architecture/CURRENT_ARCHITECTURE.md)：当前运行时架构与模块边界。
- [`ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md`](ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md)：Obsidian-Assistance 能力吸收总账。

## 运行操作

- [`HERMES_SLEEP_LOOP_ENGINE.md`](HERMES_SLEEP_LOOP_ENGINE.md)：无人值守循环。
- 根目录 `README.md`：安装、启动、稳定入口和验证命令。

## 当前执行包

- [`taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`](taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md)：DeepSeek 可续跑的全量执行协议。
- [`taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`](taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md)：网页知识摄取的原始固定任务、安全和安装态增补。
- [`taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`](taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md)：供应商可替换、能力不可删的搜索—摄取—课程—学习—AI 复用全链路强制增补。

## 设计与参考

- `bc-lines/`：B/C 线设计和开源项目吸收注册。
- `three-project-analysis/`：三项目边界与历史分析。
- [`architecture/imported-designs/reference-deliveries/archeaxis-2026/`](architecture/imported-designs/reference-deliveries/archeaxis-2026/)：用户提供的 ArcheAxis/MCS/Google Research 原始蓝图与校验清单；仅设计参考，不是当前实现证明。
- [`architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/`](architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/)：2026-08-09 原始蓝图、规划、v3/v4 任务包与 handoff 的不可变来源归档；当前执行仍由冻结基线和批准增补定义。

## 历史快照

- `PROJECT_AUDIT_2026-07-07.md`：2026-07-07 的审计快照。其中 `/run`、Ruff、版本漂移等问题已在后续修复；不得当作当前状态直接引用。

历史 handoff、TaskPack 与过期路线图已移除；Git 历史保留其可追溯性。当前 GitHub Research scope 以 `PROJECT_STATUS.md` 为准：它是 candidate-only、持久化的 `ResearchPackageV1` 工作流，不自动提升为 verified truth。
