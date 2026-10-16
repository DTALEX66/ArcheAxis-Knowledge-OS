# ASTRYN M0 架构风险与质量审查

日期：2026-10-13。审查目标：**这套基础是否足以安全地接入 AAOS，以及哪里会在接入时伤人**。
证据基线：`astryn-m0.structurizr.dsl` + `astryn-m0.evidence.md` + `AAOS-HOST-CAPABILITY-MAP.md` + `M0-ACCEPTANCE-TRACKER.md` + `DESIGN.md`。
本轮所有结论都经过代码复核；**6 条风险均确认为真实缺口并已修复（各配回归测试）**，其余为已确认的残余风险。

严重度 = 影响 × 可能性；`P1` 需立即处理，`P2` 接入前处理，`P3` 监控。

## 1. 本轮验证并修复的缺口（原先被当成"已实现"）

| # | 缺口 | 证据（修复前） | 严重度 | 修复 | 回归 |
| --- | --- | --- | --- | --- | --- |
| R1 | **渲染 seam 是装饰**：`AvatarView` 直接 `import { renderXiaoqiMarkup }`，从不经过 `AstrynAvatarRenderer` 对象。换 Live2D/VRM 驱动时必须改 UI，违背"一套 UI 多种呈现"的核心承诺 | `grep` 显示 `companion-view.tsx:4` 导入具体函数，`xiaoqiSvgRenderer` 仅被 `index.ts` 导出、无任何调用方 | P1 影响：架构承诺失效 | 契约新增 `renderMarkup?` / `mount?` 双落地方式；建立 `AVATAR_RENDERERS` 注册表与 `selectAvatarRenderer()`；UI 只认注册表，并在 DOM 上落 `data-renderer` | `tests/boundary/architecture-risks.test.tsx` R1 三项（含未知 id 回退、每个驱动必须能落地） |
| R2 | **乱序检测名不副实**：`rebase()` 把宿主原始序号丢弃并换成本地重编号，守卫只对本地序号判单调 → 宿主真乱序时检测不到，而测试全绿 | `companion-controller.ts` rebase 只设 `seq`；守卫键 `${session}\|${request}` 与控制器键 `req:${request}` 各自独立 | P1 影响：迟到/乱序回复串台（正是 A07 要防的） | 信封新增 `originSeq`；守卫对原始序号独立判序，回退即 `OUT_OF_ORDER_ORIGIN_SEQ` | R2 两项：`seq` 递增但 `originSeq` 回退必须丢弃；无原始序号时行为不变 |
| R3 | **错误文本原样透传到界面**：`error.message` 直接进入 `stream.failed`。若用户把凭据写进 base URL（`https://user:tok@host`），undici 的错误信息会带出主机与凭据，并渲染进 DOM | `openai-compatible.ts` 四处 `error instanceof Error ? error.message : String(error)` 无过滤 | P2 影响：凭据泄漏面 | 新增 `redactErrorText()`：剥 URL / Bearer / key 样式并截断 240 字符，四处全部套用上 | R3 一项（URL、Bearer、超长、普通文本不误伤） |
| R4 | **证据级别由配置推断**：`OpenAiCompatibleConversationPort.evidenceLevel` 是类常量 `'REAL'`，只要配了模型名就自称 REAL，即使代理根本没起来 | `openai-compatible.ts:48` 常量；`model-registry.ts:71` 直接沿用 | P2 影响：违反"不得把配置宣称为集成" | 配置态降为 `NO_EVIDENCE`；只有真正收到非合成端口的 `stream.delta` 内容，reducer 才升级为 `REAL` | R4 两项（配置态 NO_EVIDENCE；无活动请求时不升级） |
| R5 | **开发代理无访问控制**：只绑 `127.0.0.1` 挡不住本机任意网页拿它当免费模型代理（混淆代理 / 配额盗用） | `dev-model-proxy.mjs` 全文无 origin/allow/token 判定 | P2 影响：真实凭据被本地第三方页面消耗 | POST 强制 `ALLOWED_ORIGINS` 白名单（默认只放行开发宿主端口），非白名单 403 `PERMISSION_DENIED`；无 Origin 视为本地 CLI 调用 | R5 一项（源码级断言白名单与拒绝码存在）+ 手工 curl 复验 |
| R6 | **可用性只在发消息时才暴露**：代理未启动时界面平静，用户必须发一条消息才知道没模型 | 无启动探测 | P3 影响：状态可见性 | `controller.attach()` 内调用 `refreshModelAvailability()`，不可用即派发 `model.unavailable` | R6 一项（attach 后无需发消息即出现 `MODEL_UNAVAILABLE`） |

