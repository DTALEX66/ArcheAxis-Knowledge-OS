# 当前系统边界 · ArcheAxis Knowledge

本页解释当前项目合同；规范要求以 [PROJECT_CONTRACT](../PROJECT_CONTRACT.yaml)、[语言权威](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) 与 SUP-022为准。任务与暂停状态读 [活动指针](current/AAOS-ACTIVE-EXECUTION.json)；文档身份读 [路径路由](current/AAOS-AUTHORITY-ROUTES.json)。

- 正式宿主为 `frontend/` React/TypeScript/Vite 与 `src-tauri/` Tauri 2，复用 `desktop/` 生命周期。Avalonia为冻结供体；旧FastAPI、旧六空间和旧Release不能定义当前产品。
- Rust Core是SQLite/CAS唯一正典业务写者；界面和隔离Python workers不能直写业务库。
- 普通内容先保存，权限、结构及完整性检查保留；识别忠实度与专业依据独立，人工认可属于专用工作流，保存不等于知识已证实。
- WORK-LAB与DESIGN-LAB独立，不合仓、不共享业务数据库，不是运行时前置；受控版本化交换仍需来源、授权、用途和撤回边界。
- 产品执行PAUSED_BY_OWNER、整体PARTIAL；当前仅治理维护。V01暂停、FT01–04冻结；六项核心能力增量冻结，不自动执行。
- 本地测试、模拟/合成/真实证据、exact-SHA云端CI、安装态、Owner验收及Release各自记账，互不替代。实际结果见当前UI执行记录与分域回执。

本页旧v0.6.8正文已按 [原字节](history/authority-repair-20261010/SYSTEM_BOUNDARY-before-repair.md) 保存；其中旧Avalonia正式壳及Release断言只对原时点有效。
