# ArcheAxis Workspace 项目真相总档案与 Codex 最终主任务包 v3.0

> 中文产品名：元枢工作台
> 英文产品名：ArcheAxis Workspace
> 简称：ArcheAxis
> 文档日期：2026-08-09
> 文档性质：Truth Reset 合并前的迁移决策源、未来蓝图、命名合同与 Codex 执行入口
> 适用仓库：`DTALEX66/Cognitive-Loop-OS`（历史仓库名，产品名不沿用）
> 执行主体：Codex
> 状态：待作为 Truth Reset PR 的输入；本文本身不宣称代码已实现。AXW-001A、AXW-004A/004C 合并后，由仓库 `docs/truth/**` 接管规范权威，本文转为 frozen evidence/historical

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

这份 v3 总包覆盖并裁决此前的对话、蓝图、审计、开源调研和任务包。它不是把历史材料全部继续执行，而是把它们归入四类：

1. 当前绑定决策；
2. 可复用工程资产；
3. 仅作研究证据的历史材料；
4. 已被明确推翻或延期的污染项。

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
- OpenHuman 只吸收中央宽主工作区、左右按需上下文、底部临时任务条和其 Memory Tree 组织思想；产品内独立映射为 Topic Tree / Learning Map。中央承载文档、PDF、Office、Canvas，而不是 Agent 聊天。GPL 源码不直接复制进核心。
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
2. Truth Reset 合并前：本 v3 总包；合并后：仓库 `docs/truth/PRODUCT_POSITIONING_V3` 及 Naming/Evidence/Authority contracts；
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
- 3D/VR、企业协作、通用自动化平台；
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
| 豆包 | Visual Teaching/Spatial Memory 与核心定位有张力 | 采纳降级建议；保留 exploration，不阻断 v1.0 |
| 豆包 | 外部能力吸收已结束的文档表述需要统一 | 驳回广义禁令；改为合法复用优先、逐 Adapter/revision/license 评估 |
| DeepSeek | README 缺许可证、无签名 Release、生产 CORS/Auth 需清晰 | 纳入 AXW-005；实际配置与 LICENSE 状态由 Codex 基于最新 tree 复验 |

外部审计只作为输入，不拥有路线权威。凡与当前代码或用户最新定位冲突，以当前证据和本 v3 裁决为准。

---

## 3. 产品真相与边界

### 3.1 唯一名称合同

| 层级 | 当前名称 | 规则 |
|---|---|---|
| 中文产品 | 元枢工作台 | 面向用户、文档、安装器 |
| 英文产品 | ArcheAxis Workspace | 唯一英文全名 |
| 简称 | ArcheAxis | UI 空间有限时使用 |
| 产品类别 | Local-first Knowledge & Learning Workspace | 不再写 Agent OS |
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

### 3.6 非目标

v1.0 前不建设：

- 通用 Agent OS；
- 多 Agent 编排；
- 插件市场；
- 企业协作平台；
- 社交知识网络；
- 3D/VR；
- 通用 Workflow Automation；
- 以云端模型为必需条件的核心功能。

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
| Visual Teaching Studio | `Visual Learning Lab`，exploration |
| Interactive Simulation Lab | `Simulation Research Track`，exploration |
| Spatial Memory Palace/2.5D/3D/VR | `Spatial Memory Research`，deferred |

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
- GPL/AGPL/自定义许可整仓默认只作行为研究、独立进程或等待许可决定；
- 闭源产品只通过公开格式、API、导出和独立行为研究兼容；
- 所有旧 `implemented` 在没有 installed evidence 时降为 `integrated-unqualified`。

### 9.5 v1.0 前开源组件激活矩阵

以下是产品路线裁决，不替代精确 revision 的许可证审查。表中“许可注意”只用于选择集成方式；真正进入 PR 前必须从固定 tag/commit 重查 LICENSE、依赖、模型、资产和 fixture 条款。