> 这六条都不是"测试没写"造成的：R1/R2/R4 在 108 项全绿的情况下依然存在。**能骗过单元测试的，是结构性的自我引用**——测试断言的是我实现的那个通道，而不是承诺的那个通道。

## 2. 残余风险（本轮无法在授权范围内消除）

| # | 风险 | 证据 | 影响 / 可能性 | 现有缓解 | 建议动作 | 所需授权 |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | **`trust=authoritative` 不是安全边界**。星栖运行在浏览器同一 JS  realm 内，任何代码都能构造 `source:'host-task', trust:'authoritative'` 的事件；守卫只能保证"经过校验器的才权威"，不能阻止有人绕过校验器直接 `dispatch` | `companion-controller.dispatch()` 是公开方法；`AstrynReceiptVerifier` 只在 `ingestReceipt` 路径上被调用 | 高 / 中（P1 接入后若引入插件或远程内容即成真问题） | 事件构造集中在 controller；`rebase()` 强制降级传输层事件 | **已收窄（第四轮）**：`dispatch` 改为原生 `#dispatch`，类外语法不可达，权威事件只能经 `ingestReceipt` 校验器进入；负向测试断言实例与原型上都无 `dispatch`/`applyEvent` 等公开注入面、`@ts-expect-error` 编译钉住（`tests/companion/authority.test.ts`） | 收窄已自主完成；**AAOS 侧对 job 结果二次确认仍待集成参与** |
| Q2 | **AAOS 端点假设会过期**。模型与适配器按 2026-10-13 的 HEAD `0574c3ac` 建模，AAOS 一变即失真 | `AAOS-HOST-CAPABILITY-MAP.md`；`S0-BASELINE.md` §1 | 中 / 高（AAOS 活跃开发中） | 端点集中在 `AAOS_ENDPOINTS` 常量；证据索引逐条标 `medium` 置信度 | **已关闭（第四轮）**：`scripts/check-aaos-drift.mjs` 只读比对 AAOS 当前 HEAD 与图谱记录（VERIFIED/UNVERIFIABLE=exit 0；DRIFT/UNREADABLE=exit 1），已纳入 `npm run verify` 与本地六阶段门禁 | 已自主完成 |
| Q3 | ~~无版本锚点~~ **已关闭（D015）** | 本地已 `git init -b main` 并推送；`gates.json` 现同时记录 git HEAD 与源码树哈希 | — | 原为内容哈希替代方案 | 已升级为真锚点：本轮实测 HEAD `9cf9a44441d24706211633f0759146872a726a0c` 与服务端 `refs/heads/main` 逐字符一致；锚点随提交前移，任何 CI 结论都必须写成"run N @ SHA"而不是"当前绿" | 已闭环 |
| Q4 | **合成与真实只靠标签区分**。`SYNTHETIC` 徽标是渲染约定，若未来某个端口忘记声明 `evidenceLevel`，界面无法分辨 | `AstrynConversationPort.evidenceLevel` 为必填字段，但类型系统不校验其诚实性 | 中 / 中 | 三个端口都显式声明；UI 强制显示；`presentation-modes` 与 `architecture-risks` 测试覆盖 | 让宿主适配器成为 `evidenceLevel` 的唯一签发点（端口构造时由宿主注入，不由实现自填） | 可自主执行 |
| Q5 | **记忆/上下文真实接入完全缺位**（A11/A12 的宿主侧） | AAOS Consumer 闭集不含星栖；无"当前选区"合同 | 高 / 确定 | 契约显式返回 `BLOCKED_BY_HOST_CONTRACT`，未用夹具冒充 | 集成任务：与 AAOS 确认 Consumer 枚举与选区投影 | AAOS 集成授权 |
| Q6 | **真实模型从未跑过**（A05）。流式解析、取消、超时只有 stub 证据 | 无获准凭据 | 中 / 确定 | 合成与真实路径物理分离；`MODEL_UNAVAILABLE` 明确 | 用户提供凭据后跑一次真实三段验证（成功 / 取消 / 上游错误） | 用户授权 + 可能付费 |
| Q7 | **无障碍证据依赖单一工具**。axe 现在能判定全部节点（`incomplete=[]`），但 `reduced-motion` 的真实生效只做了 CSS 声明级断言 | `DESIGN.md` 验证节；`a11y-final.log` | 低 / 中 | 令牌与焦点环有门禁；`data-motion` 有 UI 测试 | **已交付（第四轮）**：CDP `Emulation.setEmulatedMedia` 双上下文探针（15 项检查 ×2，含强制挂类后 computed `animationName=none` 与 `elementAnimations===0` 的 CSS 层守卫）；产品实现补齐系统偏好接线（只增强不削弱）；探针报告 `.project-local/runs/q7-reduced-motion.report.json` | 已自主完成 |
| Q8 | ~~CI 配置从未运行~~ **已关闭（D015）** | run 38326024723 @ `9cf9a44`（本轮实测最新绿）；累计 7 次运行、3 绿 4 红，逐次归因见台账 A18 | — | 首跑为红（run 38324323712），红因是 "No secrets in tracked sources" 一步，拦出测试内嵌的字面凭据样式。**注意归因修正**：归档被行尾规范化破坏 SHA-256 这一缺陷 CI 并未拦到，是推送后做远端 blob 与磁盘字节比对时发现的（见 Q9） | 已闭环；`engines >=20.19` 经两版本实测成立 | 已闭环 |
| Q9 | **CI 的字节保真覆盖是缺口**：工作流没有一步校验"仓库里的字节 == 磁盘原件字节"。行尾规范化确实发生过一次——`core.autocrlf=true` 把归档从 20960 字节改成 20434 字节，而当时没有任何 CI 步骤会因此变红（`b42eee2` 那一次红的是秘密扫描，与此无关，修掉秘密问题后该缺陷仍会静默通过） | `.github/workflows/ci.yml` 步骤集合（无字节校验步）；`docs/tasks/archive/ARCHIVE-RECEIPT.md` 收据值 vs `git cat-file -s` | 中 / 已发生过一次（非推测） | `.gitattributes` 对 `docs/tasks/archive/**` 设 `-text -eol`；本地推送后人工比对 blob sha | **已交付（第四轮）**：`scripts/check-archive-fidelity.mjs`（磁盘 sha256 + staged index blob sha256 双源比对收据，无收据条目的归档文件即红）；CI 新增 "Archive byte fidelity" 步，run 38433397794 双矩阵实测 success；本地三种植入故障均点名变红（含复现行尾规范化事故的 20434 字节态） | 已闭环 |

