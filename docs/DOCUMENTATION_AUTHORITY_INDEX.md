# 文档职责与权威导航

本页只回答“该读哪个规范源”，不复制进度、运行观察或完成结论。换会话先读[根入口](../AUTHORITY.md)、[执行规则](../AGENTS.md)，再按[活动指针的 continuation_context](current/AAOS-ACTIVE-EXECUTION.json)接续。用户当前明确决定与已登记替代关系优先；历史任务包、交接和回执保留各自适用时点与证据身份。

| 职责 | 规范入口 | 使用边界 |
| --- | --- | --- |
| 活跃范围、任务来源与接续顺序 | [活动指针](current/AAOS-ACTIVE-EXECUTION.json) | 由指针选择当前任务包及覆盖合同；不从文件日期或旧 COMPLETE 推断当前队列。 |
| 闭环／最快最短完整闭环的含义 | [唯一闭环定义](truth/CLOSED_LOOP_DEFINITION.md) | 范围、兼容、免费检索、模型双通道及全链路验收的Owner规范；不另设进度，不缩成单次演示。 |
| 实际实施进度与验收证据 | [唯一 UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md) | 回执只证明其绑定源码、对象和环境；规划包中的 NOT_EXECUTED 不回填为运行结果。 |
| 当前交接与未完成事项 | [接手入口](current/AAOS-AGENT-HANDOFF-CURRENT.md)、[来源待办索引](current/AAOS-EXECUTION-BACKLOG-20261018.json) | 交接与待办用于续接，实际进度仍归唯一执行记录。 |
| Owner 决定、范围与替代关系 | [当前决定](current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[替代账本](../DECISION_SUPERSESSION_LEDGER.yaml)、[稳定真相](truth/README.md) | 决定出处与历史摘录由历史入口导航；实现证据不能取消已批准目标。 |
| 产品原则与任务合同 | [项目合同](../PROJECT_CONTRACT.yaml)、[当前任务包](taskpacks/aaos-ui-first-20261009/TASKPACK.md)；继承／覆盖合同：[后端合同](authority/taskpack-20261013-backend-host/TASKS.json)、[前端合同](authority/taskpack-20261013-frontend-ui/01-Frontend-UI/TASKS.json) | 具体激活范围读活动指针；不可变任务包是合同来源，不是第二份实时进度。 |
| 协议、生成物与源码验证入口 | [协议 Schema](../packages/contracts/)、[生成器](../scripts/contracts/)、[契约测试](../tests/)、[Rust Core](../crates/)、[正式前端](../frontend/)、[正式宿主](../src-tauri/) | Schema、实现与行为回归分别核对；仅有声明或生成 DTO 不代表真实消费者已接通。 |
| 原始资料与来源 manifest | [资料索引](../AAOS-资料索引.md)、[输入来源登记](current/AAOS-INPUT-SOURCES-20261006.json)、[原始资料清单](history/record-archive-20261009/MANIFEST.json) | 按登记路径和 SHA 查原件；索引不是跨项目或私人资料访问授权。 |
| 共享库、工具、模型与本机资源 | [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md)、[依赖声明](../config/environment/capability-requirements.yaml)、[资源观察](../config/environment/external-resources-index.json) | 登记不等于安装、可执行或可用；版本、权限及运行状态须现场核实，不猜外置根。 |
| 验证规则与交付边界 | [验证策略](VERIFICATION_POLICY.md)、[Gate 登记](../.worklab/gate-registry.v1.yaml)、[路径风险映射](../.worklab/project-validation.v1.yaml)、[运行与交付导航](RUNTIME_DELIVERY_AUTHORITY_INDEX.md) | 区分结构检查、本地测试、exact-SHA CI、原生运行和 Owner 验收；PASS 不自动授予发布或 Green 替换权限。 |
| 配置与语言边界 | [配置权威](CONFIGURATION_AUTHORITY_INDEX.md)、[语言边界](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) | 配置各归其唯一源；不把历史实现语言或供体位置当正式宿主。 |
| 目录、路径身份与归属 | [目录权威](DIRECTORY_AUTHORITY_INDEX.md)、[目录登记](../DIRECTORY_AUTHORITY.yaml)、[旧路径路由](current/AAOS-AUTHORITY-ROUTES.json) | 旧路径按登记解析；别名不产生第二份可变原件，也不改变资源归属。 |
| 历史报告、旧 current、旧规划与冻结证据 | [统一历史入口](history/README.md)、[本轮迁移清单](history/repository-consolidation-20261019/MANIFEST.json) | 原路径、归档路径与字节身份由清单核对；历史原文中的相对链接按原位置解释，不在旧位置重建副本。 |

仍适用的继承约束可从 [M0 方向覆盖](history/repository-consolidation-20261019/current/M0-DIRECTION-OVERRIDE-20260920.md)与 [R6 合同的 Release 全面冻结章节](authority/taskpack-0919-r6/TASKPACK.md#2-release-全面冻结)查证。它们保留适用的保存原则、单一正典写者、证据和发布边界；旧整包执行顺序不作为当前队列。后继决定的适用范围由活动指针和替代账本判断。

历史观察、旧 latest 段落和本轮迁移前的导航原件统一保存在上述历史体系；本页不据其声明当前 SHA、CI、模型、依赖或运行状态。
