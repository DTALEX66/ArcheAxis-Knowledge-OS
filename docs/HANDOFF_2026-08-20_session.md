# HANDOFF — 2026-08-20 最终交接摘要（ArcheAxis Knowledge / 星环知识平台）

> 统一基线：本地优先、证据驱动、双主体学习、可信知识治理。HEAD 见 git（本摘要提交时双端一致）。

## 一、本会话（08-19 → 08-20）完成清单

### 1. 联邦与知识 API（TP-20260819 全量）
- V1 契约 8 个 + app/federation（批量幂等提交 / Receipt / hash 回读 / 人工复核升级 / 分页 Verified 查询 / 外置资产索引 / **记录类型端点**：证据·学习·溯源·权限）
- E2E-003 HTTP 回环 + 知识迁移试点 3 对象 + CANDIDATE_ROUNDTRIP_PROOF

### 2. 管线全量测试（ceshi 22,422 文件）
- 知识格式 **100% 转化**：ajson 15071 / md 5602 / pdf 66 / docx 24 / canvas 22 / svg 30/31 / 图片 1273 / mp4 画面 64/64 / **mp3 音频 14/14（56,309 字符）**
- 修复：TESSDATA_PREFIX 根因（图片 OCR 0→1273）、faster-whisper 45GB 内存（分块 3.6GB）、分块补丁 NameError（先转写后误判失败）
- 诚实记录：.doc 2（缺转换器）、20 低文本截图（按设计）、css/js/bak 非知识排除

### 3. 模型与增强（本机 RTX 5060 / 20 核 / 64GB）
- **本地全链路可承担**（各环节实测）：嵌入 100% GPU、SenseVoice 34x（中文最快，zh-14M 实测不快于它）、faster-whisper CUDA、RapidOCR、DeepSeek 全网核验 **8/8 一致**
- onnxruntime-gpu、cairosvg（svg 管线）、magic-pdf/MinerU（依赖齐，模型下载待专项）
- Web 全链路补齐：msedge 无头截图 + E2E 3/3（摄取→提取→截图→OCR 交叉验证→转化）
- **配置最优确认**（PIPELINE_CONFIG_AUDIT.md）

### 4. 桌面发布（R5/R6）
- Tauri debug+release 构建成功（工具链确认在共用库：Rust 1.97.1+MSVC 14.44+WinSDK）
- 安装包：ArcheAxis_0.5.0 MSI + NSIS（packaging/release-0.5.0）

### 5. 闭环推进与审计
- G5 联邦记录端点 / G7 根包 archeaxis（转发层）/ G8 四库初始化 UX / G9 评估集固化
- 闭环审计（CLOSED_LOOP_AUDIT.md）：全链路逐环节 PASS，6 全链 E2E 12 passed + 后端 170+ + 前端 tsc0/vitest17/17
- git 卫生（target 3.4GB 忽略、Cargo.lock/schemas）；任务清单按新规划清理（废弃旧 v0.5.0 时代门禁）

## 二、当前状态
- **HEAD = origin/main**（双端一致，工作树干净）
- 所有转化任务已停止（用户指示），无后台作业
- 本地模型全链路可承担；DeepSeek 仅用于全网交叉核验（8/8）

## 三、待办（人工/外部门禁）
| # | 项 | 说明 |
| --- | --- | --- |
| T1 | ollama 升级 | 0.32.14 缺 /api/rerank（qwen3-reranker 接入）+ 视觉 500 上游 bug#15828（F9 V4 依赖） |
| T2 | MinerU 模型下载 | modelscope CLI 拉 opendatalab/PDF-Extract-Kit-1.0 |
| T3 | .doc 2 个 | 缺 LibreOffice/antiword |
| T4 | mp4 音轨 64 个 | 延后（--audio-only 就绪；F8 画面已覆盖） |
| T5 | R6 安装包干净机验收 | G2 |
| T6 | R7 平台连接器 | 设计后置 |

## 四、恢复/复现命令（关键）
- 音频转写（mp3）：env -u PYTHONPATH .venv/Scripts/python.exe scripts/pipeline/pipeline_audio.py --part 0 --parts 4 --audio-only（×4 worker，--part 0-3）
- 全量（含 mp4 音轨）：去掉 --audio-only
- 视频画面：scripts/pipeline/pipeline_video.py
- 评估集：scripts/pipeline/eval_retrieval.py
- 测试：env -u PYTHONPATH .venv/Scripts/python.exe -m pytest <files> -q --no-header；前端 frontend/ 下 npx tsc --noEmit + npx vitest run
- 桌面构建：vcvars64 + src-tauri 下 cargo build / npx tauri build（前端先 npm run build）

## 五、环境事实（勿忘）
- 共用库：工具链 → D:\All projects\OS External Configuration；模型 → D:\All projects\Model library；两库不上传 Git
- 引擎选型：SenseVoice（中文 ASR 首选）/ faster-whisper CUDA（多语）/ RapidOCR / qwen3-embedding（GPU）/ DeepSeek（仅全网核验）
- 报告：reports/current/（CLOSED_LOOP_AUDIT / PIPELINE_CONFIG_AUDIT / DEEPSEEK_CROSSCHECK / MODEL_COMPARISON / INGESTION_REALITY_MATRIX / AUDIO_FULL_RECEIPT 等）
