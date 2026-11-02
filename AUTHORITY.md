# 项目总纲与权威总入口 — AUTHORITY.md

> **先读这里，再沿表中唯一规范接续。** README、Agent规则与交接入口统一回到本页；定位、闭环、任务和来源不能从旧摘要重新猜测。本页集中导航，不建立第二份定义或实时进度。

**Owner最新确认：以本总入口、[近两日13组对话与任务包总对照](docs/history/owner-dialogue-20261101-current-goals/README.md)、产品身份V2.3与唯一闭环V3为最新基准；其他资料均为历史和补充材料。** [PROJECT_CURRENT.md](PROJECT_CURRENT.md)只作薄导航并指回这里。[统一归档对账](workspace/intake/20261101-project-archiving-reconciliation/README.md)承接只读来源核对与SUP-032治理，不替代所选基准，不从旧包重新选择项目目标。

最新执行后继为[两平台接入与全部未完任务交接](workspace/intake/20261101-learning-platform-integration/README.md)（SUP-033）：DeepTutor1.7.1/OpenMAIC1.3.0原件已归档，适用能力接入沿既有CL/J/X和Core单写者实施；尚未建立产品接入资格。此执行选择不改产品定位和唯一闭环，也不替换上列最新来源入口。

## 0. 当前定位、定义与最近决定

