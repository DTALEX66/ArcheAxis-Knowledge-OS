# AAOS-01 多格式：三种失败已定性 —— 缺失的引擎（2026-10-05）

上一轮矩阵的三种失败，其 `job.error` 已采集。**失败原因全部是引擎可用性，不是代码路径。**

## 证据（`job.error` 内嵌 worker 的结构化响应）

| 夹具 | kind | code | message |
| --- | --- | --- | --- |
| `golden-xlsx-anchor.xlsx` | office | `AAK-WORKER-003` | **xlsx engine missing (openpyxl not installed)** |
| `golden-pptx-anchor.pptx` | office | `AAK-WORKER-003` | **pptx engine missing (python-pptx not installed)** |
| `golden-screenshot-ocr.png` | image | `AAK-WORKER-003` | **tesseract binary not found on PATH (OCR engine unavailable)** |

## 定性

- **worker 与管线正确**：每个失败都以同一稳定错误码精确点名缺失引擎；
- **候选缺依赖**：`openpyxl`、`python-pptx` 未随暂存安装；`tesseract` 二进制不在候选内；
- **失败报告诚实**：失败时 `quality` 的 `coverage`/`engine`/`pages` 均为 `null`，**不伪造**；
- **`job.error` 保留完整结构化响应**，可直接诊断。

## 修复落点（「该迁移的迁移」的直接体现）

1. **`openpyxl`、`python-pptx`**：加入被声明并暂存的 Python 依赖集
   （与已在暂存器修过的两处同类问题一致：按角色判名、按 RECORD 复制）；
2. **`tesseract` 二进制**：要么随候选暂存，要么**明确记为可选引擎**
   （`AGENTS.md` §7 已注明扫描件 PDF 需 OCR 且需设 `TESSDATA_PREFIX`）；
3. **修完后重跑同一矩阵**，把 4/7 提升。

## 已通过（无需改动）

`text` · `office/docx` · `html` · `media/wav` —— 端到端通过，各自报告引擎、覆盖率 1.0 与损失计数。
