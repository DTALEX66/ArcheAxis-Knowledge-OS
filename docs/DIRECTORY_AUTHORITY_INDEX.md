# Directory Authority Index

> **2026-10-12 当前路由与状态**：产品实施 RUNNING_BY_OWNER / PARTIAL；源码已通过 PR #184 并入 main。当前任务与授权读[活动指针](current/AAOS-ACTIVE-EXECUTION.json)，实际进度读其指定的执行记录；仓库收敛与接续读[接续记录](history/repository-consolidation-20261019/current/AAOS-REPOSITORY-CONTINUITY-20261012.md)。2026-10-10 暂停仅为历史快照；六项核心能力增量仍 FROZEN_BY_OWNER，V01 暂停、FT01–04 冻结。公开发布和真实用户数据覆盖未授权；指定Green程序更新已授权，须先满足活动指针`green_update_authorization`的候选资格、备份及精确成员核验。 文件身份及旧路径按[路径身份路由](current/AAOS-AUTHORITY-ROUTES.json)分类。

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；新建或无效偏好默认 `cosmic`，保留有效已存偏好；`blueprint`、`blueprint-light`、`black`、`white` 均可切换。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


> Canonical directory classification for maintenance and future normalization.
> It names what a path is; it does not authorize a move, cleanup or deletion.

本机具体资源根以 [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md) 为准：共用模型、外置工具、绿色软件、绿色版真实资料库、项目测试资料库分属不同职责。不得把真实资料库当测试目录或把共享库当本项目清理对象。

## Authoritative topology

Current task selection is resolved by the active-execution pointer; ownership reconciliation retains the R6/M0 preservation constraints, SUP-022 and this index;
[R5-PATH-DISPOSITION.json](../config/governance/path-disposition.json) is historical evidence.
The 0910 measurement keeps its original SHA and 69 historical gaps. R5 assigned
metadata owners and maintenance-only legacy lanes; that historical assignment is
not semantic absorption or a deletion grant. `.zcode/**` is private state and
denied for commit.

| Path / surface | Class | Canonical role | Normalization rule |
| --- | --- | --- | --- |
| `app/`, `shared/`, `knowledge_base/`, `inspiration_research/` | `LEGACY_SOURCE` / `MIGRATION_DONOR` | Preserved Python-era product/domain implementation for Green compatibility, recovery and migration. It is not the formal vNext desktop/Core or isolated Python-worker boundary. Existing legacy aggregates keep their current single writer until a validated, aggregate-specific migration. | Inventory consumers and writer ownership before changing a module boundary. |
| `apps/ArcheAxis.Desktop/` | `MIGRATION_DONOR` | Preserved Avalonia behavior and recovery reference under SUP-022 | Absorb qualified behavior into the formal host; retain old assets and do not claim installed takeover or Owner acceptance from this classification. |
| `crates/`, `services/python-workers/`, `packages/contracts/` | `SOURCE` | Rust Core, isolated capabilities, shared contracts | One vNext writer; actual protocol output must be validated. |
| `frontend/` | `SOURCE` | Formal React/TypeScript/Vite product UI under SUP-022 | Finite HostAdapter commands and generated contracts; no direct database, arbitrary file or Shell access. |
| `src-tauri/` | `SOURCE` | Formal Tauri 2 host under SUP-022 | Own Core lifecycle and finite authenticated business bridge; Rust Core remains the sole canonical writer. |
| `desktop/`, `desktop/bootstrap/` | `COMPATIBILITY_SHIM` | Separate recovery shell/fallback | Preserve until its production-use matrix and G1 gate close. |
| `docs/current/`, `docs/truth/`, `docs/taskpacks/`, `docs/history/` | `CURRENT_RECORD`, `TRUTH_RECORD`, `PLAN`, `HISTORY` | Evidence, current records, plans and historical snapshots | Classify and link before archival; history is not deletion evidence. |
| `.hermes/` | `LEGACY_MIXED_PRESERVE` | Historical mixed assets; regenerability unverified | No new development writes; no blanket deletion. |
| `.project-local/` | `IGNORED_DEVELOPMENT` | Per-worktree/run state, caches and builds | Use `scripts/runtime/dev.py`; retained evidence is not disposable cache. |
| `.playwright-cli/` | `TRANSIENT_AUTOMATION` | Ignored browser-session residue | Remove only after exact content/path verification; it must never be staged. |
| Green `data/` | `PRESERVE_USER_DATA` | Out-of-repository runtime data | Never inspect, copy, clear, rename or delete for a repository repair. |
| Shared tool/model libraries | `EXTERNAL_BOUNDARY` | Reusable machine-local dependencies | May be consumed by declared path; never absorbed or reorganized by this repository. |

