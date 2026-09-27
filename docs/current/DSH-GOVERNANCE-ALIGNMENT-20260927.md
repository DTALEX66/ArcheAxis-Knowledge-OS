# 防漂移治理方案对齐报告（方案 ↔ 权威基座）

- 状态词：`STRUCTURAL`
- 日期：2026-09-27
- 对象：Owner 提供的《防漂移治理执行方案（Executive Summary）》（`Authority→CURRENT→Task Envelope→Machine Gate→Receipt`）
- 性质：**只读核实 + 设计对齐**。未创建 `.project/**` 任何文件，未新增 schema，未新增注册表，未新增脚本，未执行任何测试或构建。
- 结论摘要：方案的**三段检查意图（START / PRE-COMMIT / PRE-INTEGRATION）与现有 hostile gate 一致且正确**；但其中约六成产物与仓库既有权威基座重复，且有三处前提性事实错误（receipt v3、base_commit、模板即信封）必须先纠正，否则落地即产生第二权威。

---

## 0. 授权与边界登记

| 项 | 事实 | 锚点 |
| --- | --- | --- |
| 本文件写入落点 | `docs/**`，owner `documentation`，`execution_lanes` 含 `owner`，**无** `write_mode: serial-grant` ⇒ 非串行、非 protected | `DIRECTORY_AUTHORITY.yaml:446-448` |
| 依据 | 执行指令优先级第 1 档（Owner 本轮明确选择「对齐式落地」） | `docs/authority/AGENTS.vnext-governance.md:11` |
| **未**写 `.project/**` 的硬原因 | `.project/**` 被列入 `protected_files`，该 overlay 下**任何**匹配路径都需要**远端授权**，即使其自身 ownership 规则非串行；而 `.project/tasks/issued/`、`.project/leases/issued/` 当前**仅有 README** ⇒ 无已签发信封/授权 ⇒ 应停止 | `DIRECTORY_AUTHORITY.yaml:545`、`:558`；`docs/authority/AGENTS.vnext-governance.md:43-44` |
| 故方案 §5.1 的 `.project/current/CURRENT.yaml` | 不能按原设计落地——**不只是「避免重复」，而是该前缀当前无授权可达** | 同上 |
| `workspace/intake/` 登记 | 该前缀 lane 为 `migration`、`write_mode: maintenance-only-task-envelope`，仓库内亦无已签发信封。本次按 `AGENTS.md` §6.4「影响框架方向时加 intake note」惯例写入，并在此登记为**越界待裁** | `DIRECTORY_AUTHORITY.yaml:279-282` |

优先级说明：按 `docs/authority/AGENTS.vnext-governance.md:21`「低权威可收窄、不可放宽」，上表第 2 行的第 1 档指令覆盖第 4 档 `DIRECTORY_AUTHORITY` 的收窄；但 `protected_files` 的**远端授权**要求属第 4 档，本轮 Owner 指令**未**涉及 `.project/**` 写入，故一律不写。

---

## 1. 核实方法（可复现）

只读命令：`git worktree list`、`git rev-parse`、`git cat-file -t`、`git merge-base --is-ancestor`、`git ls-files`、`git log -1`。
逐文件读取：`.project/schemas/{task-envelope,task-template,task-receipt,authority-grant}.schema.json`、`.project/GATE-REGISTRY.yaml`、`.worklab/project-validation.v1.yaml`、`DIRECTORY_AUTHORITY.yaml`、`PROJECT_CONTRACT.yaml`、`docs/authority/AGENTS.vnext-governance.md`、`scripts/ci/check_vnext_receipt.py`、`tests/test_axr060_completion_audit.py`、`tests/test_ci_classifier.py`。

**未执行**：任何 pytest / cargo / dotnet / web 构建、任何 CI、任何 GUI 或运行时验证。本报告全部结论均为**源码与元数据级**证据。

---

## 2. 逐条差距映射（方案条目 → 仓库实际）

