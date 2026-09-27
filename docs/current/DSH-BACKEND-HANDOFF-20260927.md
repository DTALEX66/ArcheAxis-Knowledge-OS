# DSH 后端任务交接报告 — 2026-09-27

> **用途与边界：** 供 DSH 接续后端工作及核验旧 DP 交付。本报告是当前可见资料的交接摘要，不是 A15 独立审计，不是 DSH 所有任务的结项证明，不改变 R6/A00–A16 状态，也不授权实现尚未冻结的 API、资源路径或产品语义。
>
> **证据分层：** 下文将当前可读源码/契约、R6 台账状态、历史 DSH 分支报告及当前回合重新执行的检查分开记录。历史报告里的测试结果均标成“报告所载”；除明确写明外，本回合没有重新执行测试。静态/文档证据不能替代真实资料、真实模型、GUI、Clean Machine、CI 或 Owner Gate。

## 1. 当前基线与审计范围

| 项目 | 当前核对结果 |
|---|---|
| 仓库 | `D:\All projects\ArcheAxis-Knowledge-OS` |
| 当前 HEAD | `666d01b3bd1e14b9193e125593f44d282dfef524`；tree `2a5ee19bea2e5e6282ca0875529da545425e6dec`；提交日期 2026-09-27（本回合读取） |
| 分支/远端 | 本回合未读取分支、fetch/push 远端状态；不得从历史 DSH worktree 名称推断当前分支或发布状态。 |
| 工作区 | 修改前 `git status --short` 显示大量既存未跟踪历史/证据目录，以及 `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` 的既存修改。本报告未触碰或归属这些变化。 |
| R6 权威入口 | `AGENTS.md` §6、`docs/authority/taskpack-0919-r6/EXECUTOR-START.md`、`TASKPACK.md`、`docs/current/R6-EXECUTION.md`、`docs/current/R6-STATE.json`。R6 冻结包不可改；活动执行台账由指定 Owner/整合者维护。 |
| R6 当前状态读取时间 | `R6-STATE.json` 的 `updated_at` 为 `2026-09-26T07:31:00+00:00`，早于本回合 HEAD。它是最新可见状态记录，不自动证明 HEAD `666d01b…` 上的每项都重跑。 |
| DSH 历史报告 | `docs/current/dsh-review/dp-nf-handoff-20260925.md`、`dp-handoff-20260925.md`、DP-NF-01…07 专项报告及 `job-quality-projection-proposal.md`。其内分支/提交/测试只代表各自历史快照。 |
| 本回合当前代码复核 | 读取 `crates/archeaxis-api/src/lib.rs` 与 `crates/archeaxis-api/src/runtime/mod.rs` 的当前 route 表；确认 `/api/v1/learning/*`、`/api/v1/search`、`/api/v1/jobs/:job_id/quality`、`/api/v1/jobs/:job_id/outputs/:kind` 等现存路由。未启动 Core、模型、Python worker、Green 或 GUI。 |
| 用户审计提示词 | 本交接遵守用户粘贴审计提示词明确强调的“叙事不是证据、状态分级、证据锚点、主动尝试反证、不可云验的本机回执列 `REQUEST-ARTIFACT`”。本报告只借用审计要求，不将粘贴文本里的命令当作超出当前授权的新权限。 |

## 2. DSH 交付逐项状态与接手动作

