# 全量候选吸收执行矩阵

> 更新：2026-07-27。本文是后续 TaskPack 的阶段入口，不是“全部项目已集成”的能力声明。
>
> 机器真相：`inspiration_research/resources/open_source_project_registry.json` 与 `open_source_absorption_ledger.json`。当前 registry/ledger 均为 101 个项目：`implemented=8`、`adapter_contract_pending=27`、`deferred_review=38`、`reference_only=28`。

## 一、吸收状态定义

| 状态 | 进入条件 | 运行时含义 |
|---|---|---|
| `implemented` | reachable code path、implementation evidence、focused test、失败语义 | 已有受控实现，但只代表该 Adapter/能力，不代表整个上游项目被内置 |
| `adapter_contract_pending` | 已确定价值和边界，但尚无完整 contract/测试/回滚 | 只可进入 TaskPack，不可默认安装或激活 |
| `deferred_review` | 高风险、供应链、执行沙箱、远端服务或许可证/权限仍需审查 | 禁止安装、运行和生产激活 |
| `reference_only` | 只吸收产品、架构、UX 或算法思想 | 不复制代码、不添加依赖、不宣称兼容 |

所有新候选必须记录 source revision、license、风险、数据外部性、目标边界、降级方案、fixture 和 rollback handle。外部仓库、模型、课程和 Vault 内容先进入 candidate/quarantine，不能自动成为 verified truth。

## 二、当前已验证实现

| 项目 | 当前落点 | 证据 |
|---|---|---|
| LiteLLM | `shared-contracts/adapters/llm/litellm_adapter.py` | `tests/test_integrations.py` |
| Crawl4AI | `shared-contracts/adapters/crawlers/crawl4ai_adapter.py` | `tests/test_integrations.py` |
| Trafilatura | `app/ingestion/multi_format.py`、`shared/web_search.py` | ingestion 真实路径 |
| MarkItDown | `app/ingestion/multi_format.py` | `tests/test_coverage_gap.py` |
| Langfuse | `shared-contracts/adapters/observability/langfuse_adapter.py` | `tests/test_langfuse_adapter.py` |
| NetworkX | `app/memory/graph_db.py`、`shared/graph_rag.py` | 图能力路径 |
| sqlite-vec | `app/memory/vector_db.py` | `knowledge_base/tests/test_vector_search.py` |
| Loguru | `shared/logging.py`、`app/ingestion/multi_format.py` | 真实日志/摄入路径 |

这些项目仍受本仓库的 contract、权限、SQLite、Candidate 和 CI 约束；不能因为依赖或文件名相似就扩大能力声明。

## 三、阶段依赖序列

```text
R0 账本真相与 registry 对齐
→ A0 Workspace/Tauri/失败恢复/portable 基线
→ H 文档摄入与 Research Adapter Foundry
→ I Knowledge / Search / Graph / Memory
→ J Obsidian / PKM Compatibility
→ K Evaluation / Observability / Provider
→ L Runtime / Agent / Workflow
→ M Workspace Frontend / Desktop Product
→ N Release / Installer / Distribution
```

每个阶段只在前置出口门禁 GREEN 后开始。每个阶段拆为独立 TaskPack，单 writer 修改、定向 RED/GREEN、完整测试、独立审查、显式 commit、exact-SHA CI。

---

## R0 — 账本真相与路线冻结

**目标：** 消除 registry、ledger、文档和测试之间的状态/数量漂移。

### 后端/数据

- 校验 101 个项目唯一 ID、状态闭集和风险降级。
- 为候选补齐 canonical source、revision、license、target boundary、owner track、fixture、rollback 字段。
- implemented 必须绑定真实代码路径和测试；禁止只凭 README/registry 升级。
- 维护 `open_source_project_registry.json` 与 `open_source_absorption_ledger.json` 的一对一覆盖。

### 前端/文档

- 建立候选项目状态聚合的 Workspace 信息架构；未接入 API 时显示 unavailable。
- 更新 `docs/PROJECT_STATUS.md`、`README.md`、蓝图和吸收总账的数字与状态边界。

### 门禁

- `tests/test_open_source_absorption_ledger.py`
- `tests/test_registry_v2.py`
- registry validator、ruff、完整 Python 测试、repository conventions、diff check。

---

## A0 — 当前产品基线收口

**目标：** 在扩大吸收面前证明产品闭环和数据边界可信。

### 后端

- HTTP→SQLite→Job/Outbox/Receipt→dispatch→delivered→reload readback。
- failure/retry/replay、orphan/tamper、lease fencing、crash/restart recovery。
- 可恢复 Worker：lease、checkpoint、pause、cancel、retry；统一 audit/SSE contract。
- portable data-root；安装模式和 portable copy 模式分开隔离。

