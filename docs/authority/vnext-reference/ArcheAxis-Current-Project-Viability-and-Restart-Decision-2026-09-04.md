# ArcheAxis Knowledge 现有项目可用性与重启决策

副标题：现有代码还能不能继续用，以及究竟要不要重新开始

决策日期：2026-09-04
云端基线：**main@ce3c2de551bcaac52c8a26d012e6482c1a73a540**
稳定基线：**v0.6.14**（2026-08-29）
范围：只审计 ArcheAxis Knowledge；WORK-LAB、DESIGN-LAB 不纳入本次产品决策
方法：历史记录 + 最新远端 Git/Actions/Release + 干净浅克隆静态扫描 + 同命令本地复验 + 官方迁移/SQLite资料

> **执行勘误：** 本文中的 `maintenance-only` 只约束 legacy 产品路径，
> 不冻结 `main` 分支本身；同一 `main` 必须通过小 PR 接收隔离的永久
> vNext 目录。任务编号、授权与切片协议以包根 `MASTER-TASKPACK.md`、
> `TASK-GRAPH.yaml` 和 `repo-seed/.project/` 为准。

## 执行结论

**现有项目还能用，但不能继续担任未来产品主线。必须重新开始的是“产品权威主线”，不是整个项目。**

最准确、不会误导执行的表述是：**同仓结构性重启 vNext；冻结 v0.6.14 为 legacy；当前 main 继续承载新旧两区，但只有旧产品路径转为 maintenance-only 与吸收源；历史、数据、合格能力、fixtures、测试语义和发布证据全部继承。**

这不是删库重写，也不是创建一个与历史断裂的新仓库。新主线应在原仓库建立隔离目录、新数据库和新的权威边界：Avalonia/C# 负责桌面，Rust 负责领域 Core/BFF/迁移/恢复和唯一业务数据库写入，Python 只做无主库权限的能力 worker。旧库只读导出，新库只由 Rust 写，禁止双写。

### 一句话判定

| 问题 | 判定 |
|---|---|
| v0.6.14 能不能启动、恢复、试用 | **能，有完整发行证据；但只建议隔离副本试用** |
| 当前 main 能不能作为下一版发布候选 | **不能；同一 SHA 的 nightly 全量套件失败** |
| 当前架构能不能原地演进为终局 | **不值得；UI、领域权威、数据库所有权三层都要换** |
| 是否要把全部代码和历史丢掉 | **绝对不要** |
| 是否必须重开主线 | **必须** |
| 推荐形态 | **原仓库内 vNext 结构性重启 + 逐能力吸收 + 单向数据迁移** |

### 三层可用性

| 对象 | 可恢复 | 可隔离试用 | 可承载唯一重要数据 | 可作终局主线 |
|---|---|---|---|---|
| `v0.6.14` 不可变发行版 | 是 | 有条件是 | 暂不建议 | 否 |
| `main@ce3c2de` | 源码可恢复 | 仅开发沙箱 | 否 | 否 |
| 规划中的 vNext | 尚未交付 | 尚未交付 | 交付目标 | 是 |

## 1. “还能用”到底是什么意思

“能用”至少包含四个不同等级，不能混成一个结论：

1. **可恢复**：安装包、校验和、版本身份、回退材料存在且绑定精确 SHA；
2. **可试用**：在隔离 workspace 中可启动并走部分真实功能；
3. **可信日常使用**：真实数据、迁移、失败恢复、桌面交互和全格式链路在当前版本完成资格化；
4. **可继续作为终局主线**：现有架构与最终语言、权威写入、契约和维护方向一致。

v0.6.14 满足第 1 级，并有条件满足第 2 级；当前证据不足以把它提升到第 3 级。当前 main 连发布资格都没有，且第 4 级明确不成立。这种分级避免两个同样错误的极端：“旧项目完全是废品”与“有 Release 就已适合放唯一一份知识数据”。

## 2. 最新云端事实：旧发行成立，当前 main 未合格

### 2.1 精确基线

远端 `refs/heads/main` 在本次审计时为 `ce3c2de551bcaac52c8a26d012e6482c1a73a540`，提交主题是 `docs: record exact CI repair evidence`。这不是旧交接中的 `db13d056`、`9217c510` 或 `af216e3`；所有当前判断都绑定这个最新 SHA。[R01]

从 v0.6.14 tag 指向的 `c202c5b5...` 到该 main，已有 25 个提交、155 个文件变化，约 7,244 行新增、1,547 行删除。它不是一个已经发布版本后的微小文档修补，而是一批需要重新完整资格化的变化。[R02]

