# AAOS 当前接续导航：人类＋AI＋双侧连接

本入口只保存接续顺序、合同和历史导航。当前授权、执行／监控控制、源码、候选、CI、实际失败与下一步，读取[活动指针](AAOS-ACTIVE-EXECUTION.json)和[唯一执行记录末段](AAOS-UI-FIRST-EXECUTION-20261009.md)，不复制第二份可变进度。日期快照中的“当前／最新／暂停”只说明当时，不能覆盖活动指针选中的后继Owner决定。

**2026-10-29最新交接覆盖：** Owner将前端设计交STITCH、后端有限闭环优化交ZCODE，要求新本地分支、全部能力保留归并迁移、复杂项延期，并禁止ZCODE云仓库与数据上传。先读活动指针`execution_control.owner_handoff_20261029`及[完整交接入口](../../workspace/intake/20261029-stitch-zcode-handoff/README.md)。本阶段禁止push/PR/远端merge/云CI/同步/发布，覆盖下文和旧记录中的历史上传授权；本地合格合并可执行。STITCH只提交设计文字和选定参考图，ZCODE资料留本地。ZCODE报告后由Codex独立审计；提示词不等于网络隔离，严格本地须核编码模型模式，公开检索仅用非敏感公开/合成查询。UI实施与监控仍按原暂停，不自动恢复远端权限。

## 接续顺序

Owner 后继追加外溢数据追踪、迁移和清理，以及 [R5 未来能力承接包独立审计与归档](../../workspace/intake/20261030-r5-future-capability-review/README.md)。外溢先追生产者、配置、所有者、消费者与精确路径，按哈希/恢复核验迁移；不扫描整盘或清理共享库/真实库/私有状态。R5 五场景吸收到现有 R2/CL/J 工作，原始提示词不自动执行，不恢复 UI、不解冻重型扩展；WORK-LAB 仍为可选协调方。实际修复、验证、剩余权限及外溢结果沿唯一执行记录末段，不从本导航复制状态。

2026-10-30 Owner 后继优先级读取活动指针 `execution_control.owner_priority_20261030`：先完成[云端 R2／本地审计归档与任务承接](../../workspace/intake/20261030-cloud-review-and-backend-priority/README.md)，先清理项目体积、规范目录和持续增长治理，再按本地审计缺口及 R2 双侧要求推进既有有限后端。前端布局由 Owner 在云端继续修订；本地 UI 实施与监控不恢复。精确清理清单及结果只沿唯一执行记录读取。

1. 先读[唯一闭环定义](../truth/CLOSED_LOOP_DEFINITION.md)，再核活动指针的 `owner_scope_current`、`execution_control`、`continuation_context`、`delivery_authorization`、`green_update_authorization` 与 `active_progress`。同时核本地Git状态及受保护材料；历史PASS不移绑新源码或候选。
2. 从唯一执行记录末段接续具名阻断，沿原任务ID与[前后端执行覆盖](AAOS-FRONTEND-FIRST-EXECUTION-OVERLAY-20261019.md)落实；不另建任务包、业务库或进度表，不重复无变化的全审计。
3. 独立工作可并行，每个写集一个writer；构建和原生验收期间冻结其绑定的源码与文档。原始失败保留，后继结果另记；本地测试、真实Core／worker、同候选、安装、Green、精确SHA托管CI和Owner接受分别判定。

2026-10-29 的既有边界如下，优先顺序已由 `execution_control.owner_priority_20261030` 更新：后端有限闭环继续，UI构建暂停，允许融合研究、完整STITCH提示词与可落地方案。窗口要求读取 `native_window_policy.latest_owner_clarification`：同一套流式布局，只验看普通较小非最大化窗口与1920×1080满屏；中间自然适配，过小统一缩放，不另造多套尺寸版。1280×800上限和640×480观测属于既有实现记录，不是新增设计套数或已完成统一缩放的证明。有效保存偏好、草稿及降低模糊的要求继续保留。

本轮后继证据及具名未闭合项读取[App-local C++依赖修补、安装态PDF与沙盒清场](AAOS-UI-FIRST-EXECUTION-20261009.md#2026-10-29-app-local-c依赖修补安装态pdf与沙盒清场)，本入口不重复维护结果状态。

## 2026-10-30 ZCODE通宵后端闭环（五轮）与Owner待决清单

ZCODE在`codex/local-backend-closure-20261029`完成五轮并逐轮回写唯一执行记录（续轮一至五小节）：归并/Canvas导出/打包身份转正并本地提交；合格Core构建`b6f5b591…`→staging→混合候选C1→五段同候选链（真实公开检索/格式/学习/j5/REAL_MODEL）→NSIS安装器`3337fce6…`→**沙盒安装生命周期`complete_lifecycle_verified=true`（LOCAL_MIXED_CORE_INSTALLED_LIFECYCLE）**→文档冲突旅程PASS（候选层）；具名2+8条clippy项清零、四crate 184测试二进制全绿。整体如实`LOCAL_BACKEND_SCOPE_PARTIAL_PENDING_CODEX_AUDIT`。

**Owner醒来先读[决策清单](../../workspace/intake/20261030-zcode-backend-closure/OWNER-决策清单.md)**：两项待决——①安装器版本号提升（解锁真跨版本升级/回滚）；②LM Studio监听地址+沙盒网络子决策（解锁安装态AI旅程）。两项均附选项、执行工单与不做时的如实状态。无需决策即可继续的工单（guest内冲突旅程设计、142条非门禁clippy债务、外置索引刷新）已就绪。Codex审计入口在[ZCODE完成报告](../../workspace/intake/20261030-zcode-backend-closure/ZCODE-完成报告.md)。

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
- 复用既有Host/Core进行独立包装时，读取[本地固定构建包装合同](../../workspace/intake/20261029-local-pinned-packaging-contract.md)。它区分历史构建与当前工具身份，不替代CI／安装／发布资格；实际收据与剩余问题仍只沿唯一执行记录接续。
- 路径先查[项目路由登记](AAOS-AUTHORITY-ROUTES.json)、[资料索引](../../AAOS-资料索引.md)、[共享资源路径](../SHARED_RESOURCE_PATH_INDEX.md)、[能力依赖](../../config/environment/capability-requirements.yaml)及具体manifest。路径失效先查归档／ZIP；登记供导航，不授予跨项目或私人内容访问。
- [2026-10-28冻结会话交接](../history/session-handoff-20261028-ui-followup/README.md)与[TRAE历史交接](../history/trae-agent-handoff-20261024/README.md)保留原话、任务和证据；暂停／恢复、候选及CI均以当前指针和执行记录核实，不假定其他客户端已加载规则。

## 已迁出历史

归档前13190字节已[原字节保全](../history/session-handoff-20261028-ui-followup/current-handoff-before-normalization-20261028.md)，摘要、原路径、相对链接基准及替代关系见[归档映射](../history/session-handoff-20261028-ui-followup/current-handoff-normalization-20261028.json)。其中10/26旧候选、最大化预览及旧CI状态已迁出当前入口，原文未改写。更早84979字节入口与映射仍在[10/24归档](../history/project-drift-audit-20261021/current-handoff-before-compaction-20261024.md)及[原映射](../history/project-drift-audit-20261021/current-handoff-compaction-20261024.json)。归档相对链接按映射中的原 `docs/current/` 基准解析；此次减少入口冗余，不声明磁盘空间回收或产品完成。
