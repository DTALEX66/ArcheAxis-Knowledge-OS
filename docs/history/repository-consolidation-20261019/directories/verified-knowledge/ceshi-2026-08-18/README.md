# ceshi 测试库验证对比知识归档（2026-08-18）

> 本目录保留 D:\All projects\ceshi（测试库）经**共用模型库本地模型**全量转化 + 验证对比的知识资产。
> 职责分离：转化/检索/问答 = 本地模型（pymupdf / markitdown / pytesseract / ollama qwen3-embedding·qwen2.5vl / faster-whisper）；**全网交叉对比 = DeepSeek**。

## 目录
- full-conversion-report.md — 全量转化验证对比报告（22,422 文件 → 20,888 转化 93.1%，3.54 亿字符）
- deepseek-crosscheck.md — DeepSeek 全网交叉对比（费曼技巧 / 三段论 / 记忆宫殿，3/3 与公开资料一致）
- receipts/ — 5 份机器回执（转化扫描 / 本地问答 / 检索命中率 / 判别指标 / 真实管线）
- scripts/ — 可复现脚本（全库扫描、QA 本地验证）

## 关键结论
1. 全库转化链路跑通：文本类 20,804 + PDF 60 + DOCX 24 成功；质量门 pass 99.5%
2. 图片 OCR 实测 Tesseract 未就绪 → 中文 OCR 首选 **RapidOCR**（包 C 结论实证）
3. 音频 ASR 受 CPU 预算限制（large-v3-turbo），sherpa-onnx+SenseVoice 为下一步
4. 检索判别：**qwen3-embedding 改写查询命中、n-gram 未命中**（语义优势实证）
5. 本地 LLM 接地问答行为 2/2 正确（无上下文拒答 / 有上下文作答）
6. DeepSeek 全网交叉对比 3/3 一致（测试库学习方法类知识可信）

## 边界
- **ceshi 原文内容不提交**（3.54 亿字符留在测试库本体）；本目录只保留**元数据回执 + 报告 + 可复现脚本**
- 回执中的文件路径为本地绝对路径，仅作溯源，不视为外部可访问地址
- 复现：`venv python scripts/ceshi_sweep.py`（需 tesseract/ollama 就绪，音频/图片按脚本内预算执行）
