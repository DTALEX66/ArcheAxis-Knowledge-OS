# 当前最小复用卡（2026-10-08）

共同边界：基线 `4b9828c4058901c0b1fd2c75c528238c55e0ec89`，SUP-022 的 Tauri 2 / React 正式主线。当前结果是 Windows 隔离 Core API 与真实 Python 子进程的 INTEGRATED 验证，输入是项目编写的 SYNTHETIC 样例；不是安装态桌面验收。固定版本来自仓库锁文件和任务环境元数据，详细回执、许可哈希与未运行项见 `OSS-REUSE-VERIFICATION-20261008.json`。Rust 是正式 SQLite/CAS 唯一写入者。模板仅调用既有有限业务命令，不遍历开源池。

| 能力 ID / 来源与固定版本 | 吸收方式、输入 → 输出 | 真实入口与样例结果 | 失败替代 / 限制 |
|---|---|---|---|
| `html.structure` / Trafilatura 2.1.0 | 当前 saved-snapshot worker 使用 donor；本地 HTML 字节 → 正文、title、links、文本块偏移、来源 SHA、损失收据 | Core imports/jobs/executions/outputs；article 保留 measured-result 句子，去掉 NOISE_NAV / NOISE_FOOTER，Core 重开输出一致 | 非 article/main、缺依赖、空提取或异常回退既有 stdlib parser；显式记录 engine/version/attempt/fallback；偏移只对应派生正文，不冒充 DOM。Apache-2.0，未调用模型 |
| `pdf.extract` / PyMuPDF 1.28.2 | 既有 PDF worker；原始 PDF → 页/行结构、文本、损失报告 | 同一 Core 任务链；golden PDF 中 Golden Journey Evidence 与 Page Anchor 保留，重开读回一致 | 无文本页标记需 OCR；不换成 PyMuPDF4LLM、不默认 LLM。既有依赖许可为 AGPL-3.0 / 商业双许可，任务读取 COPYING；无模型 |
| `office.structure` / 本项目 worker 0.1.0，DOCX ZIP/XML stdlib | 复用现有 Office 原生解析；DOCX → 段落/表格/媒体清单与位置 | Core 任务链；Document evidence anchor 和 no personal data 句子保留；真实报告的位置能经 anchor API 定位 | PPTX/XLSX/XLS/DOC 各自依赖和版式能力本次未全面验证，缺引擎明确错误；MarkItDown 0.1.6 真实 legacy 函数保留为待绑定替代，shared-contracts 同名文件仅 txt/md 占位 |
| `image.ocr` / 已声明 Tesseract v5.5.0.20241111，eng 数据固定 SHA | 既有 vision worker 调用可执行文件；PNG → OCR text、word boxes、confidence、损失报告 | 同一 Core 任务链识别项目图片 OCR GOLDEN ANCHOR，并重开读回 | 使用既有工具/语言数据解析器；未声明或缺语言必须拒绝，不以启动证明识别。只验证英语样例；code / tessdata 注册许可为 Apache-2.0，安装分发许可文件与模型来源链未重新核定，保留缺口 |
| `canvas.structure` / JSON Canvas 仓库格式实现，worker 0.1.0 | 格式参考已具体提炼；canvas → 节点/边/文件引用结构、文本、损失报告 | Core 任务链运行 golden-canvas-anchor.canvas，非空结果持久读回；格式测试使用既有 shared/json_canvas.py | 图形布局/跨软件无损往返未证明；保留原文件与损失报告，不当作全平台认证 |
| `learning.fsrs` / py-fsrs 6.3.2 | 复用 Rust scheduler → worker_schedule → shared donor；复习事件 → due/stability/difficulty 等状态 | Core learning API；真实 worker 状态连续计算、作答重开读取，重复 client event ID 只保存一次，相同 ID 不同内容拒绝 | 缺 donor 不伪造调度；保留未评估状态。MIT 文件已哈希；无模型；复习调度不证明实操掌握 |
| `search.local` / 既有 Rust SQLite FTS5，基线固定 | 本地检索与引用式答复，不安装第二 RAG 产品 | Core ask API 7 测试：答复是原文、引用可查、无结果为 unanswered、不造锚点、查询不写库 | 优先本地已有内容；语义 embedding/sqlite-vec 未运行，仍 B；线上客户端未接成当前 Core 模板入口 |
| `document.reference` / 既有 Core versioned Document，基线固定 | 保存对象 ID + version + 可选 block ID；原对象 → 历史版本/块原文；派生 backrefs/collection/local graph/canvas | templates/bindings.ts 调用 document_create/get/version/draft，Core 实测属性/关系/卡片坐标保存、版本冲突 409、重开一致；UI 模拟测试验证点击打开原对象和上下文 | 派生视图最多 100 文档且明确显示限制；引用版本/块不存在拒绝保存。没有第二图库或集合数据库 |
| `document.edit` / Tiptap 3.31.4，经既有 ProseMirror | 编辑器保存 Core Document；新增根 attrs 保留模板元数据 | 资料库 DocumentEditor；UI 测试验证 attrs 往返不丢失正文或模板字段 | 版本冲突保留待保存内容；当前 UI 测试为 jsdom 模拟，安装桌面交互 NOT_RUN。许可按 frontend lock/包声明，非新增引擎 |
| `course.general` / 本项目现有 general course 合同、基线固定 | 只复用已有通用生成/评价 worker 与合同；不因 28 标签创建课程引擎 | test_general_course_worker 已运行，属于源级 worker 验证；T3 绑定已有 learning item 后使用原 CanonicalLearningSpace 进行作答/复习 | 通用课程 worker 到模板的 native bridge 缺口保留 B；无学科专属自动评估资格，不伪造课程掌握 |

PDF 原件阅读保留 `pdf.read` / pdfjs-dist 6.4.299 的现有 PdfReader；源码与 lock 可核，桌面渲染未运行，仍 B。音频保留现有 faster-whisper / SenseVoice 可选路径；没有为模板新增模型或第二推理栈。Crossref、DataCite、OpenAlex、Wikidata 保留现有 evidence_connectors/public_evidence 调用方，当前 Core 绑定和 live 请求未通过，不升 A。

来源策略沿用当前知识对象与原文锚点：百科用于概念导航，官方资料/原始文献用于方法依据，Issues/论坛用于问题案例；原始来源与时间需要存入对象，多个转引 URL 不算独立依据。本次验证没有外部抓取，也没有为派生正文提升证据可信等级。
