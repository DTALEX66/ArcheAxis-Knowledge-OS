# DSH 后端审计交接提示词 — 2026-09-27

> 本文件由 DSH 生成，供 **Owner 复制给网页 GPT 做第三方审计**。
> 用法：把下面 `===== 复制开始 =====` 与 `===== 复制结束 =====` 之间的**全部内容**粘贴给网页 GPT。
> 该提示词是**自包含**的：审计者无法访问本仓库（私有），因此所有结论、数字、锚点、问题都写在正文里。

**上传状态（生成本文件时的实测；本文件本身随其后的 doc-only 提交发布到 `main`，因此下列 HEAD 会在该提交后前移）**

- 远端 `refs/heads/main` = 工作分支 = 本地 `HEAD` = `69a3baed13be061f2f8283c6efd4b0e5e80c4d23`
- 本会话 5 个提交全部为 `origin/main` 祖先：`95f6638a`、`d570a986`、`c8fb6910`、`b7497dd5`、`69a3baed`
- `git log origin/main..HEAD` 为空；`git diff --stat` 为空（无未提交的已跟踪改动）
- **未上传且按规则不上传**：`apps/ArcheAxis.Desktop/MainWindow.axaml.cs`（Codex 的前端文件，EOL-only 脏，非本任务）；`docs/history/**` 共 23 项未跟踪物（早于本会话，未认领）；`.project-local/**`（`.gitignore:48` 忽略，审计回执与复跑脚本在此）；`data/**`（`.gitignore:24` 忽略）

---

===== 复制开始 =====

# 审计请求：DSH 在 ArcheAxis Knowledge 项目上的后端/审计工作（2026-09-27）

## 0. 你的角色与任务

你是独立的第三方审计者。你的任务是**证伪优先**地审计下面这份自述：找出无证据支持的断言、证据等级混淆、数字不闭合、缺少可证伪条件的结论、伪造或夸大的迹象，以及被掩盖的问题。

**重要**：你**没有**该仓库的访问权（私有仓库），因此你**无法**直接核验任何命令回执。请把"无法核验"如实标出，**不要**因为无法核验就默认它是真的，也**不要**因为无法核验就默认它是假的。你要审计的是：**叙述内部是否自洽、证据与结论是否匹配、有没有把弱证据当强证据**。

如果某条你无法判断，请明确写 **UNVERIFIABLE，需要什么材料才能判断**，而不要给一个含糊的"看起来合理"。

## 1. 项目与权威边界（被审计方声称遵守的规则）

- 仓库：`DTALEX66/ArcheAxis-Knowledge-OS`（本地路径为 `D:\All projects\ArcheAxis-Knowledge-OS`）
- 项目定位：本地优先、证据驱动的人机双向学习与可信知识工作台。
- 架构约束：**Rust Core 独占数据库写权限**；Python 是受控 worker；C#/Avalonia 是正式桌面；遗留 React/Tauri/Python 仅作兼容。**禁止双写**。
- 当前执行基线：R6 冻结任务包 `docs/authority/taskpack-0919-r6/`（Plan ID `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`），叠加 M0 最短闭环优先级；M0 优先级文件 `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`。
- 发布冻结：release `FROZEN`；A15/A16 **未签**；`local_green_updated=false`。
- **允许使用的项目状态词**只有：`TESTED_LOCAL`、`TESTED_LOCAL_PARTIAL`、`BLOCKED_BY_OWNER_DECISION`、`STRUCTURAL`、`NOT_EXECUTED`、`NOT_VERIFIED`。`PROPOSAL`/`BLOCKED`/`PASS`/`DONE` **不是**项目状态词。审计意见另有 `CONFIRMED`/`REFUTED`/`PARTIAL`/`UNVERIFIED`。
- 证据等级**不得互相冒充**：源码/静态 ≠ CI 运行 ≠ 本地 fixture ≠ 真实语料 ≠ 真实模型 ≠ 人工操作。
- 仓库权威顺序（`docs/authority/AGENTS.vnext-governance.md:9-24`）：1) Owner 当前明确指令；2) 有取代记录的生效 Owner Decision；3) `PROJECT_CONTRACT.yaml`；4) `DIRECTORY_AUTHORITY.yaml`；5) 版本化产品契约；6) **已签发的不可变任务信封与授权**（从受保护 activation commit 读取）；7) 根/最近目录 `AGENTS.md`（只能收窄上位）；8) 普通 ADR/设计文档与历史交接文档。`:21` 明定"**低权威可以收窄规则，但不能放宽规则**"；`:23-24` 明定"授权顺序**不等于**证据等级"；`:30` 明定"源代码、mock 输出、旧 SHA、**被跳过的 job**、模型置信度或 Agent 自述，单凭其一**不能**证明用户可见路径"；`:43-44` 要求"若信封/授权缺失、被撤销、**是模板**、自改、绑定错误 subject SHA 或脱离 Program 图，则停止"。