## 3. 质量属性判断

| 属性 | 判定 | 依据 |
| --- | --- | --- |
| 可测试性 | **强** | 36 文件 323 项（第四轮 R 队列后实测），逻辑层无 React 依赖；契约层纯类型可独立断言 |
| 可维护性 | **中上** | 分层清晰、令牌集中；但 R1 说明"接口存在"与"接口被用"需要门禁来保证，现已补 |
| 可靠性（状态正确性） | **强** | 三重权威防线 + 显式拒收原因 + 审计可见；R2 修复后原始序号也受判序 |
| 安全性 / 隐私 | **中** | 密钥不进浏览器、代理 loopback + Origin 白名单、错误脱敏；Q1 已收窄为类内可达（`#dispatch`），残余为 AAOS 侧结果二次确认（待集成） |
| 可访问性 | **中上** | axe WCAG2/2.1 A+AA 0 违规且全部节点可判定；焦点环、触控目标、窄视口实测达标；系统级 reduced-motion 经 CDP `Emulation.setEmulatedMedia` 实测生效（Q7 第四轮） |
| 性能 | **未评估** | 未做帧率与内存测量；构建产物 gzip 65 kB，无逐帧 filter/blend |
| 可移植性（接入 AAOS） | **弱，且是外部原因** | Q5/Q6 全部取决于宿主合同与凭据，不取决于星栖代码 |

