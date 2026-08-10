# Cognitive Workspace 最小闭环（前后端全流程）实施计划

**Goal:** 在今天交付一个可操作、可审计的本地 Cognitive Workspace MVP：人工从已持久化的 Research candidate 发起审批，经 Knowledge → Learning → Practice → Mastery → Machine Knowledge candidate 全流程完成，并在浏览器中查看每一步的状态、失败原因和 audit timeline。

**Architecture:** 复用现有 Phase 5–9 的真实治理模块与 SQLite migration owner；不另建平行数据库、Graph 路径、审批逻辑或前端状态源。新增一个小型 FastAPI Workspace router 和一个服务端渲染的 Jinja/原生 JavaScript 页面；前端只调用受鉴权、类型化的 Workspace API，不直读 SQLite，也不把 caller-supplied reviewer 字符串当作人工审批依据。

**Tech Stack:** FastAPI、Pydantic、现有 `MigrationOperator` / `shared.storage`、现有 Research/Knowledge/Learning/Mastery/Machine Knowledge modules、Jinja2 + 原生浏览器 JavaScript、pytest、Ruff。

---

## 0. 今日范围与完成定义

### 唯一用户可见闭环

```text
已持久化 ResearchPackage candidate
→ authenticated human review / promotion
→ Knowledge candidate
→ Learning artifact candidate
→ authenticated human approval
→ approved practice card
→ practice evidence
→ MasterySignal
→ MachineKnowledge candidate
→ audit timeline + diagnostics
```

### 本日交付必须同时具备

1. **后端真实写入和严格读回**：所有步骤调用当前的 governed service/facade，而不是在 API 或 UI 中复制 SQL。
2. **前端可操作**：浏览器中可选择/输入符合 contract 的对象 ID、执行允许的下一步、看到 status、timeline、错误和 diagnostics。
3. **认证边界**：所有 review / approval mutation 从 server-side authenticated principal 导出 reviewer identity；开发和测试均须显式 fixture/config，不允许 `reviewer_id` 从 JSON body 传入。
4. **审计与失败路径**：未审批时 practice 必须被拒绝；重复 command 必须幂等或明确 conflict；不支持的状态转换必须显示非敏感错误。
5. **不扩张范围**：不实现 React、账户管理、远端队列、SSE、通用 multi-agent、视觉/空间记忆、Installer 或 public release。

### 文档冲突的处理

`README.md:44-47` / `docs/PROJECT_STATUS.md:7` 表示 Phase 5–9 已有治理构件和 Alpha tracer；`docs/FUTURE_EXECUTION_BLUEPRINT.md:56-81` 与 `PROJECT_STATUS.md:51` 明确缺少的是**单一 command/outbox/worker/audit 时间线及可交互工作台**。今日任务以后一项为准：把已有构件接成最小、可见、可审计的 Workspace，不重复实现既有领域能力。

---

## 1. 建立今天的 TaskPack 与 API 合同基线

**Objective:** 固定一条端到端场景、命令 ID / actor / expected-state 合同和非目标，防止 UI 直接耦合内部表。

**Files:**
- Create: `workspace/intake/012_cognitive_workspace_mvp_taskpack.md`
- Create: `app/contracts/workspace.py`
- Modify: `app/contracts/__init__.py`
- Test: `tests/test_workspace_contracts.py`

**RED:** 先测试 `WorkspaceCommand` 拒绝空 command ID、caller-supplied reviewer、未知 action、缺少 required resource ID、非法状态转移的请求形状。

**GREEN:** 定义最小请求/响应 contract：`command_id`、`correlation_id`、resource IDs、expected revision/phase、server-derived actor；响应包含 `status`、`resource_ids`、`timeline`、安全的 `error_code`。不要在 contract 中定义 credentials、SQLite 路径或任意 SQL filter。

**Verification:**
```bash
./.venv/Scripts/python.exe -m pytest tests/test_workspace_contracts.py -q --tb=short -p no:cacheprovider
./.venv/Scripts/ruff.exe check app/contracts/workspace.py tests/test_workspace_contracts.py --no-cache
```

