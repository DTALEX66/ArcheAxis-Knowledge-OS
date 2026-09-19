# ArcheAxis Knowledge

# R6 全链路吸收优先 · Local Green 收敛总任务包

**建议 Plan ID：** `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`
**性质：** 全项目重新收敛、全链增强、成熟能力吸收优先、本地 Green 持续验证
**目标仓库：** `DTALEX66/ArcheAxis-Knowledge-OS`
**执行对象：** Codex / DSH / Hermes / 其他获授权工程执行器
**模型品牌不是权限边界。所有执行器遵守同一任务图、同一权威、同一验收。**

---

# 0. 任务总原则

本任务不是继续堆叠旧模块，也不是重写 ArcheAxis。

目标是在保留已经正确建立的核心架构前提下，将全部历史成果、当前 R5 已实现能力、成熟开源能力、本地模型、知识治理、人类学习、机器学习、课件生成、多格式、检索、记忆、研究、桌面产品与迁移能力统一收敛成一个真正可持续运行的系统。

执行总原则：

> **Absorb First · Integrate Second · Build Last**

优先顺序固定为：

1. 查现有 ArcheAxis 是否已经实现；
2. 查历史 legacy 是否已有成熟实现；
3. 查已登记外部共享工具/模型；
4. 查当前成熟开源项目、SDK、CLI、库、协议、Sidecar；
5. 能合法、稳定、低耦合吸收的直接吸收；
6. 不能直接吸收则使用 Adapter / Provider / Worker / Sidecar；
7. 只有确认没有合适成熟实现，或接入代价明显高于独立实现时，才允许自研；
8. 自研必须登记 `Capability Gap`，说明为什么不能复用。

禁止“为了技术纯洁”“为了统一语言”“为了看起来原创”而重复自研成熟能力。

---

# 1. 当前 Owner 最新裁决——最高优先级

以下为本任务包最高层 Owner 决策；与任何旧任务包、旧 Handoff、旧 Release 路线冲突时，以本节为准。

## 1.1 GitHub 主线取消产品版本推进语义

GitHub `main` 从现在开始表示：

> **持续开发主线 / Local Green Development Line**

不再把 `main` 描述为：

* 当前公开产品版本；
* 下一个发布版本；
* v0.6.15；
* v0.7.0；
* 新 Release Candidate。

历史 `v0.6.14`：

* Tag 保留；
* GitHub Release 保留；
* Release Evidence 保留；
* SHA / assets / SBOM / checksum 保留；
* 不重写；
* 不删除；
* 不冒充当前 `main`。

源码和构建系统因为包管理规范必须存在的技术版本，不属于产品版本。

允许使用类似：

`0.0.0.dev0+g<source-sha>`

或 Git-derived build identity。

但不得因此创建新的产品版本。

---

# 2. Release 全面冻结

未经 Owner 后续明确授权：

**禁止：**

* 新 Git tag；
* 新 GitHub Release；
* 新产品版本号；
* `v0.6.15`；
* `v0.7.x`；
* 新公开 Release Asset；
* 自动 Release；
* 因测试方便而发布；
* 因 CI 通过而发布；
* 因 Green Candidate 通过而发布。

原 `.github/workflows/release.yml` 可作为历史发布能力保留，但必须确保不会因为普通开发自动发布。

此前规划中的：

`vnext-release.yml`

不再是当前目标。

当前目标改为：

# Local Green Qualification

只有满足本任务最终 Owner Gate 后，才允许由 Owner 决定是否重新开启 Release 工作。

---

# 3. Local Green 是唯一真实运行基线

权威本地运行位置：

`D:\All projects\ArcheAxis.Knowledge.Green-x64`

当前 Green 保留现有 `v0.6.14` 历史发布身份。

但其内部程序允许不断通过新的本地 Green Candidate 原位升级。

正确生命周期：

