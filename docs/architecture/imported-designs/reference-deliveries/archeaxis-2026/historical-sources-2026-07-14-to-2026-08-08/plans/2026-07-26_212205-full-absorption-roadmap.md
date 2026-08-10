# Cognitive-Loop-OS 全量开源吸收与前后端大型阶段计划

**Goal:** 将现有知识库软件、开源项目和 Obsidian/PKM 候选全部纳入一条真实、可回滚、可验收的后续执行序列；不把登记、参考或 dry-run 误报为运行时集成。

**Architecture:** 保持 Cognitive-Loop-OS 的本地优先模块化单体、统一 FastAPI 网关、SQLite/MigrationOperator、版本化合同、Candidate/Review/Provenance 边界。外部项目只能通过直接工具链、显式 Adapter 或参考设计进入；任何新依赖都必须有固定 revision/license、隔离 fixture、RED/GREEN、失败降级、回滚和 exact-SHA CI 证据。

**Baseline:** `main == origin/main == 2cdf11e2b85154c15cfd621c04dae8f6c90d693b`，工作树 clean。读取 `inspiration_research/resources/open_source_project_registry.json` 与 `open_source_absorption_ledger.json` 得到 101 个项目：`implemented=8`、`adapter_contract_pending=27`、`deferred_review=38`、`reference_only=28`。旧文档 `docs/bc-lines/13_开源项目吸收总库.md` 写“103 个”，属于必须先修正的文档漂移。

---

## 0. 不可改变的吸收规则

1. **全量纳入计划，不等于全量安装进核心。** 101 个候选全部保留在矩阵中，但按 `implemented / adapter_contract_pending / deferred_review / reference_only` 管理。
2. **核心架构不被外部平台接管。** Dify、RAGFlow、LangChain、LlamaIndex、Open WebUI、AnythingLLM 等默认只参考产品和模块设计；不替换 Cognitive-OS 合同、SQLite、权限、Candidate 治理或 UI 路由。
3. **高风险项目 fail-closed。** OpenHands、AutoGen、CrewAI、browser-use、Firecrawl、执行沙箱、多租户、云同步、模型权重等不得自动安装、运行或激活。
4. **每个项目只有四种终态：** 已实现且有 evidence；Adapter contract pending；deferred review；reference only。不能用“已吸收”作为无证据总状态。
5. **每个可运行项目都必须拥有：** source revision、license 记录、adapter contract、输入/输出 schema、权限边界、真实成功测试、失败/不可用测试、隔离数据、回滚路径、README/manifest 事实更新和 exact-SHA CI。
6. **外部来源永远先 candidate/quarantine。** 项目 README、模型输出、网页、Vault 文件或第三方知识不能自动成为 verified truth。

---

## 1. Phase R0 — 吸收账本真相与路线冻结

**依赖：** 无。必须先完成，阻止后续阶段使用错误的 103 项目数字或旧分类。

### 后端/数据任务

- 统一 `inspiration_research/resources/open_source_project_registry.json`、`open_source_absorption_ledger.json` 的 schema、状态字段、license/revision/evidence 字段。
- 为每个 `project_id` 补齐：canonical name、source URL、revision、license、risk、target boundary、absorption mode、owner track、dependency tier、test fixture、rollback handle。
- 保留重复 registry ID 的迁移 provenance；禁止静默删除记录。
- 增加“项目已实现”验证器：只有真实 import/call path + implementation evidence + focused test 才能进入 implemented。

### 前端/产品任务

- Workspace diagnostics 增加“候选项目状态”聚合投影，但只显示人类可读名称、模式、状态和门禁，不暴露内部 registry ID、token 或绝对路径。
- 增加吸收矩阵页面的信息架构入口；未接入真实 API 时明确显示“尚未接入真实数据”。

### 文档/测试门禁

- 更新 `docs/bc-lines/13_开源项目吸收总库.md` 的 103 → 101，并链接机器账本。
- 新建 `docs/ABSORPTION_EXECUTION_MATRIX.md`，成为分类、Owner、阶段和验收入口。
- 扩展 `tests/test_open_source_absorption_ledger.py`：数量、状态闭集、license/revision 字段、implemented evidence、风险降级。
- 运行 registry validator、全量 Python tests、ruff、repository conventions、git diff check。