**Checkpoint:** `test(workspace): define governed command contracts`。

---

## 2. 将认证主体接入人工审批命令

**Objective:** 把 review/approval 身份从 HTTP request 的 server-side authenticated principal 派生，彻底禁止 body 中伪造 reviewer ID。

**Files:**
- Read/Modify: `shared/auth.py`
- Read/Modify: `app/main.py`（现有 auth middleware / dependency 接入点）
- Create: `app/workspace/authorization.py`
- Test: `tests/test_workspace_authorization.py`

**RED:**
- 未认证调用 approval endpoint → `401/403`，无数据库写入。
- body 提供 `reviewer_id="human:forged"` → schema 拒绝或忽略该字段，ledger actor 必须来自 verified principal。
- 已认证但无 review capability 的主体 → `403`，无数据库写入。
- 正确 reviewer principal → ledger 的 reviewer/actor 与 request body 无关。

**GREEN:** 提供一个窄的 `WorkspaceReviewPrincipal`，仅由现有认证结果构造。生产调用使用 middleware/dependency；测试用 fixture 注入隔离 identity。开发模式不提供隐式 admin 或任意 human fallback。

**Verification:**
```bash
./.venv/Scripts/python.exe -m pytest tests/test_workspace_authorization.py -q --tb=short -p no:cacheprovider
./.venv/Scripts/ruff.exe check shared/auth.py app/main.py app/workspace/authorization.py tests/test_workspace_authorization.py --no-cache
```

**Risk:** 权限/认证变更属于高风险；该 TaskPack 完成时必须运行完整本地门禁、冻结 tree 审查和独立 CI，不能等到普通 UI checkpoint。

---

## 3. 实现单一 Workspace command service 与 audit read model

**Objective:** 用服务端单一编排层调用已有真实模块，形成命令结果和可读 audit timeline；不重新实现领域写入。

**Files:**
- Create: `app/workspace/service.py`
- Create: `app/workspace/read_model.py`
- Create: `app/workspace/__init__.py`
- Read/Reuse: `app.knowledge.promotion`, `app.knowledge.closed_loop`, `app.facades.research_runtime`, `app.evaluation.governance`
- Read/Reuse: `shared/knowledge_governance_migration.py`, `shared/migration_runner.py`
- Test: `tests/test_workspace_service.py`

**Command actions (严格 allowlist):**

| Action | Existing owner to call | Required input | Expected result |
| --- | --- | --- | --- |
| `promote_research` | `app.knowledge.promotion.promote_research_package_to_candidates` | persisted `package_id`, command ID, rationale | candidate Knowledge units/relations |
| `start_learning` | `app.knowledge.closed_loop.start_learning_candidate` | candidate `unit_id`, command ID, rationale | candidate LearningArtifact |
| `approve_learning` | `app.knowledge.closed_loop.approve_learning_artifact` | `artifact_id`, command ID | approved practice-card IDs |
| `record_practice` | `app.knowledge.closed_loop.record_practice_evidence` | approved `artifact_id`, command ID, quality | MasterySignal and optional Machine Knowledge candidate |
| `audit_case` | `app.knowledge.closed_loop.audit_closed_loop` + strict reads | `artifact_id` | ordered, non-sensitive timeline |

**RED:**
- 从一个真正在测试 fixture 中持久化的 `ResearchPackageV1` 开始，断言未授权、未审批、重复 command、错误 resource relation 和 tampered provenance 都 fail closed。
- 验证读模型不创建数据库、不修改 state，且在第二个 SQLite connection/process 中可重新读取 timeline。
- 验证 command/result 无法写 legacy `graph_entities` 或 `graph_relations`。

**GREEN:** 仅适配现有 service，统一 correlation/command ID 和 response shaping；如现有表无法表达 command/audit 事实，扩展**现有** `knowledge-governance.sqlite` owner migration，写入 append-only command/event/outbox 表，并带 backup、idempotency、rollback、status-drift 测试。不得新建 parallel SQLite owner。

