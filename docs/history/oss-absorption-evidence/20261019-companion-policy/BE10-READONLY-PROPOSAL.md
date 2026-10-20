# BE10 下一个产品切片：只读分析，尚未实施

观察：2026-10-19。来源为当前工作树；不构成新 Authority、授权或完成回执。Root 是唯一产品 writer；本文件仅在忽略目录。

## 合同及实际缺口

- 活动指针 backend_host_execution_overlay 选中 BE00–BE12；BE10 是 P0、FIRST_RELEASE，依赖 BE01。原合同：`docs/authority/taskpack-20261013-backend-host/TASKS.json` 的 BE10；`TASKPACK.md:257–275`。
- 必须交付握手、能力发现、对象引用、状态和只读关联；登记 namespace、协议版本、身份、修订、新鲜度及 deep link。Context packet、task proposal、asset manifest、knowledge candidate、receipt 先合同，真实跨项目写入后阶段。
- `packages/contracts/v2/ui-host.schema.json:36–38` 的三个 project.* 仍为 null。`frontend/src/api/uiHost.ts`、`src-tauri/src/ui_host_bridge.rs:37` 当前只支持有限无输入读取，不能把任意对象/URL 塞入空 input。
- `crates/archeaxis-api/src/launch.rs:223–249,378–441` 仅有 human/machine admission。machine 不是 Observer；现有 token 不能给跨项目消费者。所有 actor header 都由 launch 中间件覆盖，但 `request_actor` 缺省 human，不能让未处理 Observer 进入该路径。
- `frontend/src/adapters/` 当前仅有 OpenMAIC 格式适配；未发现 project observer adapter 实现。Schema/类型占位不等于实际 consumer。

## 最小完整实现建议

建议使用独立 `archeaxis.project-observer/v1` 合同和端口；以下名称、上限均为实施建议，不是已有约定。

1. 在 `crates/archeaxis-contracts/src/project_observer.rs` 定义严格有限 DTO，在 `packages/contracts/v2/project-observer.schema.json` 保存规范 schema。固定 producer namespace `archeaxis`，consumer namespace 来自受信 launch grant；协商支持版本集合与有限操作集合。未知协议拒绝，不能自动降到旧 human API。
2. 在 `launch.rs` 增加独立 bootstrap Observer grant。推荐明确 v3 launch 扩展，保留 legacy/v2 行为；不对旧 v2 隐式创建 Observer。每 grant 固定 consumer namespace、consumer instance、producer workspace/restore_epoch、expiry、允许对象 ID 集合与独立凭据。凭据从 owned stdin 进入，只保留内存；不放 argv、URL、DTO、日志、仓库。所有凭据两两不同，grant/object 数量有界；缺失、重复、null、部分声明、未知字段均拒绝。
3. 在 `launch.authenticate` 中对 Observer 凭据提前分流，只允许精确 Observer 路由和读方法，其他方法/普通 API/未知路由一律拒绝。Observer 请求不能落到 `request_actor`、完整 `next.run` 或 system/version 的本地路径泄露投影。拒绝重复 token header、同时出现多种身份 header、Origin、自报 actor/consumer 的提权。
4. 新增 `crates/archeaxis-api/src/project_observer.rs`；从 `lib.rs` 暴露有限 producer。入口建议 GET handshake、GET objects（仅 grant 内对象，limit≤50）、GET objects/:id/status（冻结版本/hash 查询，不支持正文、原件或任意 query）。无 token 时 401、grant 不匹配/越权 403、版本不兼容 409、对象不存在 404、身份缺失/损坏 503；客户端显示明确有限状态。
5. producer 仅返回允许对象 metadata：document ID、现行 version、content_sha256、title（如明确允许）、source revision、observed_at、freshness TTL、producer workspace/restore_epoch、typed navigation reference。读取在同一个 Store callback/只读事务形成一致快照；不调用提取、模型、worker 或写操作。列表只 SELECT grant 允许 ID，不全表发现私人对象。
6. **身份只读陷阱**：不能复用 `ui_state::read` 或 `workspace_id`。`crates/archeaxis-domain/src/ui_state.rs:1005–1012` 的 read 会首次 INSERT 身份；`:324–332` workspace_id 也会 INSERT。应使用 `existing_workspace_id(:317)` 和现成只读 `archeaxis_store_sqlite::authorization_fence::authorization_epoch` (`authorization_fence.rs:72`)；legacy 无 fence 对应 initial，损坏拒绝，身份未初始化返回 unavailable。不要在握手路径补建身份。
7. 对象来源可用 SELECT documents.current_version JOIN document_versions；现有 `crates/archeaxis-domain/src/document.rs:135–156` 展示精确 revision/hash 来源，但 `document::read` 会展开完整 editor、blocks、projection，首期无需调用或外传这些正文。绝不能透传 `system/version` 中 workspace_db、凭据、草稿、全文或私有记忆。
8. 实际 adapter consumer 建议 `crates/archeaxis-api/src/project_observer/client.rs` + owned CLI `src/bin/project-observer.rs`，使用严格 DTO、固定 127.0.0.1:port、有限请求、超时/长度限制、无重定向、无任意 URL。可以复用现有本地 Rust HTTP 方式，不新增依赖。连接 grant 经 stdin 显式注入，不自动发现其他产品、端口、用户配置。consumer 实际进行 handshake→object read→status，对响应身份、协议、对象及修订/hash 逐项验证。
9. 如本轮要在宿主可见，`src-tauri` 使用独立 `project_observer` 只读 bridge command 及持有的 Observer credential；前端只能传有限已授权对象键，不可传 endpoint/token/SQL/路径。显示“关联对象→状态→回到本地”；不可暴露执行/提交/自动导入按钮。现有 ui-host/v2 input:{} 保持，若升级需单独 typed union/生成器/DTO/负向测试，不能把 project null 直接映射到通用 coreCommand。
10. Deep link 必须有实际 handler 才标 supported。当前未发现通用跨产品 URI 注册；可以先返回 typed navigation reference + navigation_status=UNAVAILABLE，不造可点击 archeaxis:// 已支持。若本轮验收要求真实返回本地，新增有限内部 document 导航 adapter，校验工作区/恢复 epoch/版本，用户点击才导航；对象变更或外部宿主缺失时保留关联并显示 stale/unavailable。

