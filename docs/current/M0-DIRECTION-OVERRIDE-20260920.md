# M0 最短完整闭环方向覆盖（2026-09-20）

## 记录性质与优先级

- `overlay_id`: `M0-SHORTEST-COMPLETE-LOOP`
- `source`: 用户提供的《M0 最短完整闭环 · 任务方向优先级重定向指令》
- `authority_base`: R6 immutable TaskPack `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`
- `supersession_record`: `DECISION_SUPERSESSION_LEDGER.yaml` `SUP-020`
- `scope`: 这是 R6 的优先级覆盖和执行收敛记录，不是并行 TaskPack，不删除、不重写 R5/R6/审计/收据。

R6 继续作为任务定义、契约和证据基线；M0 只改变“先做什么”和“哪些增强暂缓”。历史状态不能直接升格为当前完成，所有最终结论仍需当前代码、运行时和 Owner Gate 证据。

## 唯一最高目标

```text
真实输入
→ 插件执行
→ Canonical Source
→ Canonical Knowledge
→ Personal Knowledge
→ Search
→ Learning Plan
→ Course / Learning Artifact
→ 真人学习
→ Assessment
→ Mastery / FSRS
→ Machine 使用同一 Knowledge
→ Evaluation
→ Correction
→ Retest
→ Restart
→ Backup / Restore
→ Legacy Copy Migration
→ Local Green Candidate
→ 原位替换
→ Restart / Readback / Rollback
```

最终只允许 `LOCAL_GREEN_READY_FOR_OWNER_REVIEW` 或 `NOT_READY`；不允许把 M0 结果写成 `RELEASE_READY`。产品 Release、tag、新版本号和公开资产继续冻结。

## 当前现场基线

- 当前分支：`main`
- 当前本地与远端 `main`：`7a32702769c1be2c825aa3636c510650edb2dce5`（最新 A10 courseware scalar 契约修复已推送；本记录收据提交以其为 first parent）
- `origin/codex/full-loop-0906`：当前本地 ref 不存在；本记录不把它当作已同步证据。
- R6 状态：`release_status=FROZEN`、`overall_status=IN_PROGRESS`
- R6 TaskPack provenance：源包 CRLF SHA `dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529`；仓库规范化 LF SHA `788c5d50b5953d21eb9f67587d5406d37ad2e5457c2ca3b991399d9988e5951b`。两者均保留，不能混称为同一原始字节摘要。
- R6 既有候选、worker 修复、合成迁移和两次重启证据保留；它们是分段证据，不是完整 M0 闭环。
- `.project-local` 是唯一开发运行/证据输出根；外置共享模型、工具、Green、真实资料库和测试资料库不因 M0 方向改变而迁移或改写。

## P0–P6 映射审计

状态语义：`INHERITED_TESTED` 表示可继承的当前证据；`PARTIAL` 表示存在局部证据但不能覆盖 M0；`MISSING` 表示尚无满足 M0 的证据；`BLOCKED` 表示需要 Owner 或受保护资源；`DEFERRED` 表示明确移到 M1/M2。

| M0 包 | 责任 | 当前判断 | 可继承或缺口 |
| --- | --- | --- | --- |
| P0 | Authority + Plugin Kernel | `PARTIAL` | R6 authority、No-Release 和 capability registry 已有；M0 priority overlay、完整启停/默认/fallback/health/替换闭环尚未证明 |
| P1 | Source + Format + Knowledge | `PARTIAL` | worker 路由、format receipt、Knowledge V3 读投影和 human/machine 权限已有；统一主 Parser/fallback、真实常用格式、V3 写入和三类知识同旅程仍缺 |
| P2 | Search + Learning Plan + Course | `PARTIAL` | FTS5、domain/course/artifact 契约已有；embedding/reranker、General 行为包、KC/Prerequisite/Objective、CourseManifest 与第一 Renderer 的真实运行仍缺 |
| P3 | Human Learning | `PARTIAL` | Core 已按 active accepted/personal Knowledge 生成并持久化 Assessment，review API 回传答案与开放 projection；真人 UI 首次学习、authoritative Mastery/FSRS 全量恢复和完整重启回读仍缺 |
| P4 | Machine Loop | `PARTIAL` | machine task/correction/retest 数据边界和 receipt API 已有；同一 Accepted/Personal Knowledge 的真实任务、真实错误、人工 Correction、Retest 仍缺 |
| P5 | Persistence + Migration | `PARTIAL` | canonical Rust SQLite、合成非空迁移和两次重启身份已有；完整 Backup/Restore 校验、全状态重启回读和真实 Legacy copy 语义 diff 仍缺 |
| P6 | Local Green | `PARTIAL/BLOCKED` | exact-SHA candidate、worker 与 headless smoke 已有；Candidate 全旅程、现有 Green 备份/原位替换/回滚需 Owner Gate，不能提前执行 |

