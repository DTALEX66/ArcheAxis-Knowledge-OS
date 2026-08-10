# ArcheAxis Workspace v0.5 多格式知识工作区全量审计与修复任务包

> 审计对象：`DTALEX66/Cognitive-Loop-OS` 云端仓库、当前 `main`、开放 PR、v0.5.0 安装后实际能力、现有 UI、数据链、任务包与路线蓝图
> 审计日期：2026-08-09
> 项目唯一产品定位：**元枢工作台（ArcheAxis Workspace）——本地优先、证据驱动的人机学习与知识工作区**
> 本文只讨论 OS 项目本体。WORK LAB、旧 Cognitive Loop、旧 B/C/R 运行时蓝图均不作为当前产品主线。

## 0. 最终结论

当前项目不是“PDF 有一个小 bug”，而是**能力定义、安装依赖、数据模型、用户界面、发布验收和任务路线同时错位**：

1. v0.5.0 的安装包没有完整安装 MarkItDown 的 PDF/Office 可选依赖，普通用户上传 PDF 会直接失败。
2. 图片链虽然显示 Pillow/Tesseract 能力，但实际主转换链只输出尺寸、格式和 EXIF 等元数据，没有把 OCR 结果写成知识正文。
3. 音视频链只做 FFprobe 元数据探测，没有转写，却容易被能力名称误解为已支持音视频知识摄入。
4. PDF/Office 即使转换成功，当前数据模型仍主要保存扁平 Markdown；原文件、页码、版面、表格、图片、脚注、批注和转换损失没有形成可靠关联。
5. 上传在请求线程中同步处理，整文件读入内存，25 MB 限制，失败只返回 422 原始错误；没有转换任务、进度、重试、引擎选择和失败恢复。
6. UI 的重心仍是 Runtime、Job、Delivery、Receipt、Audit 等工程治理面，而不是用户每天使用的文件树、阅读器、编辑器、搜索、属性、反链、批注和引用。
7. 旧任务包把“任务持久化、回执、重启回读”判定为后端最小闭环，但这只证明运行时投递，不证明任何真实文档完成了“导入—解析—阅读—引用—再打开”。
8. CI 已开始做选择性门禁，但发布资格仍没有真实安装包的格式能力验收。项目过去优化了“代码是否按规则运行”，却没有证明“用户的文件是否真的可用”。

因此，当前状态应定义为：

> **治理与任务运行基础较强，但作为知识工作区尚未形成安装后可用的最小产品闭环。**

后续不应继续扩展通用 Agent Runtime、Machine、Evolution、多代理、市场、3D/VR 或更多治理界面。当前唯一主线应改为：

> **真实文件 → 可解释转换 → 原文/结构/来源保真 → 阅读与编辑 → 搜索/链接/引用 → 重启回读 → 开放导出。**

第一发布闭环为 PDF；第一高保真互操作闭环仍为 Obsidian Vault / Markdown / JSON Canvas。两者共同构成 ArcheAxis Workspace 的最小产品面。

---

## 1. 云端仓库最新状态

审计时云端 `main` 为：

