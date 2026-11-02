# AAOS 当前状态与执行入口

入口角色：navigation-only。项目身份：**ArcheAxis-Knowledge-OS（AAOS／星环知识系统）**。本页是醒目的薄入口；产品定义由[AUTHORITY总纲](AUTHORITY.md)、[产品身份V2.3](docs/truth/PRODUCT_IDENTITY_V2.md)与[唯一闭环V3](docs/truth/CLOSED_LOOP_DEFINITION.md)承载，控制和进度仍各只有一个来源。

## 当前有效决定与范围

- **执行控制提示：** 2026-11-01本次接手时官方额度读回触及Owner既定的剩余≤10%停止阈值，随后Owner知情明确要求“继续”；当前状态及既有规则以[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)为准，封存、失败与未完项见[唯一执行记录末段](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。
- **本轮优先级：** Owner先要求推进全部后端任务与两平台真实源码复用，后又要求先联网调研并重新思考界面、上传公开项目成果并合并合格分支。前端[调研与设计概念](docs/design/20261102-ui-research/界面调研与重设计方案.md)不代表产品实现或验收；具体授权和实际进度分别读[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)与[唯一执行记录](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。
- 两个核心：通用知识底座、人类与AI双向学习。人类侧贯通知识、研究、学习、表达、实践记录与复习；AI侧将**任何领域**AI工作中可转化的成果、问题、方法、流程、规范与更新提炼为知识，治理、使用、反馈、纠正和复测。原始跨项目完整会话/工具轨迹留在外部系统。
- **Owner最新确认以刚完成的AUTHORITY总入口、[近两日13组对话与任务包总对照](docs/history/owner-dialogue-20261101-current-goals/README.md)、产品身份V2.3及唯一闭环V3为最新基准；其他资料均为历史和补充材料。** 新包目标采用SUP-030，AI含义按SUP-031；[统一归档来源对账](workspace/intake/20261101-project-archiving-reconciliation/README.md)仅承接本轮治理，不覆盖该基准，见[Owner决定第二十七节](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md#二十七统一归档对账与顶层防漂移2026-11-01)和[SUP-032](DECISION_SUPERSESSION_LEDGER.yaml)。
- **AI-WORK-LAB／AIWORKLAB是WORK-LAB与DESIGN-LAB融合后的独立项目**；旧两目录是历史/迁移来源，AAOS独立运行，不共享业务DB、不依赖它运行。
- 后继Owner已选定**DeepTutor1.7.1与OpenMAIC1.3.0能力接入**，并要求新会话承接全部未完事项。读[完整执行提示词](workspace/intake/20261101-learning-platform-integration/新会话完整执行提示词.txt)、[接线与15组未完拆分](workspace/intake/20261101-learning-platform-integration/FOLLOWUP-WORKBREAKDOWN.md)及[原件绑定](workspace/intake/20261101-learning-platform-integration/MANIFEST.json)。两ZIP已独立保存在本仓；部分后端接线已写入源码，编译、实际运行及完整产品并入状态以[唯一执行记录](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)为准，不继承旧供体运行资格。
- 前轮归档治理已完成来源补齐与独立保全；外部Project Archiving、Record、xiangmuguidang只留溯源，不再是原件读取的前提。新接入继续复用正式宿主/Core和既有任务，不建第二业务库或通用Agent Runtime。整体目标、UI全面布局、监控、交付/发布、Green和真实库操作仍分别按[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)及对应Owner授权判断；原归档回合的未实施声明不阻止新选定接入工作。

## 有效规划、已补齐与证据

- 原执行队列：[AAOS-UI-FIRST任务包](docs/taskpacks/aaos-ui-first-20261009/TASKPACK.md)；选择、优先级与授权读[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)，实际结果和未完成项只记[唯一执行记录](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。CAP/REQ旧阶段字段不能取消V3的当前required，也不能充当现版本实现证据。
- 已将近期定位、闭环、对话决定和包的替代关系集中归位；[13组可见原话与R2/R5/R6/v3后继链](docs/history/owner-dialogue-20261101-current-goals/README.md)是Owner此次确认的最新对照入口，不被归档对账取代。
- 本轮补存10/23分离任务书原字节；保留其当时“人类侧不改/编程示例”的来源身份，以后继决定解释。10/09恢复包125成员在本仓已有等价字节，复用来源映射，不再复制64MB包。
- 本轮逐项来源、处理/验证状态、去重/替代与范围计数见[归档对账入口](workspace/intake/20261101-project-archiving-reconciliation/README.md)。扫描、语义对账、源码定位和产品行为验收分别报告。
- Owner后继要求“都在仓库、独立”：历史原件的有效读取沿[仓库内来源清单](workspace/intake/20261101-project-archiving-reconciliation/LOCAL-SOURCES.json)，路径全部相对本仓；外部原位置仅溯源。原件在本地Git忽略区，完整复制本地项目须带`.project-local/archives/`，仅clone源码不含这些原件。
- 代码依据：[既有文档门禁](scripts/ci/check_document_authority.py)与[反例测试](tests/workflow/test_document_authority_gate.py)覆盖入口丢失、错误项目、读序遗漏、私有/越界引用和竞争权威/队列；只能证明这些有界防漂移行为，不能证明任意文字永不漂移。实际运行资格沿本轮对账入口所指回执。

## 未完成、阻塞与下一步

1. 完整CL-01—07/J1—6、X1—X8及R6跨消费者旅程仍按唯一执行记录逐项验收；图谱、映射、效果图、候选接口和本轮档案恢复均不等于产品全链通过。
2. F05真实学习改善、独立复测、真实模型消费及安装态/Owner接受缺口分别保留；未验证的历史引擎、课程/空间能力、技能模板和开源接入不能写成已实现。
3. 旧构建/候选归一、持续增长治理、Green外溢迁移及后继交付尚有具名未闭合项；按唯一执行记录末段和原稳定ID接续，不从本页另排队。
4. 归档正文存在跨项目内容，必须区分不适用、历史来源与有效AAOS要求；未进行的附件视觉/听觉或产品操作检查明确保留，不以总扫描数抹平。
5. 下一步按[新会话完整执行提示词](workspace/intake/20261101-learning-platform-integration/新会话完整执行提示词.txt)并行接入两供体、P0治理及原具名未完项；再按[当前交接](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)和活动指针落实权限/实际进度，不重复已完成归档或历史全审。旧七项前端失败已有后继全量通过，待验的是当前候选与Owner接受。2026-11-02本轮已交付DeepTutor正式评分链与OpenMAIC场景v2契约切片（本地定向验证），修复`lint`、gitleaks、`workers-vnext`、`desktop-build`四个云端必需门禁阻断并发布候选；精确SHA门禁、合并与安装态仍未证。下一步优先级：等当前SHA必需门禁读回并合并；补正式宿主对practice-grade的前向命令与打包声明；处理DISPATCHED残留对账与真实课程链未证项。

## 最近核验的版本边界

日期：**2026-11-02（Asia/Shanghai）**。合并候选精确SHA：`4bed2d0983fdade6df8ed0211ff9e1dee06c3be5`（分支`codex/delivery-20261102`，非强推发布）；其精确SHA必需门禁与`a0-gates`通过后，PR #206以merge commit`b10fba47419947d5f4b00add48fb84e88b9b4666`进入远端main；随后只记录该事实的PR #207以merge commit`fcecb6b4db541698a1cb8f8b11b051fd0fb4cdfa`合并；PR #209（`2013c27b`，正式宿主暴露practice-grade并在安装闭包加入评分worker）以merge commit`0da0e59dbbf5ad29eb91080211f613f64a0cddcf`合并，当前远端main与本地main同为`0da0e59dbbf5ad29eb91080211f613f64a0cddcf`。门禁结果保留两次负载敏感失败：安装态旅程`Native confirmation exceeded the original exit budget`与`document_cloud_loop`合成worker 5秒超时，均**同SHA重跑后通过**，不是一次通过。安装态真实评分旅程、真实用户数据、托管发布、OpenMAIC多场景课程与真实模型生成、DISPATCHED残留对账策略及Owner接受仍分别未证，不以本页或CI合并代替。本轮实际推送的是已审核公开源码与任务记录，ignored原件、运行数据与数据库仍只在本机`.project-local/`。核验日期/HEAD是时点快照，后继Agent须现场读Git与活动指针。

本轮历史及补充资料的来源定位见[归档对账记录](workspace/intake/20261101-project-archiving-reconciliation/README.md)。完整导出JSON只作仓库内local-only压缩保全，不导入业务知识库或聊天管理系统，不自动上传。