```text
GitHub main
    ↓
开发 / 修复 / 吸收
    ↓
本地精确 SHA Build
    ↓
Local Green Candidate
    ↓
独立 staging 验证
    ↓
首次使用真实闭环
    ↓
restart readback
    ↓
migration / rollback 验证
    ↓
备份现有 Green Runtime
    ↓
原位替换本地 Green Runtime
    ↓
再次启动 / 重启 / 数据读回
    ↓
成为新的本地 Green 基线
```

这不是 Release。

本地 Green Identity 至少记录：

```text
distribution = local-green
public_release_base = v0.6.14
source_commit = <exact SHA>
source_tree = <tree SHA>
build_timestamp
runtime_manifest_digest
published = false
```

禁止把 Local Green maintenance identity 写成产品版本。

---

# 4. 本机路径权威不得改变

首先读取：

`docs/SHARED_RESOURCE_PATH_INDEX.md`

现有权威资源：

* `shared_models`

  * `D:\All projects\Model library`

* `shared_tools`

  * `D:\All projects\OS External Configuration`

* `green_application`

  * `D:\All projects\ArcheAxis.Knowledge.Green-x64`

* `green_material_library`

  * `D:\All projects\资料库`

* `project_test_corpus`

  * `D:\All projects\ceshi`

* 项目：

  * `D:\All projects\ArcheAxis-Knowledge-OS`

开发输出统一：

`<repo>/.project-local/`

禁止：

* 猜目录；
* 从 PATH 猜工具；
* 重复下载已存在模型；
* 复制共享模型库进仓库；
* 复制整个外部工具链进项目；
* 把 `资料库` 当测试数据；
* 把 `ceshi` 当真实用户资料；
* 访问未授权 E 盘；
* 为了测试修改 HOME / CODEX_HOME 等全局环境。

---

# 5. 正式技术架构继续保留，不推倒

以下历史架构裁决继续有效：

```text
Avalonia / C#
    ↓
产品 UI + Supervisor
    ↓
Loopback HTTP Contract
    ↓
Rust Core
    ↓
Rust Domain / Application / API
    ↓
Rust WriterActor
    ↓
Canonical SQLite
```

Python：

```text
Rust Core
    ↓ stdio / bounded protocol
Python Capability Worker
```

Python Worker 负责：

* parsing；
* OCR；
* ASR；
* embedding；
* reranking；
* VLM；
* local model inference；
* research provider；
* specialized computation。

Python Worker：

**禁止直接写 Canonical SQLite。**

Avalonia：

**禁止直接写 Canonical SQLite。**

第三方 Sidecar：

**禁止拥有 ArcheAxis Canonical Truth。**

Legacy Python / React / Tauri：

继续作为：

* behavior oracle；
* migration donor；
* capability donor；
* recovery/reference surface。

不恢复为新产品权威。

---

# 6. ArcheAxis 最终定位

ArcheAxis 不是普通 RAG。

不是 Obsidian 克隆。

不是通用 Agent Runtime。

不是 WORK-LAB 的子模块。

正式定位：

> **本地优先的人机双向学习、可信知识、经验沉淀与能力成长系统。**

它最终负责沉淀：

* 文件；
* 文档；
* 图片；
* 音视频；
* 代码；
* 项目；
* 个人经验；
* 学习结果；
* 错误；
* 修正；
* 方法；
* 机器执行经验；
* 研究结果；
* 专业领域知识；
* 课程；
* 学习资产；
* 可复用 Skill。

未来：

```text
ArcheAxis
    ↓ Knowledge / Learning / Experience API
WORK-LAB
DESIGN-LAB
```

WORK-LAB 和 DESIGN-LAB 不建立并行长期 Knowledge Truth。

执行结果、项目经验、失败、修正最终返回 ArcheAxis 成为 Candidate / Experience / Skill。

---

# 7. Knowledge Admission 模型全面修正

废止：

> “没有外部 Evidence 就不能进入 Knowledge。”

继续执行 SUP-004 的真实含义：

**证据是知识属性，不是知识准入门槛。**

Knowledge Source 至少支持：

```text
personal_experience
personal_note
personal_definition
project_observation
external_document
authoritative_reference
derived_inference
machine_candidate
imported_legacy
research_result
```

