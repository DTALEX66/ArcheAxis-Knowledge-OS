# AAOS 接管检查点 — 2026-09-26（DSH / DeepSeek 执行）

- 仓库：`DTALEX66/ArcheAxis-Knowledge-OS`
- 分支：`codex/aaos-p3-ui-convergence-20260922`
- 本检查点 HEAD：`14a2788c5fa03233473fbcd0877cc042c6815f3e`（本地 = 远端）
- 对应 CI：[run 36239548637](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36239548637) — **success**（`gateplan` / `lint` / **`test (3.12)`** / `a0-gates` 全部 success）
- 证据等级：`EXACT_SHA_CI` + `TESTED_LOCAL`（3351 passed / 0 failed）

## CURRENT_STATE

接管基线（只读核对，非历史报告数字）：

| 项 | 实测值 |
| --- | --- |
| cwd / toplevel | `D:\All projects\ArcheAxis-Knowledge-OS` |
| branch | `codex/aaos-p3-ui-convergence-20260922` |
| HEAD / tree | `14a2788c…` / `ca69e860…`（接管时为 `8da5dca0` / `ca69e860`） |
| 已跟踪改动 | **无**（`git status --porcelain=v1 -uno` 为空） |
| worktree | 5 个（主 + `.project-local/worktrees/{dp-f01-20260925,v3-era,verify-0c9c,worker-quality-0906}`） |
| git | 2.54.0.windows.1 |
| 远端 main | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`（交接核验时同值） |

**与交接快照的增量**：接管时 HEAD 为 `8da5dca0`；本轮新增 `14a2788c`（见 DONE）。`origin/main` 未变动。

## DONE（本轮，已推送并 CI 验证）

**D-6 冻结类分支复审 → 本地分支 27 收敛至 7**

对审计记录中**非捐赠者**的保留类分支做实质复审（判据同上：新增路径中 HEAD 不存在的数量），并据复审结果处置：

**已复审并删除（5 条）**：

| 分支 | 处置类别 | 复审结论 |
| --- | --- | --- |
| `feat/archeaxis-desktop-a1-violet-core` | `FROZEN_WEB_UI_REFERENCE_REASSESS` | 3 新增 / 2 缺失（2026-07-28 记录 + requirements 清单）→ 归档后删除 |
| `feat/axw022a-pdf-http-endpoint` | 同上 | PDF 能力已在 HEAD 由 Rust Core 提供；分支是 React/Tauri 网页侧实现（含 pdfjs 第三方资产）→ 归档后删除 |
| `feat/axw022b-evidence-annotation` | 同上 | **3→0 缺失**，完全已吸收，无需归档 |
| `codex/recovery-shell-frontend` | `FROZEN_LEGACY_REACT_TAURI_REFERENCE_NO_MERGE` | 4 新增 / **0 缺失** → 已吸收，删除 |
| `release/v0.4.0-contract` | `HISTORICAL_RELEASE_...RETAIN_EVIDENCE` | **0 新增 / 0 缺失** → 已吸收，删除（远端同名分支保留） |

**复审后确认保留（3 条）** —— 它们**确有 HEAD 中不存在的独有内容**，且审计记录明确要求作为证据保留：

| 分支 | 独有路径 | 记录裁定 |
| --- | --- | --- |
| `codex/frozen-roadmap-deepseek-v1` | 130 新增 / **118 缺失** | `HISTORICAL_RELEASE_OR_ROADMAP_FREEZE_RETAIN_EVIDENCE` |
| `codex/execution-reliability-standards` | 3 新增 / 3 缺失 | `HISTORICAL_GOVERNANCE_EVIDENCE_CROSSWALK_ONLY` |
| `docs/verification-summary-2026-08-09` | 1 新增 / 1 缺失 | `HISTORICAL_GOVERNANCE_EVIDENCE_CROSSWALK_ONLY` |

**最终 7 条本地分支及其保留理由**：

| 分支 | 理由 |
| --- | --- |
| `codex/aaos-p3-ui-convergence-20260922` | 活跃分支 |
| `codex/dp-f01-20260925` | worktree 占用 |
| `codex/worker-quality-0906` | worktree 占用 |
| `main` | `merge-base == tip`（HEAD 祖先），本地规范引用 |
| `codex/frozen-roadmap-deepseek-v1` | 118 条独有路径；记录为保留证据 |
| `codex/execution-reliability-standards` | 3 条独有路径；记录为保留证据 |
| `docs/verification-summary-2026-08-09` | 1 条独有路径；记录为保留证据 |

**关键性质：删除分支不丢内容。** 实测 5 个新删分支的 tip 对象**全部仍可达**（`cat-file -t` 均为 `commit`），`git branch <name> <sha>` 即可恢复。归档台账存于 `.project-local/tmp/`，SHA 亦记入 `docs/history/branch-donors/README.md`。

**D-5 legacy 类 10 条捐赠者分支复审 → 7 条已吸收删除、3 条归档后删除**

同一判据（新增路径中 HEAD 不存在的数量）：

| 分支 | 新增路径不在 HEAD | 处置 |
| --- | --- | --- |
| `audit/unreleased-real-version` | 0 | 已吸收 → 删除 |
| `axw/execution-h0` | 0 | 已吸收 → 删除 |
| `axw/execution-h1` | 0 | 已吸收 → 删除 |
| `chore/naming-repo-refs` | 0 | 已吸收 → 删除 |
| `feat/ms00-c-release-identity` | 0 | 已吸收 → 删除 |
| `feat/naming-step3` | 0 | 已吸收 → 删除 |
| `work/tp12-facades` | 0 | 已吸收 → 删除 |
| `feat/p1-compat-kernel-hardening` | 3 | 归档后删除 |
| `feat/portable-data-root` | 3 | 归档后删除 |
| `fix/desktop-close-request-destroy` | 1 | 归档后删除 |

**3 条有 HEAD 缺失路径的分支，逐条核实为「历史资产」而非「能力缺口」**：

- `feat/p1-compat-kernel-hardening`：`tests/test_format_capabilities.py` 已被 HEAD 的 4 个格式测试取代（`test_format_execution_v1`、`test_format_matrix`、`test_text_format_facts`、`test_workspace_pipeline_multiformat`）；另两个是 2026-08-09 的 dated intake 记录。
- `feat/portable-data-root`：`scripts/project_env.{bat,ps1,sh}` 是**已退役机制**——脚本头写的是**前身项目 `Cognitive-Loop-OS`**，运行时根为 `.hermes\task-runtime`，设 `COGNITIVE_DATA_DIR`；HEAD 已用 `config/profiles/portable-stable.yaml`（`data_policy: portable-root-only`）+ `scripts/runtime/dev.py` 的 `.project-local/` 取代。恢复它们会重新引入**已退役的项目名与运行时根**。
- `fix/desktop-close-request-destroy`：仅一份 2026-08-06 的 NSIS 交接记录。

**归档而非丢弃**：7 个独有文件已按**原始字节**存入 `docs/history/branch-donors/<branch>/<原相对路径>`，并附 `README.md` 记录来源分支、tip SHA、复审理由与恢复命令。实测 7/7 **EXACT**（`cat-file blob` 与磁盘逐字节比对）。

**本地分支 22 → 12**。剩余 12 条**全部有保留理由**，无可删：

| 分类 | 分支 |
| --- | --- |
| 活跃分支 | `codex/aaos-p3-ui-convergence-20260922` |
| 工作树占用 | `codex/dp-f01-20260925`、`codex/worker-quality-0906` |
| 祖先/主干 | `main` |
| 历史证据保留 | `codex/execution-reliability-standards`、`codex/frozen-roadmap-deepseek-v1`、`docs/verification-summary-2026-08-09`、`release/v0.4.0-contract` |
| 冻结参考（不合并） | `codex/recovery-shell-frontend`、`feat/archeaxis-desktop-a1-violet-core`、`feat/axw022a-pdf-http-endpoint`、`feat/axw022b-evidence-annotation` |

**删除后验证**：HEAD 未变、3 个 worktree 未受影响、全套 **3353 passed / 0 failed**。

**D-4 capability 类 5 条捐赠者分支语义复审 → 判定**已吸收**，已删除**

判据：分支引入的**新增路径**中，有多少在 HEAD 中**不存在**（净新增）。用 `git diff --diff-filter=A merge-base..branch` 后逐路径以 `git cat-file -e HEAD:<path>` 核实。

| 分支 | 新增路径 | HEAD 中不存在 | 结论 |
| --- | --- | --- | --- |
| `feat/h2-bakeoff` | 4 | **0** | 4 文件全在 HEAD（`shared/bakeoff.py`、`bakeoff_engines.py`、`audio_vad.py`、`tests/test_h2_bakeoff.py`），且 `app/ingestion/media_adapter.py` 消费之 → 已吸收 |
| `feat/h2-pipeline-integration` | 1 | **0** | 已吸收 |
| `feat/absorption-adopt-now` | 14 | **0** | 已吸收 |
| `feat/absorption-roadmap-r0` | 35 | **0** | 已吸收 |
| `agent/phase5-research-knowledge-governance` | 5 | **4** | 2026-07-20 的早期检查点；HEAD 已有**显著更成熟**的等价实现 → 被超越 |

**不移植 phase5 的理由**（这是本条最重要的判断）：

- 分支：`shared/knowledge_migration.py` **10,684 B**、`app/adapters/research_knowledge.py`。
- HEAD：`shared/knowledge_governance_migration.py` **30,374 B**（含 `_recorded_versions`、`_actual_owned_schema_objects`、`_validate_schema`）、`app/adapters/claim.py` + `research_package.py`。
- HEAD 另有 5 个治理测试：`test_research_knowledge_approval_contract`、`test_research_knowledge_governance_lifecycle`、`test_research_to_knowledge_promotion`、`test_knowledge_governance_migration`、`test_knowledge_governance_schema_tamper`；HEAD 研究相关测试共约 10 个。

移植该分支会把**较不成熟的旧实现**与 HEAD 已有实现**并存**，制造双实现——正是本项目明令禁止的。故判定为「已被超越」，不移植。

**执行与恢复**：删除前归档 tip SHA 至 `.project-local/tmp/deleted-branches-20260926.tsv`；本地分支 **27 → 22**。

| 分支 | tip SHA（可恢复） |
| --- | --- |
| `feat/h2-bakeoff` | `376fb8001a0a7f2e2c25a0174e1dee6601d0b95b` |
| `feat/h2-pipeline-integration` | `e1df9279fde0dd0665d4765c18b8a3d1c7ae443b` |
| `feat/absorption-adopt-now` | `081cf20a28152c271155b6c3d524550ffc545ced` |
| `feat/absorption-roadmap-r0` | `42d13c0b748243235f9ffbff3e3394b76196b368` |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa94209ccded6aa993c89c581bbfd00227` |