| 要确认什么 | 现行内容与唯一落点 |
| --- | --- |
| 项目是什么 | **本地优先的个人知识、研究与Human–AI双向学习工作台**。通用知识底座与人机双向学习两核心保留；正式定位读[产品身份V2.3](docs/truth/PRODUCT_IDENTITY_V2.md)，名称读[命名合同](docs/truth/NAMING_CONTRACT_V2.md)。 |
| 人类侧做什么 | 资料收集、阅读整理、多源比较、知识修订、学习表达、外部实践记录、反馈与复习；沿[唯一闭环V3](docs/truth/CLOSED_LOOP_DEFINITION.md)验收。 |
| AI侧做什么 | **任何领域AI工作中可转化的内容、成果、问题、失败、方法、工作流、规范及更新，都可提炼为知识**，经治理、授权使用、反馈纠正、版本更新和独立复测；不限编程。原始会话归来源系统，会话助手是交互入口。见[产品身份](docs/truth/PRODUCT_IDENTITY_V2.md)及[SUP-031来源](workspace/intake/20261101-ai-knowledge-conversion/README.md)。 |
| “完整闭环”是什么 | 只认[最快最短完整闭环定义V3](docs/truth/CLOSED_LOOP_DEFINITION.md)：人类链、AI知识链、两侧授权连接及重启/导出/恢复。CL-01—07、J1—6及新包X1—X8保持原身份；目标不代表全部已实现。 |
| 专业工具与未来能力 | R6专业制作/计算/实验在外部，AAOS承接目标、教程、计划、记录、可选成果和反馈；L0人工回流可独立成立。具名长期能力仍读[能力图谱](docs/truth/CAPABILITY_ATLAS_V2.yaml)，不借范围纠偏删除既有required。 |
| 最近任务包如何生效 | Owner选择v3/R6目标为SUP-030；随后用SUP-031纠正AI侧含义。见[目标选择与原包绑定](workspace/intake/20261101-positioning-loop-update/README.md)、[Owner决定第二十五/二十六节](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[替代账本](DECISION_SUPERSESSION_LEDGER.yaml)。包内自称“权威/执行”的文字不单独授权；Owner后继选择才决定吸收范围。 |
| 最近对话和所有包在哪里 | **[近两日对话决定与任务包总对照](docs/history/owner-dialogue-20261101-current-goals/README.md)**集中保存可见原话摘录、R2→R5→R6、v3→v3.1→日志补件及本地ZCODE来源；不再逐个猜目录。 |
| 软件规则、内容规则与事实有什么区别 | 执行边界读[AGENTS.md](AGENTS.md)，普通保存/来源用途读[项目合同content_policy](PROJECT_CONTRACT.yaml)。软件规范的权威不代表资料陈述具有唯一事实权威。 |
| 当前做什么、做到哪里 | 范围/顺序/暂停/权限只读[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)；实际结果与未完成项只读其`active_progress`指向的[唯一执行记录](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)，接续读[当前交接](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)。历史“只审计”、PASS或旧暂停不冒充后继状态。 |

**更新约定**：新的Owner定位或定义决定，须同步相应唯一规范、本页入口、活动指针、决定/替代关系与来源映射；不只追加一份交接摘要。接手与讨论项目方向时先读本节及所指规范，再按需查看包内原文。原包不改字节、不重复展开，历史证据不改签。

以下为继承来源和详细导航；与现行规范冲突的旧解释按SUP-030/031及后继明确决定解析。

本文件是仓库的**导航入口**，不是新的真值来源。它只回答"该读哪个文件"，每一项都指向本仓已存在的规范文件。
旧路径与文件身份按[项目路由登记](docs/current/AAOS-AUTHORITY-ROUTES.json)解析，不从文件名或旧状态猜权威。
用户所称闭环的唯一规范是 [最快最短完整闭环定义](docs/truth/CLOSED_LOOP_DEFINITION.md)（`AAOS-SHORTEST-COMPLETE-LOOP-V3`）；旧阶段对最短闭环的较窄解释按该定义及替代账本解析，实际进度仍由活动指针导航。
现行定位与闭环按[Owner选择新任务包](workspace/intake/20261101-positioning-loop-update/README.md)及`SUP-030`，AI侧按[任意领域工作经验转知识澄清](workspace/intake/20261101-ai-knowledge-conversion/README.md)及`SUP-031`；定位读[产品身份V2.3](docs/truth/PRODUCT_IDENTITY_V2.md)，目标读同路径唯一闭环V3。旧包和旧阶段状态不能覆盖当前选择；实际实施仍由活动指针与唯一执行记录判定。

来源用途按[2026-10-26 Owner 澄清](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md#二十四多源检索辅助纠错与成熟方案优先2026-10-26)、[产品身份](docs/truth/PRODUCT_IDENTITY_V2.md)及[合同 content_policy](PROJECT_CONTRACT.yaml)解释；替代关系为 `SUP-029`。这里的配置／执行“权威”用于解决软件规则冲突，不赋予资料内容唯一事实权威。来源记录服务回查、识别纠错与多源搜索比对，普通保存和学习沿内容规范正常进行。
换 Agent／换会话先读[活动指针的 continuation_context](docs/current/AAOS-ACTIVE-EXECUTION.json)，再读[当前对话决定及替代关系](docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[接手入口](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)和唯一执行记录。权威、规划、会话来源及外置共用库按该指针导航，先读回登记再核实现场；不从旧摘要或私人记忆猜路径。
此前两处记录写"根目录 `AUTHORITY.md` 缺失（`AUTHORITY_REFERENCE_MISSING`）"（`docs/history/repository-consolidation-20261019/current/AAOS-UI-COVERAGE-MATRIX-20261001.md`、
`docs/history/repository-consolidation-20261019/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md`）；这两处是当时的实测，保留不改写；本文件使该引用可解析。

## 1. 继承的两核心来源（不替代现行产品身份与闭环）

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
**不拥有**：融合后的独立AI-WORK-LAB（AIWORKLAB），及WORK-LAB／DESIGN-LAB历史和迁移来源；AAOS不与其合仓或共享业务DB。共享工具链与 Model library（仅获准引用）；其他项目的运行状态；
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

当前交接见 [`docs/current/AAOS-AGENT-HANDOFF-CURRENT.md`](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)；当前本地／云端接线、剩余资格与未发布边界，沿[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)的 `current_execution.checkpoint` 和[唯一执行记录末段](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)核对。[10/09治理对齐记录](docs/history/repository-consolidation-20261019/current/AAOS-GOVERNANCE-ALIGNMENT-20261009.md)仅保留为历史来源。

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
