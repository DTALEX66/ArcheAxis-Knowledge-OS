# R5 独立审计报告（只读 + 本机实测，2026-09-19）

> 性质：**独立第三方只读审计**。本报告不提升任何切片状态、不修改 `TASKS.json`、
> 不改 Q00/Q01、不删除任何分支/标签/发布、不访问 E/F 盘、不读凭据或私密状态。
> 本轮唯一写入是**本文件**（新增路径），另在 git-ignored 的 `.project-local/tooling/`
> 放置审计用一次性运行器（不入库）。
>
> 审计对象：`docs/current/HERMES-FULL-AUDIT-PROMPT-20260918.md` 定义的独立审计提示词，
> 以及对 `docs/current/DSH-COMPLETION-REPORT-20260918.md` 自报结论的**逐条独立复现**。

---

## 一、元数据

| 项 | 值 |
|---|---|
| BASE_SHA（提示词记录） | `e537349c115bcbbfc3a2b0dceace9e8978991535` |
| RECORDED_SHA（DSH 报告） | `a5384490ba82f172b30869ba6a2550c4b312e093` |
| LOCAL_HEAD（本轮实测） | `e537349c115bcbbfc3a2b0dceace9e8978991535` |
| TESTED_SHA（本轮实测对象） | `e537349c115bcbbfc3a2b0dceace9e8978991535`（工作树除本文件外无改动） |
| REMOTE_HEAD（`git ls-remote origin HEAD`） | `e537349c115bcbbfc3a2b0dceace9e8978991535` |
| origin/main | `e537349c` — 与本地、与远端 HEAD **三方一致** |
| 时间 | 2026-09-19（本地时区 UTC+08:00） |
| 平台 | Windows 11 / Git-Bash(MSYS) / 项目 venv Python 3.13.14 / .NET 10.0.400 |
| 分支 / 工作树 | `main`（主仓）；另有 4 个 worktree：主仓 + `v3-era`(detached) + `verify-0c9c`(detached) + `worker-quality-0906` |
| 工具链 | `D:\All projects\OS External Configuration\10-toolchains`（cargo/rustup/msvc/dotnet/windows-sdk/scoop）；Tesseract 与 tessdata 由 `capability-requirements.yaml` 定位 |
| run 作用域 | 全部命令经 `hermes-project-data.py --project . run --` 单命令包装；无外溢写入 |

**前后状态确认**：审计开始与结束，`git status --short` 的未跟踪集合均为同样 22 项
（`docs/history/**` 既有私有材料 + `SESSION-RESTART-2026-09-12.md`），未暂存改动 0。
本轮未触碰、未暂存、未回滚其中任何一项。

---

## 二、结论摘要

| 等级 | 条数 | 内容 |
|---|---|---|
| **HIGH（已复现，需处置）** | 3 | ① 40/40 scoop shim 全部指向不存在目标（范围远大于原报抽样 3 个）；② `PROJECT_CONTRACT.yaml` 的 `digest_profile` 指向不存在文档；③ 任务状态**双轨口径**（`TASKS.json` 与 `R5-STATE.json` 对 X00/X04/X05/X07 判定不一致） |
| **MEDIUM（已复现，属治理/可用性）** | 4 | ④ main 走 **ruleset** 而非 classic protection，审计易误判"未保护"；⑤ `ci.yml:570` 步骤名误导仍在；⑥ Rust 测试必须绑定 Tesseract **且**经 `dev.py`，否则**假红**；⑦ 外置/仓库两份 `EXTERNAL_DEPENDENCIES.md` 仍不同步 |
| **LOW（已复现，仅描述）** | 2 | ⑧ `capability-requirements.yaml` 3 处既有漂移（`plugins` 缺类目、`sense-voice` 路径越出外置根、`install_method` 非枚举值）；⑨ 两个 worktree 持有主线没有的内容（`v3-era` 属禁止处理区、`worker-quality-0906` 已归档） |
| **UNVERIFIABLE（未独立复现）** | 3 | ⑩ DSH 所称"三次推送绕过必需检查"的具体绕过记录；⑪ DSH 所称"`git fetch` 曾被拒"的历史环境事实；⑫ 内容级语义等价（122 文本 + 3 二进制 blob）未逐条重算 |

