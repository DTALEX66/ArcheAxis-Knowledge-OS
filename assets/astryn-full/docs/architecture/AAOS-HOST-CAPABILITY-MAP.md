# AAOS Host Capability Map（对 AAOS 的只读核验）

- 核验日期：2026-10-13
- AAOS 本地路径：`D:\All projects\ArcheAxis-Knowledge-OS`（同级项目，按本任务最小只读授权访问）
- Git 观察（只读命令）：HEAD `0574c3acb6cd8ea29525b7140c91188ea65c3430`，分支 `codex/conversation-closure-20261013`，最近提交 `0574c3ac "Align frozen release architecture and publish closure evidence"`；`git status --short` 为 0 行（工作树干净）。
- **声明：本次为只读核验。未启动、未构建、未运行 AAOS 任何进程或测试；对 AAOS 无任何写入；未访问 E:\、F:\；未打开任何 `*.sqlite`/`*.db`（仅登记路径存在性）；未读取凭据、`.env`、私人会话。**
- 判定档位含义：`AVAILABLE_UNVERIFIED` = 接口在现行源码中注册且有契约/schema，但本次未取得运行时证据；`BLOCKED_BY_HOST_CONTRACT` = 现行权威接口面上不存在该能力（AAOS 自己的契约文档甚至以 404 双重探针断言其不存在）；`AVAILABLE_VERIFIED` = 本次未使用（本次未运行任何东西）。

---

## 权威文件核验

| 文件 | 存在性 | 关键约束摘要 |
| --- | --- | --- |
| `AGENTS.md` | 存在 | 当前路由指向 `docs/current/AAOS-ACTIVE-EXECUTION.json`；SUP-022 确立 `frontend/`+`src-tauri/` 为正式 Tauri/React 宿主；Rust Core 是唯一规范 SQLite/CAS 写者，Python 是隔离 worker；普通文档保存不要求外部证据/云核验/人工批准，但知识准入保留人工专用工作流；发布/Green 替换/真实数据覆盖未授权。 |
| `AUTHORITY.md` | 存在 | 导航入口，非第二真值源；历史时点两处记录过根 AUTHORITY 缺失（`AUTHORITY_REFERENCE_MISSING`，2026-10-01 实测，G01 已修复——该缺失是历史时点而非当前）。正式栈 = Tauri 2 + React/TS/Vite + Rust Core 单写者（SUP-021→SUP-022）。明确区分"仅目标/候选/结构实现/受控测试/真实运行/独立验收/发布"。 |
| `PROJECT_CONTRACT.yaml` | 存在 | `archeaxis.project-contract/v1`，`contract_version: 1.0.0-draft`，effective 2026-10-09。runtime：`ui_to_core: loopback-http-json`、`core_to_worker: stdio-ndjson`、local_auth bind 127.0.0.1 / 随机端口 / per-launch token。data_authority：sqlite + rust-writer-actor + sha256 CAS；禁止 ui/worker/agent 直接 SQL、禁止双写。知识准入 final_choice=human-only；外发需 explicit-purpose 同意。contracts：HTTP openapi-3.1、消息 json-schema-2020-12。 |
| `DECISION_SUPERSESSION_LEDGER.yaml` | 存在 | SUP-022（effective）：正式宿主为 Tauri 2 + React/TS/Vite（frontend/ + src-tauri/），经 loopback HTTP 合同到 Rust Core；Rust Core 唯一规范写者不变，**旧 Python backend 不得重新接线为权威**。SUP-001/003/006 确立 Rust 单写与库隔离。 |
| `docs/current/AAOS-ACTIVE-EXECUTION.json` | 存在 | 状态 `RUNNING_BY_OWNER / PARTIAL`；`formal_stack: "Tauri 2 + React/TypeScript/Vite + Rust Core sole SQLite/CAS writer + isolated Python workers"`；权限字段逐项列出（release NOT_GRANTED 等）；delivery_readback：PR #185 已合并 main，SHA `23f22a49…` CI run 38274429552 记为 PASS（引自 AAOS 自身登记，本次未向 GitHub 独立回读）。 |
| `docs/current/AAOS-REPOSITORY-CONTINUITY-20261012.md` | 存在 | 本地根 = 该路径的本机登记；远程仅剩 `main`；9 个本地历史 worktree 有未提交差异（保留）；明确列出仍未完成范围：云端真实调用、27B 资源/质量比较、独立学习效果、Owner 验收等**尚未达成**——即产品运行时资格整体 PARTIAL。 |
| `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md` | 存在（1243 行，读头部与关键节） | 本轮 PARTIAL；前端 542 测试 PASS、Tauri 单元 78 PASS、Core 文档/分页/maintenance PASS（真实 SQLite/CAS、隔离内容）、独立 Core 进程闭环 probe 7 步 PASS（REAL Core + SYNTHETIC 内容）；均注明"非安装版、非 Owner 验收"。 |
| 补充：`docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` | 存在 | 标题即 "live-verified"：在真实 Core 进程上观察过路由清单与鉴权模型（观察时点 commit `1a981a44`，非当前 HEAD）；§3 列 96 个 method/path 对（text_worker 启动形态），§8 用双方法 404 探针断言哪些面**不存在**。这是本次能力映射的最强单一来源。 |

