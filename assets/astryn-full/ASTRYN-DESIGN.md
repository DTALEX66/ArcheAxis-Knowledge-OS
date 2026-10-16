---
version: alpha
name: ASTRYN-星栖 呈现层设计系统
description: 星栖角色呈现层的可复用视觉契约。深色、低饱和、以状态色传达系统事实；数值全部来自 src/presentation/astryn.css 与 src/avatar/state-visuals.ts 的实测提取，对比度按 WCAG 2.1 公式计算，非肉眼估计。
colors:
  bg: "#0b0d1a"
  surface: "#141830"
  surface-2: "#1c2242"
  surface-sunken: "#10142a"
  ink: "#e8ecff"
  on-primary: "#0b0d1a"
  primary: "#5ad1c8"
  muted: "#9aa4cf"
  placeholder: "#a8b1d6"
  hairline: "#2a3160"
  task-line: "#3a5fa8"
  task-text: "#bcd2ff"
  error-line: "#8a2f3c"
  error-text: "#ffb3bd"
  error-strong: "#ffc7ce"
  error-surface: "#22101a"
  warning-line: "#b98a2e"
  warning-text: "#ffd166"
  warning-surface: "#1f1a10"
  success-line: "#2e7d57"
  success-text: "#63e6a6"
typography:
  display-lg:
    fontFamily: '"Segoe UI", "Microsoft YaHei", system-ui, sans-serif'
    fontSize: 15px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0.02em
  body-md:
    fontFamily: '"Segoe UI", "Microsoft YaHei", system-ui, sans-serif'
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0px
  body-sm:
    fontFamily: '"Segoe UI", "Microsoft YaHei", system-ui, sans-serif'
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0px
  caption:
    fontFamily: '"Segoe UI", "Microsoft YaHei", system-ui, sans-serif'
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0px
  micro-tag:
    fontFamily: '"Segoe UI", "Microsoft YaHei", system-ui, sans-serif'
    fontSize: 10px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.01em
  button-md:
    fontFamily: '"Segoe UI", "Microsoft YaHei", system-ui, sans-serif'
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0px
rounded:
  none: 0px
  sm: 6px
  md: 9px
  lg: 10px
  xl: 14px
  full: 999px
spacing:
  xxs: 2px
  xs: 6px
  sm: 8px
  md: 12px
  lg: 14px
  gutter: 10px
components:
  button-primary:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: "8px 14px"
    height: 32px
  button-primary-hover:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
  button-primary-disabled:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
  button-danger:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.error-strong}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
  text-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "8px 10px"
  text-input-focused:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
  chip-neutral:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    typography: "{typography.caption}"
    rounded: "{rounded.sm}"
    padding: "6px 7px"
  chip-task:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.task-text}"
    typography: "{typography.caption}"
    rounded: "{rounded.sm}"
  chip-error:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.error-text}"
    typography: "{typography.caption}"
    rounded: "{rounded.sm}"
  message-user:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "7px 9px"
  message-assistant:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "7px 9px"
  message-error:
    backgroundColor: "{colors.error-surface}"
    textColor: "{colors.error-strong}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "7px 9px"
  approval-card:
    backgroundColor: "{colors.warning-surface}"
    textColor: "{colors.warning-text}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.lg}"
    padding: "10px"
  evidence-tag:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.muted}"
    typography: "{typography.micro-tag}"
    rounded: "{rounded.full}"
    padding: "2px 8px"
---

# ASTRYN 呈现层设计系统

## Overview

星栖是角色陪伴子系统，界面承担两件事：**传达温度**与**如实传达系统事实**。因此这套系统的核心约束不是装饰，而是可核验性：

- 深色低饱和底（`{colors.bg}` / `{colors.surface}`），角色形象是唯一的高彩度焦点。
- **状态色即系统语义**：颜色不是点缀，九种角色状态各有唯一环色 + 眼型 + 嘴型组合，用户不需要读文字也能分辨"在想"还是"在等授权"。
- 一切合成数据必须被标出（`SYNTHETIC` 徽标），一切不可用必须被说出（`MODEL_UNAVAILABLE`），不允许用视觉平滑掩盖真实状态。

来源覆盖：`src/presentation/astryn.css`（令牌与组件规则，权威实现）、`src/avatar/state-visuals.ts`（九态视觉映射表，权威实现）、`dev-host/dev-host.css`（开发宿主布局）、真实渲染截图 2 张。**无 Figma、无 Tailwind 配置、无第三方组件库**，因此本文件由实现反推，置信度标注见各节。

