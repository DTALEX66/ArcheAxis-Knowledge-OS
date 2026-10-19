# AXW-1200 — Repository Truth Snapshot & Authority Reset — Snapshot Receipt

> 任务包：`ArcheAxis_Learning_Workspace_System_Blueprint_and_HERMES_Update_TaskPack_v1_2026-08-11.zip`
> 执行时间：2026-08-12
> 状态：PASS（快照已冻结，作为本任务包全部文档的事实基线）

## 1. 快照范围与证据

| 对象 | 快照值 | 证据来源 |
|---|---|---|
| origin/main | `b97035e` (feat(h2): OCR bake-off framework + engine registry (#83)) | `git ls-remote origin main` |
| 最近 merge PR | #83 `b97035e`（2026-08-11T17:28Z） | `gh pr list` |
| 已 merge 任务 PR | #69, #75–#83（11 个） | `gh pr view` |
| 权威分支 | `codex/frozen-roadmap-deepseek-v1` `74c9017`（LOG-004~074） | 本地 worktree |
| 冻结基线 | `FROZEN_EXECUTION_BASELINE_v1_2026-08-09`（H0–H10） | docs/truth |
| 吸收账本 | `SUPPLY_CHAIN_LEDGER.json` v2（46 组件） | docs/truth |
| 吸收执行矩阵 | `ABSORPTION_EXECUTION_MATRIX.md` v2 | docs |
| 外置依赖文档 | `EXTERNAL_DEPENDENCIES.md`（本地 OS config 同步） | docs/environment + D:\All projects\OS configuration |

## 2. 已知能力状态（截至快照）

| 领域 | 状态 | 证据等级 |
|---|---|---|
| H0 真实 PDF 闭环 | 已实现 | installed + 浏览器验证 |
| H1 RawAsset/Evidence/PDF 阅读 | 已实现（#72/#74/#78） | CI + 浏览器 |
| H2 Office/DOCX Adapter | 已实现（#79） | CI |
| H2 质量门/路由/证据连接 | 已实现（#82） | CI |
| H2 bake-off 框架（OCR/ASR/VAD 桩） | 已实现框架（#83），引擎未装 | source |
| 吸收实现（JiWER/RapidFuzz/JSONCanvas/Connectors/FSRS/Magika） | 已实现（#81） | CI |
| 3D/VR/AR / 动画 / 仿真 / 空间记忆 | **未实现（长期蓝图）** | — |
| 通用 Agent / 自治演化 | **未实现（exploration）** | — |

## 3. Supersession 关系

- 本任务包（v1 2026-08-11）**supersedes** 任务包中已过时的阶段/名称声明，但**不删除**：
  - `FROZEN_EXECUTION_BASELINE_v1_2026-08-09`（冻结基线保留，H0–H10 结构有效）
  - 历史 v4 任务包、Future Blueprint、Handoff 文档（保留为历史）
- 本任务包引入 `AXW-1200~1210` 规划治理编号，与既有 `AXW-*` 实现任务并存
- 旧产品名（元枢 / archeaxis-workspace）只保留 Legacy/Migration 语境

## 4. 本轮"系统级"边界声明

本任务包只更新定位、蓝图、命名契约与任务治理文档；**不把未来能力写成当前已实现**。全部 17 个交付文件均区分：`binding_core / binding_long_term / exploration / retired` 与 `critical_now / core_next / formal_later / experimental_later / deferred_retained`。

## 5. 未决项（Owner Action 待办）

1. GitHub 仓库描述（About）按 Owner 最新裁决锁死为产品身份 + 吸收不了的开源项目 + 外置依赖链接（见 README §0）
2. 品牌可用性/商标/域名/PyPI/商店检索：**未核验**，设为 Owner Action gate
3. 远端仓库改名 `DTALEX66/archeaxis-workspace → archeaxis-workspace`：**未执行**（需 Owner 单独授权 + 迁移计划）
