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