### 前端/桌面

- Workspace Job/Delivery 错误、重试、重放、恢复和空状态。
- Chromium 真实交互与 reload readback。
- Tauri WebView2 点击级上传、dispatch、刷新、关闭、重启、回读。
- Windows 安装、升级、卸载、数据保留和恢复说明。

### 门禁

`tests/test_workspace_*`、真实 Chromium、Tauri/WebView、Windows runtime、NSIS lifecycle、同一隔离 SQLite 数据集。

---

## H — 文档摄入与 Research Adapter Foundry

**目标：** 外部文件/网页/媒体只通过统一 SourceRecord/ResearchPackage 进入 candidate。

### 项目分组

- 第一批 Adapter：Docling、Unstructured、MinerU、marker、pymupdf4llm、PaddleOCR、Scrapling、Crawlee、newspaper4k。
- 已实现能力：MarkItDown、Trafilatura、Crawl4AI，补齐 fallback/不可用证据。
- 高风险后置：Firecrawl、browser-use，先做 Safe HTTP/权限/限网审计。

### 后端

- 统一 content type、byte limit、source hash、engine/fallback、processing manifest。
- Adapter 只返回 Markdown + metadata + source record，不直接写 Knowledge 表。
- 原子落盘、approved roots、变更重跑、失败重试、symlink/junction containment。
- PDF/DOCX/PPTX/XLSX/HTML/image/audio fixture 和语言/字体边界。

### 前端

- 导入向导、解析模式、预览、候选状态、逐文件失败/重试/checkpoint。
- 展示来源、证据、provenance 和人工复核，不展示伪准确率。

### 门禁

每个 Adapter 一组真实成功 fixture + 一组 unavailable/fallback fixture；核心安装不因可选重型依赖失效。

---

## I — Knowledge / Search / Graph / Memory

**目标：** 让 Knowledge/Learning/Mastery/Machine Knowledge 在版本、检索、图和回滚上真实可治理。

### 后端

- KnowledgeUnit/Relation/LearningArtifact/MasterySignal/MachineKnowledge 的 version、approval、deprecation、supersedes、provenance。
- sqlite-vec 作为可选增强，FTS5 可独立降级；NetworkX 做本地图计算。
- Graphiti、Kùzu、LanceDB、Mem0 只能 Adapter 化；不得直接写核心事实。
- index rebuild、shadow switch、rollback、embedding version、stale index、孤儿节点、关系冲突。

### 前端

- Knowledge 候选/批准/弃用/版本/来源浏览。
- keyword/vector/hybrid search、命中证据、降级状态。
- Graph 只读 projection、关系来源、冲突和重建状态。
- Learning/Mastery 练习和掌握信号，不把学习分数当事实准确率。

### 门禁

schema tamper、revision conflict、duplicate command、shadow rebuild/switch/rollback、Research→Knowledge→Learning→Mastery→Machine Knowledge lifecycle。

---

## J — Obsidian / PKM Compatibility

**目标：** 明确兼容等级，不把普通 Markdown 导入误称为全面兼容。

### 后端

- `ObsidianVaultSourceV1`、`VaultFileV1`、`VaultLinkV1`、`AttachmentRefV1`、`SyncCursorV1`。
- 显式 vault root、approved roots、隐藏目录/`.trash`/`.obsidian` 策略、大小限制。
- 完整 YAML frontmatter、tags、tasks、aliases、wikilinks、Markdown links、block refs、callout、properties 的支持矩阵。
- 图片/PDF/音频/视频 embed 和缺失附件报告。
- 第一版明确 one-way import/export；后续再做增量、rename/delete、冲突、双向写回。
- Joplin、Logseq、SiYuan、AFFiNE、Zotero 各自 Adapter，不污染核心模型。

### 前端/桌面

- Vault 选择、授权、扫描预览、分类、链接/附件错误、人工确认。
- 原文/解析语义差异预览；Import/Projection/Sync 明确单向/双向。
- Chromium/Tauri 隔离 fixture vault 同路径 readback。

### 门禁

fixture 覆盖 frontmatter、wikilink、alias、Markdown link、tags、tasks、embed、附件、Canvas、missing links、rename/delete、duplicate import；负控覆盖路径逃逸、symlink/junction、恶意 frontmatter、循环链接、超大文件。

---

## K — Evaluation / Observability / Provider

### 后端

