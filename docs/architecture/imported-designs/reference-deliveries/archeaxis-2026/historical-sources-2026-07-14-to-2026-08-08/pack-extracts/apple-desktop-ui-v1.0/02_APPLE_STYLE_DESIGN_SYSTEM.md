# 苹果式元枢设计系统

## 1. 定位

这是“苹果式生产力软件语言”，不是 macOS 像素复制。

允许吸收：

- 克制留白；
- 清晰层级；
- 磨砂玻璃；
- 精细阴影；
- 柔和渐变；
- 圆润但不儿童化；
- 图标简洁；
- 文字优先；
- 动效自然。

禁止：

- 使用 Apple Logo；
- 分发 Apple 字体；
- 复制系统应用图标；
- 复制具体系统窗口资产；
- 让界面看起来是未经授权的 macOS 克隆。

## 2. 字体

不打包字体文件。

系统字体栈：

```css
font-family:
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  "Microsoft YaHei UI",
  "Noto Sans SC",
  system-ui,
  sans-serif;
```

## 3. 颜色

### 基础

- `--bg-app: #F4F7FC`
- `--bg-panel: rgba(255,255,255,.82)`
- `--bg-solid: #FFFFFF`
- `--text-primary: #10162B`
- `--text-secondary: #6F7890`
- `--border-soft: rgba(45,61,105,.09)`
- `--border-strong: rgba(91,82,230,.18)`

### 品牌

- `--accent: #5B57F1`
- `--accent-2: #7E68FF`
- `--accent-soft: rgba(91,87,241,.10)`
- `--glow-blue: #59B6FF`
- `--glow-violet: #A687FF`

### 语义

- Available / Success：`#21B87A`
- Evidence / Info：`#2989F5`
- Review / Candidate：`#F3A629`
- Conflict / Failed：`#EF5662`
- Planned / Disabled：`#A0A9BA`

## 4. 渐变

背景只使用很淡的环境光：

```css
background:
  radial-gradient(circle at 72% 0%, rgba(125,105,255,.13), transparent 30%),
  radial-gradient(circle at 15% 20%, rgba(79,181,255,.10), transparent 35%),
  #F4F7FC;
```

主按钮可使用蓝紫线性渐变，但不得每张卡片都渐变。

## 5. 卡片

- 圆角：14–18px；
- 内边距：16–22px；
- 边框：1px soft border；
- 阴影：`0 8px 28px rgba(35,52,95,.07)`；
- 卡片间距：12–16px；
- 面板不要过度透明；
- 长文编辑区优先纯白。

## 6. 布局

- 左导航：220–248px；
- 顶栏：60–68px；
- Inspector：300–340px；
- 底栏：36–44px；
- 主内容最大宽度根据页面决定，不强制居中窄栏；
- 960×640 为桌面最小边界；
- 390px 仅保证核心浏览器流程可操作。

## 7. 组件状态

- Hover：轻微边框和阴影增强；
- Pressed：缩放不超过 0.99；
- Focus：2px 蓝紫 Focus Ring；
- Disabled：降低对比，不使用透明到看不清；
- Loading：骨架屏或小型 Spinner；
- 不使用无法对应真实进度的进度条。

## 8. 图标

- 使用统一线性图标；
- 16/18/20/24px 四档；
- 状态图标可使用实心小圆；
- 不混用 Emoji 作为正式导航图标；
- 品牌轴心标志独立绘制。

## 9. 动效

- 120–220ms；
- 页面切换淡入 + 轻微位移；
- Drawer/Inspector 使用 spring-like easing；
- 遵守 `prefers-reduced-motion`；
- 禁止持续漂浮和高频光效。

## 10. 明暗主题

本轮先完成明亮主题：

- `apple-light`

旧主题继续兼容：

- `violet-core`
- `yaojin`
- `deepspace`

不删除现有主题，避免 localStorage 和用户偏好失效。
