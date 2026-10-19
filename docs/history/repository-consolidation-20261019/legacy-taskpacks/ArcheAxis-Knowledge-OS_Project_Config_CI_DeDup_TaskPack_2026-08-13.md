# ArcheAxis-Knowledge-OS 项目级配置、门禁与 CI 去重任务包

> 版本：v1.1（最终独立项目版）
> 日期：2026-08-13
> 目标仓库：`DTALEX66/ArcheAxis-Knowledge-OS`
> 审计基线：`1d9d87564fef066e401321ab450d998f309c7d9a`
> 对外产品名：`ArcheAxis Knowledge｜星环知识平台`
> 内部工作台：`ArcheAxis Learning Workspace`
> Python/技术包：`archeaxis-workspace`
> 仓库名 `ArcheAxis-Knowledge-OS` 是当前已确认云端正式仓库名，本任务包不得将其中的 `OS` 判为命名漂移或安排改名。

---

## 0. 两个独立项目关系铁则（最高优先级）

1. `DTALEX66/ArcheAxis-Knowledge-OS` 与 `DTALEX66/WORK-LAB` 是两个完全独立的 Git 仓库和项目。
2. ArcheAxis 不是 WORK-LAB 的子模块、子目录、monorepo 成员、Git submodule/subtree、Python 包或内部组件；WORK-LAB 也不是 ArcheAxis 的内置模块。
3. 本项目独立拥有源码根、版本、分支、CI、Release、数据库、任务状态、构建产物、运行目录和回滚链；禁止与 WORK-LAB 共享或镜像项目真值。
4. 两项目只能通过版本化外部协议、稳定 CLI/API、仓库地址及只读状态观察协作；本项目 profile、Gate、业务规则和产品配置始终由本仓库拥有。
5. 任何跨仓变更必须拆成两个任务、两个分支、两个 PR、两套测试、两套回滚；一个仓库失败不得污染、阻塞写入或回滚另一个仓库。
6. 本项目必须在未安装、未启动或不可访问 WORK-LAB 时独立完成本地运行、CI、RC 和 Release；WORK-LAB 只能作为可选外部工作流协调工具。
7. 本任务包只授权修改 ArcheAxis-Knowledge-OS；不得写入、提交或发布 WORK-LAB 仓库。

---

## 1. 交给 Hermes 的执行总指令

本仓库只管理 ArcheAxis Knowledge 项目级配置：产品运行时、格式/管线风险、数据库、Evidence/Knowledge/Learning、项目测试与项目 CI。WORK-LAB 是另一个独立仓库，可选地管理全局 Rules/Skills/Agent 编排、TaskPack runner、single-writer/lease/checkpoint、全局配置 desired state、跨项目审计协议和只读 Observer。本项目不得复制这些实现，也不得依赖其存在；只通过本仓库自有的 `.worklab` 声明与版本化外部 CLI/API 协议表达可选协作能力。

本轮清理项目配置中与 WORK-LAB 重复、过重、失效的内容，同时保留本项目业务安全门禁。采用"开发定向验证 + 三个大阶段各一次聚合 CI + RC 安装态 + Release 认证"。不得把所有高风险项都扩大成每次 full qualification。

项目未来蓝图、3D/VR、3D 记忆宫殿、动态课件、动画、系统级能力完整保留为 DEFERRED/PARKED；当前关键路径仍是常规多格式统一全链路闭环。

所有跨仓需求只生成外部协作请求，不直接改 WORK-LAB；必须在 WORK-LAB 另开任务、分支和 PR。本项目的构建、验证与发布不得因 WORK-LAB 缺席而失败。

未经所有者明确授权，不修改 WORK-LAB、用户全局配置、仓库名、branch protection，不合并 PR、不发布 Release。

---

## 2. 本项目必须拥有的配置

### 2.1 项目工作规则

