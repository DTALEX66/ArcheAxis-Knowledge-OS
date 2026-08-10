# ArcheAxis Workspace 未来总蓝图 v1.0

> 中文名：**元枢工作台**
> 英文名：**ArcheAxis Workspace**
> 蓝图日期：2026-08-09
> 蓝图性质：项目未来唯一权威产品与技术路线
> 适用对象：产品、设计、前端、后端、桌面端、数据、AI、测试、发布与开源吸收工作

---

## 0. 蓝图裁决

ArcheAxis Workspace 的未来不是继续扩建一个抽象的“认知闭环 OS”，也不是先做通用 Agent Runtime、任务编排平台或工程治理控制台。

项目重新定义为：

> **一个本地优先、证据驱动、开放兼容的人机知识与学习工作台。它首先全面兼容 Obsidian 的开放数据和核心工作方式，同时将 PDF、Office、网页、图片、音视频等真实资料可靠转化为可阅读、可编辑、可引用、可学习、可导出的知识资产。**

未来全部功能都必须服务于这一条主链：

```text
真实资料
→ 原件安全保存
→ 可解释的格式转换
→ 结构化知识与来源锚点
→ 阅读、编辑、搜索、链接和画布
→ 带引用 AI 与学习
→ 开放导出、往返兼容、冲突恢复
```

不能进入这条主链、不能改善用户真实知识工作的内容，一律降级为远期、实验性或内部能力。

---

## 1. 项目北极星

### 1.1 产品使命

让个人能够在不丢失原始资料、不丢失出处、不被单一软件锁定的前提下，把分散在文件、网页、笔记库和媒体中的信息，转化为长期可使用、可验证、可迁移的知识。

### 1.2 产品愿景

ArcheAxis 最终应成为个人本地知识资产的统一入口：

- 可以直接接管现有 Obsidian Vault，而不是要求用户重建知识库。
- 可以可靠处理 PDF、Office、图片、网页和媒体，而不是只处理 Markdown。
- 可以保留来源、页码、结构、批注和转换损失，而不是只生成一段摘要。
- 可以在用户自己的文件上使用本地或可选云端 AI，而不是把 AI 放在产品中心。
- 可以把数据带走、让其他软件重新打开，而不是制造新的封闭格式。

### 1.3 北极星指标

主指标不是测试数量、任务回执数量或 Agent 调用次数，而是：

> **有效知识资产闭环率：用户导入的真实资料中，有多少完成了“可读取、可定位、可搜索、可引用、可重启、可导出”。**

辅助指标：

- 首份真实资料成功打开率。
- 安装后 PDF 成功转换率。
- Obsidian Vault 往返无损率。
- 来源锚点稳定率。
- 转换损失可见率。
- 崩溃/重启任务恢复率。
- 用户从导入到首次有效笔记的时间。

---

## 2. 产品身份与命名体系

### 2.1 对外唯一名称

| 层级 | 名称 |
|---|---|
| 中文产品名 | 元枢工作台 |
| 英文产品名 | ArcheAxis Workspace |
| 简称 | ArcheAxis |
| 产品类别 | Local-first Knowledge & Learning Workspace |

不再对外使用：

- Cognitive Loop OS
- Cognitive-OS
- ArcheAxis OS
- 认知闭环系统
- 通用 Agent OS

### 2.2 仓库名称

当前 GitHub 仓库 `Cognitive-Loop-OS` 作为历史技术标识暂时保留，避免在 v0.5 修复期同时引入迁移风险。

建议在 v1.0 Release Candidate 前完成：

```text
DTALEX66/Cognitive-Loop-OS
            ↓
DTALEX66/ArcheAxis-Workspace
```

迁移时要求：

- GitHub redirect 验证。
- 包名、安装器、窗口标题、协议名、更新源统一。
- 旧链接和历史 Release 保留跳转说明。
- 数据目录迁移与回滚验证。

### 2.3 内部模块命名

内部命名采用职责，不采用宏大概念：

```text
workspace-shell
library-core
vault-core
asset-store
import-service
conversion-engine
document-model
evidence-core
search-index
canvas-core
learning-core
adapter-sdk
desktop-runtime
release-qualification
```

Machine、Evolution、Cognition、Runtime 等词不能再作为普通用户可见的信息架构。

---

## 3. 服务对象与核心任务

### 3.1 普通个人用户

核心任务：

- 把电脑里的资料拖进来并立即打开。
- 不需要理解格式引擎、Python、OCR 和索引。
- 能搜索、整理、写笔记并放心迁移数据。

### 3.2 学生

核心任务：

- 导入教材 PDF、讲义 PPT、课程 DOCX、网页和课堂录音。
- 按课程组织资料。
- 从原文高亮生成笔记、卡片和复习项目。
- 每个学习结果都能返回原页、原幻灯片或时间点。

### 3.3 教师

核心任务：

- 批量导入课程目录、课件、论文和表格。
- 保留课程结构和版本。
- 复用批注、讲义和引用材料。
- 将课程资料导出为开放、可交付的资料包。

### 3.4 研究者与学者

核心任务：

- 管理论文、书籍、网页、数据表和研究笔记。
- 保留页码、章节、表格、图片、公式、脚注和参考文献。
- 从结论追溯到原始证据。
- 与 Zotero、BibTeX、CSL JSON 等研究工作流互操作。

