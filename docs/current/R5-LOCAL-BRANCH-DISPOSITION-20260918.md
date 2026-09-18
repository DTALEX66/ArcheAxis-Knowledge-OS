# 本地仅存分支分类报告（只读，2026-09-18）

> 性质：**只读分类 + 一次经 Owner 授权的定向删除**。除第八章"执行记录"里明确列出的
> 1 个分支外，**未删除、未推送、未重命名、未修改**任何本地分支、标签、worktree 或引用。
>
> 与 `docs/current/R5-BRANCH-DISPOSITION-20260918.md` 的区别：那份处理**远端**分支
> （有 PR / 压缩合并证据）；本份处理**从未推送的本地分支**，因此**没有** PR、合并提交或
> 远端证据可用，只能按 blob 内容与主线比对判定。

## 一、结论摘要

- 远端 18 个分支、本地 31 个分支 → **19 个仅本地分支**（远端没有同名分支）。
- 19 个分支共携带 **80 个未推送提交**（最早 2026-07-14，最晚 2026-08-23，全部早于 R5 收敛）。
- 处置：初判 **删除候选 2 / 保留 12 / 上报 5**。
- **详审后修正（重要）**：两个删除候选中，1 个已安全删除；另 1 个
  `codex/worker-quality-0906` **改判为保留**——它的提交确实已全部在 main 里，但它被一个
  **worktree 占用**，而该 worktree 的工作区持有 **56 行 main 没有的内容**（9 个文件）。
  删分支必须先移除 worktree，那会丢掉这些内容。
- **最终处置：已删除 1 / 保留 13 / 上报 5。**
- 那 56 行已抽取归档到 `docs/history/worktree-preserved-diffs/worker-quality-0906-unique-20260918.md`。
- 另有 **2 个 stash**（本地状态，不属分支），本报告只登记、不处置。
- **未执行任何删除。** 删除候选仅 2 个，且都已有不丢失内容的证据。

## 二、方法与口径

对每个分支：

1. 取 `base = git merge-base main <branch>`，列出该分支相对 base 改动的文件；
2. 对每个改动文件做三类 blob 判定：
   - **与主线逐字节相同**（`git rev-parse <branch>:<p>` == `git rev-parse main:<p>`）→ 已吸收；
   - **仅存在于分支**（主线没有该路径）→ 再分两种：
     - 主线曾**刻意删除**该路径（`git log --diff-filter=D main -- <p>` 有记录）→ 属**退役面**，不算缺失工作；
     - 主线**从未有过**该路径 → 属**真实缺失文件**；
   - **两侧都存在但不同** → 再分两种：
     - 主线在 base 之后**改过**该路径（`git rev-list --count base..main -- <p>` > 0）→ 分支版本是**陈旧版本**；
     - 主线在 base 之后**没碰过** → 可能存在**真实未吸收差异**。
3. 以"是否存在真实缺失文件 / 真实未吸收差异"决定处置：
   - 无 → 语义已吸收（删除候选）；
   - 只有陈旧差异、没有缺失文件 → 主线已演进（保留，供人工降级）；
   - 有缺失文件或冻结差异 → 上报。

**为什么不用 patch-id（`git cherry`）定论**：压缩合并会让补丁等价失效——这正是远端分类
（`R5-BRANCH-DISPOSITION-20260918.md`）里 15 个分支"显示已分叉却其实已吸收"的原因。
本报告因此以 blob 内容为主判据。

## 三、汇总表

