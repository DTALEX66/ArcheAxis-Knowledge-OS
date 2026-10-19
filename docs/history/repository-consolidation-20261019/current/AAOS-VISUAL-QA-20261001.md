# AAOS Home 视觉 QA（2026-10-01）

状态：`PARTIAL / SOURCE_AND_NATIVE_IMAGE_REVIEW`。本轮只比对 B10 HTML 结构/CSS 与一张 Formal 原生 Home 截图；没有将 B10 在相同逻辑尺寸渲染，故没有像素级差分、量化色差或全页面通过结论。

## 精确输入

- 母版：`D:\All projects\UI套件\10_B10_最终版高保真可部署UI\archeaxis_最终版_高保真可部署UI.zip!/index.html`（42,376 B），`renderHome()` 与 CSS 是本轮核对来源。B10 包无单独图片文件。
- 将该 ZIP 成员原样复制到本仓忽略目录 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\acceptance\AAOS-B10-20261001\index.html`，SHA-256 `1DA1FE0D1FEB55DB98FBA5E28CDBAF2E261E7EC4F562D3410CC9B7E74B3149F1`；没有改动 UI 套件或源 ZIP。
- 原生截图：`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\be268a2d33\f5f5cc6b06db\artifacts\desktop-launch\2c083e046109472993d1fac1bec8dd09\home-core-final.png`，PNG 1600×1125，SHA-256 `A2FC1FD23E5DAEF0B91132EF58C9EE9D3E741A4C6C0A03A35636028F3E03F33F`。
- 截图由独立 Desktop 验证任务以 `--ui-capture home 1280 900 aurora` 生成，逻辑 1280×900 DIP，显示缩放 125%；受测 Desktop DLL SHA-256 `8B46166F536BAFFCE3AC0E31B368B6AA722BCA84E856E114B50149470EC29275`。Core `WAIT=1`，合成测试数据库、真实 Core 回应。上述是该截图来源，不能推断用户数据库或 Green 根目录安装结果。

## 对照结果

| 维度 | B10 母版源结构 | 原生截图可见情况 | 判定与具体修复方向 |
|---|---|---|---|
| 主布局 | 左 rail、顶部搜索/通知、Home 标题与动作；四 KPI；最近证据/今日进度；下方 Memory Graph/节点详情并排 | rail、搜索、标题、动作、四 KPI、最近证据/今日进度与 Memory Graph 均出现；1280 DIP 截图中的 Memory Graph 占整行，节点详情不在首屏 | 主信息架构已接近，但 Graph/节点详情在此宽度的分栏与 B10 `split{1.35fr .95fr}` 未证明一致。核对 Avalonia 内容区断点与 B10 视口断点；以相同 1280×900 渲染后裁定。 |
| 字体与层级 | `Inter, Segoe UI, PingFang SC, Microsoft YaHei, Noto Sans SC`；标题、KPI 大字、次级来源文本 | 标题、KPI 和次级说明层次清楚；中文看起来是系统字体回退 | 实际字体家族、字号、字重、字距未逐像素验证。确认 Avalonia 字体回退和 B10 CSS 具体值，避免中英混排基线漂移。 |
| 色彩 | `#061118` 背景、`#0C1C26/#102630` surface、Teal 交互、Ivory 字、少量 gold | 深空黑蓝底、青色主要捕获按钮、米白正文、细青色边框；图节点用金色环 | 方向吻合；截图肉眼无法证明精确 token 数值。应从运行时截图采样并与母版同尺寸图比色；金色只用于节点/可信重点。 |
| 间距与卡片 | B10 四 KPI 等列；最近证据与进度比例 `1.2fr 1fr`；下方 `1.35fr .95fr` | 四 KPI 等列；最近证据略宽于进度；Memory Graph 顶部在约 570 DIP，首屏下部被裁切 | 首两排构图接近。下排因高度和宽度分栏差异需修复或根据母版响应规则证明合理；不能仅以截图有滚动条视作通过。 |
| 图标与配图 | B10 导航为空心点；图谱由内嵌 SVG 节点/边绘制；没有独立 PNG/照片 | 左 rail 空心点；最近证据空态为矢量图标；Graph 为 Avalonia 矢量节点/边 | 资产种类一致。节点排列、路径、线宽、空态图标几何及应用品牌标尚未逐图校准；截图可见 Graph 下半部被首屏裁切。 |
| 数据语义 | B10 HTML 内含演示 KPI `12/72%`、Capture/Linking/Output 样例数及模拟证据 | 截图显示 Core evidence `0`、其他为 `—`/`Core 未提供`，最近证据为空态 | 与用户真实后端要求一致，应保留真实空/不可用态，不把 B10 演示数复制进产品。由此无法用样例内容做逐像素文本长度对齐。 |
| 交互/动效 | B10 `floatGlow`、`dashMove`、`pulse`、`scanSweep`，节点点击详情、按钮/Toast/Drawer | 单帧只证明控件渲染 | `UNVERIFIED`；需视频/帧差分与鼠标、键盘、reduced motion、后台暂停实测。 |

## 仍需的验收

在同一 1280×900 逻辑尺寸渲染 B10，再按区域比较 rail、Home 标题、四 KPI、证据/进度双栏、Graph/详情下排、图标和视觉 token；随后覆盖 720/1440 DIP、Aurora/Monochrome 与用户要求的 DPI/窗口缩放。本轮浏览器库存为空，`npx --no-install playwright-cli --version` 返回 `could not determine executable to run`；遵照不安装新依赖的边界，1280/720 DIP 母版截图均为 `NOT_EXECUTED`。此文只支持上述单张 Home 截图的静态观察，其他页面和主题 `NOT_EXECUTED`。