### 2.2 最新 push 的绿色不是产品绿色

当前 SHA 的 push CI `33787077225` 显示 overall success，但只实际通过 `gateplan`、`lint`、`a0-gates`；测试、格式、迁移、安全、wheel、浏览器、Windows、桌面构建和 installer 等 11 个任务均为 skipped。该结果只能说明路径选择后的快速门成功，不能证明应用、数据迁移或 Windows 产品路径成功。[R03]

### 2.3 同一 SHA 的 nightly 明确失败

2026-09-04 的 nightly `33851057281` 对同一 SHA 运行：Python 3.11/3.13 compatibility 成功，`full-suite` 失败，随后 browser-smoke 与 windows-runtime 因依赖关系被跳过。此前 #27、#28 也连续失败。因此当前主线没有项目自己要求的全量资格化证据。[R04]

本次审计在干净浅克隆上重跑 nightly 的同一 pytest 命令，结果为 **2163 passed、7 skipped、2 failed、3 warnings，180.29 秒**。失败分别为真实网页测试对 `example.com` 超时，以及全链路截图 OCR 找不到 Chromium。公开 GitHub 日志只显示 full-suite 退出码 1，未授权状态无法下载完整日志，所以不能声称云端与本地是同一个断言；但本地复验足以证明当前 full-suite 不是稳定、完全自包含的资格化门。nightly 工作流又是在 full-suite 成功之后才进入安装 Chromium 的 browser job，顺序本身需要修正。[R05]

### 2.4 v0.6.14 是真实可恢复基线

仓库内不可变发行收据把 v0.6.14 绑定到 commit `c202c5b5...`、tree `8150692f...`、完整 Verification CI `33261549586` 和 Release run `33262172637`。两次 run 成功；9 项资产包括 Setup、Green、Portable、wheel、identity、manifest、SBOM、checksums 与第三方声明；三分发生命周期与公开下载回读为 PASS。[R06][R07]

因此 v0.6.14 必须保留为：恢复点、兼容基线、旧数据导出器运行环境、行为 oracle 和回归对照。该收据也明确写明：它不证明未完成产品能力，不提升当前 main。

## 3. 代码事实：Rust 还不是 Core

最新树有 1,246 个 tracked 文件，其中 642 个 Python 文件；只有 12 个 Rust 文件，没有 C# 源文件或 `.csproj`。四个主要 Python 业务根约 315 个文件、57,399 行。当前领域逻辑和持久化权威明显仍在 Python，而不是 Rust。

两个 Tauri crate 都没有 `rusqlite` 或 `sqlx` 等领域存储依赖。根 `src-tauri/src/main.rs` 直接引用另一个 Tauri 根中的 backend/job/protocol/runtime 源文件；Rust 的实际职责是 Windows 宿主、子进程监督、恢复与安全边界。它启动 bundled Python，再执行 `python -m app.runtime_entrypoint core`。仓库自己的语言权威索引也明确把产品域 writer 定义为 Python + SQLite，并禁止在 G0 关闭前加入 Rust 生产 writer。[R08]

所以“核心应该是 Rust”没有记错——那是最终架构目标；“当前项目已经是 Rust Core”则与代码不符。

### 当前结构的硬缺口

| 指标 | 本次干净克隆结果 | 风险 |
|---|---:|---|
| 生产 Python 直连 `sqlite3.connect` 文件 | 58 | 写入、事务、校验和迁移权威分散 |
| 生产 Python 含 `CREATE TABLE` 文件 | 27 | DDL 与领域实现交织 |
| V2 Source/Evidence/Machine Receipt 真实消费者 | 多数为 0 | 新 API 存在不等于生产链已迁移 |
| 生产 `sys.path` 修改 | 18 | 包边界和运行环境未封闭 |
| C# 项目 | 0 | Avalonia 产品面必然是新实现 |
| Rust 领域数据库依赖 | 0 | Rust 目前不是领域 writer |

仓库自带 owner audit 在这个 SHA 上仍返回 58 个 SQLite 直连文件；consumer audit 仍只找到 DeepTutor bridge 调用 human-learning `append_event()`，Source V2、Evidence bundle store/review 和 machine receipt 无非定义消费者。G0 登记也把 sole-writer coverage 标为 OPEN，并禁止 Rust/Python 双写。[R09]

SQLite 的 WAL 可以让 reader 与 writer 并行，但同一时刻仍只有一个实际 writer。数据库引擎的串行锁并不会自动形成“一个应用级权威写入边界”；58 个可写入口仍会分散业务校验、幂等、审计、事件和迁移规则。[S01][S02]