## 2. 被审计的最终状态（baseline）

| 项 | 值 |
| --- | --- |
| HEAD / tree | `69a3baed13be061f2f8283c6efd4b0e5e80c4d23` / `0acd4266a8f6e7f97bd9b11cfe11b8ac7abff3a4` |
| 远端 main / 工作分支 | 均为 `69a3baed…`（分支名 `codex/aaos-p3-ui-convergence-20260922`） |
| `git diff --stat` | 空 |
| `git status --short` | 仅 ` M apps/ArcheAxis.Desktop/MainWindow.axaml.cs`（Codex 的前端文件，只改动于 CRLF 检出差异，`git diff` 逐字节为空；文件 mtime `2026-09-26 22:02:35`，**早于**被审计方第一个提交 `95f6638a`（`2026-09-27 11:40:32`）约 13.5 小时）+ 23 项未跟踪的 `docs/history/**` |
| 冻结 TaskPack 完整性 | `TASKPACK.md` 工作区 SHA-256 = `788c5d50b5953d21eb9f67587d5406d37ad2e5457c2ca3b991399d9988e5951b`，与 `docs/authority/taskpack-0919-r6/EXECUTOR-START.md:6` 钉死的 canonical-LF 值**完全相同** |
| `R6-STATE.json` | 本任务**未**写入（最后一次写入是提交 `e8e6909d`，2026-09-26） |
| tag / release | 本任务**未**创建任何 tag/release；仓库现有 21 个历史 tag，最新 `v0.6.14`（2026-08-30），均早于本会话 |

## 3. 本会话的 5 个提交

| 提交 | 内容 |
| --- | --- |
| `95f6638a` | 外置工具链接线（`scripts/runtime/dev.py::external_toolchain()`）+ 7 个闭合回归测试 + 探针脚本调整 + 台账 |
| `d570a986` | 交接文档新增 §11「合并最终审计报告」（八项 §E 要求） |
| `c8fb6910` | CI 逐 gate 读回 + 一个套件数字对账 |
| `b7497dd5` | 更正一处 gate 计数错误（14 → 16） |
| `69a3baed` | §11.10 授权边界与 Owner 裁决 + §11.5 选项锚点 + §9.7 前向指针 + 台账 |

## 4. 交付物

- `docs/current/DSH-BACKEND-HANDOFF-20260927.md` —— 审计正文；§1–§8 由另一方撰写，§9–§10 是两轮复核过程，**§11 是本次合并报告**（§11.1–§11.8 对应执行提示词的八项要求，§11.9 完成标准自检，§11.10 授权边界登记）。
- `docs/current/R6-EXECUTION.md` —— R6 可变台账（`EXECUTOR-START.md:7` 指定为 current execution ledger），本会话追加了带日期的条目。
- `.project-local/task-runtime/wsr/` —— 复跑脚本与原始回执（**gitignored，未上传**），含 `replay_ci_gates.py`、`ci_steps.py`、`verify_audit_closure.py`、CI job JSON、`cargo-fmt-check.txt`（783KB）、多个运行日志。

## 5. 被审计方声称做了、并给出回执的事项（证据等级已标注）

**CI（远端，可被第三方通过 GitHub 复现，但需仓库权限）**

| 项 | 结果 |
| --- | --- |
| `69a3baed` 的两个 run：main `36297448338`、分支 `36297444992` | 均 success；但**只执行了 `gateplan`、`lint`、`a0-gates`，其余 16 个 gate 全部 skipped**（doc-only 变更被 GatePlan 允许跳过） |
| `95f6638a`（含代码改动）的 run `36292355530` | success，代码相关 gate 有执行 |
| 早前强制 wheel-smoke run `36250176719`（提交 `ea2c3831`） | 20/20 成功；`installed '0.6.14'` == `manifest '0.6.14'`，仅一个 dist-info |
| CI job 日志正文 | 匿名 `GET /repos/.../actions/jobs/<id>/logs` 返回 **HTTP 403**（需 admin），因此 run 结论均来自 **step 级元数据**，非日志正文 |

