# ASTRYN 全量项目审计（N2）— 2026-10-14

审计时点：main @ `4163d79`（工作树含 N1「MINIMAX 光栅人物接入」未提交变更：22+3 PNG、schema v2 清单、默认渲染器切换、门禁重封为 104 文件树）。
方法：4 路只读子智能体按切片全量读取代码/测试/脚本/文档/配置（未运行构建与测试，结论均为字节读证）；主控对 S1 级发现逐条复核原始字节。行号为审计时点，N3 修复后可能漂移。
严重度：S1（高，可能造成错误事实或误提交）> S2（中，claim 与行为不符/守卫缺失）> S3（线索级缺陷）> S4（措辞/死代码级）。

## 切片结论

| 切片 | 范围 | 结论 |
|---|---|---|
| A | contracts/** + src/core | PARTIAL：2×S2（AAOS 任务终态缺失、位图失败回退未实现）+ 12×S3 |
| B | src/presentation/** + dev-host/** | PARTIAL：3×S2（系统 RM 下设置未禁用、工具栏 RM 被静默复位、代理 abort 时序失效）+ 10×S3 |
| C | tests/** + scripts/** | PARTIAL：2×S1（九态可辨断言双重恒真、回执对阶段集合与退出码 fail-open）+ 8×S2/S3 |
| D | docs/** + CI + 根配置 | PARTIAL：1×S1（`虚拟人物/` 未忽略，150 个未跟踪文件可被整目录提交）+ 大量文档漂移 |

## 发现清单

### A 切片（contracts + src 核心）

- **A1 [S2]** AAOS 任务状态默认归为 `executing` 并无限轮询——`src/adapters/aaos-bridge.ts:491-516`：状态三元表达式对未知值一律落到 `'started'`，仅 `completed/failed` 终止；宿主回 `cancelled/denied` 等时永远显示"执行中"，`setInterval` 不停、任务被无限 `task.progress` 推动。
- **A2 [S2]**「位图缺失/渲染失败 → v1 SVG 下限」未实现——`src/avatar/renderer-registry.ts:7`、`src/avatar/xiaoqi-svg-renderer.ts:12`、`STATE-ASSET-INDEX.json:61` 三处声称该下限；实际 raster 是裸 `<img>`（`xiaoqi-raster-renderer.ts:51`），全仓无 `onerror`/加载失败处理；PNG 当前全部未跟踪，失败时只显示裂图。✅主控复核（代码与注释原文）
- **A3 [S3]** `selectAvatarRenderer` 是公开 API 却丢弃 `exact:false` 信号——`renderer-registry.ts:30-32`、`src/index.ts:117`。
- **A4 [S3]** 回执无会话关联：`ingestReceipt` 用当前会话盖章——`src/interaction/companion-controller.ts:462-475,503`、`contracts/action.ts:26-38` 无 `sessionId`；`switchSession` 后旧会话回执可移动新会话任务状态。潜在（当前 dev-host 换会话即换控制器）。
- **A5 [S3]** reducer 拒绝事件静默丢弃（审计计数少报）——`companion-controller.ts:242-243` 注释称"计入审计"，`247-259` 的 `if (!result.applied) return;` 丢弃 `result.note`。
- **A6 [S3]** 模型可用探测直接改 state 不派事件、不 bump revision——`companion-controller.ts:151` 注释 vs `162-166`。
- **A7 [S3]** machine-answer 端口 `availability()` 恒 false，而 `stream()` 真调用、submit 不设门——`aaos-bridge.ts:231-237,240-273`；`companion-controller.ts:287-293`。两信号矛盾。
- **A8 [S3]** `repeatText` 夹具选项不可兑现且无人使用——`synthetic-conversation.ts:18-19` vs `88-89`（每次 `seq++`，守卫仅按 seq 去重）。
- **A9 [S3]** 守卫/控制器集合无界增长——`session-guard.ts:42,64-79`（`settled` 只增不删、`seqByKey` 不清）；`companion-controller.ts:89,214-218`。
- **A10 [S3]** 记忆治理对非陪伴消费方在 view/export 路径被绕过——`src/memory/manager.ts:160-173,307-330` 未过 `decideRead`（`contracts/memory.ts:89-92` 声称强制）；禁读表仅存在于夹具内部。
- **A11 [S3]** `decideLifecycle` 注释称"宿主回执"，实为静态可信名单 + 本地自签 receiptId——`src/memory/policy.ts:44-46,55`、`synthetic-fixture.ts:124`、`manager.ts:332-341`。
- **A12 [S3]** 注入不变量仅类型层：renderMarkup 原样插值 frame 字段——`xiaoqi-raster-renderer.ts:51-52`、`xiaoqi-avatar.ts:41-43`；公开 API 传非联合值会产出 `src="undefined"`/属性注入。
- **A13 [S3]** 取景档语义被新默认驱动丢弃（位图不做裁切）——`xiaoqi-raster-renderer.ts:36-38` vs `contracts/avatar.ts:39-42`；avatar 档 96px 槽渲染整幅而非头肩近景。
- **A14 [S4]** `renderer-registry.ts:13`「已回退默认」措辞与现状不符（默认已是 raster）。
- **A15 [S4]** 死导出/死参数：`assertStateHasDistinctVisual`（无使用）、`scopesOf`（无使用）、`ASTRYN_TASK_STATES_REQUIRING_RECEIPT`（无消费，reducer 另硬编码同表）、`toEvents(request, nextSeq)` 两参数 `void`。

### B 切片（presentation + dev-host）

- **B1 [S2]** 系统 prefers-reduced-motion 下，设置页"减少动效"复选框未禁用、无理由、可持久化相反值——`companion-settings.tsx:269-277` vs 工具栏版 `companion-shell.tsx:379-386`（后者正确禁用+理由）。违反不变量「系统覆盖在应用内不可取消」。
- **B2 [S2]** 工具栏"减少动效"开关被任意档案变更静默复位——`companion-shell.tsx:202-204`（`useEffect([profile])`）vs `386` 行只改本地态；随后任一档案改动都会把本地覆盖重置回档案值。
- **B3 [S2]** 开发代理"客户端断开即中止上游"监听挂载时机失效——`dev-host/server/dev-model-proxy.mjs:113-116`：`req.on('close')` 挂在 `await readBody(req)`（99 行）之后；Node ≥16 请求体读完即触发 close，监听永不再触发；客户端中断时上游 fetch 继续烧额度/超时。
- **B4 [S3]** 档案存未注册 rendererId 时单选组无一项选中（画面由 SVG 下限驱动）——`companion-settings.tsx:250`；控件状态与渲染事实相反，仅小字解释。
- **B5 [S3]** radio `name` 未按实例隔离，dev-host 多面板设置会串成一个单选组——`companion-settings.tsx:243-251`。
- **B6 [S3]** 记忆面板 4 个控件无程序化标签——`dev-host/memory-panel.tsx:178,185,192-198,222-227`（两 select 无 label/aria-label）。
- **B7 [S3]** 切"无模型"后来源条仍显示配置可用——`dev-host/app.tsx:43` vs `194-199`；同屏两处读数矛盾。
- **B8 [S3]** 代理超时环境变量名与示例不一致：代码 `ASTRYN_DEV_MODEL_TIMEOUT_MS`（`dev-model-proxy.mjs:27`）vs `.env.example:21` `ASTRYN_DEV_PROXY_TIMEOUT_MS`；按示例设置无效。
- **B9 [S3]** 代理头注声称可用 `.env`，但 npm script 不加载 `--env-file`——`dev-model-proxy.mjs:12`、`package.json:14`。
- **B10 [S3]** 位图 img 无固有宽高比预留：解码前高度 0，首帧后必然一次高度跳变；且无 `max-width:100%`，窄列溢出——`astryn.css:117`、`xiaoqi-raster-renderer.ts:51-52`；九态恒为 1696×2528。
- **B11 [S3]** （承接 A13 呈现侧）raster 忽略取景档 viewBox——`render-profiles.ts:17-23` vs `xiaoqi-raster-renderer.ts:37-38`；档位承诺"头肩近景"不成立。
- **B12 [S4]** Composer"角色已隐藏"占位符为不可达分支——`companion-view.tsx:244` vs `companion-shell.tsx:463`（隐藏态不渲染 Composer）。
- **B13 [S4]** 触控目标偏小：chip 移除键 min-height 16px——`astryn.css:172-175`。
- **B14 [S4]** `astryn.css:1-2` 头注与实现不符（`:root` vs `.astryn-root`；"只引用令牌" vs 多处字面 px）。
- **B15 [S4]** `availableModes()` 被 dev-host 内联复制——`mode-registry.ts:4-6` vs `dev-host/app.tsx:97`。
- **B16 [S4]** AvatarView 挂载分支 effect 无依赖数组（未来接命令式驱动会每渲染重挂载）——`companion-view.tsx:81-91`。

### C 切片（tests + scripts）

- **C1 [S1]**「九种状态两两视觉可辨」双重恒真——`tests/presentation/companion-shell.test.tsx:53-69`：签名拼接了 `${state}`（对象键唯一 ⇒ Set 必全异），markup 集合也因 `data-visible-state` 属性必全异；两种状态视觉完全相同也会通过。✅主控复核（读取字节）
- **C2 [S1]** 门禁回执对"阶段集合完整性/退出码"fail-open——`scripts/record-gates.mjs:65-71,116-126` + `.project-local/runs/gate-chain.sh:26-36`：(a) `record` 写了回执即 EXIT=0，即使 lint=2；(b) 不要求预期阶段名，`--stage test=0` 单独即可写出 `allGreen=true`；(c) gate-chain.sh 恒 exit 0。✅主控复核（读取字节）
- **C3 [S2]** 拒绝理由断言恒真——`tests/interaction/controller.test.ts:79`：`?? 'NONE'` 后 `.not.toBe(null)` 永远不会失败。
- **C4 [S2]**「真正收到后才升级为 REAL」从未驱动升级——`tests/boundary/architecture-risks.test.tsx:105-129` 只断言拒绝腿，无正腿（openRequest + 观测 delta → REAL）；全仓无任何测试驱动 `evidenceLevel` 到 `REAL`。
- **C5 [S2]** raster src 断言只钉 basename（无磁盘存在性、无清单绑定）——`tests/avatar/xiaoqi-raster-renderer.test.tsx:57-64`；文件删除或换目录仍绿。
- **C6 [S2]** raster 宽度断言不能证明 hero 档被尊重（240 与缺省 240 相同）、"显式 size 优先"未驱动——`tests/avatar/xiaoqi-raster-renderer.test.tsx:85-90`。
- **C7 [S2/scripts]** 树哈希 scope 不含 `scripts/` 与资产清单——`record-gates.mjs:19-20`；门禁机器自身与 `STATE-ASSET-INDEX.json` 变化时回执读数不变。
- **C8 [S2/scripts]** `gates.json` 无法区分 AAOS 漂移 VERIFIED/UNVERIFIABLE（两者 exit 0，回执只存 `"drift":0`）；且 `ASTRYN_AAOS_ROOT ?? default` 将空串覆盖当已配置——`scripts/check-aaos-drift.mjs:21,24-27,38-40`。
- **C9 [S3]** 渲染器选择的 保存→重载 往返未测——`tests/presentation/companion-settings.test.tsx:130-144` 只测 persona。
- **C10 [S3]** 未注册 rendererId 经 store→重载→shell 链路未测（现有覆盖均直接传 props）。
- **C11 [S3]** character-assets 测试不对目录做枚举：未注册的多余 PNG 落进 `upgraded/v1/` 全部断言仍绿——`tests/boundary/character-assets.test.ts:110-137`。
- **C12 [S4]** 测试名大于断言体：「槽位走同一条令牌链」未断言任何宽度/令牌——`companion-shell.test.tsx:43-51`。
- **C13 [S4]** approval-flow 头注称"显式选择 svg 驱动"，`:93` 实为默认档案挂载——`tests/presentation/approval-flow.test.tsx:7`。

### D 切片（docs + CI + 配置）

- **D1 [S2]** `STATUS.md` 无第五轮事件，且两处 `PENDING_EXTERNAL` 与 101 文件回执数字过期——`docs/current/STATUS.md:23,31`。
- **D2 [S2]** GF03 卡片多处"未回传/只有 .gitkeep"已为假——`docs/companion/GF03-ASSETS-AND-STATES.md:16,27,52,58,62`。
- **D3 [S2]** GF11 交付指南对 v2/渲染器/源文件/收据指针的陈述与现状脱节——`docs/companion/GF11-DELIVERY-GUIDE.md:4,16,20,72,80,88,95,150`。
- **D4 [S2]** 剩余工作台账与进度账本仍列 v2 为外部未回传——`docs/companion/REMAINING-WORK.md:22,30,56`、`docs/companion/PROGRESS.json:79,106,344,357`。
- **D5 [S2]** `PROJECT_CONTRACT.yaml` 三处字段过期（gf03 PENDING_EXTERNAL、CI 运行计数、测试数量）——`:23,46,62`。
- **D6 [S2]** 架构真相源未含渲染注册表/位图驱动——`docs/architecture/astryn-m0.structurizr.dsl:64,92-93`、`astryn-m0.evidence.md:18`。
- **D7 [S2]** 能力归属表渲染行缺注册表/位图默认——`docs/architecture/ASTRYN-CAPABILITY-OWNERSHIP.md:12`。
- **D8 [S2]** 默认渲染器切换与来源变更（origin→ai-generated）未落决策记录——`docs/authority/DECISIONS.md`（需新 D018）。
- **D9 [S1]** `虚拟人物/` 未忽略：150 个未跟踪文件（含工具内部状态、恢复副本、早期轮次字节）可被任何整目录 add 提交——`.gitignore` 无匹配。✅主控复核（`git check-ignore` + `ls-files --others`）
- **D10 [S3]** 回执 scope 不含 `assets/`（纯资产变更不改变树哈希）——与 C7 合并处置。
- **D11 [S3]** CI 与本地门禁链不对称（本地独有 drift/record/anchors；CI 独有全树秘密扫描、第三方目录扫描、双 node 矩阵）；`GF11:115` 对 CI 步骤描述缺"Archive byte fidelity"。
- **D12 [S3]** 设计/无障碍证据全部采集于 SVG 时代，切默认 raster 后未重扫——`docs/verification/design-a11y.md:3`、`DESIGN.md`、`docs/verification/M0-VALIDATION.md`；`AUTHORITY.md:29` 仍标"当前实测"。
- **D13 [S4]** `AUTHORITY.md:14` 索引描述滞后（D001-D010 → 实为 D017；STATUS 日期）。
- **D14 [S4]** 两处"渲染路线=原创 SVG"措辞未随默认切换更新——`docs/development/DEPENDENCIES.md:65`、`docs/research/OPEN-SOURCE-MATRIX.md:11`。
- **D15 [S4]** 交付清单 `.md` 无字节锚（`*.md text eol=lf`，再编辑成 CRLF 会被静默归一化）；`character-assets.test.ts:79` 仅断言存在。

## N3 修复处置（2026-10-14）

修复载体：工作树未提交变更（HEAD 4163d79；N1 资产落地与 N3 修复同处一个未提交面，45 个已跟踪文件 +1766/−276，另有 N1 新增 PNG 与清单）。
核验方式：修复后以**现行字节逐项抽查**（特征级：每条处置引用的行号均为 2026-10-14 当日复核值）+ 八阶段门禁链全绿。
重封回执：`docs/verification/gates.json` @ 2026-10-14T16:24:11Z——108 文件、树哈希 `ecd360b71f1e68f6…`、allGreen=true、aaosDrift=VERIFIED、37 个测试文件全通过。
局限：以下为特征级抽查（每项核对修复特征是否存在于现行字节），非逐断言执行；断言级行为由各自回归测试保证（列在证据列）。

### A 切片（15/15 已修）

| 项 | 处置 | 落点证据（2026-10-14 复核） |
|---|---|---|
| A1 | 终态映射表：cancelled/denied 等收束为 failed，不再无限轮询 | `src/adapters/aaos-bridge.ts:422-432` |
| A2 | 位图加载失败 → SVG 下限回退，`data-renderer-fallback=image-error` 显式作证 | `src/presentation/companion-view.tsx:66-98,116,138` |
| A3 | `exact` 信号保留在解析结果；严格取驱动另行提供，未注册即抛错 | `src/avatar/renderer-registry.ts:14,27-40` |
| A4 | 回执契约带 `sessionId`，盖章按回执会话而非当前会话 | `contracts/action.ts:15,34`；`src/interaction/companion-controller.ts:108,211` |
| A5 | reducer 拒绝按 note 计数（audit.rejected + lastRejectedReason），不静默丢 | `src/interaction/companion-controller.ts:42,108,272` |
| A6 | 探测结果落成 `model.available` 事件，不绕过守卫/reducer 直改 state | `src/interaction/companion-controller.ts:174`；`src/companion/reducer.ts:126-137` |
| A7 | `availability()` 来自真实能力探测（版本+能力注册表），与 stream 实调一致 | `src/adapters/aaos-bridge.ts:233-238` |
| A8 | `repeatText` 兑现（按 seq 递增，可被乱序守卫拒收），测试驱动 | `src/adapters/synthetic-conversation.ts:89`；`tests/interaction/controller.test.ts:98-110` |
| A9 | settled FIFO 上限 `SETTLED_LIMIT`，判决序状态随结清释放 | `src/companion/session-guard.ts:40-76` |
| A10 | view/export 读路径过 `decideRead`，排除项显式披露 | `src/memory/manager.ts:98,360-371` |
| A11 | 注释与实现对齐：明确"可信签发方名单近似，非签名校验" | `src/memory/policy.ts:47-50` |
| A12 | 未登记状态抛错（不产出坏 src）；渲染抛错走文本回退、不泄错误细节 | `src/avatar/xiaoqi-raster-renderer.ts:50-52`；`src/presentation/companion-view.tsx:73-83` |
| A13 | 裁切语义落 CSS 呈现层：`view=avatar` 圆形槽 object-fit/object-position（帧 QA 实测值） | `src/presentation/astryn.css:125-133` |
| A14 | 措辞对齐（回退下限描述与现状一致） | `src/avatar/renderer-registry.ts:32,36-37` |
| A15 | `scopesOf`/contracts 侧死 `toEvents` 已删；权威性判定抽为共享 `isTaskAuthoritative`（reducer 不再另硬编码）；`ASTRYN_TASK_STATES_REQUIRING_RECEIPT` 由测试消费；`assertStateHasDistinctVisual` 由 C1 回归消费 | `contracts/protocol.ts:64`；`tests/companion/reducer.test.ts:126-142`；`tests/presentation/companion-shell.test.tsx:68,86` |

### B 切片（16/16 已修）

| 项 | 处置 | 落点证据（2026-10-14 复核） |
|---|---|---|
| B1 | 系统 RM 下设置页复选框禁用 + 理由（"系统已开启，不可覆盖"） | `src/presentation/companion-settings.tsx:29-30,281-286` |
| B2 | 工具栏 RM 开关改为档案单源写入，消除本地覆盖被 effect 复位的双源 | `src/presentation/companion-shell.tsx:379-381` |
| B3 | 代理中止改用 AbortController + signal（替代失效的 close 监听时序） | `dev-host/server/dev-model-proxy.mjs:117,133,158` |
| B4 | 未注册 rendererId：单选组选中回退驱动事实 + 小字披露 | `src/presentation/companion-settings.tsx:254-257`；`tests/presentation/companion-settings.test.tsx`（C10） |
| B5 | radio 组名 useId 按实例隔离 | `src/presentation/companion-settings.tsx:72-73,254` |
| B6 | 记忆面板 4 个控件补 aria-label | `dev-host/memory-panel.tsx:178,185,195,226` |
| B7 | 来源条读"当前实际生效"，切无模型后显示 none/MODEL_UNAVAILABLE | `dev-host/app.tsx:197-204` |
| B8 | 环境变量名与示例一致（`ASTRYN_DEV_MODEL_TIMEOUT_MS`） | `.env.example:23`；`dev-host/server/dev-model-proxy.mjs:30` |
| B9 | 头注/示例给出手动加载方式（`--env-file-if-exists`，需 Node ≥22.9），不再声称自动加载 | `.env.example:18`；`dev-host/server/dev-model-proxy.mjs:14` |
| B10 | img `aspect-ratio: 1696/2528` 占位 + `max-width: 100%` | `src/presentation/astryn.css:121-124` |
| B11 | 同 A13（取景档裁切语义落 CSS） | `src/presentation/astryn.css:125-133` |
| B12 | 不可达的"角色已隐藏"占位符分支删除 | `src/presentation/companion-view.tsx:262-271` |
| B13 | chip 移除键 24×24（WCAG 2.5.8） | `src/presentation/astryn.css:188-193` |
| B14 | CSS 头注更新（`.astryn-root` 作用域 + 如实声明字面值缺口） | `src/presentation/astryn.css:1-6` |
| B15 | 可用模式取自 `availableModes()`，dev-host 不再内联复制 | `dev-host/app.tsx:98-99`；`src/presentation/mode-registry.ts:5` |
| B16 | 命令式挂载 effect 依赖列到 frame 各字段 | `src/presentation/companion-view.tsx:101-112` |

### C 切片（13/13 已修）

| 项 | 处置 | 落点证据（2026-10-14 复核） |
|---|---|---|
| C1 | 剥离状态名后再比：令牌签名（环色/眼型/嘴型/字形）与剥离后 markup 双重唯一 + 断言剥离动作生效 | `tests/presentation/companion-shell.test.tsx:58-87` |
| C2 | 回执 fail-closed：`REQUIRED_STAGES` 六项必选、缺失/失败即红；`gate-chain.sh` 以 WORST 真退出并驱动阶段集合 | `scripts/record-gates.mjs:70-93,153-158`；`.project-local/runs/gate-chain.sh:27-46` |
| C3 | 拒绝原因改断言确切值（`rejected['SETTLED_REQUEST']` + lastRejectedReason），不再 `?? 'NONE'` 恒真 | `tests/interaction/controller.test.ts:77-95` |
| C4 | REAL 正腿补齐：注册探测→提交→流式回复到达后升级为 REAL；拒绝腿保持 | `tests/boundary/architecture-risks.test.tsx:112-140` |
| C5 | raster src 断言绑定清单：形态正则 + 磁盘存在 + 字节 + sha256 + 派生来源链闭合 | `tests/avatar/xiaoqi-raster-renderer.test.tsx`（新增段） |
| C6 | 宽度冲突驱动：显式 size 优先于取景档（120 覆盖 168） | `tests/avatar/xiaoqi-raster-renderer.test.tsx`（新增段） |
| C7 | 树哈希 scope 纳入 `scripts/` 与 `STATE-ASSET-INDEX.json` | `scripts/record-gates.mjs:23,32-33` |
| C8 | AAOS 漂移状态（VERIFIED/UNVERIFIABLE/DRIFT）写入回执 `info.aaosDrift`；空串不覆盖当已配置 | `scripts/check-aaos-drift.mjs`；`gate-chain.sh:36-37` |
| C9 | 渲染器选择的保存→重载往返（store 断言 + 重挂载后 DOM 断言） | `tests/presentation/companion-settings.test.tsx`（新增段） |
| C10 | 未注册 rendererId 经 store→重载→shell 全链路（data-renderer-exact=false + 设置页回退披露） | `tests/presentation/companion-settings.test.tsx`（新增段） |
| C11 | 目录枚举反向门禁：`upgraded/v1/` 下每个 PNG 必须登记（植入物证伪后移除） | `tests/boundary/character-assets.test.ts:120-145` |
| C12 | 槽位令牌链断言补齐（data-avatar-view + 宽度=同档令牌 168） | `tests/presentation/companion-shell.test.tsx:43-55` |
| C13 | approval-flow 头注更正（前两例显式 svg、第三例默认位图档案） | `tests/presentation/approval-flow.test.tsx:7` |

### D 切片（1 项已修，14 项归 N4）

| 项 | 处置 |
|---|---|
| D9 | **已修**：`.gitignore` 忽略 `虚拟人物/`；实测 `git ls-files --others --exclude-standard 虚拟人物/` = 0 |
| D1-D8、D10-D15 | 归 N4 文档轮（改 STATUS/契约/决策记录/架构真相源/CI 文档等，见任务 #40） |



- **任务状态权威链**：流/模型文本不能移动任务状态（三层：rebase 降级 / guard 按 kind 拒 / reducer 复检）；回执 fail-closed（无 verifier → NO_VERIFIER）。
- **默认切换自洽**：`character.ts:175` ↔ 注册表 index 0 回退 ↔ 清单 `runtime.defaultRendererId` 一致；未知 id 的 `exact:false` 在 DOM 与设置页均有披露；迁移保留已存 rendererId。
- **PNG 字节保真**：`.gitattributes` binary 宏覆盖 `text=auto`；22+3 张 `text:unset`；清单↔磁盘 25/25 哈希相符（独立复算）。
- **代理安全姿态**：loopback 绑定、固定上游路径（非开放代理）、白名单 Origin、64KB 上限、日志无正文无密钥；"配置存在 ≠ 调用成功"证据分级正确（dev 代理 = NO_EVIDENCE）。
- **合成面标注**：dev-host 各面板 SYNTHETIC 标签齐全；"无模型"路径诚实（不静默吞提交）。
- **关键不变量**：注入面（构建期资产 URL + 数值宽度）；reduced-motion 对 img 驱动无动画；槽位令牌链两驱动一致（CSS 关闭时 width 属性自洽）。
- **门禁口径修复史**：上一轮 TEST-AUDIT 的修复（policy 禁读表正控、双候选导出、reason 钉住、420 字面量等）经读取确认为非空洞断言。

## 局限

- 审计为静态字节读证，未运行测试/构建；C 切片的"通过"性判断基于断言逻辑分析而非执行。
- 行号为审计时点（工作树含 N1 未提交变更）；N3 修复后以修复记录为准。
- 未覆盖切片：`.project-local/runs/*.mjs` 派生脚本（非提交物）；`虚拟人物/` 原始投放内容（本地区）。
