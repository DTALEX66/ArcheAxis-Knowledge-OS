# ArcheAxis Workspace 最终总蓝图与 Codex 主任务包 v4.0

> 中文产品名：元枢工作台
> 英文产品名：ArcheAxis Workspace
> 简称：ArcheAxis
> 文档日期：2026-08-09
> 文档性质：Truth Reset 合并前的迁移决策源、完整能力图谱、长期蓝图、命名合同与 Codex 唯一执行入口
> 适用仓库：`DTALEX66/Cognitive-Loop-OS`（历史仓库名，产品名不沿用）
> 执行主体：Codex
> 状态：待作为 Truth Reset PR 的输入；本文本身不宣称代码已实现。AXW-001A、AXW-004A/004C 合并后，由仓库 `docs/truth/**` 接管规范权威，本文转为 frozen evidence/historical
> 覆盖关系：本 v4 完整吸收并取代 v3 主包与同日 OSS/Windows/LER 增量包；旧文件保留历史，不再单独产生执行权

---

## 0. 最终裁决

本项目已经不是早期抽象的“认知闭环 OS”，也不是通用 Agent Runtime、WORK-LAB 子系统或工程门禁演示平台。但它也不能被再次缩窄为单纯的文件管理器、PDF 阅读器或 Obsidian 克隆。

项目的唯一产品定义是：

> **ArcheAxis Workspace 是一套面向个人与其 AI 的、本地优先、证据驱动的学习与知识系统。它把开放格式资料，以及来自官方网站、百科、社区/论坛、学术期刊等多类来源的信息，经来源记录、对照分析、交叉验证、矛盾处理和置信评估，形成可追溯证据；同一证据基底同时服务人类深度高效学习与 AI 精准学习，生成可互相转换的人类学习资产，以及 AI 可检索的记忆、规则、技能、规范和受控调用能力，从而让同一份资料“人学得更深，AI 用得更准”。**

简明口号：

> **同一份开放格式资料，人学得更深，AI 用得更准。**

唯一主链是：

```text
真实资料/现有 Vault/多源信息
→ 原件安全保存
→ 可解释转换与损失报告
→ Claim 提取、来源锚点、对比和交叉验证
→ EvidenceBundle 与可审阅知识
→ 中央工作区阅读、编辑、搜索、链接、Canvas
→ 人类：理解→练习→复习→掌握→Teach Back
→ AI：记忆候选→规则/技能/规范→受控调用→结果纠正
→ 人类学习资产 ⇄ AI 学习资产
→ 重启读回、开放导出、跨应用往返、冲突恢复
```

这份 v4 总包覆盖并裁决此前的对话、蓝图、审计、开源调研和任务包。它不再用“延期”把能力从蓝图中省略，而是把所有内容归入五类并永久保留映射：

1. 当前绑定决策；
2. 可复用工程资产；
3. 正式未来能力；
4. 仅作研究证据或候选上游的历史材料；
5. 被推翻的定位/命名/执行权与仍保留但尚未激活的远期能力。

本包的基本纪律是：**deferred 不等于 deleted，未激活不等于没有规划，候选未选择不等于从上游账本消失。** 通用 Agent、同步协作、浏览器扩展、PWA/Mobile、Visual Teaching、动画、模拟、2.5D/3D/VR/AR 等可以不进入当前 Release 关键路径，但必须在 Capability Atlas、Horizon、Program 和上游候选中有稳定位置。只有用户明确决策或有可审计的 `superseded_by/rejected_reason`，才能移出未来蓝图。

### 0.1 四层闭环必须分开

| 层级 | 当前定义 | 退出证据 |
|---|---|---|
| 生存闭环 | v0.5.1 安装版能处理真实 PDF | 真 PDF 导入、转换、打开、失败可解释、重启读回 |
| 开放资料闭环 | PDF/Office + Obsidian C4 第一高保真纵切 | 原件/MD/附件/Canvas 可读写引用、往返和冲突恢复 |
| 产品差异化最小闭环 | v1.0 Evidence + Human Learning + AI Learning 双环 | 多源交叉验证→证据→人类掌握/Teach Back→AI 记忆/规则/技能→互转与纠错 |
| 长期全面吸收 | v1.x 起逐个适配相关知识/学习软件 | 每个 Adapter 独立许可、loss、roundtrip、installed evidence |

先修 PDF 不是放弃 Obsidian 主线；Obsidian C4 也不是把产品定位缩成 PKM 克隆。二者是双学习系统赖以成立的开放资料与日常工作面。所谓“全面兼容吸收”不是在一个版本同时克隆所有软件，而是建立稳定适配器架构，再逐项交付高保真纵切。

### 0.2 本轮最高优先级决策

- 产品核心固定为 Evidence-grounded Human–AI bidirectional Learning & Knowledge Workspace；文件/Obsidian 是开放资料面，不是最终定位。
- Source/Claim/AI 输出默认是 Candidate；只有经过来源锚定、对比交叉验证、矛盾/时效/范围评估和授权的内容才叫 Evidence/正式资产。
- OpenHuman 的中央宽主工作区、左右按需上下文、底部临时任务条和 Memory Tree 组织思想映射为 Topic Tree / Learning Map；中央承载文档、PDF、Office、Canvas，而不是 Agent 聊天。在顶层许可证组合尚未裁决前采用 clean-room；完成兼容性、对应源码和分发义务决策后，GPL/AGPL 源码也允许依法吸收、修改或合并。
- 项目当前是个人所有、非商业、学习研究型项目；这使“最大化合法开源吸收”优先于保留未来闭源商业选择，但不构成任何许可证、NOTICE、源码、模型或资产义务豁免。
- Learning Experience & Representation Layer 是永久产品层：视图、表格、卡片、时间线、Learning Map、课件、动画、交互模拟及 2D/2.5D/3D/VR 记忆宫殿按 Horizon 分期，不能因当前未实现而从蓝图删除。
- 旧任务包中的“HERMES 唯一 writer、Codex 只读”全部失效。Codex 现在是唯一执行与交付责任主体；HERMES 只可作为历史上下文或可选审阅工具，不是前置依赖。

---

## 1. 证据范围、事实源优先级与使用方法

### 1.1 已整合的材料族

本总包吸收了以下材料中的有效结论：

- 当前可见的全部本项目对话和用户追加决策；
- 2026-08-09《ArcheAxis Workspace Future Master Blueprint v1.0》；
- 2026-08-09《v0.5 多格式知识工作区全量审计与修复任务包》；
- 2026-08-08《OS-only 产品/UI/命名/兼容路线总审计》；
- 2026-08-07《云端全量审计与整合执行任务包》；
- 2026-08-07 CI 提速与验证策略材料中的中立工程结论；
- 2026-08-06《全面兼容吸收最小面闭环主任务包》；
- 2026-07-31 完整对话归档；
- 369 项去重开源研究池、101 项仓库 registry/ledger、57 项开源能力精选表；
- 22 项 FullStack/WORKLAB 验真文档中与 OS 本身相关的开源和兼容结论；
- Obsidian-Assistance 历史包中的安全写入模式，仅作行为参考；
- OpenHuman、Obsidian、Zotero、Readwise、Anytype、Logseq、Joplin、SiYuan、AFFiNE、AppFlowy、Heptabase、Capacities、Tana、Roam、Notion、Anki、VS Code、Home Assistant、Langfuse/Phoenix 等产品/开源项目的界面与能力研究。

### 1.2 规范轴与事实轴

两条轴解决不同问题，禁止互相越权。

**规范轴——决定项目是什么、做什么：**

1. 用户当前明确指令；
2. Truth Reset 合并前：本 v4 总包；合并后：仓库 `docs/truth/PRODUCT_POSITIONING_V3` 及 Naming/Evidence/Authority contracts；
3. Future Master Blueprint v2；
4. Current Product Plan；
5. Atomic TaskPack/ADR。

**事实轴——决定能力是否真的实现：**

1. 安装版 exact-SHA 可复现用户行为与 artifact evidence；
2. 当前 `main` 可复现行为；
3. capability evidence registry；
4. Capability Matrix/README/UI projection。

当前 main 和安装版可以否定“已实现/已支持”的宣传，但不能用旧 README/代码名反向修改 Product Positioning。旧 SHA、PR 状态、分支数和 Release 结论不能直接复用；每个 Codex 任务开始时重新冻结事实轴。

**生命周期：** 本文只在 AXW-001A、AXW-004A/004C 合并前充当迁移决策源。仓库 truth 合并并验证 digest 后，本文件的 authority class 改为 frozen evidence/historical，`agent_discovery: deny`；后续不得与 `docs/truth/**` 并列形成双权威。

### 1.3 三种状态体系不得混用

产品兼容等级：

```text
C0 发现 → C1 读取 → C2 日常工作 → C3 安全写入 → C4 往返 → C5 生态桥接
```

开源吸收状态：

```text
discovered → researched → license-approved → selected
→ integrated → installed-verified → released
```

任务状态：

```text
planned → in-progress → code-complete → locally-verified
→ CI-verified → installed-verified → released
```

“registry 有记录”“模块可 import”“测试文件存在”“CI 通过”都不能等同于产品支持或 released。

---

## 2. 对话与蓝图演变：什么保留，什么被推翻

### 2.1 决策演变时间线

| 阶段 | 当时重点 | 当前裁决 |
|---|---|---|
| 早期 Cognitive Loop OS | Research→Knowledge→Learning→Runtime、Agent、治理 | 作为历史研究；不再支配产品路线 |
| 2026-07-31 | 369 项开源研究、四大工作区、转换可观测 | 保留研究池、用户化状态反馈、设置范围；旧导航和 v0.5 目标被后续方案覆盖 |
| 2026-08-06 | 全面兼容吸收、Obsidian 为第一高保真纵切 | 保留；旧 C0–C5 定义和 369 全量先登记计划被覆盖 |
| 2026-08-07 | 云端真相、CI/Release、源码复用优先 | 保留缺陷证据与选择性门禁；WORK-LAB 不进入产品边界 |
| 2026-08-08 | OS-only、UI/命名、中央知识工作台 | 保留；对外统一为 Workspace |
| 2026-08-09 | 安装版 PDF 失败、多格式总审计、未来蓝图 | 作为当前主路线基础 |
| 后续 OpenHuman 讨论 | 中央留白/宽工作区和 Memory Tree 很适合 | 加入 v2 UI；仅洁净实现布局与交互思想 |
| 当前执行决策 | 改用 Codex 执行 | 覆盖所有 HERMES-only 权限条款 |

### 2.2 冲突裁决表

| 冲突 | 胜出结论 | 被降级内容 |
|---|---|---|
| ArcheAxis OS vs ArcheAxis Workspace | 元枢工作台 / ArcheAxis Workspace | OS 仅暂作仓库历史标识 |
| 认知闭环/Runtime vs 用户真实知识工作 | 用户资料和开放知识资产 | Runtime/Receipt/Machine 退到内部 |
| Job 成功 vs 产品闭环 | 可读、可定位、可重启、可导出 | 任务回执不能冒充能力 |
| 先 Agent vs 先资料处理 | PDF/Office/Vault 先行 | 通用 Agent 延至 v2+ |
| 一次吸收所有软件 vs 分期 Adapter | 分期高保真适配 | 369 项不同时进入主线 |
| Dashboard vs 中央工作区 | OpenHuman 式中央工作面 | 治理仪表盘进高级抽屉 |
| AI 聊天/Agent 控制台 vs AI 学习资产 | AI Assets 是核心工作区；Cited AI 是上下文工具 | 禁止把产品缩成聊天或 Agent 控制台 |
| 旧 Obsidian C3 Alpha vs 新 C4 | 新 C0–C5 和 v1.0 C4 | 旧等级定义作废 |
| Registry=吸收 vs Release evidence | installed-verified/released 才能声明 | 清单数字不计能力 |
| WORK-LAB 相关产品规划 vs OS-only | WORK-LAB 与产品无关 | 只保留中立验证思想 |
| HERMES writer vs Codex | Codex 是唯一交付主体 | HERMES-only 全部作废 |

### 2.3 必须保留的历史资产

- FastAPI + SQLite + Tauri 的桌面底盘；
- Approved Roots、路径校验、迁移、备份和安全 HTTP 基础；
- Job/Outbox/Receipt 作为内部持久任务设施；
- 候选知识、人工复核、来源优先、模型输出不自动成事实；
- 后端承担转换/验证/重试，前端展示目标/结果/异常/需要用户决策；
- Reuse Decision Record、SBOM/NOTICE、exact upstream revision、升级与回滚；
- 无代码、无事实变化时不重复全仓审计；
- fixture→dry-run→backup→apply 的安全写入方法；
- 选择性 CI、安装版格式资格和 exact-SHA Release 证据。

### 2.4 必须归档或延期的污染项

- A–N、B/C/R、旧 HERMES TaskPack 和“认知闭环”阶段图；
- 通用 Agent Runtime、多 Agent、Agent marketplace、自治演化；
- 把 3D/VR 变成当前 Release 前置或独立品牌；3D/VR 本身保留在正式 LER 长期路线；
- 把 WORK-LAB、Obsidian-Assistance 的路径、运行时或 UI 合入本产品；
- 以 Runtime、Delivery、Audit、Machine、Evolution 为普通用户一级导航；
- 用首行 claim、Pillow 元数据、FFprobe 元数据、内部 Canvas SQLite 或静态字符串测试冒充产品能力。

### 2.5 本轮最新云端事实冻结

审计时间：2026-08-09 UTC。执行任何任务卡前仍须重新运行 AXW-000，下面只代表本文生成时的基线。

| 项目 | 冻结事实 |
|---|---|
| 云端仓库 | `DTALEX66/Cognitive-Loop-OS` |
| `main` | `492fac5982c693eb668d31cc51a6a59bac83b7a1` |
| `main` 提交 | `docs: clarify desktop release evidence boundary (#67)` |
| 源码版本 | `0.5.0`；source manifest 为 development/unreleased/public=false |
| 最新 main CI | run `31297924393`，成功；该 docs 变更只跑 gateplan + lint + a0-gates |
| 公开 Release | `v0.5.0`，source `fe977577da53dafa4528da908898995ba316b53a` |
| Release evidence | full CI `31276290892`；release workflow `31277061510`；4 个公开资产 |
| Release 与 main 差异 | main 已比 v0.5.0 多 11 commits，部分 Canvas/readiness 变更未发布 |

开放 PR：

| PR | 冻结状态 | 裁决 |
|---|---|---|
| #68 PDF dependencies | CI 失败；head `91f5f15`；ahead 3/behind 2 | 方向正确但 fixture/依赖/安装资格不足；基于最新 main 重做，不能只修绿 |
| #69 release console window | CI 成功；head `1100973` | 独立桌面修复，可正常审查，不与产品重构混包 |
| #70 verification summary/ledger | CI 成功；head `8cc9c69` | 含旧 B/C/R、硬编码本机路径和错误能力结论；不原样合并，只抽取事实 |

### 2.6 当前能力真相

| 能力 | 当前真实级别 | 主要缺口 |
|---|---|---|
| HTML/TXT/Markdown 基础 | 较可信的 source-level 路径 | 仍需 installed/restart/claim 边界 |
| 数字 PDF | code-integrated/unqualified | v0.5.0 wheel 无 PDF extra；旧/#68 fixture 不能证明正文；无页锚点 |
| Office | detected/declared | 无真实文档结构、wheel/installer 资格 |
| 图片 OCR | metadata-ready，不是 OCR-ready | 主路径先返回 Pillow 尺寸/颜色/EXIF；Tesseract binary/language pack 未随安装器 |
| 音视频 | metadata-ready | FFprobe codec/duration 不是 ASR/时间文本证据 |
| JSON Canvas | main 有基础文本/语义提取 | v0.5.0 未发布；无编辑、空间/未知字段往返 |
| Obsidian Vault | C0/C1 局部基础，约 3/10 | 无可用日常工作台、完整 YAML/附件、C3/C4 |
| Workspace UI | shell/browser smoke 可用 | 中央仍偏治理卡片，不是内容/学习工作区 |
| Candidate/Claim/Evidence 治理 | 可保留底座 | 当前 Evidence 命名未充分强制交叉验证；缺 Claim→EvidenceBundle 产品流 |
| Human Learning | contract/backend fragments | 无练习→掌握→复习→Teach Back 的产品证据 |
| AI Learning | runtime/memory fragments | 无 evidence-bound memory/rule/skill 准入→调用→纠错闭环 |
| 通用 Planner/Agent | 仅受限 `read file:` 等纵切/治理底座 | 非当前主线；不得以“完善 Planner”为下一刀 |
| Release 资产身份 | v0.5.0 较可靠 | 验证安装/启动/哈希，不证明真实 PDF/双学习能力；未来需 full profile 强绑定 |

### 2.7 当前 P0 工程阻断

1. **总门禁误绿：** GatePlan 使用 `py-primary`，aggregator 却检查 `test`；PR #68 核心测试失败而 `a0-gates` 成功。先修此漏洞，否则“门禁绿”不能当可信证据。
2. **依赖变化未触发安装资格：** `pyproject.toml` first-match 分类可能只跑 wheel，不跑 bundled Windows real-format smoke。
3. **上传顺序可能丢原件：** 现行 intake 先同步转换/写派生，最后才移动原件；转换失败时没有 RawAsset/失败记录/重试入口。
4. **文档对象缺失：** 无 RawAsset/ConversionRun/DerivedBlock/EvidenceAnchor/LossReport 等产品模型，PDF 甚至可能只取第一行形成 `document:first-claim`。
5. **Release 证明资产，不证明能力：** NSIS lifecycle 没有真实 PDF/学习/AI 用户流；workflow 合同仍需只接受 full-qualification attestation。

### 2.8 豆包与 DeepSeek 外部审计的独立裁决

外部引用 ID：`EXT-AUDIT-DOUBAO-20260809`、`EXT-AUDIT-DEEPSEEK-20260809`。二者分别登记，不合成为一个来源，也不互相算独立代码证据。

| 来源 | 外部判断 | 本总包处理 |
|---|---|---|
| DeepSeek | Facade、FastAPI/SQLite/Tauri、迁移、WAL、权限、Candidate、Outbox/Receipt、备份/回滚是成熟基础 | 改写为“当前代码存在且可能复用的底座”；每项仍以 current tree/installed evidence 复验，不继承“成熟”结论 |
| DeepSeek + cloud audit | Release v0.5.0 的 exact-SHA/installer/checksum/下载回读可靠 | 采纳“资产身份链较可靠”，不扩张为“产品能力可靠” |
| 豆包 | 人学得更深缺少练习→掌握→复习→Teach Back 产品闭环 | 完全采纳，增加 AXW-025 早期 proof，并作为 v1.0 阻断 |
| DeepSeek/豆包 | Evidence/AI 侧治理构件存在 | 采纳“有底座”，但未证明交叉验证和 AI 学习闭环 |
| DeepSeek | 媒体链、图像 OCR 已完成 | 驳回完成度；cloud audit 证明当前主要是 FFprobe/Pillow 元数据或探针 |
| DeepSeek | 下一步优先 Dynamic Planner | 驳回；通用 Planner 延期，只有双学习闭环明确需要的受控调用才可进入 |
| 豆包 | Visual Teaching/Spatial Memory 与核心定位有张力 | 采纳“不阻断当前核心”的部分；用户后续明确其为永久 LER 产品层，按 Horizon 分期而非删除或只留模糊探索备注 |
| 豆包 | 外部能力吸收已结束的文档表述需要统一 | 驳回广义禁令；改为合法复用优先、逐 Adapter/revision/license 评估 |
| DeepSeek | README 缺许可证、无签名 Release、生产 CORS/Auth 需清晰 | 纳入 AXW-005；实际配置与 LICENSE 状态由 Codex 基于最新 tree 复验 |

外部审计只作为输入，不拥有路线权威。凡与当前代码或用户最新定位冲突，以当前证据和本 v4 裁决为准。

---

## 3. 产品真相与边界

### 3.1 唯一名称合同

| 层级 | 当前名称 | 规则 |
|---|---|---|
| 中文产品 | 元枢工作台 | 面向用户、文档、安装器 |
| 英文产品 | ArcheAxis Workspace | 唯一英文全名 |
| 简称 | ArcheAxis | UI 空间有限时使用 |
| 产品类别 | Human–AI Learning & Knowledge Workspace / 人机双向学习与知识工作台 | 本地优先、证据约束、开放兼容；不再写 OS/Agent Platform |
| GitHub 仓库 | Cognitive-Loop-OS | v1.0 RC 前暂时保留，必须标 Historical Repository ID |
| 包/协议/数据目录 | 暂缓统一迁移 | 由独立迁移 TaskPack 完成，不在修 PDF 时顺手改 |

`Cognitive-Loop-OS` 在迁移完成前只承担 Git/历史分发兼容身份，不代表当前产品定位、用户可见名称或未来 machine id。

内部模块只用职责命名：

```text
workspace-shell, library-core, vault-core, asset-store,
import-service, conversion-engine, document-model, evidence-core,
knowledge-core, human-learning-core, ai-learning-assets-core,
memory-core, rules-core, skills-core, evaluation-feedback-core,
search-index, canvas-graph, adapter-sdk,
desktop-runtime, release-qualification
```

### 3.2 产品使命

让个人在不丢原件、不丢来源、不被单一软件锁定的前提下，把分散在文件、网页、社区、百科、学术文献、笔记库和媒体中的资料，经对照与交叉验证转化为长期可追溯的证据和知识；同一套证据既帮助人完成更深、更高效、可证明的学习，也帮助个人 AI 建立准确、可撤销、可调用的记忆、规则、技能和规范。

### 3.3 核心双学习系统

**Human Learning System：**

```text
EvidenceBundle
→ Learning Objective
→ Explanation / Example / Concept Relation
→ Exercise / Retrieval Practice
→ Review Schedule
→ Mastery Signal
→ Teach Back / Transfer Task
→ Correction and new evidence demand
```

**AI Learning System：**

```text
EvidenceBundle
→ Memory/Rule/Skill/Standard/Context Candidate
→ provenance + scope + freshness + conflict check
→ human/policy approval
→ callable Memory / RuleSpec / SkillSpec / Standard
→ controlled invocation + outcome proof
→ correction / supersession / revocation
```

**互相转换：**

- Evidence/知识可以生成解释、例子、练习、卡片，也可以生成 AI memory/rule/skill candidate；
- 人类的错误、掌握信号、Teach Back 和修订可反向纠正 AI 记忆与规则；
- AI 的总结、题目、链接建议和技能草案永远先是 candidate，由人或策略复核；
- 人类学习记录不能被直接当作公共事实，AI 调用结果也不能自动升级为证据。

### 3.4 北极星指标

```text
双学习有效闭环率
= 同时完成“开放资料可用 + 证据形成 + 人类学习结果 + AI 可验证使用 + 重启/导出”的主题数
  / 用户进入学习的主题数
```

辅助指标：

- 安装后首份真实 PDF 成功打开率；
- 从导入到首次有效批注/笔记的时间；
- EvidenceAnchor 重启后稳定率；
- Vault C4 语义往返无损率；
- 转换损失可见率；
- 失败任务恢复率；
- 冲突零静默覆盖率；
- 开放导出成功率；
- 人类学习增益：延迟测验、迁移题、Teach Back 的可复现改善；
- AI 使用增益：引用正确率、规则/技能调用成功率、过期/冲突记忆拦截率；
- 人类资产⇄AI 资产转换的人工采纳率与纠错率。

测试数量、Job 数、Receipt 数、Agent 调用数和 registry 项目数不是产品 KPI。

### 3.5 服务对象与必须完成的任务

| 用户 | 必须完成的真实任务 |
|---|---|
| 普通用户 | 拖入资料、核对来源、形成可靠结论、记住并能应用、让个人 AI 准确复用 |
| 学生 | 教材/课件/网页→证据→理解/练习/复习/掌握/Teach Back→回原页 |
| 教师 | 多源备课、证据对照、生成并审核练习、观察掌握信号、开放交付 |
| 研究者 | 论文/表格/网页/论坛观点对照，主张、矛盾、页码、引文和结论可追溯 |
| 专家 | 把经验转成有范围/版本/证据的规则、规范、技能，供自己和 AI 受控调用 |
| 个人 AI | 在授权范围内检索证据、使用可撤销记忆、执行已批准技能，并提交调用结果和来源 |
| 隐私/低配用户 | 离线核心闭环、明确授权、按需 OCR/模型、无 GPU 可用 |

### 3.6 当前非目标与正式远期能力的边界

以下不是 H0–H5/v1.0 的退出条件或基础运行依赖：

- 通用 Agent OS、多 Agent 编排和通用 Workflow Automation；它们只保留为 H10 Exploration，不能反向改定位；
- 插件市场、社区分享、团队协作和社交网络；相关开放 SDK/可选协作只在 H9 另行激活；
- 3D/VR/AR；它们仍是 CAP-07/AXW-090 的正式 H8 长期能力，而不是当前 Release 前置；
- 以云端模型、高端 GPU、网络服务或任何单一第三方 Provider 为必需条件的核心功能。

“当前不建设”不等于永久删除。只有通用 Agent OS 作为产品类别、自治无审查进化、商业多产品矩阵和 WORK-LAB 产品耦合属于真正 retired positioning；其余远期能力继续受 Capability Atlas 保护。

“AI 学习系统”不等于在本机训练基础模型，也不等于放开自治 Agent。v1.0 的含义是：AI 对个人证据、记忆、规则、技能和规范的受控学习与调用，全部可追溯、可更正、可撤销。

### 3.7 Product Positioning v3 固定表述

**中文规范句：**

> 元枢工作台（ArcheAxis Workspace）是一款本地优先、证据约束、开放兼容的人机双向学习与知识工作台。它将真实文件、现有知识库和经核验的开放资料，在保留原件、来源、版本与转换损失的前提下，转化为人可理解、练习、记忆与迁移的学习资产，以及 AI 可审查、可评估、可复用、可撤销的记忆、规则、技能、规范与上下文资产。人与 AI 的学习反馈可以双向提出转化候选，但只有经过来源校验、评估和用户授权后，才能升级为正式知识或正式 AI 资产。

**English canonical statement:**

> ArcheAxis Workspace is a local-first, evidence-grounded, open-interoperable Human–AI Learning & Knowledge Workspace. It transforms real files, existing knowledge bases, and corroborated open sources—while preserving originals, provenance, versions, and loss—into human learning assets and reviewable AI memory, rules, skills, standards, and context. Human and AI feedback may create bidirectional candidates, but nothing becomes verified knowledge or an approved AI asset without source validation, evaluation, and user authorization.

**固定短句：**

> 同一份开放格式资料，人学得更深，AI 用得更准。

这是产品使命/设计目标，不是当前 v0.5.0 已被研究证明的效果声明。达到比较性评测门槛前，对外 capability 只能写“支持可测的双学习闭环”，不能写“已证明提升学习效果/AI 准确率”。

术语边界：

- `Deep Human Learning` 指理解、迁移、长期记忆、练习、反馈与元认知，不是神经网络 Deep Learning；
- `AI Learning` 默认指外置、版本化、可审查的 Memory/Rule/Skill/Standard/Context/Eval 资产，不默认训练或微调模型权重；
- `AI Skill` 是有输入、输出、权限、依赖、测试、版本和回滚的可复用程序/流程资产，不是自治 Agent；
- Agent 只是未来可选的资产消费者/执行 Adapter，不是产品中心、一级导航或当前通用 Runtime。

### 3.8 Naming Contract v3

| 层级 | Canonical target | 迁移期规则 |
|---|---|---|
| 品牌 | `ArcheAxis` / `元枢` | 永久；不另建第二品牌 |
| 产品显示名 | `ArcheAxis Workspace` / `元枢工作台` | UI、README、manifest、installer、Release 唯一名称 |
| 产品类别 | `Human–AI Learning & Knowledge Workspace` / `人机双向学习与知识工作台` | 不能替换为 OS/Agent Platform |
| machine id | `archeaxis-workspace` | 配置和合同中小写稳定 ID |
| 当前云端仓库 | `DTALEX66/Cognitive-Loop-OS` | legacy repository ID，只允许 current-remote/history/migration 语境 |
| proposed 云端目标 | `DTALEX66/ArcheAxis-Workspace` | AXW-080 preflight 确认名称/权限/集成后才晋升 canonical target |
| 当前本地 checkout | `unknown/unverified` | 历史文档可能出现旧 Cognitive 路径；执行时探测，不能凭旧文档认定 |
| 本地 checkout canonical basename | `ArcheAxis-Workspace` | parent path 由用户/机器选择并只进 BaselineEvidence/bootstrap；不得盲目重复 clone/自动删除旧目录 |
| Python distribution target | `archeaxis-workspace` | 旧 distribution 至少两个稳定版本兼容/迁移 |
| Python import target | `archeaxis_workspace` | 禁止无迁移 bulk rename；先 facade/alias |
| CLI target | `archeaxis` | 旧 CLI 至少两个稳定版本 alias + deprecation |
| environment prefix | `ARCHEAXIS_` | 旧 `COGNITIVE_` 变量逐项双读/告警；不能一次删除 |
| config namespace | `archeaxis.*` | 旧 key 通过 migration map；未知双定义 fail closed |
| public API target | `/api/v1/{sources,imports,assets,documents,evidence,learning,ai-assets,capabilities}` | 旧 `/kb`/`/workspace` 路由先保留 compatibility facade |
| event/topic prefix | `archeaxis.workspace.*` | durable event migration 必须兼容旧 consumer |
| database filename proposed | `archeaxis-workspace.db` | 先 inventory 当前 owners/files；不得仅 rename 导致双库 |
| Rust crate target | `archeaxis-desktop-shell` | 仅在独立 build migration 中改 |
| Tauri `productName` | `ArcheAxis Workspace` | installer/window/about 一致 |
| Tauri bundle ID target | `com.archeaxis.workspace` | 与签名、升级和数据目录 migration 一起验证 |
| Windows 数据根目标 | `%LOCALAPPDATA%\ArcheAxis\Workspace` | 事务迁移、备份、读回、回滚；portable 独立 |
| portable env target | `ARCHEAXIS_PORTABLE_ROOT` | 属于 `ARCHEAXIS_` 迁移；旧 `COGNITIVE_PORTABLE_ROOT` 双读两版本并警告 |
| URI target | `archeaxis://` | 旧协议 alias 与 deep-link migration 独立验证 |
| Task ID | `AXW-*` | 旧 MS/K/A–N/B/C/R 只在 history index |
| branch 前缀 | `codex/axw-<id>-<slug>` | release 分支 `release/vX.Y.Z`；一个 Task 一个 branch |
| Release 标题 | `ArcheAxis Workspace vX.Y.Z` | 旧 Release 永不改写 |
| Installer 目标名 | `ArcheAxis-Workspace-Setup-X.Y.Z-x64.exe` | 资产名迁移在新版本开始，不重写历史资产 |
| executable/process target | Windows `ArcheAxis.exe`；service `archeaxis-local-service` | 先 inventory 当前进程/防火墙/快捷方式引用，再迁移 |
| window/About title | `ArcheAxis Workspace` | Tauri、browser shell、crash dialog 一致 |
| Start Menu/shortcut | `ArcheAxis Workspace` | 旧 shortcut 在升级时安全替换，不留死链接 |
| uninstall display/identity | `ArcheAxis Workspace` + 稳定 upgrade identity | 名称变化不得让升级变成第二份安装 |
| update channel | `archeaxis-workspace/stable`, `.../beta` | channel 与签名/manifest 分离；旧 channel 有迁移 |
| config/log dirs | target data root 下 `config/`, `logs/` | 日志脱敏；current inventory→backup→migration |

本地 checkout 路径只属于 machine truth/dev bootstrap，禁止出现在 runtime、测试 fixture、发布合同、用户数据模型和通用文档。检测到新旧两个 checkout 同时存在时 fail closed，要求用户选择，不自动删除/合并。

### 3.9 内部领域命名

当前允许的核心领域：

```text
source-core
asset-store
conversion-engine
evidence-core
knowledge-core
human-learning-core
ai-learning-assets-core
memory-core
rules-core
skills-core
evaluation-feedback-core
vault-core
document-model
search-index
canvas-graph
workspace-shell
adapter-sdk
desktop-runtime
release-qualification
```

历史概念映射：

| 历史名 | 当前名/处置 |
|---|---|
| Human Learning OS | `Human Learning Core` |
| Machine Knowledge OS / MKU | `AI Learning Assets Core` / migration alias |
| Cognitive Workspace | `ArcheAxis Workspace` |
| Cognitive/Agent Runtime | `Optional Execution Adapter`，deferred |
| Evolution/Sleep Loop | `Evaluation & Feedback Core`；自治演化叙事作废 |
| Model/Agent/Open-source Foundry | `Upstream Ledger` / `Adapter Registry`，不是用户产品 |
| Knowledge Graph/Cognitive Map | `Canvas / Graph / Learning Map` |
| Visual Teaching Studio | `Visual Teaching & Courseware`，LER 正式能力族，按 Horizon 分期 |
| Interactive Simulation Lab | `Simulation & Practice Lab`，LER 正式能力族，实验能力需运行证据 |
| Spatial Memory Palace/2.5D/3D/VR | `Spatial Memory`，LER 正式长期能力族；高级形态需 fallback 与学习效果证据 |
| 旧学习链 `A→B Translation`（Human→Machine） | `Controlled Human⇄AI Transformation` / CAP-09；不得再用 A/B 指代普通学习迁移 |

