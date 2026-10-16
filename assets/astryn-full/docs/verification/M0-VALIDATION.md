# M0 验证报告

日期：2026-10-13。运行时绑定：Node `v26.7.0` / npm `11.19.0`（见 `docs/development/DEVELOPMENT.md`）。原始日志与截图在 `.project-local/runs/`、`.project-local/artifacts/`（不提交），本文件是脱敏结论。

> §1–§5 是**第一轮**记录（85 项测试），保留原样作为当时的回执；第二轮复审（118 项、设计契约、axe 扫描、风险登记）见文末 §6–§9，台账与 `gates.json` 记录的是第二轮现值。

## 1. 本地门禁（真实执行，退出码原样转录）

| 阶段 | 命令 | 退出码 | 结果 |
| --- | --- | --- | --- |
| lint | `npm run lint` | 0 | 0 error 0 warning（首轮 1 error：代理脚本里未使用的 `catch (error)` 绑定，已修） |
| typecheck | `npm run typecheck` | 0 | strict + `exactOptionalPropertyTypes` + `noUncheckedIndexedAccess` + `verbatimModuleSyntax` 全开 |
| unit | `npm run test` | 0 | **Test Files 12 passed (12) / Tests 85 passed (85)**，Duration ≈ 6s |
| build | `npm run build` | 0 | 65 modules transformed，`index.js 199.41 kB (gzip 65.07)`、`index.css 3.90 kB`，产物落 `.project-local/artifacts/dev-host-dist` |
| dev host 启动 | `npm run dev` | — | Vite 5.4.21 ready in 236 ms，`http://127.0.0.1:5183/` 返回 HTTP 200 |

首轮 typecheck 有 40+ 错误（契约层的判别联合、`exactOptionalPropertyTypes` 下的可选属性、守卫结果类型），逐个修正后归零；首轮 test 因 `vite.config.ts` 的 `root` 指向 `dev-host` 而报 "No test files found"（exit 1），加 `test.root` 后解决。**这些是真实过程，不是一次通过的报告。**

## 2. 浏览器实测（Chromium via CDP，127.0.0.1:5183）

配置：`VITE_ASTRYN_ALLOW_SYNTHETIC=1`、`VITE_ASTRYN_SYNTHETIC_HOST=1`（合成来源，界面必须显示 SYNTHETIC）。

| 场景 | 断言方式 | 结果 |
| --- | --- | --- |
| 角色画面渲染 | `getBoundingClientRect()` | avatar 200×233（>40×40 判可见），shell 388×627，`horizontalOverflow=false` |
| 初始状态 | `svg[data-testid=astryn-avatar]` 的 `data-visible-state` | `idle`，`data-expression-frame=0`，环色 `#5ad1c8` |
| **真实交互驱动表情** | 聚焦输入框 → 读 DOM | `idle → listening`，环色变 `#7aa2ff`；失焦回到 `idle` |
| 流式回复驱动口型 | 提交后读 `data-expression-frame` | 0 → **4**（等于真实到达的 delta 数），结束回 `idle` |
| 合成来源标注 | `data-testid=astryn-evidence-tag` | `scripted-synthetic / SYNTHETIC`，每条合成回复带 `SYNTHETIC` 徽标 |
| 审批链路 | 点"请求需要授权的动作" | `awaiting_approval`，环色 `#ffd166`，`?` 字形，审批卡含摘要/风险级/任务号 |
| 授权→执行→完成 | 点"允许"、"完成回执" | `executing` → `completed`，环色 `#63e6a6`，字形 `✓` |
| 拒绝路径 | 新请求后点"拒绝" | `awaiting_approval → idle`，审批卡消失，不留下"已完成"假象 |
| 审计可见 | `data-testid=astryn-audit` | `已应用 13 · 拒绝 {} · 回执校验 通过` |
| **缺模型明确报错** | 切到"无模型"后提交 | 模型芯片 `MODEL_UNAVAILABLE`，日志出现 `MODEL_UNAVAILABLE：未配置获准模型接口，星栖不使用脚本回复冒充 AI。`，**无任何脚本回复**，状态 `interrupted` |
| 无选区时不伪造上下文 | 未选中就点"解释选中内容" | 提示"没有选中内容：请先在下方夹具文档里选中一段文字。"，不产生假上下文 |
| 减少动效 | 点"减少动效" | `data-motion=off`（停用 spin/breathe/dots） |
| 隐藏与恢复 | 点"隐藏角色"/"恢复角色" | 画面消失 → 恢复 |
| 两种呈现模式 | 点 embedded / panel | 根类名在 `astryn-root--embedded`(408px) 与 `astryn-root--panel`(388px) 间切换 |
| 控制台 | 全程累积消息 | **0 error、0 warning**（仅 vite debug 与 React DevTools info） |