个人知识、经验、判断、项目复盘：

可以直接进入系统。

例如：

```text
source_type = personal_experience
owner = human
external_evidence = none
status = accepted
confidence = high
```

合法。

机器生成：

```text
source_type = machine_candidate
status = candidate
```

即使附带很多链接，也不得自动 Verified。

Knowledge Object 独立维护：

```text
source_type
owner
status
support_level
confidence
risk_level
valid_from
valid_to
supersedes
superseded_by
```

高风险专业领域在“现实决策使用”阶段要求当前权威依据，不影响知识本身保存。

---

# 8. Canonical Knowledge 与 Derived Capability 分层

必须永久保持：

```text
Canonical Truth
= ArcheAxis Rust SQLite
```

以下全部只能是可重建投影或外部能力：

* Vector index；
* Graph index；
* LightRAG；
* Graphiti；
* MemOS；
* Cognee；
* external KB；
* embeddings；
* reranking；
* AI summary；
* course rendering；
* generated quizzes；
* generated slides。

任何第三方项目不得成为：

> 第二 Canonical Knowledge Store。

---

# 9. 建立 Capability Absorption Registry

新增唯一能力吸收登记。

任何新能力开发前必须查询 Registry。

每项至少包含：

```text
capability_id
capability_name
current_internal_implementation
legacy_donor
upstream_project
upstream_commit_or_release
license
model_license
runtime_requirement
local_resource_requirement
absorption_mode
authority_boundary
data_boundary
benchmark
fallback
status
replacement_candidate
reason_not_absorbed
```

`absorption_mode` 仅允许：

```text
DIRECT_DEPENDENCY
VENDORED_COMPONENT
CONTRACT_ADAPTER
PYTHON_WORKER
SIDECAR
ALGORITHM_DONOR
UX_DONOR
REFERENCE_ONLY
SELF_BUILD_GAP
```

同一个职责只允许一个默认主实现。

其他实现：

* fallback；
* benchmark；
* optional provider；
* donor。

禁止四套 Memory、三套 RAG、四套 Knowledge Graph 同时成为默认产品路径。

---

# 10. 第一批必须重新评估的成熟能力

以下不是“全部强制安装”，而是最高优先 Capability Donor Pool。

## Learning / Tutor

### DeepTutor 1.6.x

旧固定 `v1.5.17` 已过时。

重新审计当前 1.6.x：

重点吸收：

* Reading；
* Source-grounded learning；
* Courses；
* Books；
* Mastery Path；
* Question Bank；
* Learning Plugin；
* Visualize；
* Video Learning；
* Content Workspace；
* recoverable sessions；
* Skills；
* Knowledge integrations。

DeepTutor 保持 Sidecar / capability provider。

不得成为 Canonical Truth。

---

## Adaptive Learning

### OpenTutor

重点吸收：

* Learning Block schema；
* adaptive workspace；
* FSRS integration；
* cognitive load；
* adaptive difficulty；
* question types；
* review prioritization；
* knowledge graph based learning ideas。

---

## Domain / Knowledge Component

### LearningMAP

重点吸收：

* Knowledge Component Skill Bank；
* prerequisite graph；
* diagnosis；
* mastery-driven lesson；
* Pedagogy Skill；
* Socratic；
* Feynman；
* Scaffolding；
* quiz→diagnosis→lesson→review；
* cross-session learning memory。

这是 `Domain Learning Pack` 的重点结构供体。

---

## Course / Courseware / Simulation

### OpenMAIC

重点吸收：

* Course DSL；
* course planning；
* slides；
* quizzes；
* interactive learning；
* PBL；
* simulation；
* visualization；
* voice/video；
* agent course editing；
* reusable course skills；
* renderer architecture。

优先吸收 SDK / DSL / Renderer / Skill / artifact model。

不整体替换 Avalonia。

---

## Multimodal Parsing

### RAG-Anything

重点吸收：

* multimodal parsing；
* PDF；
* Office；
* image；
* table；
* equation；
* audio；
* video；
* MinerU/Docling adapter pattern。