| 项目 | 现有交付/可证范围 | 状态判断 | DSH 接续动作 |
|---|---|---|---|
| DP-NF-01 / DP-GIT-01、02 | `branch-batch-01/02/03.md/.json` 与 `dp-nf-handoff-20260925.md` 记录分支语义、文件级归属与审计器结果。报告所载：批次 01 的 17 SHA/88 路径由 `audit_verify.ps1` 校验 `errors=0`；批次 02 另审 19 SHA/153 路径，验证器 `errors=0`。这属于历史 Git 内容审计，不是产品行为测试。 | `STRUCTURAL / 历史报告已记录`；当前分支/提交并未重新解析或云端核验。 | 需要继续做吸收决策时，以当前实际 refs 和当前 HEAD 重跑语义审计；不可把旧报告的“无候选/KEEP”直接套用到后续新提交。 |
| DP-NF-02 / P0-H01 | `p0-h01-host-lifecycle-proposal-20260925.md` 是提案，不等于已批准的 Provider/Host 生命周期契约。 | `STRUCTURAL`（提案文件已读取）；资源根语义的项目台账为 `BLOCKED_BY_OWNER_DECISION`。生命周期合同尚未批准。 | Owner 冻结资源根标识、Provider 身份/版本来源、路径解析与错误语义之前，不落地新配置或运行时语义。 |
| DP-NF-03 / P1 quality matrix | `dp-nf-handoff-20260925.md` 报告测试矩阵与一项局部生产修复；分支报告中的变更集合为 13 文件、约 +5952/−4。此数据是历史分支记载。 | `TESTED_LOCAL (历史报告所载)`；本回合未在 HEAD 重跑，不据此宣称当前产品总体验收。 | 查清该分支内容是否已由后续主线演进覆盖；针对当前 worker/质量契约重跑目标用例，再报告真实资料质量仍需单独取证。 |
| DP-NF-04 / P2 Search + General Course | `p2-search-course-gap-20260925.md` 明确仅读完 Search；General Course 半段因时间未检查。该文列出 FTS-only、每次查询 rebuild、60 字符片段、不暴露 calibrated score；引用测试是他人在独立 worktree 报告的 1 条，并非作者重跑。 | `TESTED_LOCAL_PARTIAL` 仅作为旧报告记载；本回合 `NOT_EXECUTED` 当前 HEAD 复跑。Search 描述仍是历史静态分析。 | 完成 CourseManifest 与课程执行契约审计；在当前 HEAD 重新运行 search/course 测试；不要把 FTS 结果描述为向量、混合检索、图检索或相关性质量。 |
| DP-NF-05 / machine-loop restart test | `dp-nf-handoff-20260925.md` 记录增加 `crates/archeaxis-domain/tests/machine_loop_restart.rs`，并记载当时执行 `--workspace` 及其他套件的覆盖情况；测试针对文件身份/来源内容变化与重启边界。 | `TESTED_LOCAL (历史回执摘要)`；真实模型与真实用户流程未由该合成/集成测试证明。 | 在当前 HEAD 查该测试仍存在并重新执行目标与相邻 Rust 测试；区分 fixture/合成重启和真实模型、人审纠错再测。 |
| DP-NF-06 / P5 backup、P6 Candidate | `p5-backup-dirty-diff-review-20260925.md` 和 `p6-current13-candidate-readback-20260925.md` 为审阅/候选回读记录。旧交接明确 P5 没有对被审 dirty files 跑 `cargo test/check/fmt`；P6 的 `--require-current-source` 复核 `ok=false`，按原报告记为 `NOT_EXECUTED`，非 Candidate 缺陷。 | `STRUCTURAL`（历史审阅材料）；当前等价回执 `REQUEST-ARTIFACT`，本回合 `NOT_EXECUTED`；不算后端实现已验证。 | 若当前任务还依赖该审阅，先取目标 SHA、工作树快照、审计器 stdout/stderr、退出码与 manifests；之后只对明确允许范围运行测试。不要将“test exists”写成通过。 |
| DP-NF-07 / repository language-data gap | `september-repo-language-data-gap-20260925.md` 是旧报告/归属审计，特别声明若干 root/Codex lineage 文件不能归因于 DSH。 | `STRUCTURAL / 历史审计`；本次不重分配这些未跟踪文件。 | 维护者按当前 Git lineage 重新判定归属；DSH 不清理报告列出的残留或未知目录。 |
| DP-A11 / Research contract gap | `research-contract-gap.md` 明确是只读提案，指出派生投影缺 `source_revision`、Research runtime route 缺失、Provider 版本身份未建模，并建议 FTS-scoped projection；列 5 项 Owner 决策。 | `STRUCTURAL`（提案与当前 route 表已读取）；Research 合同仍待 Owner 决策，未实现的历史判断未在本回合做全仓反证。 | 先获得 Research 能力边界、Provider 身份/版本和派生投影 source revision 的 Owner 决定，再冻结 DTO 与路由；默认 unavailable，不可用伪结果填充。 |
| DP-F01 / real text quality roundtrip | `dp-handoff-20260925.md` 记录新增 8 个测试/fixture 文件、没有生产文件变更；Rust/Python 测试与邻接测试均为受控 synthetic fixtures。其修正记录确认 worker 原文件与当时 baseline 字节相同，因此没有被证明的生产缺陷。 | `TESTED_LOCAL (历史合成 fixture)`；真实 corpus/格式质量未验证。 | 从当前 HEAD 复跑 F01 Python/Rust 与邻接测试；若扩展，使用批准的真实资料并记录脱敏/来源/哈希/结果，不能用 fixture 代称真实资料。 |
| DP-F01 / quality projection follow-up | `job-quality-projection-proposal.md` 明确 `PROPOSAL / OWNER REVIEW REQUIRED`，非实现授权。当前 route 表有 `/api/v1/jobs/:job_id/quality` 及 `/api/v1/jobs/:job_id/outputs/:kind`；Proposal 描述完整 `loss_report` 可经通用输出路由读取，但 `content` 是 JSON string；`/quality` 只投影汇总、不返回 `params`/`losses`。 | `STRUCTURAL / OWNER DECISION REQUIRED`。本回合仅核当前路由存在，不重测运行返回体。 | Owner 决定采用新 typed `/receipt` 还是扩展 `/quality`；决定 schema validate、无 receipt 语义、attempt 读取、fallback/unsupported 字段边界（proposal D1–D5）。批准前不改 Rust route/schema。 |
| DP-UI-01 | `dp-ui-01-readiness.md` 报告当前 Candidate 未提供，所以 GUI acceptance matrix 未执行；不得拿旧 Candidate/脏二进制替代。 | `NOT_EXECUTED`（GUI acceptance 未执行）；候选缺失仅为历史 readiness 报告记载。 | 由 UI 任务提供精确当前源码 Candidate、manifest/source snapshot/EXE/DLL 哈希和独立数据根后再做 GUI 验收；与本后端交接分开，不把 GUI blocker 记为后端通过。 |

## 2.1 独立审计判定（本回合）

判定标签表示对报告主张的审计结论；项目状态仍只使用 R6 已定义状态。审计范围是报告文档、R6 当前可读记录与当前 API 路由声明，不是对全部历史分支和产品行为的重做。

