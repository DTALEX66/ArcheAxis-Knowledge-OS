# 执行台账 — ARCHEAXIS-NEXT-TASKPACK-2026-09-10 (R3.1)

包已按 `使用方式` 单层安装到本目录，保留 `reference-r2/` 快照。
`verify_package.py` 以 Python UTF-8 模式运行 exit 0（hashes、17 项任务依赖、
原 23 项任务全部保留）；本机 locale 为 GBK，若直接用 `python verify_package.py`
会因 `read_text()` 默认编码在 UTF-8 的 `TASKS.json` 上失败，故使用
`python -X utf8 ...`，未修改冻结的包内文件。

进度写入本文件与 `STATE.json`；`TASKS.json` 保持计划定义不变。

|切片|实际SHA|run id|命令/环境|结果|证据路径/hash|限制/回滚|
|---|---|---|---|---|---|---|
|R00|985a219（登记前基线）|—|`python -X utf8 docs/authority/taskpack-0910-r3/verify_package.py` exit 0；`cargo test --workspace --offline` 52 组 exit 0；`pwsh -File scripts/ci/run_tests.ps1 --full` 2347 passed/7 skipped exit 0；conventions 门与架构守卫通过|IMPLEMENTED_PENDING_AUDIT|`R00-BASELINE-REVIEW.md`、`PACKAGE-STATUS.md`、`.project-local/runs/r00-python-full-0910.log`、`.project-local/runs/cargo-archive-01-full.log`|仅文档与治理指针；回滚＝revert 本切片提交；未改产品实现|
|R01|2dd7d6d（起始）|—|`inventory_project.py`（只读元数据）→ 23.423 GiB/130,120 文件/20 观测错误/60 排除/10 reparse；`.hermes` 单列 42.853 GiB/718,077 文件 newest 2026-09-06；D: free 231.15 GiB；`cargo build -p archeaxis-api` 经 `.project-local/runs/cargo-build-api.bat` exit 0，根 `target/` 6,151,810,038 B/19,949 文件前后一致，`.project-local/build/cargo` +52.6 MiB|IMPLEMENTED_PENDING_AUDIT（部分范围见 §6）|`R01-CAPACITY-BASELINE.md`、`.project-local/runs/r01-census.json`|未删任何缓存；打包侧路径差分与 `__pycache__` 重定向未做；回滚＝revert 本切片文档提交|
|R02|288991a + cbe253b|—|`cargo test -p archeaxis-domain` exit 0 / 9 组全绿：accept_with_new_body_is_rejected_and_body_stays_immutable、accept_commits_status_and_one_event_atomically、failed_review_leaves_no_partial_state、modified_creates_traceable_successor、modified_creates_candidate_and_records_event_on_original|IMPLEMENTED_PENDING_AUDIT|`review_transaction.rs`、`.project-local/runs/r02-domain.log`|接受/拒绝/撤销不得改正文；仅 `modified` 建新版本+supersedes，同一事务；回滚＝revert 288991a/cbe253b|
|R03|985a219 + 本轮|—|旧实现真实样本：在 v3 时代 scratch worktree（`968c479`/`a2dbef5`/`60b355a`/`3d65609` 的 store+archive）用历史代码导出四个**非空** v3 归档（10/11/12/13 表，sources=1 knowledge=2 objects=1），作为 fixture 提交；`cargo test -p archeaxis-archive` exit 0 / 7 组全绿（含 `genuine_v3_era_archives_restore_with_content` 逐个恢复四布局并断言升级到 v4、正文逐字节保留）；全 workspace `cargo test --workspace --offline` exit 0 / 52 组|IMPLEMENTED_PENDING_AUDIT|`crates/archeaxis-archive/tests/fixtures/v3-{ten,eleven,twelve,thirteen}-tables/`（含 PROVENANCE.txt）、`.project-local/runs/r03-archive-v2.log`、`.project-local/runs/r03-full-workspace.log`|v3 实际发布过 10/11/12/13 四种布局，全部接受；v1（7 表、无 workspace_meta）明确不支持；未知布局仍拒绝；回滚＝revert 本切片提交|
|R04|本轮|—|修复 fail-open 漏洞：`Launch::from_stdin` 现只接受 `actor ∈ {human, machine}`，其余值（`alien`、`Human`、空串、`"machine "` 尾空格等）一律拒绝启动且不建 workspace；机器/人类凭据仍由启动会话声明，客户端 `x-archeaxis-actor` 一律被中间件覆盖|IMPLEMENTED_PENDING_AUDIT（凭据托管范围待补）|`.project-local/runs/r04-api.log`（launch_auth 6 测试，含 `unknown_launch_actor_is_rejected_and_never_grants_human_authority`）；既有真实进程 harness 断言 stdout 不含 token|真实宿主签发并保管的机器/人类凭据范围仍未实现；合法用户动作成功、非法启动失败已回归；回滚＝revert 本切片|
|R05|本轮|—|Core 侧适配器落地：`crates/archeaxis-application/src/scheduler.rs`（`SchedulerClient`：ARCHEAXIS_PYTHON + worker 路径，子进程 JSON 契约，校验 `authority == "fsrs"`；不可用/被拒时返回 `Unavailable`/`Rejected`，**绝不回退阶梯**）；集成测试 5 项全过：真实 Rust→Python→FSRS donor，成熟卡间隔 >14 天（证明不是阶梯）、同请求可复现、缺 rating 被拒、缺解释器/缺 worker 脚本报 Unavailable|IN_PROGRESS（API 默认路径未接）|`.project-local/runs/r07-scheduler-adapter.log`（application 套件 exit 0；`adapter_returns_fsrs_scheduling_not_the_ladder` 等 5 项）；全仓 Python `run_tests.ps1 --full` **2355 passed / 7 skipped exit 0**（`.project-local/runs/r07-python-full.log`，较此前 2347 恰为新增 8 项 worker 测试，证明 donor 增量参数无回归）|剩余：学习事件 API 仍未默认调用适配器，`learning::suggest_next_interval` 仍是 Rust 内部默认；回滚＝revert 本切片|
|R05b|本轮|—|keyed 审校路径**参数化**（不复制去重逻辑）：`ScheduleSource::{Ladder, Explicit(Option<i64>)}` + 私有 `record_review_keyed_impl`；新增公开 `record_review_scheduled(..., next_review_days: Option<i64>)`，`None`＝调度不可用 → 事件照记但 **next_review 为 NULL**、payload 带 `schedule: unavailable` 标记、返回哨兵 `SCHEDULE_UNAVAILABLE=-2`（绝不回退阶梯）；`record_review_keyed` 行为不变（Ladder 模式）；EVENT-01 语义（重放返回原收据 `-1`、跨对象/跨 payload 冲突、缺键拒绝）保持|IN_PROGRESS|`.project-local/runs/r13-r05-domain.log`（domain 10 组全绿，新增 `learning_schedule_authority` 4 测试）；`.project-local/runs/r13-r05-api.log`（api 14 组全绿含 learning_events_api、machine_correction_loop，无回归）|回滚＝revert 本切片|
|R05c|本轮|—|API 处理器接线：`LearningEventBody` 新增可选 `schedule_state`+`now`；处理器先解析权威再入库——(a) 带卡状态 → 走 `SchedulerClient`（复用 FSRS worker）；(b) 调度不可用 → `record_review_scheduled(None)` 记 **unscheduled**；(c) 无卡状态 → 显式走占位阶梯；响应新增 `schedule_authority`（`fsrs`/`unavailable`/`placeholder_ladder`），调用方无法再把阶梯误认为真实 FSRS|IN_PROGRESS（剩余见右）|`.project-local/runs/r15-r05-api.log`（api 15 组全绿；新增 `learning_schedule_api` 3 测试：卡状态→fsrs 且 >14 天、无卡状态→placeholder_ladder、不可用→unavailable/-2 且历史 `next_review` 为 null）|剩余：产品侧调用方需始终提交卡状态（属 R10 宿主接线）；scheduled 事件的**重启一致性**尚未单独断言；全 workspace 复跑待下一工作单元；回滚＝revert 本切片|
|R05d|本轮|—|补 R05 收尾两项：① 新增 schedule_survives_a_workspace_reopen（domain）——已排程事件重开库后 due 仍在、unscheduled 事件仍无 due、重启后同键重试仍判为重放（收据一致）；② 全 workspace cargo test --workspace --offline **exit 0 / 55 组全绿**（新增测试文件使组数由 52 增至 55）|IMPLEMENTED_PENDING_AUDIT（唯一遗留见右）|.project-local/runs/r16-full-workspace.log（55 组 ok，含 schedule_survives_a_workspace_reopen）|唯一遗留：产品侧调用方需始终提交 schedule_state（属 R10 宿主接线，届时阶梯不再被任何产品路径触达）；回滚＝revert 本切片|
|R06|本轮|—|公开核查的**离线可交付部分**补回归：`tests/test_x07_public_check_probe.py`（13 项）锁定必需区分——真实支持须同句含对象+单位+数字；**直径命中记为 `diameter_only`（弱证据，非支持）**；无关同数字（如「6371 年」）→ `none` 非支持；模型答「不支持」「无法判断」、空文本或报错一律**不得**成为支持；抓取失败**抛异常**而非静默变成「无证据」|IN_PROGRESS（云端部分 BLOCKED_EXTERNAL）|pytest `tests/test_x07_public_check_probe.py` → **13 passed**；probe 本体 `scripts/probes/x07_public_check_probe.py`|云端交叉核查需**用户已配置且获准**的接口与凭据（本项目默认 0 付费预算）→ 记为 `BLOCKED_EXTERNAL`，不声称云端核查完成；活体「本地检索 + 模型裁决」需外网（此前间歇）与 ollama（当前 :11434 在线），列入下一工作单元；回滚＝revert 本切片|

