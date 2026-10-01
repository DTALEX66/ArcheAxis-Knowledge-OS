# 2026-09-30 精确增量编译缓存清理

本次在用户明确授权后，清除项目 `.project-local/build` 内七个 Cargo `debug/incremental` 目录。删除前逐目录确认无 reparse point、无 Git 跟踪文件，Get-Process 未发现 cargo/rustc/dotnet/MSBuild/ArcheAxis 进程。CIM 进程查询被拒绝，未将其空结果认作成功。当前执行文档没有把这七个目录作为运行收据或产品证据。

删除并回读成功：5,148,194,907 逻辑字节，28,731 个文件，约 4.794 GiB。七个目录回读均不存在。

目标均相对于 `.project-local/build/`：

- `32a18f7418/cargo/debug/incremental`
- `4260083704/cargo/debug/incremental`
- `rust-msvc/debug/incremental`
- `cargo-frontend-current/debug/incremental`
- `cargo-r6-api-fix/debug/incremental`
- `cargo-r6-api-sdk2/debug/incremental`
- `cargo-r6-p4/debug/incremental`

机器可读删除前清单与回读：`.project-local/mig/incremental-prune-20260930/preflight.json`、`readback.json`。本次保留源码、候选程序、依赖缓存、运行收据和用户 UI 修改。增量状态由后续编译重新生成；离线重建未执行，不声明运行验证通过。早前删除被拦截是历史状态，本次精确范围的删除已实际执行成功。

Evidence: bounded cleanup and readback PASS; rebuild NOT_EXECUTED.

## 同轮其他清理

项目根 `build/`：347 个未跟踪 Python 打包产物，2,207,533 字节。此前验证政策允许清除这种打包中间目录；本轮确认目录边界、无 reparse、无跟踪文件后删除，回读不存在。

绿色版 `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline/.project-local/build/` 内以下三个目录由并行只读审计确认 Git 未跟踪、无 reparse、内容为 NuGet/MSBuild 中间文件，且当前无相关编译/应用进程。主智能体删除并回读不存在：

- `obj`：7,557,947 字节 / 23 文件。
- `dotnet/ArcheAxis.Desktop/obj`：38,572,451 字节 / 104 文件。
- `8af23851c3/dotnet/ArcheAxis.Desktop/obj`：10,886,029 字节 / 52 文件。

绿色版小计 57,016,427 字节。证据：`.project-local/mig/green-obj-prune-20260930/preflight.json`、`readback.json`。同轮总清理 5,207,418,867 逻辑字节；这不是磁盘物理释放量测量或项目最新总体积。

未删除 Green 程序 bin、依赖环境、运行数据、恢复快照或 dirty UI 源码。另一 UI 工作树 Git ownership 检查失败，未修改 ACL 或 Git 安全配置，保留待审计。未访问 E/F。没有执行产品重建、启动测试、commit 或 push。
