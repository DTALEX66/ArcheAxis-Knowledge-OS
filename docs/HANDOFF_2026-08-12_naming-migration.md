# HANDOFF 2026-08-12 — 命名体系迁移（Step 1-2）交接

> 承接会话：命名体系迁移（契约 V1 §4，Owner 授权）
> 日期：2026-08-12
> 权威来源：`docs/truth/NAMING_CONTRACT_V1.md`（V1.1 修订）、`docs/truth/EXECUTION_STATUS_LOG.md`

## 1. 摘要（已完成）

### 已上传并 merge
| PR | 内容 | 结果 |
|---|---|---|
| **#131** (merged → main `2694d86`) | 打包身份迁移：pyproject name → `archeaxis-workspace`、CLI 入口 → `archeaxis`、release-manifest id、schema URI → `archeaxis.local`（22 处）、uv.lock 重生成、CI/release.yml/prepare_bundle 同步、manifest digest rev 7 | 全量 1461 passed，门禁双绿 |
| **GitHub 仓库重命名** | `DTALEX66/ArcheAxis-Knowledge-OS` → **`DTALEX66/archeaxis-workspace`**（Owner 确认授权） | 完成，remote 已更新 |
| **OS configuration 同步** | EXTERNAL_DEPENDENCIES.md 双写（`8ab8bee..1b03433`） | 已推送 |

### 已创建待核
| PR | 内容 | 状态 |
|---|---|---|
| **#132** | 活动文件 URL 同步（AGENTS.md SSH、README badge、app/release.py、release_inject_identity.py、classify.py、EXTERNAL_DEPENDENCIES、test URL 断言） | ⚠️ CI 失败（缓存问题，见 §2） |
| **#133** | 60 文档全量替换（按 Owner "所有文档全改"要求）；本地绝对路径已恢复；冻结/权威产物保留旧名 | CI 未核 |

### 契约 §4 迁移状态（V1.1 已记录）
- ✅ Machine ID / dist：`archeaxis-workspace`（#131）
- ✅ CLI：`archeaxis`（#131）
- ✅ GitHub 仓库：`DTALEX66/archeaxis-workspace`（重命名完成）
- ✅ schema URI：`archeaxis.local`（#131）
- ⏳ 待办：环境变量 `ARCHEAXIS_*`、API 根 `/api/v1/`、事件、Tauri Bundle ID `com.archeaxis.workspace`、Windows 数据根 `%LOCALAPPDATA%\ArcheAxis\Workspace`、Windows 可执行 `ArcheAxis.exe`、本地服务 `archeaxis-local-service`

## 2. 问题清单

### 未解决（需下轮处理）
1. **#132 CI 失败**（desktop-fast/desktop-build/a0-gates）
   - 根因：Tauri 构建缓存路径错误。actions/cache 恢复了重命名前的缓存（内容含旧路径 `D:\a\ArcheAxis-Knowledge-OS\...\desktop\src-tauri\target\`），仓库重命名后 checkout 目录为 `D:\a\archeaxis-workspace\...` → os error 3 找不到路径
   - 修复方案：`ci.yml` 的 Rust cache `key` 加版本前缀（如 `-naming-v2`）使旧缓存失效 → 重跑 → 绿后 merge #132
2. **#133 CI 未核**：绿后 merge
3. **Step 3 剩余项**（§4 表中 ⏳ 项）：环境变量/API 根/事件/Bundle ID/Windows 数据根/可执行名/本地服务——需后续分步迁移（契约要求"分别迁移，禁止批量搜索替换"）

### 已解决（记录备查）
- 62 文档批量替换误改本地绝对路径（`D:\All projects\ArcheAxis-Knowledge-OS` → 新名）→ 已恢复 11 处，测试 1461 passed 恢复
- NAMING_CONTRACT §3 映射表被批量替换破坏 → 已恢复旧名 Legacy 语境 + §4 标 DONE + 修订 V1.1
- #131 CI desktop-build 显示卡 35+ 分钟 → GitHub API 状态延迟，实际 PASS（13m54s），不重跑
- bash 引号陷阱（commit message 括号被当命令）→ commit/push 分离执行
- CRLF 误报 → 不修（git blob 纯 LF，CI 用 `--source head`）
- readability_article.html 用户 WIP CRLF 伪差异 → 多次 `git checkout --` 还原，不入 PR

### 有意保留（勿改）
- 冻结/权威产物保留旧名：`FROZEN_EXECUTION_BASELINE`、`DEEPSEEK_FULL_EXECUTION_TASKPACK`、`AUTHORITY_CONTRACT`、zip 二进制、迁移报告 `.txt`/`.stat`（AUTHORITY_CONTRACT 只读 + 不可变快照）
- `NAMING_CONTRACT_V1.md` §3 映射表保留旧名（Legacy 语境）

## 3. 当前仓库状态

- **main**：`2694d86`（#131 merged）
- **权威分支** `codex/frozen-roadmap-deepseek-v1`：LOG-001~133 + 契约 V1.1 记录
- **canonical**：`D:\All projects\ArcheAxis-Knowledge-OS`（目录未改名，仍是旧路径——重命名只发生在 GitHub 远程）
- **remote**：`git@github.com:DTALEX66/archeaxis-workspace.git`
- **开放 PR**：#132（CI 修复中）、#133（待核）
- **本地全量测试**：1461 passed / 5 skipped / 0 failed
- **测试铁律**：`env -u PYTHONPATH uv run --frozen --group ci --group ci-adapters pytest`

## 4. 回滚路径

- #131/#132/#133 均可 `git revert`（各自独立提交，互不耦合）
- 仓库重命名可 `gh repo rename ArcheAxis-Knowledge-OS` 回滚（GitHub 保留旧名 301）
- 缓存修复仅改 cache key，无代码风险

## 5. 下轮首要动作

1. 修 #132 缓存 key（加前缀失效旧缓存）→ 重跑 → merge
2. 核 #133 CI → merge
3. 补 EXECUTION_STATUS_LOG（LOG-135+：命名迁移记录）
4. Step 3 分步规划（环境变量/API 根/Bundle ID 等，需逐个授权）