恢复命令：`git branch <name> <tip_sha>`（实测 5 个对象**均仍可达**，`cat-file -t` 全为 `commit`）。

**删除后验证**：HEAD 未变、3 个 worktree 未受影响、能力相关测试 **21 passed**。

**剩余 10 条 `LEGACY_CODE_DONOR_*` 分支尚未复审**（legacy 代码捐赠者），留待下一轮。

**D-3 分支审计核实（结论：审计已完成，且**未授权删除任何分支**）**

以仓库内**已有的结构化审计记录** `docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`（33 条，覆盖全部 27 个现存本地分支 + 6 个已删引用）为权威基数复核：

| 项 | 实测 |
| --- | --- |
| 审计记录条目 | **33** |
| 当前本地分支 | **27**（全部在审计记录内，无遗漏、无新增） |
| `merge_delete_authorized` | **`False` = 32，`True` = 1**（该 1 条为 `audit/r5-independent-audit-20260919`，其引用**已删除**） |

处置分类（记录原文）：

| 条数 | disposition |
| --- | --- |
| 10 | `LEGACY_CODE_DONOR_REVIEW_AGAINST_R6_BEFORE_ANY_PORT` |
| 6 | `HISTORICAL_RELEASE_OR_ROADMAP_FREEZE_RETAIN_EVIDENCE` |
| 5 | `CAPABILITY_DONOR_REVIEW_AGAINST_R6_BEFORE_ANY_PORT` |
| 3 | `FROZEN_WEB_UI_REFERENCE_REASSESS_AAVALONIA_CONTRACTS` |
| 2 | `HISTORICAL_GOVERNANCE_EVIDENCE_CROSSWALK_ONLY` |
| 2 | `FROZEN_LEGACY_REACT_TAURI_REFERENCE_NO_MERGE` |
| 2 | `ANCESTOR_OR_ATTACHED_WORKTREE_REQUIRES_CUSTODY` |
| 1 | `LOCAL_REF_DELETED_PATCH_EQUIVALENT_CONTENT_RETAINED` |
| 1 | `CURRENT_ACTIVE_BRANCH` |
| 1 | `DSH_F01_PATCH_EQUIVALENT_TO_CURRENT_HEAD; RETAIN_WORKTREE_PENDING_CUSTODY_READBACK` |

