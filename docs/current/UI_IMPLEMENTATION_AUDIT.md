# AAOS UI 套件实现审计

日期：2026-09-22
范围：`D:\\All projects\\UI套件` 中明确归属 ArcheAxis / AAOS 的 B01–B10 单项目包，以及当前 AAOS Avalonia P3 壳层。
状态：`TESTED_LOCAL / READ_ONLY_AUDIT`。本报告不是 UI 实施完成声明。

## 1. 权威来源与冲突规则

UI 套件总索引为：

`D:\\All projects\\UI套件\\00_索引与说明\\00_批次顺序_文件映射_权威规则.md`

批次优先级：`B10 > B09 > B08 > B07 > B06 > B05 > B04 > B03 > B02 > B01`。

AAOS 专属色彩必须同时核对：

`03_B03_页面级UI与AAOS配色纠正_L3\\AAOS_配色纠正母版_v2.zip`

本审计没有读取凭据、会话、浏览器数据，也没有修改 UI 套件源目录。参考包仅解压到当前项目的忽略目录：

`.project-local\\ui-audit\\references`

## 2. 套件内容核对

| 批次 | AAOS 内容 | 可验证结论 |
|---|---|---|
| B10 | `archeaxis_最终版_高保真可部署UI.zip` | 单文件高保真静态 UI；包含完整产品域、光效、渐变、Toast、Modal、Drawer、Command Palette。 |
| B09 | `archeaxis_L9_交互式真实Demo.zip` | Capture→Evidence、搜索过滤、引用插入、Memory Map、FSRS-like review、Command Palette 等交互参考。 |
| B08 | `archeaxis_L8_React_TypeScript_可运行原型.zip` | React 18 + Vite 5 + TypeScript 5；含 AppShell、PageHeader、KPI、Card、DataTable、Status、MiniChart、NodeGraph。 |
| B07 | `ArcheAxis_L7_前端开发规范工程包.zip` | 13 个产品路由、Page State、响应式、可访问性、权限和工程架构契约。 |
| B06 | `ArcheAxis_L6_18张交互状态+Tokens.zip` | Hover、Focus、Keyboard、Modal、Drawer、Empty、Loading、Error、Permission、Approval、Version 等状态参考。 |
| B05 | `ArcheAxis_L5_12张高保真产品页面.zip` | Home、Capture、Evidence Library/Detail、Originals、Human/Machine Learning、Workspace、Memory、Search、Review、Settings。 |
| B04 | `ArcheAxis_L4_组件系统_16张+Tokens.zip` | 组件、Tokens、密度、圆角、动效、响应式、可访问性和开发交接。 |
| B03 | `ArcheAxis_10张页面级UI_统一体系.zip` + AAOS 配色母版 | 信息架构、模块地图、导航、首页、Capture、Evidence、Original、学习、搜索/复习。 |
| B02 | `ArcheAxis_L2_VI+UI_36张细节图.zip` | 星环、轨道、轴、证据节点、记忆轨迹、图标和详细页面结构。 |
| B01 | `ArcheAxis_VI+UI_24张全套.zip` | 基础 VI、Logo、色彩、字体、图形语言和产品信息架构。 |

## 3. AAOS 设计结论

### 3.1 视觉 Tokens

```text
background  #061118
sidebar     #091821
surface     #0C1C26
surface-2   #102630
border      #1D5055
primary     #1FC8C5  Aurora Teal
secondary   #E6BE73  少量星辉金
text        #F3EFE6  Ivory
muted       #96AAB4
success     #37C99A
error       #E56464
info        #3B82F6
```

B04 的基础尺度为 `4/8/12/16/24/32/48/64`，圆角为 `4/12/18/24`，密度包含默认 `56` 与紧凑 `44`。金色只能承担证据、可信节点、警告和极少量关键强调，不得成为主按钮、侧栏或大面积边框。

### 3.2 产品 IA

AAOS 的核心闭环是：

`Capture → Evidence → Original → Human/Machine Learning → Memory → Review/FSRS`

这不是普通 Dashboard、模型控制台或笔记软件。AI/机器内容必须与原始证据、来源链和人工原创在视觉上明确分层。

### 3.3 当前 Avalonia P3 对照

当前实现已经具备：

- Avalonia 正式桌面壳；
- 一级空间、上下文导航、主工作区、Inspector、Activity Receipt Dock；
- Library 搜索、Source members、Knowledge V3、学习/FSRS、Machine task、Recovery/Settings 的部分 Core projection；
- headless Desktop→Core→FSRS→SQLite 冷启动回读证据。

但它仍是 Core 投影优先的 P3 壳层，不是 B05/B10 完整产品 UI。主要差距：

| 套件要求 | 当前事实 | 状态 |
|---|---|---|
| 13 个正式页面路由 | 当前以 5 个一级空间和内部 section 组织 | `PARTIAL` |
| AAOS Tokens | `AaosTheme.axaml` 已集中承载颜色、状态、间距、圆角、密度、断点与命令手势 token；页面仍需逐步消费全部尺度资源 | `PARTIAL` |
| Evidence Library/Detail | 目前只有部分 Library/Knowledge Core 投影 | `PARTIAL` |
| Original Editor/CitationPicker | 未形成真实产品页面 | `MISSING` |
| ReviewCard/FSRSGradeButtons | headless FSRS 已有，完整视觉交互未有 | `PARTIAL` |
| MemoryGraph/节点详情 | 尚未形成真实 Core-backed 图谱页面 | `MISSING` |
| Loading/Empty/Error/Permission/Version | 多处仍为单个文本状态 | `PARTIAL` |
| Command Palette/Modal/Drawer/Toast | 尚未形成完整 B06 契约 | `MISSING` |
| 真实 GUI 首用 | 当前 CUA 未读回原生窗口 | `NOT_EXECUTED` |

## 4. 推荐实施顺序

1. 继续让现有页面消费 `AaosTheme.axaml` 中的 B04/L7 资源键，避免重新散落硬编码；金色只保留证据/可信节点。
2. 将剩余页面级布局尺度与状态逐步替换为 AAOS 语义资源，并以真实 Core projection 驱动状态。
3. 抽取 `AaosCard`、`AaosKpi`、`AaosStatus`、`AaosToolbar`、`AaosEmptyState`、`AaosProvenanceTag` 等共享组件。
4. 优先完成真实 Core-backed `Capture Inbox → Evidence Library → Evidence Detail → Review/FSRS`。
5. 再补 `Original Editor + CitationPicker`、`MemoryGraph` 和统一状态系统。
6. 最后做 GUI 截图、点击、状态回读和视觉 QA。

不得直接复制 B08/B09/B10 的静态数字、localStorage 或演示数据进入正式 Core UI。

## 5. 证据边界

- UI 套件 ZIP 条目、文本和代表性图片已读取；B08/B09/B10 的套件 GUI 本轮未运行。
- Avalonia Debug build 与 P3 静态契约已有本地通过证据；真实 GUI 仍未验证。
- 本审计没有提交、推送、安装、签名、覆盖 Green 或写入外置资源库。
