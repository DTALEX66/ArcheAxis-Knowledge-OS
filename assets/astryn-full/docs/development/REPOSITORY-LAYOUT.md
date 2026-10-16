# 目录规范

这些是责任边界，不预设 npm workspace、独立进程或数据库。实际实现根据宿主合同收敛。

| 目录 | 内容 |
| --- | --- |
| docs/authority | 权威导航、路径登记、决策 |
| docs/tasks/archive | 原始任务与完整性收据，保留原文 |
| docs/current | 当前执行状态和接续入口 |
| docs/architecture | 架构与能力归属 |
| docs/research | 官方来源、版本、许可证及吸收矩阵 |
| docs/development | 启动、依赖与开发规范 |
| docs/verification | 可提交的脱敏验证报告 |
| contracts | Host、会话、记忆、动作、上下文及渲染契约 |
| src | 角色、交互、渲染和可复用 UI 源码 |
| tests | 契约与行为回归；夹具明确 SYNTHETIC |
| dev-host | 隔离开发宿主，不是第二个正式产品 |
| scripts | 仓库级开发工具（如门禁回执记录器）；不属于产品运行时，因此不在敏感面扫描范围内 |
| assets/original | 原创角色素材及来源 |
| assets/third-party | 获准第三方素材及许可记录，不放权重 |
| .project-local/runs | 本地执行日志、缓存、临时环境 |
| .project-local/artifacts | 本地产物、截图和构建输出 |

空的可追踪目录用 .gitkeep 保留，不表示功能已实现。运行数据不得写入源码或文档目录。首次引入依赖前确认版本、官方来源、scope、lockfile 和回退方案。
