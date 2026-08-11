# ArcheAxis Workspace 多格式识别转译与全网验证管线增强任务包

> 文档类型：`CHANGE_PROPOSAL` / 增强任务包（未获项目所有者批准前不具执行权威）  
> 文档 ID：`AXW-MFX-WXV-v1`  
> 生成日期：2026-08-11  
> 事实截止：2026-08-11 UTC  
> 产品：ArcheAxis Workspace / 元枢工作台  
> 当前仓库技术 ID：`DTALEX66/Cognitive-Loop-OS`  
> 仓库复核基线：`main@fba208f2551f26acc64d82613500656159fc6801`  
> 适用平台：Windows-first，本地优先；其他平台后续做能力等价验证  

## 0. 权威、范围与使用方式

本文件是对当前主任务包的增量提案，不覆盖、不改写以下冻结或既有权威文件：

- `ArcheAxis_Workspace_Final_Master_TaskPack_v4_2026-08-09.md`
- `docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`
- `docs/taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`
- `docs/taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`
- `docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`
- `docs/truth/AUTHORITY_CONTRACT.md`

若本文件与上述权威冲突，先停工并提交 `CHANGE_PROPOSAL`，不得静默选择一方。本文件只处理：多格式材料的识别转译、质量门控、选择性模型升级、公共事实验证、人工复核衔接、增量/恢复/安全/发布资格。它不扩展 Agent OS、Runtime 控制台、多智能体、市场、3D/VR 或其他远期能力。

执行时遵循：一项原子任务、一条分支、一个 PR；开始前重新读取云端 `main`、开放 PR、CI 与安装版事实。任何这里记录的“当前状态”均不得替代执行当日复核。

---

## 1. 独立结论

### 1.1 对方案 A 与方案 B 的判断

方案 A 的“便宜优先、昂贵兜底”原则正确，但线性瀑布结构不正确。模型辅助、模型完整识别并不是每份材料都必须经过的连续阶段；对原生文字 PDF、DOCX、HTML 和已有字幕的媒体，多数材料应在一次本地处理后结束。把“更贵”当成“更准”也没有依据，完整 LLM 重识别可能改写专名、数字、公式和引用。

方案 B 的方向明显更合理：按格式分叉、以质量门控升级、识别层与事实层解耦、人工复核兜底，这四点都成立。但 B 仍不完整：

1. CER/WER 只有在有金标准时才可计算；运行时不能用引擎置信度伪装成 CER/WER。
2. 分叉粒度不能只到“文件格式”，还要到 PDF 页、页面区域、音频时间段和高风险关键片段。
3. “置信度不够就上模型”过于粗糙；需要多信号、按引擎/语言/场景校准的质量门。
4. 缺少 RawAsset-first、不可变派生物、多引擎差异保留、增量缓存、失败恢复、隐私出站策略和发布资格。
5. “全网验证”不能是一个统一搜索动作，而应是 Claim 级、来源类型感知、异步、可缓存的证据检索与交叉验证。

### 1.2 推荐结构

采用方案 C：

**RawAsset-first + 页/区段路由 + 校准门控 + 选择性多引擎/LLM 升级 + Claim 级异步验证 + 人工授权。**

核心不是把能力复制到九条管线，而是建立一套可重用的核心阶段协议。各入口只负责接入，各知识/学习界面只消费投影：

```text
入口适配器
  /pipeline | /ingest/* | /workspace/api/* | KB | Research | Obsidian skills
        │
        ▼
Intake Gateway ── 原件先落盘 ──> RawAsset + SourceRecord + Import Job/Receipt
        │
        ▼
Source Profiler / Policy Router
  MIME、签名、加密、页型、语言、隐私、风险、可用引擎、预算
        │
        ▼
Conversion Orchestrator（Worker 执行）
  原生提取 | OCR | ASR | HTML 提取 | 专项结构解析
        │
        ▼
Quality Gate（识别转译层）
  ACCEPT ───────────────────────────────────────────────┐
  ACCEPT_WITH_WARNINGS ─────────────────────────────────┤
  TARGETED_RETRY -> 页/区域/时间段重试 ────────────────┤
  ALTERNATE_ENGINE -> 差异对齐 ─────────────────────────┤
  LLM_ASSIST_CANDIDATE -> 仅争议片段、需授权和预算 ────┤
  HUMAN_REVIEW / UNSUPPORTED ───────────────────────────┤
                                                         ▼
DerivedDocument + Block + LossReport + EvidenceAnchor + TextVariant
        │
        ├──> Workspace / KB / Reader / Search 的可回读投影
        │
        ▼
Claim Triage（内容事实层，异步）
  可公开查证 | 私有/主观 | 不值得验证 | 高风险 | 疑似转译噪声
        │
        ▼
Evidence Connector Registry
  官方/注册机构 API -> 学术/图书馆 -> 权威百科 -> 受控网页回退
        │
        ▼
CrossValidation + EvidenceBundle + 冲突/时效/独立性判断
        │
        ▼
人工 ReviewDecision -> 才允许 VerifiedKnowledge / 正式 AI Asset 晋级
```

识别完成不应等待互联网；事实验证默认异步。只有用户明确要求“经核验导入”、高风险发布或正式知识晋级时，验证结果才是阻断门。

---

## 2. 前提假设与事实边界

### 2.1 明确假设

- 当前是个人学习研究项目，但会生成可分发的 Windows 安装版，因此不能用“非商业”替代许可证审查。
- SQLite WAL/FTS/可选 `sqlite-vec` 仍是本地事实与索引底座，不引入重型数据库替代。
- 外部 LLM 默认关闭；只有用户授权出站、质量门满足升级条件且预算允许时才调用。
- 用户文件可以证明“文件中写了什么”，不能独立证明其中公共事实为真。
- 公开网页、API 和模型的服务条款、速率、许可证会变化；每次发布必须按 exact revision/日期复核。

### 2.2 截止 2026-08-11 的仓库事实

云端 `main@fba208f...` 已合并 H1 对象与治理后端，增强必须复用真实主链：

`RawAsset → ConversionRun / DerivedDocument / Block / LossReport → EvidenceAnchor / Claim / CrossValidation / EvidenceBundle`

不能按旧状态文档把 H1 继续写成“待合并”。源码复核发现：

- `shared/pipeline.py::run_pipeline` 的 `file` 只读 approved root 中 UTF-8 小文本；索引仍可直接写旧知识表，且 `crossref` 只是内部启发式可信度分数。
- `app/ingestion/multi_format.py` 的图片链首先调用 Pillow 元数据适配器；元数据被标为成功后会阻止实际 OCR。媒体仅有 FFprobe/FFmpeg 元数据，没有内容 ASR。
- 引擎链采用“第一个 success 即结束”，没有语义后置条件、页级路由、版本化质量门或差异保留。
- `shared/cross_reference.py` 是域名/词语/简单 SPO 启发式，不是公开来源的 Claim 级交叉验证。
- `shared/web_search.py` 依赖 DuckDuckGo Lite HTML 解析与通用正文提取，缺少来源快照、独立性、时效、速率、条款、引用元数据和验证状态协议。
- `app/workspace/service.py` 已有成熟 Job/Outbox/Receipt 投影与治理流程，但 upload 当前不是完整的 RawAsset-first 持久化顺序。
- `app/workspace/worker.py` 可作为任务执行底座，但需增加阶段任务、租约、心跳、取消、检查点、预算和失败分类。
- Obsidian 技能侧的 OCR/ASR/web-crosscheck 是参考实现与迁移来源；在依赖、许可证、失败语义、Windows 安装版和真实 fixture 通过资格验证前，不算核心仓能力。

---

## 3. 不可破坏的系统不变量

1. **原件不可变**：先保存 RawAsset、哈希、来源和权限，再做转换；任何派生结果不得覆盖原件。
2. **两层验证分离**：识别转译质量与内容事实状态使用不同对象、指标、状态和 UI。
3. **没有金标准就不报 CER/WER**：运行时只能报告代理信号与校准风险；字段应为 `gold_metric_status=unavailable`。
4. **置信度不等于准确率**：引擎原始 confidence 必须带 `engine_id/model_id`，不得跨引擎直接比较。
5. **差异不自动覆盖**：多引擎或外部来源冲突形成 TextVariant、DisagreementSpan 或 EvidenceConflict。
6. **LLM 只能提出候选**：不得把 LLM 修订直接写成 canonical transcript 或 VerifiedKnowledge。
7. **不强行验证不可查内容**：私有记录、主观陈述、原创观点、未公开事件可标 `private_source_only/not_applicable`。
8. **证据可回放**：记录请求、响应/快照哈希、规范标识、版本、检索时间、来源层级和抽取位置。
9. **可恢复、可取消、幂等**：每个阶段可单独重试；失败不使 RawAsset 或既有合格派生物丢失。
10. **能力声明由安装证据决定**：依赖存在、能力探针、真实 fixture、安装版回读、许可证与回滚全部通过才可标“支持”。

