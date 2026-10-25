# ArcheAxis Knowledge 全栈技术审计与吸收建议（2026-10-25）

审计对象：`d:\All projects\ArcheAxis-Knowledge-OS`，分支 `trae/20261024`，PR #203。
审计方式：以当前源码、锁文件、安装器载荷和既有登记为准；外部信息为 2026-10-25 检索结果；许可证以官方页面为准，无法核实处标 **UNVERIFIED**。
边界：本文是审计与候选清单，不是第二份进度表，不改变 `PARTIAL` 总体结论，不授权合并/发布/云端调用/覆盖真实数据。**本次未改产品代码，未重跑全量测试。**

---

## 0. 结论摘要（按优先级）

### P0（会直接影响“装完就能用”或合规）

1. **OCR 引擎没有随安装包分发。** 安装器载荷只带 `pytesseract` 包装层，不带 `tesseract.exe` 与 `tessdata`；干净机器上扫描 PDF/图片 OCR 会直接不可用。RapidOCR（Apache-2.0、ONNX、约 15MB 模型）已在依赖设计里出现，但 vNext OCR worker 仍只调用 Tesseract。
2. **PyMuPDF 是 AGPL-3.0，且已打包进安装器，但 `THIRD_PARTY_NOTICES.md` 没有披露。** 这是当前最明确的许可证缺口；要么按 AGPL 履行义务并如实披露，要么在试点中用 `pypdfium2`（Apache-2.0/BSD-3）+ `pdfplumber`（MIT）替换。
3. **全文检索每次查询都全量重建 FTS 索引。** `crates/archeaxis-domain/src/search.rs` 的 `search()` 与 `search_transforms()` 在查询前调用 `reindex()`，库变大后每次搜索都是 O(N) 全表重建。
4. **语义检索没有持久化向量索引。** `crates/archeaxis-api/src/runtime/semantic.rs` 每次查询把全部已接受知识正文取出来发给 worker 计算 embedding；迁移代码也明确“主库还没有向量表”。数据量一大就会变慢且占用内存。
5. **安装器体积可显著下降但当前配置更差。** `src-tauri/tauri.conf.json` 把 NSIS 压缩显式设为 `zlib`，而 Tauri 的默认是 `lzma`；当前安装器 433,078,836 字节。
6. **没有 Tauri updater，也没有 Windows 代码签名。** 这直接对应 J6 的“升级/回退”缺口，以及 SmartScreen 对未签名安装器的告警。

### P1（明显收益，风险可控）

7. **网页正文抽取没有使用 Trafilatura。** `trafilatura` 已在主依赖里，但 `worker_html.py` 仍是标准库 `HTMLParser`；广告/导航/正文分离仍是“later slice”。
8. **公开研究只有 3 个来源族**（Wikipedia、StackExchange、OpenAlex）。Crossref、DataCite、Wikidata 只出现在生成的 UI 资源目录里，没有实际接线；没有 arXiv/PubMed 全文通道。
9. **视觉描述用 7B 模型，视频固定 10 秒采样。** 短视频/长视频都按固定间隔取最多 24 帧，没有镜头边界；简单 OCR/描述不需要 7B。
10. **没有“单环节小模型”分工。** 语言识别、NER、关系、标签/摘要、查询改写、NLI 核验都还没有独立小模型；目前主要靠 4B/7B 通用模型或纯词法。
11. **前端技术代际落后。** React 18.3 / Vite 5 / Vitest 2 / TypeScript 5.5；2026 年主流是 React 19.2、Vite 7、Vitest 5、TS 5.9。升级需要单独切片，不能混在业务修复里。
12. **前端请求层没有统一超时/取消/重试策略。** `frontend/src/api/client.ts` 直接 `fetch`，只有 try/catch 与错误映射；长任务与页面切换主要靠调用方自觉。

### P2（可选能力/长期）

13. 公式、表格、版面、镜头、词级对齐、说话人、TTS、翻译、实体关系等可以按“可选小模型 + 按需安装”接入，不建议全部塞进主安装包。
14. 运行时包体存在明显冗余：`litellm` 53.3MB、`pandas` 33MB、`babel` 29.4MB、`sympy` 25.4MB、`pymupdf` 48MB、`av.libs` 62.6MB、`ctranslate2` 59.4MB、`onnxruntime` 31.6MB。需要一次“导入图审计 + 裁剪”，而不是盲目删包。

---

## 1. 当前实测架构

