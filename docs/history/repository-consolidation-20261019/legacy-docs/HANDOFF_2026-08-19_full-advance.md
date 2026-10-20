# HANDOFF — 2026-08-19/20 全量推进与管线增强（会话总结）

> 承接 08-18 会话（调研/吸收/验证）。本会话：联邦任务包全量执行 + 管线全量测试 + 模型/引擎增强 + 完整性审计 + 桌面发布。

## 1. 已达成（全部有证据）

### 联邦与知识 API（TP-20260819）
- 联邦 V1 契约（8 个）+ app/federation（批量幂等提交/Receipt/hash 回读/人工复核升级/分页 Verified 查询/外置资产索引）7 路由
- E2E-003 HTTP 回环 + 知识迁移试点（3 对象）→ CANDIDATE_ROUNDTRIP_PROOF
- SYSTEM_BOUNDARY 重生成对齐 HEAD；reports/current 交付齐全（CLOUD_BASELINE/EXACT_SHA/CONTRACT_CONFORMANCE/REMAINING_HUMAN_GATES/INGESTION_REALITY_MATRIX/FEDERATION_MIGRATION_REPORT）

### 管线全量测试（ceshi 22,422 文件）
- 文本/PDF/Office/图片/svg/视频画面：**知识类 100% 转化**（ajson 15071/md 5602/pdf 66/mp4 64/svg 30/31…）
- F8 视频 64/64；F9 V1 场景切分+V3 字幕；F1 音频（SenseVoice 4 worker 并行，分块转写修 50GB 内存失控）
- 修复：TESSDATA_PREFIX 根因（图片 OCR 0→1273）、faster-whisper 长音频内存（45GB→3.6GB 分块）
- 诚实记录：.doc 2 FAIL（缺转换器）；20 低文本截图按设计 gate-fail；css/js/bak 等非知识正确排除

### 模型与增强（本机：RTX 5060 8GB / 20 核 / 64GB）
- faster-whisper CUDA 打通（nvidia-cublas/cudnn 包）；onnxruntime-gpu 1.29（CUDA+TensorRT）
- SenseVoice int8 中文最快（34x 实时）；ASR 双引擎 CER 0.141；检索 qwen3-embedding 0.35 vs n-gram 0.25
- DeepSeek 全网交叉核验 6/6 一致；MinerU(magic-pdf) 依赖齐（模型下载+venv 隔离待专项）
- R5/R6：Tauri debug+release 构建成功（工具链在共用库 Rust 1.97.1+MSVC 14.44+WinSDK）；安装包 MSI+NSIS → packaging/release-0.5.0

### 测试与卫生
- 后端回归 + 前端 tsc 0 + vitest 17/17；gitignore 修复（target 3.4GB 忽略）；Cargo.lock/schemas 提交

## 2. 待办（人工门禁/专项）
| # | 项 | 说明 |
| --- | --- | --- |
| T1 | ollama 升级 | 0.32.14 缺 /api/rerank（qwen3-reranker 接入）+ 视觉 500 上游 bug#15828；升级会重启服务 |
| T2 | MinerU 模型下载 | magic-pdf 依赖齐；需干净 venv 隔离 + 模型（Model library/mineru-models） |
| T3 | .doc 2 个 | 需 LibreOffice/antiword（scoop 无 manifest，网络限） |
| T4 | R6 安装包验收 | 干净机器 + 升级保留验证（G2） |
| T5 | 前端 Library/Evidence/AI Assets 空间走查 | 已接真实 API，人工验收 |

## 3. 环境事实
- 共用库规则：工具链→OS External Configuration；模型→Model library；两库不上传
- F1 音频：scripts/pipeline/pipeline_audio.py --part i --parts 4；回执 audio_full_receipt.json.partN
- 视频/增强：pipeline_video.py；对比报告 reports/current/MODEL_COMPARISON_REPORT.md
