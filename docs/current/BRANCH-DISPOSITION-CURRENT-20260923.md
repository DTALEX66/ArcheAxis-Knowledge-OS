# Branch Disposition — Current Readonly Audit 2026-09-23

Evidence: local Git refs and `origin/main` local ref at
`e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`. Live remote listing is
`UNVERIFIED` because SSH `known_hosts` access was denied. No branch was merged,
deleted, rebased or force-pushed.

`ahead/behind` is relative to `origin/main`; `merged=yes` means the branch tip
is an ancestor of `origin/main`, not that the branch is safe to delete.

| Local branch | tip | ahead | behind | merged | disposition |
| --- | ---: | ---: | ---: | :---: | --- |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | 1 | 1558 | no | historical; inspect unique commit before owner decision |
| `audit/r5-independent-audit-20260919` | `6daca18e` | 1 | 196 | no | independent audit evidence; preserve |
| `audit/unreleased-real-version` | `40922904` | 2 | 1372 | no | historical release evidence; preserve |
| `axw/execution-h0` | `39df7d26` | 8 | 1372 | no | historical AXW work; no age-only deletion |
| `axw/execution-h1` | `1c688c71` | 16 | 1371 | no | historical AXW work; no age-only deletion |
| `chore/naming-repo-refs` | `a9aa0665` | 3 | 1310 | no | naming evidence; preserve until reference audit |
| `codex/aaos-p3-ui-convergence-20260922` | `974322a6` | 13 | 0 | no | active frontend delivery candidate |
| `codex/ci-release-optimization` | `74ca5536` | 7 | 1063 | no | historical release candidate; inspect only |
| `codex/execution-reliability-standards` | `affc0abc` | 2 | 1370 | no | governance evidence; preserve |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | 149 | 1372 | no | historical roadmap; preserve |
| `codex/post-release-v0.6.9` | `e50aad0d` | 2 | 1059 | no | historical release evidence |
| `codex/recovery-shell-closed-loop` | `14afe937` | 13 | 1061 | no | historical desktop evidence |
| `codex/recovery-shell-frontend` | `e4239ebd` | 9 | 1061 | no | local historical frontend; no remote tracking |
| `codex/release-v0.6.9` | `c64278df` | 2 | 1060 | no | historical release evidence |
| `codex/v0.6.8-release-closure` | `42e7c0cc` | 2 | 1062 | no | historical release evidence |
| `codex/worker-quality-0906` | `4ca46eaf` | 0 | 921 | yes | ancestor but registered worktree; owner/worktree audit first |
| `docs/verification-summary-2026-08-09` | `8cc9c690` | 1 | 1372 | no | historical verification evidence |
| `feat/absorption-adopt-now` | `081cf20a` | 7 | 1362 | no | historical absorption work |
| `feat/absorption-roadmap-r0` | `42d13c0b` | 7 | 1498 | no | historical roadmap |
| `feat/archeaxis-desktop-a1-violet-core` | `376281c6` | 5 | 1497 | no | superseded UI direction; preserve evidence |
| `feat/axw022a-pdf-http-endpoint` | `17ca9628` | 4 | 1369 | no | historical AXW work |
| `feat/axw022b-evidence-annotation` | `3edacbcb` | 2 | 1368 | no | historical evidence UI work |
| `feat/h2-bakeoff` | `376fb800` | 3 | 1359 | no | historical H2 work |
| `feat/h2-pipeline-integration` | `e1df9279` | 9 | 1303 | no | historical H2 work |
| `feat/ms00-c-release-identity` | `01e794d1` | 1 | 1443 | no | historical release identity |
| `feat/naming-step3` | `bc4a234f` | 1 | 1304 | no | naming evidence |
| `feat/p1-compat-kernel-hardening` | `a4f2de19` | 11 | 1399 | no | historical compatibility work |
| `feat/portable-data-root` | `4e1a3ed8` | 1 | 1460 | no | historical portable work |
| `fix/desktop-close-request-destroy` | `801edea8` | 1 | 1451 | no | historical desktop lifecycle |
| `main` | `e3875db0` | 0 | 0 | yes | protected baseline |
| `release/v0.4.0-contract` | `75cb72ef` | 4 | 1491 | no | release evidence; preserve |
| `work/tp12-facades` | `8d5ba104` | 1 | 1627 | no | historical facade work |

## Rules for any later merge/delete action

1. Re-read this table from live refs immediately before acting.
2. For each candidate, inspect unique commits and paths against current R6/M0
   authority; do not use ahead/behind alone.
3. Check registered worktrees with `git worktree list --porcelain` before
   deleting any branch or `.project-local/worktrees` directory.
4. Preserve or bundle history only after an exact path/hash manifest exists.
5. Merge, remote delete, bundle creation and worktree removal each require a
   separate owner-approved operation; this audit is read-only.

## 2026-10-08 分支与工作树处置（本轮实测）

边界：本节点只登记。未删除/移动/重命名任何目录或工作树，未 `git worktree remove`、未删分支、未 `prune`（见 D7）、
未 rebase/reset/stash、未 push、未建 tag、未动远端 ref、未碰主检出与其它工作树的任何文件。唯一写入是本节。

测量口径：containment 一律 `git merge-base --is-ancestor`（`git cherry` 的 +/- 只当双向假设，不作结论）；
计数一律 `git rev-list --left-right --count`；脏度一律 `git --no-optional-locks status --porcelain=v1`
（`--no-optional-locks` 保证不改写兄弟工作树的 index）；表格由脚本从下表时刻的 live refs 直接生成，无手工转录。
快照时刻 `2026-10-08 14:16:37`；表内 SHA 缩写 10 位。本轮未 fetch，`origin/*` 是本仓库最后一次 fetch 的本地快照，远端实况 NOT_VERIFIED。

