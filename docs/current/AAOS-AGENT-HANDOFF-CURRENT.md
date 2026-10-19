# 当前 Agent 接手入口

状态 **RUNNING_BY_OWNER / PARTIAL**。本页只导航，不保存多轮测试快照；实际进度唯一来源为 [UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。

1. 先读 [根权威](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[活动指针](AAOS-ACTIVE-EXECUTION.json) 与 [文档职责索引](../DOCUMENTATION_AUTHORITY_INDEX.md)。
2. 读 [Owner 决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)、指针选择的任务来源与 [待办来源索引](AAOS-EXECUTION-BACKLOG-20261018.json)。既有实现先读源码及对应回执，避免重复实施。
3. 查 [共享路径](../SHARED_RESOURCE_PATH_INDEX.md)、[运行依赖声明](../../config/environment/capability-requirements.yaml)、[本地模型入口](AAOS-LOCAL-LLM-20261018.md)。登记不替代现场版本、加载、推理与权限检查。
4. 会话出处读 [项目会话索引](AAOS-CODEX-SESSION-INDEX-20261018.md)、[已授权资料整合](AAOS-SESSION-RECONCILIATION-20261018.md) 与 [Owner 原话映射](../history/owner-dialogue-20261019/README.md)，不猜私人路径或扫描原生会话。

当前采用强核心底座与按需能力接入；模型调度、权限、持久化、多格式基本链属于底座，扩展在既有能力中心按插件、技能、MCP 或模板表达。专业 PSD／AI／CDR／CAD／3D 源格式已移出直接支持目标。小栖在 AAOS 内适配；ASTRYN 源仓仍未取得删除资格。

旧报告、旧 current、旧收据和旧目录统一见 [历史入口](../history/README.md) 及 [迁移清单](../history/repository-consolidation-20261019/MANIFEST.json)。[路径身份登记](AAOS-AUTHORITY-ROUTES.json) 可解析旧路径；不在旧位置重建副本。仍绑定的 M0/R6 约束继续有效，旧整包执行顺序不重新激活。

接续应优先处理实际未闭环的模型完整旅程、BE10 外部投递与原生交互、常用格式同候选运行及安装验收。以唯一执行记录和现场 Git/CI 核对状态，不能把归档、单测、构建或模型加载称为完整产品通过。

只运行变更相关检查，按 [验证策略](../VERIFICATION_POLICY.md) 决定必要门禁。V01 暂停、FT01–04 冻结；发布、Green 替换、真实数据覆盖及未知共享进程操作不因本轮整理获得授权。
