# Current State Truth — ArcheAxis Knowledge

> 文档 ID：`AXW-CURRENT-STATE-v1-2026-08-09`
>
> 唯一阅读入口：**`docs/PROJECT_STATUS.md`**。本文是执行层导航，不复制易过期的能力明细；它固定“什么是当前事实”与“什么是规划”的边界。

## 1. 实现事实 vs 规划/候选（严格分开）

| 类别 | 判定标准 | 文档位置 |
| --- | --- | --- |
| **实现且已验证** | 有状态日志对应 exact-SHA / LOCAL_RUNTIME / EXACT_SHA_CI / PUBLICATION / LIVE_INSTALLED 证据 | `PROJECT_STATUS.md` 已验证能力段 |
| **实现但未验证** | 源码存在，但无当前 exact-tree 执行证据 | `PROJECT_STATUS.md` 债务段；不得标 PASS |
| **candidate** | 外部来源或未复核内容，需人工复核 | 任何来源，最多为 candidate |
| **规划/蓝图/候选方向** | 冻结基线、增补包、blueprint、intake | `docs/architecture/`、`docs/truth/` 冻结任务 |
| **已废弃/历史** | 旧 handoff、旧 Phase、旧 imported-design | 仅作迁移输入，不覆盖当前指令 |

规则：**没有 exact-SHA 执行证据的“已完成”声明一律不是当前事实**，只能作为候选或历史。candidate 永远不能自动提升为 verified truth。

## 2. 冻结执行状态入口

- 任务定义：`docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`（FROZEN）
- 增补：`docs/taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`
- 增补：`docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`
- 追加式状态：`docs/truth/EXECUTION_STATUS_LOG.md`
- 执行协议：`docs/taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`
- 权威顺序：`docs/truth/AUTHORITY_CONTRACT.md`

## 3. 配置权威与命名冻结（AXC-000/010，2026-08-13）

- 仓库名 `DTALEX66/ArcheAxis-Knowledge-OS` 为正式云端仓库名，**不再改名**（任务包禁止将其中 `OS` 判为漂移）。
- 对外产品名 `ArcheAxis Knowledge｜星环知识平台`；内部工作台 `ArcheAxis Learning Workspace`；Python/技术包 `archeaxis-workspace`。
- 配置权威唯一索引：`docs/CONFIGURATION_AUTHORITY_INDEX.md`（AXC-010）。
- 任务包：`docs/taskpacks/ArcheAxis-Knowledge-OS_Project_Config_CI_DeDup_TaskPack_2026-08-13.md`（AXC-000~150，基线 1d9d875）。

## 3. 基线身份

```text
基线 ID：AXW-FROZEN-v1-2026-08-09
建立基点：origin/main = 492fac5982c693eb668d31cc51a6a59bac83b7a1
冻结哈希：
  baseline ef3066231d8251562c6b9fb361e9a0a0424c100c6c27b6ec4de8ebba7b585155
  web     971e0ee9ba32f6b30c8d8435dbb4d5c46574f0dbba96210ce00076055afedb19
  klc     2bfd1192b3119121fd921c59721890d751adbdcb9383fa4d9b15ce714a4ed288
```

实时分支/SHA/dirty/CI 必须从 Git 与 GitHub 读取，本文件不复制。

## 4. 当前阶段总判定（截至 2026-08-09）

```text
后端最小闭环：PASS（真实批量 + 重启读回）
内部 NSIS 生命周期：PASS
内部安装版已验证格式：PARTIAL（md/canvas/txt/csv/html/png/jpg）
安装版全格式支持：UNVERIFIED / BLOCKED（pdf/docx/pptx/xlsx/media/ASR）
WebView 点击级导入：UNVERIFIED
H0-H5 + Web + KLC 任务：进行中（见状态日志）
公开正式发布：NO-GO
```

## 5. 证据等级

`STRUCTURAL < LOCAL_RUNTIME < EXACT_SHA_CI < PUBLICATION < LIVE_INSTALLED`

低等级证据不得替代高等级证据。任何 PASS 必须声明其证据等级。
