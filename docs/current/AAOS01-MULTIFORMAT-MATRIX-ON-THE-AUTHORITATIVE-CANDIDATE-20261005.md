# AAOS-01 多格式闭环：权威候选上的实测矩阵（2026-10-05）

同一份权威候选、全新数据根、声明 `text_worker`、经 36 条路由的 Core，逐格式跑完整闭环
（import → job → execution → 终态 → `outputs/text` → `quality`）。

## 结果

| 夹具 | job kind | import | 终态 | outputs/text | quality.engine | loss | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `golden-text-anchor.txt` | `text` | 202 | **succeeded** | 200 | `python-worker-text` | 0 | 1.0 |
| `golden-docx-anchor.docx` | `office` | 202 | **succeeded** | 200 | `python-worker-office` | 1 | 1.0 |
| `golden-web-anchor.html` | `html` | 202 | **succeeded** | 200 | `python-worker-html` | 1 | 1.0 |
| `golden-audio-anchor.wav` | `media` | 202 | **succeeded** | 200 | `python-worker-media` | 1 | 1.0 |
| `golden-xlsx-anchor.xlsx` | `office` | 202 | **failed** | 404 | — | — | — |
| `golden-pptx-anchor.pptx` | `office` | 202 | **failed** | 404 | — | — | — |
| `golden-screenshot-ocr.png` | `image` | 202 | **failed** | 404 | — | — | — |

**四种端到端通过**（各自报告引擎身份、覆盖率 1.0、损失计数）；**三种失败**。

## 尚未采集（本轮缺陷，下一轮先做）

**三种失败作业的 `error` 文本未采集** —— 脚本只输出了 `state`。
**下一轮第一件事就是取它们各自的 `error`**，再判断是引擎缺失、依赖缺失还是格式处理未实现。

## 已确证的方法（可复用）

- **job kind = 能力前缀**（`pdf` → `pdf.extract`、`office` → `office.structure` …）；
- **引擎身份在 `jobs/:id/quality`**，不在 `capabilities`（后者是 worker 握手，自述「a job has to run…」）；
- **输出种类由 worker 写入**，非固定枚举；`quality` 给出 engine / engine_version / loss_count / coverage / pages；
- **`capabilities` 仅在声明 `text_worker` 时挂载**（否则 18 条 projections 而非 36 条）；
- **`text_worker` 的路径不得带 `\\?\` 前缀**（已修）；
- **必须用全新数据根**（Core 打不开旧 Python 库）。
