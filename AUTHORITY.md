# AUTHORITY.md — 根入口

本文件是仓库的**导航入口**，不是新的真值来源。它只回答"该读哪个文件"，每一项都指向本仓已存在的规范文件。
此前两处记录写"根目录 `AUTHORITY.md` 缺失（`AUTHORITY_REFERENCE_MISSING`）"（`docs/current/AAOS-UI-COVERAGE-MATRIX-20261001.md`、
`docs/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md`）；这两处是当时的实测，保留不改写；本文件使该引用可解析。

## 1. 母定义（沿用输入文档原文，不转述）

> AAOS 是一个本地优先的个人知识与 Human–AI 双向学习系统。它统一承载多格式资料、个人知识、研究、人的学习过程和 AI 学习资产；
> 内容可以先保存、阅读、编辑和使用，再按内容类型、使用场景及用户选择进行识别核验、专业依据分析、修订与治理。
>
> 历史中的 Universal Knowledge Foundation 与 Human–AI Co-Learning 两个永久核心继续保留。……它们不是"所有世界知识已经掌握"
> 或"已经训练出自己的基础模型"的声明。

来源：输入蓝图《AAOS 完整项目描述与未来蓝图》2026-10-06，§2。<br>
输入字节 SHA-256 `2c99e7ae7dd52298ee425c8360c90b63a40d02f41af4c1b151cad6efd55d1ed9`（已核，与提示词要求一致）。<br>
名称：内部代号 AAOS；对外"星环知识平台 ArcheAxis Knowledge"；仓库身份 `DTALEX66/ArcheAxis-Knowledge-OS`；展示状态保留 Ongoing。

## 2. 本仓库拥有 / 不拥有

**拥有**：本仓的代码、文档、决策记录与证据；根 `AGENTS.md` 定义的执行边界内的写入。
**不拥有**：WORK-LAB 与 DESIGN-LAB 两仓（同合仓、不共享业务 DB）；共享工具链与 Model library（仅获准引用）；其他项目的运行状态；
以及 Hermes / Codex / CC Switch / workflow-assistance / session / cron / Kanban 等工作流基础设施——名字提到本项目不构成归属。

## 3. 当前能力的证据范围（状态分级，不混写）

区分：仅目标 / 候选 / 结构实现 / 受控测试 / 真实运行 / 独立验收 / 发布。**测试数量、页面数量、单条纵向切片都不能定义项目本体。**
当前实现声明受 2026-10-05 审计更正约束，至少包括：Q04"完成"声明已撤销；音视频已实测仅媒体头信息探测，未证明解码/转写/时间段内容闭环；
引擎断言无有效结论（存在 cancelled/skipped 与桌面 failure）；更正记录中 Q14 为 NOT_RUN，且未做人工视觉确认。
逐条原文与来源：[`docs/current/AAOS01-AUDIT-CORRECTIONS-20261005.md`](docs/current/AAOS01-AUDIT-CORRECTIONS-20261005.md)
（字节 SHA-256 `da9998ee673086ed12dab824d951e76c2611efb92e72edccf276b91ed8d92d4d`，已核）。

## 4. 未来能力入口

长期能力编号 CAP-0010—CAP-0160（16 项）、第一包 Q00—Q15、未来扩展 F00—F14 与互通平台 I1—I6 的逐项落点与证据见本轮覆盖矩阵
（`docs/current/AAOS-COVERAGE-MATRIX-20261006.md`）。未来能力不得写成已支持；平台名单不整体进 README 的"已支持"列表。

## 5. 规范 Authority 顺序

系统与开发者规则 ＞ 根 [`AGENTS.md`](AGENTS.md) ＞ 用户当前明确指令 ＞ [`docs/truth/`](docs/truth/README.md) 已批准稳定真相 ＞ 冻结任务基线 ＞
历史 TaskPack / 蓝图 / handoff / 导入设计资料。实现证据说明"做到哪里"，不能反过来取消用户已明确的未来目标。
机器可读索引：[`docs/DOCUMENTATION_AUTHORITY_INDEX.md`](docs/DOCUMENTATION_AUTHORITY_INDEX.md)、[`docs/CONFIGURATION_AUTHORITY_INDEX.md`](docs/CONFIGURATION_AUTHORITY_INDEX.md)、
[`PROJECT_CONTRACT.yaml`](PROJECT_CONTRACT.yaml)。

## 6. 唯一 current（一个仓库不能有两个都自称 current 的源）

- **活动任务包**：`docs/authority/taskpack-1004-aaos01/`（`01_完整执行任务书.md`）——以根 `AGENTS.md` §6 为准。
- **前一个任务包（保留继承约束与回执，不再作为当前）**：R6 absorb-first（`docs/authority/taskpack-0919-r6/`），其优先级覆盖 [`M0`](docs/current/M0-DIRECTION-OVERRIDE-20260920.md) 仍作为继承约束保留。
- **AAOS-01（Q00—Q15）唯一实时进度记录**：[`docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`](docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)。
- **正式宿主**：Tauri 2 + React/TypeScript/Vite + Rust Core 单写者（[`DECISION_SUPERSESSION_LEDGER.yaml`](DECISION_SUPERSESSION_LEDGER.yaml) SUP-021 → SUP-022）；Avalonia 为供体并冻结。
- `docs/taskpacks/README.md` 曾自称"唯一当前任务包"，已作废该表述并指向上述入口。

> 记录本文件的一次自身纠错：初稿曾把 R6 写成当前任务包。`scripts/ci/check_document_authority.py` 比对现行 `AGENTS.md` 后指出该读法已过期——
> AGENTS.md §6 明写当前任务包是 `taskpack-1004-aaos01`、R6 是"preceding pack"。以 AGENTS.md 为准已改。

## 7. 审计索引（可导航链：根入口 → 有效规则 → 来源 → 能力/任务 → 代码或证据 → 两端读回）

| 角色 | 规范位置 |
| --- | --- |
| 文件职责与唯一规范源 | [`docs/DOCUMENTATION_AUTHORITY_INDEX.md`](docs/DOCUMENTATION_AUTHORITY_INDEX.md) |
| 冲突 / 更正 / 替代 crosswalk | [`DECISION_SUPERSESSION_LEDGER.yaml`](DECISION_SUPERSESSION_LEDGER.yaml) |
| 覆盖矩阵（CAP / Q / F / I） | `docs/current/AAOS-COVERAGE-MATRIX-20261006.md` |
| 输入来源与哈希（含 SOURCE_MISSING） | `docs/current/AAOS-INPUT-SOURCES-20261006.json` |
| 本轮审计快照（observed_at / SHA / 命令 / 退出码） | `docs/current/AAOS-AUDIT-SNAPSHOT-20261006.json` |
| 供应链吸收决策账本 | [`docs/truth/SUPPLY_CHAIN_LEDGER.json`](docs/truth/SUPPLY_CHAIN_LEDGER.json) |
| 文档/治理自动核验 | `scripts/ci/check_document_authority.py`（接入 CI） |

## 8. 本文件的边界

本文件不含自引用哈希，不复制上游真值，也不改变任何既有决定。发现本文件与上表规范文件冲突时，以上表规范文件为准并修正本文件。