Canonical raw object、hash、loss、job receipt 继续由 ArcheAxis 控制。

---

## Retrieval / Graph

### LightRAG

角色：

`Derived Retrieval Projection`

吸收：

* graph retrieval；
* vector retrieval；
* mixed retrieval；
* reranker；
* multimodal；
* citation；
* evaluation hooks。

---

### Graphiti

角色：

`Temporal Knowledge Projection`

吸收：

* valid_from / valid_to；
* episodic facts；
* temporal replacement；
* supersession；
* fact evolution。

非常适合：

个人经验变化、项目方法演进、行业标准更新。

---

## Agent Experience Memory

### MemOS

角色：

`Machine / Agent Experience Memory`

吸收：

* memory lifecycle；
* feedback correction；
* hybrid retrieval；
* memory cubes；
* L1 trace；
* L2 policy；
* L3 world model；
* Skill crystallization。

流向必须是：

```text
Machine Experience
    ↓
MemOS
    ↓
Lesson / Skill Candidate
    ↓
ArcheAxis Review
    ↓
Accepted Knowledge / Skill
```

MemOS 不直接提升 Canonical Knowledge。

---

## Knowledge Workspace UX

### WeKnora

吸收：

* Folder Tree；
* chunk editing；
* revision；
* diff；
* rollback；
* metadata；
* task progress；
* API scope；
* knowledge workspace interaction pattern。

---

## 综合参考

Cognee：

主要做：

* benchmark；
* graph/memory算法供体；
* ontology参考；
* session distillation参考。

不设置为第二 Memory 主系统。

---

# 11. Local Model Pool

禁止继续使用：

> “一个本地模型解决所有任务。”

建立：

`Local Model Capability Pool`

首先从：

`D:\All projects\Model library`

读取 Registry / manifest。

不扫描无关目录。

不重复下载。

模型岗位：

```text
general_tutor
reasoning
coding
vision
embedding
reranking
multimodal_embedding
multimodal_reranking
ocr
asr
tts
classification
document_layout
```

当前重点候选包括：

```text
Qwen3 4B
Qwen3 8B
Qwen3-VL 4B
Qwen3 Embedding 0.6B
Qwen3 Reranker 0.6B
Qwen3-VL Embedding
Qwen3-VL Reranker
SenseVoice
faster-whisper
PaddleOCR
Tesseract
```

不得仅凭 benchmark 选择。

必须在本机：

RTX 5060 8GB
64GB RAM
i5-14600KF

测量：

* VRAM；
* RAM；
* latency；
* context；
* task quality；
* cold start；
* concurrency；
* crash；
* Windows compatibility。

模型只是 Provider，不拥有产品权威。

---

# 12. Domain Learning Pack

这是 R6 的核心新增抽象。

不能再把所有学科都变成：

```text
PDF
→ Summary
→ Flashcard
→ Quiz
```

新增：

```text
DomainLearningPack
```

最低结构：

```text
domain_id
ontology
knowledge_components
prerequisites
learning_objectives
pedagogy
lesson_templates
activity_templates
assessment_types
rubrics
mastery_rules
tools
renderers
model_profile
evidence_policy
risk_policy
fallbacks
```

---

# 13. 不同领域必须允许不同学习形态

## 数学 / 物理

支持：

* formula；
* derivation；
* proof；
* graph；
* geometry；
* simulation；
* step checking；
* symbolic calculation；
* mistake diagnosis。

工具优先于纯 LLM 判断。

---

## Programming

支持：

* editor；
* runnable code；
* unit tests；
* debugging；
* trace；
* refactor；
* project tasks；
* hidden test evaluation。

模型评分不能替代真实执行。

---

## Design

支持：

* image comparison；
* composition；
* layout；
* typography；
* color；
* visual hierarchy；
* reference board；
* artifact critique；
* rubric；
* revision comparison。

---

## Language

支持：

* listening；
* ASR；
* pronunciation；
* dialogue；
* shadowing；
* dictation；
* vocabulary FSRS；
* grammar correction。

