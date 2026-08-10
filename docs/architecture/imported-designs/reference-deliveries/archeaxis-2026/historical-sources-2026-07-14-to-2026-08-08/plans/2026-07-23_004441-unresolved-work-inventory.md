# Cognitive-Loop-OS 未收口工作清单

**Goal:** 将当前对话、Git 工作树、睡眠状态和项目治理文档中真正尚未收口的事项分为“立即可执行”“需重新立项”和“仅历史参考”。

**Architecture:** 以当前分支 `feat/runtime-evaluation-sleep-leases` 的工作树为唯一实施现场；将 `.hermes/sleep-mode/state.json` 视为停止状态下的历史候选，不直接恢复。Runtime/Sleep 与 Research trace SQLite 边界改动属于当前唯一可验证的实施切片，先完成高风险数据库边界门禁，再决定下一条产品 TaskPack。

**Tech Stack:** Python 3.11 项目虚拟环境、pytest、Ruff、SQLite、Git、项目验证脚本。

---

## 已确认完成或不构成当前阻塞

- 外置 Scoop/Rust 和项目 Windows runtime 数据已迁往 D 盘；C 盘保留的路径是兼容 junction，不是重复实体数据。
- 本轮运行时边界改动已通过：`52 passed in 10.36s`、changed-file Ruff、`git diff --check`。
- `.hermes/sleep-mode/state.json` 当前 `mode: stopped`，`active_task: null`；没有自动执行权。
- 历史上 `Workflow-assistance` 的 GPT 代理、全局 cleanup gate、23 个未提交文件属于另一仓库，不纳入本项目当前 checkpoint。
- 当前 Temp 顶层没有仍可迁移的 `cognitive-*` / `cog-*` 项；历史锁定 Temp 清单不能再当作当前阻塞证据。

## Task 1：收口当前 Runtime / Sleep 与 Research SQLite 边界改动

**Objective:** 将当前 8 个源码/测试改动从“定向测试已绿”推进到符合数据库与运行时边界要求的冻结 checkpoint。

**Files:**
- Modify/review: `app/core/trace.py`
- Modify/review: `app/facades/research_runtime.py`
- Modify/review: `app/memory/database.py`
- Modify/review: `app/sleep_runtime.py`
- Modify/review: `shared/sleep_loop_engine.py`
- Test/review: `tests/test_research_artifact_runtime_loop.py`
- Test/review: `tests/test_sleep_runtime.py` (currently untracked; must be intentionally staged only after review)
- Test/review: `tests/test_sleep_loop_engine.py`

**Evidence so far:**
- Scheduler now derives a `frozenset` of dependency IDs whose ledger state is `done`, rather than trusting the task payload.
- Runtime rejects leased tasks without this scheduler proof.
- `run_reviewed_artifact_task(..., db_path=...)` now writes its trace to the caller-selected SQLite database before creating the evaluation candidate.
- A directed test/lint run completed: `52 passed in 10.36s`; Ruff and `git diff --check` passed.

**Step 1: Freeze and review the exact diff**

Run:
```bash
git diff --check
git diff -- app/core/trace.py app/facades/research_runtime.py app/memory/database.py app/sleep_runtime.py shared/sleep_loop_engine.py tests/test_research_artifact_runtime_loop.py tests/test_sleep_runtime.py tests/test_sleep_loop_engine.py
```

Confirm no caller still treats `task["dependencies"]` as proof and no trace path silently falls back to the default DB when an explicit `db_path` is supplied.

**Step 2: Execute the high-risk verification set**

Database and runtime-boundary changes require the policy’s independent full gate, not only a low-risk checkpoint:
```bash
python "$HERMES_HOME/bin/hermes-project-data.py" --project . run -- ./.venv/Scripts/python.exe -m pytest tests -q --tb=short -p no:cacheprovider
(cd knowledge_base && ../.venv/Scripts/python.exe -m pytest tests -q --tb=short -p no:cacheprovider)
./.venv/Scripts/python.exe -m pytest integration-tests -q --tb=short -p no:cacheprovider
./.venv/Scripts/python.exe -m ruff check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts
./.venv/Scripts/python.exe scripts/check_architecture.py
./.venv/Scripts/python.exe scripts/check_repository_conventions.py
```

If a pre-existing unrelated failure appears, isolate and document it rather than masking it or reverting the isolation test.

**Step 3: Create one scoped local checkpoint**

After all required gates pass, stage only the eight implementation/test files. Do not stage `HERMES_HANDOFF.md` unless the user explicitly changes its local-only status. Use a functional commit message such as:
```text
fix(runtime): preserve scheduler and trace persistence boundaries
```

**Step 4: Exact-SHA remote validation**

Because this includes SQLite persistence behavior, run the frozen-tree reviewer / required exact-SHA CI flow under `docs/VERIFICATION_POLICY.md` before any release or merge. Push or merge only on explicit user request.

## Task 2：重新立项下一条产品 TaskPack（不自动恢复旧 sleep queue）

**Objective:** 由当前代码、真实依赖和用户目标选择下一项产品工作，而非执行 2026-07-21 的停止快照。

**Evidence:** `.hermes/sleep-mode/state.json` 记录 `mode: stopped`，`active_task: null`，且记录分支为 `feat/cognitive-workspace-mvp`，与当前分支不一致；搜索不到相应 `next-*.json` / `next-*.md` TaskPack 实体。

**Historical candidates requiring re-validation:**
- `next-02-media-ingestion`：历史上因 Tesseract 无语言模型阻塞；外置工具链现已配置语言包，需以当前激活脚本和真实 OCR test 重新判定。
- `next-05-jobs-events`：历史上依赖 `workspace.sqlite` migration owner / connection-scoped writer；必须重新确认 Schema owner 后才能实施。
- `next-06` 到 `next-11`：仅在旧 state 中列名，当前缺失可执行 TaskPack，不得凭名字开始。

**Step 1:** 以当前项目目标选择一项候选，并先建立真实 TaskPack 与验收标准。

**Step 2:** 若重新选择媒体摄入，先激活 `D:/All projects/OS configuration/scripts/activate-toolchains.*` 并以 `tesseract --list-langs`、项目实际 OCR 测试证明阻塞已解除。

**Step 3:** 若选择 Jobs/Events，先审查 MigrationOperator、workspace SQLite owner 与事务边界；这是高风险数据库工作，独立完成全门禁。

## Task 3：路线图产品债务（非当前自动任务）

这些事项在 `docs/PROJECT_STATUS.md` 中仍明确未完成，但没有现成、已批准的 TaskPack：

1. Outbox dispatcher、SSE 审计时间线、面向普通用户且不暴露内部 ID 的 Job Center。
2. ASR、媒体时间戳、内容语义匹配 Evidence、人工真值准确率闭环。
3. 通用 Dynamic Planner、更多真实工具意图、Reviewed Feedback、统一 Runtime/Sleep Loop。
4. Installer、多端发布与正式 Alpha/Beta/Stable 产品化。

它们是产品路线图，不应与 Task 1 的当前安全/数据库收口混为同一次 checkpoint。

## Local-only hygiene decision

- `HERMES_HANDOFF.md` 是未跟踪的本地恢复锚点，按照当前项目规则保留但不自动提交。
- `.hermes/migrated-windows-state/` 是 Git 忽略的 D 盘迁移证据与运行数据，不进入版本库。
- 跨项目 `uv` cache、Hermes 全局会话与 `Workflow-assistance` 脏工作树不属于本项目的代码 checkpoint。