### 3.10 历史别名索引

每个别名必须在 `HISTORICAL_ALIAS_INDEX_V1.yaml` 登记 `replacement`、`allowed_contexts`、`retired_at`：

| 旧名 | 状态 | 允许语境 |
|---|---|---|
| `Cognitive-Loop-OS` | legacy repo slug | current remote、redirect、history、migration |
| Cognitive Loop OS / Cognitive OS / Cognitive-OS / Cognitive-Loop-OS / 认知闭环系统 | retired positioning | legacy/history 引用 |
| AXOS / ArcheAxis-OS / ArcheAxis OS / 元枢系统 / 元枢桌面 / ArcheAxis Cognitive Workspace | deprecated display alias | history、migration、旧 Release |
| 元枢·观心 | retired codename | history；除非用户以后明确重新启用 |
| Human–AI Learning & Knowledge System | historical descriptor | 引用旧文档；新类别以 Workspace 结尾 |
| WORK-LAB / HERMES / A–N / B-C-R | external/legacy identifiers | CI 兼容或历史索引；禁止产品命名 |
| Obsidian-compatible Workspace | milestone descriptor | roadmap/capability；不是产品名 |
| OpenHuman | external UX reference | provenance/ADR；不是模块名 |
| ArcheAxis OS V3.0 / V3.1 文档名 | historical blueprint label | legacy/reference index；不得作为当前 truth version |

### 3.11 产品 UI 词表

一级工作空间固定为：

1. Workspace / 工作区
2. Library / 资料库
3. Evidence / 证据
4. Learning / 学习
5. AI Assets / AI 资产
6. Settings / 设置

Global Search 位于顶栏；Canvas/Graph 是中央工作区视图，不再单独膨胀成新产品。`Agents`、`Runtime`、`Machine`、`Evolution`、`WORK-LAB`、`HERMES` 禁止作为一级导航。

AI Assets 内的用户对象固定为：Memory、Rule、Skill、Standard、Context、Evaluation。动作词固定为：`Propose`、`Review`、`Approve`、`Revise`、`Revoke`、`Invoke`；禁止用一次转换直接 `Activate`。

### 3.12 仓库与分发迁移合同

远端仓库、本地目录、包/CLI、bundle/data root 是四个独立、可回滚的迁移，不能一包 bulk rename：

1. Truth 文档先记录 current + target，不立即改远端；
2. 冻结 current remote/default branch/tags/releases/open PR/worktree；
3. Owner 重命名 GitHub repo，验证 redirect、Actions、Release URL、clone、badges；
4. Codex 更新 origin、metadata、文档和自动化；
5. 只有无活跃进程且 checkout clean 时，用户/Owner 才移动本地目录；
6. Python/CLI/env 采用双读 alias 和 deprecation；
7. Tauri bundle/data root 单独做 backup→migrate→readback→rollback；
8. 旧 tag、Release、assets、commit message 永不改写；
9. 至少两个稳定版本后才可删除兼容 alias。

### 3.13 Candidate-by-default 不变原则

- 外部材料进入后是 RawAsset/SourceRecord；其中主张是 ExtractedClaim/EvidenceCandidate，不直接是 Evidence；
- 人工输入可以作为“用户确实写下/评价了什么”的一手记录，但其中对外部世界的主张仍需核验；
- AI 输出、摘要、题目、评语、Memory/Rule/Skill 草案一律是 Candidate/Proposal；
- 执行 trace/OutcomeProof 只能证明该环境下发生了什么，不能自动证明知识或规则普遍正确；
- 任何 Candidate 晋升都必须经过对应来源、评估、冲突、权限和批准合同；
- 正式资产也有版本、有效期、替代和撤销，不存在不可更改的“永久真相”。

---

## 4. 四层闭环与统一完成定义

### 4.1 v0.5.1 生存闭环

```text
安装正式包
→ 上传一份真实、有文本层的 PDF
→ 能力探针确认 PDF 引擎已随安装包存在
→ 原件落盘且 hash 可查
→ 转换产生非空、合理顺序的内容
→ UI 打开 PDF/派生内容
→ 失败显示缺依赖/加密/损坏等可行动原因
→ 关闭应用并重启
→ 同一文档仍可打开
```

不得再用空 PDF、改扩展名文本、只验证模块 import 或源码环境测试替代。

### 4.2 开放资料/Obsidian C4 闭环

```text
安装 ArcheAxis
→ 选择真实 fixture Vault
→ 发现目录、Markdown、属性、链接、附件、Canvas
→ 在左侧文件树打开 Markdown/PDF/Office
→ 中央阅读/编辑/高亮/批注
→ 右侧查看属性、反链、引用和损失
→ 搜索并跳回来源
→ 安全保存正文/属性/Canvas
→ 关闭并重启读回
→ 在 Obsidian 或独立解析器打开同一 Vault
→ 外部再修改
→ ArcheAxis 检测冲突，不静默覆盖，可回滚
→ 导出开放资料包
```

这条链是第一高保真互操作纵切和产品基础面，但不单独等于最终差异化承诺。

### 4.3 v1.0 人机双向学习最小闭环

```text
选择一个真实学习主题
→ 导入 PDF/网页/Vault 中至少两类独立来源
→ 每个 Claim 绑定原件和位置
→ 建 EvidenceCandidate，显示支持/反驳/限制
→ 形成 CrossValidationRecord 和 EvidenceBundle
→ 人：目标→解释→练习→延迟复习→MasterySignal→Teach Back
→ AI：同一 EvidenceBundle→Memory/Rule/Skill Candidate
→ 评测、范围/权限/冲突检查→用户批准新 revision
→ 在一次低风险任务中受控检索/调用并返回来源和 OutcomeProof
→ 人的错误/Teach Back 与 AI 调用结果提出修订候选
→ 审核后修订或撤销，不自动改真相
→ 关闭重启后学习状态、证据、AI 资产和引用全部可读
→ 开放导出
```

v1.0 至少证明一个端到端主题，而不是同时覆盖所有学科、所有 Skill 或通用 Agent。

### 4.4 能力声明的六重证据

任何 capability 只有同时满足以下条件才能标记 released：

1. 真实用户操作路径；
2. 真实非空 fixture 与语义断言；
3. 源码和 bundled/installed runtime 均通过；
4. UI 可见结果和可行动错误；
5. 关闭/重启读回；
6. exact-SHA artifact、installer、hash 回读和对应 Release evidence。

对于写入/往返能力，还必须增加冲突、备份、rollback 和独立 parser/另一应用回读。

---

## 5. 目标产品架构

### 5.1 总分层

```text
Sources & Vaults
        ↓
Raw Asset / Open File Truth
        ↓
Import & Conversion Orchestration
        ↓
Derived Document / Block / Loss Report
        ↓
Evidence / Annotation / Link / Revision
        ↓
Library / Reader / Editor / Search / Canvas
        ↓
Cited AI / Learning / Ecosystem Adapters
```

### 5.2 核心对象

| 对象 | 职责 | 不可破坏条件 |
|---|---|---|
| `SourceConnection` | Vault、目录、网页、Zotero 等来源授权 | 只访问 Approved Roots/显式授权 |
| `RawAsset` | 原件、hash、mime、size、来源、版本 | 派生失败不能改写原件 |
| `ImportBatch`/`ImportItem` | 一次导入及逐文件状态 | 幂等、可恢复、逐项错误 |
| `ConversionRun` | 引擎/profile/version/状态/资源/日志 | 可取消、重试、比较、复现 |
| `DerivedDocument` | 可展示的结构化文档 | 指回 RawAsset 和 ConversionRun |
| `DerivedBlock` | 段落、标题、表格、图片、公式等 | 有稳定 block identity |
| `LossReport` | 丢失、降级、不支持、置信度 | 不能静默丢弃 |
| `EvidenceAnchor` | 页、bbox、slide、sheet/cell、time/text range | 重启和重建索引后仍可解析 |
| `Annotation` | 高亮、批注、引用笔记 | 明确人工/模型来源 |
| `Revision`/`Conflict` | 写入版本、expected hash、差异 | 禁止静默覆盖 |
| `IndexRevision` | 全文/向量/图派生索引版本 | 索引可删可重建 |

### 5.3 格式处理状态机

```text
detected
→ dependency-ready
→ preserved
→ converted
→ semantically-validated
→ persisted
→ indexed
→ presented
→ restart-verified
→ roundtrip-verified
```

UI 和文档只能声明实际到达的状态。`detected` 不能写“支持”，`converted` 不能写“知识已完成”。

### 5.4 大文件与持久任务

- 上传采用 streaming/spool，不把整文件一次读入内存；
- 原件进入 content-addressed storage 或安全引用模式；
- 转换从 HTTP 请求线程移到持久 worker；
- 每个 Item 独立 progress、retry、cancel、error；
- Job/Outbox/Receipt 只作为内部可靠设施，通过产品 BFF 映射为 Import/Conversion 状态；
- 崩溃后 queued/running 状态必须可恢复或明确失败；
- CPU、内存、GPU、磁盘和外部进程有预算与终止合同。

### 5.5 安全和数据主权

- 默认本地处理；云模型只能显式开启；
- 不自动扫描个人磁盘或私人 Vault；
- 路径必须 realpath 后验证 containment，并防 symlink escape；
- 初次连接真实 Vault 默认只读；
- 写入必须 expected hash + 原子替换 + 备份 + revision + conflict + rollback；
- AI/转换输出先进入 derived/candidate，不自动升级为人工确认的知识；
- 用户删除原件、派生、索引、模型缓存和云端凭据时边界清晰；
- 日志不记录正文、凭据或私人绝对路径。

### 5.6 Evidence Policy v1

`Evidence` 是受保护词，不能再把任何来源、摘录、AI 输出或单次执行结果直接叫证据。

| 对象 | 精确定义 | 是否可称 Evidence |
|---|---|---|
| `RawAsset` | 不可变原件或受控引用 | 否 |
| `SourceRecord` | 作者、时间、URL/路径、hash、版本、抓取方式、来源类型 | 否 |
| `ExtractedClaim` | 从来源抽取、可判断真假的陈述 | 否 |
| `EvidenceCandidate` | 有 SourceRecord + EvidenceAnchor、支持/反驳某 Claim 的候选 | 否，UI 写“待核验材料” |
| `CrossValidationRecord` | 来源独立性、权威性、时效、适用范围、支持/冲突分析 | 否，它是验证过程 |
| `CorroboratedEvidence` | 满足风险对应的交叉验证策略、范围明确的证据 | 是，UI 简称 Evidence |
| `EvidenceBundle` | 围绕一个 Claim 的支持/反驳证据、矛盾、限制和结论 | 是 |
| `VerifiedKnowledge` | 基于 EvidenceBundle 且经人工/规则审批的知识版本 | 是已审知识，不等于永恒真理 |
| `GeneratedArtifact` / execution trace | 模型生成或调用结果 | 可证明“该模型/程序在该输入和环境下输出了什么”；不能作为外部世界事实的独立 Source/佐证，只能产生 Candidate/Proposal |

### 5.7 来源与交叉验证规则

来源类型至少区分：

```text
primary/official
academic/peer-reviewed
reference/encyclopedic
professional/reporting
community/forum
user-owned-document
software-runtime-evidence
generated-artifact/model-output (provenance-only)
```

来源类型不是简单“高低分”；它决定能证明什么：论坛可作为真实用户经历的第一手材料，却不能单独证明普遍因果；官方资料可证明官方在某版本/日期的声明，却不能自动证明其效果。

晋升规则：

1. 普通开放网页、百科、二手文章、社区/论坛主张：至少两个相互独立来源，优先含一个一手/权威来源；
2. 官方一手资料：仍需检查版本、时间、适用范围；要证明广泛效果/因果，必须有独立佐证；
3. 学术主张：保留论文版本、研究设计、样本、限制、撤稿/勘误状态和相互矛盾研究；
4. 用户自有文件：hash 只证明“该文件这样写”，不能自动证明其中外部主张真实；
5. 软件运行证据：fixture、exact source SHA、environment、command、assertion、artifact 必须可复现；
6. 高风险医疗/法律/财务：一手权威 + 独立佐证 + 人工复核，禁止自动晋升；
7. 暂无独立佐证的单来源内容只能保持 `EvidenceCandidate`，UI 显示限制；
8. 必须记录反证、来源相关性/转述链、时效、司法辖区/版本和未解决矛盾；
9. 置信度是评估结果，不是来源数量的简单平均。

建议验证等级：

```text
EV0 unanchored material
EV1 anchored candidate
EV2 corroborated by independent source(s)
EV3 cross-validated with conflicts/scope/freshness assessed
EV4 reviewed/adjudicated for a declared use
```

只有 EV3/EV4 对象可在普通 UI 中显示“证据”；EV4 仍需保留有效期和可撤销状态。

### 5.8 人类学习对象

```text
LearningObjective
Concept / Relation
Explanation / Example / Counterexample
LearningNote
Exercise / RetrievalPrompt / TransferTask
ReviewItem / ReviewEvent
MasterySignal / MasteryAssessment
TeachBackSubmission / RubricAssessment
Misconception / Correction
LearningPath
LearningEffectEvaluation
```

每个对象必须关联 EvidenceBundle 或明确标记为学习者个人反思。掌握不能只由“看过”“点过”或模型评分决定；至少结合 retrieval、延迟回忆、迁移题、Teach Back 或人工评价中的适用证据。

### 5.9 AI 学习资产对象

```text
AIMemoryCandidate → AIMemoryRevision
RuleCandidate → RuleSpec
SkillCandidate → SkillSpec
StandardCandidate → StandardSpec
ContextCandidate → ContextPack
EvaluationCase / EvaluationResult
AIUseEvaluation
InvocationPlan / InvocationReceipt / OutcomeProof
Supersession / Revocation
```

所有正式 AI 资产至少有：

- provenance/EvidenceBundle；
- scope、audience、permissions；
- created/updated/effective/expiry；
- version、dependencies、compatibility；
- evaluation cases 与已知失败；
- approval actor/policy；
- supersession/revocation；
- 对 Skill 的 input/output/side effects/rollback；
- 对 Memory 的 freshness/conflict/taint；
- 对 Rule/Standard 的优先级、适用范围和冲突决议。

### 5.10 双向转化合同

允许的转化只生成候选：

```text
EvidenceBundle → Human Learning Asset Candidate
EvidenceBundle → AI Asset Candidate
HumanLearningAsset → AIAssetCandidate
ApprovedAIAsset / Evaluation → HumanLearningAssetCandidate
Human error/mastery/Teach Back → Knowledge or AI Asset Change Proposal
AI evaluation/invocation outcome → Human Learning or AI Asset Change Proposal
Memory/Rule/Standard → Skill or Context Candidate
Skill outcome/Evaluation → Memory/Rule/Standard Revision Candidate
```

统一晋升：

```text
candidate/proposal
→ source validation
→ evaluation
→ conflict and scope check
→ human/policy review
→ approve as new revision
→ monitor
→ supersede/revoke
```

禁止 HumanNote→active AIMemory、AI output→VerifiedKnowledge、execution success→Skill approved 的直通路径。

---

## 6. UI 信息架构与 OpenHuman 吸收方案

### 6.1 目标桌面结构

```text
┌──────────────────────────────────────────────────────────────────┐
│ Workspace switch | Global search | Import | Capability | Settings│
├───────────────┬────────────────────────────────┬─────────────────┤
│ Mode tree     │ Central multi-tab work surface │ Context panel   │
│ Files/Vault   │ Markdown/PDF/Office/Canvas     │ Outline         │
│ Sources       │ Evidence compare/adjudicate    │ Properties      │
│ Evidence      │ Human learning session         │ Links/Citations │
│ Learning      │ AI Memory/Rule/Skill editor    │ Contradictions  │
│ AI Assets     │ Search/Graph/Learning Map      │ Annotation/Eval │
│ Topic Tree    │                                │ Context actions │
├───────────────┴────────────────────────────────┴─────────────────┤
│ Collapsible activity strip — only while work runs/fails/needs user│
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 OpenHuman：吸收与拒绝

吸收：

- 中央区域保留足够宽度，作为真正工作面；
- 左侧树表达来源、层级和长期结构；
- 右侧面板随当前对象变化，不长期占据主视线；
- 底部只在任务运行、失败或等待用户时出现；
- 其 Memory Tree 只作为来源概念，产品词采用 Topic Tree / Knowledge Tree / Learning Map；
- 模式切换清楚，但不把所有能力变成一级菜单。

拒绝：

- 不把中央区做成 Agent 聊天主页；
- 不复制 GPL-3.0 源码、组件或视觉资产到非 GPL 核心；
- 不接入 OpenHuman/TinyAgents/TinyFlows 作为产品 Runtime；
- 不复制品牌、逐像素布局和专有服务依赖。

实施方式是截图/行为研究、独立 wireframe、独立组件树、独立 CSS token 和行为回归，不读取后直接改写其源码。

### 6.3 一级工作空间

1. Workspace / 工作区
2. Library / 资料库
3. Evidence / 证据
4. Learning / 学习
5. AI Assets / AI 资产
6. Settings / 设置

Search 是顶栏全局能力；Canvas/Graph/Learning Map 是中央工作面的视图，不再各自膨胀为一级产品。AI Assets 是可审查的 Memory/Rule/Skill/Standard/Context/Eval 资料库，不是 Agent 控制台。

以下内容进入 Settings 下的 Advanced/Diagnostics，而非普通用户主导航：

- Conversion Runs；
- Index Status；
- Adapter/Capability Status；
- Audit/Diagnostics；
- Runtime/Process/Receipt；
- Release/Build information。

禁止 `Agents`、`Models`、`Runs`、`Builder`、`Machine`、`Evolution`、`WORK-LAB`、`HERMES` 成为一级导航。模型 Provider 设置可在 Settings/AI Providers，调用记录在 AI Asset 的 Evaluation/Invocation context 中按需查看。

### 6.4 中央工作面

必须支持：

- 多标签和未保存状态；
- Markdown 阅读/编辑/分屏；
- PDF.js reader、页缩略图、搜索、选择、高亮、锚点；
- Office 结构视图和“用原应用打开”；
- 图片 OCR overlay；
- 表格工作表/区域视图；
- transcript 与时间跳转；
- JSON Canvas；
- 历史、版本和冲突提示。

### 6.5 右侧上下文面板

按对象显示 Outline、Properties、Links/Backlinks、Citations、Evidence/Contradictions、Annotations、Conversion/Loss、Learning、AI Asset Evaluation 和 Cited AI。默认只打开当前最相关页签；小窗口可折叠为抽屉。

上下文动作可包括：`Create Evidence Candidate`、`Compare Sources`、`Create Exercise`、`Propose Memory`、`Propose Rule`、`Package Skill`、`View Evaluation`。所有 AI 转化动作必须使用 `Propose`，不能从选区直接生成 active 资产。

### 6.6 状态与反馈

- blue：处理中；green：通过；yellow：需注意/降级；red：失败；gray：排队；
- 进度只能使用真实单位：页数、文件数、字节、阶段，不制造假百分比；
- 前端说用户能理解的动作和原因，不暴露内部阶段 ID；
- 每个错误至少提供重试、换 profile、查看原件、查看诊断或取消中的一种行动。

### 6.7 多产品 UI 研究的最终吸收表

| 来源 | 吸收能力 | 进入位置 | 不吸收 |
|---|---|---|---|
| Obsidian | file-first、workspace tabs、properties、links、Canvas | Library/中央/右侧 | 私有插件运行时、逐像素克隆 |
| OpenHuman | 中央宽工作面、Memory Tree、上下文 pane | App shell | GPL 代码、Agent 中心 |
| Zotero | collection、reader、annotation、citation | Sources/PDF/Citations | 整个客户端源码 |
| Readwise Reader | Feed/Library 分离、高亮与回顾 | Sources/Library/Learning | 自动内容直接变正式知识 |
| NotebookLM | Sources + 对资料提问 + 产出区 | 右侧 Cited AI/候选输出 | AI 作为产品唯一主页 |
| Anytype/Capacities/Tana | properties、type/schema、collection/query | Properties/Saved Search | 对普通用户暴露 Object/supertag 术语 |
| Heptabase/AFFiNE | 卡片白板、文档与画布融合 | Canvas | 先做重型无限画布平台 |
| Logseq/Roam | backlinks、block/page reference、局部图 | Links/Graph | 现在重做 block-first 数据库 |
| AppFlowy/Notion | 同一数据的 grid/board/calendar view | v1.x Collection views | 一开始复制协作数据库产品 |
| Joplin/SiYuan | 本地资源、导入导出、版本/块经验 | Adapter 与安全合同 | AGPL 代码直接合并 |
| Anki | daily review、FSRS、preset | Learning | 把高级调参放默认界面 |
| VS Code | split pane、command palette、setting scopes | Shell/Settings | 开发者工具感主导 UI |
| Home Assistant | connection、backup、diagnostic control center | Settings | 把控制台放首页 |
| Langfuse/Phoenix | trace/session/evaluation 区分 | Advanced diagnostics | 追踪 UI 冒充用户知识面 |

### 6.8 Evidence 工作面

中央采用 Claim-centric 对照：左/中可并排打开多个来源，右侧显示 Claim、支持材料、反证、来源独立性、时效、适用范围和 CrossValidationRecord。用户可以：

- 从原页/段/单元格/时间点创建 EvidenceCandidate；
- 合并或拆分 Claim；
- 标记 supports/refutes/qualifies/unclear；
- 识别转述链和同源重复；
- 比较官方网站、百科、论坛、期刊等不同来源；
- 记录矛盾和未解决问题；
- 在达到策略后提交 EvidenceBundle 审核；
- 一键回到任何来源锚点。

UI 不使用“AI 已验证”这种表述。AI 可建议相似来源、差异和缺失验证，但 CrossValidation 与晋升必须可解释、可人工覆盖。

### 6.9 Human Learning 工作面

围绕一个 EvidenceBundle/主题显示：学习目标、概念关系、解释/例子、主动回忆、练习、复习计划、掌握证据和 Teach Back。默认不是卡片数量仪表盘，而是“下一项最有价值的学习动作”。

掌握视图必须区分：见过、理解自评、回忆成功、延迟回忆、迁移应用、Teach Back。模型评分只能作为一个候选信号。

### 6.10 AI Assets 工作面

以资料库方式展示 Memory、Rule、Skill、Standard、Context、Evaluation，而非 Agent/Run 控制台。每项详情显示：来源证据、范围、版本、权限、依赖、评测、调用记录、已知失败、过期、冲突、替代和撤销。

Skill editor 中央可编辑输入/输出/schema/steps/tests/rollback；真正执行需要受控 Adapter 和权限确认。v1.0 只需要证明一个低风险、只读或可回滚技能纵切，不建设通用 Planner。

---

## 7. 多格式资料路线

### 7.1 PDF

基础 profile：

- 原件保存和 mime/signature 检测；
- 文本层解析；
- 页数、页文本、基本顺序；
- PDF.js 原件阅读；
- 页级与文本范围 EvidenceAnchor；
- 加密、损坏、纯扫描件、空文本的明确分类。

富 profile：

- layout、表格、图片、公式、阅读顺序；
- OCR fallback；
- bbox 级锚点；
- 多引擎比较和 LossReport。

### 7.2 Office

- DOCX：段落、标题、表格、图片、脚注/关系尽可能保留；
- PPTX：slide、shape、notes、图片、表格；
- XLSX/XLS/CSV：sheet、cell range、formula/value、merged cell、header；
- 原件可随时用系统应用打开；
- 结构视图和派生 Markdown 不能冒充原件完整保真；
- 每种格式都有真实 fixture 和 installed-format gate。

### 7.3 图片/OCR

- Pillow 只能负责图像读入/元数据，不等于 OCR；
- Tesseract 作为轻量 baseline；
- 中文复杂版面优先评估 PaddleOCR sidecar；
- 输出 word/line/block、bbox、confidence、language、engine revision；
- 低置信度和分歧进入人工复核，不自动成为事实。

### 7.4 网页

- Trafilatura 作为正文 baseline；
- 动态页面通过隔离浏览器 worker；
- 保存 URL、抓取时间、响应/快照 hash 和原始证据；
- SSRF、登录态、提示注入和 robots/服务条款进入连接器安全合同。

### 7.5 音视频

- 当前 FFprobe 元数据不等于内容处理；
- v1.0 后再接 faster-whisper optional sidecar；
- 时间戳 transcript、speaker/segment confidence 和媒体原件锚点；
- 无 ASR 组件时只声明 media-preserved/metadata-ready。

### 7.6 JSON Canvas

- 以开放 `.canvas` 文件为真相；
- 支持 text/file/link/group nodes、edges、位置、尺寸、颜色和未知字段保留；
- 内部 SQLite Canvas 不能冒充 JSON Canvas 兼容；
- 应用增强字段采用可逆扩展或 sidecar；
- 需要独立 parser 和 Obsidian 往返 fixture。

---

## 8. Obsidian C0–C5 兼容路线

### 8.1 等级定义

| 等级 | 必须能力 | 完成证据 |
|---|---|---|
| C0 发现 | Vault root、目录、`.md`、attachments、`.canvas`、`.obsidian` 边界 | 安全扫描、不越界、不改文件 |
| C1 读取 | Markdown AST、YAML 类型/顺序/未知字段、links/embeds、attachments、Canvas | 全量 fixture 解析和语义快照 |
| C2 日常工作 | 文件树、编辑、搜索、properties、links/backlinks、attachments、reader、Canvas | 安装版真实用户流和重启 |
| C3 安全写入 | stable identity、atomic write、expected hash、backup、revision、conflict、rollback | 并发外改、crash、恢复测试 |
| C4 往返 | Obsidian↔ArcheAxis 交替编辑，语义和资源不丢 | independent parser + Obsidian 人工/自动 readback |
| C5 生态桥接 | 受控插件/API/其他 PKM 适配器 | 每个 Adapter 独立发布证据 |

### 8.2 现有 importer 不应继续堆叠

已审计的旧 importer 存在随机 ID、正文截断、手写 frontmatter、只扫部分中文目录、无附件/Canvas、无幂等、无 rename/delete、无冲突/rollback、反链未接入、甚至自动创建高置信候选等结构性问题。

处置：

1. 旧 `apply` 路径默认禁用或标 legacy；
2. 不在它上面继续添加双向同步；
3. 新建 `vault-core`/Compatibility Kernel；
4. 从稳定文件身份、完整读取和只读工作台开始；
5. 直到 C3 资格通过才对真实 Vault 开放写入。

### 8.3 C4 语义范围

v1.0 必须保护：

- 文件路径和文件名；
- Unicode、换行和编码；
- YAML 值类型、列表、顺序、未知字段；
- headings、wikilinks、Markdown links、embeds、block refs；
- attachment relative paths；
- tags、aliases、properties；
- JSON Canvas node/edge 语义和未知字段；
- rename/delete/link update；
- 外部修改和冲突分支；
- 备份与 rollback。

不承诺 Obsidian 私有插件运行时、Live Preview 逐像素行为或所有社区插件语义。

---

## 9. 开源研究总池的重新统一

### 9.1 四个数字的真实含义

| 数据集 | 数量 | 含义 | 不能被解释为 |
|---|---:|---|---|
| 去重研究总池 | 369 | 广泛调研候选 | 369 项已集成 |
| 仓库 registry/ledger | 101 | 历史登记对象 | 101 项已吸收 |
| 开源能力精选表 | 57 | 某阶段深入选型/路线候选 | 57 项当前 P0 |
| 当时 implemented | 8 | 有某种代码/依赖证据 | 安装版全功能 released |

这些集合有交叉、重复、不同时间快照和不同定位。不能相加，也不能继续以“数量变大”作为进度。

补充：`Cognitive_Loop_OS_开源候选_STAR清单_2026-07-17.xlsx` 自身是约 103 个去重候选的早期快照；369 是 7 月 31 日把更多研究来源汇总后的更大去重池。二者不是同一批次，也不能拿 103/369 的差值当开发进度。

### 9.2 统一数据合同

新 `UpstreamCandidateV2` 至少包含：

```text
candidate_id
canonical_url
upstream_revision_or_release
capability_domain
product_user_path
code_license_spdx_and_hash
model_data_asset_font_fixture_licenses
selected_components
integration_mode
security_and_network_profile
fixture_and_quality_benchmark
upgrade_strategy
rollback_or_kill_switch
status
supersedes / superseded_by
owner_decision
```

每个进入代码的候选再建立 `ReuseDecisionRecord`：

```text
problem
evaluated alternatives
why dependency/SDK/CLI/sidecar/fork applies or not
license decision
pinned revision
selected API/files
modifications
tests and installed qualification
removal plan
```

### 9.3 强制复用阶梯

```text
开放格式/标准
→ 成熟许可兼容依赖
→ 官方 SDK/API/CLI
→ 隔离 sidecar
→ 固定 revision 的许可兼容 fork/vendor
→ 行为/fixture 洁净参考
→ 自研
```

Codex 若直接进入自研，必须在 TaskPack/PR 中记录前六层为何不适用。许可证未知、模型条款不清或来源不可固定时停止集成，不以“开源”字样替代审查。

### 9.4 当前激活原则

- v0.5.1–v1.0 只激活能直接服务 PDF、Office、OCR、Vault、Markdown、Canvas、search、evidence、reader/editor、FSRS 的候选；
- Agent/记忆/工作流/通用 RAG 平台不删除研究记录，但状态统一 `deferred-v2`；
- GPL/AGPL 不再默认排除：若顶层许可证组合兼容并履行源码、修改、分发和网络义务，可直接依赖、复制、修改、fork、vendor 或合并；自定义许可逐条批准；
- 闭源产品只通过公开格式、API、导出和独立行为研究兼容；
- 所有旧 `implemented` 在没有 installed evidence 时降为 `integrated-unqualified`。

### 9.5 v1.0 前开源组件激活矩阵

以下是产品路线裁决，不替代精确 revision 的许可证审查。表中“许可注意”只用于选择集成方式；真正进入 PR 前必须从固定 tag/commit 重查 LICENSE、依赖、模型、资产和 fixture 条款。

| 能力 | 候选/标准 | 当前用途 | 集成方式 | 当前波次 | 许可/边界裁决 |
|---|---|---|---|---|---|
| PDF 原件阅读 | Mozilla PDF.js | reader、页、选择、搜索、渲染 | 前端依赖/封装 | v0.6 | 优先直接依赖；进入某次 Release 时写入 ReleaseFreeze，并完成 NOTICE |
| 基线转换 | Microsoft MarkItDown | 轻量 PDF/Office baseline | Python dependency + format extras | v0.5.1 | 现有集成不等于 extras 随安装包；必须 installed qualification |
| 富文档结构 | Docling | layout/table/formula/reading order | optional provider | v0.6–0.7 | 代码与模型/下载物分别审查；不得成为基础安装唯一引擎 |
| PDF 文本校验 | pypdf / pdfplumber | 页数、文本、fixture 语义交叉校验 | 测试/轻量 provider 候选 | v0.5.1 | 选一个最小依赖；不要同时堆叠无职责组件 |
| PDF 高难基准 | MinerU | 中文复杂 PDF 质量对照 | 隔离 benchmark/待许可 | 研究 | 自定义条款未决时不进核心 |
| PDF 高难基准 | Marker | 精度对照 | 隔离 benchmark | 研究 | GPL/模型条款；不进宽松核心 |
| OCR baseline | Tesseract | 轻量、离线 OCR | optional system/bundled provider | v0.7 | 安装器要验证 binary/language pack，而非只测 Python wrapper |
| 中文复杂 OCR | PaddleOCR | 版面、表格、公式、中文扫描 | optional sidecar | v0.7 | 代码、模型卡、模型文件在进入某次 Release 时分别写入 ReleaseFreeze；资源预算和卸载清理 |
| OCR 仲裁 | GLM-OCR/其他模型 | 低置信度第二意见 | benchmark/后置 provider | v1.x | 只有模型许可与硬件实测通过后启用 |
| Office DOCX | python-docx/Docling | 结构提取 baseline/富 profile | dependency/provider | v0.7 | 选择职责清楚的组合，保留原件与 LossReport |
| Office PPTX | python-pptx/Docling | slide/shape/note 提取 | dependency/provider | v0.7 | slide EvidenceAnchor 必须稳定 |
| Spreadsheet | openpyxl + CSV stdlib | sheet/cell/formula/value | dependency/provider | v0.7 | 公式不执行为事实；记录 cached value/缺失 |
| 广格式 fallback | Apache Tika | 特殊格式兜底 | optional sidecar | v1.x | 不能扩大基础安装；JVM 能力/体积/安全独立显示 |
| 格式 CLI fallback | Pandoc | 开放格式转换参考/可选 CLI | external CLI/sidecar | v1.x | copyleft 边界；不复制源码进核心 |
| 网页正文 | Trafilatura | 静态网页正文和元数据 | dependency | v0.7 | 已有集成需补来源快照、失败和 installed evidence |
| 动态网页 | Crawl4AI/浏览器 | 动态页面抓取 | 隔离 worker | v1.x | SSRF、登录态、prompt injection、网络许可单独门禁 |
| Markdown AST | CommonMark/GFM 成熟 parser | 语义读取、链接/块定位 | dependency | v0.8 | 做 parser bake-off；禁止继续手写子集 |
| YAML roundtrip | ruamel.yaml 或等价成熟库 | frontmatter 类型/顺序/未知字段保留 | dependency | v0.8 | 需 fixture 证明注释/格式的实际承诺边界 |
| 编辑器 | CodeMirror 6 / ProseMirror/Lexical 候选 | Markdown 编辑、extension surface | 前端 dependency | v0.8 | 通过 spike 选一个；避免多编辑器长期并存 |
| JSON Canvas | 官方开放规范 | `.canvas` 数据合同 | 原生实现 | v0.8 | 规范优先；未知字段保留；不依赖 Obsidian 私有代码 |
| Canvas 交互 | XYFlow/React Flow 候选 | node/edge 编辑表面 | 前端 dependency | v0.8 | 与 JSON Canvas 文件真相分离；若现有 UI 栈不适配则洁净自研轻层 |
| 全文搜索 | SQLite FTS5 | 可重建本地全文 | 内建能力 | v0.6–0.8 | 先做确定性全文，向量不是前置 |
| 向量检索 | sqlite-vec / LanceDB | 派生语义索引 | optional index provider | v0.9+ | 数据库仍不是原件真相；可完全删除重建 |
| 本地 embedding/rerank | Qwen 小型 embedding/reranker | 本地语义检索 | optional model provider | v0.9+ | 模型卡、体积、显存、量化和下载源独立登记 |
| 本地推理 | llama.cpp | 可选本地 LLM runtime | sidecar/provider | v0.9+ | 模型许可证不随 runtime 许可证自动通过 |
| 模型路由 | LiteLLM 或薄 Provider | 可选云/本地 provider 统一接口 | existing/reevaluate | v0.9 | 不让框架接管产品数据模型；凭据和出机需显式授权 |
| ASR | faster-whisper | transcript + 时间锚点 | optional sidecar | v1.x | 模型、DLL、硬件 profile、安装/卸载单独资格 |
| 学习调度 | py-fsrs | 间隔重复 | Python dependency | v0.9 | 调度参数可解释；卡片必须指回 EvidenceAnchor |
| 文献互操作 | BibTeX/CSL JSON/Zotero API/export | 文献、附件、引用 | Adapter | v1.1 | 格式/API 是最小方式；若 R-C 兼容，可另包评估 AGPL 源码吸收 |
| 卡片互操作 | Anki/open card exchange | v0.9 只做基础 CSV/开放卡片导入导出；完整 APKG/API/media/history 在 v1.2 | Adapter | v0.9/v1.2 | 交换格式与 py-fsrs 分离；若 R-C 兼容，可另包评估 AGPL 源码吸收 |

### 9.6 相关软件与开源项目的最终处置

| 项目/生态 | 对当前产品的真实价值 | 处置 |
|---|---|---|
| Obsidian | 第一高保真开放文件工作流 | C0–C4 核心；格式/行为兼容，不复制闭源本体 |
| OpenHuman | 中央工作面、Memory Tree、上下文布局 | 当前先 clean-room；完成 copyleft composition decision 后可选择依法源码吸收 |
| Zotero | PDF 批注、collection、citation、研究来源 | v1.1 首个研究 Adapter；API/开放格式 |
| Anki | 卡片交换、复习行为 | v0.9 py-fsrs + 基础 CSV；v1.2 AXW-071 完整 Adapter |
| Joplin | Markdown/resources/notebook/export | v1.2 Adapter；API/导出优先 |
| Logseq | page/block ref、outliner、Markdown/EDN | v1.3 Adapter；若选择兼容 AGPL 顶层策略，可另包评估源码吸收 |
| SiYuan | 本地块、资源、API/export | v1.3 Adapter；协议隔离 |
| Readwise Reader | source/highlight/review 工作流 | v1.4 API/export Adapter + UX 参考 |
| Anytype | object/property/query/collection | UX/schema 参考；不引入 Object 术语 |
| Capacities | 对象化知识、属性体验 | UX 参考；公开导出后置 |
| Tana | supertag/schema UX | 行为参考；公开导出/API 后置 |
| Roam Research | block reference、网络笔记 | 行为/导出参考；不复制闭源实现 |
| Notion | database views、properties、collaboration | v1.x API/export；协作不进 v1.0 |
| Heptabase | card/whiteboard 组织 | Canvas UX 参考；不克隆产品 |
| AFFiNE | doc/whiteboard 融合 | UX 参考；许可审查前不复制代码 |
| AppFlowy | grid/board/calendar 多视图 | v1.x Collection 视图参考 |
| Excalidraw | 开放画布/嵌入生态 | C5 后置 Adapter，不阻断 JSON Canvas |
| NotebookLM | Sources + grounded ask + studio outputs | 右侧 Cited AI/候选输出参考 |
| VS Code | split panes、palette、settings scope | Shell/Settings 交互参考 |
| Home Assistant | integrations/backups/diagnostics | Settings 控制中心参考 |
| Langfuse/Phoenix | trace/eval 信息结构 | 仅 Advanced diagnostics；不成为知识 UI |
| RAGFlow/Dify/Open WebUI | RAG/LLM 产品比较 | 研究/行为参考；不整体嵌入 |
| LightRAG/Graphiti/Cognee/KAG | 图/时态/检索算法 | v1.5 后研究，不抢 deterministic search/links |
| TinyCortex/Mem0/Letta | Agent memory | v2 deferred；admission/freshness/taint/provenance 概念可进入洁净 ADR，但项目代码/依赖不激活 |
| PydanticAI/LangGraph/AutoGen | Agent runtime/workflow | v2 deferred；AutoGen 不作核心依赖 |
| TinyAgents/TinyFlows/TinyJuice | Agent/flow/context | GPL 隔离研究；不进入 v1.x 产品核心 |
| CoWork OS/NOUS OS/Bob's Big Brain Compiler | OS/Agent/认知架构研究 | 历史研究，不再支配当前定位 |
| OpenTelemetry/OpenInference | 诊断语义 | 内部可观测合同，数据最小化，非产品主面 |
| DeepEval/Ragas/Promptfoo/Inspect AI | AI 评测 | v0.9 后仅服务 cited AI 的离线/CI 资格 |
| Repomix/编码 Agent 项目群 | 工程研究和 Codex 工具辅助 | 不打包进产品，不算产品能力 |

### 9.7 对历史 57 项精选表的批量裁决

- **v1.0 激活/重评：** Docling、PaddleOCR、LanceDB/sqlite-vec（仅需时二选一/可选）、Qwen embedding/reranker（v0.9）、llama.cpp、LiteLLM、py-fsrs、XYFlow、OpenTelemetry/OpenInference（内部）。
- **v1.x 来源/媒体扩展：** Crawl4AI、faster-whisper、Tika 等按独立 Adapter/profile 启用，不阻断 v1.0。
- **仅 benchmark/待许可：** MinerU、Marker、Chandra、SQLite-Vector、tldraw production SDK。
- **v1.5+ 算法研究：** Graphiti、LightRAG、KAG、RAGFlow、Haystack、Cognee、本地多模态检索。
- **v2 deferred：** Mem0、Letta、PydanticAI、LangGraph、TinyAgents、TinyFlows、OpenHuman runtime、TinyJuice、AutoGen、NOUS OS、Agent OS 论文/项目。
- **工具链而非产品：** Repomix、DeepEval、Ragas、Promptfoo、Inspect AI、marimo、MCP SDK/Apps、Hermes Agent。

迁移这些条目时不删除研究历史；只修正 `product_relevance`、`target_horizon`、`integration_mode` 和 `status`，并把重复 canonical URL 归并为 `superseded_by`。

---

## 10. 版本蓝图 v2

### Horizon 0 — v0.5.1：产品真相与 PDF 生存修复

交付：

- Truth Reset、命名、能力声明和历史归档；
- bundled/installed capability probe；
- 真实 PDF fixture；
- PDF/Office 必需 extras 进入锁文件、wheel、bundled Python 和 installer；
- 安装版 PDF 用户流；
- GatePlan 聚合和 Release full-qualification 语义修复。

退出：在干净 Windows 安装环境中，真实 PDF 能完成保存→转换→打开→重启读回；无依赖时 UI 不再笼统报错。

### Horizon 1 — v0.6：原件、转换与 PDF 知识闭环

交付：

- RawAsset、ImportBatch/Item、ConversionRun、DerivedDocument/Block、LossReport、EvidenceAnchor；
- SourceRecord、ExtractedClaim、EvidenceCandidate、CrossValidationRecord、EvidenceBundle 的最小合同；
- streaming/spool、persistent worker、progress/retry/cancel/recovery；
- PDF.js reader；
- 页/文本/bbox 锚点、高亮、批注、搜索、重启回位；
- Import Center 和中央工作区第一版。
- 一个不依赖 Obsidian C4 的早期 Human Learning proof slice（pretest→retrieval→delayed/transfer/Teach Back sample）。

退出：从 PDF/网页选区生成有来源的 Claim/EvidenceCandidate，完成一次双来源对照并点击返回原页；同一主题完成早期可测学习切片，关闭重启后定位和学习记录不漂移。

### Horizon 2 — v0.7：常见学习资料

交付：

- DOCX/PPTX/XLSX/XLS/CSV；
- 图片 OCR；
- HTML；
- 批量导入与逐项恢复；
- installed-format matrix；
- Office/image/table reader；
- 转换 profile 与 LossReport UI。

退出：每种格式完成原件→转换→结构验证→展示→索引→重启回读。

### Horizon 3 — v0.8：Obsidian-compatible Workspace C4

交付：

- Vault discovery/stable identity/incremental scan；
- Markdown AST/YAML roundtrip；
- files/properties/tags/links/backlinks/attachments/search；
- Markdown editor；
- JSON Canvas；
- rename/delete/link update；
- expected hash、atomic write、revision、backup、conflict、rollback；
- Obsidian/independent parser roundtrip qualification。

退出：两个应用交替编辑 fixture Vault，关键语义、附件和 Canvas 不丢，外部修改不被静默覆盖。

### Horizon 4 — v0.9：交叉验证证据与人机双向学习

交付：

- Evidence compare/adjudication 工作面；
- 来源独立性、支持/反驳、时效、范围和矛盾记录；
- 选择资料范围的带引用问答，citation 点击回 EvidenceAnchor；
- Human Learning Core：目标、解释、练习、复习、MasterySignal、Teach Back；
- AI Learning Assets Core：Memory/Rule/Skill/Standard/Context/Eval candidate→approve→revise/revoke；
- Human/AI feedback 只生成双向 Change Proposal；
- py-fsrs 和基础开放卡片/CSV exchange；
- 可选本地模型 provider；
- 一个低风险、受控、可回滚 Skill 调用纵切及 OutcomeProof。
- LearningEffectEvaluation 与 AIUseEvaluation 的同主题比较性资格。

退出：一个真实主题完成 EvidenceBundle→人类练习/掌握/Teach Back→AI Memory/Rule/Skill→受控调用→反馈修订；每个结果可回来源，无证据时拒答/标注不确定，任何互转都不自动成为正式资产。

### Horizon 5 — v1.0：稳定本地工作台

交付：

- 大 Vault/大 PDF 性能档位；
- 无障碍、键盘、缩放、小窗口；
- 低配/无 GPU profile；
- upgrade/migration/uninstall/data recovery；
- 开放导出包；
- Evidence Policy EV3/EV4 产品流；
- Human Learning 与 AI Learning Assets 最小双向闭环；
- Windows installer exact-SHA 全用户流；
- 仓库/包/协议/数据目录命名迁移的独立决策与兼容方案。

### Horizon 6–10：唯一长期路线入口

§10 只对 H0–H5 当前 Release Spine 具有规范权威。H6–H10 的唯一权威表是 §27.7–§27.11：H6 Research/Knowledge/Adapters/Course/Visual Teaching；H7 full learning/animation/simulation/2.5D；H8 3D/VR/AR + encrypted sync/device + one controlled-execution research；H9 SDK/signed extension/publish/optional community；H10 generic Agent/autonomous exploration。版本标签可调整，能力顺序、状态和证据门槛不得由本摘要另行改写。

### Learning Experience & Representation Layer（永久产品层，分期退出门槛）

- H1–H5：表格、卡片、对比、时间线、Canvas、Graph、Learning Map、基础课件与 2D 表征；
- H6：Visual Teaching、Courseware、图解、动画脚本与交互内容；
- H7：Simulation & Practice Lab、动态解释、2.5D Spatial Memory 与学习行为评估；
- H8：3D/VR/AR Memory Palace 与受控学习效果研究；
- 每项高级表现必须回到 EvidenceAnchor、提供开放导出、文本/2D/无障碍 fallback，并分别记录 technical state 与 learning-evidence state。

LER 不参与尚未到达其 Horizon 的 Release 退出门槛，但它不能被删除或降成没有任务/对象的模糊备注。JSON Canvas、Graph 和 Learning Map 仍属于核心开放知识组织能力，不等待 3D/VR。

仍为纯 Exploration/Deferred 的是：通用 Agent、多 Agent、自治演化、Foundry/Marketplace；它们不借 LER 回流主线。

---

## 11. Codex 执行合同

### 11.1 主体与权限

1. Codex 是本项目当前唯一执行与交付责任主体。
2. 不再生成“交给 HERMES 执行”的提示词，不等待 HERMES，不把旧 HERMES TaskPack 当当前权限源。
3. Codex 可使用内部只读子任务并行研究，但重叠源码必须只有一个 patch owner。
4. 跨仓库写入、仓库改名、branch protection、正式 Release、删除远端分支、访问个人资料等需要新增权限时，Codex 停止并输出 Owner Action。
5. 本总包授权的是按用户后续指令执行本项目/Workspace 任务，不自动授权本轮直接修改云端仓库或发布版本。

### 11.2 每包开始协议

Codex 在任何任务卡开工前必须：

1. 重新读取仓库根 `AGENTS.md` 及适用的嵌套指令；
2. fetch/读取最新 `main`、目标 branch、commit、tree、open PR、checks、Release；
3. 记录 `BaselineEvidence`：repo、branch、commit、tree、dirty state、相关 workflow/policy/lock hash；
4. 检查工作区现有改动并保护用户修改；
5. 将任务绑定一个 Horizon、Program、用户动作和 capability；
6. 建立/更新 Reuse Decision Record；
7. 先写真实 RED fixture/失败复现，再实现；
8. 输出 scope checksum，防止任务中途漂移。

### 11.3 原子交付规则

- 一次一个原子 TaskPack、一个 branch、一个 PR、一个冻结 head/tree；
- 分支命名以任务 ID 开头，如 `codex/axw-012-pdf-installed-closure`；
- 不混合无关命名、CI、UI 和数据迁移；
- 不改写已评审历史，不 force-push，不移动现有 tag；
- 数据/schema 变化必须 forward migration、backward compatibility、backup 和 rollback；
- 先相关本地 gate，再一次云端 CI；无代码变化不重复全量；
- CI 失败优先重跑失败/受影响 gate，并先判断 flake 与真实缺陷；
- 任务完成后输出固定完成报告，不能只说“测试通过”。

### 11.4 固定完成报告

```text
Task ID / Horizon / Capability
before SHA/tree → after SHA/tree
changed files and user-visible behavior
Reuse Decision: upstream URL/revision/license/mode
RED evidence → GREEN evidence
local gates and results
real fixture/user flow
source vs bundled vs installed status
restart/roundtrip/conflict evidence
CI workflow/run/attempt/profile
artifact/installer/download SHA-256
migration/rollback/kill switch
remaining risks and explicitly deferred items
next eligible Task ID
```

### 11.5 禁止计为产品进度

- 纯文档或 schema 存在；
- 静态字符串/文件名断言；
- mock/空 fixture；
- Python 源码环境单测；
- 模块 import；
- Job/Receipt 生成；
- UI 中出现占位菜单；
- registry 状态修改；
- CI job 数量增加。

除 Truth/CI/迁移专项外，每个产品任务必须有用户动作和可见结果。

---

## 12. 总任务图

```text
H0 产品修复 Spine
AXW-000 云端冻结 → AXW-003 Gate Verdict Hotfix
AXW-002A + AXW-011A → AXW-010 → AXW-012 Installed PDF Survival

