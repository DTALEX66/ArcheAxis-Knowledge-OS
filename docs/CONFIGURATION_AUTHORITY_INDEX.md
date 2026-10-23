# Configuration Authority Index (AXC-010)

本页按 concern 指向唯一配置源，不维护第二份执行状态。当前范围与双侧闭环先读[唯一闭环定义](truth/CLOSED_LOOP_DEFINITION.md)、[活动指针](current/AAOS-ACTIVE-EXECUTION.json)的 `owner_scope_current`、`execution_control` 和 `continuation_context`；实施证据只读指针的 `active_progress`。任务包是不可变规划来源，旧状态、分支、暂停、权限和主题观察不能覆盖现行选择。

提交、推送、合并、CI、监控、冻结项与数据边界分别沿活动指针及当前 Owner 决定解析；Green 的精确路径、操作范围、候选资格、备份和数据保全条件只读 `green_update_authorization`，索引不另授予覆盖权限。路径身份按[路由登记](current/AAOS-AUTHORITY-ROUTES.json)核对；共享资源登记不是跨项目访问或修改全局配置授权。旧仓库身份与分支观察保留于[历史接续记录](history/repository-consolidation-20261019/current/AAOS-REPOSITORY-CONTINUITY-20261012.md)，不得当作当前远端事实。

> 唯一机器可读/人类可读的项目配置权威索引。一条规则只允许一个 canonical
> source；其余引用或标记 SUPERSEDED。新增会话默认权威 = 本表，不取
> Handoff/intake/旧 taskpack。
> 建立：2026-08-13（AXC-010，Project Config CI DeDup TaskPack v1.1）

