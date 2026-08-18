# 全量候选吸收执行矩阵（v2 — 2026-08-11 更新）

> 更新：2026-08-11。基于 `ArcheAxis_Workspace_Project_History_and_OSS_Absorption_Master_Atlas_v1.md` 全面更新。
> 旧 v1（2026-07-27）仍保留在 Git 历史，但不得再作为活跃状态引用。
> 权威账本：`docs/truth/SUPPLY_CHAIN_LEDGER.json`（v2，46 个组件，含吸收决策）。
>
> **机器真相已迁移**：旧 registry/ledger（101 行，`implemented=8`）已被 ledger v2 替代。旧数字不反映当前真实集成状态（PDF.js、pytesseract 等已合并但旧账本未记录）。本文不再是"全部项目已集成"的能力声明——它是当前吸收决策和执行计划。

---

## 一、吸收状态定义（v2 扩展）

| 状态 | 进入条件 | 运行时含义 |
|---|---|---|
| `CURRENT` | 真实代码路径 + 依赖/源码证据 + 测试 | 已有受控实现，但只代表该 Adapter/能力，不代表整个上游项目被内置。按 source/installed/release 三层资格分别标注。 |
| `ADOPT` | 通过决策分析，选为某能力的首选方案 | 经 exact-revision RDR（ReuseDecisionRecord）后可集成。未完成 RDR 前不得加入依赖锁。 |
| `EVALUATE` | 候选方案，需固定 fixture bake-off 比较 | 不默认使用；在多候选间用统一 corpus 比较后选 primary + fallback。 |
| `SIDECAR` | 隔离、可卸载、非默认常驻能力 | 独立资源/进程；不进入核心依赖图或默认启动路径。 |
| `REFERENCE` | 只吸收 UX、合同、算法或测试思想 | 不复制代码、不添加依赖、不宣称兼容。 |
| `DEFER` | 长期有价值，但不进入 H0–H5 | H6+ 重新评估；当前不投入资源。 |
| `REVIEW-BLOCK` | 许可、模型、安全或产品边界门禁未通过 | 默认关闭；capability probe 返回 disabled。 |
| `REJECT-CORE` | 与当前产品定位（本地学习与知识工作台）无关 | 不进入产品依赖图；历史记录保留。 |

所有新候选必须记录 source revision、license（代码/模型/数据/资产分开）、风险、数据外部性、目标边界、降级方案、fixture 和 rollback handle。外部仓库、模型、课程和 Vault 内容先进入 candidate/quarantine，不能自动成为 verified truth。

---

## 二、当前已集成项目（v2，按资格层表达）

| 项目 | 当前落点 | 资格层 | 最新决策 |
|---|---|---|---|
| PDF.js 3.11.174 | `app/workspace/ui/assets/` | source + installed | 保留；规划 5.x 升级 spike |
| MarkItDown[pdf] | `app/ingestion/multi_format.py` | source + installed | 轻量 baseline；默认禁用 LLM OCR |
| Trafilatura >=1.8 | `app/ingestion/multi_format.py` / `shared/web_search.py` | source + installed | 锁定 Apache-2.0 版本；补来源快照 |
| pytesseract + Tesseract | `app/ingestion/multi_format.py` (MFX-010) | source + installed | Baseline OCR；诚实不可用时降级 |
| Crawl4AI | Adapter | source | 动态页 sidecar；不常驻 |
| LiteLLM | Adapter | source | 薄 Provider；core MIT / enterprise 另许可 |
| Langfuse | Adapter | source | 本地 fallback；ee/ 另许可 |
| sqlite-vec | `app/memory/vector_db.py` | source | 可选派生索引；FTS5 始终可降级 |
| NetworkX | `app/memory/graph_db.py` / `shared/graph_rag.py` | source | 派生投影；Kùzu 归档不得替换 |
| Loguru | `shared/logging.py` | source + installed | 保留；与 structlog 职责收敛 |
| structlog | 直接依赖 | source + installed | 与 Loguru 收敛，避免双框架 |
| APScheduler | Runtime scheduler | source | 保留现有范围；不扩展为编排器 |

---

## 三、当前产品阶段（替代旧 R0→A0→H→I→J→K→L→M→N 序列）

旧序列已过时。当前实际阶段：

```text
H0 — 真实产品闭环（v0.5.1，已 PASS 并 merge main）
H1 — RawAsset / Evidence / 早期学习（已 PASS，全部 merge main）
H2 — 多格式识别转译闭环（首个任务 AXW-023A DOCX 已入库；OCR/ASR/质量门待推进）
H3 — Obsidian / Markdown / Canvas 兼容（JSON Canvas + 编辑器族）
H4 — 学习调度 + Claim 级验证 + 可选本地模型
H5 — 稳定 v1.0（导出/备份/升级/性能/a11y/release）
H6–H10 — Parking Lot（需显式激活）
Web 增补 / KLC 增补 — 按冻结依赖在对应 Horizon 激活
```