- `AGENTS.md`：项目使命、目录边界、隐私/数据边界、项目工作规则；
- `docs/VERIFICATION_POLICY.md`：本项目风险类型与验证节奏；
- `.worklab/project-validation.v1.yaml`：项目路径到语义 Gate 的映射；
- `.worklab/gate-registry.v1.yaml`：本项目可被调用的稳定 Gate ID；
- `.github/workflows/ci.yml`：项目 CI 实现；
- `.github/workflows/release.yml`：项目 Release 实现。

### 2.2 产品运行时配置

- `config/defaults.yaml` 与 profile：应用、数据库、日志、摄取、搜索、安全；
- `config/models.yaml`：产品内部模型 Adapter 配置，不是 Codex/Hermes provider 路由；
- `config/tools.yaml`：产品内部受控工具风险，不是全局 Agent 工具权限；
- 格式引擎、质量门、Evidence、Learning、AI Asset 规则。

### 2.3 项目不能拥有

- 全局 TaskPack runner；
- Hermes/Codex/CC Switch 的真实配置；
- 全局 Agent registry、用户级 Skills/Plugins；
- WORK-LAB Task/Telemetry Ledger；
- 跨项目 Observer；
- 全局配置 apply/backup/rollback；
- 第二套全局审计协议。

---

## 3. 已发现的重复、冲突和过重项

### P0｜项目运行配置有真实重复

`config/settings.yaml` 与 `config/defaults.yaml` 基本重复整份 app/database/logging/auth/rate_limit/pipeline/search/cors。环境变量优先级、profiles 和 settings/defaults 的职责不够清楚。

**处置**：一个默认真值 + profile patch + local/env override，禁止整份复制。

### P0｜Codex 示例已经失效且重复全局配置

`.codex.example/config.example.toml` 仍含：

- `profile='cognitive-os'`；
- 失效远端 `DTALEX66/Cognitive-OS.git`；
- 旧 served projects；
- sandbox/approval/git/reporting 等已由官方 Codex + WORK-LAB user overlay + AGENTS 管理的内容。

**处置**：优先删除该模板；如确需保留，只写本项目 root/profile 以及"可选外部协调工具"的协议指针，不得依赖 WORK-LAB bootstrap，也不得提交官方配置字段的私有仿制品。

### P1｜AGENTS 混入历史系统描述

当前仍将 Cognitive-OS 描述为本仓库的现役 front operating layer，并保留旧 Knowledge-Base/Inspiration-Research 架构叙述。它们可以作为兼容/历史事实，但不应占据 agent 首屏权威。

**处置**：AGENTS 只保留当前项目目标、业务边界和项目级规则；历史内容链接到迁移文档。

### P1｜Verification Policy 正确，但 high-risk 仍过重

现规则将安全、权限、数据库、迁移、架构、打包/依赖统一要求"完整门禁 + 独立 review + push + exact-SHA CI"。这会把每个依赖或 migration 修复扩大成发布级流程。

**处置**：高风险立即验证对应风险，但 stage 才 full CI、RC/Release 才制品 exact-SHA。

### P1｜未知路径 full qualification 过度保守

当前 classifier 对 unknown path、CI/security/schema 一律 full qualification；一旦新增普通目录就可能触发 11 jobs，包括 Windows/NSIS。

**处置**：unknown 先 static + primary test + BLOCKED classification review；只有不能安全分类且触及发布/数据安全时才 full。

### P1｜CI 文件过大且发布级工作仍在普通 CI

`ci.yml` 约 716 行、11 jobs；desktop-build 内 cargo audit、Tauri/NSIS，installer lifecycle 在一些普通变更路径触发。曾出现 11～36 分钟运行。

**处置**：CI fast、nightly、RC、release 分离；不要再次大规模重写 gate protocol。

### P2｜项目内存在全局 runner 硬编码路径

Verification Policy 写死 `D:/All projects/Workflow-assistance/scripts/workflow/run_taskpack_agent.py`。

**处置**：使用 WORK-LAB 稳定 CLI/registry；项目只声明 profile。

### P2｜文档/TaskPack/Handoff 过多

220 个 Markdown、155 个 docs 文件、19 个 taskpack、多个 truth/handoff。历史证据合理，但活跃权威入口过多。

