# 页面 08：连接管理与系统控制

## 参考图

`references/screens/08_connection_system.png`

## 目标

统一管理模型、MCP、GitHub、本地目录、浏览器、Skills、用量和系统健康。

## 分区

- 本地模式；
- 模型提供商；
- MCP；
- GitHub；
- Local Folder；
- Browser；
- Skills；
- Usage；
- System Health；
- 右侧 Connection Detail。

## 安全要求

- 不显示完整 API Key；
- 不返回真实绝对路径，除非本地设置页有明确权限；
- 文件夹使用用户可理解别名；
- Disconnect / Revoke 必须二次确认；
- 模型和连接状态来自真实 Adapter；
- 当前未实现时显示 Planned。