**出口条件：** 101/101 有唯一 ID、有吸收模式、有执行状态；所有文档数字一致；没有项目被未经证据升级。

---

## 2. Product Stage A0 Closeout — 先收口当前真实产品基线

**依赖：** R0。

### 后端任务

- 完成 Workspace failure → retry → replay、lease fencing、orphan/tamper、无重启 readback 的完整 HTTP→SQLite→Receipt 矩阵。
- 将按需 dispatcher 接入可恢复异步 Worker：lease、checkpoint、pause、cancel、retry、crash recovery。
- 建立统一 audit timeline/SSE contract；先本地 SQLite projection，再考虑远端队列。
- 将 Tauri/WebView、Chromium、Python Core 使用同一隔离数据集，统一启动/关闭/恢复协议。
- 完成 portable data-root contract，禁止回退到 `%LOCALAPPDATA%` 的不透明数据路径。

### 前端/桌面任务

- Workspace Job/Delivery 页面补齐状态机、错误 remediation、重试、重放、恢复和空状态。
- 建立 Tauri WebView 点击级验收：上传、dispatch、刷新、关闭、重启、回读。
- 提供桌面诊断、数据目录、迁移、恢复、卸载后的数据保留策略说明。

### 门禁

- `tests/test_workspace_*` 全集；真实 Chromium smoke；真实 Tauri/WebView evidence；Windows runtime/NSIS lifecycle；fresh data root readback。

**出口条件：** A0 的 HTTP→SQLite→Chromium/Tauri、失败恢复和数据边界真实 GREEN。未达到前，不引入重型 Agent、多端同步或新的核心数据库。

---

## 3. Track H — 文档摄入与 Research Adapter Foundry

**依赖：** A0 closeout；R0 中固定候选 revision/license。

### 第一批可运行 Adapter

- 已有实现保持并补齐证据：MarkItDown、Trafilatura、Crawl4AI、LiteLLM、Langfuse、NetworkX、sqlite-vec、Loguru。
- 进入 adapter contract：Docling、Unstructured、MinerU、marker、pymupdf4llm、PaddleOCR、Scrapling、Crawlee、newspaper4k、Firecrawl（默认安全禁用）。

### 后端任务

- 统一 `SourceRecordV1`、`ResearchPackageV1`、content-type、byte-limit、source hash、engine used、fallback chain。
- 文档解析 adapter 只返回 Markdown + metadata + source record，不直接写知识表。
- 解析失败必须返回结构化 unavailable/fallback，不得返回假成功。
- 增加 PDF/DOCX/PPTX/XLSX/HTML/image/audio 的真实 fixture、语言/字体/编码边界和大文件限制。
- 增加 processor manifest、原子落盘、变更重跑、失败重试和 output containment。

### 前端任务

- 导入向导：来源类型、解析模式、预览、候选状态、失败原因、重试；禁止显示 engine 内部 ID。
- 解析结果页展示 source/evidence/provenance 和“需要人工复核”，不显示未经验证的准确率。
- 批量导入显示逐文件状态、失败项和可恢复 checkpoint。

### 门禁

- 每个 Adapter 至少一组真实成功 fixture + 一组 unavailable/fallback fixture。
- `tests/test_ingestion.py`、`tests/test_media_extractor.py`、`tests/test_quality_absorption.py`、source/provenance tests。
- CI 安装 optional dependency 时必须有独立 job，核心默认安装不可被重型依赖污染。

**出口条件：** 文档/媒体输入可以稳定进入 candidate ResearchPackage，任何 parser 不可用都 fail-closed 或显式降级。

---

## 4. Track I — Knowledge / Search / Graph / Memory

**依赖：** H 的 SourceRecord/ResearchPackage 稳定；A0 的 migration/rollback 稳定。

### 后端任务

- KnowledgeUnit、Relation、LearningArtifact、MasterySignal、MachineKnowledge 的版本、审批、弃用、supersedes 和 provenance 完整化。
- sqlite-vec 作为可选向量增强，FTS5 作为可用降级；禁止向量引擎成为不可恢复核心依赖。
- NetworkX 作为本地图计算；Graphiti/Kùzu/LanceDB/Mem0 仅通过 candidate Adapter 评估，不能直接写核心事实。
- 建立检索 index rebuild、shadow switch、rollback、embedding version 和 stale index 检测。
- 建立图谱导入、关系冲突、删除/弃用和孤儿节点处理。