并行 Truth Spine（不阻塞 AXW-012）
AXW-001A → AXW-004A/C
AXW-004B/D/E/F 按独立 PR 后续完成

v0.5.1 Release 资格 Spine
AXW-012 + AXW-002D + AXW-007A/B + AXW-008A/B + AXW-009A/C/D
+ 本次实际进入 bundle 的 AXW-006 许可/RDR/分发证据
→ exact-SHA full qualification → v0.5.1 Release exit

后续产品数据与界面 Spine
AXW-012 → AXW-020A/B/C
AXW-015A/B/C/D + AXW-020A/B/C → AXW-021
AXW-020A/B/C → AXW-022 + AXW-024A/B + AXW-030A/B

产品证明 Spine（不依赖 Obsidian C4）
Human: AXW-011A + AXW-022 + AXW-024A/B
       → AXW-025 Early Human Learning Proof → AXW-051A/B/C/D
Cited AI: AXW-020C + AXW-022 + AXW-024A/B + AXW-030A/B
          → AXW-050
AI Assets: AXW-005A + AXW-015A/B/C/D + AXW-024A/B + AXW-095A/B/C
           → AXW-052A/B/C/D/E
AXW-051A/B/C/D + AXW-052A/B/C/D/E + AXW-024C/D + AXW-030A/B
→ AXW-053A/B/C/D
AXW-053D + AXW-050 → AXW-054
→ AXW-055 Dual-Learning Minimum Closure

开放互操作 Spine
AXW-020A/C + AXW-030B
→ AXW-040 → AXW-041 → AXW-042 → AXW-043 → AXW-044 → AXW-045
→ AXW-090C Canvas/Graph/Learning Map

稳定资格 Spine
AXW-009C → {AXW-055 installed capability qualification, AXW-009D installer lifecycle}
AXW-055 + AXW-045 + AXW-009D + AXW-094A/B
→ exact-SHA full qualification
→ AXW-060 Stable v1.0 Qualification

