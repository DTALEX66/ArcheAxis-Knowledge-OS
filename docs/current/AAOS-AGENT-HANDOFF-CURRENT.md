# 当前 Agent 接手入口

> **本对话最新收尾（2026-10-19）**：Owner要求中断后归档并上传，当前不再新增产品修改，不承诺自动继续。先读[本对话汇总与遗留项](../history/product-loop-20261019/conversation-closeout.md)及其中CI快照，再现场核Git/PR最新状态。产品总体PARTIAL；旧源码867d7c8a的安装grouped UI旅程FAIL，整轮CI取消，先读证据包再定位，不能报全绿；旧报告只代表各自时点。

状态 **RUNNING_BY_OWNER / PARTIAL**：Owner 明确要求今天停止额度监控并继续完成当前任务。今天不查询额度、不因额度阈值停工；已知监控id archeaxis的删除接口返回not_found；截图未命名卡片的身份仍未核实，详见收尾归档。当前收尾菜单密度、玻璃外框及安装冲突探针导航，实际进度唯一来源为 [UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。

1. 先读 [根权威](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[活动指针](AAOS-ACTIVE-EXECUTION.json) 与 [文档职责索引](../DOCUMENTATION_AUTHORITY_INDEX.md)。
2. 读 [Owner 决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)、指针选择的任务来源与 [待办来源索引](AAOS-EXECUTION-BACKLOG-20261018.json)。既有实现先读源码及对应回执，避免重复实施。
3. 查 [共享路径](../SHARED_RESOURCE_PATH_INDEX.md)、[运行依赖声明](../../config/environment/capability-requirements.yaml)、[本地模型入口](AAOS-LOCAL-LLM-20261018.md)。登记不替代现场版本、加载、推理与权限检查。
4. 会话出处读 [项目会话索引](AAOS-CODEX-SESSION-INDEX-20261018.md)、[已授权资料整合](AAOS-SESSION-RECONCILIATION-20261018.md) 与 [Owner 原话映射](../history/owner-dialogue-20261019/README.md)，不猜私人路径或扫描原生会话。

当前采用强核心底座与按需能力接入；模型调度、权限、持久化、多格式基本链属于底座，扩展在既有能力中心按插件、技能、MCP 或模板表达。专业 PSD／AI／CDR／CAD／3D 源格式已移出直接支持目标。小栖在 AAOS 内适配；ASTRYN 源仓仍未取得删除资格。

旧报告、旧 current、旧收据和旧目录统一见 [历史入口](../history/README.md) 及 [迁移清单](../history/repository-consolidation-20261019/MANIFEST.json)。[路径身份登记](AAOS-AUTHORITY-ROUTES.json) 可解析旧路径；不在旧位置重建副本。仍绑定的 M0/R6 约束继续有效，旧整包执行顺序不重新激活。

接续应优先处理实际未闭环的模型完整旅程、BE10 外部投递与原生交互、常用格式同候选运行及安装验收。以唯一执行记录和现场 Git/CI 核对状态，不能把归档、单测、构建或模型加载称为完整产品通过。

只运行变更相关检查，按 [验证策略](../VERIFICATION_POLICY.md) 决定必要门禁。Owner 后继已允许覆盖 `D:\All projects\ArcheAxis.Knowledge.Green-x64` 的程序文件；按活动指针 `green_update_authorization` 先保全程序回退、核实候选与停止状态，再更新并读回身份。现有候选安装失败尚未闭环，此授权不是安装资格。V01 暂停、FT01–04 冻结；公开发布、真实数据覆盖及终止未知共享进程仍未授权。
