# P0-H01 Formal Host Provider Lifecycle

- status: `BLOCKED_BY_AUTHORITY_DECISION`
- evidence_base: `a5ef4f5f4d29203bda4137ecb9cc026658ecb309`
- owner: project authority decision required before production host changes

## 目的

把当前仅由测试包装层证明的 provider 生命周期接入正式 Avalonia → Rust Core 宿主，同时保持 Rust Core 是唯一 Canonical 数据写入者。该卡不把 Python `CapabilityStore` 变成第二个 runner 或数据库写入者。

## 当前证据与缺口

- `tests/test_p0_python_worker_lifecycle.py` 已真实启动项目内 text NDJSON worker，证明 `PluginManifest`/`CapabilityStore` 测试门可组合；证据级别仅为 `TESTED_LOCAL_CONTRACT`。
- `apps/ArcheAxis.Desktop`/Core 当前只传递单一 worker profile；Rust executor 没有统一的 default/fallback/provider replacement 状态解析。
- Python workspace converter dispatch 是旧链路 fallback，不等于正式 Core 宿主生命周期。
- `CapabilityStore` 现有 index/manifest 没有冻结的 default、fallback、replacement generation、health 投影。

## 待冻结的最小契约（提案）

新增版本化项目内 `provider-routing.json` sidecar：由 CapabilityStore 原子写入，Rust Core 只读加载；Desktop 只传递 profile，不直接改 index。契约至少包含 `schema_version`、capability、default provider、ordered fallback providers、provider id/version/manifest digest、enabled/disabled 状态、replacement generation 和 health receipt reference。禁止重复 provider、default=fallback、未安装/disabled provider、capability/version 不匹配和路径逃逸。

## 实施边界

1. C# profile v2 传递 routing sidecar root 与只读快照。
2. Rust launch/application 校验并装载 routing；executor 按 default → fallback 选择，仅在启动/hello/执行失败时 fallback，协议或输出校验失败继续 fail closed。
3. enable/disable/replacement 由 CapabilityStore 原子更新；Core 按 generation 在新请求边界 reload，在途请求不切换。
4. 不扩 Canonical SQLite，不新增商城/自动下载，不访问外置库、Green、真实资料库、E/F 或私有 agent 状态。

## 验收入口

- `crates/archeaxis-application/tests/provider_lifecycle.rs`：default、health/执行失败 fallback、disabled 不启动、enable reload、replacement generation、双失败 terminal failure、无 SQLite 写入。
- `crates/archeaxis-api/tests/launch_auth.rs`：profile/manifest/index 拒绝与正式启动。
- `tests/runtime-paths/CoreSupervisor.Tests/Program.cs`：profile v2 → launch。
- 保留并回归 `tests/test_p0_python_worker_lifecycle.py`、`tests/test_axw_cap501_store.py`、`tests/test_axw_cap502_plugin_manifest.py`。

## 外部前置阻塞

- 当前 shell 未注入项目声明的 `ARCHEAXIS_RUST_TOOLCHAINS`/`ARCHEAXIS_MSVC_VCVARS`；`INCLUDE`/`LIB`/`WindowsSdkDir` 为空。
- 历史精确错误为 `LNK1181: kernel32.lib`，属于 Windows SDK LIB 可用性，不是 Rust API 源码错误。
- 恢复 Rust/API 运行证据需要 Owner 按精确路径授权重新验证外置 Windows SDK；本卡不修改外置工具链或系统配置。

## 模型分配建议

- Astra：冻结最终跨层契约与独立审计。
- Sol：Rust/C# provider lifecycle 协议实现。
- Terra：bounded test harness 与验证。
- Luna：静态索引、收据和低风险回归。