截图（本地，未提交）：`m0-browser-01-idle.png`、`m0-browser-02-idle-v2.png`（重画后）、`m0-browser-03-awaiting-approval.png`、`m0-browser-04-model-unavailable.png`。

## 3. 浏览器实测暴露并修复的两个真实缺陷

这两个都不是"测试写错了"，而是先写测试、再在真实宿主里跑才现形的：

1. **切换模型来源后控制器不重建**。`CompanionShell` 用 `useState(() => new Controller(deps))` 一次性构造，来源变化后仍在向旧端口要数据 → 界面显示的还是旧来源的状态。修复：`deps` 变化时重建控制器（`src/presentation/companion-shell.tsx`）。
2. **构造函数里订阅宿主，导致一次性回执被"幽灵订阅者"消耗**。React 18 StrictMode 会重复调用 `useState` 初始化器；被丢弃的那个控制器实例仍然订阅着宿主模拟器，它先调 `verify()` 把 `receiptId` 记为已见，真正在用的实例随后拿到 `REPLAYED` → 权威事件被降级为 `observed` → 审批卡永远不出现。jsdom 测试全绿，浏览器里必现。修复：构造改为无副作用，宿主订阅只在 `attach()` 建立、由 `detach/dispose` 解除，并补了回归测试 `tests/companion/authority.test.ts`（"构造控制器不得订阅宿主"）。

顺带修掉一个 DX 缺陷：`companion-shell.tsx` 同时导出组件与 `availableModes`，导致 Fast Refresh 失效、热更新后模块状态混杂。`availableModes` 移到 `src/presentation/mode-registry.ts`。

## 4. 测试覆盖的定向断言（第一轮 85 项）

| 文件 | 项数 | 覆盖的验收点 |
| --- | --- | --- |
| `tests/companion/reducer.test.ts` | 8 | A04/A06/A08：状态迁移、说完不等于完成、缺模型、非权威任务事件二次拒绝 |
| `tests/companion/guard.test.ts` | 8 | A07/A09：旧会话、协议不符、重复/乱序序号、已结清请求迟到、未知请求、切换会话、任务事件权威与 taskId 缺失、拒绝计数审计 |
| `tests/companion/authority.test.ts` | 8 | A08/A09：模型伪造完成、无校验器时降级、回执链 awaiting→executing→completed、重放拒绝、信封逐项校验、构造不得订阅 |
| `tests/adapters/sse.test.ts` | 8 | A06/A07：跨块切分、CRLF/CR、多行 data、注释、残留半行、`[DONE]`、损坏 JSON |
| `tests/adapters/openai-compatible.test.ts` | 9 | A06/A07/A15：分块、无结束事件→MALFORMED、503→MODEL_UNAVAILABLE、NETWORK、取消→ABORTED、请求体不含密钥字段 |
| `tests/interaction/controller.test.ts` | 7 | A06/A07：取消后迟到事件不串台、快速切换、切会话清空、dispose 后拒收、上游抛错可区分 |
| `tests/memory/policy.test.ts` | 6 | A11：私密不外溢、未获准/过期授权、虚构不可晋升、模型候选需宿主确认、端到端撤销删除、dispose 清空 |
| `tests/context/selection.test.ts` | 6 | A12：能力自述、不支持作用域不发授权、授权后带来源与版本、无选区、过期、伪造授权号 |
| `tests/presentation/companion-shell.test.tsx` | 9 | A03/A04/A06/A13：渲染与 AI 声明、九态视觉两两可辨、聚焦驱动、口型帧随数据、SYNTHETIC 标记、隐藏/减动效、卸载、SVG 无外部素材引用 |
| `tests/presentation/approval-flow.test.tsx` | 3 | A04/A08：审批卡落地、拒绝清除任务、正文"任务已完成"不产生任务态 |
| `tests/boundary/no-sensitive-apis.test.ts` | 8 | A10/A13/A15：源码扫描禁词（采集 API/屏幕捕获/系统命令/本地持久化/直接写库/密钥样式）、第三方素材目录为空、原创声明存在 |
| `tests/boundary/presentation-modes.test.ts` | 3 | A02：五形态声明、只承认两种实现、未实现必须带阻塞原因 |

