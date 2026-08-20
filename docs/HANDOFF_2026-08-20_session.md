# HANDOFF — 2026-08-20 交接摘要（会话最终版）

> 承接 08-19 会话。定位：ArcheAxis Knowledge / 星环知识平台（统一基线）。HEAD 见 git。

## 1. 已完成（均有证据）
- **联邦知识 API（TP-20260819）**：V1 契约 8 个；批量幂等提交/Receipt/hash 回读/人工复核/分页查询/外置资产索引/记录类型端点（证据/学习/溯源/权限）；E2E-003 + 迁移试点 3 对象
- **管线全量测试**：ceshi 22,422 文件知识类 100% 转化（ajson 15071/md 5602/pdf 66/mp4 画面 64/svg 30/31/图片 1273）；TESSDATA_PREFIX 根因修复；噪声过滤；RapidOCR；SenseVoice 34x；faster-whisper CUDA；ASR 双引擎 CER 0.141；DeepSeek 全网 6/6
- **Web 全链路**：raw-first 摄取 + msedge 无头截图 + 全链路 E2E 3/3（摄取→提取→截图→OCR 交叉验证→转化）
- **桌面发布**：R5 Tauri debug+release 构建（工具链在共用库）+ R6 MSI/NSIS 安装包（packaging/release-0.5.0）
- **闭环推进**：G5 联邦记录端点 / G7 根包 archeaxis / G8 四库初始化 UX / G9 评估集固化
- **审计**：PIPELINE_CONFIG_AUDIT（配置对本机最优：嵌入 100% GPU、ASR/OCR CPU 最优、20 核并行）；gitignore target 3.4GB；任务清单按新规划清理

## 2. 进行中
- **F1 音频转写（mp3 优先 14 个）**：4 worker 运行中（--audio-only）；完成合并回执后，此摘要即为最终交接
- mp4 音轨：延后（与 F8 画面内容重叠，需数小时）

## 3. 待办（外部/人工/专项）
| # | 项 | 说明 |
| --- | --- | --- |
| T1 | ollama 升级 | 0.32.14 缺 /api/rerank + 视觉 500 上游 bug#15828 |
| T2 | MinerU 模型下载 | modelscope CLI 拉 opendatalab/PDF-Extract-Kit-1.0 |
| T3 | .doc 2 个 | 缺 LibreOffice/antiword |
| T4 | R6 安装包干净机器验收 | G2 |
| T5 | mp4 音轨转写（64 个） | 延后项 |
| T6 | R7 平台连接器 | 设计后置 |

## 4. 环境事实（勿忘）
- 共用库：工具链→OS External Configuration；模型→Model library；两库不上传
- 本机：RTX 5060 8GB / 20 核 / 64GB；Rust 1.97.1+MSVC 14.44+WinSDK 在共用库
- 引擎：SenseVoice（中文 ASR 首选）、faster-whisper CUDA（多语）、RapidOCR、qwen3-embedding（100% GPU）
- 脚本：scripts/pipeline/{pipeline_audio(--part/--parts/--audio-only), pipeline_video, eval_retrieval}
