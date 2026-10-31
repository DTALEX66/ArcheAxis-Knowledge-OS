# ArcheAxis Knowledge — 软件读取适配入口

本入口只负责加载共享规则，不维护产品状态或另授权限。
旧路径与文件身份按 `docs/current/AAOS-AUTHORITY-ROUTES.json` 解析。
当前授权、权限、监控及进度按 `docs/current/AAOS-ACTIVE-EXECUTION.json` 与其指向的决定、交接和唯一执行记录读取；历史包和旧状态不能覆盖当前Owner决定。

下方原生导入用于全文加载；普通Markdown链接只是导航。是否实际加载须在对应客户端新会话中核验，不能从文件存在推断。具体检查步骤见 `docs/history/rules-entry-repair-20261023/README.md`。

@AGENTS.md
@AUTHORITY.md
@docs/truth/CLOSED_LOOP_DEFINITION.md
