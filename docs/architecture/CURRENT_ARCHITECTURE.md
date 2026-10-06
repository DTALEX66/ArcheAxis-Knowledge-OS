# 当前架构职责 — R6 / M0 / SUP-022

> 2026-10-04 SUP-022 正式宿主重构增量；2026-09-27 的源码核对基线保留于历史回执。
> 当前执行由 [AAOS-01](../authority/taskpack-1004-aaos01/01_完整执行任务书.md)、SUP-022、PROJECT_CONTRACT.yaml 的 content_policy 和 [语言权威](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) 定义；R6/M0 的继承约束与历史回执保留。本页不签发真实 M0、安装态或 Local Green 完成证明。

## 正式拓扑

```text
React/TypeScript/Vite UI -> finite Tauri 2 / Rust host bridge
  -> authenticated loopback HTTP -> Rust Core API
       -> application/domain -> single-writer SQLite vNext workspace
       -> bounded child-process protocol -> isolated Python capabilities
```

正式链路不经过 legacy FastAPI 网关，不与旧数据库双写。桌面只承载 UI 与 Supervisor，不直接操作主数据库。Rust 负责领域规则、权威状态和写入；Python 承担解析、OCR、ASR、模型和学习调度计算。

## 生命周期与身份

[Tauri 宿主](../../src-tauri/src/main.rs) 与 [生命周期实现](../../desktop/src-tauri/src/backend.rs) 持有自有 Core 子进程，以端口 `0` 请求分配 loopback 端口，通过继承 stdin 传入 `archeaxis.desktop-launch/v2` 载荷。[有限业务桥](../../src-tauri/src/core_bridge.rs) 将 UI 命令映射到明确的 Core 操作，不提供任意 URL、SQL、文件路径或 Shell。独立 human/machine 凭据、会话身份及可选 worker profile 都有明确边界；凭据仅由 Rust 宿主受控内存持有，不属于公开收据或前端状态。

桌面核对 readiness 地址和 `/api/v1/system/version` 的协议、角色、会话及工作区身份。Rust [启动入口](../../crates/archeaxis-api/src/main.rs) 绑定 `127.0.0.1`；[launch 认证](../../crates/archeaxis-api/src/launch.rs) 使用 `x-archeaxis-launch-token`，拒绝无效/重复凭据与浏览器 `Origin`，覆盖客户端自报 actor。业务端点继续执行领域权限检查，loopback 本身不是认证。

## 写入和计算

- [API](../../crates/archeaxis-api/src/lib.rs) 提供路由，`archeaxis-application` 编排，`archeaxis-domain` 承载领域逻辑。
- [Store / WriterActor](../../crates/archeaxis-store-sqlite/src/writer.rs) 持有工作区锁，由单线程拥有 SQLite 连接、有界队列串行处理数据库操作。能力 Executor 的 worker transport 在外部编排；不能据此声称所有子进程等待都已移出写线程。当前 review 路由在 `with_store` / `record_review_with_state_and_answer` 回调内同步等待 FSRS 子进程，仍会占用 writer，是已知的并发/延迟限制。维护和迁移使用各自的受控入口。
- [能力执行器](../../crates/archeaxis-application/src/executor.rs) 与 [worker 消息验证](../../crates/archeaxis-sidecar-protocol/src/worker.rs) 限制进程与消息边界；Rust 校验响应和输出后提交状态。Python workers 不持有主库写入权，也不能授予人工审批。
- [FSRS 适配器](../../crates/archeaxis-application/src/scheduler.rs) 调用 [worker_schedule.py](../../services/python-workers/learning/worker_schedule.py) 的单请求 JSON stdin/stdout 协议；缺失 worker 时明确报错，不以临时间隔算法冒充成功。
- [跨语言合同](../../packages/contracts/) 约束实际输入输出。Schema 不替代身份、权限、路径或跨字段校验；进程与协议隔离也不等于 OS sandbox。

## 内容保存、证据与 AI 使用原则

本节解释 [PROJECT_CONTRACT.yaml 的 content_policy](../../PROJECT_CONTRACT.yaml) 规范；对应 Schema 是正式校验合同。这些是产品必须遵循的要求，不能由文档声明推定功能已实现或验收通过，进度与缺口仍登记在既有 current 台账。

证据有两种独立用途：识别忠实度核验，将原件与本地提取结果比较；专业支持核验，将主张与支持材料、反证比较。忠实提取不等于原文事实正确，专业支持不足也不抹去忠实识别结果。来源、原件、修订与位置另行保留，以便追溯。不确定、冲突、假设与待核实状态必须可保留和呈现。

普通内容保存不因没有外部 Source/Evidence、未云端核验、核验失败或存在疑点、缺少支持、尚未真人复核而拒绝；这不禁止 Core 自动创建内部来源身份。权限、结构和数据完整性校验仍必须执行；保存不自动赋予真人认可或事实可信状态。UI 不强制外部来源/证据表单，也不等待云端结果才完成普通保存。

保留原件、原始计算与检索结果、实际位置和对应来源版本以及版本历史，不用后来的核验结论覆盖原始事实。云端原件识别、搜索与事实核验分别记录；判断必须以原件为基础，搜索无结果不代表原文错误，网上答案不得覆盖原文。允许不确定与冲突。未配置或调用失败明确记录为待配置/可重试失败，不能伪造成功、证据或确定结论。

AI 使用应展示输入内容的状态和依据。允许探索假设与未经核实的材料；涉及严格依据的任务，按该任务场景筛选合适材料，不能把普通保存限制为已经核验的事实。继续复用现有正式 Tauri 有限桥、Rust Core 单写者与隔离 Python workers，不因这些原则新建另一套领域、数据库或默认客户端。

## Legacy 与迁移

`frontend/` 与 `src-tauri/` 是 SUP-022 正式宿主的源码路径。`apps/ArcheAxis.Desktop/` 保留为 Avalonia 行为与恢复供体参考；目录登记不等于安装态接管或 Owner 验收。`app/`、`shared/`、`knowledge_base/`、`inspiration_research/` 为兼容、恢复与迁移供体，保留其原数据库所有权。现有 Green v0.6.14 不被本次重构覆盖，`desktop/` 仍是独立恢复入口，其被正式宿主复用的生命周期源码继续保留。

旧 FastAPI/Facade 拓扑的[完整原文](../history/architecture/CURRENT_ARCHITECTURE-before-R6-reconciliation-20260927.md)按原字节保留，历史标题和“当前”措辞只对原快照有效。迁移验收以 R6 A13 / M0 P5 的非空 legacy-copy、staging、差异损失核对和重启读回为准；发布及 Green 替换另受 Owner Gate 约束。

开发输出通过 `scripts/runtime/dev.py` 写入 canonical `.project-local/`。产品工作区和用户数据独立；AAOS-01 当前运行状态见 [唯一现行台账](../current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)及其证据；R6 状态保留其历史范围，而非本页架构图。
