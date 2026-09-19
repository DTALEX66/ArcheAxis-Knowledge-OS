# M0 P3 Assessment 协议冻结（2026-09-20）

## 目标

把“真人学习”从 `item_key + client correct` 的局部 review 提升为 Core 产生、可重启读回的 Assessment 链。该记录只冻结最小协议，不宣称 P3 完成。

## 冻结决定

1. **Assessment 由 Core 产生。** 客户端只能请求当前 item 的 Assessment，不能提交自造 question、content、source anchor 或 knowledge 版本来创建权威 Assessment。
2. **Assessment append-only。** 每份 Assessment 有稳定 `assessment_id`，保存 `item_key`、active `knowledge_id`、question、content snapshot，以及可空 `source_id` / `anchor_id`。历史 Assessment 不原地改写；Knowledge 变更生成新的 Assessment。
3. **Review 必须绑定 Assessment。** review 请求携带 `assessment_id`、answer 和人工 rating；Core 校验 Assessment 与 item、active Knowledge 的绑定。`correct` 只表示学习者的人工结果观察，不代表事实真值或 mastery。
4. **Mastery 是 Core-derived projection。** FSRS 状态继续由 Core 写入；mastery 只能作为事件和调度派生投影，不能写入或冒充 Knowledge truth。
5. **重启验收范围。** 重新打开同一 SQLite 后，Assessment、answer、learning event、FSRS 和 queue 必须读回；不能只证明计数或静态契约。

## 当前证据与缺口

- Accepted / personal Knowledge 创建、审核和 `/v3` 读取已有局部 API。
- Learning queue、FSRS、answer receipt 和局部 restart readback 已有代码/测试证据。
- 当前没有 Core-owned Assessment endpoint，也没有独立持久化 Assessment 或 Mastery projection。
- Avalonia 仍主要显示 item key 和来源版本，review 仍由客户端提交 `correct`。
- Rust / Avalonia 运行测试受当前环境缺少 `cargo` / `dotnet` 限制，相关结果必须标 `NOT_EXECUTED`。

## 下一张写集

- `crates/archeaxis-store-sqlite/src/lib.rs`：增加 Assessment 表或受控 on-demand schema，不改变 workspace identity 决策。
- `crates/archeaxis-domain/src/learning.rs`：Core 生成、验证、读回 Assessment；只接受 active accepted/personal Knowledge。
- `crates/archeaxis-api/src/lib.rs`：Assessment read/create route；review 绑定 `assessment_id`。
- `apps/ArcheAxis.Desktop/MainWindow.axaml(.cs)`：显示 Core Assessment content/question，提交 answer/rating/assessment_id。
- 对应 Rust API、domain、Avalonia source-contract 测试；完整 Rust/runtime 证据需在工具链可用后补跑。

实现回读：提交 `8dfc78b3` 已加入 Core-owned Assessment 表、创建/读取 route、review 绑定校验、重启读回测试和 Avalonia 显示/提交绑定；当前 Rust/Dotnet 运行验证仍为 `NOT_EXECUTED`，Mastery projection 和真实 UI 运行仍未闭合。

状态：`PROTOCOL_FROZEN / IMPLEMENTED_LOCAL / PARTIAL / NOT_READY`。