## R00 记录（2026-09-11）

- 基线锁定：分支 `codex/full-loop-0906`，HEAD `985a219`（晚于包审计基线 `cbe253b`），
  与 origin 同步，工作区仅 `.zcode/` 未跟踪（GLM 会话本地）。`main` 仍 `4ca46ea`。
- 继承缺陷重查（不假定、不回退旧实现）：R02 已修（`288991a` REVISION-01）；
  R05 已修（`288991a` EVENT-01）；R03 本会话已修（`985a219` ARCHIVE-01）；
  R06 部分（`288991a` VERIFY-01，实跑受 HTTPS/凭据 gated）。
- 入口登记：`AGENTS.md` §6、`docs/DOCUMENTATION_AUTHORITY_INDEX.md`、
  `docs/CONFIGURATION_AUTHORITY_INDEX.md`、`DECISION_SUPERSESSION_LEDGER.yaml`
  SUP-018、intake `workspace/intake/2026-09-10-next-taskpack-0910.md`。
- 乱码检查：扫描 `docs/`、`workspace/`、`config/` 及根级 md/yaml 共 451 个文件，
  活动入口文档无乱码；唯一 U+FFFD 出现在
  `docs/authority/legacy/T17-semantic-review-samples-2026-09-05.json` 的
  `head_snippet`（二进制 PNG 头片段），属合法数据而非文档损坏，历史材料不改。
- 待办：R01/R02/R03… 的验收仍以各切片独立证据为准；Q00/Q01 只由独立 GPT 判定。