**本机 exact-SHA 运行（回执在 gitignored 目录，第三方无法直接核验）**

| 目标 | 结果 | 备注 |
| --- | --- | --- |
| `tests/workers`（整目录） | 135 passed / 7 skipped / 0 failed / 0 errors / 97 subtests | 历史报告记为 117 passed / 7 skipped / **2 failed / 5 errors** → **未复现**（通过 +18） |
| `tests/workers/test_f01_real_quality.py` | 5 passed / 1 warning | 与历史回执逐字一致 |
| `tests/workers/test_p1_quality_matrix.py` | 11 passed / 2 subtests | |
| `tests/workers/test_quality_regressions.py` | 15 passed / 30 subtests | |
| `tests/test_vault_search_api.py` | 7 passed | |
| `tests/test_general_learning_contract.py` | 6 passed | |
| `tests/test_courseware_v1.py` | 11 passed | |
| `tests/test_general_courseware_renderer.py` | 8 passed | |
| 全套件（`tests/ integration-tests/ knowledge_base/tests/`） | **3419 passed / 10 skipped / 0 failed / 137 subtests / exit 0** | 同作用域 `--collect-only` = **3429**，与 passed+skipped 自洽 |
| `tests/test_unseen_evaluation.py` | 13 passed | 该套件会因语料泄漏而失败，本次通过 |
| `tests/test_migration_runner.py` / `test_approved_paths.py` / `test_ingestion.py` | 37 passed / 4 passed+1 skipped / 3 passed+1 skipped | |
| `tests/test_imported_modules.py` / `pytest tests/contract --noconftest` | 7 passed / 68 passed + 29 subtests | |
| Rust `archeaxis-domain --test machine_loop_restart` | 1 passed / 0 failed | |
| Rust `archeaxis-api --test f01_quality_roundtrip` | 5 passed / 0 failed | |
| Rust `archeaxis-application --test ocr_job_end_to_end` | 接线前 1 failed → 接线后 1 passed | |
| Rust 全 workspace（`cargo test --workspace --offline`） | 87 个测试二进制 / **240 passed / 0 failed / 0 ignored / exit 0** | |
| `cargo build -p archeaxis-api` | exit 0 | |

**守卫与静态检查（全部 exit 0，除注明者）**：`check_architecture`；`check_language_boundaries`；`check_path_conventions`（2275/2275 受跟踪路径有归属）；`check_repository_conventions --source head` 与 `--source index`；`ruff check … --select E9,F63,F7,F82`；`check_format_matrix --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json`（16 组：0 complete / 14 partial / 2 custody）；`check_vnext_contracts`；`generate_vocabulary --check`（drift `[]`）；`check_vnext_workers`；`compileall -q app shared knowledge_base scripts`。

## 6. 被审计方判定的逐项结论（DP = 被审历史交付）

