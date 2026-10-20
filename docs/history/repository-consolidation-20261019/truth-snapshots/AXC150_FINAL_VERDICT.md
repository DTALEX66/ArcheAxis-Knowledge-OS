# AXC-150 Final Verdict — Project Config CI DeDup TaskPack v1.1

> 日期：2026-08-13
> 仓库：DTALEX66/ArcheAxis-Knowledge-OS
> 批次：AX-PR-A（AXC-000~040）、AX-PR-B（AXC-050~100,140）、AX-PR-C（AXC-110~150）

## 1. 配置 Authority Matrix（AXC-010）

| Concern | Authority | 状态 |
|---|---|---|
| 项目 agent 边界 | `AGENTS.md`（6.1KB，精简后） | ✅ 已精简 |
| 验证节奏 | `docs/VERIFICATION_POLICY.md`（三阶段批量） | ✅ 已改写 |
| path risk | `.worklab/project-validation.v1.yaml`（schema v2.0） | ✅ 已减负 |
| gate vocabulary | `.worklab/gate-registry.v1.yaml`（schema v2.0，18 gates） | ✅ 已收敛 |
| CI implementation | `.github/workflows/ci.yml`（fast）+ `nightly.yml` | ✅ 已分层 |
| release implementation | `.github/workflows/release.yml` | ✅ 保留 |
| runtime defaults | `config/defaults.yaml`（唯一真值） | ✅ 已去重 |
| runtime profiles | `config/profiles/*.yaml`（差异 only） | ✅ 已确认 |
| runtime legacy shim | `config/settings.yaml`（空映射 shim） | ✅ 已降级 |
| naming | `docs/truth/NAMING_CONTRACT_V2.md` | ✅ 已引用 |
| current capability | `docs/truth/CURRENT_STATE_TRUTH.md` | ✅ 已冻结 |
| future blueprint | `docs/truth/CAPABILITY_ATLAS_V2.yaml`（DEFERRED/PARKED） | ✅ 保留 |

## 2. 删除/收缩/兼容/保留清单

### 删除
- `config/settings.yaml` 整份重复树（8 键 × 值）→ 空映射 shim（保留文件因 config.py 加载，向后兼容）

### 收缩
- `AGENTS.md` 7.2KB → 6.1KB（历史系统表压缩、V1→V2 命名、HTTPS 远程）
- `.codex.example/config.example.toml` → 最小项目指针（删 Cognitive-OS 远端/served projects/sandbox/approval 字段）
- `docs/VERIFICATION_POLICY.md` 高风险规则 → 阶段批量（不再每小任务 full）
- 分类器 unknown 路径 → static+lint+py-primary + unclassified-block（不再 full-qualification）

### 兼容
- `config/settings.yaml` 保留为 shim（加载顺序不变）
- `COGNITIVE_*` env 限期兼容（config.py 已有）
- `a0-gates` 聚合名暂保（任务包允许）
- 旧 taskpacks 标 `[ARCHIVED/SUPERSEDED]` 横幅（不删历史）

### 保留（业务安全门禁不可动）
- RawAsset SHA-256、conversion revision、Evidence digest、dedup identity
- migration backup/rollback、E盘禁令、guard 脚本
- gate-registry 的 ci-verdict 聚合器、release-verify

## 3. CI 各 tier 实测/规划耗时

| Tier | 内容 | 耗时（实测/设计） |
|---|---|---|
| ci-fast（ci.yml） | gateplan + static + lint + affected | 普通变更 **2-4 分钟**（设计目标）|
| nightly（nightly.yml） | py 3.11/3.13 compat + full suite + browser + windows | 每日 03:17 UTC |
| RC | wheel + Tauri/NSIS + 安装态 E2E | 手动/RC tag（desktop-build 历史 ~17-19min）|
| release（release.yml） | exact-SHA + SBOM + checksum + 回读 | 手动/owner approval |

本地基线：1461 passed / 5 skipped / 门禁绿 / 48.7s。

## 4. 三阶段验证计划（AXC-050）

1. Intake/RawAsset/Conversion 底座 — 阶段末一次 full CI
2. 常规多格式/OCR/ASR/Evidence — 阶段末一次 full CI（当前闭环所在阶段）
3. Knowledge/Human Learning/AI Asset/重启导出 — 阶段末一次 full CI

## 5. WORK-LAB 互操作（AXC-130）

- 契约已声明在 `.worklab/project-validation.v1.yaml#external_contract`：repo_id、workflow、stable_aggregate、gate_vocabulary、verification_tier、privacy_approved_roots、evidence_locations
- WORK-LAB 只读：读取/验证 schema/观察 CI/绑定 Task Ledger
- WORK-LAB 禁止：修改业务 profile/任意 shell/写项目 DB/Observer 状态当真值
- 本项目 standalone：无 WORK-LAB 时本地运行、CI、RC、Release 全部独立（classify.py 零外部依赖）

## 6. 命名确认

- 仓库 `DTALEX66/ArcheAxis-Knowledge-OS` **不改名**
- 对外产品名 `ArcheAxis Knowledge｜星环知识平台`；内部工作台 `ArcheAxis Learning Workspace`；包 `archeaxis-workspace`

## 7. 多格式闭环未被阻塞

- 配置重构 3 个批次均为独立短 PR，无依赖关系阻塞
- 当前多格式闭环（PR-A/PR-B）可随时继续

## 8. 最终裁决

# ✅ GO

- 项目拥有足够但不重复的项目级配置 ✅
- WORK-LAB 能统一协调而不越权（契约声明 + 只读边界）✅
- 日常验证降到分钟级（fast path 2-4 分钟设计）✅
- 大阶段和发布仍保留可信证据（stage full CI + RC + Release exact-SHA）✅
- 命名冻结、两仓独立铁则、禁止事项全部落实 ✅
