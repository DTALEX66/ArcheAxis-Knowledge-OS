# AAOS-01 OCR 缺口：引擎与语言都在共享库，缺的是指向（2026-10-05）

`image/ocr` 在矩阵中失败，错误为 `AAK-WORKER-003` / `tesseract binary not found on PATH`。
逐项查证后，性质与最初判断不同。

## 事实

```
tesseract 二进制 : <EXT>\10-toolchains\scoop\apps\tesseract\5.5.0.20241111\tesseract.exe   存在
语言数据         : <EXT>\10-toolchains\scoop\apps\tesseract-languages\4.1.0\*.traineddata   存在
当前 PATH        : NOT on PATH
```

**而 `services/python-workers/vision/worker_ocr.py` 已经处理了 tessdata 的歧义**：
`_usable_tessdata()` 明确拒绝「只检查是否存在任何 `*.traineddata`」的做法，
并警告**环境里一个指向别处的 `TESSDATA_PREFIX` 会让 tesseract 失败**；
`_declared_tessdata()` 提供显式声明路径。

## 结论

**这不是「缺引擎」，是「缺指向」** —— 引擎与语言都在共享工具库中，
worker 也已稳健处理 tessdata，**唯一缺的是让候选找到二进制**。

## 修复落点（待产品选择形式）

1. **运行环境 PATH** 加上 `<EXT>\…\tesseract\<ver>`（**最小、不动代码**）；
2. **或**在候选/启动时声明 tesseract 路径（`pytesseract.tesseract_cmd` 或等价声明）；
3. **保持可选语义**：**OCR 是可选引擎**，缺失应记为「能力不可用」而不是「产品缺陷」——
   `capabilities` 的 `health` 已如实反映，失败时 `quality` 字段为 `null`，**不伪造**。

## 附：另外两个引擎的性质不同

`xlsx`（openpyxl）与 `pptx`（python-pptx）**是真缺包**：`uv.lock` 已含二者，
而所测候选 `runtime/` 早于锁（07-29 vs 10-01）⇒ **陈旧候选与漏装未判定**，已交由 CI 断言。
