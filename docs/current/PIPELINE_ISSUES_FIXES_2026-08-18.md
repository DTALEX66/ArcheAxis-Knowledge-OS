# 转化管线全链路问题总结 · 修复 · 增强（2026-08-18）

## 一、管线全链路遇到的问题（实测）

| # | 问题 | 表现 | 根因 |
| --- | --- | --- | --- |
| 1 | **干扰项污染知识**（用户重点） | PDF 提取含页眉（书名/章节名）、页脚页码、ISBN/版权/印刷行、水印 | 文本层直接拼接，未过滤运行页眉页脚与样板行 |
| 2 | 图片 OCR 全失败 | ceshi 1269 张图片转化失败 | tesseract 二进制未就绪（import 可用但调用失败） |
| 3 | 6 个 PDF 转化失败 | 无文本输出 | 加密/损坏/纯扫描无文本层且 OCR 兜底缺失 |
| 4 | 音频 ASR 受限 | 14 个 mp3 按预算跳过 | large-v3-turbo CPU 成本高（每文件可达数十分钟） |
| 5 | 空/过短文件 | Day01.txt 等 0KB → gate fail | 课程目录占位文件 |
| 6 | ECL 规则抽取对学术文本为 0 | 牛津书实体/关系 0 条 | 规则模式面向技术文本（支持/依赖/属于），学术散文不匹配 |
| 7 | 检索判别样本不足 | 改写查询 6 条仅 2 条命中目标 | 取样页在版权/序言区，关键词在正文后部 |
| 8 | qwen3:8b chat 空内容 | 问答返回空串（done_reason=length） | ollama qwen3 思考模式怪癖（enable_thinking 无效），换 qwen2.5vl:7b 正常 |
| 9 | 目录重复 | 30天考霸课程目录嵌套重复（拷贝两次） | 源数据本身重复 |
| 10 | 全库 354M 字符无结构 | ajson 15071 个占大头 | Obsidian copilot JSON 附件，内容杂 |

## 二、已修复 / 已增强（本轮）

| 修复/增强 | 落点 | 验证 |
| --- | --- | --- |
| **干扰项过滤器（页眉/页脚/页码/水印/版权行）** | app/ingestion/content_cleaner.py：split_pages → repeated_lines（跨页运行页眉/页脚检测）→ clean_page（页码/第N页/ISBN/版次印刷/版权/水印/纯数字行）→ clean_text + noise_report 审计 | 7 测试 + 真实牛津 PDF 演示（检测"本章要点"/"【注释】"运行页眉，每书去噪 138-205 字符） |
| OCR 选型结论 | 包 C 结论落地为行动项：RapidOCR 接入（同 Paddle 精度、无重依赖） | 实测 Tesseract 未就绪印证 |
| ASR 选型结论 | sherpa-onnx + SenseVoice 中文首选（CPU 友好） | 预算上限实证 large-v3 CPU 成本 |
| 接地问答行为 | 本地 LLM 无上下文拒答 / 有上下文作答（2/2 正确） | qwen2.5vl:7b 实测 |
| 语义检索判别 | qwen3-embedding 改写查询命中、n-gram 未命中 | 判别查询"如何提高记忆力" |
| 可复现工具 | verified-knowledge/ceshi-2026-08-18/scripts/（含噪声过滤） | 归档 |

## 三、下一步增强（待办）
1. **RapidOCR 接入**（替换/并列 tesseract）：图片与扫描 PDF 的 OCR 主引擎
2. **ASR 抽样验证**：sherpa-onnx+SenseVoice 在 2-3 个 mp3 上实测
3. **噪声过滤器进主流程**：multi_format.convert_url / convert_pdf 默认套 clean_text（当前独立模块 + 归档脚本使用）
4. **完整评估集**：固定改写查询 + CER/WER/资源矩阵（扩大检索判别样本）
5. **ECL 升级**：ontology 约束已就绪，接入 LLM 抽取（qwen2.5vl 或 DeepSeek 仅对比时）提升学术文本实体召回

## 四、关键原则
- **转化的是真实知识，不是版面**：干扰项（页眉页脚/水印/版权行/页码）必须剥离后再入库
- 去噪是确定性的（规则+跨页统计），不依赖 LLM；LLM 只做语义层（检索/问答/对比）
- 证据驱动：每步有回执（receipts/），可复现可审计
