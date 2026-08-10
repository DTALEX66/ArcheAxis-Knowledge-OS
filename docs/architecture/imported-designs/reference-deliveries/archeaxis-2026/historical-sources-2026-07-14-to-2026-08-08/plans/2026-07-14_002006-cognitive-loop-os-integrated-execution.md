# Cognitive Loop OS Integrated Execution Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 在不再访问或修改外部 A 项目 `Obsidian-Assistance` 的前提下，先关闭 Cognitive-Loop-OS 当前在途吸收/安全/打包改动，再将 HERMES Full Development Package v1 转化为当前仓库可执行的 Phase 0–10 路线。

**Architecture:** 采用单仓模块化单体、Existing Assets First、Contracts First、Copy → Validate → Switch。当前 `app/`、`shared/`、`knowledge_base/`、`Inspiration-Research/` 继续作为已实现能力源；新 `modules/`、`platform/`、`integration/` 和 `/api/v1` 先以可运行 Facade/Adapter 方式接入，禁止空壳和一次性搬迁。

**Tech Stack:** Python 3.10–3.12、FastAPI、Pydantic、SQLite/WAL、FTS5、sqlite-vec、NetworkX、Pytest、Ruff、GitHub Actions、Docker。

---

## 0. 不可变边界

### 唯一写入目标

```text
<repository-root>
```

### A 项目永久只读且不再触碰

```text
<external-project-root>
```

后续任务不得对 A 项目执行：

- 文件搜索、代码扫描或测试；
- 写入、格式化、恢复、清理、暂存、提交或推送；
- 重新比较“是否已吸收”；
- 从 A 项目运行任何脚本；
- 将 A 项目路径写成运行时默认值。

A 项目既有审计结论只作为历史输入；后续验收全部针对 Cognitive-Loop-OS 当前代码。

### 设计包定位

`Cognitive_Loop_OS_HERMES_Full_Development_Package_v1.zip` 是目标设计来源，不是可直接执行的补丁。包内 prompt、PowerShell 和 `ALPHA_SCHEMA.sql` 不得直接运行；先转化为仓库原生文档、TaskPack、测试和迁移。

---

# Track A — 先关闭当前在途改动（必须先完成）

## Task A1：冻结并分类当前工作区

**Objective:** 建立本轮改动的可审计清单，避免把未来架构迁移混进当前安全/吸收收尾。

**Files:**
- Create: `docs/reports/CURRENT_WIP_CLASSIFICATION_2026-07-14.md`
- Read only: current Git index、working tree、untracked files

**Steps:**

1. 记录 `git branch --show-current`、`git rev-parse HEAD`、`git status --short`。
2. 将改动分为四组：
   - 质量能力吸收；
   - 安全与真实性；
   - `knowledge_base` 打包迁移；
   - CI/文档整理。
3. 标记所有运行时产物、数据库、日志、cache、wheel 和 egg-info，确认不提交。
4. 记录 A 项目为 `excluded/read-only/no-more-audit`，不读取它来生成报告。
5. 运行 `git diff --check`。

**Gate:** 每个修改文件只有一个明确 Ownership；无来源不明文件。

---

## Task A2：完成安装后运行时可写路径

**Objective:** 普通 wheel 安装后，数据库、日志、JWT secret、API key 文件和备份不得写入 `site-packages`。

**Files:**
- Modify: `shared/config.py`
- Modify: `shared/storage.py`
- Modify: `shared/logging.py`
- Modify: `shared/auth.py`
- Modify: `shared/backup.py`
- Test: `tests/test_hardening.py`
- Test: `tests/test_packaging.py`（新建）

**TDD cases:**

1. 源码仓运行：相对 `data/...` 解析到仓库目录。
2. wheel/非源码树运行：解析到 `COGNITIVE_DATA_DIR`；未设置时解析到用户可写目录。
3. 显式绝对路径保持不变。
4. 日志、DB、secret、backup 的 parent 自动创建。
5. 任何运行时路径都不位于安装包目录。