**因此没有任何分支属于「没用的」。** 每一条要么是**待审代码/能力捐赠者**（需先对 R6 做语义复审再决定是否移植），要么是**必须保留的历史证据**，要么是**活跃工作树**。这也解释了为何 `git branch -d` 对全部候选都返回 *not fully merged* —— 它们确实不是快进关系。

**过程留痕（含我自己的失误）**：我用 `git diff branch HEAD` 与 `git diff --name-status` 做判据，两次得到**自相矛盾**的信号（例如把 `codex/worker-quality-0906` 先判为「独有提交 0 的 HEAD 祖先」、又读出「1055 个路径差异」）。

根因：对**祖先分支**，`git diff branch HEAD` 显示的是 **HEAD 自身 1112 个提交的演化**，不是该分支独有的内容；正确判据是比较 **merge-base..branch**（分支真正引入的内容）。

决定性核实：`merge-base(codex/worker-quality-0906, HEAD) == 该分支 tip`（`4ca46eaf`）→ 分支独有提交 **0**，确为 HEAD 祖先。**未执行任何删除。**

**D-2 路由契约与真实 Core 对齐** — `a473267a`

`config/desktop/routes-v1.json` 声明 `machine_assets -> /api/v1/machine/assets`，而**该 Core 路由从来不存在**。`R6-EXECUTION.md:977` 早已记录此不一致（"The declared desktop route entries `/api/v1/knowledge` and `/api/v1/machine/assets` do not have matching current Rust read routes"）并决定不引入投机调用——**契约本身从未被调和**。