并行正式扩展（只有 required_current=true 才阻塞对应 Release）
AXW-023 Office/OCR/HTML/Media
AXW-070+ Ecosystem Adapters
AXW-090A/B/D–N LER/Courseware/Animation/Simulation/Spatial/Editor/Packages
AXW-091–095 Research/Knowledge/Learning/Project/Sync/Provider Programs
AXW-080/081/082 Repository/Local/Distribution Naming Migration
```

可并行边界：

- AXW-002 与 AXW-003 可在 AXW-000 后并行；
- AXW-006A/B、AXW-007A/B 可在 Truth/PDF 修复旁并行；完整许可证历史回填、跨机离线 kit 和所有 Windows hardening 不阻塞 v0.5.1；
- AXW-030 可在 AXW-020 合同冻结后与 AXW-021/022 并行，但 BFF/API owner 单一；
- AXW-024 可与 Import/UI 实现并行，但对象命名和 promotion policy 只能有一个 owner；
- AXW-041/043 的 parser spike 可并行，只能在 AXW-040 stable identity 合并后落主线；
- AI/学习不得早于 EvidenceAnchor、EvidenceBundle、reader 和 search；
- AXW-025 早期学习证明不等待 Obsidian C4；AXW-051 是后续产品化，不依赖 Cited AI；
- 生态 Adapter 不得早于 C4 和 Adapter contract。
- LER 是永久产品 Program；AXW-090A/B/C 随相应数据/Canvas 基础激活，D–N 按 Horizon 激活，不得提前阻塞当前 Release，也不得从蓝图删除。

### 12.1 Program Card 与原子 Child Task

以下父 ID 是 Program/验收总卡，**不得直接建立一个大 PR**。Codex 只能执行一个 child ID；每个 child 一个 branch/PR/frozen tree。未列为 Program 的 AXW 卡默认是原子 TaskPack，若开工时 scope 超过一个可独立回滚用户结果，必须先补 child split。

| Program | 原子 child | 单 PR 范围 |
|---|---|---|
| AXW-001 Truth Reset | `001A` Positioning/README/AGENTS/current truth projection；`001B` legacy/deferred archive；`001C` manifest/UI/capability wording projection | 先 001A；移动历史和用户表面投影分包 |
| AXW-002 OSS Ledger / Dynamic Provider | `002A` schema + 当前 PDF/reader RDR bootstrap；`002B` 369/101/57/8 后台映射；`002C` license/revision/status gate；`002D` 跨平台 Compatibility Policy/schema；`002E` 通用 resolver/probe/benchmark；`002F` 通用 ReleaseFreeze/rollback/substitute engine | PDF 只依赖 002A；H0 Windows 可先消费 002D schema；002B/E/F 不自动阻塞 PDF |
| AXW-004 Naming/Authority/Scope | `004A` truth/naming/evidence/authority schemas；`004B` aliases/reference/doc metadata；`004C` digest + Truth-Drift Gate；`004D` Capability/Requirement/Scope Ledger；`004E` anti-delete/task-graph gate；`004F` machine truth projections | 本文在 001A+004A/C 后退役；B/D/E/F 分包推进 |
| AXW-005 Security Truth | `005A` config/PermissionDecision/tool-risk；`005B` product license/SBOM/NOTICE；`005C` signing decision/contract | 005A 是 AI Skill/Execution 的统一权限 owner；未签名可明确声明，不冒充已签名 |
| AXW-006 OSS Absorption | `006A` R-P/R-C 顶层许可组合；`006B` distribution/license schema；`006C` NOTICE/SBOM/source bundle；`006D` vendor/fork/sidecar gate；`006E` self-replacement contract | 合法吸收优先；非商业不是许可豁免 |
| AXW-007 Windows Environment | `007A` read-only doctor/baseline；`007B` Windows toolchain candidate/observation adapter、ReleaseFreeze instance 与 build provenance；`007C` language boundary guard；`007D` sidecar ABI/lifecycle | 007B 只消费 002D canonical schema，不重定义 resolver；下一次无 sidecar 的 bundle 只要求 A/B |
| AXW-008 Bootstrap/Cache | `008A` online bootstrap；`008B` cached-only；`008C` portable offline kit | A/B 先行；完整跨机 kit 不阻塞 PDF |
| AXW-009 Windows Build | `009A` profile runner；`009B` Windows bug corpus；`009C` exact-SHA bundle；`009D` clean installed qualification | PowerShell 薄编排，复杂规则在 Python |
| AXW-011 Fixture Corpus | `011A` PDF；`011B` Office/image/HTML；`011C` Vault/Canvas；`011D` media | 每类 fixture/license/oracle 独立 |
| AXW-015 Durable Operations | `015A` command/API error/idempotency/revision；`015B` job/lease/checkpoint/cancel/retry/recover/compensate；`015C` event/transactional outbox/SSE；`015D` correlation/diagnostics/redaction | 内部 foundation；AXW-021 等只消费，不另建域内第二套 |
| AXW-020 Core Contracts | `020A` Source/RawAsset/Import；`020B` Conversion/Derived/Loss；`020C` Anchor/Index/Revision | migration 按对象族分包 |
| AXW-023 Format Matrix | `023A` DOCX；`023B` PPTX；`023C` XLSX/CSV；`023D` OCR；`023E` HTML | 每个 format/profile 独立 installed evidence |
| AXW-024 Evidence Core | `024A` schema/migration；`024B` validation/promotion policy；`024C` compare UI；`024D` revision/expiry/export | 024A/B 可在 v0.6；C/D 在产品化阶段 |
| AXW-030 Workspace Shell | `030A` clean-room ADR/layout shell；`030B` canonical IA/routes；`030C` responsive/accessibility/activity | 不与 reader/data migration 混包 |
| AXW-051 Human Learning | `051A` objectives/practice model；`051B` FSRS/history；`051C` mastery/Teach Back；`051D` basic CSV card exchange | 完整 Anki 是 AXW-071 |
| AXW-052 AI Assets | `052A` schemas/revisions；`052B` promotion/conflict/freshness；`052C` Library UI；`052D` low-risk Skill executor；`052E` export/revoke | 通用 Planner 不进入任何 child |
| AXW-053 Bidirectional | `053A` TransformationProposal；`053B` Human→AI；`053C` AI→Human；`053D` installed end-to-end | 每方向独立候选/审查证据 |
| AXW-090 LER | `090A` representation contract；`090B` structured views；`090C` map/canvas/graph；`090D` courseware；`090E` animation；`090F` simulation；`090G` 2D/2.5D spatial；`090H` 3D/VR/AR；`090I` learning evaluation；`090J` four-layer teaching/route package；`090K` editor/renderer；`090L` spatial semantics；`090M` package/export/fallback；`090N` course/learning views and effect capture | 永久 Program，按 Horizon 激活；090H 固定为 `binding_long_term + experimental_later`；technical 与 learning evidence 分开 |
| AXW-091 Research/Knowledge | `091A–G`，详见 §27.12 | discovery/source/research package/knowledge lifecycle/search 分包 |
| AXW-092 Full Learning Methods | `092A` diagnose/route；`092B` cognitive load/memory encoding/practice；`092C` metacognition/error；`092D` profile/consolidation；`092E` transfer/project/effect | HL-01–16 不做单一大 PR |
| AXW-093 Course/Project/Research | `093A` objects/contracts；`093B` workspace UX；`093C` session/rubric/reflection；`093D` package/portfolio/output proof | 不依赖 Agent execution |
| AXW-094 Exchange/Sync/Publish | `094A–G`，详见 §27.12 | H5 只激活 A/B；C 可早定义；D–G 后置 |
| AXW-095 Provider/Model | `095A` profile/probe；`095B` egress/permission；`095C` model/asset manifest；`095D` budget/fallback/audit；`095E` eval/revoke | Settings 内部能力，不建 Models/Agents 一级导航 |
| AXW-096 Platform Portability | `096A` platform contract；`096B` macOS；`096C` Linux；`096D` companion research | 每平台独立资格；D 不复制业务逻辑 |
| AXW-097 SDK/Extension/Community | `097A` versioned SDK；`097B` signed extension/permission；`097C` compatibility/sandbox；`097D` provenance sharing | H5/H8 前只 planned |
| AXW-098 Controlled Execution | `098A` adapter contract；`098B` permission/sandbox/lifecycle；`098C` installed reversible proof | 不扩展为通用 Agent Runtime |
| AXW-099 Solution Profiles | `099A` profile schema；`099B` persona templates；`099C` installed user-flow qualification | 不生成新产品/SKU/数据库 |

父卡不使用一次性的 `complete` 语义，而是记录 `program_status`、`required_current_children`、`future_children` 和 `release_completion`。当前 Release 只要求 `required_current_children`；未来 child 永久保留但不阻塞当前 Release。尤其 AXW-090/091–095 属于长期 Program，不能因为 H8 child 未做而使 H0–H5 永远未完成，也不能因为当前 Release 完成就把未来 child 删除。parent 名称不得被拿来创建 branch、commit 或“全部完成”回执。

---

## 13. Codex Program 与原子任务卡

### AXW-000｜云端事实冻结与执行面清点

**Horizon：** H0
**优先级：** P0 / 第一包
**类型：** 只读审计 + 最小治理变更（如用户授权）
**依赖：** 无

**目标用户结果：** 后续所有任务基于同一个真实 commit/tree/PR/Release，不再因旧摘要导致反复审计和漂移。

**实施：**

1. 读取最新 default branch、HEAD commit/tree、最近 merge、open PR、open issue、remote branches、tags、releases、Actions；
2. 对每个 open PR 标出：目标、head SHA、是否落后、变更文件、CI、是否仍符合 Workspace 路线；
3. 对安装版最新公开 Release 核对版本、资产、哈希和 identity；
4. 定位当前唯一 authority docs、当前 UI 入口、import/conversion/vault/CI/release 实现；
5. 生成机器可读 `docs/audit/CURRENT_BASELINE.json` 或仓库约定等价物；
6. 只提出 owner-only 动作，不擅自删分支、关 PR 或改保护。

**验收：**

- 所有事实带获取时间、commit/tree 或 API evidence；
- 旧 PR 号/SHA 不被当成现状；
- 清单能区分 merged/superseded/active/unknown；
- 输出后续任务可引用的 baseline digest。

**非目标：** 全仓代码修改、分支清理、正式 Release。

---

### AXW-001｜Product Truth Reset 与历史污染隔离

**Horizon：** H0 / Program Product Truth
**优先级：** P0
**粒度：** Program Card；只执行 AXW-001A/B/C child
**依赖：** AXW-000

**目标用户结果：** 用户、贡献者和 Codex 打开仓库时只看到 Workspace 定位与当前路线，不再被 Cognitive/Agent/WORK-LAB 蓝图带偏。

**预计触点：** `README.md`、`AGENTS.md`、产品定位/状态/边界/命名/路线文档、release manifest、UI strings、docs navigation、truth contract tests。

**实施：**

1. 建立唯一当前入口：Product Positioning、Future Blueprint v2、Current Plan、Capability Matrix、Release Qualification、Upstream Ledger；
2. 对外名称统一为元枢工作台 / ArcheAxis Workspace；
3. 仓库名仅标历史技术 ID，并记录 v1.0 RC 前独立迁移计划；
4. 将 A–N、B/C/R、旧 handoff/taskpacks、认知/Agent 重型蓝图移入 `docs/legacy/` 或 `docs/deferred/`；
5. 每个历史文档顶部写 `Historical/Deferred — not execution authority`；
6. 从默认 agent discovery、docs 索引和 TaskPack 生成器排除历史内容；
7. 删除/改写反向锁定旧标题/旧 handoff 的 meta-tests；
8. 增加 Truth Drift contract：扫描 README、AGENTS、定位、当前计划、capability、manifest 和用户可见名称。

**验收：**

- 根入口不再把产品称为 Cognitive OS/Agent OS；
- WORK-LAB/Obsidian-Assistance 没有运行时、路径或产品权威；
- 历史文件仍可追溯但不被当前 agent 默认读取；
- Truth Drift 测试以语义/允许词表工作，不锁死整段旧文案；
- UI、README、manifest 和 installer 名称一致。

**回滚：** 文档移动保留 git history；必要时 revert 单 PR。

---

### AXW-002｜开源研究池、Registry 与 Upstream Ledger v2

**Horizon：** H0 / OSS Governance
**优先级：** P0
**粒度：** Program Card；只执行 AXW-002A–F 中一个明确 child
**依赖：** AXW-000；可与 AXW-003 并行

**目标用户结果：** “吸收开源能力”成为可审计的实际复用，而不是项目名清单和 Star 数量。

**实施：**

1. 导入/映射 369 research pool、101 registry、57 curated、8 historical implemented；
2. canonical URL 去重，旧 ID 用 `superseded_by` 保留；
3. 实现 `UpstreamCandidateV2` 与 `ReuseDecisionRecord` schema；
4. 状态统一为 discovered→researched→license-approved→selected→integrated→installed-verified→released；
5. 只为 v0.5.1–v0.8 激活候选补齐 exact revision/license/component/fixture/upgrade/rollback；
6. 其余 Agent/Memory/Workflow 候选标 `deferred-v2`，不删除；
7. 增加 duplicate URL、unknown license、missing revision、released-without-installed-evidence 门禁；
8. 对模型、字体、图标、二进制和 fixture 建独立许可字段。

**验收：**

- 四组历史数字各自可追溯且不混算；
- MarkItDown、PDF.js、Docling、OCR、Markdown/YAML、editor、JSON Canvas 候选有完整 RDR；
- GPL/AGPL/custom license 无未决核心打包；
- `released` 条目都有 Release SHA/installer evidence；
- Registry 变更不会自动提升 capability claim。

---

### AXW-003｜选择性 CI、聚合门禁与 Release Evidence 修复

**Horizon：** H0 / Quality
**优先级：** P0
**依赖：** AXW-000

**目标用户结果：** 产品任务不再被无条件重型门禁拖慢，同时 Release 不会把轻量成功误判为完整资格。

**实施：**

1. 审计当前 classifier/GatePlan 与 aggregator 的 Gate ID 是否一一对应；
2. 对 unknown、classifier/workflow/security/schema 变化 fail-safe 到 full；
3. 普通 Python 保留主版本完整受影响 Workspace/core/knowledge/integration test groups + lint；当前 legacy job/test group 名只在 Gate Registry 映射，不进入产品术语；
4. UI 增 browser，Windows runtime 境内 smoke，Tauri/installer 增对应 desktop profile；
5. parser/dependency/lock 变化必须增 bundled/installed-format gate；
6. nightly/manual/RC 跑 full；
7. Release 只接受 exact SHA/tree 的 `full-qualification` attestation，拒绝 main-bind/selective run；
8. 修正任何 `py-primary`/`test` 等标识漂移；
9. 增 concurrency/cancel-in-progress；
10. tree evidence 复用只在 commit tree + workflow/policy/profile/lock 全相同且 gate deterministic 时启用；desktop flake 稳定前不复用；
11. 将静态字符串 meta-tests 改为 classifier truth table 和 required/not-required 语义测试。

**验收：**

- 故意使主 Python Gate 失败时 aggregator 必失败；
- docs-only 不触发 installer；UI 触发 browser；lock/parser 触发 installed format；unknown 触发 full；
- lightweight main run 永远不能放行 Release；
- 正式 Release evidence 包含 workflow/policy/lock/profile/job conclusions；
- 记录 PR P50/P95、runner minutes、flake rate、重复率，并以不降低逃逸缺陷率为约束。

**非目标：** 引入 WORK-LAB runtime 或产品 UI；项目可输出中立版本化验证合同供外部消费，但自身必须 standalone。

---

### AXW-004｜Naming、Authority、Reference 与 Truth-Drift Contract

**Horizon：** H0 / Product Governance
**优先级：** P0
**粒度：** Program Card；只执行 AXW-004A–F 中一个明确 child
**依赖：** AXW-000、AXW-001A；每个 child 独立 branch/PR

**目标用户结果：** 产品名、定位、历史别名、文档权威、引用、索引、云端/本地仓库目标都有唯一答案；以后任务和模型无法把项目重新带回 Cognitive/Agent/WORK-LAB 路线。

**实施：**

1. 创建 `docs/truth/product-truth.v3.yaml`、Positioning/Naming/Evidence/Authority contracts；
2. 创建 Historical Alias Index 和 Reference Index；
3. 给 current/research/deferred/legacy 文档补 authority metadata 和 discovery policy；
4. 建 canonical ID prefix、citation、index 命名合同；
5. 记录 current remote `DTALEX66/Cognitive-Loop-OS` 与 proposed target `DTALEX66/ArcheAxis-Workspace`；
6. 记录 local checkout canonical basename `ArcheAxis-Workspace`；实际 parent path 只写 BaselineEvidence/bootstrap，并先探测真实 checkout，绝不移动/删除；
7. 建 `product_truth_digest` 并让 AGENTS/plan/evidence/release identity 引用；
8. 实现 Truth-Drift Gate 17 类检查；
9. README 明确许可证真实状态：若仓库没有有效 LICENSE，先标“license not yet declared”，不能自行猜测；Owner 决定后再声明；
10. 对 CORS/Auth/portable env/CLI/bundle/data root 记录 current→target 迁移，不在本包 bulk rename。

**验收：**

- current 用户表面只出现 canonical product/display/category；
- legacy terms 只能在 alias/history/migration；
- 每个 authority domain 一个 canonical，无 orphan/循环；
- 直接从 Source/GeneratedArtifact 写外部事实 Evidence 的 contract test 失败；模型输出仅可作为自身行为的可复现 provenance；
- 修改 truth 使旧 TaskPack stale，并触发 truth gate + lint + Product Owner review；若同时改变运行时 Evidence/Promotion/Capability/Release schema，再追加受影响矩阵或 full；
- 任意本机绝对路径进入 runtime/通用文档时 gate 失败；
- 本包不改变远端仓库名、本地目录、bundle id 或数据根。

---

### AXW-005｜安全配置、许可证与签名真相

**Horizon：** H0/H5
**优先级：** P1；安全缺陷发现时提升 P0
**粒度：** Program Card；只执行 AXW-005A/B/C child
**依赖：** AXW-000、AXW-004A

**目标用户结果：** 本地模式安全默认清晰，生产/远程模式不会误用开放 CORS/无认证/弱密钥，AI Skill 和外部来源有一致权限边界；用户知道发行许可与签名状态。

**实施：**

1. 在最新 tree 复验 development/local/test/production 的 auth、CORS、weak-secret、loopback 行为，不能只引用旧文档；
2. 审计 `TOOL_RISK`/权限 registry 的 coverage、unknown tool fail-closed、declared-vs-actual tool mismatch；
3. 在 005A 定义统一 `PermissionDecision(actor, action, resource, workspace, scope, sensitivity, risk, decision, reason)`，由 import/network/model/AI Skill/optional execution 复用；
4. 将 AI Skill 的 permissions/side effects/approval/rollback 纳入同一安全模型；
5. 外部网页/论坛/文件引入 SSRF、path、prompt-injection、credential/log redaction 合同；
6. 明确仓库代码许可证：如果缺有效 LICENSE，Owner 必须选择；在此之前 README 只能写未声明，不能推定开源许可；
7. 记录第三方 NOTICE/SBOM 和 portable binary build flags；
8. 为 code signing 制定决策：证书/identity/secret custody/timestamp/revocation/unsigned fallback；未实施时 Release 明示 unsigned；
9. 增 production example config，但 local desktop 不被迫开启无意义的远程认证。

**验收：** production 开放 CORS/无认证/弱 secret fail closed；unknown/high/critical tool/skill 不会自动运行；日志无正文/secret；LICENSE/README/metadata 一致；签名状态与下载资产可验证且不虚假声明。

---

### AXW-010｜Capability Truth 与安装环境探针

**Horizon：** H0
**优先级：** P0
**依赖：** AXW-001A、AXW-003、AXW-004A

**目标用户结果：** UI 在用户选择文件前就能准确说明什么可用、缺什么、如何修复，不再“上传后才报未知错误”。

**实施：**

1. 定义 `CapabilityStatus`：detected/dependency-ready/source-verified/bundled-verified/installed-verified/released；
2. 探针同时检查 Python module、external binary、model/language pack、版本、可执行最小样本；
3. 将格式声明从扩展名列表改为 format × profile × environment；
4. API 返回 machine code、用户信息、remediation、engine/version；
5. Import dialog 预检并选择 profile/降级，不以 422 原文直接暴露；
6. README/manifest/UI 只显示 released 或明确 preview。

**验收：**

- 干净安装环境中的真实能力与 UI 声明一致；
- 移除 PDF extra/OCR binary/model 时探针失败且提供正确修复；
- 不运行重量模型即可完成轻量 capability check；
- capability 结果绑定 build/lock/bundle hash。

---

### AXW-011｜真实多格式 Fixture Corpus 与语义 Oracle

**Horizon：** H0 / Quality
**优先级：** P0
**粒度：** Program Card；只执行 AXW-011A/B/C/D child
**依赖：** AXW-002A；各 fixture child 只依赖对应当前 RDR，不等待 AXW-002B 历史回填

**目标用户结果：** 格式支持由真实资料和语义结果证明，不再由空文件、伪扩展名或 mock 证明。

**Fixture 最小集：**

- PDF：普通中文/英文、双栏、表格、图片、扫描、加密、损坏、空白、大文件；
- DOCX：标题/表格/图片/脚注；PPTX：slides/notes/table/image；XLSX：multi-sheet/formula/merged cells；
- 图片：中英、旋转、低对比、表格；
- HTML：静态、编码、正文噪声；
- Vault：YAML 类型、links/embeds/block refs/attachments/tags/callouts/rename/delete；
- JSON Canvas：全 node/edge 类型、颜色、坐标、未知字段；
- media 后置：多语言、噪声、长音频。

**实施：**

1. 只使用自建、公共领域或许可明确 fixture；
2. 每项记录来源/许可/hash/预期语义；
3. oracle 验证页数、结构、文本 sentinel、表/图片数量、锚点、loss、roundtrip，不锁死非确定性全字符串；
4. corpus 分 tiny PR、installed smoke、nightly full 三档；
5. 失败产出最小 diff 和 artifact，不上传私人内容。

**验收：** 所有 advertised format 至少有一个正向、一个降级、一个失败 fixture；Release 运行真实 installed subset。

---

### AXW-012｜v0.5.1 安装版 PDF 生存闭环

**Horizon：** H0
**优先级：** P0 / 首个产品修复
**依赖：** AXW-003、AXW-002A、AXW-010、AXW-011A

**目标用户结果：** 安装 0.5.1 后，普通真实 PDF 可以导入和打开；异常 PDF 给出具体原因。

**Reuse Decision：** MarkItDown format extras + pypdf 类轻量探针；不在本包同时引入 Docling/OCR 重栈。

**实施：**

1. 把 PDF/必要 Office extras 同步到 `pyproject`、lock、requirements/export、wheel、bundled Python、installer；
2. 建 `/capabilities` PDF 执行探针；
3. 检测 mime/signature、encryption、damage、scanned/no-text；
4. 原件先安全保存并记录 hash，再转换；
5. 空提取不能返回 success；按 `encrypted`、`scanned-needs-ocr`、`corrupt`、`dependency-missing`、`unsupported` 分类；
6. UI 用用户可理解错误和行动；
7. 干净 Windows 安装器完成 import→convert→open→restart readback；
8. Release manifest/README 只声明本包真实验证的 PDF profile。

**验收：**

- 普通中英文 PDF 非空提取、页数合理、原件可开；
- 加密/扫描/损坏各自得到正确 code；
- wheel 和 installer 中依赖真实存在；
- 源码环境通过但安装版失败时 Release 必须阻断；
- exact-SHA installer 下载后哈希回读一致。

**非目标：** OCR、复杂表格/公式、完整 PDF annotation；这些进入 v0.6/v0.7。

---

### AXW-015｜Durable Internal Operations Foundation

**Horizon：** H0–H1 / cross-cutting
**优先级：** P1；只在首个消费者前完成对应 child
**粒度：** Program Card；一次只执行 AXW-015A/B/C/D 中一个 child
**依赖：** AXW-003、AXW-005A；不成为用户一级导航

**目标用户结果：** 导入、转换、索引、同步和受控执行共用一套可恢复的命令/任务/事件语义；用户看到的是稳定进度、取消、重试和恢复，而不是每个模块各造一套 Job。

**Children：**

- `015A`：Command envelope、API error、idempotency key、revision/conflict；
- `015B`：Job/lease/checkpoint/cancel/retry/recover/compensate；
- `015C`：Event/Transactional Outbox/SSE、提交顺序与重放；
- `015D`：request/command/job/correlation IDs、diagnostics、redaction、retention。

**验收：** crash/restart、重复 command、lease 过期、cancel、retry、outbox replay、revision conflict 均有确定结果；correlation 可从 UI 状态追到脱敏诊断；AXW-021/094/098 只引用这些 contract，不复制 import-only/sync-only/execution-only 第二套基础设施。

---

### AXW-020｜RawAsset、Conversion 与 Evidence 核心合同

**Horizon：** H1
**优先级：** P0/P1
**粒度：** Program Card；只执行 AXW-020A/B/C child
**依赖：** AXW-012

**目标用户结果：** 每份资料都有可恢复原件、可解释转换、可追踪派生和稳定来源。

**实施：**

1. 建 SourceConnection、RawAsset、ImportBatch/Item、ConversionRun、DerivedDocument/Block、LossReport、EvidenceAnchor、IndexRevision；
2. 定义 content hash、source identity、revision、provenance；
3. 原件与派生存储隔离，索引只保存引用；
4. EvidenceAnchor 支持 page/bbox/text range、slide、sheet/cell、time range、Markdown block/path；
5. 提供 forward migration、backup、downgrade/read compatibility；
6. 旧对象通过 migration/adapter 读取，不一次性破坏用户数据；
7. API 转向 `/sources /imports /assets /documents /annotations /search /capabilities` 产品对象。

**验收：**

- 重跑转换产生新 ConversionRun，不覆盖旧结果；
- 删除索引后可从原件/派生重建；
- 原件 hash 和 bytes 永不因转换失败变化；
- migration 中断后可恢复；
- anchor 在重启和索引重建后仍解析。

---

### AXW-021｜持久化 Import/Conversion 编排

**Horizon：** H1
**优先级：** P1
**依赖：** AXW-020A/B/C、AXW-015A/B/C/D

**目标用户结果：** 多文件/大文件导入不阻塞页面，能看到真实进度、取消、重试和失败项。

**实施：**

1. streaming upload/disk spool；
2. 持久队列和 worker lease；
3. Item 级 detected/preserved/converting/validating/indexing/ready/failed/cancelled；
4. page/file/byte based progress；
5. crash recovery、idempotency key、retry policy、cancel signal；
6. 资源预算和外部进程清理；
7. Job/Outbox/Receipt 通过 BFF 转成用户态 Import/Conversion；
8. Import Center 列表、失败过滤、重跑、更换 profile、打开原件/结果/loss。

**验收：**

- 1GB 档位使用磁盘 spool，不线性占满 RAM；
- 50 文件中 1 个失败不回滚其余成功项；
- 杀进程/重启后状态恢复；
- cancel 后外部进程和临时文件被清理；
- 重试不重复写原件或产生重复用户文档。

---

### AXW-022｜PDF.js Reader、批注与 EvidenceAnchor

**Horizon：** H1
**优先级：** P1
**依赖：** AXW-020；可与 AXW-021/030 协同

**目标用户结果：** 用户在中央工作面阅读 PDF、高亮/批注，并能从笔记永久回到原页原位置。

**Reuse Decision：** PDF.js 作为 viewer；派生文本用于搜索/AI，但不替代原件渲染。

**实施：**

1. PDF tabs、thumbnail、page jump、zoom、find、selection；
2. 选区生成 page + bbox/text range + raw hash + document revision 的 EvidenceAnchor；
3. Annotation/笔记保留 quote、context、author、timestamp；
4. 右侧 Citations/Annotations/Loss；
5. anchor resolver 处理文本层变化和 fallback；
6. restart/readback、索引重建和重新转换后的 anchor 稳定/显式 stale；
7. 键盘、屏幕阅读、缩放、小窗口验收。

**验收：** 选中第 N 页文字→建笔记→关闭→重启→点击引用回同页同区；重新转换时不能静默指错，解析失败显示 stale/relink。

---

### AXW-023｜Office、OCR、HTML Provider Matrix

**Horizon：** H2
**优先级：** P1
**粒度：** Program Card；只执行 AXW-023A/B/C/D/E child
**依赖：** AXW-020A/B/C、AXW-021、AXW-011B；各 format child 独立

**目标用户结果：** 学生、教师和研究者常见资料真正可进入、展示、搜索、引用和重启回读。

**Reuse Decision：** baseline parsers + optional Docling；Tesseract baseline/PaddleOCR optional sidecar；Trafilatura HTML。不要默认打包多套竞争重引擎。

**实施：**

1. provider contract：probe/plan/convert/validate/cancel/version/resources；
2. 同 corpus benchmark 质量、速度、内存、安装体积和 loss；
3. DOCX/PPTX/XLSX/CSV/Image/HTML 各自 DerivedBlock 和 EvidenceAnchor；
4. OCR word/line/block+bbox+confidence；
5. UI 结构视图、sheet/slide/image/text 切换和原件打开；
6. profile 路由：light/rich/OCR，不可用时明确降级；
7. bundled/installed matrix 与 capability manifest 自动一致。

**验收：** 每种格式通过真实 source + wheel + Windows installer；表/图片/slide/cell 锚点可回读；LossReport 反映未保留内容；引擎移除时 capability 自动降级。

---

### AXW-024｜Evidence Core 与多源交叉验证

**Horizon：** H1/H4
**优先级：** P0/P1（产品定位核心）
**粒度：** Program Card；只执行 AXW-024A/B/C/D child
**依赖：** AXW-020A/C；024A/B 只需对象/Anchor，024C UI 再依赖 AXW-030

**目标用户结果：** 用户可以把官方网站、百科、论坛、期刊、个人文件等不同来源围绕同一主张进行对比；只有完成来源、矛盾、时效和适用范围核验后，内容才显示为 Evidence。

**实施：**

1. 实现 SourceRecord、ExtractedClaim、EvidenceCandidate、CrossValidationRecord、CorroboratedEvidence、EvidenceBundle、VerificationAssessment；
2. SourceRecord 记录作者/组织、类型、日期/版本、URL/path、content hash、抓取/导入方式和引用许可；
3. Claim 有 canonical text、scope、time/jurisdiction、claim type、revision；
4. Candidate 关系为 supports/refutes/qualifies/unclear，绑定 EvidenceAnchor；
5. 记录来源独立性、转述链、权威性、研究限制、时效和 conflicts；
6. 实现 risk-adaptive promotion policy；论坛/百科不能单独直升；AI 输出只能记录为 GeneratedArtifact/behavior evidence，不能独立佐证外部事实；
7. Evidence compare UI：并排来源、差异、矛盾、未解决问题和人工裁决；
8. 自动检索/模型只能提出来源与关系候选；
9. 修正所有从 Source/Claim 直接写 Evidence 的 legacy path；
10. Evidence revision、expiry、supersession、retraction 和 audit trail。

**验收：**

- 单一普通网页只能停在 EvidenceCandidate；
- 两个看似不同但实际同源转载不能算独立佐证；
- 官方资料只在其声明范围内成立，效果/因果仍需外部来源；
- 支持与反证同时存在时 UI 不隐藏冲突；
- AI 输出可登记 GeneratedArtifact 和可复现行为 provenance，但不能登记为外部事实 Source 或独立 CorroboratedEvidence；
- 任何 Evidence 点击都能回原页/段/单元格/时间点；
- restart/export 后 validation history 不丢；
- 高风险主题默认要求人工审查。

**非目标：** 自动判断世界真相、用简单来源分数替代研究方法、抓取全网。

---

### AXW-025｜早期 Human Learning Proof Slice

**Horizon：** H1/H2；不等待 Obsidian C4
**优先级：** P0（验证核心承诺）
**依赖：** AXW-011A、AXW-022、AXW-024A/B

**目标用户结果：** 用一个小而真实的学习主题证明“资料→交叉核验→主动学习→可测反馈”可运行，避免先建设完整 Vault 后才发现 Human Learning 仍只有合同。

**范围：** 一个许可清楚的 PDF + 一个独立网页/参考来源；一个 Claim/EvidenceBundle；一个 LearningObjective；一组 retrieval prompts；一次即时回忆和一次延迟回忆/迁移或 Teach Back 采样。先用轻量页面/流程，不建设完整 Learning UI/FSRS/Anki。

**验收：**

- pretest、学习耗时、即时回忆、延迟回忆/迁移或 Teach Back rubric 有持久记录；
- 每个解释/练习点击回 EvidenceAnchor；
- 模型生成内容保持 candidate，人工确认后才进入学习资产；
- 重启后主题、回答和来源仍可读；
- 输出 feasibility evidence 和 AXW-051 的真实需求，不宣称已证明普遍学习提升。

---

### AXW-030｜OpenHuman-inspired Workspace Shell

**Horizon：** H1/H2 / UX
**优先级：** P1
**粒度：** Program Card；只执行 AXW-030A/B/C child
**依赖：** AXW-020 的产品对象/BFF；可与 AXW-021/022 并行

**目标用户结果：** 打开应用首先看到安静、宽阔、以真实内容为中心的工作区，而不是治理仪表盘。

**Reuse Decision：** Obsidian/VS Code 等闭源实现只作公开行为与格式参考；OpenHuman/Zotero 等 copyleft 项目在 AXW-006 顶层许可组合裁决前先 clean-room/API/格式，裁决通过后可按许可证直接吸收相应源码。任何视觉资产、Logo、字体和示例内容仍单独审查。

**实施：**

1. 新 AppShell：top bar、left Library、center tab work surface、right context、conditional bottom activity；
2. 一级路由固定为 Workspace/Library/Evidence/Learning/AI Assets/Settings；Search 在顶栏，Canvas/Graph/Learning Map 为中央视图；
3. 把 Runtime/Delivery/Audit/Machine/Evolution 移 Advanced；
4. 实现 responsive pane sizing、collapse、keyboard focus、theme tokens；
5. 初始页为 Continue Reading/Recent Edit/Import/Needs Attention；
6. central host 可挂 Markdown/PDF/Office/Canvas，不以聊天为默认；
7. browser smoke 覆盖核心布局、窄屏、console errors。

**验收：**

- 1280×720 时中央区仍为最大有效区域；
- pane 可折叠/恢复，焦点顺序正确；
- 无死导航/占位搜索；
- Import failure 能从底部条进入对应 Item；
- independent component/CSS provenance 证明无 OpenHuman 源码复制。

---

### AXW-040｜Vault Kernel C0/C1：安全发现与稳定身份

**Horizon：** H3
**优先级：** P0/P1
**依赖：** AXW-020、002

**目标用户结果：** 用户可只读连接现有 Vault，完整看到目录、Markdown、附件和 Canvas，不被限定在预设中文目录。

**实施：**

1. 新 `vault-core`，隔离/禁用 legacy importer apply；
2. ApprovedRoot、realpath/symlink containment、ignore rules、`.obsidian` 边界；
3. stable file identity：vault + normalized relative path + content hash + revision；
4. 全量首扫 + hash/mtime/size cursor 增量；
5. rename/delete 检测基础；
6. Markdown/attachment/Canvas inventory；
7. 不截断正文，不生成随机用户对象 identity，不自动晋升知识；
8. fixture Vault only first；真实 Vault 默认只读、显式授权。

**验收：** 重复扫描幂等；rename 被识别而非 delete+duplicate；symlink/path traversal 不越界；未知文件不丢且标 unsupported；零写入真实 Vault。

---

### AXW-041｜Markdown/YAML/Links 保真内核

**Horizon：** H3
**优先级：** P1
**依赖：** AXW-040

**目标用户结果：** 原有笔记的正文、属性、链接、嵌入、标签和块引用都能正确读取，未知结构不被吃掉。

**Reuse Decision：** 成熟 CommonMark/GFM AST + roundtrip YAML；禁止手写 frontmatter/links 子集。

**实施：**

1. parser bake-off 并锁定一个 AST/YAML 组合；
2. 保留 YAML scalar/list/map/null/date/bool/number、顺序和未知字段；
3. headings、wikilinks、Markdown links、embeds、block IDs、callouts、tags；
4. 建 path/heading/block/link index；
5. links 与 stable identity 对齐，rename 计划可计算；
6. unsupported/ambiguous syntax 进入 Loss/Compatibility report；
7. golden AST/semantic snapshots。

**验收：** fixture semantic roundtrip；重复 import 幂等；未知 property 不丢；link target 正确解析路径/heading/block；不把 note name 与随机 DB ID 混用。

---

### AXW-042｜Vault Workbench C2

**Horizon：** H3
**优先级：** P1
**依赖：** AXW-030、040、041、022

**目标用户结果：** 用户可把 ArcheAxis 当成日常 Vault 工作台：浏览、阅读、编辑草稿、搜索、查看属性/反链/附件。

**实施：**

1. 虚拟滚动 file tree、folders、collections、tags、saved search；
2. Markdown editor/preview、tabs、dirty state、history；
3. Properties editor；
4. links/backlinks/embeds/attachment preview；
5. FTS5 filename/path/property/fulltext search；
6. current-note outline/local graph；
7. PDF/Office attachments 在同一 central work surface；
8. 初期写入 fixture/working copy，真实 Vault 写入等 AXW-044。

**验收：** 10k/50k note 档位无全量 DOM；search→open→backlink→attachment；重启恢复 tabs/selection；搜索输入不再 readonly/placeholder。

---

### AXW-043｜JSON Canvas 保真读写

**Horizon：** H3
**优先级：** P1
**依赖：** AXW-040、030；可与 041 parser 工作并行

**目标用户结果：** 用户能打开和编辑现有 Obsidian Canvas，节点、边、位置、尺寸、颜色和未知扩展不丢。

**实施：**

1. 独立 JSON Canvas domain model/parser/serializer；
2. text/file/link/group nodes、edges/end markers/labels；
3. precise geometry/color；
4. unknown field preservation；
5. file node 与 Vault identity/attachments 关联；
6. interaction layer 与文件模型隔离；
7. semantic diff/golden fixtures；
8. 暂不承诺 Excalidraw/plugin Canvas。

**验收：** open→move/edit/add edge→save→independent parser/Obsidian reopen；未编辑未知字段 byte/semantic preservation 达到声明；内部旧 Canvas 需显式 migration，不冒充兼容。

---

### AXW-044｜C3 安全写入、Revision、Conflict 与 Rollback

**Horizon：** H3
**优先级：** P0/P1（数据安全）
**依赖：** AXW-041、042、043

**目标用户结果：** ArcheAxis 可以写真实 Vault，但永远不静默覆盖用户在外部应用中的修改。

**实施：**

1. save plan/dry-run 显示 targets/diff；
2. expected hash/revision；
3. temp file + fsync + atomic replace；
4. pre-write backup 和 revision journal；
5. external modification watcher；
6. conflict UI：reload/compare/save copy/merge/cancel；
7. rename/delete/link update transaction plan；
8. crash injection、disk full、permission denied、locked file；
9. rollback API/UI 和 recovery on startup；
10. SafeWriter 统一用于 Vault projection，不直接 `write_text` 覆盖。

**验收：** 外部在保存前修改同一文件→写入被拒绝并形成冲突；kill 在各阶段→原件为旧版或完整新版，无半文件；rollback 恢复正文/属性/Canvas/links；Windows locked file 有明确错误。

---

### AXW-045｜Obsidian C4 安装版往返资格

**Horizon：** H3
**优先级：** P0 Release Gate
**依赖：** AXW-040–044、AXW-003、AXW-011C

**目标用户结果：** 同一 Vault 可在 Obsidian 与 ArcheAxis 之间交替工作，关键语义和资产可靠保留。

**实施/测试流：**

```text
fixture Vault baseline hash/semantic snapshot
→ Obsidian/independent writer A 修改
→ ArcheAxis installed import/open/edit/properties/links/Canvas
→ save/close/restart
→ independent parser semantic diff
→ Obsidian readback B 修改
→ ArcheAxis incremental detect/conflict/resolve
→ export/copy Vault
→ rollback proof
```

**验收：**

- Markdown/YAML/link/embed/attachment/Canvas 语义矩阵达到声明阈值；
- 未支持语义有显式 loss，不静默删；
- rename/delete/backlink 更新一致；
- real Windows installer exact-SHA；
- capability 从 C3 升 C4 只由该资格包签发；
- UI/README 不宣称社区插件全面兼容。

---

### AXW-050｜Evidence-bound Cited AI

**Horizon：** H4
**优先级：** P1
**依赖：** AXW-020C、AXW-022、AXW-024A/B、AXW-030A/B；不等待 Obsidian C4

**目标用户结果：** 用户对选定资料提问，回答逐条有来源并能点回原文；无证据时明确拒答或标不确定。

**实施：**

1. Provider-neutral contract，本地/云端显式选择；
2. scope 只能来自用户选定 Source/Document/EvidenceBundle/Collection；
3. deterministic retrieval 先行，向量为可选派生；
4. citation 对应 EvidenceAnchor，不只显示文件名；
5. 区分 source quote、model inference、generated draft；
6. feedback/correction 与 session persistence；
7. prompt injection、数据出机、credential、日志最小化；
8. 无 citation 的 claim 不能进入 reviewed knowledge；回答中的模型文字永远不是 Evidence；
9. 当 EvidenceBundle 有反证/未解决冲突时，回答必须显示而非平均抹平。

**验收：** citation precision/recall 基准；点击回页/slide/cell/block；重启 session/引用可读；断网仍可完成非 AI 核心；禁用云模型时无资料出机。

---

### AXW-051｜Human Learning Core、FSRS 与 Teach Back

**Horizon：** H4
**优先级：** P1/P2
**粒度：** Program Card；只执行 AXW-051A/B/C/D child
**依赖：** AXW-024A/B、AXW-025、EvidenceAnchor；不依赖 Cited AI

**目标用户结果：** 用户围绕一个 EvidenceBundle 完成理解、主动回忆、练习、延迟复习、迁移和 Teach Back；系统用真实学习表现而不是页面点击证明“学得更深”。

**Reuse Decision：** py-fsrs 作为调度候选；Anki 只做交换/API，不复制客户端核心。

**实施：**

1. EvidenceBundle→LearningObjective/Concept/Explanation/Example/Counterexample candidate；
2. annotation/note→candidate exercise/card→human reviewed asset；
3. Q/A、cloze、concept、evidence、retrieval practice、transfer task；
4. TeachBackSubmission + rubric + human/model candidate assessment；
5. MasterySignal 区分 seen/self-report/retrieval/delayed/transfer/teach-back；
6. FSRS history、timezone、deterministic replay、migration；
7. due query 按 card 真实历史计算，修复跨卡最新 review 污染；
8. 新卡自然进入队列；
9. source confidence、knowledge confidence、learner mastery 分离；
10. v0.9 只做基础 CSV/开放卡片导入导出和 stable internal ID；APKG/API/media/history 留给 AXW-071；
11. advanced parameters 隐藏在 preset 后；
12. 学习错误/Teach Back 只能生成 Evidence/Knowledge/AI change proposal。

**验收：** 一个真实主题完成 baseline→learning→delayed retrieval→transfer/Teach Back；多卡历史/新卡/timezone 行为正确；每项点击回来源；关闭重启 queue/mastery 不变；基础 CSV/open-card roundtrip 字段和 loss 可见；模型评分不自动提升 Mastery。

---

### AXW-052｜AI Learning Assets Core

**Horizon：** H4
**优先级：** P0/P1（产品定位核心）
**粒度：** Program Card；只执行 AXW-052A/B/C/D/E child
**依赖：** AXW-005A、AXW-024A/B、AXW-015A/B/C/D、AXW-095A/B/C；不依赖 Cited AI。`052D` 还必须消费 AXW-005A PermissionDecision，不能自建权限布尔值。

**目标用户结果：** 用户可以把经核验的知识提议为 AI Memory、Rule、Skill、Standard、Context，经评测和授权后供个人 AI 使用，并能查看、修订、过期和撤销。

**实施：**

1. AIMemoryCandidate/Revision、RuleCandidate/RuleSpec、SkillCandidate/SkillSpec、StandardSpec、ContextPack、EvaluationCase/Result；
2. 每项绑定 EvidenceBundle、scope、permissions、effective/expiry、version、dependencies、known failures；
3. promotion workflow：candidate→evaluate→conflict/freshness/security→review→approve revision；
4. Memory taint/contradiction/freshness；Rule priority/scope/conflict；Skill IO/schema/side effects/tests/rollback；
5. AI Assets Library 和详情/差异/审批/撤销 UI；
6. 受控只读或可回滚 Skill executor Adapter；通用 Planner 不在本包；
7. InvocationPlan/Receipt/OutcomeProof，引用实际使用的资产版本和证据；
8. supersede/revoke 后新调用立即停止使用旧 revision，历史回执仍可审计；
9. 导出为开放、版本化 Markdown/YAML/JSON bundle；
10. 外部规则/skill import 一律 candidate，不自动 active。

**验收：**

- 无 EvidenceBundle 的资产不能 approve；
- 过期/冲突/被撤销 Memory 不进入新 ContextPack；
- 一个低风险 Skill 通过真实输入、权限、test、invoke、OutcomeProof、rollback；
- Skill 执行成功不自动证明规则正确；
- 关闭重启后批准/撤销/版本一致；
- AI provider 可替换，资产数据模型不绑定单一模型。

---

### AXW-053｜Human ⇄ AI 受控双向转化闭环

**Horizon：** H4 / v1.0 release-driving
**优先级：** P0
**粒度：** Program Card；只执行 AXW-053A/B/C/D child
**依赖：** AXW-005A、AXW-024A/B/C/D、AXW-030A/B、AXW-051A/B/C/D、AXW-052A/B/C/D/E

**目标用户结果：** 同一份可信知识既能帮助人学习，也能帮助 AI 使用；双方反馈会互相改进，但不会绕过审核修改事实或正式资产。

**实施：**

1. 统一 `TransformationProposal`：source type、target type、evidence、rationale、diff、risk、evaluation、review；
2. Evidence→Human Asset、Evidence→AI Asset；
3. HumanLearningAsset→AIAssetCandidate，继承原 EvidenceBundle/provenance；
4. ApprovedAIAsset/Evaluation→HumanLearningAssetCandidate，继承资产 revision/evidence；
5. human misconception/mastery/Teach Back→Knowledge/AI change proposal；
6. AI evaluation/invocation outcome→Learning/Knowledge/AI change proposal；
7. Memory/Rule/Standard→Skill/Context candidate；Skill outcome/Eval→Memory/Rule/Standard revision candidate；
8. 禁止 direct activate；所有目标生成新 candidate/revision；
9. 对转换建立 provenance graph 和 bidirectional links；
10. UI 显示“由什么转来、谁审、为什么、何时撤销”；
11. exact revision export/import；
12. 建一个真实主题的端到端 installed fixture。

**验收用户流：**

```text
多源资料→EV3/EV4 EvidenceBundle
→练习/复习/Teach Back→Mastery evidence
→AI Memory + Rule + low-risk Skill proposals
→evaluation + user approval
→controlled invocation with citations/outcome
→发现错误→proposal→review→new revision/revocation
→restart/readback/export
```

任何一步缺失来源、review、version 或 rollback，v1.0 双学习 capability 不得标 released。

---

### AXW-054｜Learning Effect 与 AI Use 比较性评测

**Horizon：** H4 / v1.0 release-driving
**优先级：** P0（声明资格）
**依赖：** AXW-005A、AXW-024A/B/C/D、AXW-025、AXW-030A/B、AXW-050、AXW-051A/B/C/D、AXW-052A/B/C/D/E、AXW-053D、AXW-095A/B/C

**目标用户结果：** “人学得更深、AI 用得更准”不只证明按钮和状态能走通，而有可复现、诚实限定的对照数据。

**LearningEffectEvaluation：**

- 同一主题 pretest；
- 学习时间/完成动作；
- immediate retrieval；
- delayed retrieval；
- transfer task；
- Teach Back rubric；
- time-to-mastery、提示次数和错误类型；
- 明确样本量、用户背景、偏差和不能推广的范围。

**AIUseEvaluation：**

- 同一任务 `without approved assets` vs `with approved assets`；
- citation correctness/coverage；
- factual/claim error；
- conflict/stale/revoked memory interception；
- rule/skill scope violation；
- task success、human correction、latency/resource；
- exact model/provider/version/prompt/asset revision。

**验收与宣传边界：**

- eval fixture、输入、评分 rubric、raw results、analysis revision 可重跑；
- 失败/负结果不隐藏；
- 单用户/小样本只能证明“闭环可测”和个案结果，不能宣传普遍提升；
- 只有预注册范围内有足够数据、对照和效应时，Capability/Release notes 才能使用相应提升表述；
- 模型/资料/规则版本变化会使旧比较结果 stale。

---

### AXW-055｜人机双学习最小闭环安装资格

**Horizon：** H4 / v1.0 release-driving
**优先级：** P0 聚合资格包
**依赖：** AXW-005A、AXW-009C、AXW-015A/B/C/D、AXW-020A/B/C、AXW-021、AXW-022、AXW-024A/B/C/D、AXW-025、AXW-030A/B、AXW-050、AXW-051A/B/C/D、AXW-052A/B/C/D/E、AXW-053A/B/C/D、AXW-054、AXW-095A/B/C
**性质：** 只聚合真实用户流和证据，不在一个 PR 重新实现上述能力。

**唯一 installed Windows 用户流：**

```text
真实 PDF/资料
→ 至少两个具有独立性的来源
→ Claim + EvidenceCandidate + CrossValidationRecord
→ EvidenceBundle（包含限制/矛盾/时效）
→ HumanLearningAsset + practice + delayed/transfer + Teach Back
→ approved AI Memory + Rule + 一个低风险 Skill
→ Human→AI proposal + AI→Human proposal
→ review/approve/invoke/revoke
→ with/without approved assets 比较
→ close/restart/readback/export/reopen
```

**验收：** exact source/tree、ReleaseFreeze、installer、fixture、所有 asset revision、model/provider、rubric、UI 点击证据和结果 hash 全绑定；任一未经 review 自动晋升、引用无法回原件、撤销后仍被调用、重启丢状态或导出无法再读均失败。通过只允许声明“人机双学习最小闭环已安装验证”；比较性提升文案仍由 AXW-054 的数据边界决定。

---

### AXW-060｜v1.0 稳定性、安装、迁移与开放导出

**Horizon：** H5
**优先级：** P0 Release
**依赖：** AXW-055、AXW-045、AXW-009D、AXW-094A/B、AXW-003 full-attestation；AXW-009C 是 AXW-055 与 AXW-009D 的共同前置，二者之间无依赖；其他长期 Program 仅在对应 capability 被显式设为 `required_current=true` 时进入本 Release

**目标用户结果：** 普通用户可以长期使用、升级、备份、卸载和迁移 ArcheAxis，而不理解内部 Runtime。

**实施：**

1. 10k/50k notes、GB 级 assets、large PDF 性能档位；
2. accessibility、keyboard、screen reader、contrast、zoom、小窗口；
3. low-memory/no-GPU profile；
4. 对 AXW-094A/B 已实现的 exchange/backup/restore 做大库、迁移和安装版聚合资格；本包不重复实现第二套备份/恢复；
5. installer upgrade/repair/uninstall，用户数据默认保留；
6. 对 AXW-094A 的 open export（原件、Markdown、attachments、Canvas、annotations/evidence sidecar、CSV/JSON）做兼容、重启和回读资格；本包不另建导出格式；
7. exact-SHA full qualification、installer/assets/download hash readback；
8. 仓库/包/协议/数据目录重命名另做迁移演练和兼容 redirect；
9. Release notes 由 Capability Matrix 自动生成，preview/unsupported 清晰。

**验收：** clean install + upgrade from supported version + restart + core flow + uninstall/reinstall readback；无 P0 数据丢失；Release identity 指向正确 full CI 而非 Release workflow 自身。

---

### AXW-080｜云端仓库改名（Owner Action）

**Horizon：** H5 / v1.0 RC
**优先级：** P1，非当前 P0
**依赖：** AXW-004、active PR 收口、full qualification 绿色

**目标：** preflight 确认 proposed 名称 `DTALEX66/ArcheAxis-Workspace` 可用且不会破坏集成后，由 Owner 将其晋升为 canonical remote 并执行迁移，保留 GitHub redirect 和历史身份。

**执行边界：** GitHub rename 必须由有权限的 Owner 明确批准/执行；Codex 先做只读 preflight 和回滚说明。

**验收：** old URL redirect；new clone/fetch/push；Actions、branch protection、secrets/environment、pages/packages、badges、issues/PR、Release assets 和 source links 正常；旧 tag/Release 不改写；所有当前 metadata 使用新 URL。

---

### AXW-081｜本地 checkout 目录迁移

**Horizon：** H5 / developer migration
**优先级：** P1/P2
**依赖：** AXW-080；用户明确授权

**目标：** 本地 checkout basename 统一为 `ArcheAxis-Workspace`；Windows/macOS/Linux parent path 均由用户选择并只进入 machine BaselineEvidence/bootstrap。

**安全协议：** 先探测 current path、remote、worktree、untracked、running process；若新旧目录并存、worktree dirty 或进程占用，fail closed 并请用户选择。不得自动删除、覆盖、合并或重复 clone。路径不进入 runtime。

**验收：** remote 正确、commit/tree 不变、untracked/user changes 全保留、dev bootstrap/IDE/tasks 可运行、旧目录按用户决定保留或手工归档。

---

### AXW-082｜Package、CLI、Bundle ID、协议与数据根迁移

**Horizon：** H5 / 独立兼容 Release
**优先级：** P1
**依赖：** AXW-060、080；不能与 repo/local rename 混包

**目标：** 完成 `archeaxis-workspace` distribution、`archeaxis_workspace` import facade、`archeaxis` CLI、`ARCHEAXIS_` env/config namespace、public API compatibility facade、`com.archeaxis.workspace` bundle ID、`archeaxis://`、Windows target data root 与 portable root 的安全迁移。

