# 仓库体积审计与瘦身分析 — 2026-09-05

> 目的：把“项目本体 50 多 G”的构成、哪些可瘦身、哪些不可删、以及此前已做的清理，
> 整理成可审计文档与 JSON 证据，供云端 GPT 分析处置。

## 1. 总览
- 仓库本地磁盘占用：**56.6 GB**（实测，逐目录递归求和）
- 远端 Git 仓库：**只含源码 + 历史（<0.2GB）**；下述大目录全部 gitignored，**不上传云端**。
- 结论：**56.6GB ≈ 99% 是未入库的运行时/构建缓存**；真正的“项目本体”（源码/契约/测试/历史）约 0.15GB。

## 2. 体积构成（实测）

| 目录 | GB | 性质 | 可再生 | 处置建议 |
|---|---|---|---|---|
| `.hermes` | 42.86 | agent 运行时历史缓存/归档/站点包副本/证据 | 否(缓存) | 先挑出审计物(收据/清单)再清理 |
| `src-tauri` | 5.18 | legacy Tauri `target/` + 捆绑 python 副本 | 是 | 删 target，保留源码 |
| `desktop` | 4.91 | legacy 桌面 node_modules + tauri target + 捆绑 runtime | 是 | 删 node_modules/target |
| `target` | 1.80 | vNext cargo workspace 构建产物 | 是 | `cargo clean` |
| `.venv` | 0.86 | python 虚拟环境 | 是 | `uv sync` 重建 |
| `apps` | 0.68 | Avalonia bin/obj | 是 | `dotnet build` 重建 |
| `frontend` | 0.10 | legacy React | 部分 | 保留源码 |
| `data` | 0.09 | 开发库(项目产物) | 否 | 保留(项目数据) |
| `.git` | 0.05 | Git 对象库(全历史) | 否 | 保留 |
| 其余源码 | <0.2 | crates/services/packages/tests/scripts/docs | 否 | 保留 |

**可安全重建合计 ≈ 55.3GB；不可删(源码/历史/项目数据) ≈ 1.3GB。**

## 3. 之前已执行的清理（审计轨迹）
- 仓库外溢出：`D:\a`(junction)、`D:\All\Crashpad`(空)、`D:\d`(1.76GB 重复 10-toolchains)、`D:\All projects\.hermes`(空)
- 仓库内测试残留：`.hermes/task-runtime/{tmp,web-tmp,quality-tmp}`
- 规范/漂移修复：见 `ERRORS-AND-LESSONS-2026-09-05.md` 与各 `*-RECEIPT-*.json`

## 4. 建议的下一步（待用户确认后执行）
1. 深审 `.hermes`：抽出本会话 + 历史会话的**审计物**（收据/台账/清单/证据 JSON）归档到
   `docs/authority/` 或独立归档后，清理其余缓存（预计释放 ~40GB）。
2. 清理可再生构建产物：`target`、`src-tauri/target`、`desktop/node_modules`、
   `desktop/src-tauri/target`、`apps/.../bin,obj`（预计释放 ~11GB）。
3. 可选：重建 `.venv`（`uv sync`）以确认锁文件可复现。

## 5. 可审计性
- 机器可读证据：`REPOSITORY-SIZE-AUDIT-2026-09-05.json`（同目录）
- 测量方法：PowerShell 7 逐目录递归求和；无 E 盘访问；未删除任何源码/历史。
- 每个已执行/建议动作都有：对象、体积、可再生性、风险、回滚路径。
