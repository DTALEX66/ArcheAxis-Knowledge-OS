# OpenMAIC 吸收调研（2026-10-19）

> 最新状态：Owner 已授权适配吸收，见[统一决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)。严格 quiz M1 已有产品 adapter、可选学习入口、原件/Document 保存读回；63 项定向前端测试、1 项真实 Rust Core 重启/重放测试及 TypeScript/Vite 构建通过，见[限定回执](../history/repository-consolidation-20261019/current/receipts/AAOS-OPENMAIC-IMPORT-20261019.json)。下述首次调研和纠偏保留其观察时间，不能用其中旧 NOT_EXECUTED 覆盖后继实现；完整课堂、浏览器视觉、原生及安装资格未由这些测试证明。

> 后继[课程 UI 验证](../history/repository-consolidation-20261019/current/receipts/AAOS-CAPABILITY-COURSE-UI-20261019.json)已完成生产前端 bundle 的隔离浏览器预览、键盘核对、保存 UNKNOWN/同请求重试/重开、失败与窄窗口检查；课程选项排版有实际截图修复。该浏览器使用 SYNTHETIC Core，与前述真实 Rust API 测试是两组独立证据，不能拼接成真实 UI→Core 端到端、完整上游课堂或原生/安装验收。

结论：有较高教学能力吸收价值，优先 **ADAPT 课程结构与测验子集**，教学流程作 **REFERENCE**；完整课堂服务和任意生成 HTML 执行 **HOLD**。本轮是公开源码静态研究与证据保全，调研 PASS；运行、部署、模型效果与 AAOS 接入均 UNVERIFIED / NOT_EXECUTED。未安装、启动或执行上游代码，也未修改现有 LM Studio/provider 配置。

## 固定版本与许可

