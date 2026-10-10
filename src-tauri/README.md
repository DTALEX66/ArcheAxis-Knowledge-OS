# ArcheAxis Desktop（R5 脚手架）

- 本目录仅为 Tauri 2 桌面壳脚手架（配置 + 最小 main.rs）。
- **工具链（2026-08-19 复查，共用库已具备）**：
  - Rust 1.97.1 + MSVC target：D:/All projects/OS External Configuration/toolchains/rust/cargo/bin
  - MSVC 编译器 14.44 + Windows SDK 10：D:/All projects/OS External Configuration/10-toolchains/msvc
  - rustup toolchains（共享）：D:/All projects/OS External Configuration/10-toolchains/rustup
  - 注：之前 Get-Command 找不到是因 PATH 残留旧名目录（OS configuration 缺 External）
- 构建：`cmd /c vcvars64.bat && cargo build`（用 stable-x86_64-pc-windows-msvc）；
  正式候选使用 `npm --prefix frontend run tauri -- build --no-bundle`；默认前端入口为 `npm --prefix frontend run build`。两者按 `dev.py` 分配 owner 下独立 run 的 `artifacts/frontend-dist`，Tauri hook 在父构建 run 中生成嵌入资源。裸 Tauri 构建未携带路由时拒绝，不能消费历史共享路径。
- **状态（2026-08-19）**：debug 构建成功（11.7MB）+ 启动冒烟通过；release 构建成功（7.9MB，
  1m47s）；安装包（NSIS/MSI）需 @tauri-apps/cli，属 R6。
- 架构：桌面壳仅承载 React 构建产物 + 监督后端 FastAPI 子进程（端口 8000）；
  后端保持可独立启动（`uvicorn app.main:app`），不锁死在桌面壳内。
