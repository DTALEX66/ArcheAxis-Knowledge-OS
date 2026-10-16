# GF08 首页嵌入与侧边统一呈现（交付说明）

任务包 `ASTRYN-COMPANION-20261013` · 分支 `feat/astryn-learning-companion-v1` · 依赖 GF03/GF05/GF06/GF07（均已完成）。

本卡三条 work 的落点：①正式可复用 React 入口 `AstrynCompanionEntry` + 宿主集成交接说明（§3），主页 / 阅读嵌入 / 侧边面板三槽位共用同一会话服务；②角色大小、隐藏、专注与对话高度全部引用前端 tokens（两层令牌：per-slot/per-view 基值 + `data-*` 属性映射到生效值）；③只改 ASTRYN 自己的代码与合同，宿主槽位写入归 FE18（BLOCKED_BY_HOST_CONTRACT）。

## 1. 交付物

| 路径 | 内容 |
| --- | --- |
| `contracts/presentation.ts` (modified) | 槽位合同：`ASTRYN_HOST_SLOTS`（home/reading/sidebar）、`AstrynHostSlotSpec`（label/mode/avatarView/avatarSizeToken/logHeightToken）、`ASTRYN_HOST_SLOT_SPECS`、`hostSlotSpec()`（未知槽位抛错）；`ASTRYN_FOCUS_PRESENTATION_TOKENS`、`ASTRYN_HIDDEN_FOOTPRINT_TOKEN`。注释写明：槽位只决定模式/取景档/令牌名，不拥有会话。 |
| `src/presentation/host-entry.tsx` (new) | 正式可复用入口：`slot` → `mode` + 取景档；会话经宿主传入的共享 `manager`；不构造任何 conversation/actions/verifier 端口（无第二个模型中心）；尺寸全部经 tokens，宿主覆盖令牌即改尺寸，无需改组件代码。 |
| `src/presentation/companion-shell.tsx` (modified) | 新 props `slot` / `focus`；根元素落 `data-slot` / `data-avatar-view` / `data-focus`（隐藏占位另加 `data-hidden`）；取景档 = `props.slot` 时按 `hostSlotSpec(slot).avatarView`，否则 `avatarViewForMode(mode)`（既有行为不变）。 |
| `src/presentation/astryn.css` (modified) | 两层令牌：基值（`--astryn-avatar-size-{hero,avatar,sidebar,home,reading,focus}`、`--astryn-log-height-{home,reading,sidebar,focus}`、`--astryn-hidden-min-height`）+ 生效默认（`--astryn-avatar-size` / `--astryn-log-max-height`）声明在 `.astryn-root`（0,1,0）；`[data-avatar-view]` / `[data-slot]` / `[data-focus="true"]` / `[data-hidden="true"]` 映射规则（0,2,0，focus 必须写在槽位之后——顺序即语义）；`.astryn-avatar svg` 宽与 `.astryn-log` max-height 改走令牌（240px 字面量移除）。 |
| `src/index.ts` (modified) | 导出 `AstrynCompanionEntry` 与 `AstrynCompanionEntryProps`。 |
| `dev-host/app.tsx` + `dev-host/dev-host.css` (modified) | 「宿主槽位演示」区：三槽位各挂一个 `AstrynCompanionEntry`，共用同一 manager 与同一组宿主端口；专注输入由学习面板 `mindset.focusMode` 联动（演示接线）；边界清单新增槽位条目（正式槽位由 FE18 写入）。 |
| `tests/presentation/host-slots.test.tsx` (new, 5) | 槽位→模式/取景档/尺寸（home 240 hero embedded；reading 168 sidebar embedded；sidebar 168 sidebar panel）+ `NO MODEL`；三槽共享一个管理器（viewCount=3、一次提交 streamCalls=1、三处日志同显）；逐个卸载不销毁（viewCount 3→2→0 后重挂载 reading 记录仍在、可继续提交）；专注 `data-focus` 翻转；隐藏 `data-hidden` 保留槽位并可恢复。 |
| `tests/presentation/presentation-tokens.test.ts` (new, 5) | 契约令牌全部在 CSS 有定义且 `modeSpec(implementedInM0)` 为真；槽位/取景/隐藏映射规则在位；focus 规则索引晚于全部槽位规则（对齐「顺序即语义」）；`svg` 宽与 log 高度走令牌且 CSS 无 `max-height: 240px` 字面量；未知槽位抛 `/unknown host slot/`。 |

