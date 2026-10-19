# Project Handoff v1：BE10 本期合同准备

原 BE10 TASKS 明确要求本期准备 context/task/asset/candidate/receipt 合同，真实写入和任务投递属于后阶段。本合同交付严格 DTO、JSON Schema、共享正负案例和可执行的纯 metadata 投影，不以延期蓝图代替本期合同，也不增加跨产品执行/写入端口。

Schema：`packages/contracts/v2/project-handoff.schema.json`；DTO：`archeaxis_contracts::project_handoff`；纯投影：`archeaxis_api::project_handoff`。不引入依赖、注册器、数据库、安装器或另一产品代码。

## 公共边界

Envelope 固定 `archeaxis.project-handoff/v1` 和既有 Observer protocol，绑定 producer namespace/workspace/restore epoch、consumer namespace/instance、hex32 idempotency key、创建和到期时间。唯一 authority 为 `PREPARATION_ONLY`。有效期最多30秒，真实投影不超过已认证 Observer snapshot 的到期时间；不构成执行权或知识接纳。

原件、版本与hash复用 Observer `ObjectReference`；身份复用原 DTO/schema。所有对象与选区都固定在该修订，不静默换成最新版。对象ID、block ID、候选ID是有界 ASCII 声明；无URL、机器路径、正文、标题、任意JSON、命令或凭据字段，额外字段拒绝。任何 DTO/schema 验证本身都不证明身份认证或业务事实。

| kind | 实际用途与必要绑定 | 保守状态 |
| --- | --- | --- |
| context | source冻结引用；whole_object、block内UTF-16范围、页范围或时间范围；learning/research/conversion/visualization用途；REFERENCE_METADATA_ONLY授权范围，recipient与expiry由envelope绑定 | 选区边界存在性与语义未读取正文核对，明确UNVERIFIED，不授予正文传输或模型调用 |
| task_proposal | 明确prepare_*目标、冻结target与上下文选区；匹配既有CAP和贡献点 | execution_authority固定NOT_GRANTED；提案不变成可运行任务 |
| asset_manifest | 每项冻结资产、原件/衍生关系、冻结来源、格式族；损失为UNKNOWN或精确损失回执引用 | 格式资格UNVERIFIED；损失有引用也不等于lossless或已验引擎 |
| knowledge_candidate | candidate ID/revision、声明claim hash、冻结basis与非空证据选区 | PENDING_HUMAN_REVIEW；证据支持NOT_ASSESSED，无自动接纳、无候选正文复制 |
| receipt | 关联原提案key/kind/规范化SHA-256，保留相同producer/consumer/restore epoch；PREPARED/REJECTED/UNKNOWN/CONFLICT及有限reason | 无DELIVERED/EXECUTED/ACCEPTED/SUCCESS；UNKNOWN不折算成成功 |

空清单、超过32项、重复资产ID、反向/空选区、不相容目标/CAP/贡献点、错误来源关系、未知字段与不合法状态组合均拒绝。时间、列表关联、原提案关联等跨字段要求由实际 Rust 语义验证负责；JSON Schema 不独自证明这些要求。

## HUB-003 接续

CAP 身份来自既有 `config/capability-map.v1.json`（对应Atlas），不新建注册器。贡献点词汇与 HUB-003 提案对齐为 `format_conversion/template/learning_activity/graph_visual/model_service/tool_protocol`。本期四种明确任务目标只使用有意义的CAP/贡献点组合。

`manifest_identity` 本版严格为 `UNKNOWN`，不能靠填入一个hash就虚构已注册/安装/启用。HUB-003 本轮另行准备能力包 schema及权限/依赖/兼容/生命周期合同；未串行应用、未发布身份时不重复这些字段。后续已知manifest引用需在其合同应用后以明确版本扩展，不把UNKNOWN升级成运行资格。

## 纯投影与幂等比较

