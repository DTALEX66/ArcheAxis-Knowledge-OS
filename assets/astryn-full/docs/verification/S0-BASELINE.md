# S0 现场基线核验

任务包：T00｜核验日期：2026-10-13（Asia/Shanghai）｜方式：全部只读命令，退出码随记录给出。

## 1. 本地 ASTRYN

| 项 | 实测结果 | 证据 |
| --- | --- | --- |
| 工作目录 | `D:\All projects\ASTRYN`（Git Bash 解析 `/d/All projects/ASTRYN`） | `pwd` |
| Git 仓库根 | 不存在。`git rev-parse --show-toplevel` → `fatal: not a git repository (or any of the parent directories): .git` | 命令原文输出 |
| `.git` 目录 | 不存在（`test -e .git` → NO） | 文件探测 |
| 已有文件 | 22 个，全部为规范/任务文档与 `.gitkeep` 占位；无源码、无 manifest、无 lockfile、无测试、无 CI | `find . -type f` 全量列举（见 §5） |
| dirty/untracked 保护对象 | 上述 22 个文件全部是本会话前已存在的数据，本轮不得丢失或覆盖 | `git` 不可用，以文件清单登记 |

判定：`NOT_A_GIT_REPOSITORY`。本地不是"已被错误重建的空目录"，而是**尚未纳入版本控制的规范树**。

## 2. 远端 `DTALEX66/ASTRYN`

两条独立证据：

1. `git ls-remote https://github.com/DTALEX66/ASTRYN` → 退出码 `0`，stdout `0` 字节，stderr 空。成功且无 ref。
2. `curl https://api.github.com/repos/DTALEX66/ASTRYN` → `HTTP 200`，`full_name=DTALEX66/ASTRYN`，`private=false`，`visibility=public`，`size=0`，`default_branch=main`，`created_at=2026-10-12T16:11:14Z`，`pushed_at=2026-10-12T16:11:15Z`。

结论：远端仓库**存在、公开、无任何 commit（空仓库）**。`default_branch: main` 是 GitHub 建仓默认声明，不代表 `main` 分支真实存在（`ls-remote` 无 ref 已证否）。

验收含义：`A01 无错误重建` 判定为 **PARTIAL**——远端没有被重复创建或强推，本地也没有 `git init`；但"本地与远端建立关联"这一半尚未完成，见 §6。

### 2.1 影响 Git 传输的实际配置事实（只读取，未修改）

`git config --global --get-regexp '(^url\.|^http\.|^credential\.)'` 关键结果：

- `url.git@github.com:.insteadof=https://github.com/` — **凡 `https://github.com/…` 一律被重写为 `git@github.com:…`（SSH）**。
- `http.sslbackend=schannel`、`http.version=HTTP/1.1`。
- GitHub 凭据 helper 委托给 `gh auth git-credential`（路径指向 scoop 下 gh 2.95.0）。

这解释了 `docs/current/STATUS.md` 记录的"先前远端读取因 SSH known_hosts 权限拒绝失败"：并非 HTTPS 失败，而是被重写成了 SSH，而当时 `known_hosts` 缺少 GitHub 主机密钥。**本轮 `ls-remote` 已成功**，说明该 SSH 通路当前可用（未修改任何 SSH 配置、凭据或 ACL，仅观察到结果变化）。

任何后续 clone/fetch/push 都会走 SSH 而非 HTTPS，这是仓库获取方案必须考虑的事实。

## 3. 工具链（实测版本，未安装、未改全局配置）

PATH 内**没有** `node`/`npm`/`npx`（`which` 全部返回 not found）。可用解释器只在声明的本地根目录中存在，需绝对路径调用：

| 工具 | 版本 | 路径 | 校验命令 |
| --- | --- | --- | --- |
| Node | `v22.11.0` | `%LOCALAPPDATA%\OpenHuman\node-runtime\node-v22.11.0-win-x64\node.exe` | `node.exe -v` |
| npm（随 22.11.0） | `10.9.0` | 同上 `node_modules/npm/bin/npm-cli.js` | `node npm-cli.js -v` |
| Node | `v26.7.0` | `%LOCALAPPDATA%\hermes\tools\node-26.7.0-win32-x64\node.exe` | `node.exe -v` |
| npm（随 26.7.0） | `11.19.0` | 同上 | `node npm-cli.js -v` |
| Git | `2.54.0.windows.1` | `/mingw64/bin/git` | `git --version` |
| gh | `2.98.0` | `/c/Program Files/GitHub CLI/gh` | `gh --version` |
| Chromium | 构建 `chromium-1208` | `%LOCALAPPDATA%\hermes\tools\chromium-1208\chrome-win64\chrome.exe` | 目录存在性 |

选型：本轮工程绑定 **Node `v26.7.0` + npm `11.19.0`**（较新，对当前 Vite/Vitest 支持良好）。`v22.11.0` 登记为备选，其对本项目门禁的兼容性标 UNVERIFIED，除非另有实测记录。

npm registry 连通性：`npm ping` → `PONG pong:true use:0.385ms`，退出码 `0`。npm 缓存与临时目录已限定在项目内（`npm_config_cache=.project-local/runs/cache/npm`），未触碰全局配置。

## 4. AAOS 现场（只读，供 T01 使用）

