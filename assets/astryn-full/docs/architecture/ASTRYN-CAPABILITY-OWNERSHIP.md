# ASTRYN / AAOS 能力归属与本轮实现边界

日期：2026-10-13。依据：`PROJECT_CONTRACT.yaml` 的 `architecture` 段、启动任务第 1 节、`docs/architecture/AAOS-HOST-CAPABILITY-MAP.md` 的只读核验结论。

## 1. 归属表

| 能力 | 归属 | 本轮落地位置 | 实际状态 |
| --- | --- | --- | --- |
| 人格与角色配置 | ASTRYN | `contracts/character.ts`、`src/companion/prompt-composer.ts` | 已实现（分节结构化档案 + 版本化提示组装，非单块大提示词） |
| 陪伴行为与互动规则 | ASTRYN | `src/companion/reducer.ts`、`src/presentation/*` | 已实现（输入/请求生命周期驱动） |
| 角色情绪表达与状态编排 | ASTRYN | `src/avatar/state-visuals.ts` | 已实现（九态两两视觉可辨，映射表唯一） |
| 形象、表情、口型协调 | ASTRYN | `src/avatar/renderer-registry.ts`、`xiaoqi-raster-renderer.ts`、`xiaoqi-svg-renderer.ts` | 已实现（注册表 AVATAR_RENDERERS：默认 `xiaoqi-raster-v2` = 九态位图静帧〔AI 生成，平台条款〕；`xiaoqi-svg-v1` 原创 SVG = 回退下限 index 0。表情驱动 svg=真实文本事件帧 / raster=静帧；音素口型未实现，不得宣称） |
| 多形态呈现协调 | ASTRYN | `contracts/presentation.ts`、`src/presentation/mode-registry.ts` | 部分：`embedded`/`panel` 已实现，其余三种声明为 P2 阻塞 |
| 角色化上下文呈现 | ASTRYN | `src/presentation/companion-shell.tsx` | 已实现（获准片段带来源与版本渲染，标注 SYNTHETIC） |
| 通用模型适配与路由 | **AAOS** | `src/adapters/aaos-bridge.ts`（只定义契约） | 未接通：Core 无通用流式 chat completion |
| 会话与任务生命周期 | **AAOS** | `contracts/host.ts`、`contracts/action.ts` | 契约已定义；真实宿主未验证 |
| 统一记忆与权威存储 | **AAOS** | `contracts/memory.ts`、`src/memory/policy.ts` | 星栖侧只有候选治理规则；生产读写 `BLOCKED_BY_HOST_CONTRACT` |
| 上下文/选区服务 | **AAOS** | `contracts/context.ts` | 无"当前选区"合同；用合成夹具验证形状 |
| 工具调用、权限审批、审计回执 | **AAOS** | `contracts/action.ts`、`src/adapters/aaos-bridge.ts` | 契约按 job 轮询语义建模；合成模拟器验证链路 |
| 用户资产、配置、迁移 | **AAOS** | 未实现 | 星栖不建第二套 |
| ASR/TTS/音频感知 | **AAOS** | 未实现 | P2 |

## 2. 本轮明确没有做的事

- 没有新建第二套长期记忆主库：`src/memory/synthetic-fixture.ts` 是**进程内 Map**，`dispose()` 即清空，不落盘、不联网；`tests/boundary/no-sensitive-apis.test.ts` 扫描 `src/`、`contracts/`、`dev-host/` 禁止 `localStorage`/`sessionStorage`/`indexedDB`/`document.cookie`/`sqlite`/`writeFileSync` 等持久化面。
- 没有直接写 AAOS 的 SQLite/CAS：星栖侧不存在任何数据库连接；AAOS 侧只被只读核验过。
- 没有建立第二个正式前端：`dev-host/` 是开发宿主，页面顶部与边界声明区都写明"非正式产品"，正式形态由 AAOS 前端挂载。
- 没有引入 Tauri/Rust/Python 后台：M0 无此必要（`package.json` 运行时依赖只有 react/react-dom）。
- 没有默认启用麦克风、摄像头、屏幕采集或系统命令：源码扫描门禁 + 运行期控制台零权限请求。
- 没有让角色身份提升权限：`AstrynHostPort.requestGrant` 与 `AaosMemoryPort.probe` 都不因"是小栖"而放宽；AAOS 的 Consumer 是闭集枚举，星栖未被命名，因此适配器返回拒绝而不是假装成功。

## 3. 权威边界的技术实现（A08/A09）

任务状态的可信链是三重的，任何一环断裂都不会产生"完成"：

1. **类型层**：`AstrynActionReceipt` 只能由宿主签发；模型正文在契约里**没有**能表达"任务完成"的类型。
2. **信封层**：`isTaskAuthoritative()` 要求 `trust==='authoritative'` 且 `source∈{host-action,host-task}`。会话适配器签发的事件被强制降为 `observed`（`src/adapters/conversation-event.ts`），控制器 `rebase()` 再做一次降级。
3. **校验层**：`AstrynReceiptVerifier` 由宿主适配器持有。无校验器或校验失败 → 降级 `observed` → 守卫以 `TASK_EVENT_NOT_AUTHORITATIVE` 拒收并计入审计。

守卫还额外拦了两类容易被忽略的情况（都是本轮实测逼出来的）：判别字段 `payload.kind` 缺失的信封以 `INVALID_EVENT_KIND` 拒收（否则手工拼装的回执会绕过权威检查、在 reducer 里静默落空）；`taskId` 缺失的任务事件以 `TASK_EVENT_MISSING_TASK_ID` 拒收。

## 4. 事件与恢复语义

- 每次请求独立身份：`sessionId` + `requestId`（+ 宿主侧 `taskId`），序号按 `(session, request)` 单调。
- 旧会话、已取消、已完成、重复、乱序事件一律丢弃并计数（`AstrynEventGuard.rejectionCounts`），开发宿主把审计结果直接显示在状态条上。
- 断线恢复：`AstrynHostCapabilities.streamResume` 是显式能力声明。AAOS 现无推送与恢复面，因此适配器返回 `streamResume: false`，星栖不伪造 cursor 续传。

## 5. 待AAOS确认后才能收敛的点

见 `docs/architecture/AAOS-HOST-CAPABILITY-MAP.md` 的"ASTRYN 侧结论"：`GenerationRequest`（一次性问答映射 + 独立流式槽）、`MemoryCandidateWrite`（只产 candidate）、`ConsumerIdentity`（为未来外部消费者枚举留位）、`ActionExecution`（幂等键 + deadline + 以 job 状态为唯一权威事件）。这四项在星栖侧已按当前理解建模，但**接口最终形状属 AAOS 领地**，需集成任务授权后对齐。