### 3.5 专家与重度知识用户

核心任务：

- 管理大 Vault、大型 PDF 和长期知识资产。
- 使用版本、批处理、自定义转换 profile、脚本和 API。
- 重建索引而不破坏原文件。
- 查看引擎、模型、来源和派生版本。

### 3.6 隐私敏感和低配置用户

核心任务：

- 默认完全本地处理。
- 明确控制哪些目录、文件和模型可访问。
- 在无 GPU、低内存环境中选择轻量模式。
- 可选安装 OCR、ASR、富 PDF 等大型组件。

---

## 4. 十二条不可破坏的产品原则

1. **用户数据优先**：原文件、原目录和开放格式高于内部数据库。
2. **本地优先**：离线可完成核心闭环；云端只能是显式可选项。
3. **来源优先**：摘要、笔记、卡片和 AI 回答必须可回到原始证据。
4. **原件与派生分离**：转换结果不能覆盖原件。
5. **无静默损失**：丢失、降级和不支持项必须进入 LossReport。
6. **能力真实**：检测到扩展名、模块可 import、任务成功，都不等于产品支持。
7. **开放兼容**：优先 Markdown、JSON Canvas、标准附件、BibTeX、CSV、JSON 等开放格式。
8. **渐进增强**：轻量基础能力默认可用，富模型和重型引擎按需安装。
9. **复用优先**：许可合规的成熟依赖、源码、SDK、CLI、sidecar 优先，自研最后。
10. **可恢复**：导入、转换、索引、编辑和导出均要可重试、可回滚。
11. **用户界面优先于工程仪表盘**：内部 Job、Receipt、Runtime 不得成为默认产品面。
12. **真实安装证据优先于测试数量**：Release 必须证明安装版完成用户闭环。

---

## 5. 最小产品面：Obsidian-compatible Knowledge Workspace

### 5.1 “全面兼容”的精确定义

全面兼容不是逐像素复刻 Obsidian，也不是兼容其私有插件运行时。

ArcheAxis 的兼容目标分为五级：

| 级别 | 定义 | 结果 |
|---|---|---|
| C0 发现 | 识别 Vault、文件和配置 | 可以安全列出内容 |
| C1 读取 | Markdown、属性、链接、附件、Canvas 可解析 | 不丢关键结构 |
| C2 工作 | 文件树、编辑、搜索、反链、属性、阅读器可用 | 可替代日常核心工作 |
| C3 安全写入 | 原子写、expected-hash、备份、冲突、回滚 | 不静默覆盖 |
| C4 往返兼容 | Obsidian 与 ArcheAxis 交替编辑并保持语义 | 第一完整兼容闭环 |
| C5 生态桥接 | 公开 URI、命令、导出、插件数据适配 | 扩大生态能力 |

v1.0 的硬目标是 C4；C5 在 v1.x 持续扩展。

### 5.2 v1.0 兼容范围

必须支持：

- Vault 目录身份和批准根目录。
- `.md` 文件和原始目录结构。
- YAML frontmatter / Properties。
- Wikilink、Markdown link、embed。
- heading reference、block reference。
- tag、alias、backlink、outgoing link。
- 常见附件和相对路径。
- `.canvas` JSON Canvas 节点、边、坐标、尺寸、颜色、分组和引用。
- 增量扫描、稳定文件 ID、hash/mtime。
- rename、move、delete 和冲突。
- 原子写、备份、rollback。
- Windows/Tauri 下真实 Vault 往返。

明确不承诺：

- 运行 Obsidian 私有插件二进制。
- 复制 Obsidian Live Preview 的全部内部实现。
- 兼容每一个社区插件的私有缓存。
- 复刻 Obsidian Sync 或 Publish 的闭源服务。

---

## 6. 总体产品架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                        ArcheAxis Workspace                       │
├─────────────────────────────────────────────────────────────────┤
│  体验层                                                         │
│  Workspace｜Library｜Search｜Reader/Editor｜Canvas/Graph｜Learn  │
├─────────────────────────────────────────────────────────────────┤
│  知识操作层                                                     │
│  Properties｜Links｜Backlinks｜Annotations｜Citations｜Cards     │
├─────────────────────────────────────────────────────────────────┤
│  AI 与学习层                                                    │
│  Cited Ask｜Summarize｜Compare｜Review｜Study Plan｜Local Models  │
├─────────────────────────────────────────────────────────────────┤
│  统一知识层                                                     │
│  Document｜Block｜Asset｜Anchor｜Graph｜Revision｜Index           │
├─────────────────────────────────────────────────────────────────┤
│  转换理解层                                                     │
│  Markdown｜PDF｜Office｜HTML｜OCR｜Canvas｜Media｜Loss Report     │
├─────────────────────────────────────────────────────────────────┤
│  来源与互操作层                                                 │
│  Vault｜Files｜Web｜Zotero｜Joplin｜Logseq｜Anki｜Open Export     │
├─────────────────────────────────────────────────────────────────┤
│  本地可信底座                                                   │
│  Content Store｜SQLite｜Transactions｜Hash｜Backup｜Permissions   │
├─────────────────────────────────────────────────────────────────┤
│  跨层保障                                                       │
│  Privacy｜Security｜Capability Truth｜Audit｜Recovery｜Release QA │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 来源与互操作层