## 现行技术栈事实

来源为实际 manifest，而非文档转述：

- 前端 `frontend/package.json`：`archeaxis-knowledge-frontend` 0.6.14；React 18.3.1、TypeScript 5.5.4、Vite 5.4.11、Vitest 2.1.9；编辑器 Tiptap 3.31.4；PDF 用 pdfjs-dist 6.4.299；Tauri CLI 2.11.4（devDep）。**没有 `@tauri-apps/api` 依赖**——运行期用 `withGlobalTauri: true` 的 `window.__TAURI__.core.invoke`（`frontend/src/api/core.ts:37`、`workspace.ts:283`）。
- Tauri 宿主 `src-tauri/Cargo.toml`：`archeaxis-desktop` 0.6.14，`tauri =2.11.5`、`tauri-build =2.6.3`、`reqwest 0.13.4`（宿主用 loopback HTTP 转发到 Core）。`src-tauri/tauri.conf.json`：capability 只给 `core:default / core:event:default / core:window:default`（"无直接文件系统/shell 权限"）；CSP `connect-src 'self' http://127.0.0.1:*`。
- 根 `Cargo.toml`：workspace 成员为 `crates/archeaxis-{contracts,store-sqlite,domain,application,migration,sidecar-protocol,api,archive}`；`src-tauri` 被有意 exclude（自带 workspace）。`crates/archeaxis-store-sqlite/src/lib.rs:13`：`SCHEMA_VERSION = 12`（生产契约文档在 2026-10-01 观察为 6，2026-10-05 记录 Schema11——schema 在活跃演进）。
- Rust Core API：`crates/archeaxis-api`（axum），监听 **仅 IPv4 127.0.0.1**（`::1` 被拒，REAL 观察）；启动须父进程向 stdin 写一条 launch JSON（`archeaxis.desktop-launch/v2`，`packages/contracts/bootstrap/v2/launch.schema.json`），含 64-hex `launch_token` 与独立的 `machine_token`。
- Python workers：**真实存在**。`services/python-workers/routes.json`（`archeaxis.worker-routes/v1`）声明 16 个 capability→worker 脚本映射（pdf.extract、image.ocr、media.transcribe、machine.answer、search.semantic、course.general 等）；协议为 stdio NDJSON（`crates/archeaxis-sidecar-protocol` + `packages/contracts/v1/worker-protocol.schema.json`）。
- 遗留 Python FastAPI BFF：`app/main.py` 挂载 workspace/system/capability/learning/setup/federation 路由；`app/workspace/system.py` 实现 `GET /api/v1/system/handshake`（前端 `client.ts` 校验的 product identity 面）。按 SUP-022 与 `AAOS01-TWO-API-SURFACES-AND-WHICH-ONE-IS-Q02.md`，`app.main:app` 是**遗留/供体面，不得作为权威**；宿主回退逻辑（`desktop/src-tauri/src/backend.rs`，被 src-tauri `#[path]` 复用）：优先启动 `core/archeaxis-api.exe`（Rust Core），否则回退 `python -m app.runtime_entrypoint core`。
- SQLite/CAS：`data/archeaxis.sqlite`(+shm/wal)、`data/cognitive_os.sqlite` 路径存在（仅登记，未打开）。CAS 为 sha256 内容寻址（`crates/archeaxis-store-sqlite` raw_objects）。

