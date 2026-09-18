# ArcheAxis 任务包审计、定位与前端执行记录

日期：2026-07-28
项目：`DTALEX66/Cognitive-Loop-OS`
当前分支：`feat/archeaxis-desktop-a1-violet-core`
当前 HEAD：`f1702990f808da1074a4aac461b24e6268ec9ec7`

## 输入包与边界

| 包 | SHA-256 | 解包位置 | 结论 |
|---|---|---|---|
| `ArcheAxis_Desktop_Cloud_Reaudit_Modification_Pack_v1.0-3.zip` | `6c60bde6405a0d54e0516525ceecbaf3fb3f186cc548475fd15804f460433e76` | `.hermes/task-runtime/pack-inspection/desktop-reaudit-v1.0-3/` | 旧 A1/A2/A3 桌面融合规格；作为设计参考，不覆盖今日最终定位 |
| `ArcheAxis_Today_Conversation_Archive_HERMES_TaskPack_2026-07-28_v1.0-2.zip` | `65bd1b3359d4d2e7ba5ef9c43cd4f3156fdf4119cf5d357ebcd255991f9100f3` | `.hermes/task-runtime/pack-inspection/today-archive-v1.0-2/` | 最新定位、决策、技术栈、配置和分阶段任务包；对冲突设计具有优先级 |

附件仅作规格和路线输入；没有把 prototype、旧 deliverable 或参考图片覆盖进运行时。

## 已吸收的稳定原则

- 保留 Python/FastAPI/SQLite/Tauri 真相链；A1 不改 schema、迁移、Research/Knowledge 核心持久化或 Tauri 安全边界。
- 普通用户从资料 URL/文件进入，不填写 command/package/job/artifact 等内部 ID。
- UI 数字、状态、能力和活动必须来自真实 API；没有后端合同就显示 Planned/Unavailable，不制作假 Agent、模型、Token、成本或进度。
- 保留 Source、Claim、Evidence、Permission、Trace、Evaluation、Lesson、Candidate/Approved、Job/Outbox/Receipt 等 Cognitive-Loop-OS 专有治理概念。
- A1 只做桌面壳、导航、真实状态投影、Inspector/Activity Dock 和可验证交互；A2 再做公开任务投影，A3 再做 Canvas/Replay。
- 浏览器、Tauri backend、Tauri WebView 点击证据必须分开记录。

## 冲突与决策

### 主题

Desktop Reaudit A1 规格将 Violet Core 作为默认主题；最新 Today Archive 的 `target-configuration.yaml` 与 decision register 则冻结为 Apple-light 默认、Violet Core 暗色主题。

**决策：**以最新 Today Archive 为准：默认主题切换为 Apple-light，同时保留 Violet Core、曜金和深空的显式用户选择和 localStorage 持久化。真实 Chromium smoke 覆盖无历史偏好默认、Apple-light 与 Violet Core 双向切换。

### 产品中心

Desktop Reaudit A1 偏统一 Agent Desktop；Today Archive 将 Agent 降为 AI 使用层，主线改为总览、资料、研究、知识、学习。

**决策：**不创建伪造的资料库或 Agent Center 页面。A1 只保留已具备真实合同的入口和 Planned 状态；后续页面必须按 Today TaskPack 的资料→研究→知识→学习顺序，以真实 API 合同独立交付。

## 当前代码确认的前端缺口

1. 主题只有 Violet Core/曜金/深空，没有 Apple-light；
2. 一级/二级导航已存在，但 `available/partial/planned/blocked` 没有可见状态投影；
3. 导入成功只触发总览刷新，活动坞和任务/投递投影依赖轮询，缺少同一动作后的即时 readback；
4. `app.js` 有两个 document click listener，动作分发可维护性较差；
5. A0 smoke 尚未断言 Apple-light、导航状态和导入后活动坞即时收敛。

## 前端优先执行路线

### Slice F1：真实主题与状态投影

- 增加 Apple-light 主题 token 和主题按钮；
- 保留旧 `aa-theme` localStorage 值的安全回退；
- 为 Rail/二级导航渲染 `available/partial/planned/blocked` 状态，不改变后端合同；
- Planned 状态继续不可执行，不增加假按钮。

### Slice F2：导入后同案例即时回读

- intake 成功后立即刷新 status、activity dock 和 runtime projections；
- 保持失败/部分响应 fail-closed；
- 不向普通页面返回内部 ID。

### Slice F3：验收

- 更新真实 Chromium smoke：主题切换/刷新、导航状态、导入后即时投影；
- 运行 JS 语法、架构、convention、定向 Workspace 测试和项目数据边界检查；
- 再决定是否进入 A2，不在本轮创建 Task Detail/Canvas/Replay API。

## 不纳入本轮

- React/TypeScript/Vite 重写；
- Apple/OpenHuman 品牌资产、外部字体、CDN；
- 多 Agent、Worker、SSE、通用 Planner；
- A2 public task reference/detail/capabilities；
- A3 Canvas/Replay；
- 数据库 schema、迁移、Tauri Rust 和 release capability 语义变化。

