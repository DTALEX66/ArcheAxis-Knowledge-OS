# AAOS Desktop 页面与真实 Core 接口映射（2026-10-01）

## 范围与证据

本表按当前 `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`、`CoreSupervisor.cs`、`crates/archeaxis-api/src/lib.rs`、`runtime/mod.rs`、`main.rs` 逐项核对。此处的“已接线”仅表示 UI 有对应请求与状态处理，不表示 Green 安装态、真实用户资料或整条 M0 闭环已验收。当前读取时仓库为 `codex/Audit`，HEAD `29762818f5d25dfe5883a4ce3e07a75c118327b2`；本表不以历史交接 SHA 代替现场事实。

正式链路为 Avalonia `MainWindow` → `CoreSupervisor` 持有的 Core 子进程 → 带 human launch token 的 loopback HTTP → Rust 单写入者 vNext SQLite。Supervisor 以动态端口启动，先核对 `system/version` 的 runtime、contract、launch protocol、actor、session、workspace DB，并以 machine token 另行核验机器身份；UI 请求经 `SendAsync` 使用 human token。当前 `MainWindow` 未调用 `SendMachineAsync`。`CoreSupervisor` 限定 `/api/v1/` 路径、同源回环地址，返回前移除请求中的 token。不能把 UI 的 `created_by`、`reviewer` 等字段当作权限来源；权限由 Core 的可信身份检查决定。

## 页面—动作—接口—状态矩阵

| 页面 / 动作 | 生产 HTTP 方法与路径 | 请求与响应身份 | UI 成功 / 空 / 失败处理及缺口 |
| --- | --- | --- | --- |
| 启动、Home、Workspace、Settings | `GET /api/v1/system/version`；`GET /api/v1/workspaces/info` | Supervisor 核对 session、actor、workspace DB；页面另读 workspace 信息 | 离线/启动失败有状态文本；Home 概览来自 Core projection。握手通过只证明此 Core 身份，不能证明所有页面数据可用或 Green 已安装。 |
| Home 最近证据、Evidence Library | `GET /api/v1/evidence/anchors` | anchor、source、raw hash 与位置由 Core 返回 | 有结果显示 Core anchor；空结果显示空态；HTTP/解析失败显示错误。列表并非完整跨域 Evidence 服务。 |
| Capture Inbox 导入与转换 | `POST /api/v1/imports` → `POST /api/v1/jobs` → `POST /api/v1/jobs/:job_id/executions` → `GET /api/v1/jobs/:job_id` | 导入回执核对 `source_id`/`sha256`；job 使用本次 `job_id`；执行携 `idempotency-key` 和 `deadline_ms`，状态按 job 回读 | 接收、排队、运行、成功、失败、取消、未知分别显示；POST 接收不等于转换完成。执行路由要求启动时有效 `text_worker`。超时/异常保留已接收来源并提示刷新回执；无全历史任务列表。 |
| Capture 任务质量、输出、取消 | `GET /api/v1/jobs/:job_id/quality`；`GET /api/v1/jobs/:job_id/outputs/:kind`；`POST /api/v1/jobs/:job_id/executions/:request_id/cancel` | 输出前后核对最新 job 的 `job_id`、`state`、`request_id`、`attempt`；取消针对所选 request ID | 输出缺失与 HTTP 错误不显示为成功；取消只显示信号已请求，最终状态仍待 job 回读。quality 是汇总投影，不能代替 typed loss receipt。 |
| Source Reader / 来源关联 Candidate | `GET /api/v1/sources/:source_id/members`；`GET /api/v1/sources/:source_id/jobs`；`GET /api/v1/sources/:source_id/jobs/:job_id/transform`；`POST /api/v1/knowledge-items/from-transform` | 创建请求携 `source_id`、`job_id`、`transform_id`、UTF-16 选区与 quote；核对返回知识、anchor、source/job、raw hash | 仅在 Core 校验当前持久 transform 与选区后创建待审核 Candidate；权限拒绝与源身份变化单独显示。当前不是通用原文编辑器或任意内容自动接受。 |
| Knowledge / Original 候选与审核 | `POST /api/v1/knowledge-items`；`GET /api/v1/knowledge-items/:id/v3`；`GET /api/v1/knowledge-items/:id/qualification`；`POST /api/v1/knowledge-items/:id/review-decisions` | 创建携 type/body/candidate/V3 owner/support/risk；review 携 action/reviewer/note；返回 ID 后重新读取 V3 和 qualification | UI 不预先改变接受状态；空、404、权限失败、HTTP 错误有状态。当前 UI 的候选表单不是带自动保存/版本历史的完整 Original Editor。 |
| Search | `GET /api/v1/search?q=…&active_only=…` | 使用 Core `count` 与 `items[]` | `count=0` 为成功空结果，离线、权限拒绝与请求失败分别显示。当前是词法搜索；没有向量、reranker 或图谱检索路由。 |
| Human Learning 建立来源与问题 | `POST /api/v1/learning/items/:item_key/references`；`POST /api/v1/learning/items/:item_key/assessment`；`GET /api/v1/learning/items`、`.../assessment`、`.../state`、`GET /api/v1/learning/events/:item_key` | 关联已接受 Knowledge ID；Assessment 返回独立身份及 Knowledge 版本 | 引用成功而 Assessment 失败会显示部分完成，不启动学习；队列为空和 Core 错误分开。不能从学习事件推断机器能力。 |
| Review / FSRS | `POST /api/v1/learning/reviews` → `GET /api/v1/learning/items/:item_key/state` | POST 携稳定 `client_event_id`、`exposure_id`、`assessment_id`、`knowledge_version`、answer、correct、rating；成功回执与状态回读核对 event ID、item key、assessment ID、answer | 只有回读一致才显示成功并清除提交身份；GET 失败/异常保留身份供幂等重试。`schedule_authority=unavailable` 与真实 `fsrs` 必须分辨，Mastery projection `closed=false` 不等于掌握度真值。当前定向合同测试覆盖这项转移；真实安装态冷重启仍待验。 |
| Machine Learning | `GET /api/v1/machine/tasks/:task_id` | 按具体 task ID 读取 Core 任务投影 | 当前 UI 只读取已有任务；无从页面执行机器 correction/retest 的完整写入闭环。不得把未暴露的 provider、embedding、模型状态标为可用。 |
| Memory Map、Workspace 等可视面 | 已有证据、Knowledge、学习与 workspace 投影的 UI 复用；无 `/api/v1/graph`、`/api/v1/workspaces` 编辑路由 | 仅使用现有 Core 对象身份 | 视觉节点、筛选或面板不能证明独立图谱后端或 workspace 编辑能力。缺数据应为空态/不可用，不得补虚构计数。 |