## 能力映射

统一权限模型（对下面四节都适用，证据：`crates/archeaxis-api/src/launch.rs:378-441` authenticate 中间件；REAL 观察于 `AAOS-PRODUCTION-HTTP-CONTRACT` §2）：每个请求必须带唯一 `x-archeaxis-launch-token` 头；v2 会话有 human token 与 machine token 两把凭据，**actor 由服务端按命中的 token 派生**，客户端自报 `x-archeaxis-actor` 会被覆写；带 `Origin` 头的请求一律 403（浏览器不是合法客户端）；写路由另有人工专用守卫（machine principal → 403）。前端写调用还要求 `workspace:write` scope + `Idempotency-Key`（`frontend/src/api/client.ts:149-161`）。

### 1. 模型服务 / 会话与流式输出

| 能力 | AAOS 实际证据（文件:符号） | 接口形态 | 版本/兼容 | 权限模型 | 可用性判定 | ASTRYN Adapter 责任 | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 本地一次性模型问答（非流式） | `crates/archeaxis-api/src/runtime/mod.rs:198` `POST /api/v1/machine/answers`；实现 `runtime/colearning.rs`；worker `services/python-workers/machine/worker_machine_answer.py`（先探 Ollama `/api/generate`，再 OpenAI 兼容 `/chat/completions`，仅允许 numeric loopback） | HTTP JSON，一请求一答案；答案持久化为 `runtime.answer` 机器回执，`outcome: unmeasured`，**永不自动晋升知识** | 请求/回执有 JSON Schema；`api_contract "1.x"`（`client.ts:25`） | 任意合法 token；knowledge 必须 active+accepted，否则 404 before inference | `AVAILABLE_UNVERIFIED` | 星栖的"角色表达生成"若走宿主模型，只能按"提问→候选回答→人工评估"闭环建模；不得假设有会话对象 | 无会话/多轮状态对象；无流式；无 token 级事件 |
| 通用 chat completion / 模型路由 API | 契约文档 §8：`GET/POST /api/v1/models`、`/models/providers` 双方法 404，由 `crates/archeaxis-api/tests/contract_absent_surfaces.rs` 断言；`config/models.yaml` 仅产品内部 adapter 配置（default provider: stub） | 不存在 | — | — | `BLOCKED_BY_HOST_CONTRACT` | 不得渲染/依赖"宿主 provider 列表"；星栖若需自有生成通道，属于 ASTRYN 侧决定且不得写入 AAOS | 宿主不暴露通用模型调用面 |
| 流式输出（SSE/WebSocket/事件） | 权威 Core 96 个 method/path 面无任何 streaming 路由（`runtime/mod.rs` 全量 route 列表）；唯一 `text/event-stream` 在遗留 BFF `app/workspace/router.py:841 /api/audit/stream`（审计流，maintenance 面，非模型输出） | 不存在（正式面） | — | — | `BLOCKED_BY_HOST_CONTRACT` | 星栖 UI 的打字机效果只能在 ASTRYN 侧对整段回执做呈现层模拟 | 宿主无 push/流式通道；跨进程事件推送不存在 |
| 模型配置/清单观察 | `runtime/mod.rs:199-200` `GET /api/v1/machine/configuration`、`POST /api/v1/machine/inventory`（空输入、有界本地观察，无推断） | HTTP JSON | 2026-10-12 清单 #127/#128 登记 | 任意 token | `AVAILABLE_UNVERIFIED` | 可用作启动期能力探测 | "listing 不证明 inference 可用"（AAOS 自己的措辞） |
| 受控云调用（文档核查） | `lib.rs:65` 与 `runtime` 的 `POST /api/v1/documents/{id}/checks/execute`；worker `services/python-workers/machine/document_check.py` + `shared-contracts/adapters/llm/litellm_adapter.py`；配置来自固定 `data-root config/document-check.json`；2026-10-13 增一次性 dispatch approval 语义 | HTTP JSON + stdio NDJSON worker | `format-execution-receipt.schema.json` 等 | **human only**；每次云操作需有界、一次性、绑定 attempt/material digest 的批准；撤回阻断后续决定 | `AVAILABLE_UNVERIFIED`（合成传输测试；真实云资格未建立，见 CONTINUITY 未完成清单） | 星栖不得假定宿主可自由外发；任何涉云呈现须走此批准语义或留在 ASTRYN 侧 | 非通用调用面；provider 固定；真实外发 UNVERIFIED |

