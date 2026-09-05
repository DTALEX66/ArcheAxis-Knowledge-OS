# ArcheAxis vNext crates（同仓结构性重启）

> 对齐 `DIRECTORY_AUTHORITY.yaml`（repo-seed）。legacy 产品路径（app/shared/frontend/src-tauri/desktop）maintenance-only；v0.6.14 冻结为 recoverable legacy 基线。

## 布局（根级 Rust workspace）

- `Cargo.toml` / `rust-toolchain.toml`：workspace（resolver 3，stable 工具链）
- `crates/archeaxis-contracts/`：稳定词表（9 类知识 + 状态常量，零依赖）
- `crates/archeaxis-store-sqlite/`：DDL + workspace init（**唯一可写数据库入口**）+ `migrations/`
- `crates/archeaxis-domain/`：业务逻辑（source/anchor/knowledge/learning/search/backup）

规划（后续 slice，占位未建代码）：
- `crates/archeaxis-application`（编排）、`archeaxis-api`（OpenAPI 3.1）、`archeaxis-sidecar-protocol`、`archeaxis-migration`、`archeaxis-archive`
- `services/python-workers/`（隔离 capability worker，无主库句柄）、`services/local-service`
- `packages/contracts/`（JSON-Schema/OpenAPI）、`apps/desktop/`（Avalonia）

## 权威边界
- Rust = 唯一业务 writer（`crates/archeaxis-store-sqlite` 是唯一可写入口）
- 禁：双写、worker/agent/UI 直连 SQL、复制 live WAL/SHM、Rust 写 legacy 库

## 验证
```powershell
cmd /c "call \"D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat\" && cd /d D:/All projects/ArcheAxis-Knowledge-OS && cargo test"
```
`crates/archeaxis-domain/tests/v01_closed_loop.rs` 覆盖 v0.1 闭环数据层 12 步（含重启回读 + 备份恢复）。