## 2. 验收对照（任务包 GF08 卡）

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 集成不需要第二个正式前端或独立模型中心 | PASS | 入口只渲染 `CompanionShell`，不构造任何模型端口；未注入 conversation 时证据标签为 `NO MODEL`（单测）；三槽挂载共享同一注入端口——一次提交 `streamCalls===1`（不各自建模型通道）；正式槽位由 FE18 写入 AAOS 前端，本仓库只交付可挂载入口与合同；dev-host 槽位区仅是演示宿主。 |
| 每种呈现保持同一 session，组件卸载不意外销毁共享会话 | PASS | 三槽同 sessionId + 同一 manager：viewCount=3；浏览器实测在主页槽位提交一句 ⇒ 左侧 aside 与三个槽位日志同时出现同一轮回复；单测逐个卸载 viewCount 3→2→0、重挂载 reading 后历史仍在且可继续提交；延迟销毁语义由 GF02 既有 `disposeWhenUnobserved` 承担（最后视图离开后按规则销毁，宿主显式 dispose 除外）。 |
| work①：正式入口 + 交接说明；三槽共用服务 | PASS | `AstrynCompanionEntry` + 本文 §3（集成交接）；共用性见上行证据。 |
| work②：大小/隐藏/专注/对话高度引用 tokens | PASS | 契约令牌表 + CSS 映射 + 门禁测试（presentation-tokens）；浏览器实测令牌值 240/168/112/72/128px 全部可读回。 |
| work③：只改 ASTRYN 自己；FE18 负责槽位 | PASS（FE18 侧未接线） | 变更文件全部在 allowed_roots；FE18 槽位写入 BLOCKED_BY_HOST_CONTRACT（§3.6）。 |

## 3. 宿主集成交接（FE18 · integration handoff）

### 3.1 消费形态（当前事实）

- 本仓库未发布 npm 包（`package.json` `private: true`）。消费经源码/路径别名：`vite.config.ts` 已示范 `@astryn/core` → `src/index.ts`、`@astryn/contracts` → `contracts/index.ts`。FE18 需在自己构建里配等价别名（或 workspace 引用）。
- 运行时：React 18（`react ^18.3.1`）；组件不引入任何其它第三方 UI 库。
- 样式随组件带入：`companion-shell` 内 `import './astryn.css'`，打包器自动收录；宿主无需单独引样式。
- 唯一公开入口：

```tsx
import { AstrynCompanionEntry } from '@astryn/core';
```

### 3.2 槽位表（真源 `ASTRYN_HOST_SLOT_SPECS`，contracts/presentation.ts）

| slot | label | mode | 取景档 | 角色大小令牌（默认值） | 对话高度令牌（默认值） |
| --- | --- | --- | --- | --- | --- |
| `home` | 主页嵌入 | `embedded` | `hero` | `--astryn-avatar-size-home`（240px） | `--astryn-log-height-home`（240px） |
| `reading` | 阅读嵌入 | `embedded` | `sidebar` | `--astryn-avatar-size-reading`（168px） | `--astryn-log-height-reading`（240px） |
| `sidebar` | 侧边面板 | `panel` | `sidebar` | `--astryn-avatar-size-sidebar`（168px） | `--astryn-log-height-sidebar`（240px） |

（默认值为实测值：浏览器计算宽 240/168px、对话区 240px。）

### 3.3 会话与端口规则（宿主职责）

1. **会话归宿主**：`createCompanionSessionManager({ sessionId, profile, conversation, actions, verifier }, { disposeWhenUnobserved: true })` 由宿主建一次，三槽位把**同一实例**经 `manager` prop 传入；每个槽位组件只 retain 一个视图。
2. **端口归宿主**：`conversation` / `actions` / `verifier` / `profileStore` 全部由宿主注入；入口不构造任何模型通道。未注入 `conversation` 时呈现 `NO MODEL`（正常降级，不是错误）。
3. **卸载语义**：一个槽位卸载 = release 一个视图，不销毁会话；管理器生命周期由宿主掌控（例如宿主应用退出时 dispose）。
4. `sessionId` 由宿主提供且三槽一致；星栖不铸造会话身份。

### 3.4 令牌覆盖规则（宿主定制尺寸/主题）

- 基值令牌声明在 `.astryn-root` 上（特异度 0,1,0）；生效值 `--astryn-avatar-size` / `--astryn-log-max-height` 由 `data-slot` / `data-avatar-view` / `data-focus` 映射（0,2,0）。
- **宿主覆盖必须写在与 `.astryn-root` 自身匹配、特异度 ≥0,2,0 的选择器上**：

```css
.aaos-home-slot .astryn-root { --astryn-avatar-size-home: 200px; }
```

  写在祖先容器上（不含 `.astryn-root`）不会生效——`.astryn-root` 自身声明的值优先于继承值。
- 专注（`data-focus="true"`）与隐藏（`data-hidden="true"`）由组件按宿主传入的 props 落属性；focus 映射与槽位映射同特异度、靠源序在后取胜（有门禁测试钉住顺序，勿调序）。

### 3.5 接线示意（FE18 侧形状）

```tsx
// 宿主应用层（示意；真实接线归 FE18 / AAOS 前端）
const manager = createCompanionSessionManager(
  { sessionId, profile: XIAOQI_PROFILE, conversation, actions, verifier },
  { disposeWhenUnobserved: true }
);

<aside className="aaos-sidebar-slot">
  <AstrynCompanionEntry
    slot="sidebar"
    sessionId={sessionId}
    manager={manager}
    conversation={conversation}
    actions={actions}
    verifier={verifier}
    focus={userInFocus}   /* 宿主状态；星栖不自行推断专注 */
  />
</aside>
```

### 3.6 未接通与阻塞