### 2. 记忆（memory / preference / knowledge 读写与权限）

| 能力 | AAOS 实际证据（文件:符号） | 接口形态 | 版本/兼容 | 权限模型 | 可用性判定 | ASTRYN Adapter 责任 | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 长期知识条目读写 | `lib.rs:195-208` `POST /api/v1/knowledge-items`、`/from-transform`、`GET /{id}/v3`、`/{id}/qualification`；审核 `POST /{id}/review-decisions`、`POST /api/v1/knowledge/{id}/review/versioned` | HTTP JSON，schema `knowledge_v3`（`schema_version: "3.0.0"`） | v1 路由 + v3 payload；`packages/contracts/v1/*.schema.json` | 创建候选任何合法 actor；**晋升/否决 human only（machine 403）**；契约：knowledge_admission final_choice = human-only | `AVAILABLE_UNVERIFIED` | 星栖写入宿主记忆的唯一合法路径=创建 candidate，由人审阅晋升；Adapter 必须把"星栖想记住 X"表达为候选而非直接生效 | 无自动晋升；无按 actor 命名的记忆分区 |
| AI 资产（含 memory kind）与授权上下文包 | `runtime/mod.rs`+`lib.rs:104-107` `GET /api/v1/ai/assets`、`POST /api/v1/ai/context-packets`；`crates/archeaxis-domain/src/asset_context_grant.rs`（`Consumer{LocalMachine, ManualContextPacket}`、`Operation{ReadPacket,Answer,Retest}`、`State{Candidate,Granted,Revoked}`）；schema `packages/contracts/v2/ai-asset.schema.json`（kind 含 `"memory"`，state candidate/adopted） | HTTP JSON + 冻结快照 grant（document_id+version+content_sha256） | `archeaxis.asset-context-grant/v1` | Consumer 是**闭集枚举，只有两个值**；非法/被围栏 grant → `archeaxis.context-admission-refusal/v1`（`runtime/context_refusal.rs`） | `AVAILABLE_UNVERIFIED`（枚举本身即硬缺口） | **星栖今天不能成为被命名的记忆消费者**——Consumer 枚举没有外部子系统位；seam 应预留 consumer 身份扩展 | `BLOCKED_BY_HOST_CONTRACT` 的实质：第三方 consumer grant；`shared-contracts/adapters/memory/__init__.py` 仅 "placeholder for future integration" |
| 工作状态（非长期记忆） | `lib.rs:73-84` `GET/PUT /api/v1/workspace/ui-state`(+clear-saved/recover/clear-job/cancel-machine/machine-status)；CAS 依 workspace_id+restore_epoch+state_revision | HTTP JSON | `packages/contracts/v2/ui-working-state.schema.json` | **human only**（清单 #122-126/#129/#133） | `AVAILABLE_UNVERIFIED` | 星栖不能把它当宿主记忆读；至多是"用户当前现场"的呈现参考 | 无对外稳定读取合同 |
| 遗留记忆实现 | `app/memory/{episodic,long_term,vector_db,memory_layers,...}.py` 存在（Python 遗留 BFF 内部） | 无正式 v1 路由暴露 | — | — | `NO_EVIDENCE`（作为可调用接口） | 不得依赖；它是行为供体，不是接口 | SUP-022 禁止将 Python backend 重新接线为权威 |

