# 当前 Agent 接手入口

> 2026-10-19 关键对话已另存[39项主题来源与决定路由](../history/owner-dialogue-20261019/README.md)。包含工具迁移与中文说明的精确回执入口；提问、决定、历史声明和工程推导分列。现行决定/进度仍按下方固定读序，不以快照推导实时资格。

当前状态 **RUNNING_BY_OWNER / PARTIAL**。本文件只提供接续导航，不复制另一套权威、任务或资源配置。

## 固定读序

1. 根 `AUTHORITY.md`、`AGENTS.md` → [活动指针](AAOS-ACTIVE-EXECUTION.json)的 `continuation_context`。
2. [当前对话决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)，尤其第九节：强底座、内置能力市场、模型分层及替代关系。
3. [唯一执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)，从最新日期向前核对；TaskPack保存规划原文，不能替代实际进度。
4. 按任务读取下表相关入口，现场核对Git、文件、manifest、版本、进程与证据所属源码。

## 决定与路径导航

| 内容 | 规范入口及边界 |
| --- | --- |
| 来源、原件、旧任务包 | [根资料索引](../../AAOS-资料索引.md)、[资料总收敛](AAOS-PROJECT-CLOSURE-20261018.md)；原字节按登记保全，不从旧路径推导丢失 |
| 文件角色、旧路径替代 | [路径身份路由](AAOS-AUTHORITY-ROUTES.json)、[文档权威索引](../DOCUMENTATION_AUTHORITY_INDEX.md) |
| 外置工具、模型、测试资料库 | [共享资源路径索引](../SHARED_RESOURCE_PATH_INDEX.md)；具体声明读 `config/environment/capability-requirements.yaml`，观察读 `config/environment/external-resources-index.json`；先查登记再问路径 |
| Codex／Claude／Cowork来源 | [会话对账](AAOS-SESSION-RECONCILIATION-20261018.md)、[Codex索引](AAOS-CODEX-SESSION-INDEX-20261018.md)；完整Cowork逐字正文UNVERIFIED，不扫描无关私人会话 |
| 本地模型与旧运行时 | [本地LLM入口](AAOS-LOCAL-LLM-20261018.md)、[迁移归档](../history/runtime-migration-20261018/README.md)；LM Studio为当前通道，无Ollama自动回退，权重库只读；库存、加载、推理与质量分验 |
| 小栖／ASTRYN | [整合决定](../../workspace/intake/20261018-xiaoqi-in-project.md)、[迁移现状](AAOS-XIAOQI-MIGRATION-20261018.md)；在AAOS适配，复用Core会话／模型／记忆，源仓库仍NOT_READY_TO_DELETE |
| 开源吸收与扩展 | [决定及任务映射](AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[图谱供体](AAOS-OSS-UI-DONORS-20261019.md)、[OpenMAIC](AAOS-OPENMAIC-ABSORPTION-20261019.md)；择优复用、合法自研、明确降级，复杂能力保留未来规划 |
| 测试覆盖和诊断 | [逐轮范围与差距](AAOS-AUDIT-TEST-COVERAGE-20261018.md)；测试数量不等于商业验收，工程诊断集中既有入口 |

## 最新验证快照（2026-10-19，桌面标题与取消边界后继）

[当前限定回执](receipts/AAOS-REVIEW-CANCELLATION-20261019.json)、[本轮源码/红绿回归/失败/截图/只读评审快照](../history/oss-absorption-evidence/20261019-review-cancellation/README.md)。桌面标题换行、小栖status/cancel严格两字段身份、材料取消ACK身份及布尔值校验已应用。176文件1747项前端、10项Rust API、最终86项Python＋145 subtests、Core/TypeScript/Vite/Tauri限定PASS；各自源码资格分别保留。浏览器1280/640长标题已不溢出，3图实看；对比度仍一项incomplete。

两次本轮原生旅程整体FAIL，取消均未发出：第一轮切页草稿确认阻断，第二轮打开文档确认阻断。两轮的标题投影、实际27B材料/陪伴、同进程恢复、冷重开、备份恢复后读回阶段PASS；14图实看，自有进程/端口退出。最后已补文档选择受信确认并完成86项回归，**最终探针原生NOT_EXECUTED**。不得从上述阶段PASS推导取消、服务端停止、安装或产品整体通过。

## 接续执行

- 首先按当前探针源码重建/核对自有候选绑定，再运行既有grouped material/companion＋cancel旅程。当前候选见本轮candidate-build；它已包含产品修复，但其全局patch先于最终探针文档确认修正。使用唯一新run-id，不重用旧执行目录，不覆盖旧失败。
- 小栖一般复习建议仍被回答为“上下文无信息”。只读复核已核实日常companion复用严格材料grounding模板的策略错配；最小版本化策略、旧plan兼容/重放与定向验收见本轮READONLY-REVIEW，尚未实施。completed不是质量合格。
- 工程字段密度/学习项目键直露、导航语义及页签遮挡、手工对比度仍待处理；保留现有大地图、内缩结构、人物窗口与渲染器。
- BE10仍缺独立Observer准入、有限版本化只读端口及实际adapter消费者；不得共用human token或以schema占位宣称互通。
- HUB-003/004能力manifest与安装更新生命周期、统一模型底座合同及原队列按[决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)和唯一执行记录推进；V01、FT01–04与六项对话增量沿现有冻结边界。模型实例按现行profile现场读回，不从加载回执推导性能或永久常驻。

## 保全与交接

本轮旧handoff按原字节保存于[本轮快照](../history/oss-absorption-evidence/20261019-review-cancellation/handoff-before-update.md)，MANIFEST记录SHA-256。此前[71成员标题快照](../history/oss-absorption-evidence/20261019-review-title/README.md)、[旧提案接续快照](../history/oss-absorption-evidence/20261019-continuation-checkpoint/README.md)及[前序原生限定资格](../history/oss-absorption-evidence/20261019-material-companion-qualified/README.md)保留各自时间、源码和未验项，不回写成当前结果。

新决定维护决定正文及替代关系，实际状态只写唯一UI执行记录，当前入口只路由规范源。共享根引用原索引，路径移动/退役保留原身份及替代路径；先查登记与manifest，再核实现场，不重新猜路径或扫描私人会话。

保存未知dirty修改、Green、真实数据、共享模型及未完成迁移的源仓库；本轮未提交、推送、云端备份或发布。本地归档不等于完整Cowork逐字正文、所有平台资格或产品完成。接手先读本文件顶部固定读序，再按各回执和现场核对。