- PIN（本轮起点 = 我的写入分支起点）：`fb63001542ecf9dfa755d82e4de445d34a42c650`
- 集成线 `codex/aaos-gov-ui-20261008` 写入时是 `b55a1238f398a47b782c8a6f8df471352814f1e9`；PIN 到它的链：`fb63001542` -> `bf357f76` -> `24f77292` -> `74504d46` -> `d73c50d7` -> `b55a1238`。PIN 是其祖先：yes —— 本节全部 containment 结论对更新后的 tip 同样成立。
- `refs/remotes/origin/main` 本地快照：`4b9828c4058901c0b1fd2c75c528238c55e0ec89`；是 PIN 的祖先：yes（PIN 领先 52）。
- 我的分支：`codex/aaos-branch-disposition-20261008` @ `fb63001542ecf9dfa755d82e4de445d34a42c650`，工作树 `<WT>/a-gates-20261008`。
- 两次快照之间的 refs/脏度漂移：`codex/aaos-gov-ui-20261008` tip：24f7729211 -> b55a1238f3；`<WT>/b-surfaces-20261008` dirty：3 -> 0；`<WT>/b-surfaces-20261008` HEAD：fb63001542 -> d73c50d7c0；`<WT>/d-docs-20261008` dirty：0 -> 2；`<WT>/gov-ui-20261008` dirty：0 -> 1；`<WT>/gov-ui-20261008` HEAD：24f7729211 -> b55a1238f3；`codex/aaos-gov-ui-20261008`：24f7729211 -> b55a1238f3；`codex/aaos-ui-templates-20261008`：fb63001542 -> d73c50d7c0；磁盘 `<WT>/*` 目录数：44 -> 38（volume agent 正在回收；已消失 `aaos-p02-readback-20261007`, `aaos-p03-folder-batch-20261007`, `pycache-172`, `pycache-f06ui`, `pycache-f09`, `pycache-full`；新增 无）
- 规模实测：本地分支 44、注册工作树 38（含主检出）、磁盘 `<WT>/*` 目录 38（其中 3 个既无注册也无 `.git`）、本地 tag 32。

### D0 交办时“已知状态”的逐条复核

- 主检出：`<MAIN>` @ `1a981a4482`，是 `origin/main` 的祖先（is-ancestor=yes），落后 750；工作树未跟踪内容见 D6。
- `a8d2e0bb` = `a8d2e0bb2e`（`codex/aaos-ui02-nav3-20261008`）：实测 `origin/main` + 22，⊂PIN=yes，⊂live=yes —— 本轮基线已并入。
- `15f79cf7` = `15f79cf7fc`（`codex/oss-reuse-templates-20261008`）：独立线（`origin/main` + 1），现已并入 PIN：⊂PIN=yes。
- 集成分支 `codex/aaos-gov-ui-20261008` @ `b55a1238f3`：PIN 是其祖先（yes），PIN 之后新增 5 个提交（链见上）。
- Green 侧注册工作树 `minimax-aaos-cosmic-ui-20261001`：仍注册于本仓库、路径存在、dirty=0；它不是“未注册遗留”，但落在本仓库之外的部署目录里（见 D2）。
- owner 报告的独立克隆实测位于 `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline`（在 `.ui-task-tree` 下，不在 Green 根目录）：自带 `.git` 目录、未在本仓库注册；本轮只核实存在与形态，5.78 GB 的体量与 `CodexSandboxOnline` 属主本轮未重测（NOT_VERIFIED），未进入、未执行任何命令。

### D1 分支处置表（44 个本地分支）

分类计数：DIRTY-UNCOMMITTED-PROTECTED=7、MERGED-CONTAINED=33、UNIQUE-COMMITS-LOCAL-ONLY=2、UNIQUE-COMMITS-PUSHED=2。DETACHED / UNREGISTERED-LEFTOVER / FOREIGN-OWNERSHIP 只适用于工作树，见 D2；分类不互相折叠。

判定顺序：分支的注册工作树里有未提交内容 -> `DIRTY-UNCOMMITTED-PROTECTED`（优先，不因其 tip 已并入就当可清理）；
否则有 PIN 之外的提交 -> 按“该 tip 是否被某个 `refs/remotes/*` 包含”分 `UNIQUE-COMMITS-PUSHED` / `UNIQUE-COMMITS-LOCAL-ONLY`；
否则 tip 是 PIN 的祖先（或等于 PIN）-> `MERGED-CONTAINED`。
`⊂PIN`/`⊂main` = is-ancestor；`⊂live` = tip 是否也在写入时的集成线 tip（`b55a1238f3`）里——PIN 在本轮被反复推进，`⊂PIN=n` 但 `⊂live=Y` 的分支其实已被吸收，不需要合并决策，只是不满足本节以 PIN 为准的 retire 入选条件；`a/b vs main`、`a/b vs PIN` = ahead/behind；`remote` = 同名 `origin/<name>` 的缩写 SHA（`=` 与本地一致，`!=` 不一致并附其是否已并入 PIN，`-` 无该远端 ref）；`tag` = 是否有 `refs/tags/*` 钉住同一 tip（钉住则分支删掉后提交仍可达）。