## 5. 未执行与不可宣称

| 项 | 状态 | 原因 |
| --- | --- | --- |
| 真实模型调用（A05） | `NOT_TESTED` / `NO_EVIDENCE` | 无获准凭据；未付费、未读取其他项目密钥。配置路径与错误路径已实现并被测试覆盖 |
| AAOS 真实集成（A17） | `UNVERIFIED` | 见 `docs/architecture/AAOS-HOST-CAPABILITY-MAP.md`：Core 无通用流式会话面；记忆 Consumer 是闭集且不含星栖；无"当前选区"合同；宿主无事件推送面。适配器已按这些事实写成类型化契约，但没有一次真实调用 |
| 远端 CI（A18） | **PASS** | 已推送并跑通：最新绿 run `38326024723` @ `9cf9a44`，Node 20.19 与 22.12 两矩阵各 10 步 success（含秘密扫描与素材检查）。main 上累计 7 次运行 = 3 绿 4 红；首跑 `38324323712` 红于 "No secrets in tracked sources"，拦出测试内嵌的字面凭据样式。**归因修正**：归档被行尾规范化破坏 SHA-256 并非 CI 拦出，是推送后人工比对远端 blob 与磁盘字节才发现（风险登记册 Q9 要求把该断言写进 CI） |
| Git 关联（A01） | **PASS** | 本地 HEAD 与服务端 `refs/heads/main` 逐字符一致；未 force push、未改全局配置 |
| 安装运行/用户验收（A19） | `NOT_EXECUTED` | 未安装任何正式程序；浏览器验证不等于用户验收 |
| floating / pet / voice-only 形态 | `BLOCKED` | 需原生窗口/托盘与 AAOS ASR/TTS，属 P2 |
| 记忆生产读写、真实选区 | `BLOCKED_BY_HOST_CONTRACT` | 宿主合同缺失，未用合成夹具冒充 |

结构性检查、本地执行、真实模型、AAOS 集成、exact-SHA CI、安装运行、用户验收是七件不同的事，本报告分别给状态，不做互相推断。

---

# 第二轮：设计、无障碍与架构风险复审（同日追加）

用 `design-review` 与 `architecture-visualization` 技能套件独立复审第一轮成果。详细记录：`docs/verification/design-a11y.md`、`docs/architecture/astryn-m0.risk-quality.md`、`DESIGN.md`、`docs/architecture/astryn-m0.structurizr.dsl`。

## 6. 门禁重跑（修复后）

| 阶段 | 退出码 | 结果 |
| --- | --- | --- |
| lint | 0 | 0 error 0 warning |
| typecheck | 0 | — |
| test | 0 | **Test Files 14 passed / Tests 118 passed**（新增 `design-tokens` 23 项、`architecture-risks` 10 项） |
| build | 0 | 产物同上 |

字节锚点：`docs/verification/gates.json`（源码树 64 文件内容哈希、工具链绑定、四阶段退出码）。这是无 Git 情况下对"报告与现场脱节"风险的替代缓解（登记册 Q3）。

## 7. axe 无障碍扫描（三视口 × 两状态）

- 违规 **0**；关键：`color-contrast` 的 **incomplete 从 19–21 个节点降为 0**。修复前"0 违规"其实是 axe **拒绝判定**（文字坐在径向渐变上）；把渐变移出承载文字的容器后，对比度才真正被机器判过一遍。
- 键盘：真实 Tab 走查，焦点环 <2px 或缺失 **0**、触控目标 <24px **0**、聚焦时横向裁切 **0**；审批流可全程键盘完成。
- 对比度实测 14/14 组 ≥4.5:1（修复前占位符 3.73:1、禁用态 3.82:1 不达标）；九态环色对两种底面全部 ≥3:1。
- 375px 视口横向溢出（`scrollWidth 414 > 375`）已修，复测 `overflowX=false`。
- 控制台 0 error 0 warning。

