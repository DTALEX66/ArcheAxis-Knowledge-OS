# ArcheAxis vNext（同仓结构性重启 · Day-0 Core）

> 依据：`ArcheAxis-vNext-Complete-Execution-TaskPack-2026-09-04`（MASTER-TASKPACK §0/§3/§4 +
> PROJECT_CONTRACT.yaml + ADR-0001）。执行裁决：旧产品树 maintenance-only；v0.6.14 冻结为 legacy
> 基线（recoverable / migration-source / behavior-oracle）；同仓 vNext 为未来权威主线。

## 语言与权威边界（不可漂移）

| 层 | 语言 | 主库写入 | 状态 |
| --- | --- | --- | --- |
| Core / Domain / BFF / SQLite store | **Rust**（edition 2024） | ✅ 唯一 writer | ✅ Day-0 落地（本目录） |
| 桌面体验 / Supervisor | C# / Avalonia 12.x | ❌ | 规划（v0.1 之后） |
| Capability worker | Python（隔离包） | ❌ 无库句柄 | 规划 |
| 契约 | OpenAPI 3.1 / JSON Schema | — | 规划 |

禁止：双写、worker/agent 直连 SQL、UI 直连 SQL、复制 live WAL/SHM、Rust 写 legacy 库。

## 已完成（v0.1 闭环数据层，`cargo test` 全绿）

`vnext/src`：
- `schema.rs`：建库建表（WAL）+ schema_version + 对象计数
- `source.rs`：sha256 content-addressed 导入（重复幂等）+ transform 回执
- `anchor.rs`：锚点（source + revision + position）
- `knowledge.rs`：9 类知识 + candidate/accepted/rejected/deprecated 状态机 + 不可变回执哈希
- `learning.rs`：learning_event + 间隔提示
- `search.rs`：FTS5 检索（ensure/reindex/search）
- `backup.rs`：Online Backup API 快照 + restore + 计数核验

集成测试 `tests/v01_closed_loop.rs` 覆盖 12 步闭环的数据层：init → 导入(幂等) → transform
→ anchor → 个人定义+机器候选 → 接受/拒绝 → FTS5 → learning → **重启回读** → **备份 → 新库恢复（计数一致）**。

## 待办（后续 slice）
- Avalonia 桌面 + Supervisor（握手、无终端启动）
- Python worker 契约（提取/OCR/ASR 经 API，无库权限）
- v0.6.14 单向迁移（一致快照 → 只读导出 → Rust dry-run → staging → 差分 → 人工确认）
- Windows 11 Green 打包与 12 步端到端验收

## 命令
```powershell
# 构建/测试（工具链在共用库：Rust 1.97.1 + MSVC；rsproxy 镜像已配）
cmd /c "call \"D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat\" && cd /d D:/All projects/ArcheAxis-Knowledge-OS/vnext && cargo test"
```