---

## 4. 九条现有管线的接入决策

| # | 管线 | 定位 | 必须改造 | 不应做 |
|---|---|---|---|---|
| 1 | `shared/pipeline.py::run_pipeline` | 兼容入口/轻量编排 | 文件、URL、YouTube 等转换委托统一 Intake/Conversion；旧索引仅消费合格派生物 | 自己复制 OCR/ASR；直接把截断文本当正式知识 |
| 2 | `app/ingestion/multi_format.py` | 引擎适配器与格式探针 | 修复元数据成功语义；实现页/区段路由、EngineInvocation、LossReport | 继续“第一个 success 即合格” |
| 3 | `app/workspace/service.py` | BFF/治理与投影 | 所有 intake 先 RawAsset；展示阶段、损失、验证和复核状态 | 在请求线程跑重 OCR/ASR/联网验证 |
| 4 | `app/workspace/worker.py` | 持久化执行底座 | 增加转换、质量、验证、索引任务；lease/heartbeat/checkpoint/budget | 把业务判断写死在 dispatcher |
| 5 | Runtime facades | 受控下游消费者 | 以后只消费经授权的 AI Assets/VerifiedKnowledge | 为本项目扩建 Agent Runtime 或自主执行层 |
| 6 | Knowledge Base | 合格派生物投影与检索 | 块/锚点/版本索引；验证状态过滤；增量重建 | 把 FTS/向量相似度当事实正确性 |
| 7 | Research | Claim/Evidence 人工治理 | 复用 EvidenceBundle、冲突和复核决策；支持重新验证 | 另建不兼容的第二套证据模型 |
| 8 | Obsidian skills | 参考实现、fixtures、交互入口 | 下沉可复用规则与测试；通过核心 API/CLI 接入 | 核心仓依赖 Hermes runtime；把技能存在写成产品完成 |
| 9 | Release/Desktop | 能力资格与交付 | 打包/探测 FFmpeg、Tesseract、模型包；SBOM/NOTICE/哈希/离线与回滚 | 将构建发布标为“与识别无关” |

结论：建立“一套核心阶段协议 + 多个入口适配器 + 多个只读投影”，而不是每条管线各自接 OCR、ASR 和 web crosscheck。

---

## 5. 核心阶段协议与对象复用

### 5.1 先做对象复用矩阵

实现前必须把下面的“目标概念”映射到现有 H1 表/对象；能以字段或子记录扩展就不新建平行实体：

| 目标概念 | 优先复用 | 最小必需信息 |
|---|---|---|
| 原件与来源 | RawAsset / SourceRecord | SHA-256、字节数、MIME/签名、原名、来源 URI、许可/权限、采集时间 |
| 一次引擎调用 | ConversionRun 子记录或 EngineInvocation | 引擎/模型 exact revision、参数、输入/输出哈希、耗时、资源、退出码 |
| 转译内容 | DerivedDocument / Block | 页/区段/时间码、规范文本、结构、坐标、语言、版本 |
| 转译损失 | LossReport | 丢失类型、位置、严重度、代理信号、受影响能力 |
| 来源锚点 | EvidenceAnchor | RawAsset 页/坐标/时间码到 Block 的双向映射 |
| 质量评估 | ConversionRun/新 QualityAssessment | profile、信号、校准版本、决策、理由代码 |
| 多结果差异 | Block 版本/新 TextVariant、DisagreementSpan | 候选、来源引擎、对齐位置、差异类别、人工选择 |
| 事实声明 | Claim | 原文锚点、规范化 claim、类型、可查证性、风险和时效 |
| 外部检索 | CrossValidation 子记录/新 EvidenceFetch | connector、query、响应哈希、URL/PID、时间、许可和错误 |
| 证据集合 | EvidenceBundle | 支持/反驳/不确定、独立性、版本冲突、状态 |
| 预算 | Job/新 BudgetLedger | 本地 CPU/GPU、网络字节、API 成本、LLM input/output token |

任何新迁移都必须可逆；不得创建 `DocumentV2`、`FactV2` 等重复真相源。

### 5.2 StageRequest / StageResult

所有 worker 阶段共享版本化信封，至少包含：

```yaml
StageRequest:
  schema_version: 1
  job_id: uuid
  asset_id: uuid
  stage: profile|convert|quality|resolve|claim_triage|retrieve|cross_validate|project
  input_artifact_hashes: []
  policy_profile: local_private|local_public|verified_import|high_risk
  capability_snapshot_id: uuid
  budget_id: uuid
  idempotency_key: string

StageResult:
  schema_version: 1
  status: succeeded|succeeded_with_warnings|retryable_failed|permanent_failed|cancelled
  outcome: ACCEPT|ACCEPT_WITH_WARNINGS|TARGETED_RETRY|ALTERNATE_ENGINE|LLM_ASSIST_CANDIDATE|HUMAN_REVIEW|UNSUPPORTED
  reason_codes: []
  engine_ref: {id, code_revision, model_id, model_sha256, license_state}
  output_artifact_hashes: []
  metrics: {}
  losses: []
  resource_usage: {}
  checkpoint: {}
```

状态名称必须机器可读；用户文案由 BFF 映射，不能把内部异常栈暴露给 UI。

---

## 6. 格式路由与默认引擎策略

### 6.1 统一预检

每个输入先执行无 Token 预检：

- SHA-256、大小、扩展名、声明 MIME、magic/内容类型交叉检查；Magika 只做路由信号，不作安全证明。
- 检查加密、密码保护、损坏、归档嵌套、页数/时长、宏、外链、可执行内容。
- 识别语言候选、私密等级、是否允许联网、目标质量 profile。
- 生成 capability snapshot，禁止在任务中途因 PATH 变化静默换引擎。

### 6.2 PDF

按页分类，而不是整份 PDF 只选一个引擎：

1. **原生文字页**：MarkItDown/pdfplumber/pypdf 提取；保留页号、字符框、链接、图片和结构损失。
2. **扫描页**：渲染受控 DPI 后 OCR；默认 Tesseract fast/best profile，中文/混排或布局困难页按资格测试启用 PaddleOCR。
3. **混合页**：原生文字与 OCR 区域融合，但不得重复同一文字；记录每个 Block 的来源。
4. **复杂布局/表格/公式**：只把相关页送 Docling 或通过资格的专项引擎，不对全文件强制重跑。
5. **损坏 PDF**：qpdf/pikepdf 只做诊断/可逆修复副本；原件不变。
6. **加密 PDF**：返回 `NEEDS_PASSWORD`，密码只驻留任务内存/受控秘密存储，不写日志。

### 6.3 图片

- Pillow 只提供尺寸、色彩、EXIF 等 metadata，结果状态必须是 `metadata_only`，不能满足 content conversion。
- 基线：Tesseract；候选第二引擎：PaddleOCR、EasyOCR、RapidOCR，必须按语言、印刷/拍照、倾斜、手写、表格分别基准。
- 预处理（旋转、去噪、二值化、去倾斜）保存参数和派生图哈希，不能覆盖原图。
- LLM 视觉仅允许裁剪后的争议区域或无法解析的关键图示；输出是候选 TextVariant。

### 6.4 Office 与文本格式

- DOCX/PPTX/XLSX/CSV：优先 MarkItDown 与格式原生库；保留 sheet/slide/paragraph/cell 锚点和公式/批注/隐藏内容损失。
- 老式 DOC/PPT/XLS 或罕见格式：Apache Tika/LibreOffice 作为受限 sidecar 候选，不在主进程加载宏，不自动执行外链。
- 密码保护 Office：先用 msoffcrypto-tool 等探针检测，状态为 `NEEDS_PASSWORD`。
- CSV/TSV 的编码、方言和公式注入风险单独报告；不得把首个可解码结果自动视为完整。

### 6.5 HTML、URL、RSS、Search

1. Safe HTTP 负责 SSRF、重定向、大小、内容类型、超时、robots/条款策略。
2. 保存原始响应/规范 URL/headers/抓取时间/内容哈希；正文只是派生物。
3. 静态正文首选 Trafilatura；失败或高差异时用 Mozilla Readability 作第二结果。
4. JavaScript 动态页面只有在用户允许联网且静态结果确实不完整时，才使用 Crawlee/Playwright sidecar。
5. 通用搜索只能发现候选来源；DuckDuckGo HTML 正则结果不得直接成为权威证据。
6. 抽取出的 HTML 必须视为不可信内容，展示前净化；页面中的“忽略指令/上传秘密”等文本标记为 prompt injection 内容而非系统指令。