| 层 | 实际实现 | 关键版本/事实 |
| --- | --- | --- |
| 桌面壳 | `src-tauri/`（正式宿主） | Tauri `2.11.5`、tauri-build `2.6.3`；`desktop/src-tauri/` 是旧壳，被根 workspace 排除 |
| 前端 | `frontend/` React + TypeScript + Vite | React `18.3.1`、Vite `^5.4.11`、Vitest `^2.1.9`、TS `^5.5.4`、pdfjs-dist `6.4.299`、Tiptap `3.31.4`、dockview `8.5.1` |
| Core | `crates/archeaxis-*` | rusqlite `0.39.0`（bundled/backup）、axum `0.7`、tokio 1；SQLite WAL；CAS + 单写者 |
| 检索 | SQLite FTS5 + Python 语义 worker | `knowledge_fts`、`transform_fts`；无持久化向量表；语义检索为查询时快照 |
| Worker | `services/python-workers/` 30+ 个 NDJSON worker | PDF/Office/OCR/媒体/网页/研究/模型/学习/质量 |
| 本地模型 | LM Studio OpenAI-compatible | 回答 `qwen3.5-4b`；embedding `qwen3-embedding-0.6b`；rerank `qwen3-reranker-0.6b`（本机无 `/v1/rerank`，走 logprobs 近似） |
| 云端模型 | `material_cloud.py` + `document_check.py` | OpenAI-buffered 专业接口；真实云推理按 Owner 决定未执行 |
| 安装 | Tauri NSIS/MSI | `currentUser`、`zlib`、`webviewInstallMode=skip`、无 updater、无签名 |

---

## 2. 逐环节审计

### 2.1 文件类型检测

- 现状：`worker_detect.py` 使用 vendored Magika ONNX（Apache-2.0），返回 label/group/score，明确不把 label 猜成 MIME。
- 结论：这一环已经成熟，**保留**。可选升级到 `standard_v3_3`（环境登记已声明），但升级必须同步模型身份与测试，不是免费收益。

### 2.2 文本与网页

- 文本/Markdown/RTF/CSV/JSON/EPUB/ODF：`worker_light_formats.py`，RTF 用 `striprtf`，EPUB 自解析。
- HTML：`worker_html.py` 用标准库 `HTMLParser`，只跳过 script/style 等标签；**没有调用 Trafilatura**。
- 网页抓取：`worker_webpage.py` 有有界抓取与可选 Playwright 渲染，但渲染结果仍交给基础 HTML 抽取。
- 结论：正文质量是研究链和剪藏链的瓶颈；Trafilatura 已在依赖里，接线成本低。**P1：先用 Trafilatura，失败回退现有抽取器。**

### 2.3 PDF

- 现状：`worker_pdf.py` 使用 PyMuPDF，逐页文本块、图片清单、`find_tables()` 表格几何、启发式双栏阅读序；无文本页渲染 PNG 供 OCR。
- 限制：阅读序是启发式模型（“one vertical gutter, then column by column”），不是学习式版面模型；扫描页只负责渲染，OCR 由另一 lane 处理。
- 许可证：PyMuPDF 为 **AGPL-3.0 或商业许可**，当前已被打包分发但未在 NOTICES 披露。
- 结论：功能上够用；许可证是主要风险。**P0：披露并决策；P1：pypdfium2 + pdfplumber 试点替换。**

### 2.4 Office

- DOCX：纯标准库 ZIP+XML（段落/表格/媒体清单），不是完整版式保真。
- PPTX：`python-pptx`；XLSX：`openpyxl`；XLS：`xlrd`；DOC：`antiword` 旁路；PPT：Tika + Zulu JRE 旁路。
- 缺失：原应用级渲染/编辑/往返、复杂样式、批注、修订、图表语义。
- 结论：读文本与结构够用，不能宣称“Office 全保真”。若要提升，Docling 是 MIT 候选，但依赖重，**只适合可选 sidecar，不进主包**。

### 2.5 OCR 与版面

- 现状：`worker_ocr.py` 只调用系统 Tesseract；`REVIEW_THRESHOLD=60` 只是审阅阈值，不是准确率。
- 安装器载荷：没有 `tesseract.exe`、没有 `tessdata`、没有 `rapidocr_onnxruntime`；只有 `pytesseract` 包装层。
- 既有设计：`pyproject.toml` 的 `ci-adapters` 有 `rapidocr-onnxruntime`；legacy `app/ingestion/rapid_ocr_adapter.py` 用 RapidOCR；环境登记称 RapidOCR “bake-off CER 最优”。vNext worker 没有接线。
- 结论：**P0。** 干净安装的 OCR 不可用是产品级缺陷。建议把 RapidOCR（PP-OCR ONNX 三模型，Apache-2.0）作为默认引擎随包分发；Tesseract 保留为可选回退。版面/表格再加 RapidLayout / RapidTable（Apache-2.0，ONNX），比引入 PaddlePaddle 或 Docling 轻得多。

