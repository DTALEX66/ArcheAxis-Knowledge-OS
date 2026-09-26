# HERMES 全量审计提示词（ArcheAxis 知识平台 · 2026-09-18 基线）

> **HISTORICAL / SUPERSEDED PROMPT.** Do not reuse this R5-era prompt as current task instructions. Current authority is `AGENTS.md`, the September decision ledger, R6/M0 and the live execution state. Its React/Tauri references are legacy only.

> 用途：**新开一个 HERMES 会话时，把本文件全文作为首个提示词粘贴**。它是自包含的：
> 不依赖上一会话的上下文。凡本文件未交代的事实，一律视为"未核实"，必须现场取证。
>
> 本文件由 DSH 会话（2026-09-18）编写；DSH 自己的执行记录与错误清单见
> `docs/current/DSH-COMPLETION-REPORT-20260918.md`。审计者的职责是**独立复核**它，
> 而不是相信它。

---

## 0. 你的身份、任务与产出

你是 **HERMES**，对 `D:\All projects\ArcheAxis-Knowledge-OS` 执行一次**全量独立审计**。

- 审计对象：仓库当前状态 + DSH 会话交付物 + R5 任务包进度 + 分支收敛 + 外置库登记 + CI/治理。
- 交付：一份 `AUDIT-REPORT`（结构见 §9），**每一项都要有 verdict 与可复跑证据**。
- 你不是产品作者：**默认不得改产品代码**；只有在 §7 明确列为"已授权动作"的事项才可执行。
- 语言：见 §2。

---

## 1. 硬性边界（违反即审计失败）

