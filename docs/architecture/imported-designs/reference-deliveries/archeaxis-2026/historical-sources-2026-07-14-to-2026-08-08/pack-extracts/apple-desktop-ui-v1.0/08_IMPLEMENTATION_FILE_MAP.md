# 实施文件映射

## A1

允许修改：

- `app/workspace/ui/index.html`
- `app/workspace/ui/assets/styles.css`
- `app/workspace/ui/assets/app.js`
- `scripts/a0_browser_smoke.py`
- 直接相关 UI 测试和文档

禁止修改：

- SQLite Schema
- Research/Knowledge 持久化
- Planner
- Auth
- Safe HTTP
- Tauri 导航安全
- Release public 状态

## A2

增加真实 Dashboard、Research、Knowledge 详情时，可修改：

- Workspace router/service；
- Public projection adapters；
- UI；
- 测试；
- 必要 Contract。

## A3

任务/Agent 需要独立高风险分支：

- Public Task/Agent projections；
- Action capabilities；
- Command receipts；
- UI Mission Control；
- Tests。

## A4

Canvas/Replay：

- 只读 projection；
- Contracts/Adapters；
- UI；
- Performance tests。

## A5

Connections/System：

- Adapter status projections；
- Redaction；
- Permission；
- UI；
- Security tests。