| 被审主张 | 判定 | 可见证据 | 残余不确定性 |
|---|---|---|---|
| R6 状态时间早于当前 HEAD，不能证明 HEAD 上所有任务已重跑 | `CONFIRMED` | `docs/current/R6-STATE.json` 的 `updated_at=2026-09-26T07:31:00+00:00`；本报告记录 HEAD `666d01b3bd1e14b9193e125593f44d282dfef524` 日期为 2026-09-27 | 未读取所有 refs/CI，不能据此判断具体提交吸收情况 |
| 当前 API 声明 learning/search/job-quality/workspace 路由 | `CONFIRMED`（结构层） | `crates/archeaxis-api/src/lib.rs:63-74`；job execution/output 路由见 `crates/archeaxis-api/src/runtime/mod.rs:30-42` | 只确认源码声明；未启动 Router/Core，未校验 DTO、状态码、错误体及端到端语义 |
| DP-F01、DP-NF-03、DP-NF-05 的历史摘要证明当前 HEAD 测试通过 | `UNVERIFIED` | 报告明确将这些结果标为历史回执；本回合没有相同 SHA 的测试运行 | 需 DSH 在当前 HEAD 重新运行并保存命令、环境、退出码和 summary |
| 所有历史 DSH commits 已吸收到当前 HEAD | `UNVERIFIED` | 本回合未读取当前分支/远端，也未建立完整 commit ancestry/path 表 | 需要实际 refs、纳入 SHAs 与当前 HEAD 的图/路径审计 |
| R6/A02、A16 等状态和冻结边界 | `CONFIRMED`（台账记录层） | 当前可读 `R6-STATE.json` 与根 `AGENTS.md` §6；二者分别提供状态值与冻结/发布边界 | 状态 JSON 晚于/早于具体代码变更的关系仍须按 subject SHA 复核；本报告不代替台账 Owner 更新 |
| GUI、真实语料、真实模型和当前 Green 候选已验收 | `REFUTED`（就“本回合已完成”这一可能推断而言） | 本回合明确未运行 GUI、真实素材/模型、Candidate 或 Green；历史 readiness 也将 GUI 标为未执行 | 不推断其他独立会话或机器没有相关证据；该证据须按 exact artifact 提供 |

## 3. R6 当前后端相关未闭合项

`docs/current/R6-STATE.json`（更新时间 2026-09-26 UTC）把 R6 整体保持在进行中，A16 为 `BLOCKED_BY_OWNER_DECISION`，并明确 release `FROZEN`。以下摘要按该状态文件记录，不推断它已在 2026-09-27 HEAD 重跑：

- **A02 — 资源/路径/环境权威：** `BLOCKED_BY_OWNER_DECISION`。需要为外部资源根、shared Model library 与 plugins 冻结 schema/resolver 语义。不得通过放宽 containment 或伪造插件条目消除偏差。
- **A04 — Knowledge/Source V3：** `TESTED_LOCAL_PARTIAL`。状态记录称 Rust canonical write、sidecar persistence、projection/revision inheritance 已有本地测试；桌面经 UI 的 Core 重启和真实 first-use journey 未闭合。
- **A05 — 多格式：** `TESTED_LOCAL_PARTIAL`。记录称启用 builtin converters 并提供显式 path-free fallback receipt；语义质量、动态渲染、外部转换引擎和代表性真实 fixture 仍未核验。
- **A06 — Retrieval/Graph/Research：** `TESTED_LOCAL_PARTIAL`。有词法搜索派生回执和 source/revision binding；vector/reranker/graph/research、Provider readback 与 benchmark 仍缺。
- **A07/A08/A09/A10/A11/A14：** 台账均仍为 `TESTED_LOCAL_PARTIAL`。已记录的本地/合成证据不能闭合真实模型执行、真实领域内容、自适应学习、完整人机纠错再测与 Owner 定义的 Mastery（A08 的 `closed=false` 明示仍未闭合）。
- **A12/A13：** Avalonia/Candidate 证据虽增加，台账仍标 partial；当前重建 DLL 的 UIA 路由/交互矩阵仍需重播；不能把先前 DLL 的 UIA 结果移植到新 DLL。Green replace/restart/rollback 仍受 Owner Gate 约束，本交接不操作 Green。
- **A15/A16：** A15 为 `TESTED_LOCAL_PARTIAL`，历史独立审计有其自身 subject SHA；G01–G14 尚有 real formats/quality、model、Legacy、GUI/clean-machine、runtime-directory 与 release 等缺证。A16 仍阻塞；不可签发 Release 或完整闭环结论。

## 4. 给 UI 的后端对接合同（现存与待决分开）

### 当前可从代码路由表确认的接口（仅结构确认）

当前 `crates/archeaxis-api/src/lib.rs:63-74` 声明：

- `POST /api/v1/imports`、`POST /api/v1/jobs`；
- `POST /api/v1/sources/:source_id/anchors`、`GET /api/v1/evidence/anchors`；
- `GET /api/v1/sources/:source_id/jobs`、`GET /api/v1/sources/:source_id/jobs/:job_id/transform`、`GET /api/v1/sources/:source_id/members`；
- `POST /api/v1/knowledge-items`、`POST /api/v1/knowledge-items/from-transform`、`GET /api/v1/knowledge-items/:id/v3`、`GET /api/v1/knowledge-items/:id/qualification`；
- `POST /api/v1/learning/events`、`POST /api/v1/learning/reviews`、`GET /api/v1/learning/events/:item_key`、`GET /api/v1/learning/items`、`POST /api/v1/learning/items/:item_key/references`、`GET|POST /api/v1/learning/items/:item_key/assessment`、`GET /api/v1/learning/items/:item_key/state`；
- `POST /api/v1/machine/tasks`、`GET /api/v1/machine/tasks/:task_id`、`GET /api/v1/search`、`GET /api/v1/jobs/:job_id/quality`、`GET /api/v1/workspaces/info`。

当前 `crates/archeaxis-api/src/runtime/mod.rs:30-42` 另声明 `GET /api/v1/jobs/:job_id`、`POST /api/v1/jobs/:job_id/executions`、`GET /api/v1/jobs/:job_id/outputs/:kind`；通用 outputs 的完整返回语义见 F01 提案，仍需以当前运行读取验证。列出路由不代表 API 全流程已经运行验证。

### 已识别但尚待决策的 UI 缺口

