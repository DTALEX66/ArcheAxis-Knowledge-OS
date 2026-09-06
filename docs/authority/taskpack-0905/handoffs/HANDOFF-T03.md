# HANDOFF — T03 Rust 存储、原件与可恢复事务（CODEX）

交接人：DeepSeek（集成者）· 日期：2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
在 vNext Rust workspace 实现可恢复的权威存储层，验收：
- 单写者 + 跨进程工作区锁；CAS 原子写入；禁止裸 Connection 外泄；
- 版本迁移与“未来版本拒绝”；统一快照、全表及对象哈希恢复验证；
- 修复“原件丢失、部分写入、恢复不校验”；任务/研究/学习表按契约迁移；
- “移走外部原件并重启后仍逐字节一致”；故障注入回滚；篡改包拒绝；不同版本库保护有效。

## 现状与上下文（已存在，勿重复造）
- 根 Cargo workspace，8 crates：contracts/store-sqlite/domain/application/migration/sidecar-protocol/api/archive。
- crates/archeaxis-store-sqlite 与 domain/src/backup.rs、source.rs、archive 已有骨架与单测（cargo test 全绿于 2bae648/本地 e9a7d2d 时代）。
- 契约：PROJECT_CONTRACT.yaml data_authority（Rust 唯一写者；sha256 内容寻址原件；禁 dual-write、禁 copy-live-wal）。
- 迁移：crates/archeaxis-migration；旧库(legacy v0.6.14)不得由 Rust 写入。
- 相关决策：DECISION_SUPERSESSION_LEDGER.yaml SUP-003/006；T17 输出将作为吸收清单输入。

## 范围与允许路径（任务包 05-TASKS.json T03）
crates/archeaxis-store-sqlite/**、crates/archeaxis-archive/**、
crates/archeaxis-domain/src/backup.rs、crates/archeaxis-domain/src/source.rs。

## 验收（任务包原文）
- 移走外部原件并重启后仍逐字节一致；
- 故障注入回滚；篡改包拒绝；不同版本库保护有效。

## 环境事实
- cargo/rustc 1.97.1；需 vcvars64.bat（见总摘要）后 `cargo test --workspace`；
  RUSTUP_HOME=D:\All projects\OS External Configuration\10-toolchains\rustup；
  CARGO_HOME=D:\All projects\OS External Configuration\10-toolchains\cargo；
- Windows 现场：RTX5060 8G；新测试通过 scripts/runtime/dev.py 分配 .project-local/runs/（0906 覆盖旧 .hermes/task-runtime/ 指令；历史证据不改写）；
- 提交前跑 scripts/check_repository_conventions.py（CRLF/BOM/行尾规则）并保持绿。

## 建议切片
1. 跨进程锁 + CAS 原子写 + 连接封装（禁裸句柄）与失败回归；
2. 版本门（未来库拒绝）+ 迁移序列扩展（任务/研究/学习表）；
3. 快照/全表/对象哈希恢复 + 故障注入（kill/断电模拟=进程中止后回滚）测试；
4. 原件外移/重启逐字节一致旅程测试 + 篡改拒绝。

## 风险与阻塞
- 与 T04（jobs 写入）共享 store；串行合入共享文件，避免与集成者并发改 Cargo.lock。
- 不写旧库；不引入第二个主库写者。

## 输出契约
- 每个切片：变更与原因、实际验证（真实命令输出）、剩余风险、回滚路径、精确 SHA；
- 证据落 docs/authority/taskpack-0905/T03/（收据 JSON + 测试日志路径）；
- 完成后向集成者（本会话）报告：commit SHA、cargo test 结果、验收逐项对照表。
