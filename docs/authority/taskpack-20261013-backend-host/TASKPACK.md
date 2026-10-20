# 星环知识系统基础后端接入任务包

计划 ID：AX-HOST-20261013

补齐配置、材料问答、共享会话、记忆、布局和真实状态，重载能力保留合同并延期。

## 共同交付边界

正式产品使用 ArcheAxis／星环知识系统；AAOS 是内部代号。产品为本地优先的知识与 Human–AI 双向学习工作区。首期关注多格式、最快真实闭环、完整前端框架与基础文本小栖，多位测试者各自在本机使用。

主项目继续使用 Tauri 2、React 18、TypeScript、Vite、Rust Core 单写者及隔离 Python workers。ASTRYN 只持有人格、交互与人物表现；模型、长期记忆、上下文、任务和权限由主项目持有。WORKLAB／DESIGNLAB 独立运行、独立数据与凭据，Observer 只读，专业设计编辑回原生宿主。

本包是新分支的执行输入，产品任务为 PLANNED；已下载资产、合同提案和代码配方不表示产品已接通。旧任务在继承表中保留，未选择的 V01、FT01–04 和六核心历史增量不自动解冻。用户当前明确指令优先；实施者核对本包与当前权威、合同和实际代码，登记必要的新范围，不因为历史字段阻止已明确授权的新 UI 工作。

每个 checkout 只有一个 writer；用独立分支或隔离 worktree，保护现有 dirty/untracked 文件。运行资料、密钥、个人对话、模型权重和数据库不进入公开任务包或提交。例行可逆操作按当前任务授权继续；提交、推送、合并、安装发布及正式资料覆盖按当前会话与仓库现行授权处理，不能从此压缩包额外推导权限。

shared 中逻辑合同由 BE01 统一正式登记。前端和 ASTRYN 不能各自新建另一套模型中心、长期记忆库或泛用执行桥。Contract Proposal 明确是提案；执行前必须变成实际请求／响应 Schema、Rust／TypeScript DTO、有限命令映射和负面测试。

## 执行任务

### BE00 基础后端接手与缺口核对

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：无；先核对本仓当前权威和状态。

执行内容：
- 读取根权威和现有配置、恢复、上下文、模型与 worker 合同。
- 核实已存在接口并复用，明确新增最小范围与重载延期。

必须产物：
- host-baseline.json
- backend-scope.md

通过条件：
- 不重复实现已有 Core，不启动通用 Agent 或冻结引擎。

继承任务：UF00、CB01

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE01 有限宿主合同与所有权登记

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE00

执行内容：
- 将 shared 合同提案正式登记为 typed schema、DTO 与有限桥；同一版本由后端合同维护者拥有。
- 明确请求 ID、对象版本、权限引用、真实目的地、错误、取消、回执与事件序号。
- 前端和 ASTRYN 消费固定版本；不创建任意执行或凭据透传接口。

必须产物：
- formal UI host contracts
- finite bridge mapping
- contract-change-notes.md

通过条件：
- 三包接口版本及字段一致，未知输入拒绝。
- launch-token 留在宿主；非空字段不替代权限或签名校验。

继承任务：CB01

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE02 独立布局偏好与 CAS 恢复

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- 布局与 WorkingState 业务草稿分开存储，保持 Core 单写者。
- 版本、设备、布局树、组件与对象引用采用明确边界和 CAS。
- 读取、写入、迁移和恢复对未知组件或屏幕外位置有回退。

必须产物：
- layout schema and persistence
- CAS and restoration tests

通过条件：
- 重启读回，冲突不覆盖另一修订。
- 不把业务正文、秘密或任意可执行组件写入布局。

继承任务：CB01

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE03 材料上下文与受限问答

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01、BE04

执行内容：
- 核对现有 machine_answer 的知识约束，补新导入材料和选区问答缺口。
- 绑定文档／派生版本、选区、来源、用途授权与实际模型目的地。
- 读材料与存普通笔记无需通用审批；提问回执可定位原材料。

必须产物：
- material context DTO
- bounded document question adapter
- source-linked answer receipt

通过条件：
- 真实新导入资料可问答，回答来源明确。
- 缺提取、权限或模型有具体原因，不伪装成功。

继承任务：UF03

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE04 模型配置凭据与用途绑定

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- 提供脱敏配置读写、原生凭据引用、模型清单和逐用途试运行。
- 首期接一种已有获准服务，分开 API 账户与正式客户端适配；本地能力逐项探测。
- 全局、工作区和本次覆盖保留版本；本地故障不隐式改目的地。
- 逻辑 FAST／DEEP、用途预算和有限排队引用真实模型能力；向量模型变更先检查索引与重建计划。

必须产物：
- model configuration contracts
- credential adapter
- purpose bindings
- real call receipt

通过条件：
- 重启保持有效配置与用途；配置读不触发推理。
- 凭据不进日志或导出，未知加载和费用显示未知。

继承任务：UF10

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE05 正式陪伴会话流与取消

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01、BE04