### 6.6 音频与视频

1. FFprobe 读取容器/轨道；优先提取合法内嵌字幕与用户提供字幕。
2. FFmpeg 生成受控 PCM 派生音频；记录 build config，因为启用 GPL 组件会改变许可证边界。
3. Silero VAD 切分语音，减少静音推理与幻觉；不得丢弃切分时间码。
4. 默认 ASR 候选：faster-whisper + 明确哈希的 OpenAI Whisper 权重；CPU/低配备选 whisper.cpp 量化模型。
5. sherpa-onnx 仅在特定语言/流式场景通过“代码 + 每个模型”许可与质量测试后启用。
6. 说话人分离不是首发依赖；pyannote 等 gated 模型未通过许可/下载/离线资格前保持可选。
7. YouTube：先用用户有权访问的官方字幕/自有媒体；yt-dlp 只能在用户有权处理且显式启用时作为下载适配器，不能绕过 DRM、登录或平台限制。

---

## 7. 识别转译质量门

### 7.1 有金标准时

使用 JiWER 或等价透明实现计算：

- OCR：CER、WER；关键实体单独计算数字/日期/人名/DOI/引用准确率。
- ASR：WER/CER、时间戳偏差、语言识别、无语音误插入率。
- 结构：标题层级、阅读顺序、表格单元格、列表、页/段锚点、公式与脚注保留率。

下表只是初始 benchmark 分档，不是跨语言、跨引擎的运行时硬编码真理：

| 目标用途 | OCR CER 初始目标 | ASR WER 初始目标 | 附加要求 |
|---|---:|---:|---|
| 搜索/预览草稿 | ≤5% | ≤15% | 明确显示“草稿/未核验” |
| 阅读/学习 | ≤2–3% | ≤8–10% | 关键实体无系统性错误，锚点可回读 |
| 引用/证据 | ≤1% | ≤5–8% | 数字、人名、日期、引用、公式/表格需双引擎或人工确认 |

最终阈值由每个 `engine × model × language × document_class × hardware/profile` 的保留集校准。未经 benchmark，不得宣传“准确率 X%”。

### 7.2 无金标准时

运行时组合代理信号，不生成伪 CER/WER：

- 内容覆盖：页/区域文字覆盖、空白页比例、截断、替换字符、乱码、不可打印字符。
- 结构一致性：阅读顺序、标题/列表/表格闭合、跨页段落、页数与锚点完整。
- 几何/视觉：文字框覆盖、重叠、越界、旋转、图像清晰度、渲染与 OCR 区域一致性。
- 语言/词法：语言不匹配、异常字符分布、重复句段、词典/专名异常；只作风险信号。
- 多源一致性：原生文本与 OCR、内嵌字幕与 ASR、两个引擎在关键 span 的差异。
- ASR 专项：静音段出字、重复环、压缩比异常、时间戳倒退/跳跃、VAD 覆盖、语言漂移。
- 关键 span：数字、金额、年份、专名、定义、公式、表格、书目字段的风险权重高于普通文字。
- 引擎 confidence：先在有金标准的保留集做可靠性校准；原始值永不直接作为通用准确率。

质量评估必须输出 `reason_codes`，例如：

`LOW_TEXT_COVERAGE`、`MIXED_PAGE_UNROUTED`、`CRITICAL_SPAN_DISAGREEMENT`、`STRUCTURE_LOSS_TABLE`、`ASR_NO_SPEECH_HALLUCINATION`、`LANGUAGE_MISMATCH`、`ENGINE_UNAVAILABLE`。

### 7.3 决策状态

- `ACCEPT`：满足当前用途，无严重损失。
- `ACCEPT_WITH_WARNINGS`：可读/可索引，但部分结构或非关键内容损失。
- `TARGETED_RETRY`：仅重跑失败页、区域或时间段。
- `ALTERNATE_ENGINE`：当前引擎不适合该局部或输出高度不一致。
- `LLM_ASSIST_CANDIDATE`：本地引擎已用尽且高价值局部仍无法解析；需要出站授权与预算。
- `HUMAN_REVIEW`：关键冲突、低置信且无法安全自动解决。
- `UNSUPPORTED`：依赖、许可、加密、损坏或安全政策阻止处理。

---

## 8. 多引擎差异与融合

多引擎不是每份文件都并行跑，也不是多数投票：

1. 第一引擎按格式/页面 profile 运行。
2. 质量门定位问题页/块/span；只有这些局部调用第二引擎。
3. 以页、坐标、段落或时间码对齐；RapidFuzz 可用于候选对齐，不决定事实。
4. 完全一致的 span 可自动合并；空白/标点等低风险规范化必须可逆。
5. 数字、专名、定义、公式、表格或引用差异形成 `DisagreementSpan`，保留所有候选及来源。
6. LLM 只能看到争议局部、原始裁剪/短上下文和明确任务；不得重写无争议全文。
7. 人工选择生成 ReviewDecision；canonical 更新为新版本，旧版本和决策链仍可回读。

禁止：用三个同源模型的“多数”冒充独立性；用语言模型流畅度覆盖原图/原音；在没有坐标/时间码的情况下悄悄拼接不同结果。

---

## 9. 全网验证的边界与协议

### 9.1 值得验证

- 人名、机构、地名、年份、金额、数量、单位、排名、版本、现任职位等可变或精确事实。
- 概念定义、理论归属、历史事件、法规/标准/产品规格。
- DOI、ISBN、PMID、作者、题名、期刊、出版年等书目事实。
- 用户准备晋级为 VerifiedKnowledge、课程事实、正式 AI Rule/Standard 的声明。
- 医疗、法律、财务、安全等高风险声明；此类必须权威来源 + 独立佐证 + 人工复核。

### 9.2 不应自动验证

- 私人日记、会议私密事实、未公开项目状态、个人体验和主观判断。
- 原创论证、假设、创作文本、课堂任务指令；可验证其引用，不验证其“观点正确”。
- 明显 OCR/ASR 噪声；先回识别层，不应拿乱码搜索全网。
- 对当前用途没有决策价值的琐碎陈述。
- 会把 PII、秘密、未公开内容发送到公网的 query。

### 9.3 ClaimTriage 状态

`public_verifiable`、`time_sensitive`、`high_risk`、`private_source_only`、`subjective`、`creative`、`not_worth_verifying`、`suspected_transcription_noise`、`access_restricted`。

只有前三类默认进入外部验证候选；任何外发还必须通过 egress policy。

### 9.4 来源层级与独立性

| 层级 | 示例 | 用途 |
|---|---|---|
| A 原始/权威 | 政府、标准组织、官方文档、注册机构、原始论文/数据 | 高风险与精确事实首选 |
| B 学术/图书馆 | Crossref、DataCite、Europe PMC、NCBI、OpenAlex、图书馆目录 | 书目、研究与引用网络 |
| C 结构化百科 | Wikidata、Wikipedia、专业百科 | 常识、实体关系、发现线索；争议事实需上溯 |
| D 受控普通网页 | 高信誉机构或新闻、经安全提取的网页 | 补充上下文、发现来源，不单独晋级高风险事实 |

“两个 URL”不等于两个独立来源。需要记录共同 DOI、同一新闻稿、转载链、相同发布者/数据集等依赖。搜索摘要、LLM 回答、聚合页不能作为独立证据。

### 9.5 验证输出状态

`corroborated`、`partially_corroborated`、`contradicted`、`contested`、`insufficient_public_evidence`、`private_source_only`、`not_applicable`、`access_restricted`、`outdated_or_version_mismatch`。

验证结果绝不覆盖转译原文；它形成 EvidenceBundle 和并排差异。证据至少记录：规范 URL/PID、标题/发布者、版本/日期、retrieved_at、响应/快照 SHA-256、相关短 excerpt/字段、支持或反驳关系、来源层级、独立性组、许可/访问限制、connector revision。

---

## 10. 首批证据连接器

连接器应采用 registry/plugin contract；每个连接器有 `capabilities`、query schema、rate policy、cache policy、terms/licence record、fixture 和错误映射。

首批顺序：