| 方案条目 | 方案产物 | 仓库实际（证据锚点） | 判定 |
| --- | --- | --- | --- |
| §1 假设「每 Agent 独立 worktree，主工作树唯一」 | — | `git worktree list` 实测 **8 个**（含 3 个 detached；此为测量时点值，其后另有新增，见 §10.1）；当时 checkout = Codex 前端分支 `69a3baed`，且带脏文件 `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` | `REFUTED` |
| §3 `gen_current.py` | 新脚本 | 不存在；但已存在 `scripts/generate_current_reports.py`（命名近撞，易混） | `PARTIAL` |
| §3 `check_drift.py` | 新脚本 | 不存在；门禁侧已有 5 个自检/hostile gate_id | `PARTIAL` |
| §3 `verify_scope.py` | 新脚本 | scope/ownership 已有**两处**权威：changed-path→risk→gates 分类表，与 gate registry 的 path_rules | `DUPLICATE` |
| §3 `enforce_receipt.py` | 新脚本 | receipt 已有 schema 且已定义**外部 CI 证明**语义（不提交进它所证明的 head） | `DUPLICATE` |
| §5.1 `CURRENT.yaml` | 新投影 | 确实不存在（`git ls-files` 无 `CURRENT.yaml`）——**真实缺口** | `ABSENT` |
| §5.2「Task Envelope 模板」 | 新模板 | 已存在**两套互斥** schema：issued 信封 与 non-authorizing 模板；模板「永不授权」 | `WRONG-CONCEPT` |
| §5.3「Lease 模板」 | 新模板 | 已存在 grant 模板 + grant schema + `leases/{templates,issued,revocations}` | `DUPLICATE` |
| §6 CI 门禁对照表 | 自造门禁名 | 已注册 35 个 gate_id；方案门禁名多数未注册 | `PARTIAL` |
| §7 负例测试矩阵 | 9 行 | 其中 1 行与**活门禁直接冲突**（见 §3.1） | `CONFLICT` |
| §8「Receipt v3 兼容」 | 迁移策略 | 前提不成立：把三个不同 schema 混成一个（见 §3.1） | `REFUTED` |
| §9 并行工作流约束 | — | 与「单切片=单泳道=单分支=单 worktree=单 owner」一致 | `SUPPORTED` |
| §10 P0/P1/P2 工期（1–2/3–5/5–7 天） | 排期 | 无证据基础，作提案可、作承诺不可 | `NOT_VERIFIED` |

---

## 3. 必须先纠正的六处事实错误

### 3.1 「Receipt v3」把三个互不相关的 schema 混成一个（最高危）

| 被混为一谈的东西 | 真实身份 | 锚点 |
| --- | --- | --- |
| task receipt | `archeaxis.task-receipt/v1`，`schema_version` const **1**；`status` enum = `PASS/FAIL/BLOCKED/NOT_EXECUTED`；语义是「针对某个 subject head 的 CI 证明，**不**提交进它证明的那个 head」 | `.project/schemas/task-receipt.schema.json:28-29`、`:25`、`:5` |
| vNext journey receipt | `archeaxis.vnext/v01-closed-loop-receipt`，且 **`schema_version` 必须 == 2**，否则拒绝 | `scripts/ci/check_vnext_receipt.py:14-17` |
| release identity schema | `2.0.0` / `3.0.0` —— 属**发布身份**，与 receipt 无关 | `scripts/release_inject_identity.py:129,147` |

**后果**：方案 §7 写「旧 Receipt v2 用在接受 v3 的校验器 → 退出码 ≠0（`schema_version 2 is not supported`）」并作为负例测试。若照此实现，会**直接打挂**现有 `check_vnext_receipt.py`（它要求 v2）。
同样地，方案 §8 要求校验 `source_tree` / `source_dirty` / `patch_sha256` —— 这三个字段在 tracked task-receipt schema 中**不存在**（该 schema 用的是 `subject_tree_sha` / `changed_paths` / `envelope_sha256` / `activation_sha`）。

### 3.2 `base_commit` 已过期且跨分支

方案 §5.2/§5.1 模板钉 `base_commit: "ee015075"`。