## Required records before a move

Every proposed relocation or archival action must first have one row compliant
with the [AX-DIR-010 inventory schema](history/repository-consolidation-20261019/current/AX_DIR_010_INVENTORY_SCHEMA.md):
source and target path, owner, data class, hashes, consumer scan, rollback,
verification and an exact deletion-authorization state.

The [directory-migration adoption map](history/repository-consolidation-20261019/current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md)
is a historical proposal, partially superseded by R6/M0 and its dated freeze
banner. Use this index and the current project authority for present path roles.
A dirty tree, unresolved consumer, missing rollback receipt or `NOT_REQUESTED`
deletion state still stops any exact-path move or deletion.

## Relationship to other authority records

- [Documentation authority](DOCUMENTATION_AUTHORITY_INDEX.md) classifies
  document truth/current/history status.
- [Runtime and delivery authority](RUNTIME_DELIVERY_AUTHORITY_INDEX.md)
  governs the Windows executable chain.
- [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)
  governs implementation ownership; a directory name cannot change it.
- [Repository normalization state](history/repository-consolidation-20261019/current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
  is a frozen 2026-09-03 snapshot; its React/Tauri and G0 sequencing are
  superseded by R6/M0. Its dated hygiene evidence remains historical and does
  not authorize a move or deletion.


## 2026-10-30 体积与文件规范

Owner 要求先清理项目体积、规范全部项目目录和文件，再推进后端优先任务；前端布局由 Owner 在云端修订。授权与顺序只沿活动指针 `execution_control.owner_priority_20261030`，本节不维护第二份进度。明确的本轮清理授权允许按已审查的精确清单清理可再生成缓存，替代旧注释中“所有历史编译缓存永不清理”的无限保留理解；大小、年龄、ignored 身份均不单独授予删除权限。

### 文件落点

| 内容 | 落点与规则 |
| --- | --- |
| 源码、合同、配置、维护工具和测试 | 保持上表模块归属；正式工具放 `scripts/`，不按后缀批量搬移。模块边界变更先核消费者与回退。 |
| 当前授权和进度 | 活动指针、现行决定与唯一执行记录。来源报告不成为第二状态中心，旧片段保持历史身份。 |
| Owner 输入和外部报告 | `workspace/intake/YYYYMMDD-topic/`，附原件、来源、大小、SHA-256 和证据边界；已有归档引用原位置。 |
| 历史正文和轻量索引 | `docs/history/`；迁移需哈希、消费者和旧路径映射；运行库、日志包和完整构建载荷不进 Git。 |
| 临时脚本、测试输出、日志和回执 | `dev.py` 分配的 `.project-local/runs/<worktree-id>/<run-id>/` 下 `tmp/`、`logs/`、`artifacts/`，不再散落至仓库根或 `.project-local/` 根。 |
| 编译和依赖缓存 | 沿 `dev.py` 的共享 Core/Host target 与 lock；同一依赖锁不每 run 完整复制。保留离线依赖源；清理中间产物会增加后续编译成本。 |
| 候选、回滚材料和运行证据 | 大载荷留项目 ignored 目录，Git 仅保存轻量 manifest/哈希/结论。保护有效候选、必要回滚及唯一失败；相同载荷收敛为一份，经逐文件替代映射与恢复验证保全旧引用。 |
| 原件、真实数据、共享资源和 Agent 私有状态 | 不因规范化改动；Green、模型库及共享盘不属本次清理。私有目录不读正文，不据项目名认领。 |

### 生命周期与增长检查

正式便携 producer 的 >=1GiB 装配必须在 mkdir/copy 前提供用途、共享方式、保留理由，并同步生成本批 pre 计量，finally 封存 post；不接受旧 current 代替实时调用，不提供绕过参数。唯一固定治理基线为活动指针 `execution_control.owner_priority_20261030.operator_storage_checkpoint`，descriptor schema 为 `aaos.operator-storage-checkpoint/v1`，字段为 `schema/path/bytes/sha256/report_schema/recorded_by/measurement_scope`；`path` 为本仓 `.project-local/runs/<identity>/<run>/artifacts/<report>.json`，`report_schema` 为 `aaos.storage-footprint/v2`，bytes/SHA 绑定原始报告。Codex 仅在已有 Owner 授权的实际治理批次完成后登记，不冒称新增 Owner 原话。此处不重复可变基线值；基线不逐包自动滚动。缺登记、CI 无本仓可核 checkpoint 时明确失败，只能在对应已授权批次初始化，不自动继承、降级或绕过。本轮 large-copy 边界只支持 artifacts 落当前 REPO 内的 canonical run；linked worktree 的 common-owner artifacts 路由尚未适配，即使初始化 checkpoint 也不能解除此拒绝，后继须另行解决计量根/owner 映射，不视为本轮已支持。

pre 或载荷投影的既有 growth_review 为 REVIEW_REQUIRED 时停止复制；NO_NEW_GROWTH_TRIGGER 与 measurement_status=PARTIAL 分开记录，旧债持平/下降不新增触发。PARTIAL 不等于完整预算合格，产品静态成员 PASS 不能替代存储覆盖结论。每个大批次同步前后计量，无人为时限；measured_at 不证明全仓静止。失败保留候选/原异常，不自动删除；backend-only 继续现有 in-place＋pinnedCore 路线。小于阈值的合成装配不触发全仓扫描。此边界只治理当前便携 producer，非跨 producer 原子容量保证。

1. `dev.py` 为新 run 创建 `run-metadata.json`，记录归属、worktree、源码身份、创建时间和 `UNCLASSIFIED_PRESERVE`。14 天是复核提醒，不是删除期限；旧未分类 run 同样保留待核。
2. `storage_report.py` 计入源码、Git、环境、规范目录及散落目录的可读大小；不跟随 reparse point，不扫描凭据/Agent 私有目录。访问/长路径失败与排除项单列，可读下界不冒充完整体积。
3. 既有预算是复核线，编译缓存也计入。`--check-budgets` 可退出 2 触发审查，不能自动删除。相对同仓库 v2 基线新增规范外路径、类别首次超预算、净增超过 2 GiB，或当前超预算类别自身增长超过 2 GiB，均触发审查；其他类别减少抵消总量不豁免新越线或旧超预算类别的大幅增长。各超预算类别的可比较字节增量单列；旧债持平或下降不因此新增触发。基线承接有类别记录的旧债，不能把 PARTIAL 计量改成 PASS；有限反例与实际源码验证见[预算越线记录](history/storage-cleanup/2026-10-31-budget-crossing/README.md)及[旧超预算类别增长修复](history/storage-cleanup/2026-10-31-over-budget-class-growth/README.md)。
4. 大构建、打包、沙盒批次开始前和封存后各计量一次；单 run 预计超过 1 GiB，先记录载荷来源、共享方式、预计大小和保留理由。小测试不重复全仓扫描。生成者负责封存证据并清理可重建临时副本。
5. 沙盒输入应按源码/候选/工具指纹复用已验证的只读输入，重试只生成独立输出；不默认复制整套仓库、解释器、PowerShell 和安装器。共享输入改造须验证 guest 权限、写入隔离和身份绑定。
6. 目录规范化按“归属 → 消费者 → 目标与哈希 → 回退 → 执行 → 链接/行为验证”逐批处理。现有散落路径进入清单，不扩大 allowlist 掩盖问题，不一次批量改名破坏路径。
7. 精确删除须确认项目根内、无 reparse 逃逸、无人使用、源码/保护证据不在清单；副本有保留的同哈希替代，可重建缓存有锁定输入和重建命令；事后核对缺失/保留及退出码。拒绝项保留，不改 ACL 或终止共享进程。

检查示例（新的唯一 run ID；输出目录由 dev.py 创建）：

```powershell
.\.venv\Scripts\python.exe scripts/runtime/dev.py --run-id storage-review-YYYYMMDD-N -- .\.venv\Scripts\python.exe scripts/runtime/storage_report.py --json .project-local/runs/be268a2d33/storage-review-YYYYMMDD-N/artifacts/footprint.json --baseline <本仓库已登记的v2基线.json> --check-budgets
```

退出 2 表示增长/布局/预算需要复核，退出 1 表示布局或计量有未覆盖项；`NO_NEW_GROWTH_TRIGGER` 仅表示没有新增触发条件。精确清理结果沿唯一执行记录与对应 manifest 查询。

共享沙盒输入的正式检查入口是 [`scripts/runtime/sandbox_inputs.py`](../scripts/runtime/sandbox_inputs.py)，沿 `dev.py` 使用独立 run。它要求精确的来源清单 SHA-256，先拒绝私有状态、开发缓存、Windows 路径别名和重复声明，再核完整文件集、大小和哈希；不复制载荷，不改原输入。`--prepare-proposal` 仅写三路只读输入、一路全新可写输出的 `lifecycle.wsb.proposed`，不会启动程序。输入仍可能被宿主修改，实际启动前须再次核验；历史清单的 approval 仅说明来源，不授予新一轮执行权限。

冻结的旧 launcher 只接受每 run 自有的 package/input 映射，不能直接套用共享提案。共享 launcher 的配置/来源绑定与 guest 真实写入隔离未合格前，不把 `.proposed` 改成可执行配置或重跑旧 staging 生成整包副本。来源清单含 `.mimosa` 等私有状态时拒绝复用；保留旧证据，在新的 canonical run 准备洁净输入，不修改历史清单或扩大私有路径豁免。操作示例和本轮有限证据见[共享输入续批记录](history/storage-cleanup/2026-10-30-followup/README.md)。

共享来源的后继正式执行入口为 [`scripts/runtime/shared_sandbox.py`](../scripts/runtime/shared_sandbox.py)，按新run完整重核后，由显式开关执行映射探针或具名同版本混合Core生命周期。其唯一ID意图、三路只读输入、独立输出、精确停止和源输入事后核验，已有[真实离线有限验证](history/storage-cleanup/2026-10-30-shared-sandbox/README.md)；这是该类别的替代路径，不回写冻结旧 launcher，不自动恢复UI/网络/模型权限，也不放行历史混合私有输入。后继[自有连接终态修复](history/storage-cleanup/2026-10-31-owned-connection-terminal/README.md)要求环境清场与本次保留句柄的退出证据分别满足，停止环境失败仍尝试回收自有连接；45项模拟测试不追认历史未确认进程或新一轮真实沙盒资格。继续保留共享来源供所有消费者和恢复使用，未完成的其他生产者仍单独审阅。

Native 历史公开胶囊的有限准备入口为 [`scripts/runtime/native_inputs.py`](../scripts/runtime/native_inputs.py)，仅接受已审来源/完整清单指纹，复用现存三路输入，输出落当前独立 run。共享入口的 `--prepare-native-probe` / `--execute-native-probe` 只准备或验证映射；原 native 命令另存 `.wsb.proposed`，不在该模式执行。[有限验证与接续条件](history/storage-cleanup/2026-10-31-native-input-reuse/README.md)区分宿主不复制输入与 guest 业务仍有复制；未来业务须重核输入/空输出并单独资格，不从 mapping PASS 推出整包生产者全面替代。

Legacy 备份探针 [`scripts/probes/backup_restore_probe.py`](../scripts/probes/backup_restore_probe.py) 沿 `dev.artifact_directory` 分配当前 run 下唯一 UUID，启动时不删除旧固定目录。其[实际合成库验证](history/storage-cleanup/2026-10-31-backup-probe-routing/README.md)不替代 Rust Core 备份/恢复验收；未知归属的旧散落资料继续保留。

正式 backend candidate 的 [`prepare_bundle.py`](../desktop/scripts/prepare_bundle.py) 由既有 stager 独占创建 fresh 最终根，在该根直接准备 Python，不再先建完整 `*-python-input` 再复制一次。仅当前 canonical run 的内部 callback 使用该路径；默认独立 stager 仍复制 donor 并拒绝覆盖。锁定依赖、wheel 和 timing 留当前 run，`UV_LINK_MODE=copy` 只传准备子进程，拒绝 link/nlink、额外成员和非预期改动；失败保全，不启动删旧输出。其[合成资格与后继检查](history/storage-cleanup/2026-10-31-backend-runtime-in-place/README.md)不等于生产打包、实测回收或安装资格。

### 外溢追踪与迁移

冲突旅程的洁净准备入口为 [`scripts/runtime/conflict_inputs.py`](../scripts/runtime/conflict_inputs.py)：只提取固定Git身份的有限harness文件，不复制旧repo/历史/私有状态，安装包和PowerShell沿清单 `source_roots` 复用本仓保留输入。其显式共享冲突执行已有[真实离线有限验证](history/storage-cleanup/2026-10-30-clean-conflict-inputs/README.md)。有限harness快照不是产品构建身份；旧输入及恢复映射仍保护，未自动授权旧目录清理。

Owner 2026-10-30 追加外溢数据追踪、迁移和清理，沿活动指针的同一体积/规范化优先项执行。先查已登记历史精确路径、项目生成入口/配置、运行证据与当前消费者；路径登记和名称相似均不能单独证明所有权。每批记录生产者、所有者依据、精确源/目标、大小/哈希、数据库侧文件组与占用、恢复方式、源文件清理授权及事后读回。先修生成落点，再迁移保全和清理已确认冗余，避免旧入口继续外写。

归档日志、测试输出和旧候选沿项目 ignored 归属路径存放；源码/文档沿正式模块和 intake/history。共享工具/模型缓存、系统文件、真实产品资料和代理私有状态分别保留；不以外溢治理授权扫描 Home、磁盘或重组其他项目。精确授权内可以连续处理；ACL/锁拒绝及未确认所有权只阻塞对应项，不能扩大权限或推断不存在。原始 DB/WAL/SHM/lock 不拆组或按旧时间删除，活动库须沿一致备份/导出。

### Frozen donor archive — 2026-09-26

`docs/history/branch-donors/execution-reliability-20260926/` is HISTORICAL_RECORD, not execution authority. ARCHIVE.json identifies three exact-tip, byte-preserved repository documents and source hashes. This bounded archive is repository documentation; it does not classify other mixed history paths. The source branch was retired on 2026-09-27 after review and a verified full-history local bundle; the six bounded imported documents and duplicate/move dispositions are recorded in [the consolidation manifest](history/DOCUMENT-CONSOLIDATION-20260927.json). Other mixed history paths retain their protected classification.

### 2026-10-31 Owner 最新产物保留覆盖

本次“除了最新构建和产物，其余全部删除”沿活动指针 `latest_only_cleanup_20261031` 及[实际记录](history/storage-cleanup/2026-10-31-portable-pair-qualification/LATEST-ONLY-RETIREMENT.md)。只保留现用最新可用候选和其真实运行/构建依赖；不按每个历史改版、phase或失败另造永久保留大包。旧生成的安装器、运行库、展开仓库副本、测试fixture/合成DB和编译缓存均可按生产者与精确scope退役，真实数据/原始输入/主源码/未知来源及私有状态除外。历史保留字样与14天提醒不覆盖此次已审退役；未知对象仍待核。

保留紧凑原失败、manifest、来源和实际结果，大副本不作为留证默认方式。优先复用已审归属与现有清单，用当前metadata、占用/删除句柄及缺失后验完成必要验证；普通再生缓存不强制重复全载荷hash、全RM或整包恢复演练。硬链接只unlink选中旧名字，不能宣称相同逻辑大小的物理释放。真实ACL/锁/执行策略拒绝仅阻塞对应范围，不绕过；读取权限不等于删除权限。

新产物先复用共享输入/原地准备并沿canonical run落点；替代者可用后退役旧生成副本，测试终态复核其temp/cache，当前仍需调试的最新版保留。固定增长基线只在已授权实际治理批次后更新，禁止逐包自动上调掩盖累计增长。现有>=1GiB便携producer门禁继续执行；其他producer的自动保留/增长门禁未全面覆盖，不能把本规则或NO_NEW_GROWTH_TRIGGER当作自动清理已经实现。
