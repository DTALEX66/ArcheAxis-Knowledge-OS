# Hermes handoff — archeaxis-workspace

Generated: 2026-08-23 (v0.6.8 release closure; older continuation notes retained below)

> **Current authoritative continuation**: v0.6.8 is publicly released at
> <https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.8>.
> Release commit `93e58a3b2c537dd348903dd2296933e0cfb5a503` passed exact-SHA CI
> `32607097436` and Release run `32607789507`. See
> `docs/HANDOFF_2026-08-23_v0.6.8-release.md`; older SHA/test-count statements
> below are historical context, not current evidence.

## NEXT-RUN QUICKSTART（2026-08-15 晚 · 共用库改造后 · 给 DEEPSEEK HARNESS）

> 只读本段即可开工，无需回读全历史。

**当前状态**
- 项目端 HEAD = `0c75f3b`（= origin/main，双端一致，工作树干净）；全量 **1776 passed / 9 skipped**（2026-08-15 基线）+ 吸收批次新增 **~190 passed**（学习引擎/管线/OCR/ASR）。
- **2026-08-18/19 会话**（见 docs/HANDOFF_2026-08-19_pipeline-cleanup.md）：09 调研报告 + 11 学习引擎 + 闭环 + ceshi 全库验证 + 管线修复（TESSDATA 根因/RapidOCR/SenseVoice/噪声过滤）+ 模型补齐（共用库规则已入用户级记忆）+ 清理。
- **2026-08-18 双向学习吸收批次**（见 `docs/HANDOFF_2026-08-18_dual-learning-absorption.md`）：调研报告 09（含 42 条目在线核实）+ 11 个后端学习引擎模块 + 学习者状态 API + 前端 Learning 空间（69 后端 + 13 前端测试）；04 吸收矩阵并入；双向闭环编排器 co_learning_loop.py 已打通。
- 外置库 `D:\All projects\OS External Configuration` = **跨项目共用库（仅工具链/依赖本体）**；本项目构建产物已全部迁回 `.hermes/task-runtime/`；**外置库不上传（保持本地，不 commit 不 push）**。

**下一轮任务（优先级从高到低）**
1. **P0 项目配置规则减重**（Owner 指定优先）——见 `docs/design/` 与记忆；实测 `.hermes/cache` + `task-artifacts` 有 ~965MB 第三方 config/rules 垃圾，规则文档（AGENTS 6KB / VERIFICATION_POLICY 6.7KB / HANDOFF 15KB）可查冗余整合；GitHub ruleset（main/tag-protection）**不可动**。
2. **AXW-WEB-CAPTURE-v3 TaskPack**（OWNER-APPROVED，源 `D:\All projects\AXW_WEB_CAPTURE_V3.zip` 已解到 `.hermes/task-runtime/axw-web-capture-v3/`）——22 任务 DAG：`000→001→003→010→011→012→020→021→022→023→024→030→032→042→EXIT`（消灭 web.py stub、统一 PolicyGate、Raw-first、真实非 mock E2E）；050-052 可选。
3. **RC 三包发布：已完成**（历史 v0.6.7 已由当前 `v0.6.8` 取代；CI `32607097436`，Release `32607789507`，9 项资产独立读回通过）。
4. **App Shell 接 Tauri**（frontend/ dist → frontendDist）+ ENV-103 剩余 hold（rust/uv-cache/wsl2/ci-venv——环境变量/注册表确认后）。

