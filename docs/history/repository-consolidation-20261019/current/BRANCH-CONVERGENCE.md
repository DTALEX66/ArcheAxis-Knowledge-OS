# Branch Convergence Baseline · 2026-09-17

本文件是 R5 分支收敛附包的刷新证据，不是新的产品 authority，也不改变冻结任务正文。它记录当前远端分支与收敛提交；任何合并、归档、删除和主线资格结论都必须绑定后续逐分支证据。

## Post-merge disposition — 2026-09-18

- `origin/main`: `3907d0ba190c1c6124832969f813629b99e8d0d1` (PR #149 merge plus branch-disposition evidence).
- Remote branch count after prune: 21.
- Deleted after individual absorption review: `codex/append-only-audit`, `codex/client-write-boundary`, `codex/evidence-bundle-version`, `codex/first-run-setup`, `codex/inspector-activity-closure`, `codex/pipeline-green-hotfix`, `codex/raw-first-web`, `codex/release-candidate-promotion`, `codex/v0.6.0-integration`, `codex/full-loop-0906`.
- The convergence branch was deleted after full qualification; historical baseline entries below are retained for traceability, and this section plus the JSON `post_merge` object describe current disposition.

## 当前基线

- 远端仓库：`DTALEX66/ArcheAxis-Knowledge-OS`
- 远端分支数：32
- 开放 PR：0（`gh pr list --state open`）
- `origin/main`：`1e9813ea2bd49f47d334ba6717c78d3e9feda6ce`
- `origin/codex/full-loop-0906`：`252e7fdf58c0595e814f1751e77d9ef41c8c59cf`
- 当前 checkout HEAD：`7e89f4642ae619d80bad2f6da339c2a769e02b20`
- 精确 CI：`35235195807`，结论 `success`，所有 required jobs completed success
- 本次清单：[`BRANCH-CONVERGENCE.json`](./BRANCH-CONVERGENCE.json)

## 初始分类计数

| 分类 | 数量 |
|---|---:|
| `CURRENT_MAINLINE` | 1 |
| `CURRENT_INTEGRATION_LINE` | 1 |
| `ANCESTOR_ABSORBED` | 9 |
| `SEMANTICALLY_ABSORBED` | 6 |
| `SUPERSEDED` | 3 |
| `CHECK_FOR_VALID_RESIDUAL` | 2 |
| `DONOR_CAPABILITY_TO_REIMPLEMENT` | 2 |
| `HISTORICAL_ARCHIVE_ONLY` | 3 |
| `RELEASE_HISTORY_ONLY` | 4 |

## 证据边界

JSON 对每条远端分支记录当前 tip SHA、merge base、ahead/behind、相对 `origin/main` 的提交/路径数量、最近提交时间和分类。`current_equivalent`、`unique_assets_preserved`、`latest_intent_verdict` 和删除证据仍待逐分支审计，不能把分类直接当作删除批准。

当前任务包要求先完成历史资产保全、最新意图复核、Release/Tag 证据核对和必要的最小 port，再创建短期 convergence branch。`main` 保护、v* 标签、Release 及其资产不在本阶段修改范围内。

## 下一步顺序

1. 审计 `codex/full-loop-0906` 与最新 R5 状态，决定是否需要最小修正。
2. 对 frozen-roadmap、donor、release 和 naming 分支完成唯一资产/行为矩阵，必要时把历史资料复制到既有 history/reference 层并记录来源 SHA。
3. 从最新 `origin/main` 创建的短期 `codex/main-convergence-20260917` 已完成正常 merge，并通过精确 SHA full qualification。
4. 创建 PR 到 `main`，等待 PR 检查和合并后 SHA 回读；不得把本分支 CI 当作 `main` 已合并证据。
5. 只有 main exact SHA qualification 通过、PR 合并且证据落盘后，才逐条删除已批准的远端历史分支。

本阶段未合并、未删除远端分支、未修改 main 保护、未修改 tag/Release。工作区现有未知历史/会话未跟踪路径保持原样。