**实施：** current inventory→alias layer→backup→transaction migration→dual read→readback→rollback→deprecation telemetry/documentation；旧 alias 至少保留两个稳定版本。

**验收：** old install/data/CLI/env/protocol 可升级；new install 不建两套事实库；portable 与 installed 隔离；rollback 回旧版可读；卸载不删用户数据；签名/更新通道/bundle identity 重新资格。

---

### AXW-070｜Adapter SDK 与 Zotero 第一纵切

**Horizon：** H6
**优先级：** P1/P2
**依赖：** AXW-060、AXW-002C

**目标用户结果：** 研究者可导入 Zotero 文献、附件和批注，并保持 citation identity 和来源。

**实施：**

1. Adapter contract：discover/probe/authorize/plan/import/export/incremental/delete/loss/cancel；
2. 网络、凭据、rate limit、cursor、offline cache；
3. 最小纵切优先 Zotero API/BibTeX/CSL JSON/export；若 AXW-006 的顶层许可组合与 exact-revision RDR 通过，可在独立包依法复用/修改对应客户端源码；
4. attachment linking/copy policy；
5. citation key/revision/EvidenceAnchor；
6. 100+ item fixture/authorized test account（不提交私人数据）；
7. 独立 capability 和 kill switch。

**验收：** initial + incremental + rename/delete + annotations + attachment + export/readback；断网/撤权可恢复；卸载 Adapter 不破坏已导入原件。

---

### AXW-071～075｜后续生态 Adapter

按一个 Adapter 一个 TaskPack/PR/Release 执行：

| ID | Adapter | 核心合同 |
|---|---|---|
| AXW-071 | Anki | 完整 APKG/API、cards/decks/media/stable ID/history loss |
| AXW-072 | Joplin | JEX/Markdown/resources/tags/notebooks |
| AXW-073 | Logseq | Markdown/EDN/pages/blocks/refs/properties |
| AXW-074 | SiYuan | API/export/blocks/resources/refs |
| AXW-075 | Readwise | OAuth/API/highlights/cursor/delete/rate-limit |

任何闭源 PKM（Tana/Roam/Heptabase/Capacities/Notion）只有在公开 API/导出和用户需求明确时新增独立卡，不承诺源码吸收。

---

## 14. Authority、Reference、Citation 与 Index Contract

### 14.1 唯一文档拓扑

```text
README.md                         # public projection；不独自定义路线
AGENTS.md                         # Codex executor projection；只引用 truth

docs/INDEX.md                     # 唯一文档入口

docs/truth/
  product-truth.v3.yaml           # exact strings/IDs/core/non-goals/horizons
  PRODUCT_POSITIONING_V3.md       # 产品语义权威
  NAMING_CONTRACT_V3.md
  AUTHORITY_REFERENCE_CONTRACT_V1.md
  EVIDENCE_POLICY_V1.md
  HISTORICAL_ALIAS_INDEX_V1.yaml
  REFERENCE_INDEX_V1.yaml

docs/current/
  FUTURE_MASTER_BLUEPRINT_V2.md
  CURRENT_PRODUCT_PLAN.md
  CAPABILITY_MATRIX.md
  UPSTREAM_LEDGER.md
  RELEASE_QUALIFICATION.md

docs/decisions/                   # approved ADR；不高于 truth
docs/evidence/                    # SHA/run/artifact frozen evidence
docs/research/                    # 无执行权
docs/deferred/                    # 无当前执行权
docs/legacy/                      # 历史只读，默认不发现
```

README 只投影当前事实；不能通过改 README 单方面改定位。AGENTS 只能告诉 Codex 去哪里读取当前 truth，不重复维护一份易漂移长蓝图。

### 14.2 两条权威轴

**规范轴——决定应该做什么：**

```text
PRODUCT_POSITIONING_V3
→ Naming / Evidence / Authority contracts
→ FUTURE_MASTER_BLUEPRINT_V2
→ CURRENT_PRODUCT_PLAN
→ Atomic TaskPack
→ ADR / technical specification
```

**事实轴——决定是否真的拥有：**

```text
installed exact-SHA evidence
→ reproducible current-main behavior
→ capability evidence registry
→ CAPABILITY_MATRIX projection
→ README / UI / Release claim
```

规范不能把计划写成 available；事实轴发现安装失败时必须覆盖宣传文字。Issue、PR、TaskPack、模型摘要、外部审计不能反向修改 Product Positioning。

### 14.3 文档元数据

所有当前和历史 Markdown 顶部必须包含：

```yaml
doc_id: DOC-...
title: ...
authority_class: canonical|active_plan|decision|evidence|research|deferred|historical|superseded|external_reference
product_truth_version: 3
status: draft|active|frozen|retired
effective_at: ISO-8601
supersedes: []
superseded_by: []
agent_discovery: allow|deny
scope: []
source_commit: ...
```

规则：

- research/deferred/historical/superseded 默认 `agent_discovery: deny`；
- 每个 authority domain 恰有一个 canonical；
- supersedes 图无环，引用目标存在；
- evidence 文档 immutable/frozen，新证据生成新 revision；
- current plan 必须引用 product truth digest；
- 本机绝对路径、临时 branch/SHA 不得写入长期 canonical 文档，除非明确 machine/evidence 字段。

### 14.4 Reference Index

`REFERENCE_INDEX_V1.yaml` 为所有文档和外部研究的唯一索引。每项至少包含：

```text
reference_id
title
path_or_url
type
authority_class
current_revision_or_retrieved_at
license_if_external
scope
supersedes/superseded_by
allowed_for_agent_discovery
claims_or_decisions_supported
```

内部链接优先 repo-relative path；GitHub 事实引用 canonical repository URL + commit/blob/tree/PR/run；Library 资料使用稳定 library_file_id，仅在内部证据元数据保存，不暴露为产品运行时依赖。

### 14.5 稳定对象 ID

| 前缀 | 对象 |
|---|---|
| `SRC-` | SourceRecord |
| `AST-` | RawAsset |
| `ANC-` | EvidenceAnchor/SourceAnchor |
| `CLM-` | ExtractedClaim/Claim revision |
| `EVC-` | EvidenceCandidate |
| `XVR-` | CrossValidationRecord |
| `EVB-` | EvidenceBundle |
| `KNW-` | VerifiedKnowledge revision |
| `HLA-` | HumanLearningAsset |
| `LRN-` | Learning session/event |
| `MST-` | MasteryAssessment |
| `AIM-` | AI Memory revision |
| `RUL-` | AI Rule revision |
| `SKL-` | AI Skill revision |
| `STD-` | AI Standard revision |
| `CTX-` | ContextPack |
| `EVA-` | Evaluation case/result |
| `TRP-` | TransformationProposal |
| `INV-` | Invocation/OutcomeProof |
| `REV-` | General revision/conflict record |
| `IMP-` | ImportBatch/Item |
| `CVR-` | ConversionRun |
| `IDX-` | IndexRevision |
| `CAP-` | Capability |
| `UPR-` | Upstream candidate/decision |

ID 是稳定身份，不携带用户文件名、绝对路径或可变状态。用户界面默认显示名称和来源；诊断/导出显示 ID。

### 14.6 引用合同

引用不是把 `[reference:21]` 或文件名硬写进正文。Canonical Citation 至少包含：

```text
citation_id
claim_id/evidence_bundle_id
source_record_id
anchor_id
source_revision/hash
quote_or_summary
retrieved_at/effective_at
citation_style metadata
license/quotation boundary
resolution_status
```

- 产品内引用存关系；Markdown 导出可生成稳定脚注 `[^axw-...]`；
- 学术资料可投影 BibTeX/CSL JSON；
- 网页引用保留 snapshot/hash/time；
- 论坛引用保留 thread/post identity、时间和编辑状态；
- 引文不是证据晋升，必须经过 Evidence Policy；
- 来源变更、撤稿或失效时 citation 标 stale/retracted，不静默重指向。

### 14.7 索引合同

原件、Evidence、知识和学习资产本身不是索引。以下全部为派生、可重建对象：

| Index | 内容 | 事实源 |
|---|---|---|
| Source Index | filename/path/URL/metadata | SourceRecord/RawAsset |
| Document Index | text/block/page/slide/cell/time | DerivedDocument/Block |
| Evidence Index | Claim→candidate/evidence/conflict | Evidence Core |
| Knowledge Index | reviewed knowledge/relations | Knowledge revisions |
| Human Learning Index | objective/exercise/review/mastery | Human Learning events |
| AI Asset Index | Memory/Rule/Skill/Standard/Context/Eval | approved AI asset revisions |
| Link/Graph Index | links/backlinks/relations | files + canonical relations |
| Capability Index | environment/profile/state/evidence | capability registry |
| Upstream Index | candidate/revision/license/status | Upstream Ledger |

FTS、vector、graph cache 均带 `IndexRevision`、schema/engine/source watermark。删除索引后能够重建；向量结果不能替代引用；AI Memory 不得成为第二个知识事实库。

### 14.8 Truth-Drift Gate

实现 `scripts/verify_product_truth.py`（或仓库当前语言等价物）+ schema + contract tests，至少覆盖：

1. **Exact-name：** README/UI/OpenAPI/manifest/installer/pyproject/Tauri 使用 canonical display name；
2. **Forbidden-term：** 旧 OS/Runtime/Agent 定位在当前用户表面出现即失败，history/alias/migration 白名单除外；
3. **Repository：** machine truth 同时记录 current+target；迁移后 package metadata/homepage/repo URL 一致；
4. **Local path：** 除 machine truth/bootstrap 外出现 `C:/D:/E:/` 等硬编码即失败；
5. **Single authority：** 每域一个 canonical、无 orphan、supersedes 无环；
6. **Agent discovery：** current docs 不引用 legacy/deferred 作为执行依据；
7. **Positioning checksum：** `product_truth_digest` 绑定 AGENTS、TaskPack、PR evidence、Release identity；truth 变化使旧 TaskPack stale；
8. **Core/non-goal：** 必须同时包含 Human Learning、AI Learning Assets、controlled bidirectional transformation，并明确 not Agent OS；
9. **Priority：** Visual/Simulation/Spatial 属于永久 LER Program；只能在相应 Horizon 进入 active Release required capability，不得提前阻塞 PDF/Evidence，也不得被代理从 Master Blueprint 删除或用漂亮演示冒充学习效果；
10. **Evidence semantics：** SourceRecord 不能直写 Evidence；必须有 Candidate + CrossValidation；AI output 只能作 GeneratedArtifact/自身行为 provenance，不能作外部事实 Source 或独立佐证；
11. **Promotion：** Human/AI 转换只能 proposal/candidate；无 evaluation/review/approval 不得正式化；
12. **Capability claim：** `支持/available/complete/PASS/compatible` 必须指向 CAP ID、installed fixture、UI、restart、Release evidence；metadata-only 不得冒充 OCR/ASR；
13. **Upstream：** integrated 依赖有 exact revision/license/model/assets/mode/fixture/upgrade/rollback；
14. **Plan：** 每个 active TaskPack 映射 Horizon/Program/user path；deferred 不进 current plan；
15. **Release：** identity 含 product_truth/capability/source-tree/workflow/lock/bundle/installer digest 和 installed user flow；
16. **UI IA：** 禁止 Agents/Runtime/Machine/Evolution/WORK-LAB/HERMES 一级导航；AI Assets 允许；
17. **Truth-change risk：** 纯定位/名称/别名/引用变化运行 truth gate + lint + Product Owner review；运行时 Evidence/Promotion/Capability/Release schema 变化追加受影响矩阵，高风险/unknown/RC 才 full。所有 truth 变化都使旧 TaskPack stale，但不机械运行无关 installer。

### 14.9 路线漂移硬拒绝

任何新 TaskPack 必须明确改善至少一个核心支柱：

1. Source Fidelity；
2. Evidence Integrity；
3. Deep Human Learning；
4. AI Learning Assets；
5. Controlled Bidirectional Transformation；
6. Open Interoperability；
7. Local Control/Release Reliability。

无法映射，或会在当前 Horizon 重新引入通用 Agent、重型 Runtime、无 EvidenceAnchor/学习目标/降级路径的纯视觉演示、跨项目控制面者，默认拒绝进入 active plan。符合 LER 合同并到达对应 Horizon 的视图、课件、动画、模拟和空间记忆不属于路线漂移。改变本条只能由用户/Product Owner 明确修改 Product Positioning v3，并产生新的 truth digest。

---

## 15. 开源与外部能力快速引用索引

此表是执行入口，不是许可证法律意见。每次 selected/integrated 前仍要固定 tag/commit 并重查 LICENSE、NOTICE、模型、权重、字体、图标、fixture、二进制构建选项和传递依赖。

| 项目/规范 | 官方入口 | 快照许可/边界 | 当前模式 |
|---|---|---|---|
| OpenHuman | https://github.com/tinyhumansai/openhuman | GPL-3.0 | 当前 clean-room；R-C compatibility 通过后允许 source absorption |
| JSON Canvas | https://github.com/obsidianmd/jsoncanvas | MIT | 规范直接实现 |
| Obsidian API types | https://github.com/obsidianmd/obsidian-api | MIT；不代表 Runtime 开源 | C5 独立 bridge 参考 |
| Obsidian URI | https://obsidian.md/help/Extending%2BObsidian/Obsidian%2BURI | 公开协议 | v0.8/v1.x deep-link |
| PDF.js | https://github.com/mozilla/pdf.js | Apache-2.0 | v0.6 reader dependency |
| MarkItDown | https://github.com/microsoft/markitdown | MIT | v0.5.1 baseline + extras |
| pypdf | https://github.com/py-pdf/pypdf | 常见版本 BSD-3-Clause；锁 tag | PDF probe/辅助 |
| Docling | https://github.com/docling-project/docling | code MIT；models separate | optional rich provider |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR | code Apache-2.0；models separate | optional OCR provider/sidecar |
| Tesseract | https://github.com/tesseract-ocr/tesseract | Apache-2.0 | OCR baseline CLI/provider |
| Apache Tika | https://github.com/apache/tika | Apache-2.0；组件/CVE 另审 | v1.x optional sidecar |
| Trafilatura | https://github.com/adbar/trafilatura | 现代版本 Apache-2.0；旧版许可不同 | HTML baseline，必须锁版本 |
| Unstructured | https://github.com/Unstructured-IO/unstructured | core Apache-2.0；extras/SaaS separate | benchmark，不建第二默认链 |
| MinerU | https://github.com/opendatalab/MinerU | custom license | benchmark/待许可 |
| Marker | https://github.com/datalab-to/marker | GPL-3.0，models separate | 当前 benchmark；R-C 通过且模型独立批准后可作为 provider/source absorption |
| PyMuPDF | https://github.com/pymupdf/PyMuPDF | AGPL/commercial dual | R-P 默认排除；R-C/AGPL 组合通过后可依法吸收，无需以商业许可为唯一道路 |
| Repomix | https://github.com/yamadashy/repomix | MIT | 工程/代码来源 Adapter 后置 |
| Crawl4AI | https://github.com/unclecode/crawl4ai | exact tag/browser deps 复核 | isolated web worker 后置 |
| Zotero | https://github.com/zotero/zotero | AGPLv3 | 最小先 API/BibTeX/CSL；R-C 通过后可另包吸收源码 |
| Anki | https://github.com/ankitects/anki | AGPLv3-or-later | 最小先 exchange/API；R-C 通过后可另包吸收源码 |
| py-fsrs | https://github.com/open-spaced-repetition/py-fsrs | MIT | Human Learning scheduler |
| Joplin | https://github.com/laurent22/joplin | AGPL-3.0-or-later；assets separate | JEX/Markdown/API Adapter |
| Logseq | https://github.com/logseq/logseq | AGPL-3.0 | 最小先 Markdown/EDN Adapter；R-C 后可评估源码吸收 |
| SiYuan | https://github.com/siyuan-note/siyuan | AGPL-3.0 | 最小先 export/API Adapter；R-C 后可评估源码吸收 |
| AFFiNE | https://github.com/toeverything/AFFiNE | exact tag/packages/assets re-audit | UX/architecture reference |
| XYFlow | https://github.com/xyflow/xyflow | MIT | Canvas/Graph interaction candidate |
| marimo | https://github.com/marimo-team/marimo | Apache-2.0 | v1.x research tool, not core |
| H5P | https://github.com/h5p/h5p-php-library | core MIT；content types separate | later learning content exchange |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | MIT；models separate | v1.x ASR provider |
| FFmpeg | https://github.com/FFmpeg/FFmpeg | build flags determine LGPL/GPL | media CLI，binary SBOM required |
| sqlite-vec | https://github.com/asg017/sqlite-vec | MIT/Apache-2.0；pre-v1 risk | optional derived index |
| LanceDB | https://github.com/lancedb/lancedb | Apache-2.0 | benchmark/optional derived index |
| TinyCortex | https://github.com/tinyhumansai/tinycortex | MIT | v2 deferred；v1.0 仅允许不复制代码的概念 ADR，不能替代 truth layer |
| llama.cpp | https://github.com/ggml-org/llama.cpp | MIT；models separate | optional local model provider |
| OpenTelemetry | https://github.com/open-telemetry/opentelemetry-specification | Apache-2.0 | internal diagnostics semantics |
| OpenInference | https://github.com/Arize-ai/openinference | Apache-2.0 | AI trace semantics, Advanced only |

闭源但需要兼容/研究的产品：Obsidian、Readwise、Tana、Roam Research、Heptabase、Capacities、Notion、NotebookLM。文档只能写 `format/API interoperability` 或 `UX/behavior reference`，不能写“开源源码吸收”。

### 15.1 历史研究材料索引

| 材料 | 当前用途 |
|---|---|
| `Cognitive_Loop_OS_开源候选_STAR清单_2026-07-17.xlsx` | 103 去重候选的早期发现快照；Star 不参与优先级 |
| 2026-07-31 完整对话/369 项总池 | 广泛候选和 UI 模式来源；无执行权 |
| `03_AXOS_开源能力总表.xlsx` | 57 项深入候选；需按 v4 重新分 Horizon |
| repository 101 registry/ledger | 历史登记与代码证据入口；按 Upstream V2 迁移 |
| 22 Verified FullStack/WORKLAB integration doc | 仅抽取 OS 边界、上游和许可结论；WORK-LAB 规划无产品权威 |
| HERMES/Obsidian-Assistance 包 | 仅借鉴 dry-run/backup/apply 安全模式；不是 OS 源码路线 |

完整条目不复制进 active roadmap；它们通过 Reference Index 和 Upstream Ledger 可追溯。只有 selected 当前纵切进入任务卡，避免再次让候选数量淹没产品闭环。

---

## 16. 验证、CI 与 Release 总合同

### 16.1 最小安全矩阵

| 变化类型 | 必跑 |
|---|---|
| 普通文档/机械格式 | convention + truth/reference link；非 truth 文档可轻量 |
| 纯 Product Truth/Naming/Alias/Reference 文档 | truth gate + lint + Product Owner review；不机械跑 installer |
| Evidence/Promotion/Capability/Release runtime schema 或 claim | 受影响测试/安装资格 + Product Owner review；高风险/unknown 时 full |
| 普通 Python | lint + Python 主版本完整相关产品套件 |
| UI/BFF | baseline + browser smoke + accessibility smoke |
| Windows runtime/storage/process | baseline + Windows bundled-runtime smoke |
| Rust/Tauri shell | desktop-fast；打包资源再加 desktop-build |
| Installer/NSIS/bundle/data migration | installed lifecycle + migration/rollback + real user flow |
| Python public contract/dependency/lock/parser | compatibility matrix + wheel + Windows bundled real-format smoke |
| PDF/Office/OCR/ASR Adapter | real corpus + source/wheel/bundled/installed profile；对应 external binary/model |
| Evidence/promotion/permission/security | contract + adversarial + migration + independent review |
| Vault/Markdown/Canvas | fixture semantic + conflict/rollback + Windows installed roundtrip |
| AI/learning | cited eval + deterministic history + safety + installed user flow |
| unknown/classifier/workflow/schema/migration | full fail-safe |
| nightly/manual/RC | full matrix + corpus tiers + flake sampling |
| formal Release | exact-SHA/tree full + artifact/installer/assets/download hashes + installed closure |

### 16.2 聚合规则

- 每个 logical Gate 有唯一 ID；workflow job 名只是 implementation mapping；
- required Gate failed/cancelled/timed-out/unknown 时 verdict fail；
- not-required 才允许 skipped；
- 已运行的非 required 安全/测试 Gate 失败也不能被 aggregator 忽略；
- GatePlan 输出、needs mapping、attestation job set 三者由同一 registry 生成/验证；
- `py-primary`/`test` 这类漂移必须由 truth table 捕获；
- selective run 和 main tree-bind 不能标 release eligible；
- Release 只读取 full attestation，不搜索“任意同 SHA 的 CI success”。

### 16.3 证据复用

允许复用的同一性：

```text
source commit/tree
+ actual checkout tree
+ workflow digest
+ policy/profile/classifier digest
+ lock/bundle digest
+ environment epoch
+ required gate set/conclusions
```

任一未知/变化/过期即 full fallback。已知 flaky desktop lifecycle 在稳定前按触发条件重新验证，不用 tree proof 隐藏 flake。

### 16.4 Release Identity v3

至少包含：

```text
product_name / machine_id / version
product_truth_digest
capability_evidence_digest
source_commit / source_tree
workflow / policy / classifier / lock digests
full_qualification_run / required gates / conclusions
wheel / bundle / installer hashes
installed user flows and fixture hashes
release workflow run
public asset names/sizes/hashes/provider digests
download readback hashes
signing status
```

若没有签名，明确 `signing_status: unsigned`，不得暗示签名。v0.5.0 历史 Release/asset 不回写；新合同从新版本开始。

---

## 17. 评分与 v1.0 的 8 分硬门槛

以下为证据型审计估计，不是自动测试分数：

| 维度 | 当前估计 | 8+ 硬门槛 |
|---|---:|---|
| 真实资料摄入 | 3.5 | PDF/Office/OCR advertised formats 均有 installed/restart/loss；raw-first |
| Evidence Integrity | 4.0 | Candidate→cross-validation→EvidenceBundle→review；矛盾/时效/引用可见 |
| Deep Human Learning | 2.5 | 真实主题完成 pretest→练习→即时/延迟回忆→迁移→Teach Back，并有诚实限定的比较性评测 |
| AI Learning Assets | 3.5 | Evidence-bound Memory/Rule/Skill candidate→eval→approve→invoke→revoke；同任务 with/without assets 对照 |
| 双向转化 | 2.0 | Human/AI feedback→proposal→review→new revision；零自动晋升 |
| 日常可用性 | 4.5 | 中央工作区、文件树、reader/editor/search/context、失败恢复、重启 |
| Obsidian/开放互操作 | 3.0 | C4 semantic roundtrip、conflict/rollback、installed Windows |
| Release 资产身份 | 8.0 | v0.5.0 资产链较强；新版本还需绑定真实产品 capability/full profile |

综合不能靠 Release 工程高分拉升。以下任一为零/缺失时，产品总体不得宣称 8+：真实安装资料闭环、EV3/EV4 Evidence、Human Learning、AI Asset promotion、双向修订、开放导出/恢复。

---

## 18. 立即执行队列

### 第 0 步：每次重新冻结

执行 AXW-000。本文基线是 `main@492fac5`，若云端改变，先更新 BaselineEvidence，不重写产品定位。

### 第 1 个代码 PR：先修误绿门禁

执行 AXW-003 的最小 hotfix：Gate ID/aggregator/full-attestation/依赖 real-format classification。当前 PR #68 的 `test (3.12)` 为 **2 failed / 1106 passed / 1 skipped**，失败分别是 `tests/test_ci_a0_gates.py` 仍硬断言 `markitdown>=0.1`，以及 `requirements.txt` 仍未与 `markitdown[pdf]>=0.1` 同步；但 `a0-gates` 仍结论 success。先修聚合漏洞，并让依赖真相由同一 projection 生成/验证，不能只改字符串直到变绿。

### 第 2 组产品与 Truth 双车道

- 产品车道：AXW-002A → AXW-011A → 修复/替代 PR #68 → AXW-010 → AXW-012 installed PDF；
- Truth 车道：AXW-001A → AXW-004A/C/D/E；它可与 fixture/PDF 并行，但不得以归档 369 项或搬迁所有历史文档阻塞 PDF；
- AXW-001B/001C、004B/F 按独立 PR 后续完成；不同时改 runtime、包名、远端仓库或数据目录；
- PR #70 不原样合并，其旧 B/C/R/HERMES 执行顺序无现行权威。

### 第 3 组横切增量（与产品修复并行）

- 先执行 AXW-006A：比较 Permissive Core 与 Research Copyleft Composition，按“最大化合法源码吸收”给出 Owner Decision；不直接重许可或复制第三方源码。
- 执行 AXW-006B：把 local/source/binary/network 分发通道和许可证状态写入 Upstream Ledger。
- 执行 AXW-007A/B、AXW-002D：只读 doctor、Environment Observation、Compatibility Policy 和 ReleaseFreeze 分层；不猜本机工具版本，不自动改 PATH/注册表，不把某一版本写进 Product Truth。
- 需要重建 bundle 时再执行 AXW-008A/B 与 AXW-009A；完整跨机 offline kit 和全部 Windows bug corpus 不阻塞 PDF。

### 第 4 组开源账本与 fixture PR 序列

先执行 AXW-002A 的 schema + PDF 当前上游 RDR bootstrap；再用独立 branch/PR 执行 AXW-011A 真实 PDF corpus。历史 369/101/57/8 reconciliation 由 AXW-002B 后台进行，不阻塞 PDF，但 machine gate 必须保证所有旧 ID 最终可追溯。

### 第 5 个产品修复序列

```text
AXW-010 Capability Truth
→ AXW-012 Installed PDF Survival / v0.5.1
→ AXW-020 RawAsset/Data Contracts
→ AXW-015 Durable Operations + AXW-021/022/024/030
→ AXW-090A/B Structured Representation
```

PR #68 先在最新 main 上同步依赖真相与真实正文 oracle，再纳入 AXW-012 的 wheel/bundle/installer 资格；不能以空 PDF fixture 和源码环境变绿合并。#69 可独立审查；#70 仅抽取真实问题后关闭/替代。

### Codex 启动口令

用户下一步可直接说：

```text
按最终主任务包执行 AXW-000；冻结最新云端事实，完成后不要跨入下一包。
```

随后：

```text
基于 AXW-000 的冻结基线，执行 AXW-003 最小 hotfix；创建单独分支和 PR，按任务卡报告证据。
```

---

## 19. 最终 Definition of Done

### Product Truth

- 唯一产品名、类别、定位、短句、核心/非目标和历史别名已机器化；
- 用户界面与文档不再出现路线漂移；
- Codex 是当前执行主体；
- repo/local/package/data migration 有独立、可回滚合同。

### Source & Evidence

- 真实资料 raw-first、不静默损失；
- Source/Claim/Candidate/Evidence/Knowledge 不混用；
- Evidence 来自风险适配的交叉验证、矛盾/时效/范围审查；
- citation 可回原件和确切位置。

### Human Learning

- 真实主题有目标、解释、练习、延迟复习、迁移、Mastery 和 Teach Back；
- 学习结果可回 Evidence；模型评分不自动算掌握。
- LearningEffectEvaluation 记录 pretest、即时/延迟回忆、迁移/Teach Back、耗时和适用范围；没有数据时不宣传效果提升。

### AI Learning

- Memory/Rule/Skill/Standard/Context/Eval 是外置、版本化、可审查资产；
- candidate→evaluation→review→approve；
- 调用绑定资产 revision、权限、来源和 OutcomeProof；
- 过期、冲突、替代、撤销有效。
- AIUseEvaluation 对照 with/without approved assets，记录引用、冲突拦截、scope violation 和版本；没有数据时不宣传准确率提升。

### Bidirectional Transformation

- 双向互转只生成 proposal/candidate；
- 人的学习反馈和 AI 调用结果可提出修订；
- 无来源/评估/授权的内容不正式化；
- 完整 provenance graph、version、restart/export。

### Workspace & Interoperability

- OpenHuman-inspired 中央工作面独立实现；
- PDF/Office/OCR/Markdown/Canvas 真实安装版可用；
- Obsidian C4 往返、冲突、备份、rollback；
- Zotero/Anki 等按独立 Adapter 后续扩展。