## 4. 三条路线比较

### 4.1 方案 A：继续在当前 main 原地修

优点是表面上最快：已有 UI、Python 能力、安装脚本、测试和旧数据路径。缺点是终局需要同时替换 React/Tauri 产品面、Python 领域 writer、数据库所有权和进程协议。继续加功能只会扩大未来必须二次迁移的表面，并延长双栈、双权威和文档漂移窗口。

**判定：仅允许维护，不作为产品主路线。**

### 4.2 方案 B：删除旧项目，从空白新仓重写

它会得到干净目录，但也会丢失最难重建的资产：不可变 Release、真实 schema、边缘行为、失败案例、fixtures、rights/hash 记录、兼容语义、安装生命周期和历史决策。大型空白重写在较长时间内没有可对照的真实系统，风险集中到最终切换。

**判定：拒绝。**

### 4.3 方案 C：同仓 vNext 结构性重启

在原仓库建立隔离的 `apps/`、`crates/`、`services/python-workers/`、`packages/contracts/` 和新 workspace 数据根；旧树 feature-freeze，但继续提供导出、行为对照和迁移输入。功能按一个个真实垂直切片切走，直到 legacy 可退役。

**判定：采用。** 微软的 Strangler Fig 与 Anti-Corruption Layer 指南也支持逐步替换、在新旧语义之间设隔离层，并在替代路径达到可靠性/可观测目标后再退役旧端点。[S03][S04]

### 4.4 加权决策矩阵

分数 1-5；加权结果只是透明化判断的决策辅助，不是假装精确的工程测量。

| 维度 | 权重 | 原地修 | 空白重写 | 同仓 vNext |
|---|---:|---:|---:|---:|
| 首个可用闭环速度 | 20 | 3 | 1 | 3 |
| 终局架构匹配 | 20 | 1 | 5 | 5 |
| 数据安全 | 20 | 2 | 2 | 5 |
| 历史与证据复用 | 15 | 5 | 1 | 5 |
| 切换可逆性 | 10 | 2 | 2 | 5 |
| 交付确定性 | 15 | 2 | 1 | 4 |
| **加权总分 / 100** | **100** | **49** | **42** | **89** |

同仓 vNext 并不是折中主义。它明确重启未来运行时，同时拒绝浪费已有的可验证资产。

## 5. 哪些保留，哪些重做

| 处置 | 资产 | 规则 |
|---|---|---|
| **Reuse** | Git 历史、v0.6.14、SBOM/checksums/NOTICE、rights、golden fixtures、稳定纯函数 | 原样保留，绑定来源 SHA 与许可证 |
| **Wrap** | OCR/ASR、格式转换、抓取、解析、模型 provider、评测算法 | Python worker 无主库路径，只收输入包并返回候选/证据包 |
| **Port** | Source/Anchor/Knowledge/Review/Learning/Job 状态机，迁移、恢复、幂等与审计 | 按语义重建到 Rust；禁止逐行翻译旧 Python |
| **Oracle** | 旧 FastAPI、Pydantic DTO、React/Tauri、旧 DB schema、行为测试 | 用于差分和兼容，不成为 vNext 运行依赖 |
| **Quarantine** | 无消费者 V2 store、权利不明样本、无法证明运行可达的模块 | 先证明消费者、许可和价值，再决定吸收 |
| **Retire** | 58 个直连、分散 DDL、`sys.path` 注入、反向导入、重复 Tauri 根、mock/placeholder | 对应 aggregate 切换后删除，历史由 Git/tag 保留 |

判断一个旧模块能否直接复用必须同时满足：行为在当前精确 SHA 可达；无主库写权限；契约可版本化；许可证清楚；有 fixture 与回退；不会把旧目录依赖带进新核心。只要任一项不满足，就进入 wrap/port/oracle，而不是 copy。

## 6. 正确的迁移与切换

### 6.1 数据方向

旧数据迁移只允许这一条方向：

```text
legacy DB snapshot
  -> read-only exporter
  -> versioned migration package + hashes + rights + ID map
  -> Rust dry-run validation
  -> staging vNext database
  -> semantic diff + rejection ledger
  -> owner confirmation
  -> atomic profile activation
```

旧应用与 vNext 不共享可写数据库、不做实时同步、不做双写。SQLite 官方 Online Backup API 可以在源数据库仍被访问时生成一致快照，适合本项目先快照、再只读导出；不能直接复制活动中的 `.sqlite/.wal/.shm` 文件冒充备份。[S05]