**Verification:**

```bash
python -m pytest tests/test_hardening.py tests/test_packaging.py -q --tb=short
```

---

## Task A3：修正当前状态文档中的夸大项

**Objective:** 文档只陈述已由最新执行证明的能力。

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `README.md`
- Modify: `docs/architecture/CURRENT_ARCHITECTURE.md`
- Modify: `AGENTS.md`

**Required corrections:**

- `/run` 仍是 echo-based planner，不得描述为完整真实认知闭环；
- 测试数、路由数只记录命令和时间，不作为永久事实；
- A 项目明确为已完成吸收的只读历史来源；
- `knowledge_base/` 是当前合法包名；
- wheel 验证必须注明安装后数据目录；
- Mypy 历史债务继续如实记录。

**Gate:** 文档事实与当前代码、测试输出一致。

---

## Task A4：执行当前工作区完整质量门

**Objective:** 对 Track A 最新树获得一组可重复的真实门禁输出。

**Commands:**

```bash
python -m pytest tests -q --tb=short
cd knowledge_base && python -m pytest tests -q --tb=short
cd .. && python -m pytest integration-tests -q --tb=short
python -m ruff check app shared knowledge_base cli.py
python -m ruff check shared-contracts/adapters app/workflow
python -m build --wheel
```

额外验证：

1. 临时目录安装 wheel，不使用 editable install。
2. 从仓库外导入 `app.main` 和 `knowledge_base.api`。
3. TestClient 验证 `/health`、`/kb`、`/kb/quality`、Dashboard 模板。
4. 执行 `cognitive-os health` 和 `cognitive-os stats`。
5. 递归枚举 `(method, full_path)`，确保无重复和静态路由遮蔽。
6. 验证 Dataview/View/Export 不能访问内部表。
7. 验证 production：auth=false、CORS `*`、无 API key 均启动失败。
8. 扫描 diff 中的凭据模式，输出仅允许 `[REDACTED]`。
9. `git diff --check`。

**Gate:** 所有命令退出码 0；若失败，先修复并重新运行完整门禁。

---

## Task A5：独立审查当前 diff

**Objective:** 在提交前查出 wheel、路由、安全、真实性和兼容性回归。

**Review scope:**

- `shared/storage.py`：SQL 安全与表级授权分离；
- `shared/auth.py` / `shared/config.py`：同一环境事实源；
- `shared/processing_manifest.py`：源/输出指纹和原子产物；
- `shared/evidence_verification.py`：调用者自报不得 verified；
- `knowledge_base/api.py` / routers：路由集合与参数兼容；
- wheel：模板、config、合法包、安装后运行时路径；
- workflow/adapters：真实执行或明确 unavailable；
- 文档：无硬编码完成数字。

**Gate:** 所有 blocker 关闭；非 blocker 进入 Phase 0 Gap Report。

---

## Task A6：分四个逻辑提交并同步

**Objective:** 把当前在途改动拆成可回滚提交，而不是一个不可审查的大提交。

**Preparation:** 如需清空当前暂存区，只执行非破坏性的 index unstaging，并保留 working tree；随后按精确路径暂存，禁止 `git add .`。

**Commit 1 — 质量能力：**

```text
feat: absorb portable quality and resumable ingestion capabilities
```

包含 manifest、accuracy、evidence、content quality、OER、multi-format 与对应测试/吸收总账。

**Commit 2 — 安全和真实性：**

```text
fix: harden auth data access and external integrations
```

包含 auth/config、SQL/allowlist、CORS、workflow/adapters、hardening/integration tests。

**Commit 3 — 包结构和发布：**

```text
refactor: package knowledge base and verify wheel runtime
```

包含 `knowledge_base` rename、imports、CLI、pyproject、config package data、Docker、CI、安装后路径测试。

**Commit 4 — 文档单一事实源：**

