# 管线配置最优审计（PIPELINE_CONFIG_AUDIT）· 2026-08-20

> 对照本机：RTX 5060 8GB / 20 核 CPU / 64GB RAM。逐环节核对是否最佳/最强/最优配置。

## 1. 配置最优确认（实测/审计）

| 环节 | 当前配置 | 判定 | 证据 |
| --- | --- | --- | --- |
| 嵌入检索 | qwen3-embedding:0.6b，**100% GPU**（RTX 5060） | ✅ 最优 | ollama ps 实测 GPU 100% |
| ASR 中文 | SenseVoice int8 CPU（34x 实时） | ✅ 最优 | 60s→1.74s；GPU fw 仅 10.5x（中文慢 3 倍） |
| ASR 多语 | faster-whisper CUDA（10.5x） | ✅ 已备 | nvidia-cublas/cudnn 包 + device=cuda |
| OCR | RapidOCR CPU（onnxruntime-gpu 已装） | ✅ 最优 | GPU/CPU 实测相当（22.7 vs 25.4s，小模型无增益） |
| 并行度 | 4-8 worker 吃满 20 核 | ✅ 最优 | F1 4 worker（内存有界 3.6GB/worker） |
| 内存 | 64GB 预算（worker 3.6GB×8 + ollama 2.4GB） | ✅ 充足 | free 35GB+ |
| 视频 | 抽帧 RapidOCR + PySceneDetect | ✅ 已配 | F8 64/64 |
| 桌面 | Tauri MSI+NSIS（release 7.9MB） | ✅ 已配 | R5/R6 完成 |

**结论：现有配置已适配本机为最优**（GPU 用于嵌入这类值得的模型；ASR/OCR 小模型 CPU 更快；20 核并行）。

## 2. 全链路缺口审计 → 本轮补齐

| 环节 | 之前 | 本轮 |
| --- | --- | --- |
| Web 摄取 | ✅ raw-first capture_web | — |
| Web 提取 | ✅ convert_url 链 | — |
| **Web 截图** | ❌ 缺 | ✅ app/ingestion/web_screenshot.py（msedge 无头，零依赖） |
| **Web 全链路 E2E** | ❌ 缺 | ✅ integration-tests/test_web_full_chain_e2e.py 3/3（摄取→提取→截图→OCR→交叉验证→转化） |
| Web 上传/转化 | ✅ /ingest + convert_url | — |
| Web 验证对比 | ✅ DeepSeek 全网核验 | — |

## 3. 多格式完整性（更新）
- 本地文件：知识格式 100%（文本/PDF/Office/svg/图片/视频画面/音频 F1 进行中）
- **网页：全链路现已完整**（摄取→原文保全→提取→截图→OCR 交叉验证→上传→转化→验证）

## 4. 剩余（外部/人工）
- G2 ollama 升级、G4 .doc 转换器、G6 V4（上游 bug）、G12 R7 平台连接器（设计后置）