**Verification:**
```bash
./.venv/Scripts/python.exe -m pytest tests/test_workspace_service.py tests/test_phase5_mcs_closed_loop.py -q --tb=short -p no:cacheprovider
./.venv/Scripts/ruff.exe check app/workspace tests/test_workspace_service.py --no-cache
```

**Checkpoint:** `feat(workspace): add governed closed-loop command service`。

---

## 4. 暴露受保护的 Workspace HTTP API

**Objective:** 只通过 typed API 让前端读取 case、执行允许动作和取得 diagnostics；不让浏览器直接访问 SQLite 或 legacy domain writer。

**Files:**
- Create: `app/workspace/router.py`
- Modify: `app/main.py`（注册 router；不破坏 `/kb` compatibility mount）
- Test: `tests/test_workspace_api.py`

**API surface（最小）:**

```text
GET  /workspace/api/diagnostics
GET  /workspace/api/cases/{artifact_id}
POST /workspace/api/commands/promote-research
POST /workspace/api/commands/start-learning
POST /workspace/api/commands/approve-learning
POST /workspace/api/commands/record-practice
```

- `GET` 返回真实 read model / existing `/diagnostics` 的安全子集。
- `POST` 使用 Task 2 的 principal dependency；request schema 不接受 reviewer identity、database path、任意 URL 或 SQL。
- `409` 用于状态/revision/idempotency conflict；`422` 用于 contract validation；`401/403` 用于 authentication/authorization；所有错误使用稳定 code，不泄露路径/provenance/secret。

**RED:** FastAPI `TestClient` 覆盖匿名写入、伪造 reviewer、正常授权闭环、重复 command、未审批 practice、只读 GET 无数据库增量。

**GREEN:** router 只转发 `WorkspaceCommandService`；不在 router 中执行 SQL、合成 fake review、调用外部网络或自动提升 candidate truth。

**Verification:**
```bash
./.venv/Scripts/python.exe -m pytest tests/test_workspace_api.py -q --tb=short -p no:cacheprovider
./.venv/Scripts/ruff.exe check app/main.py app/workspace/router.py tests/test_workspace_api.py --no-cache
```

---

## 5. 实现服务端渲染 Cognitive Workspace 前端

**Objective:** 在现有 FastAPI/Jinja 技术栈中提供一个真正可操作的最小工作台，而不是静态 mock 或全量重写 `knowledge_base/templates/dashboard.html`。

**Files:**
- Create: `app/workspace/templates/index.html`
- Create: `app/workspace/static/workspace.js`
- Create: `app/workspace/static/workspace.css`
- Modify: `app/workspace/router.py`（`GET /workspace` HTML route 与 static mount）
- Test: `tests/test_workspace_ui.py`

**UI information architecture:**

1. **System bar**：release / health / migration state；所有 unavailable/error 均明确显示，绝不显示伪成功。
2. **Case selector**：输入已有 `package_id` / `unit_id` / `artifact_id`；前端不创建或猜测 ID。
3. **Governance stepper**：Research → Knowledge → Learning → Practice → Mastery → Machine candidate；每步呈现真实 status、可执行动作和先决条件。
4. **Human review panel**：显示当前 authenticated identity 的公开 display label（若后端允许），rationale 输入、明确确认按钮；不允许编辑 reviewer ID。
5. **Practice panel**：仅 approved artifact 显示 quality 0–5 输入；未批准时禁用且展示 server error。
6. **Audit panel**：按 event time/order 呈现 timeline、command/correlation IDs 和 resource links；不呈现 SQLite 文件路径、full provenance payload 或 secrets。

**RED:**
- HTML 只通过 `GET /workspace` 返回，且引用本地 static assets。
- 页面 action 对应 exact API allowlist，不包含 direct database URL、legacy graph endpoint 或任意 external URL write。
- 用 browser-level/HTML contract test 验证 action 按钮在未满足先决条件时 disabled、错误在 DOM 中可读、timeline 使用 API response 渲染。