**关键环境事实**
- 共用库工具（10-toolchains/scoop/apps/*/current）：node 24.18.0 / ffmpeg 8.1.2 / tesseract 5.5.0+126语言 / pandoc / gh 2.95.0 / git 2.54.0；python 10-toolchains/python（3.12.13/3.13.14）；rust toolchains/rust；msvc 10-toolchains/msvc。模型权重 40-models/（HF 216MB + ModelScope 896MB）。
- 用户 PATH 已加 ffmpeg + tesseract（node 未加，避免覆盖 HERMES_HOME）；前端构建用完整路径指共用库 node v24。
- junction 断链修复法：`cmd /c rd /s /q <name>` + `cmd /c mklink /J <name> <target>`（Python 3.11 无 is_junction；os.symlink 需特权）。
- 项目工具消费索引：共用库 `00-registry/project-tool-index.yaml`。

**铁律（不可违）**
- terminal 必须经 `python "C:/Users/ALEX/AppData/Local/hermes/bin/hermes-project-data.py" --project . run -- <单命令>`；禁 chaining/重定向/内联绝对路径/多行 python -c（绕行=写脚本到 .hermes/task-runtime）。
- 测试：`env -u PYTHONPATH uv run --frozen --group ci --group ci-adapters pytest`；门禁 `python scripts/check_repository_conventions.py --source head`。
- 证据写项目内 `.hermes/task-runtime/`；外置库不上传；E: 盘不碰；数据边界不外溢。

## Current continuation point

- Repository: `D:\All projects\ArcheAxis-Knowledge-OS` (canonical, single writer: Hermes)
- Branch: `main` — HEAD `e2012d3` and origin in sync (verify with `git status --short --branch` before resuming)
- Cloud: `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS` (push via 127.0.0.1:7890 proxy; api.github.com direct)
- Shared external lib: `D:\All projects\OS External Configuration` (cross-project toolchain/dependency bodies only; build artifacts belong under each project's `.hermes/task-runtime/`; NOT uploaded). Tool index: `00-registry/project-tool-index.yaml`.
- Baseline: AXC TaskPack 2026-08-13 (AXC-000~150 v1.1) + Final Architecture TaskPack 2026-08-14 (R0-R8). Full suite: **1776 passed / 9 skipped** (2026-08-15 local, three dirs); ruff + repository-conventions gate green on head; cargo check + 16/16 Rust tests green; frontend vitest 9/9 + vite build 0 warnings.

## Frozen-baseline execution state (LOG-147..180 in `docs/truth/EXECUTION_STATUS_LOG.md`)

Implemented and CI-verified (continuous green: CI runs 524-592; 585/588 were pre-fix runs — lint & cross-platform path — both fixed, latest green):

- **AXW-022B**: PDF evidence annotation reachable (text-layer overlay + cached selection); real browser-smoke first ran on CI at `85b3311` (run 31732780580).
- **H5 implementation layer** (`5dc3d9b` + `d129aa3`): AXW-094A open-exchange export (`app/exchange/export.py`), AXW-094B verifiable backup (`app/exchange/backup.py`), AXW-096A performance benchmark (`shared/performance_benchmark.py`), AXW-096B keyboard accessibility (UI), AXW-096C batch import control (`app/ingestion/batch_controller.py`). EXIT is a verification gate, not an implementation prerequisite (precedent 023A-F/043B/050A).
- **AXW-096A real data**: layered zh/en public-domain corpus (Gutenberg, sources.json provenance, corpus NOT committed) + real benchmark PASS (`01ad561`); toolchain `scripts/prepare_benchmark_corpus.py` / `scripts/run_performance_benchmark.py`; report `docs/truth/PERFORMANCE_BENCHMARK_096A.md`.
- **Workspace API surface** (`81df63b`): exchange export/verify, backup create/verify/restore(dry-run), batch import/status — error semantics explicit (400/404/409/422).
- **User-facing UI entry** (`892b87b`): Evidence page 开放交换与备份 card — four reachable buttons (export/verify/backup create/verify) with API round-trip asserted in browser-smoke (`#evidence` hash route).
- **Async batch control** (`8ea9a05` + `976bf13` + `6011b81`): pause/resume/shutdown on a live registry; ledger task-list recovery + terminal-state restoration (from_checkpoint) — interrupted batches are resumable, totals honest; duplicate-active rejected 409 (covered).
- **CI ecosystem audit**: nightly zero-collection defect fixed (`af3df00`); Release workflow pre-first-run audit PASS (`7d72e34`); nightly py-compat 3.13 matrix verified locally (`9c9adb4`); **Release pipeline local verification 100%** (`7eb0131`: prepare_bundle end-to-end + staged-runtime import + verify_nsis_install.ps1 AST parse). nightly next real trigger: **local 11:17 (03:17 UTC)** — the earlier "skipped tick" observation was a timezone misread (Actions page shows local +08:00 time; cron is UTC; see LOG-161); never-ran fully explained by add-time vs tick timeline (LOG-162).
- Capability Atlas: CAP-0140 (AXW-094) projected `in_progress` (`01ad561`).

- **Nightly made real (LOG-165/166/167)**: manual dispatch before the first
  scheduled tick exposed three genuine gaps, all fixed and re-verified
  (Runs #1-#5: fail → green → green → fail → green): real OCR engine in
  full-suite (`6b395b5`), explicit three-directory collection incl.
  integration-tests (`b99d111`), and browser-smoke upgraded to a real
  Chromium regression that must run inside the venv (`98a0ee6` + `d8db1ad`).
- **Gateplan fail-closed (LOG-168/169/170)**: router.py + browser-smoke
  script classified under ui risk (`a03e27f`); four targeted gates were
  planned but never executed/verified — now carried by the test job and
  checked by ci-verdict (`dfe287c`); all-class profile probe audit PASS.
- **Release pre-audit PASS (LOG-171)**: tag-only workflow audited with the
  nightly gap classes — all release scripts stdlib-only, identity reaches
  the NSIS payload via tauri bundle resources; only real build+install
  remains (Owner tag).
- **H5 acceptance matrix (LOG-172 + `e610c4d`)**: AXW-097 diagnostics now
  assert no secrets/auth/paths anywhere in the response; AXW-096B keyboard
  coverage confirmed (focus trap, aria-live feedback, PDF reader keyboard
  reach); 6/9 tasks ready — 095/060/H5-EXIT remain Owner-gated.
- **CI timeouts + nightly Run 6 (LOG-173)**: timeout-minutes added to all
  ci.yml Python jobs (`24606db`) and all four nightly jobs (`c8a85ce`);
  nightly Run 6 green 3m51s on the timeout build — scheduled tick
  (local 11:17) is a formality.
- **Flaky fix (LOG-174 + `be6c23f`)**: batch shutdown test polled for
  worker start instead of a fixed sleep; product code verified clean.
- **Batch R0 — Final Architecture TaskPack 2026-08-14 (LOG-175/176)**:
  - AXW-REL-001: Nightly Run 7 (schedule) failed `pause 404`; root cause
    chain fixed — pause/resume now lock-protected (no finished→paused
    overwrite hang), ledger appends serialized under a separate
    `_ledger_lock` (concurrent `open("a")` handles corrupted JSONL lines,
    silently dropping events on `from_checkpoint` replay: in-memory 200 vs
    rehydrated 199), `_process_task` catches BaseException (worker never
    dies mid-task silently), test is deterministic (200 files + poll +
    visibility polling + completeness assertions). Evidence: **200/200
    fresh-subprocess loop** (`9b47c00`), full suite 1619 passed,
    **nightly Run 8 green**.
  - AXW-REL-002: release.yml fully dynamic — `Resolve and verify release
    version` step parses the tag, fails on drift across
    pyproject/package.json/tauri.conf.json, and every asset name
    (installer `ArcheAxis.Knowledge-v<ver>-Windows-x64-Setup.exe`, wheel,
    readback) derives from `release_version`; zero hardcoded 0.5.0 remains
    (`0e33aac`).
  - AXW-REL-003: `main-protection` (non_fast_forward + deletion +
    required_status_checks a0-gates) and `tag-protection` (update+deletion
    blocked) rulesets active; admin bypass added because required status
    checks block direct pushes (CI-deadlock) — collaborators/PRs still
    enforced. Ruleset API schema trap documented (nested
    `required_status_checks: [{context}]` + `strict_required_status_checks_policy`).
    Signing decision already recorded (RELEASE_LEDGER).
- **Final Architecture TaskPack R1-R8 batch (LOG-177, 2026-08-15)**:
  - R1 (AXW-ENV-101~105): machine-readable capability-requirements.yaml +
    2 JSON schemas + doc generator; host_inventory.py real scan (8 tools
    health + tesseract langs) → 00-registry/; restructure_dryrun.py 16-move
    plan (dry-run only, no actual moves); Enter/Exit-ArcheAxisDev.ps1
    session env; capability_download.py stage/verify/quarantine/activate
    governance. Deliverables live in OS External Configuration repo
    (scripts/, 00-registry/, logs/) — uncommitted by design (local-only
    inventory; task pack: not a public install dependency).
  - R2 (AXW-RUN-201~206): Recovery Shell (bootstrap state machine + IPC
    token, window opens frontendDist first); Runtime Profile v1 (4
    config/profiles/*-stable.yaml + fail-closed loader); Backend Handshake
    /api/v1/system/handshake; Supervisor state machine + /status + /restart;
    canonical ARCHEAXIS_* env (Rust sets both, sanitizes both families);
    CSP + security headers + CORS loopback-only. Rust: cargo check +
    16/16 tests; Python: 36 tests.
  - R3 (AXW-DEV-301~304): external-dev profile + Developer Kit
    (packaging/developer-kit/) — hot-reload integration pending Supervisor
    wiring in the shell.
  - R4 (AXW-DATA-401~404): workspace manifest schema + impl (four asset
    domains); path_policy.py four-mode fail-closed (portable never falls
    back to user dir); DATA-403 migration design doc; 46 tests.
  - R5 (AXW-CAP-501~504): Capability Store v1 (registry/installed/disabled/
    staging/quarantine, atomic activate) + /api/v1/capabilities router;
    Plugin Manifest v1 schema + validator.
  - R6 (AXW-PKG-602/603/605): assemble_distributions.py Green/Portable ZIPs
    from the same verified runtime (portable data/ zones + portable.flag);
    smoke-tested ZIP layouts; Developer Kit.
  - R7 (AXW-SUP-701~704): identity schema v3 (7-artifact manifest +
    dependency lock hashes); release.yml 6-asset checksums/upload/readback;
    release_sbom.py (634 components); v0.5.0 release renamed to historical
    brand with banner (assets untouched).
  - R8 (AXW-UI-803): OSUI audited (zero references) + downgrade banner;
    React migration deferred to next batch (node toolchain restore).
  - Acceptance §19: #1/#2/#3/#4/#7-#14/#16-#18 green; #5/#6/#15 partial
    (Supervisor wiring, hot reload, migration implementation pending).
- **Final Architecture TaskPack R1-R8 batch 2 (LOG-178, 2026-08-15)**:
  - R3 (AXW-DEV-301~304): HotReloadWatcher (mtime poll, ignore rules, ring
    buffer) + Supervisor request_reload/reload (external-dev fail-closed)
    + reload fields in /status; bootstrap dev-mode panel (badge + reload
    state + manual reload button); clone_test_workspace (new uuid4 id,
    dst-exists raises); Developer Kit README workflow.
  - R4 (AXW-DATA-402/403): app/setup wizard (GET /api/v1/setup/status +
    POST /api/v1/setup/initialize idempotent) appended to main.py (middleware
    untouched); app/workspace/migrate.py (VACUUM INTO backup → dry-run →
    migrate to four asset domains → rollback hash readback → legacy DB kept,
    idempotent).
  - R5 (AXW-CAP-503/504): app/capability/builtin/ six converter plugin
    registrations + discover() + store builtin injection; scripts/
    capability_pack.py pack builder/verifier (per-file sha256). Guard fix:
    sys.path.insert → importlib spec + sys.modules registration
    (forbidden-sys-path-mutation); webview2_detect absolute paths →
    os.environ (forbidden-absolute-path).
  - R6 (AXW-PKG-601/604): install-lifecycle L4 checklist doc (verify_
    nsis_install.ps1 already wired); webview2_detect.py real run — this
    host: Evergreen absent, Fixed Version 151.0.4129.78 ~849 MB; offline
    spike doc (Evergreen default, offline installer path, offline pack not
    in default chain).
  - R8 (AXW-UI-801/802/804): frontend/ React+TS+Vite App Shell skeleton
    (six spaces Workspace/Library/Evidence/Learning/AI Assets/Settings per
    §15.3; api client token-in-memory + product fail-closed; runtime state
    machine mirroring Recovery Shell; a11y tokens focus-visible/reduced-
    motion). npm via npmmirror (68 pkgs); vite build verified (44 modules,
    0 warnings). UI-804 acceptance baseline doc.
  - Acceptance §19 update: #5/#6/#7 now green (supervisor+reload+isolated
    clone); #15/#17 partial (migration implemented; long-path + end-to-end
    UI flow pending L4 / App Shell wiring).
- **Final Architecture TaskPack batch 3 (LOG-180, 2026-08-15)**:
  - R5 (AXW-CAP-503 step 2): real activator wiring — each builtin converter
    module exposes get_activator() wrapping the real ingestion adapter;
    app/capability/conversion.py dispatcher (get_converter returns None for
    inactive plugins, fail-closed; list_active_converters). 24 tests green
    (activator + builtin, independently re-run).
  - §19 #17: integration-tests/test_axw_main_chain_e2e.py — txt/md/html real
    full chain (ingest → convert → evidence ledger → human learning entry →
    AI asset registration with evidence binding, read-back verified).
    5 tests green.
  - AXW-UI-801/804: Vitest 2.1 + Testing Library + jsdom wired into
    frontend; 3 component test files (App/SpaceRail/StatusBar with a11y
    assertions) — 9/9 green + vite build 0 warnings.
  - R7 (AXW-SUP-701/702/703): scripts/release_manifest.py (public asset
    manifest generator); release_sbom.py --notices-out (THIRD_PARTY_NOTICES
    .txt, 634 entries, npm license extraction); release.yml 6→8 assets
    (identity v3 names, checksums, payload equality, upload, readback
    expectedAssets + 9 required kinds).
  - R1 (AXW-ENV-103 apply): 7/10 low-risk moves executed (~13.5 GB) with
    rollback list (rollback-20260815.json); Enter-ArcheAxisDev.ps1 5 path
    refs synced; rust/uv-cache/wsl2/ci-venv held (env/registry-dependent).
  - §19 #15: Windows long-path — plain >260 fails without LongPathsEnabled
    (documented); \\?\ extended-path workspace create + full migration
    round-trip verified; migrate.py _connect fixed (SQLite URI parser cannot
    express \\?\ — extended paths connect natively).
  - Acceptance §19 update: #15/#17 now green; remaining: App Shell→Tauri
    wiring (UI-801 step 2) and L4 real three-distribution publish.

- **Coverage audits (LOG-163)**: all 51 workspace router endpoints and all
  12 UI data-action handlers now have test references (3 genuine route gaps
  closed in `5fdba13`).
- **Nightly first-run closed (LOG-164/165)**: pre-flight audit of all 4 jobs,
  then a manual `workflow_dispatch` exposed a real gateplan-blind defect —
  full-suite lacked the OCR engine install (tesseract/ffmpeg/fonts) that
  ci.yml's OS-level job has; fixed in `6b395b5`, re-dispatched, **nightly
  Run #2 all-green** (py-compat x2 + full-suite + browser-smoke +
  windows-runtime). Scheduled nightly now expected to succeed at local
  11:17 (UTC 03:17) daily.

## Remaining work (Owner-gated — cannot be done autonomously)

- **H1-H4 EXIT** double-loop adjudication (verification gate; prerequisite for 045/055 acceptance).
- **AXW-045/055**: owner acceptance of implementation layer.
- **AXW-012C**: install-state PDF evidence; **AXW-095**: Windows install state — need user-installed runtime + real NSIS install evidence.
- **AXW-097** release qualification, **AXW-060** v1.0 release package: Release workflow (`v*` tag → main check → exact-SHA CI → NSIS → wheel → checksums → draft release) is ready and audited; execution is Owner.
- **AXW-096A large-vault acceptance**: user data after H4-EXIT.
- **full-qualification**: AXC-060 RC logic profile — only triggers at RC.

## Environment facts (non-negotiable)

- All terminal commands must go through the project-data wrapper:
  `python "C:/Users/ALEX/AppData/Local/hermes/bin/hermes-project-data.py" --project . run -- <single command>`
- Test command: `env -u PYTHONPATH uv run --frozen --group ci --group ci-adapters pytest ...`
- Commits: `git add <specific files>` only; commit messages via `git commit -F <file>`.
- E: drive is protected (exact per-request authorization required). `ceshi`/`Obsidian知识库` are read-only black boxes.
- `.hermes/` holds runtime data only; never commit it. `docs/truth/` logs are tracked.
- Browser-smoke gate triggers only on `app/workspace/ui/**`; script fixes can borrow an index.html comment change to force a real CI run.
- Local chromium cache lives inside the project (ARCHEAXIS_DATA_DIR isolation for browser tests).
- GitHub API unauthenticated rate limit 60/hr — use browser Actions page for CI verification when limited; CI diagnostics via `::error::` workflow annotations.

## Boundaries

- Do not access or modify E: without a new exact user authorization.
- ArcheAxis and WORK-LAB are fully independent repos; do not cross-wire.
- Do not touch the frozen advisory branch worktree (`.hermes/task-runtime/frozen-rd`, append-only).
- Review and gate a frozen staged tree. Report CI only for its exact commit SHA.
- Credentials are never committed or printed ([REDACTED]).