## 4. 优先级修复顺序（下一步）

1. ~~**P1｜Q3 无锚点**~~ **已完成**：`docs/verification/gates.json` 现由 `scripts/record-gates.mjs` 生成，同时记录 git HEAD/分支、源码树文件数与 sha256、各阶段退出码与测试计数；回执与被测字节绑定。
2. ~~**P1｜Q1 收窄 `dispatch`**~~ **已完成（第四轮）**：`dispatch` 现为原生 `#dispatch`，类外不可达；`tests/companion/authority.test.ts` 负向断言 + `@ts-expect-error` 编译钉住"直接 dispatch 伪造权威事件"在公开面上不可达，且合法权威链对照组仍全绿。
3. ~~**P1｜Q9 CI 字节保真步骤**~~ **已完成（第四轮）**：`scripts/check-archive-fidelity.mjs` 双源（磁盘 + staged blob）比对收据；CI run 38433397794 双矩阵实测 success；三种植入故障（含事故态 20434 字节）均点名变红。
4. ~~**P2｜Q2 AAOS 漂移检查**~~ **已完成（第四轮）**：`scripts/check-aaos-drift.mjs` 四模式实测（VERIFIED/UNVERIFIABLE 绿；DRIFT/UNREADABLE 红），已纳入 `npm run verify` 与本地六阶段门禁。
5. ~~**P2｜Q7 reduced-motion 真机验证**~~ **已完成（第四轮）**：CDP `Emulation.setEmulatedMedia` 双上下文 15 项检查 ×2；产品实现补上系统偏好接线（只增强不削弱）。
6. **P3｜Q4 证据级别由宿主签发** → 与 P1 挂载设计一并决定，避免现在猜接口。
7. ~~**R 队列上传**~~ **已完成（第四轮）**：R1–R4 打包为 PR #1（`38d1fb2`），CI run 38433397794 双矩阵 success 后合并入 main（merge commit `c8cc3a7a`），main 侧推送 CI run 38433650701。

## 5. 本次审查的方法学结论

- **"0 违规"必须连同"未判定数"一起读**。axe 初次扫描报 0 违规，但同一次输出里 `color-contrast` 对 19–21 个节点是 incomplete——那是"没判"，不是"通过"。把渐变从文字层移开之后 incomplete 才归零。
- **单元测试全绿不等于浏览器正确，浏览器正确不等于架构承诺兑现**。R1/R2/R4 三条都在 jsdom 与 Chromium 双双通过的状态下被静态审查发现。
- **接缝要用门禁钉住，不是用注释钉住**。`contracts/avatar.ts` 早就写着"可替换渲染驱动"，但直到本轮才有测试要求 UI 必须经注册表取驱动。
- **"CI 变红"和"CI 能看见这个缺陷"是两件事**。`b42eee2` 那次确实红了，但红在秘密扫描；同一提交里归档被行尾规范化、字节数从 20960 变成 20434 的问题，工作流里没有任何一步会为之变红——它是推送后人工比对远端 blob 与磁盘字节时才发现的。一次成功的拦截容易让人以为整条防线都在工作，实际只是另一条线起了作用（见 Q9）。