```text
docs: reconcile architecture status and operating boundaries
```

**Sync gate:**

```bash
git fetch --prune origin
git rev-list --left-right --count HEAD...origin/main
git push origin main
git fetch --prune origin
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

最终要求：`HEAD == origin/main`、ahead/behind `0 0`、工作区干净。

---

# Track B — 将设计包转化为仓库原生 Phase 0

## Task B1：导入设计包为“参考规范”，不是运行指令

**Objective:** 保存有价值设计，同时隔离外部 prompt 和不可直接执行脚本。

**Files:**
- Create: `docs/architecture/target-v1/README.md`
- Create: `docs/architecture/target-v1/EXECUTION_CONSTITUTION.md`
- Create: `docs/architecture/target-v1/TARGET_ARCHITECTURE.md`
- Create: `docs/architecture/target-v1/MINIMUM_COMPLETE_ALPHA.md`
- Create: `docs/architecture/target-v1/ALPHA_ACCEPTANCE_MATRIX.md`
- Create: `docs/architecture/target-v1/SECURITY_BASELINE.md`
- Create: `docs/architecture/target-v1/CONTRACT_CATALOG.md`
- Create: `docs/architecture/target-v1/MIGRATION_STRATEGY.md`
- Create: `docs/architecture/target-v1/SOURCE_INTEGRITY.md`

**Rules:**

- 不提交 ZIP 二进制；
- 不把外部 prompts 安装成 Agent 指令；
- 不运行包内 PowerShell；
- `ALPHA_SCHEMA.sql` 只登记为目标模型，不复制为可执行 migration；
- 记录 checksum 56/56 匹配但无签名保证。

---

## Task B2：建立明确 Ownership 与保护边界

**Objective:** 消除“当前 A 项目”歧义，并定义模块所有权。

**Files:**
- Create: `SYSTEM_OWNERSHIP.md`
- Create: `system-manifest.yaml`
- Modify: `AGENTS.md`

**Required content:**

```yaml
protected_external_projects:
  - name: Obsidian-Assistance
    path: D:/All projects/Obsidian-Assistance
    access: no_access_by_default
    status: absorbed_read_only_archive
