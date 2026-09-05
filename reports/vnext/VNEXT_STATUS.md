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
| 归档 | archive crate：开放格式导出/恢复 + manifest | ✅ |
| **v0.1 十二步闭环（Core 层）** | journey 测试全 PASS → `reports/vnext/v01-closed-loop-receipt.json`（11 PASS + manifest sha256） | ✅ |
| 测试基线 | `cargo test --workspace`：14 集成测试全绿（本机 vcvars64+共用库工具链） | ✅ |
| vNext CI | `.github/workflows/vnext-ci.yml`（Windows cargo test + receipt 校验） | 已落（云端执行待 push 后 Actions 确认） |

## 环境门禁（未完成，如实）
| 项 | 门禁 | 处置 |
| --- | --- | --- |
| Avalonia apps/desktop（Green 桌面 + Supervisor） | 无 .NET SDK（本机 dotnet 不可用） | 安装 dotnet-10-lts → OS External Configuration/10-toolchains/dotnet（共用库）；装后建 Avalonia 解决方案 |
| v0.1 Windows Green 端到端（无终端启动） | 依赖 Avalonia 门禁 | 同上 |
| 真实 legacy（v0.6.14）库迁移 dry-run | 需真实旧 workspace 数据（不在仓库） | Owner 提供 legacy 数据文件后：migration export → reports/vnext/legacy-dryrun-*.json |

## 复现
```powershell
cmd /c "call \"D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat\" && cd /d D:/All projects/ArcheAxis-Knowledge-OS && cargo test"
$env:VNEXT_RECEIPT_OUT = ".../reports/vnext/v01-closed-loop-receipt.json"  # journey 测试生成收据
```
