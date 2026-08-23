# AXW-UI-804 — 性能 / 无障碍 / 高 DPI 验收基线

> 状态：验收基线定义（2026-08-15）；逐项在 UI 后续批次按空间落地。
> 关联：frontend/src/design-system/tokens.css（focus-visible / reduced-motion 已实现）。

## 1. 标准硬件基线

- Windows 10/11 x64，8 GB RAM，SSD；
- 1920×1080 @ 100% 与 150% 缩放（高 DPI）；
- 双屏（150% + 100% 混合缩放）。

## 2. 性能验收

| 场景 | 标准 |
|---|---|
| 冷启动（Tauri → Recovery Shell → handshake → 主工作台） | ≤ 5 s（本机 SSD） |
| 后端重启 / 热重载重连 | 状态可见变化 ≤ 1 s；窗口不关闭 |
| 长列表（1 万行知识账本） | 滚动帧率 ≥ 30 fps（虚拟化）；首次渲染 ≤ 500 ms |
| 大型 PDF 打开 | PDF.js worker 不阻塞主线程；翻页 ≤ 300 ms |
| 内存 | 空闲 ≤ 400 MB；连续 2 h 无明显泄漏（任务管理器采样） |

## 3. 无障碍验收（WCAG 2.1 AA 子集）

| 项 | 标准 | 现状 |
|---|---|---|
| 键盘 | 全部交互可达：Tab 顺序、Esc 关闭、箭头导航；focus-visible 可见 | tokens.css 已实现 outline |
| 读屏 | 语义 landmark（header/nav/main/aside/footer）；aria-current 标注当前空间；按钮有 aria-label | 骨架已实现 |
| 状态冗余 | 状态不只靠颜色：text + shape + color（§OSUI v2 statusRedundancy） | 状态徽标含文本 |
| 缩放 | 150%/200% 无布局破裂；无水平滚动（除表格） | 骨架 flex 布局待验证 |
| reduced motion | prefers-reduced-motion 禁用动画/过渡 | tokens.css 已实现 |
| 对比度 | 正文 ≥ 4.5:1；大文本 ≥ 3:1（紫晶色板需对比度复核） | 待 tokens 复核 |

### 当前代码级补充（2026-08-24）

- 六空间导航除标准 Tab/Enter 外，支持 `ArrowUp`/`ArrowDown`、`ArrowLeft`/
  `ArrowRight`、`Home` 和 `End`；移动时焦点与当前空间一起更新。
- 此项由 Vitest 及本地 Vite 的真实浏览器键盘操作验证。浏览器开发模式没有连接
  受认证后端时出现的数据加载错误，不是桌面运行时通过证据。
- 该补充不替代读屏、高 DPI、安装版或 10,000 行实际性能测量；它们仍需在目标
  设备和正式运行时分别取证。

## 4. 高 DPI

- 图标使用矢量（内联 SVG/字符图标，非位图）；
- 最小可点区域 ≥ 44×44 px（rail 按钮已按此设计）；
- Windows 缩放变化时窗口内容自适应（无模糊位图）。

## 5. 验收方式

- 每批次 UI 交付附带：键盘走查清单 + axe-core 扫描（0 critical/serious）+ 缩放截图；
- 冷启动计时在 Release Candidate 用真实安装包测（L4）。