```

定义现有 Ownership：

- `app/` → current runtime implementation；
- `shared/` → legacy cross-cutting implementation，逐步收口；
- `knowledge_base/` → current KB package；
- `Inspiration-Research/` → current research implementation；
- `modules/` → new public module facades；
- `platform/` → new platform interfaces；
- `integration/` → cross-module workflows；
- `legacy/` 仅在入口切换后才使用，不提前复制整树。

---

## Task B3：执行 Phase 0 Delta Inventory

**Objective:** 针对 Track A 已提交的最新 HEAD 生成真实基线，不再使用旧 `b23bcf4` 数字。

**Files:**
- Create: `CURRENT_PHASE.yaml`
- Create: `migrations/reports/phase-0/ASSET_MAP.md`
- Create: `migrations/reports/phase-0/FILE_INVENTORY.csv`
- Create: `migrations/reports/phase-0/API_ROUTE_MAP.json`
- Create: `migrations/reports/phase-0/DEPENDENCY_REPORT.md`
- Create: `migrations/reports/phase-0/TEST_BASELINE.md`
- Create: `migrations/reports/phase-0/SECURITY_BASELINE.md`
- Create: `migrations/reports/phase-0/ARCHITECTURE_GAPS.md`
- Create: `migrations/reports/phase-0/REUSE_DECISIONS.md`
- Create: `migrations/reports/phase-0/PHASE_1_TASKPACK.md`

**Phase 0 scope:** 只分析 Cognitive-Loop-OS；不访问 A 项目；不移动业务代码；不改数据库 Schema；不改变 API 行为。

**Required gap dimensions:**

- 已实现且已执行验证；
- 已实现但未接主链；
- declarative only；
- stub/simulated；
- security blocker；
- data migration blocker；
- contract gap；
- E2E gap；
- documentation drift。

**Gate:** Phase 0 报告引用真实命令输出、Git SHA 和时间；`CURRENT_PHASE.yaml` 从 `in_progress` 更新为 `passed` 后才能进入 Phase 1。

---

# Track C — Phase 1：先建可运行 Facade，不搬代码

## Task C1：建立模块包，但每个入口必须调用真实旧实现

**Files:**
- Create: `modules/inspiration_research/public.py`
- Create: `modules/knowledge_base/public.py`
- Create: `modules/cognitive_enhancement/public.py`
- Create: `modules/cognitive_runtime/public.py`
- Create: `modules/cognitive_contracts/__init__.py`
- Create: `platform/__init__.py`
- Create: `integration/__init__.py`
- Test: `tests/architecture/test_facades_are_live.py`

**Negative control:** 禁止空函数、`pass`、固定返回值、未被调用的包。

**Gate:** 每个 Facade 至少有一个真实调用者和合同测试。

---

## Task C2：建立 Architecture Guard

**Files:**
- Create: `scripts/architecture_guard.py`
- Create: `tests/architecture/test_dependency_direction.py`
- Modify: `.github/workflows/ci.yml`

**Rules enforced:**

- Contracts 不导入业务模块；
- Platform 不导入业务模块；
- 新 modules 不直接访问其他模块内部数据库；
- 新代码不得增加 `sys.path.insert`；
- A 项目路径不得出现在运行时代码；
- 新 Facade 必须有真实调用者。

---

# Track D — Phase 2：Contracts First

## Task D1：先定义版本化核心合同

**Files:**
- Create: `modules/cognitive_contracts/schemas/source.py`
- Create: `modules/cognitive_contracts/schemas/claim.py`
- Create: `modules/cognitive_contracts/schemas/evidence.py`
- Create: `modules/cognitive_contracts/schemas/knowledge.py`
- Create: `modules/cognitive_contracts/schemas/runtime.py`
- Create: `modules/cognitive_contracts/states/lifecycle.py`
- Create: `modules/cognitive_contracts/errors.py`
- Test: `tests/contract/`

**First contracts:** `SourceRecord`、`Claim`、`Evidence`、`ResearchPackage`、`KnowledgeUnit`、`MasterySignal`、`MachineKnowledgeUnit`、`TaskPack`、`Evaluation`。

**Contract tests:** required fields、enum、JSON round trip、旧对象 Adapter、版本字段、未知字段策略。

---

## Task D2：为现有对象建立 Adapter，不改现有表

**Files:**
- Create: `integration/compatibility/current_to_v1.py`
- Test: `tests/contract/test_current_to_v1.py`

**Mappings:**

- `kb_documents` → `KnowledgeUnit` candidate；
- `kb_evidence` → `Evidence` candidate；
- `kb_reviews`/`kb_mistakes` → `MasterySignal` 输入；
- `a_to_b_candidates`/`machine_knowledge_units` → Machine Knowledge lifecycle；
- execution trace/eval/lesson → Runtime contracts。

**Gate:** 不建新业务表；只做纯转换和合同测试。

---

# Track E — Phase 3：关闭安全和数据正确性 P0

## Task E1：移除代码内默认管理员 Key

**Files:** `shared/auth.py`、`shared/config.py`、`tests/security/test_auth.py`。

**Acceptance:** 任何环境都没有硬编码管理员 key；开发环境也需显式 key 或一次性本地初始化。

## Task E2：阻止 Token 角色自选

**Files:** `app/main.py` 或新 `/api/v1` auth router、`shared/auth.py`、安全测试。

**Acceptance:** 请求参数不能将普通主体提升为 admin；角色由认证主体/服务端策略决定。

## Task E3：统一 Safe HTTP / SSRF Guard

**Files:**
- Create: `platform/network/safe_http.py`
- Adapt: `shared/web_search.py`、`shared/feed_collector.py`、`shared/youtube_extractor.py`、workflow integrations、GitHub collector
- Test: `tests/security/test_ssrf.py`

**Acceptance:** 拒绝 loopback/private/link-local/reserved/multicast/metadata；每次 redirect 重检；限制 timeout、size、content type。

## Task E4：Approved Source Roots

**Files:** `platform/storage/path_policy.py`、ingestion/source discovery/Obsidian adapters、安全测试。

**Acceptance:** 无显式 allowed root 不读取仓库外路径；symlink/junction 越界被拒绝；A 项目不是默认 allowed root。

## Task E5：稳定哈希和索引迁移

**Files:** `app/memory/vector_db.py`、versioned migration、migration tests。

**Acceptance:** 不再用 Python `hash()` 生成持久 rowid/embedding bucket；提供 FTS/vector rebuild 和回滚；旧 DB 副本升级可验证。

## Task E6：Rate Limiter 接入

**Files:** `shared/rate_limit.py` 或 `platform/security/rate_limit.py`、`app/main.py`、安全测试。

**Acceptance:** `remaining()` 不消耗额度；主网关和敏感端点有配置化限制；返回 429 和审计信息。

## Task E7：正式 Migration Runner

**Files:** `platform/database/migrations/`、`platform/database/runner.py`、migration tests。

**Acceptance:** 空库升级、现有 v0.4 副本升级、重复运行、失败回滚、表数/记录数/hash、backup/restore、FTS/vector rebuild。

**Important:** 不直接运行设计包 `ALPHA_SCHEMA.sql`；目标 22 表与当前 25 表必须逐表映射。

---

# Track F — Phase 4–6：Research、Knowledge、Enhancement

## Phase 4 Research

1. `SourceRecord` Facade；
2. Claim/Evidence candidate pipeline；
3. 可信来源与真实多源 cross-validation；
4. conflict/unknown/risk 输出；
5. GitHub Repository Audit；
6. 复用已吸收的 accuracy、manifest、evidence locator、OER；
7. 所有外部内容进入 quarantine/candidate。

## Phase 5 Knowledge

1. Knowledge Unit Facade；
2. Source/Claim/Evidence 追溯；
3. Relation 与版本化；
4. Card/Review/Mistake 继续复用；
5. Mastery Signal；
6. Machine Candidate → Approval → Active → Deprecated；
7. 高风险 Machine Knowledge 不得自动 executable；
8. 课程转换账本、verification audit、evidence sidecar 归入本阶段，不再读取 A 项目。

## Phase 6 Enhancement

1. 统一 `LearningArtifact`；
2. Simple/Expert Explanation；
3. Cards/Questions；
4. Mermaid/Diagram；
5. Quality Report；
6. 现有 Canvas、Mermaid、Progressive Summary 通过 Adapter 复用；
7. 生成内容默认 candidate，不直接覆盖正式知识。

每个 Phase 均使用 TDD、独立 TaskPack、明确回滚和单独提交。

---

# Track G — Phase 7–8：修复真实 Runtime 与 Sleep Loop

## Task G1：替换固定 echo Planner

**Files:** `app/core/compiler.py`、`modules/cognitive_runtime/planner/`、Planner tests。

**Acceptance:** 计划由 Goal、Context、Constraints、Tools、Risk 生成；echo/preview 标记 `simulated`，不能成为成功证据。

## Task G2：统一 Tool Evidence Contract

**Files:** executor、tool registry、runtime contracts、tests。

**Acceptance:** 每种工具声明 evidence validator；无有效 evidence 不得 `success=True`。

## Task G3：多维 Evaluation

**Dimensions:** success criteria、evidence、safety、completeness、quality、rollback state。

**Acceptance:** 不再由单一 bool 决定 1.0；simulated/no-op 得不到成功 lesson。

## Task G4：Lesson 真正反馈 Planner

**Acceptance:** 下一次相似 Goal 的 Context/constraints/tool recommendation 能读取已审核 Lesson；candidate lesson 不自动 active。

## Task G5：Sleep Loop 复用统一 Runtime

**Acceptance:** Sleep Loop 不维护第二套 Planner/Evaluator；支持 retry/replan/pause/approval；完成必须有真实工具证据；长任务恢复后状态一致。

---

# Track H — Phase 9：E2E Alpha

必须通过五条真实闭环：

1. GitHub URL → Research Package → Knowledge → Artifact → Task → Eval；
2. Document → Card → Review → Mistake → Mastery → Machine Candidate；
3. Goal → Dynamic Plan → Permission → Tool Evidence → Eval → Lesson；
4. New Evidence → Conflict → New Knowledge Version → Old Machine Knowledge Deprecated；
5. Long Goal → Dependency Queue → Execute → Evidence → Resume/Replan。

**Rules:**

- 使用固定本地 fixture 和可控网络 mock；
- 至少一个真实只读 GitHub/HTTP smoke 作为可选外部验证；
- 不使用 A 项目；
- 不将文件存在、confidence 或 mock success 冒充 E2E 成功；
- 每条 E2E 保存 trace/evidence/evaluation，但测试产物写临时目录。

---

# Track I — Phase 10：产品化 Roadmap

Phase 9 通过后才进入：

- 完整 Learning OS / FSRS / Teach-back；
- Research Intelligence / Aether Radar；
- 多模态 Courseware/Presentation/Simulation；
- MCP、Model Router、Sandbox、Multi-Agent；
- Web/Desktop/Mobile；
- Installer、Upgrade、Diagnostics、Backup UI；
- Public Alpha → Beta → Stable。

禁止在 Phase 9 前过早微服务化、VR 化、社交化或插件市场化。

---

# 每个 TaskPack 的统一执行模板

1. 读取 `CURRENT_PHASE.yaml`。
2. 检查 Cognitive-Loop-OS `git status --short`。
3. 声明 Ownership Scope 和禁止修改范围。
4. 写失败测试。
5. 运行失败测试并记录预期失败。
6. 实现最小修复。
7. 运行定向测试。
8. 运行 changed-file Ruff/type gate。
9. 运行相关 contract/integration/security gate。
10. 检查 diff、凭据、运行时产物。
11. 独立 spec review。
12. 独立 code-quality review。
13. 显式路径暂存并提交。
14. 写 Phase/Task report 和回滚方式。
15. 只有 Gate Decision=passed 才进入下一 TaskPack。

---

# 提交与并发策略

- 一个 TaskPack 只处理一个 Ownership；
- 常规任务尽量不超过 12 个修改文件；
- 大迁移拆成 Facade、Adapter、Switch、Deprecate 四个提交；
- 数据 migration 与业务功能分开提交；
- 安全修复与功能开发分开提交；
- 不并发运行共享 SQLite ledger 的测试；
- 子代理只做彼此独立的只读审查或独立模块实现；
- 禁止多个代理同时编辑 `shared/storage.py`、`app/main.py`、`knowledge_base/api.py`、`pyproject.toml`。

---

# 近期执行优先级

```text
P0-Now  A1-A6：关闭当前 WIP、验证、审查、提交、同步
P0-Next B1-B3：设计包入库 + Phase 0 Delta
P1      C1-C2：可运行 Facade + Architecture Guard
P1      D1-D2：Contracts + Current Adapters
P0      E1-E7：Auth/SSRF/Path/Hash/Rate/Migration
P1      F：Research/Knowledge/Enhancement 正式闭环
P0      G：真实 Planner/Evidence/Eval/Lesson/Sleep Loop
P0      H：五条 E2E Alpha
P2+     I：完整产品 Roadmap
```

当前立即执行点是 **Task A1**，不是重新访问 A 项目，也不是直接建立 `modules/` 空目录。
