# ArcheAxis vNext 状态与收据（2026-09-04 · goal round 4）

> 依据：MASTER-TASKPACK（同仓结构性 vNext）。完成态以 cargo test / CI 绿 + exact-SHA 收据为准；本文件记录已达成的证据与仍被环境/Owner 门禁阻塞的项（不写成已完成）。

## 已达成（均有证据）

| Slice | 证据 | 状态 |
| --- | --- | --- |
| 治理与契约落仓 | PROJECT_CONTRACT/DIRECTORY_AUTHORITY/DECISION_SUPERSESSION_LEDGER/LEGACY_MANIFEST + .project/** + taskpacks/ + docs/authority(vNext 决策) + ADR-0001 | ✅ |
| packages/contracts/v1 | openapi-outline/errors.catalog/worker-protocol/coverage-receipt/assessment/compatibility | ✅ |
| crates（8 个） | contracts / store-sqlite / domain / api / application / sidecar-protocol / migration / archive | ✅ 全绿 |
| 语言权威边界 | Rust 唯一 writer（store 唯一 DDL）；worker/agent/UI 无库句柄（代码结构约束 + 测试） | ✅ |
| worker 契约 | api jobs 端点 + services/python-workers/worker_extract.py（隔离） | ✅ |
| 迁移 dry-run 工具 | migration crate：只读 inventory/JSONL/sha256 manifest/legacy 零改动（合成库测试） | ✅ |
| **真实 legacy dry-run** | 对真实工作区（快照+主库）只读 export 成功（17 迁移记录）；**两库用户知识表均为空**——管线就绪，内容迁移 N/A（如实） | ✅ reports/vnext/legacy-dryrun-2026-09-04.json |
| Avalonia Supervisor 无头冒烟 | `--smoke`：C# spawn Rust core → 握手 → 清理；SMOKE OK | ✅ |
| Green publish | `dotnet publish -r win-x64` 成功（框架依赖产物） | ✅ |
| 归档 | archive crate：开放格式导出/恢复 + manifest | ✅ |
| **v0.1 十二步闭环（Core 层）** | journey 测试全 PASS → `reports/vnext/v01-closed-loop-receipt.json`（11 PASS + manifest sha256） | ✅ |
| 测试基线 | `cargo test --workspace`：14 集成测试全绿（本机 vcvars64+共用库工具链） | ✅ |
| vNext CI | `.github/workflows/vnext-ci.yml`（Windows cargo test + receipt 校验 + Avalonia dotnet build） | ✅ 云端绿（54f23ba success；首次 failure=收据 grep 模式已修） |

## 环境门禁（未完成，如实）
| 项 | 门禁 | 处置 |
| --- | --- | --- |
| Avalonia apps/desktop（Green 桌面 + Supervisor） | ✅ 已解除并落地 | .NET SDK 10.0.400 → 共用库；apps/ArcheAxis.Desktop 骨架 + CoreSupervisor（spawn core/握手/清理）+ MainWindow 接线；dotnet build 0 错误 |
| v0.1 Windows Green 端到端（无终端启动） | 依赖 Avalonia 门禁 | 同上 |
| 真实 legacy（v0.6.14）库迁移 dry-run | 需真实旧 workspace 数据（不在仓库） | Owner 提供 legacy 数据文件后：migration export → reports/vnext/legacy-dryrun-*.json |

## 复现
```powershell
cmd /c "call \"D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat\" && cd /d D:/All projects/ArcheAxis-Knowledge-OS && cargo test"
$env:VNEXT_RECEIPT_OUT = ".../reports/vnext/v01-closed-loop-receipt.json"  # journey 测试生成收据
```
