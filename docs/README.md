# 文档导航

文档按“当前事实、运行操作、设计参考、历史快照”区分。历史审计中的数字不能代替实时测试和 `/health`。

先从 [`DOCUMENTATION_AUTHORITY_INDEX.md`](DOCUMENTATION_AUTHORITY_INDEX.md) 判断一份文件是否为当前权威、冻结基线、计划、参考或历史记录；不要仅按文件名或日期引用。

## 当前事实与未来方向

- [`PRODUCT_POSITIONING.md`](PRODUCT_POSITIONING.md)：ArcheAxis Knowledge 对外产品定位、治理边界与术语。
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)：当前验证状态、已知限制和质量门禁。
- [`FUTURE_EXECUTION_BLUEPRINT.md`](FUTURE_EXECUTION_BLUEPRINT.md)：长期设计原则、候选轨道、延后项和进入执行门槛；不代表当前完成度。
- [`architecture/CURRENT_ARCHITECTURE.md`](architecture/CURRENT_ARCHITECTURE.md)：当前运行时架构与模块边界。
- [`ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md`](ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md)：Obsidian-Assistance 能力吸收总账。
- [`LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)：Python/React/Rust 的当前职责、兼容命名与迁移 no-go 门禁。
- [`DIRECTORY_AUTHORITY_INDEX.md`](DIRECTORY_AUTHORITY_INDEX.md)：源码、兼容层、历史记录、运行态与外置库的路径分类。
- [`current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md`](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)：当前目录清理、权威索引与语言边界工作的统一队列；不是删除或迁移授权。

## 运行操作

- [`HERMES_SLEEP_LOOP_ENGINE.md`](HERMES_SLEEP_LOOP_ENGINE.md)：无人值守循环。
- 根目录 `README.md`：安装、启动、稳定入口和验证命令。

## 设计与参考

- `bc-lines/`：B/C 线设计和开源项目吸收注册。
- `three-project-analysis/`：三项目边界与历史分析。
- [`architecture/imported-designs/reference-deliveries/archeaxis-2026/`](architecture/imported-designs/reference-deliveries/archeaxis-2026/)：用户提供的 ArcheAxis/MCS/Google Research 原始蓝图与校验清单；仅设计参考，不是当前实现证明。

## 历史快照

- `PROJECT_AUDIT_2026-07-07.md`：2026-07-07 的审计快照。其中 `/run`、Ruff、版本漂移等问题已在后续修复；不得当作当前状态直接引用。

根目录中仍有待迁移的历史 handoff 和 summary；它们的归类及安全迁移条件见
[`DOCUMENTATION_AUTHORITY_INDEX.md`](DOCUMENTATION_AUTHORITY_INDEX.md)，不得作为当前任务权威。
当前 GitHub Research scope 以 `PROJECT_STATUS.md` 为准：它是 candidate-only、持久化的
`ResearchPackageV1` 工作流，不自动提升为 verified truth。