### 6.2 回退边界

在首次 vNext 写入之前，可以把 profile 指针切回未改动的 legacy 副本。首次 vNext 写入之后，不允许自动切回旧 writer，因为旧系统无法理解新 revision、receipt 和状态；回退只能恢复 vNext 自己的上一个快照，或明确导出一个兼容包。这个限制必须在 UI 明示。

### 6.3 每个 aggregate 的切换门

1. 旧 schema 与语义清单完成；
2. 只读 exporter 有版本、hash、rights 与 ID 映射；
3. Rust importer dry-run 不写正式库；
4. 两个真实复制 workspace 的 `unclassified_loss=0`、`hash_mismatch=0`、`dangling_reference=0`；
5. 重复导入为 no-op；
6. 新旧行为差分连续两次零未分类语义差异；
7. exact-SHA CI、Windows 产品路径、备份恢复与拒绝路径通过；
8. 才能把该 aggregate 的旧 writer 退役。

## 7. 立即执行的项目政策

### legacy maintenance-only

legacy 产品路径只允许四类变化：数据损坏修复、安全修复、导出/备份/恢复、妨碍迁移或复现实验的资格化修复。`main` 仍可通过受约束小 PR 接收隔离的 vNext 永久目录。停止向 React/Tauri/Python 旧主线增加新的终局产品功能。

CI 立即增加两个冻结门：

- `sqlite_direct_connect_files <= 58`，第 59 个直接失败；目标是只降不升；
- `legacy_product_feature_delta = 0`，除批准的 maintenance 标签外拒绝扩大旧产品面。

### vNext clean boundary

- 新数据库从 Day 1 只由 Rust 打开 read-write 连接；
- Avalonia、Python、Agent 与脚本不得获得主库路径；
- Python worker 只能写 job scratch，返回 schema/hash 完整的候选包；
- 新代码不得从 legacy 根反向 import；
- `contracts/`、迁移、锁文件、CI、版本和发布 manifest 使用串行合并租约；
- 每个并行 Agent 使用独立 branch/worktree 与 allowed-paths 信封。

## 8. 首个 30 天计划

### 第 0-2 天：冻结与测量

1. 创建 `legacy/v0.6.14` 不可变说明和 `LEGACY_MANIFEST.yaml`；
2. 将 current main 中的 legacy 产品路径标为 maintenance-only，同时保留 main 接收隔离 vNext 目录；
3. 修复 nightly 顺序：full-suite 不依赖实时互联网，Chromium fixture 在需要它的 job 之前安装；
4. 固化 58 直连、27 DDL、语言 LOC、consumer reachability 基线；
5. 建立 vNext 新目录、新 workspace ID 和独立空数据库；
6. 写三份 ADR：终局语言、单写者、legacy 单向迁移。

### 第 3-10 天：Hello Triangle

Avalonia 启动 Rust Core；Rust 通过 stdio NDJSON 调一个 Python 文本/PDF 能力 worker；worker 返回结果；Rust 校验后唯一写入新库；UI 回读。强杀 worker 不损坏权威数据，job 失败可重试且幂等。

### 第 11-20 天：最小真实闭环

导入原件 -> 保存不可变 RawAsset/hash -> 转换 -> Reader 精确 Anchor -> 保存个人知识或机器候选 -> 人工接受/拒绝 -> FTS 检索 -> 跳回来源 -> 创建一次学习事件 -> 关闭重启回读。

### 第 21-30 天：迁移试点与 Owner Preview

只迁一个复制 workspace、一个 aggregate；生成导出 manifest、dry-run、拒绝账本和差分。通过后打包 Windows Green Preview，完成无终端启动、备份、恢复、版本握手与 12 步 Golden Journey。旧 v0.6.14 仍可独立运行。

第 30 天不是全量迁移承诺，而是验证“新主线能独立闭环、旧资产可安全进入”。如果 Hello Triangle 在第 10 天前仍无法形成可重复端到端路径，停止扩功能，先修契约、进程和写入边界。

## 9. 什么证据会推翻本裁决

只有以下条件**全部**在限定周期内成立，才值得重新考虑原地修；普通编译或一个绿色 workflow 不够：