执行内容：
- 提供陪伴与材料学习两类明确请求，流式事件绑定 session、request、sequence。
- 持久化历史及冻结请求，取消和晚到片段有确定处理。
- 补受限 ASTRYN consumer 或正式适配范围，保留有限权限与宿主身份。

必须产物：
- conversation host port
- stream/cancel/history contracts
- consumer adapter

通过条件：
- 真实模型对话通过；切换呈现不重复执行。
- 重启恢复与取消查询不扩大范围或静默重试。

继承任务：本轮新增的有限范围；保留领域边界。

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE06 角色档案与受控长期记忆

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- Core 持有角色偏好、学习目标与获准记忆，ASTRYN 只通过端口。
- 支持读取、纠正、遗忘、导出与停用，分别规定聊天、索引缓存和备份语义。
- 人物与关系风格不改变事实来源和权限。

必须产物：
- character profile persistence
- memory operations and provenance
- deletion semantics

通过条件：
- 真实保存重开与纠正删除可读回。
- 不建立第二长期知识主库；不只隐藏卡片冒充遗忘。

继承任务：本轮新增的有限范围；保留领域边界。

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE07 能力状态与范围化就绪探测

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- 为 operation 返回实现、依赖、连接、资格、权限、范围、原因及有效期。
- 已存在目录与 Atlas 投影复用；按当前视图与变化刷新。
- 父级汇总不能因一个子项通过全绿，过期与未知降级。

必须产物：
- readiness snapshots
- operation status aggregation
- status expiry tests

通过条件：
- 页面标记和映射不当作运行资格；执行前再次校验。
- 状态查询不加载所有模型或轮询全部重引擎。

继承任务：UF06

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE08 配置依赖与部署计划边界

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01、BE07

执行内容：
- 读取已有模块与服务配置，提供有限变更与依赖计划。
- 计划区分本机下载与已有远端服务，展示来源、版本、hash、大小、风险范围和回退。
- 首期无安装实现时返回明确不可执行原因，重安装引擎延期。

必须产物：
- module/configuration plan contracts
- installed engine diagnostics

通过条件：
- 不以演示进度冒充安装，不把所有候选自动装进电脑。
- 安装或更新动作如实际执行必须绑定正式计划与授权回执。

继承任务：O01

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE09 页面草稿和学习对象最小保存

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- 复用现有文档、教学交换、研究与学习状态合同。
- 仅为确有缺口的对象补有类型保存，不用通用 JSON 写入绕过领域规则。
- 覆盖人工课程、方案、反馈、练习和视图草稿的保存重开与版本引用。

必须产物：
- page draft/learning object adapters
- version and restart tests

通过条件：
- 每个首期可编辑页面具有真实保存去向。
- 布局、草稿与正式知识真值分开，普通保存不增加治理负担。

继承任务：CB02、CB03、UF05

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE10 跨项目只读接入与版本协商

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- 首期握手、能力发现、对象引用、状态和只读关联。
- 登记 namespace、协议版本、身份、对象修订、新鲜度和深链接。
- 准备上下文包、任务提案、资产清单、知识候选和回执合同；真实写入后阶段。

必须产物：
- project read-only adapters
- handshake and reference schema
- future handoff contracts

通过条件：
- 各产品独立数据与凭据，无另一产品也能运行。
- Observer 不执行；候选不自动接纳；投递幂等但不承诺恰好一次。

继承任务：本轮新增的有限范围；保留领域边界。

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE11 格式资格与转换回执

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE01

执行内容：
- 核对现有原件保存与隔离 worker，实现逐文件计划、状态、损失报告和引用。
- 逐 store、preview、extract、edit、export、roundtrip 返回版本与资格。
- 复杂 OCR、视频转写和大型解析作为选装 worker，首屏不启动全部模型。

必须产物：
- format operation status
- batch receipts and loss reports
- verified sample manifest

通过条件：
- 真实文本与至少一类现有文档样例闭环，其余格式按实际结果发布。
- 失败可追踪，可保存不冒充原生编辑或无损互通。

继承任务：CB04

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

### BE12 原生桥接与联合验收

优先级 P0；阶段 FIRST_RELEASE；状态 PLANNED。

前置任务：BE02、BE03、BE05、BE06、BE07、BE08、BE09、BE10、BE11

执行内容：
- 测试 Tauri 有限桥与 Core、worker 的身份、取消、恢复、版本和权限。
- 给前端与 ASTRYN 集成环境，真实调用与安装证据分别记录。
- 诊断默认脱敏并提供已知缺口与可回退记录。

必须产物：
- joint integration evidence
- native host qualification
- backend handoff

通过条件：
- 重启、CAS 冲突、取消竞态、过期授权和未知结果有一致读回。
- 源码、CI、安装与人工资格不互相推断。

继承任务：UF13、M01

证据：source_sha, changed_paths, commands_and_exit_codes, artifact_hashes, limitations, rollback_handle。

## 后续范围

- 大型模型自动部署、量化与优化
- 批量 OCR／音视频转写与复杂解析引擎
- 语音音素对齐和神经说话视频服务
- 跨项目授权写入与生产任务联邦
- 通用 Agent、训练、同步与 XR 引擎