这使契约承诺了 canonical writer 从不提供的投影，也违反了该文件自己的测试所守护的原则（`test_unavailable_domains_are_not_declared_as_core_readiness_routes`：只有真实存在的 Core 投影才能被声明）。

调和结果：

- `page_id` `machine_assets` → `machine_growth`，与真实桌面 section 一致（`SetSection("machine-growth", …)`），也与其他 page_id 的既有惯例一致（它们本就跟随 shell 的 section）。
- `core_endpoint` → `/api/v1/machine/tasks/{task_id}` —— Core 确实提供、且桌面唯一实际调用的 machine 端点（`MainWindow.axaml.cs:2559`）。

新增回归 `test_every_declared_core_endpoint_exists_in_the_router`：解析真实 Axum 路由表，要求契约声明的每个端点都能解析到真实路由。**RED 已验证**：把 `/api/v1/machine/assets` 注回后失败于
`manifest declares endpoints Core does not serve: [('machine_growth', '/api/v1/machine/assets')]`。

CI @ `a473267a`：`gateplan` ✓ `lint` ✓ `test (3.12)` ✓ **`contracts-vnext` ✓** `a0-gates` ✓；`vnext-ci/cargo-test` ✓。

**D-1 `test_axr060` 校验边界修复** — `14a2788c`

复核 `5819cace` 中的实现，确认提示词列出的缺陷真实存在，其中第 3 条是**可利用漏洞**：

- 旧实现按文件前 600 字符的正文标记识别收据，**无路径限制**，且对所有表面生效。
- 在隔离 fixture 上验证：`SYSTEM_BOUNDARY.md` 内放入 `FROZEN AUDIT SNAPSHOT / NON-AUTHORITY` 标记后，其中的伪造 40 位 ID **对旧算法不可见**（`False`），对**新算法可见**（`True`）。
- 同一对比在真实仓库上运行：两者覆盖**完全相同的 246 个标识符**（差异 0）→ 修复无副作用。

修复内容：

