# 后端职责归并与前端场景衔接

2026-10-29。Owner要求“所有能力重新分类整理合并，界面不分这么细”，随后明确“后端也需要调整，该合并的合并”。本增量接续活动指针选定的后端有限开发；正式UI实现仍暂停。不新建执行队列，不将分类整理当成产品能力已完成。

## 结论

前端继续采用工作台与四个业务场景。后端将可共用的规则、调度和对象访问收敛到既有Core内部；业务入口可以组合相同服务，不为每个界面分组新建一套后端。四个场景是用户工作的组织方式，不要求把Rust模块机械改成四个巨型文件，也不要求移动已有数据。

本轮落实五类内部重复规则归并，保持公开路由、请求／响应合同、数据库结构与既有数据不变。未进行数据库迁移或实际数据合并。

## 对应关系与保留边界

以下是既有模块的职责归组和前端组合方向，不新增六个进程、六份数据库或六个导航入口。模块存在不等于其全部蓝图能力已接入或通过安装态验收。

| 职责归组 | 前端使用位置 | 既有实现承接 | 合并方式及边界 |
| --- | --- | --- | --- |
| 资料与知识 | 资料收集、识别校对、阅读、笔记、组织、图谱 | domain的source、document、anchor、collection、object_reference、relation_projection、search、vault | 共用Source／Document／版本引用和查询；原件、可编辑正文、知识接纳各自保留含义，不多写一份知识数据库 |
| 研究与比较 | 免费外部检索、多源比较、疑点、纠错、研究板 | research、public_research、material_question；API的对应runtime与定位接口 | 复用资料对象、定位、引用、检索和任务控制；外部结果不能因界面合并而直接变成已接纳知识，普通保存仍不依赖联网成功 |
| 学习与表达 | 课程、练习、复习、表达、成果导出 | learning、course、teaching、expression、portable_document；现有documents导出入口 | 共用内容、引用、导出和资源访问；学习表现与AI评测不合并为一个评分记录，已有格式的损失范围继续显式保留 |
| AI助手 | 上下文问答、陪伴、AI候选与修订、授权连接 | machine、machine_evaluation、ai_asset、character_memory、context_grant、asset_context_grant、external_context；现有conversation／material runtime | 共用受控上下文、模型配置、取消和结果发布边界；人类学习、AI资产、机器收据及授权仍各自保存，候选不能自动越过接纳和执行权限 |
| 共享任务与能力底座 | 全局任务抽屉、各业务的状态和取消 | application的Executor、jobs、attempts、scheduler；API runtime、capabilities；store的capability_settings | 统一已有共用策略和只读状态解释；文件转换job与机器执行的取消合同不同，当前不强行合表或用一个状态覆盖两者 |
| 共享资源与系统底座 | 资源中心、设置、诊断、日志、备份恢复 | template_definition、template_binding、model_configuration、configuration_plans、readiness、failure_log、backup、ui_state及既有store | 共用能力发现、配置来源和入口；模板定义、Python provider、AI技能资产保留类型与生命周期，诊断日志不能替代业务任务历史 |

单一Rust Core继续通过现有store写入SQLite／CAS。Python worker不获得数据库句柄，前端不直接写数据库。现有API facade与application/domain/store分层保留，归并发生在内部策略复用处。

## 已落地的归并

1. **研究关系的共同校验。** 研究保存与历史图谱读取共用`research::validate_relations_with`，统一schema、条数、ID唯一性、标签字节限制与目标校验顺序。保存路径传入实际对象解析；历史图谱仅检查引用形状，合法但缺失的对象仍是`unavailable`，不能误报为不支持的历史内容。逐条校验保留首个错误的次序，避免后面的坏ID遮盖前面的缺失目标。
2. **对象引用的共同形状校验。** `object_reference::resolve`沿用入口处的`validate_shape`，移除Document／Source／Knowledge分支内重复检查。固定文档版本、块存在性、source hash匹配、knowledge存在性检查继续保留，未新增CAS读取。
3. **四类机器请求的共同取消规则。** conversation、material_questions、public_research、machine_journal共用`MachineActive::request_cancel`。调用仍发生在与发布关闭相同的registry锁内；各自请求键、attempt／restore_epoch限制、身份检查及原响应状态不变。重复取消在仍可接收时保持原行为。取消请求成功仍不代表provider已经停止。
4. **能力列表与详情的共同provider记录。** `registered_record`收敛默认provider、备用provider及声明记录组装。保持声明顺序、原选择算法、仅默认行附带fallback；健康握手仍由原有显式观察路径执行。能力启停回读继续使用`observe_health=false`，不因修改开关启动worker。
5. **模板两入口的共同事务提交。** 生命周期变更与旧启停入口共用`commit_state`，在同一事务内递增epoch、写状态、回读和commit。两入口的前置条件仍分别检查，保留expected_epoch、definition hash、未安装启用拒绝与旧对象访问规则；未把模板降格为普通布尔开关。

