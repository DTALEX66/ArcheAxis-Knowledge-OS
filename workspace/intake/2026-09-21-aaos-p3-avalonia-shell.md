# AAOS P3 Avalonia 首用壳增量（2026-09-21）

## Scope

本记录只覆盖正式 `apps/ArcheAxis.Desktop/` 的 UI 壳收敛：首页、资料库、学习、任务、设置五个导航入口；资料库使用既有 Core `/api/v1/search` 读投影，任务和设置保留未接入 Core 读模型时的诚实空状态。它不新增数据库、Provider、Sidecar 或产品真相。

## Current local change

- `MainWindow.axaml` 增加正式产品导航、工作区标题、Learning surface 和未接入读模型的显式状态。
- 资料库搜索读取既有 `/api/v1/search`，分别显示 knowledge 与 extracted transform 结果。
- 设置面读取既有 `/api/v1/system/version`，仅展示 runtime、contract、schema_version，不复制配置。
- Learning surface 提供直接的“载入学习路径”入口，避免从左侧导航进入后无法触发既有 Core 学习流程。
- 任务面只追踪本次桌面会话创建的 job ID，使用既有 `/api/v1/jobs/{job_id}` 与 `/quality` 读取状态和质量事实；不伪造全量任务历史。
- `MainWindow.axaml.cs` 增加 UI-only section state；学习入口仍走既有 Core Assessment/review/readback 逻辑。
- `tests/test_desktop_navigation_contract.py` 增加 source-level navigation/provenance-boundary contract。

## Evidence boundary

- `P3_NAVIGATION_CONTRACT_MANUAL_PASS`：PowerShell 字面契约回读通过。
- `LIBRARY_SEARCH_STATIC_PASS`：Library `/api/v1/search` 控件、端点和响应字段静态回读通过。
- `SETTINGS_STATIC_PASS`：Settings `/api/v1/system/version` 控件、端点和响应字段静态回读通过。
- `JOBS_RECEIPT_STATIC_PASS`：Jobs 会话边界、状态/质量端点和结果字段静态回读通过。
- XAML XML parse：通过。
- C# brace balance：100/100。
- `git diff --check`：通过。
- Python pytest：`NOT_EXECUTED`，系统无 `pytest`，项目 `.venv\Scripts\python.exe` 为 uv trampoline 且返回 permission denied。
- .NET build：`NOT_EXECUTED`，当前 PATH 与约定系统路径均无 `dotnet`。
- 这些证据不等于 Avalonia GUI first-use/runtime PASS；P3、A12、M0 仍保持 partial/not-ready。

## Boundaries

未访问 E/F 盘、外置资源、Green 运行目录、凭据、私有状态或未知 `docs/history/` 未跟踪资产；未提交、推送、发布或修改安装运行时。