1. 锁定表面（`SYSTEM_BOUNDARY.md`、`reports/current/`）**永不可豁免**；路径判定先于任何正文读取。
2. 收据豁免需同时满足**获准目录** + **精确 `schema_version` 值**；`aaos-` 前缀不再构成通行证。
3. 分类器接受显式 `root`，可测试且不能被模块常量改写（这本身是第二个真实缺陷：旧实现用模块级 ROOT，在任意 root 下恒返回 None）。
4. 远端探测加**有界超时**并区分结局；明确 `ls-remote` 只描述远端**当前**状态，**不能**证明分支曾经存在。
5. 保留既有优化（批量 `cat-file --batch-check`、单次 `ls-remote`），未退回逐 SHA/逐分支子进程。

新增 9 项回归（A / A2 / B / C / D / E / E2 / F / G），反例只放隔离 tmp fixture，未污染正式 current 文档。

## DONE（承接自上一轮，未重新修改）

尾随空格 lint、`install_builtin` 协议化、已提交文档/契约缺口、流式导入断言、适配器名称、`desktop_launch` 边界、GC、10 文件恢复 —— 均按提示词要求**默认关闭**，仅在其出现新复现证据时才重开。

## OPEN

**O-1 路由契约与真实导航的**剩余**差异**（`machine_assets` 幻影端点已由 D-2 修复）

已修复的部分：`machine_assets` → `machine_growth` + 真实端点（见 D-2）。

**仍存在的差异**（需 Owner 裁定权威侧）：

| 来源 | 内容 |
| --- | --- |
| `config/desktop/routes-v1.json`（已修正后） | **7 个 page_id**：`knowledge`、`source_reader`、`learning`、`jobs`、`machine_growth`、`settings`、`recovery` |
| `MainWindow.axaml.cs` 实际 `SetSection(...)` | **16 个 section**：`home`、`capture`、`library`、`source-reader`、`knowledge`、`learning`、`evidence`、`research`、`original-editor`、`memory-map`、`machine-growth`、`jobs`、`plugins`、`models`、`settings`、`recovery` |

具体：

- `home`、`capture`、`library`、`evidence`、`research`、`original-editor`、`memory-map`、`plugins`、`models` **未在契约中登记**。
- `source_reader` 与真实 section 名 `source-reader` 命名不一致。
- 契约 `page_id` 是**封闭 Literal** 且 `routes` 要求 `min_length=7`，扩展它需要同时改 Pydantic 契约 + JSON schema + 测试。
- 其中 `research`/`plugins`/`models` 已被既有测试确立为**诚实不可用占位**（不调用 Core），把它们登记进契约需要 `core_endpoint` 变为可选——那是一次**契约语义变更**，故不擅自执行。

裁定：`PROPOSED` —— 需要 Owner 确认哪一侧是权威（把契约扩到真实导航，或把导航收敛到契约）。**未擅自改动任一侧**。

**O-2 正式 UI 纵向切片**

- 正式实现：`apps/ArcheAxis.Desktop/`（C#/Avalonia，中文优先，黑底白灰深色基线）。
- 现有：`MainWindow.axaml` 810 行 + `MainWindow.axaml.cs` 4727 行、`Themes/AaosTheme.axaml`、已拆出 `Views/SourceReaderView` 与 `Views/EvidenceCenterView`、`Contracts/Generated/Vocabulary.g.cs`。
- 待做：以 O-1 裁定后的权威路线表为准建立**完整页面清单**（不得套用旧 12 页面列表），再实现「启动 → Capture → 导入反馈 → Reader/Evidence → 知识绑定 → 学习/Review → 重启读回」的高质量切片。该切片必须达到最终界面质量，不是先交裸原型。

**O-3 设计资产缺失** — `UNVERIFIED_REFERENCE`

仓库内**未找到** `DESIGN-SPEC`、`B10`、`B09` 资产文件。提示词要求的「实际查找 B10/B09 资产和当前 DESIGN-SPEC」结果为：**不存在**。按规则记为 `UNVERIFIED_REFERENCE`，**不自行生成替代图**后宣称一比一还原。现有设计权威为 `config/product/UI_CONTRACT_V2.json`、`docs/current/UI_V3_PRODUCT_ROADMAP.md`、`docs/current/AAOS_VISUAL_QA.md`、`docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md`。