## 生产边界与错误语义

- Rust `main.rs` 仅在 `text_worker` 配置存在时挂载 `runtime::router` 的执行、取消、job 状态与输出路由；否则挂载基础 `projections`。`POST /api/v1/jobs/:job_id/receipts` 仅在 `manual_receipts=true` 的兼容测试路由注册，正式启动不注册，Desktop 也未调用。
- Core 生产路由可见于 `lib.rs` 与 `runtime/mod.rs`。`/api/v1/research*`、`/api/v1/plugins*`、`/api/v1/models*`、独立 graph/editor/version-history API 未在这两份路由表中注册。对应 UI 只能表达未接通，不能以 mock 结果声称集成。
- `401/403` 表示会话/权限问题；`404` 是未知对象或未注册路由；`409` 可表示幂等键与不同 payload 冲突。`200` 且空数组/`count=0` 是成功空态。部分 UI 分支当前只展示 HTTP 码或通用错误，尚未形成每个页面一致的 404/409 专属文案。
- 本轮静态对照与 Desktop 编译、复习回读定向合同测试只达到 `IMPLEMENTED_LOCAL / TESTED_LOCAL`。仍缺原 Green 实际启动后的逐页动作、真实写入→收据→重启回读、权限冲突、离线恢复及完整 UI 验收证据；状态为 `PARTIAL / UNVERIFIED`，不提升为 `LOCAL_GREEN_READY_FOR_OWNER_REVIEW`。
