# Desktop Shell 与便携运行验收记录（2026-07-23）

## 结论

`ArcheAxis OS` 已不是单纯浏览器预览：当前 `main` 包含可构建、可启动的 Windows Tauri 桌面壳。它启动随包附带的隔离 Python runtime，再以 WebView2 打开本机 `/workspace`。

本次验收在本机以当前 `main`（`604a41275bad0671389f1200f1e9519ed77264bc`）完成；不把浏览器 smoke 或 Rust 单元测试误报为桌面安装验收。

## 已验证事实

1. `npm --prefix desktop run tauri build` 成功，生成：
   - `desktop/src-tauri/target/release/archeaxis-desktop-shell.exe`
   - `desktop/src-tauri/target/release/bundle/nsis/ArcheAxis OS_0.4.0_x64-setup.exe`
2. CI 的 exact-SHA `desktop-shell` 真实构建并执行 NSIS 安装验收，结果为：
   - `WorkspaceStatus=200`
   - `GracefulShutdown=true`
   - `ForcedTreeCleanup=true`
   - `CleanUninstall=true`
3. 本机建立了未提交、被 `.gitignore` 覆盖的复制运行目录：
   - `.hermes/portable-archeaxis/ArcheAxis-OS-0.4.0/`
   - 内容为 release executable 与完整 `runtime/`；16,731 个文件、387,130,510 bytes。
4. 该复制件经 PowerShell `Start-Process` 成功启动。验收时：
   - desktop PID：`28788`；进程响应正常；
   - child Python：便携目录下的 `runtime/python/python.exe`；
   - Python 命令：`-B -I -m app.runtime_entrypoint core`；
   - child listener：`127.0.0.1:59016`；
   - child WebView：Microsoft Edge WebView2，`archeaxis-desktop-shell.exe` embedded mode。

## 当前问题与边界

### P0：严格 portable data mode 尚未实现

当前 installed runtime 的 `resolve_runtime()` 使用 Tauri `app_local_data_dir()` 同时作为工作目录与 `COGNITIVE_DATA_DIR`。因此复制的 executable 虽能免安装启动，但运行数据和 WebView2 profile 仍落入：

```text
%LOCALAPPDATA%\com.archeaxis.cognitive-workspace\
```

证据：`desktop/src-tauri/src/lib.rs:47-57` 传入 `app_local_data_dir()`；`desktop/src-tauri/src/runtime.rs:46-51` 将它作为 `cwd`/`data_dir`。这不是数据随目录携带的严格便携产品，不能称为完整 portable release。

**完成条件：** 增加显式、可测试的 portable mode 合同（例如 executable 邻近的可写 data root 或受控启动参数）；默认安装版仍保留 per-user local data；禁止 portable mode 回退到用户 profile；新增 Rust/unit、安装/复制运行、退出清理测试。

### P1：桌面用户说明缺失

`desktop/README.md` 不存在。虽然 CI 能构建、安装和卸载，但用户没有独立文档了解：默认安装路径、启动方式、数据位置、如何删除本地数据，以及 portable mode 当前不具备严格数据隔离的事实。

**完成条件：** 新增面向普通用户的桌面启动/卸载/数据边界说明；不要暴露内部 command、package 或 artifact 标识。

### P1：Workspace 仍非完整普通用户闭环

Research 人工审核队列已经是实体页面，但 Knowledge、Learning、Machine Knowledge 等多个导航区仍缺少面向普通用户的投影与动作契约。现阶段不得以“桌面壳可启动”宣称完整产品闭环或公开 release。

## 非产品阻塞项

从 Git-Bash 经 `cmd.exe start` 启动带空格路径的 portable `.exe` 返回“拒绝访问”；改用 PowerShell `Start-Process` 后程序正常启动。这是本机 Git-Bash/`cmd start` 调用链问题，不是 Tauri release executable 的启动失败。未来的用户启动器不得依赖该 Git-Bash 调用方式。

## 推荐下一 TaskPack（依赖有序）

1. 先为 strict portable mode 定义 runtime resolution 合同与 fail-closed 测试。
2. 实现 data root 选择，并对 default install 与 portable copy 分别测试。
3. 以 release copy 运行真实桌面外壳，验证 bundled Python、listener、Workspace 200、退出后子进程清理、数据目录边界。
4. 写入桌面用户说明与已知限制。
5. 将 Workspace 的下一个真实用户生命周期页面接入无内部 ID 投影；保持 candidate/review 治理边界。
