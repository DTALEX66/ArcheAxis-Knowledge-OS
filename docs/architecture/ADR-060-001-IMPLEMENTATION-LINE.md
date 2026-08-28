# ADR-060-001：v0.6.0 唯一实现线

- 状态：accepted
- 日期：2026-08-20
- 决策：`frontend/` + 根 `src-tauri/` 是 v0.6.0 唯一规范 UI/桌面实现线；Python 服务由根 `app/` 和公开 `archeaxis` 入口提供。

## 迁移来源与退役条件

| 路径 | 当前角色 | 退役条件 |
| --- | --- | --- |
| `desktop/` | Supervisor、打包与生命周期逻辑的迁移来源 | 根 `src-tauri/` 实现同等 Supervisor、Recovery Shell、三形态构建与 Windows 生命周期回归后，Owner 批准删除。 |
| `OSUI/` | legacy/reference | `frontend/` 的相应空间有真实 API、浏览器回归与可访问性证据后，Owner 批准删除。 |
| `app/workspace/ui/` | removed | canonical React/Tauri 已覆盖保留工作流；旧 loopback 产品壳、资产路由和 package-data 已删除。 |
| 根静态页面 | legacy/reference | 替代路径具备等价真实功能并经 Owner 批准后，才可删除。 |

任何 legacy/reference 路径不得作为 v0.6.0 发布产物的 UI 或桌面真相来源。