## BLOCKED

**B-1 main/nightly 集成 —— `BLOCKED_BY_OWNER`**

本地依赖核对已完成（只读，未写 main）：

- `origin/main` 是 HEAD 的**祖先**：`git rev-list --left-right --count origin/main...HEAD` = **`0  187`** → 积分是**纯快进**，无需 merge，无冲突面。
- 集成门禁计划（`scripts/ci/classify.py`，215 个变更文件，`unknown_paths: []`）：

```
ci-verdict, contracts-vnext, desktop-build, desktop-fast, desktop-vnext,
format-targeted, installer-lifecycle, lint, py-primary, release-verify,
rust-vnext, security-targeted, static, wheel-smoke, workers-vnext
```

- **关键差异**：当前分支 CI 只实际运行 `gateplan` / `lint` / `test (3.12)` / `a0-gates`；上列 `rust-vnext`、`desktop-vnext`、`contracts-vnext`、`workers-vnext`、`installer-lifecycle`、`wheel-smoke`、`security-targeted`、`format-targeted` 在本轮分支运行中均为 **SKIPPED**，**未验证**。
- 因此：**分支修复已验证 ≠ main 集成完成 ≠ main 新 SHA 的 nightly 已通过**。本轮**未**更新 main、未建 PR、未碰 release 守卫。
- 需要的授权：Owner 明确的 main 集成授权（快进或 PR）。

**B-2 平台覆盖** — 本机为 Windows；`macos` / `windows` 运行时、桌面构建、安装器生命周期作业在本轮为 **SKIPPED / NOT_RUN**，不得把 Linux Python CI 推广为 Windows/macOS 通过。

## DECISIONS

| ID | 决策 | 依据 |
| --- | --- | --- |
| DEC-1 | 锁定表面优先于正文标记：路径判定先行 | `SYSTEM_BOUNDARY.md` 加标记即可自我豁免是**可利用漏洞**，已用隔离 fixture 复现 |
| DEC-2 | 收据豁免用**精确 schema 白名单**，非 `aaos-` 前缀 | 前缀会开出一张通用免检通行证 |
| DEC-3 | 分类器改为显式 `root` 参数 | 旧实现依赖模块常量，导致任意 root 下不可用且不可测 |
| DEC-4 | `ls-remote` 只支持「当前未公布」，不足以证明「已删除」 | 远端探测无法回溯历史；错误分类须显式失败而非静默通过 |
| DEC-5 | 补 `contract-bearing-docs` 风险类（仅精确路径） | `docs/PROJECT_STATUS.md` 等被契约测试断言，却只跑 `[static]`；宽 glob 会迫使所有散文改动跑主套件 |
| DEC-6 | main 集成**不执行**，记 `BLOCKED_BY_OWNER` | 本提示词明确「不新增 merge/push 权限」 |
| DEC-7 | 不生成 B10/B09/DESIGN-SPEC 替代资产 | 资产不存在 → `UNVERIFIED_REFERENCE`，自造会变成假的一比一宣称 |

## ERRORS

| ID | 现象 | 根因 | 影响 | 修复 | 防复发 |
| --- | --- | --- | --- | --- | --- |
| ERR-1 | 规范检查报 `tests/test_axr060_completion_audit.py: crlf` | **本文件的编辑工具把全文统一写成 CRLF**；HEAD 中该文件本来只有 311 个 CRLF（混合行尾），被改成 547 个纯 CRLF | 会阻塞 CI `lint` | 将该文件规范化为 LF（547 → 0 CRLF） | 改动后先跑 `check_repository_conventions.py --source worktree` 再提交 |
| ERR-2 | `test_docs_only_classifies_static` 失败 | 该测试用 `docs/PROJECT_STATUS.md` 作为「纯文档」示例，而它**实际被契约测试断言** | 分类修正被过时示例挡住 | 改为真正普通文档 `docs/history/notes.md`，并新增 `contract-bearing-docs` 回归 | 分类变更必须同时更新承受该分类的测试示例 |
| ERR-3 | `config/desktop/routes-v1.json` 一度变成 **UTF-8 BOM**，全部 JSON 解析失败 | 用 PowerShell `Set-Content -Encoding utf8` 写该文件时写入 BOM | 会破坏契约与其全部测试 | 用 Python 以字节方式剥离 BOM 并复核解析 | **不要用 PowerShell `Set-Content` 改仓库内的 JSON/源码**；用 Python 字节写入 |
| ERR-4 | 同一文件随后变成 **CRLF**；`tests/test_desktop_routes_v1.py` 亦然 | 编辑/写入工具统一按 CRLF 落盘，而 HEAD 中这些文件是 LF | 会阻塞 CI `lint`（与 ERR-1 同类） | 全部规范化为 LF，`git diff --stat` 复核为**仅 1 行/必要行**差异 | 每次写文件后立刻查 `CRLF` 计数；提交前跑 `check_repository_conventions.py --source worktree` |