每个 Horizon 只在前置出口门禁 GREEN 后开始。每个阶段拆为独立 TaskPack，单 writer 修改、定向 RED/GREEN、完整测试、独立审查、显式 commit、exact-SHA CI。

**关键纠正**：旧交接文档中"H1 未 merge、PDF.js 前端待实现"已过时（H1 已于 #72 合并、PDF.js 已于 #74 合并）；"implemented=8"的旧账本数字已被 ledger v2 替代。

---

## 四、当前遗留问题与漂移

### 4.1 旧文档漂移（须在下一轮授权迁移中更正）

- `docs/PROJECT_STATUS.md` 仍写"H1 在 PR、PDF.js 前端待实现"
- `docs/truth/H0_H1_STATUS_HANDOFF.md` 仍写 PR #72 未 merge
- 旧 registry/ledger（2026-07-22）停留在 101 行 / implemented=8，未反映 PDF.js、pytesseract 等当前事实

### 4.2 吸收账本漂移

旧 ledger 的 `implemented=8` 和 registry 的 `candidate` 状态均已被 ledger v2 替代。旧数字不能继续被引用为"集成数量"或"待集成数量"。369 / 101 / 103 / 57 / 8 这些来源高度重叠，不能相加。

---

## 五、推荐开源吸收任务包（只定义，不授权执行）

### 包 A：Ledger Truth Reset
- 冻结六套来源快照（369/101/103/57/historical-8/later-research）+ 哈希
- 标准化 URL/名称；归并迁移别名
- 建立 canonical component ledger（基于 ledger v2 schema）
- 生成机器 reconciliation report

### 包 B：Current Integration Qualification
- 对 §二 12 个当前已接线项目建立 exact revision + 三层状态 + Windows capability probe + NOTICE/SBOM + failure fixture

### 包 C：H2 Recognition Provider Bake-off
- PDF/Office：MarkItDown / Docling / 专用库
- OCR：Tesseract / PaddleOCR / RapidOCR / EasyOCR bake-off
- ASR：faster-whisper / whisper.cpp / sherpa-onnx bake-off
- 统一固定 fixture corpus + CER/WER/结构/资源/失败率

### 包 D：Evidence Connector Registry
- Crossref / DataCite / OpenAlex / Wikidata / Europe PMC / NCBI / Open Library 首批连接器
- 统一 rate-limit / cache / provenance / source-independence / egress policy

### 包 E：Workspace/Learning OSS Qualification
- Markdown parser + YAML roundtrip bake-off
- 单编辑器族决策（CodeMirror 6 / Lexical / TipTap / BlockNote）
- JSON Canvas + XYFlow；py-fsrs；Zotero/Anki/Joplin API Adapter

### 包 F：Supply Chain Minimum Set
- Syft + pip-audit + 一个漏洞扫描器 + Gitleaks + Cosign（H5）

---

## 六、上游更新与纠错记录

| 项目 | 旧结论 | 2026-08-11 更新 |
|---|---|---|
| Marker | "GPL-3.0" | 代码 Apache-2.0；权重修改版 OpenRAIL-M。代码/权重分审。 |
| MinerU | "Apache-2.0" | Apache-2.0 + 附加 MAU/收入阈值与在线服务标识义务。不得笼统写 Apache-2.0。 |
| PyMuPDF4LLM | "AGPL/商业" | AGPL-3.0。只有明确接受 AGPL 或购商业许可后使用。 |
| tldraw | "候选 SDK" | 生产需要 license key。不是 OSS 默认组件。REVIEW-BLOCK。 |
| Kùzu | "graph DB 候选" | 上游 2025-10-10 归档。不得选为 primary。 |
| H5P PHP Library | "core MIT" | **GPL-3.0**。旧 MIT 结论作废。 |
| Phoenix | "开源观测" | **Elastic License 2.0**。不是 OSS。 |
| Firecrawl | "API/crawler 候选" | 主体 **AGPL-3.0**；SDK/UI 部分 MIT。组件级审查。 |
| LiteLLM | "MIT" | 核心 MIT；**enterprise/ 另许可**。 |
| Langfuse | "MIT" | 核心 MIT；**ee/ 另许可**。 |
| PDF.js | "3.11.174 已接入" | 上游已有 5.x。不盲升；建兼容/CVE 升级 spike。 |

---

## 七、不应吸收到产品核心的项目族

### 7.1 通用 Agent / 编码 Agent
OpenHands、AutoGen、CrewAI、LangGraph、PydanticAI、OpenAI Agents SDK、Semantic Kernel、OpenCode、Aider、Claude Code、Cline、SWE-agent 等：

- 可作为开发工具、typed contract 参考
- **不作为 Workspace 产品能力**
- 不得绕过现有 Job/Outbox/Receipt、Permission、Evidence 和 Human Review
- H10 前不进入默认依赖图

