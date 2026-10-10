# ArcheAxis Knowledge — 正式 Tauri 2 宿主

本目录与 `frontend/` 是 SUP-022 的正式宿主。先读 [AUTHORITY](../AUTHORITY.md)、[当前架构](../docs/architecture/CURRENT_ARCHITECTURE.md)、[运行交付索引](../docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md) 与 [活动指针](../docs/current/AAOS-ACTIVE-EXECUTION.json)。产品执行目前暂停，源码存在不等于已安装验收。

`src/main.rs` 复用 `desktop/src-tauri/` 生命周期与有限 HostAdapter 桥；宿主监督 Rust Core，SQLite/CAS 的正典业务写入只在 Core。Python workers由Core隔离调度。旧FastAPI/8000拓扑是历史兼容参考，不能从本目录恢复为正式后端。

正式构建入口：`npm --prefix frontend run tauri -- build --no-bundle`。前端构建为 `npm --prefix frontend run build`；路径由 `scripts/runtime/frontend.mjs` 与 `scripts/runtime/dev.py` 分配到独立 `.project-local/runs/`。裸Tauri构建不能使用历史共享dist。

工具链位置与版本动态读取 [共享资源索引](../docs/SHARED_RESOURCE_PATH_INDEX.md)、锁文件与实际环境；不沿用旧README的机器路径、版本或冒烟结果。安装/发布/Green替换需相应Owner授权，本地build不等于runtime或exact-SHA CI。
