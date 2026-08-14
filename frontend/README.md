# ArcheAxis Knowledge — Frontend（AXW-UI-801 渐进迁移）

React + TypeScript + Vite App Shell 骨架（任务包 §9.1/§10/§15.3）。

## 结构

```text
frontend/
├─ src/
│  ├─ app/            App Shell（状态栏 + 空间导航 + 检查器 + 活动坞）
│  ├─ spaces/         六大空间：Workspace / Library / Evidence / Learning / AI Assets / Settings
│  ├─ components/     共享组件（SpaceRail / StatusBar / Inspector / ActivityDock）
│  ├─ design-system/  tokens.css（紫晶主题，light/dark，reduced-motion）
│  ├─ api/            loopback API client（token 内存传递，product fail-closed）
│  ├─ runtime/        连接状态机（booting→ready/reconnecting/failed…）
│  └─ contributions/  （后续批次：插件 UI contribution 点）
├─ public/
└─ tests/             （后续批次：Vitest + Testing Library）
```

## 开发

```bash
# 本机 node 在 HERMES_HOME（PATH shim 断链时用完整路径 + 镜像源）
node "C:/Users/ALEX/AppData/Local/hermes/node/node_modules/npm/bin/npm-cli.js" \
  install --registry=https://registry.npmmirror.com
npm run dev        # 127.0.0.1:5173（loopback only）
npm run build      # tsc --noEmit && vite build → dist/
```

## 迁移路径（渐进）

1. Recovery Shell（desktop/bootstrap，已交付）→ 保持为启动/恢复层；
2. 本 App Shell 骨架（本轮）→ 后续批次接 Tauri frontendDist 与 handshake；
3. Library / Evidence / Learning / AI Assets 逐空间从旧页面路由过渡。

## 约束

- 不直接访问 SQLite；不加载任意插件网页；token 不写 localStorage；
- 六大空间为产品固定结构，第三方品牌只出现在 Adapter 设置内。