1. Owner 正式撤销 Avalonia + Rust Core 终局，决定长期保留 React/Tauri + Python authoritative writer；
2. 当前精确 HEAD 的 full suite、browser、Windows、wheel、installer、compat、format、migration 和 security 均实际运行并通过，无 required skip；
3. 真实运行 trace 覆盖每个写入口，58 个入口均证明只读或统一进入一个 command boundary；
4. 一个真实 aggregate 已迁到 Rust，连续两次差分零未分类语义差异，无 Python/Rust 双写；
5. 两个复制 workspace 的迁移损失、hash mismatch 和 dangling reference 均为零；
6. Avalonia 只依赖稳定新契约，移除 React/Tauri 不阻断核心闭环；
7. 实测显示在旧树完成其余 aggregate 的成本、失败面和切换风险显著低于隔离 vNext。

若这些条件真的满足，项目实际上已经形成 vNext 边界，仍不会回到“继续随意在旧树堆功能”的路线。

## 10. 风险与限制

- **本轮没有在全新 Windows 机器重新下载并安装 150-224 MB 的 v0.6.14 包。** “可恢复发行版”来自精确发布收据与既有 lifecycle 证据；最终现场可用性仍需一台干净 Windows 机器复验。
- **GitHub 未授权访问无法下载 nightly 完整日志。** 已确认云端 full-suite 退出码 1；本地同命令复现出两个失败，但不把本地断言冒充云端精确根因。
- **当前仓库文档有漂移。** README 顶部仍以 v0.6.11 叙述，HERMES_HANDOFF 早于 v0.6.14，CURRENT_REALITY 仍指父 SHA。以后当前真相应按 release receipt / exact run / G0 register / append-only log 的优先级读取，而不是只看一份交接文档。[R10][R11]
- **个人研究、非商业使用不自动解除第三方许可。** 代码、模型、权重、数据、素材和 fixtures 继续分别记录许可与用途边界。
- **结构性重启不是无限蓝图。** v0.1 只做 Workspace、Source、KnowledgeItem、LearningItem、Job 五个 aggregate 和一条 Golden Journey。

## 11. 最终执行清单

- [ ] 冻结 v0.6.14 tag、资产、receipt 与恢复说明；
- [ ] 当前 main 改为 maintenance-only；
- [ ] 修复 nightly 的网络与浏览器非密闭问题；
- [ ] CI 固定 58 SQLite 直连上限，只降不升；
- [ ] 在同仓建立隔离 vNext 目录与新数据根；
- [ ] Rust 从第一天成为新库唯一 writer；
- [ ] Python worker 无主库路径和句柄；
- [ ] 旧代码逐项打上 reuse/wrap/port/oracle/quarantine/retire；
- [ ] 先完成 Hello Triangle，再迁一个 aggregate；
- [ ] 两个复制 workspace 差分通过后才考虑 cutover；
- [ ] 首次 vNext 写入后禁止自动回到 legacy writer；
- [ ] 所有完成声明绑定精确 SHA、实际执行 job 与可读 receipt。

## 附录 A：一手仓库证据

R01 — GitHub 最新 main 提交 `ce3c2de`：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/commit/ce3c2de551bcaac52c8a26d012e6482c1a73a540

R02 — v0.6.14 到最新 main 的变更比较：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/compare/c202c5b5a4789f0dc21accaa7ccbfed4676f0573...ce3c2de551bcaac52c8a26d012e6482c1a73a540

R03 — 当前 main push CI `33787077225`：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/33787077225

R04 — 同一 SHA 的 nightly `33851057281`：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/33851057281

R05 — nightly 工作流定义：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/.github/workflows/nightly.yml

R06 — v0.6.14 不可变发行收据：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/reports/release/v0.6.14/release-evidence.json

R07 — v0.6.14 完整 Verification CI：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/33261549586

R08 — 当前语言权威边界：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md

R09 — 当前 G0 阻断登记：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/docs/current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md

R10 — README 当前 UI 与发行叙述：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/README.md

R11 — 追加式执行状态日志：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/docs/truth/EXECUTION_STATUS_LOG.md

R12 — 当前系统边界：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/SYSTEM_BOUNDARY.md

R13 — 项目 Python 依赖与运行时事实：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/pyproject.toml

## 附录 B：外部官方资料

S01 — SQLite Write-Ahead Logging：
https://www.sqlite.org/wal.html

S02 — SQLite Isolation：
https://www.sqlite.org/isolation.html

S03 — Microsoft Azure Architecture Center, Strangler Fig Pattern：
https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig

S04 — Microsoft Azure Architecture Center, Anti-Corruption Layer Pattern：
https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer

S05 — SQLite Online Backup API：
https://www.sqlite.org/backup.html

—— 完 ——