### 7.1 来源类型

```text
Local File
Local Folder
Obsidian Vault
Web Page / URL
Clipboard / Drag-and-drop
Scanner / Image
Zotero Library
Joplin / Logseq / SiYuan export
Readwise / Anki export
Later: cloud storage and remote knowledge APIs
```

### 7.2 来源连接原则

- 所有来源先生成 `SourceConnection` 和明确权限。
- 本地目录必须经过用户批准，不允许隐式全盘扫描。
- 每个连接器都必须定义身份、增量游标、删除语义、冲突语义和导出能力。
- 闭源软件只使用公开格式、公开 API、官方导出或用户授权的本地文件。
- 导入适配器和同步适配器分离；“能导入一次”不能冒充“持续兼容”。

### 7.3 适配器合同

每个 Adapter 必须提供：

```text
detect()
inspect()
import_snapshot()
import_incremental()
export()
roundtrip_test()
capability_report()
loss_report()
```

并登记：

- 上游仓库和版本。
- License、模型 License 和资产 License。
- 集成方式：dependency / SDK / CLI / sidecar / fork / reference-only。
- 输入/输出 fixture。
- 安全边界。
- 回滚与卸载方式。

---

## 8. 原件与导入架构

### 8.1 核心数据对象

```text
SourceConnection
ImportBatch
ImportItem
RawAsset
AssetRevision
FileIdentity
DirectoryIdentity
```

### 8.2 RawAsset 合同

RawAsset 至少保存：

- 原始内容哈希。
- 原文件名和扩展名。
- MIME 和探测依据。
- 文件大小和时间。
- 原始路径/URL/来源连接。
- 只读内容存储引用。
- 导入批次和授权边界。
- 后续派生版本列表。

### 8.3 大文件策略

- 上传采用 disk spool 和流式哈希，不整文件常驻内存。
- 大 PDF、媒体和 Vault 附件使用路径/内容存储引用。
- 按格式配置大小、页数、时长、内存和时间预算。
- 超预算进入排队或提示用户选择轻量 profile。
- 批次逐项持久化，单文件失败不回滚成功文件。

### 8.4 增量与幂等

- `source identity + content hash + import profile` 作为幂等基础。
- 同一内容不重复存储，但保留多来源引用。
- rename/move 不被误判成删除+新建。
- 删除分为来源删除、工作区隐藏和永久删除，默认可恢复。

---

## 9. 多格式转换与文档理解架构

### 9.1 格式能力状态机

所有格式统一使用：

```text
detected
→ dependency_ready
→ converting
→ converted
→ validated
→ persisted
→ indexed
→ presented
→ restart_verified
→ roundtrip_verified
```

面向用户的能力状态：

| 状态 | 含义 |
|---|---|
| Ready | 安装环境中真实转换与展示通过 |
| Degraded | 可处理但会丢失明确结构 |
| Metadata only | 只能读取文件信息，不能提取知识内容 |
| Missing component | 可安装组件缺失 |
| Unsupported | 当前没有实现 |
| Failed | 文件损坏、加密、超时或引擎失败 |

### 9.2 ConversionRun

```text
queued
→ detecting
→ extracting
→ ocr/transcribing
→ structuring
→ validating
→ persisting
→ indexing
→ ready
```

每个阶段支持：

- 进度。
- 取消。
- 超时。
- 重试。
- 换引擎。
- 崩溃恢复。
- 结构化错误。

### 9.3 派生文档模型

```text
DerivedDocument
├─ Section
├─ Page / Slide / Sheet
├─ Paragraph / Heading / List
├─ Table / Cell
├─ Figure / Caption
├─ Formula
├─ Footnote / Citation
└─ MediaSegment / TranscriptSegment
```

每个 Block 可以保存：

- 原件 hash。
- 页码、幻灯片号或工作表。
- bbox、单元格范围或时间范围。
- 提取引擎和版本。
- 置信度。
- 文本与结构。
- 与原件的跳转定位。

### 9.4 格式路线

#### Markdown / TXT

- 原生一级格式。
- 保留换行、标题、代码块、链接和 frontmatter。
- 编辑时尽量最小化无关重写。

#### PDF

- born-digital：轻量文本/页级 baseline。
- rich layout：可选 Docling profile。
- scanned PDF：OCR profile。
- 保留页、区域、表、图、公式和损失。
- PDF.js 负责用户阅读，不自研 renderer。

#### DOCX

- 标题、段落、列表、表格、图片、脚注。
- 保留原件并显示降级项。

#### PPTX

- 幻灯片顺序、标题、正文、备注、图片和关系。
- 引用锚点必须包含 slide number。

#### XLSX / XLS / CSV

- 工作表、表头、行列、单元格和显示值。
- 公式文本与计算值分开。
- 表格数据不得只降为一段 Markdown。

#### 图片

- 元数据和 OCR 分离。
- OCR 保存语言、bbox、置信度和旋转。
- 支持单图和扫描文档批次。

#### 网页

- 原 URL、标题、作者、抓取时间和正文。
- 保存快照或内容哈希。
- 动态网页和登录内容必须明确授权。

#### 音频/视频