| 分支 | tip | 日期 | 未进 main 提交 | 改动文件 | 相同 | 退役 | 陈旧 | 冻结 | 缺失 | 判定 / 处置 |
|---|---|---|---|---|---|---|---|---|---|---|
| `codex/worker-quality-0906` | `4ca46eaf` | 2026-09-06 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 提交已全在 main / **详审改判：保留**（worktree 持有 56 行独有内容） |
| `fix/ci-playwright-collection` | `0a12fc11` | 2026-07-28 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 语义已吸收 / **已删除（2026-09-18）** |
| `audit/unreleased-real-version` | `40922904` | 2026-08-09 | 2 | 5 | 1 | 0 | 4 | 0 | 0 | 主线已演进 / 保留 |
| `axw/execution-h0` | `39df7d26` | 2026-08-09 | 8 | 15 | 0 | 0 | 15 | 0 | 0 | 主线已演进 / 保留 |
| `axw/execution-h1` | `1c688c71` | 2026-08-10 | 16 | 26 | 16 | 0 | 10 | 0 | 0 | 主线已演进 / 保留 |
| `codex/recovery-shell-frontend` | `e4239ebd` | 2026-08-23 | 9 | 19 | 3 | 1 | 15 | 0 | 0 | 主线已演进 / 保留 |
| `feat/absorption-adopt-now` | `081cf20a` | 2026-08-12 | 7 | 26 | 7 | 0 | 19 | 0 | 0 | 主线已演进 / 保留 |
| `feat/absorption-roadmap-r0` | `42d13c0b` | 2026-07-28 | 7 | 56 | 19 | 0 | 36 | 0 | 0 | 主线已演进 / 保留 |
| `feat/axw022a-pdf-http-endpoint` | `17ca9628` | 2026-08-11 | 4 | 10 | 0 | 5 | 5 | 0 | 0 | 主线已演进 / 保留 |
| `feat/axw022b-evidence-annotation` | `3edacbcb` | 2026-08-11 | 2 | 4 | 1 | 2 | 1 | 0 | 0 | 主线已演进 / 保留 |
| `feat/h2-bakeoff` | `376fb800` | 2026-08-12 | 3 | 4 | 0 | 0 | 4 | 0 | 0 | 主线已演进 / 保留 |
| `feat/h2-pipeline-integration` | `e1df9279` | 2026-08-12 | 9 | 78 | 28 | 2 | 48 | 0 | 0 | 主线已演进 / 保留 |
| `feat/ms00-c-release-identity` | `01e794d1` | 2026-08-07 | 1 | 6 | 0 | 0 | 6 | 0 | 0 | 主线已演进 / 保留 |
| `work/tp12-facades` | `8d5ba104` | 2026-07-14 | 1 | 37 | 17 | 3 | 16 | 0 | 0 | 主线已演进 / 保留 |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | 2026-07-20 | 1 | 13 | 0 | 1 | 8 | 0 | 4 | 有效缺失工作 / **上报** |
| `feat/archeaxis-desktop-a1-violet-core` | `376281c6` | 2026-07-28 | 5 | 17 | 0 | 4 | 11 | 0 | 2 | 有效缺失工作 / **上报** |
| `feat/p1-compat-kernel-hardening` | `a4f2de19` | 2026-08-10 | 11 | 14 | 1 | 0 | 10 | 0 | 3 | 有效缺失工作 / **上报** |
| `feat/portable-data-root` | `4e1a3ed8` | 2026-08-05 | 1 | 18 | 3 | 3 | 9 | 0 | 3 | 有效缺失工作 / **上报** |
| `fix/desktop-close-request-destroy` | `801edea8` | 2026-08-06 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 有效缺失工作 / **上报** |

## 四、逐类明细

### 4.1 删除候选（初判 2 → 详审后 1 个执行删除）

| 分支 | 详审结论 | 处置 |
|---|---|---|
| `fix/ci-playwright-collection`（`0a12fc11`） | 唯一改动是在 `requirements-ci.txt` 加一行 `playwright>=1.61,<1.62`；该文件已被主线删除，而其**意图已被主线覆盖**（`pyproject.toml` 的浏览器组与 ci 组都含 playwright，`ci.yml` 会安装 Chromium），主线无任何活引用 | **已删除** |
| `codex/worker-quality-0906`（`4ca46eaf`） | 提交层面：0 个独有提交、tip 是 main 祖先。**但详审发现它被 `.project-local/worktrees/worker-quality-0906` 占用，且该 worktree 工作区有 6 个已改文件（+244/−68）与 9 个未跟踪路径**；逐文件比对后，其中 **9 个文件含 56 行 main 没有的内容**，另有 3 个文件是主线严格领先的旧版 | **改判保留**（删除需先移除 worktree，会丢内容） |