### 7.2 整体 RAG / 知识平台
Dify、RAGFlow、Open WebUI、AnythingLLM、FastGPT、Kotaemon、Khoj 等只作产品/UX 参考。项目的事实层、开放文件和 EvidenceAnchor 不能交给另一套平台接管。

### 7.3 Agent Memory / Graph RAG
Mem0、Letta、Graphiti、Cognee、LightRAG、GraphRAG、KAG、HippoRAG 等继续留在 H7+ 研究池。

### 7.4 安全研究实验室
Ghidra、radare2、Rizin、Frida、pwntools、sqlmap、angr、AFL++、syzkaller、QEMU、Wireshark、ZAP、MobSF、Volatility、YARA 等全部 `isolated-lab/reference-only`。禁止进入自动执行链。

---

## 八、启动与完成定义

每个阶段开始前建立独立 TaskPack，包含用户目标/非目标、候选清单、revision/license、contract、数据边界、RED/GREEN、失败/回滚、fixture、CI 和 release gate。阶段出口必须同时有源代码、产品路由、真实运行时、测试、CI、文档和发布事实证据。

当前活跃队列（依 Horizon 顺序）：

```text
H2 — 多格式识别闭环（MFX-010/012/001 已完成，AXW-023A DOCX 已入库）
  → OCR bake-off、ASR bake-off、质量门、Evidence Connector Registry
H3 — JSON Canvas + 编辑器族 + XYFlow
H4 — py-fsrs + Claim 验证 + 可选本地模型
H5 — release qualification
```

"全部纳入计划"已完成；"全部运行时吸收"只有在每个项目通过自身门禁后才可逐项标记，不能用计划、registry、dry-run 或旧报告替代真实完成证据。


---

## 2026-08-18 执行批次（Owner 授权 · 代码已落库）

将"登记未吸收"与 09 调研报告的新候选落成真实实现（详见 09 报告 §12）：

| 新增实现 | 来源 | 状态 |
| --- | --- | --- |
| app/knowledge/knowledge_tracing.py（BKT EM + 在线更新） | OATutor/pyBKT/pyKT | CURRENT（9 tests） |
| app/knowledge/dual_mastery.py（M0-M7/K0-K8/证据成熟度 + Gap） | 09 报告 | CURRENT（6 tests） |
| app/knowledge/teach_back_eval.py（rubric + 误解提取） | Studyield/OpenCognition | CURRENT（6 tests） |
| app/knowledge/distillation.py（人机蒸馏 候选→规则→技能） | colleague-skill | CURRENT（6 tests） |
| app/memory/temporal_graph.py（时序事实/版本链/冲突） | Graphiti 概念 | CURRENT（6 tests） |
| app/memory/reasoning_memory.py（轨迹→原则） | ReasoningBank | CURRENT（6 tests） |
| app/knowledge/skill_evolution.py（演化闭环+门禁） | Hermes Self-Evolution/SkillRL | CURRENT（7 tests） |
| app/memory/memory_layers.py（L1-L4 分层） | MemoryOS/MemOS/Hermes Memory OS | CURRENT（8 tests） |
| app/rag/embedder.py + index.py（真实嵌入索引） | sqlite-vec | CURRENT（7 tests） |
| app/api/learning.py（6 端点学习者状态） | Tutor MCP 概念 | CURRENT（路由注册） |
| frontend Learning 空间三视图 + api/learning.ts | DeepTutor/Studyield/FSRS/OpenTutor | CURRENT（4 vitest） |

治理边界维持：Mem0/Letta/Graphiti/Cognee 等仍属 H7+ 研究池（§7.3）；通用 Agent/RAG 平台不进核心（§7.1/7.2）；本批以本地自研等价能力覆盖其概念，未新增重型外部依赖。


---

## 2026-08-18 并入批次 2（执行，代码已落库）

| 新增实现 | 来源 | 状态 |
| --- | --- | --- |
| app/learning/quiz.py + learning_path.py | DeepTutor/OpenTutor/adaptive-KG | CURRENT（9 tests） |
| app/learning/corpus_to_skill.py | Corpus2Skill | CURRENT（4 tests） |
| app/knowledge/graph_pipeline.py（ECL） | Cognee | CURRENT（5 tests） |
| app/agent/experience_harvest.py | Meta Knowledge Graph | CURRENT（5 tests） |
| app/memory/memory_files.py | ReMe | CURRENT（3 tests） |
| app/graph/community.py | GraphRAG | CURRENT（4 tests） |
| app/adapters/anki_zotero.py | 包 E | CURRENT（8 tests 与 long_term 合并） |
| app/memory/long_term.py | Mem0 | CURRENT（同上） |

- 包 D（证据连接器）：确认已吸收（shared/evidence_connectors.py，ADS-004/005/006/007 + tests），未重复实现。
- 全套吸收测试累计 **107 passed**（批 1: 69 + 批 2: 38）；治理边界不变，无新重型依赖。