- FFmpeg 只负责媒体探测、音轨、关键帧。
- ASR 产生带时间戳 transcript 后才算知识处理。
- 模型下载、体积、语言和隐私必须可见。

#### JSON Canvas

- 节点、边、坐标、尺寸、颜色、分组和引用均为一等结构。
- 不再把 Canvas 压成纯文本。

---

## 10. 统一知识与证据层

### 10.1 核心对象

```text
KnowledgeDocument
KnowledgeBlock
EvidenceAnchor
Annotation
Property
Tag
Link
Backlink
Collection
Revision
IndexRevision
KnowledgeCandidate
LearningItem
```

### 10.2 证据锚点

EvidenceAnchor 必须能够表达：

```text
原件 hash
+ 原件版本
+ 页/幻灯片/工作表/时间点
+ bbox/单元格/文本范围
+ 派生 Block
+ 转换引擎版本
```

任何 AI 结论、人工摘录、学习卡片或知识候选均可关联一个或多个 Anchor。

### 10.3 知识状态

```text
Source Material
→ Extracted Content
→ User Note / Annotation
→ Knowledge Candidate
→ Reviewed Knowledge
→ Learning Item / Reusable Output
```

禁止：

- 把转换成功自动标为知识正确。
- 把 AI 摘要自动标为已验证知识。
- 用文档第一行制造伪 claim。
- 丢弃来源后只保留向量或摘要。

### 10.4 搜索与索引

搜索分层：

- 文件名、路径、属性、标签。
- 全文和结构块。
- 批注和引用。
- 链接与图关系。
- 语义检索。

索引可以删除和重建，原件、笔记和知识对象不能依赖索引存活。

---

## 11. Workspace UI 总蓝图

### 11.1 桌面布局

```text
┌────────────────────────────────────────────────────────────────┐
│ 工作区切换｜全局搜索｜导入｜同步/能力状态｜设置               │
├──────────────┬───────────────────────────────┬─────────────────┤
│ Library      │ 中央多标签工作区              │ Context Panel   │
│ Vault/File   │ Markdown Reader/Editor        │ Outline         │
│ Collections  │ PDF Reader                    │ Properties      │
│ Tags         │ Office Preview                │ Backlinks       │
│ Saved Search │ JSON Canvas / Graph           │ Citations       │
│ Sources      │ Image / Table / Transcript    │ Annotations     │
│              │                               │ Cited AI        │
├──────────────┴───────────────────────────────┴─────────────────┤
│ 可折叠任务条：仅在导入、转换、索引、同步运行或失败时出现       │
└────────────────────────────────────────────────────────────────┘
```

### 11.2 一级导航

1. Workspace
2. Library
3. Search
4. Canvas / Graph
5. Learning
6. Settings

高级治理抽屉：

- Conversion Runs
- Index Status
- Audit
- Diagnostics
- Adapter Status
- Release/Capability Information

### 11.3 Workspace 首页

首页显示：

- 继续阅读。
- 最近编辑。
- 最近导入。
- 当前课程/项目。
- 未完成批注和学习项。
- 失败或需要处理的导入。

不显示：

- 大面积 Runtime 健康状态。
- 默认 Job Receipt 列表。
- 机器内部阶段编号。
- 无用户意义的门禁和哈希卡片。

### 11.4 Library

- 原生文件树。
- Collection 与文件目录分离。
- Tag 和 Property 筛选。
- 文件、网页、Vault、Zotero 等来源统一入口。
- 可预览、移动、重命名、删除和恢复。
- 大库虚拟滚动和增量加载。

### 11.5 Reader / Editor

- Markdown 分屏/阅读/编辑模式。
- PDF.js 阅读器。
- Office 结构视图与原件打开。
- 图片 OCR overlay。
- 音视频 transcript 与时间跳转。
- 标签页、历史、版本和未保存状态。

### 11.6 右侧上下文面板

根据当前对象切换：

- Outline。
- Properties。
- Links / Backlinks。
- Citations。
- Annotations。
- Conversion Info / Loss Report。
- Cited AI。

### 11.7 Import Center

导入前：检测格式、体积、引擎、OCR 需求和能力状态。

导入中：显示 queued、extracting、OCR、structuring、indexing、ready。

导入后：

- 打开结果。
- 打开原件。
- 查看损失。
- 重新转换。
- 更换 profile。
- 定位错误文件。

### 11.8 Canvas 与 Graph

Canvas 用于主动组织；Graph 用于查看关系，二者不能混为同一个功能。

- JSON Canvas 是开放文件真相。
- 应用内增强数据采用 sidecar 或可逆扩展。
- Graph 默认局部、可筛选，不追求装饰性全库星云。

### 11.9 视觉与交互原则

- 克制、低噪声、长时间阅读友好。
- 内容优先，工程状态退后。
- 深浅主题。
- 字体、行宽、间距和高亮适合论文/教材阅读。
- 所有核心操作支持键盘。
- 焦点、屏幕阅读、对比度、缩放和小窗口进入正式验收。

---

## 12. AI 与学习层蓝图

### 12.1 AI 的位置

AI 是知识使用层，不是产品中心，也不是数据真相来源。

所有 AI 能力遵循：

- 默认基于用户选定资料。
- 显示引用。
- 可回原文。
- 区分原文、推断和生成。
- 不自动覆盖人工内容。
- 可选择本地模型或显式云模型。

