# 当前架构职责 — R6 / M0

> 2026-09-27 源码职责核对，基线 `96024a2782247a3f073c5eae5aeb175f9e156ee6`。
> 当前执行由 [R6](../authority/taskpack-0919-r6/EXECUTOR-START.md)、[M0](../current/M0-DIRECTION-OVERRIDE-20260920.md) 和 [语言权威](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) 定义。本页不签发真实 M0、安装态或 Local Green 完成证明。

## 正式拓扑

```text
C#/Avalonia desktop + CoreSupervisor
  -> authenticated loopback HTTP -> Rust Core API
       -> application/domain -> single-writer SQLite vNext workspace
       -> bounded child-process protocol -> isolated Python capabilities
```

正式链路不经过 legacy FastAPI 网关，不与旧数据库双写。桌面只承载 UI 与 Supervisor，不直接操作主数据库。Rust 负责领域规则、权威状态和写入；Python 承担解析、OCR、ASR、模型和学习调度计算。

## 生命周期与身份

[CoreSupervisor](../../apps/ArcheAxis.Desktop/CoreSupervisor.cs) 持有自有 Core 子进程，以端口 `0` 请求分配 loopback 端口，通过继承 stdin 传入 `archeaxis.desktop-launch/v2` 载荷。独立 human/machine 凭据、会话身份及可选 worker profile 都有明确边界；凭据不属于公开收据。

桌面核对 readiness 地址和 `/api/v1/system/version` 的协议、角色、会话及工作区身份。Rust [启动入口](../../crates/archeaxis-api/src/main.rs) 绑定 `127.0.0.1`；[launch 认证](../../crates/archeaxis-api/src/launch.rs) 使用 `x-archeaxis-launch-token`，拒绝无效/重复凭据与浏览器 `Origin`，覆盖客户端自报 actor。业务端点继续执行领域权限检查，loopback 本身不是认证。

## 写入和计算

- [API](../../crates/archeaxis-api/src/lib.rs) 提供路由，`archeaxis-application` 编排，`archeaxis-domain` 承载领域逻辑。
- [Store / WriterActor](../../crates/archeaxis-store-sqlite/src/writer.rs) 持有工作区锁，由单线程拥有 SQLite 连接、有界队列串行处理数据库操作。能力 Executor 的 worker transport 在外部编排；不能据此声称所有子进程等待都已移出写线程。当前 review 路由在 `with_store` / `record_review_with_state_and_answer` 回调内同步等待 FSRS 子进程，仍会占用 writer，是已知的并发/延迟限制。维护和迁移使用各自的受控入口。
- [能力执行器](../../crates/archeaxis-application/src/executor.rs) 与 [worker 消息验证](../../crates/archeaxis-sidecar-protocol/src/worker.rs) 限制进程与消息边界；Rust 校验响应和输出后提交状态。Python workers 不持有主库写入权，也不能授予人工审批。
- [FSRS 适配器](../../crates/archeaxis-application/src/scheduler.rs) 调用 [worker_schedule.py](../../services/python-workers/learning/worker_schedule.py) 的单请求 JSON stdin/stdout 协议；缺失 worker 时明确报错，不以临时间隔算法冒充成功。
- [跨语言合同](../../packages/contracts/) 约束实际输入输出。Schema 不替代身份、权限、路径或跨字段校验；进程与协议隔离也不等于 OS sandbox。

## Legacy 与迁移

`app/`、`shared/`、`knowledge_base/`、`inspiration_research/` 为兼容、恢复与迁移供体，保留其原数据库所有权。`frontend/`、`src-tauri/` 和现有 Green v0.6.14 是行为/恢复参考，`desktop/` 是独立恢复入口；本次文档整合没有修改这些前端路径。

旧 FastAPI/Facade 拓扑的[完整原文](../history/architecture/CURRENT_ARCHITECTURE-before-R6-reconciliation-20260927.md)按原字节保留，历史标题和“当前”措辞只对原快照有效。迁移验收以 R6 A13 / M0 P5 的非空 legacy-copy、staging、差异损失核对和重启读回为准；发布及 Green 替换另受 Owner Gate 约束。

开发输出通过 `scripts/runtime/dev.py` 写入 canonical `.project-local/`。产品工作区和用户数据独立；真实运行状态见 [R6 状态](../current/R6-STATE.json)及其证据，而非本页架构图。
