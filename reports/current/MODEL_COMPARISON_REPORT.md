# 本地模型 vs API 模型（全网）对比分析 · 2026-08-19

> 规则：本地模型负责转化/检索/问答；API 模型（DeepSeek）负责全网交叉核验。
> 无人工金标准 → 报告覆盖率/一致度/资源消耗，不称"准确率"（基线）。

## 1. 检索 bake-off（本地语义嵌入 vs 词法基线）
语料：牛津《简明逻辑学》PDF 文本层（83 块 / 40,376 字符）；固定改写查询 20 条；top-5 命中率。

| 引擎 | 命中率 | 耗时 | 说明 |
| --- | --- | --- | --- |
| **qwen3-embedding:0.6b**（本地 ollama） | **0.35** | 24.3s | 语义改写查询（"如何提高记忆力"等）能命中 |
| n-gram 字符基线（内置降级） | 0.25 | ~0s | 词法匹配，改写即失配 |

结论：**本地语义嵌入 > 词法基线**（+10pt 命中率）；改写查询判别力已在此前的真实管线复现（cos 0.605 vs 0.223）。
证据：reports/current/MODEL_COMPARISON_RECEIPT.json

## 2. ASR 双引擎一致性（本地两个 ASR 引擎互证）
样本：真实中文讲座 60s（北大学子考研分享）。

| 引擎 | 字符数 | 样例 |
| --- | --- | --- |
| SenseVoice int8（sherpa） | 242 | "…参加了二零一八年的研究生入学考试…" |
| faster-whisper large-v3-turbo | 270 | "…参加了2018年的研究生入学考试…" |

- **CER（字符级）0.141**：差异主要为中文数字 vs 阿拉伯数字（二零一八/2018）与标点，语义一致。
- 资源：SenseVoice 1.74s / faster-whisper 45s（~26x），SenseVoice 为 CPU 首选。
证据：reports/current/ASR_CROSS_ENGINE.json

## 3. OCR 双引擎一致性（本地两个 OCR 引擎互证）
| 图片 | RapidOCR | Tesseract | CER |
| --- | --- | --- | --- |
| 课程表.jpg | 441 字符 | 340 字符 | 0.857（RapidOCR 捕获更多行列） |
| obs-command-banner.png | 176 | 172 | 0.562（同内容，字符序差异） |

结论：RapidOCR 中文覆盖优于 Tesseract（TESSDATA 修复后仍受行序影响）；双引擎一致性中等，RapidOCR 为主。

## 4. API 模型（DeepSeek 全网交叉核验）
| 知识点 | 本地转化内容 | DeepSeek 全网核验 | 一致 |
| --- | --- | --- | --- |
| 费曼四步法 | 教+简化+补缺口+再讲 | 公开资料四步一致 | ✅ |
| 三段论 | 大前提+小前提→结论 | 亚里士多德逻辑标准定义一致 | ✅ |
| 记忆宫殿 | 空间位置编码 | 方法学一致 | ✅ |
| 进步本 | 记录进步/纠错反馈 | 深度学习/刻意练习原理一致 | ✅ |
| 复合增长 | 年化 50%→20 年 3325 倍 | 巴菲特复利案例一致 | ✅ |
| 刻意练习 | 目的性训练+反馈 | Ericsson 刻意练习理论一致 | ✅ |
证据：verified-knowledge/ceshi-2026-08-18/deepseek-crosscheck.md + 本轮 web_search 来源。

## 5. 视频画面转化（F8 全量）
64/64 mp4 全部成功（5-7 帧/视频，RapidOCR，gate pass）——课程画面知识（PPT/板书/案例数字）已提取。

## 6. 资源矩阵（本地模型）
| 引擎 | 模型 | 设备 | 关键指标 |
| --- | --- | --- | --- |
| 嵌入 | qwen3-embedding:0.6b | CPU | 639MB，20 查询 24s |
| 聊天 | qwen2.5vl:7b | CPU/GPU | 6GB，接地问答可用（视觉 500 待修） |
| ASR | SenseVoice int8 | CPU | 228MB，~26x 实时 |
| ASR 兜底 | faster-whisper large-v3-turbo | CPU | 1.6GB，~1.3x 实时（长音频高内存） |
| OCR | RapidOCR | CPU | ~15MB onnx，1-3s/图 |

## 7. 结论
- 本地模型全链可用；检索/ASR/OCR 均已有可量化证据；SenseVoice 与 faster-whisper 语义一致（CER 0.141）。
- API（DeepSeek）仅用于全网事实核验，6/6 知识点一致。
- 待修：ollama qwen2.5vl 视觉 HTTP 500（V4 帧描述 BLOCKED，需重启/重装 ollama）。
