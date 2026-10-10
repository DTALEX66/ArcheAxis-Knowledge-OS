# AAOS-01 Q00 现场与最小对账回执（2026-10-04）

包：`AAOS_01_快速重构_多格式闭环_20261004`（`registries/tasks.json` schema `aaos.taskpack.planning/v1`，`production_configuration: false`）
本文件按 `reports/现场与交接回执模板.md` 填写，**只写已观察的事实**，未知 `UNVERIFIED`，未执行 `NOT_RUN`。

## 1. 模板逐项

| 模板字段 | 已观察的事实 |
| --- | --- |
| 当前任务和唯一 writer | **Q00**。Rust Core 仍是唯一 canonical 写者；本轮**未改变写者**（未执行 Q01） |
| 项目根与有效 Authority | 根 `D:\All projects\ArcheAxis-Knowledge-OS`（`codex/Audit @ 1a981a44`）。Authority：`AGENTS.md`、`LESSONS_LEARNED.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`docs/SHARED_RESOURCE_PATH_INDEX.md`、`docs/truth/*`、`docs/current/*`、`docs/authority/taskpack-0919-r6/*` |
| HEAD 完整 SHA / dirty / worktree | 本工作树 `9fd945012ebdc5036e16c69b4e0c3f924adefd25`，分支 `codex/dsh-aaos-real-multiformat-loop-20261001`，**CLEAN** |
| 当前 PR head/base 和依赖 | **PR #157**（head 本分支，**base `codex/Audit`**）OPEN；**PR #158**（`codex/minimax-aaos-cosmic-ui-20261001` → `codex/Audit`）OPEN；**PR #156**（`codex/aaos-ui-phase2-20261001` → `main`）OPEN |
| worktree 数量 | **8** 个：根 1、本项目 `.project-local/worktrees` 3、Green 下 `.ui-task-tree` 4 |
| 程序/安装路径与产物哈希 | 官方 Green 安装 `D:\All projects\ArcheAxis.Knowledge.Green-x64`（**本轮未触碰**） |
| PID / run_id / 合同版本 | **NOT_RUN**（本轮未启动任何进程） |
| 数据根 / schema / 数据副本身份 | **UNVERIFIED**（本轮未读取 schema 版本） |
| CAS 与备份 manifest / 恢复点 | **UNVERIFIED** |
| 共享模型 root ID / 引用与实际服务 | **UNVERIFIED**；`D:\All projects\Model library` 与服务状态未核 |
| 输入样本与来源版本 | **NOT_RUN**（本轮未导入样本） |
| 实际修改范围与保留旧实现 | **本轮只新增本回执，未改任何实现**。旧实现全部保留 |
| 命令、exit、测试时间和证据位置 | 见 §2 |
| 格式逐项状态与损失 | **NOT_RUN**（属 Q06，未开始） |
| 人类认可 / 机器候选 / 未评估状态 | **NOT_RUN** |
| 实际窗口截图、DPI、主题与窗口条件 | **NOT_RUN**（本轮未启动窗口） |
| NOT_RUN / FAILED / BLOCKED 及具体原因 | 见 §3 |
| 本次不能直接推断的事情 | 见 §4 |
| 回退路径 | 本回执为单文件新增；`git revert` 单个提交即可 |
| 下一项任务和需要读的文件 | **Q01**（重构决定与目录登记）→ 读 `01_完整执行任务书.md` 的 Q01 段、`registries/formats.json` 头部、仓库现行 `docs/CONFIGURATION_AUTHORITY_INDEX.md` |

## 2. 本轮实际执行的命令与结果

| 命令 | 结果 |
| --- | --- |
| `git rev-parse HEAD` / `--abbrev-ref HEAD` | `9fd94501…` / `codex/dsh-aaos-real-multiformat-loop-20261001` |
| `git status --porcelain=v1 -uall` | 空（CLEAN） |
| `git worktree list` | 8 项（见上） |
| `gh pr list --limit 8` | #157 / #158 / #156 均 OPEN |
| `git ls-files` 过滤 lock/tauri/vite | `Cargo.lock`、`uv.lock`、`desktop/package.json`、`desktop/src-tauri/tauri.conf.json`、`desktop/src-tauri/Cargo.lock`、`frontend/package.json`、`frontend/vite.config.ts`、`src-tauri/tauri.conf.json`、`src-tauri/Cargo.lock` |

## 3. NOT_RUN / 待办与阻塞

- **Q01–Q15 全部 NOT_RUN**（本轮只做 Q00）。
- **未登记 Authority delta**：重构决定（Tauri 2 + React/TS/Vite 成为正式宿主）**尚未**写入 Authority —— 属 Q01，本轮未做。

## 4. 本轮**不能**推断的事（写下来免得以后被当成已知）

1. **`frontend/`、`src-tauri/`、`desktop/` 的现状未核实。** 仓库里**确实存在** Tauri/Vite 相关文件（见 §2），而 `AGENTS.md` 现行文本把这三者列为"recovery/behavior references"。**它们离"可用的 Tauri 2 产品"有多远，本轮没有读，因此不判断。**
2. **PR 基线是 `codex/Audit` 而非 `main`**，所以"合并到 main"不是随手可做的一步；集成顺序需单独对待（未裁决）。
3. **官方 Green 与官方资料库本轮零触碰**（未读、未写、未启动、未替换）。
4. **未验证**任何 schema 版本、CAS、备份或共享模型服务状态。

## 5. 与上一轮的衔接

上一个任务包（`AAOS_完整执行任务包_20261004`）的工作停在本分支 `9fd94501`，双端一致、工作树 CLEAN。本轮**不重做**其已收敛项；其中 **`routes.json` 已集中路由**，新包也要求"不重复重做三份映射收敛"（启动提示词第 7 行），与本仓库现状一致。

## 6. 现场身份核验（2026-10-06，只读；补 §1 的三项 UNVERIFIED）

本轮以**只读**方式补核 §1 的三项 `UNVERIFIED`。原文件与官方数据根未被写入：数据库身份取自**副本**，副本制作前后原文件未变。

| 项目 | 已观察的事实 | 证据 |
| --- | --- | --- |
| 声明的存储位置 | `config/defaults.yaml:11-13`：`database.path = data/archeaxis.sqlite`、`journal_mode = WAL`、`backup_dir = data/backups` | 读 `config/defaults.yaml` |
| 实际存在的数据库 | 本工作树 `data/` 下**没有** `archeaxis.sqlite`；实际是 `cognitive_os.sqlite`（3,223,552 B，sha256 `b318c99e5a58107f…`），旁带 `-shm`（32,768 B，sha256 `fd4c9fda…`）与 `-wal`（0 B，空文件 sha256 `e3b0c442…`）；`data/backups` 不存在 | `ls -la data`；对副本取 SHA-256 |
| 该库的身份 | `PRAGMA schema_version=121`、`user_version=0`、`application_id=0`、`page_size=4096`、`journal_mode=wal`；`sqlite_master` 计 90 张表 | 副本置于 `.project-local/task-runtime/q00-identity-20261006/` 后打开读取；WAL 为空，故副本忠实于原库 |
| 必须登记的差异 | **声明路径与实际文件名不一致**：配置指向 `archeaxis.sqlite`，磁盘上是 `cognitive_os.sqlite`。库文件 mtime 为 2026-08-13，而 `-shm` 为 2026-10-06（近期被打开过），因此**不能**断言它就是现役产品库 | 文件名与 mtime |
| 共享模型 root | 仅以环境变量声明：`config/environment/capability-requirements.yaml:283` 的健康检查引用 `$env:ARCHEAXIS_MODEL_LIBRARY_DIR\sherpa-onnx\*\model.int8.onnx`。本 shell 中该变量**未绑定**（None）；磁盘上 `D:\All projects\Model library` 存在（ComfyUI、Qwen、ggml-org、ollama 等）。**存在不等于已绑定**，故模型服务状态仍 `UNVERIFIED` | 环境变量读取；目录存在性 |
| CAS 与备份 manifest | **仍 `UNVERIFIED`**：`config/defaults.yaml` 未声明 CAS 根；仓库内唯一含 "cas" 的路径是任务产物 `.project-local/task-runtime/aaos01-tools/media-cas-patch`；未找到任何备份 manifest，且声明的 `data/backups` 不存在。本轮未执行备份（那是写操作），故恢复点身份仍 `NOT_RUN` | 声明与文件检索 |

**本轮仍未覆盖的未知现场**（保留标注，不当作已知）：CAS 根的位置与内容身份；备份/恢复点（需要一次真实备份，属写操作，须另行授权）；`data/cognitive_os.sqlite` 是否即现役产品数据根（需要 Core 运行期读回，本轮未启动任何进程，故 `NOT_RUN`）。