### 3. 上下文（context / selection / 当前文档 / 任务上下文）

| 能力 | AAOS 实际证据（文件:符号） | 接口形态 | 版本/兼容 | 权限模型 | 可用性判定 | ASTRYN Adapter 责任 | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 机器上下文清单 | `lib.rs:101` `GET /api/v1/machine/contexts`（machine_governance.rs） | HTTP JSON | 2026-10-10 清单 #106 登记，标注 "Runtime acceptance UNVERIFIED" | 任意 token + handler guard | `AVAILABLE_UNVERIFIED` | 星栖取"当前工作上下文"应经此投影，不得自行扫描工作区 | 无实时性/事件通知；语义需另行细读 |
| 授权上下文包（grant-fenced） | `POST /api/v1/ai/context-packets`（见第 2 节）；同请求不同 packet → 409，packet 内容冻结可重放 | HTTP JSON | v1 | Consumer 闭集；恢复后 grant 被围栏（RESTORED_GRANT_FENCED） | `AVAILABLE_UNVERIFIED` | 这是 AAOS 现成最接近"可获准读取上下文"的合同；星栖侧只应请求、不应组装旁路 | 同样受 Consumer 枚举限制 |
| 文档/原件/检索读取 | `GET /api/v1/documents/{id}`、`GET /api/v1/sources/{id}/original`、`GET /api/v1/search`（FTS5 词汇，硬上限 20 条）、`POST /api/v1/search/semantic`（≤128 候选、90s、`index_persisted: false`） | HTTP JSON | DTO 由 `core-document.schema.json` 生成 | 任意 token（读路径） | `AVAILABLE_UNVERIFIED`（2026-10-01 对这些读路由有 REAL 观察记录） | 星栖引用宿主内容一律走这些投影 + anchor 身份，不复制原文进星栖私有库 | 无向量主库 API；语义搜索是查询时有界排序而非持久索引（§8 明言"vector/hybrid/graph 不存在"） |
| "当前选中/当前文档"跨子系统广播 | 全库无相关 Core 路由；选择状态只存在于 frontend 组件与 human-only ui-state | 不存在 | — | — | `BLOCKED_BY_HOST_CONTRACT` | 星栖不能假设"读到用户正在看的选区"；需要该信号时应标 BLOCKED 并请求宿主扩展 | 无事件总线、无 push；`core:event:default` 仅是 Tauri 窗口内事件，不跨进程 |

### 4. 动作 / 权限审批 / 执行回执