`prepare` 要求调用者先通过既有实际 `ObserverClient` 取得已认证响应。本函数本身不认证、不打开socket、不读文件/DB，只核验snapshot新鲜度，并要求每个来源、target、证据、原件/衍生来源和损失回执精确包含在当前Objects清单或CURRENT ObjectStatus中；STALE、缺失版本、不同hash、不在allowlist或过期均失败。不能把手工构造的 DTO 当作认证响应。

`prepare_receipt` 必须带原提案。PREPARED重新检查原提案仍有效且全部引用CURRENT，回执expiry不超过原提案；UNKNOWN/拒绝/冲突只表达该状态，不能恢复current。`receipt_matches` 校验原提案身份、key、kind和内容指纹，返回的是“关联成立”，不是投递或业务成功；调用方必须保留receipt state。

提案指纹为：固定前缀UTF-8 `archeaxis.project-handoff/v1` 后接一个零字节，再接整个严格DTO的规范JSON，做SHA-256。规范JSON对象key按字典序、数组保序、无空白、整数十进制；本合同字符串均为有限词汇或ASCII标识。Rust实际计算与Python `sort_keys=True,separators=(',',':'),ensure_ascii=False` 对同一正例逐项比对。后续其他语言必须保留精确整数，不可先转有损浮点。

`classify_retry` 以producer workspace/restore epoch、consumer identity、idempotency key为作用域：严格DTO内容完全一致为Equivalent；同key更换payload、purpose或expiry为Conflict；其他作用域或key为Unrelated。不存在持久化队列或真实投递，因此这是可用的合同比较逻辑，不宣称已实现跨进程投递幂等或exactly-once。

## 证据边界

共享67案例验证真实Rust严格解码/语义与JSON Schema；实际纯投影测试覆盖五类用途、11种非回执正例、版本/hash/allowlist、资产来源和损失、候选不接纳、回执关联、过期与同key内容冲突。仅owned临时镜像中的先前key/kind-only比较用于红控，正式提案与产品不注入缺陷。

本期未执行：真实跨产品投递/写入、持久化去重、外部产品UI/native、deep link、共享配置、安装分发、真实用户资料或Owner验收。独立Observer首切片的既有HTTP证据保留自己的SHA/时点，本合同测试不替代该证据。

## CLI真实只读准备消费

在原有handshake/objects/status之外，`archeaxis-project-observer`的有界stdin action支持：

- `{operation:"prepare_handoff",key:<hex32>,payload:<strict project-handoff Payload>}`：上下文、任务提案、资产清单或知识候选。receipt payload不能绕过原提案绑定。
- `{operation:"prepare_receipt",key:<hex32>,original:<strict Handoff>,state:<ReceiptState>,reason:<ReceiptReason>}`：必须提供原提案，调用既有digest绑定和状态语义；PREPARED只表示metadata准备完成，UNKNOWN/CONFLICT不是成功投递。

两个动作都先沿用专用stdin admission进行真实只读握手，再读取固定objects端口，调用`project_handoff::prepare`或`prepare_receipt`。调用者不能提供snapshot、任意URL、endpoint、命令、正文或grant。输出严格`archeaxis.project-handoff/v1`，只包含冻结metadata及PREPARATION_ONLY；manifest identity仍UNKNOWN。没有目标产品投递、执行、持久化幂等表或业务数据库写入；不创建业务工作区。

错误继续使用`archeaxis.project-observer-error/v1`有限code：已有OBSERVER_*或HANDOFF_INVALID_SNAPSHOT、HANDOFF_INVALID_PROPOSAL、HANDOFF_REFERENCE_NOT_CURRENT、HANDOFF_ORIGINAL_REQUIRED、HANDOFF_IDENTITY_MISMATCH。输入/认证原文及token不输出。stdin原有64KiB/5秒边界、argv拒绝及每HTTP请求3秒deadline保留；这不是整个多请求流程3秒承诺。

工程验收由`project_handoff_process`使用自建合成资料、owned临时Core和CLI真实进程验证；所有业务表前后快照不变，检查无token/title/body/路径泄漏。仍不代表WORK-LAB/DESIGN-LAB真实UI、原生宿主、安装分发或Owner接纳通过。