| branch | tip | ⊂PIN | ⊂live | ⊂main | a/b vs main | a/b vs PIN | remote | tag | 唯一提交 | 工作树 | dirty | 类 |
| --- | --- | :-: | :-: | :-: | ---: | ---: | --- | :-: | ---: | --- | ---: | --- |
| `codex/Audit` | `1a981a4482` | Y | Y | Y | 0/750 | 0/802 | - | Y | 0 | <MAIN> | 22 | DIRTY-UNCOMMITTED-PROTECTED |
| `codex/aaos-branch-disposition-20261008` | `fb63001542` | Y | Y | n | 52/0 | 0/0 | - | n | 0 | a-gates-20261008 | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-coredemo-20261008` | `c94c725900` | Y | Y | n | 33/0 | 0/19 | - | n | 0 | g-coredemo-20261008 | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-docs-20261008` | `ec9f3b97b3` | Y | Y | n | 24/0 | 0/28 | - | n | 0 | - | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-honesty-20261008` | `15f0e6de93` | Y | Y | n | 33/0 | 0/19 | - | n | 0 | e-honesty-20261008 | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-oss-20261008` | `ea1e170024` | Y | Y | n | 35/0 | 0/17 | - | n | 0 | f-oss-20261008 | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-resindex-20261008` | `9f3fd470a5` | Y | Y | n | 23/0 | 0/29 | - | n | 0 | c-resources-20261008 | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-ui-20261008` | `b55a1238f3` | n | Y | n | 57/0 | 5/0 | - | n | 5 | gov-ui-20261008 | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `codex/aaos-gov-uia11y-20261008` | `da952cd5aa` | Y | Y | n | 23/0 | 0/29 | - | n | 0 | - | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-uigates-20261008` | `9b306242ed` | Y | Y | n | 23/0 | 0/29 | - | n | 0 | - | 0 | MERGED-CONTAINED |
| `codex/aaos-gov-volume-20261008` | `fb63001542` | Y | Y | n | 52/0 | 0/0 | - | n | 0 | d-docs-20261008 | 2 | DIRTY-UNCOMMITTED-PROTECTED |
| `codex/aaos-longpath-app-20261007` | `1c5d42b262` | Y | Y | Y | 0/86 | 0/138 | `1c5d42b262`= | n | 0 | aaos-longpath-app-20261007 | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `codex/aaos-member-chain-20261007` | `0e04f494df` | Y | Y | Y | 0/76 | 0/128 | `0e04f494df`= | n | 0 | aaos-member-chain-20261007 | 0 | MERGED-CONTAINED |
| `codex/aaos-p04-doc-loop-20261007` | `72a0bbc24a` | n | n | n | 6/0 | 6/52 | `72a0bbc24a`= | n | 6 | aaos-p04-doc-loop-20261007 | 0 | UNIQUE-COMMITS-PUSHED |
| `codex/aaos-p3-ui-convergence-20260922` | `43c2cafa1b` | Y | Y | Y | 0/813 | 0/865 | - | n | 0 | - | 0 | MERGED-CONTAINED |
| `codex/aaos-ui-core-integration-20261007` | `5afb4f285b` | Y | Y | Y | 0/95 | 0/147 | `5afb4f285b`= | n | 0 | - | 0 | MERGED-CONTAINED |
| `codex/aaos-ui-newui-20261007` | `81eb27bb0f` | Y | Y | Y | 0/268 | 0/320 | - | n | 0 | aaos-ui-newui-20261007 | 5 | DIRTY-UNCOMMITTED-PROTECTED |
| `codex/aaos-ui-phase2-20261001` | `1a981a4482` | Y | Y | Y | 0/750 | 0/802 | - | Y | 0 | - | 0 | MERGED-CONTAINED |
| `codex/aaos-ui-templates-20261008` | `d73c50d7c0` | n | Y | n | 53/0 | 1/0 | - | n | 1 | b-surfaces-20261008 | 0 | UNIQUE-COMMITS-LOCAL-ONLY |
| `codex/aaos-ui-u05-20261007` | `88cc2c47d0` | Y | Y | Y | 0/92 | 0/144 | `88cc2c47d0`= | n | 0 | aaos-ui-core-integration-20261007 | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `codex/aaos-ui02-nav3-20261008` | `a8d2e0bb2e` | Y | Y | n | 22/0 | 0/30 | - | n | 0 | ui02-nav3-20261008 | 0 | MERGED-CONTAINED |
| `codex/asr-pipe-utf8-20261007` | `7d27a1cabd` | Y | Y | Y | 0/10 | 0/62 | `7d27a1cabd`= | Y | 0 | asr-pipe-utf8-20261007 | 0 | MERGED-CONTAINED |
| `codex/canonical-browser-host-20261007` | `fa3cc7fb75` | Y | Y | Y | 0/5 | 0/57 | `fa3cc7fb75`= | Y | 0 | canonical-browser-host-20261007 | 0 | MERGED-CONTAINED |
| `codex/cleanup-readback-20261007` | `6396bfbbce` | Y | Y | Y | 0/38 | 0/90 | `6396bfbbce`= | n | 0 | cleanup-readback-20261007 | 0 | MERGED-CONTAINED |
| `codex/dsh-aaos-real-multiformat-loop-20261001` | `45a7d17c5d` | Y | Y | Y | 0/129 | 0/181 | `45a7d17c5d`= | n | 0 | dsh-backend-loop-20261001 | 0 | MERGED-CONTAINED |
| `codex/f01-csv-cells-20261007` | `3419419045` | Y | Y | Y | 0/20 | 0/72 | `ea4f554b43`!=（并 PIN:yes） | n | 0 | f01-csv-cells-20261007 | 0 | MERGED-CONTAINED |
| `codex/f04-detect-20261007` | `86bae0f32d` | Y | Y | Y | 0/56 | 0/108 | `86bae0f32d`= | n | 0 | f04-detect-20261007 | 0 | MERGED-CONTAINED |
| `codex/f04-detect-ui-20261007` | `34ec2bd0cb` | Y | Y | Y | 0/63 | 0/115 | `34ec2bd0cb`= | n | 0 | f04-detect-ui-20261007 | 0 | MERGED-CONTAINED |
| `codex/f06-pages-ui-20261007` | `86c0170e2d` | Y | Y | Y | 0/30 | 0/82 | `86c0170e2d`= | n | 0 | f06-pages-ui-20261007 | 0 | MERGED-CONTAINED |
| `codex/f09-cell-anchor-20261007` | `96cbff5ce4` | Y | Y | Y | 0/41 | 0/93 | `96cbff5ce4`= | n | 0 | f09-cell-anchor-20261007 | 0 | MERGED-CONTAINED |
| `codex/f10-diarize-20261007` | `0830cc5e95` | Y | Y | Y | 0/73 | 0/125 | `0830cc5e95`= | n | 0 | f10-diarize-20261007 | 0 | MERGED-CONTAINED |
| `codex/f10-supply-20261007` | `995a2cdf5b` | Y | Y | Y | 0/13 | 0/65 | `995a2cdf5b`= | Y | 0 | f10-supply-20261007 | 0 | MERGED-CONTAINED |
| `codex/f15-folder-ingest-20261007` | `3742603faf` | Y | Y | Y | 0/6 | 0/58 | `3742603faf`= | Y | 0 | f15-folder-ingest-20261007 | 0 | MERGED-CONTAINED |
| `codex/f15-status-row-20261007` | `4b9828c405` | Y | Y | Y | 0/0 | 0/52 | `815c6f70b6`!=（并 PIN:yes） | n | 0 | f15-status-row-20261007 | 0 | MERGED-CONTAINED |
| `codex/github-delivery-docs-20260929` | `aa8046996c` | n | n | n | 1/787 | 1/839 | - | Y | 1 | - | 0 | UNIQUE-COMMITS-LOCAL-ONLY |
| `codex/index-newline-20261007` | `cdb908e53a` | Y | Y | Y | 0/77 | 0/129 | `cdb908e53a`= | n | 0 | index-newline-20261007 | 0 | MERGED-CONTAINED |
| `codex/longpath-importer-20261007` | `4f547f5f2b` | Y | Y | Y | 0/61 | 0/113 | `4f547f5f2b`= | n | 0 | longpath-importer-20261007 | 0 | MERGED-CONTAINED |
| `codex/longpath-intake-20261007` | `064603cdaa` | Y | Y | Y | 0/48 | 0/100 | `064603cdaa`= | n | 0 | longpath-intake-20261007 | 0 | MERGED-CONTAINED |
| `codex/minimax-aaos-cosmic-ui-20261001` | `627e74ffcc` | n | n | n | 2/750 | 2/802 | `627e74ffcc`= | n | 2 | minimax-aaos-cosmic-ui-20261001 | 0 | UNIQUE-COMMITS-PUSHED |
| `codex/oss-reuse-templates-20261008` | `15f79cf7fc` | Y | Y | n | 1/0 | 0/51 | - | n | 0 | oss-reuse-20261008 | 0 | MERGED-CONTAINED |
| `codex/spillover-readback-20261007` | `759bb5ee61` | Y | Y | Y | 0/21 | 0/73 | `759bb5ee61`= | n | 0 | spillover-readback-20261007 | 0 | MERGED-CONTAINED |
| `codex/supply-bind-20261007` | `563471fee4` | Y | Y | Y | 0/88 | 0/140 | `563471fee4`= | n | 0 | supply-bind-20261007 | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `main` | `59498723a8` | Y | Y | Y | 0/768 | 0/820 | `4b9828c405`!=（并 PIN:yes） | n | 0 | - | 0 | MERGED-CONTAINED |
| `preserve-p3-ui-convergence` | `43c2cafa1b` | Y | Y | Y | 0/813 | 0/865 | - | n | 0 | - | 0 | MERGED-CONTAINED |

配置了 upstream 但本地已无对应 `refs/remotes/*`（推送状态因此 NOT_VERIFIED，不能当作已推送）：`codex/Audit`、`codex/aaos-p3-ui-convergence-20260922`、`codex/aaos-ui-phase2-20261001`、`codex/github-delivery-docs-20260929`。

### D2 工作树登记表（注册 38 + 磁盘未注册 3 + Green 侧 4）

`git worktree list --porcelain` 与 `.git/worktrees/*` 双向核对：37 条 admin 注册全部出现在 list 中、路径全部存在、无 `locked`、无 `prunable`。注册 id 可与目录名不同：`<WT>/supply-bind-20261007` 的注册 id 是 `wb`。

reparse（Windows 联接点/junction）逐个实测：注册工作树全部 False，因此 retire 配方里的 `cmd /c rmdir` 解联接步骤本轮不需要。

路径简写：`<MAIN>` = `D:/All projects/ArcheAxis-Knowledge-OS`（主检出），`<WT>` = `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees`。

| worktree path | HEAD | branch | dirty | 类 |
| --- | --- | --- | ---: | --- |
| `<MAIN>` | `1a981a4482` | `codex/Audit` | 22 | DIRTY-UNCOMMITTED-PROTECTED |
| `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/wi` | `fa226ffb12` | DETACHED | 0 | DETACHED |
| `<WT>/a-gates-20261008` | `fb63001542` | `codex/aaos-branch-disposition-20261008` | 0 | REGISTERED |
| `<WT>/aaos-longpath-app-20261007` | `1c5d42b262` | `codex/aaos-longpath-app-20261007` | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `<WT>/aaos-member-chain-20261007` | `0e04f494df` | `codex/aaos-member-chain-20261007` | 0 | REGISTERED |
| `<WT>/aaos-p04-doc-loop-20261007` | `72a0bbc24a` | `codex/aaos-p04-doc-loop-20261007` | 0 | REGISTERED |
| `<WT>/aaos-ui-core-integration-20261007` | `88cc2c47d0` | `codex/aaos-ui-u05-20261007` | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `<WT>/aaos-ui-newui-20261007` | `81eb27bb0f` | `codex/aaos-ui-newui-20261007` | 5 | DIRTY-UNCOMMITTED-PROTECTED |
| `<WT>/asr-pipe-utf8-20261007` | `7d27a1cabd` | `codex/asr-pipe-utf8-20261007` | 0 | REGISTERED |
| `<WT>/b-surfaces-20261008` | `d73c50d7c0` | `codex/aaos-ui-templates-20261008` | 0 | REGISTERED |
| `<WT>/c-resources-20261008` | `9f3fd470a5` | `codex/aaos-gov-resindex-20261008` | 0 | REGISTERED |
| `<WT>/canonical-browser-host-20261007` | `fa3cc7fb75` | `codex/canonical-browser-host-20261007` | 0 | REGISTERED |
| `<WT>/cleanup-readback-20261007` | `6396bfbbce` | `codex/cleanup-readback-20261007` | 0 | REGISTERED |
| `<WT>/d-docs-20261008` | `fb63001542` | `codex/aaos-gov-volume-20261008` | 2 | DIRTY-UNCOMMITTED-PROTECTED |
| `<WT>/dsh-backend-loop-20261001` | `45a7d17c5d` | `codex/dsh-aaos-real-multiformat-loop-20261001` | 0 | REGISTERED |
| `<WT>/e-honesty-20261008` | `15f0e6de93` | `codex/aaos-gov-honesty-20261008` | 0 | REGISTERED |
| `<WT>/f-oss-20261008` | `ea1e170024` | `codex/aaos-gov-oss-20261008` | 0 | REGISTERED |
| `<WT>/f01-csv-cells-20261007` | `3419419045` | `codex/f01-csv-cells-20261007` | 0 | REGISTERED |
| `<WT>/f04-detect-20261007` | `86bae0f32d` | `codex/f04-detect-20261007` | 0 | REGISTERED |
| `<WT>/f04-detect-ui-20261007` | `34ec2bd0cb` | `codex/f04-detect-ui-20261007` | 0 | REGISTERED |
| `<WT>/f06-pages-ui-20261007` | `86c0170e2d` | `codex/f06-pages-ui-20261007` | 0 | REGISTERED |
| `<WT>/f09-cell-anchor-20261007` | `96cbff5ce4` | `codex/f09-cell-anchor-20261007` | 0 | REGISTERED |
| `<WT>/f10-diarize-20261007` | `0830cc5e95` | `codex/f10-diarize-20261007` | 0 | REGISTERED |
| `<WT>/f10-supply-20261007` | `995a2cdf5b` | `codex/f10-supply-20261007` | 0 | REGISTERED |
| `<WT>/f15-folder-ingest-20261007` | `3742603faf` | `codex/f15-folder-ingest-20261007` | 0 | REGISTERED |
| `<WT>/f15-status-row-20261007` | `4b9828c405` | `codex/f15-status-row-20261007` | 0 | REGISTERED |
| `<WT>/g-coredemo-20261008` | `c94c725900` | `codex/aaos-gov-coredemo-20261008` | 0 | REGISTERED |
| `<WT>/gov-ui-20261008` | `b55a1238f3` | `codex/aaos-gov-ui-20261008` | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `<WT>/index-newline-20261007` | `cdb908e53a` | `codex/index-newline-20261007` | 0 | REGISTERED |
| `<WT>/longpath-importer-20261007` | `4f547f5f2b` | `codex/longpath-importer-20261007` | 0 | REGISTERED |
| `<WT>/longpath-intake-20261007` | `064603cdaa` | `codex/longpath-intake-20261007` | 0 | REGISTERED |
| `<WT>/oss-reuse-20261008` | `15f79cf7fc` | `codex/oss-reuse-templates-20261008` | 0 | REGISTERED |
| `<WT>/spillover-readback-20261007` | `759bb5ee61` | `codex/spillover-readback-20261007` | 0 | REGISTERED |
| `<WT>/supply-bind-20261007` | `563471fee4` | `codex/supply-bind-20261007` | 1 | DIRTY-UNCOMMITTED-PROTECTED |
| `<WT>/ui02-nav3-20261008` | `a8d2e0bb2e` | `codex/aaos-ui02-nav3-20261008` | 0 | REGISTERED |
| `<WT>/v3-era` | `968c4795e4` | DETACHED | 3 | DIRTY-UNCOMMITTED-PROTECTED/DETACHED |
| `<WT>/worker-quality-0906` | `4ca46eaf94` | DETACHED | 15 | DIRTY-UNCOMMITTED-PROTECTED/DETACHED |
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/minimax-aaos-cosmic-ui-20261001` | `627e74ffcc` | `codex/minimax-aaos-cosmic-ui-20261001` | 0 | FOREIGN-OWNERSHIP(path) |

磁盘存在、既无注册也无 `.git`（`UNREGISTERED-LEFTOVER`；删除属 volume agent/owner，本节点只登记，未解析其内容）：

| `<WT>/` 目录 | 顶层内容 |
| --- | --- |
| `.project-local/` | `runs` |
| `dp-f01-20260925/` | `data` |
| `worker-outside-test/` | `worker-check` |

Green 部署目录 `.ui-task-tree/` 侧（本仓库之外，只读登记，绝不进入）：

| 目录 | `.git` 形态 | 本仓库是否注册 |
| --- | --- | --- |
| `ArcheAxis-Knowledge-OS/` | 无 | 否 |
| `ArcheAxis-Knowledge-OS-mainline/` | gitdir | 否 |
| `ci-green-candidate-6621aab7/` | 无 | 否 |
| `minimax-aaos-cosmic-ui-20261001/` | gitfile | 是 |

`ArcheAxis-Knowledge-OS-mainline` 自带 `.git` 目录、未在本仓库注册，是独立克隆（owner 前一轮报 5.78 GB、属 `CodexSandboxOnline`、git 以 dubious ownership 拒绝）；本轮只核实其存在与形态，体量未测量（NOT_MEASURED），未在其中执行任何命令。

### D3 retire-ready 与命令（由 owner/volume 执行，本节点不执行）

入选三条同时成立：tip 是 PIN 的祖先或等于 PIN；其注册工作树干净；PIN 之外无提交。
已排除：`main`（本地基线名，不属本轮清理）、集成线 `codex/aaos-gov-ui-20261008` 与同 tip 的 `codex/aaos-gov-volume-20261008`、以及我的写入分支 `codex/aaos-branch-disposition-20261008`。

```
# 0) 站在 HEAD 已包含待删 tip 的工作树里执行；否则 `git branch -d` 会因当前 HEAD 未含该 tip 而拒绝（这是 -d 的保险，不是缺陷）
cd "<WT>/a-gates-20261008"
# 1) 先摘工作树（脏的会被 git 拒绝）；若某路径是联接点，先 `cmd /c rmdir "<path>"` 解联接（本轮实测无联接点）
git worktree remove "<path>"
# 2) 再删分支，只用 -d，绝不用 -D
git branch -d "<name>"
```

| branch | tip | 工作树 | 命令 |
| --- | --- | --- | --- |
| `codex/aaos-gov-coredemo-20261008` | `c94c725900` | `g-coredemo-20261008` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/g-coredemo-20261008" ; git branch -d "codex/aaos-gov-coredemo-20261008"` |
| `codex/aaos-gov-docs-20261008` | `ec9f3b97b3` | `-` | `git branch -d "codex/aaos-gov-docs-20261008"  # 无注册工作树` |
| `codex/aaos-gov-honesty-20261008` | `15f0e6de93` | `e-honesty-20261008` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/e-honesty-20261008" ; git branch -d "codex/aaos-gov-honesty-20261008"` |
| `codex/aaos-gov-oss-20261008` | `ea1e170024` | `f-oss-20261008` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f-oss-20261008" ; git branch -d "codex/aaos-gov-oss-20261008"` |
| `codex/aaos-gov-resindex-20261008` | `9f3fd470a5` | `c-resources-20261008` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/c-resources-20261008" ; git branch -d "codex/aaos-gov-resindex-20261008"` |
| `codex/aaos-gov-uia11y-20261008` | `da952cd5aa` | `-` | `git branch -d "codex/aaos-gov-uia11y-20261008"  # 无注册工作树` |
| `codex/aaos-gov-uigates-20261008` | `9b306242ed` | `-` | `git branch -d "codex/aaos-gov-uigates-20261008"  # 无注册工作树` |
| `codex/aaos-member-chain-20261007` | `0e04f494df` | `aaos-member-chain-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/aaos-member-chain-20261007" ; git branch -d "codex/aaos-member-chain-20261007"` |
| `codex/aaos-p3-ui-convergence-20260922` | `43c2cafa1b` | `-` | `git branch -d "codex/aaos-p3-ui-convergence-20260922"  # 无注册工作树` |
| `codex/aaos-ui-core-integration-20261007` | `5afb4f285b` | `-` | `git branch -d "codex/aaos-ui-core-integration-20261007"  # 无注册工作树` |
| `codex/aaos-ui-phase2-20261001` | `1a981a4482` | `-` | `git branch -d "codex/aaos-ui-phase2-20261001"  # 无注册工作树` |
| `codex/aaos-ui02-nav3-20261008` | `a8d2e0bb2e` | `ui02-nav3-20261008` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/ui02-nav3-20261008" ; git branch -d "codex/aaos-ui02-nav3-20261008"` |
| `codex/asr-pipe-utf8-20261007` | `7d27a1cabd` | `asr-pipe-utf8-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/asr-pipe-utf8-20261007" ; git branch -d "codex/asr-pipe-utf8-20261007"` |
| `codex/canonical-browser-host-20261007` | `fa3cc7fb75` | `canonical-browser-host-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/canonical-browser-host-20261007" ; git branch -d "codex/canonical-browser-host-20261007"` |
| `codex/cleanup-readback-20261007` | `6396bfbbce` | `cleanup-readback-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/cleanup-readback-20261007" ; git branch -d "codex/cleanup-readback-20261007"` |
| `codex/dsh-aaos-real-multiformat-loop-20261001` | `45a7d17c5d` | `dsh-backend-loop-20261001` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/dsh-backend-loop-20261001" ; git branch -d "codex/dsh-aaos-real-multiformat-loop-20261001"` |
| `codex/f01-csv-cells-20261007` | `3419419045` | `f01-csv-cells-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f01-csv-cells-20261007" ; git branch -d "codex/f01-csv-cells-20261007"` |
| `codex/f04-detect-20261007` | `86bae0f32d` | `f04-detect-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f04-detect-20261007" ; git branch -d "codex/f04-detect-20261007"` |
| `codex/f04-detect-ui-20261007` | `34ec2bd0cb` | `f04-detect-ui-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f04-detect-ui-20261007" ; git branch -d "codex/f04-detect-ui-20261007"` |
| `codex/f06-pages-ui-20261007` | `86c0170e2d` | `f06-pages-ui-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f06-pages-ui-20261007" ; git branch -d "codex/f06-pages-ui-20261007"` |
| `codex/f09-cell-anchor-20261007` | `96cbff5ce4` | `f09-cell-anchor-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f09-cell-anchor-20261007" ; git branch -d "codex/f09-cell-anchor-20261007"` |
| `codex/f10-diarize-20261007` | `0830cc5e95` | `f10-diarize-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f10-diarize-20261007" ; git branch -d "codex/f10-diarize-20261007"` |
| `codex/f10-supply-20261007` | `995a2cdf5b` | `f10-supply-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f10-supply-20261007" ; git branch -d "codex/f10-supply-20261007"` |
| `codex/f15-folder-ingest-20261007` | `3742603faf` | `f15-folder-ingest-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f15-folder-ingest-20261007" ; git branch -d "codex/f15-folder-ingest-20261007"` |
| `codex/f15-status-row-20261007` | `4b9828c405` | `f15-status-row-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f15-status-row-20261007" ; git branch -d "codex/f15-status-row-20261007"` |
| `codex/index-newline-20261007` | `cdb908e53a` | `index-newline-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/index-newline-20261007" ; git branch -d "codex/index-newline-20261007"` |
| `codex/longpath-importer-20261007` | `4f547f5f2b` | `longpath-importer-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/longpath-importer-20261007" ; git branch -d "codex/longpath-importer-20261007"` |
| `codex/longpath-intake-20261007` | `064603cdaa` | `longpath-intake-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/longpath-intake-20261007" ; git branch -d "codex/longpath-intake-20261007"` |
| `codex/oss-reuse-templates-20261008` | `15f79cf7fc` | `oss-reuse-20261008` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/oss-reuse-20261008" ; git branch -d "codex/oss-reuse-templates-20261008"` |
| `codex/spillover-readback-20261007` | `759bb5ee61` | `spillover-readback-20261007` | `git worktree remove "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/spillover-readback-20261007" ; git branch -d "codex/spillover-readback-20261007"` |
| `preserve-p3-ui-convergence` | `43c2cafa1b` | `-` | `git branch -d "preserve-p3-ui-convergence"  # 无注册工作树` |

retire-ready 共 31 个分支，其中 24 个还挂着注册工作树。tip 均已在 PIN 内，删工作树只丢可复现的检出目录，不丢内容；执行前仍需各线主/owner 逐条确认该线已闭，尤其本轮 20261008 的 9 条已并入线：`codex/aaos-gov-coredemo-20261008`, `codex/aaos-gov-docs-20261008`, `codex/aaos-gov-honesty-20261008`, `codex/aaos-gov-oss-20261008`, `codex/aaos-gov-resindex-20261008`, `codex/aaos-gov-uia11y-20261008`, `codex/aaos-gov-uigates-20261008`, `codex/aaos-ui02-nav3-20261008`, `codex/oss-reuse-templates-20261008`。

### D4 PIN 之外、需要合并决策的分支（唯一提交及其触及文件）

已并入 PIN 的分支不在此列（D1 中 `唯一提交=0` 者）。已知冲突面在本树的实际路径：`frontend/src/components/DocumentEditor.tsx`、`frontend/src/spaces/CanonicalLibrarySpace.tsx`、`frontend/src/spaces/CanonicalLearningSpace.tsx`；供给台账 `docs/truth/SUPPLY_CHAIN_LEDGER.json`。

- `codex/aaos-gov-ui-20261008` @ `b55a1238f3`（DIRTY-UNCOMMITTED-PROTECTED）：PIN 之外 5 个提交。集成线本身（其 PIN 之后的提交就是把其它线并进来的动作）。提交：`b55a1238 integrate: template workspace gated in a real browser engine with falsification`; `d73c50d7 test(ui): gate the 学科模板 surface in the real browser engine and make its empty states honest`; `74504d46 fix(audit): make citation resolution exact but invocation-independent`; `24f77292 docs(handoff): narrow the template-gate claim to what the grep actually shows`; `bf357f76 docs(handoff): record the honesty fixes, the OSS integration and the post-merge verification`
  - 触及文件（7）：`docs/current/AAOS-GOVERNANCE-UI-HANDOFF-20261008.md`, `frontend/src/__tests__/TemplateBindings.test.tsx`, `frontend/src/components/content.css`, `frontend/src/templates/TemplateWorkspace.tsx`, `scripts/a0_browser_smoke.py`, `scripts/audit/reference_validation.py`, `tests/test_reference_validation.py`
  - 远端包含：无（推送状态 NOT_VERIFIED）；工作树：gov-ui-20261008；冲突面命中：未命中；供给台账命中：未命中

- `codex/aaos-p04-doc-loop-20261007` @ `72a0bbc24a`（UNIQUE-COMMITS-PUSHED）：PIN 之外 6 个提交。需要合并决策：写入时集成线仍缺 6 个。提交：`72a0bbc2 style: apply rustfmt to the writer-isolated review path and basis guard`; `d17bac63 feat(frontend): route ODF and RTF to the text reader from the product UI`; `47f30a95 fix(learning): compute FSRS schedule outside the canonical writer`; `19e5688c test+fix(frontend): satisfy full-suite tsc and design-contract gates after format/folder fixes`; `fb8ee899 fix(frontend): make folder ingest a real, resumable batch instead of a fixed first-200 enqueue`; `cba1106f fix(frontend): read back ordinary format results and route text-source extensions`
  - 触及文件（10）：`crates/archeaxis-api/src/lib.rs`, `crates/archeaxis-domain/src/learning.rs`, `crates/archeaxis-domain/tests/assessment.rs`, `crates/archeaxis-domain/tests/learning_schedule_basis_guard.rs`, `frontend/src/__tests__/FolderIngest.test.tsx`, `frontend/src/__tests__/JobContent.test.tsx`, `frontend/src/__tests__/TranscriptionReopen.test.tsx`, `frontend/src/api/conversionKinds.ts`, `frontend/src/components/FolderIngest.tsx`, `frontend/src/components/JobContent.tsx`
  - 远端包含：`refs/remotes/origin/codex/aaos-p04-doc-loop-20261007`；工作树：aaos-p04-doc-loop-20261007；冲突面命中：未命中；供给台账命中：未命中

- `codex/aaos-ui-templates-20261008` @ `d73c50d7c0`（UNIQUE-COMMITS-LOCAL-ONLY）：PIN 之外 1 个提交。无需合并决策：写入时集成线 tip 已全部吸收。提交：`d73c50d7 test(ui): gate the 学科模板 surface in the real browser engine and make its empty states honest`
  - 触及文件（4）：`frontend/src/__tests__/TemplateBindings.test.tsx`, `frontend/src/components/content.css`, `frontend/src/templates/TemplateWorkspace.tsx`, `scripts/a0_browser_smoke.py`
  - 远端包含：无（推送状态 NOT_VERIFIED）；工作树：b-surfaces-20261008；冲突面命中：未命中；供给台账命中：未命中

- `codex/github-delivery-docs-20260929` @ `aa8046996c`（UNIQUE-COMMITS-LOCAL-ONLY）：PIN 之外 1 个提交。需要合并决策：写入时集成线仍缺 1 个。提交：`aa804699 docs: update optional GitHub delivery guide`
  - 触及文件（1）：`GITHUB_DELIVERY.md`
  - 远端包含：无（推送状态 NOT_VERIFIED）；工作树：无；冲突面命中：未命中；供给台账命中：未命中

- `codex/minimax-aaos-cosmic-ui-20261001` @ `627e74ffcc`（UNIQUE-COMMITS-PUSHED）：PIN 之外 2 个提交。需要合并决策：写入时集成线仍缺 2 个。提交：`627e74ff State the palette invariant instead of counting palettes by hand`; `fec7a18f Add the cosmic UI layer: backdrop, glass shell and honest placeholders`
  - 触及文件（14）：`apps/ArcheAxis.Desktop/AaosBackdrop.cs`, `apps/ArcheAxis.Desktop/MainWindow.axaml`, `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`, `apps/ArcheAxis.Desktop/Program.cs`, `apps/ArcheAxis.Desktop/ThemePalette.cs`, `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml`, `apps/ArcheAxis.Desktop/Views/SourceReaderView.axaml`, `tests/test_aaos_icon_b10_contract.py`, `tests/test_aaos_narrow_layout_contract.py`, `tests/test_avalonia_visual_authority.py`, `tests/test_b03_navigation_rail_contract.py`, `tests/test_desktop_navigation_contract.py`, `tests/test_home_graph_b10_breakpoint.py`, `tests/test_navigation_hierarchy_contract.py`
  - 远端包含：`refs/remotes/origin/codex/minimax-aaos-cosmic-ui-20261001`；工作树：minimax-aaos-cosmic-ui-20261001；冲突面命中：未命中；供给台账命中：未命中

`codex/aaos-gov-ui-20261008` 本身不是待合并候选：它是承载 PIN 的集成线，本轮相对 PIN 多出的 5 个提交中 merge 提交 1 个，即“把其它线并进来”的动作本身。

### D5 脏工作树保护清单（写入时逐个复测；只登记，不解析、不处置）

| 工作树 | HEAD | branch | dirty |
| --- | --- | --- | ---: |
| `<MAIN>` | `1a981a4482` | `codex/Audit` | 22 |
| `<WT>/aaos-longpath-app-20261007` | `1c5d42b262` | `codex/aaos-longpath-app-20261007` | 1 |
| `<WT>/aaos-ui-core-integration-20261007` | `88cc2c47d0` | `codex/aaos-ui-u05-20261007` | 1 |
| `<WT>/aaos-ui-newui-20261007` | `81eb27bb0f` | `codex/aaos-ui-newui-20261007` | 5 |
| `<WT>/d-docs-20261008` | `fb63001542` | `codex/aaos-gov-volume-20261008` | 2 |
| `<WT>/gov-ui-20261008` | `b55a1238f3` | `codex/aaos-gov-ui-20261008` | 1 |
| `<WT>/supply-bind-20261007` | `563471fee4` | `codex/supply-bind-20261007` | 1 |
| `<WT>/v3-era` | `968c4795e4` | DETACHED | 3 |
| `<WT>/worker-quality-0906` | `4ca46eaf94` | DETACHED | 15 |

交办时点名的 6 个脏保护工作树，写入时复测值：`worker-quality-0906`=15、`aaos-ui-newui-20261007`=5、`v3-era`=3、`supply-bind-20261007`=1、`aaos-ui-core-integration-20261007`=1、`aaos-longpath-app-20261007`=1。

写入时新出现的脏项（并行 agent 正在其中编辑/提交，同样只登记不处置）：`<WT>/d-docs-20261008`=2、`<WT>/gov-ui-20261008`=1。

### D6 `codex/Audit` 与主检出的未跟踪内容

- 分支 `codex/Audit` @ `1a981a4482`：是 `origin/main`（`4b9828c405`）的祖先：yes，落后 750；也是 PIN 的祖先，PIN 之外提交 0 个。所以“Audit 有而 main 没有”的提交集合为空——它的唯一性不在 git 里。
- 主检出 `D:/All projects/ArcheAxis-Knowledge-OS`：写入时 porcelain 22 条，全为未跟踪 `??`（示例：`?? crates/archeaxis-api/tests/contract_capability_registry.rs`，`?? docs/history/closure-tasks/`，`?? docs/history/desktop-attachments/`）。
- `docs/history/` 实测：1114 个文件、498341341 字节（475.3 MiB），git 只跟踪其中 88 个；`git check-ignore docs/history` 返回码 1（非 0 = 未被忽略）。即绝大多数体量是**未跟踪且未被忽略**，只存在于这台机器，任何分支删除、检出切换或 `git worktree remove` 都不会重建它。
- 结论：`codex/Audit` 分支名本身可 retire（tip 已在 PIN 内），但**主检出目录不是本轮清理对象**；在这批 `docs/history/*` 被归档或提交之前，不得对主检出做清理、`git clean` 或切换式操作。

### D7 `git worktree prune`

- survey 阶段与写入阶段各跑一次 `git worktree prune --dry-run -v`，写入时的输出：`(empty)`。
- 写入时复查：38 条注册路径中缺失 0 条；37 条 `.git/worktrees/*` admin 记录与 list 一一对应；无 `locked`、无 `prunable`。
- 结论：**本轮没有过期注册，因此未执行真正的 `git worktree prune`**（执行也是 no-op，且会与并行删除动作抢元数据）。

### D8 复现

收据（gitignored，不入库）在本工作树 `.project-local/branch-disposition/`：`survey3.py`/`survey3.json` 与 `survey4.py`/`survey4.json`（较早快照，只用于漂移对照）、`gen_section2.py`（本节的生成器：重跑即按当时 live refs 全量再测）、`gates.py` + `gates-before.txt`/`gates-after.txt`（三道文档门）。
