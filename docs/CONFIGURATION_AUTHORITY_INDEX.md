# Configuration Authority Index (AXC-010)

> **2026-10-11 当前路由与状态**：Owner 已明确恢复完整框架、常见常用格式与最短闭环产品实施；状态 RUNNING_BY_OWNER / PARTIAL。当前范围与恢复决定读[活动指针](current/AAOS-ACTIVE-EXECUTION.json)，实际进度仍在该指针指定的 UI 执行记录。2026-10-10 暂停仅为历史时点，旧 COMPLETE、FAIL 和证据保留各自 SHA。六项核心能力对话增量仍 FROZEN_BY_OWNER；V01 暂停、FT01–04 冻结；发布、Green 替换和真实用户数据覆盖未授权。 文件身份与旧路径按[路由登记](current/AAOS-AUTHORITY-ROUTES.json)核对。

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


> 唯一机器可读/人类可读的项目配置权威索引。一条规则只允许一个 canonical
> source；其余引用或标记 SUPERSEDED。新增会话默认权威 = 本表，不取
> Handoff/intake/旧 taskpack。
> 建立：2026-08-13（AXC-010，Project Config CI DeDup TaskPack v1.1）

| Concern | Authority | 说明 |
|---|---|---|
| 项目 agent 边界 | `AGENTS.md` | 使命、目录边界、隐私/数据边界、工作规则 |
| 内容保存、证据用途与 AI 使用原则 | `PROJECT_CONTRACT.yaml` 的 `content_policy`，由 `.project/schemas/project-contract.schema.json` 校验 | canonical 规范：原件识别忠实度与专业事实支持/反证独立，普通保存不以外部来源/证据/云核验/人工复核为前置；权限与结构完整性仍必需。人类可读解释见 `docs/architecture/CURRENT_ARCHITECTURE.md`，实现与验收状态只见现行执行台账，不由规范声明推定。 |
| 当前执行与架构决策 | `docs/current/AAOS-ACTIVE-EXECUTION.json`、`PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml` | 当前活动指针是任务源与进度入口的规范投影；当前任务来源为 UI 优先新包，G01 已由用户选中。SUP-022 的正式 Tauri/React 宿主、Rust Core 唯一正典写者、隔离 Python workers 与1004有效合同继承。R6/M0旧顺序冻结；旧证据与无发布边界不变。 |
| 本机共享库、绿色软件与资料根路径 | [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md) | 用户 2026-09-07 指定的五个资源根；每次定位工具/模型/测试资料先查此表，不猜目录；真实资料库与测试库严格分离，不等于修改产品设置 |
| 开发运行根 | `scripts/runtime/dev.py` | `.project-local` 下 worktree/run 隔离；Bash/PowerShell 共用；不是产品 workspace |
| 正式桌面worker路径载荷 | `scripts/release/stage_backend_runtime.py`、`src-tauri/src/main.rs`、`desktop/src-tauri/src/backend.rs`、`desktop/src-tauri/src/runtime.rs`、`crates/archeaxis-api/src/launch.rs` | 权威暂存器统一生成 runtime/Core/workers、manifest 与 worker-profile；正式 Tauri 沿复用的 backend/runtime 构建 v2 Core 启动文档，Core 校验路径、权限及 text_worker 声明。实际启动解释器须与候选/profile/import 证据一致，text_worker 不添加 schema 字段。Avalonia `apps/ArcheAxis.Desktop/WorkerProfile.cs` 是历史供体，不能覆盖正式 Tauri 契约；保留隔离开发根和旧数据边界。 |
| 桌面启动身份 | `packages/contracts/bootstrap/v2/launch.schema.json`、`docs/current/R5-DESKTOP-IDENTITY-V2.md` | 显式v2 stdin双令牌、单Core写者；Core作跨字段及路径语义校验，不能把Schema验证当作权限验收 |
| Core持久复习状态 | `packages/contracts/learning/v1/review.schema.json`、`docs/current/R5-LEARNING-STATE.md` | `/api/v1/learning/reviews`从Core事件恢复完整FSRS状态，独立于旧/events收据契约；只有human可写，状态由Core与worker产生，正式学习UI接线与验收读当前UI执行记录及分域回执，旧接线状态不代表当前事实 |
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
| historical capability/state model | `docs/truth/CURRENT_STATE_TRUTH.md` | 2026-08-09 historical snapshot; R6/M0 receipts retain their own tested SHAs. Inherited AAOS-01 Q00–Q15 progress is only `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`; new UI progress is resolved through `docs/current/AAOS-ACTIVE-EXECUTION.json`; historical COMPLETE claims do not establish current behavior. |
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


集合／研究合同：正式writer中的 `packages/contracts/v2/collection.schema.json`、`research.schema.json` 为这两个metadata namespace的单源；生成React DTO不建立第二配置库。Rust Core拥有Document保存与引用验证、公式和只读图／视图投影。详细writer及源码SHA读 [CB03/UF08回执](current/receipts/AAOS-RESEARCH-STAGE-20261010.json)；上次源码/合同已合并发布，见仓库同步回执；本轮修复的最新发布状态单独读AAOS-AUTHORITY-REPAIR-20261010.md，不从历史writer路径推定当前文件缺失。