---

## History / Humanities

支持：

* timeline；
* people graph；
* map；
* primary sources；
* perspective comparison；
* essay；
* argument structure。

---

## Engineering

支持：

* diagram；
* formula；
* parameter；
* simulation；
* troubleshooting；
* SOP；
* case analysis。

---

## Law / Medicine / Other high-risk domains

知识可以保存。

现实决策使用必须额外检查：

* jurisdiction / date；
* current authoritative source；
* guideline / law revision；
* risk disclosure。

---

## Personal Experience / Professional Practice

允许：

* experience cards；
* project review；
* failure cases；
* decision trees；
* SOP；
* heuristics；
* personal standards；
* skill distillation。

无需强制外部 Evidence。

---

# 14. Learning Engine 重新定义

Human Learning 不只是 FSRS。

完整学习链至少覆盖：

```text
Learning Goal
↓
Knowledge Components
↓
Prerequisite Diagnosis
↓
Pre-test
↓
Learning Path
↓
Lesson
↓
Activity
↓
Practice
↓
Teach-back
↓
Assessment
↓
Error Diagnosis
↓
Mastery Update
↓
FSRS / Review
↓
Cross-session Reflection
↓
New Learning Path
```

Mastery 与 Truth 永久分离：

> 用户答对，不代表知识是真。

> 知识是真，不代表用户掌握。

---

# 15. Machine Learning / Machine Growth

Machine side 不得只保存 Task Receipt。

增加：

```text
MachineExperience
Method
ToolUsage
Failure
Correction
Retest
Lesson
SkillCandidate
CompetenceMeasurement
```

机器成长流程：

```text
Knowledge
↓
Machine Task
↓
Outcome
↓
Failure / Success
↓
Evaluation
↓
Reflection
↓
Experience Memory
↓
Lesson Candidate
↓
Skill Candidate
↓
Human / Rule Review
↓
Accepted reusable Skill
↓
Future Task
↓
Retest
```

禁止将：

“模型自己说学会了”

写成 Machine Competence。

---

# 16. 课件和学习资产成为正式一等对象

新增：

```text
LearningArtifact
```

类型至少支持：

```text
note
book
lesson
slide_deck
quiz
flashcard
simulation
interactive
visualization
coding_lab
project
case_study
timeline
concept_map
audio_lesson
video_lesson
worksheet
exam
teachback_session
```

每个 Artifact 必须能回溯到：

* Knowledge；
* Domain Pack；
* renderer；
* model/tool version；
* generation config；
* learner context。

但个人经验型 Knowledge 不要求虚构外部来源。

---

# 17. 多格式能力必须从“Partial”向真实 Complete 推进

当前历史矩阵：

`0 complete / 14 partial / 2 custody-only`

不得通过降低验收要求把 Partial 改成 Complete。

优先提升：

```text
F01 Text / Markdown / JSON / code
F04 Images
F05 Native PDF
F06 Scanned PDF
F07 DOCX
F08 PPTX
F09 XLSX
F12 Subtitle / JSON Canvas
```

优先复用：

* Docling；
* RAG-Anything；
* PaddleOCR；
* Tesseract；
* existing Office libs；
* FFmpeg；
* faster-whisper / SenseVoice。

每个格式必须保留：

```text
Original
Transform
Loss
Structure
Anchor
Engine
Version
Quality facts
Fallback
```

---

# 18. Research 重新定位

Research 不是 Knowledge 自动写入器。

流程：

```text
Question
↓
Query Plan
↓
Multiple Sources
↓
Snapshot
↓
Claim Extraction
↓
Independent Source Clustering
↓
Support / Conflict / Gap
↓
ResearchPackage
↓
Candidate Knowledge
```

PaperQA、RAGFlow、搜索 Provider 等可作为供体。

Research 结果永远不能自动覆盖用户个人知识。

---

# 19. Avalonia 产品壳必须真正产品化

历史 9/14、9/15 审计已经证明：

“窗口能启动”

远远不等于：

“产品闭环成立”。