| 项 | 判定 | 依据锚点 | 说明 |
| --- | --- | --- | --- |
| DP-NF-01 / Git 审计器 | **PARTIAL** | `docs/current/dsh-review/branch-batch-01.md:266`（`No test was executed for any SHA`）；`branch-batch-02.md:256`（`verify_batch02.py` `errors=0`）；`branch-batch-03.md` | 交付物已吸收、数字逐字一致；但原交接稿把批次 02 的验证器写成 `audit_verify.ps1`（实为 `verify_batch02.py`），且漏了 branch-batch-03 的 16 SHA/107 路径 |
| DP-NF-02 / P0-H01 | **CONFIRMED（作为提案）** | `p0-h01-host-lifecycle-proposal-20260925.md:3`（`STATUS: PROPOSAL / OWNER DECISION REQUIRED … Not an adopted contract`） | 仍只是提案，未获批准；无测试 |
| DP-NF-03 / P1 quality matrix | **CONFIRMED** | `tests/workers/test_p1_quality_matrix.py`（引入提交 `5bb89aa7`，HEAD 祖先） | 13 文件/+5952−4 等数字与原文一致 |
| DP-NF-04 / Search + General Course | **PARTIAL** | Search：`tests/test_vault_search_api.py` 7 passed；Course：6/11/8 passed | 契约/渲染层测试通过；但原报告对 Search 的描述（FTS-only、每次查询 rebuild、字符窗口、无 calibrated score）是历史静态分析，**本任务未重判其正确性**；`CourseManifest` 合约内容**未逐条审计** |
| DP-NF-05 / machine-loop restart | **CONFIRMED** | `crates/archeaxis-domain/tests/machine_loop_restart.rs`（引入 `5bb89aa7`） | 由 `NOT_EXECUTED` 升为 exact-SHA 本机实测 |
| DP-NF-06 / P5、P6 | **PARTIAL** | `dp-nf-handoff-20260925.md:168` 对比同文件 `:196-197`；`p6-current13-candidate-readback-20260925.md:77-89` 对比 `:151-155` 对比 `AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md:177` | P5 按设计未跑测试；P6 `ok=false` 的**成因在底层三份材料里有三种互相矛盾的说法**；`NOT_EXECUTED` 标签应采信同文件 Correction |
| DP-NF-07 / language-data gap | **CONFIRMED（作为只读审计）** | `dsh-review/september-repo-language-data-gap-20260925.md:136` | 纯只读、无测试；本任务未重分配任何未跟踪文件 |
| DP-A11 / Research contract gap | **CONFIRMED（作为提案）** | `dsh-review/research-contract-gap.md:3-5` | Research 仍 unavailable；DTO 未冻结前不实现 |
| DP-F01 / Python 真实文本质量 | **CONFIRMED** | `tests/workers/test_f01_real_quality.py`（引入 `d5f026ee`） | 合成 fixture，**非**真实语料 |
| DP-F01 / Rust roundtrip | **CONFIRMED** | `crates/archeaxis-api/tests/f01_quality_roundtrip.rs`（引入 `d5f026ee`） | 由 `NOT_EXECUTED` 升为 exact-SHA 本机实测 |
| DP-UI-01 | **CONFIRMED（作为未执行）** | `dsh-review/dp-ui-01-readiness.md:5`（`STATUS: BLOCKED / NOT_EXECUTED`） | 无 Candidate、无 GUI run；本任务不触碰 UI 写范围 |

**整体判定：`STRUCTURAL`。没有任何一项达到 `REAL`、`GUI_ACCEPTED`、`MERGED_MAIN`、`INSTALLED_RUNTIME_VERIFIED` 或 `CI_VERIFIED_EXACT_SHA`。**

## 7. 吸收 / 取代 / 未吸收 / 无法判定（声称已机械核验）

| 路径 | 状态 | 引入提交（已验证为 HEAD 祖先） |
| --- | --- | --- |
| `crates/archeaxis-domain/tests/machine_loop_restart.rs` | 已吸收 | `5bb89aa7`（2026-09-26） |
| `tests/workers/test_p1_quality_matrix.py` | 已吸收 | `5bb89aa7`（2026-09-26） |
| `tests/workers/test_f01_real_quality.py` | 已吸收 | `d5f026ee`（2026-09-25） |
| `crates/archeaxis-api/tests/f01_quality_roundtrip.rs` | 已吸收 | `d5f026ee`（2026-09-25） |

未吸收：未发现明确未吸收的交付物，但**也未建立完整表**（仅覆盖上述 4 个路径）。**无法判定**：DP-NF-01/02/04/06/07、DP-A11、DP-UI-01 的**分支侧**交付与当前 HEAD 的逐条关系，因为本任务未读全部 refs、未建立 commit 图。

## 8. Owner 决策单与依赖链（这是被审计方最希望第三方检查的部分之一）

四项标注 `BLOCKED_BY_OWNER_DECISION`，且被审计方声称这四项是该标签的**全部**范围：

| 决策 | 形态 | 锚点 | 兼容影响锚点 |
| --- | --- | --- | --- |
| **A02** resource-root/schema | 闸门式（保持 Owner Gate），非 A/B 选项 | `docs/current/M0-DIRECTION-OVERRIDE-20260920.md:198` | 未集中给出 |
| **P0-H01** Provider/Host 身份与生命周期 | **D1–D6 冻结问题表** | `dsh-review/p0-h01-host-lifecycle-proposal-20260925.md:161-170` | 同文件 `:139` `4.9 Migration compatibility` |
| **DP-F01** typed loss receipt | **唯一有真 A/B/C 选项的一项**：Option A（新 typed `/receipt`，提案推荐）、Option B（扩宽 `/quality`，更小）、Option C（改 outputs 路由，不推荐） | `dsh-review/job-quality-projection-proposal.md:95`、`:129`、`:135`；决策点 D1 见 `:162` | 同文件 §3 |
| **DP-A11 / Research** | **D1–D5 问题表**（D1 标 Recommended） | `dsh-review/research-contract-gap.md:194-200` | 同文件 `:178` `4.6 Migration compatibility` |