## Colors

令牌实测值与对比度（WCAG 2.1 相对亮度公式，`.project-local/runs/contrast-recheck.mjs` 计算）：

| 令牌 | 值 | 用途 | 实测对比度 |
| --- | --- | --- | --- |
| `{colors.bg}` | `#0b0d1a` | 面板底色（纯色，不用渐变，见下） | — |
| `{colors.surface}` | `#141830` | 卡片、日志、输入底 | — |
| `{colors.surface-2}` | `#1c2242` | 按钮、用户气泡 | — |
| `{colors.surface-sunken}` | `#10142a` | 角色气泡 | — |
| `{colors.ink}` | `#e8ecff` | 正文 | 16.45:1 / 14.86:1 / 13.17:1 / 15.47:1 **PASS** |
| `{colors.muted}` | `#9aa4cf` | 次要说明、AI 声明 | 7.14:1 / 7.90:1 **PASS** |
| `{colors.placeholder}` | `#a8b1d6` | 输入占位符 | 8.25:1 **PASS** |
| `{colors.hairline}` | `#2a3160` | 分隔描边 | 非文字，图形判定 |
| `{colors.primary}` | `#5ad1c8` | 焦点环、强调、idle 环色 | 9.47:1 **PASS** |
| `{colors.task-text}` | `#bcd2ff` | 任务态芯片 | 11.47:1 **PASS** |
| `{colors.error-text}` | `#ffb3bd` | 错误芯片 | 10.34:1 **PASS** |
| `{colors.error-strong}` | `#ffc7ce` | 错误正文（于 `{colors.error-surface}`） | 12.37:1 **PASS** |
| `{colors.warning-text}` | `#ffd166` | 审批卡（于 `{colors.warning-surface}`） | 12.00:1 **PASS** |
| `{colors.success-text}` | `#63e6a6` | 真实来源徽标、completed 环色 | 11.14:1 **PASS** |
| `{colors.on-primary}` | `#0b0d1a` | 主色上的文字（当前用于前景图标/深字压亮环） | — |

**关于 `primary` 与 brand**：星栖没有独立品牌色板；`{colors.primary}` 别名到 idle 状态环色（`#5ad1c8`），因为它同时承担"焦点可见"与"角色待机"两个语义。若未来引入品牌 hue，必须另立令牌而不是替换 `primary`。

### 九态环色（`state-visuals.ts` 实测，非文字图形按 3:1 判定）

| 状态 | 环色 | vs `{colors.bg}` | vs `{colors.surface}` |
| --- | --- | --- | --- |
| idle | `#5ad1c8` | 10.48:1 | 9.47:1 |
| listening | `#7aa2ff` | 7.77:1 | 7.02:1 |
| thinking | `#c08bff` | 7.71:1 | 6.96:1 |
| speaking | `#ffb454` | 10.96:1 | 9.90:1 |
| interrupted | `#f2647c` | 6.34:1 | 5.73:1 |
| awaiting_approval | `#ffd166` | 13.40:1 | 12.11:1 |
| executing | `#4fd1ff` | 10.95:1 | 9.89:1 |
| completed | `#63e6a6` | 12.33:1 | 11.14:1 |
| failed | `#ff5d5d` | 6.42:1 | 5.80:1 |

九态的 `环色 × 眼型 × 嘴型 × 字形` 组合两两唯一，由 `tests/presentation/companion-shell.test.tsx` 断言（9 个签名 + 9 段 markup 全部互不相同）。

## Typography

实测字号只有 5 档：`10 / 11 / 12 / 13 / 15px`。字体栈 `"Segoe UI", "Microsoft YaHei", system-ui`，中文优先落到 Microsoft YaHei，不加载网络字体（低资源与离线可用优先）。

- `{typography.display-lg}`（15px/600）仅用于面板标题与"小栖 · 星栖"。
- `{typography.body-md}`（13px）是对话正文与按钮文字——**不得低于 13px**，中文在 11px 以下可读性骤降。
- `{typography.caption}`（11px）用于芯片、边界声明、AI 身份声明。
- `{typography.micro-tag}`（10px）只允许用于 `SYNTHETIC` / `NO MODEL` 这类徽标，不得承载必要信息。