**总体判断**：DSH 报告在**可由本机复现的范围内全部成立**（11 道闸门、Python 全量、
Rust 全工作区、C#/桌面、双端一致性、分支计数、worktree 内容量、外置文档两份）。
本轮**新增**的是上面 3 条 HIGH 中的 ①③ 与 MEDIUM 中的 ④⑥——都是"D、执行器看不见、
但会误导下一位审计者"的坑。

---

## 三、§3.5 闸门全量（逐条记退出码）

| # | 闸门 | 退出码 | 关键数字 |
|---|---|---|---|
| 1 | `scripts/check_path_conventions.py --json` | **0** | `tracked_paths=2074, owned=2074, unowned=0, coverage=100.0%`；记录测于 `b81c789d`，工作树已漂移 +282 跟踪路径（记录文件自带说明） |
| 2 | `scripts/check_architecture.py` | **0** | `architecture guard passed` |
| 3 | `scripts/check_language_boundaries.py` | **0** | `protocol major 1 agreed by rust/python/schemas; database owner = crates/ only` |
| 4 | `scripts/check_repository_conventions.py --source worktree` | **0** | `passed (worktree)` |
| 5 | `scripts/check_format_matrix.py --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` | **0** | 16 组；**0 complete / 14 partial / 2 custody-only**；11 core + 10 worker 路由全部存在 |
| 6 | `scripts/workflow/execution_preflight.py . --json` | **0** | `passed=true`；`private_state_opened=false`；564 链接 / 0 broken / 2 expected_fixture_missing |
| 7 | `scripts/maintenance/check_resource_boundaries.py . --purpose test` | **0** | 5 个登记根全部 `reparse=false`；未读内容 |
| 8 | `scripts/ci/check_vnext_contracts.py` | **0** | 结构与语言边界一致（protocol major 1） |
| 9 | `scripts/ci/check_vnext_workers.py` | **0** | `workers-vnext check passed` |
| 10 | `docs/authority/taskpack-0912-r5/verify_package.py` | **0** | `PASS`：23 任务 / 38 原始场景 / 18 附加切片 / 10 cleanup / 4 repo / 4 migration |
| 11 | `.\.venv\Scripts\python.exe -B scripts/runtime/dev.py --pytest -- tests/ integration-tests/ knowledge_base/tests/ -q` | **0** | **2894 passed / 46 skipped / 135 subtests**（DSH 自报 2891，本轮 2894，差 3 项属其自身新增测试后的再增长，方向一致） |

**独立结论**：闸门 11/11 全绿，与 DSH 自报一致。⚠️ 首次尝试用系统 `python`（无 yaml）
运行闸门 1/4/5 会 `ModuleNotFoundError: yaml`——**必须用项目 venv 解释器**，
否则会把"环境用错"误判成"仓库违规"。

---

## 四、§3.6 本机构建与运行时（实测）

| 对象 | 命令（受管入口） | 结果 |
|---|---|---|
| Rust 全工作区 | `dev.py -- cmd.exe /c scripts\ci\cargo_test.bat --workspace`，并绑定 `ARCHEAXIS_RUST_TOOLCHAINS`/`ARCHEAXIS_MSVC_VCVARS`/`TESSERACT_CMD`/`TESSDATA_PREFIX` | **exit 0**：**79 套件 / 197 项通过 / 0 失败**（日志 `test result:` 79 行、`FAILED` 0 次、`panicked` 0 次、`error:` 0 次） |
| C# 构建 | `dotnet build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj -v minimal` | **exit 0**：0 警告 / 0 错误；输出 `.project-local/build/dotnet/.../ArcheAxis.Desktop.dll` |
| C# 词汇契约 | `dotnet run --project tests/contract/Vocabulary.Tests -- tests/contract/fixtures/vocabulary-cases.json` | **29 shared wire cases** 解析通过 |
| 桌面 supervisor | `dotnet run --project tests/runtime-paths/CoreSupervisor.Tests`（设 `ARCHEAXIS_RUN_ROOT`/`ARCHAXIS_CORE_BIN`/`ARCHEAXIS_PYTHON`） | **9/9 PASS**，含 `real Core with spaced path, assigned port, handshake and shutdown`、`silent C# -> authenticated Core -> actual Python -> persisted output`、`actual Windows short-path workspace identity` |
| Avalonia 冒烟 | `dotnet run --project apps/ArcheAxis.Desktop -- --smoke ...` | **`SMOKE OK: owned core handshake ok: archeaxis-api 0.1.0-outline`** |

