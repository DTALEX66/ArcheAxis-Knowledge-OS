> **2026-10-23 最新范围纠正：人类与AI双侧闭环继续／PARTIAL**：Owner最新明确“人类侧不冻结，还是按照闭环执行”，并进一步确认“闭环应该还要包括AI侧”。当前范围为人类知识／学习链＋AI知识／学习链＋两侧按权限共享知识与证据的双向连接。AI专项未改人类侧是历史实施事实，不是后续冻结禁令；原始跨项目会话仍归外部系统，未来扩展与暂停监控不因此恢复。 以[决定二十二](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md#二十二人类与ai双侧闭环继续交接时的最新范围2026-10-23)、[唯一闭环定义](docs/truth/CLOSED_LOOP_DEFINITION.md)及[完整换会话交接](docs/history/owner-dialogue-20261023-thread-handoff/README.md)为接续入口。下方AI专项“只改AI”和旧暂停／权限阻塞段按其历史时点理解，不能再次限定整个项目只做人类侧或只做AI适配接口。本次仅完成交接归档，未启动后继产品执行。

> **2026-10-23 AI 侧定向职责纠偏**：本轮仅执行外部上下文／知识候选边界；跨项目与跨 Agent 原始上下文归独立外部系统，AAOS 保留受治理 AI 知识与有限问答上下文，人类学习侧不变。候选接收与隔离测试已落地，真实外部状态 NOT_CONNECTED；不启动其他开发／安装／付费调用。规范：[AI 边界](docs/current/AAOS-AI-CONTEXT-BOUNDARY-20261023.md)，实际进度仍读原唯一执行记录。

> **2026-10-23 当前权限已恢复／目标仍未完成**：Owner将本会话切换为完全访问并要求解决阻塞后，项目canonical Python 3.13.14及Python子进程启动PASS；正式Git临时引用创建、读回、删除PASS，原分支、HEAD和暂存区不变。此前直接操作.git临时文件的探针命令在执行前被策略拒绝，该拒绝保留，但不能据此继续断言Git只读。当前为PERMISSIONS_RECOVERED／PARTIAL；下方权限阻塞段为历史。正式构建、同候选闭环、真实云端、原生安装与交付尚未由本次权限检查验证；监控仍暂停，未新增功能、改ACL、提交或上传。证据见[恢复检查点](docs/history/project-drift-audit-20261021/execution-permission-recovery-20261023.json)。

> **2026-10-23 当前权限阻塞**：目标未完成，状态BLOCKED_EXECUTION_PERMISSIONS／PARTIAL；Owner执行授权保留，非Owner暂停。canonical Python -V仍被uv子进程os error5拒绝，当前.git只读；前三个连续目标回合均受相同限制。当前云模型生产执行亦未激活，不能把Vault／协议模拟当真实云闭环。当前恢复入口与未完成清单见[完整交接](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)，证据见[检查点](docs/history/project-drift-audit-20261021/cloud-execution-blocker-20261023.json)。监控保持暂停，不绕过权限或借用Codex凭据。

# AUTHORITY.md — 根入口

> **2026-10-22 最新恢复**：Owner后继要求“根据新的规划和闭环开始执行”。当前 `RUNNING_BY_OWNER / PARTIAL`，按决定十九／二十节继续首版闭环与Stitch实施；下文暂停和只读核查为之前时点，最新进度见原唯一执行记录。监控仍暂停，可选扩展不激活。

> **2026-10-22 当前接续**：[决定十九／二十节](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md#十九首个可用版本核心收敛与能力启动台2026-10-22)记录首版收敛、现有Stitch内能力启动台及玻璃／标准图标纠偏，[统一归档](docs/history/owner-dialogue-20261022-desktop-launcher/README.md)保存来源、概念图与设计核查。当前仅归档及定向设计核查，产品仍 `PAUSED_BY_OWNER / PARTIAL`，监控暂停；下方10/11的RUNNING是历史时点。

> 本地/云端仓库身份、分支保留及换会话接续：[接续记录](docs/history/repository-consolidation-20261019/current/AAOS-REPOSITORY-CONTINUITY-20261012.md)。路径和 SHA 是可核对的观察，不是永久环境或新权限。

> **2026-10-11 当前路由与状态**：Owner 已明确恢复完整框架、常见常用格式与最短闭环产品实施；状态 RUNNING_BY_OWNER / PARTIAL。当前范围与恢复决定读[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)，实际进度仍在该指针指定的 UI 执行记录。2026-10-10 暂停仅为历史时点，旧 COMPLETE、FAIL 和证据保留各自 SHA。六项核心能力对话增量仍 FROZEN_BY_OWNER；V01 暂停、FT01–04 冻结；公开发布和真实用户数据覆盖未授权；Green程序精确目录更新已由Owner后继授权，范围读活动指针green_update_authorization。 文件身份与旧路径按[路由登记](docs/current/AAOS-AUTHORITY-ROUTES.json)核对。

本文件是仓库的**导航入口**，不是新的真值来源。它只回答"该读哪个文件"，每一项都指向本仓已存在的规范文件。
用户所称闭环的唯一规范是 [最快最短完整闭环定义](docs/truth/CLOSED_LOOP_DEFINITION.md)（`AAOS-SHORTEST-COMPLETE-LOOP-V2`）；旧阶段对最短闭环的较窄解释按该定义及替代账本解析，实际进度仍由活动指针导航。
换 Agent／换会话先读[活动指针的 continuation_context](docs/current/AAOS-ACTIVE-EXECUTION.json)，再读[当前对话决定及替代关系](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[接手入口](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)和唯一执行记录。权威、规划、会话来源及外置共用库按该指针导航，先读回登记再核实现场；不从旧摘要或私人记忆猜路径。
此前两处记录写"根目录 `AUTHORITY.md` 缺失（`AUTHORITY_REFERENCE_MISSING`）"（`docs/history/repository-consolidation-20261019/current/AAOS-UI-COVERAGE-MATRIX-20261001.md`、
`docs/history/repository-consolidation-20261019/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md`）；这两处是当时的实测，保留不改写；本文件使该引用可解析。

## 1. 母定义（沿用输入文档原文，不转述）

> AAOS 是一个本地优先的个人知识与 Human–AI 双向学习系统。它统一承载多格式资料、个人知识、研究、人的学习过程和 AI 学习资产；
> 内容可以先保存、阅读、编辑和使用，再按内容类型、使用场景及用户选择进行识别核验、专业依据分析、修订与治理。
>
> 历史中的 Universal Knowledge Foundation 与 Human–AI Co-Learning 两个永久核心继续保留。……它们不是"所有世界知识已经掌握"
> 或"已经训练出自己的基础模型"的声明。

来源：输入蓝图《AAOS 完整项目描述与未来蓝图》2026-10-06，§2。<br>
输入字节 SHA-256 `2c99e7ae7dd52298ee425c8360c90b63a40d02f41af4c1b151cad6efd55d1ed9`（已核，与提示词要求一致）。<br>
名称：内部代号 AAOS；对外"星环知识系统 ArcheAxis Knowledge"；仓库身份 `DTALEX66/ArcheAxis-Knowledge-OS`；展示状态保留 Ongoing。

## 2. 本仓库拥有 / 不拥有

**拥有**：本仓的代码、文档、决策记录与证据；根 `AGENTS.md` 定义的执行边界内的写入。
**不拥有**：WORK-LAB 与 DESIGN-LAB 两仓（不合仓、不共享业务 DB）；共享工具链与 Model library（仅获准引用）；其他项目的运行状态；
以及 Hermes / Codex / CC Switch / workflow-assistance / session / cron / Kanban 等工作流基础设施——名字提到本项目不构成归属。

## 3. 当前能力的证据范围（状态分级，不混写）

区分：仅目标 / 候选 / 结构实现 / 受控测试 / 真实运行 / 独立验收 / 发布。**测试数量、页面数量、单条纵向切片都不能定义项目本体。**
以下是继承的 2026-10-05 审计时点声明（不是当前源码资格），至少包括：Q04"完成"声明已撤销；音视频已实测仅媒体头信息探测，未证明解码/转写/时间段内容闭环；
引擎断言无有效结论（存在 cancelled/skipped 与桌面 failure）；更正记录中 Q14 为 NOT_RUN，且未做人工视觉确认。
逐条原文与来源：[`docs/history/repository-consolidation-20261019/current/AAOS01-AUDIT-CORRECTIONS-20261005.md`](docs/history/repository-consolidation-20261019/current/AAOS01-AUDIT-CORRECTIONS-20261005.md)
（字节 SHA-256 `da9998ee673086ed12dab824d951e76c2611efb92e72edccf276b91ed8d92d4d`，已核）。

## 4. 未来能力入口

长期能力编号 CAP-0010—CAP-0160（16 项）、第一包 Q00—Q15、未来扩展 F00—F14 与互通平台 I1—I6 的逐项落点与证据见本轮覆盖矩阵
（`docs/current/AAOS-COVERAGE-MATRIX-20261006.md`）。未来能力不得写成已支持；平台名单不整体进 README 的"已支持"列表。

## 5. 规范 Authority 顺序

系统与开发者规则 ＞ 用户当前明确指令 ＞ 根 [`AGENTS.md`](AGENTS.md) ＞ [`docs/truth/`](docs/truth/README.md) 已批准稳定真相 ＞ 冻结任务基线 ＞
历史 TaskPack / 蓝图 / handoff / 导入设计资料。实现证据说明"做到哪里"，不能反过来取消用户已明确的未来目标。
机器可读索引：[`docs/DOCUMENTATION_AUTHORITY_INDEX.md`](docs/DOCUMENTATION_AUTHORITY_INDEX.md)、[`docs/CONFIGURATION_AUTHORITY_INDEX.md`](docs/CONFIGURATION_AUTHORITY_INDEX.md)、
[`PROJECT_CONTRACT.yaml`](PROJECT_CONTRACT.yaml)。

## 6. 唯一 current（一个仓库不能有两个都自称 current 的源）

- **当前活动任务包**：`docs/taskpacks/aaos-ui-first-20261009/`（AAOS-UI-FIRST-PLAN-20261009），由用户当前执行/G01请求选中；规范路由为 [`docs/current/AAOS-ACTIVE-EXECUTION.json`](docs/current/AAOS-ACTIVE-EXECUTION.json)。
- **当前 UI 实施进度**：[`docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。任务包中的 NOT_EXECUTED 是规划时快照，不回填该原包。
- **继承合同来源**：`docs/authority/taskpack-1004-aaos01/`（`01_完整执行任务书.md`），保留内容保存、身份与原 Q/F 验收条款，不作为并行当前队列。
- **前一个任务包（保留继承约束与回执，不再作为当前）**：R6 absorb-first（`docs/authority/taskpack-0919-r6/`），其优先级覆盖 [`M0`](docs/history/repository-consolidation-20261019/current/M0-DIRECTION-OVERRIDE-20260920.md) 仍作为继承约束保留。
- **继承 AAOS-01（仅 Q00—Q15）的进度记录**：[`docs/history/repository-consolidation-20261019/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`](docs/history/repository-consolidation-20261019/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)。
- **正式宿主**：Tauri 2 + React/TypeScript/Vite + Rust Core 单写者（[`DECISION_SUPERSESSION_LEDGER.yaml`](DECISION_SUPERSESSION_LEDGER.yaml) SUP-021 → SUP-022）；Avalonia 为供体并冻结。
- `docs/taskpacks/README.md` 曾自称"唯一当前任务包"，已作废该表述并指向上述入口。

> 2026-10-06 的 AAOS-01 接手纠错属于该阶段历史。10/09 用户选中 UI 优先队列和 G01；旧 R6/M0/AAOS-01 整包顺序冻结，有效约束继承。V01 仍暂停，FT01–04 保留未来意图。新布局适用于所有主题；当时的 blueprint 默认已由后续 UI 方向覆盖，现行主题策略读活动指针 theme_policy，同一主题全局一致。

当前交接见 [`docs/current/AAOS-AGENT-HANDOFF-CURRENT.md`](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)，本地/云端漂移与未发布范围见 [`docs/history/repository-consolidation-20261019/current/AAOS-GOVERNANCE-ALIGNMENT-20261009.md`](docs/history/repository-consolidation-20261019/current/AAOS-GOVERNANCE-ALIGNMENT-20261009.md)。

## 7. 审计索引（可导航链：根入口 → 有效规则 → 来源 → 能力/任务 → 代码或证据 → 两端读回）

| 角色 | 规范位置 |
| --- | --- |
| 文件职责与唯一规范源 | [`docs/DOCUMENTATION_AUTHORITY_INDEX.md`](docs/DOCUMENTATION_AUTHORITY_INDEX.md) |
| 冲突 / 更正 / 替代 crosswalk | [`DECISION_SUPERSESSION_LEDGER.yaml`](DECISION_SUPERSESSION_LEDGER.yaml) |
| 覆盖矩阵（CAP / Q / F / I） | `docs/current/AAOS-COVERAGE-MATRIX-20261006.md` |
| 输入来源与哈希（含 SOURCE_MISSING） | `docs/current/AAOS-INPUT-SOURCES-20261006.json` |
| 本轮审计快照（observed_at / SHA / 命令 / 退出码） | `docs/history/repository-consolidation-20261019/current/AAOS-AUDIT-SNAPSHOT-20261006.json` |
| 供应链吸收决策账本 | [`docs/truth/SUPPLY_CHAIN_LEDGER.json`](docs/truth/SUPPLY_CHAIN_LEDGER.json) |
| 文档/治理自动核验 | `scripts/ci/check_document_authority.py`（接入 CI） |

## 8. 本文件的边界

本文件不含自引用哈希，不复制上游真值，也不改变任何既有决定。发现本文件与上表规范文件冲突时，以上表规范文件为准并修正本文件。