### 4.2 保留（12）—— 内容已被主线越过，但未证明"无独立价值"

这些分支改动过的文件在主线中**全部**在分支点之后被继续修改过（陈旧版本），且**没有任何
文件缺失于主线**。因此按最保守口径列为保留，供人工复核后再降级：

`audit/unreleased-real-version`、`axw/execution-h0`、`axw/execution-h1`、
`codex/recovery-shell-frontend`、`feat/absorption-adopt-now`、`feat/absorption-roadmap-r0`、
`feat/axw022a-pdf-http-endpoint`、`feat/axw022b-evidence-annotation`、`feat/h2-bakeoff`、
`feat/h2-pipeline-integration`、`feat/ms00-c-release-identity`、`work/tp12-facades`

> 注：其中 `codex/recovery-shell-frontend` 与远端已吸收的 `codex/recovery-shell-closed-loop`
> 主题相邻（恢复壳），但本分支**从未推送**，因此不能用 PR#142 的压缩合并证据吸收它；
> 其正文本体在主线已存在（`frontend/src/components/RecoveryShell.tsx` 等），差异属陈旧版本。

### 4.3 上报（5）—— 存在**主线从未有过**的文件

| 分支 | 主线从未有过的文件 |
|---|---|
| `agent/phase5-research-knowledge-governance` | `app/adapters/research_knowledge.py`、`shared/knowledge_migration.py`、`tests/test_research_knowledge_candidate_contract.py`、`workspace/intake/011_phase5_p01_governed_candidate_checkpoint.md` |
| `feat/archeaxis-desktop-a1-violet-core` | `requirements-ci-adapters.txt`、`workspace/intake/2026-07-28-archeaxis-pack-analysis.md` |
| `feat/p1-compat-kernel-hardening` | `tests/test_format_capabilities.py`、`workspace/intake/2026-08-09-multiformat-capability-boundary.md`、`workspace/intake/2026-08-09-online-learning-corpus.md` |
| `feat/portable-data-root` | `scripts/project_env.bat`、`scripts/project_env.ps1`、`scripts/project_env.sh` |
| `fix/desktop-close-request-destroy` | `docs/workflow/HANDOFF_DESKTOP_CLOSE_LIFECYCLE_2026-08-06.md` |

**这 5 个分支不得由执行器删除。** "主线从未有过"只证明它没被吸收，不证明它现在仍需要；
是否吸收（或明确判定废弃）属 Owner 决策，可能需转 CODEX/HERMES 做语义吸收评估。

## 五、局限（必须与结论一并阅读）

1. **无远端证据**：这些分支从未推送，没有 PR、没有压缩合并提交可比对，因此吸收判定只能基于 blob 内容。
2. **"主线已演进" ≠ "内容已被吸收"**：只说明主线在该路径上继续前进过（分支版本陈旧）。真正的语义等价仍需人工。
3. **"主线从未有过" ≠ "需要"**：只说明未吸收；是否需要、是否已被别的实现取代，需 Owner 判断。
4. 本报告**不覆盖** `stash`：`stash@{0}`（2026-09-18，注释称内容已进 main，6 文件 +1280/−1193）、
   `stash@{1}`（2026-08-05，`feat/portable-data-root` 上的恢复点，6 文件 +48/−24）。丢弃 stash 是
   破坏性动作，需单独授权。
5. 判定脚本未纳入"分支是否含二进制/大文件"的额外成本考量。

## 六、删除时的安全路径（更新：必须先用 `git worktree list` 检查占用）

1. **前置检查（本轮血的教训）**：`git worktree list`。被 worktree 检出的分支**不能**直接
   `git branch -D`（会报 `cannot delete branch ... used by worktree`），而移除 worktree 可能
   丢掉其中的未提交内容——必须先逐文件确认工作区内容是否已在主线。
