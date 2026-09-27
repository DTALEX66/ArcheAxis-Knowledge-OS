# DSH 后端合同交接（面向 Codex）— 2026-09-27

> 用途：本文件把**当前真实可运行**的后端启动方式、路由表、错误语义与已验样例交给
> Codex 前端任务使用。所有内容取自当前源码与当前 SHA 的实际运行，不取自历史报告。
>
> 基线：`HEAD = 69a3baed13be061f2f8283c6efd4b0e5e80c4d23`，
> `tree = 0acd4266a8f6e7f97bd9b11cfe11b8ac7abff3a4`，
> 分支 `dsh/backend-20260927`（隔离 worktree，未推送）。
>
> **本文件不新增、不改名任何 API 路径。** 未实现的领域仍明确不可用（见 §6）。
> 未冻结的提案（typed loss receipt、Research DTO、资源根语义）不在本合同内。

---

## 1. 正式启动方式（实际可运行，非测试替身）

Core 是可执行文件 `archeaxis-api.exe`，由 Supervisor 以子进程启动：

```
archeaxis-api <workspace-db-path> [port]
```

- `port` 省略时用 `ARCHAXIS_VNEXT_PORT`，再省略用 `47831`。传 `0` 由系统分配（探针即用 `0`）。
- stdin 必须收到一行 ≤4096 字节的 launch JSON，并由父进程在 5 秒内关闭。
- 就绪信号是 stdout 上的一行：`archeaxis-api ready on http://127.0.0.1:<port>`。
- 绑定地址固定为 `127.0.0.1`（本机回环，非局域网服务）。
- 缺少 `launch` / 身份非法时不创建 workspace 并非零退出（fail-closed）。

launch JSON（`protocol: archeaxis.desktop-launch/v2`，一个 workspace 两个不同身份）：

```json
{
  "launch_token":  "<64 hex>",
  "machine_token": "<64 hex>",
  "session_id":    "<32 hex>",
  "actor":         "human",
  "protocol":      "archeaxis.desktop-launch/v2",
  "text_worker": {
    "python":  "<absolute path to python.exe>",
    "script":  "<absolute path to services/python-workers/transport/text_ndjson.py>",
    "staging": "<absolute path to a writable staging dir>"
  }
}
```

- 省略 `text_worker` 时仍有 Core 的读写基础路由；带上它才会挂载 `/jobs/:id/executions` 等 worker 执行路由。
- FSRS 解释器优先取 `ARCHEAXIS_PYTHON`，其次显式 `ARCHEAXIS_WORKER_PROFILE`
  （兼容 `ARCHAXIS_WORKER_PROFILE`），最后可执行文件旁 `worker-profile.json`。
  显式配置无效时拒绝降级；全部缺失或无效才记录调度不可用。worker profile
  与 launch JSON 是独立契约。下述旧收据仅证明各自命名的源码与运行身份。
- 维护入口（不启动服务、不需要 launch JSON）：
  `archeaxis-api --maintenance-backup <db> <artifact>` /
  `archeaxis-api --maintenance-restore <db> <artifact>`，stdout 输出一行 JSON。

---

## 2. 路由表（30 条，均由当前源码提取）

`crates/archeaxis-api/src/lib.rs`（Core 基础读写路由）：

| 方法 | 路径 |
| --- | --- |
| GET | `/api/v1/system/version` |
| GET | `/api/v1/workspaces/info` |
| POST | `/api/v1/imports` |
| POST | `/api/v1/jobs` |
| GET | `/api/v1/jobs/:job_id/quality` |
| POST | `/api/v1/jobs/:job_id/receipts` |
| POST | `/api/v1/sources/:source_id/anchors` |
| GET | `/api/v1/sources/:source_id/jobs` |
| GET | `/api/v1/sources/:source_id/jobs/:job_id/transform` |
| GET | `/api/v1/sources/:source_id/members` |
| GET | `/api/v1/evidence/anchors` |
| POST | `/api/v1/knowledge-items` |
| POST | `/api/v1/knowledge-items/from-transform` |
| GET | `/api/v1/knowledge-items/:id/v3` |
| GET | `/api/v1/knowledge-items/:id/qualification` |
| POST | `/api/v1/knowledge-items/:id/review-decisions` |
| GET | `/api/v1/search` |
| POST | `/api/v1/learning/events` |
| POST | `/api/v1/learning/reviews` |
| GET | `/api/v1/learning/events/:item_key` |
| GET | `/api/v1/learning/items` |
| GET | `/api/v1/learning/items/:item_key/state` |
| GET | `/api/v1/learning/items/:item_key/assessment` |
| POST | `/api/v1/learning/items/:item_key/references` |
| POST | `/api/v1/machine/tasks` |
| GET | `/api/v1/machine/tasks/:task_id` |