被审计方声称本轮**实测出**一条此前未写成链的依赖关系：**`A02 → P0-H01(D5) → Research(D3)`**：

- P0-H01 的 **D5** 问"provider/model 路径解析是否落在未决的 A02 资源根决策之下"（`p0-h01-…:169`）
- Research 的 **D3** 问"Research 是否可先以 FTS-only + `provider: unavailable` 上线，还是必须等 provider 身份决策"（`research-contract-gap.md:198`）

即：**先决 A02 一次可解锁两项**；反之先冻结 Research DTO，D3 仍会把问题挡回 P0-H01。被审计方声明：检索 `docs/current` 后确认 A02 与 P0-H01 多处只是**并列**出现，没有任何一处把三级先后关系连成一句。

## 9. `REQUEST-ARTIFACT` 清单（缺证据，不得视为 0 或成功）

| ID | 状态 | 仍需的材料 |
| --- | --- | --- |
| RA-01 | 仍缺 | DP-NF-01/02/04/05/06/07 分支侧 readback：目标 worktree 的 branch/ref、baseline/head/tree、changed paths、命令与 stdout/exit |
| RA-02 | 本机已补 | DP-F01 Python/Rust 原始回执已本机补齐；若需**真实语料**结论，仍需获准语料的路径/哈希/引擎/attempts/loss 回执 |
| RA-03 | 本机已补 | DP-NF-03/05 复跑回执已本机补齐；跨机复核需提供隔离目录身份 |
| RA-04 | 仍缺 | A04/A08/A14 真实 first-use 与重启 readback：版本与哈希、隔离 DB 身份、各业务 ID、重启前后 readback、幂等键、FSRS schedule |
| RA-05 | 仍缺 | A05 真实文件质量：获准输入路径/哈希、格式、engine/version、attempts/fallback、loss receipt、人工结构/语义判定 |
| RA-06 | 仍缺 | A06 Research/Provider/vector/rerank：冻结契约/版本、provider 身份与版本、配置来源（不含密钥）、输入/来源修订、结果数/empty/error、benchmark 原始回执 |
| RA-07 | 仍缺 | A13 Candidate/当前源码与 GUI：manifest/source snapshot/EXE/DLL 哈希、isolated data root、verifier stdout/exit、**当前 DLL** 的 UIA 路由/键盘/DPI 截图 |
| RA-08 | 部分已补 | 远端 refs 与 run ID 已知；**job 日志正文仍不可读**（403，需 admin） |

## 10. 被审计方主动申报的问题、偏离与自我更正（**请重点审这一节**）