### Quality & Release

- 总门禁不会在核心 Gate 失败时误绿；
- 普通 PR 选择性、风险变化充分、RC/Release full；
- Release exact-SHA/tree、truth/capability/workflow/lock/bundle/installer/hash 全绑定；
- 下载后安装版完成真实用户闭环；
- 旧 tag/Release/资产不改写。

---

## 20. 一句话最终路线

> **先让真实开放资料可靠进入并保留来源，再通过多源对照形成真正证据；让人基于同一证据完成理解、练习、记忆、迁移与 Teach Back，让 AI 基于同一证据形成可审查、可评估、可调用、可撤销的记忆、规则、技能与规范；两侧只通过受控候选互相改进，并始终能够回到原件、版本、冲突和开放格式。**

---

## 21. 本总包的来源账本

以下 Library ID 只用于本次治理证据和未来人工追溯，不进入产品运行时或仓库硬编码：

| 材料 | Library ID | 本总包采用内容 |
|---|---|---|
| Future Master Blueprint v1 (2026-08-09) | `libfile_170cd96502048191a0ab2ebb3ade5183` | 本地优先、开放资料、多格式、Obsidian C4、UI/版本骨架 |
| v0.5 Multiformat Audit/Recovery | `libfile_420f7c20183081918ae4e37886fac362` | PDF/Office/OCR/媒体真实缺口、RawAsset/Conversion/Loss |
| OS-only Product/UI/Naming Audit | `libfile_e2b9cc3b33508191b9e9099fb864f016` | Workspace 命名、中央工作区、兼容边界 |
| Cloud Full Audit/Integrated TaskPack | `libfile_01b1e47c1e1c8191aba5135e6930f0bc` | 旧云端债务、CI/Release、复用阶梯、伪完成规则 |
| Minimum Surface Master TaskPack | `libfile_4b3d5c1a73488191acf28c4f4bac1584` | 369/101/8 口径、Compatibility Kernel、源码复用优先 |
| 2026-07-31 完整对话整理 | `libfile_4062a1fe3f548191a3f2798e8b7e971a` | 开源总池、旧 UI 研究、状态可观测、历史决策 |
| CI Acceleration/WORKLAB-Compatible old pack | `libfile_c84167dd3a808191ab76d1d45f6e3c97` | 只采用选择性验证思想；跨项目规划被剥离 |
| Agent FullStack 22 Verified doc | `libfile_7845aa3f9e288191bc12db804ab77d2e` | OS 上游/适配/许可建议；不采用 WORK-LAB 产品耦合 |
| 用户上传的同文档副本 | `libfile_24d1bbba060c8191b028f86ebb55543c` | 附件身份追溯；不重复计数 |
| 03 AXOS 开源能力总表.xlsx | `libfile_3148895b1ea88191a096107afd6a08fd` | 57 项候选、许可/阶段/PoC 重新裁决 |
| 7/17 开源候选 Star 清单.xlsx | `libfile_55f5c955ffb0819180fececce93369ca` | 约 103 去重早期候选；仅发现池 |
| Open Source Research Master List | `libfile_96abf84c781c8191bb4afa5b6959426c` | 扩展候选和去重来源 |
| KnowledgeBase 开源吸收总方案 | `libfile_411b75aa40d08191a79f363edc2219e3` | 许可/Adapter/吸收方法的历史参考 |
| KnowledgeBase 下一步深化方案 | `libfile_5ab4b3c7a83c819194d33ff65293efd0` | 知识流程历史研究；按 v4 裁决 |
| 旧 HERMES Master TaskPack | `libfile_e3d20e3c5db481918e114a9accc0187e` | 历史任务证据；writer 权限作废 |
| 元枢系统应用界面展示.png | `libfile_659e80cf25d881919cdb825fc5e6f57` | 旧界面视觉/信息密度参考，不作当前 IA 权威 |
| 暗色知识管理仪表盘界面.png | `libfile_8cae373a7d548191b68737409596cc42` | 视觉研究；治理 dashboard 不作为默认产品面 |
| ArcheAxis OS V3.0/V3.1 docs | `libfile_1b9ef0421ad881919cfc8ae3d800a6ac`, `libfile_871a17e6aed88191810cec30da5226a7` | 人类学习/AI 学习/视觉/空间旧重型愿景；核心机制保留，OS/重型表面延期 |
| Personal Research / Windows / LER 增量任务包 | `libfile_e456529807248191bf10c5a3671b9bf0` | 合法 copyleft 吸收、Windows 可复现构建、永久学习体验与知识表征层 |

豆包审计以 `EXT-AUDIT-DOUBAO-20260809`、DeepSeek 审计以 `EXT-AUDIT-DEEPSEEK-20260809` 分别作为 `external_reference` 进入 §2.8；每条 claim/verdict/evidence 独立记录。它们不互相构成代码佐证，也不覆盖当前云端行为和 Product Positioning v3。

### 21.1 云端事实入口

- Repository: https://github.com/DTALEX66/Cognitive-Loop-OS
- Baseline commit: https://github.com/DTALEX66/Cognitive-Loop-OS/commit/492fac5982c693eb668d31cc51a6a59bac83b7a1
- Release v0.5.0: https://github.com/DTALEX66/Cognitive-Loop-OS/releases/tag/v0.5.0
- PR #68: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/68
- PR #69: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/69
- PR #70: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/70

这些 URL 只证明本文审计时的来源；活动状态执行前由 AXW-000 重查。

---

## 22. Personal Research / Windows / LER 已合并裁决

本节吸收了同日增量包；其完整细则已进一步统一进 §23–§29。旧增量文件登记为 `authority_class: superseded/historical`、`agent_discovery: deny`、`superseded_by: this-v4`，只保留历史来源身份，不再需要单独读取或形成第二执行路线。

### 22.1 Personal Research Operating Profile

- 项目当前是个人、非商业、学习研究型项目；`Personal Research Project` 是状态，不是第二品牌或 Edition；
- 不为未来闭源商业化主动牺牲成熟开源复用；
- 任何开源项目只要与顶层许可和分发形式兼容、义务可完整履行，就允许 dependency/source-copy/source-merge/fork/vendor/link/sidecar/API/CLI/format；
- GPL/AGPL 可以直接吸收，但必须接受结合作品许可、Corresponding Source、构建/安装脚本和网络源码入口等实际义务；
- 当前非商业不构成许可证、模型、数据、字体、图标、素材和 fixture 豁免；
- 后期可换自研 provider，旧 commit/tag/Release 的许可和来源证据永久保留。

### 22.2 Windows 构建与语言边界

- Python 负责知识、Evidence、Learning、AI Assets、转换编排、迁移和语义验证；当前 CI 使用的主 minor 只是事实快照，后续由 Compatibility Policy 和 resolver 选择支持范围，不写入永久 Product Truth；
- JavaScript/TypeScript/Node 负责当前 WebView/前端构建与经 ADR 选择的 viewer/renderer；不预先锁死未来动画/3D 的实现语言，也不复制后端 promotion/permission/migration 规则；
- Rust/Tauri 负责桌面 shell、WebView、Job Object、loopback 安全、窗口/路径/原生 picker、bundle 资源发现和 installer bridge；不承载 Evidence/学习/AI 资产业务真相；
- PowerShell 7 只做 Windows doctor/bootstrap/build/test/installer qualification 的进程调用与只读诊断薄编排，不进入安装版运行时；复杂 manifest/identity/capability 判断在可测试的主程序模块；安装版 runtime child lifecycle 唯一归 Rust/Job Object；
- 工具链真相拆为 Compatibility Policy、Candidate Resolution、gitignored Environment Observation、某次 ReleaseFreeze 和 build/runtime attestation；任何 `windows.lock` 都只是某次构建/发布投影，不是永久 canonical 产品真相；
- 先修 ambient Python、未锁 Rust/Node/MSVC/SDK/WebView2/NSIS、registry 来源、动态端口 TOCTOU、路径/编码/文件锁/进程残留；
- online bootstrap、cached-only 和 portable offline kit 分级；完整跨机离线包不阻塞 v0.5.1。

### 22.3 Learning Experience & Representation Layer

LER 是 Human Learning Core 的永久一等输出层：

```text
Structured Views
→ Learning Maps
→ Visual Teaching & Courseware
→ Animation & Dynamic Explanation
→ Simulation & Practice Lab
→ Spatial Memory 2D / 2.5D / 3D / VR / AR
```

每个 Representation 必须绑定 LearningObjective、KnowledgeBlock/EvidenceAnchor、provenance、LossReport、renderer/provider/version、asset license、fallback 和开放导出。技术成熟度与学习效果成熟度分别记录；能显示不等于能提升学习。

### 22.4 新 Program 索引

| Program | 目的 |
|---|---|
| AXW-006 | OSS License Compatibility & Distribution Compliance（Personal Research profile） |
| AXW-007 | Windows Environment Policy, Doctor & Release Freeze |
| AXW-008 | Windows Bootstrap & Offline Cache |
| AXW-009 | Windows Build Profiles & Exact-SHA Qualification |
| AXW-090 | Learning Experience & Representation Layer |

上述增量不恢复 WORK-LAB、Agent OS 或商业产品矩阵，也不改变 PDF/Evidence/Obsidian/双学习主链；它扩大合法复用方式、固定本机工程底座，并把完整学习辅助版图恢复到正式未来蓝图。

---

## 23. v4 完整能力图谱：任何后期能力都不得再被省略

### 23.1 图谱状态与防删规则

每个能力必须有稳定 `capability_id`，并同时拥有两个不可混用的字段：

```text
authority_status = binding_core | binding_long_term | exploration | retired
```

`authority_status` 决定该能力是否属于产品承诺；`roadmap_state` 决定当前推进阶段：

```text
critical_now          当前生存/最小闭环关键路径
core_next             当前最小闭环完成后立即进入
formal_later          正式长期产品能力，已有 Horizon 和 Program
experimental_later    正式研究能力，先证明可用与学习效果
deferred_retained     保留在蓝图但不进入当前资源队列
retired_positioning   只退役旧名字、旧外壳或错误路线，不删除可复用机制
rejected_with_record  经明确决策拒绝，保留原因、证据和替代项
```

合法组合固定为：`binding_core → critical_now|core_next`；`binding_long_term → formal_later|experimental_later`；`exploration → experimental_later|deferred_retained`；`retired → retired_positioning|rejected_with_record`。`experimental_later` 可同时描述正式长期但证据未成熟的能力，或没有产品承诺的探索项；两者必须由 `authority_status` 区分。任何代理不得把 `binding_long_term + experimental_later`、`formal_later` 或 `deferred_retained` 改写为“项目不做”。能力移除必须同时满足：用户明确批准、写入 Decision Record、说明替代/影响/数据迁移、保留 tombstone 和历史引用。Active Plan 可以很窄，Capability Atlas 必须完整。

Horizon 是依赖顺序，不是永久绑定的发行号：

```text
H0 生存与真相
H1 原件/Evidence/PDF Reader
H2 常见多格式
H3 Obsidian C4 与日常工作台
H4 人类/AI 双学习最小闭环
H5 稳定单用户 1.0 资格
H6 Research/Knowledge/Adapters/Course/Visual Teaching
H7 full learning/animation/simulation/2.5D
H8 3D/VR/AR + encrypted sync/device + one controlled-execution research
H9 SDK/signed extension/publish/optional community
H10 generic Agent/autonomous exploration
```

若版本号、市场环境或依赖成熟度变化，可以调整版本标签，但不能跳过前置能力和证据门槛。

### 23.2 CAP-00｜Product Truth、权威与治理内核

| 能力族 | 永久范围 | 状态/Horizon |
|---|---|---|
| 产品真相 | 唯一名称、定位、服务对象、核心/非目标、口号、Owner 决策 | `binding_core + critical_now / H0` |
| 权威与引用 | canonical/current/research/deferred/historical 分类、supersedes DAG、引用索引 | `binding_core + critical_now / H0` |
| Candidate 治理 | 外部材料、人工输入、AI 输出、执行 trace 默认候选；晋升需证据/评估/授权 | `binding_core + core_next / H0–H4` |
| 能力真相 | technical/license/installed/learning-evidence 四轴，不以模块或测试数冒充支持 | `binding_core + critical_now / H0` |
| 生命周期 | stable ID、revision、freeze/fork/diff/deprecate/revoke/rollback | `binding_core + core_next / H1–H5` |
| 隐私与范围 | Approved Roots、数据范围、权限、隔离、审计、导出、删除 | `binding_core + critical_now / H0–H5` |
| 上游治理 | Scope Ledger、Upstream Ledger、RDR、SBOM、NOTICE、许可证与替换历史 | `binding_core + critical_now / H0+` |

旧“本源/Primal Core”的可用机制归入本 CAP；旧 OS 品牌和多产品矩阵不恢复。

### 23.3 CAP-01｜Source Capture、Research 与 Evidence Radar

正式来源面不能只剩 GitHub URL 或本地文件：

- 本地文件、文件夹、现有 Vault、拖放、剪贴板、扫描件、相机/截图；
- 网站、官方文档、百科、论坛/社区、博客、新闻、标准、政府/机构页面；
- 学术期刊、论文、预印本、专利、图书/章节、数据集、参考文献与引文网络；
- RSS/Atom、公开 API、导出包、网页快照、浏览器选区、Web Archive；
- Git 仓库、代码、Issue/PR、Release、文档站、Notebook、数据文件；
- Zotero/BibTeX/CSL、Readwise、高亮、Anki/课程平台导出；
- 音视频、字幕、播客、讲座、课程、图片、图表、课件；
- 用户原创笔记、观察、实验记录、访谈、问卷与人工判断。

核心对象：`SourceConnector`、`CaptureSession`、`RawAsset`、`SourceRecord`、`SourceSnapshot`、`FetchPolicy`、`AccessGrant`、`ResearchQuestion`、`SearchRun`、`SourceGraph`、`ResearchPackage`、`UpdateWatch`。

正式能力：检索计划、来源类型覆盖、重复/镜像识别、来源独立性、权威性、时效、版本/发布日期、抓取方式、引用链、冲突来源、失效链接、订阅更新、手动复核。自动研究只能生成候选，不得自动写成事实。

状态：本地/网页基础为 `binding_core + core_next H1–H2`；学术/专利/数据集和来源雷达为 `binding_long_term + formal_later H4–H7`；自动持续监测为 `binding_long_term + formal_later H7+`。

### 23.4 CAP-02｜Raw-first 多格式转换与内容理解

必须规划的输入族：

| 输入族 | 最小语义与保真目标 | 阶段 |
|---|---|---|
| Markdown/TXT/RST/AsciiDoc | 文本、标题、链接、代码块、扩展语法、编码/EOL | H1–H3 |
| HTML/MHTML/网页 | 正文、DOM/标题层级、元数据、表格、链接、快照与 URL 版本 | H1–H2 |
| PDF | 原件页、文本层、阅读顺序、bbox、表格/公式/图片、扫描/OCR、页锚点 | H0–H2 |
| DOC/DOCX/ODT | 段落、样式、标题、表格、批注、修订、页/节、媒体 | H2+ |
| PPT/PPTX/ODP | 幻灯片、层级、shape、speaker notes、媒体、动画/转场损失 | H2+ |
| XLS/XLSX/ODS/CSV/TSV | sheet/cell/formula/cached value/merged range/table/chart 与损失 | H2+ |
| JSON/XML/YAML/TOML/数据库导出 | schema、类型、层级、稳定路径、敏感字段 | H2+ |
| EPUB/MOBI/电子书 | 章节、目录、注释、图像、位置锚点、DRM 边界 | H6+ |
| 图片/扫描 | 原图、OCR、版面、表格/公式/图表、置信度、语言与旋转 | H2+ |
| 音频/视频 | 原媒体、ASR、speaker、时间戳、章节、画面 OCR、关键帧与字幕 | H6+ |
| 字幕/转录 | cue、speaker、time range、语言、修订 | H2/H6 |
| 代码/仓库/Notebook | commit/tree、文件、symbol、cell/output、依赖、license、diff | H6+ |
| 邮件/聊天/会议导出 | thread、sender/time、附件、隐私范围、引用边界 | H9+ |
| Canvas/白板/图 | node/edge/group/geometry/style/unknown fields/attachments | H3+ |

每条转换统一走：

```text
RawAsset → ConversionPlan → ProviderProbe → ConversionRun
→ DerivedDocument/Block/MediaSegment/Table/Formula
→ EvidenceAnchor + LossReport + QualitySignal
→ Review/Retry/AlternateProvider → IndexRevision
```

`metadata_only`、文件扩展名识别、首行文本、Pillow 尺寸或 FFprobe 时长不能冒充内容转换/OCR/ASR。大文件必须流式或磁盘 spool，失败保留原件、运行记录与可重试状态。

### 23.5 CAP-03｜Evidence Integrity 与多源交叉分析

完整对象链：

```text
RawAsset
→ SourceRecord
→ ExtractedClaim
→ EvidenceCandidate
→ CrossValidationRecord
→ EvidenceBundle / CorroboratedEvidence
→ ReviewedKnowledge
```

必须覆盖：

- claim 原文、语义规范化、适用范围、时间、版本、实体和来源锚点；
- 支持、反驳、部分支持、不可比、未知五类关系；
- 一手/二手、独立性、权威性、方法质量、样本、偏差、利益冲突与时效；
- 同名不同物、版本漂移、复制转载、循环引用、来源聚类和共同祖先；
- 矛盾并存、置信区间/不确定性、反例、适用条件与过期策略；
- 人工 adjudication、审查理由、修订历史、撤销和开放导出；
- 高风险领域的权威来源、独立佐证和强制人工复核；
- 软件能力的 exact tree/environment/fixture/assertion；
- AI 输出只能证明“某模型在某输入下生成了什么”，不能独立证明外部事实。

Evidence 工作面应同时显示 claim、来源、锚点、支持/反驳、独立性、时效、冲突、适用范围和审查记录，而不是只显示一个总分。

### 23.6 CAP-04｜Knowledge Workspace 与开放知识模型

核心对象：`Workspace`、`Library`、`Vault`、`Collection`、`Document`、`KnowledgeBlock`、`Property`、`Tag`、`Link`、`Backlink`、`Attachment`、`Citation`、`Annotation`、`Canvas`、`Graph`、`TopicTree`、`LearningMap`、`SavedSearch`、`Template`、`Revision`、`ExportPackage`。

永久视图：

- 文件树、收藏/最近/固定、来源库、导入中心；
- Markdown/富文档/PDF/Office/图片/音视频 Reader 与 Editor；
- 列表、卡片、表格、数据库、Board、Gallery、Calendar、Timeline、Matrix、Comparison；
- Outline、Properties、Tags、Links、Backlinks、Citations、Annotations；
- 全文/属性/链接/引用/语义搜索和保存查询；
- Canvas、概念图、知识图谱、Topic Tree、Learning Map、路线图；
- 版本、diff、冲突、恢复、导出与兼容状态；
- 多标签页、分栏、焦点模式、命令面板、键盘和无障碍。

开放文件/格式是真相面，SQLite/FTS/vector/graph 都是可迁移或可重建投影；任何高级视图不得把知识锁进不可导出的专有状态。

### 23.7 CAP-05｜Deep Human Learning Core：16 个正式子系统

旧 Human Learning OS 的 16 个子系统全部保留，但统一为一个 Human Learning Core：

| ID | 子系统 | 产品对象/用户结果 | 阶段 |
|---|---|---|---|
| HL-01 | Capture | 从真实材料捕获学习单元并保持来源 | H1–H2 |
| HL-02 | Knowledge Structure | 主题、先修、概念、例子、反例和关系结构 | H3–H4 |
| HL-03 | Learning Diagnosis | 目标、先验、误区、能力缺口、pretest | H4 |
| HL-04 | Learning Route | 目标到路径、依赖、节奏、里程碑与调整 | H4–H6 |
| HL-05 | Cognitive Load | 分块、渐进揭示、难度、冗余和可访问性 | H4–H7 |
| HL-06 | Memory Encoding | 联想、双编码、例子、比喻、视觉/空间锚点 | H4–H8 |
| HL-07 | Spaced Review | FSRS/可替换调度、复习队列、历史与解释 | H4 |
| HL-08 | Knowledge Palace | 2D→2.5D→3D 空间记忆路线 | H5–H8 |
| HL-09 | Active Training | retrieval、辨析、生成、填空、问答、错题 | H4 |
| HL-10 | Skill Practice | 步骤练习、案例、项目、模拟、rubric | H4–H7 |
| HL-11 | Metacognition | 信心、反思、策略、时间、困难与调整 | H4–H6 |
| HL-12 | Feedback/Error Book | 错因、纠错证据、相似错题、反模式 | H4 |
| HL-13 | Output/Teaching | Feynman、Teach Back、讲义、演示和评价 | H4–H7 |
| HL-14 | Personal Learning Profile | 偏好/可访问性/历史/节奏，本地可控 | H5+ |
| HL-15 | Consolidation | daily/weekly review、长期保持、跨主题连接 | H5–H7 |
| HL-16 | Transfer & Applied Output | 新情境迁移、跨领域类比、知识到行动/项目 | H4–H7 |

“学会”必须能观察到回忆、解释、辨析、应用、迁移、输出、Teach Back 和真实项目使用；浏览时长、点击、模型评分或完成一张卡都不能单独算掌握。

### 23.8 CAP-06｜Learning Experience & Representation：完整视觉教学体系

LER 的四层合同：

1. **Fact Layer**：定义、来源、数据、公式、结论、条件、范围、证据、冲突和风险；
2. **Memory Layer**：比喻、故事、PAO、视觉锚点、对比、空间位置、情绪、动作、助记和 Memory Scene Script；
3. **Visual Layer**：信息图、流程图、架构图、时间线、思维/概念图、知识图谱、比较、层级、剖面、决策树、路线图、数据图、Canvas、2D/2.5D/3D、动画和交互；
4. **Teaching Layer**：新手/专家解释、例子/反例、问题、测验、练习、复习、教学脚本、课堂演示、rubric 和学习验证。

正式输出族：

- 课程首页、课程地图、章节路线、知识树、先修图、进度/时间线、Palace 入口；
- 概念/方法/案例/错题/术语/行动卡、对比图、流程、框架、决策、视觉锚点和动态演示；
- PPT/课件、讲义、storyboard、voice-over/动画脚本、教师演示包、数字人候选；
- 练习步骤、交互题、虚拟实验、sandbox、案例复盘、项目任务、作品集和 rubric；
- 表格、卡片、Matrix、Timeline、Database View、Canvas/Graph/Learning Map；
- 文本/2D/键盘/屏幕阅读/低配 fallback 和开放导出。

正式 `RoutePackage`：

```text
FactLayer + MemoryEncoding + VisualAssets + TeachingAssets
+ ReviewPlan + PracticeTasks + EvidenceIndex
+ Version + AuditStatus + RouteLineage
```

支持 local save、freeze、fork、diff、教师/学习者审阅、复制单层或完整路线、路线谱系和候选共享。任何生成内容都必须能回 EvidenceAnchor；视觉补全/推断明确标识。

### 23.9 CAP-07｜Spatial Memory：2D、2.5D、3D、VR/AR 全路线

核心空间模型：

```text
World → Palace → Room → Locus → Object → Route
```

正式能力：admission score、知识类型/难度/混淆度分析、room/locus 分配、visual anchor、route generation、review scheduling、容量/碰撞/相似干扰检测、弱点高亮、路线优化、局部重排、mastery/transfer 记录。

正式模式：edit、explore、learn、walk、recall、weak-point、project-review、exam、output、explain。

Graph 与 Palace 不得混同：Graph 服务语义关系和检索；Palace 服务位置、路线、空间联想和回忆。3D 只有在改善定位、联想、回忆、关系理解、路线复习、项目复盘或情境迁移时才能晋升；装饰建筑、节点堆积、频繁自动移动、游戏大厅化、强迫所有人用 3D 均为失败。

阶段：2D 为 `binding_core + core_next H4–H5`；2.5D 为 `binding_long_term + formal_later H7`；3D 为 `binding_long_term + experimental_later H8`；VR/AR 受控原型和学习效果研究为 `binding_long_term + experimental_later H8`。所有高级模式必须有 2D/文本 fallback、GPU 可选和开放导出。

### 23.10 CAP-08｜AI Learning Assets Core

正式资产不是“Agent”，而是外置、版本化、可审查对象：

- `AIMemory`：事实/情境/偏好/程序记忆，含来源、范围、时效、冲突和 taint；
- `AIRule`：条件、约束、允许/禁止、优先级、冲突策略、测试和回滚；
- `AISkill`：输入/输出、权限、依赖、步骤/代码、fixture、风险、版本、撤销；
- `AIStandard`：schema、质量标准、风格、术语、协议和合规要求；
- `AIContext`：任务/项目/工具/少样例/压缩上下文，含预算和选择理由；
- `AIEval`：rubric、dataset、result、regression、适用模型/环境；
- `OutcomeProof`：使用了什么资产 revision、产生什么结果、如何验证、何时失败。

旧 Machine Knowledge Unit、Context Pack、Compressed Context、Few-shot、Tool/Project Context、Privacy Scope、Allowed/Blocked Tasks、Precondition、Anti-pattern、Last Verified、Deprecation、Model Access Audit 全部映射进上述对象，不恢复 Machine Knowledge OS 品牌。

### 23.11 CAP-09｜Human ⇄ AI 受控双向转化

两条直向链必须同时存在：

```text
HumanLearningAsset + EvidenceBundle
→ AIAssetCandidate → Eval → Review → Approved AI Asset

ApprovedAIAsset/AIUseEvaluation + EvidenceBundle
→ HumanLearningAssetCandidate → Review/Practice → Human Asset Revision
```

同时保留反馈链：Human learning error/mastery/Teach Back 与 AI invocation/eval/trace 只能提出 `TransformationProposal/ChangeProposal`。每次转化继承 EvidenceBundle、来源、范围、版本和不确定性；无 review/eval/authorization 不晋升；隐私笔记和个人掌握记录默认不暴露给模型或导出。

### 23.12 CAP-10｜Search、Retrieval、Graph 与 Model Provider Layer

检索阶梯：确定性路径/属性/FTS → links/backlinks/citation → graph → optional vector → rerank → multimodal。向量、图或模型索引都可删除重建，不能成为唯一事实库。

模型能力族：云端/本地 LLM、embedding、reranker、vision、OCR、ASR、TTS、图像/视频生成；支持 provider capability probe、成本/延迟/上下文/速率、隐私、离线/GPU、fallback、模型卡/资产许可、prompt/eval version。GPT/Claude/DeepSeek/Kimi/Qwen/GLM/Gemini/Grok/Ollama/llama.cpp 等只是可替换 provider 候选，不进入产品名和永久核心依赖。

RTX/CUDA 只属于可选本地加速 profile；无 GPU 必须仍能运行核心资料、Evidence、学习和开放互操作。

### 23.13 CAP-11｜Compatibility Kernel 与生态 Adapter

永久 Adapter 合同：

```text
discover → probe → authorize → inspect → plan → dry-run
→ import/export → incremental cursor → rename/delete
→ conflict/loss → backup/apply/rollback → restart/roundtrip
```

正式生态范围：

- 第一纵切：Obsidian Vault、Markdown、Properties、links/backlinks、attachments、JSON Canvas C4；
- 文献/研究：Zotero、BibTeX、CSL JSON、RIS、DOI/OpenAlex/Crossref 等公开接口候选；
- 学习：Anki/APKG/API、FSRS、H5P、Moodle、Open edX、Kolibri；
- PKM：Joplin、Logseq、SiYuan、AFFiNE、AppFlowy、Anytype、Notesnook、Trilium/TriliumNext、SilverBullet、Foam；
- 阅读/高亮：Readwise/Reader、NotebookLM 行为、浏览器选区/扩展；
- 闭源兼容/UX：Notion、Tana、Roam、Heptabase、Capacities；
- 画布：JSON Canvas、Excalidraw、开放 whiteboard/diagram adapter；
- 开放导入导出：Markdown folder、ZIP、JSON/JSONL、CSV/TSV、HTML、PDF、BibTeX/CSL、Anki、Canvas、媒体与 manifest。

每个 Adapter 独立 capability、许可、fixture、loss、C-level、installed evidence 和 kill switch，不以“支持生态”统称。

### 23.14 CAP-12｜Evaluation、Feedback 与 Consolidation

保留旧 Evolution Loop 中有用机制：rubric、regression、trace audit、human mistake、success pattern、anti-pattern、conflict resolution、knowledge update、palace rearrangement、constraint update、daily consolidation、weekly review、long-goal resume、diagnostics、capability score。

自治 Sleep Loop、无审查自我改写、自动激活 Machine Lesson 继续 `exploration + deferred_retained H10`。Human learning 日/周复盘和 AI asset 定期过期/冲突检查则属于核心，必须人工可见、可暂停、可撤销。

学习效果与 AI 使用效果采用两套独立评测：

- `LearningEffectEvaluation`：pretest、即时/延迟回忆、迁移、Teach Back rubric、耗时、到掌握时间；
- `AIUseEvaluation`：同任务 with/without approved assets、引用正确性、冲突/过期拦截、scope violation、结果质量与成本。

没有研究数据时只能声明“闭环可测”，不能宣传提高学习率、记忆率或 AI 准确率。

### 23.15 CAP-13｜Optional Execution Adapter、Tool、MCP 与 Workflow

旧 Praxis Runtime 的 intent/goal/plan/route/dependency/context/task/tool/MCP/permission/risk/dry-run/sandbox/worktree/checkpoint/trace/pause/resume/replan 全部保留为 `exploration + deferred_retained H10` 的可选执行层，不再成为默认产品中心。

只允许在 AI Skill 最小纵切中激活低风险、显式授权、可回滚调用。通用 Planner、多 Agent、Agent 市场、自治执行、Foundry、工作流平台、通用 MCP 控制台不得进入 v1.x 一级导航或阻塞核心闭环。未来激活时必须通过 Adapter 消费已批准 AI Assets，不能越过 Evidence/Permission/Revision。

### 23.16 CAP-14｜Bridge、Sync、Publish、Device 与 Community

正式远期路线必须保留：

- folder watch、Git、WebDAV、可选加密同步、冲突合并；
- local REST API、CLI、MCP 数据访问适配器；
- browser extension/clipper、PWA、Mobile companion；
- Desktop 主端、便携模式、备份/迁移/恢复；
- 静态 Publish、课程/知识发布包、演示/课件导出；
- RoutePackage/template/fixture 的候选分享与版本谱系；
- 可选小团队/师生协作、权限、评论和发布审核。

单用户本地数据真相未稳定前不激活团队/云端；同步/社区不改变本地优先，任何出机需明确授权、端到端范围说明和可撤销。

### 23.17 CAP-15｜Security、Privacy、Reliability 与 Recovery

必须覆盖 Approved Roots/realpath/symlink containment、safe HTTP/SSRF、auth/CORS/secret、tool risk、sandbox、quarantine、path traversal、atomic write、expected hash、backup、migration、WAL/lock、crash recovery、process tree、port ownership、installer upgrade/uninstall、audit/redaction、data export/delete、supply chain、SBOM/NOTICE/source offer、模型/资产许可。

统一权限对象固定为 `PermissionDecision(actor, action, resource, workspace, scope, sensitivity, risk, decision, reason)`；network、model/data egress、Vault write、AI Skill、export、sync 与 optional execution 都必须消费 AXW-005A 的同一合同，unknown action/resource 默认拒绝，任何域不得另建更宽松的本地布尔开关绕过它。

个人 Vault/正式学习资料永不作为公开 fixture；默认只读、先 synthetic fixture/dry-run；真实写入需用户授权、backup、expected-hash、atomic write、conflict 和 rollback。

### 23.18 CAP-16｜Developer Foundation、Windows、Quality 与 Release

开发底座包括：Windows doctor/bootstrap/cache/profile runner、Python/Rust/Node/PowerShell/外部 sidecar 边界、Unicode/中文/空格/长路径、文件锁/端口/进程/WebView2/MSVC/SDK/Defender 诊断、clean exact-tree bundle、安装/启动/重启/关闭/强杀/卸载。

质量体系包括：真实 fixture/oracle、契约/迁移/安全/性能/无障碍/跨版本/installed-format/roundtrip 测试、选择性 PR 门禁、nightly/RC full、Release exact-SHA/tree/lock/toolchain/bundle/asset/download readback。测试数量、Job/Receipt 或静态字符串断言不构成产品进度。

### 23.19 CAP-17～CAP-30｜显式长期子能力族

为避免 CAP-01/04/10/14/16 过宽而再次被摘要丢失，下列子能力各自拥有稳定 ID；它们与上文父能力是组成关系，不是重复产品：