工具偏离如实记录：技能自带 `audit-a11y.mjs` 要求的 Chromium 修订号（1248/1178/1187）本机均不存在，且不允许下载运行时，因此改用同一 `@axe-core/playwright@4.13.0` 规则集 + `playwright-core@1.64.0` 显式 `executablePath` 指向本机已有的 chromium-1228。技能自带的证据收集器则**已跑通**（需项目内补 `fast-glob`/`yaml` 并用 `module.register()` 注册解析钩子，未改插件缓存）。

## 8. 复审发现的六处"看起来已实现、实际可被绕过或被高估"

| # | 缺口 | 为什么第一轮没暴露 |
| --- | --- | --- |
| R1 | 渲染 seam 被 UI 直接绕过：`AvatarView` import 具体函数，从不经过 `AstrynAvatarRenderer` | 测试断言的是我实现的那条通道，不是承诺的那条通道 |
| R2 | 乱序检测只作用于本地重编号，宿主原始序号在 `rebase()` 里被丢弃 | 所有测试都用本地序号喂事件，无法证伪 |
| R3 | 错误文本原样透传到界面，可能带出上游 URL 与凭据 | 无真实上游，stub 错误信息无害 |
| R4 | `evidenceLevel:'REAL'` 是类常量，配了模型名就自称 REAL | 没有测试断言"配置 ≠ 已验证" |
| R5 | 开发代理无 Origin 校验，本机任意页面可消耗用户配额（混淆代理） | 单元测试不覆盖进程边界 |
| R6 | 可用性只在发消息时才暴露，代理没起来时界面平静 | 测试直接断言 reducer 结果，不模拟启动时序 |

六条全部修复并各配回归测试。残余八条（Q1–Q8）与优先级顺序见 `astryn-m0.risk-quality.md` §2、§4；其中 Q1（`trust=authoritative` 在浏览器同一 realm 内不是安全边界）是最需要在 P1 接入前解决的一条。

## 9. 研究补全

方向 2/3/5/7/9 补研 43 个候选（工作记录在 `.project-local/runs/research/gap-*.md`），并入 `docs/research/OPEN-SOURCE-MATRIX.md` §3。要点：P2 渲染首选 Rive（唯一"运行时 MIT + 官方 React 绑定 + 状态机数据驱动"齐备）；语音首选 sherpa-onnx + silero-vad + Kokoro 且**归 AAOS**，星栖只取呈现时机；Tauri 2.12.3 的桌宠能力已文档+源码双层确证，并纠正 `acceptFirstMouse`（macOS 专用，非鼠标穿透）与 `visibleOnAllWorkspaces`（Windows 不支持）两处误解。**全部候选零运行验证。**

# 第五轮：raster 默认下的 a11y 重扫与两处回归修复（2026-10-14）

第二轮 §7 的扫描证据停留在 SVG 渲染时代；GF05–GF09 面板扩充、D018 默认渲染器切换后未重扫（审计项 D12）。本轮回对当前代码（`xiaoqi-raster-v2` 默认）做真实重扫。

- 工具与视口同 §7（同一 `@axe-core/playwright` 规则集、chromium-1228、三视口 × 两态共 6 屏）；脚本 `.project-local/runs/node-libs/a11y-scan.mjs`。
- 修复后读数：axe 违规 **0** / `incomplete=[]` / `inapplicable=40`；键盘焦点环缺失 **0**、触控目标 <24px **0**、聚焦横向裁切 **0**；三档视口 `scrollWidth == innerWidth`。
- 重扫发现两处回归并当轮修复：① `.astryn-title` 缺 `overflow-wrap: anywhere`，长 token 使 375 档溢出 `384 > 375`；② `.devhost-input/.devhost-textarea` 焦点环走 UA 默认、与产品"显式声明"公约不一致。详见 `design-a11y.md` §8（修复前后读数、两轮定位方法与证据 sha256 均留证）。
- 证据文件：`.project-local/runs/a11y-rescan-n4.stdout.txt`（修复前）、`a11y-rescan-n4-afterfix.stdout.txt`（修复后）、`node-libs/design-qa-out/a11y-scan.json`（sha256 `7107fe2ea19547f9a1c5b7d636e952e7e2b3db7a287ea99e8cfcef77fb2f4541`，105795 字节）。
- 设计契约侧同步：`DESIGN.md` 的 Responsive/Motion/Known Gaps/验证四节已按本次读数更新。
