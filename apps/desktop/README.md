# apps/desktop（Avalonia 桌面层 · 骨架占位）

> DIRECTORY_AUTHORITY：`apps/desktop/**` → avalonia-ui（C#，`may_open_main_database: false`）。
> v0.1 闭环第 1 步：无终端启动 Green 包；Avalonia Supervisor 启动 Rust Core 并完成握手
> （`crates/archeaxis-sidecar-protocol` 信封 + `archeaxis-application::bootstrap` 身份）。

## 构建前置（环境门禁）
本机暂无 .NET SDK（`dotnet` 不可用）。按共用库规则，Avalonia 工具链应落位：
`D:\All projects\OS External Configuration\10-toolchains\dotnet\`（scoop `dotnet`/手动 SDK 安装）。
装好后执行：

```powershell
# 预期：dotnet --version 可用后在此目录创建解决方案
dotnet new sln -n ArcheAxis.Desktop
# 参照 PROJECT_CONTRACT: csharp + dotnet-10-lts + avalonia-12.1.x
```

## 边界
- 桌面层不直接打开主库；经本地 HTTP（`archeaxis-api`）或 sidecar 信封与 Core 通信
- Supervisor 职责：启动 Core 子进程 → handshake → 健康探针 → 退出/异常恢复
- 未完成能力不做空壳"完成态"

## 状态（2026-09-04）
- ✅ 骨架已建：`apps/ArcheAxis.Desktop/`（dotnet new avalonia.app，Avalonia 模板），
  `dotnet build` 0 警告 0 错误（.NET SDK 10.0.400 已装 → OS External Configuration/10-toolchains/dotnet）
- 后续：Supervisor 握手接线（sidecar-protocol + archeaxis-application::bootstrap）→ Green 无终端启动