| ID | 子能力族 | Parent / 状态 |
|---|---|---|
| CAP-17 | Research Discovery & Intake | CAP-01；`binding_long_term + formal_later` H6–H7 |
| CAP-18 | Knowledge Curation & Lifecycle | CAP-03/04；`binding_core + core_next` H1–H5，发布扩展 H6 |
| CAP-19 | Search/Index/Graph Semantics | CAP-04/10；`binding_core + core_next` H1–H5 |
| CAP-20 | Editor/Renderer/View Platform | CAP-04/06；basic `binding_core + core_next` H2–H5，extended H6–H8 |
| CAP-21 | Course/Project/Research Workspace & Outputs | CAP-05/17；`binding_long_term + formal_later` H4–H7 |
| CAP-22 | Exchange/Backup/Restore/Publish | CAP-14/16；backup/export `binding_core + core_next` H5，publish H6+ |
| CAP-23 | Provider & Model Governance | CAP-10；minimum H4，full H7 |
| CAP-24 | Durable Internal Operations | CAP-16；internal core，非用户一级能力 |
| CAP-25 | Windows/Desktop & Platform Portability | CAP-16；Windows `binding_core`，macOS/Linux `binding_long_term + formal_later` |
| CAP-26 | Quality/Release/Performance/Accessibility | CAP-16；all Horizons |
| CAP-27 | Solution Profiles/Templates | CAP-05/06/17；`binding_long_term + formal_later` H6–H7 |
| CAP-28 | SDK/Team/Community/Marketplace | CAP-11/14；SDK/签名/permission 为 `binding_long_term + formal_later H9`；team/community/marketplace 为 `exploration + experimental_later H9+`，不建空市场 |
| CAP-29 | Controlled Execution Extension | CAP-13；exploration H10；当前只允许一个低风险 Skill proof |
| CAP-30 | Retired Positioning Index | OS/Agent-first/自治进化/商业矩阵/WORK-LAB；retired，保留 tombstone |

CAP-17 对象至少含 ResearchProject/Question/DiscoveryCandidate/SourceCollection/ResearchFinding/ResearchPackage/Watch；CAP-18 含 KnowledgeUnit/Version/Entity/Relation/Conflict/Collection/Publication/Deprecation；CAP-20 含 EditorShell/RendererContract/undo/draft/autosave/revision/diff/freeze/fork/export；CAP-21 含 Course/Project/Session/Route/Decision/Artifact/Rubric/Reflection/Portfolio/OutputProof；CAP-24 含 Job/Checkpoint/Event/Outbox/idempotency/cancel/retry/recover/compensate/diagnostics，并由 AXW-015A–D 唯一实现。它们不能因为不是一级导航就从数据合同或任务图消失。

### 23.20 服务对象与端到端任务矩阵

| 角色 | 最小任务 | 后续增强 |
|---|---|---|
| 普通个人 | 导入真实资料、读写、搜索、整理、重启和导出 | 多视图、模板、个人知识/学习路线 |
| 学生 | 从教材/课件形成证据化笔记、练习、复习、错题和 Teach Back | 课件、动画、模拟、记忆宫殿、考试/迁移模式 |
| 教师 | 保留来源地制作解释、案例、练习、课程路线和 rubric | RoutePackage、课堂演示、互动内容、学生反馈 |
| 研究者/学者 | PDF/Zotero/网页/数据集比较、引用、冲突与文献链 | 多文档证据矩阵、引文网络、研究模板和可复现包 |
| 专家/重度用户 | 接管 Vault、属性/链接/Canvas、批量转换与自动化 | Adapter、规则/技能、同步、版本和可控执行 |
| AI 使用者 | 让 AI 只使用批准范围并给可点击引用 | Memory/Rule/Skill/Context/Eval 资产与可撤销反馈 |
| 隐私敏感/低配置用户 | 离线、CPU、开放格式、本地备份和无云也可用 | 可选本地模型/GPU；所有高级模式有低配 fallback |
| 开发/研究贡献者 | 可重现构建、fixture、adapter contract、许可真相 | SDK、扩展、评测与公开研究包 |

---

## 24. v4 用户闭环、UI 结构与工作模式

### 24.1 不变的最小用户闭环

```text
选择真实来源
→ 原件本地保存并记录来源/hash/version
→ 选择或自动探测转换 Provider
→ 显示转换结果、置信度、损失和失败恢复
→ 在中央工作区阅读/编辑/批注/搜索/链接
→ 提取 Claim 并比较多个独立来源
→ 审阅形成 EvidenceBundle/ReviewedKnowledge
→ 生成 Human/AI 候选资产
→ 人类练习/复习/迁移/Teach Back；AI eval/受控调用
→ 反馈只生成修订候选
→ 重启读回、开放导出、跨应用往返、冲突恢复
```

H0 只证明 PDF 生存闭环；H1–H3 建立可持续资料与日常工作面；H4 才完成产品差异化最小闭环。后续视觉/空间/同步/执行能力必须挂接此链，不能另建平行“演示闭环”。

### 24.2 Canonical IA

一级空间固定为：

```text
Workspace | Library | Evidence | Learning | AI Assets | Settings
```

Search 是全局命令/顶栏和可保存视图；Canvas/Graph/Timeline/Table/Palace 是中央内容视图；Import Center 从 Library/Workspace 进入；Runtime/Delivery/Audit/Machine/Evolution/Agents/WORK-LAB/HERMES 不得成为一级导航。

布局：左侧 Library/Vault/Topic Tree；中央宽主工作区承载 PDF/Markdown/Office/Table/Canvas/Graph/Learning Map/Courseware/Simulation/Palace/AI Asset Editor；右侧按需显示 Outline/Properties/Backlinks/Citations/Annotations/Evidence/Cited AI/Learning Actions/AI Asset Proposal；底部任务条只在导入、转换、索引、同步或失败时出现。

### 24.3 中央工作面模式

| 模式 | 中央内容 | 右侧上下文 |
|---|---|---|
| Read | 原件/派生双视图、页/块定位、高亮 | Outline、Source、Citations、Annotations |
| Edit | Markdown/属性/链接/表格/结构 | Backlinks、Revision、Conflict、Evidence |
| Compare | 多来源、claim/evidence matrix、diff | 支持/反驳、独立性、时效、adjudication |
| Learn | 解释、练习、卡片、复习、路线、Teach Back | 目标、掌握、错因、next review |
| Teach | 课件、讲义、storyboard、演示、rubric | 来源、教学层、反馈、导出 |
| Map | Canvas/Graph/Topic Tree/Learning Map | 节点属性、路径、证据、布局 |
| Simulate | 动画、交互演示、实验、项目步骤 | 参数、目标、结果、rubric、fallback |
| Palace | 2D/2.5D/3D 空间与路线 | Locus、回忆、弱点、路线历史 |
| AI Assets | Memory/Rule/Skill/Standard/Context/Eval | 来源、scope、eval、revision、approve/revoke |

OpenHuman 的价值仅是中央宽工作面、按需上下文和临时任务条；默认中央不是聊天，Memory Tree 在产品中使用 Topic Tree/Knowledge Tree/Learning Map，避免外部项目词直接变成内部品牌。

### 24.4 不同学习表征的晋升门槛

```text
planned → prototype → source-grounded → workflow-integrated
→ installed-verified → released

untested → usability-observed → behavior-observed
→ retention-observed → transfer-observed → controlled-verified
```

一个动画/3D 场景可以作为 `prototype`，但若没有真实学习任务、source anchor、fallback、重启/导出和效果观察，不得宣称“提升学习”。

---

## 25. 动态依赖、环境、语言与 Provider 合同

### 25.1 不锁死版本的六层权威

产品蓝图写行为和边界，不永久指定今天的依赖版本。精确版本只在某次可复现构建/发布中冻结：

| 层 | 权威内容 | 禁止 |
|---|---|---|
| Product Truth | 产品能力、开放格式、用户行为、安全、隐私与非目标 | 第三方 package/model/tool 的永久 pin |
| Compatibility Policy | 支持的平台/profile、兼容范围、最低能力、排除条件、许可/安全阈值、可替代 Provider 族 | 把“latest”当规则；混入本机路径 |
| Candidate Resolution Record | 当次候选、版本、来源、探针、fixture、benchmark、拒绝理由和选择结论 | 无证据自动选择 star/热度最高项 |
| Environment Observation | 本机实际 OS/工具/路径/组件/驱动/WebView2/缓存和 hash；脱敏、gitignored | 反向成为团队规范；进入产品运行时 |
| ReleaseFreeze | 某 exact source tree 的精确语言工具链、包、模型、sidecar、browser、asset、URL/hash/license 和 fallback | 浮动范围、未锁下载、ambient PATH |
| Runtime Capability Attestation | 安装后实际探针、引擎/模型版本、能力、降级、失败、重启和回读 | 仅从 lock 推断能力已经可用 |

生命周期：

```text
declared-range
→ candidates-resolved
→ probed
→ benchmarked
→ selected
→ release-frozen
→ bundled-verified
→ installed-verified
→ released
→ superseded | revoked
```

负向状态：`unavailable`、`incompatible`、`degraded`、`stale`、`revoked`。动态解析只在依赖维护、显式 bootstrap、Provider 评估或 Release 准备任务发生；安装版运行时禁止静默联网取 `latest`、自动升级、自动下载模型或悄悄切换 Provider。

### 25.2 选择与升级流程

```text
能力需求/真实 fixture
→ 发现候选与替代族
→ 许可证/来源/维护/安全/平台过滤
→ API/CLI/sidecar/格式/资源探针
→ 同一 semantic oracle 的质量/资源/失败基准
→ ADR/RDR 选择主 Provider + fallback + kill switch
→ exact revision/hash ReleaseFreeze
→ source/wheel/bundle/installed/restart 资格
→ 漂移/漏洞/上游更新监测
→ upgrade/replacement task
→ canary + rollback 到 known-good freeze
```

升级不是“永不更新”，也不是“永远最新”。当存在更稳定、维护更好、安全修复或效果更优版本时，resolver 重新生成候选；只有同一 fixture/oracle、迁移、性能、许可、bundle 和 rollback 通过后才改下一次 ReleaseFreeze。旧 Release/lock/SBOM/NOTICE 不改写。

### 25.3 分级验证，避免动态治理反而拖慢闭环

| 变更 | 最小验证 |
|---|---|
| 普通传递依赖 | 来源/许可/安全、lock 完整性、install/import/build smoke |
| Parser/Converter/OCR/ASR | 对应真实格式 corpus、semantic oracle、LossReport、取消/失败/资源、installed profile |
| 模型/重 sidecar | 任务准确性、模型/数据许可、CPU/GPU/内存/磁盘、隐私、降级、取消/卸载 |
| UI viewer/renderer | bundle、browser smoke、语义/无障碍/fallback/export，不重跑不相关模型 benchmark |
| 语言工具链/SDK | supported range、clean build、ABI/lock、installed lifecycle；RC 再 full |

普通 PR 不做全候选重新选型；版本研究在独立 maintenance TaskPack 执行。未知或 lock/policy/classifier 本身变化才升级验证范围。

### 25.4 Provider 可替换性

必须定义 Port/Provider 的能力族：

```text
PDF/Text/Layout/Table/Formula
OCR
Office
Web Capture/Extraction
ASR/Media
Markdown/YAML
Search/Vector/Graph/Rerank
LLM/Vision/Embedding
Editor/Renderer/Canvas/Simulation/Spatial
Sync/Export/Adapter
```

核心 schema 不能直接使用某 Provider 私有类型；所有结果投影到版本化中立合同，并保存 provider id/revision、输入 hash、输出 manifest、质量、损失和原始 provider artifact。替换自研版或另一上游时用相同 golden fixture/oracle 验证，不修改用户 canonical 原件。

### 25.5 语言职责按边界固定，未来实现语言按 ADR 选择

| 边界 | 唯一职责 | 禁止 |
|---|---|---|
| Python | Domain、Evidence、Learning、AI Assets、转换编排、迁移、provider 语义验证、评测 | 桌面窗口/installer 生命周期；把 PowerShell 当业务层 |
| Rust/Tauri | desktop shell、WebView、Job Object、loopback/token、路径/窗口/picker、bundle/installer 资源 | 决定 Evidence/学习/AI 资产状态或直接维护业务 schema |
| JS/TS/Node | 当前前端/WebView/构建；具体 viewer/renderer 经 ADR 激活 | 复制 promotion/权限/迁移业务；默认变成后台 runtime |
| PowerShell 7 | Windows 环境发现、bootstrap/build/test/installer qualification 的进程调用、注册表只读检查与诊断薄编排 | 产品业务、Evidence/Capability/Release 决策；修改全局 ExecutionPolicy；安装版 runtime child lifecycle；安装版依赖 |
| SQL | 经 migration/repository 层管理的本地持久化 | UI/sidecar/临时脚本直接改事实库 |
| 可选 Java/C/C++/WASM/其他 | 仅作为经批准的成熟 Provider/sidecar/renderer | 因语言偏好进行全项目重写 |

不进行 Python→Rust、Python→Node 或 Tauri→其他框架的全量重写。只有真实瓶颈、上游集成或平台能力证明需要时，在 Port 后替换一个边界。

### 25.6 Sidecar ABI 与进程边界

外部 Provider/模型/CLI 必须声明：

```text
protocol_version / provider_id / provider_revision
capability_probe / health / self_test
request_id / job / cancel / timeout / resource_budget
input_content_handle / hash / approved_scope
output_manifest / engine / model / version / loss / quality
stable_error_taxonomy
permissions / network_policy / credential_scope
process_owner / port / token / kill semantics
upgrade / rollback / uninstall
license / source / model / asset / hash manifest
```

Sidecar 不得直接读取未授权 Vault、直写 SQLite、自动联网、静默升级、自行晋升 Candidate 或保留未声明副本。桌面端由 Rust 维护进程身份、Job Object、端口/token 和强制退出；Python 负责语义编排、输出验证、Candidate 创建和事务落库；前端不得直接启动 sidecar。

### 25.7 Windows 环境不是硬编码版本表

Windows 构建治理分成：

- `windows-compatibility-policy`：支持的 OS/arch/profile 和所需能力；
- `toolchain-candidates`：当前可评估 Python/uv/Rust/Node/npm/PS/MSVC/SDK/WebView2/NSIS/Tauri/browser/provider 组合；
- `windows-observed`：doctor 发现的个人机事实；
- `release-freeze`：本次 exact tree 的精确组合与 hash；
- `build-provenance/runtime-attestation`：构建和安装后实证。

WebView2 Evergreen 记录兼容范围和实测版本，不伪装为永恒 pin；只有 Fixed Version Runtime 才进入精确冻结。`.python-version`、`rust-toolchain.toml`、`.node-version`、package/Cargo/uv lock 都是解析/构建投影，可随经验证维护 PR 更新，不属于 Product Truth。

本机已有 PowerShell 7 可被 doctor 发现并在兼容时复用；不因“已有”跳过版本/架构/执行能力探针，也不默认全局升级。GPU、CUDA、模型 runtime 都是 optional profile；CPU/无模型核心必须保持可用。

### 25.8 动态替代族（不预选永久赢家）

| 能力 | 候选族示例 | 选择维度 |
|---|---|---|
| PDF baseline/structure | MarkItDown、pypdf/pdfplumber、Docling、Tika、MinerU/Marker/Chandra 等候选 | 数字/扫描、layout/table/formula、Windows bundle、许可、资源 |
| OCR | Tesseract、PaddleOCR、GLM-OCR、其他可审查模型/provider | 中文/多语、版面/公式、CPU/GPU、模型/资产许可 |
| Office | 轻量专用库、Docling、Tika、可选 CLI/provider | 结构、批注/公式/notes、损失、体积 |
| Web | Trafilatura、新spaper/readability、Crawl4AI/Playwright/Firecrawl 等 | 静态/动态、快照、SSRF、登录态、服务/本地边界 |
| ASR | faster-whisper、系统/其他 provider | 时间戳、语言、模型许可、硬件、体积 |
| Editor | CodeMirror、ProseMirror/TipTap、BlockNote、Lexical 等 | Markdown/结构、许可、扩展、无障碍、bundle |
| Canvas/Graph | JSON Canvas 自有中立内核、XYFlow、tldraw/Excalidraw/其他 renderer | 规范保真、未知字段、交互、许可和 export |
| Retrieval | SQLite FTS、sqlite-vec、LanceDB/FAISS/Qdrant/Chroma 等 | 本地、可重建、规模、升级/卸载 |
| Model routing | 薄自有 Port、LiteLLM/其他 SDK | 数据外发、provider 覆盖、错误语义、依赖重量 |
| Learning scheduling | py-fsrs/兼容算法实现 | 历史可解释、迁移、参数、Anki 互操作 |
| 2D/3D/Simulation | 浏览器原生/Canvas/SVG/WebGL/WASM/成熟引擎候选 | 学习任务、fallback、GPU、开放格式、许可 |

表中项目都是候选而非绑定决定；进入 Release 的只有当次 `selected + release-frozen + installed-verified` 项。

### 25.9 新原子任务

| Task | 内容 | 依赖 | 核心验收 |
|---|---|---|---|
| AXW-002D | 跨平台 canonical Compatibility Policy/schema 与版本权威分层 | AXW-004A | Product Truth 无第三方 pin；policy 支持 range/exclusion/profile/substitute；Windows/macOS/Linux/provider 只消费同一合同 |
| AXW-002E | 通用 Provider candidate resolver、probe 与分级 benchmark | 002D、006B、007A、010 | 至少一个 PDF Provider 有选择/拒绝理由；运行时零静默解析；不包含本机工具链观察 |
| AXW-002F | 通用 ReleaseFreeze/rollback/substitute engine | 002E | exact tree 可复现；known-good 可回退；替代项通过同 oracle；平台适配器只生成实例 |
| AXW-007C | 语言边界 Architecture Guard | 004A、005A | 跨层业务复制、PS 业务逻辑、UI/sidecar 直写事实库被拒绝 |
| AXW-007D | Sidecar ABI 与生命周期 | 002D、005A、006B、007C | probe/cancel/timeout/kill/restart/rollback；无默认联网/DB 直写 |

---

## 26. OSS Atlas v4：完整候选图谱与历史账本防删合同

### 26.1 Atlas 的性质与来源分类

本节是按产品能力生成的人类可读投影，不是许可证结论，也不替代完整 machine ledger。所有项目先分四类：

- `O`：公开源码/OSS 候选；只有 exact upstream revision、LICENSE/NOTICE、传递依赖和分发方式完成 RDR 后才可写 `oss_verified`；
- `F`：公开格式、标准、协议或官方 API；兼容它不等于复制产品源码；
- `C`：闭源/商业产品，只允许公开 API/导出互操作或 UX/行为 clean-room 参考；
- `U`：canonical source、许可、模型、资产或可复用组件尚未解决；保留但不得进入发行物。

复用路径：`format/spec → dependency → SDK/API/CLI → replaceable provider → isolated sidecar → fixed-revision fork/vendor → clean-room behavior/fixture → self-developed fallback`。

以下名称来自历史 369 池、101/约 103 去重登记、57 项精选表、历史 8 项 implemented 和今日补充。它们是候选身份快照，不代表今天仍活跃、许可证已确认或已经适合本项目；选用前由 AXW-002D–F/006 重新解析。

### 26.2 Research、文献、来源、证据与评测候选

- 文献/研究：Zotero、GROBID 等公开源码候选；OpenAlex/Crossref 是公开 API 候选；DOI 是公开标识标准；BibTeX、CSL JSON、RIS 是开放/公开交换格式；
- 数据/谱系：OpenLineage、Marquez、DVC、lakeFS；
- AI trace/eval：Langfuse、Phoenix、Opik、OpenInference、OpenTelemetry、Evidently、MLflow、Weave、TruLens、Ragas、DeepEval、Promptfoo、Inspect AI、Giskard、LightEval、EvalScope、lm-evaluation-harness；
- 安全/guardrail：Guardrails、NeMo Guardrails、PyRIT、garak、Presidio、LLM Guard、OpenLIT、OpenLLMetry、Helicone；
- 闭源行为参考：NotebookLM 的 Sources/grounded ask/studio outputs，Readwise Reader 的 source/highlight/review。Zotero 的 collection/item/reader/annotation UX 可作行为参考，但 Zotero 源码候选本身归 `O`，不得放入闭源组。

H1–H4 先实现证据对象、页/块/坐标锚点和引用回跳；H6 做 Zotero/BibTeX/CSL；trace/eval 工具只服务诊断/资格，不成为普通用户知识 UI。

### 26.3 PDF、OCR、Office 与多格式候选

历史解析/OCR 候选：

```text
allenai/olmocr
apache/tika
camelot-dev/camelot
datalab-to/marker
docling-project/docling
facebookresearch/nougat
GROBID/grobid
HKUDS/RAG-Anything
jsvine/pdfplumber
Layout-Parser/layout-parser
microsoft/markitdown
microsoft/table-transformer
ocrmypdf/OCRmyPDF
opendatalab/MinerU
opendatalab/MinerU-Ecosystem
opendatalab/PDF-Extract-Kit
PaddlePaddle/PaddleOCR
py-pdf/pypdf
pymupdf/PyMuPDF4LLM
tesseract-ocr/tesseract
thelosttimes/kreuzberg
Unstructured-IO/unstructured
VikParuchuri/surya
PDF.js
GLM-OCR
Chandra OCR
python-docx
python-pptx
openpyxl
ruamel.yaml
Pandoc
```

替代族：PDF viewer（PDF.js）；baseline converter（MarkItDown/Kreuzberg/轻量库）；rich parser（Docling/Unstructured/Tika）；结构/精度 benchmark（MinerU/Marker/PyMuPDF4LLM/Nougat）；OCR（Tesseract/PaddleOCR/olmOCR/GLM-OCR/Surya/Chandra）；table（Camelot/Table Transformer/Docling/PaddleOCR）；Office（专用轻量库/Docling/Tika）。代码、模型、语言包、字体和示例资产分别审查。

### 26.4 网页、RSS、浏览器与社交来源候选

```text
adbar/trafilatura
AndyTheFactory/newspaper4k
apify/crawlee
browser-use/browser-use
browserbase/stagehand
bytedance/UI-TARS-desktop
D4Vinci/Scrapling
daijro/camoufox
DIYgod/RSSHub
Douyin_TikTok_Download_API
instaloader
TikTokDownload
patchright
XHS-Downloader
mendableai/firecrawl
microsoft/playwright
gallery-dl
MediaCrawler
bilibili-api
Scrapy
Selenium
unclecode/Crawl4AI
twscrape
yt-dlp
```

Trafilatura 是静态正文 baseline 候选；Crawl4AI/Scrapling/Firecrawl/Crawlee 是动态采集替代族；Playwright/Selenium/Stagehand/Patchright/Camoufox 是浏览器执行族。平台采集只进入授权、限量、隔离 Research Provider，并先过 robots/ToS、登录态、SSRF、prompt injection、来源快照和隐私门禁。

### 26.5 音视频、视觉理解、语音与计算机操作候选

```text
PySceneDetect
UI-TARS / UI-TARS-desktop
Demucs
Segment Anything 2
FFmpeg
fish-speech
CosyVoice
SenseVoice
whisper.cpp
GroundingDINO
sherpa-onnx
WhisperX
OmniParser
OpenCLIP
FunASR
OpenVoice
NeMo
MiniCPM-V
OpenCV
InternVL
OS-Copilot
PaddleSpeech
pyannote-audio
Qwen-VL
ShowUI
faster-whisper
yt-dlp
```

ASR/说话人/场景切分/视觉 embedding/目标定位/TTS 分成不同 Provider。UI-TARS、ShowUI、OmniParser、OS-Copilot 属于计算机操作研究，不进入当前知识工作台主线。

### 26.6 PKM、Obsidian、文献与学习生态

源码/格式/API 候选：

```text
Anki
Anytype
AppFlowy
Foam
H5P
Joplin
Kolibri
Logseq
Moodle
Obsidian desktop product（`C`）
Obsidian sample plugin / API types（`O/public_source_pending`）
Obsidian URI / JSON Canvas（`F`）
Obsidian community plugin ecosystem（`U/mixed_ecosystem`）
FSRS4Anki / Py-FSRS
Open edX
Outline
SilverBullet
SiYuan
Notesnook
AFFiNE
Trilium / TriliumNext
Memos
Zotero
OpenHuman
TinyCortex
```

公开互操作：Markdown Vault、JSON Canvas、Obsidian URI、Wiki Links、Frontmatter、BibTeX、CSL JSON、CSV/card exchange、Joplin JEX/Data API、Logseq Markdown/EDN、SiYuan export/API、Zotero API/export。Obsidian 桌面产品保持 `C`；sample plugin/API types 进入 `O/public_source_pending`；社区插件生态整体保持 `U/mixed_ecosystem`，只有逐插件建立独立 RDR 后才能选择。`obsidian-codex-mcp`、`mcp-obsidian` 等可继续登记为桥接候选，但 MCP 连通不等于 Obsidian C4。

闭源 UX/行为参考：Obsidian、Readwise Reader、Tana、Roam Research、Heptabase、Capacities、Notion、NotebookLM。VS Code/Code-OSS、Home Assistant、Anytype 等必须区分上游源码、官方发行物、Logo/资产和云服务，不按产品名整体得出许可结论。CoWork OS、OpenMAIC、EDUKG 等 source 未稳定时标 `unresolved-source`。

### 26.7 Editor、Canvas、Graph、Table 与结构化视图候选

```text
a2ui
AG-UI
Apache ECharts
Automerge
CodeMirror
Cytoscape.js
Excalidraw
Lexical
React
Monaco Editor
Jotai
Zustand
ProseMirror
Radix Primitives
Recharts
shadcn/ui
Tailwind CSS
TanStack Query / Router / Table / Virtual
Tauri
tldraw
BlockNote
Tiptap
vis-network
Vite
XYFlow / React Flow
Yjs
Vega / Vega-Lite
Observable Plot
D3
Mermaid
markmap
JSON Canvas
SVG / Canvas / WebGL
```

编辑器 bake-off 从 CodeMirror、ProseMirror/TipTap、Lexical、BlockNote、Monaco 等选一个主族；JSON Canvas 是文件真相，XYFlow/Excalidraw/tldraw 是 renderer/adapter 候选；图表/Graph/状态/同步分别选型，不把一个 UI framework 写进 Product Truth。

### 26.8 Learning、FSRS、课程与互动内容候选

```text
Anki
FSRS4Anki
Py-FSRS
pyKT
Moodle
Open edX
Kolibri
H5P
marimo
JupyterLite
Pyodide
reveal.js
Slidev
Marp
```

Py-FSRS 是可解释调度 baseline 候选；pyKT 是研究；Moodle/Open edX/Kolibri 是 LMS/离线课程生态，不整体嵌入；H5P/Marimo/JupyterLite/Pyodide、reveal.js/Slidev/Marp 分别属于互动内容、可执行学习与课件替代族。

### 26.9 Visual Teaching、动画、动态解释和仿真候选

```text
TanStack Table
ECharts
Vega / Vega-Lite
Observable Plot
D3
Cytoscape.js
Mermaid
markmap
Excalidraw
reveal.js
Slidev
Marp
H5P
Manim Community
Motion Canvas
Lottie renderer
p5.js
Pyodide
JupyterLite
marimo
Web Animations API
```

候选族：declarative chart（Vega/ECharts）；custom teaching chart（D3/Observable Plot）；concept diagram（Mermaid/markmap/Cytoscape）；slide/courseware（reveal.js/Slidev/Marp）；interactive learning（H5P/p5.js/Pyodide）；animation（Manim/Motion Canvas/Web Animations/Lottie）。任何动画保留 EvidenceAnchor、步骤、输入、输出和静态降级。

### 26.10 Spatial Memory、2D/2.5D/3D/VR/AR 候选

```text
Three.js
React Three Fiber
A-Frame
WebXR
SVG / Canvas / CSS 3D / WebGL
XYFlow / Cytoscape / Excalidraw（2D fallback）
```

canonical 数据是 `SpatialMemoryPackage/Map`，不是引擎 scene。3D 模型、纹理、HDRI、字体、声音和动画均进独立 Asset Ledger；2D map、CSS/Canvas 2.5D、Three/R3F 3D、A-Frame/WebXR immersive 是替代层，不在 H0–H5 预先选择永久赢家。

### 26.11 RAG、Search、Graph、Long-term Memory 候选

RAG/问答/知识平台历史池：

```text
MaxKB
Kotaemon
Haystack
Flowise
LightRAG
MiniRAG
RAG-Anything
VideoRAG
RAGFlow
Khoj
FastGPT
LangChain
LangGraph
LangFlow
Dify
LobeChat
GraphRAG
AnythingLLM
QAnything
txtai
Open WebUI
KAG
HippoRAG
Pathway
Quivr
LlamaIndex
R2R
DSPy
WeKnora
private-gpt
```

图谱/记忆历史池：

```text
Graphiti / Zep
igraph
Kuzu
LanceDB
LangMem
Letta
Mem0
HaluMem
MemOS
Neo4j
NetworkX
Agent Memory Techniques
OpenSPG
rustworkx
Cognee
TinyCortex
Bob's Big Brain Compiler
NOUS OS
sqlite-vec / SQLite-Vector
FAISS / Qdrant / Chroma
```

H1–H3 以 SQLite FTS5、路径和 links/backlinks 为确定性基线；向量、graph、RAG、memory 全是派生 Provider，不得变成第二事实库。H4 可按 benchmark 选择嵌入式向量；H7 才研究 Graphiti/LightRAG/GraphRAG/KAG/Cognee；Agent memory 族默认 `exploration + deferred_retained H10`。

### 26.12 Model、Inference、Embedding、Rerank 与 Training 候选

```text
llama-cpp-python
OpenLLM
LiteLLM
bitsandbytes
llama.cpp
LLaMA-Factory
Optimum
PEFT
Text Generation Inference
TRL
FastChat
MLX-LM
MLC-LLM
LocalAI
TensorRT-LLM
Ollama
Axolotl
Aphrodite Engine
torchtune
SGLang
Triton Inference Server
ExLlamaV2
Unsloth
vLLM
Xinference
Qwen Embedding/Reranker/VL Embedding/VL Reranker/本地生成模型
GLM-OCR 及 OCR/ASR/vision provider 权重
```

模型代码、权重、量化、tokenizer、数据集、模型卡和输出条款逐项登记。H4 只需要可选 embedding/rerank 和薄 Provider；本地 runtime bake-off 后置；大型 serving/training 不抢个人工作台核心。

### 26.13 AI Observability、Evaluation 与 Guardrail 候选

```text
OpenInference
Phoenix
PyRIT
Opik
DeepEval
lm-evaluation-harness
Evidently
Ragas
Giskard
Guardrails
Helicone
LightEval
Langfuse
Presidio
MLflow
EvalScope
garak
NeMo Guardrails
OpenTelemetry
OpenLIT
Promptfoo
LLM Guard
OpenLLMetry
TruLens
Inspect AI
Weave
```

H0 保留最小内部诊断语义；H4 为 Cited AI 建离线 eval；高级 red-team/Agent trace 后置。不能把这些项目变成普通 PR 的固定重型矩阵或默认用户 UI。

### 26.14 Desktop、Storage、Sync、Backup、Lineage 与 Publish 候选

```text
Apache Arrow
sqlite-vec
Automerge
Litestream
Chroma
Dolt
DuckDB
ElectricSQL
PGlite
FAISS
Infinity
DVC
LanceDB
Marquez
Meilisearch
Milvus
OpenLineage
OpenSearch
ParadeDB
pgvector
Polars
PowerSync
RxDB
Qdrant
Tantivy
rclone
restic
Datasette
lakeFS
Typesense
USearch
Vespa
Weaviate
Yjs
Tauri / React / Vite / FastAPI / SQLite FTS5
```

Tauri/SQLite/filesystem 保持当前可复用底盘，但不成为永久技术宗教。H5 先完成备份、恢复、升级、卸载和开放导出；Litestream/rclone/restic 是备份/同步候选；Automerge/Yjs/RxDB/PowerSync/ElectricSQL 属于 H9 协作/同步研究，不能提前侵入 file-first core。

### 26.15 Agent、Protocol、Workflow 与 Durable Execution 候选

Agent/编码工具历史池：

```text
Agno
Aider
Goose
Atomic Agents
UI-TARS-desktop
CAMEL
Cline
Continue
CrewAI
Fast Agent
OpenManus
MetaGPT
Gemini CLI
Google ADK
smolagents
BeeAI Framework
MCP Agent
Mastra
AutoGen
Semantic Kernel
Codex
OpenAI Agents SDK
Swarm
OpenHands
Open Interpreter
SWE-agent
PydanticAI
Qwen Agent
Qwen Code
Roo Code
OpenCode
Bolt DIY
Strands Agents
Tabby
Anthropic Skills / Claude Code / Claude Agent SDK / Claude Code Action
grok-build
TinyAgents / TinyFlows / TinyJuice
Hermes Agent
Quine / AOHP / VeriOS / Self-State Attacks research
```

协议候选：A2A/A2A Python、A2UI、AG-UI、AsyncAPI、FastMCP、JSON Schema、MCP Inspector/Servers/Specification/Apps/Python SDK、OpenAPI、OpenRPC、OpenTelemetry semantics、Agent Client Protocol。

工作流/队列候选：Activepieces、APScheduler、FastStream、Airflow、Dramatiq、Celery、Dagster、Dapr、DBOS Transact、Hatchet、Inngest、Kestra、n8n、Node-RED、Prefect、ARQ、Restate、RQ、Taskiq、Temporal、Trigger.dev、Windmill。

全部保留在 H10/开发工具 Atlas；当前产品只做一个低风险可回滚 Skill proof。编码 Agent 是 Codex 的外部开发参考，不是 Workspace 产品能力。

### 26.16 Security、Permission、Sandbox 与 Supply-chain 候选

供应链/策略/沙箱候选：

```text
Grype
Syft
Trivy
SpiceDB
Wasmtime
Casbin
Cedar
Bubblewrap
Podman
Daytona
E2B
age
Firecracker
SOPS
CodeQL
Gitleaks
gVisor
nsjail
Vault
Kata Containers
Keycloak
Moby
OPA
OpenFGA
OpenSandbox
Bandit
pip-audit
RustSec
Semgrep
Cosign
```