- Commit：`492fac5982c693eb668d31cc51a6a59bac83b7a1`
- 最新提交：`docs: clarify desktop release evidence boundary (#67)`
- 仓库：[DTALEX66/Cognitive-Loop-OS](https://github.com/DTALEX66/Cognitive-Loop-OS)

当前三个开放 PR：

| PR | 内容 | 审计判断 |
|---|---|---|
| [#68](https://github.com/DTALEX66/Cognitive-Loop-OS/pull/68) | `fix/pdf-runtime-dependencies` | 方向正确但不完整；CI 失败，且只修 PDF extra，未修 Office、安装器格式验收和数据模型 |
| [#69](https://github.com/DTALEX66/Cognitive-Loop-OS/pull/69) | Desktop no-console | CI 成功，可独立处理，不应与知识摄入主线混合 |
| [#70](https://github.com/DTALEX66/Cognitive-Loop-OS/pull/70) | 新摘要/总结 | 不应按原文直接合并；其中 B/C/R 严格顺序、后端闭环 PASS、`ArcheAxis OS` 名称和本机路径均与当前产品真相冲突 |

### 1.1 PR #68 的真实状态

PR #68 把 `markitdown>=0.1` 改为 `markitdown[pdf]>=0.1`，这证明 PDF 报错的直接原因已被找到：安装包缺少 PDF 可选依赖。但当前仍有四个阻断：

- 分支落后 `main`，需要先更新基线。
- `requirements.txt` 未同步，依赖真相不一致。
- 旧元测试仍硬编码旧依赖字符串，CI 出现 2 个失败；该次运行是 1106 passed、1 skipped、2 failed。
- 新增所谓“真实 PDF”测试只生成空内容 PDF，并只断言结果是字符串；它不能证明任何文字、页码、表格或中文内容被正确识别。

更严重的是，CI 聚合门禁存在命名不一致：GatePlan 返回 `py-primary`，聚合逻辑却检查 `test`。这可能导致核心 Python job 失败时，聚合 job 仍显示成功。即使整个 workflow 当前仍因子 job 失败而红，这种不一致也不能进入分支保护或发布资格判断。

### 1.2 发布资格的盲点

当前 Release 流程的安装器生命周期验证包括：安装、启动、健康检查、工作区响应、关闭、子进程清理、卸载等。这些是必要的，但没有任何真实 PDF/Office/图片通过**安装后的 bundled runtime + Desktop/WebView** 完成导入和读取。

这解释了为什么 CI 和安装器门禁可能全部通过，用户仍然无法上传 PDF：

> **现在验证的是“应用能启动”，不是“产品能力能工作”。**

---

## 2. 根因：项目把五种不同状态混成了“支持”

任何格式都必须经过以下状态，不能再用一个 `available` 覆盖：

1. **Detected**：能识别扩展名/MIME。
2. **Dependency-ready**：当前安装环境真的具备引擎、模型和外部二进制。
3. **Converted**：能产出非空且可验证的正文或结构。
4. **Validated**：关键文本、页/幻灯片/工作表结构和损失符合验收标准。
5. **Persisted**：原文件、派生结果、哈希、引擎版本和损失报告已经事务化保存。
6. **Indexed**：搜索、链接和引用索引可用。
7. **Presented**：用户能在界面中阅读、定位、编辑、引用和处理错误。
8. **Restart-readback**：重启后能打开同一结果，锚点不漂移。
9. **Export/roundtrip**：可开放导出，原文件不丢，冲突可检测和恢复。

HTTP 200、生成一条 JobReceipt、或把文字写进 SQLite，只能证明其中一小步，不能称为格式支持。

---

## 3. 多格式后端全链审计

### 3.1 PDF

现状：

- 主引擎声明为 MarkItDown，后备列表包含 Marker、Docling。
- v0.5.0 安装包缺 `markitdown[pdf]` 可选依赖，因此真实 PDF 直接失败。
- Marker、Docling 只是代码中的候选导入，并没有形成稳定的默认安装与运行配置。
- 成功时主要得到扁平 Markdown，没有可靠页锚点、版面块、表格单元格、图片、公式和转换损失。
- 自动生成的“第一条 claim”只是转换文本的首个非空行，位置固定为 `document:first-claim`，无法构成学术引用。

判断：**PDF 当前为不可发布状态。**

### 3.2 DOCX / PPTX / XLSX / XLS

现状：

- 当前都只走 MarkItDown。
- MarkItDown 官方将这些格式拆为独立 optional extras；只安装基础包不能证明 Office 支持。
- 没有安装包内的真实 Word、PowerPoint、Excel fixture 验证。
- 当前模型也没有段落样式、幻灯片编号、演讲者备注、工作表/单元格坐标等稳定锚点。

判断：**界面和文档不得声称已支持。**

### 3.3 图片与 OCR

现状：

- 图片主链先走 Pillow。
- Pillow 转换器只输出格式、宽高、模式、EXIF 等元数据。
- Tesseract/pytesseract 可能被环境探测到，但没有接入实际的图片知识转换链。
- 因此 PNG/JPG smoke 通过，只说明图片能被 Pillow 打开，不代表图片文字已进入知识库。

判断：能力名称应拆为 `image_metadata` 和 `image_ocr`；前者可用，后者当前不可用。

### 3.4 音频与视频

现状：

- FFmpeg/FFprobe 只输出容器、编码、时长等媒体元数据。
- 没有 ASR，没有时间戳文本，没有说话人信息，也没有音视频片段锚点。
- `audio_track_and_video_keyframes` 等能力名容易造成已完成知识提取的错觉。

判断：当前只能标为 `metadata_only`。在 ASR 落地前，不得称为音视频知识摄入。

### 3.5 HTML / CSV / Markdown / TXT

- Markdown/TXT 是最可靠的当前基线，应明确作为原生格式。
- HTML 使用 Trafilatura 是合理方向，但仍需保存原 URL/文件、抓取时间、标题、正文选择和丢失项。
- CSV 应保持表结构、列类型和行坐标，不能只降为文本。

### 3.6 JSON Canvas

现有解析会把节点文本、文件/链接/分组标签压成普通文本，边和空间关系没有进入统一知识模型。现有应用内 Canvas 又是独立 SQLite 模型，不等同于 Obsidian JSON Canvas。

判断：当前只能叫 `canvas text extraction`，不能叫 JSON Canvas 兼容。

### 3.7 Vault 与附件

当前兼容层扫描附件时会把二进制完整读入内存；大型 PDF、视频或 2 万文件 Vault 都有明显风险。Vault 检查和搜索仍可能反复全量扫描，没有成熟的增量索引、忽略策略、预算、游标、重命名和删除同步。

已存在原子写、expected-hash 和 rollback 基础，这部分值得保留；但它还没有进入用户可操作的冲突界面。

---

## 4. 后端应调整为“原件—转换—知识”三层架构

### 4.1 原件层：Raw Asset Layer

必须永久区分原件与派生内容。建议核心实体：

```text
RawAsset
  asset_id
  content_hash
  original_name
  mime_type
  size
  source_kind / source_locator
  imported_at
  immutable_blob_ref

ImportBatch / ImportItem
  用户本次选择了什么、每项状态、授权根目录、失败与重试
```

要求：

- 原文件不可被转换结果覆盖。
- 大文件流式/分块写入磁盘，不得在 HTTP 请求和 Vault 扫描中整文件常驻内存。
- 内容寻址哈希必须基于原文件，同时单独记录派生结果哈希。
- 目录导入使用批准根目录、realpath/symlink containment 和明确忽略规则。

### 4.2 转换层：Conversion Layer

```text
ConversionRun
  run_id / asset_id
  engine / engine_version / model_version
  conversion_profile
  state: queued → extracting → ocr → structuring → validating → indexing → ready
  started_at / finished_at
  warnings / error_code / retryability

DerivedDocument
DerivedBlock
  page / slide / sheet / section
  block_type
  text / table / figure / formula
  source_bbox / source_anchor

LossReport
  unsupported_elements
  dropped_elements
  confidence
  fallback_used
```

要求：

- 转换必须作为异步持久化任务执行，支持取消、超时、重试、换引擎和断点。
- 引擎失败返回结构化错误码，不能把 Python 异常原样扔给普通用户。
- 格式能力由安装环境运行探针和真实 fixture 共同生成，不再由静态 manifest 自报。
- 任何降级都必须显示，例如“表格转为纯文本”“扫描页仅 OCR”“未识别公式”。

### 4.3 知识层：Knowledge & Evidence Layer

```text
EvidenceAnchor
  raw_asset_hash
  page_or_slide
  bbox_or_cell_range
  derived_block_id

Annotation
  anchor / quote / comment / color / author / revision

KnowledgeCandidate
  statement / source anchors / review state

IndexRevision
  parser/chunker/embedding version
```

要求：

- 转换文本默认是“来源材料”，不是已验证知识。
- AI 回答、卡片、笔记和学习项必须引用 EvidenceAnchor。
- 研究者必须能够从引用跳回 PDF 原页/区域，从派生文本跳回原件。
- 批注保存在数据库中以支持同步、冲突和搜索，同时允许导出到开放格式或嵌入副本。

---

## 5. 引擎与开源复用规划

坚持“许可合规的成熟源码/依赖/CLI/sidecar 优先，自研最后”。但“开源”不等于可以直接复制，必须为每个包记录 repo、revision、license、模型许可、集成方式和隔离边界。

| 能力 | 推荐顺序 | 许可/架构判断 |
|---|---|---|
| PDF 基线文本 | MarkItDown PDF extra；必要时 pypdf 辅助页级处理 | MarkItDown 适合文本分析基线，不适合单独承担高保真阅读模型 |
| 富 PDF/Office 结构 | [Docling](https://github.com/docling-project/docling) 可选本地引擎 | 代码 MIT；模型需逐项审查；可产出更丰富的结构文档 |
| 扫描 PDF/图片 OCR | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 可选 sidecar；Tesseract 作为轻量基线 | PaddleOCR Apache-2.0；模型许可仍需入账 |
| 广格式兜底 | [Apache Tika](https://github.com/apache/tika) 可选 sidecar/CLI | Apache-2.0，但 Java 运行时较重，不宜默认塞入轻安装包 |
| PDF 阅读器 | [PDF.js](https://github.com/mozilla/pdf.js) | Apache-2.0；优先直接复用，避免自研 PDF viewer |
| 音频转写 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 可选本地 sidecar | 代码 MIT；模型许可和体积单独治理 |
| MinerU | 只做候选评估 | 当前带附加条件的自定义许可，必须先完成法务/分发决策 |
| PyMuPDF | 不作为默认打包依赖 | AGPL-3.0/商业双许可，与 MIT 分发目标冲突风险高 |
| SiYuan / Logseq | 研究 UX、协议和 fixture | AGPL-3.0，不能未经决策直接复制进 MIT 产品 |
| AFFiNE | 按 package 审查后再决定 | 许可混合，不能把整个仓库视为统一可复制资产 |

MarkItDown 官方文档明确列出 `[pdf]`、`[docx]`、`[pptx]`、`[xlsx]`、`[xls]`、`[audio-transcription]` 等可选能力，并说明其输出主要面向文本分析，而非高保真人类阅读转换：[官方 README](https://github.com/microsoft/markitdown/blob/main/README.md)。所以它适合第一层 baseline，不应成为全部文档能力的唯一架构。

---

## 6. UI 与信息架构重排

### 6.1 现有界面的核心问题

当前 UI 的默认导航和常驻区域仍然把用户带到：Runtime、Delivery、Research、Evidence、Machine、Evolution、Diagnostics、Audit 等系统概念。右侧 Inspector 和底部 Activity/Job 区占据大量空间，却缺少用户最基本的知识工作面。

Vault 页面需要手工输入 Windows 绝对路径，文件与搜索结果主要以 `<pre>` 展示；没有可点击文件树、系统目录选择器、笔记编辑器、PDF 阅读器、属性、标签、反链、附件预览和搜索筛选。Import 弹窗只显示引擎、字符数、前 400 字和原始错误，失败后用户不知道缺什么、怎么重试、结果保存到哪里。

### 6.2 目标桌面布局

```text
┌ 顶栏：工作区切换 | 全局搜索 | 导入 | 同步/能力状态 | 用户设置 ┐
├ 左栏 ─────────┬ 中央多标签工作区 ─────────────┬ 右侧上下文栏 ┤
│ Library/Vault │ Markdown 编辑/阅读             │ 大纲         │
│ 文件树        │ PDF.js 阅读器                  │ 属性/标签    │
│ 收藏/集合     │ Office 结构预览                │ 反链/引用    │
│ 标签          │ JSON Canvas / Graph            │ 批注         │
│ 保存的搜索    │ 数据表/图片/媒体转写            │ 带引用 AI    │
├───────────────┴───────────────────────────────┴──────────────┤
│ 可折叠任务条：仅在导入/转换/索引运行或失败时出现               │
└──────────────────────────────────────────────────────────────┘
```

一级导航建议只保留：

1. **Workspace**：最近文档、项目/课程、继续阅读。
2. **Library**：Vault、文件树、集合、标签、导入中心。
3. **Search**：全文、属性、引用、批注和筛选。
4. **Canvas / Graph**：JSON Canvas 与关系视图。
5. **Learning**：从引用材料生成并复核的学习项。
6. **Settings**：存储、引擎、隐私、导入规则、诊断。

Research / Evidence / Knowledge / Runtime / Delivery / Machine / Evolution 应移入“高级/治理”抽屉，或作为对象状态存在，不再作为普通用户必须理解的一级页面。

### 6.3 导入中心

导入前：

- 检测格式、大小、是否扫描件、可用引擎与缺失依赖。
- 明确显示“可完整处理 / 可降级处理 / 仅元数据 / 当前不可用”。
- 支持文件、文件夹、Vault、拖放、系统目录选择器。

导入中：

- `排队 → 提取 → OCR → 结构化 → 验证 → 索引 → 完成`。
- 显示页数、进度、当前引擎、耗时和可取消操作。

导入后：

- `打开结果`、`打开原件`、`查看损失报告`、`重新转换`、`换引擎`。
- 单文件失败不拖垮整个批次。
- 错误文案面向用户，例如“当前安装缺少 PDF 组件；安装组件/更新到 v0.5.1”，同时保留可复制的诊断 ID。

### 6.4 PDF 阅读与知识动作

PDF 视图至少需要：

- 缩略图、目录、页码、页内搜索、连续/单页模式。
- 文字选择、高亮、批注、引用复制。
- 从高亮生成笔记/卡片/候选知识，同时保存页码和坐标。
- 派生 Markdown 与原 PDF 双向跳转。
- 原件、转换结果、OCR 层和损失报告可切换。
- 重启应用后批注、选区和引用定位不漂移。

---

## 7. 不同用户视角的验收标准

### 7.1 普通用户

用户只关心“拖进来能不能打开”。安装后第一份 PDF 不应要求懂 Python extra、OCR、adapter 或 gate。失败必须能解释、能重试、不会丢原文件。

**成功标准**：从安装到打开首份 PDF 的时间可预测；同一界面能看到导入进度和结果；重启后仍可继续阅读。

### 7.2 学生

典型材料是教材 PDF、老师 PPT、课程 DOCX、网页和课堂录音。需要按课程组织、搜索、批注、生成带出处的笔记和复习卡。

**成功标准**：每张卡片能返回原页/原幻灯片；不能只生成脱离来源的 AI 摘要。

### 7.3 教师

需要批量导入课程文件夹、讲义、PPT、论文和表格；保留目录结构，组织课程包，更新版本后不重复导入，能开放导出给学生。

**成功标准**：批量任务可恢复、重名和更新可解释、原文件可追溯、课程资料可迁移。

### 7.4 研究学者

关注页码、章节、表格、图、公式、脚注、参考文献和可复现性。任何静默丢失都比明确失败更危险。

**成功标准**：引用包含原件哈希、页/区域和解析版本；可以从结论回到原文；转换损失显式；可与 Zotero 风格的批注/来源体系互操作。

Zotero 将批注保存在数据库以支持同步和冲突，同时支持导出/嵌入副本，这种“内部可靠状态 + 外部可移植”设计值得采用：[Zotero annotation design](https://www.zotero.org/support/kb/annotations_in_database)。

### 7.5 专家与重度用户

需要大 Vault、大 PDF、批处理、增量索引、自定义引擎、版本锁定、失败重跑、脚本/API 和可审计导出。

**成功标准**：同一原件和转换 profile 具备缓存；引擎升级可重新派生而不覆盖旧结果；索引可重建；可查看每个结果的来源和版本。

### 7.6 隐私、无障碍与低配置用户

- 本地文件默认不出机；任何云引擎必须明确选择。
- 目录授权必须清晰，不能隐式扫描任意路径。
- 键盘导航、屏幕阅读、焦点、对比度和错误提示必须进入 UI 验收。
- OCR 语言包、模型体积和硬件需求必须在安装前/设置中透明显示。
- 低配置设备要允许选择轻量引擎、页数预算和后台处理。

---

## 8. 当前能力评分（证据型，不以测试数量计分）

| 维度 | 当前分 | 主要原因 | 8 分门槛 |
|---|---:|---|---|
| 产品定位真相 | 7/10 | 正式定位已清楚，但部分 AGENTS、PR 文档和 UI 仍叫 OS/旧运行时路线 | 所有用户入口、代理入口、路线、能力名统一为 Workspace |
| 安装后知识摄入 | 2/10 | PDF/Office 依赖缺失；图片无 OCR；媒体仅元数据 | 干净 Windows 安装后真实多格式矩阵通过 |
| 多格式转换 | 2/10 | 扁平文本、空 PDF 测试、缺结构/损失 | PDF/Office/OCR 结构化、可验证、可重跑 |
| 来源与派生数据模型 | 3/10 | 有哈希/证据基础，但缺原件—页块—知识稳定映射 | RawAsset/ConversionRun/Anchor/LossReport 完整落地 |
| 日常工作区 UI | 2.5/10 | 更像治理/任务仪表盘，缺阅读器/编辑器/文件树 | 用户无需理解 Runtime 即可完成导入—阅读—引用 |
| 证据治理 | 6/10 | 候选、事务、审计基础较强 | 与真实页/区域引用连接，不再用首行伪 claim |
| Obsidian/开放互操作 | 3/10 | 单向/基础扫描，缺高保真 roundtrip | Markdown/附件/属性/链接/Canvas/冲突完整闭环 |
| 发布能力验收 | 3.5/10 | 启动和生命周期门禁强，产品格式门禁空缺 | exact-SHA 安装包完成真实格式与重启回读 |
| 任务包与蓝图对齐 | 3/10 | 旧 B/C/R、Agent/Runtime 路线仍争夺主线 | 当前唯一权威路线改为知识摄入和 Workspace 闭环 |
| CI 效率与正确性 | 5.5/10 | 已有选择性 GatePlan，但依赖变更漏桌面资格，聚合命名有 bug | 变化分类与产品风险一致，发布证据不可误绑定 |

---

## 9. 蓝图与任务包的去污染和重排

### 9.1 保留为当前真相

- `docs/PRODUCT_POSITIONING.md` 的本地优先、证据驱动、人机学习知识工作区定位。
- 产品公开名：**元枢工作台 / ArcheAxis Workspace**。
- 原子写、哈希、审计、候选复核、回滚、安装器生命周期等基础设施。
- Obsidian Vault / Markdown / JSON Canvas 作为第一高保真兼容切片。

### 9.2 降级为历史/延期蓝图

- `FUTURE_EXECUTION_BLUEPRINT` 旧 A-N 强制顺序。
- `ABSORPTION_EXECUTION_MATRIX` 中把 Obsidian 和前端放到重型 runtime 之后的顺序。
- B 线“不做 Obsidian”的 IR→Contract→ContextPack→TaskPack→MachineLesson 主闭环。
- C 线以 schema/fixture/report 为产品闭环的定义。
- 通用 Agent Runtime、多代理、技能/模型市场、Machine/Evolution、企业协作、3D/VR。

它们可以保留在 `docs/legacy/` 或 `docs/deferred/`，但必须从 AGENTS、README 当前执行入口和新任务生成器中排除。

### 9.3 PR #70 处理建议

**不要原样合并。** 可保留的内容只有：区分证据层级、承认安装包多格式仍是 NO-GO、记录已验证范围。必须重写：

- `ArcheAxis OS` → `ArcheAxis Workspace`。
- 删除 `D:/...` 本机路径、临时分支和 WIP 现场信息。
- 删除“B/C/R 严格唯一顺序”和“后端最小闭环 PASS”。
- 1161 项 fixture 必须标明实际构成主要是 Markdown/Canvas/TXT，不得作为 PDF/Office/媒体能力证据。
- PNG/JPG Pillow smoke 标为 metadata-only，不得写成图像知识处理通过。
- 将当前 NO-GO 直接转为本文 P0/P1 任务，而不是继续总结旧运行时。

---

## 10. 总修复任务包

### TP-00：立即止损与能力真相（P0，1–2 天）

目标：停止把不可用能力交付给用户。

任务：

- 在 README、安装说明、能力面板和 Release notes 明确 v0.5.0 已知问题：PDF/Office 不具备安装后验证，图片 OCR/ASR 未接入。
- 不改写已有 tag/资产；准备 v0.5.1 热修复。
- 所有 format capability 增加状态：`ready`、`degraded`、`metadata_only`、`missing_dependency`、`not_implemented`。
- Import UI 在转换前做运行探针并显示状态。
- 暂停新增 Runtime/Machine/Evolution 导航与功能。

验收：用户在选择文件后、点击转换前就能知道该格式能否工作；文档、UI、manifest 与安装环境一致。

### TP-01：修复 PR #68 与发布门禁（P0，2–4 天）

任务：

- 更新 PR #68 到最新 main；同步 `pyproject.toml`、`uv.lock`、`requirements.txt` 和所有依赖契约。
- 第一阶段至少安装 `markitdown[pdf,docx,pptx,xlsx,xls]`；若实际包 extra 名称有差异，以锁文件和安装后探针为准。
- 删除“文本伪装成 .pdf”和“空 PDF 只断言字符串”的假测试。
- 加入真实小型 fixtures：双语 born-digital PDF、多页 PDF、表格 PDF、扫描 PDF；分别断言已知文本、页数/锚点、损失状态。
- 修复 GatePlan `py-primary` / aggregator `test` 命名不一致。
- `pyproject.toml`、锁文件、bundle 脚本、格式适配器变化必须触发 desktop-build + installed-format qualification，不能只跑 wheel/Python。
- Release 只接受 exact-SHA 的 full qualification attestation，不能只查一个名为 CI 的成功 run。

验收：干净 Windows 安装 v0.5.1 后，用户通过真实 Desktop UI 上传 fixture PDF、打开结果、重启回读；任一步失败 Release 必须红。

### TP-02：原件与转换任务模型（P0/P1，1 周）

任务：

- 落地 RawAsset、ImportBatch、ImportItem、ConversionRun、DerivedDocument/Block、LossReport。
- 上传改为磁盘 spool/流式哈希；移除整文件 `await read()` 和固定 25 MB 的单一策略。
- 按格式设置可配置预算；大文件后台化，支持取消、超时和重试。
- 原文件 blob 与派生结果分别存储、分别哈希。
- 结构化错误码：missing dependency、encrypted PDF、corrupt file、OCR required、timeout、unsupported element 等。

验收：进程崩溃/重启后任务状态可恢复；批次中单文件失败不影响其他文件；原文件永不丢失。

### TP-03：PDF 第一产品闭环（P1，1–2 周）

任务：

- MarkItDown/pypdf 提供轻量 born-digital baseline。
- 评估并接入 Docling optional profile，保留页、块、表、图、公式结构；完成模型许可登记。
- 扫描 PDF 使用 Tesseract baseline 或 PaddleOCR optional sidecar。
- 建立 EvidenceAnchor：原件 hash + page + bbox + derived block。
- 前端接入 PDF.js，完成原文阅读、搜索、选区、高亮、批注、引用跳转。
- 引用生成的笔记/卡片必须能返回原页。

验收闭环：

```text
安装 → 导入 PDF → 查看进度 → 打开原 PDF/派生文本
→ 高亮并生成带页码笔记 → 搜索找到 → 重启 → 回到原页
→ 导出原件、笔记和引用数据
```

### TP-04：Workspace UI 骨架重构（P1，1–2 周，可与 TP-03 并行）

任务：

- 导航改为 Workspace / Library / Search / Canvas-Graph / Learning / Settings。
- 落地可点击文件树、系统目录选择器、中央 tabs、右侧上下文面板。
- Job/Receipt/Audit 移入可折叠高级面板；底部任务栏仅有任务时出现。
- Import Center 完成预检、阶段进度、错误恢复、损失报告和“打开结果”。
- 接入现有 `/api/vault/file` 或重构统一文件 API，不再 `<pre>` dump。
- 完成键盘、焦点、屏幕阅读和窗口尺寸 smoke。

验收：新用户不接触 Runtime/Delivery 概念，也能完成 PDF 和 Markdown 的完整流程。

### TP-05：Office、图片和表格矩阵（P1/P2，1–2 周）

任务：

- DOCX：标题层级、段落、表格、图片引用、脚注损失报告。
- PPTX：幻灯片号、标题、正文、备注、图片和顺序。
- XLSX/XLS/CSV：工作表、表头、行列坐标、公式/显示值策略。
- 图片：实际接通 OCR；保留尺寸、旋转、语言、置信度和 bbox。
- 每类都有 tiny / normal / malformed / password or unsupported fixture。

验收：安装器中每种格式至少有一个真实内容 fixture 经 UI 导入、索引、打开、重启回读；不是只 import 模块。

### TP-06：Vault / Obsidian 高保真兼容（P2，2–4 周）

任务：

- 增量扫描、ignore、游标、stable file ID、hash/mtime、rename/delete。
- 完整 YAML frontmatter、wikilink、embed、heading/block reference、tags、attachments。
- JSON Canvas 节点、边、坐标、分组和文件引用。
- 搜索索引、反链、属性、附件预览进入 Workspace UI。
- expected-hash 冲突检测、三方选择、原子写、备份和 rollback UI。
- Windows/Tauri 真实 Vault open-edit-save-restart-roundtrip。

验收：同一 Vault 可被 Obsidian 与 ArcheAxis 往返打开；未支持项有 loss report；冲突不静默覆盖。

### TP-07：引用 AI 与学习层（P2/P3）

前置条件：TP-03 至 TP-06 的来源锚点已稳定。

任务：

- AI 回答必须逐段引用 EvidenceAnchor。
- AI 不能把转换文本自动升级为已验证知识。
- 笔记、卡片、候选知识和课程复习项保留来源与复核状态。
- 支持从 PDF/笔记/批注生成学习项，并一键回原文。

验收：删除模型生成文本后，原件、批注和人工笔记仍独立存在；每条已采纳知识有可验证来源。

### TP-08：媒体与广格式扩展（P3，延期）

- FFmpeg 负责音轨和关键帧提取，不再冒充转写。
- faster-whisper optional sidecar 产生带时间戳 transcript。
- Apache Tika/Unstructured 只作为可选广格式 fallback，经体积、安全和许可评估后接入。
- 只有完成“转换—索引—展示—重启回读”才允许在 UI 标为支持。

### TP-09：蓝图、文档与命名归一（P0/P1）

- `AGENTS.md`、README、状态页、路线、taskpack 和 release-manifest 统一 `ArcheAxis Workspace / 元枢工作台`。
- 仓库名可暂时保留以避免迁移风险，但产品 UI、包描述和文档不再以 Cognitive Loop 或 ArcheAxis OS 对外。
- 将旧 A-N、B/C/R、Cognitive Loop 重型材料迁到 legacy/deferred。
- 新建唯一权威 `CURRENT_PRODUCT_PLAN.md`，只引用本任务包的当前阶段。
- 建立“能力声明契约测试”：扫描所有用户可见的 `available/已支持/PASS`，要求存在安装包真实 fixture 证据。

---

## 11. 新的验证与发布标准

验证应服务于产品风险，而不是继续堆数量。

### 普通 PR

- 静态检查、lint、Python 3.12 主测试、受影响契约。

### 格式适配器或依赖变化

- 对应格式真实 fixture。
- bundled runtime 探针。
- desktop-build。
- 至少一条安装后 API smoke；涉及 UI 时加 WebView/browser smoke。

### UI 阅读器/导入中心变化

- 浏览器 smoke + Desktop smoke。
- 可访问性、焦点、错误态、空态和小窗口。

### Nightly

- PDF/Office/图片/Markdown/HTML/CSV 全矩阵。
- malformed/encrypted/large/retry/restart。
- Vault 增量、重命名、冲突和 roundtrip。

### Release Candidate / 正式 Release

必须由 exact-SHA full qualification 产生不可歧义的证据：

- source tree、workflow/policy hash、lock hash、bundle manifest、安装器 hash。
- clean Windows 安装。
- Desktop UI 真实上传并打开多格式 fixtures。
- 页面/幻灯片/工作表锚点断言。
- 重启回读。
- 原文件下载 hash 回读。
- 卸载和数据保留策略。

“1118 tests passed”不能替代上述能力证据；反过来，也不需要每个普通 PR 都重跑完整安装器矩阵。

---

## 12. 执行顺序与发布里程碑

### v0.5.1：PDF 生存修复

只包含 TP-00、TP-01 和 TP-02 的最小必要部分：依赖真相、真实 PDF、结构化错误、安装后验证。没有干净安装证据不得发布。

### v0.6：PDF 知识闭环

TP-02、TP-03、TP-04。目标不是“更多后台 API”，而是用户能阅读、批注、引用和重启回读。

### v0.7：多格式学习材料

TP-05：Office、图片 OCR、表格，覆盖学生/教师常见材料。

### v0.8：Obsidian-compatible Workspace

TP-06：Vault 文件树、编辑、属性、链接、搜索、附件、JSON Canvas、冲突与 roundtrip。

### v0.9：引用 AI 与学习闭环

TP-07。只有来源锚点可靠后，才扩大 AI 与学习层。

### v1.0 候选

必须满足：

- 五类普通用户都能在安装版完成核心流程。
- 产品 UI 无需暴露内部 runtime 概念。
- PDF/Office/OCR/Vault 具有能力真相和开放导出。
- 所有发布声明都有 exact-SHA 安装证据。
- 重型 Agent/市场/企业协作不再阻塞 1.0。

---

## 13. 下一步立即动作

按顺序执行，不再继续追加蓝图：

1. 暂停合并 PR #70，按本文重写为当前产品真相。
2. 修复并更新 PR #68，但把目标从“加 `[pdf]` 字符串”提升到“安装后真实 PDF 闭环”。
3. 立即修复 GatePlan 聚合命名错误，防止失败 job 被聚合门禁漏判。
4. 新开 TP-00/TP-02 数据模型与能力真相 PR。
5. 新开 PDF.js Reader + Import Center 垂直切片；同一 PR/TaskPack 必须带安装后验收脚本。
6. 把 README 的“下一刀”从 failure/retry/replay runtime UI 改为 PDF/多格式知识摄入闭环。
7. 冻结通用 Runtime/Machine/Evolution 扩展，直到 v0.8 最小产品面完成。

## 14. 管理层一句话判定

> 项目现在最需要的不是更多门禁、更多任务回执或更多“支持”标签，而是让一名普通用户安装应用后，真正把一份 PDF 变成可阅读、可定位、可引用、可重启、可导出的知识资产。只要这条链没有通过，任何更重的蓝图都应延期。
