# AAOS 当前接续导航：人类＋AI＋双侧连接

本入口只保存接续顺序、合同和历史导航。当前授权、执行／监控控制、源码、候选、CI、实际失败与下一步，读取[活动指针](AAOS-ACTIVE-EXECUTION.json)和[唯一执行记录末段](AAOS-UI-FIRST-EXECUTION-20261009.md)，不复制第二份可变进度。日期快照中的“当前／最新／暂停”只说明当时，不能覆盖活动指针选中的后继Owner决定。

## 接续顺序

1. 先读[唯一闭环定义](../truth/CLOSED_LOOP_DEFINITION.md)，再核活动指针的 `owner_scope_current`、`execution_control`、`continuation_context`、`delivery_authorization`、`green_update_authorization` 与 `active_progress`。同时核本地Git状态及受保护材料；历史PASS不移绑新源码或候选。
2. 从唯一执行记录末段接续具名阻断，沿原任务ID与[前后端执行覆盖](AAOS-FRONTEND-FIRST-EXECUTION-OVERLAY-20261019.md)落实；不另建任务包、业务库或进度表，不重复无变化的全审计。
3. 独立工作可并行，每个写集一个writer；构建和原生验收期间冻结其绑定的源码与文档。原始失败保留，后继结果另记；本地测试、真实Core／worker、同候选、安装、Green、精确SHA托管CI和Owner接受分别判定。

Owner后继要求默认普通窗口、按显示缩放和工作区适配，上限1280×800；小窗正文优先，菜单、人物／资料侧窗和Dock仍可操作，并降低毛玻璃模糊度。有效保存偏好及业务草稿须保留。实际实现与原生验证读执行记录“后继原生验证与默认小窗口”及其后继，不把旧最大化预览或旧截图当成现状。

## 范围与保护边界

- 本期保留人类资料／研究／知识／学习／恢复、AI候选治理／授权使用／纠正复测／恢复，以及两侧按权限复用同一来源和版本。CL-01—07/J1—6不能缩成单次导入问答；外部原始上下文系统是否连接单独核实。
- 模型按[决定二十三](AAOS-OSS-INTEGRATION-DECISION-20261019.md#二十三先落地可用产品本地模型优先云端专业接口2026-10-24)：沿既有已测试本地路线，云端专业接口仍须验收，真实云推理延期；不改服务商、端点、鉴权或全局设置，不以模拟回答冒充真实推理。
- 来源用途按[决定二十四／SUP-029](AAOS-OSS-INTEGRATION-DECISION-20261019.md#二十四多源检索辅助纠错与成熟方案优先2026-10-26)及 [PROJECT_CONTRACT](../../PROJECT_CONTRACT.yaml) 的 `content_policy`：回查、定位、多源比较、保留分歧并持续纠正；普通保存、展示和学习不以联网或人工事实审批为前置。优先复用成熟组件及官方接口。
- 全量截图包与MiniMax该批素材已取消，按需截图和副本清理读[取消决定](AAOS-UI-FIRST-EXECUTION-20261009.md#2026-10-28-owner取消全量截图交付并清理副本)及最新清理回执。原图、唯一失败、原件、最新候选、构建缓存与六项预存dirty/untracked材料受保护；目录陈旧或体积大不构成删除依据。
- 订阅剩余≤10%时停止新增任务、安全封存、整理交接，上传已授权公开进度，仅处理资格满足的必要合并并读回双端SHA，见[停止与接续规则](AAOS-UI-FIRST-EXECUTION-20261009.md#2026-10-28-额度10停止与接续交接)。当前是否触发及监控状态以活动指针为准；继续开发不自动恢复监控。
- 输出、缓存、临时脚本和证据使用ignored `.project-local/` 与 canonical `scripts/runtime/dev.py`。项目运行资料、Agent私有状态和产品工作区按归属保护；不扫描凭据、私人会话或未授权磁盘，不自动替换Green、发布或覆盖真实数据。提交、推送、合并分别核当前授权及检查条件；拒绝不换渠道绕过。

## 合同与资料定位

- 根规则：[AGENTS](../../AGENTS.md)、[AUTHORITY](../../AUTHORITY.md)、[PROJECT_CONTRACT](../../PROJECT_CONTRACT.yaml)。Owner决定及替代关系读[当前决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[10/19冻结原话与映射](../history/owner-dialogue-20261019/README.md)和[10/23完整交接](../history/owner-dialogue-20261023-thread-handoff/README.md)。历史权限仅作来源。
- 当前合同：[TASKPACK](../taskpacks/aaos-ui-first-20261009/TASKPACK.md)、[TASKS](../taskpacks/aaos-ui-first-20261009/TASKS.json)、[页面计划](../taskpacks/aaos-ui-first-20261009/PAGE-PLAN.csv)、[冻结登记](../taskpacks/aaos-ui-first-20261009/FREEZE-REGISTER.md)；补充[前端合同](../authority/taskpack-20261013-frontend-ui/01-Frontend-UI/TASKPACK.md)和[后端宿主合同](../authority/taskpack-20261013-backend-host/TASKPACK.md)。计划时NOT_EXECUTED不替代实际执行记录。
- 路径先查[项目路由登记](AAOS-AUTHORITY-ROUTES.json)、[资料索引](../../AAOS-资料索引.md)、[共享资源路径](../SHARED_RESOURCE_PATH_INDEX.md)、[能力依赖](../../config/environment/capability-requirements.yaml)及具体manifest。路径失效先查归档／ZIP；登记供导航，不授予跨项目或私人内容访问。
- [2026-10-28冻结会话交接](../history/session-handoff-20261028-ui-followup/README.md)与[TRAE历史交接](../history/trae-agent-handoff-20261024/README.md)保留原话、任务和证据；暂停／恢复、候选及CI均以当前指针和执行记录核实，不假定其他客户端已加载规则。

## 已迁出历史

归档前13190字节已[原字节保全](../history/session-handoff-20261028-ui-followup/current-handoff-before-normalization-20261028.md)，摘要、原路径、相对链接基准及替代关系见[归档映射](../history/session-handoff-20261028-ui-followup/current-handoff-normalization-20261028.json)。其中10/26旧候选、最大化预览及旧CI状态已迁出当前入口，原文未改写。更早84979字节入口与映射仍在[10/24归档](../history/project-drift-audit-20261021/current-handoff-before-compaction-20261024.md)及[原映射](../history/project-drift-audit-20261021/current-handoff-compaction-20261024.json)。归档相对链接按映射中的原 `docs/current/` 基准解析；此次减少入口冗余，不声明磁盘空间回收或产品完成。
