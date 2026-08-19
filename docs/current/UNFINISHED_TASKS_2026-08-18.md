# 未完成任务清单（2026-08-18 整理）

> 来源：HERMES_HANDOFF.md（2026-08-15）、本次吸收批次遗留、09 调研报告 §9、04/13 吸收矩阵。
> 责任标记：**[Owner]** = 需 Owner 操作/裁决；**[Agent]** = 可自主执行；**[混合]** = Agent 准备、Owner 确认。

## A. 本次吸收批次未收尾（2026-08-18 会话内）

| # | 任务 | 责任 | 状态/说明 |
| --- | --- | --- | --- |
| A1 | ~~提交吸收批次~~ | ✅ | 已提交 3 个 commit：9fcb3be（代码）/ a26eca8（文档）/ d77badc（04 矩阵并入） |
| A2 | ~~Teach-Back LLM 精评接线~~ | ✅ 部分 | 配置 learning.teach_back.llm_model 已接线（grade_with_config），配 key 即启用 |
| A3 | ~~04 吸收矩阵并入 §11.5~~ | ✅ | 已并入 d77badc（S: colleague-skill/Graphiti；A/B/C 全量） |
| A4 | ~~S/A 级候选代码级拆解~~ | ✅ | 5 项目拆解完成（批 3 文档 §3）；高优先 4 项已实现（bi-temporal/ontology/SKILL.md/verify gate） |
| A5 | ~~RAG LLM 嵌入配置~~ | ✅ 部分 | rag.embedding.provider/model 已接线（configured_embed_many），配模型即启用 |

## B. 交接遗留（HERMES_HANDOFF · Owner 门禁）

| # | 任务 | 责任 | 说明 |
| --- | --- | --- | --- |
| B1 | RC 三包发布：git tag v0.6.0 → release.yml 8 资产链 → L4 验收（AXW-PKG-601） | [Owner] | 流水线已就绪并审计，执行是 Owner |
| B2 | App Shell 接 Tauri（frontend/dist → frontendDist）+ ENV-103 剩余 hold（rust/uv-cache/wsl2/ci-venv） | [混合] | UI-801 step 2；环境变量/注册表确认后 |
| B3 | H1-H4 EXIT 双循环裁决（045/055 验收前置门禁） | [Owner] | verification gate |
| B4 | AXW-045 / AXW-055 验收 | [Owner] | implementation layer |
| B5 | AXW-012C 安装态 PDF 证据 + AXW-095 Windows 安装态 | [Owner] | 需用户安装运行时 + 真实 NSIS 证据 |
| B6 | AXW-097 release 资格、AXW-060 v1.0 release 包 | [Owner] | Release workflow 已 ready/audited |
| B7 | AXW-096A 大库验收（H4-EXIT 后用户数据） | [Owner] | 性能基准已有真实数据 |
| B8 | AXC-060 RC 逻辑档案 | [Owner] | 仅 RC 触发 |

## C. 交接 P0/P1 优先任务（可自主推进）

| # | 任务 | 责任 | 说明 |
| --- | --- | --- | --- |
| C1 | ~~P0 配置/缓存减重~~ | ✅ 执行 | 纯缓存删除 3.81GB（批 3 文档 §7）；证据/构建产物保留；规则文档整合待下轮 |
| C2 | AXW-WEB-CAPTURE-v3 TaskPack（22 任务 DAG） | [Agent] | OWNER-APPROVED；消灭 web.py stub、统一 PolicyGate、Raw-first、真实 E2E；050-052 可选 |
| C3 | H2 推进（OCR/ASR/质量门） | [Agent] | H2 多格式识别转译闭环首个任务已入库，OCR/ASR 待推进 |

## D. 09 调研报告 §9 下一轮深挖

