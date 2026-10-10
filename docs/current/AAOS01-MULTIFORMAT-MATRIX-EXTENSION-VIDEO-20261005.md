# AAOS-01 多格式矩阵 · 扩展（视频）（2026-10-05）

在同一权威候选上补跑视频夹具，并复现文本与 HTML 作为对照。

| 夹具 | kind | 终态 | outputs/text | quality.engine | loss | coverage |
| --- | --- | --- | --- | --- | --- | --- |
| `golden-video-anchor.mp4` | `media` | **succeeded** | 200 | `python-worker-media` | 1 | 1.0 |
| `golden-text-anchor.txt` | `text` | succeeded | 200 | `python-worker-text` | 0 | 1.0 |
| `golden-web-anchor.html` | `html` | succeeded | 200 | `python-worker-html` | 1 | 1.0 |

## 累计（同一候选，端到端）

**通过 5 种**：`text` · `office/docx` · `html` · `media/wav` · `media/mp4`；
**失败 3 种**：`office/xlsx`（openpyxl 未装）· `office/pptx`（python-pptx 未装）· `image/png`（tesseract 二进制不在 PATH）。

**三种失败的定性仍未判定**：锁里已有 `openpyxl`/`python-pptx`，而所测候选的 `runtime/` 早于锁（07-29 vs 10-01）⇒
**陈旧候选与流水线漏装皆未排除**。判定需全新暂存，已交由 CI 断言（**该轮结论未出**）。

**未覆盖**：`canvas.structure` · `archive.inventory` · `subtitles.structure` —— **金样本集中无对应夹具**，需另行准备样本后才能实测。