## Layout

- 间距令牌：`{spacing.xxs} 2px`、`{spacing.xs} 6px`、`{spacing.sm} 8px`、`{spacing.md} 12px`、`{spacing.lg} 14px`、`{spacing.gutter} 10px`。
- 面板宽度 `min(360px, 100%)`（panel）/ `100%`（embedded），**不使用固定像素宽度**：375px 视口下曾实测到 `scrollWidth 414 > 375` 的横向溢出，已修（`.devhost-aside { width: min(380px, 100%) }` + `@media (max-width: 420px)` 全宽堆叠）。
- 对话日志 `max-height: 240px; overflow-y: auto`，消息 `overflow-wrap: anywhere` 防止长 token 撑破。

## Elevation & Depth

不使用阴影层叠。深度只靠两层：底色 `{colors.bg}` 与卡片 `{colors.surface}`/`{colors.surface-2}` 的明度差，外加角色自身的径向光晕（画在 SVG 内，**不含 HTML 文字**）。

> 这是有意的可访问性决策：早期版本把径向渐变画在 `.astryn-root` 上，导致 axe 的 `color-contrast` 规则对 **19–21 个节点判为 incomplete（无法计算）**——"0 违规"其实是"没判"。把渐变移出文字所在层后，同一扫描变为 `incomplete = []` 且 0 违规。**规则：任何承载文字的容器不得用渐变作背景。**

## Shapes

`{rounded.sm} 6px` 芯片 → `{rounded.md} 9px` 按钮/输入/气泡 → `{rounded.lg} 10px` 容器 → `{rounded.xl} 14px` 面板 → `{rounded.full}` 徽标。层级越浅，圆角越小。

## Components

- `{components.button-primary}`：默认按钮。hover 只做 `translateY(-1px)`（合成属性），不改颜色，避免与状态色冲突。`:focus-visible` 必须有 `2px` 实心环 + `2px` offset，**不依赖 UA 默认焦点环**。
- `{components.button-primary-disabled}`：`opacity 0.62`。禁用控件在 WCAG 1.4.3 下豁免对比度，但实测等效仍有 5.91:1。
- `{components.button-danger}`：停止生成 / 拒绝授权。
- `{components.text-input}` 与 `{components.text-input-focused}`：占位符必须显式声明 `{colors.placeholder}`（未声明时浏览器默认灰在深色底上仅约 3.7:1）。
- `{components.chip-neutral}` / `{components.chip-task}` / `{components.chip-error}`：状态芯片。**任务类芯片必须同时出现状态名与任务号**，颜色只是加速识别，不是唯一载体。
- `{components.message-user}` / `{components.message-assistant}` / `{components.message-error}`：合成回复必须在气泡内前置 `SYNTHETIC` 徽标。
- `{components.approval-card}`：审批请求卡。必须含动作摘要、风险级、任务号与两个显式按钮；键盘可达（已实测 Enter 可激活）。
- `{components.evidence-tag}`：证据级别徽标。`--synthetic`（琥珀）与 `--real`（绿）两型，**不得省略**。

## Do's and Don'ts

- **Do** 用 `state-visuals.ts` 的映射表加状态视觉；**Don't** 在组件里写 `if (state === 'x') style.color = ...` 的散落分支。
- **Do** 让表情/口型只响应真实事件（`expressionFrame` 由 reducer 随 `stream.delta` 递增）；**Don't** 用定时器或假进度模拟智能。
- **Do** 给每个新色对做对比度计算；**Don't** 肉眼判断"看起来够亮"。
- **Do** 把不可用状态说出来（`MODEL_UNAVAILABLE`）；**Don't** 用脚本回复或占位文案冒充真实模型/真实集成。
- **Don't** 在承载文字的容器上使用渐变背景（见 Elevation 节，会让自动化对比度检查失效）。
- **Don't** 引入第三方角色素材或权重。`assets/third-party/` 必须保持只有 `.gitkeep`。

## Responsive Behavior

实测三档视口（1280×900、375×720、640×512≈200% 缩放）× 两态（idle、awaiting_approval）：