### 12.2 核心 AI 能力

第一阶段：

- 选区解释。
- 带引用问答。
- 文档摘要。
- 多文档比较。
- 术语提取。
- 从批注生成笔记草稿。

第二阶段：

- 研究问题分解。
- 证据对照。
- 矛盾发现。
- 文献综述辅助。
- 课程知识图谱草案。

第三阶段：

- 在严格权限和可回滚条件下执行跨文档整理。
- 自动提出候选链接、属性和集合。
- 生成学习计划并根据复习结果调整。

### 12.3 学习系统

学习层采用轻量、可解释模型：

```text
来源材料
→ 高亮/批注
→ 笔记
→ 候选卡片
→ 人工复核
→ 复习队列
→ 学习反馈
```

支持：

- 问答卡、填空卡、概念卡、证据卡。
- 间隔重复。
- 掌握度与置信度分离。
- 每张卡返回来源。
- Anki 导入/导出。

### 12.4 本地模型路线

- 小模型负责分类、标签、简单摘要和 OCR 后处理。
- Embedding 和 reranker 可本地运行。
- 大模型作为可替换 Provider，不把数据模型绑定到单一 API。
- 模型能力、下载体积、显存需求和许可证进入 Capability Registry。
- RTX 3060 Ti 等消费级 GPU 提供量化模型 profile；无 GPU 仍能完成非 AI 核心功能。

---

## 13. 相关软件能力吸收地图

吸收的是成熟能力和开放格式，不是把所有产品界面拼成一个超级菜单。

### 13.1 第一圈：直接互操作

| 产品/生态 | 主要吸收点 | 路线 |
|---|---|---|
| Obsidian | Vault、Markdown、Properties、links、Canvas | v1.0 核心 |
| Zotero | 文献、附件、批注、引用、BibTeX/CSL | v1.x 研究适配器 |
| Anki | 卡片、复习、导入导出 | v0.9/v1.x |
| Joplin | Markdown、资源、notebook、导出 | v1.x 适配器 |
| Logseq | block/page/reference/outliner | v1.x 读取与转换 |

### 13.2 第二圈：能力借鉴与格式桥接

| 产品 | 借鉴点 |
|---|---|
| Readwise Reader | 阅读、高亮、回顾和来源工作流 |
| Heptabase | 视觉卡片与白板知识组织 |
| Capacities | 对象化知识与属性体验 |
| Tana | supertag、结构化节点和 schema UX |
| Roam Research | block reference 与网络化笔记 |
| Notion | 数据库视图、属性和协作体验 |
| SiYuan | 本地优先、块模型、编辑与资源管理 |
| AFFiNE | 文档/白板融合和工作区布局 |

闭源产品通过公开 API、导出格式和行为研究兼容；AGPL/混合许可项目只能在完成许可决策后复用代码。

### 13.3 第三圈：远期来源与发布

- Calibre / EPUB 生态。
- Pandoc 格式转换生态。
- Git 仓库与代码知识库。
- 云盘和对象存储。
- 学术数据库公开 API。
- LMS / 课程平台导出。

---

## 14. 开源复用与许可证架构

### 14.1 复用优先级

```text
官方开放格式
→ 成熟依赖库
→ 官方 SDK/API
→ CLI/sidecar
→ 许可兼容 fork/vendor
→ 行为与 fixture 参考
→ 自研
```

### 14.2 推荐组件方向

- PDF viewer：PDF.js。
- 文档 baseline：MarkItDown。
- 富文档结构：Docling optional profile。
- OCR：Tesseract baseline、PaddleOCR optional sidecar。
- 广格式 fallback：Apache Tika optional sidecar。
- ASR：faster-whisper optional sidecar。
- HTML：Trafilatura。
- Markdown AST：选择成熟 CommonMark/GFM parser。
- YAML：成熟 roundtrip parser，不再手写子集。

### 14.3 禁止项

- 许可证未知直接复制。
- 把 AGPL 代码静态合并进宽松许可发行物而不作决策。
- 只记录项目名，不记录 commit/release revision。
- 忽略模型、字体、图标、fixture 和训练数据许可。
- 把用户个人 Vault 当开源测试数据。

### 14.4 Upstream Ledger

每个候选至少包含：

```text
canonical repository
revision/tag
license
model/data/assets license
integration mode
security notes
fixtures
modifications
upgrade plan
rollback plan
```

---

## 15. 平台与技术底座

### 15.1 桌面平台

- Tauri 作为桌面 shell。
- Windows 是第一正式平台。
- macOS/Linux 在核心数据层和 UI 稳定后扩展。
- 浏览器模式用于前端开发和轻客户端验证，不冒充完整桌面能力。

### 15.2 后端

- Python 服务负责格式适配、转换编排、知识服务和本地 AI。
- 重计算从 HTTP 请求线程移到持久化 worker。
- 每个 worker 有资源预算和取消信号。
- 外部二进制通过版本化 Adapter 封装。

### 15.3 存储

- 原件：content-addressed asset store。
- 元数据、任务、图和批注：SQLite。
- 全文：可重建本地索引。
- 向量：可删除重建的派生索引。
- Vault 原文件仍是开放文件真相；数据库不劫持所有权。

### 15.4 API