正式 Avalonia Surface 至少实现：

```text
Home
Knowledge
Source
Learning
Jobs
Machine / AI Assets
Settings
Recovery
```

不能只是画侧栏。

每个 Button 必须有真实 Route / View / State。

核心 Golden Journey 必须完全从 UI 完成。

---

# 20. First-Use Breakpoint 必须永久纳入验收

保留 2026-09-15 的四个关键历史发现。

必须防止再次出现：

### Breakpoint A

Import 只保存 Source，没有自动转换。

### Breakpoint B

空知识库没有第一份学习内容。

### Breakpoint C

DEV 临时 SQLite 被误认为用户 Green Workspace。

### Breakpoint D

测试人为写 `correct=true` 冒充学习闭环。

所有未来 Journey 必须对这四项做 regression。

---

# 21. 唯一真实 First-Use Journey

禁止 Mock。

禁止人工 SQL。

禁止预灌 Learning Event。

必须：

```text
打开 Local Green
↓
选择真实测试资料
↓
Import
↓
Source
↓
Job
↓
Worker
↓
Transform
↓
在 UI 看到真实内容
↓
建立 / 接受 Knowledge
↓
生成第一份 Learning Artifact
↓
用户真实答题 / Teach-back
↓
真实评分
↓
Mastery / FSRS
↓
关闭程序
↓
重新打开
↓
读取同一 Workspace
↓
学习状态恢复
↓
机器使用同一 Knowledge 完成真实任务
↓
记录 Machine Receipt
↓
故意引入失败
↓
Correction
↓
Retest
↓
Lesson / Skill Candidate
↓
再次关闭
↓
再次启动
↓
全部状态读回
```

只有这条链真实完成才叫 Closed Loop。

---

# 22. Migration

Legacy → vNext 不允许声明式迁移。

流程固定：

```text
Legacy Green DB
↓
一致只读 Snapshot / Export
↓
Immutable package
↓
Rust staging import
↓
semantic diff
↓
loss ledger
↓
Owner review
↓
activation
↓
restart
↓
readback
```

禁止：

* dual write；
* live sync；
* Rust 写 Legacy DB；
* Legacy Python 写 vNext DB；
* 直接拿真实 Green DB 当测试库。

真实迁移测试必须首先使用隔离 copy。

---

# 23. Local Green Replacement Gate

新 Candidate 必须在 `.project-local` staging 完成验证。

然后：

1. 停止所有 ArcheAxis 进程；
2. 确认真实 executable path；
3. 对现有 Green Runtime 做 hash-addressed backup；
4. 不修改 Green 用户 `data/`；
5. 不修改 `green_material_library`；
6. 部署 Candidate Runtime；
7. readback SHA；
8. 通过 `启动星环知识.vbs` 启动；
9. GUI first-use；
10. restart；
11. same workspace readback；
12. failure/recovery；
13. rollback test。

只有通过才能成为新的本地 Green 基线。

仍然：

**不 Release。**

---

# 24. Repository Authority Convergence

修复当前已经确认的治理漂移。

必须处理：

* `TASKS.json` 与 `R5-STATE.json` 双状态源；
* `digest_profile` 死路径；
* PROJECT_CONTRACT required checks 与 GitHub ruleset 不一致；
* Release Ledger current version 漂移；
* CURRENT_ARCHITECTURE / SYSTEM_BOUNDARY 旧架构漂移；
* DeepTutor v1.5.17 固定描述漂移；
* Capability requirements / schema 漂移；
* External dependency index 漂移。

新原则：

```text
一个 Authority
↓
多个 Derived Projection
```

禁止两个 Current Truth 独立手工维护。

---

# 25. 新任务图

## A00 — Authority Reset

目标：

建立 R6 为唯一活动 Plan。

工作：

* 新 Supersession；
* R5 变 historical active-source；
* 更新 Documentation Authority；
* 更新 Configuration Authority；
* 统一 TASK state SSOT；
* 修 digest profile；
* 统一 GitHub required check semantics。

不得删除历史。

---