- 横向溢出：第五轮（2026-10-14，raster 默认）复测三档全部 `scrollWidth == innerWidth`。历史：第二轮修复 `414 > 375`；此后面板扩充（GF05 学习 / GF06 记忆 / GF09 语音外壳）引入长 token 撑破标题的回归 `384 > 375`，第五轮定位为 `.astryn-title` 缺 `overflow-wrap: anywhere` 并修复。
- 键盘 Tab：第五轮实测 DOM 可聚焦 55（idle）/ 63（审批态）、Tab 落点 40/40（去重 25/26），焦点环 <2px 或缺失 **0**，聚焦时横向裁切 **0**，触控目标 <24px **0**（第二轮为 13/15 可聚焦，差额来自面板扩充；`.devhost-input/textarea` 的焦点环在第五轮按同一公约补显式声明）。
- 窄屏（≤420px）宿主侧栏全宽堆叠；角色面板 `min(360px, 100%)` 自适应。
- `prefers-reduced-motion: reduce` 下停用 `.astryn-spin / .astryn-breathe / .astryn-dots`，且角色 SVG 的 `data-motion` 转为 `off`。系统偏好**只增强不削弱**：系统开启后应用内开关禁用并显示"系统已在减少动效"（第四轮实现；CDP `Emulation.setEmulatedMedia` 双上下文 15 项检查实测生效）。

## Motion

只用 `transform` 与 `opacity`（合成层），无 `mix-blend-mode`、无逐帧 `filter`。三个环境动画（环旋转、呼吸、思考点漂移，周期 6s / 4.2s / 2.4s）属于回退渲染器 `xiaoqi-svg-v1` 的产物；默认渲染器 `xiaoqi-raster-v2` 是九态位图静帧，零环境动画（`maxAmbientAnimations: 0`，`data-motion="off"`，reduced-motion 天然满足）。SVG 渲染器的口型变化**不是动画**，是逐条真实数据驱动的离散帧。

## Known Gaps（needs-design-decision）

1. **亮色主题未定义**：当前只有深色一套。`AstrynCharacterAppearance.theme` 已预留 `'dawn'`，但无对应令牌集——需要设计决策，不自行发明。
2. **角色尺寸与面板比例**在 <340px 宽度下未实测（开发宿主最小验证到 375px）。
3. **中文字宽与截断**：长 URL / 无空格英文串依赖 `overflow-wrap: anywhere`。第五轮（2026-10-14）做了首轮视觉走查：定位并修复 `.astryn-title` 缺 `anywhere` 导致 375 档横向溢出（实测归零）；走查仅覆盖当前面板集，新增长 token 文案时需回归。
4. **语音形态（voice-only）无视觉语言**：P2 前不应补，避免凭空设计。
5. 状态色 `speaking #ffb454` 与 `awaiting_approval #ffd166` 色相接近，靠字形（无 vs `?`）与卡片区分；若后续状态继续增多需重新拉开色相距离。

## 验证与防漂移

- `tests/boundary/design-tokens.test.ts`：从 `astryn.css` 解析令牌，断言每组文字/背景对比度 ≥4.5:1、九态环色 ≥3:1、承载文字容器无渐变背景、组件规则内零硬编码十六进制色。
- `tests/presentation/companion-shell.test.tsx`：九态视觉签名两两唯一；系统级 reduced-motion 三测（matchMedia stub：系统开启即 `data-motion=off` 且开关禁用、实时 change 事件翻转、禁用态点击不可覆盖）。
- 系统级 reduced-motion 浏览器级证据（第四轮）：CDP 探针在默认与 `reduce` 双上下文实测三层防线（产品层 `data-motion`、运行时零运行中动画、CSS 媒体查询强制挂类后 `animationName=none`），报告 `.project-local/runs/q7-reduced-motion.report.json`。
- axe（WCAG2 A/AA + 2.1 A/AA）扫描纳入 `docs/verification/M0-VALIDATION.md`，并**必须报告 axe 未判定（incomplete/inapplicable）的节点数**——零违规不等于通过。
- a11y 重扫（第五轮，2026-10-14，raster 默认）：三视口 × 两态 6 屏，axe 违规 0 / `incomplete=[]` / `inapplicable=40`、键盘焦点环缺失 0、横向溢出 0。原始证据 `.project-local/runs/node-libs/design-qa-out/a11y-scan.json`（sha256 `7107fe2e…`，105795 字节）与修复前/后两份 stdout（`.project-local/runs/a11y-rescan-n4{,-afterfix}.stdout.txt`）；此期间修复 `.astryn-title` 溢出与 `.devhost-input/textarea` 焦点环两处回归。