1. **质量详情：** `/quality` 是汇总投影；UI 若要展示 decode、format facts 与 losses，需要采用 Owner 冻结后的 typed contract。不能前端解析双层 JSON 并自创 `fallback=true`。
2. **Search/Research：** 现有 `/search` 不等于 embeddings/reranking/graph/research。UI 应呈现能力实际可用状态和结果来源；Research route/Provider/version 未冻结前需显示明确 unavailable/未接通状态。
3. **Source/Evidence：** UI 必须保留稳定 `source_id`、revision/hash 和 anchor 引用，区分 Source、Evidence/Original 与派生 Knowledge；不得以 Memory Graph 边代替来源链。
4. **Learning/FSRS：** 使用稳定 `item_key`、assessment/event ID、幂等事件键、due/schedule/readback 的现存合同。新 Mastery 字段、跨产品 Human Learning Kernel 闭环不得由 UI 猜造。
5. **多格式导入：** fallback 和语义保真只能显示回执中实际存在的 facts；未经真实 fixture 验证的格式不可显示为质量已保证。
6. **Model/Plugin/路径：** A02/P0-H01 Owner 决策前，UI 不呈现虚构 provider、模型版本、插件激活或成功状态。
7. **错误与离线：** 各 API 的空/404/不可用/冲突/重试语义，应由冻结契约逐条规定；当前表只确认路径存在，不替代 error-code DTO 审计。

以上“待决”项是交接缺口，不是已锁定的新 API 契约。变更需先走当前任务授权和项目写入边界。

## 5. DSH 可执行下一步

1. **固定审计基线：** 读取当前 `git status --short`、HEAD、实际 refs；只对明确纳入的 DSH 提交建立 commit/tree/path 表。对现有脏文件保持不认领。
2. **校正历史交接：** 按当前主线核 DP-NF-01…07、DP-F01 的 commit ancestry/path 状态；标记已吸收、被后续实现取代、仍未吸收和无法判定项。历史分支报告本身不能证明已经合入当前 HEAD。
3. **重跑可复现的后端门禁：** 从 `scripts/runtime/dev.py` 声明的隔离运行目录执行最小针对集：DP-F01 Python+Rust 与邻接测试；DP-NF-03 quality matrix；DP-NF-05 machine-loop restart/domain；P2 search 与 General Course。记录 exact command、interpreter/toolchain、HEAD/dirty state、exit code、完整 summary、receipt path。遇到依赖缺失标 `NOT_EXECUTED/BLOCKED`，不安装全局依赖、不降低断言。
4. **请求 Owner 只决定确实互斥的语义：** A02 resource-root/schema；P0-H01 Provider/host 生命周期；DP-F01 proposal D1–D5；Research/source revision 与结果状态。每项给出上下文、选项与兼容影响；决策前保持 Proposal。
5. **真实能力取证：** 分别安排获准的真实文档格式 corpus、真实模型/Provider、学习人审纠错再测、同数据库进程重启回读。每份证据记录输入身份、受控路径、哈希、命令/版本、输出及人工判定；fixture、synthetic UIA 与结构测试单列。
6. **回填状态：** 只由台账指定整合者按 R6 规则维护 `R6-EXECUTION.md`/`R6-STATE.json`；不得改冻结 TaskPack，不得把本交接直接登记成状态升级。
7. **前端接口协调：** 对每个 UI 使用动作给出冻结的 operation/method+route、DTO/schema、稳定 ID/revision、状态/时间字段、empty/error/conflict/retry 语义和可重复验收；新建议明确标注 `PROPOSAL` 并指定 Owner。

## 6. 测试、运行证据与未执行项

### 历史 DSH 报告所载结果（未在本回合重跑）

- DP-F01 Python：`tests\workers\test_f01_real_quality.py`，报告称 `5 passed, 1 warning, exit 0`；邻接 Python lane `58 passed, 1 warning, 77 subtests, exit 0`。
- DP-F01 Rust：`scripts\ci\cargo_test.bat test -p archeaxis-api --test f01_quality_roundtrip --offline -- --test-threads=1`，报告称 `5 passed, 0 failed, exit 0`；邻接 Rust lane `13 passed, 0 failed, exit 0`。
- DP-F01 全 `tests/workers`：报告称 `117 passed, 7 skipped, 2 failed, 5 errors`，并归因于环境缺失依赖/ASR model。它是失败运行，不能计为 PASS；依赖归因也应在 DSH 重跑时逐项核实。
- DP-NF-01/02/04/07 与 DP-A11：历史报告注明审计/提案用途，没有测试运行。
- DP-NF-05、DP-NF-06：具体运行范围/限制见 `dp-nf-handoff-20260925.md`；任何没有 stdout、退出码和对应 SHA 的旧摘要均只视作二手记录。
- DP-UI-01：历史 report 标 `BLOCKED/NOT_EXECUTED`，无 GUI run。

### 本回合实际执行

- 读取根 `AGENTS.md`、R6 Executor Start、R6 当前台账/状态、DSH handoff/proposal、当前 Rust route 表；记录当前 HEAD 与修改前 Git status。
- 对有关未修改 R6 文件执行 `git diff --check -- docs/current/R6-EXECUTION.md docs/current/R6-STATE.json`：exit 0（该命令只覆盖这两个文件，不是全仓检查）。
- **未执行** pytest、Cargo、.NET、Worker、Core runtime、真实素材/模型、GUI/UIA、Candidate、CI、Green 或 Release 验收。

## 7. REQUEST-ARTIFACT / 需补齐证据

以下证据未由本回合读取；DSH 如果要据此签发更强结论，需提供项目内可追溯的本机 artifact 或重新执行并保存回执：

