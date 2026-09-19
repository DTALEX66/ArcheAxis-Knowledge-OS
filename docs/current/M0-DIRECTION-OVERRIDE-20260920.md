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
- 当前本地与远端 `main`：`dc5aa97fc1d95f81a3c480901de7807dffd963f2`
- `origin/codex/full-loop-0906`：当前本地 ref 不存在；本记录不把它当作已同步证据。
- R6 状态：`release_status=FROZEN`、`overall_status=IN_PROGRESS`
- R6 既有候选、worker 修复、合成迁移和两次重启证据保留；它们是分段证据，不是完整 M0 闭环。
- `.project-local` 是唯一开发运行/证据输出根；外置共享模型、工具、Green、真实资料库和测试资料库不因 M0 方向改变而迁移或改写。

## P0–P6 映射审计

状态语义：`INHERITED_TESTED` 表示可继承的当前证据；`PARTIAL` 表示存在局部证据但不能覆盖 M0；`MISSING` 表示尚无满足 M0 的证据；`BLOCKED` 表示需要 Owner 或受保护资源；`DEFERRED` 表示明确移到 M1/M2。

| M0 包 | 责任 | 当前判断 | 可继承或缺口 |
| --- | --- | --- | --- |
| P0 | Authority + Plugin Kernel | `PARTIAL` | R6 authority、No-Release 和 capability registry 已有；M0 priority overlay、完整启停/默认/fallback/health/替换闭环尚未证明 |
| P1 | Source + Format + Knowledge | `PARTIAL` | worker 路由、format receipt、Knowledge V3 读投影和 human/machine 权限已有；统一主 Parser/fallback、真实常用格式、V3 写入和三类知识同旅程仍缺 |
| P2 | Search + Learning Plan + Course | `PARTIAL` | FTS5、domain/course/artifact 契约已有；embedding/reranker、General 行为包、KC/Prerequisite/Objective、CourseManifest 与第一 Renderer 的真实运行仍缺 |
| P3 | Human Learning | `PARTIAL` | Core 已按 active accepted/personal Knowledge 生成并持久化 Assessment，review 可绑定答案；真人 UI 首次学习、Mastery/FSRS 全量恢复和完整重启回读仍缺 |
| P4 | Machine Loop | `PARTIAL` | machine task/correction/retest 数据边界和 receipt API 已有；同一 Accepted/Personal Knowledge 的真实任务、真实错误、人工 Correction、Retest 仍缺 |
| P5 | Persistence + Migration | `PARTIAL` | canonical Rust SQLite、合成非空迁移和两次重启身份已有；完整 Backup/Restore 校验、全状态重启回读和真实 Legacy copy 语义 diff 仍缺 |
| P6 | Local Green | `PARTIAL/BLOCKED` | exact-SHA candidate、worker 与 headless smoke 已有；Candidate 全旅程、现有 Green 备份/原位替换/回滚需 Owner Gate，不能提前执行 |

## 2026-09-20 并行执行回读

本轮按独立写集并行完成 P0、P1、P2 的最小可验证切片；它们不等于 M0 全链路完成：

- P0：`TESTED_LOCAL`。现有 capability kernel 的 health、注册/启用、执行、失败、禁用、恢复、同 `plugin_id` provider 替换和不创建 canonical DB 均有回归证据；真实 Python worker 的 manifest/runner/health 绑定仍待后续卡。
- P1：`TESTED_LOCAL`。格式执行保留 attempted engines、fallback 状态和无路径泄露的原因，并在 conversion run 重启回读和 format receipt 中保持一致；真实常用格式质量、外部引擎和 Knowledge V3 写入仍未闭合。
- P2：`TESTED_LOCAL`。新增 general-only CourseManifest、Knowledge Component、Learning Objective 契约，覆盖 Concept/Fact/Procedure/Method/Case、引用闭合、lesson 要求和跨域拒绝；Search 的 embedding/reranker、真实课程内容和 renderer 仍未闭合。
- P3：`PARTIAL`。Core review receipt 现在保存用户提交的 answer，空白回答在 API/UI 被拒绝，并有桌面契约与 Rust restart/readback 回归；Core 尚未从 Accepted Knowledge 产生真实 Assessment/content，客户端仍提交 correct，Mastery/FSRS 全旅程未闭合。
- P5：`PARTIAL`。备份校验现在同时验证 `sources.sha256` 对应的 `.objects` 内容，篡改对象会被拒绝；Rust 测试因当前环境没有 `cargo` 未执行，SQLite workspace identity 仍需冻结。
- P4.1：`IMPLEMENTED_LOCAL / NOT_EXECUTED`。machine task 现在要求 `knowledge_version` 绑定 active accepted/personal Knowledge，`retest_of` 绑定已存在 failed task，并有重启读回测试；真实模型任务运行和 Rust 测试仍未执行。
- P5.1：`IMPLEMENTED_LOCAL / NOT_EXECUTED`。backup/verify 现在拒绝 schema 漂移、外键损坏和源对象 hash 篡改；SQLite `workspace_id` 仍需 Owner/Authority 决策。
- P3.1：`IMPLEMENTED_LOCAL / PARTIAL`。Core-owned Assessment 已按 active accepted/personal Knowledge 生成并持久化，review 可绑定 assessment_id，Avalonia 显示 question/content；Mastery projection、真实 UI/runtime 和 Rust/Dotnet 验证仍未闭合。

验证记录：P0–P2 提交 `e478aa41`，P3/P5 提交 `c546c0c6`，P4.1/P5.1 提交 `eea865e1`，P3.1 提交 `8dfc78b3`；Python 定向回归 `120 passed, 3 warnings`，P3 桌面契约 `7 passed`，退出码均为 `0`；Rust/Rustfmt/Dotnet 为 `NOT_EXECUTED`（缺 `cargo`/`rustfmt`/`dotnet`）。未运行完整产品门禁，未宣称 M0 完成或 Local Green 就绪。

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

当前先不新增外部 Provider 或大功能。下一项应从 P3 人类学习的真实首用路径开始，接入已有 Core Assessment/review/FSRS 和 restart readback；随后再补 P4 真实 machine correction/retest 与 P5 backup/restore 校验。模型库/Domain Pack 只读审计已确认结构 `PARTIAL`，不得把浅层目录收据或 `contract_only` manifest 当作 executable/runtime 证据。A02 的共享资源根语义仍需 Owner 决策，A13/P6 的真实 Green 替换和回滚仍保持 Owner Gate，A15 仍必须独立审计。

## 本记录限制

本次只调整优先级和执行方向，没有删除历史、没有读取或写入 E/F 盘、没有访问私有 `.codex/.zcode/.hermes`、没有修改外置共享库、真实资料库、测试源资料或现有 Green runtime，也没有创建 tag/release。