### 前端任务

- Knowledge browser：候选/批准/弃用/版本/来源过滤。
- Search：keyword/vector/hybrid、来源过滤、命中证据和降级状态。
- Graph：只读 projection、关系来源、冲突、孤儿和重建状态。
- Learning/Mastery 页面：候选学习卡、练习、掌握信号和人工审核，不把学习分数当事实准确率。

### 门禁

- schema tamper、revision conflict、duplicate command、shadow rebuild/switch/rollback、FTS-only fallback。
- API projection 不暴露数据库表名、内部 ID、payload 或 lease。
- Integration tests 验证 Research → Knowledge → Learning → Mastery → Machine Knowledge 的真实生命周期。

**出口条件：** 检索、图和记忆都能降级、回滚、审计；Runtime 只能消费 approved Machine Knowledge。

---

## 5. Track J — Obsidian / PKM Compatibility Layer

**依赖：** H 的文档合同、I 的 Knowledge/Relation 版本化、A0 的路径与桌面 readback。

### 支持范围分层

1. **Obsidian 基础导入：** 显式 vault root、递归 Markdown、frontmatter、tags、tasks、aliases、wikilinks、Markdown links。
2. **资源关系：** 图片/PDF/音频/视频附件、embed、relative path、缺失附件报告。
3. **Obsidian 语义：** block reference、callout、properties、Canvas/Excalidraw/Dataview/Tasks 等逐项定义“不支持/转换/保留原文”。
4. **同步策略：** 第一版明确单向导入或单向 projection；后续才做增量、rename/delete、冲突和双向写回。
5. **PKM Adapter：** Joplin、Logseq、SiYuan、AFFiNE、Zotero 作为独立 Adapter，不把任何产品的数据模型写入核心。

### 后端任务

- 创建 `ObsidianVaultSourceV1`、`VaultFileV1`、`VaultLinkV1`、`AttachmentRefV1`、`SyncCursorV1` 合同。
- 使用 approved roots、symlink/junction containment、大小/扩展名/隐藏目录策略。
- 解析完整 YAML frontmatter；保留原文、解析 AST/语义和 warning。
- 建立稳定 source identity、hash、mtime、relative path、rename/delete 状态。
- 先实现 one-way import/export；任何 write-back 都要求 explicit command、dry-run、expected revision、backup 和 readback。
- 禁止默认访问个人 E 盘或外部 Obsidian-Assistance。

### 前端/桌面任务

- Vault 选择、路径授权、扫描预览、分类统计、冲突/失败列表和人工确认。
- 笔记预览显示原文与解析语义差异；链接/附件可点击检查。
- Import/Projection/Sync 页面明确显示单向/双向能力，不能把 dry-run 写入显示为完成。
- Tauri 和 Chromium 使用项目内隔离 fixture vault 做相同 readback。

### 门禁

- fixture vault 覆盖 frontmatter、wikilink、alias、Markdown link、tags、tasks、embeds、attachments、Canvas、missing links、rename/delete、duplicate import。
- 安全负控：路径逃逸、symlink、junction、`.obsidian`、`.trash`、超大文件、恶意 frontmatter、循环链接。
- 真实 Windows path + Tauri/Chromium E2E；不接触用户真实 E 盘 Vault。

**出口条件：** 只能在所有明确支持的 Obsidian 语义通过真实 fixture 和失败门禁后，发布对应兼容等级；未覆盖项必须展示为 unsupported，而不是“全面兼容”。

---

## 6. Track K — Evaluation / Observability / Provider

**依赖：** I 的生命周期和 J 的来源/provenance 合同。

### 后端任务

- LiteLLM 保持现有 Adapter contract；不得把 provider key 写入配置、日志、trace 或 UI。
- Promptfoo 作为离线评估 Adapter：输入 fixture、预期结果、差异、人工 review；不自动改变治理状态。
- OpenTelemetry 作为可选 trace exporter，Langfuse 保持 payload-safe local trace fallback。
- OpenAI Agents Python、Pydantic AI 只在 Permission/Tool/Trace contract 上做 Adapter spike；不得绕过现有 executor。
- OpenCode/Aider 只做受控开发工具或 Git patch Adapter；不得直接获得全磁盘/无边界 shell。