| 能力 | 候选/标准 | 当前用途 | 集成方式 | 当前波次 | 许可/边界裁决 |
|---|---|---|---|---|---|
| PDF 原件阅读 | Mozilla PDF.js | reader、页、选择、搜索、渲染 | 前端依赖/封装 | v0.6 | 优先直接依赖；固定版本、NOTICE |
| 基线转换 | Microsoft MarkItDown | 轻量 PDF/Office baseline | Python dependency + format extras | v0.5.1 | 现有集成不等于 extras 随安装包；必须 installed qualification |
| 富文档结构 | Docling | layout/table/formula/reading order | optional provider | v0.6–0.7 | 代码与模型/下载物分别审查；不得成为基础安装唯一引擎 |
| PDF 文本校验 | pypdf / pdfplumber | 页数、文本、fixture 语义交叉校验 | 测试/轻量 provider 候选 | v0.5.1 | 选一个最小依赖；不要同时堆叠无职责组件 |
| PDF 高难基准 | MinerU | 中文复杂 PDF 质量对照 | 隔离 benchmark/待许可 | 研究 | 自定义条款未决时不进核心 |
| PDF 高难基准 | Marker | 精度对照 | 隔离 benchmark | 研究 | GPL/模型条款；不进宽松核心 |
| OCR baseline | Tesseract | 轻量、离线 OCR | optional system/bundled provider | v0.7 | 安装器要验证 binary/language pack，而非只测 Python wrapper |
| 中文复杂 OCR | PaddleOCR | 版面、表格、公式、中文扫描 | optional sidecar | v0.7 | 代码、模型卡、模型文件分别锁定；资源预算和卸载清理 |
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
| 文献互操作 | BibTeX/CSL JSON/Zotero API/export | 文献、附件、引用 | Adapter | v1.1 | 格式/API 优先；不复制 Zotero 客户端 |
| 卡片互操作 | Anki/open card exchange | v0.9 只做基础 CSV/开放卡片导入导出；完整 APKG/API/media/history 在 v1.2 | Adapter | v0.9/v1.2 | Anki 客户端代码不并入；交换格式与 py-fsrs 分离 |

### 9.6 相关软件与开源项目的最终处置

| 项目/生态 | 对当前产品的真实价值 | 处置 |
|---|---|---|
| Obsidian | 第一高保真开放文件工作流 | C0–C4 核心；格式/行为兼容，不复制闭源本体 |
| OpenHuman | 中央工作面、Memory Tree、上下文布局 | UX 洁净参考；GPL 源码不进核心 |
| Zotero | PDF 批注、collection、citation、研究来源 | v1.1 首个研究 Adapter；API/开放格式 |
| Anki | 卡片交换、复习行为 | v0.9 py-fsrs + 基础 CSV；v1.2 AXW-071 完整 Adapter |
| Joplin | Markdown/resources/notebook/export | v1.2 Adapter；API/导出优先 |
| Logseq | page/block ref、outliner、Markdown/EDN | v1.3 读取/转换 Adapter；AGPL 源码不合入 |
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

### Horizon 6 — v1.1–v1.4：生态 Adapter

顺序：Zotero/BibTeX/CSL → Anki → Joplin → Logseq → SiYuan → Readwise → 其他公开 API/导出。

每个 Adapter 独立 capability、loss、fixture、roundtrip、安装和 Release，不以“一次全面兼容”捆绑发布。

### Horizon 7 — v1.5：本地智能研究与学习

候选：多资料证据对照、引用检查、长期学习模型、课程/研究模板、可控自动整理、多模型路由。仍须服从来源、权限和可回滚。

### Horizon 8 — v2+

只有 v1.x 本地单用户、数据合同、权限和扩展签名稳定后，才评估第三方 Adapter SDK、加密同步、小团队协作和受控 Agent。插件市场、通用 Agent OS 不自动回归主线。

### Exploration（不参与当前 Release 退出门槛）

- Visual Learning Lab；
- Interactive Simulation；
- Spatial Memory/Memory Palace/2.5D/3D/VR；
- 通用 Agent、多 Agent、自治演化、Foundry/Marketplace。

JSON Canvas、Graph 和 Learning Map 仍属于核心开放知识组织能力，不因为 Spatial Memory 被延期而延期。

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
AXW-000 云端冻结
  ├─ AXW-001 Truth Reset
  ├─ AXW-002 OSS Ledger v2
  ├─ AXW-003 CI/Release Evidence Repair
  ├─ AXW-004 Naming/Authority/Reference Contract
  └─ AXW-005 Security/License/Signing Truth
          ↓
AXW-010 Capability Truth + AXW-011A Real PDF Fixture Corpus
          ↓
