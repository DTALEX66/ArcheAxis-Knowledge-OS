# AAOS-01 Q06：**17 个真实文件的格式矩阵**

样本全部来自**仓库内已跟踪的 fixture**（各有 provenance），**没有为这次探针合成任何文件**。
回执记录**实际发送的字节的哈希**。

## 逐文件实测结果

| 样本 | 产物 format | 引擎 | 结果 | 原件哈希 |
| --- | --- | --- | --- | --- |
| `note.md` | `md` | `passthrough` | carried | ✅ |
| `legacy-gbk.txt`（**非 UTF-8**） | `txt` | `passthrough` | carried | ✅ |
| `plain.txt` | `txt` | `passthrough` | carried | ✅ |
| `page.html` | `html` | **`html-adapter`** | carried | ✅ |
| `document.pdf` | `pdf` | **`markitdown`** | carried | ✅ |
| `report.docx` | `docx` | **`docx-adapter`** | carried | ✅ |
| `sheet.xlsx` | `xlsx` | **`xlsx-adapter`** | carried | ✅ |
| `slides.pptx` | `pptx` | **`pptx-adapter`** | carried | ✅ |
| `ragged.csv` | `csv` | **`markitdown`** | carried | ✅ |
| `picture.png` | — | — | **`engine_missing`（422）** | — |
| `screenshot.png` | — | — | **`engine_missing`（422）** | — |
| `board.canvas` | `canvas` | `json-canvas` | **custody_only** | ✅ |
| `learning.canvas` | `canvas` | `json-canvas` | carried | ✅ |
| `audio.wav` | — | — | **`engine_missing`（422）** | — |
| `video.mp4` | — | — | **`engine_missing`（422）** | — |
| `package.apkg`（真 ZIP） | **`unknown`** | `markitdown` | carried | ✅ |
| `mystery.unknown-ext` | **`unknown`** | `markitdown` | carried | ✅ |

**12/17 被 carried 且原件哈希一致；5 个因缺引擎被拒（422）。**

## 值得记下的四点

1. **每个家系都有真实引擎名**：`html-adapter` · `markitdown`（pdf/csv/unknown）· `docx/xlsx/pptx-adapter` · `json-canvas` · `passthrough`。**不是笼统的「支持若干格式」。**
2. **同一格式可得不同结果**：`board.canvas` 是 `custody_only`，`learning.canvas` 是 carried —— **同为 canvas、同一个 `json-canvas` 引擎，差别在内容**。
3. **产品对自己不认识的东西诚实**：`.apkg`（真 ZIP）与 `mystery.unknown-ext` 都报 **`format: unknown`**，但**仍然 carried** —— 它**不假装认识**。
4. **非 UTF-8 的文本（GBK）也能 carried**，哈希一致。

## 测试改成**规则型**，不再钉环境相关的结果

第 38/50 轮的教训：**钉「本机行为」会被 CI 驳回**。所以本次：

| 断言的 | 不再断言的 |
| --- | --- |
| 17 个样本**全部被尝试** | 具体哪些 carried / 哪些缺引擎（**取决于机器装了什么**） |
| 每条都**记录了 outcome + evidence** | reported format 等于我的猜测（产品会如实报 `unknown`） |
| **每个 200 都保留了原件哈希** | |
| **没有证据命名结构就不许叫 `structured`** | |

**结果：9 passed，6.93 秒。**

## 本轮未做

1. **未**为任何缺引擎的格式安装选装依赖（包内不鼓励为凑数装引擎）；
2. **未**改任何实现文件；
3. 官方 Green 与资料库**零触碰**；探针临时库自清理。