`crates/archeaxis-api/src/runtime/mod.rs`（执行路由，需要 `text_worker`）：

| 方法 | 路径 |
| --- | --- |
| GET | `/api/v1/jobs/:job_id` |
| POST | `/api/v1/jobs/:job_id/executions` |
| POST | `/api/v1/jobs/:job_id/executions/:request_id/cancel` |
| GET | `/api/v1/jobs/:job_id/outputs/:kind` |

---

## 3. 已验样例（来自 2026-09-27 的实际运行，非文档转述）

全部取自一次连续的 M0 全链运行
（`.project-local/m0loop/f7f32c46/m0-loop-receipt.json`，worktree
`.project-local/worktrees/dsh-backend-20260927`，`ok: true`）。

- `POST /api/v1/imports` → `202`，返回 `source_id`、`sha256`；
  同字节重复导入返回 `duplicate: true` 且 `source_id` 不变（幂等）。
- `POST /api/v1/jobs` → `202`，返回 `job_id`。
- `POST /api/v1/jobs/:job_id/receipts` → 结算 job；此后
  `GET /api/v1/sources/:source_id/jobs/:job_id/transform` → `200`，
  返回 `transform_id` 与抽取文本。
- `POST /api/v1/knowledge-items/from-transform` → `201`，返回
  `knowledge_id`、`anchor_id`、`raw_sha256`、`requires_human_review: true`、`status: "candidate"`。
- `GET /api/v1/knowledge-items/:id/v3` → `200`，`schema_version: "3.0.0"`。
- `GET /api/v1/search` → `200`，返回 `count` 与 `items[]`（词法检索）。
- `POST /api/v1/knowledge-items/:id/review-decisions` → `200`，人工接受后
  `GET .../v3` 的 `status` 变为 `accepted`、`owner` 为 `human`。
- `POST /api/v1/learning/items/:item_key/references` → `201`。
- `POST /api/v1/learning/events` → `201`；同 `client_event_id` 重放 → `200` 且 `duplicate: true`。
- `POST /api/v1/learning/items/:item_key/assessment` → `201`，返回
  `assessment_id` 与 `knowledge_version`（绑定被接受的知识版本）。
- `POST /api/v1/learning/reviews` → `201`，返回 `answer`、`event_id`、
  `schedule_authority: "fsrs"`、`schedule_state`（`stability`/`difficulty`/`due`/`state`/`step`）、
  `mastery_projection`、`next_review`。
- `GET /api/v1/learning/items/:item_key/state` → `200`，重启同一 workspace 后
  仍读回同一 `answer` 与 `next_review`。
- `POST /api/v1/machine/tasks`（失败）→ `201`；`POST` 人工纠正产生后继版本；
  带 `retest_of` 的再次提交 → `201`；`GET /api/v1/machine/tasks/:id` → `200` 且 `retest_of` 指回原失败任务。

---

## 4. 错误、空值与冲突语义（已观测，未编造）

- 未知对象返回**具名 404**，不是空对象。
- 缺字段 / 空 `item_key` / 未带 `assessment_id` 却提交 `answer` → `400` 且带原因文本。
- 身份不允许的操作 → `403`（机器身份不能写人类学习结果、不能自我接受知识）。
- 同一 idempotency key 配不同 payload → `409`。
- 重复提交同一 key 且 payload 一致 → `200` + `duplicate: true`，不重复计分、不重复排程。
- `search` 的 `count: 0` 是**成功空结果**，与错误不同。
- 具体响应体字段以当前源码为准；本表只登记已实际观测到的行为。

---

## 5. 调度权威（`schedule_authority`）— 前端必须据此显示

这是**三种不同事实**，不能互相顶替：

| 值 | 含义 | 触发条件 |
| --- | --- | --- |
| `fsrs` | 真实 FSRS 调度，`schedule_state` 有值 | Core 进程环境里有 `ARCHEAXIS_PYTHON` 且能跑 FSRS worker |
| `unavailable` | 复习已记录，但**排程不可用**；`next_review` 为 `null`，`next_review_days` 为哨兵 `-2` | 有卡状态但调度器不可答 |
| `placeholder_ladder` | 占位阶梯，**不是** FSRS | 调用方未提供卡状态 |

另有两条已实测的端点差异，前端不要用其中一个去推断另一个：

