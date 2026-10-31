# AI 外部上下文与知识候选边界

> **2026-10-23 后继范围澄清**：本文件中的“人类侧不改”是已完成AI上下文专项的实施边界与保护事实。Owner在换会话前明确人类侧不冻结，并确认闭环同时包括AI侧；后续按[唯一双侧闭环定义](../truth/CLOSED_LOOP_DEFINITION.md)及[决定二十二](AAOS-OSS-INTEGRATION-DECISION-20261019.md#二十二人类与ai双侧闭环继续交接时的最新范围2026-10-23)继续人类、AI及双向连接的有限首版。外部原始上下文归属不变；候选接收隔离测试不等于AI完整闭环或真实外部连接。下面“本轮不修改”仍如实描述原专项，不延伸为后续禁令。

Owner 2026-10-23 决定：跨项目、跨软件、跨 Agent 原始会话、执行轨迹和运行记忆属于独立的 `EXTERNAL_CONTEXT_PROVIDER`。AAOS 只治理可复用知识候选及已批准的 AI 学习资产。本文件只改变 AI 侧职责，不改变人类学习侧权威、功能、接口或数据结构；实际进度仍只写 `AAOS-UI-FIRST-EXECUTION-20261009.md`。

## 职责与影响面

| 现行或历史入口 | 真实身份与本次处置 |
| --- | --- |
| `app/rag/retriever.py`、`app/schemas.py`、`app/evaluation/feedback.py`、`app/memory/store.py` | 历史 Python 路线；intake 001/002 的 active 是创建时点状态，不能作为 Tauri 正式路径。保留历史文件和数据，不据此恢复全局上下文职责。 |
| `crates/archeaxis-api/src/project_observer.rs` | 现行有限只读投影、授权对象元数据；不是全 Agent 会话采集。保留。 |
| `crates/archeaxis-api/src/project_handoff.rs` | 有限纯元数据准备合同，无 HTTP 写入口和业务库；不是上下文中心。保留，不扩展连接其他仓库。 |
| `crates/archeaxis-domain/src/ai_asset.rs` | 现行文档版本内 AI 资产、候选／采纳／撤回、固定人工审查、冲突和版本关联。复用，不另建知识库。Memory 类型可承载经过治理的产品知识资产，不等于所有 Agent 的原始会话库。 |
| `context_grant.rs`、`asset_context_grant.rs`、`material_question.rs`、`machine_evaluation.rs`、`machine.rs` | 保留有限请求上下文、RAG、AI 知识使用、纠正／复测和版本依据。不得按“外置上下文”理由删除。 |
| `crates/archeaxis-domain/src/character_memory.rs` | 产品内部受治理的角色记忆，与全局外部 Agent 运行会话不同；本次不修改。 |
| 新 `crates/archeaxis-domain/src/external_context.rs` | 白名单 DTO、显式授权 Admission、namespace、限长、幂等接收与受限读回；写入已有 Document／AiAsset，不创建任何表或外部 transport。 |
| 新 `crates/archeaxis-api/src/external_context.rs` | 在既有 launch 认证和 Store writer 下提供人工授权离线导入及未连接状态；没有 provider 登录、同步或后台采集。 |
| 人类侧、前端、Tauri、workers、store schema | 本轮不修改。仅两个 Rust `lib.rs` 增加 AI 模块／新路由装配，不改变原路由和语义。 |

## 有限接收合同

- `GET /api/v1/machine/external-context/status` 返回 `fetch_status: NOT_CONNECTED`、`provider_id: null`、有限 capabilities；`network_fetch`、`raw_context_capture` 和 `automatic_recall` 均为 false。这不是 provider 健康探测。
- `POST /api/v1/machine/external-context/candidates` 只允许既有认证链绑定的 human actor。body 为 `{candidate, material_authorized, redaction_confirmed}`；两个授权确认必须显式为 true。machine actor 返回 403；这不是供远程 Agent 自行授予访问权的接口。
- Candidate 的 Rust DTO 是执行合同：版本、稳定 ID、知识类别、摘要／问题／根因／失败尝试／解决方案／适用与禁用条件、证据引用、verification 和 source。所有嵌套对象 `deny_unknown_fields`，拒绝 messages、raw_context、tool_logs、session_history、governance 等额外字段。source 包含任意合法 project_id（不固定三个项目）、provider_id、source_app、source_ref、auth_scope、fetch_status、provenance、updated_at。
- body 上限 65536 字节，候选序列化上限 48000 字节、单字符串 4096 字节；引用另限 1024，拒绝明显本机绝对路径、file URI、带 userinfo 或 query 的引用。人工确认脱敏是必要条件，**不是自动 DLP 或能证明任意摘要不含秘密的保证**；不应提交私人原文。
- admission 的唯一用途为 `knowledge_candidate:import`。未来 provider adapter 必须在可信边界建立并撤销 Admission，不得从来源包推导权限。当前 HTTP 只实现人工离线导入，不宣称有 provider 认证／撤权订阅服务。
- `(provider_id, project_id, candidate_id)` 复用现有 create_request_id 幂等机制；相同请求返回原件，改写同 ID 的内容失败，不覆盖旧版本。项目／provider 不同则身份不同；领域读接口显式核对 admission namespace。
- 原始 PASS、FAIL、UNKNOWN、NOT_RUN 等只是外部声明。即使附 diff、命令、exit_code、hash，AAOS 也不伪称已验证，统一标 `UNVERIFIED_EXTERNAL`，资产始终以 `candidate` 入草稿。无批准、无自动技能执行，也不授予正式知识准入。
- 相似候选、语义去重、冲突和适用性判断沿现有人工审查／版本冲突机制完成。本轮只有精确身份去重，**没有新增语义相似度引擎或自动修复证据核验器**。不能将同一结论的不同候选 ID 当作多个独立证据。
- 现有 Document 读回／备份、AiAsset 审查与撤回机制继续使用；领域读接口在来源 offline／timeout／revoked／missing／deleted／unknown 时明确返回状态，不返回候选正文，也不删除已存历史。状态是可信调用方提供的观察，当前没有实际出网读取引用。

## 保留边界与未来接入

Rust Core 是唯一业务 writer；无 SQL migration，无第二套数据库、运行时、会话采集和全局 recall。普通人类草稿保存无需该外部验证。OpenViking、Hy-Memory 等尚未选型、安装、连接；Windows、许可、部署、日志隐私与费用须独立审核。私人会话访问和跨仓连接均未授权，WORK-LAB／DESIGN-LAB 未修改。

后续接入必须单独验证 provider 身份／撤权、有限证据回读、稳定引用删除、超时／离线、真实人工治理与适用性；不得把本轮隔离测试算跨软件同步。人类学习、多格式、科研及当前文档问答保持现行定义。

## 验证与回滚

本轮报告与命令索引：[检查点](../history/project-drift-audit-20261021/ai-context-separation-20261023.json)。原始合并 stdout/stderr、退出码和工作树身份保存在项目 `.project-local/runs/be268a2d33/ai-context-separation-*`，不上传运行库；新源码单独记录 SHA256，不能把 dirty HEAD 当精确提交资格。

精确回滚：仅移除两个 `lib.rs` 中本轮新增的模块声明及新路由装配，删除本轮四个新增 Rust 实现／测试文件；不回退其他已有修改。文档只去掉本轮 AI 边界条目。逐文件的变更前副本、task-only diff 和哈希位于 `.project-local/artifacts/ai-context-separation-20261023/`，确认当前文件仍等于收尾哈希后才按清单恢复。无数据迁移，已导入候选仍是原有格式的 Document/AiAsset；不删库或候选数据。若已有后续修改，人工合并反向补丁，不全量 reset／clean。