### 2.6 媒体、ASR、视频、说话人

- 解码：PyAV + FFmpeg 8.1.2（LGPL 子集，wheel 内 `av.libs`）；`media_decode.py` 在系统 ffmpeg 缺失时回退。
- ASR：faster-whisper `1.2.1`；安装器自带 `faster-whisper-base`；共享库有 `large-v3-turbo`；SenseVoice 只在环境登记/可选 extra 中，未接入 vNext。
- 时间定位：segment 级 cue；VAD `speech_pad_ms=400` 已按真实位置保留并标注。
- 说话人：`worker_diarize.py` 用 sherpa-onnx + pyannote segmentation 3.0 + speaker embedding。
- 视频：固定 `--frame-interval-ms 10000`、最多 24 帧；视觉描述最多 3 帧，走 7B VL。
- 结论：ASR 链路成熟；视频“视觉覆盖”仍是采样而非事件覆盖。**P1：PySceneDetect（BSD-3）做镜头边界；Florence-2（MIT, 0.23B）承担简单 OCR/描述；7B 只做复杂场景。** SenseVoice 可作中文快速 lane，但权重许可需先核实（**UNVERIFIED**）。

### 2.7 公开研究与检索

- 现状：`public_research.py` 的 `FAMILIES` 只有 `wikipedia`、`stackexchange`、`openalex`。
- Crossref/DataCite/Wikidata：只出现在 `frontend/src/api/generated/resource-catalog.ts`，没有 worker/Core 消费。
- 缺失：arXiv、PubMed、Semantic Scholar、DOI 解析、全文可获取性判断、来源去重后的多源比较。
- 结论：CL-03 的“三类通道”已满足最低形态，但“科研全文与 DOI 证据”仍薄。**P1：先接 Crossref/DataCite/Wikidata 的元数据；全文通道按免费条件逐个核实后接入，不能假设免费。**

### 2.8 存储、索引、语义检索

- SQLite WAL + `rusqlite` + CAS 校验；Rust 是唯一写者，边界正确。
- FTS5：`knowledge_fts` 与 `transform_fts` 每次查询前 `DELETE` + 全量 `INSERT`。
- 语义：`semantic.rs` 查询时取全部 `accepted` 知识，worker 计算 query + 候选 embedding，再按余弦/logprobs 排序；没有 embedding 表、没有增量更新、没有 ANN。
- 结论：**P0/P1。** 先做 FTS 增量维护与 `snippet()/highlight()`；再做 embedding 缓存（模型身份 + 维度 + 版本）与混合检索。**不建议现在引入 Tantivy/Kùzu**：FTS5 已够用，Kùzu 已被登记为 REJECT-CORE。

### 2.9 模型接入与小模型分工

- 本地回答：`worker_machine_answer.py`，LM Studio，OpenAI 兼容，usage 只认真实报告值。
- 云端：`material_cloud.py` 有确认、预览、取消、失败边界；真实云推理未执行。
- 文档核验：`document_check.py` 可走 LiteLLM adapter；独立检索 query 必填。
- 语义重排：`semantic_ranking.py` 用 Responses logprobs 判断 yes/no；不是标准 rerank 接口。
- 配置：`config/models.yaml` 仍是 `stub` + `hash-embedding`，与运行时的 LM Studio 路径不一致；这是“默认回退配置”，但容易被误读为产品实际模型。
- 结论：模型接入“能用”，但缺少**按任务分角色**的模型注册与路由（小模型只做一件事）。建议新增“任务角色”层（不新建第二模型运行时）：`detect/ocr/layout/embed/rerank/tag/summarize/rewrite/nli/asr/diarize`，每个角色声明模型、端点、许可证、尺寸、失败回退。

### 2.10 前端与交互

- 结构：22 页 + 414 个 TS/TSX 文件；Tiptap 编辑器、pdfjs 阅读器、MediaReader、Dockview、图谱、检查器。
- 状态：以 React Context/局部 state 为主，无 TanStack Query/Zustand/Redux；数据请求手写。
- 请求：`createApiClient` 无统一超时、AbortController、重试/退避；错误映射到 `ApiError`。
- 测试：记录显示 2108 项中 2090 通过 / 18 失败，且与改动前基线相同；失败是长期质量债。
- 可访问性：已有焦点环、对比度、`axe` 检查与窄窗门槛；仍缺屏幕阅读器/IME/DPI 全面验收。
- 结论：**P1：** 先引入查询缓存/取消/重试策略（TanStack Query 或等价最小实现），再评估 React 19 + Vite 7 + Vitest 5 的独立升级切片。**不要**为了“新”而重写编辑器/阅读器。

### 2.11 桌面、安装、更新、签名