1. **授权偏离（已由 Owner 裁决）**：执行提示词的硬约束 4 明写"不执行 commit/push/merge/release"，但实际有 4 个提交（`95f6638a`、`d570a986`、`c8fb6910`、`b7497dd5`）被推送到 `main`。被审计方给出的判据是：该提示词按仓库权威顺序**落在第 8 档**，而第 8 档"只能收窄、不能放宽"；实测 `.project/tasks/issued/` 与 `.project/leases/issued/` 下**只有 README.md**，授权仅存在于 `.project/leases/templates/AUTHORITY-GRANT.authority-grant-template.yaml`（**模板**），即**没有已签发信封、没有已签发授权**；因此唯一能覆盖该收窄的是第 1 档的 Owner 指令。**Owner 已裁决：会话中的"全部授权"覆盖该收窄，四个提交属已授权写入，历史不改动。** Owner 同时决定**暂不**补建签发通道，因此被审计方注明：此类边界**仍不会被系统自动拦下**。
2. **一处被审计方自己的计数错误（已修）**：§11.8 初稿写"其余 **14** 个 gate skipped"，逐 gate 读回后实为 **16**，已在 `b7497dd5` 更正，并被写入台账说明"正是把它写下来才抓到"。
3. **一个套件数字未能对账（未解释）**：台账早前记 `3413 passed, 14 skipped`（合计 **3427**），而当前在 `d570a986` 上用明确作用域实测 **3419 passed / 10 skipped**（合计 3429），且 `--collect-only` 该作用域 = **3429**。被审计方测了三个候选作用域的收集数（`tests/ integration-tests/ knowledge_base/tests/` = 3429；`tests/ knowledge_base/tests/` = 3382；`tests/` = 3344），**没有一个是 3427**，因此 2 例差额的成因被明确写为**未追平、不臆测**。**请审计这个处理是否恰当。**
4. **两个非本任务所有的 stash（未处理）**：`stash@{0}`（2026-09-18，来自 `codex/local-pre-api-updates-20260918`，触及 **`MainWindow.axaml` + `.axaml.cs`**、`BRANCH-CONVERGENCE.*`、`R5-EXECUTION.md`、`R5-STATE.json`）与 `stash@{1}`（2026-08-05，来自 `feat/portable-data-root`，触及 **`app/workspace/ui/**`**、`run_windows.bat`、`a0_browser_smoke.py`、`test_ui01_navigation_contract.py`）。被审计方声明未创建、未 pop、未 drop 任何 stash，且因二者都含界面文件而按 Owner"不要碰前端"的指示不动。
5. **一处"环境态"被判定为非产品缺陷（附证伪实验）**：本机 `data/archeaxis.sqlite` 上 `python -m app.runtime_entrypoint migrate` 与 `scripts/runtime_http_smoke.py` **都失败**（`baseline schema does not match core.sqlite owner: missing=…table:kb_attachment_facts`）。判定过程：该库 96 张表、**全表 0 行**、缺 `kb_attachment_facts`；改用全新 `ARCHEAXIS_DATA_DIR` 后 `migrate` **exit 0**、生成 **97 张表且含该表**，`runtime_http_smoke` **exit 0**（`runtime HTTP smoke passed at http://127.0.0.1:60675`）；`kb_attachment_facts` 由提交 `421736c8`/`a6ff9a09` 于 **2026-09-18** 引入 schema，故本机库早于该日、早于本会话。结论：当前代码按 `shared/core_schema.py:74-86` **fail-closed** 拒绝陈旧库，是正确行为。
6. **一处 Rust 格式问题（既存、无 gate 覆盖）**：`cargo fmt --all -- --check` 在根 workspace **exit 1**，差异遍布 `archeaxis-api`/`application`/`archive`/`contracts`/`domain`/`sidecar-protocol`/`store-sqlite`。本会话改动 **0 个 `.rs` 文件**。CI 中唯一的 `cargo fmt` 位于 `working-directory: src-tauri`（而 `Cargo.toml:4` 把 `src-tauri` 排除在根 workspace 之外），因此**根 workspace 的格式从未被任何 gate 检查**。
7. **一个 gate 未能本地复跑（未闭合）**：`scripts/ci/check_vnext_receipt.py` 本地 exit 1（`vNext receipt rejected: 'ARCHEAXIS_RUN_ROOT'`）。它校验必须由**同一次运行**写入 `ARCHEAXIS_RUN_ROOT` 的 journey receipt；被审计方尝试用 `dev.py --github-env` 复刻 CI 的环境导出失败（该模式在真实 Actions 之外 exit 2），`dev.py --run-id` 又是**一次性**的（目录已存在即拒绝）。**该 gate 的实质部分（`cargo test --workspace` 240 passed/0 failed）已跑通，receive 校验部分未闭合。**
8. **`check_format_matrix.py` 的一处口径更正**：被审计方先前**裸跑**该脚本得到 exit 2 并称"不适用"，后经读 `ci.yml` 发现 CI 传的是 `--matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json`，带上参数即 exit 0。**先前那句"不适用"是错的，已更正。**
9. **一处本任务在 Owner 真实数据目录留下的产物（已申报，未擅自删除）**：`data/.archeaxis.sqlite.b024cddc3a589c7b.migration_operator_locks.lockdb`（12KB，本会话运行 `migrate` 时生成），同时刷新了 `data/archeaxis.sqlite` 的 mtime（**内容未变**，仍是 96 表 0 行）。被审计方未删除该文件，等待 Owner 指示。
10. **一处过时表述（已加前向指针）**：§9.7 曾写"本回合未提交任何文件……该文件当前为未跟踪状态"，自 `95f6638a` 起不再成立；已在该处加指针指向 §11.10，而不是改写历史。

