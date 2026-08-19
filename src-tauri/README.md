# ArcheAxis Desktop（R5 脚手架）

- 本目录仅为 Tauri 2 桌面壳脚手架（配置 + 最小 main.rs）。
- **构建状态：BLOCKED** —— 本机未安装 Rust/cargo 工具链（2026-08-19 审计）。
- 完成条件（G1 人工门禁）：安装 Rust toolchain 后执行
  `cd src-tauri && cargo tauri build`（前端先 `npm run build --prefix frontend`）。
- 架构：桌面壳仅承载 React 构建产物 + 监督后端 FastAPI 子进程（端口 8000）；
  后端保持可独立启动（`uvicorn app.main:app`），不锁死在桌面壳内。