- 现状：Tauri 2.11.5（当前代际），NSIS `currentUser`，`zlib` 压缩，`webviewInstallMode=skip`，无 updater，无代码签名。
- 后果：
  - 安装包比必要的大；
  - 无法做应用内升级/回滚（J6 缺口）；
  - 浏览器下载会触发 SmartScreen；
  - 依赖系统 WebView2（本机有，干净机器不一定）。
- 结论：**P0/P1。** 先改 `lzma`；再加 `tauri-plugin-updater`（2.14.x）与签名流程；WebView2 是否固定分发需按体积/离线需求决策。

### 2.12 质量、测试、安全、供应链

- CI：exact-SHA 全绿；AXR060、Gitleaks、pip-audit、Syft 已接入；安装态旅程与 AV UI 有真实回执。
- 缺口：
  - PyMuPDF AGPL 未披露；
  - 运行时包体冗余（见 P2）；
  - 18 项前端基线失败；
  - 安装器无 SBOM 附属文件（Syft 在 CI，但用户拿到的安装包不带 SBOM/NOTICE 汇总）；
  - 模型资产许可（SenseVoice、Qwen2.5-VL、Docling 模型）需要逐项固化到 `aaos-model.json`/NOTICES。

---

## 3. 缺陷清单（带证据）

| 级别 | 缺陷 | 证据 |
| --- | --- | --- |
| P0 | OCR 引擎未随包分发 | 安装器载荷无 `tesseract.exe`/`tessdata`/`rapidocr_onnxruntime`；`services/python-workers/vision/worker_ocr.py` 只走 Tesseract |
| P0 | PyMuPDF AGPL 未披露 | `pyproject.toml` 主依赖 `pymupdf`；载荷 `pymupdf` 48MB；`THIRD_PARTY_NOTICES.md` 无 PyMuPDF/MuPDF 条目 |
| P0 | FTS 每次查询全量重建 | `crates/archeaxis-domain/src/search.rs` `search()`/`search_transforms()` 先 `reindex()` |
| P0 | 语义检索无持久化索引 | `crates/archeaxis-api/src/runtime/semantic.rs` 每次快照全部知识；`crates/archeaxis-migration/src/lib.rs` 注明“mainline has no vector table yet” |
| P0 | 安装器压缩配置劣于默认 | `src-tauri/tauri.conf.json` `"compression": "zlib"`（Tauri 默认 `lzma`） |
| P0 | 无 updater / 无签名 | `src-tauri/Cargo.toml` 无 `tauri-plugin-updater`；`tauri.conf.json` 无签名配置 |
| P1 | Trafilatura 未接线 | `pyproject.toml` 有 `trafilatura`；`worker_html.py` 仍用 `HTMLParser` |
| P1 | 研究来源仅 3 族 | `public_research.py` `FAMILIES` 只有 wikipedia/stackexchange/openalex |
| P1 | 视频固定采样、无镜头检测 | `worker_video.py` 头注释与 `--frame-interval-ms 10000` |
| P1 | 7B VL 承担所有视觉描述 | `worker_caption.py` `OPENAI_MODEL="qwen2.5-vl-7b-instruct"` |
| P1 | 前端请求无统一超时/取消/重试 | `frontend/src/api/client.ts` `requestRaw` 直接 `fetch` |
| P1 | 前端代际落后 | `frontend/package.json` React 18.3 / Vite 5 / Vitest 2 / TS 5.5 |
| P1 | 运行时包体冗余 | 载荷 `litellm` 53.3MB、`pandas` 33MB、`babel` 29.4MB、`sympy` 25.4MB、`pymupdf` 48MB |
| P2 | `config/models.yaml` 与运行时不一致 | `config/models.yaml` 仍为 `stub`/`hash-embedding`；运行时为 LM Studio |
| P2 | Windows 文本/CRLF 残留 | 工作区仍有 4 个 CRLF-only 脏文件（未提交） |
| P2 | 文档漂移 | `services/python-workers/README.md` 仍写“F06 逐页 OCR 未接线”，与当前扫描 PDF 证据不一致 |

---

## 4. 小模型矩阵（按环节，只做一件事）

原则：**能用确定性算法/ONNX 小模型的，不用 LLM；能按需安装的，不进主包。** 主包优先只新增 OCR/版面两个小模型。