仓库 [THU-MAIC/OpenMAIC](https://github.com/THU-MAIC/OpenMAIC/tree/6b83751a87896df99c47e98c20cea40cec09efb4)，main 固定 `6b83751a87896df99c47e98c20cea40cec09efb4`，提交 UTC `2026-10-18T14:09:42Z`。根 package 1.2.1；独立 `@openmaic/dsl` 包 0.11.3、无运行依赖。根 LICENSE 为 MIT，Copyright (c) 2026 THU-MAIC。源码分发必须保留完整许可与版权；模型、字体、音视频及其他素材的权利分别核实。公开源码可读不等于全部资产可重分发。

本地证据根：`.project-local/archives/oss-intake-20261019/OpenMAIC/6b83751a87896df99c47e98c20cea40cec09efb4/`。MANIFEST.json 记录 18 个指定 UTF-8 文本的字节数、Git blob SHA-1、SHA-256、固定版本读取 URL；逐文件核对通过。这是研究所需的源码子集，**不是完整仓库镜像**。首次大 tree 响应 IncompleteRead 未当作成功，改用指定路径 contents API 完整读取和 blob 校验；没有更改网络或认证设置。

## 实现与项目映射

| 分型 | 实际实现与证据 | AAOS 处理 |
|---|---|---|
| ADAPT | [Stage/Scene 契约](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/packages/%40openmaic/dsl/src/stage.ts#L21)：slide、quiz、interactive、pbl，场景与动作有独立类型 | 首批仅章节文本、学习目标和测验，转换为绑定知识及来源版本的课程候选；复用现有教学界面 |
| REFERENCE | [plan](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/server/generation/run/plan.ts#L22)：材料分析→研究→大纲→确认→角色→逐场景内容/动作/旁白；[engine](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/server/generation/run/engine.ts#L1182) 将课程写入与检查点置于事务并持有 lease | 映射既有 Core job 的取消、重试、恢复与失效状态；禁止新建第二数据库写入真相 |
| REFERENCE | [action](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/packages/%40openmaic/dsl/src/action.ts#L30) 实现元素聚焦、语音、白板图形/公式、讨论；[PBL evaluator](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/pbl/v2/agents/evaluator.ts#L155) 有里程碑、最终评价及视觉模型路径 | 借鉴教学节奏与候选反馈；AI 评分不能证明掌握，保留人工复核 |
| HOLD | Next16/React19、长期 Node22.19+、PostgreSQL16 与 agent runtime；语音克隆、视频服务、任意 HTML | 不整体迁入现有 Tauri/React/Rust 主宿主；不引入第二模型路由或持久化系统 |

AAOS 已有实际接点：`frontend/src/components/KnowledgeCoursePanel.tsx` 的课程候选/知识来源版本/derived_only/人工复核；`frontend/src/spaces/CanonicalLearningJourneySpace.tsx` 的课程与学习旅程；`frontend/src/api/core.ts` 的 Core bridge。当前 `course_from_knowledge` **不是**通用 MAIC 导入接口；保存导入课程需要补正式合同及 Rust Core 回执/读回，不能仅前端写 localStorage。

## 必须改造的边界

1. **结构有效不代表安全或正确。** [validate.ts](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/packages/%40openmaic/dsl/src/validate.ts#L1) 明确只是结构校验子集。[stage.ts:96](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/packages/%40openmaic/dsl/src/stage.ts#L96) 说明新增 voice 字段不升 DSL_VERSION，但旧严格 schema 会拒绝。Adapter 必须固定包/schema 版本，限制数值、文本长度、场景数量、重复 ID、未知字段和引用；保留原载荷摘要，拒绝不能静默丢弃或报成功。
2. **研究步骤可能把材料发送到模型和搜索服务。** [research.ts:36](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/server/generation/steps/research.ts#L36) 截取教材供查询改写，并调用 searchWeb。AAOS 默认禁用外搜，沿用已授权模型与材料范围；另行授权才可出网。
3. **iframe 隔离不等于断网。** [InteractiveIframeHost.tsx:437](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/components/scene-renderers/InteractiveIframeHost.tsx#L437) 不授予 allow-same-origin，但仍允许 scripts/forms/popups。本轮不将任意生成 HTML 带入 Tauri；首批只接受结构化内容。不是已验证的漏洞利用结论。
4. **OpenAI-compatible 不等于 LM Studio 已验证。** [slot 解析](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/server/model-config/resolve-slot.ts#L89) 与 [模型解析](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/server/resolve-model.ts#L197) 有能力/锁定/路由规则，私网 endpoint 还受 SSRF 约束。不得为了兼容上游重新启用 Ollama、弱化网络校验或修改用户配置；需在隔离测试中另验工具调用、schema、上下文预算与取消。

## 进入项目的最小任务

这些是研究形成的候选任务，记录于 intake 并由当前 UI 执行记录链接，不能当作实现完成或独立权威队列。

| ID | 任务 | 当前状态与验收 |
|---|---|---|
| OSS-OMA-001 | 固定许可与源码证据、映射实际接点 | PASS / 静态研究；18 个文本完整性校验，不含运行效果 |
| OSS-OMA-002 | 纯 openmaicCourseAdapter：章节文本/quiz→课程候选，含知识版本和来源修订 | NOT_EXECUTED；空/单/多场景、重复ID、类型不匹配、未知字段、超预算、无答案题、过期引用都必须明确拒绝 |
| OSS-OMA-003 | 在现有 KnowledgeCoursePanel 增加导入预览，补 Core 合同并读回 | NOT_EXECUTED；模拟与真实 Core 分别验证，保存失败不报成功，拒绝/取消不留半成品，不加载远程资源 |
| OSS-OMA-004 | 大纲确认与 checkpoint/lease 恢复映射到现有 job | NOT_EXECUTED；先完成002/003；断开、重开、重复命令、版本失效与取消后重放均要覆盖 |
| OSS-OMA-HOLD | 完整服务、任意HTML、完整多Agent课堂、语音克隆/视频 | HOLD；需要独立范围、运行隔离和资产许可验证，本次没有安装或改造 |

本轮没有证明“一键完整课堂”“所有多模态离线”“评分证明学习效果”或商业落地。模型输出质量、完整格式往返、屏幕阅读器、原生宿主和安装验收均未执行。

## 2026-10-19 实施边界纠偏

这是后续精读所得的实施范围更正，不改写上面首次静态研究的原始结论。OSS-OMA-002/003 继续由当前执行记录跟踪，不是新增第二个任务队列。

- **实际输入**：[classroom-zip-types.ts](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/export/classroom-zip-types.ts) 与 [导出组装](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/lib/export/use-export-classroom.ts) 表明 `manifest.json` 是 `{formatVersion,exportedAt,appVersion,stage,agents,scenes,mediaIndex}`，`formatVersion` 为 1；导出场景没有 `id/stageId`。首批接受该 manifest 文件，不宣称已经支持 `.maic.zip`、HTML 或任意 Stage 对象导入。
- **保真边界**：[slides.ts](https://github.com/THU-MAIC/OpenMAIC/blob/6b83751a87896df99c47e98c20cea40cec09efb4/packages/%40openmaic/dsl/src/slides.ts) 的 canvas 还含位置、HTML 文本、字体、图形、表格、公式、代码、script 和媒体。抽文本不能冒充保真转换。因此首批 M1 收敛为严格 quiz 子集；其他场景、非空动作／白板／媒体、启用多角色须明确拒绝转换，并可由用户另选仅保全原件。完整 slide 进入 CAP-0060 的后续保真适配。
- **领域身份**：外部内容保存为 `candidate / external_unverified / human_review_required`。不能随意绑定一条已接受知识而称来源核验通过，也不能直接复用 `course_from_knowledge` 伪装其生成物。
- **接入方式**：通用外部课程候选合同＋独立 OpenMAIC 格式 adapter，按需显示在既有学习入口；教学流程后续作为模板／受控技能。没有品牌专属主页面、第二模型路由或 PostgreSQL。
- **持久化路径**：现有 `source_import` 保全原字节；`source_original` 比较字节和 SHA；`document_create` 在 `editor_json.attrs` 保存版本化 typed 候选与原件身份；`document_get` 核对内容、来源、版本和内容 SHA，再做重启读回。原件与文档是两步保存，文档失败必须明确“原件已保全，课程尚未保存”，保留冻结创建请求。尚未实现这些 adapter 行为。
- **测验语义**：题型 `single/multiple/short_answer`，选项是 `{label,value}`、参考答案是可选 `string[]`；验证答案引用、唯一 ID、顺序、数量与预算。无答案不判对，短答不按字符串相等写入掌握；参考答案只代表课件提供内容，`commentPrompt` 仅保全，不送模型执行。

上述三个补充源码在固定 SHA 只读获取，独立补充清单为 `.project-local/archives/oss-intake-20261019/OpenMAIC/6b83751a87896df99c47e98c20cea40cec09efb4/MANIFEST-extension-20261019.json`。不重写原 18 文件清单或已绑定它的历史收据。本次仍没有安装、运行或执行上游代码。

## 后继 M1 实现与证据（2026-10-19）

上文 NOT_EXECUTED 是首次研究/纠偏时点。当前严格 quiz adapter、通用外部候选和可选学习入口已有实现，实际覆盖及失败历史见[限定回执](../history/repository-consolidation-20261019/current/receipts/AAOS-OPENMAIC-IMPORT-20261019.json)，进度见唯一[当前执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。原件保全和文档创建是两步，部分失败按阶段保留，不能承诺拒绝后完全不留原件。完整课堂、slide、多模态、模板/技能和原生安装仍未据此通过；后续基于同一任务继续，不重开已通过的静态调研。