## 2026-09-20 并行执行回读

本轮按独立写集并行完成 P0、P1、P2 的最小可验证切片；它们不等于 M0 全链路完成：

- P0：`PARTIAL`。现有 capability kernel 与真实 Python worker 的 manifest/runner/health、启用/禁用、失败和恢复组合已有本地测试证据；正式宿主默认/fallback/provider replacement 生命周期仍未绑定，因此不升级为 M0 完成。
- P1：`TESTED_LOCAL`。格式执行保留 attempted engines、fallback 状态和无路径泄露的原因，并在 conversion run 重启回读和 format receipt 中保持一致；真实常用格式质量、外部引擎和 Knowledge V3 写入仍未闭合。
- P2：`TESTED_LOCAL`。新增 general-only CourseManifest、Knowledge Component、Learning Objective 契约，覆盖 Concept/Fact/Procedure/Method/Case、引用闭合、lesson 要求和跨域拒绝；Search 的 embedding/reranker、真实课程内容和 renderer 仍未闭合。
- P3：`PARTIAL`。Core review receipt 现在保存用户提交的 answer，空白回答在 API/UI 被拒绝，Assessment 绑定与 FSRS/restart API 回归已通过，桌面重启打开学习项会恢复已保存答案文本；真人 UI 首次学习、authoritative Mastery/FSRS 全量恢复和完整重启读回仍缺。
- P5：`PARTIAL`。备份校验现在同时验证 `sources.sha256` 对应的 `.objects` 内容，篡改对象会被拒绝；backup/migration/store SQLite Rust 定向测试合计 `18 passed`，SQLite workspace identity 仍需冻结。
- P4.1：`TESTED_LOCAL / PARTIAL`。machine task 要求 `knowledge_version` 绑定 active accepted/personal Knowledge，`retest_of` 绑定已存在 failed task；API/domain 定向 Rust 测试合计 `12 passed`，真实 Core 进程的合成 correction→retest→restart 已通过，真实模型任务和用户错误仍未完成。
- P5.1：`TESTED_LOCAL / PARTIAL`。backup/verify 拒绝 schema 漂移、外键损坏和源对象 hash 篡改；对应 backup/migration/store SQLite 测试已通过，SQLite `workspace_id` 仍需 Owner/Authority 决策。
- P3.1：`IMPLEMENTED_LOCAL / TESTED_LOCAL_PARTIAL`。Core-owned Assessment 已按 active accepted/personal Knowledge 生成并持久化，review 可绑定 assessment_id，Avalonia 显示并恢复 answer 文本；Mastery projection、真实 UI/runtime 和全状态重启读回仍未闭合。

本轮增量（当前 subject：`97300cc6c8e6389edc33f5dc32adaec8761e6c58`）：P1 补齐合成 fallback 的 intake → SQLite conversion run → public receipt readback；P2.1 为 General CourseManifest 增加 prerequisite 引用闭合、自环和多节点环校验。两项均为 `TESTED_LOCAL` 契约/回归证据，不升级为真实外部引擎、真实课程渲染或全链路闭环。

P4 增量（当前 subject：`b20d87af26b120161bed1dab3ae21da3c64f24f6`）：machine-feedback schema 现在要求 correction_applied/correction_reverted 携带 `feedback.reviewed_by_human=true`；这只收紧已声明的人审约束，不等于真实模型 correction/retest 运行闭环。

P5 增量（当前 subject：`fc0df3a182abed4feded8eeb0ab25b88bb4bcadb`）：directory backup manifest 现在拒绝绝对路径、点段/父段逃逸、root 外 symlink 和未列出的旁路文件；这仍是 Python backup 层证据，不替代 Rust SQLite schema/FK/source-object hash 或 workspace identity 决策。