2. 先做本地备份，再删：`git bundle create <file> ^main <branches>`，并用 `git bundle verify <file>` 校验；
3. 只删已确认无独有内容的分支：`git branch -D <branch>`；
4. 删除后核对：`git for-each-ref refs/heads | wc -l`、`git log --branches --not --remotes --oneline | wc -l`；
5. 删除仅影响本地引用，**不推送、不改写远端**；已删除对象的 SHA 仍留在 reflog 中一段时间，可用 `git branch <name> <sha>` 复原。

## 七、执行记录（Owner 授权后，2026-09-18）

| 步骤 | 内容 |
|---|---|
| 授权 | Owner 指示"详细审计，有用的留下并入，没用的去掉" |
| 审计 A | `codex/worker-quality-0906`：主线领先 720 个提交、该分支 0 个独有提交；但被 worktree 占用，工作区 6 个已改文件（+244/−68）+ 9 个未跟踪路径 |
| 审计 A 细判 | 逐文件以 blob 比对工作区内容 vs 主线：4 个文件与主线相同、0 个路径为"主线完全没有"、**9 个文件含 56 行主线没有的内容**、3 个为旧版；抽取归档到 `docs/history/worktree-preserved-diffs/worker-quality-0906-unique-20260918.md` |
| 审计 B | `fix/ci-playwright-collection`：1 行依赖新增，意图已被主线覆盖 → 判定无用 |
| 备份 | `git bundle create .project-local/archive-local-branch-candidates-20260918.bundle ^main codex/worker-quality-0906 fix/ci-playwright-collection`，`git bundle verify` 返回 okay（0.6 KB） |
| 删除 | `git branch -D fix/ci-playwright-collection` → 成功（`was 0a12fc11`）；`codex/worker-quality-0906` **未删除**（worktree 占用 + 持有独有内容） |
| 计数变化 | 本地分支 31 → **30**；未推送提交 80 → 80（不变：被删提交仍被其它本地分支引用）；main HEAD 未变；远端分支 18 未变 |
| 未执行 | 未移除任何 worktree、未推送、未改远端、未丢弃 stash |

### 8.1 详审附带发现的其他本地状态（只读报告，未处置）

| 位置 | 状态 | 归口 |
|---|---|---|
| worktree `worker-quality-0906` | 6 改 + 9 未跟踪路径；56 行独有内容已归档 | 保留；若要并入主线需人工做语义合并（主线在这些文件上已领先 300+ 行，**不能整文件覆盖**） |
| worktree `v3-era`（`968c4795`，detached） | 2 个已暂存修改：`crates/archeaxis-archive/src/lib.rs`、`crates/archeaxis-store-sqlite/src/lib.rs`；1 个未跟踪新文件 `crates/archeaxis-archive/tests/gen_v3_fixture.rs`（主线无此路径） | **上报**：`archeaxis-archive` 与 Rust v3 schema 属 §15/§16 明令 DSH 不得处理的区域 |
| worktree `verify-0c9c`（`cdc07cd0`，detached） | 干净 | 无动作 |

### 8.2 删除时的安全路径（修订）

删除前必须**先** `git worktree list`；被检出的分支不能直接删；审计脚本在
`.project-local/analyse-local-branches-v2.py`（只读）与 `.project-local/audit-worktree-wip.py`。

## 八、复核命令

```powershell
# 仅本地分支清单
git for-each-ref --format='%(refname:short)' refs/heads | Where-Object { (git ls-remote --heads origin) -notmatch $_ }

# 某分支相对主线的改动文件与两侧 blob 是否相同
$b = 'fix/ci-playwright-collection'
$base = git merge-base main $b
git diff --name-status $base $b
git rev-parse "${b}:requirements-ci.txt"; git rev-parse 'main:requirements-ci.txt'

# 主线是否刻意删除过某路径
git log --format=%h -1 --diff-filter=D main -- requirements-ci.txt
```