## A01 — Version & Release Freeze

目标：

从 GitHub 活跃开发语义中移除产品版本推进。

完成：

* main = development；
* historical releases preserved；
* no release；
* package technical identity 与 product version 分离；
* local Green identity contract。

---

## A02 — Resource / Path / Environment Authority

继承 9/15 成果。

统一：

* model resolver；
* tool resolver；
* external capability registry；
* exact paths；
* tool versions；
* no PATH guessing；
* no duplicate download。

---

## A03 — Capability Absorption Registry

全量盘点：

* internal；
* legacy；
* external；
* open-source；
* local models。

逐能力决定：

`keep / absorb / adapter / replace / benchmark / self-build-gap`

---

## A04 — Knowledge / Source Model V3

实现：

* personal knowledge；
* external knowledge；
* machine candidate；
* temporal validity；
* support level；
* confidence；
* risk；
* supersession。

废止 Evidence admission gate。

---

## A05 — Multiformat Pipeline

吸收成熟 parser/OCR/media。

目标：

核心格式从 Partial 开始真正产生 Complete。

---

## A06 — Retrieval / Graph / Research

组合：

* FTS5；
* Embedding；
* Reranker；
* LightRAG；
* Graphiti；
* bounded research。

全部为 Derived Projection。

---

## A07 — Machine Memory / Growth

评估并吸收 MemOS。

实现：

Machine Experience → Lesson → Skill Candidate → Review → Reuse。

---

## A08 — Human Learning Kernel

整合：

* current FSRS；
* DeepTutor；
* OpenTutor；
* LearningMAP。

实现真实自适应学习。

---

## A09 — Domain Learning Pack

建立统一 Domain Pack Contract。

至少先完成：

```text
General
Math/Physics
Programming
Design
```

作为不同学习形态验证样板。

---

## A10 — Courseware / Interactive Learning

吸收 OpenMAIC。

建立：

* Lesson renderer；
* Slide；
* Quiz；
* Visual；
* Simulation；
* PBL；
* coding activity；
* video/audio learning artifact。

---

## A11 — Local Model Pool

对本机已有模型先做 inventory。

然后 benchmark。

形成：

`role → model → quantization → runtime → memory → fallback`

禁止一模型全包。

---

## A12 — Avalonia Product Shell

真正实现：

* navigation；
* knowledge；
* source reader；
* learning；
* jobs；
* machine assets；
* settings；
* recovery。

所有页面必须读取真实 Core。

---

## A13 — Legacy Migration + Local Green

完成：

* nonempty legacy copy；
* staging migration；
* loss；
* diff；
* restart；
* local Green candidate；
* local replacement；
* rollback。

---

## A14 — Full Human↔Machine Closed Loop

执行真正：

Source → Knowledge → Human Learning → Machine Use → Evaluation → Correction → Lesson → Retest。

不得使用 synthetic PASS 冒充最终闭环。

---

## A15 — Independent Audit

独立检查：

* Authority；
* Repository；
* Contracts；
* Security；
* Data；
* Migration；
* Learning；
* Machine；
* Local models；
* Domain Packs；
* First-use；
* restart；
* Green。

执行者不得自签最终 READY。

---

## A16 — Owner Gate

最终结果只能是：

```text
LOCAL_GREEN_READY_FOR_OWNER_REVIEW
```

或者：

```text
NOT_READY
```

绝对不得自动变成：

```text
RELEASE_READY
```

只有 Owner 明确说：

> 可以发布

之后，才能建立新的 Release TaskPack。

---

# 26. R5 任务映射

保留原任务事实，不重复开发。

```text
X00 → A00
X01 → A00 / A02
X02 → A03
X03 → A08 / A12
X04 → A04
X05 → A04 / A13
X06 → A05
X07 → A04 / A06
X08 → A08 / A09
X09 → A07
X10 → A13
X11 → A12 / A13 / A14
X12 → A05 / A09 / A10
X13 → A00 / A02 / A12
X14 → A02 / repository maintenance
Q00/Q01 → A15
F01-F06 → 不再简单冻结，先经过 A03 再决定是否已有成熟 upstream 可低成本提前激活
```