**GREEN:** 原生 JS 用 `fetch` 调用 Workspace API、渲染 JSON-safe content（禁止 `innerHTML` 注入服务器文本）、处理 401/403/409/422；CSS 复用当前 Purple Gemstone 视觉语言但不复制旧 Dashboard 的过期 endpoint assumptions。

**Verification:**
```bash
./.venv/Scripts/python.exe -m pytest tests/test_workspace_ui.py tests/test_workspace_api.py -q --tb=short -p no:cacheprovider
./.venv/Scripts/ruff.exe check app/workspace tests/test_workspace_ui.py --no-cache
```

---

## 6. 端到端真实数据库 + 浏览器流验收

**Objective:** 证明前端与后端联通的是同一条 governed workflow，而非独立的 mock-shaped tests。

**Files:**
- Create: `tests/test_workspace_e2e.py`
- Create (可选，若已有浏览器基础设施): `integration-tests/test_workspace_browser.py`
- Modify: `docs/PROJECT_STATUS.md`（仅在真实验收完成后更新稳定事实）
- Modify: `README.md`（只新增 `/workspace` 入口和正确范围）

**E2E fixture:** 建立项目内隔离 `COGNITIVE_DATA_DIR` 和一个 fresh operator-managed SQLite database；使用现有 hermetic GitHub transport 持久化 ResearchPackage；以测试认证 principal 走全部 HTTP command；从第二 connection/read model 读取 audit timeline。

**Acceptance assertions:**

```text
Research candidate is never automatically verified
unauthorized / forged reviewer mutation writes nothing
promotion yields only candidate Knowledge
practice before learning approval fails
approved practice persists mastery evidence
mastered signal creates only MachineKnowledge candidate
GET case/audit has zero database-write delta
UI renders timeline and actionable next state
legacy graph tables have zero writes
```

**Verification:**
```bash
./.venv/Scripts/python.exe -m pytest tests/test_workspace_e2e.py -q --tb=short -p no:cacheprovider
./.venv/Scripts/python.exe -m pytest integration-tests -q --tb=short -p no:cacheprovider
```

---

## 7. 高风险发布门禁、审查与交接

**Objective:** 因本日范围包含 authentication、HTTP mutations、SQLite governance migration、architecture/UI router，按高风险路径独立收口。

**Files:**
- Create: `workspace/intake/013_cognitive_workspace_mvp_release_handoff.md`
- Modify: `docs/PROJECT_STATUS.md`, `README.md`（仅最终事实）

**Before commit:**

```bash
./.venv/Scripts/python.exe -m pytest tests -q --tb=short -p no:cacheprovider
./.venv/Scripts/python.exe -m pytest knowledge_base/tests -q --tb=short -p no:cacheprovider
./.venv/Scripts/python.exe -m pytest integration-tests -q --tb=short -p no:cacheprovider
./.venv/Scripts/ruff.exe check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts --no-cache
./.venv/Scripts/python.exe scripts/check_architecture.py
./.venv/Scripts/python.exe scripts/check_repository_conventions.py --source worktree
git diff --check
git status --short
```

Then stage exact paths, record `git write-tree`, perform one GPT-only frozen-tree read-only review focused on auth, mutation API, migration/outbox, provenance and frontend endpoint boundaries. If the review is GO, commit/push a dedicated branch; verify `HEAD == origin/<branch>` and the exact SHA's GitHub CI. Do not auto-merge to `main`.

---

## Risks and explicit non-goals

- **Authentication availability:** if the present middleware cannot expose a trustworthy reviewer principal without a broader identity system, stop after Task 2 with a documented blocker; do not invent a `human:` prefix, bypass auth in the browser, or claim complete E2E.
- **Migration:** any required event/outbox schema must be an incremental migration through the existing governance owner, with tested backup/rollback; no direct DDL at request time.
- **External research:** today uses deterministic persisted fixtures for E2E. Live GitHub collection is not a required browser demo and must not expose credentials.
- **Frontend scope:** one server-rendered workspace route. React, desktop/mobile clients, SSE/WebSocket and multi-user collaboration are deferred.
- **Release scope:** this is a local MVP / governed checkpoint, not an Installer or public Alpha/Beta/Stable claim.
