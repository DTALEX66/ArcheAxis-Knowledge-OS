# AAOS UI 数据溯源审计

日期：2026-09-22
范围：UI 套件示例数据与当前 Avalonia/Core 数据边界。
状态：`TESTED_LOCAL / READ_ONLY_AUDIT`。

## 1. 核心判断

B08、B09、B10 是视觉和交互参考，其中存在静态演示值与浏览器 `localStorage` 持久化。它们不能直接作为 AAOS 真实知识、Evidence、Mastery 或 FSRS 数据源。

当前 AAOS 的正确方向是：

```text
UI reference → layout / token / interaction pattern
Rust Core     → authoritative product state
Python worker → bounded adapter / FSRS schedule authority
UI            → projection only; never a second truth store
```

## 2. 数据类型对照

| UI 内容 | 套件中的表现 | AAOS 正式来源 | 处理规则 |
|---|---|---|---|
| Home KPI | B08/B10 静态数字，如 248/12/5/3 | Core projections | 只能显示真实返回值；没有数据时显示 Empty/Unknown |
| Evidence | B08/B09 示例书名、arXiv 和状态 | Core source/knowledge/evidence projections | 必须保留 source、evidence、引用和验证状态 |
| Original | 示例编辑器和引用按钮 | Core-owned original/version/citation contract | 不得把前端文本当最终 Original truth |
| Human Learning | 示例进度和图表 | Core assessment/review/event + FSRS worker | 使用真实 assessment、answer、review receipt |
| Machine Learning | B08/B10 机器卡片/脑图 | Core machine task receipt + worker contract | 必须标记 machine-derived，不得冒充 Evidence |
| Memory Map | 静态 SVG/演示节点 | 未来 Core-backed projection | 没有真实 graph projection 时明确未接入 |
| Search | 示例过滤和 hash route | Core search/read projection | 不使用 localStorage 作为正式搜索真相 |
| Review/FSRS | B09 的 FSRS-like 示例 | Core + 项目候选 Python FSRS worker | schedule authority 必须回读 `fsrs` 或明确 unavailable |

## 3. 当前已验证的真实边界

- P3 headless learning smoke 已使用项目内 Desktop、当前 Core 候选、项目内候选 Python 和 `.project-local` SQLite。
- 已验证 Knowledge → Assessment → learner answer/review → FSRS projection → Core restart readback。
- `mastery_projection.closed=false`，因此不能把 projection 叫作 authoritative Mastery。
- UI 套件的 localStorage 与静态样例没有被接入正式产品数据层。

## 4. UI 实施时必须保留的标记

建议所有数据表面至少区分：

- `Original / 原始资料`
- `Evidence / 证据`
- `Human observation / 人类学习观察`
- `Machine-derived / 机器生成或推断`
- `Projection / 投影`
- `Authoritative / Core 权威状态`
- `Needs review / 待人工复核`

右侧 Inspector 应逐步演进为 Provenance Drawer，至少能够显示来源 ID、知识版本、证据引用、产生者、时间、状态和关联任务，而不是只显示自由文本摘要。

## 5. 禁止事项

- 不把 B08/B09/B10 的 248、12、72% 等演示值写入 Core 或正式 UI 默认状态。
- 不用浏览器 `localStorage` 替代 SQLite/Core。
- 不让 UI 直接写 Mastery truth。
- 不把机器推断卡片标成已验证 Evidence。
- 不因为页面看起来完整就声称真实资料库、真实模型或 Green 已接入。
