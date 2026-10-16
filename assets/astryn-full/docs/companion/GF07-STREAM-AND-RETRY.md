# GF07 真实文本流与取消恢复（交付说明）

任务包 `ASTRYN-COMPANION-20261013` · 分支 `feat/astryn-learning-companion-v1` · 依赖 GF04（已完成）。

本卡三条 work 的落点：①输入/材料标签/流式文本/错误/重试/停止保持连续；②请求 ID、序号、恢复与晚到事件按正式流合同处理；③重试保留输入，但未知执行结果先查询原请求。核心新增是**正式流合同里的 `lookupRequest?` 可选端口能力**与**重试候选/处置三态**（RESENT / RESENT_WITHOUT_LOOKUP / HELD_BACK）。

## 1. 交付物

| 路径 | 内容 |
| --- | --- |
| `contracts/conversation.ts` (modified) | 正式流合同补全：`AstrynRequestLookupOutcome`（completed/in-progress/not-found/unknown）、`AstrynRequestLookup`、`ASTRYN_UNKNOWN_OUTCOME_FAILURE_CODES = [NETWORK, TIMEOUT, MALFORMED_STREAM, ABORTED, UNKNOWN]`、端口可选方法 `lookupRequest?(requestId)` 与逐条文档注释（请求身份=requestId；重试必须用新 ID；乱序/重复由守卫按 seq 处理；已结算事件作废；端口无查询能力必须如实上报）。 |
| `src/interaction/companion-controller.ts` | `RetryCandidate` / `RetryDisposition` / `ControllerRetryResult` 类型；`retry()`：未知结果先 `lookupRequest`（顺序可断言），completed/in-progress ⇒ `HELD_BACK` 不重发（防重复执行）且候选保留；端口无查询能力 ⇒ `RESENT_WITHOUT_LOOKUP` 如实标注；重发始终新 requestId 且按成功附带过的片段重建材料标签。`submit()` 重构：提交时捕获材料标签快照（`fragmentsByRequest`），`activeSubmissions` 计数、失败/中止后置 `lastInterrupted`；用户停止 ⇒ 候选 `cause:'cancelled'`、`failureCode:'ABORTED'`（属未知结果集）；成功一轮清空候选。 |
| `src/interaction/session-manager.ts` | 快照新增 `pendingAttachments`（未提交材料标签）与 `retry`（重试候选）；`retry()` 与 `submit()` 共享单飞标志（忙碌返回 `SESSION_BUSY`）；`removePendingContext(index)`；修复 `attachContext` 不改无效化导致标签条不出现的缺陷（现与移除对称 `invalidate()`）。 |
| `src/adapters/synthetic-conversation.ts` | `lookupRequest`：仅“此刻正在流式输出”报 `in-progress`，其余一律 `not-found`——合成夹具**不保留已结束请求的任何记录**（不写正式记录），并注释明确。 |
| `src/presentation/companion-view.tsx` | `Composer` 改为受控（`value/onValueChange/attachments/onRemoveAttachment/...`），材料标签条 `astryn-composer-tags`（逐条 `astryn-attachment-{i}` + 可访问移除按钮）；新增 `RetryBar`（保留文本 + 结果语义预告两态 + 单一重试按钮，只转发意图不自作重发）。 |
| `src/presentation/companion-shell.tsx` | 草稿归外壳持有（设置开关/隐藏角色/失败重试都不吞输入）；重试处置→回执文案四态（HELD_BACK 含"输入已放回输入框"、RESENT_WITHOUT_LOOKUP 标注宿主合同缺项、lookup unknown 提示可能重复执行、已知未执行直接重发）。 |
| `src/presentation/astryn.css` | `.astryn-composer-tags`、`.astryn-chip--tag`、`.astryn-chip-remove`（含 focus-visible）、`.astryn-retry`（warning 语义令牌；容器内文字改用 warning-text 以满足对比度门禁）。全部走令牌，无硬编码色。 |
| `src/index.ts` | 导出 `ControllerRetryResult`、`RetryCandidate`、`RetryDisposition`、`AstrynRetryOutcome`。 |
| `tests/interaction/stream-retry.test.ts` (new, 10) | 失败重试保留输入+材料标签且新请求身份；未知结果 lookup 顺序 `['stream','lookup','stream']` 与 `lookupArgs=[原ID]`；completed/in-progress ⇒ HELD_BACK（streamCalls 恒 1）；UPSTREAM_REJECTED 已知 ⇒ 不查询直接重发；取消 ⇒ 候选已停止/ABORTED 未知结果 ⇒ 先查再发；**取消后晚到片段证词**（迟到的 stream.delta 与迟到权威 task.completed ⇒ SETTLED_REQUEST×2、streamedText 冻结、taskId 保持空）；端口忽略中止 ⇒ 循环断开后文本不再派发；无端口 ⇒ MODEL_UNAVAILABLE 为已知结果直接重发且输入不丢；管理器快照同步（候选/标签/SESSION_BUSY/成功清空）；合成夹具 lookup 三态。 |
| `tests/presentation/composer-continuity.test.tsx` (new, 5) | 草稿穿设置开关与隐藏；材料标签可见/可移除/提交后消费；**关视图≠停止**（隐藏期间跑完、恢复可见）；**停止≠关视图**（中断 + 晚到片段不进回复 + 候选已停止）；重试条全景（保留文本、先查询预告、回执文案、重发完成）。 |

