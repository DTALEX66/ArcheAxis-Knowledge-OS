# AAOS 外部审计报告核验（2026-09-26）

- 性质：对一份外部审计/优化方案（"全面审计 + 问题定位 + CODEX 分析 + 前端重构 + 任务包 + 交接"）的**逐条事实核验**
- 方法：只读检查本地仓库、Git 引用、GitHub 远端 API、npm registry、本机 Codex 配置
- 边界：**未执行任何破坏性操作**（无删除、无 gc、无 filter-repo、无 force push、无 push）
- 裁定档位：`CONFIRMED` / `REFUTED` / `NOT EXECUTED`

## 0. 结论摘要

该报告的可执行前提与仓库真实状态**严重不符**。其核心处方（`git-filter-repo` 删除敏感数据、清理分支"外溢"、按 `1.4.0` 安装 Codex 插件、改 `preferred_auth_method`、`web_search=false`）要么基于不存在的配置项，要么会违反本仓库 `AGENTS.md` 的禁止性规则。

同时，本次核验**发现了一个报告完全没有提到的真实 P0 缺陷**：当前 HEAD 的 CI 因一个尾随空格而失败（§3.1）。

| 报告主张 | 裁定 | 依据 |
| --- | --- | --- |
| 存在未合并 PR 需处理 | **REFUTED** | 开放 PR = 0（#150→#51 全部 MERGED/CLOSED） |
| 历史中存在敏感信息泄露 | **REFUTED** | 历史唯一敏感命名文件为 `.env.container.example`（模板） |
| SSH 访问失败，需改 remote URL | **REFUTED** | remote 已是 `git@github.com:...`，`gh auth status` SSH 正常 |
| `web_search = true` 拖慢 Codex | **REFUTED** | `config.toml` 中不存在该键 |
| `preferred_auth_method` 需改为 `chatgpt` | **REFUTED** | `config.toml` 中不存在该键 |
| `network_access = true` 需关闭 | **未证实** | 仅同名片段出现，非顶层键 |
| 存在 `.codexrc` 项目规则拖慢生成 | **REFUTED** | `~/.codex/.codexrc` 与仓库内 `.codexrc` 均不存在 |
| 应安装 `@softspark/dsh-codex@1.4.0` | **REFUTED（有害）** | 包存在，但 1.4.0 面向 DSH `0.1.1-rc.2`；本机 host 为 `0.1.5-rc.2` |
| 大文件已污染产品分支历史 | **REFUTED** | 154MB 二进制**仅在** `refs/codex/**` 检查点引用中 |
| 需用 `git-filter-repo` 清理历史 | **REFUTED（越权）** | 违反 `AGENTS.md` §3/§4；且会重写全部 ref + 需 force push |
| 分支"外溢"导致仓库缓慢 | **部分成立** | 5260 个不可达对象 + 5 个临时 pack 残留为真；但非 447MB 的主因 |

## 1. 仓库真实状态（基线）