### 前端任务

- Evaluation dashboard：样本、人工真值、CER/WER、命中证据、失败分类、候选状态。
- Observability：trace timeline、correlation、tool result、redaction、export status。
- Provider health/capability 页面只显示真实配置状态，不伪造模型在线状态。

### 门禁

- provider unavailable、timeout、rate limit、redaction、no-key local mode、trace exporter failure。
- evaluation 不把 model confidence 当 accuracy，不把单样本当总体结论。

**出口条件：** provider/observability 可替换、可禁用、可回退，不改变核心事实和审批语义。

---

## 7. Track L — Runtime / Agent / Workflow

**依赖：** A0、I、K；尤其是 Permission、Trace、Evaluation、Recovery 已稳定。

### 后端任务

- 把 `read file:` tracer 扩展为有限的 typed intents；每个 intent 有 permission、tool evidence、失败/补偿/评估。
- n8n、Airflow、Prefect 只做 workflow Adapter；Job/Outbox/lease 仍由 Cognitive-OS 自己拥有。
- LangGraph 只在本地可恢复状态机需要时做 Adapter；不复制第二套状态库。
- OpenHands、AutoGen、CrewAI、browser-use 继续 deferred review，直到沙箱、权限、审计、预算和 kill/recovery 门禁完成。
- 远端队列、多 Agent、云模型、自动执行沙箱必须是独立高风险 TaskPack。

### 前端任务

- Plan/Permission/Execution/Trace/Recovery 页面。
- 用户只能选择公开意图和安全参数，不填写 package/unit/command/lease 内部 ID。
- 失败 remediation、暂停、取消、重试、恢复和人工批准必须有真实 API projection。

### 门禁

- forbidden intent、path escape、network SSRF、timeout、crash/restart、lease fencing、duplicate command、replay/tamper。
- 动态 Planner 不能越过 permission/review，也不能以 echo/mock 作为真实执行证据。

**出口条件：** 仅受治理 intent 可执行；任何外部 Agent 都不能接管核心 Runtime。

---

## 8. Track M — Cognitive Workspace Frontend / Desktop Product

**依赖：** C、A0、I、J、K、L 的公开 projection 合同。

### 前端任务

- 统一 navigation inventory 与真实 page inventory；未知入口必须是明确 unavailable state。
- API client 仅使用 typed DTO/contract，不读 SQLite，不暴露内部 ID。
- 完成 Import、Research Review、Knowledge、Learning、Mastery、Machine Knowledge、Search、Graph、Obsidian/PKM、Jobs、Trace、Evaluation、Diagnostics 页面。
- 每个页面同时定义 loading/empty/error/retry/stale/recovery 状态。
- Chromium real browser matrix：用户动作、网络响应、持久化回读、reload、关闭/恢复。

### 后端/产品 API 任务

- 为每个页面建立聚合 projection 和 action reference。
- API 统一 pagination/filter/sort、ETag/revision、error code、retry-after 和 redaction。
- 不允许把 command/package/artifact/lease/correlation ID 作为普通用户流程输入。

### 桌面任务

- Tauri WebView2 启动 readiness、core lifecycle、data-root、profile、upgrade、uninstall、restore。
- portable copy 与 installed mode 分开验证；明确数据保留/删除策略。

**出口条件：** 前端所有可见按钮均对应真实 API 或明确 unavailable；Chromium 与 Tauri 使用同一隔离数据集，页面状态可无重启回读。

---

## 9. Track N — Release / Installer / Distribution

**依赖：** M、L、Tauri lifecycle、portable data-root。

### 后端/构建任务

- tag-only release workflow；构建隔离 staging tree。
- 注入 exact commit/tree/CI identity 到非源码 release manifest。
- 生成 checksum、SBOM/provenance、签名策略和 artifact manifest。
- NSIS install/upgrade/uninstall/recovery 真实验证；发布前 readback GitHub Release asset。
- 源码 `unreleased/public=false` 继续保持，直到公开链完整。

### 前端/桌面任务

- 普通用户安装/升级/卸载/恢复说明，不暴露内部 artifact/command ID。
- capability manifest 与实际 runtime 版本一致；不以 CI build 代替 public release。