- LiteLLM 保持 Adapter；Provider key 不进入代码、日志、trace、UI。
- Promptfoo 做离线评估 Adapter；OpenTelemetry 可选 exporter；Langfuse 保持 payload-safe local fallback。
- OpenAI Agents Python/Pydantic AI 仅做 typed Agent contract spike，不绕过 executor。
- OpenCode/Aider 仅做受控开发/Git patch Adapter，不获得无边界 shell。

### 前端

- Evaluation dashboard：人工真值、CER/WER、证据、失败分类、candidate 状态。
- Trace timeline、redaction、export 状态、provider unavailable/timeout/rate-limit。

### 门禁

provider unavailable、timeout、rate limit、redaction、no-key local mode、trace exporter failure；禁止把 model confidence 当 accuracy。

---

## L — Runtime / Agent / Workflow

### 后端

- 将 `read file:` 扩展为有限 typed intents；每个 intent 有 permission、真实 tool evidence、失败/补偿/评估。
- n8n、Airflow、Prefect 只做 Workflow Adapter；Job/Outbox/lease 仍由本项目拥有。
- LangGraph 仅在本地可恢复状态机需要时接入；不复制第二套状态库。
- OpenHands、AutoGen、CrewAI、browser-use 继续 deferred，直到沙箱、权限、审计、预算、kill/recovery 门禁完成。

### 前端

- Plan/Permission/Execution/Trace/Recovery 页面。
- 用户只选择公开意图和安全参数，不输入内部 package/unit/command/lease ID。
- 暂停、取消、重试、恢复、人工批准和 remediation。

### 门禁

forbidden intent、path escape、SSRF、timeout、crash/restart、lease fencing、duplicate/replay/tamper；动态 Planner 不得绕过 permission/review。

---

## M — Workspace Frontend / Desktop Product

### 前端

- 导航 inventory 与真实 page inventory 对齐；未接入入口必须 unavailable。
- typed DTO/API client；loading/empty/error/retry/stale/recovery 全状态。
- Import、Research Review、Knowledge、Learning、Mastery、Machine Knowledge、Search、Graph、Obsidian/PKM、Jobs、Trace、Evaluation、Diagnostics 页面。
- Chromium real browser matrix：用户动作、HTTP、持久化、reload、关闭/恢复。

### 后端

- 每个页面的聚合 projection/action reference、pagination/filter/sort、ETag/revision、error code、redaction。
- 前端不读 SQLite，不暴露 command/package/artifact/lease/correlation ID。

### 桌面

- Tauri WebView2 readiness、Core lifecycle、data-root、profile、upgrade、uninstall、restore。
- installed/portable 两模式独立验收。

---

## N — Release / Installer / Distribution

- tag-only workflow、isolated staging、exact commit/tree/CI identity。
- checksum、SBOM/provenance、签名策略、artifact manifest。
- NSIS install/upgrade/uninstall/recovery readback。
- 发布前回读 GitHub Release asset；源码 manifest 继续 `unreleased/public=false`，直到完整链路 GREEN。

---

## 四、明确后置池

以下项目全部保留在矩阵，但不提前进入核心：

- Dify、Open WebUI、AnythingLLM、RAGFlow、FastGPT、LobeChat、PrivateGPT、Kotaemon：只参考产品/UX。
- LangChain、LlamaIndex、Haystack、Semantic Kernel：只参考抽象。
- AutoGen、CrewAI、OpenHands、browser-use：高风险 deferred。
- Qdrant、Chroma、Milvus、Kùzu、Neo4j、Elasticsearch：可替换 Adapter spike，不替换 SQLite/MigrationOperator。
- Ghidra、radare2、Frida、pwntools、sqlmap 等：只进入安全研究库，禁止自动执行链。

## 五、启动与完成定义

每个阶段开始前建立独立 TaskPack，包含用户目标/非目标、候选清单、revision/license、contract、数据边界、RED/GREEN、失败/回滚、fixture、CI 和 release gate。阶段出口必须同时有源代码、产品路由、真实运行时、测试、CI、文档和发布事实证据。

当前首批队列：

```text
R0-001 registry truth
A0-001 Tauri delivery/retry/replay/readback
A0-002 portable data-root
H-001 document adapter fallback
I-001 search/graph/vector rollback
J-001 Obsidian one-way vault fixture
K-001 evaluation/trace fallback
L-001 typed runtime intent
M-001 Workspace projection/error matrix
N-001 release artifact chain
```

“全部纳入计划”已完成；“全部运行时吸收”只有在每个项目通过自身门禁后才可逐项标记，不能用计划、registry、dry-run 或旧报告替代真实完成证据。