API 围绕产品对象：

```text
/sources
/imports
/assets
/documents
/annotations
/links
/search
/canvases
/learning
/capabilities
```

避免继续暴露以内部阶段、Runtime 或临时研究管线命名的主 API。

### 15.5 扩展机制

v1.0 前只提供内部 Adapter SDK，不急于开放插件市场。

Adapter 隔离：

- 格式解析器。
- 来源连接器。
- 导出器。
- AI Provider。
- OCR/ASR sidecar。

v1.x 在合同、权限和签名成熟后再开放第三方扩展。

---

## 16. 安全、隐私和数据主权

### 16.1 默认边界

- 本地文件默认不出机。
- 云模型默认无权限读取整个工作区。
- 每次来源连接有明确目录和操作权限。
- 写入 Vault 前执行 expected-hash。
- 不跟随逃逸授权根目录的 symlink。
- HTML、PDF、Office 和媒体解析在受限 worker 中运行。

### 16.2 权限模型

```text
read source
write derived data
write original/Vault
run external converter
use network
send to AI provider
export/share
```

权限按 Adapter 和任务授予，不使用一个全局“允许全部”。

### 16.3 数据生命周期

- 原件保存策略可配置。
- 删除先进入可恢复状态。
- 导出和卸载前提示数据位置。
- 更新和迁移先备份、后验证、失败回滚。
- Telemetry 默认关闭或严格匿名、可查看、可删除。

---

## 17. 性能与规模蓝图

### 17.1 目标规模档位

| 档位 | 典型用户 | 目标 |
|---|---|---|
| S | 1,000 文档 | 即时启动和搜索 |
| M | 20,000 文档 | 增量索引、虚拟列表、后台转换 |
| L | 100,000 文档/大型研究库 | 分片索引、预算调度、诊断工具 |

### 17.2 性能原则

- 首屏不等待全库扫描。
- 文件树和搜索分页/虚拟化。
- 转换按内容 hash + profile 缓存。
- 索引增量更新。
- OCR、ASR 和 embedding 可暂停。
- 后台任务不能阻塞阅读和编辑。
- 每个版本公开性能基线，不承诺未经测量的速度数字。

### 17.3 可靠性目标

- 原文件写入必须原子化。
- ConversionRun 重启可恢复。
- Index 可重建。
- 任意派生数据损坏不应破坏原件。
- 编辑冲突必须显式，不使用最后写入静默覆盖。

---

## 18. 验证、门禁与发布蓝图

### 18.1 验证层级

```text
单元/契约测试
→ 真实格式 fixture
→ 后端端到端
→ 浏览器用户流
→ Desktop bundled runtime
→ Windows 安装器
→ 重启回读
→ 导出/往返/冲突恢复
```

### 18.2 变化感知门禁

- 普通代码：lint + Python 主版本 + 受影响测试。
- UI：增加 browser smoke。
- Windows runtime：增加 Windows smoke。
- Desktop/Tauri/Installer：增加 desktop shell/lifecycle。
- 解析器/依赖/bundle：增加真实安装格式 qualification。
- 兼容接口：增加版本矩阵和 roundtrip fixture。
- Nightly/RC：完整格式与安装矩阵。

### 18.3 Release Evidence

正式 Release 绑定：

- exact source SHA/tree。
- workflow/policy hash。
- lock/bundle manifest。
- 安装器 hash。
- fixture 版本。
- 完整 job-set 结论。
- 安装后真实用户流。
- 资产下载 hash 回读。

不能只查询“同 SHA 有一个名为 CI 的成功 run”。

### 18.4 能力声明门禁

任何面向用户的“支持、可用、完成、PASS”必须映射到：

```text
capability
→ installed dependency probe
→ real fixture
→ expected semantic assertion
→ UI presentation
→ restart readback
→ evidence record
```

---

## 19. 路线总图

### Horizon 0：产品真相与生存修复

对应版本：v0.5.1。

目标：安装后至少能可靠处理真实 PDF，不再出现能力声明与安装产物不一致。

交付：

- 依赖真相。
- 真实 PDF fixtures。
- 格式能力状态。
- 结构化错误。
- CI 聚合修复。
- 安装后 PDF qualification。

退出门槛：干净 Windows 安装 → Desktop 上传真实 PDF → 打开 → 重启回读。

### Horizon 1：知识摄入底座

对应版本：v0.6。

目标：建立原件—派生—证据模型和真正的导入中心。

交付：

- RawAsset。
- ImportBatch/Item。
- ConversionRun。
- DerivedDocument/Block。
- LossReport。
- EvidenceAnchor。
- PDF.js reader。
- 批注与页码引用。

退出门槛：PDF 高亮生成笔记并可返回原页，重启定位不漂移。

### Horizon 2：多格式学习材料

对应版本：v0.7。

目标：覆盖学生、教师和普通用户常见资料。

交付：

- DOCX/PPTX/XLSX/CSV。
- 图片 OCR。
- HTML 来源。
- 批量导入。
- 结构化预览。
- 安装后格式矩阵。

退出门槛：每种格式完成原件→转换→索引→展示→重启回读。

### Horizon 3：Obsidian-compatible Workspace

对应版本：v0.8。

目标：达到兼容级别 C4。

交付：

