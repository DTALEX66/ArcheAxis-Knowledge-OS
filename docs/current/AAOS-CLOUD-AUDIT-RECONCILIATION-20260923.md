# AAOS 云端审计复核与目标增量记录（2026-09-23）

## 记录性质

本文件把用户提供的《ArcheAxis 云端全量审计与前次架构结论复核报告》转化为 AAOS 当前项目的可执行目标增量。它不是云端全量审计的替代品，也不把报告中的云端文件树、未展开的 workflow、外部仓库或历史对话自动认定为当前事实。

- source: 用户粘贴附件 `C:\Users\ALEX\.codex\attachments\1135fb25-19a7-4786-b51f-c3fc5ea4ab98\已粘贴的文本.txt`
- source_sha256: `A11CAF0B48596FFD1CB227CB308AB430230043D98816F80BD5BF1D3BAF180FF9`
- reviewed_against_commit: `c1e426ad5842eaa6ba90b26c798c3d315f74183c`
- status: `ANALYZED / TARGET_ADDED / IMPLEMENTATION_NOT_STARTED`

## 复核结论

### 接受为架构方向

以下方向与 AAOS 当前 R6/M0 权威边界一致，加入后续目标：

1. ArcheAxis 继续作为 Knowledge–Evidence–Learning–Experience Authority，不新增第四套 Agent Runtime。
2. 外部项目和社区内容只能通过 Adapter/Receipt → Candidate 进入，不能直接写入 Active Knowledge。
3. Candidate 的正确路线是加固现有入口，而不是另建第二套 Candidate/Prompt Library。
4. Evidence、Validation、Promotion、Applicability、Expiry/Revalidation 必须成为可检查的系统不变量。
5. WORK-LAB、DESIGN-LAB、Beacon、Jev、GEP、AutoResearch 的角色必须保持边界：Receipt/Adapter/Evaluator/实验侧车，不能替代 AAOS Canonical Truth。
6. AutoResearch/RSI 不得获得 Self-Merge、Self-Deploy、Self-Declare-Truth 权限。

### 当前 checkout 的事实校正

报告引用的下列云端路径在当前 checkout 中不存在：

```text
src/aaos/candidate.py
src/aaos/components/candidate.py
knowledge-workspace/scripts/aaos_candidate_import.py
tests/test_candidate_import.py
tests/test_candidate_enrichment.py
tests/test_candidate_hash_identity.py
tests/test_aaos_candidate_import.py
```

当前 checkout 中可定位到的相关能力表面是：

```text
app/evidence/graph.py
app/evidence/relations.py
app/evidence/ledger.py
app/knowledge/promotion.py
app/agent/experience_harvest.py
shared-contracts/schemas/github_project_candidate.schema.json
shared-contracts/validators/validate_project_candidates.py
tests/test_evidence_graph.py
tests/test_research_to_knowledge_promotion.py
tests/test_knowledge_candidate_versioning.py
tests/test_machine_knowledge_candidates.py
```

因此，报告中“云端 main 存在 Candidate 源码/测试”的结论当前只登记为：
`CLOUD_MAIN_REPORTED / LOCAL_PATH_DRIFT_REQUIRES_RECONCILIATION`。
不能把它直接写成当前分支已经实现，也不能据此重复创建 Candidate Pipeline。

当前 `.github/workflows/` 确实存在 `ci.yml`、`nightly.yml`、`release.yml`、`vnext-ci.yml`，但本次只核对了目录元数据；workflow 权限、Action SHA、下载、Secrets、`pull_request_target` 和运行日志仍然是 `NOT_AUDITED`。

## 加入当前任务目标的后续队列

本队列排在当前前端 Candidate/staging 与 Local Green Owner Gate 之后；不改变 R6/M0 的 no-release、外置库和 Green 数据边界。

### P0-A — Canonical Object Model 逐文件复核

- 目标：以当前 checkout 为准，建立 Source、Candidate、Claim、Evidence、Artifact、Validation、Knowledge、Method、Skill、Experience、Experiment、Review、LearningState 的对象/字段/序列化/写入者矩阵。
- 首读范围：`app/`、`packages/contracts/`、`shared-contracts/`、`crates/`、`tests/`。
- 验收：每一项必须有文件与行号；重复事实源、legacy/vNext 重叠和未实现项分别标记；不只根据文件名下结论。
- 前置：只读；不修改 schema，不改数据库，不触碰外置库。

### P0-B — 现有 Candidate 入口加固