| 环节 | 推荐 | 规模 | 许可证 | 运行方式 | 现状 | 建议 |
| --- | --- | --- | --- | --- | --- | --- |
| 文件类型 | Magika `standard_v3_3` | 小型 ONNX | Apache-2.0 | ONNX Runtime | 已接入 | 保留；升级需同步模型身份 |
| 语言识别 | Lingua | 规则/统计，无大权重 | Apache-2.0 | Python/Rust | 未接 | P2；比 fastText（模型 CC-BY-SA）更干净 |
| OCR | RapidOCR PP-OCRv4/v5 | det+rec+cls 约 15MB | Apache-2.0 | ONNX Runtime | 依赖存在，未接线 | **P0 随包**；Tesseract 回退 |
| 版面 | RapidLayout | 小型 ONNX | Apache-2.0 | ONNX Runtime | 未接 | P1；替代学习式版面模型 |
| 表格 | RapidTable / TableFormer | 小型 ONNX | Apache-2.0 / MIT | ONNX Runtime | 部分（PyMuPDF 几何） | P1；先 RapidTable |
| 公式 | pix2tex | ~100MB+ | MIT | PyTorch | 未接 | P2 可选；不进主包 |
| ASR 默认 | faster-whisper-base | 145MB | MIT | CTranslate2 | 已随包 | 保留 |
| ASR 中文快线 | SenseVoice-small int8 | 约 200–300MB | **UNVERIFIED** | sherpa-onnx | 已声明未接 | P1 先核权重许可 |
| ASR 英文快线 | Parakeet TDT 0.6B v3 | 0.6B | CC-BY-4.0 | ONNX/GGML | 未接 | P2；仅英文 |
| 词级对齐 | WhisperX | 依赖 wav2vec2 | BSD-2-Clause | PyTorch | 未接 | P2；先评估体积 |
| 说话人 | sherpa-onnx + pyannote 3.0 | 两枚 ONNX | Apache-2.0 runtime；资产 MIT/CC-BY | ONNX | 已接 | 保留 |
| 镜头检测 | PySceneDetect | CPU 算法 | BSD-3-Clause | Python | 未接 | P1；替代固定 10 秒采样 |
| 视觉描述 | Florence-2-base | 0.23B | MIT | ONNX/PyTorch | 未接 | P1；简单 OCR/描述 |
| 视觉复杂场景 | Qwen2.5-VL-7B | 7B | Apache-2.0 | LM Studio | 已接 | 保留为可选大模型 |
| Embedding | Qwen3-Embedding-0.6B | 0.6B | Apache-2.0 | LM Studio | 已接 | 保留；补持久化缓存 |
| Rerank | bge-reranker-v2-m3 或 Qwen3-Reranker-0.6B | 0.6B | Apache-2.0 | ONNX/专用 rerank | 近似 logprobs | P1；用真实 rerank 接口 |
| NER | GLiNER2.5-small | 74M | Apache-2.0 | ONNX | 未接 | P2 |
| 关系 | GLiNER2（含关系） | 0.2–0.3B | Apache-2.0 | ONNX | 未接 | P2；GLiREL 是 CC-BY-NC，拒绝 |
| 标签/摘要 | Qwen3-1.7B | 1.7B | Apache-2.0 | LM Studio | 未接 | P2；一个模型多提示词 |
| 查询改写 | Qwen3-0.6B | 0.6B | Apache-2.0 | LM Studio | 未接 | P2 |
| NLI/核验 | DeBERTa-v3-small MNLI | ~180MB | MIT | ONNX | 未接 | P2 |
| TTS | Kokoro-82M | 82M | Apache-2.0 | ONNX | 未接 | P3 可选；Piper 许可存在分歧，不推荐 |
| 翻译 | Qwen3-1.7B | 1.7B | Apache-2.0 | LM Studio | 未接 | P3；NLLB 是 CC-BY-NC，拒绝 |

---

## 5. 候选技术处置矩阵