- `/api/v1/learning/events`（不带卡状态）→ `placeholder_ladder`；
- `/api/v1/learning/reviews`（带答案与 assessment）→ `fsrs`。

`mastery_projection.closed` 当前恒为 `false`，`status` 为 `"projection"`。
**它不是 Knowledge Truth，也不是已完成的 Mastery。**

---

## 6. 当前明确不可用的面（前端不得呈现为可用）

以下在源码中**没有**路由或没有冻结契约，前端必须显示"未接通/不可用"，不得显示成功状态：

- `/api/v1/research*`、`/api/v1/plugins*`、`/api/v1/models*` —— 均不存在（已有契约测试断言其不存在）。
- 向量检索 / reranker / 图谱检索：`/api/v1/search` 当前是词法检索，不代表 embedding 或混合检索。
- Research DTO 与 Provider 身份/版本：Owner 决策未定，不实现。
- typed loss receipt（`/receipt` vs 扩展 `/quality`）：Owner 决策未定，当前
  `/api/v1/jobs/:job_id/quality` 只是汇总投影；前端不得自行解析双层 JSON 或自造 `fallback=true`。
- 资源根 / Provider 身份语义：Owner 决策未定，前端不得呈现虚构 provider、模型版本或插件激活状态。

---

## 7. 前端写集边界（本任务未触碰）

本任务对 `apps/**` **零改动**（含 `MainWindow.axaml.cs` 与所有 Avalonia 视图/主题/ViewModel）。
Codex 的既有未提交修改保持原样。原生 UI/交互/DPI/键盘验收仍由 Codex/Owner 完成。

---

## 8. 回滚

本合同的全部源码改动都在一条隔离分支上，回滚 = 回退该分支的提交；
不涉及 force push、reset --hard、分支删除，也不涉及任何 build 产物或 `.project-local/`。

---

## 9. 第二轮增补（2026-09-27，受测提交 `ee015075`）

### 9.1 源码身份必须连工作区状态一起读

`git rev-parse HEAD` 对干净检出和带未提交修改的检出是**同一个值**。因此：
receipt 现在携带 `source_tree`、`source_dirty`、`source_patch_sha256`、`worktree_root`；
`dev.py` 把同样的值写入 `execution.json`。**任何只引用 commit 的后端资格说法都不要采信**，
请连 `source_dirty` 一起读。干净运行校验器输出 `committed <sha>`；
脏运行输出 `UNCOMMITTED … not a committed-source qualification`。

### 9.2 正式启动所需的环境（前端接入须知）

Core 进程需要 `ARCHEAXIS_PYTHON` 指向具备 `fsrs` 的解释器，`/api/v1/learning/reviews`
才会返回 `schedule_authority: "fsrs"`；否则返回 `"unavailable"` 且 `next_review` 为 `null`。
**不要**让用户在界面里手工填写该变量——正式宿主应由 Supervisor 在启动子进程时注入。
在此之前，前端必须按 §5 如实显示三种权威状态，不得把 `unavailable` 显示为已完成排程。

### 9.3 已完成的独立后端打包与安装后运行

| 项 | 值 |
| --- | --- |
| wheel | `archeaxis_workspace-0.6.14-py3-none-any.whl`，sha256 `a97d326127e3d5b7e49710d671626853376649e24a7de84d09d33b918aebbfc4` |
| 隔离安装根 | `D:\All projects\AAOS-DSH-WHEEL-QUAL\ee015075`（仓库之外，临时资质目录） |
| 安装后入口 | `python -m app.runtime_entrypoint migrate` exit 0；重复执行**幂等**；`archeaxis health` exit 0 |
| 遮蔽核验 | 隔离环境中 `app`/`shared`/`config` 全部解析到隔离 site-packages，无 checkout 遮蔽 |
| 明确缺口 | `services/python-workers/**` **不在 wheel 内**，因此完整的 M0 环仍由源码构建的 Core＋worker 承载 |

**注意**：安装的 Python 后端拥有**自己的** schema 基线（`python_compatibility`，本机
97 表、含 `kb_attachment_facts`），与 Rust vNext Core 的 `workspace_meta` 基线**不是同一个库**。
前端不得把两者当成同一事实源，也不得双写。

### 9.4 `mastery_projection.closed` 的准确含义

它是**合同规定的保留状态**，不是未实现的完成位。`crates/archeaxis-domain/src/learning.rs:144`
原文：*"deliberately marked open: review observations and FSRS scheduling do not establish
Knowledge truth or a closed mastery claim."*
前端应显示为"投影/未闭合"，**不得**据此显示已掌握。