## 2. 验收对照（任务包 GF07 卡）

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 输入、附件或材料标签、流式文本、错误、重试和停止保持连续 | PASS | 草稿在设置开关/隐藏角色/失败后均保留（UI 测试 + 浏览器实测三连：设置↔返回、隐藏↔恢复，输入值均原样）；材料标签提交前可见可移除、被接受提交后消费干净；失败后重试条展示「输入已保留——「原文」」；停止后同样保留。 |
| 请求 ID、序号、恢复与晚到事件按正式流合同处理 | PASS | 合同文件写明 requestId 身份与重试新 ID 规则；重试实测 `streamCalls[1].requestId ≠ streamCalls[0].requestId` 且消息与材料标签一致重建；乱序/重复/晚到由既有守卫链（seq 单调 + 结算集合）处理，GF07 补晚到证词测试：取消后迟到的增量与迟到的权威任务完成事件均被 `SETTLED_REQUEST` 静默丢弃（审批数=2），流式文本冻结、任务状态不被改变。 |
| 重试保留输入，但未知执行结果先查询原请求 | PASS | 未知结果集（NETWORK/TIMEOUT/MALFORMED_STREAM/ABORTED/UNKNOWN）先 lookup：顺序断言 `['stream','lookup','stream']`、lookupArgs 为原请求 ID；completed/in-progress ⇒ `HELD_BACK`（零重发，防重复执行）且输入放回输入框；`not-found` ⇒ 按新请求重发；端口无能力 ⇒ `RESENT_WITHOUT_LOOKUP` 如实标注（不假装查过）；已知未执行（UPSTREAM_REJECTED/MODEL_UNAVAILABLE）⇒ 不查询直接重发。 |
| 真实调用可用，合成夹具显著标注且不写正式记录 | PARTIAL（真实调用 UNVERIFIED） | 「真实模型调用」本次会话无上游配置（无 dev 代理上游凭证），不主张可用：openai-compatible 适配器与 SSE 解析由适配器测试覆盖，非宿主集成（与 A17 同口径）。合成侧 PASS：全部回复带 SYNTHETIC 标签（浏览器实测截图面缺失，DOM 读数：`SYNTHETIC[合成夹具] 我在的…` + `astryn-evidence-tag--synthetic`）；合成夹具不写正式记录由构造实证：会话运行时无记忆/学习存储引用，`lookupRequest` 对已结束请求恒 `not-found`（单测三态）。 |
| 停止与关视图不同，取消后晚到片段不继续动作或回复 | PASS | UI 测试：隐藏期间这一轮继续跑完、恢复后可见且回到空闲、无重试候选；停止 ⇒ `interrupted` + 候选 `已停止（ABORTED）`；端口忽略中止信号时晚到「后半」不进入任何呈现（streamedText 恒「前半」）。浏览器实测停止全链路：microtask 捕获停止 ⇒ `状态：interrupted` + 重试条「上一轮已停止（ABORTED）：输入已保留——「微任务里点停止」」⇒ 点重试 ⇒ 回执「已先查询原请求（宿主无该请求记录）：按新请求重发。」⇒ 重发完成（转录尾部：用户消息×2 + 完整合成回复）。 |