1. **标识符直查**：DOI/PMID/ISBN/ORCID/ROR 等先规范化，减少模糊搜索。
2. **Crossref REST**：DOI 与出版元数据；使用有效 mailto/User-Agent、读取服务端 rate headers、429 backoff。元数据通常开放，但摘要版权单独处理。
3. **DataCite REST**：Findable DOI 元数据；公开 API 无需认证。
4. **OpenAlex**：引用图谱和学术发现；当前 API 为 freemium，单项 ID/DOI 查询免费，search/list 有免费日额度和超额成本，必须读 `cost_usd`/rate headers。
5. **Europe PMC / NCBI E-utilities**：生命科学；遵守 tool/email/API key 与速率规则。
6. **Wikidata/MediaWiki**：结构化实体与常识；WDQS 不用于全文/模糊搜索，遵守 User-Agent、maxlag、429/Retry-After。
7. **Open Library**：低流量 ISBN/书目补充；缓存、标识 User-Agent，不作高并发抓取。
8. **官方域适配器**：法规、标准、软件官方文档等按领域添加，不能用一个“全网权威分数”代替。
9. **通用 web fallback**：只有结构化连接器不足时使用；保留网页快照与安全抽取，结果默认是 EvidenceCandidate。

---

## 11. 开源组件决策矩阵

状态含义：`ADOPT_BASELINE` 为通过资格后默认；`EVALUATE` 为必须对比测试；`OPTIONAL_SIDECAR` 为隔离可选；`LICENSE_REVIEW_REQUIRED` 为默认关闭；`DO_NOT_DEFAULT` 为不得作为默认路径。

| 能力 | 项目 | 上游许可/边界 | 决策 | 理由与约束 |
|---|---|---|---|---|
| 文件类型 | Google Magika | Apache-2.0 | ADOPT_BASELINE | 小型本地模型、200+ 类型；仅路由，不作安全证明 |
| 常规转换 | Microsoft MarkItDown | MIT；可选依赖另审 | ADOPT_BASELINE | 已有、轻量、结构化 Markdown；只用窄 `convert_local/stream`，禁默认 LLM OCR |
| PDF 文本 | pdfplumber / pypdf | MIT / BSD-like | ADOPT_BASELINE | 原生文字、页级信息、低成本；复杂布局需升级 |
| 复杂文档 | Docling | 代码 MIT；模型各自许可 | EVALUATE | 只用于复杂页/表格，经模型 SBOM、Windows 和质量测试后启用 |
| 广格式 | Apache Tika | Apache-2.0；子组件另列 | OPTIONAL_SIDECAR | 1000+ 类型、Java 17；用于 legacy/罕见格式，不替换主链 |
| 广格式 | Unstructured | Apache-2.0；系统依赖重 | EVALUATE | 覆盖广但 Poppler/Tesseract/LibreOffice/Pandoc 依赖重；只补明确缺口 |
| PDF/OCR | Tesseract + tessdata | Apache-2.0 | ADOPT_BASELINE | 100+ 语言、TSV/hOCR/ALTO/PAGE，Windows 可打包；需预处理和语言包 |
| OCR/结构 | PaddleOCR | Apache-2.0；模型逐项记录 | EVALUATE→BASELINE_CANDIDATE | 中英混排与结构能力强；先测 PP-OCR/PP-Structure，VLM 不默认 |
| OCR | EasyOCR | Apache-2.0；模型逐项记录 | EVALUATE | 已有候选；按真实 fixtures 与 Paddle/Tesseract 比较，不凭名气排序 |
| OCR/ONNX | RapidOCR | 代码 Apache-2.0；派生模型来源另审 | EVALUATE | Windows/CPU 有潜力；模型哈希与权利链通过后使用 |
| 可搜索 PDF | OCRmyPDF | MPL-2.0；Tesseract/Ghostscript 等组合 | OPTIONAL_SIDECAR | 适合生成文本层副本；发布时审完整二进制许可矩阵 |
| PDF 修复 | qpdf / pikepdf | Apache-2.0 / MPL-2.0 | OPTIONAL_SIDECAR | 诊断和可逆副本修复，不覆盖 RawAsset |
| 学术结构 | GROBID | Apache-2.0 | OPTIONAL_SIDECAR | 论文元数据/引用专项，不处理所有文档 |
| ASR | faster-whisper | MIT；Whisper 权重 MIT | ADOPT_BASELINE | 本地 CTranslate2/量化、无 API token；以实测 WER/资源为准 |
| ASR 低配 | whisper.cpp | MIT；模型逐项记录 | EVALUATE | Windows CPU/量化/离线，作为低配与独立实现备选 |
| VAD | Silero VAD | MIT | ADOPT_BASELINE | 本地小模型，减少静音推理；保留时间线 |
| 流式 ASR | sherpa-onnx | 代码 Apache-2.0；模型各自许可 | EVALUATE | 多平台/离线；按具体模型登记，不做总括许可 |
| 媒体 | FFmpeg/ffprobe | 通常 LGPL-2.1+；构建选项可变为 GPL | ADOPT_BASELINE_WITH_BUILD_AUDIT | 固定 build config、NOTICE、哈希与能力探针 |
| HTML | Trafilatura ≥1.8 | Apache-2.0；旧版 GPLv3+ | ADOPT_BASELINE | 已有、低成本；必须锁定现代版本 |
| HTML 第二结果 | Mozilla Readability | Apache-2.0 | EVALUATE | 用于失败/差异比较；输出仍需净化 |
| 动态网页 | Crawlee Python | Apache-2.0；浏览器依赖另审 | OPTIONAL_SIDECAR | 仅动态页按需启动，避免常驻重浏览器 |
| 质量指标 | JiWER | Apache-2.0 | ADOPT_BASELINE | 透明计算 WER/CER；只在有 truth 时使用 |
| 文本对齐 | RapidFuzz | MIT | ADOPT_BASELINE | 对齐/差异定位，不作为事实裁决 |
| 近重去重 | datasketch | MIT | EVALUATE | MinHash/LSH；持久化时锁定 hash scheme/version |
| 增量监视 | watchfiles | MIT | EVALUATE | Windows wheels；事件后仍以内容哈希确认 |
| PII 提示 | Presidio | MIT | OPTIONAL_ADVISORY | 自动检测不完整，只作出站预警，不承诺脱敏完整性 |
| 令牌估算 | tiktoken | MIT | ADOPT_FOR_ESTIMATE | 只估 OpenAI 兼容 token；最终以 provider usage 为准 |
| 学术发现 | Crossref/DataCite/Wikidata/Europe PMC | 公共 API/开放元数据，各有条款 | ADOPT_CONNECTORS | 结构化查询优先，缓存、标识、速率和时效可审计 |
| 学术图谱 | OpenAlex | 数据 CC0；API freemium | ADOPT_WITH_BUDGET | API 成本模型会变；记录服务端成本并缓存 |
| 复杂文档 | MinerU | Apache-2.0 + 2026 附加条件 | LICENSE_REVIEW_REQUIRED | 有在线服务标识和规模阈值条款；未经所有者/法律复核默认关闭 |
| PDF 转换 | Marker | GPL-3.0；模型/商业条款另审 | DO_NOT_DEFAULT | 组合许可和模型权重边界不适合作为默认安装依赖 |
| PDF 转换 | PyMuPDF/PyMuPDF4LLM | AGPL-3.0 或商业许可 | LICENSE_REVIEW_REQUIRED | 不因个人/非营利豁免；明确接受 AGPL 或购许可后再用 |
| 中文 ASR | FunASR/SenseVoice | 代码 MIT；模型为自定义可修订协议 | LICENSE_REVIEW_REQUIRED | 模型协议含行为条款、自动修订与未定义法域，不作为默认包 |
| 元数据 | Zotero translation-server | AGPL | OPTIONAL_SIDECAR/LICENSE_REVIEW | 能力优秀但需隔离和 AGPL 合规决策 |
| 搜索聚合 | SearXNG | AGPL-3.0 | OPTIONAL_SIDECAR | 可自托管发现候选；不能嵌入后声称宽松许可 |

“采用”仍不等于立即依赖：每项先建 upstream ledger，固定 exact revision、代码/模型/数据/字体许可、下载来源、SHA-256、Windows wheel/二进制、CVE、fixture、能力探针、升级与回滚。

---

## 12. Token、API 与本地算力预算

### 12.1 默认零 Token 路径

文件类型检测、原生提取、OCR、ASR、正文抽取、Claim 规则抽取、标识符查询、FTS/BM25 检索、差异定位和大多数格式化均在本地/结构化 API 完成。不得为了摘要友好或文本流畅而默认调用 LLM。

### 12.2 LLM 升级条件

必须同时满足：

