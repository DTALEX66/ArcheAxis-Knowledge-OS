# AXR-060-202 Tier A 固定格式结构矩阵交接（2026-08-24）

## 本次代码级闭环

- 新增固定 fixture 的结构写入/读回矩阵：受版本控制的 DOCX、PPTX、XLSX、HTML
  与真实 PDF 都必须经过对应转换路径，持久化为 `ConversionRun` 后再读取。
- Office 断言各自的原生锚点：DOCX 的 Markdown 源片段、PPTX 的 slide number、
  XLSX 的 sheet/A1 坐标；HTML 保留 `main-content`，PDF 保留页号。
- 修复 XLSX 公式序列化：openpyxl 提供的 `=SUM(...)` 不再被二次加前缀而变成
  `==SUM(...)`。固定工作簿 fixture 明确保护该行为。

## 本地验证

```text
tests/test_tier_a_fixture_matrix.py                         2 passed
tests/test_axw023a_docx_adapter.py
tests/test_axw023b_f_adapters.py
tests/test_pdf_extraction.py
tests/test_conversion_run.py                                23 passed
ruff check app/ingestion/xlsx_adapter.py tests/...          PASS
```

## 证据边界

这是 `IMPLEMENTED_LOCAL` / `TESTED_LOCAL` 的固定 fixture 结构覆盖，不是
“所有格式已安装态资格”。它不覆盖 OCR/媒体的真实引擎输出、十万行以上工作簿、
读屏/高 DPI、nightly 完整格式矩阵，或干净 Windows 安装包中的格式链路。
这些项目仍必须在下一次汇集候选的 Full Qualification 与独立人工/设备 receipt 中
分别记录，不能用本矩阵升级为 `INSTALLED_RUNTIME_VERIFIED`。
