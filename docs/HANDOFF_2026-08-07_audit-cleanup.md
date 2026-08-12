# Handoff — 项目审计、清理与交接（2026-08-07）

## 1. 项目状态

- 仓库：`DTALEX66/archeaxis-workspace`（public）
- main HEAD：`ed0888f1ef0b107b263734a9ac9478e53e90ec49`（本地 == 云端）
- 工作树：clean（0 changes）
- 开发线版本：`0.5.0`（unreleased / development / public=false）
- Release 状态：`v0.4.0`、`v0.4.4` 历史公开；`v0.4.2` draft；无新 tag/Release

## 2. 已完成里程碑（本阶段）

| TaskPack | PR | merge SHA | main CI |
|---|---|---|---|
| R0-RELEASE（identity v2） | #42 | `d49aa3d4` | `31183343446` ✅ |
| R0-CI-SHADOW（GatePlan 分类器） | #43 | `13c5e451` | ✅ |
| R0-CI-SELECTIVE（选择性门禁） | #44 | `ba3b200c` | `31188385075` 10/10 ✅ |
| R0-CI 修复（tests/**） | #46 | `d9d8833a` | 重跑中 |
| R0-CI 修复（根目录 **/*.md） | #47 | `22a61fe` | `31193479622` ✅ |
| K0 Truth Reset | #45 | `ed0888f` | `31195559570` ✅ |

**成果：** 选择性 CI 已落地并验证——普通 Python/docs 变更走轻量路由（desktop-shell/windows/wheel/browser 全部 skip，关键路径 23min→3min）；K0 对齐产品真相（Human–AI Learning Workspace 定位）+ 坏 endpoint 501 fail-closed。

## 3. 云端清理（审计 + 瘦身）

### 分支清理
- **审计前：** 30 个非 main 分支
- **删除 27 个**（全部已合并进 main，ahead=0 或已被后续 PR 取代，无 open PR 引用）：
  - chore/ms00-ci-01-contract-shadow, chore/project-naming-alignment, ci/cache-rust-audit
  - feat/axdesk-a2-task-cockpit, feat/k0-truth-reset, feat/ms00-a-product-truth, feat/ms00-b-version-state
  - feat/ms00-ci-02-selective-pr, feat/portable-data-root-clean, feat/r0-registry-provenance-contract
  - feat/tp-be01-workspace-bff, feat/ui01-navigation-shell, feat/ms00-c-release-identity
  - fix/ci-classifier-root-md, fix/ci-classifier-tests-path, fix/ci-window-readiness
  - fix/desktop-close-lifecycle, fix/desktop-close-lifecycle-race, fix/ms00-c-release-identity-v2
  - fix/release-staging-clean, fix/release-v0.4.2-contract, fix/release-v0.4.3-identity
  - fix/ci-playwright-collection, fix/desktop-close-request-destroy, fix/ui-persistent-intake
  - release/v0.4.1-candidate, release/v0.4.3-contract-remediation, release/v0.4.4-lifecycle-remediation
  - sleep/continuous-writer
- **保留 3 个**（含 superseded 提交，非未合并 WIP，安全起见保留）：
  - `feat/archeaxis-desktop-a1-migration`（stale，被取代）
  - `feat/archeaxis-desktop-a1-violet-core`（stale PR #15，被取代）
  - `release/v0.4.0-contract`（历史 release）

### 本地分支
- 删除 27 个已合并进 main 的本地分支（与云端对应）
- 保留 17 个未合并本地分支（`work/tp12-facades`、`fast/*`、`agent/*` 等含独特提交，需独立审查）
- `git fetch --prune` 清理远端已删的 remote-tracking refs

### Releases / tags
- 全部保留（历史证据，不重写）：`v0.4.0`–`v0.4.4` tags；`v0.4.0`/`v0.4.4` 公开 Release + `v0.4.2` draft

## 4. 本地项目清理（瘦身）

**项目目录：13.8G → 7.0G（释放约 6.8G）**

| 删除项 | 大小 | 理由 |
|---|---|---|
| `desktop/src-tauri/target/debug` | 1.9G | Cargo 构建产物，可再生 |
| `.hermes/task-runtime/cache/cargo-target` | 4.0G | Cargo 构建产物，可再生 |
| `.hermes/task-runtime/pycache` | 115M | Python 字节码，可再生 |
| `.hermes/task-runtime/tmp/pytest-of-ALEX` | 128M | pytest 临时，可再生 |
| 根 `.pytest_cache`/`.ruff_cache`/`__pycache__` | ~150K | 测试缓存，可再生 |

**保留项（理由）：**
- `.hermes/toolchains/vs-build-tools` 3.4G — Windows C++ 工具链（重建需大型下载）
- `.hermes/task-runtime` 1.9G — 保留证据（desktop-dev DB、artifacts、evidence、handoff）
- `.hermes/portable-archeaxis` 409M — 可用运行时
- `.hermes/desktop-attachments` 228M — 交接输入（任务包附件）
- `.hermes/desktop-runtime-v1` 395M — 打包运行时
- `.hermes/cache/uv-desktop` 387M、`playwright-browsers` 690M — 依赖缓存（重建慢）
- `.venv` 499M — 虚拟环境（保留，重建耗时）

## 5. Hermes 根目录（区分结论）

**审计结论：Hermes 根目录内无任何 archeaxis-workspace 项目 spill。**

`C:/Users/ALEX/AppData/Local/hermes/` 下所有项均为 Hermes **全局基础设施**，全部保留，未删除：
- `backups` 4.5G（受保护恢复备份）、`hermes-agent` 4.1G（Hermes 代码库）、`state.db` 2.5G（全局状态库）
- `state-snapshots`、`cache`、`lsp`、`node`、`bin`、`skills`、`profiles`、`sessions`、`logs`、`cron`、`config.yaml`

删除任何这些项会破坏 Hermes 运行时。区分原则：**项目 spill 归项目 `.hermes/`，Hermes 全局 state 归 Hermes 根**。项目相关 spill 已在第 4 节（项目根 `.hermes/`）内清理。

## 6. 执行边界

- ✅ **E 盘未触碰**（用户明确要求无许可不动；本次全程未访问）
- ✅ Hermes 全局基础设施未修改/删除
- ✅ 未创建/删除任何 tag 或 Release
- ✅ 未访问凭据、auth、密钥
- ✅ 所有分支删除前均确认无 open PR、无唯一未吸收 WIP
- 项目 git 工作树全程 clean

## 7. 未完成 / 阻塞

- **PR #46 merge-SHA main CI `31191909052`**：历史 merge `d9d8833a` 的 desktop-shell 遇 WM_CLOSE flaky 多次失败；其内容（classifier tests/** 修复）已通过更新 main `ed0888f` 的 CI `31195559570` 验证。已重跑失败 job 作为最终确认。
- 保留的 17 个未合并本地分支 + 3 个 superseded 远端分支：非本次清理范围，留待后续独立审查。

## 8. 后续路线

```text
K1 P0 上游选型 → K2 Compatibility Kernel → K3 Obsidian/Markdown/JSON Canvas C3
→ K4 Workspace UI → K5 Citation + Card/Review → K6 Installed C3 → R1 0.5.0 Alpha
```

（K0 已闭环，K1 可随时启动。）