| 候选 | 许可证 | 处置 | 理由/接入方式 |
| --- | --- | --- | --- |
| RapidOCR | Apache-2.0 | **ADOPT NOW** | 已有设计；ONNX；随包约 15MB；OCR 干净安装可用 |
| RapidLayout / RapidTable | Apache-2.0 | **ADOPT** | ONNX；版面/表格；避免 Paddle 框架 |
| Trafilatura | Apache-2.0 | **ADOPT** | 已在依赖；接线 `worker_html`，保留回退 |
| PySceneDetect | BSD-3-Clause | **ADOPT** | 镜头边界；替换固定采样 |
| Florence-2 | MIT | **PILOT** | 0.23B；简单 OCR/描述；需评估 ONNX 导出 |
| WhisperX | BSD-2-Clause | **PILOT** | 词级时间戳；依赖 torch/wav2vec2，体积需评估 |
| Parakeet TDT 0.6B v3 | CC-BY-4.0 | **EVALUATE** | 英文强；多语言有限 |
| GLiNER2.5 | Apache-2.0 | **PILOT** | 74M NER；关系用 GLiNER2 |
| bge-reranker-v2-m3 | Apache-2.0 | **PILOT** | 568M；比 7B 便宜；需 rerank 运行时 |
| bge-m3 | MIT | **EVALUATE** | 与 Qwen3-Embedding 二选一，不并存 |
| Kokoro-82M | Apache-2.0 | **DEFER** | 朗读/无障碍可选；非闭环必需 |
| Docling | MIT（代码）；模型 MIT/Apache | **PILOT as sidecar** | 高保真版面/表格；依赖重，不进主包 |
| olmOCR | Apache-2.0 | **PILOT** | 学术 PDF；VLM 重，可选 sidecar |
| MinerU | MinerU Open Source License（Apache-2.0 + 附加条款） | **HOLD/REVIEW** | 登记原为 AGPL REVIEW-BLOCK；已改许可但附加条款需法务复核 |
| Marker | GPL + 权重 CC-BY-NC-SA | **REJECT** | 不适合当前分发模型 |
| Surya | 版本间许可不一致（GPL/权重 NC vs 新版 Apache 声明） | **HOLD** | 许可 **UNVERIFIED**，不接入 |
| GLiREL | CC-BY-NC-SA | **REJECT** | 非商用限制 |
| SearXNG | AGPL-3.0 | **KEEP BLOCK** | 既有登记；不自建聚合壳 |
| Firecrawl | AGPL/付费 | **KEEP BLOCK** | 既有登记 |
| Kùzu | MIT | **KEEP REJECT-CORE** | 已有 FTS/图谱边界，避免第二存储 |
| tldraw | 自定义/水印条款 | **KEEP BLOCK** | 既有登记 |
| pypdfium2 | Apache-2.0/BSD-3 | **PILOT** | 替换 PyMuPDF 渲染；配合 pdfplumber |
| pdfplumber | MIT | **PILOT** | 文本/表格；MIT |
| Tauri updater | MIT/Apache-2.0 | **ADOPT** | 2.14.x；需签名与更新端点 |
| Crossref / DataCite / Wikidata | 各自 API 条款 | **ADOPT/VERIFY** | 元数据通道；免费额度与 UA 需核实 |
| arXiv / PubMed / Semantic Scholar | 各自条款 | **EVALUATE** | 先元数据/摘要，不假设全文免费 |

---

## 6. 建议实施顺序（每步可独立回滚）

### Wave 0：合规与开箱可用（最小改动）

1. `src-tauri/tauri.conf.json`：`zlib` → `lzma`；重新测量安装器体积与构建时间。
2. `THIRD_PARTY_NOTICES.md`：补 PyMuPDF/MuPDF AGPL 条目与源码获取方式；同步 `SUPPLY_CHAIN_LEDGER.json` 的 PyMuPDF 行。
3. 打包 RapidOCR：在 `pyproject.toml` 主依赖或打包白名单加入 `rapidocr-onnxruntime`，固定模型版本与 SHA；`worker_ocr.py` 优先 RapidOCR，Tesseract 回退；新增“干净载荷无 Tesseract”负例。
4. 加 `tauri-plugin-updater` 与签名配置骨架；未配置密钥时明确 `NOT_ACTIVATED`，不伪造更新能力。

验收：安装器在无 Tesseract 的隔离环境完成图片/扫描 PDF OCR；体积对比；NOTICES 哈希；AXR060 与定向测试通过。

### Wave 1：检索与网页质量

1. `search.rs`：改为触发器/增量索引；加 `snippet()` 与 `highlight()`；保留查询转义测试。
2. `worker_html.py`：Trafilatura 主路径 + 现有 parser 回退；用现有网页样本做对照，记录正文/噪声差异。
3. `semantic.rs`：先加 embedding 缓存表（模型 ID、维度、源版本、向量 blob），Rust 内余弦精确检索；>50k 再评估 ANN。
4. 研究来源：接 Crossref/DataCite/Wikidata 元数据；arXiv/PubMed 仅在确认免费与许可后接入。

验收：大库搜索不随库增长线性变慢；同一 query 的 FTS/语义结果可解释；来源 receipt 可回跳。

### Wave 2：媒体与视觉

1. `worker_video.py`：PySceneDetect 镜头边界 + 关键帧；保留固定采样回退。
2. `worker_caption.py`：Florence-2 处理 OCR/简单描述；7B 仅复杂场景；模型角色配置化。
3. `worker_transcribe.py`：可选 SenseVoice 快速 lane（先核实权重许可）；faster-whisper 保持默认。
4. `worker_diarize.py`：保持 sherpa；评估 pyannote 新版权限，不自动接受 gated 下载。

