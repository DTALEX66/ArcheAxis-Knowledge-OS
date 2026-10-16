# GF02 抽离共享会话管理器（小栖学习伴侣 v1）

分支 `feat/astryn-learning-companion-v1` · 任务包 ASTRYN-COMPANION-20261013 · 日期 2026-10-13

## 交付内容

| 交付物 | 位置 | 说明 |
| --- | --- | --- |
| 会话管理器 | `src/interaction/session-manager.ts`（新增） | `CompanionSessionManager` 拥有控制器、transcript、请求与取消状态；对外只暴露快照订阅。单飞提交（同会话在途只允许一个请求，`SESSION_BUSY`，`EMPTY_INPUT`/`DISPOSED` 各有独立理由）；`retainView()/release()` 引用计数多视图订阅同一状态；`configurePorts()` 对四个端口 identity 比对，变了才重建控制器并重置会话 |
| 零视图规则 | 同上 | 视图数为 0 时 `renderingPaused=true`：快照推送暂停，但业务照常——提交、流式结束入账、宿主回执入账、档案变更都不受影响（在途请求不被中断） |
| StrictMode 安全生命周期 | 同上 | 构造函数纯（不 start、不 attach）；`disposeWhenUnobserved:true` 时离视图采用 0ms 延迟终结，同一批次内重新 retain 会取消终结——React 18 严格模式的"挂载→清理→再挂载"不会销毁被丢弃实例的会话，也不会把在用会话误终结 |
| 档案加载去重 | 同上 | 同一 store 的 `ensureProfileLoaded()` 返回同一 promise，重复调用不重读、不覆盖用户刚做的修改 |
| 呈现层改造 | `src/presentation/companion-shell.tsx` | 组件不再持有控制器与端口状态，改为 `retainView` + `subscribe` 快照；`manager` 可由外部注入（多视图共享），未注入时自建并 `disposeWhenUnobserved` |
| 开发宿主接线 | `dev-host/app.tsx` | `useMemo` 按 `sessionId` 创建共享管理器，`panel` 与 `embedded` 呈现接同一实例 |
| 控制器修正 | `src/interaction/companion-controller.ts` | 历史补记（本轮用户消息与助手回复落账）后补 `publish()`：此前订阅方会永久缓存住缺本轮回复的 transcript 快照 |
| 会话测试 | `tests/interaction/session-manager.test.ts`、`tests/presentation/shared-session.test.tsx`（新增） | 8 + 3 项：单飞、构造与挂载分离、零视图、风格变化不丢会话、换端口重建、档案去重、dispose 幂等、延迟终结；双视图共享/关闭一个呈现不打断/一端改风格两端生效 |

## 验收对照

| 验收条目 | 证据 |
| --- | --- |
| 同一请求只执行一次 | `session-manager.test.ts` 单飞用例：`EMPTY_INPUT` → 在途返回 `SESSION_BUSY` → 完成后 `accepted`，端口 `streamCalls===1`；浏览器实测两轮各一条回复无重复 |
| 切换呈现记录连续 | `shared-session.test.tsx`：两个呈现 `viewCount 2`、一次提交端口只被调 1 次、两侧 UI 同步；关闭 `embedded` 后重开立即拿到含全部历史（含新会话前）的完整记录；浏览器实测 `panel→embedded` 切换后记录原样保留 |
| 风格变化不丢会话 | 测试：在途改回复长度后 roles 仍 `['user','assistant']`，下一轮提示词换新风格（`回复控制在两句以内。` vs 第一轮 `回复保持在一到三句。`）；浏览器实测设置里改"回复长度→brief"并关闭后记录不丢 |
| 无视图时暂停渲染并保留业务请求 | 测试：零视图时 `renderingPaused=true`、快照推送计数冻结，但在途流照常完成并入账 transcript，宿主回执照常入账 `awaiting_approval` |

## 证据（本机实测）