### 4.1 新发现：Rust 测试的两个"假红"陷阱（MEDIUM-⑥）

同一 SHA、同一工具链，仅启动方式不同，得到三种结果：

| 启动方式 | 结果 | 观察到的信息 |
|---|---|---|
| 直接调 `cargo test`（不经 `dev.py`） | **假红 1 项** | `stateful_schedule_failures::real_scheduler_timeout_keeps_review_and_releases_transaction_for_next_review` panic 于 `crates/archeaxis-api/src/lib.rs:511`，信息仅 `run through dev.py` |
| 经 `dev.py`，但**未绑定 Tesseract** | **假红 1 项** | `ocr_job_end_to_end` 失败并返回 `AAK-WORKER-003 tesseract binary not found on PATH`，`retryable:false`（这是**正确的失败闭合**，不是产品缺陷） |
| 经 `dev.py` **且**绑定 Tesseract | **全绿** | 79 套件 / 197 项 / 0 失败 |

**判据**：两次红都是**环境契约未满足**，而不是回归。但两个红都把"你没按我们的入口跑"
表达成了测试失败，`lib.rs:511` 那处甚至只回一句 `run through dev.py`。
建议（不由本轮执行）：把该断言换成带变量名与期望值的显式诊断，
并在 `docs` 或 CI 步骤中把 Tesseract 绑定写成前置条件——否则下一位审计者会重复假红。

---

## 五、§3.7 双端一致性

| 检查 | 结果 |
|---|---|
| `git fetch origin --prune` | exit 0 |
| `rev-list --left-right --count main...origin/main` | `0	0` |
| `git diff --name-only main..origin/main` | 空 |
| `ls-remote origin HEAD` | `e537349c…` = 本地 HEAD |
| 远端分支计数 | **18** |
| 本地分支计数 | **30** |
| worktree | 4（主仓 + `v3-era` + `verify-0c9c` + `worker-quality-0906`） |
| stash | 2（`stash@{0}` 0918、`stash@{1}` 0805 恢复点） |
| 开放 PR | **0** |
| CI `main@e537349c` | run `35369065744` → **success** |
| nightly run `35323175367`（`44bd821`） | **failure**：`full-suite` 失败（5 failed / 2877 passed / 35 skipped），`browser-smoke` 与 `windows-runtime` 被 `needs:` 跳过 —— 该 SHA 是**旧远程基线**，非当前 HEAD |

**结论**：本地 = 远端 = API 三方一致，无未推送分歧；nightly 的红是已过时的旧 SHA 记录，
不构成当前 HEAD 的失败证据（新的 `main@e537349c` CI 为成功）。

---

## 六、§6 逐项裁决（含独立复现）

### 6.1 分支收敛 A/B 组

- 本地 30 分支、其中仅本地分支 19 个（远端无同名），未推送提交 80 个 —
  **计数与既有记录一致**。
- `fix/ci-playwright-collection` 已删除、`codex/worker-quality-0906` 保留，二者在
  `git branch` 与 `git worktree list` 中呈现**与既有处置记录一致**。
- 两个 worktree 状态**独立复核通过**：
  - `v3-era`：`M  crates/archeaxis-archive/src/lib.rs`、`M  crates/archeaxis-store-sqlite/src/lib.rs`（**已暂存**）、`?? crates/archeaxis-archive/tests/gen_v3_fixture.rs` —— 属 §15/§16 禁止处理区，**保持上报，本轮未触碰**。
  - `worker-quality-0906`：6 个已改文件 + 9 个未跟踪路径 —— **与既有记录（6 改 / 9 未跟踪）逐项吻合**；其 56 行独有内容已归档，本轮未改动。
- 远端 17 个非 main 分支的"零文件差异 = 13 / 含残留 = 4"分类，本轮**未重算全部 blob**，
  仅抽查计数与结构性结论（全部 `diverged`、15 个走压缩合并）——列为**部分复现**。

### 6.2 外置库 3 处偏差（**全部已独立复现，其中 1 处范围被显著放大**）

**(a) scoop `shims` 全目录陈旧 —— HIGH，范围 40/40（原报只抽验 3 个）**