未解决但已记录：`crates/archeaxis-api/tests/maintenance_cli.rs` 的 CRLF 是**既存且本轮未触碰**；CI 的 `--source head` 检查历史通过，`--source worktree` 会报。本轮未处理（不在授权范围）。

## EVIDENCE

| 证据 | 位置 / 标识 |
| --- | --- |
| exact-SHA CI（全绿） | run `36239548637` @ `14a2788c` |
| 全绿 run 的作业结论 | `gateplan` ✓ `lint` ✓ `test (3.12)` ✓ `a0-gates` ✓ |
| 本地全套 | 3351 passed / 46 skipped / 0 failed |
| 边界修复 RED 反证 | 隔离 fixture：旧算法 `False` / 新算法 `True`；真实仓库覆盖差异 0（246 == 246） |
| 集成门禁计划 | `scripts/ci/classify.py --paths <215 files>` → `unknown_paths: []`，`full_qualification: false` |
| 门禁注册表 | `.worklab/gate-registry.v1.yaml`；聚合门 `a0-gates` |
| 运行输出根 | `.project-local/runs/`（各次 run id 见执行输出） |

## NEXT（新会话可直接接续，勿重复已完成项）

0. **分支审计已核实完成**（D-3）：33 条记录、`merge_delete_authorized=False` 共 32 条，**无可删分支**。下一步不是删除，而是按记录逐条做**语义复审**：对 15 条 `*_DONOR_REVIEW_AGAINST_R6_BEFORE_ANY_PORT`（10 legacy + 5 capability）判定是否移植 R6 缺失能力；对 6 条 `HISTORICAL_*RETAIN_EVIDENCE` 保持保留。**不要**用 `git branch -D` 绕过记录。
1. **O-1**：接通路由契约剩余漂移（契约 7 page_id vs shell 16 section；`page_id` 为封闭 Literal、`routes` 有 `min_length=7`；`research`/`plugins`/`models` 是诚实不可用占位，登记它们需把 `core_endpoint` 变可选——属契约语义变更，需裁定）。
2. **O-2**：从当前实际路由建立完整页面清单，再实现纵向切片（启动 → Capture → 导入反馈 → Reader/Evidence → 知识绑定 → 学习/Review → 重启读回）。每步先跑最小相关测试。
3. **O-3**：向 Owner 确认 B10/B09/DESIGN-SPEC 是否存在于仓库之外；在确认前保持 `UNVERIFIED_REFERENCE`。
4. **B-1**：取得 Owner 授权后再执行 main 快进/PR，并对新 main SHA 取 exact-SHA 证据；**不得**用旧 SHA 的结果声称新 main 已验证。
5. **B-2**：Windows/macOS 原生验收需相应环境；不得用 Linux CI 代替。

### 复现命令

```powershell
# 基线
git rev-parse HEAD; git rev-parse "HEAD^{tree}"; git status --porcelain=v1 -uno
git rev-list --left-right --count origin/main...HEAD

# 契约/分类回归
.\scripts\ci\run_tests.ps1 tests/test_axr060_completion_audit.py tests/test_ci_classifier.py -q
.\.venv\Scripts\python.exe -B scripts/check_repository_conventions.py --source worktree
.\.venv\Scripts\python.exe -B scripts/ci/classify.py --paths docs/PROJECT_STATUS.md

# 集成门禁计划（只读）
.\.venv\Scripts\python.exe -B scripts/ci/classify.py --paths (git diff --name-only origin/main HEAD)
```