| 项 | 实测值 |
| --- | --- |
| 当前检出分支 | `codex/aaos-p3-ui-convergence-20260922`（**不是 main**） |
| HEAD | `edf9a7e56f78b1449137bf4e947db4c81f04e3af` |
| `origin/main` | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`（2026-09-20T23:34:15Z） |
| 分叉 | **领先 175 / 落后 0** |
| 工作区 | 48 个已修改 + 大量未跟踪历史文件（**未触碰**） |
| 本地分支 / 远程分支 | 27 / 7 |
| 标签 | 21（`v0.4.0` … `v0.6.14`） |
| 子模块 | **无** (`no .gitmodules`) |
| worktree | 5 个（主 + `.project-local/worktrees/*`） |
| stash | 2 |
| 引用总数 | 99（`refs/codex` 42、`refs/heads` 27、`refs/tags` 21、`refs/remotes` 8、`refs/stash` 1） |
| 仓库体积 | `size-pack` = **447.59 MiB**，in-pack 27309 |

> 命名澄清：报告中"ARCHEAXIS 云端仓库"的实际仓库身份是 `DTALEX66/ArcheAxis-Knowledge-OS`（`AGENTS.md` §5 已锁定）。

## 2. 逐项核验

### 2.1 未合并 PR —— REFUTED

`gh pr list --state open` 返回**空**。`gh pr list --state all --limit 100` 显示 #150 至 #51 全部为 `MERGED`，仅 #136、#70、#68 为 `CLOSED`。报告示例中的"未合并 PR：#23, #27"不存在。

### 2.2 敏感信息泄露 —— REFUTED

对 `git rev-list --objects --all` 全历史按 `\.env$|id_rsa|id_ed25519|\.pem$|\.p12$|\.pfx$|credentials|\.npmrc|\.pypirc|auth\.json` 扫描，唯一命中：

```
a9812f8b2461d5de4ebd6a6c8b4dfda86cc8307  .env.container.example
```

`.env.container.example` 是**模板文件**（`.example` 后缀），不是凭据。报告所称"发现 repository.settings 包含明文密码"在本次扫描中无任何证据支持。

> 说明：本仓库**确实**将 `~/.codex/auth.json`、SSH 私钥等视为禁读禁打（`AGENTS.md` §3、§8），本次核验同样未读取、未打印其内容。

### 2.3 大文件与 447 MiB 体积的真正来源 —— 报告误判

最大 blob（`git verify-pack`）：

| 大小 | 路径 | 所在引用 |
| --- | --- | --- |
| 154,463,538 B | `docs/history/task-artifacts/v0.6.11-candidate-.../ArcheAxis Knowledge_0.6.11_x64-setup.exe` | **仅** `refs/codex/turn-diffs/checkpoints/**` |
| 154,153,926 B | `docs/history/task-artifacts/rc/ArcheAxis Knowledge_0.6.14_x64-setup.exe` | **仅** `refs/codex/turn-diffs/checkpoints/**` |
| 78,993,877 B | `docs/history/desktop-attachments/ArcheAxis_Today_Conversation_Archive_HERMES_TaskPack_2026-07-28_v1.0.zip` | **仅** `refs/codex/turn-diffs/checkpoints/**` |
| 24,159,226 B | `OSUI/ArcheAxis-Knowledge-OPEN-DESIGN-UI-TaskPack-v1-2026-08-12.zip` | `refs/codex/snapshots/**` + 5 个产品分支 |

**关键事实**：前三个巨型对象**不在任何产品分支上**，只被 `refs/codex/turn-diffs/checkpoints/**` 引用（42 个 `refs/codex` 引用）。HEAD 树内最大跟踪文件仅 5,264,396 B。

**直接后果**：报告的下一步处方"`git-filter-repo --sensitive-data-removal --invert-paths --path <file>`"是在错误对象上作业——它会重写**全部 ref**（含这 42 个 `refs/codex`），且清不掉正确目标。

**归属警告**：`AGENTS.md` §3 明确禁止仅凭名称主张 Hermes/Codex 等 workflow 基础设施文件的所有权。`refs/codex/turn-diffs/checkpoints/**` 是 **Codex CLI 自己的会话检查点存储**，不是本项目产物，不得删除。

### 2.4 分支"外溢"与不可达对象 —— 部分成立

- `git fsck --unreachable` 报 **5260** 个不可达对象 —— 成立
- `.git/objects/pack/` 存在 **5 个 `tmp_pack_*` 残留**（约 8.95 MiB `size-garbage`）—— 成立
- 27 个本地分支中 **20 个未推送到 origin**，其中 `work/tp12-facades` 最新提交为 2026-07-14（逾 2 个月）

但报告把 447 MiB 归因于此是**误判**：主因是 §2.3 的 `refs/codex` 检查点（单个 pack 461,425,949 B）。

### 2.5 SSH / HTTP / 权限 —— REFUTED

```
origin  git@github.com:DTALEX66/ArcheAxis-Knowledge-OS.git (fetch)
origin  git@github.com:DTALEX66/ArcheAxis-Knowledge-OS.git (push)
gh auth status: ✓ Logged in to github.com account DTALEX66 (keyring)
                Git operations protocol: ssh
                Token scopes: 'gist', 'read:org', 'repo', 'workflow'
```

报告建议的 `git remote set-url origin git@github.com:...` 是**无操作**——已经是该值。
`gh` 已认证且 SSH 协议生效，报告所称"SSH 访问失败 / HTTP 受限"无据。

**真实且唯一的权限缺口**：token scope 列表中**没有 `admin:org`**。因此报告表格里"调整组织策略允许 HTTPS""检查 Organization 限制"这类动作在当前凭据下**不可能执行**（属 NOT EXECUTED，而非已完成）。

### 2.6 CI/CD 授权 —— 报告未提，但真实故障在别处

远端工作流：`ci.yml`、`nightly.yml`、`release.yml`、`vnext-ci.yml`，全部 `active`。

**`main` 的 CI**：最近 6 次 push 运行中 5 次 `success`，最新成功 `35545049468`（2026-09-20T23:34:34Z）。**授权/auth 无故障**。

**`nightly` 在 `main` 上连续 6 天失败**（报告完全未提及）：

| 运行 | 结论 | 日期 |
| --- | --- | --- |
| 36230109236 | failure | 2026-09-26 |
| 36114760216 | failure | 2026-09-25 |
| 35975041891 | failure | 2026-09-24 |
| 35837636715 | failure | 2026-09-23 |
| 35705091183 | failure | 2026-09-22 |
| 35580210519 | failure | 2026-09-21 |

失败作业为 `full-suite`；`py-compat (3.11)` 与 `py-compat (3.13)` 均 `success`。

## 3. 本次核验新发现的真实缺陷

### 3.1 P0 —— 当前 HEAD 的 CI 红且原因已定位（CONFIRMED）

**实测**：对 HEAD `edf9a7e5` 的 push 运行 `36230328734`：

```
success    gateplan
failure    lint
skipped    test / rust-vnext / desktop-* / browser-smoke / ...
failure    a0-gates          <- 因 lint 失败而连坐
```

**根因**：CI `lint` 作业的第一个校验步骤 `python scripts/check_repository_conventions.py --source head` 失败。

本地复现（`.venv/Scripts/python.exe`，Python 3.13.14）：

```
[check_repository_conventions] exit=1
docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md: trailing-whitespace: line ends with space or tab
repository convention check failed: 1 issue(s)
[check_architecture]        exit=0
[check_language_boundaries] exit=0
[check_format_matrix]       exit=0
[check_path_conventions]    exit=0
```

**精确定位**到 `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md` **第 4 行**（HEAD 提交内容）：

```
HEAD     : "Scope: the canonical Avalonia surface in `apps/ArcheAxis.Desktop/`  "  (len=68, 尾随 2 空格)
WORKTREE : "Scope: the canonical Avalonia surface in `apps/ArcheAxis.Desktop/`"     (len=66, 已修好)
```

该缺陷由 `4d496831`（2026-09-23 `docs(ui): map AAOS suite coverage`）引入。

**关键点**：该修复**已经存在于工作区**，但**尚未提交**。因此这不是一个需要"修 bug"的任务，而是一个**提交已存在修复**的任务。

> 另注：本地 `ruff` 无法运行，原因为沙箱拒绝写 `.ruff_cache`（`os error 5`）。这是**本地沙箱限制**，与 CI 的 ruff 结论无关，CI 上的 ruff 结果本次 **NOT EXECUTED**。

### 3.2 真实性能瓶颈在 Codex 会话存储，而非网络开关

`C:\Users\ALEX\.codex` 实测占用 **4.98 GB**：

| 大小 | 文件 |
| --- | --- |
| 649.6 MB | `thread_history_1.sqlite` |
| 393.8 MB | `logs_2.sqlite` |
| 346.3 MB | `archived_sessions/rollout-2026-09-13T...jsonl` |
| 307.1 MB ×2 | `plugins/.plugin-appserver/codex.exe`、`.sandbox-bin/codex.exe` |
| 283.6 MB | `plugins/.plugin-appserver/codex.exe.pre-sync-bak` |
| 271.9 MB | `sessions/2026/09/24/rollout-...jsonl` |
| 182.6 MB | `sessions/2026/09/21/rollout-...jsonl` |

**这是一个有据可依的优化方向**，而报告中"关 `web_search` / 关 `network_access`"的处方针对的是**不存在的键**。

### 3.3 Codex `config.toml` 实际内容（键名，值不打印）

存在的顶层键：`model_provider`、`sandbox_mode`、`model`、`model_reasoning_effort`、`personality`、`model_verbosity`、`approval_policy`、`project_doc_max_bytes`、`service_tier`、`notify`，以及 `[mcp_servers.node_repl]`、`[model_providers.cc-switch-official]`、`[model_providers.custom]`、`[desktop]`、`[marketplaces.*]`、`[plugins.*]`。

| 报告主张的键 | 实测 |
| --- | --- |
| `network_access` | 非顶层键（仅同名字符串片段出现）→ **未证实** |
| `web_search` | **不存在** |
| `preferred_auth_method` | **不存在** |
| `.codexrc` | **不存在**（`~/.codex/.codexrc` 与仓库内均无） |

已生效的相关值：`project_doc_max_bytes = 65536`（对应报告"AGENTS.md 全局提示加载"一项，该机制**真实存在**）；`model_reasoning_effort = "low"`、`model_verbosity = "low"`（报告建议"降低 reasoning_effort 提速"**已是当前状态**，无优化空间）。

### 3.4 DSH / Codex 插件 —— 报告的安装命令会破坏兼容性

`@softspark/dsh-codex` **确实存在**（Apache-2.0，SoftSpark，`dsh.bundle.patch` 存在）。但：

| 项 | 实测 |
| --- | --- |
| registry `latest` | **1.6.2** |
| 报告指定的 1.4.0 | 存在，但面向 **DSH `0.1.1-rc.2`** |
| 本机 DSH host | `dsh-plugin-desktop` **2.0.13**，`@deepseek-ai/dsh-llm` = **0.1.5-rc.2**，`dsh-session` = **0.1.5-rc.2**，`dsh-attachment` = **0.1.5-rc.2**，`@deepseek-ai/cordis` = **4.0.2** |

该包 README（外部内容，作为数据）自述：*"Published `1.4.0` requires the older DSH host; use a local candidate tarball for the new host until `1.5.0` is published."*

**因此按报告执行 `dsh plugin --profile web add @softspark/dsh-codex@1.4.0` 会装入一个与本机 host 不匹配的版本。**

补充事实：
- 另有**不同的**包 `dsh-codex`（维护者 yan-zero，latest `0.3.1`，面向 DSH `0.1.7-rc.2`，提供 `imagegen`/`read_image` URL/`web_search`/代理设置）——与 `@softspark/dsh-codex` 是**两个不同项目**，报告未区分。
- 本机**不存在 `~/.dsh` 目录**，因此报告中的 `dsh plugin --profile web add ...` 在该 profile 下**无法按原文执行**（NOT EXECUTED）。
- `@softspark/dsh-codex@1.4.0` 的 peer 为 `dsh-session`，而 `dsh-session` 在 **1.5.0** 才加入 peer 列表，进一步说明版本-宿主配对敏感。

### 3.5 `release.yml` 处于冻结状态

`release.yml` 中 `publish` 作业的守卫为 `if: ${{ false }} # R6 release freeze`。报告的"打包与部署流水线"计划若涉及发布，**会被此守卫静默拦下**，必须先由 Owner 授权的发布任务替换该守卫（`AGENTS.md` §6 的 no-release 边界）。

### 3.6 `verify` 工具本次异常（记录，非仓库问题）

`verify npm @softspark/dsh-codex` 返回工具内部 schema 错误（`value.summary.exists` 等未声明属性）。已改用 `registry.npmjs.org` 直接读取，结论以 §3.4 为准。

## 4. 修正后的清理优先级与执行建议

> 下表**刻意不含** `git-filter-repo`、`filter-branch`、`forced push`、批量 `branch -D`、对 `refs/codex/**` 的任何写操作。

| 优先级 | 项 | 事实 | 建议动作 | 风险/回滚 |
| --- | --- | --- | --- | --- |
| **P0** | HEAD CI 红 | `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md:4` 尾随空格（修复已在工作区，未提交） | 单独提交该文件（显式路径），重跑 CI 确认 `lint` + `a0-gates` 转绿 | 纯空白改动，`git revert` 即可 |
| **P0** | `nightly` 连续 6 天红（main） | `full-suite` 失败，`py-compat` 通过 | 先取失败日志定位（需可从 Windows 写缓存目录调用 `gh run view --log-failed`），再判定 | 只读排查 |
| **P1** | 真实性能瓶颈 | `~/.codex` = 4.98 GB，`thread_history_1.sqlite` 649.6 MB | 在 Codex 空闲时归档/轮转 `archived_sessions` 与历史 rollout；核对 Codex 官方清理方式后再动 | 属**用户级全局配置**，`AGENTS.md` §3 要求显式授权 |
| **P1** | Codex 插件版本错配 | 报告建议 1.4.0，本机 host 为 `0.1.5-rc.2` | 改用与 host 匹配的版本，或按上游 README 用本地 tarball 验证；**先隔离 `DSH_HOME` 评估** | 装错版本影响 DSH 功能，可卸载回滚 |
| **P2** | 5260 不可达对象 + 5 个 `tmp_pack_*`（8.95 MiB） | `git fsck --unreachable`、`git count-objects -vH` | 先 `git gc`（安全）；`git prune` 仅在确认无 `refs/codex` 依赖后由 Owner 授权执行 | 中断的 gc 曾留下这些 `tmp_pack`；gc 可重跑 |
| **P2** | 20 个未推送本地分支，`work/tp12-facades` 停滞 >2 月 | `git branch -r` 比对 | 逐个判定"合并/归档/保留"，**一次一个**，删除需 Owner 确认 | 删除前可先 `git tag archive/<branch>` 留引用 |
| **P2** | 2 个 stash 长期滞留 | `stash@{0}`、`stash@{1}` | 导出为 patch 存 `docs/history/worktree-preserved-diffs/` 后再决定 `stash drop` | patch 文件即回滚保障 |
| **P3** | 21 个标签 | `v0.4.0` … `v0.6.14` | 暂不动；报告"标签过时需清理"无证据 | — |
| **—** | 敏感信息泄露 | **未发现** | **不建议**执行 `git-filter-repo` | 越权且破坏 42 个 `refs/codex` |
| **—** | SSH/HTTP/权限 | **正常** | **不建议**改 remote URL | 无操作 |

## 5. 对报告其余部分的裁定

| 报告章节 | 裁定 | 理由 |
| --- | --- | --- |
| 前端重构计划（里程碑/工时估算） | **NOT EXECUTED / 无依据** | 报告自述"假如未提供设计稿"。仓库内无该设计稿基线，估时与验收标准无法核验 |
| 责任矩阵（张三/李四/王五…） | **REFUTED** | 示例性占位姓名与 `@example.com`，非真实联系人；不可作为交接材料 |
| 监控告警（Prometheus+Grafana） | **NOT EXECUTED** | 无证据表明本项目采用该栈；`release.yml` 处于冻结状态 |
| 任务包 JSON（`dsh run_task` / `dsh apply_controlled_patch`） | **NOT EXECUTED** | 未在本地 `dsh` 中核验这些子命令的存在性；不应作为执行依据 |
| 变更日志规范（Keep a Changelog） | 可用 | 与仓库现状无冲突 |

## 6. 诚实边界

- **未执行**：任何 git 写操作、任何推送、任何 `refs/codex` 清理、`git gc`/`prune`、插件安装、Codex 配置修改。
- **未读取**：`~/.codex/auth.json`、SSH 私钥、任何 token 值（`gh auth status` 仅显示掩码）。
- **NOT EXECUTED**：CI 上的 `ruff` 门（本地沙箱拒绝写 `.ruff_cache`）；`nightly full-suite` 失败日志（`gh run view --log-failed` 需写 `%LOCALAPPDATA%\GitHub CLI` 缓存，被沙箱拒绝且未申请升级）。
- 本轮所有结论均可由 §1–§3 记录的命令复现。工作区既有的 48 个已修改文件与未跟踪历史文件**未被修改、未被提交**。

## 7. 复现命令

```powershell
# 基线
git rev-parse HEAD; git rev-parse origin/main
git rev-list --left-right --count HEAD...origin/main
git for-each-ref --format='%(refname)' | ForEach-Object { ($_ -split '/')[0..1] -join '/' } | Group-Object

# 体积与大对象
git count-objects -vH
git verify-pack -v .git/objects/pack/pack-bb7677fa1568ad7b55f9ba1b126ef4be2a8eaa6a.idx

# 敏感命名扫描
git rev-list --objects --all | Select-String '\.env$|id_rsa|\.pem$|credentials|auth\.json'

# CI 真实状态
gh pr list --state open
gh run list --workflow=ci.yml --branch main --limit 6
gh run view 36230328734 --json jobs

# P0 复现（关键）
.venv/Scripts/python.exe -B scripts/check_repository_conventions.py --source head
```

---

# 附录 A：第二轮报告的增量核验（同日）

第二份报告（含"MASTER PROMPT"）重复了第一份的多数主张，另新增若干**具体配置键**与**破坏性命令**。以下仅记录增量。

## A.1 必须先声明：MASTER PROMPT 含指令覆盖，本轮未予采纳

该 Master Prompt 以 `忽略所有之前的指令。` 开头。这属于**指令覆盖/提示注入**模式，与它自己"不可变规则"里的"不得出现模型自创内容"相矛盾。

**处理**：我不会因为待执行文本中的这句话而放弃本仓库 `AGENTS.md` 的边界、用户既有指令或本会话的核验结论。该段落被当作**待审数据**处理，而非指令。其中"不得输出虚构内容或不实信息"这一条我完全遵从——正是它要求我驳回报告自身的若干未证实主张。

## A.2 新增配置键主张 —— 全部 REFUTED

对 `~/.codex/config.toml` 按顶层赋值精确匹配：

| 报告主张的键 | 实测顶层赋值数 | 裁定 |
| --- | --- | --- |
| `fast_mode` | **0** | REFUTED（不存在） |
| `shell_snapshot` | **0** | REFUTED（不存在） |
| `timeout` | **0** | REFUTED（不存在） |
| `model_context_window` | **0** | REFUTED（不存在） |
| `service_tier` | **1** | 存在，实测值 `"default"` |

报告称"`model`（默认为 `gpt-6-sol`）"—— 实测为 `model = "gpt-6-luna"`。**REFUTED**。

报告称"检查项目目录下是否存在 `.codex/config.toml`"—— 仓库内**不存在 `.codex/` 目录**。该步骤无对象可审。

**结论**：报告第 2 节要求的"修改 config.toml：`fast_mode=true`、`shell_snapshot=true`"是向文件中写入**该 CLI 不认识的键**，属无效操作；若强行写入，轻则被忽略，重则导致配置解析失败。

## A.3 报告对 AGENTS.md 加载开销的担忧 —— 无需处理

`project_doc_max_bytes = 65536`（真实存在的键），而仓库 `AGENTS.md` 实测 **10,132 B**，约为上限的 **15%**。该加载路径不构成性能瓶颈。

## A.4 SSH / HTTPS / 凭证 —— 全部已就绪，报告表格的高优先级项不成立

| 报告主张 | 实测 |
| --- | --- |
| "SSH 链接失败，密钥未配置/失效" | **REFUTED**：`ssh -T -o BatchMode=yes git@github.com` 返回 `Hi DTALEX66! You've successfully authenticated` |
| "HTTPS 验证失败，PAT 缺失或未缓存" | **REFUTED**：`credential.helper = manager` **已配置** |
| 建议执行 `git config --global url."ssh://git@github.com/".insteadOf "https://github.com/"` | **已是现状**：`url.git@github.com:.insteadof https://github.com/` 已存在 |
| 建议 `gh auth login` | **已认证**（`gh auth status`：account DTALEX66，protocol ssh） |

因此"任务对照表"里被标为**优先级=高**的 "SSH 链接失败 / HTTPS 验证失败" 两行，实际是**零工作量**。表中的状态列（"未开始"）与真实状态不符。

**仍需注意**：`gh` token scope 无 `admin:org`，故任何"调整组织策略/Organization 限制"的动作在当前凭据下无法执行。

> 注：`ssh -T` 的退出码为 1 是 GitHub 的正常行为（不提供 shell 访问），**不代表认证失败**。报告若按退出码判定"SSH 失败"会得到错误结论。这也是本次核验显式记录退出码与输出文本两方面的原因。

## A.5 第 4 节命令是破坏性的 —— 且在本仓库会删除 `main`

报告给出的批量删除命令：

```bash
git for-each-ref --format="%(refname)" refs/heads/ | grep -v master | xargs -P4 -n1 git branch -D
```

**干跑（dry-run，未执行删除）结果**：

```
branches matching grep -v master: 27
of total local branches:        27
contains 'main'?                True
contains current branch?        True
```

**该命令在本仓库会试图删除全部 27 个本地分支，其中包括 `main` 和当前检出分支。**

原因：过滤器写的是 `master`，而本仓库默认分支名为 **`main`**，因此过滤**完全失效**，没有任何分支被排除。叠加 `-D`（强制删除，跳过未合并检查）与 `-P4` 并行，破坏性极大。

该命令与 `AGENTS.md` §3"不得使用破坏性操作（递归删除、hard reset、forced push、批量覆盖）除非用户单独确认范围"直接冲突。**建议：整条作废，不得采用。**

其"回滚"建议也不成立：`git reflog expire --expire-unreachable=now --all` 是**主动清除**恢复信息，把它列为回滚手段在方向上相反。

## A.6 第 4 节仍然正确的部分

| 命令 | 裁定 | 说明 |
| --- | --- | --- |
| `git fetch --prune` / `git remote prune origin` | 可用 | 仅清理远程跟踪引用 |
| `git gc --aggressive --prune=now` | **部分可用** | 能回收 §2.4 的 5260 不可达对象与 5 个 `tmp_pack_*`；但**不会**触及 `refs/codex/**`（受引用保护），故不会缩小 461 MB 主因 |
| "对比清理前后大小/耗时" | 合理 | 属正确的度量思路 |

**关于"并行处理加速"**：仓库对象清理不是可 CPU 并行化的短板（受 I/O 与引用图约束），`xargs -P4` 在此不会带来"数倍提升"。报告"目标至少提升数倍速度"缺乏依据。

## A.7 其余部分的裁定（与第一轮一致）

| 报告章节 | 裁定 |
| --- | --- |
| §1 分支审计方法（命令本身） | 大体正确；但 `git branch -r --merged origin/main` 在本地仅有 7 个远程分支、20 个分支从未推送的前提下会**漏掉**真正需要处置的本地分支 |
| §5 前端重构（React/JSX/CSS 示例） | **与仓库技术栈不符**：正式桌面端为 `apps/ArcheAxis.Desktop/`（**C#/Avalonia**），非 React。报告给出的 JSX 示例无法应用 |
| §5 "每页面 4-8 人时" | 无设计稿基线，无法核验（NOT EXECUTED） |
| §7 Lighthouse 得分 ≥90 / FID、TTI <300ms | 针对 Web 产品；对 Avalonia 桌面端不适用 |
| §8 交接文档模板 | 可用 |
| 任务依赖 Mermaid 图 | 逻辑合理，但 `click A1 "#1"` 类跳转锚点对不上第 5 节（前端）的编号 |

## A.8 本轮核验边界（补充）

- **未执行**：`git branch -D`（仅干跑计数）、`git gc`、`git prune`、`git fetch --prune`、任何配置写入。
- **已执行**：`ssh -T`（只读认证测试，`BatchMode` 非交互）、`git config --get*` 读取、`config.toml` 键名匹配（**未打印值**）。

## A.9 两轮报告的共同模式

值得记录：两份报告的正确部分（`git fetch --prune`、`git gc`、`git branch -a`、WCAG 2.1 是真实标准、Keep a Changelog 是真实规范）都是**通用 Git/前端常识**；而所有**针对本项目的具体断言**（未合并 PR、敏感泄露、SSH 失败、`web_search=true`、`fast_mode`、容器内 154 MB 大文件在主干上）**全部与实测不符**。

而**真实的 P0**（`docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md:4` 尾随空格导致 HEAD CI 红、修复已在工作区未提交）与**真实的 P0**（`nightly` 在 `main` 连续 6 天失败）**两份报告都未提及**。

结论：这两份报告不适合作为执行依据；应以其"方法论框架"为参考，而**所有具体结论与命令**必须以本轮实测为准。