| # | 方向 | 责任 | 说明 |
| --- | --- | --- | --- |
| D1 | ~~Human Mastery → Machine Skill 自动蒸馏~~ | ✅ | co_learning_loop.py + tick API + E2E 全链跑通（150 后端测试） |
| D2 | ~~Machine Skill → 个人最优学习路径生成~~ | ✅ | learning_path.py + quiz.py + 前端学习路径/测验视图已实现 |
| D3 | ~~AI Learning OS 方向~~ | ✅ | 10 项目调研 + learner_state（遗忘融合）+ learner_profile（置信校准）已实现 |
| D4 | ~~Agent Memory 技术栈选型~~ | ✅ | 5 候选对比完成：无一直接引入，本地等价模块已确认；剩余零依赖补齐见批 3 文档 §9 |
| D5 | ~~04 矩阵扩编~~ | ✅ | 4 新领域 38 项目判定（6/22/5/5）+ 优先集 10（批 3 文档 §6） |

## E. 明确未吸收 / 观察项（治理决策维持）

| # | 项 | 状态 |
| --- | --- | --- |
| E1 | Mem0 / Letta / Graphiti / Cognee 等重型 Agent-Memory 框架 | H7+ 研究池（治理 §7.3）；概念已由本地模块覆盖 |
| E2 | 通用 Agent / RAG 平台（LangGraph、Dify、RAGFlow、Open WebUI 等） | 不进核心（治理 §7.1/7.2） |
| E3 | MinerU / PaddleOCR / Docling 深度解析 bake-off | C 级后置；包 D 证据连接器确认已吸收（shared/evidence_connectors.py ADS-004/007） |
| E4 | Paperless AI Research Brain | 查无此名；按能力方向改盯 pdf-brain / PaperLeaf |
| E5 | 外部库 ENV-103 剩余（rust/uv-cache/wsl2/ci-venv） | 环境/注册表确认后执行 |

## 执行顺序建议

1. A1（提交吸收批次）→ B/C 中可自主项并行 → 04 并入（A3）→ D 按序。
2. Owner 门禁项（B1-B8）在自主项就绪后逐项交 Owner。


## F. 转化管线待办（2026-08-19 更新 · 模型/引擎已就绪）

| # | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| F1 | 音频全量转写（14 mp3 + 64 mp4） | ⏸ 暂停（用户指示） | **SenseVoice int8 已就绪且验证**（60s 中文讲座 1.74s，比 faster-whisper-large-v3 快 ~26x）；sherpa-onnx 1.13.6 已装；恢复时跑 .hermes/task-runtime/_audio_fast.py |
| F2 | 2 个旧版 .doc 转换 | 待做 | 需 LibreOffice/antiword 转换器（共用库工具链） |
| F3 | 8 张超大/损坏图片 | 待做 | PIL 解压炸弹上限（>89478485 像素）；可放大上限或跳过 |
| F4 | SenseVoice 全量模型修复 | ✅ 已替代 | 原 999MB tar 损坏 → HF model.int8.onnx（228MB）+ tokens.txt 已下载到 Model library |
| F5 | sherpa-onnx 安装 | ✅ | uv pip 已装 1.13.6 |
| F6 | 音频转写引擎优先级 | 就绪 | SenseVoice（快）→ faster-whisper（兜底） |
| F7 | 全量重扫图片/PDF/pptx | ✅ 完成 | 1273 图片 + 66/66 PDF + 4/4 pptx（回执已归档） |
| F8 | 视频画面转化（64 mp4 抽帧 OCR） | ⏸ 暂停（用户指示先调研） | 抽帧+RapidOCR 已实证（进步本/黑石案例/复合增长）；脚本 _video_full.py 就绪 |
| F9 | 视频转化增强（PySceneDetect 场景切分 + Qwen2.5-VL 帧描述 + 字幕 SRT） | 待做（调研完成） | 见 docs/current/VIDEO_CONVERSION_RESEARCH_2026-08-19.md（V1-V5 优先级） |

### 共用库规则（用户强调，勿忘）
- **工具链 / 外置依赖** → `D:\All projects\OS External Configuration`（如 tesseract/scoop/ffmpeg/7zip）
- **模型权重** → `D:\All projects\Model library`（如 ollama / whisper / sherpa-onnx / ComfyUI）
- 两库均为**跨项目共用**；项目运行产物留在各自 `.hermes/task-runtime/`
