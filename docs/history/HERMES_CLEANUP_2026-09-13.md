# .hermes 遗留目录清理与迁移 — 2026-09-13

> 执行人：Hermes（DeepSeek-v4-pro）。依据：用户授权「根据新规划的仓库规范，有用的迁移并入新规范化目录，没用的全部删除」。
> 权威依据：`docs/DIRECTORY_AUTHORITY_INDEX.md`（`.hermes/` = `LEGACY_MIXED_PRESERVE`）、`docs/current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md`、`docs/authority/taskpack-0912-r5/CLEANUP-AND-SPILL.md`（CLEAN05 保全 → CLEAN07 精确清理）。
> 本报告是证据记录，不代表 commit/push 授权。

## 1. 体积结果（实测回读）

| 指标 | 清理前 | 清理后 | 释放 |
|---|---:|---:|---:|
| 项目根 `.` | 46G | 14.67G | **~31.3G** |
| `.hermes/` | 34G | 497MB | **~33.5G** |

清理后 `.hermes/` 剩余 497MB = `rt/`（496MB，打包 runtime，规范排除在自动清理外）+ 残留 ACL-deny 空目录（约 1MB）。

## 2. 迁移（保全的有用资产 → `docs/history/`）

全部经大小校验（源 == 目标）后 `shutil.move`：

| 源（.hermes/ 下） | 目标（docs/history/ 下） | 大小 |
|---|---|---:|
| desktop-attachments/ | desktop-attachments/ | 127.5MB |
| task-artifacts/ | task-artifacts/ | 352.2MB |
| kanban/ | kanban/ | 0.1MB |
| plans/ | plans/ | 0.1MB |
| handoffs/ | handoffs/ | <0.1MB |
| closure-tasks/ | closure-tasks/ | <0.1MB |
| evidence/ | evidence/ | 0.9MB |
| migrated-windows-state/ | migrated-windows-state/ | 5.9MB |
| sleep-mode/ | sleep-mode/ | 0.3MB |
| sleep-tasks/ | sleep-tasks/ | <0.1MB |
| skill-call-index.json | skill-call-index.json | 4KB |
| （散落文档 11 个） | task-runtime-scattered/ | 小 |
| （4 个 dirty worktree 的 diff） | worktree-preserved-diffs/ | 小 |

注：`desktop-attachments/` 含用户真实资料（TaskPack 附件 zip/md/docx + 2 本 PDF 书），判定为唯一数据，迁移保留。

## 3. 删除（没用的可再生资产）

### 3.1 git worktree（23 个，分支 ref + 提交对象保留在 `.git`）

- 19 个 clean worktree：`git worktree remove` 直接移除。
- 4 个 dirty worktree（ci-baseline-db13d056、client-write-boundary-task1-scope、evidence-anchor-pagination、ci-release-optimization）：先导出 diff 到 `docs/history/worktree-preserved-diffs/`，再 `--force` 移除。
- 合并状态已核查：已 merge 的移除；未 merge 的（append-only-sql-allowlist、bundle-inspector-closure、ci-release-optimization、evidence-anchor-pagination、recovery-shell-closed-loop、recovery-shell-frontend、release-v0.6.9、tier-a-a11y、tier-a-format-matrix）其分支 ref 仍在 `refs/heads/codex/*`，提交对象未丢失。

### 3.2 可再生缓存 / 测试运行目录

- `.hermes/cache/`（uv/pip/playwright 缓存，1.8G→0）
- `.hermes/task-runtime/`（cache 9.9G、cargo-target 1.8G、venvs、pycache、pytest-tmp、bundle-driver-venv、各类 `*-2026090X`/`t-*`/`browser-smoke-*`/`pytest-*`/`full-suite-*`/`os-tests-*` 测试目录，29.9G）
- `.hermes/c/`（pytest 临时目录）、`.hermes/toolchains/`（空目录）、`t2-*-pycache`（7 个）
- 29 个 junction（测试用例自建 + worktree 的 frontend/node_modules 复用链接）先 `rmdir` 单删链接、不跟目标。

## 4. 残留（需管理员权限删除）

46 个 ACL-deny 空目录（历史「路径隔离/权限」测试遗留的 deny-everyone ACL），非管理员无法 takeown/icacls/删除，空间约 1MB：

- `.hermes/cache/`（空壳）
- `.hermes/t2-{base,base2,cache,cache2,final-base,final-cache,fix1-base,fix1-cache,fix1-full-base,fix1-full-cache}/`
- `.hermes/task-runtime/` 下 35 个残留目录（ci-release-optimization、post-release-v068、post-release-v069、release-v069、worktrees、t-*、g-* 等）

管理员清理命令（需在管理员 PowerShell 中逐项执行）：

```powershell
takeown /f "<path>" /r /d y
icacls "<path>" /grant "$($env:USERNAME):F" /t /c /q
rd /s /q "<path>"
```

## 5. Git 状态

- `git status --short`：0 modified，14 untracked（全部为 `docs/history/` 迁移资产 + 会话前既有的 `docs/current/SESSION-RESTART-2026-09-12.md`）。
- `git worktree list`：仅剩主仓库 + `.project-local/worktrees/{v3-era,worker-quality-0906}`（新根，不在本次清理范围）。
- **未执行 commit / push / 清理**，等待用户决定迁移资产是否纳入版本管理。

## 6. 回滚说明

- 已删除的 worktree：分支 ref + 提交对象在 `.git`，`git checkout codex/<branch>` 可恢复。
- 已删除的缓存/测试目录：由对应工具重跑再生。
- 已迁移资产：`docs/history/` 下完整保留。
- dirty worktree 的未提交改动：diff 已保全在 `docs/history/worktree-preserved-diffs/`。
