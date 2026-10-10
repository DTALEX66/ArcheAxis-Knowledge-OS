# apps/desktop（Avalonia 桌面层 · 骨架占位）

> **2026-10-10 路由修正：本页属于历史/继承范围，不是当前执行授权。** 原日期、原SHA和正文按历史解释；其旧宿主/队列/优先级不得覆盖平台规则、Owner当前决定与 [../../AUTHORITY.md](../../AUTHORITY.md)。正式Tauri/React + Rust Core，产品暂停；先解析当前活动指针及路径身份路由。

> DIRECTORY_AUTHORITY：`apps/desktop/**` → avalonia-ui（C#，`may_open_main_database: false`）。
> v0.1 闭环第 1 步：无终端启动 Green 包；Avalonia Supervisor 启动 Rust Core 并完成握手
> （`crates/archeaxis-sidecar-protocol` 信封 + `archeaxis-application::bootstrap` 身份）。

## 构建前置（环境门禁）
构建使用共用库中的 .NET SDK：
`D:\All projects\OS External Configuration\10-toolchains\dotnet\`（scoop `dotnet`/手动 SDK 安装）。
装好后执行：

```powershell
dotnet --version
dotnet build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj --no-restore --nologo
# PROJECT_CONTRACT: csharp + dotnet-10-lts + avalonia-12.1.x
```

## 边界
- 桌面层不直接打开主库；经本地 HTTP（`archeaxis-api`）或 sidecar 信封与 Core 通信
- Supervisor 职责：启动 Core 子进程 → handshake → 健康探针 → 退出/异常恢复
- 未完成能力不做空壳"完成态"

## 状态（2026-09-04）
- ✅ 正式工程：`apps/ArcheAxis.Desktop/`，Avalonia build 已通过（.NET SDK 10.0.400；输出写入项目本地 build 根）
- 当前缺口：可见窗口完整工作台、安装器/签名/卸载和干净机验收仍未闭合