1. 当前目标确需解决该错误，而不是可接受 warning；
2. 本地原生/第二引擎/预处理已失败或不适用；
3. 只发送争议页裁剪、短音频段或必要短上下文；
4. egress policy 允许，PII/秘密检查通过；
5. 用户或预先批准的 policy 允许；
6. 预算未耗尽；
7. 输出保存为 Candidate，并可人工回读原始锚点。

### 12.3 预算账本

每个 run/stage 记录：

- `local_cpu_seconds`、`gpu_seconds`、peak RAM/VRAM、磁盘临时字节；
- `bytes_fetched`、connector call count、429/retry；
- `llm_input_tokens`、`llm_output_tokens`、provider、model、实际 provider cost；
- OpenAlex/其他计费 API 返回的 `cost_usd` 或额度消耗；
- `escalation_reason`、处理页/区段比例、结果是否改变最终决策。

预算按 asset、run、day 和 connector 设软/硬上限。硬上限触发 `BUDGET_EXHAUSTED → HUMAN_REVIEW`，不能静默降级到更贵服务。Token 节省率只有在同一 fixture 上有“全文件 LLM 基线”与实际测量时才可发布；理论估算必须标 `estimated`。

---

## 13. 去重、增量、缓存与版本

### 13.1 身份与缓存键

文件路径不是内容身份。转换缓存键至少包含：

```text
sha256(raw_bytes)
+ engine_id
+ engine_code_revision
+ model_id
+ model_sha256
+ profile_version
+ normalizer_version
+ locale/language_pack
+ canonical_params_digest
```

事实检索缓存键包含：规范化 Claim/identifier、connector、query schema version、source revision/freshness policy、语言和权限 profile。

### 13.2 增量规则

- 同 RawAsset + 同缓存键可重用 immutable result；换模型、参数、语言包或 normalizer 必须新 ConversionRun。
- 目录 watcher 只提示变化，最终以内容哈希确认；rename 不触发重转换。
- 只重新索引受影响 Block/Claim；IndexRevision 记录父版本和原因。
- Web 证据有 TTL/freshness class：出生年份等相对稳定，现任职位、价格、法律和软件版本高频失效。
- 内容级去重：精确 SHA-256；近重只用于提示/聚类，不自动合并两个不同来源。

---

## 14. Worker、失败恢复与幂等

- Job 状态：`queued/running/checkpointed/succeeded/succeeded_with_warnings/retryable_failed/permanent_failed/cancelled/review_required`。
- 每个 stage 使用 idempotency key；Outbox 事件只在同一事务中写入，消费者幂等投影。
- 长任务需要 lease、heartbeat、超时、取消点；按页/时间段检查点恢复。
- 重试分类：网络 429/5xx、sidecar crash、临时磁盘为 retryable；不支持格式、许可证禁用、密码缺失、安全上限为 permanent/review。
- 指数退避尊重 `Retry-After`；禁止无限重试和跨 connector 失控扩散。
- 临时文件使用任务专属目录；成功后原子发布，崩溃后 orphan cleanup 可回收。
- 已合格旧版本在新运行失败时仍可读；UI 明示当前版本与失败的新尝试。
- Receipt 对用户暴露稳定 job 状态，不暴露数据库内部 ID 或敏感路径。

---

## 15. 安全、隐私与出站

1. **文件安全**：MIME/签名不一致、路径穿越、ZIP bomb、超大页/像素、XML 外部实体、宏、嵌入对象、字体/图片炸弹均设硬上限。
2. **进程隔离**：Tika、LibreOffice、浏览器、OCR/ASR 大模型优先 sidecar/子进程；最低权限、只读输入、独立 temp、CPU/RAM/时长限制、无默认网络。
3. **SSRF**：只允许 http/https；阻断 loopback、link-local、RFC1918、metadata service、DNS rebinding；逐跳验证 redirect。
4. **内容不可信**：网页/文档内指令只是数据；不得改变 system policy、发网请求或读本地秘密。
5. **出站分级**：`local_private` 默认永不联网；`local_public` 只允许用户认可的公开 Claim；`verified_import` 可按白名单 connector；`high_risk` 需人工确认。
6. **PII**：Presidio 等只作 advisory。检测不到不代表安全；用户必须能查看将外发的最小 query。
7. **凭据**：API key/token 不进日志、EvidenceBundle、fixture、异常栈或导出。
8. **版权/条款**：只保存验证所需最小 excerpt 和合法快照；不把付费全文或受限数据重新分发。
9. **供应链**：依赖/模型哈希、来源、签名（如有）、SBOM、NOTICE、CVE 扫描和撤销清单进入发布证据。

---

## 16. Windows 安装版与能力声明

发布构建必须生成 `CapabilityManifest`：

```yaml
capability: ocr.image.zh_en
technical_state: qualified|degraded|unavailable
engine: tesseract|paddleocr|...
engine_revision: exact
model_id: exact
model_sha256: exact
license_state: approved|review_required|blocked
installed_probe: pass|fail
fixture_suite: id
last_qualified_at: timestamp
fallback: human_review|alternate_engine|none
```

要求：

- doctor/bootstrap/build/clean 覆盖 FFmpeg、Tesseract、语言包、模型包、Java/Tika 可选 sidecar、GPU/CPU 后端。
- 基础安装器尽量小；大模型/多语言包作为可校验、可卸载、可离线镜像的 capability pack。
- 记录 build config、锁文件、commit/tree、dirty 状态、二进制/模型哈希、安装路径、AppData 数据根、卸载保留策略。
- installed-format 测试必须在干净 Windows VM 执行真实 PDF、扫描图、音频、DOCX、HTML，重启后读取 Block/Anchor/LossReport。
- 缺少依赖时 UI 必须诚实显示 degraded/unavailable，不能用 metadata-only 冒充 OCR/ASR。

---

## 17. 原子任务图

### 17.1 阶段与依赖

```text
P0 Truth/止损
  MFX-000 ─┬─ MFX-001
           ├─ MFX-010 ─ MFX-011 ─ MFX-020 ─ MFX-021 ─ MFX-022
           └─ MFX-012

P1 本地转换
  MFX-021 ─┬─ MFX-030 PDF
           ├─ MFX-031 OCR
           ├─ MFX-032 Office
           ├─ MFX-033 HTML
           └─ MFX-034 ASR

P2 质量与差异
  MFX-030..034 ─ MFX-040 Benchmark ─ MFX-041 Gate ─ MFX-042 Resolver/LLM

P3 Claim 级验证
  MFX-020 ─ MFX-050 Triage ─ MFX-051 Registry ─ MFX-052 Connectors
                                      └────────── MFX-053 Web fallback
  MFX-052 + MFX-053 ─ MFX-054 CrossValidation/Promotion

P4 平台化与资格
  MFX-022 + MFX-041 + MFX-054 ─┬─ MFX-060 Dedup/Incremental
                               ├─ MFX-061 UI/Review
                               ├─ MFX-062 Security
                               └─ MFX-063 Packaging
  MFX-060..063 ─ MFX-070 End-to-end qualification
```

### 17.2 总览

