# AXW-ENV-103 — 外置目录 00-90 分区：执行记录（2026-08-15）

> 承接 dry-run plan（logs/environment-audit/move-plan-20260815.json）。本轮执行
> **低风险 7 项**；中/高风险项 hold（需环境变量/注册表更新确认）。

## 修正（2026-08-15 晚，Owner 边界澄清）

Owner 澄清外置库边界：**共用库只放工具链/依赖本体**（node/python/rust/msvc/
ffmpeg/tesseract/playwright/模型权重/共用缓存）；**构建产物、下载缓存、审计日志、
运行数据一律留在项目自己的 `.hermes/task-runtime/`**。据此把下面 5 项构建产物从
共用库迁回本项目 `.hermes/task-runtime/`：

| 共用库原位置 → 项目位置 | 体积 |
|---|---|
| 80-build/portable-staging → `.hermes/task-runtime/build-staging/` | 357 MB |
| 20-runtimes/desktop-runtime-v1 → `.hermes/task-runtime/desktop-runtime-v1/` | 349 MB |
| 60-cache/downloads → `.hermes/task-runtime/downloads/` | 12 MB |
| logs/environment-audit → `.hermes/task-runtime/environment-audit/` | <1 MB |
| .hermes/task-runtime → `.hermes/task-runtime/shared-lib-runtime/` | 4 MB |

共用库相应分区（20-runtimes/60-cache/80-build）保留为空，仅工具链/依赖本体留存。
外置库 **不上传**（保持本地）。

## 已执行（7 项 low-risk move，~13.5 GB）

| 源 → 目标 | 验证 |
|---|---|
| toolchains/scoop → 10-toolchains/scoop | ✅ 目录到位 |
| toolchains/02a-python-runtime → 10-toolchains/python | ✅ |
| toolchains/playwright → 10-toolchains/playwright | ✅ |
| toolchains/vs-build-tools → 10-toolchains/msvc | ✅ |
| toolchains/downloads → 60-cache/downloads | ✅ |
| runtimes/desktop-runtime-v1 → 20-runtimes/desktop-runtime-v1 | ✅ |
| archives/portable-archeaxis → 80-build/portable-staging | ✅ |

**回滚清单**：`logs/environment-audit/rollback-20260815.json`（逐项 from→to）。

## 引用同步

- `scripts/Enter-ArcheAxisDev.ps1`：5 处旧路径引用已更新（10-toolchains/scoop、
  tesseract-languages、shims、10-toolchains/python、10-toolchains/playwright）。
- 外置仓未自动 commit（技能规则：全局配置仓不自动提交——留给用户确认）。

## Hold（未执行，需确认）

| 项 | 风险 | 原因 |
|---|---|---|
| toolchains/rust | medium | rustup 内部工具链路径（toolchains/1.88.0-...）——移动需 rustup 重新配置 |
| uv-cache | medium | UV_CACHE_DIR 环境变量指向旧路径——移动后需同步环境变量 |
| wsl2 | medium | WSL 发行版注册表绑定旧路径——移动可能断 WSL |
| ArcheAxis-Knowledge-OS-ci-venv | high | CI venv 引用（解释器路径写死） |
| manifests/scoopfile.json | low | 待并入 00-registry（内容确认后） |

## 验证

- 移动后：uv 0.12.0 正常；项目 pytest 快速回归 14 passed 无断裂；
- 本机关键工具（tesseract 语言包/playwright 浏览器）经 ps1 引用同步后路径有效。

## 剩余风险

- rust/uv-cache/wsl2 移动需先在环境变量/注册表层面确认引用点，再执行（下一步）；
- scoop 的 shims 引用（用户目录 C:\Users\ALEX\scoop\shims）不受本体移动影响（shim 本来断链——node/npm 用 HERMES_HOME）。