## 本轮实施结果

- `app/workspace/ui/index.html`：增加可切换的 `浅色` 入口，并将首屏默认主题设为 `apple-light`。
- `app/workspace/ui/assets/styles.css`：增加 Apple-light token、桌面/小屏适配和导航状态标签/状态点样式。
- `app/workspace/ui/assets/app.js`：增加路由状态投影；主题白名单包含 Apple-light；导入成功后立即刷新 Status、Activity Dock 和当前 Runtime；Activity Dock 对 Research response 做 v1 schema fail-closed 校验。
- `scripts/a0_browser_smoke.py`：增加主题切换、规划中入口状态和导入后 Activity Dock 请求的真实 Chromium 断言。

## 实际验证

- `python -m pytest tests/test_workspace_api.py tests/test_workspace_job_center.py tests/test_ci_a0_gates.py -q`：`32 passed, 1 warning`。
- `python scripts/a0_browser_smoke.py`（全新项目内隔离数据目录）：`A0 Chromium browser smoke passed`。
- `python scripts/check_architecture.py`：`architecture guard passed`。
- `node --check app/workspace/ui/assets/app.js`：通过。
- `python -m py_compile scripts/a0_browser_smoke.py`：通过。
- `git diff --check`：通过。

全量 `python -m pytest tests/ -q --tb=short` 在当前 Hermes 环境返回 `962 passed, 29 failed, 6 skipped`；失败集中于未安装的 `markitdown`、`apscheduler`、`sqlite_vec`、`networkx`，safe-http adapter 依赖差异、sleep-loop 环境状态和既有 429，不属于本轮前端改动的定向回归证据。该结果不被伪装为全量通过。

## Exact-SHA CI 失败修复

Run `30361028569` 对应 HEAD `f1702990f808da1074a4aac461b24e6268ec9ec7` 的所有测试、lint、wheel、Windows runtime 和 desktop-shell 门禁均通过；唯一失败为 `browser-smoke`，随后被 `a0-gates` 正确拦截。

根因是 smoke 对诊断失败场景错误断言隐藏的总览 `#capability-summary` 必须显示“能力状态/不可用”。当前前端实现只更新诊断页 `#diagnostics-summary`，这是正确的页面隔离行为；该 smoke 断言属于过时且依赖初始状态的非确定性断言。已删除跨页面断言，保留诊断页自身的 `本地状态读取失败` 断言。

修复后本地全新隔离 Chromium smoke 已通过；提交、推送与新的 exact-SHA CI 需以该提交的真实 SHA 为准。

## WSL 必要性核验

本机安装核验结果：WSL 引擎已安装，`wsl.exe --status` 显示默认版本 2；WSL 版本 `2.7.11.0`，内核 `6.18.33.2-2`。Ubuntu-24.04 已注册为默认发行版，当前状态为 `Stopped`，尚未执行首次启动的 Linux 用户初始化。发行版虚拟磁盘已落在 `D:/All projects/OS configuration/wsl2/Ubuntu-24.04/ext4.vhdx`，没有把 Ubuntu 数据放到默认用户目录。

项目路径不要求本机 WSL：GitHub workflow 的 Linux job 使用 GitHub-hosted `ubuntu-latest`；Windows runtime 与 `desktop-shell` job 使用 `windows-latest`。本机已具备 Windows 原生 Rust MSVC toolchain `1.88.0-x86_64-pc-windows-msvc`、Cargo `1.88.0`、Node `v24.18.0`、Tauri CLI `2.11.4` 和 Playwright `1.61.0`。

Windows 原生验证：

- `cargo check --locked`：通过；
- `cargo build --locked`：通过；
- `target/debug/archeaxis-desktop-shell.exe`：真实生成，`12,837,888` bytes；
- exact-SHA CI `30361028569`：`desktop-shell` 已通过，唯一失败是 browser-smoke 的旧断言。

结论：当前 Cognitive-Loop-OS/Tauri Windows 开发和构建不需要本机 WSL；但整个项目的质量门禁确实包含 Linux 验证层，当前由 GitHub-hosted `ubuntu-latest` 提供。WSL2 不是项目硬性前置依赖，而是“本机复现完整 Linux CI lane”的可选工具：如果要求离线/本地完成与 GitHub Ubuntu 同等的 Core、KB、Integration、wheel、lint 和 browser 验证，建议安装 WSL2 + Ubuntu；如果接受 push 后用 exact-SHA GitHub CI 验证，则现在不必安装。WSL2 仍不能替代 Windows 原生 Tauri/WebView2/NSIS 验证。它也不是修复本次 browser-smoke 失败的路径；若未来 Windows 原生发布构建遇到链接器或 SDK 错误，应检查 Visual Studio Build Tools/Windows SDK，而不是先安装 WSL。