### 门禁

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-221934.log`
- 阶段：`STAGE=lint EXIT=0`、`typecheck EXIT=0`、`test EXIT=0`、`build EXIT=0`、`record EXIT=0`、`anchors EXIT=0`
- 回执：`docs/verification/gates.json`，72 个源文件，树哈希 `9a04f3a025a0d8b1…`，全绿=true；封存时 `git.head` 为 `3a85821a55cd`（本任务提交落在其上，回执的 worktreeNote 指示以 git status 判定）
- 测试：19 个文件 147 通过（GF01 基线为 17 文件 136 通过）；新增 `tests/interaction/session-manager.test.ts`（8 项）与 `tests/presentation/shared-session.test.tsx`（3 项）
- 构建产物：`index-COfKJKMr.js` 221.05 kB（gzip 72.68 kB）

### 开发宿主浏览器实测（DOM 结构证据）

- `npm run dev` → `http://127.0.0.1:5183/`（日志 `.project-local/runs/dev-gf02.log`，0 条错误），`VITE_ASTRYN_ALLOW_SYNTHETIC=1`
- 实测字符串：来源条显示 `模型来源：synthetic · 证据级别：SYNTHETIC · 可用`；第一轮输入"在吗"得到唯一一条回复 `SYNTHETIC[合成夹具] 我在的，不过这条回复来自测试脚本，不是真实模型。…`，状态回 `idle`，无重复渲染；第二轮同会话再发一条后 transcript 共 4 条（2 问 2 答），每条回复各出现一次
- 呈现切换 `panel → embedded` 后 `astryn-root--embedded` 生效、记录与在途状态连续；设置里改"回复长度"并关闭后记录连续
- 控制台仅 vite 连接与 React DevTools 提示，0 条错误
- 说明：本轮浏览器证据为结构化 DOM 读数（browser-use 工具在该表面无截图能力，如实记录）；操作经由页面测得的真实点击路径（工具层 `Enter`/uid 点击在本表面未触发提交，改用节点自身 `click()` 后走通）

### 边界核对

- `tests/boundary/no-sensitive-apis.test.ts` 全绿：会话管理器不落浏览器持久化、不落文件、不引入采集接口
- 合成与真实分隔保持：合成端口 `evidenceLevel='SYNTHETIC'` 恒不变，浏览器里 UI 明确标注"合成夹具"

## 如实记录的修正

1. **控制器历史补记后未推送**：`AstrynCompanionController.submit()` 在 `finally` 中给 history 补记助手回复后没有 `publish()`，而会话管理器的快照缓存正是在 `publish()` 时构建——会导致订阅方拿到缺本轮回复的 transcript。旧壳每渲染都重读控制器所以未暴露；抽离后被 8 项新测试当场拦下，已补 `publish()`。这是共享状态抽离的典型收获：原来"碰巧对"的时序变成了显式的信号。
2. **同句两遍**：修好第 1 条后，已落账回复会在 transcript 与 `state.streamedText` 各渲染一次（reducer 只在 `turn.submitted` 清空流式文本）。呈现层对"已落账的尾部回复"去重，浏览器实测确认消除。

## 阻塞与残余

- **宿主会话流 BLOCKED_BY_HOST_CONTRACT**：`depends_on` 里的 BE05（宿主会话流）未接通，本任务的会话管理器在 ASTRYN 侧完成并全部走现有端口（会话端口/合成端口/合成宿主）；真实宿主会话流的接入仍等宿主合同，不以合成流补齐正式结果。
- 开发宿主按 `sessionId` 重建管理器；跨会话持久化不在本任务范围（GF08 首页嵌入与侧边统一呈现时会复用同一管理器实例）。
- 多视图共享的"关闭一个呈现不打断"已由测试覆盖；真实窗口级多视图（原生浮层 + 嵌入）待 GF08/GF10。

## 回滚

本任务线性提交于 `feat/astryn-learning-companion-v1`；回滚 = `git revert` 本提交。未改写已推送历史。
