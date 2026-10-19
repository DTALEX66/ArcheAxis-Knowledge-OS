# 绿色仓库清理审计（2026-10-06 测量）

被测路径：`D:\All projects\ArcheAxis.Knowledge.Green-x64`，`du -sh` 合计 **15 G**。
本文只做分类与来源判定，不授权删除；每条给出实测大小、归属依据与建议动作。
删除类动作须先有本清单，且保留点（源码/锁文件/原始数据库）先行确认。

## 一、实测构成（含点目录）

| 路径 | 实测 | 归属判定 | 依据 | 建议 |
| --- | --- | --- | --- | --- |
| `.ui-task-tree/` | 8.9 G | **外部工作流基础设施** | 内含 6 个各自带 `.git` 的工作树：`AAOS-integration-verification-413ad3a0`、`ArcheAxis-Knowledge-OS`、`ArcheAxis-Knowledge-OS-mainline`、`aaos-ui-phase2-integrate`、`ci-green-candidate-6621aab7`、`minimax-aaos-cosmic-ui-20261001` | **保留，不动**。AGENTS.md §3 明令不得因名称含本项目就认领工作流基础设施；归属不明则保留并标记未决 |
| `AAOS-v82e8d28c-20261002-x64/` | 947 M | 本产品旧候选 | `启动星环知识-AAOS-82e8d28c.vbs` 指向它 | **保留**（README 明令） |
| `AAOS-v18a00075-20261001-x64/` | 867 M | 本产品旧候选 | `启动星环知识-AAOS-18a00075.vbs` 指向它 | **保留**（README 明令） |
| `AAOS-vd6bd374-20261001-x64/` | 864 M | 本产品旧候选 | `启动星环知识-AAOS新版.vbs` 指向它 | **保留**（README 明令） |
| `AAOS-Tauri-578d06b78413/` | 775 M | 最新 Tauri 候选 | 本树 P0-2 的独立部署目标 | 保留 |
| `AAOS-Tauri-f151f4c7998a/` | 679 M | Tauri 工程候选 | README 明确记录其已实际部署并已跑完旅程/矩阵 | **保留**（README 明令） |
| `runtime/` | 675 M | 产品运行期目录 | 与候选配套 | 保留 |
| `backups/` | 443 M | 备份 | 属保留点类别 | 保留 |
| `AAOS-Frontend-Acceptance-v4/` | 236 M | 前端验收产物 | 验收留档 | 保留或归档 |
| `EBWebView/` | 42 M | 产品 WebView2 用户态 | 运行产品生成 | 保留（属运行状态，非垃圾） |
| `data/` | 40 M | 产品数据 | 与库配套 | 保留 |
| `aaos-vnext-data*/`（3 个） | ≤352 K | 三个候选各自的隔离数据根 | 每候选一套 | 随候选决定 |
| 根级文件 | <10 M | 含 `archeaxis.sqlite` 987 K、`ArcheAxis.exe` 9 M、若干 `.vbs` 启动器 | — | 保留 |

三份旧候选合计 **2,678 M（2.62 G）**；`.ui-task-tree` 一项即占 8.9 G，是体积主体。

## 二、结论

1. **本仓库没有可自主删除的体积**。8.9 G（约六成）是外部工作流管理的工作树（各带 `.git`），按 AGENTS.md §3 不得认领、不得清理。
2. 其余较大项**既不是垃圾、也有明确保留指令**：本目录 `README.md` 已把本区定义为"本地部署与历史候选保留区"，并写明"目录中的程序、启动器、用户数据与备份分别保留"、"不按目录名再次整删候选、backup 或 venv"。三个旧候选各自被一个 `.vbs` 启动器指向，删除即破坏可点入口。
3. 因此本仓库**本轮零删除**：不做任何目录整删，不新建第二套台账。若日后确需缩减，须先由 README 的保留规则让位，再按逐条清单执行。
4. `EBWebView/`、`data/`、`backups/`、`archeaxis.sqlite` 属运行状态或保留点，保留。

## 三、已执行的清理（本工作树，非绿色仓库）

以下为本轮自查出的**我自己**产生的越界文件，已删除；均可在原流程内重建：

- `.project-local/ci-cargo.bat`：机器本地 cargo 包装。已改为修 `scripts/ci/cargo_test.bat` 支持 `ARCHEAXIS_CARGO_HOME`，用受跟踪入口即可，无需本地包装。
- `.project-local/prove-split.py`：分段执行真实取证脚本。证据已归档至 `.project-local/task-runtime/aaos01-split-20261006/`（`prove-split.py` SHA-256 `0e4dbc10…3a75efff3`，`proof-output.txt` SHA-256 `3c796494…879d471b`），原路径副本删除。
- `.project-local/tmp-window/`：一次性 unittest 运行根，删除。

## 四、开发根（`.project-local`）而非绿色仓库的账目修正

开发根 `build/` 实测 28.28 GB，曾超我先前自定的 22 GB 预算。查明原因后**不改预算数字、也不删缓存**，改为把不可动的那部分如实分列：

- `build/` 中 **25.07 GB 是编译缓存**（`build/cargo`、`build/cargo-gnu`、`build/<identity>/cargo`）。
- `scripts/runtime/dev.py` 明言 "Do not move or remove any historical cache"，缓存因此不在预算可比范围内；把它算进预算只会得到永久假警报。
- `storage_report.py` 现在同列缓存实测量，但预算只对非缓存部分生效（`build/` 非缓存部分约 3.2 GB）。输出示例：`28.28 GB  build/  budget 22.0  (25.07 GB of it is a cache dev.py forbids removing)`。

本轮另修好一个真实缺陷：`_git_root_names()` 以平台默认编码读取 `git ls-files`，遇到本仓库的非 ASCII 路径直接崩溃（整份报告变成异常而非测量）。现按 UTF-8 解码并保留不可解码名。

## 五、保留点说明

上一版把 G1–G5 列为"待裁"，那是在读到本目录 `README.md` 的保留规则之前。现按证据更正为**不删除**：该 README 是绿色仓库自身的权威说明，其"不按目录名再次整删候选、backup 或 venv"是业主既有指令，优先级高于本次清理意图。如业主日后决定缩减，需先修改该 README 的保留规则，再按逐条清单（含 `release-identity.json` 与目录清单 SHA 存档）执行。
