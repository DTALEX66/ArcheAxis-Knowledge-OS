# AAOS UI 套件吸收审计（2026-09-22）

## 范围与权威链

本次只读取用户明确指定的 `D:\All projects\UI套件`，未读取 E:/F:、Green、凭据或其他外置库。依据套件索引，AAOS UI 的冲突优先级为：

`B10 > B09 > B08 > B07 > B06 > B05 > B04 > B03 > B02 > B01`

已核对 AAOS 专属包：B10 最终 UI、B09 交互 Demo、B08 React 原型、B07 开发规范、B06 交互状态、B05 页面级产品、B04 Design Tokens，以及 B03 AAOS 配色纠正母版和页面级体系。

本项目吸收目标仍是 Avalonia canonical shell；B10/B09 的 HTML/React 实现不是第二套运行时，也没有被复制为正式产品入口。

## 已确认规则与当前决策

| 维度 | UI 套件证据 | AAOS 实装 |
| --- | --- | --- |
| 背景/Surface | B10/B09/B04：`#061118`、`#0C1C26`、`#102630` | `AaosBackgroundBrush` / `AaosSurfaceBrush` / `AaosSurface2Brush` |
| 主交互色 | Aurora Teal `#1FC8C5` | `AaosPrimaryBrush` 与 `primary-action` 渐变 |
| 文字 | Ivory `#F3EFE6`、Muted `#96AAB4` | 固定 Dark 主题，并为 Button/ListBoxItem/ComboBoxItem/CheckBox 提供 Ivory 前景兜底 |
| 星辉金 | `#E6BE73`，只作证据/关键节点强调 | 保留 Evidence/Review 语义色，不作为默认按钮或导航主色 |
| 布局 | 侧栏、Topbar、内容区、面板/抽屉 | Avalonia Rail + Context Sidebar + Workspace + Inspector + Activity Drawer |
| 交互态 | B06 的 Hover/Focus/Modal/Drawer/Empty/Loading/Error/Permission/Responsive | 延续现有 Classes 与状态文本，补齐主题主操作和暗色前景基线 |
| 键盘/触达 | Cmd/Ctrl+K、Esc、Enter、最小 44px | 保留命令面板与 Compact density，主按钮保持 44px 触达高度 |

## 本次实际吸收

1. `apps/ArcheAxis.Desktop/App.axaml` 固定 `RequestedThemeVariant="Dark"`，避免系统主题把 Fluent 默认控件前景带入 AAOS。
2. `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml` 增加 AAOS Aurora Teal 主操作渐变，并为列表、下拉项、复选框等内容控件增加 Ivory 前景兜底，修复“深色背景 + 黑色控件文字”的视觉风险。
3. Home、Capture、Library、Source Reader、Knowledge、Learning/Review 的真实主动作使用 `primary-action`；次要动作继续使用 Surface/Border 语义，不把星辉金扩散成主交互色。
4. Home 仍只投影 Core 真实回执，未把套件中的 demo localStorage、演示 KPI、伪造 Evidence 或 FSRS 数据引入 canonical Avalonia 产品。

## 明确不吸收

- 不复制 B10/B09 的 HTML/React/localStorage 作为第二套产品运行时。
- 不把 demo 中的静态 KPI 迁入 AAOS。
- 不把截图、品牌素材、专属 icon/trade dress 当作代码资产提交。
- 不用 UI 套件演示状态替代 Rust Core 的 Knowledge、Evidence、Learning、Job Truth。

## 当前未完成与下一步

- 主题与主操作层已完成最小吸收，但真实 native GUI 视觉仍需在可用桌面运行环境中截图核验。
- B10/B09 的 `Capture → Evidence → Original → Memory → Review` 交互继续逐项映射到现有 Core contract；不能用 demo 数据补齐缺失后端。
- `tests/test_desktop_launch.py` 仍因当前 Python 环境无 pytest 未执行，不能把静态/构建通过扩大解释为 GUI PASS。

证据等级：`IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC / TESTED_LOCAL_BUILD`；本报告不代表发布、安装、Green 覆盖或外置库写入。
