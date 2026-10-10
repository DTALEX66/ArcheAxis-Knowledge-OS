# 当前 Agent 接手入口 · 2026-10-10

先读 [根权威入口](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[项目合同](../../PROJECT_CONTRACT.yaml)、[文档权威索引](../DOCUMENTATION_AUTHORITY_INDEX.md) 和 [路径身份路由](AAOS-AUTHORITY-ROUTES.json)。这些是仓库公开入口，适用于遵循项目规则的本地/云端软件与模型；不依赖私人配置。

## 当前任务与停止边界

[活动指针](AAOS-ACTIVE-EXECUTION.json) 是任务路由；来源为 `docs/taskpacks/aaos-ui-first-20261009/`，实际进度读 [UI执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md) 和其分域回执。产品执行 **PAUSED_BY_OWNER**，整体 **PARTIAL**；不把 selected_tasks 或历史“下一队列”视为恢复指令。当前仅执行 Owner 明确要求的资料归档及权威/引用治理维护。V01暂停；FT01–04冻结；安装、发布和Green替换未授权。

六项核心能力对话增量已 [归档冻结](../history/conversation-summary-20261010/INDEX.md)：**FROZEN_BY_OWNER / NOT_EXECUTED**，不加入当前队列。其旧AAOS-01活动队列措辞、旧源码基线、48项测试提案和包内执行提示词均不是当前授权。

## 不变的产品规则

正式 `frontend/` + `src-tauri/`，Tauri 2 + React/TypeScript/Vite；Rust Core唯一SQLite/CAS业务写者，Python worker隔离。Avalonia是冻结供体，旧FastAPI不成为正式后端。普通内容先保存，权限/结构/完整性仍检查；识别忠实度与专业依据独立，人工认可属专门流程。

新布局/架构按UI优先包，blueprint默认，blueprint-light与black/white/cosmic可切换；所有主题共用新布局，同主题全局语义颜色一致。治理更新不改产品配色和代码。

## 当前检出、云端与证据

本轮开始主检出 `codex/Audit` 与代码检出 `.project-local/worktrees/gov-ui-20261008` 同为 `fb590dfb060e51c348dce57226a4e0bbc1e19f31`；GitHub main也经原生API核实为该SHA。它们是观察时点，不是永久事实。每次接手动态读取 branch/HEAD/status/远程ref；旧检出与旧分支仍可能保留历史源码，不能推定最新。

上次 [同步交付](AAOS-REPOSITORY-SYNC-20261010.md) 已发布；先前“源码不同、未commit/push、云端缺文件”只描述旧时点。本轮最新治理修复的发布/readback见 [修复记录](AAOS-AUTHORITY-REPAIR-20261010.md)，不能用上次发布回执证明本轮dirty已上传。

本地检查、exact-SHA云端CI、安装运行、Owner验收分别记账；required missing/failed/skipped不能写PASS。当前产品安装与M01完整资格未完成，历史通过回执绑定原时点、原SHA、REAL/SYNTHETIC/SIMULATED层级。

## 旧路径与接手行为

搜索命中旧handoff、docs/current中的dated文件、authority/taskpack、蓝图或模型总结时，先按路径身份路由分类，再回到活动指针和相应Concern索引。文件名CURRENT、旧COMPLETE与旧grant不能提升成当前规则、状态或操作授权。外部/私人路径不自动进入；本地共享资源读 [资源路径索引](../SHARED_RESOURCE_PATH_INDEX.md)，云端不照搬本机绝对路径。

原本页历史各阶段叙述按 [完整原字节](../history/authority-repair-20261010/AAOS-AGENT-HANDOFF-before-repair.md) 保留，不再与当前接手指令混排。所有历史FAIL、PARTIAL、证据SHA与原权限保持其原时点。
