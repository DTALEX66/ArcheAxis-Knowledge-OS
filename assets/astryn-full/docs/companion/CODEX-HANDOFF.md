# ASTRYN 前端 UI 交接（CODEX 范围）

日期：2026-10-16 · 维护方：小栖资产线（素材侧）

> 边界：界面前端 UI 实现归 CODEX。本文件只登记"素材已就绪 + 行为规格 + 接缝位置"，不代替 CODEX 的实现决策；CODEX 接线后请在条目内回填实际实现位置（文件:行），保持单向登记。
> 素材登记处：`assets/character/STATE-ASSET-INDEX.json`；资产状态与派生成分：`docs/companion/GF03-ASSETS-AND-STATES.md`。

---

## C1 说话口型 / 眨眼帧交换接线（素材已就绪，待接）

### 素材（全部 runtimeUsable=true，已登记）

| 用途 | 文件 |
| --- | --- |
| 口张开 = 静帧基准 | `assets/character/upgraded/v1/xiaoqi_state_speaking_sleepwear_v1.png`（speaking 母版本身） |
| 口闭合 | `assets/character/upgraded/v1/derived-frames/xiaoqi_mouth_closed_sleepwear_v1.png` |
| 口半开 | `assets/character/upgraded/v1/derived-frames/xiaoqi_mouth_half_sleepwear_v1.png` |
| 眨眼闭合 | `assets/character/upgraded/v1/derived-frames/xiaoqi_blink_closed_sleepwear_v1.png` |
| 眼睁 = 静帧基准 | 同 speaking 母版（无需另存） |

三帧与母版同机位、同构图、同光照；ROI（口部/眼部）外零差异像素（机验 PASS，回执 `.project-local/runs/derived-frames/acceptance-e-frames.md`）。

### 现状（实测）

- `src/avatar/xiaoqi-raster-renderer.ts` 为九态静帧：只按 `frame.visibleState` 选图，输出 `data-motion="off"`，**不读 `frame.expressionFrame`**。
- 契约字段已在：`AstrynAvatarFrame.expressionFrame`（`contracts/avatar.ts`）；`src/companion/reducer.ts` 已在流式文本到达时递增该帧；`src/presentation/companion-view.tsx` 已把整帧传入渲染器。
- v1 SVG 渲染器有离散口型循环（`MOUTH_CYCLE`）——那是回退下限路径，不作为接线目标。

### 目标行为（建议规格；实现方案归 CODEX）

1. speaking 态：随流式文本到达节奏，在 口闭合/半开/张开 三帧间离散交换；单帧驻留 >120ms（防频闪）；文本流结束回静帧（口张开母版）。
2. 眨眼：低频单次（闭合帧驻留 80–120ms），随机间隔 3–6 秒一次；仅眼睁开态（idle/listening/speaking 等）适用。
3. 切换必须瞬切（img src 替换或双 img 叠加），不做交叉淡入（防重影）；三帧同机位同构图，天然无位移跳变。
4. `prefers-reduced-motion: reduce`：禁用帧交换，保持静帧。
5. 红线：这是**文本事件驱动的帧交换，不是音素口型**；不得引入 viseme/音素时间戳宣称；`audioDriver` 保持 null（GF09 接通后另议）。

### 接缝建议

契约与数据流已就位（帧号在 reducer 侧递增）；可选两条实现路线，由 CODEX 定：

- a) 渲染器层：raster renderer 消费 `expressionFrame` 选图（素材→图映射写死在渲染器内部常量）；
- b) UI 层：`AvatarView` 按可见状态与帧号叠加帧交换。

无论哪条，素材引用必须继续走**构建期 import 常量**，不得引入运行时字符串拼接（渲染器不变量：写入 DOM 的字符串只由内部常量、构建期资源 URL 与数值拼装）。

## C2 D 组三呈现构图参考件（可选采纳，runtimeUsable=false）

派生自 idle 母版原生像素画布重排（无缩放无重绘），回执 `.project-local/runs/derived-refs-d/derive-report-d-group.json`：

| 呈现 | 文件 | 尺寸 / 机验 |
| --- | --- | --- |
| 首页 | `assets/character/upgraded/v1/xiaoqi_home_sleepwear_v1.png` | 4552×2528；主体左 1/3、右侧 2/3 全透明（机验） |
| 头像 | `assets/character/upgraded/v1/xiaoqi_avatar_sleepwear_v1.png` | 904×904；眼线 45.9%H、头宽 523 ≤ 圆内径 777（机验） |
| 侧边 | `assets/character/upgraded/v1/xiaoqi_sidebar_sleepwear_v1.png` | 1255×2510；左右边距 175/177px、顶留白 18%H（机验） |

现状呈现层用 CSS 从同一宽度令牌出图（`src/avatar/render-profiles.ts` 三档 + `src/presentation/astryn.css` 裁切）。是否改用这三张构图件（或仅参考其构图比例调整 CSS）由 CODEX 决定；采纳后需同步登记 `runtimeUsable`。

## C3 动态序列帧（预留，等 H7 素材）

idle 呼吸循环源视频已在交接清单 H7（MINIMAX 侧生成，5 秒 / 24fps / 纯色底）。回传后项目侧抽帧 → 去背 → 登记，届时在本条补素材路径与帧序规格；帧交换机制与 C1 相同。

## 记录规则

- 条目状态：待接 / 已接 / 驳回；接线后回填实现位置，素材侧不改 CODEX 的 hunk。
- 素材侧新增或替换帧素材时，在本文件对应条目追加一行并注明提交号。