A14 增量（当前 subject：`274de700c4dc4c02ede5d15fb3938fef5498677f`）：closed-loop complete receipt 现在要求 correction 与 retest 阶段各自有非空 evidence refs；这只阻止空证据误报，不证明真实 runtime journey。

工具链增量（当前 subject：`428de718a808acebb025ca01f3c1e62c60c30916`）：项目声明的共享 Rust/MSVC exact path 与 Windows SDK 变量已验证；domain `cargo check` 通过，Assessment/learning persistence/machine tasks 合计 16 passed；API learning-state、machine-task、machine-correction 合计 10 passed，包含真实 FSRS worker、Assessment 绑定、answer 读回与重启；桌面契约 `11 passed, 1 warning`，外部 .NET SDK 10.0.400 构建 `0 warnings, 0 errors`，CoreSupervisor apphost 与 Vocabulary wire cases 运行通过。完整 Avalonia 首次使用、authoritative mastery 与 adaptive journey 未闭合。

A12 增量（当前 subject：`de80584cf5282f78c7a910a4487cbc04c3bd6602`）：Green candidate verifier 现在拒绝候选目录中未列入 `candidate-manifest.json` 的旁路文件；定向候选/发布回归 `22 passed, 1 skipped, 1 warning`，Ruff 通过。该增量只加强本地候选包完整性收据，不证明清洁机器、签名、安装器、Green 原位替换或回滚。

A09/A10/P2 增量（当前 subject：`4e5394e39d81476591a3bd0fd892976f4213c331`）：General artifact 的知识组件必须被 Learning Objective 覆盖；native lesson renderer 对 interactive 或非 `native-lesson` 形状 fail closed。定向回归 `26 passed, 1 warning`，Ruff 通过。该增量只强化课程契约和静态投影边界，不证明真实互动课程或真人学习闭环。

A00 authority 修复（当前 subject：`5005172114d329057e08829bf780a343b9c1d76f`）：保留不可变 TaskPack 正文和用户源 CRLF provenance SHA，补充仓库 LF artifact SHA、换行语义和 `check_r6_taskpack_authority.py` 验收；`EXECUTOR-START.md` 不再包含未解析的 `$sha`。这修复了摘要语义缺失，不等于 R6/M0 运行时闭环完成。

A07 碰撞修复（当前 subject：`facd30eacc2ce217825132988af9ab546cec6881`）：machine-growth receipt 对重复、后缀相撞和空时间戳 fallback 使用全局占用集生成确定性唯一事件 ID；A07 定向套件 `20 passed, 1 warning`。仍不等于真实模型、真实用户错误或 review/reuse/retest 闭环。

P0 route contract 增量（当前 subject：`80398b1e4fd550301b5f7949a6fa3d0c53602960`）：新增静态检查，遍历 `text_ndjson.ROUTES`，验证 worker 路径 containment、`ENGINE`/`extract()`、版本、媒体类型和调用元数据；定向套件 `27 passed, 1 warning, 47 subtests`，vNext worker check 通过。真实 manifest/health/启停/provider replacement 生命周期仍未闭合。

P0-H01 provider-routing 契约切片（当前 subject：`5a53d9a6445935e755df5f3ac263bd7922839aa7`）：新增纯 Python fail-closed snapshot contract 与反例测试，冻结 schema_version、generation、provider manifest SHA、enabled/installed、health receipt、default/fallback 闭合、相对引用安全和健康筛选；定向契约 `10 passed, 1 warning`，相关 provider/CapabilityStore/manifest/activator 回归 `60 passed, 3 warnings`，Ruff 与语法编译通过。该切片不接入正式宿主，P0-H01 仍需跨层 Authority 决策与 Rust/C# 实现。


