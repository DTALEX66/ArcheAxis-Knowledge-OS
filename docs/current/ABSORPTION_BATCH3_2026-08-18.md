# 吸收批 3 + 全量推进记录（2026-08-18 深夜）

## 1. 真实管线转化测试（ceshi 授权语料）

- 语料：D:\All projects\ceshi\牛津通识读本\简明逻辑学（中文版）.pdf（136 页，有文本层）
- 结果：pymupdf 提取 12 页 8805 字；OCR 质量门 **pass**；本地 n-gram 嵌入 top-chunk cos **0.223** vs ollama qwen3-embedding(0.6b) **0.605**（语义优势显著）；sqlite-vec 检索正常；ECL 规则抽取对学术文本 **0 实体/0 关系**（印证需 ontology 约束）；corpus_to_skill 产出 7 topics/7 procedures/7 提案
- 回执：.hermes/task-runtime/real_pipeline_receipt.json

## 2. 包 C 识别管线 bake-off（网络调研结论）

- 主链路：**Docling → RapidOCR → qwen3-embedding → qwen3-reranker → sqlite-vec**
- Fallback：解析 Docling→pymupdf4llm→MinerU(AGPL)；OCR RapidOCR→PaddleOCR→Tesseract；Embedding BGE-M3→qwen3→n-gram
- 实测解读：正文走 pymupdf 系即可（有文本层），OCR 仅门禁；qwen3 语义远超 n-gram，n-gram 降级为词法腿；下一步补固定 query top-k 命中 + 端到端 QA 命中率指标
- 参考：pdfmux.com/pdf-extractor-comparison-2026 / dev.to 5 工具实测 / qwen3 vs BGE-M3 对比

## 3. A4 五项目代码级拆解（已落实的高优先项）

| 项目 | 吸收动作 | 已落地 |
| --- | --- | --- |
| Graphiti | temporal_graph 加 **ingested_at 双时态** + 时态置信 | ✅ app/memory/temporal_graph.py（6 测试通过） |
| Cognee | graph_pipeline 加 **ontology 枚举约束 + grounding span 锚定** | ✅ app/knowledge/graph_pipeline.py |
| colleague-skill | **SKILL.md frontmatter 规范 + Persona/Skill 双轨** | ✅ app/knowledge/skill_spec.py |
| Hermes | skill_evolution.verify_patch 加 **回归基准门禁** | ✅ app/knowledge/skill_evolution.py |
| DeepTutor | capabilities 注册表 + ChatOrchestrator 路由 | 后置（涉及新架构面） |

## 4. D3 AI Learning OS（已落实 R1/R2）

- 调研：10 个项目在线核实（DeepTutor/OpenTutorAI/OATutor/pyBKT·pyKT/FSRS v6.2/Tutor MCP/Tutor CoPilot/KST/KnowLP/DAS3H）
- 差距：BKT 无遗忘维度、M 级未与 BKT 概率融合、缺 IRT/置信校准
- **R1 已实现**：app/knowledge/learner_state.py（BKT×FSRS 遗忘融合：mastery/recall_probability/forgetting_risk）
- **R2 已实现**：app/knowledge/learner_profile.py（能力画像 + 置信校准 ECE 风格）
- R3（先决路径推荐）由 learning_path.py 承接

## 5. D4 Agent 记忆栈选型

- 五候选全 Apache-2.0、活跃；**无一直接引入**（Mem0 需 Qdrant、Graphiti 默认 Neo4j、Letta 完整运行时、Cognee 依赖树大、Zep CE 废弃）
- 本仓 4 个本地模块恰好对应其 4 个概念；下一步零依赖补齐：GraphOntology（已做）、ingest_episode 双时态+自动失效（temporal_graph 已做 bi-temporal）、long_term.add_from_conversation、memory_layers.check_memory_pressure→蒸馏触发

## 6. D5 吸收矩阵扩编（38 项）

- 判定：**直接集成 6 / 借鉴架构 22 / 借鉴算法 5 / 排除 5**
- 直接集成：genanki、Ollama、llama-cpp-python、sentence-transformers、FlagEmbedding(BGE)、nomic-embed-text
- 优先集 10：Ollama→BGE-M3→sentence-transformers→anki-connect→genanki→fsrs-rs optimizer→obsidian SRS 卡片语法→Ragas 指标→MTEB/BEIR 门禁→Dataview DQL

## 7. C1 配置/缓存减重（执行完毕）

- 删除纯缓存：uv 1655.6 + npm 200.3 + pip 124 + cargo 449.8 + playwright-browsers 688.5 + uv-desktop 452.3 + pycache 238.1 + pytest/ruff 0.3 = **3.81 GB 释放**
- 保留：task-artifacts（证据）、rt-verify（证据）、build-staging/desktop-runtime（构建产物）、.venv（工作环境）

## 8. 本轮新增测试

- test_ocr_gate (6)、test_skill_spec_verify (8)、test_learner_state_profile (7) + 既有扩展
- 全套 **170 passed**（后端）+ 17 vitest（前端）

## 9. 待办（剩余）

- C2 AXW-WEB-CAPTURE-v3 TaskPack（22 任务，OWNER-APPROVED，最大块）
- B1-B8 Owner 门禁（RC v0.6.0 发布、Tauri 接线、H1-H4 EXIT、验收项）
- D4 剩余零依赖补齐（long_term.add_from_conversation / memory_layers.check_memory_pressure）
- 包 C 补充指标测试（top-k 命中率/QA 命中率/耗时矩阵）
- A2/A5 配置接线已落地（learning.teach_back.llm_model / rag.embedding.provider），待配 key 启用