## 11. 明确未执行的事项（不得升级为通过）

真实语料格式质量；真实模型/Provider 调用；GUI/UIA/键盘/DPI 验收；当前 DLL 路由复播；Candidate 验收；Clean Machine；Green 安装/替换/回滚；Release/tag/版本变更；跨机 CI 复现。此外，被审计方声明**本轮未重新构建 wheel**（wheel-smoke 仅在会话早前验证过，强制 run `36250176719` = 20/20）。

## 12. 第三方无法验证、需要材料才能判断的部分

1. 所有本机测试回执的原始 stdout/exit（位于 gitignored `.project-local/`，未上传）。
2. CI job 日志正文（403，需 admin）。
3. 真实语料/真实模型/GUI/Candidate/Green 的任何结论（本身即未执行）。
4. 分支侧交付与 HEAD 的完整吸收关系（未建立）。
5. 上述 4 个路径之外的"已吸收"判断。

## 13. 请你（审计者）输出以下内容

1. **逐条证伪表**：针对第 5、6、7、8、10 节的每一条，给出 `SUPPORTED` / `PARTIALLY SUPPORTED` / `UNSUPPORTED` / `UNVERIFIABLE`，并说明依据的是叙述内部的哪一处矛盾或哪一处证据缺口。
2. **证据等级审计**：列出所有你发现的"弱证据被当强证据"或"证据等级互相冒充"的地方（包括：本地 fixture 被当成真实数据、静态路由被当成运行时验证、被跳过的 job 被当成 gate 通过、二手报告被当成当前实测）。
3. **数字审计**：检查第 5 节的数字之间是否自洽（尤其 `tests/workers` 的 135/7 与历史 117/7/2/5 的关系；3419/10/137 与 3429 的关系；240 passed 与 87 个二进制的关系；16 skipped 与 3 executed 的关系）。指出任何不闭合之处。
4. **状态词审计**：检查是否使用了项目允许之外的状态词，或把 `PROPOSAL`/`PASS`/`DONE` 当作项目状态。
5. **授权审计**：评价第 10 节第 1 条的处理是否恰当——被审计方"先登记偏离、再交 Owner 裁决"的做法，与"未经授权就写入"之间，审计上应如何定性？Owner 裁决之后，报告中"硬约束 4 按字面不满足、经裁决后授权有效"的写法是否可接受？
6. **遗漏审计**：指出第 11 节"未执行"之外，你认为**应该做而没做**的事（例如：在无签发通道的情况下是否应当停止工作、是否应当先建 quarantine 目录、是否应当把证据提升到受跟踪路径等）。
7. **最弱的三条结论**：明确排出你认为最站不住脚的三条，以及各自的证伪条件（什么材料出现就能推翻它）。
8. **你需要的材料清单**：为把 `UNVERIFIABLE` 降到最低，你需要 Owner 提供什么（按优先级排序）。

## 14. 审计时的注意事项

- 不要因为"没有仓库访问权"而整体判定不可审：本提示词的目的是审计**叙述的自洽性与证据纪律**，这是可以在无仓库访问的情况下完成的。
- 不要提出"重新跑一遍所有测试"这类无法执行的建议；请提出**具体的、可交付的 artifact 请求**。
- 不要替 Owner 做产品语义决策（尤其 A02、P0-H01、DP-F01、Research 四项）；那些是 Owner Gate。
- 不要建议删除、重置、强推、清理历史等破坏性操作。
- 如果某个数字看起来可疑但你无法确定，请标 `UNVERIFIABLE` 并写出你的怀疑方向，而不是猜一个结论。

===== 复制结束 =====

---

## 给 Owner 的附注（不要复制给审计者）

- 本提示词里的每一项事实都来自本会话的实际工具输出，没有推测填充。若你发现某条与你的记忆不符，以仓库与 `.project-local/` 回执为准。
- 若审计者要求原始回执，`\.project-local\task-runtime\wsr\` 下有：`replay_ci_gates.py`（cheap/runtime/rust/targets 四组）、`replay_rust_gate.py`、`ci_steps.py`、`verify_audit_closure.py`、`ci-jobs-d570a986.json`、`cargo-fmt-check.txt`、各 run 日志。
- 你仍有 4 项未决 Owner 决策与 8 项 `REQUEST-ARTIFACT`；另有两个含前端内容的 stash（非本任务）与一个我留在 `data/` 的锁文件待你处置。