- **FE18 正式槽位写入 BLOCKED_BY_HOST_CONTRACT**：AAOS 前端尚无槽位合同（挂载点/DOM 契约归宿主），本仓库不替宿主决定。
- `floating` / `pet` / `voice-only` 三形态 `implementedInM0=false`（P2：需原生窗口/托盘/ASR-TTS），`contracts/presentation.ts` 已如实标注阻塞原因。

## 4. 门禁与封存（GF08 终局）

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-234143.log`：**lint=0 typecheck=0 test=0 build=0 record=0 anchors=0**（六阶段全 0，一次通过）。
- 测试：**34 文件 / 303 通过**（其中 GF08 新增 10：host-slots 5 + presentation-tokens 5；此前 293）。
- 封存收据 `docs/verification/gates.json`：源码树 **96 文件**（+3：host-entry.tsx、host-slots.test.tsx、presentation-tokens.test.ts），树哈希 `ce9846f0f7c70fba44bce87e5c42c48c6a84a6f8432866fe9172a9fff06f6cb4`；`allGreen: true`；`git.head` `14f0e0d`（GF08 提交前的分支头）。
- 构建产物（实测磁盘字节）：`index-jeSTOzBq.js` 284,009 B，sha256 `b87de972b22109913d5858c51c35e809cc20532a71327279e2cc981dce8b9a2b`；`index-PqCch4VI.css` 11,670 B，sha256 `3e8d7372f43837ecad034ac17102b90fa1a51fa5d13dddb4dfc680fe3ff6ec64`。
- 反证（test falsification）：把 `host-entry` 的 `slot` 忽略（恒取 `'home'`）植入 ⇒ host-slots 测试第 1 条立即变红（1 failed | 4 passed）⇒ 还原后全绿。测试确实钉住槽位映射。

## 5. 浏览器实测（Dev Host，DOM 读数）

`VITE_ASTRYN_ALLOW_SYNTHETIC=1` 起 Vite（127.0.0.1:5183），实测后按 netstat PID 14640 终止、端口释放：

- 三槽初始：home 240px/hero/embedded；reading 168px/sidebar/embedded；sidebar 168px/sidebar/panel；三处对话区 max-height 240px。
- 会话共享：在主页槽位提交一句 ⇒ 左侧 aside 与三个槽位日志**同时出现同一轮回复**（同一 session）。
- 专注：学习面板「专注模式」开启 ⇒ 三槽 `data-focus=true`、头像计算宽 112px、对话区 160px；关闭后恢复 240/168/240px。
- 隐藏：侧栏槽位隐藏 ⇒ `data-hidden=true`、`data-slot` 保留、min-height 72px；恢复后日志仍在。
- 宿主覆盖：注入宿主样式覆盖 reading 槽位令牌 ⇒ `svg` 计算宽 128px；移除 ⇒ 回到 168px。
- 控制台：3 条（vite debug×2 + React DevTools info），**0 错误**。
- 证据形态：结构化 DOM 读数（本会话无截图面）。

## 6. 诚实边界

- **FE18 正式槽位未接线（BLOCKED_BY_HOST_CONTRACT）**：本仓库交付的是可挂载入口 + 合同 + 演示宿主，不等于 AAOS 前端已集成。
- **dev-host 槽位区接线无测试载体**（与 GF05/GF06/GF07 同一盲区，仅浏览器实测）。
- **草稿是每视图本地状态**：四个视图（aside + 三槽）各有一份输入草稿，不跨视图同步；会话记录与任务状态共享。这是既有壳层语义，非缺陷。
- **专注在 dev-host 的来源**是学习面板 `mindset.focusMode` 联动（演示接线）；正式语义是宿主给出 `focus` prop，星栖不推断。
- **SVG 的 width 属性**（240/96/168，来自取景档）保留为无 CSS 情景的回退；浏览器实际宽度由 `var(--astryn-avatar-size)` 决定。
- **隐藏足迹是 min-height 72px 的最小值**，占位仍带「恢复角色」入口；不是像素级承诺。
- **本卡令牌只管四项**（角色大小、对话区高度、隐藏足迹、专注收敛）；`.astryn-root--panel` 宽度 `min(360px, 100%)` 不随槽位变化，容器宽度由宿主布局决定。
- 组件自建管理器路径（不传 `manager` 时）仍存在——但 GF08 的推荐接线是宿主共享 manager；三槽各自不传 manager 会各自建会话（单测锁定的是传入共享实例的语义）。

## 7. 回滚

`git revert` GF08 提交（分支 `feat/astryn-learning-companion-v1` 上单个提交）。新增文件 `src/presentation/host-entry.tsx`、`tests/presentation/host-slots.test.tsx`、`tests/presentation/presentation-tokens.test.ts`；其余为既有文件修改：契约与 CSS 均为**增量**（新增常量与规则；`.astryn-avatar svg` 宽度规则与 `.astryn-log` 由 240px 字面量改走令牌，回滚后恢复原字面量行为）；既有导出与既有组件 props 形状不变（`slot`/`focus` 为新增可选）。无迁移、无宿主侧写入。