| ID | 目标 | 依赖 | 交付门 |
|---|---|---|---|
| AXW-MFX-000 | 登记增量权威与最新仓库事实 | 无 | 不覆盖 frozen baseline；状态日志可追踪 |
| AXW-MFX-001 | Upstream/模型/二进制许可台账 | 000 | exact revision、SHA、许可、NOTICE、回滚齐全 |
| AXW-MFX-010 | 修复 metadata-only 假成功与能力声明 | 000 | 图片/媒体不能再假报内容成功 |
| AXW-MFX-011 | 所有入口统一 RawAsset-first | 010 | 原件先持久化，失败可恢复 |
| AXW-MFX-012 | 隔离旧 credibility heuristic | 000 | 不能产生 web-verified/evidence 状态 |
| AXW-MFX-020 | 阶段信封、状态、对象复用迁移 | 011 | 无平行真相源，迁移可回滚 |
| AXW-MFX-021 | SourceProfiler/PolicyRouter | 020 | 格式/页/隐私/预算路由可解释 |
| AXW-MFX-022 | Worker 阶段任务与预算/租约 | 020 | 幂等、取消、checkpoint、retry 可验证 |
| AXW-MFX-030 | PDF 原生/扫描/混合页管线 | 021,022 | 页级 Block/Anchor/LossReport 与重启回读 |
| AXW-MFX-031 | 图片/扫描 OCR 管线 | 021,022 | Tesseract 基线 + 第二引擎接口，真实 fixtures |
| AXW-MFX-032 | Office/文本管线 | 021,022 | sheet/slide/paragraph 锚点和损失 |
| AXW-MFX-033 | HTML/URL 安全快照与正文 | 021,022 | SSRF 受控、快照可回放、静态优先 |
| AXW-MFX-034 | 音视频 ASR 管线 | 021,022 | VAD+ASR+时间码，metadata 与 transcript 分开 |
| AXW-MFX-040 | 金标准与 benchmark harness | 030–034 | CER/WER/结构/资源可复现，不伪造广泛结论 |
| AXW-MFX-041 | 无金标准多信号质量门 | 040 | 校准版本、reason codes、状态机 |
| AXW-MFX-042 | 局部多引擎差异与 LLM 候选 | 041 | 只升级争议局部，所有差异可回读 |
| AXW-MFX-050 | ClaimTriage、风险与隐私出站 | 020 | 私有/主观/噪声不发网 |
| AXW-MFX-051 | Evidence connector registry | 050 | rate/cache/terms/error contract |
| AXW-MFX-052 | 首批结构化权威连接器 | 051 | Crossref/DataCite/OpenAlex/Wikidata 等 fixtures |
| AXW-MFX-053 | 安全 web fallback 与来源独立性 | 051 | 搜索仅发现候选，快照/转载链可审计 |
| AXW-MFX-054 | CrossValidation/EvidenceBundle 晋级门 | 052,053 | 冲突不覆盖，人工授权后才晋级 |
| AXW-MFX-060 | 内容去重、缓存、增量和 freshness | 041,054 | 版本化 cache key，局部重建 |
| AXW-MFX-061 | Workspace/Evidence/Review UI | 041,054 | 两层状态并排、差异/预算/来源可见 |
| AXW-MFX-062 | 文件/sidecar/web/供应链安全 | 030–054 | 负面 fixtures 与出站阻断 |
| AXW-MFX-063 | Windows capability packs/SBOM/doctor | 001,030–034,062 | 干净 VM installed probes |
| AXW-MFX-070 | 端到端资格、文档和发布声明 | 060–063 | 真实用户流、重启/失败/回滚完整 |

---

## 18. 原子任务详细规格

### AXW-MFX-000 — Truth reset 与提案登记

**改动**：在 `docs/truth/EXECUTION_STATUS_LOG.md` 追加本提案，绑定当日 main SHA、H1 已合并事实、九管线现状和 owner 决策状态；不修改 frozen 文档正文。  
**验收**：旧审计与新事实有日期/来源；“OCR 已实现”“ASR 已实现”“全网验证已实现”分别按 installed/core/skill/reference 状态表达。  
**证据**：源码路径清单、云端 commit/PR/CI 快照、文档 diff。  
**回滚**：仅撤销新增 append-only 记录；不得篡改历史状态。

### AXW-MFX-001 — 供应链与许可台账

**改动**：为每个代码包、模型、语言包、字体、二进制建立 upstream ledger；新增 `approved/review_required/blocked` gate。  
**验收**：MarkItDown/Docling/Tesseract/PaddleOCR/faster-whisper/Whisper/FFmpeg/Trafilatura 及候选项均有 exact revision、下载 URL、SHA、许可文件快照、NOTICE/SBOM、升级与替换。代码许可和模型许可分开。  
**负面测试**：FunASR 模型、MinerU、PyMuPDF 等未批准时 capability probe 必须返回 disabled。  
**回滚**：从 manifest 禁用组件，不影响 RawAsset/旧派生物读取。

### AXW-MFX-010 — 假成功止损

**改动**：把 Pillow/FFprobe 的结果改为 `metadata_only`；引擎成功增加内容后置条件；修正 README/format_capabilities/status。  
**验收**：纯图片没有 OCR 引擎时返回 degraded/unavailable，而不是 success；媒体没有 ASR 时只有 metadata capability；raw HTML fallback 不得在没有正文后置条件时标完整成功。  
**测试**：真实 PNG/JPEG、扫描 PDF、MP3/MP4、空文件、损坏文件、仅 EXIF 图片。  
**回滚**：保留旧 metadata API 兼容字段，撤销内容能力路由即可。

### AXW-MFX-011 — Canonical RawAsset-first

**改动**：`/pipeline`、`/ingest/file`、directory、workspace upload/url 等入口委托同一 intake service；原件与 Job/Outbox/Receipt 同一治理链后再转换。  
**验收**：转换进程崩溃后原件和 Receipt 仍存在；重试不重复保存原件；旧入口响应 DTO 兼容；直接旧知识表写入被投影层替代。  
**测试**：上传后 kill worker、磁盘写失败、重复请求、同内容不同文件名、重启继续。  
**回滚**：feature flag 切回旧入口，但新 RawAsset 不删除。

### AXW-MFX-012 — Legacy credibility 隔离

**改动**：将 `score_credibility` 明确命名/标记为 `legacy_heuristic`，禁止写入 EvidenceBundle、CrossValidation 或 verified 状态。  
**验收**：可信域后缀、DOI 字样或“peer-reviewed”词语不能自动晋级事实；UI 不显示成“全网已验证”。  
**测试**：伪造 DOI、可信域用户内容、转载页、冲突事实。  
**回滚**：可保留旧分数作排序实验，但不能恢复其验证语义。

### AXW-MFX-020 — 核心协议与迁移

**改动**：完成对象复用矩阵、StageRequest/Result、状态与 reason code；最小可逆迁移补 QualityAssessment/TextVariant/EvidenceFetch/BudgetLedger 所缺字段。  
**验收**：每次结果可从 RawAsset 到 Block/Anchor/LossReport 回放；无 DocumentV2/FactV2 平行真相；旧记录有明确 migration/default。  
**测试**：upgrade/downgrade、旧数据库重启、部分迁移失败、并发 worker。  
**回滚**：向下兼容读，新增表/列迁移有 down/disable 路径。

### AXW-MFX-021 — Profiler 与 Router

**改动**：实现文件签名/MIME、加密、页型、语言、隐私、风险、目标 profile、引擎可用性与预算的决策树。  
**验收**：同一输入和 capability snapshot 决策确定；每个分支有 reason code；PDF 可混合页路由；外网禁用不会被引擎自行绕过。  
**测试**：伪扩展、混合 PDF、加密 Office/PDF、CJK/RTL、超大图、未知格式。  
**回滚**：router profile 版本化，可切回上版，不改已生成结果。

### AXW-MFX-022 — Durable stage worker

**改动**：在既有 worker/Outbox 上增加阶段任务、lease、heartbeat、checkpoint、cancel、budget 与错误分类。  
**验收**：一页成功后第二区段崩溃可从 checkpoint 恢复；相同 idempotency key 不重复发布；429 尊重 Retry-After；预算耗尽进 review。  
**测试**：强杀、超时、磁盘满、sidecar exit、网络断开、重复 delivery、取消/重启。  
**回滚**：每种新 job type 可单独 feature flag 禁用。

### AXW-MFX-030 — PDF 页级转换

**改动**：原生/扫描/混合/复杂/损坏/加密页分类；页级引擎；Block/坐标/Anchor/LossReport；必要时 Docling 专页资格实验。  
**验收**：真实文本 PDF 不强制 OCR；扫描页不为空；混合页不重复；表格/双栏损失可见；安装版重启回读。  
**测试**：至少覆盖中英、双栏、表格、脚注、旋转页、扫描、混合、损坏、加密和 100+ 页长文档。  
**回滚**：保留 MarkItDown/pdfplumber 基线 profile，可禁用复杂引擎。

### AXW-MFX-031 — 图片与扫描 OCR

**改动**：Tesseract adapter 输出文字、TSV/box 和引擎元数据；可插拔 Paddle/Easy/RapidOCR；保存预处理派生物和语言包信息。  
**验收**：图片内容进入 DerivedDocument/Block；低质图触发 targeted retry；关键 span 差异可见；没有 OCR 时诚实降级。  
**测试**：印刷/拍照/倾斜/阴影/低分辨率、简中/繁中/英文/混排、数字表格和手写负例。  
**回滚**：每个 OCR adapter 独立开关；Tesseract baseline 不依赖第二引擎。

### AXW-MFX-032 — Office 与文本转换

**改动**：DOCX/PPTX/XLSX/CSV 的结构锚点与 LossReport；legacy sidecar 接口；密码检测；公式/批注/隐藏内容状态。  
**验收**：slide/sheet/cell/paragraph 可引用；公式与图表未解析时不静默消失；宏不执行；CSV 编码/方言可解释。  
**测试**：真实 Office fixtures、嵌入图片、合并单元格、公式、批注、隐藏 sheet、老格式和加密文件。  
**回滚**：逐格式切回 MarkItDown，保留 loss semantics。

