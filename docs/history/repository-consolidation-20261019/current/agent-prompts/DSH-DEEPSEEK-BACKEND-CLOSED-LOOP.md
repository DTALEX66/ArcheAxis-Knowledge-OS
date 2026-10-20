# 可直接交给 DSH / DeepSeek 的任务提示词：AAOS 真实多格式闭环

你接手 **ArcheAxis Knowledge / 星环知识平台** 后端全链路实施。**人类学习、机器学习、两者相互学习成长是同等重要的长期产品主体**；M0 只安排近期实施顺序，不得删减三者的领域模型、接口合同、路线图或未来能力。请直接推进可验证工作，不把任务停在报告；也不要把任务包、编译成功、模拟数据或一次 Desktop/Core 握手记为整条产品闭环完成。

## 目标与顺序

在**独立新分支**上，完成当前 R6 + M0 所定义的最短、同时尽可能完整的真实多格式闭环：真实输入 → 插件/适配器 → Canonical Source → Canonical Knowledge → Personal Knowledge → Search → Learning Plan / Course / Learning Artifact → 真人学习 → Assessment → Mastery / FSRS → 机器使用同一 Knowledge → Evaluation → 真实错误 → 人审 Correction → Retest → 重启回读 → 隔离测试资源的 Backup / Restore → Local Green 候选验证。产品正式 UI 优先、轻量治理其次，后端工作可与 UI 的接口合同并行，但同一文件仅一个 writer。M0 的真实 Legacy copy migration、原位替换和发布涉及用户已暂停的数据库迁移或 Owner Gate，**不得执行或假装通过**；其余闭环继续完成，并精确列出无法闭合的门。

## 先读当前真值

工作目录 `D:/All projects/ArcheAxis-Knowledge-OS`；原绿色版 `D:/All projects/ArcheAxis.Knowledge.Green-x64`。先动态读取本地 `git status --short`、HEAD、分支、远端 `main`/UI 分支精确 SHA、Git 工作树及当前 CI；不得沿用提示词中的历史 SHA。按顺序读取 `AGENTS.md`、根 [`AUTHORITY.md`](../../../AUTHORITY.md)、`docs/DOCUMENTATION_AUTHORITY_INDEX.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml`、`docs/authority/taskpack-0919-r6/EXECUTOR-START.md`、`TASKS.json`、`TASKPACK.md`、`docs/current/R6-STATE.json`、`R6-EXECUTION.md`、`M0-DIRECTION-OVERRIDE-20260920.md`。本提示词 2026-10-01 成文时根 `AUTHORITY.md` 确实不存在，当时要求"若不存在则明确记录 `AUTHORITY_REFERENCE_MISSING`"——该写法保留为历史口径；2026-10-08 复核根 `AUTHORITY.md` 已存在并是导航入口，当前执行者从它按 §5 权威顺序进入，仍不要从旧包重建权威。

接着读 `docs/current/AAOS-EXECUTION-PACKET-20261001.md`、`AAOS-UNFINISHED-TASKS-20261001.md` 和 `AAOS-ALL-TASKS-DISPOSITION-20261001.csv` 的 `BACKEND_FRONTEND_LOOP`、`OWNER_GATE` 行；只按相关 key 读取 `AAOS-ALL-TASKS-LEDGER-20261001.json` 的原要求与验收，以及 `AAOS-ERRORS-BLOCKERS-20261001.md`、`AAOS-UI-BACKEND-MAP-20261001.md`。9/28 与 9/30 原任务包的项目内副本在 `docs/history/external-taskpacks/2026-10-01/`；9/29 规划和 10/1 生态资料在对应 `docs/history/`，是历史/提案/证据输入，不自动覆盖当前 Authority。真实后端交接附件在 `C:/Users/ALEX/.codex/attachments/94f7489e-e267-4906-8fff-7a9c2689a11f/已粘贴的文本.txt`，只读任务相关部分，不复制私人状态。

## 分支与写入边界

先读 `docs/current/AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md`：Green 下存在独立克隆和同仓库工作树，不是已验证安装。分支/仓库目录清理由 GC-01..05 单列轻量治理：先审独有修改、引用、索引、回退，再逐 exact path/ref 处置；不得借后端任务删除数据、缓存、历史文档或恢复包。你的隔离后端树不应新增到 Green 运行根，最终只提交经过验收的后端运行构建物。

**责任边界**：你负责全后端与端到端真实闭环。确需改动前端时，只改为验证真实协议所必需的适配、状态或调用代码，并与 MiniMax 的 UI 文件写集隔离；不承担页面视觉、布局、图标、主题与动效设计。历史后端及跨端开源池按总账原 key 逐项审查版本、许可证、维护状态、数据边界和替代成本，合法可用的依赖/SDK/API/CLI/Adapter 优先吸收；记录采用/拒绝理由、锁定版本和回退，不能把历史候选视为已集成。