- Vault 工作台。
- Markdown 编辑。
- Properties、links、backlinks、tags。
- 附件和 PDF 统一体验。
- JSON Canvas。
- 增量、rename/delete。
- 冲突、备份、rollback。
- Obsidian 往返验证。

退出门槛：真实 Vault 在两个应用之间交替编辑，关键语义和资产不丢失。

### Horizon 4：引用 AI 与学习

对应版本：v0.9。

目标：AI 与学习建立在可靠来源之上。

交付：

- 带引用问答。
- 多文档比较。
- 笔记/批注→卡片。
- 间隔复习。
- 本地模型 Provider。
- Anki 导入导出。

退出门槛：每个 AI/学习结果可回到原始证据，模型内容不会自动成为事实。

### Horizon 5：稳定 1.0

对应版本：v1.0。

目标：成为可长期使用和迁移的本地知识工作台。

交付：

- Obsidian C4。
- PDF/Office/OCR 稳定矩阵。
- 搜索、编辑、Canvas、学习基础。
- 开放导出。
- 大库和大文件基线。
- 无障碍和低配置模式。
- 更新、迁移、卸载和数据恢复。

退出门槛：真实用户无需理解内部 Runtime，即可完成全部核心知识流程。

### Horizon 6：知识生态互操作

对应版本：v1.1–v1.4。

目标：按适配器逐项吸收相关软件能力。

优先顺序：

1. Zotero / BibTeX / CSL。
2. Anki。
3. Joplin。
4. Logseq。
5. SiYuan export/import。
6. Readwise export/API。
7. Notion/Tana/Roam/Heptabase/Capacities 公开导出与 API。

每个适配器独立发布、独立能力声明、独立 loss/roundtrip 证据。

### Horizon 7：本地智能研究与学习平台

对应版本：v1.5–v1.x。

目标：增强研究、写作和个性化学习，而不破坏数据主权。

候选能力：

- 本地文献分析。
- 多资料证据对照。
- 引用检查。
- 长期学习模型。
- 课程/研究项目模板。
- 可控自动整理。
- 多模型路由。

### Horizon 8：开放扩展与可选协作

对应版本：v2.0 以后。

前置门槛：v1.x 本地单用户、数据合同、权限和扩展签名全部稳定。

候选能力：

- 第三方 Adapter SDK。
- 受控扩展市场。
- 端到端加密同步。
- 小团队共享知识库。
- 细粒度协作和审阅。
- 受控 Agent 执行。

这些能力不能提前进入当前主线。

---

## 20. 任务包总分解

### Program A：Product Truth

- A00 Naming Contract。
- A01 Capability Truth。
- A02 Current Plan Reset。
- A03 Legacy Blueprint Archive。
- A04 Release Statement Contract。

### Program B：Source & Asset

- B00 RawAsset。
- B01 Import Batch。
- B02 Streaming/Spool。
- B03 Source Permissions。
- B04 Stable Identity。
- B05 Incremental Sync。

### Program C：Conversion

- C00 ConversionRun。
- C01 PDF baseline。
- C02 Rich PDF/OCR。
- C03 Office。
- C04 Image OCR。
- C05 Web/CSV。
- C06 Media ASR。
- C07 LossReport。

### Program D：Knowledge Model

- D00 DerivedDocument/Block。
- D01 EvidenceAnchor。
- D02 Annotation。
- D03 Properties/Tags/Links。
- D04 Revision/Conflict。
- D05 Search/Index。

### Program E：Workspace UX

- E00 Navigation Shell。
- E01 Library Tree。
- E02 Import Center。
- E03 Markdown Reader/Editor。
- E04 PDF Reader。
- E05 Context Panel。
- E06 Search。
- E07 Canvas/Graph。
- E08 Accessibility。

### Program F：Obsidian Compatibility

- F00 Vault Discovery。
- F01 Markdown/YAML Fidelity。
- F02 Links/Embeds/References。
- F03 Attachments。
- F04 JSON Canvas。
- F05 Safe Write。
- F06 Incremental/Rename/Delete。
- F07 Conflict/Rollback。
- F08 C4 Roundtrip Qualification。

### Program G：AI & Learning

- G00 Provider Contract。
- G01 Cited Ask。
- G02 Summarize/Compare。
- G03 Candidate Knowledge。
- G04 Cards/Review。
- G05 Local Models。
- G06 Anki Interop。

### Program H：Ecosystem Adapters

- H00 Adapter SDK。
- H01 Zotero。
- H02 Joplin。
- H03 Logseq。
- H04 SiYuan。
- H05 Readwise。
- H06 Other PKM/API adapters。

### Program Q：Quality & Release

- Q00 Real Fixture Corpus。
- Q01 Installed Format Qualification。
- Q02 Browser/Desktop Flows。
- Q03 Roundtrip Matrix。
- Q04 Performance Baselines。
- Q05 Exact-SHA Release Evidence。
- Q06 Upgrade/Migration/Uninstall。

执行规则：Program 编号只是领域，不代表全部并行。每个版本只激活能够完成当前 Horizon 的最小任务集。

---

## 21. 组织与仓库真相

### 21.1 唯一权威文档

仓库应只保留以下当前入口：