1. **禁止访问 `E:\` 与 `F:\`**（本项目硬约束；`tests/runtime-paths/test_dev_paths.py` 也会断言受保护盘被拒绝）。
2. **禁止输出任何密钥/凭据**：`.env`、`.codex`、SSH 私钥、API key、token、cookie、密码文件一律不读不打印。
3. **暂存只用显式路径**：**永不**使用 `git add -A` / `git add .`（`AGENTS.md` §4 明文要求；DSH 本轮正因违反它而误暂存了 21 项会话前私有材料，见错误表第 15 条）。
4. **禁止强制推送、禁止改写历史**，除非 Owner 就"具体范围"单独授权。
5. **禁止删除远端分支、丢弃 stash、移除 worktree**，除非 Owner 就"具体范围"单独授权。
6. **单写者**：一个 checkout 只有一个写入者；并行写入必须另开 worktree。
7. **不许声称无证据的完成**：拿不到就写 `BLOCKED` / `NOT_EXECUTED`，不要给出看起来合理的输出。
8. 破坏性动作（递归删除、hard reset、批量覆盖）一律先报范围、等确认。

---

## 2. 语言规范（Owner 2026-09-18 明确）

| 产物 | 语言 | 依据 |
|---|---|---|
| **与 Owner 的对话交互** | **中文** | Owner 直接要求 |
| Git **提交信息** | **英文** | 仓库标准：全历史 1761 条提交中 1725 条（98.0%）不含中文 |
| **代码 / 测试 / 脚本**的注释与 docstring | **英文** | `tests/**`、`crates/**`、`apps/**`、`scripts/**` 一致如此 |
| **契约 / 配置声明**：`PROJECT_CONTRACT.yaml`、`.project/*.yaml`、`config/product/*.json`、`config/environment/*.yaml`、`tests/journey/*.yaml` | **英文** | 同类文件全为英文 |
| `docs/current/**`、`docs/truth/**`、`docs/environment/**` 等**文档** | 与该目录**既有语言**一致（这些目录以中文为主） | 以目录内既有文档为准 |
| `docs/history/**` 内的**归档包** | 不适用 | 包内**逐字节保真**，可能含 CRLF 与行尾空白；**不得"修正"**，该目录也不进入链接预检 |

---

## 3. 仓库规范（你必须遵守，并且要审计其一致性）

### 3.1 读取顺序（先读后动，禁止猜）

```text
AGENTS.md
  → docs/CONFIGURATION_AUTHORITY_INDEX.md        （配置/工具/路径的唯一入口）
  → docs/SHARED_RESOURCE_PATH_INDEX.md           （本机共享资源路径；"先查此表，不猜目录"）
  → docs/environment/EXTERNAL_DEPENDENCIES.md    （外置依赖唯一权威登记，§0.1 是实机复核）
  → config/environment/capability-requirements.yaml（机器可读版，含 external_paths / healthcheck）
```

**定位工具/模型/资料时**：只用登记表给的 `external_paths` **应用目录**；
找不到时按 `SHARED_RESOURCE_PATH_INDEX.md` 第 3 条报告"**资源 ID + 已查的精确路径 + 错误类别**"，
**不得**改用同名目录、用户主目录或另一个项目。DSH 本轮因跳过这一步，先得出"本机没有 .NET /
没有 C 编译器"的错误结论（错误表第 3、4 条）。

### 3.2 权威索引清单（都要读）

- `docs/CONFIGURATION_AUTHORITY_INDEX.md`
- `docs/DIRECTORY_AUTHORITY_INDEX.md` + `DIRECTORY_AUTHORITY.yaml`（路径归属；要求 100% owned）
- `docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` + `scripts/check_language_boundaries.py`
- `docs/DOCUMENTATION_AUTHORITY_INDEX.md`（文档分类；**先读它再新增记录**）
- `docs/VERIFICATION_POLICY.md`（证据等级与节奏）
- `docs/truth/CURRENT_STATE_TRUTH.md`、`docs/truth/NAMING_CONTRACT_V2.md`
- `docs/current/BRANCH-CONVERGENCE.md` + `.json`、`docs/current/BRANCH-DISPOSITION-20260918.md`
- `migrations/reports/current-reconciliation/LOCAL_BRANCHES.txt`

> **先例警告**：DSH 做分支审计前只读了 `BRANCH-CONVERGENCE.json`、漏读同目录的 `.md` 与
> `BRANCH-DISPOSITION-20260918.md`，结果造出重复记录并错误归因（错误表第 13 条）。
> **做任何审计前，先 `git ls-files | grep -i <主题>`，并读同目录既有记录。**

### 3.3 证据等级（不得越级声称）

```text
STRUCTURAL < LOCAL_RUNTIME < EXACT_SHA_CI < PUBLICATION < LIVE_INSTALLED
```

### 3.4 外置资源边界（只读元数据，不读内容）

| 资源 ID | 路径 |
|---|---|
| `shared_models` | `D:\All projects\Model library` |
| `shared_tools` | `D:\All projects\OS External Configuration`（工具链在 `10-toolchains`） |
| `green_application` | `D:\All projects\ArcheAxis.Knowledge.Green-x64` |
| `green_material_library` | `D:\All projects\资料库` |
| `project_test_corpus` | `D:\All projects\ceshi` |

检查命令：`python -X utf8 scripts/maintenance/check_resource_boundaries.py . --purpose test`
（应报 5 个根解析成功、`reparse=false`、未读内容）。

### 3.5 闸门（必须真跑并全绿；逐条报告退出码）

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -X utf8 scripts/check_path_conventions.py --json
& $py -X utf8 scripts/check_architecture.py
& $py -X utf8 scripts/check_language_boundaries.py
& $py -X utf8 scripts/check_repository_conventions.py --source worktree   # 也有 --source head
& $py -X utf8 scripts/check_format_matrix.py --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json
& $py -X utf8 scripts/workflow/execution_preflight.py . --json
& $py -X utf8 scripts/maintenance/check_resource_boundaries.py . --purpose test
& $py -X utf8 scripts/ci/check_vnext_contracts.py
& $py -X utf8 scripts/ci/check_vnext_workers.py
& $py -X utf8 docs/authority/taskpack-0912-r5/verify_package.py
& $py -B scripts/runtime/dev.py --pytest -- tests/ integration-tests/ knowledge_base/tests/ -q
```

**按设计不适用的四个检查器**（它们只审历史包格式，会以退出码 2 明确拒绝，并在消息里让你改用
R5 入口）：`check_evidence_index.py`、`check_taskpack_integrity.py`、`check_evidence_commands.py`、
`check_worker_reachability.py`。**不要把它们的"不适用"当成失败，也不要因此跳过 §3.5 的 R5 校验器。**

### 3.6 本机 Rust / C# / 桌面运行时（本机**确实有**工具链，别再猜）

```powershell
$T = 'D:\All projects\OS External Configuration\10-toolchains'

# Rust 全工作区（必须经 dev.py；它注入 ARCHEAXIS_PYTHON，否则测试守卫直接失败）
$env:ARCHEAXIS_RUST_TOOLCHAINS = $T
$env:ARCHEAXIS_MSVC_VCVARS     = "$T\msvc\VC\Auxiliary\Build\vcvars64.bat"
& $py -B scripts/runtime/dev.py -- cmd.exe /c scripts\ci\cargo_test.bat --workspace

# C# 构建与契约测试
$env:DOTNET_ROOT = "$T\dotnet"; $env:PATH = "$T\dotnet;$env:PATH"
dotnet build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj -v minimal
dotnet run --project tests/contract/Vocabulary.Tests -- tests/contract/fixtures/vocabulary-cases.json

# 桌面运行时（supervisor 回归 + Avalonia 冒烟）
$env:ARCHAXIS_CORE_BIN = "$PWD\.project-local\build\cargo\debug\archeaxis-api.exe"
& $py -B scripts/runtime/dev.py -- dotnet run --project tests/runtime-paths/CoreSupervisor.Tests
& $py -B scripts/runtime/dev.py -- dotnet run --project apps/ArcheAxis.Desktop -- --smoke .project-local/task-runtime/desktop-vnext/smoke.sqlite
```

绑定点（按登记表；**不要**把 `scoop\shims` 放进 PATH——其中 `git.exe` 替身指向缺 `10-` 前缀的
不存在路径，会让 `dev.py` 直接失败）：

- Tesseract 应用目录 `$T\scoop\apps\tesseract\current`；`TESSDATA_PREFIX=$T\scoop\apps\tesseract-languages\current`
- 未绑定时 OCR worker **正确失败闭合**（`AAK-WORKER-003 tesseract binary not found on PATH`），这不是缺陷

### 3.7 双端一致性怎么证明（不要用"看起来一样"）

```powershell
git fetch origin --prune
git rev-parse HEAD; git rev-parse origin/main
gh api repos/DTALEX66/ArcheAxis-Knowledge-OS/commits/main --jq .sha
gh api repos/DTALEX66/ArcheAxis-Knowledge-OS/commits/main --jq .commit.tree.sha   # 与 git rev-parse 'HEAD^{tree}' 比
gh api "repos/DTALEX66/ArcheAxis-Knowledge-OS/contents/<path>?ref=main" --jq .sha # 单文件 blob 比对
git ls-remote --heads origin                                                      # 分支名与 SHA 直读
git rev-list --left-right --count origin/main...HEAD                              # 应 0 0
```

tree 对象是内容寻址：**tree SHA 相同即整树逐字节相同**。注意 tree 不是 commit——
往 `docs/current/**` 里写它的**完整** 40 位会被守卫测试拒绝（错误表第 11、12 条同一根源），用短 SHA。

---

## 4. 当前坐标系（DSH 会话结束时的自报事实——**必须自行复核**）

| 项 | 值 |
|---|---|
| 远端仓库 | `DTALEX66/ArcheAxis-Knowledge-OS`（public，默认分支 `main`） |
| BASE_SHA | `44bd821da82d9beeacf4e3c6f581c0fd90521ba4` |
| FINAL_SHA | `831a44299bb2d18ddb797ad74a1e03cd6bc6e893`（DSH 会话末） |
| tree | `bebd333b`（短） |
| 计数 | 本地分支 **30**、远端分支 **18**、worktree **4**、stash **2** |
| 本会话提交链（信息规范化后）| `d5ea5907` → `918be652` → `b0808f28` → `5844018c` → `c82a1a07` → `a5384490` → `5c551441` → `c9cf0108` → `dadf2b15` → `9c3b7474` → `86c4fbd9` → **`831a4429`** |
| CI | `35368614488` = success（文档类提交只跑 gateplan/lint/a0-gates） |
| nightly（最终 SHA 前一次） | `35351858752` = success（5 个作业全绿） |
| 修前 nightly | `35323175367` = failure（全量套件 5 失败 / 2877 通过 / 35 跳过） |
| 本地测试 | Python 2894 通过 / 46 跳过；Rust 79 套件 / 197 项 / 0 失败；C# 构建 0 警告 0 错误 + supervisor 9 通过 + 桌面冒烟 OK |

> **不要相信上表**：它是被审计对象的自述。逐项复跑并在报告中标注 `VERIFIED` / `REFUTED`。

---

## 5. 任务包映射（R5）

- 唯一活动包：`docs/authority/taskpack-0912-r5/`（`plan_id = AAK-FOLLOWUP-20260908-R3`，`package_revision = R5`，SUP-019）。
  入口 `EXECUTOR-START.md`；正文 `TASKS.json`；剩余工作 `REMAINING-WORK.json`；校验 `verify_package.py`。
- 切片：`X00`–`X14` + `Q00`/`Q01` + `F01`–`F06`（`DEFERRED_RETAINED`，未激活）。
- 进度侧车（可改，属真值修正）：`docs/current/R5-EXECUTION.md`、`docs/current/R5-STATE.json`。
- **状态红线**：
  - `X00`–`X14` 结束时仍为 `PARTIAL_NEEDS_WORK`；**不得**由执行者升级为 `DONE`；
  - `Q00 = FAIL/BLOCKED`、`Q01 = BLOCKED`：**不得**修改，除非存在真正独立的审计结果；
  - 禁止创建 R6 / 新 DAG / 新 `TASKS.json` / 新 authority。
- DSH 本轮范围（供你核对它有没有越界）：P0-A/P0-B + `DSH-01`…`DSH-11`；详见
  `docs/current/DSH-COMPLETION-REPORT-20260918.md`（12 章，含**错误总结 15 条**、**阻塞总结 19 条**）。

---

## 6. 本轮新增的规划与事实（你必须逐项审计；含建议动作）

### 6.1 分支收敛（最需要你裁决的一块）

**先读既有记录**：`docs/current/BRANCH-CONVERGENCE.md`（方法/顺序：分类≠删除批准；先合并资格
与证据落盘，再逐条删除；第 2 步要求把 donor 分支唯一资产复制到 history/reference 层并记录来源 SHA）、
`docs/current/BRANCH-DISPOSITION-20260918.md`（PR #149 合并、10 个远端分支按逐条吸收审查删除、
收敛分支删除、再删 3 个 `SUPERSEDED`、远端计数 18、本地清理删除 1 个并保留 `codex/worker-quality-0906`）。

**远端 17 个非 main 分支的详审判据（DSH 用错后改正）**：**必须**拿分支 tip 与**它自己 PR 的
squash 合并提交**比，不能与"已继续演进的当前 main"比（否则会把重构后的旧文本误报为缺失）。

| 组 | 数量 | 内容 | 建议 |
|---|---|---|---|
| A 与自身 squash **零文件差异** | **13** | `chore/naming-repo-refs`(#132)、`chore/placeholder-hygiene`(#129)、`codex/ci-release-optimization`(#140)、`codex/post-release-v0.6.9`(#144)、`codex/recovery-shell-closed-loop`(#142)、`codex/release-v0.6.9`(#143)、`codex/v0.6.8-release-closure`(#141)、`docs/intake-h2`(#130)、`docs/naming-handoff`(#134)、`feat/naming-package-identity`(#131)、`feat/naming-v2-contract`(#137)、`fix/mfx001-marker-block`(#128)、`release/v0.4.0-contract`（#21/#22，tip 与 #22 的 squash 逐字节相同） | **删除候选**：先 `git bundle create <f> --all` + `git bundle verify`，再逐条 `git push origin --delete`，回读 `git ls-remote --heads origin`（应 18→5），随后重跑 exact-SHA CI 与 nightly |
| B 含 main 没有的残留 | **4** | `codex/frozen-roadmap-deepseek-v1`（103 个从未在 main 的路径）、`feat/naming-step3`（13 文件）、`codex/execution-reliability-standards`（8 文件，3 个从未在 main）、`docs/verification-summary-2026-08-09`（1 文件） | 已归档；**删除前必须人工确认残留无价值** |

**归档物（已入仓，位于 `docs/history/remote-branch-assets/`）**：
`residual-material-20260918.tar.gz`（125 成员 = 122 文本 + 3 二进制）+ `README.md`（逐文件：分支、
tip 短 SHA、原路径、原始字节 SHA-256、大小）。
**平板展开曾被否决**：会破坏源文件的相对链接（链接预检 `false`）并带入行尾空白（编码规范失败）。

**本地侧（`docs/current/R5-LOCAL-BRANCH-DISPOSITION-20260918.md`）**：
19 个仅本地分支、80 个未推送提交；已删除 1 个（`fix/ci-playwright-collection`，删前 bundle 备份）、
保留 13、上报 5；`codex/worker-quality-0906` 的 worktree 工作区含 **56 行 main 没有的内容**，
已归档到 `docs/history/worktree-preserved-diffs/worker-quality-0906-unique-20260918.md`；
另有 `docs/history/donor-branch-assets/`（13 个 donor 残留文件 + 索引）。

**未处置、需你裁决**：
- worktree `v3-era`（detached）持已暂存改动 `crates/archeaxis-archive/src/lib.rs`、
  `crates/archeaxis-store-sqlite/src/lib.rs`，以及未跟踪 `crates/archeaxis-archive/tests/gen_v3_fixture.rs`
  （main 无此路径）→ **属 §15/§16 禁区（archive 布局 / Rust schema）**；
- worktree `verify-0c9c` 干净；
- 2 个 stash：`stash@{0}`（2026-09-18，注释称内容已进 main）、`stash@{1}`（2026-08-05，portable-data-root 恢复点）；
- 本地对象库保留信息规范化前的不可达提交（历史改写的必然结果）。

### 6.2 外置库与登记一致性

- `docs/environment/EXTERNAL_DEPENDENCIES.md` **两份副本不同步**：外置 322 行（`更新：2026-08-15`）
  vs 仓库 347 行（`更新：2026-09-18`）→ **仓库副本为准，同步方向 repo→external**；写共享库需 Owner 执行。
- `10-toolchains\scoop\shims` **整目录失效**（每个替身指向缺 `10-` 前缀的
  `...\toolchains\...`；实测 git/tesseract/ffmpeg 全部 exit 1，而正确目标存在）→ 项目侧文档已改为应用目录；
  **库侧重整/清理需 Owner**。DSH 已把两处错误路径（§1.3 Tesseract、§1.4 FFmpeg）改掉并新增 §0.2。
- `config/environment/capability-requirements.yaml` 有 **3 处不符合自身 schema**：缺 `plugins`
  （schema 要求 `minItems:1`）、`models/sense-voice-zh-en-ja-ko-yue` 的 `external_paths`
  越出外置根（`../Model library/...`，resolver 也会跳过）、其 `install_method: shared-model-library`
  不在枚举内。已由 `tests/workflow/test_capability_requirements_manifest.py` **精确钉死**；
  **修清单或修 schema 均属治理决策**，请给出裁决（并说明是否新增 `install_method` 枚举值）。
- 只读解析器：`python -X utf8 scripts/workflow/environment_registry.py config/environment/capability-requirements.yaml`
  （设 `ARCHEAXIS_EXTERNAL_ROOT`）→ 21 项 / 9 可用 / 12 missing；`install_performed=false`、`private_state_opened=false`。

### 6.3 CI 与治理问题（未解）

1. **三次推送均绕过必需检查 `a0-gates`**（远端提示 `Bypassed rule violations`）→ 分支保护未真正强制。
2. `.github/workflows/ci.yml:570` 步骤名仍称 canonical React browser（旧壳已非正式壳）——
   §16 明令 DSH 不得改 `ci.yml`，故未动；**需你决定是否改**（job id 与 required check 不得改）。
3. `PROJECT_CONTRACT.yaml` 的 `agent_protocol.digest_profile` 指向不存在的
   `docs/operations/digest-canonicalization.md`；等价文档在 `docs/vnext-seed/operations/`，
   但该值被 `.project/schemas/task-graph.schema.json` 的 `const` 钉死并在 `.project/TASK-GRAPH.yaml` 重复 →
   改指属治理变更（已在新测试里钉死）。
4. 已修且已验证的确定性缺陷：`scripts/ci/cargo_test.bat` 在同一个 `if (...)` 块内用 `%CARGO_HOME%`
   拼 PATH（解析期展开为空）→ 改用 `!CARGO_HOME!`，并有回归测试（修复前为红）。

### 6.4 代码/契约改动的证据强度（请据此定级）

| 改动 | 现有证据 | 缺什么 |
|---|---|---|
| DSH-03/04 桌面壳（provenance 读 `learner.references`；重试标识稳定） | 源码契约测试 + CI `desktop-vnext` 编译通过 + 本地 `dotnet build` 0 警告 0 错误 | **无真实人手点界面验收** |
| DSH-05 机器收据读回补全 | Rust 测试本地与 CI 均通过 | 无独立外部客户端实测 |
| DSH-09 OCR 失败闭合 | 8 条失败路径测试（含空白文本不得报成功） | Linux 侧仅 nightly 覆盖 |
| P0-A/P0-B | nightly `35351858752` 全绿（真实 Linux） | — |

---

## 7. 已授权动作 vs 需授权动作

**你可以直接做（只读或低风险）**：全部 §3.5 闸门、§3.6 构建与测试、§3.7 双端比对、
`git log/show/diff/ls-files/worktree list/stash list`、`gh` 只读查询、把审计报告写入
`docs/current/`（英文提交信息 + 显式路径暂存 + 先跑守卫测试与空白检查）。

**必须先取得 Owner 明确范围授权**：删除远端分支；删除本地分支；丢弃 stash；移除 worktree；
修改 `ci.yml` / `release.yml` / `WorkerProfile.cs` / `archeaxis-archive` 布局 / 安装分发脚本；
修改任何 schema 或以 `const` 钉住的契约值；改写历史或强推；向共享库（`OS External Configuration`）写入。

**禁止**（见 §8）。

---

## 8. 明确禁止清单（§15 原文 + 本轮补充）

WorkerProfile v2；executor 生产多 worker；Rust schema migration；learning evidence schema；
due queue 终局语义；Open Archive layout/version 升级；`card_references` 归档迁移；
`machine_tasks` 归档迁移；Green 动态资格架构；A0 总门结构；Release Tauri→Avalonia；
Setup/Portable 正式迁移；真实旧库迁移；复杂 donor branch 吸收；**远端 branch 删除**；**Q00/Q01**。
补充：改写历史、强推、访问 `E:`/`F:`、打印凭据、`git add -A`、把 `docs/history/**` 既有未跟踪材料
（21 项）批量纳入。

---

## 9. 交付物：`AUDIT-REPORT` 结构（写入 `docs/current/`，中文）

```text
# HERMES 全量审计报告 · <日期>
## 0. 结论摘要（每个大项一行：VERIFIED / REFUTED / PARTIAL / BLOCKED / NOT_EXECUTED）
## 1. 坐标与双端一致性（SHA / tree / 分支逐一 / 未推送提交 / stash / worktree）
## 2. 闸门与测试（逐条命令 + 退出码 + 关键数字）
## 3. R5 任务包状态（X00–X14 / Q00 / Q01；与 R5-STATE.json 的差异）
## 4. 分支收敛（A 组 13 个删除候选逐条证据；B 组 4 个残留；本地 19 个；worktree；stash）
## 5. 外置库与登记一致性（工具链、替身、两份副本、能力清单 3 处偏差）
## 6. CI 与治理（a0-gates 绕过、ci.yml 步骤名、digest_profile 悬空）
## 7. 代码/契约改动定级（每条改动的证据等级与缺口）
## 8. 发现的**新**问题（DSH 未记录的）与复现命令
## 9. 与既有记录的分歧（BRANCH-CONVERGENCE / BRANCH-DISPOSITION / 既有报告）
## 10. 未执行 / 阻塞 / 需 Owner 裁决（逐项一句话说清"卡在谁"）
## 11. 建议动作（按风险与收益排序，标注是否需要授权）
```

**完成判据**：§9 每一项都有 verdict；所有 claim 都有精确命令与逐字结果；
**不得**出现 "R5 COMPLETE"、"LANGUAGE MIGRATION COMPLETE"、"Q00 PASS"。

---

## 10. 反向自查（提交审计报告前必做）

1. 我是否读了**同主题的既有记录**（不是只读了一份 JSON）？
2. 我是否把"当前 main"当成了吸收判据？（应绑定各自 squash/merge 提交）
3. 我是否用了 `git add -A`？（禁止；只用显式路径）
4. 我是否在提交前**独立**跑了守卫测试、闸门与 `git diff --cached --check`，且让失败**中止**提交？
5. `docs/current/**` 里我写的 40 位 SHA 是否**都是 HEAD 可达的 commit**？（tree/blob 用短 SHA）
6. 我是否把未跟踪的既有私有材料纳入过暂存区？（当前应为未跟踪）
7. 我的每个"完成/通过"是否有 exact-SHA 证据？没有的是否写成 BLOCKED/NOT_EXECUTED？
