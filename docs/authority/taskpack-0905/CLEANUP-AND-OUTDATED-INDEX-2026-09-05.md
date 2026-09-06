# 清理瘦身与过时文档/索引登记 — 2026-09-05

## 已执行清理（本轮）
| 对象 | 处理 |
|---|---|
| `.hermes/task-runtime/tmp/**`（pytest 残留 source_archive/raw-assets 千余文件） | 删除 |
| `.hermes/task-runtime/web-tmp/**`、`quality-tmp/**`（本会话验证残留） | 删除 |
| `C:\Users\ALEX\AppData\Local\ArcheAxis\Workspace\workspaces`（测试 initialize 空目录） | 删除（连同空父级 Workspace/ArcheAxis 一并移除） |
| 本会话临时 ps1/探针/json | 删除 |

## 保留（历史/证据，不删）
- `.hermes/task-runtime` 其余 prior-session 目录（anchor-page/browser-smoke/append-only 等）：
  gitignored 项目运行域，属历史运行证据，未逐一审计前不删（防删唯一证据）。
- `docs/current/`、`docs/authority/vnext-reference/` 历史决策文档：保留为历史。
- 用户输入 `D:\All projects\ARCHEAXIS-FAST-FULL-LOOP-TASKPACK-2026-09-05.zip`：保留（用户原件）。
- Green-x64 真实 data 与捆绑 backup.py 补丁：用户侧产物/授权修复，保留。

## 过时索引登记（保留为历史，标注 superseded）
- `docs/authority/vnext-reference/*.md`（04 决策文档）：被 DECISION_SUPERSESSION_LEDGER SUP-001..010 取代，保留全文作历史。
- `LEGACY_MANIFEST.example.yaml`：模板示例，保留（非过时实现）。
- `openapi-outline.yaml` 旧标题版本：已被 0.2.0-reference-slice2 取代（同文件升级）。
- `.project/**` 治理协议文件：仍为权威，不清理。
- 收据目录按时间切片命名，保留全部（审计链）。

## 双端一致性
本地 HEAD == origin/main；工作树干净；`.hermes` 为 gitignored 不影响远端仓库。
