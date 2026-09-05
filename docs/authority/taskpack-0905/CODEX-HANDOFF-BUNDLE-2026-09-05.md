# CODEX 交接合集 — Fast-Full-Loop taskpack 2026-09-05-r2（DeepSeek 线完成后）

本文件是交给用户/CODEX 侧的**唯一完整交接入口**。DeepSeek 侧可执行任务已全部完成并落库
（禁止虚报：全部为实测+收据+精确 SHA，见各任务收据目录）。以下每项任务均附：目标、输入
（DeepSeek 侧已交付物路径）、依赖、验收、阻塞、环境事实。

## 交接清单

| CODEX 任务 | 交接文档 | DeepSeek 侧输入（已就绪） | 依赖/阻塞 |
|---|---|---|---|
| T03 Rust 存储/恢复 | `handoffs/HANDOFF-T03.md` | T02 契约冻结（schemas+正反例）、PROJECT_CONTRACT data_authority | 无 |
| T04 执行器/Supervisor | `handoffs/HANDOFF-T04.md` | worker 矩阵 12 项（README+gate）、worker-protocol schema、T04-FIX1 | T02 评审可选 |
| T08 云端联网核查 | `handoffs/HANDOFF-T08.md` | job-status 词表(PARTIAL/BLOCKED_CREDENTIALS)、coverage-receipt、quality-report | **云端凭据未配置**(T00) |
| T09 知识版本/检索 | `handoffs/HANDOFF-T09.md` | assessment-vocabulary、anchor schema、T17 台账 | 无 |
| T10 人类学习 | `handoffs/HANDOFF-T10.md` | learning-feedback schema、金标样例体系 | 无 |
| T11 机器/MCP | `handoffs/HANDOFF-T11.md` | machine-feedback schema、job-status(machine_competence) | 无 |
| T18 前端设计 | `handoffs/HANDOFF-T18.md` | 12-UI-REDESIGN.md、现有 Avalonia 壳 | 凭据缺→本地 qwen2.5vl 降级 |
| T12 Avalonia 工作台 | `handoffs/HANDOFF-T12.md` | CoreSupervisor、--smoke、desktop-vnext 门禁 | T18 设计 |
| T13 吸收+非空迁移 | `handoffs/HANDOFF-T13.md` | **LEGACY_MANIFEST.yaml**(1246 项)、T17 语义抽样 30 项、legacy-dryrun 基线、migration crate | T17 台账 |
| T15 资格验收 G01-G19 | `handoffs/HANDOFF-T15.md` | 各任务收据目录、worker 矩阵、质量评测链、模型 profile | 前述全部 |
| T02 契约评审 | `handoffs/HANDOFF-T02-REVIEW.md` | T02 slice1+slice2（9b4a4ec/188745d） | 无 |

## DeepSeek 已交付物索引（供 CODEX 引用）

- 决策/契约：`DECISION_SUPERSESSION_LEDGER.yaml`(SUP-001..010)、`PROJECT_CONTRACT.yaml`、`packages/contracts/v1/**`
- 目录与门禁：`DIRECTORY_AUTHORITY.yaml`、`.worklab/project-validation.v1.yaml`（1415 tracked 全分类）、`ci.yml` vNext 门禁
- Worker：`services/python-workers/**`（12 项能力+README 矩阵，workers-vnext gate）
- 评测与模型：`services/python-workers/evaluation`、`docs/authority/taskpack-0905/T07/`、`config/model-profiles/local-2026-09-05.yaml`
- 旧资产：`LEGACY_MANIFEST.yaml`、`docs/authority/legacy/T17-*`
- 收据总目录：`docs/authority/taskpack-0905/T{00,01,02,05,06,07,14,17}/*-RECEIPT-2026-09-05.json`

## 完成基准（SHA 链）

DeepSeek 线提交：2bf4d36→20add00→c19e1ae→9b4a4ec→55021e9→b2a9cfa→891118c→e512a2f→fa5f391→
37447ef→1bd24dc→c1ca1ff→980e981→2b50d28→be6e788→9f74390→6ccfb53→a1c7ccd→312104c→80a48f8→
180f4c7→9820f5b→188745d→1a48084→d38e8c5→4f89094→d44d2f7→9d0e8be→(final)

离线全量自审（DS-OFFLINE-SWEEP-RECEIPT-2026-09-05.json）：
全仓 pytest 2092 passed、knowledge_base 38 passed、cargo test --workspace exit 0、
cargo fmt 修复 20 文件后 --check 干净、dotnet build 0 错、architecture/conventions/ruff 全绿、
1415/1415 tracked 全分类、无 PENDING 收据、manifest 头同步、工作树干净、本地==远端。
clippy 因工具链未安装该组件（需联网安装，超离线范围）如实登记 NOT_RUN。

## 阻塞汇总（用户侧，不属 DeepSeek 可执行范围）

1. 云端模型/搜索凭据未配置 → T08 产品级联网核查、T18 云端模型设计
2. F03 动态页渲染需 playwright+chromium 运行器（runtime 级，非代码缺口）
3. T16 打包需 T15 资格证据（CODEX 侧）
4. 真实用户旧库切换需另行授权（M3）