- `ee015075`（2026-09-27，`fix(evidence): align the receipt schema version and name each guard's failure`）**是** DSH worktree HEAD `7503195b` 的祖先。
- 它**不是**当前 checkout HEAD `69a3baed` 的祖先。
- 且 DSH worktree 自身 HEAD 已是 `7503195b`，比 `ee015075` 更新。

⇒ 该字段在写下时即已陈旧；任何按它生成的 CURRENT/Task Envelope 都会触发「stale base」类拒绝。

### 3.3 工作树与写入身份假设不成立

- 实测 8 个 worktree（测量时点；其后另有新增，见 §10.1），而非「主树唯一」。
- **当前 checkout 是 Codex 前端分支** `codex/aaos-p3-ui-convergence-20260922`，且脏文件正是 `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` —— 即方案划给 DSH 的 **deny 路径**。
- ⇒ 若在当前树按方案写入，按方案**自身规则**即构成 scope violation。方案缺少「先确认当前 worktree 身份再动手」的 START 前置检查（现有 gate 已覆盖此意图，见 §6）。

### 3.4 「模板即信封」——方案 §5.2 命名与字段不匹配任何既有 schema

`.project/schemas/task-envelope.schema.json:5` 原文：模板使用**另一个** schema，且**永不授权**。

- issued 信封：`schema` const `archeaxis.task/v1`、`state` const `issued`、`additionalProperties: false`（`:37-39`、`:7`）。
- 模板：`archeaxis.task-template/v1`、`state` const `template`，且描述明写「Scope Gate 必须把此 schema 拒为 `E001_TASK_NOT_ISSUED`」（`.project/schemas/task-template.schema.json:26-29`、`:5`）。

方案 §5.2 的字段集（`task_id/agent/owner/authority_generation/base_commit/branch/write.allow/write.deny/consumes_contracts/owner_gates`）**既不匹配 envelope 也不匹配 template** ⇒ 会造出第三个竞争 schema。

### 3.5 状态词三层混用

| 层 | 取值 | 锚点 |
| --- | --- | --- |
| 产品状态词 | `TESTED_LOCAL`、`TESTED_LOCAL_PARTIAL`、`BLOCKED_BY_OWNER_DECISION`、`STRUCTURAL`、`NOT_EXECUTED`、`NOT_VERIFIED` | 项目状态词表 |
| receipt `status` enum | `PASS` / `FAIL` / `BLOCKED` / `NOT_EXECUTED` | `.project/schemas/task-receipt.schema.json:25` |
| gate 判定政策 | `required_status_policy: only-pass-is-success` | `.project/GATE-REGISTRY.yaml:3` |

方案 §5.1 把 `qualification.required_status: TESTED_LOCAL` 放进 CURRENT 投影，等于把产品状态词塞进 receipt/gate 语义位。`docs/authority/AGENTS.vnext-governance.md:23-24` 已明定：**授权顺序 ≠ 证据等级**，同理这三层不可互换。

### 3.6 scope gate 已在 `.worklab/`，且脚本落点有实测副作用

- changed-path → risk class → gate 集已有权威分类表：`.worklab/project-validation.v1.yaml`（`schema_version: "2.0"`，`:11-13`），含 `unclassified: block-until-classified`（`:368-370`，AXC-060）。
- **副作用**：该表 `:44-53` 把 `scripts/runtime/**` 归入 `vnext-ci-policy`，改动该前缀即强制 `static, lint, rust-vnext, desktop-vnext, contracts-vnext, workers-vnext` **六条泳道**。方案 §4 把漂移脚本放进 `scripts/runtime/`，会让**每次治理脚本改动都拉起整套 vNext 门禁**。
- 另：`.project/**` 与 `.worklab/**` 归 `ci-policy`（`:67-75`，gates `static,lint`），且 `.project/**` 另受 gate registry path_rules 追加 `schema-validation, scope-gate-self-test, secret-and-vendor-state-scan`（`.project/GATE-REGISTRY.yaml:81`）。

---

## 4. 修正后的 CURRENT 投影设计（不新建注册表）

### 4.1 定位原则