```text
README.md
AGENTS.md
docs/PRODUCT_POSITIONING.md
docs/FUTURE_MASTER_BLUEPRINT.md
docs/CURRENT_PRODUCT_PLAN.md
docs/CAPABILITY_MATRIX.md
docs/RELEASE_QUALIFICATION.md
docs/UPSTREAM_LEDGER.md
```

### 21.2 历史材料

旧 Cognitive Loop、A-N、B/C/R、旧 taskpack 和旧 handoff：

```text
docs/legacy/
docs/deferred/
```

要求：

- 文件顶部明确 Historical/Deferred。
- 不进入默认 agent discovery。
- 不被当前 TaskPack 生成器引用。
- 只有达到对应 Horizon 前置门槛后才能重新评审。

### 21.3 外部项目边界

- OS/ArcheAxis Workspace 独立完成产品逻辑、数据模型、UI 和发布。
- 外部治理项目可以消费验证证据，但不能成为运行时依赖。
- 不复制外部项目的 Agent Runtime、门禁控制面或观测数据库进安装包。
- 任何跨项目集成都必须通过版本化合同，而不是硬编码本机路径。

---

## 22. 决策门与停止条件

### 22.1 进入下一 Horizon 的条件

- 当前 Horizon 的真实用户闭环通过。
- exact-SHA 安装证据完整。
- 文档、UI、manifest 和安装环境能力一致。
- 没有 P0 数据丢失和静默覆盖风险。
- 已知降级全部可见。

### 22.2 必须停止扩展的情况

- PDF/Office 安装版仍失败。
- 原件和派生数据未分离。
- 引用无法回原页。
- Vault 写入可能静默覆盖。
- 重启后状态丢失。
- UI 仍要求普通用户理解 Runtime/Receipt。
- Release 只证明程序启动，未证明产品能力。

### 22.3 永久反模式

- 用测试数量证明产品完成。
- 用空 fixture、伪格式文件证明格式支持。
- 用“模块可 import”证明安装版可用。
- 用自动生成首行 claim 证明知识链成立。
- 把所有相关软件功能一次性塞进一个超级导航。
- 在许可未决时复制源码。
- 先建设重型 Agent，再补基础文件阅读。

---

## 23. 资源优先级

在达到 v1.0 前，建议资源分配：

| 方向 | 比例 |
|---|---:|
| 多格式转换、原件与数据模型 | 30% |
| Workspace UI、Reader、Editor、Search | 25% |
| Obsidian 兼容与 roundtrip | 25% |
| 质量、安装器和 Release Evidence | 15% |
| AI/学习预研 | 5% |

以下方向 v1.0 前原则上为 0：

- 插件市场。
- 多代理系统。
- 企业协作。
- 3D/VR。
- 社交和公共知识网络。
- 通用自动化平台。

---

## 24. 成功标准

### 产品成功

一名普通用户安装 ArcheAxis 后，可以：

1. 选择现有 Obsidian Vault。
2. 在文件树打开 Markdown、PDF 和附件。
3. 导入 Word、PPT、Excel 和图片。
4. 阅读、搜索、高亮、批注和编辑。
5. 从原文生成带引用笔记和学习卡片。
6. 重启后回到同一位置。
7. 在 Obsidian 中再次打开修改后的 Vault。
8. 导出原文件、笔记、批注和开放数据。

### 工程成功

- 原文件不因派生失败受损。
- 冲突不静默覆盖。
- 索引可重建。
- 任务可恢复。
- Release 声明有安装版 exact-SHA 证据。
- Adapter 有来源、版本和许可证记录。

### 战略成功

ArcheAxis 不再依赖“比 Obsidian 多几个功能”竞争，而形成自己的组合优势：

```text
Obsidian 开放文件兼容
+ PDF/Office/媒体知识转换
+ 证据级引用
+ 本地 AI
+ 学习闭环
+ 开放迁移
```

---

## 25. 当前唯一执行起点

未来蓝图很大，但当前只能从下面顺序开始：

```text
01 修复 v0.5.0 PDF/Office 安装依赖和能力声明
02 建立 RawAsset + ConversionRun + LossReport
03 完成真实 PDF 导入、阅读、页码引用和重启回读
04 重构 Library / Reader / Editor / Context Panel
05 完成 Office 与图片 OCR
06 完成 Obsidian C1–C4
07 接入引用 AI 与学习
08 扩展其他 PKM 适配器
09 达到稳定 1.0 后再开放重型能力
```

任何新任务包都必须指出它属于哪个 Horizon、Program 和用户闭环；无法对应的任务不得进入当前队列。

---

## 26. 最终蓝图摘要

ArcheAxis Workspace 的最终形态不是一个充满 Runtime、Agent、Machine、Evolution 菜单的技术展示平台，而是一个安静、可靠、开放的知识工作空间：

- 左边是用户熟悉的文件和知识库。
- 中间是真实文档、PDF、笔记和画布。
- 右边是属性、反链、引用、批注和有出处的 AI。
- 底层保存原件、结构、来源、版本和损失。
- 外部可以与 Obsidian、Zotero、Anki、Logseq 等工具交换数据。
- AI 可以增强理解和学习，但不能夺走用户的数据所有权和知识判断权。

这份蓝图的核心顺序始终是：

> **先让真实资料可靠进入，再让知识能够工作，然后让 AI 和生态在可靠基础上生长。**
