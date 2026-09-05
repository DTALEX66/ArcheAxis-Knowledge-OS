# services/python-workers（隔离 capability worker）

> DIRECTORY_AUTHORITY：`services/python-workers/**` 为 worker 执行域，**无主库权限**
> （may_open_main_database=false）。语言边界：Python worker 只能经本地 HTTP API
> （crates/archeaxis-api，契约 packages/contracts/v1）与 Rust Core 交互。
> 禁止：直连 SQLite、写库、sys.path 修改后 import app 包、双写。

## Worker 能力矩阵（2026-09-05 实测状态）

| worker | 格式/能力 | 引擎 | 状态 | 收据 |
|---|---|---|---|---|
| worker_extract.py | 纯文本 envelope 样例 | stdlib | ✅ gate | T02s1 |
| document/worker_text.py | TXT/MD/CSV/TSV/JSON/XML(F01) | stdlib | ✅ | T05s1 |
| document/worker_canvas.py | JSON Canvas(F12) | stdlib | ✅ | T05s1 |
| document/worker_subtitles.py | SRT/VTT(F12) | stdlib | ✅ | T05s1 |
| document/worker_office.py | DOCX/PPTX/XLSX/PDF(F05/F07/F08/F09) | stdlib+pptx+openpyxl+pymupdf | ✅(docx CI 全跑; 其余本地实测) | T05s2b |
| document/worker_html.py | 静态 HTML 快照(F02 正文段) | stdlib | ✅ | T05s2a |
| web/worker_webpage.py | 有界抓取+快照(F02 网络) | urllib | ✅ 本地实测 | T05s2c |
| media/worker_transcribe.py | WAV/MP3/M4A/FLAC ASR(F10) | faster-whisper-large-v3-turbo | ✅ 本地实测 | T06s1 |
| media/worker_video.py | 视频音轨+关键帧(F11 部分) | ffmpeg | ✅ 本地实测 | T06s2a |
| vision/worker_ocr.py | 图像 OCR 文本+框(F04 部分) | tesseract 5.5 | ✅ 本地实测 | T06s2b |
| vision/worker_caption.py | 图示/场景描述(F04 层2) | ollama qwen2.5vl:7b | ✅ 本地实测 | T06s2c |
| evaluation/worker_quality.py | CER/WER 评测(T07) | stdlib | ✅ | T07s1 |

通用契约：成功=单行 JSON envelope（engine/engine_version/text 或格式专属字段 + loss_receipt）；
失败=非零退出 + `{"error": ...}`，绝不伪造成功。CI 门禁：`workers-vnext`
（scripts/ci/check_vnext_workers.py：编译+正反例+探针+失败契约）。

## 明确边界（不冒充已完成）

- F03 动态网页渲染/截图：需 playwright+chromium 运行器，当前标 BLOCKED-RUNTIME（记录于模型 profile）。
- F06 扫描 PDF/混合 OCR 页：OCR lane 组件已备（rapidocr/tesseract 探测），逐页判定编排未接线。
- 嵌入图/幻灯片图像 OCR、字幕对齐、画面事件语义（VL）：独立 lane 未接线。
- 广告/正文分离（trafilatura 级）与多栏阅读序：后续 slice。

## worker-protocol（contract: packages/contracts/v1/worker-protocol.schema.json）

worker 调用流（v0.1 slice 未实现 HTTP job 队列前的最小形态）：

1. 输入：文件路径 / 原始字节 + source_name（owner 通过 Core 导入后调用）
2. 处理：调用本仓可替换能力（解析/OCR/ASR 由包 C 引擎：pymupdf/RapidOCR/SenseVoice —— 复用现有 legacy 引擎代码作为行为来源）
3. 输出：`text` + `loss_receipt`（engine/version/params/loss_note）→ POST 给 Core（Rust 持久化 transform）
4. 失败：显式错误回执；绝不假装成功

HTTP job 包装（request_id/job_id/attempt，worker-protocol.schema.json）由 T04 执行器 lane 负责；
envelope 契约与通道映射见 `packages/contracts/v1/protocol-mapping.md`。