1. CURRENT 是**投影**，不是权威。它必须可随时由权威文件重新生成，且**不得**成为任何检查的判定依据。
2. 权威顺序见 `docs/authority/AGENTS.vnext-governance.md:11-19`；CURRENT 落在第 5 档以下，`AGENTS.md`（第 7 档）可收窄、不可放宽。
3. **不得**写入 `.project/**`（`protected_files`，需远端授权）。
4. 不得自造字段语义；每个字段必须指向唯一权威来源。

### 4.2 字段映射（方案字段 → 权威来源）

| 方案 CURRENT.yaml 字段 | 权威来源 | 修正说明 |
| --- | --- | --- |
| `authority.project_contract_digest` | `PROJECT_CONTRACT.yaml`（`archeaxis.project-contract/v1`） | 必须先定义**规范化口径**，见 §4.3 |
| `authority.directory_authority_digest` | `DIRECTORY_AUTHORITY.yaml` | 同上 |
| `authority.product_contract_digest` | 版本化产品契约（第 5 档） | 方案未指明具体文件 ⇒ 需补 |
| `current_tasks.*.task_id` | envelope `task_id`，须匹配 `^PR-[0-9]{2,3}[A-Z]?(?:-S[0-9]{2})?$` | 方案的 `AAOS-BACKEND-R4` **不匹配**该 pattern |
| `current_tasks.*.base_commit` | envelope `subject_base_sha`（`sha40`，40 位十六进制） | 方案用 8 位缩写，不满足 schema |
| `current_tasks.*.branch` | envelope 无关字段；属 receipt `execution.branch` | 分层放错 |
| `write_ownership.*.allow` | envelope `scope.allowed_paths` | 权威在信封，投影不得自定义 |
| `write_ownership.*.deny` | envelope `scope.forbidden_paths` | 同上 |
| `shared_resources.governance` | `DIRECTORY_AUTHORITY.yaml` protected_resource + `protected_files` | 布尔开关无法表达「需远端授权」 |
| `owner_gates[]` | Owner Decision + `DECISION_SUPERSESSION_LEDGER.yaml` | 投影不得自造 gate 状态 |
| `qualification.required_status` | 产品状态词表 / gate `required_status_policy` | 见 §3.5，须拆成两个字段 |

### 4.3 未决项：digest 规范化口径（**不得擅自发明**）

仓库已有两种并存先例，二者对同一文件会给出**不同** digest：

- canonical-LF 口径：`docs/authority/taskpack-0919-r6/EXECUTOR-START.md:5` 记「user-provided **CRLF** bytes」= `dcc51e92…9529`，`:6` 记「repository **canonical LF** bytes」= `788c5d50…951b`。
- JSON 规范化口径：`digest_profile: AAK-JCS-1`（`.project/schemas/task-envelope.schema.json:158`）；receipt 的 `receipt_payload_sha256` 用 RFC 8785 canonical JSON（`.project/schemas/task-receipt.schema.json:147-150`）。

⇒ 方案直接写 `<sha256>` 而不声明口径，在多主机（Windows CRLF / Linux LF）下**必然漂移**。此项列为**待 Owner 决策**，本轮不选定。

### 4.4 存放位置建议

| 选项 | 位置 | 评价 |
| --- | --- | --- |
| a)（推荐） | `.project-local/current/` | 属 worktree scratch（`DIRECTORY_AUTHORITY.yaml:559-568` 的 ignored_local_roots 邻域）；无需授权、可随时重生成 |
| b) | 受跟踪路径 | 需先有**已签发信封** + 为该路径新增 ownership 规则，并将触发 `schema-validation`/`scope-gate-self-test` 等门禁 |
| c) | `.project/current/`（方案原设计） | **不可行**：`protected_files` 且无已签发授权 |

### 4.5 修正后的最小投影示例（**设计示意，非可签发物**）

