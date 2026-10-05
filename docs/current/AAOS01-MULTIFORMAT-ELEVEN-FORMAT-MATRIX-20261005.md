# AAOS-01 多格式闭环：11 种格式的实测总表（2026-10-05）

同一权威候选、全新数据根、声明 `text_worker`、经 36 条路由的 Core；每种格式走完整闭环
（import → job → execution → 终态 → `outputs/text` → `quality`）。

## 通过（8 种）

| 格式 | 夹具/样本 | job kind | quality.engine | loss | coverage |
| --- | --- | --- | --- | --- | --- |
| 文本 | `golden-text-anchor.txt` | `text` | `python-worker-text` | 0 | 1.0 |
| Word | `golden-docx-anchor.docx` | `office` | `python-worker-office` | 1 | 1.0 |
| HTML | `golden-web-anchor.html` | `html` | `python-worker-html` | 1 | 1.0 |
| 音频 | `golden-audio-anchor.wav` | `media` | `python-worker-media` | 1 | 1.0 |
| 视频 | `golden-video-anchor.mp4` | `media` | `python-worker-media` | 1 | 1.0 |
| **Canvas** | `anchor.canvas`（JSON Canvas） | `canvas` | **`python-worker-canvas`** | 1 | 1.0 |
| **压缩包** | `anchor.zip` | `archive` | **`python-worker-archive`** | 0 | 1.0 |
| **字幕** | `anchor.srt` | `subtitles` | **`python-worker-subtitles`** | 1 | 1.0 |

## 失败（3 种）—— 全部为引擎可用性，非格式处理能力

| 格式 | job kind | 错误码 | 消息 |
| --- | --- | --- | --- |
| Excel | `office` | `AAK-WORKER-003` | xlsx engine missing (openpyxl not installed) |
| PowerPoint | `office` | `AAK-WORKER-003` | pptx engine missing (python-pptx not installed) |
| 截图 OCR | `image` | `AAK-WORKER-003` | tesseract binary not found on PATH (OCR engine unavailable) |

**这三种失败的定性仍未判定**：`uv.lock` 已含 `openpyxl`/`python-pptx`（带 wheel URL ✓），
而所测候选的 `runtime/` 早于锁（07-29 vs 10-01）⇒ **陈旧候选与漏装皆未排除**。
判定已交由 CI 断言（`desktop-build` 的 engine-assert step），**该轮结论未出**。

**OCR 另属一类**：`tesseract` 与 `tesseract-languages` **已存在于外部共享工具库**，
缺的是候选未指向它（`TESSDATA_PREFIX` / PATH）—— **是「指路」而非「缺引擎」**。

## 方法要点（可复用）

- **job kind = 能力前缀**（`canvas` → `canvas.structure`）；
- **引擎身份在 `jobs/:id/quality`**，不在 `capabilities`；
- **输出种类由 worker 写入**；失败时 `quality` 字段为 `null`（**不伪造**）；
- **`capabilities` 仅在声明 `text_worker` 时挂载**（否则 18 条而非 36 条路由）；
- **`text_worker` 路径不得带 `\\?\` 前缀**（已修）；
- **必须用全新数据根**（Core 打不开旧 Python 库）；
- **`canvas`/`archive`/`subtitles` 无现成金样本** —— 本轮自建最小样本（JSON Canvas / zip / srt）后测通。
