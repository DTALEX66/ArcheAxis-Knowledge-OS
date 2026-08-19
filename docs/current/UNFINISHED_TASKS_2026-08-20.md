# 未完成任务清单（2026-08-20 更新 · 按统一基线清理）

> 基准：ArcheAxis Knowledge 统一基线（2026-08-19，本地优先/证据驱动/双主体学习/可信知识治理）。
> 清理原则：过时（旧命名/旧 v0.5.0 时代验收/已被新规划取代）→ 移入废弃区；真实缺口保留；已完成标记。
> 状态词：PASS / PARTIAL / FAIL / NOT_EXECUTED / BLOCKED。

## 一、真实缺口（保留，符合新规划）

| # | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| G1 | **音频全量转写**（14 mp3 等音频） | 🔄 进行中 | F1：SenseVoice 4 worker 并行分块转写；完成自动合并回执 |
| G2 | **ollama 升级**（解 qwen3-reranker 接入 + 视觉 500 上游 bug#15828） | BLOCKED | 升级重启服务需避开其他会话；0.32.14 无 /api/rerank |
| G3 | **MinerU 扫描 PDF 兜底** | PARTIAL | magic-pdf 依赖齐+venv 隔离已解（PYTHONPATH='' 干净）；模型下载需 modelscope CLI（opendatalab/PDF-Extract-Kit-1.0）→ 专项 |
| G4 | **.doc 旧格式 2 个** | FAIL | 需 LibreOffice/antiword（共用库无） |
| G5 | **联邦契约实现**（EvidenceIntake/LearningRecord/Provenance/Rights V1） | ✅ 完成 | 4 记录类型端点+表+测试（10 联邦测试绿） |
| G6 | **F9 视频增强 V4/V5**（VLM 帧描述 / 时间戳知识块） | PARTIAL | V1 场景切分+V2 帧OCR+V3 字幕完成；V4 被 ollama 视觉阻塞 |
| G7 | **Python 根包 archeaxis** | ✅ 转发层 | archeaxis/ 包别名（archeaxis.app.main 可用）+ 测试；全量重命名留续项 |
| G8 | **R1 四库首启 UX** | ✅ 基础 | Settings 空间"初始化四库工作区"按钮（POST initialize）真实接线 |
| G9 | **完整评估集固化** | ✅ | scripts/pipeline/eval_retrieval.py（20 固定查询）+ EVAL_SET_RECEIPT.json |
| G10 | **C2 Web 捕获余项**（PolicyGate 统一/DAG 收尾） | PARTIAL | web.py stub 已消灭；其余 DAG 待跑 |
| G11 | **ENV-103 环境确认**（rust/uv-cache/wsl2/ci-venv） | NOT_EXECUTED | 环境/注册表确认 |
| G12 | **R7 平台采集**（微信/抖音/B站等） | NOT_EXECUTED | 设计后置（核心闭环后） |

## 二、已完成（本会话/近期，标记确认）

- 知识格式 100% 转化（ajson/md/pdf/mp4 画面/docx/canvas/svg 30/31/json/txt/csv/pptx/html/gif）
- TESSDATA_PREFIX 根因修复（图片 OCR 0→1273）；噪声过滤器；RapidOCR adapter
- SenseVoice 快引擎（34x）+ faster-whisper CUDA + ASR 双引擎 CER 0.141
- 联邦知识 API（幂等提交/Receipt/hash 回读/人工复核/分页查询）+ E2E-003 + 迁移试点
- R5 Tauri 构建（debug+release）+ R6 安装包（MSI+NSIS）→ packaging/release-0.5.0
- 对比报告（检索 0.35 vs 0.25；DeepSeek 全网 6/6 一致）；reports/current 交付齐全
- git 卫生（target 忽略/Cargo.lock/schemas/根包名 pyproject 已对齐）

## 三、废弃区（过时/不符合新规划，不再作为任务）

| # | 原项 | 废弃原因 |
| --- | --- | --- |
| X1 | B3-B8 Owner 门禁（H1-H4 EXIT 双循环、AXW-045/055/012C/095/097/060 验收、AXW-096A 大库验收、AXC-060 RC 档案） | v0.5.0/Cognitive-Loop-OS 时代验收编号，命名契约已锁定新身份；统一基线判定旧 release 资产为历史基线，不再适用 |
| X2 | B1 "RC v0.6.0 三包发布"（旧 release.yml 8 资产链） | 基于旧发布链审计；新规划 R6 以新身份（ArcheAxis 0.5.0 已出 MSI/NSIS）重新走发布 |
| X3 | F3 "8 张超大/损坏图片" | 已澄清真相：20 低文本截图按设计 gate-fail，非超大图问题 |
| X4 | E3 "MinerU/PaddleOCR/Docling 深度解析 bake-off（C 级后置）" | 本会话已推进 MinerU（magic-pdf 装好，转 G3 收尾） |
| X5 | E4 "Paperless AI Research Brain（查无此名）" | 同名项目不存在，目标已由 E5 方向替代 |
| X6 | 旧命名残留（Cognitive-Loop-OS 时代任务引用） | 命名契约：旧名仅历史，不再作为活动任务 |
| X7 | "F1: 14 mp3 + 64 mp4 全转写" 旧描述 | 64 mp4 画面已由 F8 完成（64/64）；F1 仅剩音频（G1） |

## 四、人工门禁（保留，需 Owner）
- R6 安装包干净机器验收（G2）；前端六空间人工走查（T5）；大库真实数据验收（新规划 R3 后）