确认远端 `main` 后新建独立分支，建议 `codex/dsh-aaos-real-multiformat-loop-20261001`；若已存在，加唯一后缀，不强制覆盖。保护正式根的未知 dirty/untracked，必要时用独立工作树；不得 reset/clean/stash 用户修改来方便执行。UI 当前分支 `codex/aaos-ui-phase2-20261001` 由另一 writer 负责；你写 Core、适配器、API 合同及对应测试，UI 差额以合同/交接传递，不在并行分支争写。分支创建、push、PR、merge 均须真实执行后 readback；软件无 Git 能力时报告能力缺口，不假称已做。使用 DSH 软件**当前自己的**模型、provider、reasoning、认证与许可，不硬编码/改全局设置。

禁止访问 E/F 盘；不得读取或上传凭据、私人会话、用户数据库、真实工作区。清理任务已停止：不删除、迁移、重排缓存、历史文档、数据库、恢复包。开发输出只按项目规范写入 `.project-local/`；不把运行数据/日志/虚拟环境提交。对外依赖先核官方来源、版本、许可证、lockfile、可回退方式，不为补功能全局安装或启用未授权付费调用。

## P0–P6 可验收实施

1. **P0 Authority / Plugin Kernel**：确认 Rust canonical writer 和唯一资源路径；真实启停、默认/fallback、health、替换与错误回执。只接当前闭环必需能力。
2. **P1 Source / Format / Knowledge**：用合法且可追溯的代表性真实文本、PDF、Office、HTML、图片、音频、视频、Canvas 输入；按当前已支持引擎验证摄取、转换、OCR/ASR（适用时）、来源、原件 hash、格式损失、fallback、失败重试、Knowledge V3 写入/读取与引用。某格式缺实际引擎或合法输入就写 `BLOCKED/UNVERIFIED`，不以假 fixture 冒充 REAL。
3. **P2 Search / Learning Plan / Course**：验证词法检索并完成当前计划所需的 embedding/reranker 有界降级；把真实 Knowledge Component、Prerequisite、Objective、CourseManifest 与第一种实际 renderer 串起来。没有提供方时让 UI 收到准确不可用状态。
4. **P3 Human Learning**：真实用户从已接受/个人 Knowledge 进入学习、Assessment、答案、Review、Mastery/FSRS；核幂等、版本绑定、负例和进程冷重启后状态。合成通过不能代替真人首用。
5. **P4 Machine Loop**：机器使用同一 Knowledge 版本执行真实任务；捕获真实错误、评估、人审 Correction、复用 Retest 和回执，再冷重启读回。没有真实模型/授权时标 `BLOCKED`，不得用模板答案宣布闭环。
6. **P5/P6 Persistence / Local Green**：在隔离测试资源做 Backup / Verify / Restore、完整状态重启和回滚演练；组装同一 SHA 的 Green 候选并跑原生 Desktop/Core 全链路。真实 Legacy 数据迁移、原位替换、Release/tag/版本发布保持暂停或 Owner Gate，结论只能是 `LOCAL_GREEN_READY_FOR_OWNER_REVIEW`（所有门满足时）或 `NOT_READY`。

## 与正式前端的合同

把 Source、Transform、Evidence、Knowledge、Human Learning、Machine Learning、双向纠错/复测与成长、Jobs、Backup 的实际生产 HTTP 路由、请求/响应样本、对象 ID、权限、幂等/冲突、分页与版本语义写入版本化合同。明确 `loading / empty / error / offline / permission / conflict / unavailable`，由 UI 分支按该合同连接；不在桌面造第二写入路径，不把示例 KPI/图谱节点/模型健康伪装为 Core 数据。Desktop/dotnet 崩溃以实际进程日志、stderr、Windows 事件与堆栈定位，`0xe0434352` 只是一条症状。

## 验收、上传和最终报告

按每个 CSV key 更新原有 R6/M0 账本的真实状态，附源码 SHA、输入来源、命令、日志/回执、失败路径、重启结果和证据等级 `NO_EVIDENCE / SIMULATED / SYNTHETIC / INTEGRATED / REAL`；不得把 `UNKNOWN` 写成 `PASS`。先跑定向回归，再跑项目规范的受影响模块和最终门禁；失败、取消、required skip 均不算 PASS。提交仅任务所属公共文件，推送新分支并创建 Draft PR；回读远端精确 SHA 与该 SHA CI，不因 push/PR/编译解除 R6 release 冻结。交付：分支与 PR、完整/部分闭环矩阵、生产 API 合同、真实格式与人机纠错证据、Desktop/Green 实际启动路径（若验证过）、未闭合 Owner/环境阻塞、回滚步骤。你无法实际执行的动作必须写 `NOT_EXECUTED`，不能写成计划已完成。

节省 token：先读索引和本队列 key；每轮只打开相关源码、合同、测试和日志片段，用文件路径+行号/SHA 引用大包，不在上下文反复粘贴 270 行总账或完整 ZIP。持续推进有真实证据的下一项独立任务。