| ID | 所需 artifact | 最低字段 |
|---|---|---|
| RA-01 | DP-NF-01/02/04/05/06/07 目标 worktree/分支最终 readback | branch/ref、baseline/head/tree SHA、status、具体 changed paths、命令/stdout/stderr/exit code；若不存在则 `NOT_AVAILABLE` |
| RA-02 | DP-F01 Python/Rust 的原始运行回执 | 当前被测 SHA、解释器/工具链、完整命令、exit code、测试 summary、warnings/errors、被测 fixture 路径与 hashes |
| RA-03 | DP-NF-03 与 DP-NF-05 当前复跑回执 | exact test target、HEAD、环境与隔离目录、失败/跳过项、数据库或 fixture 身份 |
| RA-04 | A04/A08/A14 当前真实 first-use 与重启 readback | Core/Desktop 版本与哈希、隔离 DB 路径身份、source/knowledge/assessment/event/task IDs、重启前后 readback、幂等键、FSRS schedule；敏感真实正文不进入普通日志 |
| RA-05 | A05 代表性真实文件质量回执 | 获准输入路径/文件 hash、格式、engine/version、attempts/fallback、loss receipt、结构/语义人工判断；synthetic fixtures 单独分栏 |
| RA-06 | A06 Research/Provider/vector/rerank 运行证据 | Frozen contract/version、provider identity/version、配置来源（不暴露密钥）、输入/来源修订、结果数/empty/error、benchmark 方案与原始回执 |
| RA-07 | A13 Candidate/当前源码与 GUI | manifest/source snapshot/executable hashes、isolated data root、Candidate verifier stdout/exit、当前 DLL 对应的 UIA 路由/键盘/DPI/缩放截图回执；旧 DLL 证据不迁移 |
| RA-08 | 外部 CI/远端状态（若报告提及） | 精确 repository、run ID/URL、tested SHA、job/gate、结论及时间。当前会话未查询远端，因此远端状态为 `UNKNOWN` |

不要附 `.env`、token、cookie、私钥、credential、原始 session/memory 或未批准用户资料。缺 artifact 记 `REQUEST-ARTIFACT`，不要将 UNKNOWN 变成 0 或成功。

## 8. 恢复与结论

- 本文是单个新增报告文件，不更改源码、合同、TaskPack、R6 当前执行台账或状态 JSON。若文档内容需撤回，可在目标文件级恢复本次新增前状态（本文件原先不存在）；不要用批量 restore/clean 触碰其它脏文件。
- **总体结论：** `STRUCTURAL`。本回合完成文档、台账与源码路由的结构核验；未做全量分支合并核验、未重跑后端测试，也未运行产品/GUI/真实数据闭环。历史 DSH 结果仍是二手本地运行报告，不升级为当前 SHA 的 `TESTED_LOCAL`。
- **证据级别：** 当前路由与状态文件为本地源码/文档读取（`STRUCTURAL`）；历史 DP 测试为二手本地运行报告；本回合唯一命令级检查为限定文件的 `git diff --check` exit 0。没有 `CI_VERIFIED_EXACT_SHA`、`REAL`、`GUI_ACCEPTED`、`MERGED_MAIN`、`INSTALLED_RUNTIME_VERIFIED` 的新证据。
- **主要未决项：** A02 与 P0-H01 需 Owner 决策；typed loss receipt 与 Research DTO 需冻结契约；真实格式/模型/学习闭环/当前 DLL UIA/Green gate 证据不足；历史 DSH commit 是否都已由当前 HEAD 吸收尚未逐项验证。

---

## 9. DSH 复核审计（追加于 2026-09-27，exact SHA `666d01b3bd1e14b9193e125593f44d282dfef524`）

本节由 DSH 在后端执行提示词下追加。它**不改写**上文任何内容；上文的主张一律先当**主张**处理，下面只写本回合实测到的结果。
本回合**未**执行 commit / push / merge / release，未修改源码、合同、TaskPack、`R6-EXECUTION.md` 或 `R6-STATE.json`。

### 9.1 基线身份（复核上文 §1）

| 项 | 实测 |
| --- | --- |
| HEAD | `666d01b3bd1e14b9193e125593f44d282dfef524` |
| tree | `2a5ee19bea2e5e6282ca0875529da545425e6dec`（与上文一致） |
| committer date | `2026-09-27T00:05:33+08:00`（上文"提交日期 2026-09-27"成立） |
| 远端引用（本回合已读） | `refs/heads/main` = `refs/heads/codex/aaos-p3-ui-convergence-20260922` = `666d01b3…` |
| dirty/untracked | `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`（M），加上既有未跟踪历史目录，以及本交接自身两个未跟踪文件 `docs/current/DSH-BACKEND-HANDOFF-20260927.md`、`docs/current/DSH-BACKEND-EXECUTION-PROMPT-20260927.md`。本回合未认领、未清理任何一项。 |

**上文 §1 声称的引用路径全部存在**（已逐一 `Test-Path`）：`docs/current/dsh-review/` 下 17 个文件（含
`branch-batch-01/02/03.md|json`）、`dp-nf-handoff-20260925.md`、`dp-handoff-20260925.md`、
`p0-h01-host-lifecycle-proposal-20260925.md`、`p2-search-course-gap-20260925.md`、
`p5-backup-dirty-diff-review-20260925.md`、`p6-current13-candidate-readback-20260925.md`、
`september-repo-language-data-gap-20260925.md`、`research-contract-gap.md`、`dp-ui-01-readiness.md`、
`job-quality-projection-proposal.md`，以及 `crates/archeaxis-api/src/runtime/mod.rs`、
`tests/workers/test_f01_real_quality.py`、`crates/archeaxis-api/tests/f01_quality_roundtrip.rs`、
`crates/archeaxis-domain/tests/machine_loop_restart.rs`。上文不是凭空引用。