| 能力 | AAOS 实际证据（文件:符号） | 接口形态 | 版本/兼容 | 权限模型 | 可用性判定 | ASTRYN Adapter 责任 | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 作业生命周期（enqueue→execute→status→cancel→output） | `lib.rs:178` `POST /api/v1/jobs`；`runtime/mod.rs:176-186` `GET /jobs/{id}`、`POST /jobs/{id}/executions`（必填 `idempotency-key` 头，`deadline_ms` 1..300000，202=持久声明非完成）、`/executions/{request_id}/cancel`、`GET /jobs/{id}/outputs/{kind}`（metadata 带 sha256 与 `authority_effect: candidate_or_measurement_only`）；状态枚举 `queued/running/succeeded/failed/cancelled`（`job-status.schema.json`） | HTTP JSON | v1 | 任意 token；取消请求≠观察到的 cancelled，必须重读 | `AVAILABLE_UNVERIFIED`（REAL 观察于 2026-10-01 同族路由 + 合同测试） | 星栖发起宿主动作就映射到这条链：幂等键、deadline、以 job 状态为唯一权威事件源（正对应 ASTRYN 规则"系统任务状态只来自权威事件"） | 无回调/无推送——只有轮询；无跨启动的 watch 通道 |
| 执行回执 / 损失回执 | `packages/contracts/v1/format-execution-receipt.schema.json`、`coverage-receipt.schema.json`、`loss-receipt.schema.json`、`crates/archeaxis-contracts/src/loss_receipt.rs`；`GET /jobs/{id}/quality` 仅是聚合投影**不是类型化损失回执**（§8 明言） | JSON Schema 2020-12 | 独立版本（compatibility-policy.md：API/worker 协议/schema/导出格式各自协商 minor） | — | `AVAILABLE_UNVERIFIED` | 星栖消费回执必须按 schema 校验、拒绝未知字段；不得从 quality 里"解析出"回执 | `POST /api/v1/jobs/{id}/receipts`（手动回执）明确不在生产面（404，"Do not call it"） |
| 人工审批 | `POST /api/v1/knowledge/{id}/review/versioned`、`/knowledge-items/{id}/review-decisions`（machine→403，stale version→409）；`POST /api/v1/workspace/backups` human only；v2 restore preview/confirm 走宿主命令（`src-tauri/src/main.rs:968` invoke_handler：`core_command`、`workspace_restore_preview/confirm`、`restore_backup` 等 10 个） | HTTP JSON / Tauri command | `desktop-routes.schema.json`、`core-command.schema.json`（operation 闭集枚举 ~80 项） | 审批决定即授权线性化点（云 dispatch approval，§Native content 节） | `AVAILABLE_UNVERIFIED` | 星栖呈现不得替人批准；凡"星栖建议做 X"落为宿主动作前必须过 human-only 路由 | 星栖不能请求"代批"；宿主也不提供审批回调 |
| 能力开关（注册表作为权限屏障） | `runtime/mod.rs:189-193` `GET /api/v1/capabilities[/{cap}]`、`PUT /{cap}/enabled`；`capabilities.rs`（health 只基于文件存在 + 协议 hello，明言不证明引擎）；禁用后 claim 事务内拒绝（409 AAK-CAP-001，零 attempt 行） | HTTP JSON | `AAOS_CAPABILITY_REGISTRY_V1` | 任意 token 可读写开关（注意：不是 human-only） | `AVAILABLE_UNVERIFIED` | 星栖 Adapter 启动时应先读 capabilities 做能力协商，把 `worker_missing`/disabled 映射为 ASTRYN 侧 NOT_EXECUTED 而非失败猜测 | fallback 字段当前生产启动恒 null（无第二 provider） |
| 权威事件记录 | `POST /api/v1/machine/tasks`（**machine only**，human 403；回执不可变；`runtime.` scope 前缀 Core 保留）；`POST /api/v1/learning/events`（human only，`client_event_id` 幂等）；job/machine journal（`runtime/job_journal.rs`、`machine_journal.rs`、`execution_claim.rs`、`withheld.rs`——UNKNOWN 语义保留、显式清除需精确 CAS） | HTTP JSON | 生成契约 + 上述 journal schema | 双 actor 严格分向 | `AVAILABLE_UNVERIFIED` | 星栖的"已执行/未执行"陈述只能转写为这些事件，不自建第二事件账本 | 无读取"所有权威事件"的订阅面；只有按对象回读 |
| 通用工具调用 / 插件注册 | §8：`/api/v1/plugins`、`/api/v1/research` 双方法 404（测试断言）；`contracts/plugin/plugin-manifest.schema.json` 存在但无装载路由；工具注册=启动时 launch 声明 worker 路由（`launch.rs` TextWorker.routes，`routes.json` 16 项） | 不存在（运行期不可注册） | — | — | `BLOCKED_BY_HOST_CONTRACT` | 星栖不得假设能向宿主注册新 tool/plugin；新能力=配置+重启级别的宿主决定 | 无动态 tool 面；plugin manifest 是孤儿合同（无执行路由证据） |