```yaml
# 仅示意字段映射；不写入 .project/**，不作为任何检查的判定依据
schema: archeaxis.current-projection/v0   # 若需固化，须先经 Owner 决策与已签发信封
schema_version: 0
generated_from:
  project_contract: {path: PROJECT_CONTRACT.yaml, digest_profile: PENDING-OWNER-DECISION, digest: "..."}
  directory_authority: {path: DIRECTORY_AUTHORITY.yaml, digest_profile: PENDING-OWNER-DECISION, digest: "..."}
slices:
  - task_id: "PR-XX"                 # 必须匹配 ^PR-[0-9]{2,3}[A-Z]?(?:-S[0-9]{2})?$
    envelope_sha256: "..."           # 40/64 位；指向已签发信封
    subject_base_sha: "..."          # 40 位，来自信封，非手写
    execution_lane: "owner"          # 必须是 DIRECTORY_AUTHORITY 该路径规则 lane 的成员
    allowed_paths_from_envelope: []  # 一律引用信封，不在投影内自定义
    forbidden_paths_from_envelope: []
status_vocabulary:
  product_status: "STRUCTURAL"       # 产品状态词
  receipt_status: "NOT_EXECUTED"     # receipt enum
```

---

## 5. 修正后的 Task Envelope / Grant 设计

### 5.1 关键区分

| 概念 | schema | state | 能否授权 |
| --- | --- | --- | --- |
| 已签发信封 | `archeaxis.task/v1` | `issued` | 是 |
| 任务模板 | `archeaxis.task-template/v1` | `template` | **否**（Scope Gate 须拒为 `E001_TASK_NOT_ISSUED`） |

### 5.2 方案 §5.2 遗漏但 envelope schema **必填**的字段

`state, issuance_id, issuer, assignee, not_before, issued_at, expires_at, subject_base_sha, subject_base_tree, program_graph_sha256, program_acceptance_refs, program_evidence_refs, machine_requirements（含 external_waits_satisfied: true）、artifact_inputs、authority_manifest_sha256、consumed_interfaces{entries,digest_sha256}、required_gate_ids、gate_registry_sha256, work_base_policy, receipt_policy, acceptance, evidence_required, rollback`
（锚点：`.project/schemas/task-envelope.schema.json:8-19`）

另有三处硬约束方案未提：

- `scope` 必填 `allowed_operations` / `allowed_paths` / `forbidden_paths` / `limits`，且 `limits.max_files` **上限 25**（`:175-203`、`:195`）。
- `required_gate_ids` **必须等于** Gate Registry 对该 `program_task_id` 的 `task_rules` 选择（`:205-209`）。
- `work_base_policy` const `activation-commit-or-disjoint-descendant`；`receipt_policy` const `external-exact-sha-ci-attestation`（`:218-219`）。

### 5.3 方案 §5.3「Lease」→ authority-grant 映射

| 方案字段 | 真实字段 | 备注 |
| --- | --- | --- |
| `lease_id: "LEASE-GOV-20260927"` | `grant_id`，须匹配 `^GRANT-[A-Za-z0-9._-]{8,80}$` | 方案的 `LEASE-` 前缀**不匹配** |
| `owner` | `holder` | |
| `resource` | `protected_resources[]`（数组） | |
| `valid_until` | `expires_at`（RFC3339） | |
| `authority_generation` | `envelope_sha256` + `subject_base_sha` + `issuance_id` | 授权必须**绑定**到信封 |

`authority-grant.schema.json:5-6` 明定：该授权与「Git-common-dir 协调锁」是**两回事**（后者仅同机协调，`DIRECTORY_AUTHORITY.yaml:569-577`）。
且 `docs/authority/AGENTS.vnext-governance.md:43-44` 要求：若信封/授权缺失、被撤销、**是模板**、自改、绑定错误 subject SHA 或**脱离 Program 图**，则停止 —— 方案的独立 lease（不绑定 envelope_sha256）正落在「脱离 Program 图」。

---

## 6. CI 门禁对照表（修正版）

已注册 gate_id 共 35 个（`.project/GATE-REGISTRY.yaml:5-39`）。方案 §6 的门禁名绝大多数**未注册**：

