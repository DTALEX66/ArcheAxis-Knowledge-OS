# 元枢·紫曜 Violet Core 设计系统

## 1. 视觉定位

关键词：

- 专业
- 深邃
- 认知
- 克制
- 高密度
- 长时间可用
- 非游戏化
- 非普通 SaaS 后台

视觉母版来自你上传的旧紫晶概念图，但必须去除 Obsidian 名称与近似标志，
重绘成元枢“轴心晶核”。

## 2. 色彩比例

- 70%：深蓝黑与中性面板；
- 15%：灰蓝层级；
- 10%：紫曜品牌色；
- 5%：语义状态色。

## 3. 核心颜色

- App Background：`#070A13`
- Deep Surface：`#0B1020`
- Surface 1：`#10172A`
- Surface 2：`#141D34`
- Surface 3：`#1A2540`
- Text Primary：`#F3F5FA`
- Text Secondary：`#A3ACC0`
- Border：`rgba(155, 121, 255, 0.16)`
- Border Strong：`rgba(155, 121, 255, 0.36)`
- Violet Core：`#7C5CFF`
- Violet Bright：`#AA76FF`
- Evidence Blue：`#4DB7FF`
- Approved Green：`#4DBB84`
- Review Amber：`#D8A84E`
- Failed Red：`#D65A67`

## 4. 状态语义

紫色不能承担所有状态：

- 当前选中 / 品牌 / Agent 核心：紫；
- Evidence / Source：蓝；
- Approved / Complete：绿；
- Candidate / Review：琥珀；
- Failed / Conflict：红；
- Waiting / Planned：灰蓝。

## 5. 面板

- 主卡片圆角：10–12px；
- 工具面板圆角：8px；
- 按钮圆角：7–8px；
- 不使用大号胶囊按钮作为主风格；
- 边框优先于大阴影；
- 发光仅用于当前步骤、轴心核心、严重状态；
- 玻璃透明只用于顶栏和浮层，不用于长文编辑区。

## 6. 字体

不打包或分发字体文件。

使用系统字体栈：

```css
font-family:
  "Microsoft YaHei UI",
  "Noto Sans SC",
  "Segoe UI",
  Inter,
  system-ui,
  sans-serif;
```

品牌标题可使用系统可用衬线字体，缺失时回退。

## 7. 阅读模式

长文、Evidence 和知识编辑区：

- 提高面板亮度；
- 减少背景星点；
- 关闭持续动画；
- 行宽 72–88 字符；
- 正文对比度达到 WCAG AA；
- 支持 Focus Mode。

## 8. 晶核使用规则

允许出现：

- 启动页；
- 观心首页；
- Agent 核心；
- 空白画布；
- About；
- 完成动画。

禁止：

- 每张卡片都放晶体；
- 把晶体当普通列表图标；
- 使用与 Obsidian 官方标志近似的轮廓。

## 9. 动效

- 默认 120–220ms；
- 当前执行路径可有轻微脉冲；
- Respect `prefers-reduced-motion`；
- 不使用持续漂浮粒子干扰阅读；
- 不让加载动画伪装成真实执行进度。

## 10. 工作区布局

默认：

- 一级 Rail：56px；
- 二级栏：248–280px；
- Inspector：320–380px，可折叠；
- 顶栏：48–56px；
- 活动坞：40px 收起，160–220px 展开；
- 中央区域自适应。

小屏：

- Inspector 抽屉；
- 二级栏可折叠；
- 最小支持 960×640 桌面壳；
- 390px 浏览器回归仍需无横向溢出。
