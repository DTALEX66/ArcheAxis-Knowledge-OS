# 当前 Agent 接手入口

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

## 最新验证快照（2026-10-19）

[原生限定回执](receipts/AAOS-MATERIAL-COMPANION-QUALIFIED-20261019.json)和[12成员证据快照](../history/oss-absorption-evidence/20261019-material-companion-qualified/README.md)：截止预算修复已编入自有隔离候选；Core／TypeScript／Vite／Tauri构建及真实UI→Core→LM Studio 27B材料／陪伴执行、同进程恢复、冷重开、备份恢复后原回执读回PASS。构建与原生绑定patch `bf27efc04415d6de00714147225e410327042adebd9bfe8311316528507e30c8`，不代表当前全部dirty文件资格。7图已实看，拥有进程／端口已退出，八旧组件ZIP保全。

挂接后观察窗口无新增执行调用；启动调用数UNVERIFIED，原生取消NOT_EXECUTED。材料单次88秒不是性能基准，陪伴未给实用建议，不能据completed声称质量合格。全格式、安装、真实用户学习效果和Owner验收未关闭。

前序[超时失败](../history/oss-absorption-evidence/20261019-material-companion-final/README.md)、[历史恢复](../history/oss-absorption-evidence/20261019-material-companion-recovery/README.md)、[最终源码修复及回归](../history/oss-absorption-evidence/20261019-machine-deadline/README.md)保留各自源码资格，不能把旧失败冒充最新状态，也不能抹去失败。

## 接续执行

- 复习长键标题：前序[未应用提案快照](../history/oss-absorption-evidence/20261019-continuation-checkpoint/README.md)保留历史身份；后继已应用并修复课程绑定校验和主壳选择回传的重复读取。见[新限定回执](receipts/AAOS-REVIEW-TITLE-20261019.json)及[71成员快照](../history/oss-absorption-evidence/20261019-review-title/README.md)。176文件1741项前端、14项Rust、80项Python＋145 subtests及TypeScript/Vite通过，各有源码绑定；浏览器合成Core三项功能通过，3图实看，但1280桌面极长标题仍裁切，axe对比度一项incomplete。**本切片PARTIAL**：下一步先补桌面换行并同时测1280/640，之后构建自有候选重验原生；旧原生候选不含本次改动。
- 原生取消、材料／小栖质量、工程信息密度与导航语义仍需验证／修复。
- BE10仍缺独立Observer准入、有限版本化只读端口及实际adapter消费者；只读评审见[快照](../history/oss-absorption-evidence/20261019-material-companion-qualified/READONLY-REVIEW.md)。不得共享human token充当Observer或用schema占位冒称互通。
- HUB-003／004能力manifest与安装更新生命周期、统一模型底座合同及原队列按[决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)和唯一执行记录推进；V01、FT01–04与六项对话增量沿现有冻结边界。

## 保全与交接

本轮完整旧handoff已按原字节保存到[历史快照](../history/oss-absorption-evidence/20261019-continuation-checkpoint/handoff-before-consolidation.md)，MANIFEST记录SHA-256。历史段落的“最新”仅适用于当时，不覆盖上述回执。新决定同步决定正文、受影响路由与唯一进度；共享根只引用原索引，移动／退役路径保留身份和替代入口。归档检查见[读回回执](receipts/AAOS-CONTINUATION-CHECKPOINT-20261019.json)。

后继标题切片与对话导航归档的[当前读回](receipts/AAOS-REVIEW-TITLE-ARCHIVE-READBACK-20261019.json)核验71个快照成员、24个未再变化源码、26个当前导航目标和9类决定覆盖；[检查原始结果](receipts/AAOS-REVIEW-TITLE-ARCHIVE-CHECKS-20261019.json)保存文档门禁、diff检查及自有进程/41730监听退出。这里只证明限定检查，不提升产品或安装资格。

保存未知dirty修改、Green、真实数据、共享模型与源仓库；不因PASS获得新权限。本轮未提交、推送、云端备份或发布；本地归档不等于全部私人客户端全文齐备。最终事实以现场及各自限定证据为准。