**处置**：建立 active index，历史文件归档/标 superseded，不删除 Git 历史。

---

## 4. 目标优先级

项目独立执行时：

```text
官方客户端规则
  ↓
本项目 AGENTS + PROJECT PROFILE（项目工作）
  ↓
TaskPack（当前任务）
```

可选外部协调时：

```text
WORK-LAB USER_OVERLAY（仅全局协调，不进入产品运行时）
  ↓ 版本化协议读取
本项目 AGENTS + PROJECT PROFILE（权威仍在本仓库）
```

产品运行时：

```text
defaults.yaml
  ↓
profile/{development,test,desktop,production}.yaml
  ↓
local ignored config
  ↓
ARCHEAXIS_* environment
  ↓
CLI explicit override
```

工作配置与产品运行配置绝对分开。

---

## 5. 任务清单

### AXC-000｜冻结云端命名与基线

- 以 `DTALEX66/ArcheAxis-Knowledge-OS` 为正式仓库；
- 产品名为 ArcheAxis Knowledge｜星环知识平台；
- 不安排仓库改名；
- 记录最新 main、dirty state、现有 workflows；
- 未来蓝图保留为 DEFERRED/PARKED。

### AXC-010｜配置 Authority Index

建立唯一机器可读/人类可读索引：

| Concern | Authority |
|---|---|
| 项目 agent 边界 | AGENTS.md |
| 验证节奏 | VERIFICATION_POLICY |
| path risk | project-validation |
| gate vocabulary | gate-registry |
| CI implementation | ci.yml |
| release implementation | release.yml |
| runtime defaults | defaults.yaml |
| runtime profiles | profiles/*.yaml |
| naming | naming V2 authority |
| current capability | CURRENT_STATE_TRUTH |
| future blueprint | capability atlas/future blueprint |

Handoff、intake、旧 taskpack 不得成为新会话默认权威。

### AXC-020｜运行时配置去重

- `defaults.yaml` 保留完整默认值；
- `profiles/*.yaml` 只保存差异；
- `settings.yaml` 改为兼容入口/迁移 shim，或删除整份重复并保留指针；
- 明确 precedence；
- local override 文件进入 ignore；
- env 统一 `ARCHEAXIS_*`，历史 `COGNITIVE_*` 只做有期限兼容；
- 配置 readback 显示来源层，不泄漏秘密。

**验收**：同一字段只有一个默认定义；profile 不复制整树。

### AXC-030｜Codex/WORK-LAB 边界清理

- 移除失效 `.codex.example` 字段和旧 repo；
- 理想结果：项目不需要 Codex config template，只需本仓库的 AGENTS + 项目自有 profile；外部 WORK-LAB 可按协议发现，但不是运行前提；
- 若必须保留示例，只含 project ID/root/profile pointer，不含 sandbox、approval、provider、reporting、全局 Git 规则；
- Verification Policy 不再写死全局 runner 绝对路径；
- 不提交真实 `.codex/`。

### AXC-040｜AGENTS 精简为项目 Overlay

AGENTS 只保留：

- 当前产品使命和双向学习定位；
- 用户授权目录、原件/证据/隐私规则；
- 项目模块边界；
- 最小实现工作流；
- 项目专属禁止事项；
- WORK-LAB 指针。

移出/链接：

- 旧 OS/IR/KB 长篇历史；
- 全局单 writer/reviewer/TaskPack runner 细节；
- 官方 Codex 通用 Git/沙箱说明；
- 易过期能力状态。

目标：约 4～8KB，不降低安全边界。

### AXC-050｜验证政策改为阶段批量

固定三大阶段：

1. Intake/RawAsset/Conversion 底座；
2. 常规多格式/OCR/ASR/Evidence；
3. Knowledge/Human Learning/AI Asset/重启导出。

节奏：

- 开发：定向测试，30～90 秒；
- checkpoint：本地 commit，不 push；
- 每大阶段：一次 full project CI；
- nightly：兼容矩阵和长期 corpus；
- RC：Windows 安装态全格式；
- Release：exact-SHA、SBOM、checksum、签名、下载回读。

### AXC-060｜风险分类器减负

修改 profile 语义：

- docs → static；
- ordinary Python → lint + affected/primary；
- format adapter → lint + format-targeted + wheel smoke；
- UI → lint + browser targeted；
- migration → migration-targeted + backup/rollback + primary；
- security/path/network → security-targeted + primary；
- dependency → lock/license + wheel；
- desktop Rust → desktop-fast；
- installer config → desktop-build + lifecycle；
- release workflow/tag → release-only。

Unknown path：

1. static/classification check；
2. 标记 `unclassified`；
3. 阻止 merge 直到 profile 补分类；
4. 不默认运行 NSIS/full matrix。

### AXC-070｜Gate Registry 收敛

项目 Gate 建议：

- static
- lint
- py-targeted
- py-primary
- format-targeted
- migration-targeted
- security-targeted
- wheel-smoke
- browser-smoke
- windows-runtime
- desktop-fast
- desktop-build
- installer-lifecycle
- stage-verdict
- release-verify

`full-qualification` 只作为 stage/RC 逻辑 profile，不由普通 unknown 自动触发。

### AXC-080｜CI 分层

#### `ci-fast.yml` 或现有 CI fast path

- PR/push；
- GatePlan；
- static、lint、affected tests；
- 目标 2～4 分钟；
- stable aggregate：`a0-gates` 可暂保兼容名称。

#### `nightly.yml`

- 完整 Python/compat；
- 全格式 corpus；
- browser、Windows runtime；
- 定时或手动。

#### `rc.yml`

- wheel；
- Tauri/NSIS；
- 安装态全格式 E2E；
- upgrade/uninstall/restart；
- 手动/RC tag。

#### `release.yml`

- exact-SHA qualification；
- SBOM/NOTICE；
- checksum/signing；
- publish/download readback；
- owner approval。

避免同一 push 同时跑 PR 与 push 两套等价完整 CI。

### AXC-090｜Hash 与幂等边界

**产品实时**：

- RawAsset SHA-256；
- conversion revision；
- Evidence anchor/source digest；
- dedup identity。

**项目阶段**：

- frozen tree SHA；
- corpus manifest；
- stage qualification。

**Release-only**：

- wheel/installer checksum；
- exact-SHA release attestation；
- SBOM/signature/download readback。

幂等只用于 intake、RawAsset 写入、Job/Outbox、migration、网络核验、批准/撤销、导出写入；纯转换计算、查询、UI 不做重复"认证"。

### AXC-100｜审计与 Reviewer 触发

立即定向 reviewer：

- 权限/安全；
- migration/数据恢复；
- 外部高风险写入；
- release/签名；
- 新的许可证硬风险。

不需要 reviewer：

- 文档；
- 格式化；
- 既有 Adapter 小修；
- 测试补充；
- UI 文案；
- 已有规则覆盖的普通缺陷。

全仓审计只在新 Phase、架构/数据/安全边界改变或新违规类别时运行。

### AXC-110｜项目配置和业务配置边界

- `models.yaml` 明确为产品推理/embedding Adapter，不影响 Hermes/Codex；
- `tools.yaml` 只管理产品内受控执行；若当前通用 Planner 延期，保持最小并标 DEFERRED，不建设 Agent 平台；
- `route_policy.yaml` 评估是否仍属于产品知识路由；其中 TASK/agent/code_exec 等历史 OS 路由若不是当前闭环入口，应标兼容/deferred，不作为全局 Agent 权限；
- CORS/auth/rate limit/profile 属于产品；
- WORK-LAB 不读取或覆盖以上业务值。

### AXC-120｜文档与 TaskPack 压缩

- 保留一个 CURRENT_STATE_TRUTH；
- 保留一个 Authority Index；
- 保留一个当前 MCL 执行 TaskPack；
- 历史 taskpack/handoff/intake 标 archive/superseded；
- SHA sidecar 只保留真正需要不可变分发的规范，不给普通 Markdown 都生成 hash；
- Git/CI 作为执行证据，不抄测试数量到多份文档。

### AXC-130｜与外部 WORK-LAB 的可选协作契约

项目 profile 对外声明：

- repo ID 和 workflow；
- stable aggregate；
- gate vocabulary；
- verification tier；
- privacy/approved roots；
- evidence locations。

WORK-LAB 可以：

- 读取；
- 验证 schema；
- 观察 CI；
- 绑定 Task Ledger。

WORK-LAB 不可以：

- 修改业务 profile；
- 执行任意 shell；
- 写项目 DB；
- 将 Observer 状态当项目能力真值。

独立性验收：

- WORK-LAB 不存在、未安装、离线或协议不匹配时，本项目 standalone local/CI/RC/Release 仍能运行；
- 本项目不会读取 WORK-LAB 数据库、任务状态或构建产物作为产品真值；
- 契约升级分别在两个仓库建任务、分支、PR、测试和回滚，不允许单 PR 跨仓修改。

### AXC-140｜回归测试

必须验证：

1. 普通 Python 改动不构建 NSIS；
2. 文档提交约 30～60 秒；
3. Adapter 改动只跑目标格式+wheel；
4. migration 运行 rollback/restore，但不做下载回读；
5. 三个大阶段各一次 full CI；
6. RC 才安装态；
7. Release 才 exact-SHA 制品验证；
8. WORK-LAB runner 能解析 profile；
9. 无 WORK-LAB 时项目 standalone CI 仍可运行；
10. 配置优先级和 readback 正确；
11. 两仓无共享源码目录、数据库、任务状态、CI/Release 制品或本地运行目录；
12. 外部协议故障只降低可选协调能力，不阻断产品管线。

### AXC-150｜最终裁决

输出：

- 配置 authority matrix；
- 删除/收缩/兼容/保留清单；
- CI 各 tier 实测耗时；
- 三阶段验证计划；
- WORK-LAB 互操作结果；
- 命名确认：仓库 `ArcheAxis-Knowledge-OS` 不改；
- 当前多格式闭环任务未被配置重构阻塞；
- GO/NO-GO。

---

## 6. 与多格式闭环的关系

配置整改不得先进行数周。优先顺序：

1. AXC-000～070：用一个短 PR 完成权威、配置去重和 Gate 分类；
2. 立即继续多格式闭环 PR-A/PR-B；
3. AXC-080 的 nightly/RC 拆分与闭环测试一起落地；
4. AXC-120 文档归档可在功能空档执行，不阻塞产品；
5. AXC-150 与 MCL-EXIT 一起裁决。

---

## 7. 推荐实施批次

1. **AX-PR-A：配置权威和重复清理**：AXC-000～040。
2. **AX-PR-B：验证/CI 减负**：AXC-050～100、140。
3. **AX-PR-C：业务边界、文档和外部协作契约**：AXC-110～150。

---

## 8. 禁止事项

- 禁止将仓库名 `ArcheAxis-Knowledge-OS` 判为错误；
- 禁止修改已确认命名体系；
- 禁止复制 WORK-LAB runner/ledger/observer；
- 禁止删除项目业务 Hash、Evidence 或数据恢复门禁；
- 禁止每个小任务做 full CI/安装器/release verify；
- 禁止配置重构取代常规多格式闭环；
- 禁止删除未来蓝图；
- 禁止把本项目表述或实现为 WORK-LAB 子模块、monorepo 成员、submodule/subtree、包或内部组件；
- 禁止共享源码目录、数据库、任务状态、CI 制品、Release 制品或本地运行目录；
- 禁止一个 PR 同时修改两个仓库；
- 禁止未经授权改 WORK-LAB、全局用户配置、push/merge/release。

完成标准：项目拥有足够但不重复的项目级配置，WORK-LAB 能统一协调而不越权，日常验证降到分钟级，大阶段和发布仍保留可信证据。
