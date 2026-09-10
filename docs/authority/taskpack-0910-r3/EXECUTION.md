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
|R05|本轮|—|Core 侧适配器落地：`crates/archeaxis-application/src/scheduler.rs`（`SchedulerClient`：ARCHEAXIS_PYTHON + worker 路径，子进程 JSON 契约，校验 `authority == "fsrs"`；不可用/被拒时返回 `Unavailable`/`Rejected`，**绝不回退阶梯**）；集成测试 5 项全过：真实 Rust→Python→FSRS donor，成熟卡间隔 >14 天（证明不是阶梯）、同请求可复现、缺 rating 被拒、缺解释器/缺 worker 脚本报 Unavailable|IN_PROGRESS（API 默认路径未接）|`.project-local/runs/r07-scheduler-adapter.log`（application 套件 exit 0；`adapter_returns_fsrs_scheduling_not_the_ladder` 等 5 项）|剩余：学习事件 API 仍未默认调用适配器，`learning::suggest_next_interval` 仍是 Rust 内部默认；回滚＝revert 本切片|

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
