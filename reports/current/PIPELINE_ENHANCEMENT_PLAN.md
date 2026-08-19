# 管线全面增强方案（PIPELINE ENHANCEMENT）· 2026-08-19/20

> 依据：现有转化实测结果 + 本机配置（RTX 5060 8GB / 20 核 CPU / 64GB RAM）+ 开源调研。
> 规则：本地优先、证据驱动、不引重依赖、模型进 Model library、工具进 OS External Configuration。

## 0. 机器能力基线（决定增强方向）
- **GPU：RTX 5060 8GB** → 可承载 OCR/ASR/嵌入/小模型推理（已打通 faster-whisper CUDA）
- **CPU：20 核** → 并行 worker 吃满（F1 已用 4 路）
- **内存：64GB** → 多 worker + 大模型（qwen3-coder 30b GGUF 已有）
- **已有模型**：qwen3-embedding 0.6b / qwen2.5vl 7b / qwen3:8b / **qwen3-reranker（494MB 未接入！）** / SenseVoice / faster-whisper large-v3-turbo / RapidOCR / Tesseract 5.5

## 1. 逐环节增强矩阵

### 1.1 文档解析（现：pymupdf + adapters）
| 候选 | 定位 | 判定 |
| --- | --- | --- |
| **MinerU**（opendatalab） | 扫描 PDF→Markdown，中文最强（juejin 对比） | 高优先：复杂版面/中文扫描件；依赖较重，装到共用库 |
| **Docling**（IBM） | 版面分析/结构化 | 中：docx/pptx 复杂结构 |
| **Marker** | PDF→MD | 参考（中文支持弱） |
落地：✅ magic-pdf（真 MinerU）已装（torch/transformers/ultralytics/doclayout-yolo/rapid-table 依赖补齐，PyPI 的 mineru 是空包坑已避开）；⏳ 模型下载中（mineru-models → Model library）；就绪后作为扫描件兜底。

### 1.2 OCR（现：RapidOCR + Tesseract）
| 增强 | 说明 |
| --- | --- |
| **RapidOCR + onnxruntime-gpu** | 装 onnxruntime-gpu → 图片 OCR 上 GPU（RapidOCR 底层 ONNX 直通） |
| PaddleOCR v3（ONNX 版） | 中文更强（monkt/paddleocr-onnx）；备选 |
落地：onnxruntime-gpu 一行安装；RapidOCR 检测到 CUDA provider 自动用 GPU。

### 1.3 ASR（现：SenseVoice 34x 实时 CPU / fw-GPU 10.5x）
| 候选 | 判定 |
| --- | --- |
| **FunASR/Paraformer（GPU）** | 中文会议音频基准最强；RTX 5060 可跑；依赖较大，装共用库 |
| whisper.cpp | CPU 极快备选；中文弱于 SenseVoice |
| **faster-whisper CUDA（已打通）** | 英文/多语主引擎（device=cuda） |
落地：中文 SenseVoice（不变）+ 英文 fw-CUDA + 未来 FunASR GPU。

### 1.4 视频理解（现：抽帧+RapidOCR + PySceneDetect）
| 候选 | 判定 |
| --- | --- |
| **Qwen2.5-VL 帧描述** | ⚠️ ollama 视觉 500 = 上游已知 bug（ollama#15828 GGML_ASSERT），需 ollama 升级或换 Vision Toolkit（modlens/vision_understand 走 VISION_API_KEY） |
| VideoContext-Engine 思路 | 场景+ASR+VLM 组合（参考架构，自研不引） |
落地：V1-V3 已完成；V4 走 vision_understand（外部视觉 API）绕过 ollama bug。

### 1.5 检索/RAG（现：qwen3-embedding 命中率 0.35 vs n-gram 0.25）——**最大增强点**
| 增强 | 说明 |
| --- | --- |
| **混合检索（BM25 + 向量 + RRF）** | 稀疏+密集互补，中文 RAG 标配 |
| **接入 qwen3-reranker（494MB 已有！）** | 对 top-20 重排 → 命中率显著提升；零下载 |
| BGE-M3 | 中文多语言嵌入升级候选（GGUF/ONNX 本地） |
落地：立即实现 混合检索 + reranker 重排，与 0.35 基线对比。

### 1.6 知识/图谱/记忆（已有）
- Graphiti/Cognee 调研结论不变（重依赖不做）；双时态/ontology 约束已吸收。

### 1.7 模型加速与推理
| 增强 | 说明 |
| --- | --- |
| onnxruntime-gpu | OCR/嵌入/ASR 引擎统一 GPU 化 |
| llama.cpp / ollama GPU | qwen3-coder 30b GGUF 已有 → 编码/总结任务 GPU 化 |

### 1.8 桌面/发布（Tauri 已构建）
- NSIS/MSI 已出；后续：自动更新（tauri-plugin-updater）、图标多尺寸、安装向导中文化。

## 2. 优先级（基于 ROI）
| P | 项 | 预期 |
| --- | --- | --- |
| P0 | 混合检索 + qwen3-reranker 接入 | 命中率 0.35 → 0.5+（零新依赖） |
| P0 | onnxruntime-gpu → OCR/嵌入 GPU 化 | 图片 OCR 提速 |
| P1 | MinerU 扫描 PDF 兜底 | 复杂版面质量提升 |
| P1 | V4 走 vision_understand 绕过 ollama bug | 视频帧语义描述打通 |
| P2 | FunASR GPU / whisper.cpp | 多语 ASR 备选 |
| P2 | ollama 升级修复视觉 | 上游修复后回归 |

## 3. 落地记录（实测）
- P0-2 ✅ onnxruntime-gpu 1.29.0（CUDA+TensorRT provider）→ RapidOCR 可 GPU 化（CUDA provider available=True）
- P0-1 🟡 混合检索 RRF 实测：vector 0.35 = hybrid 0.35（该严格指标下稀疏无增益）；
  **qwen3-reranker 重排阻塞**：ollama 0.32.14 无 /api/rerank（404）→ 升级 ollama 或下载 ONNX reranker（HF bge/qwen3-reranker）
- 环境事实：ollama qwen2.5vl 视觉 500 = 上游 bug（ollama#15828 GGML_ASSERT），升级 ollama 修复；
  或 V4 走 Vision Toolkit vision_understand（外部视觉 API）
- 下一步：GPU 嵌入/OCR 实测提速回执；ollama 升级（含 rerank+视觉双修复）