P0-H01 identity hardening（当前 subject：`5a53d9a6445935e755df5f3ac263bd7922839aa7`）：Astra 当前-SHA 复核发现 provider/capability/fallback 标识首尾空白归一化不一致；新增 RED→GREEN 回归并统一拒绝空白身份，避免快照解析成功但执行查找失败。契约与相关回归 `62 passed, 3 warnings`，Ruff、py_compile、git diff --check 通过；正式宿主仍未接入。
P0-H01 host lifecycle 边界（当前 subject：`a5ef4f5f4d29203bda4137ecb9cc026658ecb309`）：正式宿主仍未接入统一 provider routing；已形成 `provider-routing.json` sidecar 提案，要求 CapabilityStore 原子写、Rust Core 只读、Core 为唯一 Canonical writer。该卡标记 `BLOCKED_BY_AUTHORITY_DECISION`，不得把 test-only worker 生命周期升格为 M0 完成。当前 Rust/API 运行还受外置 Windows SDK `kernel32.lib`（历史 `LNK1181`）阻塞。

P0-H01 CapabilityStore sidecar feasibility（当前 subject：`90573dcef2573029da3fc70f706349fb9d272221`）：只读审计确认 manifest/record 没有 capability、route、generation、health 的权威输入，且 pack move、index replace、sidecar replace 不是单一事务；disable/enable 的 fallback 语义也未冻结。相关回归 `36 passed, 2 warnings`，实现保持 `BLOCKED_BY_AUTHORITY_DECISION`。

P2-R2 renderer provenance（当前 subject：`4b035b8983061e5ebcb888c89d862e733e5e15b8`）：补充 native lesson Projection 的 `source`、`wikilinks`、`tags` 绑定回归，确保确定性 General lesson 投影的 provenance 不被静默丢失；renderer 定向回归 `8 passed`，Ruff 与 diff check 通过。该切片只加强本地 projection 契约，不等于真实课程渲染或真人学习闭环。

P4/A14 real-model preflight（当前 subject：`004587fde08661239012ac1c70b180eea363c2c0`）：项目模型配置仍为 `stub/local-stub`，本机未发现 `ollama` 命令，`127.0.0.1:11434` TCP 探测为 `false`。真实 machine task → 用户错误 → correction → retest → restart 未执行，A14 继续 `TESTED_LOCAL_PARTIAL`，M0 继续 `NOT_READY`。

P5 backup manifest integrity（当前 subject：`e793252cd149c23c868c84921ab13ef3c7f31150`）：`verify_backup()` 现在按规范化相对路径拒绝重复 manifest entries，避免重复项伪造 `verified_files == file_count`；定向备份回归 `17 passed`，生产文件 Ruff 和 diff check 通过。测试文件存在未由本卡引入的 `SIM105` lint，未扩大修改范围；Rust SQLite、workspace identity、真实 Legacy diff 与 Green rollback 仍未闭合。

A08/P3 learning tick input boundary（当前 subject：`7793a2c47a010024811994bc4e5bea10c4e19b3a`）：`/api/v1/learning/tick` 现在要求 idempotency key 为非空字符串，拒绝空白或非字符串输入，避免无效请求绕过写意图边界；安全回归 `10 passed`，learning loop E2E `1 passed`，Ruff 与 diff check 通过。该修复只强化输入边界，不等于真实 UI、Mastery/FSRS 全状态重启或 A14 真实模型闭环。

P0 worker lifecycle 增量（当前 subject：`092c71a64c313a31701df5b1dfb41228cb896da6`）：新增 test-only 真实 subprocess 组合测试，使用临时 `PluginManifest` 与 `CapabilityStore` 验证 hello、成功 `text.extract`、输出哈希、失败无输出、disable 阻断、enable 恢复、staging 仅含 input/output 且不创建 `.db/.sqlite`。新卡与相邻 manifest/activator/NDJSON 回归合计 `47 passed, 1 warning, 47 subtests passed`，vNext worker check 与 Ruff 通过；证据级别为 `TESTED_LOCAL_CONTRACT`，正式宿主仍未改写，P0/M0 继续 `PARTIAL/NOT_READY`。

验证记录：P0–P2 提交 `e478aa41`，P3/P5 提交 `c546c0c6`，P4.1/P5.1 提交 `eea865e1`，P3.1 提交 `8dfc78b3`；Python 定向回归 `120 passed, 3 warnings`，P3 桌面契约 `11 passed, 1 warning`，本轮 API Rust 定向回归 `10 passed`，P5 Rust 定向回归 `18 passed`，退出码均为 `0`；完整 workspace Rust gate、rustfmt、完整 .NET 产品门禁仍未执行。未运行完整产品门禁，未宣称 M0 完成或 Local Green 就绪。