### AXW-MFX-033 — HTML/URL 安全摄取

**改动**：安全 fetch + 原始快照 + Trafilatura；Readability 第二结果；动态 browser sidecar 可选；URL canonicalization 和 freshness。  
**验收**：每个正文块可回到抓取快照；SSRF/重定向/大小受控；静态能提取时不启动浏览器；raw fallback 标 warning。  
**测试**：文章、文档页、JS-only、登录墙、robots/429、重定向环、内网 IP、恶意 HTML、重复 URL。  
**回滚**：禁用动态 sidecar，不影响静态快照与旧内容。

### AXW-MFX-034 — 本地 ASR

**改动**：字幕优先、FFmpeg 音轨派生、Silero VAD、faster-whisper、时间码 Block；whisper.cpp 备选接口。  
**验收**：音视频产生 transcript 而非只有 metadata；静音不大量出字；每段回到 RawAsset 时间码；模型/compute type/语言记录完整。  
**测试**：中英/混说、噪声、音乐、静音、长音频、不同采样率、内嵌字幕、CPU 无 GPU、重启续转。  
**回滚**：禁用 ASR pack 后仍保留媒体 metadata 与旧 transcript。

### AXW-MFX-040 — Benchmark 与金标准

**改动**：建立有权使用的分层 fixture corpus、truth/prediction 格式、JiWER 与结构指标、资源/延迟 harness。  
**验收**：至少每类真实输入都有正常/困难/失败 fixture；gold 与 prediction 严格分开；结果绑定 commit、模型哈希、硬件和参数。  
**防误导**：样本不足只报告该 fixture set，不外推“全语言准确率”；没有 gold 的运行不显示 CER/WER。  
**回滚**：benchmark 数据和产品数据隔离，可移除受限 fixture 不破坏产品。

### AXW-MFX-041 — 校准质量门

**改动**：实现代理信号、关键 span 风险、分 profile 阈值、校准版本和七态 outcome。  
**验收**：门控决策有可读 reason codes；原始 confidence 不直接跨引擎比较；阈值变更形成新版本，可在同 fixture 重放。  
**测试**：高 confidence 错数字、低 confidence 但正确、结构丢失但文字正确、ASR 静音幻觉等反例。  
**回滚**：切回上版 gate profile；结果仍保留评估版本。

### AXW-MFX-042 — Differential resolver 与有限 LLM

**改动**：页/坐标/时间码对齐、多引擎 TextVariant/DisagreementSpan；局部 LLM candidate 接口、出站预览和 token ledger。  
**验收**：第二引擎只跑问题局部；LLM 无权覆盖 canonical；数字/专名/公式冲突进 review；零 Token 默认路径测试通过。  
**测试**：同义改写、标点差异、数字差异、坐标错位、模型超时/拒绝/结构错误、预算耗尽。  
**回滚**：关闭 `allow_external_llm` 后全部核心转换仍可运行。

### AXW-MFX-050 — ClaimTriage 与 egress policy

**改动**：规则优先抽取实体/日期/数字/定义/归属/标识符；可查证性、风险、时效、隐私分类；外发最小 query 预览。  
**验收**：私人日记、会议秘密、主观/创作、疑似 OCR 噪声不自动发网；高风险必进人工门。  
**测试**：PII、API key、内部代号、虚构人物、歧义名字、历史与现任职位、乱码。  
**回滚**：关闭自动 triage 时允许人工选择 Claim，不影响转换。

### AXW-MFX-051 — Evidence connector registry

**改动**：统一 query/result/error、rate limiter、cache、terms/licence、source tier、independence group、snapshot contract。  
**验收**：连接器不能绕过 Safe HTTP/egress；429/5xx/访问限制映射稳定；每个 connector 有录制/脱敏 fixture 与 live opt-in test。  
**回滚**：单 connector 熔断/禁用，不影响其他连接器和本地内容。

### AXW-MFX-052 — 结构化权威连接器

**改动**：按顺序实现 Crossref、DataCite、OpenAlex、Wikidata/MediaWiki、Europe PMC/NCBI、Open Library 的最小只读适配。  
**验收**：DOI/PMID/ISBN 精确查优先；User-Agent/mailto/key/rate headers/服务端成本可审计；返回规范 PID、版本与来源。  
**测试**：存在/不存在/歧义/撤回或版本变更、429、schema 变化、额度耗尽、离线缓存。  
**回滚**：版本化 connector，可切旧版或转人工，不伪造结果。

### AXW-MFX-053 — 普通 Web 回退与来源独立性

**改动**：Claim query planner、安全搜索发现、网页快照、转载/共同根来源聚类、时效判断。  
**验收**：搜索摘要不成为证据；两个转载 URL 不计两份独立佐证；页面冲突形成 contested；无法访问标 access_restricted。  
**测试**：SEO 垃圾、复制新闻稿、同域子站、更新后的官方页、404/robots/login wall、prompt injection。  
**回滚**：关闭 web fallback 后仍可使用结构化连接器与人工 URL。

### AXW-MFX-054 — CrossValidation 与晋级

**改动**：EvidenceCandidate → CrossValidation → EvidenceBundle；支持/反驳/部分/时效/独立性；与 research review/promote/learning 对接。  
**验收**：验证状态与识别质量在数据库/API/UI 分开；冲突不改原文；只有 policy 满足且人工授权才产生 VerifiedKnowledge/正式 AI Asset。  
**测试**：单来源、双同源、双独立、权威冲突、过时版本、私人来源、高风险。  
**回滚**：撤销 promotion 生成新版本/决策，不删除 EvidenceBundle 历史。

### AXW-MFX-060 — 去重、缓存、增量

**改动**：实现版本化 cache key、exact/near duplicate、Block/Claim 局部重建、web freshness 与 watcher。  
**验收**：rename 不重算；模型/参数变化会新算；相同内容跨入口复用；近重不自动合并来源；更新证据不重跑 OCR。  
**测试**：复制/改名/一字修改、语言包升级、normalizer 变更、源 URL 内容更新、datasketch 版本变更。  
**回滚**：清单式失效特定 cache namespace，不删除 RawAsset。

### AXW-MFX-061 — UI 与人工复核

**改动**：Workspace 活动条、Import Center、Reader、Evidence 并排视图和统一 review queue。  
**验收**：用户能看到原件、转换版本、质量理由、LossReport、差异 span、验证状态、来源、预算；可接受/拒绝/编辑候选并回到锚点。  
**防混淆**：不得用同一“准确率”显示两层状态；“无法验证”不显示成“错误”。  
**回滚**：BFF DTO feature flag 隐藏新 UI，不破坏 API/数据。

### AXW-MFX-062 — 安全资格

**改动**：文件上限、归档/路径、sidecar sandbox、SSRF、HTML 净化、prompt injection 隔离、秘密/PII 出站、供应链 gate。  
**验收**：负面 fixtures 全部在解析/出站前被阻断或安全降级；日志无密钥/密码/私密 query；进程超限可杀且 job 可恢复。  
**测试**：zip slip/bomb、XXE、恶意宏、超大像素、内网 URL、DNS rebinding、重定向、文档恶意指令、模型篡改哈希。  
**回滚**：安全限制只能通过显式版本化 policy 放宽，不提供隐藏 bypass。

### AXW-MFX-063 — Windows capability pack 与发布

**改动**：基础包/可选模型包、doctor/bootstrap、能力 manifest、SBOM/NOTICE、二进制哈希、离线缓存与卸载。  
**验收**：干净 VM 无 ambient Python/npm/PATH 也能探测；缺 GPU 自动 CPU；缺 pack 显示 unavailable；安装/升级/降级/卸载/保留数据符合政策。  
**测试**：Windows 受支持版本、无网安装、低磁盘、非 ASCII 路径、普通用户权限、模型包损坏、FFmpeg LGPL/GPL build 差异。  
**回滚**：capability pack 独立卸载/回退，核心应用与数据仍可启动。

### AXW-MFX-070 — 端到端资格与声明

**改动**：执行完整用户流与故障流；更新 Capability Atlas、README、状态日志和 release evidence。  
**验收用户流**：真实来源 → RawAsset → 转换 → Block/Loss/Anchor → 阅读/搜索/引用 → Claim 验证 → EvidenceBundle → 人工授权 → 重启回读 → 开放导出。  
**验收故障流**：离线、引擎缺失、模型损坏、预算耗尽、网页冲突、worker 强杀、升级失败均可解释和恢复。  
**发布声明**：只声明 exact fixture/语言/格式/profile 已通过的能力；skill/reference/technical/installed/release/license/learning evidence 状态分开。  
**回滚**：按 release manifest 回退应用/pack/schema；RawAsset 与用户决策历史不丢失。