## ASTRYN 侧结论

1. **M0 不可依赖的接口**（一律标 `BLOCKED_BY_HOST_CONTRACT`，不许写成"应该有"）：流式/会话式模型输出；通用 chat completion 与 provider 目录；跨子系统"当前选区/当前文档"广播；第三方 consumer 身份的记忆读写（`Consumer` 闭集）；运行期注册工具/插件；执行回调/事件推送（只有轮询）；向量索引持久 API 与 graph API。
2. **可以对接、但必须按 AVAILABLE_UNVERIFIED 对待的**：`machine/answers` 一次性问答、`ai/context-packets`、`machine/contexts`、knowledge candidate/review 链、jobs 生命周期与回执 schema、capabilities 注册表。每次验收前需真实启动 Core 复核（本次未运行）。
3. **seam 建议**（ASTRYN Host Adapter 接口层预留）：
   - `CapabilityDiscovery` port ↔ `GET /api/v1/capabilities`（含 health/enabled/fallback 语义，未知值→UNKNOWN，不得猜测）；
   - `GenerationRequest` port ↔ `POST /api/v1/machine/answers`，返回类型设计成"候选回执 + outcome:unmeasured"，并为未来流式预留独立接口槽（当前实现返回 NOT_EXECUTED/BLOCKED）；
   - `MemoryCandidateWrite` port ↔ `POST /api/v1/knowledge-items`（强制 candidate 语义，晋升永远依赖 human review）；
   - `ContextRead` port ↔ `machine/contexts` + `ai/context-packets`，本地定义 `ConsumerIdentity` 抽象但注释标明宿主枚举暂缺外部值；
   - `ActionExecution` port ↔ jobs 链（Adapter 侧必须自带 idempotency-key 与 deadline 策略，且以 job 状态为唯一权威事件）；
   - `ApprovalSurface` 只渲染状态、绝不代批。
4. **验收影响**：凡依赖流式呈现、宿主记忆自动写入、工具注册、选区感知的 M0 验收项 → `BLOCKED_BY_HOST_CONTRACT`；其余依赖 AAOS 运行时的项在真实启动+握手+exact-SHA 之前 → 最多 `AVAILABLE_UNVERIFIED`/NOT_EXECUTED。握手面注意：`/api/v1/system/handshake` 由**遗留 Python BFF** 实现，Rust Core 的对应身份面是 `GET /api/v1/system/version`（`runtime: "archeaxis-api"`，宿主在 `src-tauri/src/main.rs:911` 用它做恢复读回校验）——星栖 Adapter 的健康检查应绑定后者。

## 未核验与限制

- 未运行 AAOS 任何二进制/测试/进程；所有 OBSERVED/REAL/PASS/CI 字样均**转引自 AAOS 自己的带日期登记**（观察 commit `1a981a44`、`fca7e715`、`23f22a49`，均早于当前 HEAD `0574c3ac`），本次未向 GitHub 独立回读 CI。
- `AAOS-UI-FIRST-EXECUTION-20261009.md` 只读头部与关键节（全文 1243 行）；`AAOS-COVERAGE-MATRIX-20261006.md`、`docs/truth/*`、FREEZE-REGISTER 未读。
- 遗留面（`app/` Python BFF、`desktop/`、`apps/ArcheAxis.Desktop/` Avalonia）只核验了角色定位，未逐路由审计；其上的 `/api/planner/*`、`/api/audit/stream` 等不构成正式宿主合同。
- 未打开 `data/archeaxis.sqlite` 等运行数据库与 `.project-local/` 证据目录内容；未读任何凭据/`.env`。
- `machine/contexts`、`ai/context-packets` 的请求/响应字段细节未逐字段核验（AAOS 清单自身也标注 "inspect handler and generated contract"）。
- 双启动形态（有/无 `text_worker`）导致的路由面差异（69 对 vs 96 对）以文档与源码声明为准，本次未实测 404/405 区分。
