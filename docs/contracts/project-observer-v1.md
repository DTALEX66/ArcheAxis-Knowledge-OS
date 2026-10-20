# Project Observer v1：首期只读适配端口

BE10 的首个工程切片。规范 schema：`packages/contracts/v2/project-observer.schema.json`；实际 Rust DTO：`archeaxis_contracts::project_observer`；producer 和实际 HTTP consumer：`archeaxis_api::project_observer`。不建立第二当前任务台账。

本切片提供独立只读准入、握手、允许对象的版本/hash 清单和冻结引用状态；不提供远程执行、正文提取、知识接纳、投递、自动发现或跨产品数据库访问。

## 启动与所有权

旧 legacy/v2 human/machine 接口保持原行为。Observer 仅可通过明确的 `archeaxis.desktop-launch/v3` stdin 启动声明激活；现有 v2 桌面不会自动启用。v3 仍要求独立 human/machine token，并添加 1–2 项 `observer_grants`。每项包含：

- `token`：独立小写 hex64，不能等于 human、machine 或另一项 Observer token；只在受信父进程/消费者内存和 inherited stdin 传递。
- `consumer`：有限 namespace `work-lab` 或 `design-lab`，以及 hex32 `instance_id`；这是显式配置绑定，不宣称外部产品身份认证已完成。
- `producer`：namespace 固定 `archeaxis`，已存在工作区的 hex32 `workspace_id` 与 `restore_epoch`（initial 或 hex32）。
- `expires_at_ms`：当前时点之后、不超过 24 小时的 Unix 毫秒值；每次请求重新检查。
- `document_ids`：1–32 个不重复、有界 ASCII ID，明确授权 metadata 读取；不接受目录、URL、SQL 或任意对象字典。

未初始化身份的空工作区只读握手返回 unavailable，不能由 Observer 建身份。正常拥有者流程先初始化业务工作区；Observer 不调用具有首次写入副作用的 UI read helper。

Observer token 在 launch 认证层提前分流；只有下列精确端口可达，无法落入普通 human/machine router。普通 API、未知端口、写方法、Origin、自报 actor、错误 consumer、协议不兼容、重复身份 header 均拒绝。不得把 human token 交给 Observer。

## 端口

共同请求头为既有 `x-archeaxis-launch-token`（仅 Observer 专用值）和 `x-archeaxis-observer-protocol: archeaxis.project-observer/v1`、`x-archeaxis-observer-namespace`、`x-archeaxis-observer-instance`。不接受请求正文。

| 方法与路径 | 有限输出 |
| --- | --- |
| GET `/api/v1/project-observer/handshake` | 协议/双方身份、三项只读操作、REFERENCE_ONLY、执行/接纳授权均 false |
| GET `/api/v1/project-observer/objects` | grant 中仍存在的对象 ID/version/hash，最多32项；不返回正文、title、草稿、记忆、机器路径或凭据 |
| GET `/api/v1/project-observer/objects/:id?version=:version&content_sha256=:hash` | 原冻结 reference 与 CURRENT/STALE；不把新版本静默替代为原引用 |

响应绑定 producer workspace/restore epoch、consumer、checked_at_ms 与最多30秒的新鲜期；有效期不超过 grant 到期。客户端重新校验 schema、协议、身份、字段集合、时间与所选操作，过期/未来时间不能证明 current；网络失败不返回缓存成功。

错误使用有限 error schema/code，不回显 HTTP 私密正文。主要状态为 401 未准入、403 受限/过期、409 协议或工作区变化、404 允许范围内的对象不存在、503 未初始化/损坏/不可读取。恢复 epoch 改变后旧 grant 拒绝。

`navigation` 当前明确 UNAVAILABLE：提供对象引用没有自动注册 URI handler。外部原生宿主 deep link 与产品 UI 关联/返回旅程需要后续实际实现和验收，不能从字段或概念说明推导已支持。

## 实际消费者

`archeaxis-project-observer` Rust 可执行入口只读有界 stdin，不接受 argv。输入根对象严格包含 `admission` 与 `action`；admission 为 port、专用 token、producer/consumer；action 为 `{operation:handshake}`、`{operation:objects}` 或 `{operation:status,reference:{document_id,version,content_sha256}}`。

传输只连接 `127.0.0.1:port`，每次 HTTP 请求固定3秒单调时钟总截止（包括 connect、write、read、EOF、DTO 解析及最终核验）；每次 I/O 只使用剩余预算，连续慢流不能续期，迟到合法 metadata 同样返回 OBSERVER_UNAVAILABLE。有界 HTTP frame、不跟随重定向、严格响应 DTO。首次握手通过后才进行所选只读调用。stdout 只有有限 metadata 或有限错误码。该 CLI 是首期实际 adapter 入口，未自动加入现有安装包或共享产品配置。

## 证据与未覆盖范围

`project_observer_process` 使用两个自建合成工作区、真实 Core 及 Rust CLI/HTTP，核对所有业务表不变、无私有正文/路径泄漏、旧角色保持、版本变更、恢复失效、断连与过期；`project_observer_client` 使用 owned loopback 负例响应检查拒绝能力。JSON Schema 和 Rust 使用同一组合同案例。

这些属于合成资料的工程集成证据，不是 WORK-LAB/DESIGN-LAB 实际原生互通或用户资料验收。独立外部产品接入、可见关联 UI、真实 deep link、context/task/asset/candidate/receipt 合同及本CLI准备消费见project-handoff-v1.md；幂等投递和安装分发仍未交付。读请求可重复且无写入，不承诺 exactly-once delivery。

## CLI真实只读准备消费

在原有handshake/objects/status之外，`archeaxis-project-observer`的有界stdin action支持：

- `{operation:"prepare_handoff",key:<hex32>,payload:<strict project-handoff Payload>}`：上下文、任务提案、资产清单或知识候选。receipt payload不能绕过原提案绑定。
- `{operation:"prepare_receipt",key:<hex32>,original:<strict Handoff>,state:<ReceiptState>,reason:<ReceiptReason>}`：必须提供原提案，调用既有digest绑定和状态语义；PREPARED只表示metadata准备完成，UNKNOWN/CONFLICT不是成功投递。

两个动作都先沿用专用stdin admission进行真实只读握手，再读取固定objects端口，调用`project_handoff::prepare`或`prepare_receipt`。调用者不能提供snapshot、任意URL、endpoint、命令、正文或grant。输出严格`archeaxis.project-handoff/v1`，只包含冻结metadata及PREPARATION_ONLY；manifest identity仍UNKNOWN。没有目标产品投递、执行、持久化幂等表或业务数据库写入；不创建业务工作区。

错误继续使用`archeaxis.project-observer-error/v1`有限code：已有OBSERVER_*或HANDOFF_INVALID_SNAPSHOT、HANDOFF_INVALID_PROPOSAL、HANDOFF_REFERENCE_NOT_CURRENT、HANDOFF_ORIGINAL_REQUIRED、HANDOFF_IDENTITY_MISMATCH。输入/认证原文及token不输出。stdin原有64KiB/5秒边界、argv拒绝及每HTTP请求3秒deadline保留；这不是整个多请求流程3秒承诺。

工程验收由`project_handoff_process`使用自建合成资料、owned临时Core和CLI真实进程验证；所有业务表前后快照不变，检查无token/title/body/路径泄漏。仍不代表WORK-LAB/DESIGN-LAB真实UI、原生宿主、安装分发或Owner接纳通过。