验收：视频镜头覆盖可解释；视觉任务不再一律 7B；ASR 默认/快速 lane 的引擎身份与损失分别记录。

### Wave 3：前端与包体

1. 请求层：统一 AbortController/超时/重试策略；长任务用显式状态而非静默重试。
2. 独立升级切片：React 19 + Vite 7 + Vitest 5 + TS 5.9；先跑基线，保留 18 项失败清单，不混入业务改动。
3. 包体审计：基于导入图裁剪 `litellm/pandas/sympy/babel` 等未用依赖；输出“删除项—引用证据—回滚”清单。
4. 可选：TanStack Query / 虚拟列表；先测量再引入。

---

## 7. 不改变的产品边界

- 本文不把任何候选写成“已接入”。除已实测项外，均为 **CANDIDATE / PILOT / HOLD**。
- CL-04 成熟知识库全面兼容、CL-05 开源池吸收仍按延期处理；本文不把 Docling/MinerU 等候选升级为“全面兼容”。
- 云端真实推理仍为 `DEFERRED`；本文不配置凭据、不调用付费服务。
- 跨版本升级/回退仍为 `NOT_EXECUTED`；updater 是能力建设，不等于已有前序 Rust 版本可升级。
- Owner 验收仍为 `NOT_EXECUTED`；安装器仍不覆盖现有用户安装。

---

## 8. 外部来源（访问日期 2026-10-25）

- Docling（MIT）：https://pypi.org/project/docling/2.113.0/ ，https://docling.org/about/
- Docling 模型目录：https://docling-project.github.io/docling/usage/model_catalog/
- PaddleOCR / PP-StructureV3（Apache-2.0）：https://www.paddleocr.ai/main/en/index/ ，https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-StructureV3/PP-StructureV3.html
- RapidLayout（Apache-2.0）：https://pypi.org/project/rapid-layout/0.0.15/
- RapidTable（Apache-2.0）：https://pypi.org/project/rapid-table/
- olmOCR（Apache-2.0）：https://pypi.org/project/olmocr/
- MinerU 许可变更：https://opendatalab.github.io/MinerU/reference/changelog/
- Surya（许可存在版本差异，UNVERIFIED）：https://pypi.org/project/surya-ocr/0.22.0/ ，https://pypi.org/project/surya-ocr/0.2.0/
- Florence-2（MIT）：https://www.microsoft.com/en-us/research/publication/florence-2-advancing-a-unified-representation-for-a-variety-of-vision-tasks/
- Parakeet TDT 0.6B（CC-BY-4.0）：https://catalog.ngc.nvidia.com/orgs/nim/teams/nvidia/containers/parakeet-0.6b-tdt
- GLiNER（v2.1/2.5 Apache-2.0；v0/v1 CC-BY-NC）：https://pypi.org/project/gliner/ ，https://fastino.ai/blog/gliner2-5-span-free-information-extraction
- GLiREL（CC-BY-NC-SA）：https://pypi.org/project/glirel/1.2.0/
- bge-m3（MIT）/ bge-reranker-v2-m3（Apache-2.0）：https://build.nvidia.com/baai/bge-m3.md ，https://bge-model.com/_sources/bge/bge_reranker_v2.rst.txt
- Qwen3-Embedding（Apache-2.0）：https://www.siliconflow.com/models/qwen-qwen3-embedding-0-6b
- WhisperX（BSD-2-Clause）：https://patch-diff.githubusercontent.com/m-bain/whisperX
- PySceneDetect（BSD-3-Clause）：https://www.scenedetect.com/download/
- Kokoro-82M（Apache-2.0）：https://kokorotts-ai.com/about
- Trafilatura（Apache-2.0）：https://trafilatura.readthedocs.io/en/latest/
- PyMuPDF（AGPL-3.0 或商业）：https://pymupdf.readthedocs.io/en/latest/_sources/about.rst ，https://pypi.org/project/PyMuPDF/
- pypdfium2（Apache-2.0/BSD-3-Clause）：https://pypi.org/project/pypdfium2/4.4.0/
- pdfplumber（MIT）：https://www.npmjs.com/package/git-for-me （转引 GitHub jsvine/pdfplumber；建议以仓库 LICENSE 复核）
- FFmpeg（LGPL-2.1+）：https://www.ffmpeg.org/doxygen/trunk/md_LICENSE.html
- PyAV（BSD-3-Clause 绑定）：https://pypi.org/project/pyav/11.1.0/
- FSRS Python（MIT）：https://pypi.org/project/fsrs/
- Tauri updater：https://tauri.app/release/updater/
- Tauri NSIS 压缩默认 lzma：https://v2.tauri.app/reference/config/
- Tauri Windows 签名：https://tauri.app/fr/distribute/sign/windows/
- Vitest 5（2026-09）：https://main.vitest.dev/blog/vitest-5
- Vite 7（2025-06）：https://ko.vite.dev/blog/announcing-vite7
- pdfjs-dist 6.4.299（当前 latest）：https://www.npmjs.com/package/pdfjs-dist?activeTab=versions
- Tauri 2.11.5：https://v2.tauri.app/release/tauri/
- sqlite-vec 0.1.10-alpha ANN 进展：https://dreaming.press/posts/sqlite-vec-ann-diskann-alpha-brute-force-when-to-graduate.html

