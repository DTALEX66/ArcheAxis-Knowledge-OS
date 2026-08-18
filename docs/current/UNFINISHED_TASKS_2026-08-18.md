# 未完成任务清单（2026-08-18 整理）

> 来源：HERMES_HANDOFF.md（2026-08-15）、本次吸收批次遗留、09 调研报告 §9、04/13 吸收矩阵。
> 责任标记：**[Owner]** = 需 Owner 操作/裁决；**[Agent]** = 可自主执行；**[混合]** = Agent 准备、Owner 确认。

## A. 本次吸收批次未收尾（2026-08-18 会话内）

| # | 任务 | 责任 | 状态/说明 |
| --- | --- | --- | --- |
| A1 | 提交吸收批次（25 文件：10 后端模块 + 学习 API + 前端 Learning 空间 + 测试 + 文档） | [Agent] | 工作树已有全部改动，未 commit/push |
| A2 | Teach-Back LLM 精评启用（teach_back_eval.grade_with_llm 需 provider/API key） | [混合] | rubric 已可用；配 key 后启用 LLM 精评 |
| A3 | 04 吸收矩阵正式并入 §11.5 建议（colleague-skill S 级 / Graphiti A→S 等） | [混合] | 已写入 09 报告 §11.5，待并入 04 矩阵 |
| A4 | S/A 级候选代码级拆解 + 选型实验（colleague-skill / Graphiti / DeepTutor / Hermes Agent Self-Evolution / Cognee） | [Agent] | 09 报告 §9 方向 4 |
| A5 | RAG 可选 LLM 嵌入 provider 配置（app/rag/embedder.llm_embed） | [混合] | 默认本地 n-gram，可选升级 |

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
| C1 | P0 项目配置规则减重 | [Agent] | .hermes/cache + task-artifacts ~965MB 第三方 config/rules；AGENTS 6KB/VERIFICATION_POLICY 6.7KB/HANDOFF 15KB 冗余整合；GitHub ruleset 不可动 |
| C2 | AXW-WEB-CAPTURE-v3 TaskPack（22 任务 DAG） | [Agent] | OWNER-APPROVED；消灭 web.py stub、统一 PolicyGate、Raw-first、真实 E2E；050-052 可选 |
| C3 | H2 推进（OCR/ASR/质量门） | [Agent] | H2 多格式识别转译闭环首个任务已入库，OCR/ASR 待推进 |

## D. 09 调研报告 §9 下一轮深挖

| # | 方向 | 责任 | 说明 |
| --- | --- | --- | --- |
| D1 | Human Mastery → Machine Skill 自动蒸馏实现与评测 | [Agent] | 本轮已落 distillation/skill_evolution 骨架，需打通自动蒸馏 + 评测门禁 |
| D2 | Machine Skill → 个人最优学习路径生成 | [Agent] | OpenTutor/adaptive-KG 方向 |
| D3 | AI Learning OS 方向（AI 导师/自适应/知识蒸馏/个人能力模型） | [Agent] | 报告 §9.3 |
| D4 | Agent Memory 技术栈选型实验（Mem0/Zep/Letta/Graphiti/Cognee） | [Agent] | H7+ 研究池内做 fixture bake-off |
| D5 | 04 矩阵扩到 50–100 项目逐项判定（直接集成/借鉴架构/借鉴算法/排除） | [Agent] | 报告 §9.6 |

## E. 明确未吸收 / 观察项（治理决策维持）

| # | 项 | 状态 |
| --- | --- | --- |
| E1 | Mem0 / Letta / Graphiti / Cognee 等重型 Agent-Memory 框架 | H7+ 研究池（治理 §7.3）；概念已由本地模块覆盖 |
| E2 | 通用 Agent / RAG 平台（LangGraph、Dify、RAGFlow、Open WebUI 等） | 不进核心（治理 §7.1/7.2） |
| E3 | MinerU / PaddleOCR / Docling 深度解析 bake-off | C 级后置；Docling/PaddleOCR 已有 adapter 痕迹待核实 |
| E4 | Paperless AI Research Brain | 查无此名；按能力方向改盯 pdf-brain / PaperLeaf |
| E5 | 外部库 ENV-103 剩余（rust/uv-cache/wsl2/ci-venv） | 环境/注册表确认后执行 |

## 执行顺序建议

1. A1（提交吸收批次）→ B/C 中可自主项并行 → 04 并入（A3）→ D 按序。
2. Owner 门禁项（B1-B8）在自主项就绪后逐项交 Owner。