**出口条件：** exact-SHA gate、Windows lifecycle、artifact provenance、公开发布和资产读回全部成功后，才可以宣称可发布版本。

---

## 10. Deferred Research Pool — 永久保留但不提前激活

以下项目仍纳入矩阵，但默认不进入核心运行时：

- Dify、Open WebUI、AnythingLLM、RAGFlow、FastGPT、LobeChat、PrivateGPT、Kotaemon：只参考产品/前端设计。
- LangChain、LlamaIndex、Haystack、Semantic Kernel：只参考抽象，不接管核心 contracts。
- AutoGen、CrewAI、OpenHands、browser-use：高风险 deferred review。
- Qdrant、Chroma、Milvus、Kùzu、Neo4j、Elasticsearch：只做可替换 Adapter spike；不替换 SQLite/MigrationOperator。
- Firecrawl、browser-use、Playwright 自动浏览：先安全审计、限网、fixture 和人工批准。
- Ghidra、radare2、Frida、pwntools、sqlmap 等安全研究池：只进入 Inspiration-Research 安全研究库，禁止进入自动执行链。

---

## 11. 阶段执行顺序与启动条件

按依赖顺序执行：

```text
R0 账本真相
→ A0 产品基线收口
→ H 文档/Research Adapter
→ I Knowledge/Search/Graph/Memory
→ J Obsidian/PKM
→ K Evaluation/Observability/Provider
→ L Runtime/Agent/Workflow
→ M Workspace Frontend/Desktop
→ N Release/Distribution
```

每个阶段开始前必须创建独立 TaskPack，包含：

- 用户目标与非目标；
- 项目/Adapter 清单；
- source revision/license；
- backend/frontend/data/desktop owner；
- contract 与 migration；
- RED/GREEN 测试；
- 失败、降级、回滚、恢复；
- 隔离数据目录；
- 本地门禁与 exact-SHA CI；
- 文档、manifest 和 release truth 更新。

**时间承诺规则：** 当前蓝图没有给出日历日期，不能伪造“某月全面完成”。阶段启动时间由上一阶段出口门禁决定；只有用户明确选定某个 TaskPack 后，该阶段才进入执行队列。

---

## 12. 第一批真实 TaskPack 切片

1. `R0-001`：修正 101/103 registry 漂移，补全吸收矩阵字段和 validator。
2. `A0-001`：Tauri WebView delivery 点击、retry/replay、restart readback。
3. `A0-002`：portable data-root 与 Windows install/copy 双模式恢复。
4. `H-001`：Docling/MarkItDown/Trafilatura unified adapter contract + fallback fixture。
5. `I-001`：search/graph/vector shadow rebuild 与 rollback projection。
6. `J-001`：Obsidian one-way vault import fixture（frontmatter/link/tag/task/attachment）。
7. `K-001`：Promptfoo/Otel evaluation/trace local fallback。
8. `L-001`：typed runtime intent + permission/recovery；不进入多 Agent。
9. `M-001`：Workspace lifecycle UI typed projection + unavailable/error/retry matrix。
10. `N-001`：tag-only release artifact chain、checksum/provenance/readback。

任何一个 TaskPack 未完成前，不把同类候选项目批量激活；并行审计可以进行，shared checkout 的写入保持单 writer。

---

## 13. 总体完成定义

只有同时满足以下条件，才能说“全量吸收阶段完成”：

- 101 个候选项目均有真实状态和归类；
- 所有 `implemented` 项目都有 reachable code path、focused test 和 evidence；
- 所有 Adapter 项目都有独立 contract、失败降级和 rollback；
- reference/deferred 项目不会被误报为已安装或已运行；
- Obsidian/PKM 兼容等级按实际语义覆盖发布；
- 前端所有公开入口都有真实 projection 或明确 unavailable 状态；
- 后端、桌面、数据、worker、测试、CI、installer、release manifest 事实一致；
- exact-SHA CI、Windows lifecycle 和公开 artifact readback 全部通过。

在这些条件之前，产品文案只能写“候选矩阵已登记、部分 Adapter 已实现、后续阶段按门禁吸收”，不能写“所有开源项目已融入”或“全面兼容”。
