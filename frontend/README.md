# ArcheAxis Knowledge — 正式 React 前端

本目录为 SUP-022 的正式 React/TypeScript/Vite 界面，与 `src-tauri/` 组成正式 Tauri 2 宿主。任务来源与停止状态从 [活动指针](../docs/current/AAOS-ACTIVE-EXECUTION.json) 读取；当前产品暂停、整体PARTIAL，实际结果见 [UI执行记录](../docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。

新布局和导航按UI优先任务包及实际接线验收；不得把早期六空间骨架视为固定产品结构。默认blueprint，blueprint-light和black/white/cosmic作为主题；五主题共用布局与组件状态，同一主题统一语义颜色。主题真值与源码以当前design-system及合同为准，治理更新不改颜色。

`src/app/` 承载Shell，`src/spaces/`承载页面，`src/components/`为组件；`src/api/`与生成DTO经有限认证桥进入Rust Core。界面不直连SQLite、不自建业务写者、不加载任意插件网页，启动令牌不存localStorage。

构建使用 `npm --prefix frontend run build`；桌面使用 `npm --prefix frontend run tauri -- build --no-bundle`。脚本将产物路由到独立 `.project-local/runs/`，不能引用旧共享dist。开发命令、测试及依赖版本从当前 `package.json`/lockfile读取；共享工具链先查 [资源路径索引](../docs/SHARED_RESOURCE_PATH_INDEX.md)，不从旧安装示例推定安装授权。

权威顺序与旧路径分类读 [AUTHORITY](../AUTHORITY.md)、[文档索引](../docs/DOCUMENTATION_AUTHORITY_INDEX.md) 和 [运行交付索引](../docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md)。测试夹具、截图、build和源码不自行证明安装态、真人验收或发布。