## 3. 门禁与封存（GF07 终局）

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-232954.log`：**lint=0 typecheck=0 test=0 build=0 record=0 anchors=0**（六阶段全 0，一次通过）。
- 测试：**32 文件 / 293 通过**（其中 GF07 新增 15：stream-retry 10 + composer-continuity 5）。
- 封存收据 `docs/verification/gates.json`：源码树 **93 文件**，树哈希 `d0a223a0dd84e7e41b197fb77c2914e704d48886fe782dc6a748b61029321008`；`allGreen: true`；`git.head` `f1bf14e`（GF07 提交前的分支头）。
- 构建产物（实测磁盘字节）：`index-CbOSzxQX.js` 281,523 B，sha256 `1cf192baaa4f44a8760d0c28632cf3e61201d9f9c952d4b1cd8daca97c24d2a1`；`index-jmmVyAgy.css` 10,076 B，sha256 `f9ee4dba2d3945b103f551f7d45539707068911c40cf585785c4376a9c24a218`。

## 4. 浏览器实测（Dev Host，DOM 读数）

`VITE_ASTRYN_ALLOW_SYNTHETIC=1` 起 Vite（127.0.0.1:5183），实测后按 netstat PID 14584 终止、端口释放：

- 装载：标题「星栖 ASTRYN · 开发宿主」；证据标签 `scripted-synthetic / SYNTHETIC`；模型芯片 `synthetic-fixture / SYNTHETIC`；学习/记忆面板同在。
- 草稿连续性：输入「浏览器里的草稿」→ 设置开（输入框消失）→ 返回（草稿原样）→ 隐藏角色 → 恢复（草稿原样）。
- 无模型路径：切「无模型」提交 ⇒ 重试条「上一轮未完成（MODEL_UNAVAILABLE）：输入已保留——「无模型的一问」」+ 预告「执行结果已知（未执行）：重试将直接重发。」⇒ 点重试 ⇒ 回执「执行结果已知未执行：已直接重发。」（重试后仍无模型，候选按新身份重新出现；失败芯片 `MODEL_UNAVAILABLE：未配置获准模型接口…`）。
- 停止：提交后微任务内点「停止生成」⇒ `状态：interrupted`、候选「已停止（ABORTED）」（合成脚本零延迟，停止窗口为亚帧级，需微任务捕获；时序敏感语义由受控时钟测试覆盖）。
- 停止→重试→查询→重发：点重试 ⇒ 「已先查询原请求（宿主无该请求记录）：按新请求重发。」⇒ 重发完成，转录 7 条（两次用户消息如实入账 + 完整合成回复）。
- 资料解释回归：选中夹具文档片段 ⇒ 「解释选中内容」⇒ 上下文行「SYNTHETIC获准读取上下文：《合成夹具·宿主边界说明》v1 · 选区「本文档是合成测试夹具…」」+ 回复落账 + 材料标签消费干净。
- 控制台：3 条（2 条 vite debug + 1 条 React DevTools info），**0 错误**。
- 证据形态：结构化 DOM 读数（本会话无截图面）。

## 5. 诚实边界

- **真实模型与真实宿主流 UNVERIFIED**：本会话无上游模型凭证；`lookupRequest` 属新增端口能力，开发代理（openai-compatible）端口未实现它 ⇒ 走 `RESENT_WITHOUT_LOOKUP` 如实标注；AAOS 宿主的"原请求查询"面 `BLOCKED_BY_HOST_CONTRACT`。
- **晚到权威事件丢弃的物理前提**：依赖既有守卫链（GF04），GF07 只补证词（取消后迟到增量/迟到权威完成被 `SETTLED_REQUEST` 丢弃）。端口忽略中止信号本身是端口缺陷，客户端只能保证"不再派发、不再渲染"。
- **合成脚本零延迟**：浏览器内停止窗口亚帧级（本次以微任务捕获完成实测）；停止/乱序/时序语义的正式证据在受控时钟测试（`tests/interaction/stream-retry.test.ts`）。
- **重发会如实产生第二条用户消息**：转录记录两次真实请求（可见于浏览器实测尾部），不做"合并显示"粉饰。
- 已知盲区：`dev-host/app.tsx` 接线无测试载体（与 GF05/GF06 同一盲区，仅浏览器实测）；观测到 devhost 来源条展示的是"配置解析结果"而非覆盖后的实时状态（切「无模型」后来源条仍显示 synthetic 可用，实时真值以壳层模型芯片 `MODEL_UNAVAILABLE` 为准）——dev 宿主展示细节，不影响产品语义。

## 6. 回滚

`git revert` GF07 提交（分支 `feat/astryn-learning-companion-v1` 上单个提交）。全部为增量：新文件 `tests/interaction/stream-retry.test.ts`、`tests/presentation/composer-continuity.test.tsx`；其余为既有文件修改（契约新增为**可选**成员与新增类型，不改既有成员形状，回滚后旧端口定义仍可编译）。无迁移、无宿主侧写入。