本轮产品写集为`crates/archeaxis-api/src/capabilities.rs`、`runtime/{mod,conversation,material_questions,public_research,machine_journal}.rs`，以及`crates/archeaxis-domain/src/{research,relation_projection,object_reference,template_definition}.rs`。测试写集为`crates/archeaxis-domain/tests/relation_projection.rs`。其余既有dirty成果保留，不纳入本增量的所有权。

## 后续接入的方式

这些是后续设计／实施约束，尚未全部编码：

- **场景组合：** 同一Document／固定版本引用可以在阅读、研究、学习和AI窗口中打开，任务抽屉根据真实业务ID打开原记录。布局拖拽、窗口组合与粒子光效属于前端呈现；粒子选中时使用实际对象引用加载详情，不能把可视节点位置作为新的知识身份。
- **任务展现：** 前端可以用一个任务列表展示转换、检索、AI请求等，但保留原任务类型、ID、尝试、状态、原始失败与未知状态。先用既有接口组合只读结果；只有真实消费需求证明有必要时再加薄的聚合查询，不先创建通用任务平台或第二个后台调度器。
- **资源入口：** 模板、插件、技能、模型、导入／导出适配器可在同一资源中心按类型筛选。发现入口与通用启用信息可复用；安装、授权、版本、适用范围、应用和卸载仍遵循各自合同。已发现或已安装不自动等于可执行。
- **未来能力：** 沿前端能力映射展示“待开发／待接入／需配置／可用”等真实状态。规划状态来自蓝图，运行状态来自现有实际注册、配置及资格；不能把蓝图条目伪装为活的Core路由。现有provider注册只覆盖其合同支持的能力，不把所有未来能力硬塞成Python worker。
- **日志与诊断：** 用户可从任务或对象跳到关联诊断，系统设置集中展示环境与健康。业务收据、失败日志、UI恢复状态、模型观测保留原语义，避免共用一个“成功”字段隐藏未验证、未知、撤销或失败。

当前没有新增Marketplace、通用Agent Runtime、任意代码执行或企业协作；未来3D／空间展现按原蓝图保留，不能以本次辅助光效研究宣称这些能力已经实现。完整能力意图继续引用既有186项映射，不另复制一份可变能力清单。

## 验证与证据

变更前以现有domain/API合同测试建立基线；变更后复验同一合同，并补充跨保存／历史投影的引用回归、首错顺序与取消可重复性检查。此次是行为保留的重构，未新增产品业务行为，不伪造新行为的RED阶段。

正式执行证据与本轮有限范围汇总见[本地归并回执](../../.project-local/runs/be268a2d33/backend-merge-api-final-20261029/artifacts/backend-consolidation-receipt.json)。同目录的`backend-consolidation-review.md`记录一次只读定向源码审查；各测试run保留自己的`execution.json`和日志。最终测试绑定同一执行期dirty patch；本说明与进度回写发生在测试之后，不能把该patch身份称为当前整个工作树的发布身份。

现有未使用导入／字段编译警告保留，没有顺带改动无关模块。此次本地Rust测试不构成真实模型推理、外部论坛访问、原生Host、当前安装包、新精确SHA CI或Owner验收。现有安装包没有包含本增量；后继须由新Core构建和对应制品身份承接，不能借用旧包的资格。

## 回退及产物归属

没有schema迁移与真实数据改写，回退只需撤销上述本轮代码hunk和测试增量；不得用整仓reset覆盖原有dirty成果。公开说明归项目；回执、审查记录和测试日志位于dev launcher已分配的ignored run，属于本轮生成证据，可按相同命令重建。它们当前被此说明和唯一进度记录引用，应在后继验证替代并更新引用后再决定回收，不能因目录是临时运行目录就自动删除。