| Concern | Authority | 说明 |
|---|---|---|
| 项目 agent 边界 | `AGENTS.md` | 使命、目录边界、隐私/数据边界、工作规则 |
| 内容保存、证据用途与 AI 使用原则 | `PROJECT_CONTRACT.yaml` 的 `content_policy`，由 `.project/schemas/project-contract.schema.json` 校验 | canonical 规范：原件识别忠实度与专业事实支持/反证独立，普通保存不以外部来源/证据/云核验/人工复核为前置；权限与结构完整性仍必需。人类可读解释见 `docs/architecture/CURRENT_ARCHITECTURE.md`，实现与验收状态只见现行执行台账，不由规范声明推定。 |
| 当前执行与架构决策 | `docs/current/AAOS-ACTIVE-EXECUTION.json`、`PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml` | 指针选择现行任务、范围及唯一进度；SUP-022 正式 Tauri/React、Rust Core 唯一正典写者与隔离 Python workers 沿现行合同继承。旧整包顺序及其状态不作为新队列。 |
| 人类与AI双侧闭环、原始上下文边界 | [唯一闭环定义](truth/CLOSED_LOOP_DEFINITION.md)、[当前决定](current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[AI上下文边界](current/AAOS-AI-CONTEXT-BOUNDARY-20261023.md) | 双侧知识及授权连接按现行范围验收；原始跨软件会话外置，合同不等于真实外部连接；AI专项原人类不改边界不冻结后续人类开发。 |
| 本机共享库、绿色软件与资料根路径 | [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md) | 用户 2026-09-07 指定的五个资源根；每次定位工具/模型/测试资料先查此表，不猜目录；真实资料库与测试库严格分离，不等于修改产品设置 |
| 开发运行根 | `scripts/runtime/dev.py` | `.project-local` 下 worktree/run 隔离；Bash/PowerShell 共用；不是产品 workspace |
| 正式桌面worker路径载荷 | `scripts/release/stage_backend_runtime.py`、`src-tauri/src/main.rs`、`desktop/src-tauri/src/backend.rs`、`desktop/src-tauri/src/runtime.rs`、`crates/archeaxis-api/src/launch.rs` | 权威暂存器统一生成 runtime/Core/workers、manifest 与 worker-profile；正式 Tauri 沿复用的 backend/runtime 构建 v2 Core 启动文档，Core 校验路径、权限及 text_worker 声明。实际启动解释器须与候选/profile/import 证据一致，text_worker 不添加 schema 字段。Avalonia `apps/ArcheAxis.Desktop/WorkerProfile.cs` 是历史供体，不能覆盖正式 Tauri 契约；保留隔离开发根和旧数据边界。 |
| 桌面启动身份 | `packages/contracts/bootstrap/v2/launch.schema.json`、`docs/history/repository-consolidation-20261019/current/R5-DESKTOP-IDENTITY-V2.md` | 显式v2 stdin双令牌、单Core写者；Core作跨字段及路径语义校验，不能把Schema验证当作权限验收 |
| Core持久复习状态 | `packages/contracts/learning/v1/review.schema.json`、`docs/history/repository-consolidation-20261019/current/R5-LEARNING-STATE.md` | `/api/v1/learning/reviews`从Core事件恢复完整FSRS状态，独立于旧/events收据契约；只有human可写，状态由Core与worker产生，正式学习UI接线与验收读当前UI执行记录及分域回执，旧接线状态不代表当前事实 |
| 跨语言词汇与损失回执 | `packages/contracts/v1/`、`scripts/contracts/generate_vocabulary.py` | Schema 为单源；Rust/C#/Python 词汇生成后须 `--check`；loss receipt 另有跨字段运行时校验，完整 DTO/权限协议仍在推进 |
| 验证节奏 | `docs/VERIFICATION_POLICY.md` | 风险类型与验证节奏、审计/审查触发 |
| path risk | `.worklab/project-validation.v1.yaml` | 变更路径 → 风险类 → Gate 映射 |
| gate vocabulary | `.worklab/gate-registry.v1.yaml` | 本项目可被调用的稳定 Gate ID |
| fast CI implementation | `.github/workflows/ci.yml` | push/PR 的路径风险选择与快速门禁；不是全量资格证据 |
| full qualification implementation | `.github/workflows/ci.yml` 的 `workflow_dispatch(force_full)`；`.github/workflows/nightly.yml` 的兼容矩阵 | AAOS-01 完整门禁绑定 full SHA + workflow + run ID + attempt，要求目标断言实际执行成功；cancelled/skipped 不算通过。nightly 保留 schedule/manual 的兼容矩阵，不替代指定提交的安装态/产品断言。 |
| release implementation | `.github/workflows/release.yml` | 精确 SHA 候选产物的发布流程；发布不替代资格门禁 |
| runtime defaults | `config/defaults.yaml` | 产品运行时默认真值（唯一） |
| runtime profiles | `config/profiles/*.yaml` | 按环境差异（不复制整树） |
| runtime legacy shim | `config/settings.yaml` | 兼容入口（保持空映射） |
| naming | `docs/truth/NAMING_CONTRACT_V2.md` | 命名体系 V2（binding） |
| historical capability/state model | `docs/history/repository-consolidation-20261019/truth-snapshots/CURRENT_STATE_TRUTH.md` | 2026-08-09 historical snapshot; R6/M0 receipts retain their own tested SHAs. Inherited AAOS-01 Q00–Q15 progress is only `docs/history/repository-consolidation-20261019/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`; new UI progress is resolved through `docs/current/AAOS-ACTIVE-EXECUTION.json`; historical COMPLETE claims do not establish current behavior. |
| future blueprint | `docs/truth/CAPABILITY_ATLAS_V2.yaml` | 未来蓝图（DEFERRED/PARKED 保留） |
| language ownership and migration | `docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` | 语言边界、兼容命名与迁移门禁 |
| directory topology and cleanup | `docs/DIRECTORY_AUTHORITY_INDEX.md` | 路径分类、归档/移动/删除前置条件 |

## 优先级（项目独立执行时）

```text
官方客户端规则
  ↓
本项目 AGENTS + 项目 profile（项目工作）
  ↓
TaskPack（当前任务）
```

## 优先级（可选外部协调时）

```text
WORK-LAB USER_OVERLAY（仅全局协调，不进入产品运行时）
  ↓ 版本化协议读取
本项目 AGENTS + 项目 profile（权威仍在本仓库）
```

## 产品运行时配置优先级

```text
defaults.yaml
  ↓
profile/{development,test,desktop,production}.yaml
  ↓
local ignored config（不提交）
  ↓
ARCHEAXIS_* environment（COGNITIVE_* 仅限期兼容）
  ↓
CLI explicit override
```

工作配置与产品运行配置绝对分开。

| 能力吸收登记 | docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml + config/schemas/capability-absorption-registry.schema.json | R6 A03 唯一能力吸收登记；状态、许可、来源、边界和回退必须逐项记录；不得把候选或供体写成已集成 |


集合／研究合同：正式writer中的 `packages/contracts/v2/collection.schema.json`、`research.schema.json` 为这两个metadata namespace的单源；生成React DTO不建立第二配置库。Rust Core拥有Document保存与引用验证、公式和只读图／视图投影。详细writer及源码SHA读 [CB03/UF08回执](history/repository-consolidation-20261019/current/receipts/AAOS-RESEARCH-STAGE-20261010.json)；上次源码/合同已合并发布，见仓库同步回执；该修复时点的发布观察见[历史修复记录](history/repository-consolidation-20261019/current/AAOS-AUTHORITY-REPAIR-20261010.md)；当前交付状态只沿活动指针核实，不从历史writer路径推定当前文件缺失。