| 方案门禁名 | 已注册对应 | 判定 |
| --- | --- | --- |
| `cargo fmt/check` | 无独立 gate_id；`rust-quality-suite` 覆盖质量 | 部分缺口（根 workspace fmt **目前无 gate**，见 §8） |
| `ruff` | `lint` | 等价 |
| `openapi-diff` | `backward-compatibility-check` / `openapi-lint` | 等价（改名） |
| `mypy` | **未注册** | 缺口，需决策 |
| `pytest tests/backend`（"240+"） | `python-quality-suite` | 等价；"240+" 是历史回执数字，**不是**门禁定义 |
| `pytest tests/migration` | `persistence-integrity-migration` | 等价 |
| `check_runtime.py` | 未注册同名；对应 `runtime-protocol-lifecycle` / `release-artifact-identity` | 改名 |
| 「候选资格」收敛脚本 | `full-qualification-receipt-tests` / `exact-sha-promotion-rejection` | 等价 |
| 「架构边界」静态扫描 | `check_architecture` / `check_language_boundaries`（脚本层）+ `lint` | 部分 |
| — | **方案完全未提但已注册**：`scope-gate-self-test`、`stale-base-rejection`、`self-escalation-rejection`、`protected-path-without-grant-rejection`（`:14-17`） | **这四条正是方案 §3 START 检查想做的事** |
| `dotnet-desktop-quality` | 方案未提 | 补齐 |
| `csharp/rust/python-generation-drift`、`three-language-canonical-fixtures` | 方案未提 | 补齐 |

**结论**：方案 §3 的三段检查应**复用**上述四个 hostile gate_id，而不是新造 `check_drift.py` 与自造错误文案。

---

## 7. 负例测试矩阵（修正版）

| 方案行 | 判定 | 修正 |
| --- | --- | --- |
| 干净运行 → `TESTED_LOCAL` | 保留但改词 | receipt `status` 用 `PASS`；`TESTED_LOCAL` 是**产品**状态词 |
| START 未签发 → 自造文案「Authority not stable」 | 改写 | 复用 `protected-path-without-grant-rejection`；既有错误码先例 `E001_TASK_NOT_ISSUED` |
| base commit 不符 → 「Base commit mismatch」 | 改写 | 复用 `stale-base-rejection` |
| 范围外路径 → 「Scope violation」 | 保留 | 落 `.worklab` 分类（`unclassified: block-until-classified`）+ `scope-gate-self-test` |
| 未申请 Lease → 警告/拒绝 | 改写 | 语义即 `protected-path-without-grant-rejection` |
| Authority 变动 → 「Authority drift」 | 保留 | **前置**：先定 digest 口径（§4.3） |
| 旧 Receipt v2 被拒 | **删除** | 与活门禁直接冲突：`check_vnext_receipt.py:15` 要求 v2（§3.1） |
| 缺失 `python.exe` → 明确报错 | 保留 | 与提交 `7503195b` 主题一致（该修复已在 DSH worktree） |
| Windows `os.mkdir(0o700)` 权限失配 | 未验证 | 本轮不判定 |

---

## 8. 未执行 / 未验证 / 待 Owner 决策

**未执行**：任何 pytest / cargo / dotnet / wheel / CI / GUI / 真实语料 / 真实模型验证。本报告不提升任何产品状态。

**未创建**：`.project/**` 下任何文件、任何新 schema、任何新注册表、任何新脚本、任何 CI 门禁定义。

**待 Owner 决策（4 项）**：

1. digest 规范化口径（canonical-LF vs AAK-JCS-1 vs RFC 8785）—— 直接决定 CURRENT 是否会在跨主机漂移。
2. CURRENT 投影的落地位置（`.project-local/current/` 受忽略 vs 受跟踪路径）。
3. `mypy` 是否设独立 gate（当前未注册）。
4. `workspace/intake/` 在无已签发信封下的写权限（本文件旁边的 intake note 已按 `AGENTS.md` §6.4 惯例写入，登记为越界待裁）。

**已知但未闭合（引自仓库既有申报，本轮未复核）**：根 workspace `cargo fmt --all -- --check` 无任何 gate 覆盖（CI 中唯一 `cargo fmt` 位于被根 workspace 排除的 `src-tauri`）。本轮**未**复跑该命令，故仅作转述、不作结论。

---

## 9. 回滚

删除本文件与同批 intake note 即可；无其他文件被修改。