## 状态、未来合同与幂等边界

- 握手兼容不等于连接长期在线；latest snapshot 到期必须变 STALE/UNVERIFIED，网络失败不能继续报 CURRENT。过期 grant 拒绝；consumer 同时验证 TTL、checked_at、可接受时钟偏差，不接受未来时间证明新鲜。
- 每次读校验 producer workspace 和 restore_epoch；备份恢复、重启换 token、错误工作区、过期授权都不沿用原 admission。原对象引用保留，不自动修订或自动接纳。
- 首期 delivery 为 NONE/REFERENCE_ONLY。未来 HandoffEnvelope 合同只声明：有限 kind（context_packet/task_proposal/asset_manifest/knowledge_candidate/receipt）、envelope ID、producer/consumer namespace/identity、协议/修订、object ref、digest、expires_at、correlation/idempotency key、candidate authority、grants_execution=false、grants_knowledge_acceptance=false。无写入入口。
- 重复读取不新增 DB 记录；request_id 只关联。未来投递相同 idempotency key+digest 可重放同回执、同 key 不同 digest 冲突；不能宣称 exactly-once。Schema 中的 idempotency 字段不等于本轮已实现 delivery。

## 建议验收矩阵（不可用窄 PASS 代替完整 BE10）

1. legacy/v2 启动和 human/machine 现有回归仍通过；未配置 Observer 时本地业务独立运行。
2. 独立 process bootstrap 测试：有效专用凭据读成功；旧/过期/错误 token、重复 header、human/machine token 冒用 Observer grant、伪 consumer/actor、Origin 均按合同拒绝。观察响应/日志/argv 没有 token 或真实路径。
3. 对每个普通路由类至少选实际 mutation（document save/create、job execute/cancel、model config、conversation send、memory、knowledge accept）和高风险 read（原件、正文、历史/私有记忆）：Observer 全部不可达，数据库逻辑快照不变，owned worker invocation=0。GET 方法本身不是只读证明。
4. 在已有初始化身份和未初始化空 store 都测 handshake：前者成功，后者明确 unavailable；两者前后 sqlite schema/meta/业务行都不变。可用 rusqlite readonly connection 验证纯 helper，在真实 process 验证 admission 不绕开。
5. producer 两个同名对象/不同 revision，allowlist 外拒绝；超大/未知 query、ID 路径/编码注入、未知版本、超限 limit、响应超限/类型/identity/schema 错配拒绝。
6. 真正 adapter 对两个隔离合成实例（A producer、B consumer，独立 DB、session、凭据）执行真实 HTTP handshake/list/status，并确认两者没有直接打开对方 DB，没有第二产品仍可独立运行。consumer 必须调用正式模块，不用 mock/fake request 手写成功结果。
7. A 更新对象：旧引用明确 STALE，读取新引用需重新核对；A 备份恢复 epoch变化后旧 grant失效；A 断连/重启/超时、过期时间、未来时间、错误 namespace/identity/version，B 不继续展示绿色 CURRENT。重读不产生学习/知识接纳。
8. 导航有已实现的内部 typed handler 或明确 UNAVAILABLE；真实 UI 只读关联无执行按钮，窄窗口/键盘和返回本地至少一条旅程。
9. future envelopes schema 执行负例校验，未提供投递 HTTP 路由，candidate/grants false 不可客户端改为已接纳。

证据分级：上述 Rust/process/adapter 使用合成资料只能标 INTEGRATED/SYNTHETIC。WORK-LAB/DESIGN-LAB 真实源码接入、其原生宿主、真实用户资料和最终安装仍须单列 NOT_EXECUTED/UNVERIFIED；不能用两个 AAOS 合成实例冒充外部产品验收。不得为追求 BE10 全绿越界改另外仓库。

建议定向门禁：新增 `crates/archeaxis-api/tests/project_observer_api.rs` 与 `project_observer_process.rs`；保留 `launch_auth`；新增 contracts JSON Schema 正反例；若 host/UI 有修改，新增有限 bridge/adapter 及实际 UI 旅程。按 canonical `scripts/runtime/dev.py` + `scripts/ci/cargo_test.bat ... --offline --locked` 执行。先不升级依赖，不做全库治理，不安装外部服务。

本轮状态：READONLY_PROPOSAL / NOT_EXECUTED。没有修改产品、共享库、另仓、凭据、全局配置；未启动服务/浏览器；未执行测试。