| 证据 | 实测 |
|---|---|
| `.shim` 文件数 | **40** |
| 目标含 `10-toolchains` 前缀 | **0 / 40** |
| 目标文件实际存在 | **0 / 40** |
| 样例 | `git.shim → …\OS External Configuration\toolchains\scoop\apps\git\current\bin\git.exe`（不存在） |
| 正确前缀根 | `…\10-toolchains`（9 个子目录：cargo/deeptutor/dotnet/msvc/playwright/python/rustup/scoop/windows-sdk） |
| 无前缀根 | `…\toolchains` 确实存在（5 个子目录：mingw/playwright/rust/rustup/scoop），**但其中没有 `apps\` 层**，故 shim 目标仍全部落空 |

→ 结论：这不是 3 个替身的问题，而是**整个 `shims` 目录（40 个）**的登记漂移。
属共享外置库，**由 Owner 处置**；项目侧应继续只使用 `external_paths` 精确路径
（`docs/environment/EXTERNAL_DEPENDENCIES.md` §1.3/§1.4 已如此要求）。

**(b) 两份 `EXTERNAL_DEPENDENCIES.md` 不同步 —— MEDIUM，已复现**

| 副本 | 行数 | 字节 | SHA-256(前16) |
|---|---|---|---|
| 仓库 `docs/environment/EXTERNAL_DEPENDENCIES.md` | **368** | 17 377 | `e00c4ba75b3249b0` |
| 外置 `D:\All projects\OS External Configuration\EXTERNAL_DEPENDENCIES.md` | **322** | 12 715 | `c95c672756b4d1e2` |

→ 外置副本 322 行与 DSH 报告所称行数**逐字吻合**；仓库副本已增至 368 行
（DSH 报告写为 347 行，为其自身编辑过程中的中间值）。**同步方向仍为 `仓库 → 外置`**，
写入共享库须由 Owner 执行，本仓库不代改。

**(c) `capability-requirements.yaml` 3 处既有漂移 —— LOW，已复现（直接读文件）**

1. `capabilities:` 下**没有 `plugins:` 类目**，而 schema 要求 `minItems: 1`；
2. `models/sense-voice-zh-en-ja-ko-yue` 的 `external_paths: ["../Model library/sherpa-onnx"]`
   **越出外置根**（`environment_registry` 会跳过它）；
3. 同条目 `install_method: shared-model-library` **不在枚举内**
   （枚举为 `scoop|uv|rustup|playwright-install|下载安装器|自动下载|内置|uv-sync|system`）。

→ 三处均需治理决策（补条目或改 schema），**不由执行器单方面修改**；判定维持原样。

### 6.3 CI 治理 3 项（**全部已独立复现，并纠正一处理解偏差**）

**(a) `a0-gates` 绕过 —— 已复现，但入口与直觉不同（MEDIUM-④）**

| 探针 | 实测结果 |
|---|---|
| `GET /repos/…/branches/main/protection` | **404 `Branch not protected`** |
| `GET /repos/…/rulesets` | `main-protection`（id `20849492`, target=branch, **enforcement=active**）、`tag-protection`（id `20849089`） |
| `GET /repos/…/rulesets/20849492` | `conditions.ref_name.include = ["refs/heads/main"]`；规则仅一条：`required_status_checks = ["a0-gates"]`；**无必需 PR 评审**；`bypass_actors` 未配置 |

→ **关键提示**：classic protection API 返回 404 会让人得出"main 未受保护"的错误结论；
真实约束在 **ruleset**。live 规则确实只要求 `a0-gates` 一项，因此
"直推 main 绕过 `a0-gates`"在机制上成立，与 DSH 报告一致。
建议把"main 由 ruleset 20849492 保护"写进治理文档，避免下一位审计者误判。

**(b) `ci.yml:570` 步骤名误导 —— 已复现**

- `ci.yml:570` = `- name: Run real canonical React browser regressions`（**存在**）
- 同名文本在 `nightly.yml` 中**不存在**
- `fetch-depth: 0`：`ci.yml` 3 处、`nightly.yml` 1 处
- `fonts-noto-cjk`：`ci.yml` 1 处

→ 改名属**单行治理变更**，§16 禁止 DSH 修改 `ci.yml`；保持上报待授权。

**(c) `digest_profile` 悬空 —— 已复现（HIGH-②）**

| 位置 | 值 | 目标是否存在 |
|---|---|---|
| `PROJECT_CONTRACT.yaml` | `digest_profile: docs/operations/digest-canonicalization.md` | **不存在** |
| 实际文档 | `docs/vnext-seed/operations/digest-canonicalization.md`（46 行） | 存在 |
| `.project/TASK-GRAPH.yaml` | `manifest_digest_profile: AAK-JCS-1` | 与 schema 一致 |
| `.project/schemas/task-graph.schema.json` | `"manifest_digest_profile": {"const": "AAK-JCS-1"}` | 钉死 |

→ 契约里的 `digest_profile` 指向一个**不存在的路径**，而 schema 用的是 profile **常量**。
改指向会触及 schema `const`，属治理变更，维持上报。

### 6.4 证据定级与本轮未复现项

- 上表所有"已复现"均为**本机、本 SHA 的直接命令输出**（不是转述），等级 **VERIFIED**。
- "13 个分支与自身 squash 零文件差异"、"122 个文本文件已逐字节保全"、
  "3 个二进制 blob 仅登记 SHA-256" —— 本轮**未逐条重算**，等级 **PARTIAL_REPRODUCTION**。
- "三次推送绕过必需检查"、"`git fetch` 曾被环境拒绝" —— 属**历史环境事实**，
  本轮 `git fetch` 与 `gh api` 均正常，**无法回溯复现**，等级 **UNVERIFIABLE**（不否认、不背书）。

---

## 七、与 DSH 自报的差异（本轮新增）

| # | 差异 | 性质 | 影响 |
|---|---|---|---|
| 1 | Rust 测试存在**双重假红陷阱**（不经 `dev.py` 红 1 项；未绑 Tesseract 红 1 项） | 新增发现 | 下一位审计者若直接 `cargo test` 会误判回归；DSH 报告只在 §10 注中提了 Tesseract，未提 `dev.py` 强制与误导性 panic 文案 |
| 2 | main 保护实为 **ruleset**（classic API 404） | 新增发现 | 防止把"未保护"写成结论 |
| 3 | 陈旧 shim 范围是 **40/40**，非 3 个 | 范围放大 | 处置清单从 3 个变成整目录 |
| 4 | `TASKS.json`（X00/X04/X05/X07 = `REOPENED`）与 `R5-STATE.json`（全部 `PARTIAL_NEEDS_WORK`）**口径不一致** | 新增发现（HIGH-③） | 两处都在 main 上；`REPO01`"只存在一个活动 TASKS 入口"的验收点因此存在双轨风险，需指定唯一权威并让另一处引用它 |
| 5 | 仓库 `EXTERNAL_DEPENDENCIES.md` 现为 **368 行**（报告写 347 行） | 口径更新 | 不改变"以仓库副本为准"的方向 |
| 6 | Python 全量为 **2894 passed**（报告写 2891） | 口径更新 | 属报告写后新增测试，方向一致 |
| 7 | 外置 `EXTERNAL_DEPENDENCIES.md` 位于外置**根目录**，非 `docs/` 下 | 位置澄清 | 便于下次直接定位 |

---

## 八、状态不变量（本轮未改变）

- `TASKS.json`：`X00`–`X14` 仍为 `REOPENED`/`PARTIAL`（**无 DONE**）；
  `Q00 = FAILED_AT_BASELINE`、`Q01 = NOT_READY`；`F01`–`F06` 仍 `DEFERRED_RETAINED`。
- `R5-STATE.json` 的 `independent_audit`（`Q00: AUDITED_FAIL_BLOCKED_20260918`、
  `Q01: BLOCKED_DEPENDENCY_Q00`）**一字未改**。
- 未创建 R6，未新建 DAG/权威入口。
- 未删除/重命名任何远端或本地分支、未动 worktree、未丢弃 stash。
- 未修改 `ci.yml`、`release.yml`、`WorkerProfile.cs`、`archeaxis-archive` 布局、
  安装/分发脚本。
- 未访问 E 盘、F 盘；未读凭据、私密状态或真实资料库内容。
- **不得**据此报告声称：R5 完成、语言迁移完成、Q00 通过、格式矩阵已闭合。

---

## 九、限制与未闭合项（必须与结论一并阅读）

1. 远端 17 个非 main 分支的 blob 级"零差异"结论**未由本轮重算**，仅抽查计数与结构性结论。
2. `codex/execution-reliability-standards` 的 8 个文件、`codex/frozen-roadmap-deepseek-v1`
   的 137 个文件**未逐份打开**；是否仍需要属 Owner 决策。
3. 两份 `EXTERNAL_DEPENDENCIES.md` 的 65 行差异**未逐行重算**（仅比行数/字节/摘要），
   "全部为仓库副本新增或更正"沿用既有判定。
4. `crates/archeaxis-archive` 与 Rust v3 schema 属禁止处理区，`v3-era` worktree 的
   已暂存修改**仅登记未评审**。
5. 未做"人手点界面"级验收（provenance 显示文本、重试行为）。
6. 未做真实 Vault 往返、真实旧库迁移、签名安装器/干净机首用验收。
7. 全格式质量矩阵仍为 **0 complete / 14 partial / 2 custody-only**。
8. 本轮未触发任何 `install`（`environment_registry` 语义未复核）。

---

## 十、复现命令（本机，按登记的外置库）

```powershell
$T       = 'D:\All projects\OS External Configuration\10-toolchains'
$PY      = '.\.venv\Scripts\python.exe'          # 必须用项目 venv（系统 python 无 yaml）
$env:ARCHEAXIS_RUST_TOOLCHAINS = $T
$env:ARCHEAXIS_MSVC_VCVARS     = "$T\msvc\VC\Auxiliary\Build\vcvars64.bat"
$env:TESSERACT_CMD             = "$T\scoop\apps\tesseract\current\tesseract.exe"
$env:TESSDATA_PREFIX           = "$T\scoop\apps\tesseract-languages\current"
$env:DOTNET_ROOT               = "$T\dotnet"; $env:PATH = "$T\dotnet;$env:PATH"
$env:ARCHAXIS_CORE_BIN         = "$PWD\.project-local\build\cargo\debug\archeaxis-api.exe"