## P0–P6 执行队列

### P0 — 先建立最小插件内核

1. 登记 M0 priority overlay，保留 R6 TaskPack 为 immutable base。
2. 收敛 `PluginManifest`、`PluginRegistry`、`CapabilityResolver`、`PluginRunner`、`PluginHealth` 的最小契约。
3. 只支持 Enable、Disable、Default Provider、Fallback Provider、Health Check；不做商城、自动下载或社区插件。
4. 用一个现有本地 worker 做真实注册→启用→执行→失败→禁用→替换 Provider 测试，确保 Canonical 数据不由插件直接写入。

### P1 — 一条默认输入链

1. 选择一个当前已具备的 Parser/worker 作为 M0 默认实现；其他能力只登记为 fallback/benchmark/donor。
2. 保持原件、hash、类型、Parser、版本、Transform、Structure、Anchor、Loss、Quality receipt。
3. 优先补 TXT/MD/PDF text/HTML/图片中的一条真实可运行链，再按相同契约扩展其余 M0 格式；Unsupported/Partial 必须显式。
4. Knowledge V3 的 external、personal、machine_candidate 三类状态必须在同一链路中可区分。

### P2 — General 学习链

1. M0 只保留 `general` Domain Pack；其他 Domain Pack 停止新增深化。
2. 用 Concept、Fact、Procedure、Method、Case 建立最小 KC、Prerequisite、Learning Objective 和 CourseManifest。
3. Search 默认只保留 FTS5 加一个已验证的 Embedding Provider 和一个 Reranker；LightRAG/Graphiti 等延后。
4. 选择一个第一 Renderer，优先验证 H5P 适配；OpenMAIC 只登记，不成为 M0 blocker。

### P3 — 真人学习

实际 UI 必须让用户看到内容、看到问题、输入/点击答案、提交结果；Assessment 由 Core 产生，Rust Core 写 Mastery/FSRS，且 `Mastery != Truth`。必须证明完全退出再启动后 Course、Artifact、Learning Event、Mastery、FSRS 和队列可恢复。

### P4 — Machine Loop

以同一批 Accepted Knowledge 和 Personal Knowledge 执行一个真实任务，写入 Model、Knowledge Versions、Input、Output、Result；人工指出一个真实错误，形成 Correction，再执行 Retest。不得用模型自评或预写 `correct=true` 代替。

### P5 — Persistence / Migration

补齐真实 Backup/Restore 的 DB identity、schema、workspace identity、hash 和 referential integrity；使用非空 Legacy DB 的隔离副本，完成 read-only export、staging import、semantic diff、loss report、restart/readback。不得改原 Legacy 或真实 Green data。

### P6 — Local Green

只有 P0–P5 的真实证据齐全后，才进入 exact-SHA Candidate 全旅程。现有 Green 目录的备份、Runtime 原位替换、启动脚本 readback 和 rollback 是 Owner-gated 操作；在授权前保持 `BLOCKED`，不把候选包当正式 Green。

## 延后清单

### M1：M0 之后

Plugin Marketplace、在线商店、自动下载、多套 RAG、多套 Memory、Graphiti、MemOS、LightRAG 深度集成、DeepTutor/OpenMAIC 全量集成、LearningMAP/OpenTutor、Math/Programming/Design/Language Pack、更多 Renderer、更多研究源和更多模型 Provider。

### M2：M1 之后

3D、VR、AR、高级 Simulation、CAD、多设备同步、多用户协作、云同步、社区插件、自动发现和自动安装。

这些能力保留在 Registry/Roadmap，不从历史文件中删除，也不作为 M0 的完成条件。

## 永久回归门

- `FUB-01`: Import 后真实产生 Job/Transform。
- `FUB-02`: 空 Knowledge 状态可以产生第一份真实 Learning Artifact。
- `FUB-03`: DEV SQLite 不得冒充 Local Green Workspace。
- `FUB-04`: 不得人工预写 `correct=true` 冒充学习闭环。

任一门失败，M0 保持 `NOT_READY`。

## 下一项可执行工作