本分支已隔离到独立 worktree，完整回滚还需一步：`git worktree remove .project-local/worktrees/dsh-governance-20260927`。删除**远端**分支是独立的破坏性副作用，需单独授权，本报告未执行也未建议自动执行。

回滚后主 worktree 的 `git status --short` 应回到基线（仅 `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` 的既存 EOL-only 脏 + 既存 `docs/history/**` 未跟踪物）。

---

## 10. 并发写入实测事件、隔离处置与协调缺口（会话内追加）

### 10.1 实测事件（全部为命令输出，非推测）

| 时点 | 观测 | 含义 |
| --- | --- | --- |
| 本次 fetch 后 | `HEAD` = `69a3baed` = `origin/main` = `origin/codex/aaos-p3-ui-convergence-20260922` | 三 ref 同 SHA、零分叉 |
| 随后创建分支时 | `HEAD` 已变为 `43c2cafa`（`docs(dsh): add a self-contained audit prompt for third-party review`） | **同一窗口期内另一写入者提交了它** |
| 再 fetch 后 | `origin/main` 与 `origin/codex/…` 均已为 `43c2cafa` | 该提交**已被推送到远端** |
| 数分钟后 | `git worktree list` 新增 `.project-local/worktrees/dsh-backend-r5`（`7503195b`，分支 `dsh/backend-r5`），此前不存在 | 并发活动**仍在继续** |

结论：本检出上存在**至少一个并发写入者**。把新分支直接创建在主 worktree，等于与它共享检出与 HEAD。

### 10.2 处置：一分支一 worktree

依 `docs/authority/AGENTS.vnext-governance.md:51-53`（单切片 = 单泳道 = 单分支 = **单 worktree** = 单 owner）与 `DIRECTORY_AUTHORITY.yaml:560`（`.project-local/worktrees/` 属 `ignored_local_roots`）：

- 主 worktree `D:/All projects/ArcheAxis-Knowledge-OS` 已切回 `codex/aaos-p3-ui-convergence-20260922` @ `43c2cafa`；其既存脏文件 `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` 未受影响。
- 本分支隔离至 `.project-local/worktrees/dsh-governance-20260927`，实测 `branch = dsh/governance-drift-alignment-20260927`、`HEAD = a0b0ef5a` = `origin/dsh/governance-drift-alignment-20260927`、`git status --porcelain` 为空。
- 本任务后续写入**仅**发生在该 worktree 内。

### 10.3 协调缺口（本报告的新增关键发现）

`DIRECTORY_AUTHORITY.yaml:569-577` 与 `docs/authority/AGENTS.vnext-governance.md:41-42` 声明同机协调后端为 `git-common-dir/archeaxis-agent/state.sqlite`，用途明列 `local-coordination-locks`、`active-task-ownership`、`worktree-heartbeats`。

实测结果：

- `git rev-parse --git-common-dir` = `.git`，而 `.git/archeaxis-agent/` **不存在**。
- `scripts/**` 全量检索 `archeaxis-agent`、`state.sqlite`、`coordination-lock`：**零命中**。

⇒ 「不要并发写入」目前**没有任何机器保障**，只能依赖 Agent 自觉；这正是 10.1 的碰撞得以发生、且未被任何门禁拦下的原因。该缺口定为 `STRUCTURAL`，**本报告未自行补建**（补建需已签发信封，以及 `.project/**` 或 `scripts/**` 的写入授权）。

### 10.4 建议（本轮未实施）

1. 若要把「禁止并发写入」变成**强制**约束：实现该**已声明**的协调后端并提供 CLI（登记 / 心跳 / 超时回收），再把「检出身份与登记不匹配即拒绝」接入 START 检查。这恰是原方案 §3 的**意图**，但落点应是这个已声明的后端，而非另造 lease 文件。
2. 在新后端落地前，最低成本、且已被本仓库规则支持的约束是：**每个写入者一个 worktree + 一条分支**，并在交接文档首行登记 worktree 身份与 `worktree_id` —— 后者正是 `.project/schemas/task-receipt.schema.json:75` 的既有字段。