AXW-012 Installed PDF Survival (v0.5.1)
          ↓
AXW-020 Core Data Contracts
     ├─ AXW-021 Persistent Import/Conversion
     ├─ AXW-024 Evidence Core/Cross-validation
     └─ AXW-030 OpenHuman-inspired Shell
          ↓
AXW-022 PDF Reader & Evidence Anchors
→ AXW-025 Early Human Learning Proof
          ↓
AXW-023 Office/OCR/HTML Matrix (v0.7)
          ↓
AXW-040 Vault Kernel C0/C1
→ AXW-041 Markdown/YAML Fidelity
→ AXW-042 Workbench C2
→ AXW-043 JSON Canvas
→ AXW-044 Safe Write C3
→ AXW-045 Obsidian C4 Qualification
          ↓
AXW-050 Cited AI (PDF/Evidence slice; no C4 dependency)
→ AXW-051 Human Learning/FSRS/Teach Back
→ AXW-052 AI Learning Assets Core
→ AXW-053 Controlled Bidirectional Transformation
→ AXW-054 Comparative Learning/AI Use Evaluation
          ↓
AXW-060 Stable v1.0 Qualification
├─ AXW-080/081/082 Repository/Local/Distribution Naming Migration
└─ AXW-070+ Ecosystem Adapters
```

可并行边界：

- AXW-002 与 AXW-003 可在 AXW-000 后并行；
- AXW-030 可在 AXW-020 合同冻结后与 AXW-021/022 并行，但 BFF/API owner 单一；
- AXW-024 可与 Import/UI 实现并行，但对象命名和 promotion policy 只能有一个 owner；
- AXW-041/043 的 parser spike 可并行，只能在 AXW-040 stable identity 合并后落主线；
- AI/学习不得早于 EvidenceAnchor、EvidenceBundle、reader 和 search；
- AXW-025 早期学习证明不等待 Obsidian C4；AXW-051 是后续产品化，不依赖 Cited AI；
- 生态 Adapter 不得早于 C4 和 Adapter contract。

### 12.1 Program Card 与原子 Child Task

以下父 ID 是 Program/验收总卡，**不得直接建立一个大 PR**。Codex 只能执行一个 child ID；每个 child 一个 branch/PR/frozen tree。未列为 Program 的 AXW 卡默认是原子 TaskPack，若开工时 scope 超过一个可独立回滚用户结果，必须先补 child split。

| Program | 原子 child | 单 PR 范围 |
|---|---|---|
| AXW-001 Truth Reset | `001A` Positioning/README/AGENTS/current truth projection；`001B` legacy/deferred archive；`001C` manifest/UI/capability wording projection | 先 001A；移动历史和用户表面投影分包 |
| AXW-002 OSS Ledger | `002A` schema + 当前 PDF/reader RDR bootstrap；`002B` 369/101/57/8 后台映射；`002C` license/revision/status gate | PDF 只依赖 002A；002B 不阻塞产品 |
| AXW-004 Naming/Authority | `004A` truth/naming/evidence/authority schemas；`004B` aliases/reference/doc metadata；`004C` digest + Truth-Drift Gate | 本文在 001A+004A/C 后退役 |
| AXW-005 Security Truth | `005A` config/permission/tool-risk；`005B` product license/SBOM/NOTICE；`005C` signing decision/contract | 未签名可明确声明，不冒充已签名 |
| AXW-011 Fixture Corpus | `011A` PDF；`011B` Office/image/HTML；`011C` Vault/Canvas；`011D` media | 每类 fixture/license/oracle 独立 |
| AXW-020 Core Contracts | `020A` Source/RawAsset/Import；`020B` Conversion/Derived/Loss；`020C` Anchor/Index/Revision | migration 按对象族分包 |
| AXW-023 Format Matrix | `023A` DOCX；`023B` PPTX；`023C` XLSX/CSV；`023D` OCR；`023E` HTML | 每个 format/profile 独立 installed evidence |
| AXW-024 Evidence Core | `024A` schema/migration；`024B` validation/promotion policy；`024C` compare UI；`024D` revision/expiry/export | 024A/B 可在 v0.6；C/D 在产品化阶段 |
| AXW-030 Workspace Shell | `030A` clean-room ADR/layout shell；`030B` canonical IA/routes；`030C` responsive/accessibility/activity | 不与 reader/data migration 混包 |
| AXW-051 Human Learning | `051A` objectives/practice model；`051B` FSRS/history；`051C` mastery/Teach Back；`051D` basic CSV card exchange | 完整 Anki 是 AXW-071 |
| AXW-052 AI Assets | `052A` schemas/revisions；`052B` promotion/conflict/freshness；`052C` Library UI；`052D` low-risk Skill executor；`052E` export/revoke | 通用 Planner 不进入任何 child |
| AXW-053 Bidirectional | `053A` TransformationProposal；`053B` Human→AI；`053C` AI→Human；`053D` installed end-to-end | 每方向独立候选/审查证据 |

父卡只有全部 required children 通过时完成；parent 名称不得被拿来创建 branch、commit 或“全部完成”回执。

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
**粒度：** Program Card；只执行 AXW-002A/B/C child
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
**粒度：** Program Card；只执行 AXW-004A/B/C child
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
3. 将 AI Skill 的 permissions/side effects/approval/rollback 纳入同一安全模型；
4. 外部网页/论坛/文件引入 SSRF、path、prompt-injection、credential/log redaction 合同；
5. 明确仓库代码许可证：如果缺有效 LICENSE，Owner 必须选择；在此之前 README 只能写未声明，不能推定开源许可；
6. 记录第三方 NOTICE/SBOM 和 portable binary build flags；
7. 为 code signing 制定决策：证书/identity/secret custody/timestamp/revocation/unsigned fallback；未实施时 Release 明示 unsigned；
8. 增 production example config，但 local desktop 不被迫开启无意义的远程认证。

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
**依赖：** AXW-020

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

**Reuse Decision：** OpenHuman/Obsidian/Zotero/VS Code 仅作 clean-room UX 参考；输出 ADR 和差异表，不引入 GPL/闭源源码或资产。

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
**依赖：** AXW-005、AXW-024A/B、权限/评估基础；不依赖 Cited AI

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
**依赖：** AXW-024B、AXW-051 required children、AXW-052 required children

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
**依赖：** AXW-025、AXW-051 required children、AXW-052 required children、AXW-053D

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

### AXW-060｜v1.0 稳定性、安装、迁移与开放导出

**Horizon：** H5
**优先级：** P0 Release
**依赖：** H0–H4 所有 release-driving 卡

**目标用户结果：** 普通用户可以长期使用、升级、备份、卸载和迁移 ArcheAxis，而不理解内部 Runtime。

**实施：**

1. 10k/50k notes、GB 级 assets、large PDF 性能档位；
2. accessibility、keyboard、screen reader、contrast、zoom、小窗口；
3. low-memory/no-GPU profile；
4. database/data-dir migration、backup/recovery；
5. installer upgrade/repair/uninstall，用户数据默认保留；
6. open export：原件、Markdown、attachments、Canvas、annotations/evidence sidecar、CSV/JSON；
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
3. Zotero API/BibTeX/CSL JSON/export，不复制 AGPL 客户端；
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
9. **Priority：** Visual/Simulation/Spatial 只能 exploration/deferred，不进 active Release required capability/一级导航；
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

无法映射，或会在当前 Horizon 重新引入通用 Agent、重型 Runtime、视觉/空间演示、跨项目控制面者，默认拒绝进入 active plan。改变本条只能由用户/Product Owner 明确修改 Product Positioning v3，并产生新的 truth digest。

---

## 15. 开源与外部能力快速引用索引

此表是执行入口，不是许可证法律意见。每次 selected/integrated 前仍要固定 tag/commit 并重查 LICENSE、NOTICE、模型、权重、字体、图标、fixture、二进制构建选项和传递依赖。

| 项目/规范 | 官方入口 | 快照许可/边界 | 当前模式 |
|---|---|---|---|
| OpenHuman | https://github.com/tinyhumansai/openhuman | GPL-3.0 | UX/behavior clean-room only |
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
| Marker | https://github.com/datalab-to/marker | GPL-3.0，models separate | benchmark only |
| PyMuPDF | https://github.com/pymupdf/PyMuPDF | AGPL/commercial dual | 默认排除，除非商业许可/整体决策 |
| Repomix | https://github.com/yamadashy/repomix | MIT | 工程/代码来源 Adapter 后置 |
| Crawl4AI | https://github.com/unclecode/crawl4ai | exact tag/browser deps 复核 | isolated web worker 后置 |
| Zotero | https://github.com/zotero/zotero | AGPLv3 | API/BibTeX/CSL/export only |
| Anki | https://github.com/ankitects/anki | AGPLv3-or-later | exchange/API only |
| py-fsrs | https://github.com/open-spaced-repetition/py-fsrs | MIT | Human Learning scheduler |
| Joplin | https://github.com/laurent22/joplin | AGPL-3.0-or-later；assets separate | JEX/Markdown/API Adapter |
| Logseq | https://github.com/logseq/logseq | AGPL-3.0 | Markdown/EDN clean-room Adapter |
| SiYuan | https://github.com/siyuan-note/siyuan | AGPL-3.0 | export/API external Adapter |
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
| `03_AXOS_开源能力总表.xlsx` | 57 项深入候选；需按 v3 重新分 Horizon |
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

执行 AXW-003 的最小 hotfix：Gate ID/aggregator/full-attestation/依赖 real-format classification。原因是当前 PR #68 已出现核心测试失败而总门禁成功；不修会污染后续所有完成证据。

### 第 2 组 Truth PR 序列

先执行 AXW-001A 的 Product Positioning/README/AGENTS truth projection PR；再分别执行 AXW-004A（machine contracts）与 AXW-004C（Truth-Drift Gate），AXW-001B/001C、004B 后续按独立 PR 完成。它们都不同时改 runtime、包名、远端仓库或数据目录。PR #70 不原样合并。

### 第 3 组开源与 fixture PR 序列

先执行 AXW-002A 的 schema + PDF 当前上游 RDR bootstrap；再用独立 branch/PR 执行 AXW-011 真实 PDF corpus。历史 369/101/57/8 回填由 AXW-002B 后台进行，不阻塞 PDF。

### 第 4 个产品修复序列

```text
AXW-010 Capability Truth
→ AXW-012 Installed PDF Survival / v0.5.1
→ AXW-020 RawAsset/Data Contracts
→ AXW-021/022/024/030
```

PR #68 应 rebase/supersede 成 AXW-012，不以空 PDF fixture 和源码环境变绿合并；#69 可独立审查；#70 仅抽取真实问题后关闭/替代。

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
| KnowledgeBase 下一步深化方案 | `libfile_5ab4b3c7a83c819194d33ff65293efd0` | 知识流程历史研究；按 v3 裁决 |
| 旧 HERMES Master TaskPack | `libfile_e3d20e3c5db481918e114a9accc0187e` | 历史任务证据；writer 权限作废 |
| 元枢系统应用界面展示.png | `libfile_659e80cf25d881919cdb825fc5e6f57` | 旧界面视觉/信息密度参考，不作当前 IA 权威 |
| 暗色知识管理仪表盘界面.png | `libfile_8cae373a7d548191b68737409596cc42` | 视觉研究；治理 dashboard 不作为默认产品面 |
| ArcheAxis OS V3.0/V3.1 docs | `libfile_1b9ef0421ad881919cfc8ae3d800a6ac`, `libfile_871a17e6aed88191810cec30da5226a7` | 人类学习/AI 学习/视觉/空间旧重型愿景；核心机制保留，OS/重型表面延期 |

豆包审计以 `EXT-AUDIT-DOUBAO-20260809`、DeepSeek 审计以 `EXT-AUDIT-DEEPSEEK-20260809` 分别作为 `external_reference` 进入 §2.8；每条 claim/verdict/evidence 独立记录。它们不互相构成代码佐证，也不覆盖当前云端行为和 Product Positioning v3。

### 21.1 云端事实入口

- Repository: https://github.com/DTALEX66/Cognitive-Loop-OS
- Baseline commit: https://github.com/DTALEX66/Cognitive-Loop-OS/commit/492fac5982c693eb668d31cc51a6a59bac83b7a1
- Release v0.5.0: https://github.com/DTALEX66/Cognitive-Loop-OS/releases/tag/v0.5.0
- PR #68: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/68
- PR #69: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/69
- PR #70: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/70

这些 URL 只证明本文审计时的来源；活动状态执行前由 AXW-000 重查。