---

## 9. 未验证项（必须二次核实）

- SenseVoice 权重许可与再分发条款（环境登记只写了运行时 Apache-2.0）。
- Docling 各模型权重的完整许可组合（layout Apache-2.0 已见，TableFormer MIT 已见，但需逐文件核对发行包）。
- Surya 当前发行版代码与权重许可是否一致（搜索结果自相矛盾）。
- MinerU 附加条款对分发/在线服务的影响（需法务复核，不能只按“Apache-2.0”处理）。
- PyAV 每个 wheel 内 FFmpeg 的实际编译选项（NOTICES 写 LGPL 子集，但仍应逐发行版核对 `av.libs`）。
- Magika `standard_v3_3` 的参数量/体积与升级影响。
- 各外部 API（Crossref/DataCite/Wikidata/arXiv/PubMed/Semantic Scholar）的当前免费额度、UA 要求与全文可获取性。
- 18 项前端基线失败的具体用例与是否仍具产品意义（本次未重跑全量套件）。

---

## 10. CI 失败分类与可复用修复（2026-10-25 补记）

最近几轮失败不是“开源方案不够”，而是本项目把**输入字节钉进了多层派生契约**；一次依赖变更会沿链触发校验，任何一层没同步都会以“CI 失败”出现。逐类如下：

| 类别 | 典型报错 | 根因 | 可复用修复 |
| --- | --- | --- | --- |
| 锁文件派生哈希 | `Qualification source drift: uv.lock`；`release-manifest` digest 不符 | `uv.lock`／`pyproject.toml` 变了，但 `AAOS-RESOURCE-QUALIFICATION`、`app/release-manifest.json`、`resource-catalog.ts` 未同批重建 | 依赖变更必须与“锁文件→release-manifest→qualification→resource-catalog”同批重建；禁止拆成多个提交 |
| 账本派生哈希 | `input-drift[docs/truth/SUPPLY_CHAIN_LEDGER.json]`；OSS manifest 输出 digest 不符 | `SUPPLY_CHAIN_LEDGER.json` 被 `OSS-REUSE-CROSSWALK-20261008.manifest.json` 字节钉住，改账本必须重建 701 行 OSS 表 | 功能切片不改账本；账本变更单独切片，重建表并更新 manifest 全部 inputs/outputs |
| 运行依赖清单 | `requirements.txt` 与 `pyproject.toml` runtime deps 不一致 | 只改 `pyproject`，没同步 `requirements.txt` | 依赖变更同批改三处：`pyproject.toml`、`requirements.txt`、`uv.lock` |
| 测试夹具假设 | `FOREIGN KEY constraint failed`；搜不到自己刚插入的行 | 测试删除了已被 review 事件引用的知识行；查询词与 body 不一致 | 测试用独立未 review 行验证删除；查询词必须与夹具正文一致 |
| 异步 UI 竞态 | `Unable to find an element with the text: 跳过：排除目录` | 第一行已渲染，第二行尚未挂载就用了同步 `getByText` | 对异步新增行统一用 `findByText`，不要用第一行的完成信号推断第二行 |
| 安装器/构建 | 体积、成员数、`installer-lifecycle` | 依赖增加或压缩方式改变 | 在 `desktop-build` 产物上读回真实体积与成员；不在本地伪造 |

**可直接复用的工程做法**（不需要改产品架构）：

1. 新增 `scripts/ci/preflight_contracts.py`：在推送前一次性运行上述派生检查（resource catalog、release manifest、external index、OSS manifest、requirements 同步），失败即停。
2. 依赖变更采用“单提交闭环”：`pyproject.toml` + `requirements.txt` + `uv.lock` + 所有派生哈希一次提交，禁止“先合依赖、后补哈希”。
3. 功能变更与依赖变更分开：功能切片不碰 `SUPPLY_CHAIN_LEDGER`、不改 `uv.lock`；需要时单独开“供应链重绑定”切片。
4. 对异步 UI 断言统一使用 `findByText`/`waitFor`；对状态机测试避免删除被事件引用的实体。
5. 失败日志保留并按上表归类，不把“本地通过”当成 exact-SHA 通过。