**一处行号引用不精确（PARTIAL）。** 上文 §4 称路由声明位于 `crates/archeaxis-api/src/lib.rs:63-74`
并据此列出 `/imports`、`/jobs`、anchors、sources 等路由。实测该文件的路由块从 **第 47 行**开始
（`/api/v1/system/version`），到 **第 74 行**结束；`63-74` 实际只覆盖最后一段，起始是
`/api/v1/learning/items`。被列入 `63-74` 的 `/imports`、`/jobs`、`/sources/*`、`/evidence/anchors`
位于 **47–59**。路由确实存在，但该行号区间不足以支撑上文的列举。`runtime/mod.rs:30-42` 与实测一致
（路由在 30–36）。

### 9.2 历史交付是否已被当前 HEAD 吸收（上文 §5 第 2 步）

用 `git cat-file -e HEAD:<path>` 判存在、`git log --diff-filter=A` 取引入提交；`git log` 只走 HEAD 祖先，
故被列出的引入提交**必然**是 HEAD 祖先（并另以 `git merge-base --is-ancestor` 复核）。

| 交付物路径 | HEAD 上存在 | 引入提交 | 判定 |
| --- | --- | --- | --- |
| `crates/archeaxis-domain/tests/machine_loop_restart.rs` | 是 | `5bb89aa7` 2026-09-26 `Integrate audited DP-NF task pack` | **已吸收** |
| `tests/workers/test_p1_quality_matrix.py` | 是 | `5bb89aa7` 2026-09-26 | **已吸收** |
| `tests/workers/test_f01_real_quality.py` | 是 | `d5f026ee` 2026-09-25 `test(f01): real text quality roundtrip …` | **已吸收** |
| `crates/archeaxis-api/tests/f01_quality_roundtrip.rs` | 是 | `d5f026ee` 2026-09-25 | **已吸收** |

`5bb89aa7` 与 `d5f026ee` 均经 `git merge-base --is-ancestor <sha> HEAD` 判定为 HEAD 祖先（exit 0）。
因此对上文"历史 DSH commit 是否都已吸收尚未逐项验证"这一未决项，**在路径层**本回合给出部分结论：
上述四个 DP-NF/DP-F01 交付物确已吸收。**不等于**"全部历史 DSH commit 已吸收"——未建立完整
commit/path 表，其余 DP 项的交付路径未逐一比对。

### 9.3 当前 HEAD 复跑回执（上文 §5 第 3 步、§6）

环境身份（所有 Python 目标共用）：interpreter `.venv\Scripts\python.exe` = **Python 3.13.14**；
`-p no:cacheprovider`；cwd = 仓库根；HEAD/dirty 同 §9.1；未安装任何全局依赖，未降低断言。

| 目标（exact command 前缀 `python -B -m pytest <target> -q --tb=line -p no:cacheprovider`） | 结果 | exit |
| --- | --- | --- |
| `tests/workers/test_f01_real_quality.py` | **5 passed**, 1 warning | 0 |
| `tests/workers/test_p1_quality_matrix.py` | **11 passed**, 2 subtests | 0 |
| `tests/workers/test_quality_regressions.py` | **15 passed**, 30 subtests | 0 |
| `tests/test_vault_search_api.py` | **7 passed** | 0 |
| `tests/test_general_learning_contract.py` | **6 passed** | 0 |
| `tests/test_courseware_v1.py` | **11 passed** | 0 |
| `tests/test_general_courseware_renderer.py` | **8 passed** | 0 |
| `tests/workers`（整目录） | **135 passed, 7 skipped, 0 failed, 0 errors, 97 subtests**, 16.64s | 0 |

**对上文的一处实质更正。** 上文 §6 记 DP-F01 全 `tests/workers` 为
`117 passed, 7 skipped, 2 failed, 5 errors`，并归因于环境缺依赖/ASR model。在**当前 HEAD** 上同一目录实测
`135 passed, 7 skipped, 0 failed, 0 errors`：通过的用例 +18，**2 个 failure 与 5 个 error 均未复现**。
上文自己已写明"依赖归因也应在 DSH 重跑时逐项核实"——本回合核实结果为：**该失败记录不适用于当前 HEAD**，
它至少不是当前源码的缺陷证据。本回合无法从现有材料判定差异来自环境补齐还是测试演进，故不给出归因，
只记录"历史失败未复现"。

DP-F01 Python 的历史回执（`5 passed, 1 warning, exit 0`）与本次实测**逐字一致**，该条可判 `CONFIRMED`。

### 9.4 Rust 目标：本机仍不可编译（`NOT_EXECUTED`，非产品缺陷）

```
$env:CARGO_HOME=<repo>/.project-local/cache/cargo
$env:CARGO_TARGET_DIR=<repo>/.project-local/build/cargo
PATH+=D:\All projects\OS External Configuration\toolchains\rust\cargo\bin
cargo test -p archeaxis-domain --test machine_loop_restart --offline
```

- `cargo` 在**已登记工具链** `D:\All projects\OS External Configuration\toolchains\rust\cargo\bin` 找到；
  `--offline` 依赖解析成功（CARGO_HOME 缓存可用），随后编译失败：
  **`error: linker link.exe not found`**，exit **101**。
- 追因：`vswhere.exe` 可执行，但查询 `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` **未返回任何安装路径**；
  在注册工具链根与常见 VS 安装根做有界搜索**未找到任何 `link.exe`**。MSVC 链接器在本机缺失。
- 判定：DP-NF-05 / DP-F01 的 Rust 目标 **`NOT_EXECUTED`（blocked: MSVC linker absent）**。这与上文
  "sandbox 缺 `link.exe`"的说法一致，**不是**产品缺陷，也**不**因失败而记作 FAIL。

