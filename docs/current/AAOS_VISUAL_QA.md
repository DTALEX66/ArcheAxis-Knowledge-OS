# AAOS 视觉 QA 基线

日期：2026-09-22
证据等级：`TESTED_LOCAL / READ_ONLY_AUDIT`。这是参考套件对照基线，不是当前 Avalonia GUI 已通过的声明。

## 1. 视觉基线

权威参考：

- `D:\\All projects\\UI套件\\03_B03_页面级UI与AAOS配色纠正_L3\\AAOS_配色纠正母版_v2.zip`
- `D:\\All projects\\UI套件\\04_B04_组件系统与DesignTokens_L4\\ArcheAxis_L4_组件系统_16张+Tokens.zip`
- `D:\\All projects\\UI套件\\05_B05_高保真产品页面_L5\\ArcheAxis_L5_12张高保真产品页面.zip`
- `D:\\All projects\\UI套件\\10_B10_最终版高保真可部署UI\\archeaxis_最终版_高保真可部署UI.zip`

| 检查项 | 验收标准 | 当前结果 |
|---|---|---|
| 背景 | 深空黑蓝 `#061118`，有层次，不是纯黑 | `PARTIAL`，当前 Avalonia 仍有纯黑层 |
| 主交互 | Aurora Teal `#1FC8C5` | `PARTIAL`，当前仍有 Indigo 硬编码 |
| 文字 | Ivory `#F3EFE6`，Muted `#96AAB4` | `PARTIAL`，存在纯白大面积使用 |
| 金色 | 只用于证据/可信/关键节点 | `NOT_ALIGNED`，尚未形成明确语义资源 |
| 面板 | Surface 层次、边框、内高光、可读密度 | `PARTIAL` |
| 页面 IA | Capture/Evidence/Original/Learning/Memory/Review 闭环 | `PARTIAL` |
| 原始证据与机器内容 | 必须有 provenance/derived 区分 | `PARTIAL` |
| 状态 | Loading/Empty/Error/Permission/Version | `PARTIAL` |
| 动效 | 低频、状态清晰、支持 reduced motion | `NOT_VERIFIED` |
| 响应式 | Desktop/Tablet/Mobile 规则 | `NOT_VERIFIED` |
| 可访问性 | 44px hit target、4.5:1、keyboard/focus | `NOT_VERIFIED` |
| GUI 回读 | 原生窗口截图、点击、状态读取 | `NOT_EXECUTED` |

## 2. 当前最明显的视觉问题

当前 Avalonia P3 更像“本地 Core 管理壳”，而不是参考套件中的 AAOS 产品工作台。问题不是缺少更多装饰，而是：

1. Token 没有集中管理，造成黑灰 + Indigo 的视觉漂移。
2. 右侧 Inspector 还不是 Evidence Reference Drawer / Source Chain。
3. 首页内容偏入口卡和状态卡，缺少最近证据、今日关注、待复习、原创进展和 Memory 摘要的产品层次。
4. Evidence、Original、Machine-derived、Learning 的来源关系没有形成统一视觉组件。
5. B09/B10 的 Command Palette、Toast、Modal、Drawer、Focus/Pressed 反馈尚未形成 Avalonia 组件契约。

## 3. 视觉修复验收顺序

1. Token/resource dictionary 对齐。
2. 工作台、资料库、学习三个现有页面先完成视觉层对齐。
3. Capture Inbox、Evidence Library/Detail 形成真实首用主链。
4. 增加 ProvenanceTag、SourceChain、EvidenceBadge、ReviewCard、MachineDerivedTag。
5. 再做 Memory Graph、Original Editor、Command Palette 和统一状态。
6. 使用真实原生窗口执行截图和点击回读；在此之前不得标记视觉 PASS。

## 4. 禁止回归

- 不得重新引入米白/金色三栏合并稿、橙黑 WORK-LAB 或三项目混合主题。
- 不得把星云、行星、金色光效扩大成海报化背景。
- 不得用静态 demo 数字证明真实 Core 状态。
- 不得把 AI 生成、机器推断和原始 Evidence 画成同一种卡片。