当前先不新增外部 Provider 或大功能。下一项是用 Owner 允许的真实模型/用户任务替换 P4 合成输入；P3 真实 Avalonia 控件首用仍缺无 UI 入口，P5 workspace identity 仍需 Owner 决策。模型库/Domain Pack 只读审计已确认结构 `PARTIAL`，不得把浅层目录收据或 `contract_only` manifest 当作 executable/runtime 证据。A02 的共享资源根语义、A13/P6 的真实 Green 替换和回滚仍保持 Owner Gate；A15 独立审计已 PASS，A16 仍 BLOCKED。

## A06 增量（2026-09-20）

当前 subject：`14da2ea80dcc0f3a2f928b6f5e29a758f6b325c4`。`DerivedProjectionReceiptV1` 现在拒绝只含空白字符的 `query`，与 Vault 搜索入口的非空白约束保持一致；新增对应 Pydantic 回归测试，并修正同文件的 Ruff 类型注解问题。定向回归 `tests/test_derived_projection_v1.py tests/test_vault_search_api.py` 为 `12 passed`，Ruff 与 `git diff --check` 通过。证据仅为本地契约/搜索边界，不代表向量、重排、图检索、真实 Provider 或 M0 全链路完成。

## A11 增量（2026-09-20）

当前 subject：`f19fea2027259c8d5e8b4475eadea6f1df5b31f5`。`ModelRoleEntryV1` 现在要求 `measured_current` 或 `measured_historical` 条目提供至少一个 `evidence_refs`，防止无证据条目被标记为已测；`unmeasured` 与 `blocked` 仍可保持空引用。模型池定向回归 `5 passed`，Ruff 与 `git diff --check` 通过。证据仅为本地 Pydantic 契约与合成 payload，不代表模型可执行性或角色基准完成。

## A05 增量（2026-09-20）

当前 subject：`dd71d77adba53cd4235a93dc1d61af636ecfc6e5`。`FallbackInfoV1` 现在拒绝 `used=false` 但携带 `reason` 的自相矛盾收据，同时保留未使用状态下记录首选引擎的合法 `attempted_engines`。format receipt 与 workspace 多格式定向回归 `15 passed`，测试文件 Ruff、排除既有 B009/UP037 基线后的生产文件 Ruff 及 `git diff --check` 通过。完整生产文件 Ruff 仍有未由本卡引入的既有 B009/UP037 告警；证据仅为本地 receipt/合成管线，不代表真实外部转换引擎或 M0 完成。

## A08 增量（2026-09-20）

当前 subject：`8e8d33ea41c152f403e83c35aadd6272ae50c64b`。`LearningKernelReceiptV1.source_anchor_ids` 现在要求来源锚点唯一且保留原顺序，防止重复 provenance；learning kernel 定向回归 `5 passed`，Ruff 与 `git diff --check` 通过。证据仅为本地 Pydantic receipt 契约，不代表 Avalonia 首用、权威 Mastery/FSRS 或完整重启读回完成。

## A07 增量（2026-09-20）

当前 subject：`8786d069bd88bbf7f31865453806d5f22d458252`。`MachineGrowthReceiptV1.source_event_ids` 现在要求来源事件唯一且保留原顺序，防止同一增长收据重复绑定来源；machine growth 定向回归 `5 passed`，排除既有 I001/SIM102 基线后的生产文件 Ruff、测试文件 Ruff 与 `git diff --check` 通过。证据仅为本地 Pydantic receipt 契约，不代表真实模型、人工审核、复用或复测闭环完成。

## A10 增量（2026-09-20）

当前 subject：`7a32702769c1be2c825aa3636c510650edb2dce5`。`CoursewareArtifactV1` 现在拒绝 `artifact_id`、`title`、`renderer` 和 `renderer_version` 的全空白值，与来源/知识 ID 的非空白边界保持一致；courseware 定向回归 `11 passed`，Ruff 与 `git diff --check` 通过。证据仅为本地 Pydantic artifact 契约，不代表真实 renderer、Avalonia 首用或领域课程验收完成。

## 本记录限制

本次只调整优先级和执行方向，没有删除历史、没有读取或写入 E/F 盘、没有访问私有 `.codex/.zcode/.hermes`、没有修改外置共享库、真实资料库、测试源资料或现有 Green runtime，也没有创建 tag/release。