**可转移的 CI 证据（严格限定条件）。** 已读 run
[36251109714](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36251109714) 在
`ea2c3831d9a46ae83fcf8199bc9ccf65da54e598` 的结论：`rust-vnext` **success**（同一 run 的
`test (3.12)` / `lint` / `wheel-smoke` 亦 success）。且
`git diff --name-only ea2c3831..HEAD -- crates/ Cargo.toml Cargo.lock` **为空**，即从该 SHA 到 HEAD
没有任何 Rust/Cargo 源码改动（HEAD 相对该 SHA 只改了 `app/workspace/migrate.py`、`R6-EXECUTION.md`、
4 个 `scripts/probes/*` 与 1 个 `tests/*`）。因此在**源码身份层**，那次 `rust-vnext` 结论覆盖 HEAD 的
Rust 源码。**但**：HEAD 自身的 run 里 `rust-vnext` 被 GatePlan **skipped**，所以这**不是** HEAD 的
exact-SHA Rust 验证，不得记为 `CI_VERIFIED_EXACT_SHA`。

### 9.5 本回合补齐 `RA-08`（远端/CI 状态）

上文 §7 记 `RA-08` 为"当前会话未查询远端，因此远端状态为 `UNKNOWN`"。本回合**已读**远端引用与 run：

| 项 | 实测 |
| --- | --- |
| `refs/heads/main` | `666d01b3bd1e14b9193e125593f44d282dfef524` |
| `refs/heads/codex/aaos-p3-ui-convergence-20260922` | 同上（与 main 同 SHA） |
| main 在该 SHA 的 run | [36254292169](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36254292169) **success**；`a0-gates`/`gateplan`/`lint` success，其余由 GatePlan skipped |
| `ea2c3831` 的 main run | [36251109714](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36251109714) **success**，含 `rust-vnext`/`wheel-smoke`/`test (3.12)` |

`RA-08` 由 `UNKNOWN` 降为"部分已核验"；仍未核验的是本机无法读取的 job **日志正文**——匿名访问
`GET /repos/.../actions/jobs/<id>/logs` 返回 **403**（需 admin），本回合的 run 结论来自 step 级元数据。

### 9.6 本回合**未**验证的（诚实边界）

- 真实语料格式质量、真实模型/Provider 执行、GUI/UIA、当前 DLL 路由复播、Candidate 验收、Clean Machine、
  Green 安装/替换/回滚、Release/tag：一律**未执行**。
- 上文 §2 的 DP-NF-01/02/04/06/07、DP-A11 交付的**内容级**审计：本回合只做了路径存在性与引入提交核对，
  未复核其分支语义、提案内容或声明范围。
- 未建立完整"全部历史 DSH commit → 当前 HEAD"吸收表；仅覆盖 §9.2 四个路径。
- 未读 `docs/current/dsh-review/` 各报告正文（只读取了上文对它们的转述与路径），因此上文对它们的
  **转述准确性**尚未逐条核对。

### 9.7 与本次追加相关的操作事实

- 本节是**追加**；上文 §8"总体结论 `STRUCTURAL`"对本回合仍然成立，本回合把其中若干项从
  `NOT_EXECUTED/二手` 提升为**本机 exact-SHA 实测回执**：DP-F01 Python `CONFIRMED`、
  DP-NF-03/DP-NF-04 相关目标 `CONFIRMED`（本机运行层）、DP-NF-05 Rust `NOT_EXECUTED`（工具链缺失）、
  `tests/workers` 历史失败记录 **REFUTED（不适用于当前 HEAD）**。
- 本回合**未**提交任何文件。若需保留本节，须由有授权的写入者 commit；届时注意该文件当前为**未跟踪**状态，
  且其行尾/编码需过一次 `scripts/check_repository_conventions.py --source worktree`。
- 无新增 Owner 决策项；上文 §5 第 4 步的四项（A02、P0-H01、DP-F01 D1–D5、Research DTO）**不变**。

---

## 10. 阻塞修复与内容级转述审计（追加于 2026-09-27 第二轮）

### 10.1 结论：两个阻塞都不是"缺工具"，而是"已登记工具未接线"——**未下载任何东西**

| 阻塞 | 实测根因 | 处置 |
| --- | --- | --- |
| Rust 无法编译（历史 `LNK1181 kernel32.lib`；本轮 `error: linker \`link.exe\` not found`，exit 101） | `10-toolchains\msvc\VC\Tools\MSVC\14.44.35207` 下 **`link.exe`、`vcvars64.bat`、76 个 x64 `.lib` 全在**；Windows SDK `10.0.28000.0` 在 C: 也有 `x64\kernel32.Lib`。而 `scripts/ci/cargo_test.bat` **本来就支持** `ARCHEAXIS_MSVC_VCVARS` + `ARCHEAXIS_RUST_TOOLCHAINS`——只是没人设 | 设这两个变量即可编译；**零下载** |
| OCR worker 失败（`AAK-WORKER-003`） | 真 exe 在 `10-toolchains\scoop\apps\tesseract\current`；**scoop shim 是坏的**（指向不存在的 `toolchains\scoop\apps\tesseract\current`，报 `Shim: Could not create process`）；继承的 `TESSDATA_PREFIX` 也指向**不存在**的旧树 | 改用真 exe 目录 + 存在的 tessdata；**零下载** |

因此"缺工具就下载到外置工具库"在本轮**无需执行**：外置库里工具齐备，缺的是把环境指向它。

### 10.2 Rust 回执（上文 §9.4 记为 `NOT_EXECUTED`）

```
ARCHEAXIS_MSVC_VCVARS=<ext>\10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat
ARCHEAXIS_RUST_TOOLCHAINS=<ext>\toolchains\rust
ARCHEAXIS_PYTHON=<repo>\.venv\Scripts\python.exe
scripts\ci\cargo_test.bat test --workspace --offline --no-fail-fast
```

