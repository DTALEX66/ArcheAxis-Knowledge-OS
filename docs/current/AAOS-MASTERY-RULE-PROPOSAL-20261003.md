# Mastery 规则提案 · 待 Owner 裁决（2026-10-03）

提出方 DSH。**本文只是提案：未改动任何代码、契约或数据。**

## 1. 现状（已核对源码）

`mastery_projection` 由 Core 生成，实现在 `crates/archeaxis-domain/src/learning.rs:147` `mastery_projection_json()`，返回固定形状：

```json
{
  "status": "projection",
  "closed": false,
  "basis": "fsrs_review_state_and_learner_observation",
  "review_state": <FSRS state>,
  "stability": <FSRS stability>,
  "correct_streak": <派生：等于记录中 correct 事件数>
}
```

关键事实：

1. `closed` **恒为 false**，而且是被**契约钉住**的，不是遗漏。`crates/archeaxis-api/tests/contract_constant_fields.rs:178` `the_mastery_projection_is_open_wherever_it_is_reported` 断言 `closed == false`，失败信息写着 `mastery is deliberately an open projection, never a closed claim`。
2. 同一测试还钉住 `machine.status == "not_recorded"`，理由是 `nothing writes the competence ledger` —— **当前不存在能力账本写者**。
3. `correct_streak` 是**派生值**，不是独立权威。
4. 界面：首页 `本月掌握` 目前显示 `Core 未提供`。
5. 该函数的文档注释本身写明：`review observations and FSRS scheduling do not establish Knowledge truth or a closed mastery claim`。

**所以这不是 bug。** 它是刻意的认识论立场：产品拒绝声称「你已掌握」。

## 2. 它留下的产品空缺

- 用户拿不到任何「进展」信号；首页 `本月掌握` 恒空。
- 「掌握」这个词在产品里**没有定义**，却出现在卡片标题上。
- 一旦给它加规则，产品就开始对学习者做**结论性声称**，因此其证据基础必须由 Owner 认可，不能由执行方自行决定。

## 3. 三个方案

### 方案 A —— 永久不闭合，只把界面说清楚

- `closed=false` 保持不变；**把首页 `本月掌握` 改名为非结论指标或直接移除**。
- 优点：认识论风险为零，改动最小。
- 缺点：产品永远不回答「我学得怎么样」。

### 方案 B（推荐）—— 有界、带证据限定的**进展**投影

- **`closed` 仍然恒为 false，契约不动。** 不新增权威、不新增写者。
- 只增加**派生**字段（全部可由已有数据算出，只读）：
  - `attempts`：该学习项的评估次数
  - `distinct_correct_days`：答对发生在多少个不同日期
  - `last_correct_at`：最近一次答对时间
  - `next_review_at`：FSRS 下次复习时间（已有）
- 界面只显示**可复述的事实**，并**始终**附带非结论限定，例如：
  `已连续答对 3 次 · 最近 8-14 · 下次复习 8-17（这表示排程与作答记录，不构成掌握结论）`
- 优点：给出真实进展，同时不声称掌握；只读派生，实现风险低。
- 缺点：需要一次契约补充（新增字段）与一次界面改动。

### 方案 C —— 真正允许闭合掌握

- 需要：新的能力账本写者、真人真值/预测配对。项目规则明确 `Accuracy claims require human truth/prediction pairs; model confidence is not accuracy`。
- 代价大，且与 M0「最短完整闭环」方向冲突。
- **建议：不在 M0 内做。**

## 4. 需要 Owner 回答的问题

| # | 问题 | 我的建议 |
| --- | --- | --- |
| 1 | 选 A / B / C？ | **B** |
| 2 | 若选 B：上述 4 个派生字段是否可接受？ | 可接受；它们都是可复述的计数与时间 |
| 3 | 若选 B：界面是否接受常驻「不构成掌握结论」限定？ | 接受；这正是产品诚实性的体现 |
| 4 | 卡片名 `本月掌握` 是否保留？ | **改名为 `本月进展`** —— 「掌握」若无定义就不该出现在标题上 |
| 5 | FSRS 的 `stability` 是否直接展示？ | 不建议；应翻译为用户语言，避免把模型参数当成绩 |
| 6 | 若选 C：谁提供真人真值配对？能力账本写者落在哪个路由？ | 需你指定；执行方不得自行引入 |

## 5. 边界与实施方式

- **本文不修改任何东西。** 我不会自行把 `closed` 改成 true，也不会新增掌握写者或能力账本。
- 若 Owner 选定方案，实施顺序建议：① Core 新增派生字段 → ② 契约测试钉住 `closed` 仍为 false 且新字段形状稳定 → ③ 界面只读展示并带限定 → ④ 全量门禁 + CI 精确 SHA 验证。
- **无论选哪个方案，`closed=false` 都应作为硬不变量保留**，除非 Owner 明确选择 C 并接受其证据要求。

## 6. 与「真实闭环」的关系

这一项**不在** P0–P5 真实闭环的必经路径上：`closed=false` 不影响 来源→转换→锚点→审核→检索→课件→学习→纠正 任何一步。它是**产品完整度**问题，不是闭环阻塞项。真实库中 19 条知识候选的真人复核仍是闭环的唯一人工闸门。