# 闸门（全部应退出 0）
& $PY scripts/check_path_conventions.py --json
& $PY scripts/check_architecture.py
& $PY scripts/check_language_boundaries.py
& $PY scripts/check_repository_conventions.py --source worktree
& $PY scripts/check_format_matrix.py --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json
& $PY scripts/workflow/execution_preflight.py . --json
& $PY scripts/maintenance/check_resource_boundaries.py . --purpose test
& $PY scripts/ci/check_vnext_contracts.py
& $PY scripts/ci/check_vnext_workers.py
& $PY docs/authority/taskpack-0912-r5/verify_package.py

# Python 全量 / Rust 全工作区 / 桌面
& $PY -B scripts/runtime/dev.py --pytest -- tests/ integration-tests/ knowledge_base/tests/ -q
& $PY -B scripts/runtime/dev.py -- cmd.exe /c scripts\ci\cargo_test.bat --workspace
dotnet build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj -v minimal
dotnet run --project tests/contract/Vocabulary.Tests -- tests/contract/fixtures/vocabulary-cases.json
& $PY -B scripts/runtime/dev.py -- dotnet run --project tests/runtime-paths/CoreSupervisor.Tests
& $PY -B scripts/runtime/dev.py -- dotnet run --project apps/ArcheAxis.Desktop -- --smoke .project-local/task-runtime/desktop-vnext/smoke.sqlite

