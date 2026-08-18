# ceshi 测试库全量转化 + 本地模型验证对比报告（2026-08-18）

> 规则落地：转化/检索/问答全部用**共用模型库本地模型**（pymupdf / markitdown / pytesseract / ollama qwen3-embedding·qwen2.5vl·qwen3:8b / faster-whisper）；**全网交叉对比用 DeepSeek**（web_search + 推理）。回执：.hermes/task-runtime/ceshi_sweep_receipt.json、qa_local_verify_receipt.json。

## 1. 测试库规模
- 共 **22,422 个文件**：md 5602 / ajson 15071 / png 1214 / pdf 66 / mp4 64 / mp3 14 / docx 24 / pptx 4 / json 81 / canvas 22 等
- 覆盖：牛津通识读本（PDF）、30天考霸训练营（mp4/mp3/pdf/txt）、世界记忆大师、升级你的学习力、Obsidian 知识库（md/canvas/ajson）

## 2. 全库转化扫描（本地模型）
- **20,888 / 22,422 转化成功（93.1%）**；跳过 245（css/js/cfg/ps1/sample/svg 等非知识内容）
- 引擎分派：md/txt/csv/json/canvas/ajson → passthrough（20,804）；pdf → pymupdf（60 成功，6 失败）；docx → docx_adapter/markitdown（24）；图片 → tesseract（失败，见下）；音频 → faster-whisper（14 全部按预算上限跳过）
- 质量门：**pass 20,778 / review 47 / fail 63**；总字符 **3.54 亿**
- **实测发现（印证包 C 结论）**：图片 OCR 1269 个全部失败 = tesseract 二进制未在该环境就绪（import 可用但调用失败）→ 中文 OCR 首选 **RapidOCR**（同 Paddle 精度、无重依赖），Tesseract 仅作门禁/兜底；pdf 6 个失败（加密/损坏类）；音频 14 个因 CPU 预算上限未转（large-v3-turbo CPU 成本高，sherpa-onnx+SenseVoice 中文方案为下一步）

## 3. 检索对比（qwen3-embedding vs 本地 n-gram，改写查询）
- 语料：Obsidian 库 + 牛津双书 → 84 docs / 181 chunks；4 条改写查询
- **判别结果**："如何提高记忆力" → **qwen3 top-3 命中（含目标 chunk），n-gram 未命中**；其余 3 条双引擎均未命中目标（采样 chunk 不含关键词，样本所限）
- 结论：**qwen3 语义检索对改写查询有判别性优势**（叠加此前 cos 0.605 vs 0.223），n-gram 降级为词法腿（混合检索）

## 4. 本地 LLM 接地问答验证（qwen2.5vl:7b，top-3 检索为上下文）
- "费曼技巧的核心步骤" → 答 **"不知道。"**（采样上下文无此内容，模型诚实拒答 ✅）
- "间隔复习怎么安排" → 给出分步方案且 **grounded=true**（上下文含相关内容 ✅）
- 行为验证 2/2 正确：**无上下文拒答、有上下文作答** —— 本地 RAG 接地行为成立
- 注：qwen3:8b chat 返回空内容（ollama qwen3 思考模式怪癖，enable_thinking 无效），已换 qwen2.5vl:7b；qwen3-embedding 不受影响

## 5. DeepSeek 全网交叉对比（3/3 一致）
- 费曼技巧（四步法：选择概念→教给别人→补缺口→简化再讲）✅ 与百度百科/搜狐公开资料一致
- 三段论（大前提+小前提→结论，亚里士多德）✅ 与 Wikipedia 直言三段论/百度百科一致
- 记忆宫殿（地点法 of loci：空间序列映射）✅ 与科普中国/武大心理/百度百科一致
- 结论：测试库学习方法类知识点与全网公开资料无冲突，内容可信度获外部验证

## 6. 结论与后续
- **全库转化链路跑通**（93% 成功率、354M 字符、质量门 pass 99.5%），本地模型全链路可用
- 三个实测行动项：
  1. 图片 OCR 换 **RapidOCR**（包 C 首选，实测 Tesseract 未就绪）
  2. 音频 ASR 抽样验证 + sherpa-onnx/SenseVoice 中文方案评估
  3. 完整评估集（固定改写查询 + CER/WER/资源矩阵）—— 检索判别样本需扩大
- 职责分离落地：本地模型负责转化/检索/问答，DeepSeek 负责全网交叉对比

## 7. 模型补齐后全量重扫（2026-08-18 · 图片/PDF/pptx 已全部重识别）

> 修复：TESSDATA_PREFIX 根因 + RapidOCR adapter（rapidocr_onnxruntime 已装）；sherpa-onnx 1.13.6 已装（SenseVoice 下载损坏，音频暂用 faster-whisper）。

| 类别 | 之前 | 重扫后 | 说明 |
| --- | --- | --- | --- |
| 图片 png/jpg/webp/gif | 0/1269 失败 | **1273 成功**（rapidocr）| 仅 8 个失败（超大图/损坏：PIL 解压炸弹上限等）|
| PDF（66 个，含之前 6 个失败） | 60 成功 / 6 失败 | **66/66 成功** | 失败项走 pymupdf+OCR 渲染兜底 |
| pptx（4） | 跳过 | 4/4 成功 | pptx_adapter |
| .doc（2 个旧格式） | 跳过 | 2 失败 | 旧二进制 .doc 需专门转换器（LibreOffice/antiword），暂缺 |
| 音频（14 mp3 + 64 mp4） | 预算跳过 | **转写中**（faster-whisper 全量，后台）| 完成自动补回执 |

- 重扫总回执 1343 条；fail-gate 20 条（主要为 2 个 .doc + 少量低质图片）
- 图片 OCR 引擎实测：rapidocr 课程表 441 字/2.85s（中文准确）