隔离安全研究池：AFL++、angr、RetDec、Capstone、Frida、pwntools、syzkaller、Keystone、LIEF、mitmproxy、MobSF、Ghidra、pwndbg、QEMU、radare2、Rizin、sqlmap、Unicorn、YARA、Volatility、Wireshark、x64dbg、ZAP。

后者只能标 `isolated-lab/reference-only`，不会因存在于历史开源池而获得产品优先级；前者也按本地桌面实际威胁选择，禁止为“全面”引入一套云原生基础设施。

### 26.17 历史 57 项精选表全量映射

57 项必须全部有 canonical row/Horizon/处置，不得用精选表更新覆盖旧记录：

```text
P001 Docling
P002 PaddleOCR-VL / PaddleOCR
P003 GLM-OCR
P004 Crawl4AI
P005 Repomix
P006 MinerU
P007 Marker
P008 Chandra OCR
P009 faster-whisper
P010 LanceDB
P011 sqlite-vec
P012 SQLite-Vector
P013 Qwen Embedding
P014 Qwen Reranker
P015 Qwen VL Embedding
P016 Qwen VL Reranker
P017 Graphiti
P018 TinyCortex
P019 Mem0
P020 Letta
P021 Cognee
P022 LightRAG
P023 OpenSPG / KAG
P024 RAGFlow
P025 Haystack
P026 Bob's Big Brain Compiler
P027 NOUS OS
P028 PydanticAI
P029 LangGraph
P030 TinyAgents
P031 TinyFlows
P032 OpenHuman
P033 CoWork OS
P034 llama.cpp
P035 Qwen local model
P036 LiteLLM
P037 TinyJuice
P038 AutoGen
P039 OpenTelemetry
P040 OpenInference
P041 DeepEval
P042 Ragas
P043 Promptfoo
P044 Inspect AI
P045 Self-State Attacks on Self-Hosted AI Agents
P046 Py-FSRS
P047 pyKT
P048 marimo
P049 H5P
P050 React Flow / XYFlow
P051 MCP Apps
P052 MCP Python SDK
P053 tldraw
P054 AOHP
P055 VeriOS
P056 Quine
P057 Hermes Agent
```

### 26.18 历史 101/约 103 去重候选全量投影

下面逐类保留原清单所有 canonical names；“约数/已核验”只描述历史快照，不继承到当前选择：

- AI 前端/应用：vercel/ai；stackblitz-labs/bolt.diy；
- AI 编码/Agent：sst/opencode；anthropics/claude-code；google-gemini/gemini-cli；All-Hands-AI/OpenHands；cline/cline；Aider-AI/aider；continuedev/continue；QwenLM/qwen-code；RooCodeInc/Roo-Code；xai-org/grok-build；TabbyML/tabby；
- Agent SDK/Skills/编排与研究 Agent：openai/openai-agents-python；pydantic/pydantic-ai；anthropics/claude-agent-sdk-python；anthropics/claude-agent-sdk-typescript；anthropics/skills；microsoft/semantic-kernel；langchain-ai/langgraph；mem0ai/mem0；anthropics/claude-code-action；microsoft/autogen；crewAIInc/crewAI；assafelovic/gpt-researcher；
- LLM/RAG UI 与平台：langgenius/dify；open-webui/open-webui；lobehub/lobe-chat；langchain-ai/langchain；labring/FastGPT；infiniflow/ragflow；Cinnamon/kotaemon；Mintplex-Labs/anything-llm；zylon-ai/private-gpt；QuivrHQ/quivr；khoj-ai/khoj；
- 文档/OCR：microsoft/markitdown；docling-project/docling；Unstructured-IO/unstructured；apache/tika；opendatalab/MinerU；datalab-to/marker；pymupdf/PyMuPDF4LLM；PaddlePaddle/PaddleOCR；
- Web/Browser：mendableai/firecrawl；microsoft/playwright；browser-use/browser-use；browserbase/stagehand；unclecode/crawl4ai；apify/crawlee；D4Vinci/Scrapling；adbar/trafilatura；AndyTheFactory/newspaper4k；
- PKM/文献：toeverything/AFFiNE；laurent22/joplin；logseq/logseq；siyuan-note/siyuan；zotero/zotero；Obsidian desktop（`C`）；obsidianmd/obsidian-sample-plugin 与 obsidianmd/obsidian-api（`O/public_source_pending`）；Obsidian URI/JSON Canvas（`F`）；Obsidian community plugin ecosystem（`U/mixed_ecosystem`，逐插件独立 RDR）；
- 检索/数据库/图：facebookresearch/faiss；qdrant/qdrant；chroma-core/chroma；lancedb/lancedb；asg017/sqlite-vec；sqliteai/sqlite-vector；neo4j/neo4j；kuzudb/kuzu；networkx/networkx；getzep/graphiti；topoteretes/cognee；
- 模型/可观测/评测：BerriAI/litellm；langfuse/langfuse；promptfoo/promptfoo；OpenTelemetry 生态；xai-org/grok-1；
- 工具/迁移/代码图谱：Delgan/loguru；hynek/structlog；CodeGraphContext/CodeGraphContext；davidrothlis/declarative-schema-migration；PrefectHQ/prefect；
- 安全研究：NationalSecurityAgency/ghidra；x64dbg/x64dbg；mitmproxy/mitmproxy；sqlmapproject/sqlmap；radareorg/radare2；MobSF/Mobile-Security-Framework-MobSF；frida/frida；Gallopsled/pwntools；zaproxy/zaproxy；VirusTotal/yara；wireshark/wireshark；capstone-engine/capstone；unicorn-engine/unicorn；angr/angr；pwndbg/pwndbg；volatilityfoundation/volatility3；avast/retdec；google/syzkaller；keystone-engine/keystone；AFLplusplus/AFLplusplus；lief-project/LIEF；rizinorg/rizin；qemu/qemu。

### 26.19 历史 8 项 implemented 的真实语义

LiteLLM、Crawl4AI、Trafilatura、MarkItDown、Langfuse、NetworkX、sqlite-vec、Loguru 的 `historical_implemented` 只表示当时存在依赖或代码证据；它们必须重新投影为 `integrated-unqualified/source-qualified/installed-qualified/release-qualified`，不能自动继承为公开安装版支持。

### 26.20 369/101/57/8 防删合同

完整账本不在叙事文档逐行复制；完整性由来源快照、hash、reconciliation 和 machine gate 证明：

1. 每条原始候选拥有永久 `candidate_id`；
2. 禁止物理删除；重复通过 `aliases/duplicate_of/superseded_by` 合并；
3. 上游改名/迁移/归档保存旧 URL、名称和快照；
4. 不相关项标 `deferred` 或 `rejected-with-reason`；许可未知标 `license-pending`；source 未解标 `unresolved-source`；
5. 新候选只追加或建立 supersession，不重写历史来源；
6. Narrative/roadmap 没展示不构成删除授权；
7. 只有 Owner 批准的 ledger migration 可以修正错误记录，被合并项仍保留 tombstone/provenance；
8. 历史 count 是 reconciliation baseline，不是未来总数上限。

统一字段：

```text
candidate_id
canonical_name / canonical_url
source_nature: oss_verified | public_source_pending | format_api | closed_ux | unresolved
source_sets: [369, 101, 57, implemented_8, later_research]
source_ids[] / aliases[]
capability_domains[] / alternative_family
integration_modes[] / target_horizon
license_state / selected_revision
technical_state / installed_state / release_state
evidence_refs[]
duplicate_of / superseded_by
rejected_reason / history[]
```

状态：

```text
discovered → normalized → source-resolved → license-pending
→ evaluated → selected → integrated-unqualified
→ source-qualified → installed-qualified → release-qualified

旁路：reference-only | deferred | isolated-lab | rejected-with-reason
     | superseded | upstream-archived | unresolved-source
```

机器完整性不再断言“总数永远等于 369/101”，而断言：原 369/101/57/8 每条均有 canonical row 或 duplicate/tombstone mapping；新增允许增长；任何减少都有 merge/tombstone/provenance；所有 active 项有 RDR，未固定 revision 不产生许可证结论。

AXW-002B 拆分：

- `002B-1` 冻结四套来源快照与 hash；
- `002B-2` canonical URL/name/alias 去重；
- `002B-3` reconciliation report；
- `002B-4` Atlas 从 ledger 动态生成，禁止第二套手工名单；
- `002B-5` PR 输出 added/changed/superseded/rejected diff；
- `002B-6` 删除 candidate/source/provenance 直接失败；
- `002B-7` active 项 RDR/exact revision gate；
- `002B-8` historical implemented 与当前 S0–S5 分栏；
- `002B-9` 每个当前能力族至少有 primary/fallback/deferred alternatives；
- `002B-10` 叙事文档只引用 Atlas snapshot/query，不充当完整 369 行账本。

最终规则：允许改变状态、Horizon、复用方式和替代关系；不允许丢失项目身份、来源、历史判断和证据链。

---

## 27. v4 终局 Horizon 与正式长期 Program

§10 是 H0–H5 的当前产品 Release Spine；本节补全 H6–H10，二者不是两套路线。所有 Horizon 以 capability gate 为准，具体 semver/日期可在 `CURRENT_PRODUCT_PLAN` 中调整。

### 27.1 H0｜Truth、门禁可信、Windows 工程底座与真实 PDF 生存

H0 分成两个不可混淆的退出条件：

- **产品修复 exit：** `AXW-000 → AXW-003`，并由 `AXW-002A + AXW-011A → AXW-010 → AXW-012` 完成源码、wheel/bundle、已安装版真实 PDF→重启回读；`AXW-001A → AXW-004A/C` 是并行 Truth Spine，不是 AXW-012 的前置。
- **v0.5.1 Release exit：** 在产品修复 exit 上增加 `AXW-002D + AXW-007A/B + AXW-008A/B + AXW-009A/C/D`，以及本次实际进入 bundle 的组件 RDR、许可 lane、NOTICE/SBOM/分发义务证据，再执行 exact-SHA full qualification。

当前云端 PR #68 的两处依赖真相测试必须修复/替代；PR #69 独立审查；PR #70 只抽取事实，不恢复 B/C/R/HERMES 权威。`AXW-004B/D/E/F`、完整顶层许可组合研究、369 回填、`AXW-007C/D`、`AXW-008C` 跨机离线 kit、Office 全矩阵、Obsidian、动画和 3D 都不得隐式阻塞产品修复 exit；只有实际进入当次 bundle 的依赖合规是 Release 硬门。

### 27.2 H1｜RawAsset、Evidence 基础、PDF Reader 与早期学习证明

Required：AXW-005A、AXW-015A/B/C/D、AXW-020A/B/C、AXW-021、AXW-022、AXW-024A/B、AXW-025、AXW-030A/B、AXW-090A/B。退出时至少能从真实 PDF/网页选区生成 Claim/EvidenceCandidate，与第二来源比较，点击回原页，并完成一次可重启的 pretest→retrieval→delayed/transfer→Teach Back 小切片。

### 27.3 H2｜Office/OCR/Web/表格/图片/媒体基础

Required 以当期宣布的格式逐项激活 AXW-011B/D、023A-E；没有 installed evidence 的格式不进 UI ready 状态。音视频 ASR 可作为后续 profile，不因 file picker 接受扩展名而宣称支持。

### 27.4 H3｜Obsidian C4、Editor/Renderer 与日常 Workspace

Required：AXW-040–045、030B/C、090C/K，以及 Markdown/YAML/links/attachments/search/editor/JSON Canvas/conflict/rollback/installed roundtrip。Obsidian 是第一高保真纵切，不是终局或逐像素克隆。

### 27.5 H4｜Evidence-bound Human/AI 双学习最小闭环

Required：AXW-005A、AXW-009C、AXW-015A/B/C/D、AXW-020A/B/C、AXW-021、AXW-022、AXW-024A/B/C/D、AXW-025、AXW-030A/B、AXW-050、AXW-051A/B/C/D、AXW-052A/B/C/D/E、AXW-053A/B/C/D、AXW-054、AXW-055、AXW-095A/B/C。Structured Views、basic course/route/2D representations 可作为当期 Scope Ledger snapshot 的显式 required；完整动画/仿真/3D 不是前置。

### 27.6 H5｜稳定单用户本地工作台

Required：`AXW-009C → {AXW-055, AXW-009D}`，再由 AXW-045 + AXW-055 + AXW-009D + AXW-094A/B + AXW-060 聚合；大库/大 PDF、无障碍、低配/无 GPU、升级/迁移/备份/恢复/卸载、开放导出、exact-SHA full qualification。AXW-094A/B 是 exchange/backup/restore 的唯一实现 owner，AXW-060 只做稳定资格。仓库/包/协议/数据目录改名各自是可回滚任务，不以一次 bulk rename 阻塞产品。

### 27.7 H6｜Research/Knowledge Production、生态 Adapter、课程与 Visual Teaching

正式激活：Zotero/BibTeX/CSL、Anki 完整交换、Joplin/Logseq/SiYuan/Readwise 逐项；ResearchProject/ResearchPackage、KnowledgeVersion/Conflict/Publication；LearningRoutePackage 四层；Course/Project/Research workspace；课件/讲义/演示/图解；Editor/Renderer 扩展；macOS/Linux 可移植性研究。

### 27.8 H7｜高级研究助手、完整学习法、动画、仿真与 2.5D

正式激活：多文档/引文/矛盾/综述候选、来源 Radar、完整 HL-01–16、学习行为评估、animation/dynamic explanation、Simulation & Practice Lab、2.5D Spatial Memory、本地模型/检索/图谱 Provider 评测。所有生成仍为 candidate。

### 27.9 H8｜3D/VR/AR、同步、设备端与受控执行研究

3D/VR/AR Spatial Memory 的受控原型与学习效果研究是 `binding_long_term + experimental_later` 的正式长期能力，达到 usability/behavior/retention/transfer 证据并经 Owner 决策后逐步晋升。多设备加密同步、browser clipper、PWA/mobile companion、一个受控 execution adapter 可在此阶段研究；不恢复 Agent-first 产品。

### 27.10 H9｜SDK、签名扩展、可选协作、Publish 与 Community

在单用户数据/权限/同步合同稳定后，开放第三方 Adapter/Renderer SDK、签名扩展、静态/课程发布、小团队/师生评论审核和 RoutePackage 候选分享。所有服务都是可选，不改变本地原件与离线可用。

### 27.11 H10｜远期 Exploration

通用 Planner、多 Agent、Agent marketplace、自治 workflow/evolution、实时多人，以及超出 H8 受控原型/效果研究范围的 VR/AR 大规模部署与泛化研究，只能作为新的 Owner Decision 后的 Exploration。它们保留历史候选和可复用协议，但没有当前交付承诺，也不能把产品改名为 OS/Agent 平台；这不降级 AXW-090H 的正式长期身份。

### 27.12 正式长期 Program 目录

#### AXW-090｜LER、Editor/Renderer、Visual Teaching 与 Spatial Memory

已有 090A–I 继续保留，并新增：

- `090J` Fact/Memory/Visual/Teaching 四层 + `LearningRoutePackage`；
- `090K` `EditorShell/RendererContract`、draft/autosave/undo/revision/diff/freeze/fork/export；
- `090L` World→Palace→Room→Locus→Object→Route、stable position、move-map、SceneGraph 分离；
- `090M` Visual/Courseware/Simulation/Spatial package 的 manifest、fallback、asset license、开放导出；
- `090N` 课程/学习视图和真实学习行为/效果采集边界。

#### AXW-091｜Research Discovery 与 Knowledge Production

Children：

- `091A` ResearchProject/Question/DiscoveryCandidate/SourceCollection；
- `091B` authorized search/connectors/watch/quarantine；
- `091C` ResearchFinding/Package、文献/来源/冲突矩阵；
- `091D` KnowledgeUnit/Version/Entity/Relation/Collection/Domain；
- `091E` draft→candidate→reviewed→active→superseded/deprecated/archived；
- `091F` KnowledgeConflict/Publication/export/引用/撤销；
- `091G` source/claim/evidence/knowledge scope-aware Search 和 why-recalled。

#### AXW-092｜Full Human Learning Methods

AXW-051 只完成最小产品化；092 逐组扩展 HL-01–16：`092A` diagnosis/prerequisite/route；`092B` cognitive load/memory encoding/interleaving/deliberate practice；`092C` metacognition/calibration/error attribution；`092D` personal profile/daily-weekly consolidation/decay/relearning；`092E` transfer/project/portfolio/effect evaluation。每种方法声明适用内容、限制、EvidenceAnchor、交互事件、效果指标和 fallback。

#### AXW-093｜Course、Project、Research Workspace 与 Output

`093A` 定义 Course/Theme/Project/ResearchSession/LearningSession、Objective/Route/Decision/Artifact/Rubric/Reflection/Portfolio/OutputProof、ProjectPackage；`093B` 交付 workspace UX；`093C` 交付 session/rubric/reflection；`093D` 交付 package/portfolio/output proof。它为学习、研究、创作、设计、软件学习和项目实践提供模板，不依赖 Agent 执行，也不成为商业 SKU。

#### AXW-094｜Exchange、Backup、Restore、Sync 与 Publish

AXW-094A/B 是 H5 exchange/backup/restore 的唯一实现 owner，依赖 AXW-015A/B/C/D 和对应数据合同；AXW-060 只消费并资格化其输出。

- `094A` WorkspaceExchangeManifest/Package、schema/checksum/license/source；
- `094B` backup/verify/candidate restore/diff/rollback；
- `094C` device/revision/origin/sync/conflict 合同预留；
- `094D` optional Git/WebDAV/rclone/restic/provider；
- `094E` encrypted multi-device queue/merge；
- `094F` static knowledge/course publish、browser clipper/PWA/mobile companion；
- `094G` optional team/comment/review/community candidate，固定为 `exploration + experimental_later H9`，不因父 Program 获得 binding 承诺。

H5 只要求 A/B；C 可以早定义，D–G 按 H8–H9 激活。

#### AXW-095｜Provider、Model 与 Resource Governance

Children：`095A` ProviderProfile/CapabilityProbe/HardwareProfile（依赖 002D/010）；`095B` DataEgressPermission（依赖 005A）；`095C` Model/AssetManifest（依赖 006B）；`095D` Budget/Rate/Latency/PromptRevision/CallAudit/Fallback/Degrade（依赖 A–C）；`095E` EvalResult/Revoke（依赖 D）。Settings 内可见；不建立 Models/Agents 一级控制台。

#### AXW-096｜Platform Portability

`096A` 共享 platform contract；`096B` macOS；`096C` Linux；`096D` PWA/mobile companion research。Windows 为 H0–H5 主资格；macOS/Linux 使用共享 domain/data/UI contracts 分期适配；PWA/mobile 只作 companion，不复制三套业务逻辑。每个平台有独立 toolchain、installer、data path、permission、update/uninstall、fixture 和 ReleaseFreeze。

#### AXW-097｜SDK、Extension 与 Community

`097A` versioned Adapter/Renderer/Import/Export SDK；`097B` 签名与 permission manifest；`097C` sandbox/kill switch/兼容矩阵；`097D` 模板/RoutePackage 分享与 provenance。未满足 H5/H8 前 `planned`，不显示空 marketplace。

#### AXW-098｜Optional Controlled Execution Adapter

依赖 AXW-005A PermissionDecision 与 AXW-015A/B/C/D。`098A` adapter contract；`098B` permission/dry-run/sandbox/checkpoint/trace/cancel/rollback；`098C` installed reversible proof。把旧 Planner/Tool/MCP/Workflow 机制限制在可选消费者，只读已批准 Context/AI Assets；通用自治和多 Agent 不属于本 Program 的 children。

#### AXW-099｜Solution Profiles 与模板

`099A` profile schema；`099B` 个人终身学习、学生、教师、研究者、专家知识转 AI、创作/设计、软件学习、项目实践模板；`099C` installed user-flow qualification。它们只是组合模板与用户流，不生成新产品、仓库、品牌、数据库或商业版本。

---

## 28. Capability/Requirement/Scope/TaskGraph 防漂移合同

### 28.1 必须进入仓库的机器真相

```text
docs/truth/CAPABILITY_ATLAS_V1.yaml
docs/truth/REQUIREMENT_TRACE_V1.yaml
docs/current/SCOPE_LEDGER_V1.yaml
docs/current/TASK_GRAPH_V1.yaml
docs/current/UPSTREAM_LEDGER_V2.yaml|jsonl
docs/decisions/SCOPE_CHANGE_DECISIONS/
```

`CAPABILITY_ATLAS` 决定能力是否被规划；`REQUIREMENT_TRACE` 把用户/历史要求映射到能力；`SCOPE_LEDGER` 记录当前 Release 激活范围；`TASK_GRAPH` 记录原子执行依赖；`UPSTREAM_LEDGER` 保存候选；`ScopeChangeDecision` 记录降级/退休/替代。它们不能合成一张含混总表。

### 28.2 Capability 最小字段

```yaml
capability_id:
canonical_name:
pillar:
product_layer:
user_outcomes: []
authority_status: binding_core|binding_long_term|exploration|retired
roadmap_state: critical_now|core_next|formal_later|experimental_later|deferred_retained|retired_positioning|rejected_with_record
technical_state:
learning_evidence_state:
interop_state:
license_state:
activation_horizon:
required_current: false
release_required_for: []
dependencies: []
entry_gate: []
exit_evidence: []
objects: []
views: []
fallbacks: []
origin_requirement_ids: []
source_refs: []
supersedes: []
superseded_by: []
retirement_decision:
```

四条状态轴不得折叠：

```text
technical: planned→prototype→source-grounded→workflow-integrated→installed-verified→released
learning evidence: untested→usability→behavior→retention→transfer→controlled-verified
interop: C0→C5
license/distribution: unknown→reviewed→approved-for-lane→packaged-compliant
```

### 28.3 Requirement Trace

每条用户明确要求、历史蓝图能力和后来裁决都保留稳定 `requirement_id`、原话/摘要、日期、source reference、current verdict、capability IDs、task IDs 和 supersession。模型总结、Issue、PR 或 TaskPack 不能悄悄覆盖用户要求；发生冲突按规范轴裁决并保留两条记录。

### 28.4 Scope Ledger

当前 Release 只激活最小集合：

```text
required_current
optional_current
deferred_next
binding_long_term
exploration
retired
```

`binding_long_term` 不阻塞当前 Release，但不能删除；`exploration` 没有承诺日期，不能宣传；`required_current` 的降级/移除必须有 Owner `ScopeChangeDecision`。当前最小闭环失败时，未来能力可以研究但不能消耗 Release Spine 的主要交付资源。

### 28.5 TaskGraph

每个 active child TaskPack 必须映射：

```text
requirement_id + capability_id + Horizon
+ one user action/result
+ exact dependencies
+ entry/exit evidence
+ rollback
+ required_current flag
```

Graph 必须无环、无不存在依赖、无父/子完成语义混用、无 `future child` 隐式阻塞当前 Release。Program 使用 `program_status: active`；Release 只判断 `required_current_children`。

### 28.6 Anti-delete / Route-drift Gate

机器门禁至少拒绝：

1. 直接删除 capability、requirement、task、reference、alias 或 upstream candidate ID；
2. 把 `binding_long_term` 改成不存在而无 tombstone/Owner decision；
3. rename 未保留 alias/supersession/migration；
4. `required_current` 被移除/降级而无 ScopeChangeDecision；
5. active task 无 requirement/capability/user action/Release Spine；
6. Product Truth 出现第三方精确版本或具体个人机路径；
7. ReleaseFreeze 使用浮动版本、运行时静默下载/解析 `latest`；
8. 未登记 sidecar、模型、资产、字体或 fixture 进入 bundle；
9. WORK-LAB/HERMES 获得当前产品/执行权；
10. LER/Research/Knowledge/Learning/Sync/Provider 等长期 Program 被摘要删除；
11. 未到 Horizon 的能力生成默认导航占位或冒充 supported；
12. visual/simulation/spatial projection 缺 anchor/provenance/loss/fallback/export/license；
13. Agent/Runtime/Job 数替代产品用户流；
14. parent Program 因未来 child 未做被错误判“整个项目失败”，或因当前 child 完成被错误判“终局完成”。

纯 truth/atlas 文档变更只跑 schema/truth lint/Owner review；运行时 schema、capability claim、release identity、dependency policy 变化按影响面升级；RC/Release 才 full。防漂移不能再次制造每个 PR 全量 9-job。

### 28.7 新原子治理任务

| Task | 范围 | 验收 |
|---|---|---|
| AXW-004D | Capability Atlas + Requirement Trace + Scope Ledger | 当前、长期、探索、retired 全有稳定 ID/source |
| AXW-004E | Anti-delete + TaskGraph + Route-drift Gate | 直接删除失败；带 Owner decision 的 retire/supersede 通过 |
| AXW-004F | 文档/Atlas/Task/Upstream 投影生成 | Narrative 与 machine truth 无第二套手工名单 |
| AXW-180 | 定期 Blueprint Completeness Review | 每个 Release/季度输出 added/activated/deferred/superseded/retired diff，不重做无变化审计 |

### 28.8 Truth 变更的权威边界

- Product Truth 决定项目是什么；Capability Atlas 决定完整能力范围；Current Plan 决定当前做什么；
- 当前 main/installer 只能否定“已实现”，不能用旧代码名改变定位或删未来能力；
- 上游更新可改变 Provider 选择，不改变用户数据合同；
- 用户明确的新决定可以改任何路线，但必须生成 supersession/ScopeChangeDecision；
- 大模型不得以“聚焦”“降复杂度”“当前不做”为由物理删除长期蓝图。

---

## 29. v4 补全 Program Cards 与 Codex 可执行入口

本节补全 §13 未展开的横切 Program。全部父卡只能用于规划；Codex 每次只执行一个 child、一个 branch、一个 PR、一个 frozen tree。

### 29.1 AXW-006｜OSS License Compatibility & Distribution Compliance

**依赖：** AXW-000、004A；与 PDF 实现并行，不阻塞已批准的现有依赖。

| Child | 内容 | 验收 |
|---|---|---|
| 006A | 顶层 LICENSE/依赖组合、R-P/R-C 或其他适合个人研究项目的 composition decision | Owner 选择；不凭“非商业/GitHub 可见”猜许可 |
| 006B | local-lab/public-source/public-binary/network lane + LicenseProfile | 每个代码/模型/数据/字体/图标/fixture 可分别批准 |
| 006C | LICENSES/、NOTICE、SPDX SBOM、modification/source bundle | exact installer 内容可反查 upstream/revision/license/hash |
| 006D | dependency/vendor/fork/sidecar/source-copy 目录与门禁 | 未登记源码/模型/资产不能进入 build |
| 006E | 自研替换 Port/fixture/migration/rollback | 同 semantic oracle 可替换；旧 Release 义务不改写 |

### 29.2 AXW-007｜Windows Environment Policy, Doctor & Release Freeze

**依赖：** AXW-000；下一次无 sidecar 的 H0 bundle 前只要求 AXW-007A/B；C/D 按实际语言/sidecar 影响面激活。

| Child | 内容 | 验收 |
|---|---|---|
| 007A | read-only doctor + Environment Observation | 无 secret/私人资料；准确报告 OS/语言/工具/MSVC/SDK/WebView2/NSIS/Provider/锁/缓存问题 |
| 007B | Windows toolchain candidate/observation adapter、ReleaseFreeze instance 与 build provenance | 消费 AXW-002D canonical schema，不重定义 Compatibility Policy/resolver；本机观察与当次冻结精确区分 |
| 007C | 语言边界 Architecture Guard | UI/PS/sidecar 直写事实库、跨层业务复制被拒绝 |
| 007D | Sidecar ABI/lifecycle | probe/cancel/timeout/kill/restart/rollback；无静默网络/升级/DB 写入 |

### 29.3 AXW-008｜Windows Bootstrap & Offline Cache

**依赖：** 007A/B、002D；每个下载对象来自 ReleaseFreeze/approved cache manifest。

| Child | 内容 | 验收 |
|---|---|---|
| 008A | 薄 PS wrapper + bootstrap/cache engine | online 只从批准来源下载并验 hash；系统级变更停为 Owner Action |
| 008B | content-addressed cache + cached-only | cache miss 给确定对象 ID；零联网 fallback |
| 008C | portable offline kit | 明确区分同机缓存与跨机 kit；manifest/license/hash 完整 |

008C 是正式后续增强，不隐式阻塞 PDF；H0 bundle 只要求当期 `required_current_children`。

### 29.4 AXW-009｜Windows Build Profiles & Exact-SHA Qualification

**依赖：** AXW-003、AXW-007A/B、AXW-008A/B；有 sidecar 或语言边界变化时再增加 AXW-007C/D；Release 另依赖当期产品能力。

| Child | 内容 | 验收 |
|---|---|---|
| 009A | 单入口 dev/test/bundle profiles | `-NoProfile`、幂等、native exit、脱敏 JSON；复杂规则在可测试模块 |
| 009B | Windows bug corpus | 空格/中文/长路径/编码/文件锁/端口/WebView2/进程/SQLite/portable |
| 009C | clean exact-tree bundle provenance | 拒 dirty、ambient runtime、浮动 dependency、toolchain drift；hash 可回读 |
| 009D | clean installer qualification | install→当期真实资料流→restart→WM_CLOSE/force-kill→uninstall；零孤儿/端口/数据泄漏 |

依赖边固定为：`AXW-009C → AXW-055` 与 `AXW-009C → AXW-009D`；AXW-055 负责已安装产品能力流，AXW-009D 负责 installer/shell lifecycle，二者可并行且互不依赖；AXW-060 同时聚合两者，禁止形成 055↔009D 环。

### 29.5 AXW-090～099 的激活规则

- `090` 永久 active Program；每个 Release 只选相应 Horizon 的 children；
- `091–093` 是 `binding_long_term + formal_later`；`094A/B` 是 `binding_core + core_next H5`，`094C–F` 是 `binding_long_term + formal_later`，`094G` 是 exploration；`095A–C` 的最小 provider/egress/manifest 合同随 H4 成为 binding core，`095D/E` 为 H7 binding long-term；首次激活前先建对象/用户流/exit evidence，不直接写完整系统；
- `096A–D` 与 `099A–C` 为 `binding_long_term + formal_later`，其中 `096D` 按 H8 companion 合同激活；`097A–C` 为 `binding_long_term + formal_later H9`，`097D` community sharing 为 `exploration + experimental_later`；`098A–C` 为 `exploration + experimental_later`。没有 Horizon/Owner 激活与依赖满足时，任何项都不建空导航、空 API 或假 capability；
- 所有 child 进入 active plan 前必须先做 RDR/Provider 决策，证明成熟复用项为何选/不选；
- 任何 future child 都不允许进入 H0–H5 的隐式 `needs`。

### 29.6 每个原子 TaskPack 的固定模板

```text
task_id / title
product_truth_digest
baseline commit/tree + dirty state
requirement_ids / capability_ids / Horizon
one user action/result
scope / explicit non-scope
dependencies and required_current
reuse candidates / RDR / exact selected revision
license/distribution lane
data/schema/migration/security impact
real RED fixture + semantic oracle
implementation steps
affected local gates
installed/restart/roundtrip evidence when applicable
rollback/kill switch
completion report fields
```

### 29.7 Definition of Ready

任务只有在以下条件满足时才能写代码：最新 main/PR/CI/Release 已冻结；Product Truth digest 有效；用户动作明确；依赖无环；fixture 合法；RDR/许可/Provider 边界足够；当前非目标写清；一个 patch owner；rollback 可行。否则只允许完成准备 child，不跨包实现。

### 29.8 Definition of Done

```text
真实 RED → 最小实现 → GREEN
→ 受影响本地 Gate 一次
→ exact-head cloud Gate 一次
→ 用户界面/安装/重启/往返证据（若 capability 需要）
→ before/after SHA/tree + artifact hash
→ capability/ledger/taskgraph 状态更新
→ rollback 验证 + 剩余风险
```

无代码/依赖/policy/tree 变化不重复同一 full 审计；失败先定位失败 Gate，不重跑全部成功 job。正式 Release 才执行 full exact-SHA/tree、installer、asset/download hash 回读。

### 29.9 Owner Action/停止条件

远端 repo rename、branch protection、正式 Release、顶层重许可、签名证书、访问真实个人 Vault/账号、管理员级工具安装、自动出机/同步或激活 retired/exploration 路线需要用户新增授权。Codex 在边界前停止并给最小 Owner Action，不借机引入 WORK-LAB 或外部执行控制面。

### 29.10 当前唯一启动序列

```text
AXW-000
→ AXW-003 Gate verdict hotfix
→ AXW-002A + AXW-011A
→ 修复/替代 PR #68 的依赖真相与真实 PDF oracle
→ AXW-010
→ AXW-012 installed PDF survival
```

并行但不阻塞 PDF：`001A → 004A/C/D/E`、`006A/B`、`007A/B`。后台但不阻塞：`002B 369/101/57/8 reconciliation`、`008C offline kit`、`090D+` 等未来 children。

当前最小面完成后按两条 Spine 推进：产品证明 Spine 到 AXW-055；开放互操作 Spine到 AXW-045；二者与 Windows installed/full evidence 汇合于 AXW-060。

用户可直接给 Codex：

```text
按 ArcheAxis Workspace Final Master TaskPack v4 执行 AXW-000；
只完成该原子包并冻结最新云端事实，不跨入下一包。
```