# 双端一致性
git fetch origin --prune
git rev-list --left-right --count main...origin/main      # 期望 0  0
git ls-remote origin HEAD
gh pr list --repo DTALEX66/ArcheAxis-Knowledge-OS --state open

# 治理（注意：classic protection 返回 404 属预期）
gh api repos/DTALEX66/ArcheAxis-Knowledge-OS/rulesets
gh api repos/DTALEX66/ArcheAxis-Knowledge-OS/rulesets/20849492
```

> 注：**不要**直接 `cargo test`（须经 `dev.py`），**不要**漏绑
> `TESSERACT_CMD`/`TESSDATA_PREFIX`（OCR worker 会正确失败闭合，被误读为回归）。

---

## 十一、关联记录

- 提示词：`docs/current/HERMES-FULL-AUDIT-PROMPT-20260918.md`
- 被审报告：`docs/current/DSH-COMPLETION-REPORT-20260918.md`
- 远端分支分类：`docs/current/R5-BRANCH-DISPOSITION-20260918.md`
- 本地分支分类：`docs/current/R5-LOCAL-BRANCH-DISPOSITION-20260918.md`
- 状态侧车：`docs/current/R5-STATE.json`、`docs/current/R5-EXECUTION.md`
- 权威任务入口：`docs/authority/taskpack-0912-r5/{TASKS.json,REMAINING-WORK.json,EXECUTOR-START.md}`
- 外置依赖登记：`docs/environment/EXTERNAL_DEPENDENCIES.md`、
  `config/environment/capability-requirements.yaml`