关键变化：

> 以前因为“需要大量自研”而 Deferred 的能力，在 Absorb-first 下必须重新评估。

存在成熟 upstream 的，不得继续因为旧计划写了 Future 而永久冻结。

---

# 27. 验收门

## Gate 0

Authority 单一。

## Gate 1

Repository / contracts / build clean。

## Gate 2

Capability absorption registry 完成。

## Gate 3

Core format / retrieval / learning capability 实际运行。

## Gate 4

真实 first-use journey。

## Gate 5

Human learning restart。

## Gate 6

Machine learning / experience / retest。

## Gate 7

Domain Pack 不同领域真实行为差异。

## Gate 8

Legacy copy migration。

## Gate 9

Local Green Candidate。

## Gate 10

Local Green 原位替换和 rollback。

## Gate 11

独立审计。

## Gate 12

Owner Review。

Gate 12 之前：

**Release 永久禁止。**

---

# 28. 每个切片必须报告

执行每个切片必须输出：

```text
task_id
subject_sha
authority_source
changed_paths
upstream_absorbed
upstream_version_or_sha
license
tests
actual_runtime_result
data_touched
external_paths_touched
limitations
rollback
remaining_gap
```

不得写：

“应该能用。”

只能写：

* tested；
* not tested；
* blocked；
* unavailable；
* partial。

---

# 29. 绝对禁止事项

禁止：

* 发布新版本；
* 创建 tag；
* GitHub Release；
* 自动修改真实资料库；
* 删除 Green data；
* E 盘扫描；
* 读取 Agent private state；
* 密钥输出；
* 双写；
* AI self-verify；
* 把 confidence 当 accuracy；
* 把用户 mastery 当 truth；
* 把 machine result 当 verified knowledge；
* 因为新 upstream 出现就复制整个项目；
* 因为历史目录旧就删除；
* 用 mock 代替 final journey；
* 用 README 声明代替实测；
* 用 build success 代替 GUI；
* 用 CI success 代替 Local Green；
* 用 Local Green success 代替 Release authorization。

---

# 30. 最终目标

本轮不是追求“代码最多”。

而是建立：

```text
                     ArcheAxis
                        │
               Canonical Rust Kernel
                        │
 ┌──────────┬──────────┼──────────┬───────────┐
 │          │          │          │           │
Knowledge  Human     Machine    Domain      Research
          Learning    Growth     Packs
 │          │          │          │           │
 └──────────┴──────────┼──────────┴───────────┘
                       │
               Capability Mesh
                       │
  Parsing / OCR / ASR / RAG / Graph / Memory
  Models / Courseware / Simulation / Visualization
                       │
                Avalonia Workspace
                       │
                 Local Green
```

ArcheAxis 自己只永久掌握：

* Canonical Truth；
* Source / Knowledge lifecycle；
* Human Learning canonical state；
* Machine canonical measurement；
* authority；
* permission；
* contract；
* history；
* migration；
* capability registry；
* Local Green lifecycle。

成熟算法与能力：

尽可能吸收。

只有真正没有成熟实现的缺口才自研。

---

# 31. 执行结束条件

当且仅当以下全部成立：

* GitHub Authority 已收敛；
* 无活动产品版本漂移；
* no-release gate 生效；
* Local Green 身份明确；
* Source/Knowledge V3 生效；
* personal knowledge 无外证可合法进入；
* machine candidate 权限隔离；
* 核心格式可用；
* retrieval/graph 可用；
* learning 可用；
* Domain Pack 可用；
* courseware 可用；
* local model pool 可用；
* human learning restart 可用；
* machine experience/retest 可用；
* legacy copy migration 可用；
* Avalonia first-use 可用；
* Local Green replacement 可回滚；
* independent audit 通过；

才允许把状态写为：

`LOCAL_GREEN_READY_FOR_OWNER_REVIEW`

然后停止。

**不要发布。**

等待 Owner 明确授权下一步。