`D:\All projects\ArcheAxis-Knowledge-OS` **存在**，含 `.git/`、`AGENTS.md`、`AUTHORITY.md`、`PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml`、`frontend/`、`src-tauri/`、`Cargo.toml`、`Cargo.lock`、`.github/` 等。本轮对 AAOS **未发生任何写操作**；能力级核验见 `docs/architecture/AAOS-HOST-CAPABILITY-MAP.md`（T01 产物，其可用性判定以该文件实测为准，不从本文件推断）。

`docs/authority/PATH-REGISTRY.md` 中 AAOS 的"UNVERIFIED"标签在"路径存在性"这一维度上已被本文件推翻，其余维度（仓库身份、当前运行现场归属、接口可用性）仍未核验，登记保持有效。

## 5. 本轮前既有文件清单（须完整保留）

```
.gitignore  AGENTS.md  AUTHORITY.md  PROJECT_CONTRACT.yaml  README.md
assets/original/.gitkeep          assets/third-party/.gitkeep
contracts/.gitkeep                dev-host/.gitkeep
docs/architecture/.gitkeep        docs/authority/DECISIONS.md
docs/authority/PATH-REGISTRY.md   docs/current/STATUS.md
docs/development/REPOSITORY-LAYOUT.md        docs/research/.gitkeep
docs/tasks/AGENT-START-PROMPT.md  docs/tasks/M0-ACCEPTANCE-TRACKER.md
docs/tasks/M0-EXECUTION-HANDOFF.md           docs/tasks/archive/ARCHIVE-RECEIPT.md
docs/tasks/archive/ASTRYN-DEVELOPMENT-START-V1.0.txt   docs/verification/.gitkeep
src/.gitkeep                      tests/.gitkeep
```

归档完整性：`ASTRYN-DEVELOPMENT-START-V1.0.txt` 的 SHA-256 已由 `docs/tasks/archive/ARCHIVE-RECEIPT.md` 记录为 `866C151DB45E0D0ADFCAFA9F059A836DF859D830420B65AB95673FDD4B08450F` 并与源附件一致（A00 = PASS，沿用既有收据，未在本轮重复生成）。

## 6. 阻塞项与不受阻塞项

`BLOCKED_NEEDS_USER_AUTHORIZATION`：Git 关联方式。三个互斥方案，均需用户选定后才能执行，本轮一律未做：

| 方案 | 动作 | 风险 |
| --- | --- | --- |
| G1 | 在 ASTRYN 根 `git init` + 添加 remote + 首次 commit | 需 `git init` 授权；D003 明确"不自动初始化 Git" |
| G2 | clone 远端空仓库到**新目录**，把现有 22 个文件迁入 | 需新路径授权；不得 clone 到非空目录 |
| G3 | 保持无 Git，仅本地开发 | 无法产出 diff/branch/exact-SHA 证据，A01、A18 长期受限 |

不因该阻塞冻结的工作（本轮继续）：工程骨架、契约与状态机、原创角色与 Dev Host、对话适配、记忆/上下文契约、本地门禁、浏览器验证、交付文档。

明确未执行：`git init`、`clone`、`fetch`、`commit`、`push`、`merge`、`release`、`reset`、`clean`、全局配置修改、SSH/凭据修改、付费模型调用、大型运行时或模型权重下载、正式安装。

| 命令 | 结果 |
| --- | --- |
| `git rev-parse --show-toplevel` | `fatal: not a git repository (or any of the parent directories): .git` |
| `test -e .git` | NO |
| `git ls-remote https://github.com/DTALEX66/ASTRYN` | 退出码 0，stdout 0 字节 |
| `curl https://api.github.com/repos/DTALEX66/ASTRYN` | HTTP 200，`size=0`、`visibility=public`、`default_branch=main`、`created_at=2026-10-12T16:11:14Z` |
| `sha256(归档原文)` | `866C151DB45E0D0ADFCAFA9F059A836DF859D830420B65AB95673FDD4B08450F`（20,960 字节 / 527 行）与 ARCHIVE-RECEIPT 记录逐字符相等 |

## 7. 后续变更追加（同日，非改写上文）

上文 §1–§6 记录的是 T00 时刻的现场，保持原样。之后用户下达"全部上传"指令（D015），现场已变：

- 本地已 `git init -b main`，7 个正向提交 `b42eee2` → `5603f34` → `6aa9785` → `ce07148` → `eb1f4b5` → `2a671f6` → `9cf9a44`，已推送 `DTALEX66/ASTRYN`（推送前实测远端 0 ref，未 force push）。
- `git_identity` 由 UNVERIFIED 变为已核验：本地 HEAD 与服务端 `refs/heads/main` 逐字符一致。
- 远端 CI：`5603f34` 上首次转绿（run 38324785775），最新绿 run 38326024723 @ `9cf9a44`；main 累计 7 次运行 = 3 绿 4 红，逐次归因见台账 A18。
- §6 表中 G1/G2/G3 三选一的问题以 **G1** 落地；G2/G3 不再适用。
- 全程未 force push、未修改全局配置或凭据、未访问 E:/F:。

## 8. 证据级别

本文件所有结论级别：`NO_EVIDENCE` 项已标明；其余为本地实测（终端输出），不涉及真实模型与 AAOS 集成。`REAL` 级别仅适用于远端 API 与 git 命令的实际返回值，已在 §2 原样转录。