---

## 19. 推荐实施批次与停止条件

### Batch 0：先止损，不扩能力

执行 MFX-000/001/010/012。先修“假成功、假验证、许可不明”，否则继续增加引擎会放大错误状态。

### Batch 1：统一原件与执行底座

执行 MFX-011/020/021/022。所有入口进入同一 RawAsset-first 和 worker 协议后，再做格式能力。

### Batch 2：完成零 Token 本地闭环

按真实用户优先级执行 PDF/OCR/Office/HTML/ASR；每个格式单独 PR 和真实 installed fixture。不要等待所有格式一起完成。

### Batch 3：质量门与局部升级

执行 MFX-040/041/042。没有 benchmark 与 gate 前，不启用自动第二引擎或 LLM。

### Batch 4：Claim 级验证

先 structured connectors，再普通 web fallback；最后接人工 promotion。不要把通用搜索作为第一版验证核心。

### Batch 5：增量、UI、安全、发布资格

执行 MFX-060–070；只有此批通过后，README/安装器才可把相应能力标为 qualified。

任一任务遇到以下情况必须停止并请求所有者决策：

- 需要修改 frozen authority；
- 需要接受 AGPL/GPL/custom model licence 或购买商业许可；
- 需要把私密内容发送外部服务；
- 需要新增长期常驻服务、重型数据库或 Runtime/Agent 架构；
- 需要删除/覆盖 RawAsset、历史派生物、人工决策或用户 Vault；
- 当前 main/PR 已有重叠实现，无法安全 rebase/拆分。

---

## 20. 每个 PR 的统一完成证据

每个任务提交以下机器可读摘要：

```yaml
task_id: AXW-MFX-xxx
base_sha: exact
head_sha: exact
tree_state: clean|dirty_with_explanation
capability_ids: []
user_actions_proven: []
files_changed: []
migrations: []
dependencies_added:
  - name: exact
    revision: exact
    code_license: exact
    model_license: exact|null
    sha256: exact
tests:
  affected: []
  installed_fixture: []
  negative: []
quality_evidence:
  fixture_set: exact
  metrics: {}
resource_evidence: {}
privacy_egress: none|details
known_losses: []
rollback: command_or_steps
claims_not_proven: []
```

测试通过、fixture 数、Job/Receipt 数、引擎 confidence、模型评分或搜索结果数均不能单独证明产品完成或事实正确。

---

## 21. 完整验收场景

至少覆盖以下端到端 fixtures：

1. 原生中英 PDF：一次本地提取结束，无 OCR/LLM；页/块/锚点可回读。
2. 混合 PDF：原生页 + 扫描页分别路由；不重复；扫描页低质区域定向重试。
3. 复杂表格 PDF：普通引擎有结构损失；专项页引擎产生候选；原结果和差异保留。
4. 中文拍照图片：预处理 + OCR；数字/年份冲突进入 review。
5. DOCX/PPTX/XLSX：结构锚点、图片/公式/隐藏内容损失可见。
6. 静态 HTML：保存快照、Trafilatura 正文；断网时仍可回放。
7. JS-only 页面：静态失败后才启动受控浏览器；禁止访问内网。
8. 中英音频：VAD + faster-whisper + 时间码；静音不出大段文本；CPU 可完成。
9. 私人会议音频：本地转换可以进行，Claim 默认不发网。
10. DOI/ISBN/PMID Claim：标识符直查，返回规范来源；缓存重放不重复计费。
11. 现任职位/软件版本：按 freshness 重新验证，旧证据保留为过时版本。
12. 两个转载网页：识别共同根，不误算独立交叉佐证。
13. 权威来源互相冲突：状态 `contested`，不覆盖原文，进入人工队列。
14. Worker 中途被杀：RawAsset、检查点、已发布块不丢失；重启从局部继续。
15. 模型/引擎缺失：能力诚实降级；用户可安装 pack 或人工处理。
16. 外部 LLM 关闭/预算为零：核心识别、索引与结构化验证仍工作。
17. Windows 干净安装：无开发机 PATH；安装、重启、升级、卸载和数据保留可证明。

---

## 22. 本提案回答五个接入问题

1. **统一还是各自接入？** 统一核心阶段协议与持久化对象；各管线只做入口/投影适配，不建一个同步巨型函数。
2. **门控放哪层？** Conversion worker 后、正式 DerivedDocument 投影前；可页/块/时间段循环。UI/service 不做重计算。
3. **验证自动强制还是异步？** 默认异步、选择性；普通导入不阻断，VerifiedKnowledge/高风险发布/用户指定 verified import 才阻断。
4. **如何接人工治理？** 复用现有 research review/promote/learning，以 EvidenceBundle、DisagreementSpan 和 ReviewDecision 作为队列输入，避免第二套队列。
5. **技能侧如何下沉？** 迁移纯规则、adapter contract、fixtures 和失败用例；核心实现归 repo，技能通过核心 API/CLI 调用，不反向依赖 Hermes runtime。

---

## 23. 官方上游与公共服务核验来源

以下链接仅证明上游当日公开信息；纳入构建时仍须固定 exact revision 并保存许可文件：

- Docling（MIT 代码，模型许可另查）：https://github.com/docling-project/docling
- MarkItDown（MIT、格式能力与安全说明）：https://github.com/microsoft/markitdown
- Apache Tika（Apache-2.0、广格式）：https://github.com/apache/tika
- Tesseract / tessdata（Apache-2.0）：https://github.com/tesseract-ocr/tesseract 、https://github.com/tesseract-ocr/tessdata
- PaddleOCR（Apache-2.0）：https://github.com/PaddlePaddle/PaddleOCR
- faster-whisper（MIT）：https://github.com/SYSTRAN/faster-whisper
- whisper.cpp（MIT、Windows/量化）：https://github.com/ggml-org/whisper.cpp
- Silero VAD（MIT）：https://github.com/snakers4/silero-vad
- sherpa-onnx（Apache-2.0 代码，模型另查）：https://github.com/k2-fsa/sherpa-onnx
- FFmpeg 许可证与构建差异：https://ffmpeg.org/doxygen/trunk/md_LICENSE.html
- Trafilatura（≥1.8 Apache-2.0，旧版 GPL）：https://github.com/adbar/trafilatura
- Mozilla Readability：https://github.com/mozilla/readability
- Crawlee Python：https://github.com/apify/crawlee-python
- Google Magika：https://github.com/google/magika
- JiWER：https://github.com/jitsi/jiwer
- RapidFuzz：https://github.com/rapidfuzz/RapidFuzz
- MinerU 自定义附加许可：https://github.com/opendatalab/MinerU/blob/master/LICENSE.md
- PyMuPDF4LLM AGPL/商业许可：https://github.com/pymupdf/pymupdf4llm
- Marker GPL：https://github.com/datalab-to/marker
- FunASR 代码与模型许可：https://github.com/modelscope/FunASR 、https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE
- Crossref REST：https://support.crossref.org/hc/en-us/articles/214320426-REST-API
- DataCite REST：https://support.datacite.org/docs/api
- OpenAlex 当前 API 认证/计费：https://developers.openalex.org/api-reference/authentication
- Wikidata 数据访问与服务礼仪：https://www.wikidata.org/wiki/Help:Data_access
- Europe PMC REST：https://europepmc.org/RestfulWebService
- NCBI E-utilities：https://www.ncbi.nlm.nih.gov/books/NBK25497/
- Open Library API：https://openlibrary.org/developers/api

---

## 24. 所有者批准项

本任务包可以作为执行输入前，需要项目所有者明确批准：

1. 方案 C 的核心阶段结构与“默认异步验证”政策；
2. 首批默认引擎为 MarkItDown/pdfplumber/pypdf、Tesseract、faster-whisper、Silero VAD、Trafilatura；PaddleOCR/Docling 先资格测试；
3. 外部 LLM 默认关闭、只处理争议局部；
4. MinerU、PyMuPDF、Marker、FunASR/SenseVoice、Zotero/SearXNG 不进入默认包，除非单独通过许可证决策；
5. 采用 `AXW-MFX-*` 任务 ID 或由权威任务包重新映射 ID；
6. 将本文件以 append-only `CHANGE_PROPOSAL` 登记，而不是替代 v4 主任务包。

批准前，本文件只用于审计、估算与任务拆分，不授权修改仓库、远端、用户数据或发布物。