- 目标：审计并加固当前 `github_project_candidate`、Evidence/Research candidate 和 promotion 入口的 normalize、hash、dedup、provenance、license、quarantine 与路径/命令边界。
- 首读范围：`shared-contracts/schemas/github_project_candidate.schema.json`、`shared-contracts/validators/validate_project_candidates.py`、`app/agent/experience_harvest.py`、`app/knowledge/promotion.py` 及对应测试。
- 验收：外部输入不能绕过 Candidate；imported/reviewed/validated/active 语义不可混同；补充的每个 invariant 均有负例测试和真实命令证据。
- 明确禁止：不创建第二套 Prompt Library，不自动执行外部 Prompt，不把报告中的云端旧路径复制回当前仓库。

### P0-C — Evidence Graph 与 Provenance Replay

- 目标：核对 Source → Claim → Evidence → Validation → Promotion 的实际可追溯性，区分“Evidence 概念存在”和“完整 Graph 已实现”。
- 首读范围：`app/evidence/graph.py`、`app/evidence/relations.py`、`app/evidence/ledger.py`、`app/evidence/bundle.py`、`tests/test_evidence_graph.py`、`tests/test_evidence_bundle.py`、`tests/test_evidence_contract.py`。
- 验收：抽样对象可以读回 source identity/version、evidence/artifact、validation、review/promotion；断链必须标记 `TRACEABILITY_GAP`，不得用模型分数替代存在性检查。

### P0-D — Promotion State Machine 与 Experience 生命周期

- 目标：审计/补齐 `RAW → CANDIDATE → NORMALIZED → REVIEWED → EXPERIMENTAL → VALIDATED → ACTIVE → STALE/DEPRECATED/REJECTED/CONFLICTED/QUARANTINED` 的合法转换、不可变 receipt、适用条件和失效重验证。
- 首读范围：`app/knowledge/promotion.py`、`app/agent/experience_harvest.py`、`tests/test_research_to_knowledge_promotion.py`、`tests/test_knowledge_candidate_versioning.py`。
- 硬门禁：禁止 Candidate/Quarantined/未重验证 Stale 直接 Active；每次 promotion 要有 actor、policy、evidence、validation、timestamp、source commit。
- 前置：先完成 P0-A 的对象矩阵；不引入 GEP 作为 Canonical Model。

### P0-E — CI / 供应链与运行时下载审计

- 目标：只读审计 workflow、依赖锁、脚本和运行时下载/执行边界。
- 范围：`.github/workflows/*.yml`、`pyproject.toml`、`requirements*.txt`、`uv.lock`、`package*.json`、`scripts/`、Docker/Make 文件（若存在）。
- 检查项：Action 是否 SHA pin、最小 permissions、`pull_request_target`、动态下载执行、未 pin 依赖、`shell=True`/`os.system`、runtime install、SBOM/checksum、Secrets exposure。
- 验收：每个结论有文件/行号；未读日志/规则/Secrets 元数据保持 `NOT_AUDITED`，不宣称 CI 安全。

### P0-F — 跨项目 Receipt Boundary

- 目标：确认 WORK-LAB/DESIGN-LAB/Beacon 的输出只能形成 Receipt/Candidate，不得直接写 AAOS Active Knowledge。
- 前置：用户明确授权对应外部仓库的精确只读路径和范围；当前不扫描外置共享库、真实资料库或私有会话。
- 验收：形成跨仓调用路径、权限边界、exchange schema、receipt 位置和绕过 Candidate 的负例；不创建共享数据库或自由写 Memory。

### P1 — 受治理 Adapter 与实验侧车

只有 P0 治理链通过后，才评估 Prompts.chat Source Adapter、GEP Experience Adapter、Beacon Receipt Adapter、Jev Evaluation Sidecar、Experiment Registry、AutoResearch Sandbox 和 Evidence-aware Retrieval。

### P2 — 优化项

Experience ranking、adaptive retrieval、冲突建议、实验调度和受控 knowledge evolution candidate 只能在 P0/P1 稳定后进入；Controlled RSI 继续后置，不进入生产治理路径。

## 访问与交付边界

- 本记录不授权访问 E/F 盘、`.codex/.zcode/.hermes`、凭据、浏览器状态、Green 数据或真实资料库。
- 外置资源只按 `docs/SHARED_RESOURCE_PATH_INDEX.md` 定位；不复制共享库到本项目。
- 本轮不实施上述 P0/P1/P2，只把经过复核的任务加入当前目标队列。
- 前端当前优先级不被本审计替换；云端审计治理任务在前端 staging/Green Owner Gate 之后执行。