| 目标 | 结果 |
| --- | --- |
| `-p archeaxis-domain --test machine_loop_restart`（DP-NF-05） | **1 passed / 0 failed** |
| `-p archeaxis-api --test f01_quality_roundtrip`（DP-F01 Rust） | **5 passed / 0 failed** —— 与历史回执逐字一致 |
| `-p archeaxis-application --test ocr_job_end_to_end` | 接线前 0 passed/1 failed → 接线后 **1 passed / 0 failed** |
| **完整工作区** | **87 个测试二进制 / 240 passed / 0 failed / 0 ignored / exit 0** |

**必须记录的调用约定。** 直接 `cargo test` 会让 `f01_quality_roundtrip` 报 `1 passed; 4 failed`，失败正文是测试自己的守卫：`run cargo via scripts/runtime/dev.py to select the exact Python`。它要求经受跟踪入口执行（`ARCHEAXIS_PYTHON` 由 `dev.py` 注入）。**把该输出读成产品失败是错的**——它只说明调用方式不对。

### 10.3 持久修复：`scripts/runtime/dev.py::external_toolchain()`

新增发现函数 + 7 条封闭式回归 `tests/runtime-paths/test_external_toolchain.py`（用伪造外置根，不依赖本机布局）：

- 仅在已设 `OS_EXTERNAL_CONFIG` / `ARCHEAXIS_EXTERNAL_ROOT` 且目标**存在**时生效；**无外置根返回 `{}`，CI 不受影响**（实测 `no root -> {}`）。
- **已设且有效**的值保留；**已设但不存在**的值被替换（正是坏 `TESSDATA_PREFIX` 的情形）；`PATH` 只在该目录不在其中时前置，避免重复。
- MSVC 版本目录以"最新含 `bin\Hostx64\x64\link.exe` 的子目录"发现，**不硬编码版本号**。
- 写这条测试时它抓到我自己一个真 bug：`Path("")` 等于 `Path('.')`，其 `is_dir()` 为真，导致 **`TESSDATA_PREFIX` 未设置时反而不被发现**。已修（显式空值检查）。
- 端到端证明：**只设 `OS_EXTERNAL_CONFIG`**，`tests/workers/test_bulk_ocr.py` 由"跳过"变为 **4 passed**；dev/OCR 相关合计 **74 passed**。

### 10.4 内容级转述保真度审计（委派只读子代理，逐条回源到 `文件:行号`）

- **12 项中 11 项 `MATCH`**；**所有被复述的数字逐字一致**（17SHA/88 路径、19SHA/153 路径、13 文件 +5952/−4、5 passed、58/77/1、5+13、117/7/2/5、678+/100−、21,474、33 根未跟踪、G-01…G-05 等）；**0 处无支撑主张**（唯一 `PARTIAL` 是 `lib.rs:63-74`，已由 §9.1 自我更正）。
- **1 项 `DISTORTED`，需回填：DP-NF-01 行。** 批次 02 的验证器**不是** `audit_verify.ps1`——`branch-batch-02.md:256` 写明是 `.project-local/dsh-audit/verify_batch02.py`（`errors=0`）；该行还**漏了** `branch-batch-03.md` 自己的 16 SHA / 107 路径。
- **底层报告之间 4 处互相矛盾，上文未转述：**
  1. P6 `ok=false` 定性三说：`p6-current13-candidate-readback-20260925.md:77-89` 称 "live concurrency artefact"；同文件 `:151-155` Correction 反称 "does not prove concurrency was the sole cause"；`AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md:177` 第三说 "cause still unproven"。
  2. `dp-nf-handoff-20260925.md:168` 记 P6 为 `NOT_EXECUTED`，同文件 `:196-197` 明确该标签**已被取代**（executed snapshot mismatch）——§2 采信了旧标签。
  3. `dp-nf-handoff:126-149` 称 NF-F1 "needs an owner look"；同文件 `:186-191` Correction 称 NF-F1 已 **stale**。
  4. `branch-batch-03.md:42` 称归档覆盖 5/12；`branch-batch-03-archive-correction-20260926.md:3` 更正为**至少 6**，并与 `branch-batch-03.md:356` 附近 "no archived copy" 冲突。

### 10.5 由本轮证据产生的判定修订

| 项 | §9 判定 | 本轮修订 |
| --- | --- | --- |
| DP-NF-01 | `UNVERIFIED` | **`PARTIAL`**：路径与数字回源一致，但验证器归属错误、漏 branch-batch-03 |
| DP-NF-05 Rust | `NOT_EXECUTED` | **`CONFIRMED`（exact SHA 本机运行）**：1 passed |
| DP-F01 Rust | `NOT_EXECUTED` | **`CONFIRMED`（exact SHA 本机运行）**：5 passed，与历史回执一致 |
| DP-NF-06 | `MATCH（含陈旧标签）` | **`PARTIAL`**：标签应采信同文件 Correction |
| 全 Rust 工作区 | 无本地证据 | **240 passed / 0 failed / exit 0（本机 exact SHA）** |

### 10.6 未变

A02 / P0-H01 / F01 D1–D5 / Research DTO 四项 **Owner 决策不变**；真实语料质量、真实模型/Provider、GUI/UIA、当前 DLL 路由复播、Candidate、Clean Machine、Green 与 Release 一律**未执行**；本回合**未**改冻结 TaskPack、`R6-EXECUTION.md`、`R6-STATE.json`。本轮改动落在：`scripts/runtime/dev.py`、`tests/runtime-paths/test_external_toolchain.py`、本文件。
