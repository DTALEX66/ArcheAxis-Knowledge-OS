# R5 当前瘦身处置清单（2026-09-14）

本清单只记录当前 checkout 的可读 regular-file 观察，不把卷总量或 ACL 拒绝内容归因到项目。删除仍须按精确路径执行并做 `Test-Path` 后置验证。

| 路径 | 当前观测 | 处置 | 理由/限制 |
|---|---:|---|---|
| `.project-local/build/cargo` | 5.297 GiB / 2,814 files | 保留 | 当前 Rust Core 构建目标；可重建但删除会失去本地可复现产物，待明确窗口后再清理 |
| `.project-local/build/dotnet` | 0.552 GiB / 127 files | 保留 | 正式 Avalonia 构建产物，当前架构验证依赖 |
| `.project-local/runs/be268a2d33` | 1.829 GiB | 保留 | 当前 R5 证据、清理清单和收据根；不可按缓存盲删 |
| `.project-local/runs/taskpack-paths-test-venv` | 0.723 GiB | 保留 | 当前实际 Python 测试解释器 |
| `.project-local/cache/uv-cache` | 0.464 GiB（清理前） | CLEARED | uv 下载缓存已删除并通过 `Test-Path` 后置验证；需要时可重建 |
| `.project-local/runs/fulltest-final-20260913` | 0.222 GiB | 证据保留 | 全回归收据与失败分类仍用于审计 |
| `.project-local/deeptutor-val` | 0.077 GiB | 证据保留 | DeepTutor 资格验证材料 |
| `.venv` | 0.876 GiB | 保留 | 项目兼容环境；未确认无调用者 |
| `.hermes` | 0.463 GiB 可读 | 保留/未知 | 旧材料与 ACL/私有边界；不读、不整体删除 |
| `.git` | 0.450 GiB 可读 | 保留 | Git 对象与历史，禁止以瘦身名义重写历史 |
| 125 个清理候选 | 约 0.227 GiB（历史收据估算） | BLOCKED | 当前 ACL 拒绝；普通权限重复删除 0/125，不能修改 ACL 绕过 |
| 60+ GiB 差额 | 未观测 | UNKNOWN | 当前可读盘点无法复现；可能包含受保护、重解析或卷外占用，不能归因 |

## 当前证据

- 当前顶层可读汇总：`.project-local` 9.483 GiB、`.venv` 0.876 GiB、`.hermes` 0.463 GiB、`docs` 0.461 GiB、`.git` 0.450 GiB。
- 目录盘点收据：`.project-local/runs/r5-inventory-post-cleanup-20260914/artifacts/inventory.json`。
- 清理候选收据：`.project-local/runs/be268a2d33/r5-dsh-runs-audit-2/candidates.json`。
- 本清单不扩大删除范围；本轮仅执行已分类且用户已授权的 `.project-local/cache/uv-cache` 清理。

### Inventory refresh (2026-09-14)

`inventory_project.py` produced `.project-local/runs/inventory-20260914.json`: 11,523,900,070 logical bytes across 110,284 observed regular files. Observation remains `partial` because 186 ACL permission errors and 11 reparse points were skipped; opaque private directories are intentionally not measured. This does not validate the reported 60+ GiB volume claim and does not authorize ACL changes.

### Large-file candidate refresh (2026-09-14)

项目内当前未发现单个超过 100 MiB 的普通文件；`.project-local/cache` 约 0.17 GiB（cargo 0.096 GiB、uv-python 0.060 GiB、uv-cache-r5 0.011 GiB），均为当前解释器/工具链依赖，未找到新的无条件可删除候选。构建与运行收据仍按可复现性保留。

### ACL-deny path inventory (2026-09-14)

- Receipt: `.project-local/runs/denied-paths-20260914.json`.
- Metadata-only walk of `.project-local` found 206 denied directory observations (nested observations included). Paths are listed for review only; no ACL, ownership, deletion, or content read was performed.
- The list is not a deletion authorization: each path requires ownership, lock, reparse, and retention review before any action.
