# AAOS 治理收敛与正式 UI 完成 — 分支交接（2026-10-08）

分支 `codex/aaos-gov-ui-20261008`，基线 `a8d2e0bb`（= `origin/main` + 22 个 UI 提交）。
本文只作导航与状态汇总：不复制任务包、不复制大表、不新建总账；数字与结论一律指向本轮实测收据与文件路径。

> 引用约定：反引号内是本检出内可解析的路径引用，须通过 > `scripts/audit/reference_validation.py --record docs/current/AAOS-GOVERNANCE-UI-HANDOFF-20261008.md` 的严格校验；仅存在于主检出被忽略的产物根、兄弟工作树或绿色仓库的路径一律写作 `未跟踪 <路径>`，它们在新克隆中不可解析，因此不作为可核验的证据引用出现。校验需在链接工作树内以共享产物根为额外根运行一次：`--root project_local="D:/All projects/ArcheAxis-Knowledge-OS/.project-local"`。


## 1. 基线纠正（执行前必须知道）

| 事实 | 实测方法 |
| --- | --- |
| 主检出 `D:\All projects\ArcheAxis-Knowledge-OS` 停在 `codex/Audit` @ `1a981a44`，是 `origin/main` 的**祖先**，落后 750 提交（0 领先） | `git rev-list --left-right --count origin/main...HEAD`、`git merge-base --is-ancestor HEAD origin/main` → YES |
| 因此主检出工作树里的 `AGENTS.md`、`docs/current`（171 文件）、无 `AUTHORITY.md`、无 `config/environment/external-resources-index.json` 都是**旧状态**，不可据以推导当前 | `git ls-tree` 对比：`codex/Audit` 47 个 `frontend/src` 文件 vs `a8d2e0bb` 130 个 |
| 现行 tip 是 `a8d2e0bb`（被审分支 `codex/aaos-ui02-nav3-20261008`），它包含 `origin/main` 全部历史 | `git rev-list --left-right --count origin/main...a8d2e0bb` → `0 22` |
| `codex/oss-reuse-templates-20261008`（`15f79cf7`）= `origin/main` + 1 提交，与 `a8d2e0bb` **不同血统**，不能当补丁盲贴 | `git rev-list --left-right --count a8d2e0bb...15f79cf7` → `22 1` |
| 真实基线上 Avalonia-正式壳叙述**已被取代**（SUP-021→SUP-022，`docs/truth/README.md:13` 已明确纠正；基线 `AGENTS.md` 已写"donor under SUP-022"）。旧分支上看到的"formal desktop is Avalonia"属陈旧树，未据此改动 | 基线 `grep` |

并行任务保护：`worker-quality-0906`(15)、`aaos-ui-newui-20261007`(5)、`v3-era`(3)、`supply-bind-20261007`、`aaos-ui-core-integration-20261007`、`aaos-longpath-app-20261007` 各有未提交内容，本轮**一律未触碰**；一个 checkout 只有一个 writer，四路 writer 各用独立 worktree + 独立分支，由我串行整合。

## 2. 已落地改动（P1 治理）

| # | 内容 | 提交 | 入口/证据 |
| --- | --- | --- | --- |
| G1 | **机器合同与 SUP-022 收敛**：`config/product/UI_CONTRACT_V2.json` 原把冻结供体写成正式壳，且被 3 个 Python 门禁 + `.github/workflows/nightly.yml` 注释强制，导致机器权威与 `AGENTS.md` 相互矛盾而**两边全绿**。现声明 Tauri2+React/TS/Vite 为正式宿主、Avalonia 为 `donorShell`、`desktop/` 为 `recoveryEntry`；门禁改为断言"声明的入口必须存在于磁盘" | `9f552f01` | `tests/test_ui_contract_v2.py`、`tests/test_workspace_ui_design_contract.py`、`tests/test_documentation_authority_index.py` |
| G2 | **文档收敛**：`docs/current` 405→342 跟踪文件，63 项以 `git mv` 迁入 8 个带日期历史组，逐项含 source/target/bytes/sha256/consumers/owner/authorization/deletion_authorization/rollback；无删除、无改写原文，只加带日期 superseded 头 | `ec9f3b97` | `docs/history/DOCUMENT-CONSOLIDATION-20260927.json`（83 行，其中 MOVE 64） |
| G2b | 恢复验证：本轮**独立复算** 64 条 MOVE 行的原始字节 SHA-256 并核对源路径已消失 → `VERIFIED 64 / HASH_MISMATCH 0 / TARGET_MISSING 0 / SOURCE_STILL_PRESENT 0` | — | `未跟踪 .project-local/scratch/verify_relocation_hashes.py` |
| G3 | **过时"AUTHORITY.md 缺失"更正**：根 `AUTHORITY.md` 存在且被跟踪，7 个当前入口改为带日期更正（保留 2026-10-01 实测来源），本轮又清掉剩余 4 处现在时态断言（含 1 处 JSON `disposition` 字段，该文件另有 `evidence_level: REAL`，无测试钉住原句） | `9f747528`、`f0897492` | `docs/current/AAOS-OPEN-WORK-REGISTER-20261001.md:22` 等 |
| G4 | **五个路由问题一个现存文件**：现行索引新增该节，含"共用工具/模型从哪里解析""哪些仅历史参考"，并诚实列出"本轮无法靠搬迁收敛的重复组" | `ec9f3b97` | `docs/DOCUMENTATION_AUTHORITY_INDEX.md:68,214` |
| G5 | **外置资源解析**：`environment_registry` 的 PATH 优先（静默替换）改为声明优先并在降级时点名；修掉把 faster-whisper/rapidocr/sherpa-onnx/magika 与 ci-venv 统一认证成 `uv 0.12.23` 的探针谎言；Rust 三根合一（manifest/dev.py/cargo_test.bat 统一到 `toolchains/rust` + 导出 `RUSTUP_HOME`），`TESSDATA_PREFIX`、MSVC 探针、PowerShell 类"假 MISSING"、caption/machine-answer 端点登记全部落地；每行新增 `verification_level` 与 code/asset 许可分离字段 | `9f3fd470` | `config/environment/external-resources-index.json`（32 行：RESULT_VERIFIED 4 / VERSION_PROBED 16 / FILE_EXISTS 9 / unavailable 2 / NOT_RUN 1） |
| G6 | **死控制项修复**：`tests/runtime-paths/test_external_toolchain.py` 的 rustc 实跑测试读的是 setUp 自己清空后的 `environ`，因此**永远自我跳过**；改为读清空前快照后真实执行 `rustc --version` 与 `cargo --version` 并断言同一工具链版本 | `9f3fd470` | `1 passed in 1.27s`（原 `1 skipped`） |
| G7 | **体积分类与回收清单**：按类别分别实测（Git 历史/跟踪树/ignored 产物/各 worktree/重复占用/共用根），明说 Git 历史不可减、跟踪字节本轮**净增** 406,580 bytes；`docs/current` 收敛只是把字节搬进 `docs/history`，不是瘦身 | `9005b2d2` | `docs/current/REPOSITORY-CLEANUP-HANDOFF-20260921.md` 2026-10-08 批次节 |
| G8 | **运行不得膨胀落地到维护规范**：`docs/VERIFICATION_POLICY.md` 新增该节，规则挂到既有 `scripts/runtime/dev.py`（精确 worktree 根、忽略校验、按身份哈希分目录、per-run tmp/logs/artifacts、`ARCHEAXIS_RUN_ID`）与 junction 复用机制；未新建体系、未建定时删除器 | `9005b2d2` | — |
| G9 | **绿色仓库边界复测**：身份冲突与断链登记（见 §5） | `969c6130` | `docs/current/AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md` 2026-10-08 节 |
| G10 | 共用资源人工根索引指向唯一机器入口，消除"各写一套路径说明" | `72e2e7f1` | `docs/SHARED_RESOURCE_PATH_INDEX.md` |

## 3. 已落地改动（P2 UI 与门禁）

| # | 审计问题 | 处置 | 证据 |
| --- | --- | --- | --- |
| U1 | 两项静态真相门禁可被"清空正文/空扫描列表"骗过 | 抽出唯一扫描器 `frontend/src/__tests__/support/productSourceScan.ts`，正反用例共用；空集、少于下限、必需目标缺失、根不存在一律 **throw** 而非返回空 offender 列表；反向用例改为驱动生产扫描函数 | `9b306242`；用例数 3→15、4→17；`未跟踪 vitest-integrated.txt` |
| U2 | 原始 payload 仍在阅读面 | `CanonicalLearningSpace.tsx:96` 历史 JSON、`CanonicalCapabilitiesSpace.tsx:89` observation JSON 改为人类可读摘要 + 既有 `RawReceiptButton`；未新建诊断系统。全树 `grep '<pre>{JSON'` 现只剩 `DiagnosticConsole.tsx:33` | `da952cd5` + 本轮 grep 自证 |
| U3 | 多个 `role="status"` 并存（Exchange 最多 4 个） | 按播报事件收敛：持续态/静态派生/占位句去掉 role（可见文本保留），失败态合并为一个区域；`failureReason` 无 role 的修正保留；知识页 `getAllByRole('status')==1` 未削弱并扩到学习页与能力页 | `frontend/src/__tests__/LiveRegionBudget.test.tsx`（15 用例）、`frontend/src/__tests__/CoreFailureStates.test.tsx` 扩展 |
| U4 | 真实 Core 闭环 | `scripts/verification/core_roundtrip.py`：真实 **release** Core（9,115,136 bytes，`sha256 4ada192d…`）上 `document_create` 201 → `document_draft` 200 → **停进程、同数据根重启** → `document_get`/`document_version` 200，`version=2`、`content_sha256 c59ddc38…`、`editor_json` 与历史 v1 逐字节一致，`roundtrip_errors=[]` | `c94c7259`；`未跟踪 .project-local/coredemo/receipt/run2/RESULT.md` |
| U5 | 浏览器门禁依赖临时 Shell 环境 | `scripts/a0_browser_smoke.py` 的 `shutil.which('node')` 失败即哑叫"缺 Node"，改为回落声明索引 `ext.toolchains.nodejs-lts`；反证：PATH 清到只剩系统目录时仍解析出 `24.18.0/node.exe`，把索引指向不存在路径时返回 `None` 并在错误里列出已查询源 | `fd3754d8` |

## 4. 验证（本轮实跑，分级）

| 层 | 命令 / 结果 | 级别 |
| --- | --- | --- |
| 前端全量 | `node node_modules/vitest/vitest.mjs run --reporter=basic --no-color` → **57 files / 428 tests passed**（基线 56/381；A +25、B +22 并存无冲突） | INTEGRATED（jsdom） |
| 前端类型 | `tsc --noEmit -p tsconfig.json` → exit 0，0 行输出 | — |
| 浏览器几何 | `scripts/a0_browser_smoke.py` → `"status": "PASS"`，10 视口×3 主题，`source_revision.base_commit=9005b2d2`、`worktree_dirty=false`，`canonical_host_problems=[]`，三级导航 `primary 9 / secondary 4 / focused anchors / tertiary src_a0_nav3` | **SIMULATED**（stub 桥，只证布局，不证 Core 调用） |
| Python 门禁 | 11 个套件合并跑 → **101 passed**（`未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/pytest-consolidated-414a4513.txt`） | REAL（本机） |
| 真实 Core 写读 | 见 U4 | **REAL** |
| 解析稳健性（自测复现） | `tests/workflow/test_external_resources_index.py` 从仓库根 / `services/python-workers` / `frontend/src` 三种 cwd 各 **12 passed**（同一结果，解析不依赖当前目录）；把 `ARCHEAXIS_EXTERNAL_ROOT` 指向不存在目录后 **2 failed / 10 passed**（`test_external_resources_index.py:245`），即缺资源明确变红而不静默回落 PATH | REAL |
| 文档/目录检查 | `scripts/check_path_conventions.py` 3122/3123 归属、0 deny 被跟踪、0 歧义；`scripts/ci/check_document_authority.py` 单一当前记录、根引用可解析、输入哈希相符；`scripts/check_repository_conventions.py` 通过 | REAL |
| 远端 CI / 安装资格 / 人工验收 | 未执行 | **NOT_RUN**（本地绿不等于远端绿；未 push） |
| 写入隔离（自测复现） | 先删 `%TEMP%\archeaxis-resource-probe`，再以 `ARCHEAXIS_RESOURCE_PROBE_WORKDIR` 与 `ARCHEAXIS_INDEX_OUTPUT` 指向任务目录跑生成器：探针目录只在 run 路径内生成、`%TEMP%` 无残留、输出 76,369 bytes 落在任务路径、`git status config/` 为 0 修改 | REAL |
| 缺资源与未运行项（生成器实测表） | `local-embedding-model` → `1024-dim vector returned`（RESULT_VERIFIED）；`local-rerank-model` → **`NOT_RUN`，原因随行走廊**（模型 id 被服务但宿主端点应答不符）；被跟踪索引当前等级分布经复算为 VERSION_PROBED 16 / RESULT_VERIFIED 4 / FILE_EXISTS 9 / unavailable 2 / NOT_RUN 1，共 32 行 | REAL |
| 生成器不再污染治理记录（本轮缺陷修复） | `test_declared_paths_resolve_on_this_host` 曾以子进程就地重写被跟踪索引：干净跑一次该文件，被跟踪 blob 由 `4c8bf6aeebcb…` 变为 `7910abe4ad85…`，即"跑测试"本身改写治理记录，且该文件含主机绝对路径，谁最后跑谁决定提交内容。改为 `ARCHEAXIS_INDEX_OUTPUT` 可重定向后：正常根 `12 passed` 且 blob 保持 `4c8bf6ae`；把根指向不存在目录时 **4 项点名失败**而 blob 仍 `4c8bf6ae` | REAL（`e0e52a21`） |

### 整合后终验（七路全部并树后，HEAD `fb630015`）

两条各自验证过的分支首次同树，故整体重跑：

| 层 | 实测 | 收据 |
| --- | --- | --- |
| 前端全量 | **58 files / 436 tests passed**，exit 0 | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/vitest-merged-fb630015.txt` |
| 类型 | `tsc --noEmit -p tsconfig.json` exit 0，**0 行输出** | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/tsc-merged-fb630015.txt` |
| Python 18 套件 | **190 passed**，exit 0；跑后被跟踪索引 blob 仍为 `4c8bf6aeebcb…`（零污染），`git status` 干净 | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/pytest-merged-fb630015.txt` |
| 浏览器几何 | `scripts/a0_browser_smoke.py` → `status PASS`、`errors []`、`canonical_host_problems []`、10 视口 × 3 主题、`base_commit fb630015`、`worktree_dirty False`、导航 `primary 9 / secondary 4 / anchors / tertiary src_a0_nav3 / 复习队列存在` | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/A0-MERGED.txt` ＋ `未跟踪 .project-local/legacy-scratch-20261006/project-local/a0final/artifacts/browser-smoke/*.png` |
| 可视复核 | 我打开两帧确认：library 帧显示资料库（4 个对象分组、人类可读文案、无 JSON），learning 帧显示学习页（失败态"不兼容：本地核心的返回不符合当前合同，已停止而未按成功显示"）——文件名与画面内容一致 | 同上 |
| 未跑项 | 新增 Rust 测试 `crates/archeaxis-api/tests/oss_template_reuse.rs` **NOT_RUN**（未跑就不主张）；远端 CI、安装资格、真人旅程、日用安装验收 **NOT_RUN** | — |

依赖变化：**无**。`frontend/package.json`/`frontend/package-lock.json`/`Cargo.toml`/`Cargo.lock`/`pyproject`/`uv.lock`/`.csproj` 均未被本轮改动（`git diff --name-only` 过滤实证）；新 worktree 经 junction 复用既有 `node_modules`，未复制大型共用资源。

## 5. 诚实性与 OSS 整合（已落地，原为在飞）

两路 writer 中途停摆且未提交，由我停止其代理、接管各自 checkout 后收口（保持"一个 checkout 一个 writer"）。

| 项 | 落地 | 提交 | 实测 |
| --- | --- | --- | --- |
| 审计项 5 引用完整性 | `scripts/audit/reference_validation.py`（580 行，带 `--record/--scan-evidence/--root/--json` CLI）取代按 basename 全树 `rglob` 的旧法：精确路径 + 声明根内解析、按记录哈希或提交核身份、同名歧义列双方并拒绝、裸 basename 永不通过、绝对路径与越出根的 `..` 一律拒、历史引用可解析但标记且不被同名件自动满足、判定类不折叠 | `15f0e6de` | `tests/test_reference_validation.py` **18 passed**，含"旧规则对这些故障全盲"的反证用例 |
| 审计项 6 生成器诚实性 | `scripts/audit/emission_discipline.py`：数字必须来自 resolver（模板里留字面数字即构造期拒绝）、不可重算者以 `CLAIM`/`INSUFFICIENT-EVIDENCE` 具名输出、手写标记被 `scan_unproduced` 拒、`check_written` 复核**落盘字节**、生成器打印自己算出的 tally 而不再声称"全部由磁盘重算" | `15f0e6de` | `tests/test_emission_discipline.py` **13 passed**（把审计里 `（前端 365、Rust 526）`、`PASS/CI(force_full)` 原文当作栽入故障） |
| 审计项 4 证据哈希 | 台账新增带日期更正节：`未跟踪 .project-local/artifacts/evidence/machine-answer-real-release-core-20261008/receipt.raw.log` 4,114 B / `0cf9deba…`、`未跟踪 .project-local/artifacts/evidence/machine-answer-real-release-core-20261008/summary.json` 1,865 B / `0294d344…`、记录值 `2d3c69a5…` 对两者任何可辨识形式均不匹配且穷举 artifacts 无命中 → 来源记为**不可证**，不猜测、不重跑凑值；同时记捕获缺陷（JSON 正文恰在 char 4000 截断，与 `coverage_caveat` 的"从未截断"矛盾，该条改判 REFUTED，而 `machine.answer` 的 REAL 判定按回执内容与 Core 身份保留）；原工件与旧值未改 | `15f0e6de` | 两个哈希由我本轮 `sha256sum` 独立复算，非转述 |
| P3 OSS 与 T1/T2/T3 模板 | `git merge 15f79cf7` 按 hunk 整合：`CanonicalLearningSpace` 保留本轮 `historySummary`+`RawReceiptButton` 诊断路由、无 role 的 `failureReason` 与单一 live region，仅取 OSS 侧 `initialItemKey` 学习项绑定；`DocumentEditor`/`CanonicalLibrarySpace` 取模板根属性与 dirty 保护而不丢 nav/onTrail；20,584 行 / 992,500 字节生成表**不再入库**，改为跟踪生成器 + `OSS-REUSE-CROSSWALK-20261008.manifest.json`（记录产生命令、输入、原始字节与 CRLF 规范化两种摘要），并由测试重新生成比对、生成器自身变更即失效；PDF.js 由 REFERENCE 改 CURRENT（`frontend/package.json:21` 声明 `pdfjs-dist 6.4.299`、`PdfReader.tsx:3` 实际导入，旧桶位是假陈述），改为直接钉"只能主张 source 存在" | `ea1e1700` → 整合 `fb630015` | 前端 **58 files / 436 tests**、tsc 零输出、`test_mfx001`+crosswalk+manifest+html_donor **23 passed** |

未达成的部分如实保留：新增 Rust 测试 `crates/archeaxis-api/tests/oss_template_reuse.rs` 本地 **NOT_RUN**（需 cargo 构建，未跑就不主张）；模板在 jsdom 下渲染属 SIMULATED/INTEGRATED，不等于真实知识库操作；OSS 侧的 T1/T2/T3 与 28 学科配置经整合后由 `frontend/src/__tests__/TemplateBindings.test.tsx` 与 `tests/workflow/test_oss_reuse_crosswalk.py` 覆盖，未经真人学习配对验证。

### 已核实的门禁边界（对我先前一句过宽说法的收窄）

穷尽 `grep TemplateLauncher frontend/src` 的结果只有三处：`CanonicalLibrarySpace.tsx:16` 导入、`:385` 挂载、`frontend/src/__tests__/TemplateBindings.test.tsx:5` 与 `frontend/src/__tests__/TemplateBindings.test.tsx:71` **独立渲染该组件**。因此准确说法是：

- **已有守卫**：`frontend/src/__tests__/TemplateBindings.test.tsx` 覆盖组件自身逻辑，包括"拒绝放弃脏模板属性时保持展开"这条真实行为（`window.confirm` 返回 false → `details.open` 仍为 true、草稿值保留）。
- **确实无守卫**：**没有任何测试断言资料库页面挂载了它**（`grep 学科模板 frontend/src/__tests__/*.tsx` 为空），浏览器门禁也不覆盖。删掉 `:385` 那一行，58 文件 / 436 测试与 A0 全绿。
- 该缺口由并行线 2（`codex/aaos-ui-templates-20261008`）关闭，要求含"拆掉挂载必须变红"的反证；本轮不在我的工作树重复实现，以免与它在前端文件上互相覆盖。

## 6. 并行三线整合（体积 / UI 门禁 / 分支处置）

三线各用独立 worktree 与独立分支，基线 `fb630015`，由我串行整合；两路 writer 中途停摆时我停止其代理并接管其 checkout。

| 线 | 分支 → 整合提交 | 落地与实测 |
| --- | --- | --- |
| 1 体积清理与目录规范化 | `codex/aaos-gov-volume-20261008` → `6c678521`（`cd83a4ff`） | **回收 1,002,595 KB**：4 个未注册 `pycache-*`（186,871 KB，逐文件普查 100% 为 `.pyc`、零嵌套 junction）＋ 2 个空壳（含 junction 者先 `cmd /c rmdir` 卸链，共享目标前后 **5,626 文件**且探针 SHA 一致）＋ 4 份重复 `frontend/node_modules` 改 junction。**删除前先落清单、先证可恢复**：9,919 个 `.pyc` 中 9,916 可由现存源重生成，6 个孤儿归档为 zip 并按 name+size+CRC32+SHA-256 逐成员核验。**拒绝并报告命中**：`dp-f01-20260925`（31 处跟踪命中，含受保护恢复收据）、`worker-outside-test`（被 `tests/maintenance/test_check_vnext_workers_paths.py:36` 点名）、未合并/脏工作树、暖缓存、`未跟踪 runs/recovery/mig/artifacts`、`.hermes`、Git 历史 |
| 1b 机器强制归属 | 同上 | `DIRECTORY_AUTHORITY.yaml` 新增四类归属（各自带 `carried_by`/`machine_predicate`/`fails_when`）、共用资源安装规则，并把 `recovery/`、`mig/` 补进被忽略根；`check_path_conventions.py::copied_shared_resources()` 现在拒绝"同一安装在多个干净已合并工作树里各存一份"。检查器输出新增 `0 duplicated shared install group(s)`；变异测试证明其非空转（削弱后测试即红）。`tests/test_path_conventions.py` 21→**22 passed** |
| 2 模板面门禁 | `codex/aaos-ui-templates-20261008` → `b55a1238`（`d73c50d7`） | 见 §4 终验的三组模板断言。**反证**：摘掉 `CanonicalLibrarySpace.tsx:385` 挂载 → 门禁红 `expected exactly one 学科模板 disclosure on 资料库, found 0`，随后按自留副本还原并核 SHA 一致，`git diff fb630015 HEAD -- 该文件` 为 0 字节。它同时纠正了我给的判据：**仅比 `frontend/package-lock.json` 哈希不足以换 junction**——`oss-reuse-20261008` 锁相同（`bad16049…`）但已安装树不同（`de498046…` vs `54b79a7b…`），据此拒绝 |
| 3 分支与工作树处置 | `codex/aaos-branch-disposition-20261008` → `83d738a0`（`7652836e`） | 44 分支分类：MERGED-CONTAINED 33 / DIRTY-UNCOMMITTED-PROTECTED 7 / UNIQUE-COMMITS-PUSHED 2 / UNIQUE-COMMITS-LOCAL-ONLY 2；38 个注册工作树（我此前给的"≈31"被实测纠正），3 个未注册残留。**`git worktree prune` 两次 dry-run 输出为空**，故未执行。退役清单 31 项只列命令、只用 `git branch -d`（`-d` 的拒绝即安全属性），**未删任何分支或工作树**。不可退役项含 `codex/aaos-p04-doc-loop-20261007`（6 个提交不在 tip，触 `crates/archeaxis-api/src/lib.rs` 等）、`codex/minimax-aaos-cosmic-ui-20261001`、`codex/github-delivery-docs-20260929`（其 upstream 无本地跟踪引用 → 推送状态 `NOT_VERIFIED`） |
| 4 我自身的越界与纠正 | `d878badf`、`69f18606` | 宽跑套件暴露两个只由我造成的红：我在 `.project-local` 里造了 `receipts/`、`scratch/` 与根 `__pycache__`，违反工作树布局契约。用**既有** `scripts/runtime/realign_dev_layout.py` 把 12 项归档（非删除）进 `legacy-scratch-20261006` 并留清单，收据迁到 launcher 规定的 `runs/<身份>/<run_id>/artifacts/` 下并同步交接引用；`__pycache__` 归入 `ALLOWED_IGNORED`（与已列入的 `.pytest_cache`/`.ruff_cache` 同类，删了下次跑 pytest 又长回来）——**栽一个根目录杂项即变红、移除即变绿**，证明归类没有掏空守卫。另修 `scripts/a0_browser_smoke.py` 7 处 `str(x.relative_to(ROOT))`：`ARCHEAXIS_RUN_ROOT` 在仓库外时直接抛异常，而 dev.py 恰恰把链接工作树的 run 根放在主检出共享 `.project-local` 内——此前"外部 run 根会让门禁只跑一个视口就死"的判断实为此崩溃 |

### 最终终验（HEAD `69f18606`，干净树）

| 层 | 结果 |
| --- | --- |
| 前端 | **58 files / 440 tests passed**，exit 0 |
| 类型 | `tsc --noEmit` exit 0，无输出 |
| Python 宽范围 | `tests/workflow`＋`tests/maintenance`＋`tests/runtime-paths`＋`tests/contract`＋审计/合同/分类器/a0 共 **538 passed / 3 skipped / 0 failed**（早先一次 5 failed 全部由我给 pytest 传了越界的 `--basetemp` 造成，去掉后归零；被测工具的"输出逃逸 run 根即拒绝"守卫本身行为正确） |
| 浏览器 | `status PASS`、`errors []`、`canonical_host_problems []`、10 视口 × 3 主题、`base_commit 69f18606`、`worktree_dirty False`、三级导航与模板断言全在 |
| 治理检查器 | `check_path_conventions` 3145/3146 归属、0 deny 被跟踪、0 歧义、0 重复共用安装组；`check_document_authority` 单一当前记录；`check_repository_conventions` 通过 |
| 仍未达成 | 远端 CI / 安装资格 / 人工旅程 / 日用安装验收 **NOT_RUN**；`crates/archeaxis-api/tests/oss_template_reuse.rs` **NOT_RUN**；模板的图谱/画布/引用原文块在真实引擎下仍只有空态被驱动（stub 的 `document_create` 不合 `DocumentDto` 合同），窄窗断言对"多引用画布"无覆盖 |

## 7. 需业主决定的具体事项

1. **push 与远端 CI 资格化**：分支 `codex/aaos-gov-ui-20261008`（HEAD `69f18606`）未推送；`a0-gates`/`browser-smoke` 需一次 push 才能取得当前分支的远端结论。本地全绿不构成其替代。
2. **主检出唯一未跟踪资产（已精测）**：`docs/history/` 下 **1114 文件 / 498,341,341 bytes（475.3 MiB）**，其中仅 88 个被跟踪，`git check-ignore` 返回未忽略；未跟踪部分在真实基线**零跟踪**，即删除不可从 Git 恢复。纳入提交还是显式忽略需一个裁决；现状态下任何 `git add .` 会把它们整体带入。分支名 `codex/Audit` 本身可退役（其提交全是 `origin/main` 祖先），但**该目录不可**在任何清理命令前动。
3. **`src-tauri/tauri.conf.json:10` `frontendDist: ../.project-local/build/frontend-dist` 非身份隔离**（实测；对照 `scripts/runtime/dev.py` 的 `build/<identity>/cargo` 已隔离）：并发 UI 构建会互相覆盖同一 dist。改动涉及打包/发布路径，未擅动；最小修法已在此说明。
4. **绿色目录纯净度（GC-03）**：`.ui-task-tree/` 实测 6,471,511 KB 开发占用，其中 5,783,275 KB 属 `CodexSandboxOnline` 独立克隆（git dubious ownership 拒绝，我不动）。是否迁出、迁往何处需位置裁决；同时 `README.md:13` 指向的恢复入口 `未跟踪 AAOS-vd6bd374-20261001-x64/desktop/ArcheAxis.Desktop.exe` 实测 **MISSING**，重指向属版本切换决策。
5. **体积回收：本轮已执行的部分与仍待授权的部分**
   - 已执行（在"体积清理"指令范围内，逐项先归档、先证可恢复、先查引用）：4 个未注册 `pycache-*` 与 2 个空壳、4 份重复 `node_modules` 改 junction，合计 **1,002,595 KB**；清单与核验件在 `未跟踪 d-docs-20261008/.project-local/volume-20261008/`，孤儿 `.pyc` 归档 zip 逐成员验过 CRC32 与 SHA-256。
   - 仍待授权：`speaker-embedding.onnx` 26,530,550 bytes 与共享根逐字节同哈希的副本（同目录 `.PATCHED.onnx` 是修改件，**不得按同名处理**）；其余 6 份重复 `node_modules`（含锁相同但安装树不同的 `oss-reuse`，需按树摘要逐个判）；`.project-local/build` 中真正孤儿仅 54,154 KB，其余 41.8 GB 属**在册活跃工作树**的重建成本，回收等于把成本转给下一轮，需业主就"退役哪些工作树"一并决定；Git 历史清理/改写/远程 ref 删除/强推不在默认授权内。
6. **分支与工作树退役**：§6 线 3 给出 31 项 retire-ready 及精确命令（`worktree remove` 先于 `branch -d`，一律 `-d` 不 `-D`），以及 3 个含独有提交的不可退役分支。**同日稍后更新**：31 项 retire-ready 中的 9 个兄弟工作树已按上述二次证明移除（分支与 ref 未动，无 `--force`）；分支本身仍未退役任何一条。。**本轮一个分支、一个工作树都没删**。
7. **UI-01 的 12 张页面母版**：8 个权威根内不存在 → 保持 `BLOCKED-ON-SUPPLY`，不编造母版一致性。因此"布局是否还原母版"目前无法判定，本轮只自证内部一致。
8. **不能自签项**：`docs/authority/taskpack-1004-aaos01/checks/acceptance.json` 的 AQ26/AQ27 保持 `NOT_RUN`；物理 IME/DPI/P95/冷启动、九步人工旅程、真人学习配对、日用安装验收需业主执行。
9. **cross-encoder 重排**：fail-closed 属业主模型装载，非代码缺陷；caption/embedding/rerank 属 loopback 端点，`11434` 关闭而 `1234` 曾被证实可用，不得称"Ollama 阻塞"。
10. **标志母版中文行与命名合同不一致**：业主 2026-10-08 提供的黑白母版中文行写「星环知识系统」，而 `docs/truth/NAMING_CONTRACT_V2.md` 锁「星环知识平台」。本轮按合同处理：产品内只用图形 emblem，名称继续由文本承担，拉丁 wordmark 另存母版供需要完整 lockup 的表面使用；既没有改母版，也没有把「系统」引进界面。要采用哪一处措辞、以及是否需要在界面呈现完整 lockup，属业主命名决定项。

## 8. 整合顺序与回退

```
基线 a8d2e0bb
 └─ 5ab344f1 integrate uigates   (9b306242)      frontend/src/__tests__ + support 扫描器
 └─ 1d38e938 integrate uia11y    (da952cd5)      spaces/components + LiveRegionBudget
 └─ 93e335cb integrate resindex  (9f3fd470)      config/environment + scripts + services + tests
 └─ b3cf63cd integrate docs      (ec9f3b97,9f747528) docs/current→docs/history
 └─ 9f552f01 合同收敛  969c6130 绿色复测  9005b2d2 体积与规则  fd3754d8 node 解析  f0897492 断言更正
 └─ 414a4513 integrate coredemo  (c94c7259)      scripts/verification/core_roundtrip.py
 └─ 49714ea4 integrate honesty   (15f0e6de)      scripts/audit/{reference_validation,emission_discipline}.py + 台账证据更正
 └─ fb630015 integrate oss       (ea1e1700)      templates/ + 生成表改清单 + 供应链台账
 └─ 74504d46 引用解析收紧（根相对/记录相对/目录/glob）  764b9cbb 完成度审计生成器移植
 └─ b55a1238 integrate ui-templates (d73c50d7)   模板面浏览器门禁 + 反证
 └─ 83d738a0 integrate disposition(7652836e)     分支与工作树处置登记
 └─ 6c678521 integrate volume     (cd83a4ff)     回收 1,002,595 KB + 归属机器强制
 └─ d878badf 布局契约合规   69f18606 a0 外部 run 根崩溃修复
```

九次 `git merge --no-ff` 全部 exit 0，**无一次冲突需要人工取舍**（各线路径互不重叠；唯一重叠风险 `frontend/src/spaces/CanonicalLearningSpace.tsx` 由 OSS 线按 hunk 解决并已验证）。回退：任一分支提交可单独 `git revert`；文档搬迁的回退由清单逐行给出（`git mv` 反向 + 目标字节与哈希比对）；被删除的体积项全部先归档并逐成员核验，`.pyc` 可由现存源重生成；用户数据、数据库、CAS、恢复件未被触碰。

工作树占用说明：本轮共使用 8 个 writer worktree（`gov-ui` 加 `a-gates`/`b-surfaces`/`c-resources`/`d-docs`/`e-honesty`/`f-oss`/`g-coredemo`），**未新建任何 worktree**（后三线复用已合并的空闲位，避免为并行再增加体积）。它们**本轮不删除**：其中 4 个的 `frontend/node_modules` 是指向 `f15-folder-ingest-20261007` 共享安装的 junction，递归删除会跟随链接删掉共享源。安全顺序是先 `cmd /c rmdir <junction>`（只卸链接），再 `git worktree remove`；分支提交仍在，随时可重开工作树。此项已列入 §7 第 6 条待授权清单。

**更正（同日稍后，提交 `978043bf`）**：上面「本轮不删除」与 §7 第 6 条「一个工作树都没删」已被同一轮稍后的处置取代。9 个兄弟工作树在逐项二次证明（`git status --short` 空、`git log --oneline 29c3cb98..<branch>` 空、`merge-base --is-ancestor` 通过、HEAD 附着于分支）后**已全部移除**，`git worktree list` 由 38 项降到 29 项；4 个 `frontend/node_modules` 链接先以 `cmd /c rmdir` 卸载再删工作树，共享安装在六个测量点恒为 8,078 文件 / 190,195,893 字节，且经本工作树链接与直接路径各数一遍一致。**分支与 ref 一个未删**，任何 `git worktree remove` 都未使用 `--force`；回执先归档（18,807,969 字节）后才动目录。逐条证据、回退命令（9 × `git worktree add` + 3 × `cmd /c mklink /J`）与 11 项未授权保留项见 `docs/current/REPOSITORY-CLEANUP-HANDOFF-20260921.md` 的「2026-10-08 批次 B」。
仍待业主裁决的是另一回事：`§7` 第 5 条列出的重复 `node_modules`、`speaker-embedding.onnx` 副本与 `.project-local/build` 中属于在册工作树的 41.8 GB，本轮未动。

## 9. 第二轮：品牌图、窗口缩放与几何门禁（提交 `4611e8a4`、`27da2816`）

业主在本轮追加两项要求：把项目标志按界面尺寸用进去，以及「界面一定要适配缩放窗口大小，不要缩小后叠加在一块」。

| 项 | 落地 | 实测依据 |
| --- | --- | --- |
| 品牌图来源 | 业主 2026-10-08 提供的黑白标志母版抠图，替换三张自绘近似 SVG | 母版 `未跟踪 Three_Project_Logos_BW_4K_0001_图层 3.jpg` 1280x1384、295,557 字节、SHA-256 `670eb8238380992436960333af8950aaf6aa90029847cf0ab98b3f2c7e4b1617`；逐文件哈希登记在 `docs/current/AAOS-UI-ASSET-MANIFEST-20261007.json`（含被替换 SVG 的原哈希与原提交 `29c3cb98`） |
| 抠图方式 | 亮度拉伸直接作 alpha，RGB 取各主题自身 `--aaos-text`，不重绘任何笔画 | 配方与逐尺寸对照：`.project-local/legacy-scratch-20261008/runs-dirs/logo-extract-20261008/extract_logo_assets.py`、`未跟踪 .project-local/legacy-scratch-20261008/runs-dirs/logo-extract-20261008/compare_small_sizes.py` |
| 尺寸按槽位取 | 状态栏 28 CSS px 高，标志按其自身 1.107 比例画成 31x28（资产画布 182x165）；方形画布会把标志压到约 20 px 高 | 28 px 下线性 alpha 丢细轨道，`gamma 0.6` 是四档对照中唯一保住轨道的取值 |
| 光效 | 静态 `drop-shadow`，颜色取每主题新增令牌 `--ax-brand-glow`；无动画，故 reduced motion 无需拦截 | Chromium 计算样式逐主题不同，断言见下 |
| 命名冲突 | 母版中文行是「星环知识系统」，`docs/truth/NAMING_CONTRACT_V2.md` 锁「星环知识平台」→ 产品内只用图形 emblem，名称仍由文本承担 | 属业主裁决项，见 §7 第 10 条 |
| 窗口下限 | `src-tauri/src/main.rs` 增 `.min_inner_size(640.0, 480.0)`（此前只有 `.inner_size`，而恢复入口 `desktop/src-tauri/src/lib.rs` 早已声明 960x640） | 声明前实测：520px 视口下 `scrollWidth 640 / clientWidth 520`，阅读列有 120px 落在窗口外 |
| 门禁覆盖 | 浏览器矩阵补 760x800、640x800、640x480，使被测最窄视口恰等于窗口拒绝越过的下限 | `tests/test_window_minimum_size.py` 把两者钉在一起，任一边漂移即红 |

### 对上一段我自己一条断言的撤回

几何门禁最初在 640x480 报出 `landmarkOverlaps: [['center','templates',346,327.5], ['dock','templates',346,40]]`，我据此说「模板工作区叠在活动坞上」。这条**不成立**：`.app-center` 本就是 `overflow-y: auto` 的滚动列（`clientHeight 396 / scrollHeight 987`），交叉点 `elementFromPoint` 落回活动坞自身，被裁切的可滚动内容并没有画在那里。原因是我把矩形容器的可见裁剪丢了——只比原始 rect，就会把任何正常滚动的长页面判成叠加。

把探针改为按「每个裁剪祖先 + 视口」求可见框后，用同一门禁跑改动前的样式表：**同样通过**。所以那条红是门禁的假阳性，不是产品缺陷；样式表那处改动（列数由容器宽度决定而非视口断点强制）保留，但它的理由是"更短、少一次滚动"，不是"修了一个叠加"。

同时，改裁剪感知差点把门禁弄瞎：`position: fixed` 的元素脱离流、不被祖先 overflow 裁剪，第一版因此对一个真实叠加报了"无叠加"。现按视口单独裁剪 fixed 带，并补 `unreachableBands`（溢出且其滚动祖先无法带回即红），使"被裁掉"不等于"再也看不到"。

反证（两轮，工作树哈希在每次运行前后一致，故结论可归因）：

| 运行 | 结果 |
| --- | --- |
| 现状树 | `A0_EXIT=0`，回执 `status PASS`，五个资料库尺寸（900/840/760/640x800/640x480）折叠与展开的 `landmarkOverlaps []`、`clippedBands []`、`unreachableBands []`、`missingBands []` |
| 改动前样式表 | 亦 `PASS` —— 上面那条撤回的依据 |
| 植入 `details.template-launcher { position: fixed; top: 430px }` | `A0_EXIT=1`，红在 `assert not geometry["landmarkOverlaps"]`，即它本该抓的那条规则 |

驱动与回执：`.project-local/legacy-scratch-20261008/runs-dirs/a0semantics-20261008/run_semantics_probe.py`、`未跟踪 .project-local/legacy-scratch-20261008/runs-dirs/a0semantics-20261008/summary-as-is-planted-painted-overlap.json`。

### 本轮这一段的验证

- 前端 `vitest run`：58 files / 440 tests passed；`tsc --noEmit` 零输出。
- Python：`tests/test_window_minimum_size.py` 5 passed、`tests/test_ui_asset_manifest.py` 4 passed、`tests/test_reference_validation.py` 24 passed（新增一条：反引号里的 CLI 标志不得当路径引用，`--record/--scan-evidence/--root/--json` 此前被算成 6 条悬空引用）。
- 交接文档自身的引用被同一把尺子量：初测 62 条里 31 条不合规（裸文件名歧义 + 指向主检出被忽略产物根/绿色仓库的路径），按"反引号=本检出可解析、`未跟踪 <路径>`=故意不可解析"的约定重写后 51 PASS / 1 AMBIGUOUS，剩下那条是并行线正在新建的 `tests/workflow/test_oss_reuse_crosswalk.py`，落地后补全路径。
- 仍未达成：已安装 WebView2 宿主内的品牌图与图标观感、Windows 资源管理器/任务栏对 `icon.ico` 各尺寸的渲染、业主肉眼验收 —— 均 `NOT_EXECUTED`，不由 Chromium 结果代替。

## 10. 第二轮：体积按总量重测、分支收敛、绿色仓库审计（2026-10-08 晚）

上一轮我把体积线报成"闭环"，实际只回收了 148.6 GB 里的 7%。业主用资源管理器戳穿了这一点。
本轮先把总量重新测出来，再按类别动手，所有数字都注明来自哪条命令。

### 体积（`scripts/runtime/storage_report.py` 与 `未跟踪 .project-local/runs/volume-map-20261008/` 两个脚本各测一遍）

| 范围 | 前 | 后 | 依据 |
| --- | --- | --- | --- |
| 项目主体整盘 | 148.6 GB（159,551,857,557 B） | **80.7 GB（86,618,369,845 B）** | `未跟踪 .project-local/runs/volume-map-20261008/where_the_bytes_are.py` 单次遍历，链接不跟随 |
| `.project-local` | 145.96 GB | **48.48 GB** | `未跟踪 .project-local/runs/volume-map-20261008/drill_dev_root.py` 单次遍历 |
| 其中 `worktrees/` | 71.04 GB | 3.12 GB | 18 个已合并且干净的工作树移除，41.97+26.20 GB |
| 其中 `build/` | 41.01 GB | 15.95 GB | 按 dev.py 自身的 `sha256(casefold(root))[:10]` 反查归属，只删孤儿 |
| 其中 `runs/` | 9.48 GB | 9.28 GB | 4 项证据先归档后删（229,614,206 B / 247 文件） |
| 其中 `recovery/` `mig` `cache` `artifacts` | 18.68 GB | 18.77 GB | 归档落进 `mig/`，净增即归档开销 |
| 云端侧（对照用） | Git 包 510,446,592 B、跟踪源码 65,931,381 B / 2,448 文件、2,813 可达提交 | 不变 | `count-objects -v` + `ls-tree -r -l` |

**关键对照**：148 GB 全部是本机忽略产物，一字节都不上云；源码侧不到 0.6 GB。
不可约的 Git 历史 510 MB 按原样列出，没有靠"改写历史"去藏它（未授权）。

### 分支：44 → 10

- 33 条用 `git branch -d` 退役，全部由 git 自身的合并检查放行；每条退役前记 tip SHA，可按名恢复。一次没用 `-D`。
- 1 条（`codex/github-delivery-docs-20260929`）本轮先 `--no-ff` 合并再退役：它唯一提交的内容与线上**逐字节相同**，
  且线上落笔晚 1 小时 43 分（PR #154），所以合并是空内容的对账，目的是让它成为祖先、让 `-d` 能自己放行。
- 剩 10 条：`main` 与 8 条已并入本线但**仍挂着工作树**；1 条未合并——
  `codex/minimax-aaos-cosmic-ui-20261001`（+2 提交，14 文件，+365/−96，"cosmic UI 层：背景、玻璃壳、诚实占位"
  与调色板不变量）。它动的是 **SUP-022 已冻结的 Avalonia 供体**一侧，且工作树有未提交改动。
  按"不自动合并主线"的边界，这条留给业主裁：要供体侧的视觉层就合，不要就连工作树一起处置。
- 2 条 `-d` 拒绝的原因已查明并记录：`codex/f15-status-row-20261007` 已并入本线，但其 upstream
  `origin/…` 缺这些提交 → 要删需先推送（业主）；`codex/Audit` 被主检出占用。

### 绿色仓库：审计成功，删除被 NTFS 挡住

见 `docs/current/AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md` 的"2026-10-08 授权轮"。要点：
三个原以为"外部账户所有、不能碰"的路径**全部可读**，所以"不能审计就删"这条没触发；克隆里 23 个 ref
全部能在主仓解析、无未推送提交，但有 **98 个文件的未提交 Avalonia 工作别处没有**——已归档
（补丁 758,982 B + 79 个未跟踪文件，合计 11,160,518 B），并**在基线提交的临时 worktree 里重放补丁验证过**
（恢复出 19 条跟踪改动）。真正删不动的原因是 `rmdir` 对属主为 `CodexSandboxOnline` 的内层文件报
"拒绝访问"，而 `takeown` 因本会话非管理员被拒；6.89 GB 因此原地保留，命令已写给业主。
`aaos-vnext-data` 里是 `workspace.sqlite` 加 WAL/SHM，属用户数据与 CAS，**有权限也不删**。
本轮绿色仓库净回收 280,873 B。

### 证据归档（4 项，已核验）

`未跟踪 .project-local/mig/evidence-archive-20261008/`：4 个 zip 全部 `testzip()` 通过
（成员 225/14/7/1，合计 82,615,053 B），对应源目录已不在，逐项目录带 manifest。
其余 `未跟踪 runs / recovery / mig / artifacts 四类` 未处理——负责这条的执行体在 150 轮上限处中断，
所以剩下 28 GB 仍是"未做引用判定"，不是"判定过但保留"。

### 本轮终验（HEAD `231ea600`，运行前后工作树哈希同为 `d9151ad78b2d`，故可归因）

| 层 | 结果 |
| --- | --- |
| 前端 | 59 文件 / **473 通过** |
| 类型 | `tsc --noEmit` 零输出 |
| **生产构建** | `vite build` exit 0，三张品牌 PNG 以哈希名落进 `dist/assets`（未被内联，资源管线成立） |
| Python | **535 通过 / 3 跳过 / 0 失败**（范围写进回执，含 4 个子目录 + 10 个具名文件） |
| 能力目录 | `generate_capability_catalog.py --check` exit 0 |
| 吸收跨接 | `build_oss_absorption_crosswalk.py --check` current：68 条、仅 7 条可启停、115 条分歧保留 |
| 浏览器门禁 | **PASS**，13 视口 × 3 主题，0 错误，5 个资料库尺寸零叠加/零不可达/零自裁切 |
| 引用完整性 | 交接 **55/55**、品牌记录 **9/9**，零悬空零歧义 |

### 我自己这一轮的两处执行错误（都记下来）

1. 终验驱动脚本我写错了两次：一次 `cd` 指到共享 runs 根（脚本在工作树自己的 runs 根），
   包装层照样报 exit 0；一次把 `run()` 返回的 dict 当对象取属性。**两次都是"通知说完成了"但活没干**。
2. 回收脚本第二次运行把第一次的回执**覆盖**在同一文件名上。原始 JSON 回执丢了一份，
   我从两份运行日志重建了合并清单——但这是补救，不是没犯错。

### 仍未达成（不是本地能关掉的）

远端 CI 资格化与 push、装机验收、九步人工旅程、物理 IME/DPI/P95/冷启动、
`docs/authority/taskpack-1004-aaos01/checks/acceptance.json` 的 AQ26/AQ27（保持 `NOT_RUN`）、UI-01 的 12 张页面母版（`BLOCKED-ON-SUPPLY`）、
cross-encoder 重排（业主装载模型）、绿色仓库 6.89 GB（需提权）、
`minimax` 供体分支（需裁决）、剩余 28 GB 证据的引用判定。

## 11. 第三轮：两个仓库的目录文件规范化（2026-10-08 深夜）

业主指令为"项目本体仓库目录文件治理规范化，绿色仓库目录文件治理规范化，该归档的归档，没用的过时的该删除的删除"。本轮实际改的是**布局与分类**，并顺带纠正了我自己的一个会毁掉交付物的判据错误。

### 11.1 先前所有布局检查都看不到的深度

`dev.py:75` 构造 `runs/<identity>/<run_id>`（`identity = sha256(str(root).casefold())[:10]`），因此 `runs/` 第一层任何非 10 位十六进制名都不是启动器产物，而是会话临时抢出来的目录。既有四项布局断言只遍历 `.project-local` 的**直接子项**，从不进入 `runs/`，于是主检出在全部检查绿灯的同时攒下 **2,206 个第一层条目：297 个浅层目录（3.89 GB）+ 1,866 个散文件（27.4 MB）**，另有 169 个 `.project-local` 顶层散项。工作树自身也有 13 个，包括我自己本轮写的 `runs/final-verify-20261008/`。修法分两步：`scripts/runtime/storage_report.py` 新增 `runs_layout()`（区分"深度/形状违规"与"形状正确但工作树已退役"）与 `checkout_roots()`，`--repo` 参数使同一份逻辑能测另一个检出；`tests/workflow/test_workspace_layout_contract.py` 的 `test_no_run_directory_sits_at_the_wrong_depth` 按 `scripts/check_path_conventions.py` 的既有惯例执行"允许存在但不允许未登记"：测量集合必须等于基线集合，新增红、基线过期也红。双向证过：清空后 5 passed，`mkdir .project-local/runs/planted-shallow-20261008` 后该测试立刻 FAILED。

### 11.2 已执行的迁移与归档

| 对象 | 处置 | 计数 |
| --- | --- | --- |
| 主检出 `runs/` 浅层条目 | 按 regenerable / evidence / unknown / empty 分类后移入 `legacy-scratch-20261008/`（含清单与 sha256） | 移动 2,126，**23 项 WinError 5 拒绝访问**（他人账户 ACL，记录未强攻） |
| 本工作树 `runs/` | 同上 | 13 → 只剩 `f714401b40/` |
| `aaos-longpath-app` / `aaos-ui-core-integration` / `aaos-ui-newui` 三个工作树 `runs/` | 同上 | 3 / 3 / 56 全部移动 |
| `.project-local` 顶层散项 | 用**既有** `scripts/runtime/realign_dev_layout.py`（加 `--repo/--stamp/--dry-run`，并把引用判定扩到所有检出的 `git worktree list`） | 169 → 移动 123，50 项因被跟踪文档点名而跳过 |
| 根层 4 项 | `p-w7n3ehdf/` 空目录 `rmdir` 移除；`archeaxis_workspace.egg-info/` 移入 scratch；`tools/` 与 `.zcode/` **是检查器的错而非文件系统的错**，登记进 `ALLOWED_IGNORED` | 根层漂移归零 |
| 被移动的 13 个目录的引用 | 只改交付分支（主检出是待合并旧副本，两边都改会造出两条互相矛盾的记录） | 16 个文件、36 条引用重写，重写即时校验 56/56 与 9/9；本节写完后终值 62/62 与 9/9 |

`未跟踪 tools/tesseract/tessdata/eng.traineddata`（4,113,088 B）差点被我删掉：`find -maxdepth 2` 只看到目录、`rmdir` 因此拒绝（这一步本身就是证明），实查 `.gitignore:50` 声明该路径、`crates/archeaxis-application/tests/ocr_job_end_to_end.rs`、`crates/archeaxis-application/tests/pdf_ocr_chain.rs`、`scripts/launch/core_launch.py:77` 三处解析它。结论：声明式忽略但承重，不是漂移。

### 11.3 撤回：我说 3.3 GB 是可再生缓存，这是错的

第一版判据是"目录树里出现 `venv`/`site-packages`/`node_modules`/`__pycache__` 即 regenerable"，据此列出 16 项 3.324 GB 待删。加"可再生字节占比 ≥90%"闸门后同一批目录全部降到 0%–62%，逐项看结构才知道它们是什么：`candidate-q04b` = `ArcheAxis.Knowledge.Green-v0.0.0-q04candidate-x64/`（1,019.9 MB）+ 同名 `.zip`（318.8 MB），`candidate-q04c` 同形；`aaos-ui-current-candidate-20260926`（521 MB）是 B10 断点/命令面板 UIA 读回 JSON 的 `artifacts/`；`r10-live-retry-20260915` 是 `deeptutor-web/` 一份副本。**绿色候选发布件自带 Python 运行时，所以"含 venv"必然误判整份构建为缓存**；按第一版判据执行会连两个候选交付物及其 ZIP 一起销毁。实际删除：1 项 `pip-cache`（≈0 B）。**本轮体积回收为 0.00 GB**，3.3 GB 属"候选件与证据留不留"的业主裁决，不是我能靠目录名替业主决定的。

### 11.4 绿色仓库（非 Git 目录，是安装态部署根）

先只读盘点（独立子代理，禁止任何写/移/删，且明令不得进入 `.ui-task-tree/` 中他人账户的克隆、不得读 `data/`/`backups/`/`aaos-vnext-data*/`/sqlite 内容），再据证据执行 11 项：

- 三个 `启动星环知识-AAOS*.vbs` 的 appRoot（`AAOS-vd6bd374-20261001-x64`、`AAOS-v18a00075-20261001-x64`、`AAOS-v82e8d28c-20261002-x64`）**全部不存在**，各自在自身检查处 `WScript.Quit 1`；它们与其独占的三个 `aaos-vnext-data*` 数据根、两份 37 天无持有者的锁文件（`tasklist` 无 ArcheAxis/wscript，根库无 `-wal/-shm` 即已干净关闭）、`AAOS01-文档同步-20261006` 文档快照，一并归档进 `backups/green-normalize-20261008.zip`（235,411 B，SHA-256 `e74fac6ded3b56735b2a4e4daead923f61bea0635ff2cb5115e43ac81632a190`，**31 个成员逐个按名称/大小/CRC32 核验后才删原件**，清单 `未跟踪 backups/green-normalize-20261008-manifest.json`）。归档落在部署自身的 `backups/` 而不是我的 run 目录——唯一副本的压缩包放在会被下次清理掉的暂存区里等于没有归档。
- 文件名损坏的 `README-þ++Þë¦þëê.txt`：字节流 `FE 2B 2B DE EB A6 FE EB EA` 在 GBK/GB18030/Big5/Shift_JIS/EUC-KR 下均非法，**名称不可无损还原**；但真名由生成它的脚本确定——`desktop/scripts/assemble_distributions.py:77` 写 `未跟踪 README-绿色版.txt` 且正文逐字节相同（去 CR 后 md5 `0318b68ed9782cf9aec2b1fdf61244da` 两侧一致，138 B）。按此改名恢复，SHA-256 `da189627868bc02a5aa76c415558d69fc2c1a7e24fbb078ea9ea1b53ffc640d6`。我自己的"改名后归档"顺序先归档了旧名又删了新名，使这条发布说明一度从活目录消失，已按清单核验取回。
- `README.md` 两处失效入口已更正（保留历史陈述、只改当前入口）：恢复件 `AAOS-vd6bd374-…` 段落后追加带日期的规范化更正；台账链接原指 `未跟踪 .project-local/worktrees/dsh-backend-loop-20261001/…`，该工作树已退役（台账在 6 个现存检出里都有，且它是被跟踪文件），改指仓库根 `docs/current/`，并写明部署说明不得引用可回收的工作树路径。
- 根层条目 33 → 24。`output/`、`reports/`、`licenses/` 实测为空但**保留**：无法证明二进制不在启动时依赖它们，空目录零成本，而猜错的代价是宿主起不来；同时 `licenses/` 为空本身是发布合规缺口，记为发现而非清理项。`未跟踪 apply_migrations.py` 根副本 `from shared.core_schema import apply` 而 `shared/` 只存在于 `AAOS-Tauri-f151f4c7998a/` 内 → 根副本不能独立运行，属发现（不复制第二份库，那正是 §3 禁止的）。
- 遗留边界：`.ui-task-tree/` 中 5.78 GB 属 `CodexSandboxOnline` 独立克隆（`du` Permission denied、git dubious ownership、`takeown` 因非管理员被拒），`AAOS-Frontend-Acceptance-v4/`（235 MB，Avalonia 验收候选，ProductVersion `1.0.0+d8f99a6…` 与当前 0.6.14 不同身份）是否迁出仍需位置与版本裁决。

### 11.5 本轮终验（HEAD 未变，工作树按登记状态）

| 层 | 结果 |
| --- | --- |
| Python 宽范围 | **536 passed / 3 skipped / 0 failed**（295.15 s；比上轮 +1 即新增的 runs 布局断言），`PYTEST_EXIT=0` 读自日志而非包装器 |
| 布局契约 | `tests/workflow/test_workspace_layout_contract.py` 5 passed；植入浅层目录后同一条立刻 FAILED，移除即恢复 |
| 引用 | 交接记录 62/62 PASS、母版审计 9/9 PASS，UNRESOLVED / AMBIGUOUS / HASH_MISMATCH / HISTORICAL 均 0（本节新写的 12 条引用先被判红，逐条改为可解析路径或标 `未跟踪` 后归零） |
| 路径归属 | `check_path_conventions` 3156/3157 归属，唯一未归属项 `.gitleaks.toml` 已在册（不是缺陷） |
| 体积 | 主检出 `du` 实测 50.08 GB（本账户可读部分；业主 Explorer 口径含不可读部分），绿色根 2.73 GB 可读。**回收 0.00 GB**，理由见 §11.3 |
| 仍未达成 | §7 全部业主项不变；新增：25 项 ACL 拒绝访问的 `runs/` 条目、35 个身份目录属已退役检出（5.36 GB）、`legacy-scratch-20261008` 内 3.3 GB 候选件与证据的留存裁决、绿色 `AAOS-Frontend-Acceptance-v4` 与 5.78 GB 他人克隆的位置裁决 |

## 12. Codex 接手：治理安全收敛与状态栏修复（2026-10-08）

本轮沿用唯一 writer；主检出仍为交付分支的祖先。本节是新增当前结果，§1–§11 的历史收据保留。
治理、目录/体积及外溢迁移与正式 UI 优先，其他未完成任务尚未启动。没有推送、合并主线、切换 Green 日用版本或删除数据库/CAS。

| 改动 | 提交 | 实测前值 | 实测后值 | 仍未达成 |
| --- | --- | --- | --- | --- |
| T0 局部恢复累计记录 | 本节所在本地变更 | 22 行 / 23 处损坏标注 | 连续损坏标注 0；历史原文及合法产物路径保留，引用初轮 62/62 | 本节新增引用须最终复验 |
| T1/T2 状态栏与窄窗 | 本节所在本地变更 | 640×480 胶囊 7 行、y=-45.5→88.5；检查器 13.1px、select 62.3px | 胶囊 1 行、上下溢出 0；检查器 28×28、select 96×30；修正 select 父容器压缩，窄窗命令快捷键提示收起，长状态仍保留完整文本/悬停标题 | 安装态物理 DPI/IME 不由 Chromium 代签 |
| T3 三主题焦点 | 本节所在本地变更 | white 环 1.14/1.00；cosmic 环 1.55/2.93 | 实际聚焦阴影合成后最差 black 14.32 / white 4.66 / cosmic 6.99，全部 ≥3；select 使用同一主题 token | 本机 WebView2/人工验收 NOT_RUN |
| T4 几何与无障碍门禁 | 本节所在本地变更 | status 未入声明带、子元素外溢与目标缩小漏检 | status 入带；每带直接子元素可见外溢断言；13 视口×3主题检查焦点/目标/胶囊；5 类植入必红/移除必绿；4 个真实产品状态标签逐项测量 | 桥接使用 stub，不能据此宣称真实知识数据操作通过 |
| T5 品牌说明 | 本节所在本地变更 | 注释错误归因静态 halo 为可读性来源 | 更正为墨色对比决定可读性、halo 装饰；未调整品牌光晕 | 无新增视觉决策 |
| 主检出历史资产防误暂存 | 项目本地 Git exclude；不入提交 | 1114 总文件/498,341,341 B，88 跟踪，1007 未忽略未跟踪，19 已忽略数据库 | 对现存 1007 路径逐文件精确本地排除；未忽略未跟踪 1007→0、跟踪仍88；无搬迁/删除/上传 | 资产长期入库/留存/清理仍未关闭；不将排除视为体积回收 |
| 外溢迁移工具与恢复 | 本节所在本地变更 | shutil.move 可在拒绝时退化为复制；manifest 仅最后写；undo 不认新 dated manifest | 同盘 os.rename，逐步原子保存恢复清单；保护目标存在/权限拒绝；只查本体及自有 worktree，排除私人检出导致覆盖未知时保留资产；undo 支持显式 repo/stamp，拒绝穿越/重解析点；定向16测试通过 | 未执行未知外部目录迁移；未删唯一证据；目录逐成员哈希与预算裁决仍待后续 |
| 两根归档恢复资格 | 本轮只读核验 | 旧摘要不算当前证明 | 5归档/278成员复核：本体4包247个逐名/大小/CRC匹配，Green31个流式CRC及完整SHA匹配 | Green历史manifest无独立逐成员expected表；不能把ZIP自带CRC当独立历史名单 |
| 仓库文本规范 | 本节所在本地变更 | conventions 本轮查出2个CRLF文件 | 对照Git正文一致后仅规范为LF，conventions=0问题 | 历史“通过”不替代本轮核验 |
| 外部资源真值 | 本节所在本地变更 | 完整Python初轮2failed：MSVC初始化后 where 不在子进程PATH；crosswalk旧索引摘要过期 | 声明改显式系统 where.exe；实跑MSVC RESULT_VERIFIED；既有宿主uv 0.12.23只加本轮进程PATH并明示 unbound_path_fallback，未改全局PATH；重生成索引/投影 | 当前本地provider探针拒绝连接，保留 unavailable，不能沿用旧 caption/embedding REAL 结论 |

数据口径：历史目录全量475.3 MiB不等于全部未跟踪字节。原始分组是88跟踪14,038,963 B、1007未忽略未跟踪483,442,218 B（461.05 MiB）、19已忽略860,160 B，合计498,341,341 B。本地精确排除只解决误暂存风险，资产尚在原位置。没有据此声称回收体积，本轮归档资产删除0 B。

证据：浏览器及故障注入收据 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/browser-smoke/canonical-browser-smoke.json`；修改前后探针 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/before/a11y-probe.json` 与 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/after/a11y-probe.json`；归档复验 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/archive-reverification.json`；防暂存清单 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/history-staging-protection.json`。

验证状态：初轮聚合 FAIL（Python 2failed/537passed/3skipped、crosswalk过期、执行期间树变更）；不能改写成PASS。初轮前端59文件/473测试、tsc零输出、隔离产物目录Vite build与A0通过。两条迁移边界在只读复核后补齐：空manifest读取前拒绝重解析点根、自有注册检出缺失时不证明无引用。稳定树终验 PASS：前端59文件/473测试，Python542passed/3skipped/0failed，tsc零输出、Vite隔离构建、生成物双检查、三项治理门禁、62/62与9/9引用及13视口×3主题A0全通过，聚合failures为空、运行前后树摘要一致；终值写入 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts` 内的稳定终验子目录，不覆盖初轮失败证据。无障碍四脚本已复跑，证据等级为Chromium实际渲染 REAL/桥接数据 SYNTHETIC，不是安装资格或真人签署。

外溢现状：已有candidate-run、dsh-backend-runtime、dsh-wheel-qual归档/合并清单存在；旧工具会访问外部原根或私人克隆，未重跑。未知归属/拒绝访问项保留；remaining runs/recovery/mig/artifacts 的生命周期处置仍为PARTIAL。缺失UI母版、九步人工旅程、AQ26/AQ27、物理IME/DPI/P95/冷启动、远端CI/安装验收、非身份隔离frontendDist、供体分支/模型装载裁决仍未完成，目标未关闭。

回退：代码与文档通过本节对应提交的反向提交或本轮逐文件diff恢复，不覆盖其他任务修改；项目本地exclude只能在当前摘要仍匹配收据after值时用 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/git-exclude-before.bin` 恢复，若有后续编辑则仅移除本轮标记区；归档与唯一资产均未删除。新迁移工具写入的manifest可用undo的显式repo/stamp恢复，失败保持非零，不把PARTIAL写为PASS。

### 截图指定外溢对象的实际迁移与去重

用户后续明确指定D盘截图对象，并补充三个目录位于D:/All projects；此授权仅用于这些对象，不外推到同盘其它软件/项目。
12个根层测试日志（含负证据）、ddocs的37个治理/恢复文件、ACL目录4文件、stray archive的10文件和root backup的2文件，合计65文件/1,087,673 B，已按组同盘原子迁至主检出的mig批次。原始相对名/大小/SHA-256逐项读回一致，16个源对象均不存在；SQLite原件/WAL/SHM/lock族保留，未连接、合并或覆盖正式数据库。ACL脚本仅留存，未执行，不改ACL。

迁移清单与逆向位置记录：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/mig/d-root-spillover-20261008/migration-manifest.json`。其中ACL载荷归属AAOS；DSH是生成actor。旧spillover register的“belongs to DSH”判断已添加当前更正，原测量行保留作历史证据。

重复lf_test.py与受控测试文件及保留Git提交的原始blob逐字节相同，SHA-256核验后删除源副本1个/39,787 B。恢复用清单内retained_commit和canonical读取原始Git blob；该对象已证明不需要换行转换。其余65个文件是迁移，不能算全盘空间回收。没有删除唯一记录、回滚载荷或候选件。

D:/tmp剩余3项4,775,670 B：appshell.probe.mjs是未定位原项目的手写回归探针；skip.js是DT ALEX STUDIOS定制WebGL首页源码；wlidx.json是WORK-LAB跨文件索引，尚无可重建证明。这三项有用或归属未定，保留原位，不误迁AAOS、不按tmp名称删除；D:/tmp未整体删除。截图中未圈出的安装镜像与其它目录均未触碰。


## 13. 2026-10-09 持续治理与模板非空态验证

体积报告已改为报告可读所属字节下界，并记录每个拒绝访问项、私人子树排除项与外部/私人检出排除项；不再把跳过的目录当完整零字节。先按词法归属筛掉私人和外部 worktree 再做文件系统探测。当前目录 Authority 的 agents/leases/logs/artifacts 已纳入合法目录集合；历史例外仍保留。总量超预算另行告警，缓存保留规则与禁止自动删除不变。realign 在测量 PARTIAL 时拒绝生成执行计划，--repo 不先 resolve 跳过重解析点检查。

本轮实测主检出所属开发数据可读下界51,139,713,202 B：1169个测量拒绝/错误项、73个私人子树排除项、1个私人/外部检出排除项，状态PARTIAL。Green可读所属下界2,110,812,579 B，0个可读范围错误、3个私人子树排除项，仍是PARTIAL而非全量体积。此项仅测元数据，没有读取数据库正文、进入私人检出或执行删除。收据分别为 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/storage-main-completeness.json`、`未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/storage-green-completeness.json`。定向回归28 passed，覆盖真实junction、权限拒绝、私人零访问、Authority目录集合及不完整测量拒绝迁移。

正式UI新增状态化文档桥接fixture，覆盖创建、三个版本绑定引用、保存、折叠重进后读回，以及目标当前版本已更新时仍显示绑定历史原文。其正文/持久化属于SYNTHETIC，Chromium渲染与按钮中心命中属于REAL，不能当成Rust写入或安装验收。

新门禁在修复前实测失败：卡片高53px，而原生成位置y步长35px，三卡互相重叠。已改为按现有卡片实测高度留20px间隔生成新引用，标题可换行、操作分行、卡片限制在画布内，并用ResizeObserver按实际卡片尺寸更新画布高度；已有保存的坐标不擅自重写。900x800与640x480各三主题实测通过：三卡均高94px、间隔20px，九个按钮可命中；每次只有create与draft两个写命令，expected_version=1，保存结果v2，三个引用仍绑定目标v1，重新进入可读回。修改前负证据 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/template-before/artifacts/browser-smoke/failure.txt`；修改后六案例收据 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/template-after/artifacts/browser-smoke/roundtrip.json`。

本节新增代码后的完整门禁以新收据为准；§12的稳定终验对应上一轮树。frontendDist调用链隔离仍待实施；AQ27可对本地最终候选自动验证，不应与AQ26非开发用户环境验收一起笼统视为必须真人执行。尚未完成全量目标，无发布、推送、日用版本切换或历史改写。


复核后补齐的边界：protected_bytes第二遍不再进入agents或跟随junction；每个漂移迁移候选单独拒绝私人子树、拒绝访问和链接；scratch、source、target、manifest临时写入均使用启动器同一safe_path验证，拒绝重解析祖先，避免归档路径跳出项目。对应定向集31 passed。此前没有执行任何新批量迁移。

移动交互负证据亦已复现：旧按钮连续移动会再次让卡片相交并不断压缩横向空间。现移动按可用画布宽度限制x，遇其它卡片时寻找其下方空位；y仍保存为实际用户操作结果，不改既有未操作坐标。门禁扩展到首卡移动两次、尾卡移动12次、删除后重加、保存重进逐坐标比对，以及块ID绑定历史引用。900x800与640x480各三主题均通过，所有按钮至少24px且中心可命中；保存仍只有一次draft、expected_version=1，重进保存坐标完全一致。收据 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/template-move-after/artifacts/browser-smoke/roundtrip.json`；负证据 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/template-move-before/artifacts/browser-smoke/failure.txt`。

第一次连续推进完整终验PASS：59前端文件/473测试，Python554 passed/3 skipped，tsc/Vite/A0及治理门禁通过，运行前后源树摘要de731e846917@fc5d4adc一致。此收据对应进一步移动/目标边界补齐前的树，不能代替最后修订的检查：`未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/continuation-20261009-check/final-verify.json`。最终修订另保留新收据，不覆盖此记录。


最后两项同类边界已补：.project-local/runs在任何探测或枚举前拒绝重解析点；嵌套敏感文件名仅记录排除、不stat正文、不读取或随目录迁移。当前定向34 passed。最终共享运行根主检出复测为 {"status": "PARTIAL", "bytes": 51208978876, "errors": 1169, "private": 125, "excluded_checkouts": 1}，为当前可读所属字节下界；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/storage-main.json`。

第二次完整终验前端473测试、Python557 passed/3 skipped及各治理检查通过，整体FAIL：深层截图路径在Python写文件时超过Windows传统路径长度，A0无最终收据。失败未改成PASS，收据 `未跟踪 .project-local/runs/f714401b40/codex-ui-governance-20261008/artifacts/continuation-final-20261009-check/final-verify.json`。已按既有启动器布局改用项目本体共享runs身份根存放最后终验，避免深层工作树内再次叠加整套路径，不改系统、注册表或安装目录；最后收据独立保存于 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/final/final-verify.json`，运行结论以实际内容为准。


最终共享根聚合实测PASS：前端59文件/473测试，Python560 passed/3 skipped/0 failed，tsc零输出，Vite隔离构建、生成物检查、文档/目录门禁、62/62与9/9引用、13视口×3主题A0均通过；failures为空，运行前后源码摘要a9ba5c225826@fc5d4adc一致。模板非空态含移动/删后重加/块引用的六案例纳入该A0，不再只验证空态。此段为终验后的结果登记，产品代码仍为该收据所测版本；登记后只复验文档与规范。

后续体积治理事实：主仓runs可读6,112,925,198 B，超过2 GiB预算。recovery的protected_bytes不能笼统叫编译cache：只读核对其中cargo-gnu-binaries与cargo-msvc-pdb两ZIP合计8,111,494,993 B，是恢复压缩包，须保留但应按恢复证据统计。该预算分类修正与已知candidate-q04b/q04c展开件对现存ZIP逐成员等价证明，列为后续执行项；现无新合格删除集合，不以cargo名称、退役身份或旧清单销毁资产。全量目标仍为PARTIAL。

## 14. 2026-10-09 运行体积定位与构建链继续收敛

恢复类预算口径已落实：只有build类下的Cargo编译输出可按既有规则单列，recovery/cargo-*恢复ZIP不免预算。本次主检出复算recovery为8,548,203,219 B、protected_bytes=0，超过4 GiB；runs为6,144,530,871 B，超过2 GiB。1169个测量错误和142个私人路径排除项仍保留，整体PARTIAL；没有提高预算或删除恢复资产。收据：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/storage-budget-corrected.json`。

新增storage_report.py --rank-runs，按合法identity/run两层逐项统计并按可读所属字节排序；不进入私人名字或junction，拒绝访问与排除项显示为未知。退役身份也一律UNCLASSIFIED_PRESERVE，deletion_qualified=false。实测4893个运行目录、5,908,073,262 B、1064个错误、175个排除路径，PARTIAL；仅合法运行子集，不替代runs总量。最大一批230–243 MB目录含pytest临时树、测试链接及被排除文件，尚无整批删除资格。收据：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/runs-ranked.json`。定向存储、恢复和启动器检查58 passed/1 skipped/9 subtests；前两次启动分别因测试文件名写错、复用已存在run-id未执行测试，未计PASS，纠正入口后两次定向执行均通过。

candidate-q04b/q04c的6254个成员已与保留ZIP逐名、大小、CRC32和SHA-256一致，共2,040,219,218 B展开件；该证明仅为PASS_BYTE_EQUIVALENCE_ONLY，尚缺当前消费者/恢复引用闭环，没有执行删除。收据：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/candidate-duplicate-audit/summary.json`。

构建链当前事实更正：旧Vite outDir按import.meta.url落在各checkout自身的.project-local/build/frontend-dist；当前两目录均不是junction，不应声称已实证跨worktree共用一个dist。真实缺口为偏离dev.py的git-common owner/identity路由、同一checkout并发覆盖以及产物与运行登记不一致。

2026-10-09 默认构建链已实施：`npm --prefix frontend run build` 与 `npm --prefix frontend run tauri -- build` 经 `scripts/runtime/frontend.mjs`、`scripts/runtime/frontend.py` 和 `scripts/runtime/dev.py` 分配 owner `.project-local/runs/<worktree-id>/<run-id>/artifacts/frontend-dist`。同一checkout即使继承同一个既有run，独立默认构建仍分配不同run；仅带明确父构建context和匹配overlay的Tauri beforeBuild hook复用父run。Vite生产配置验证canonical路径与overlay并拒绝CLI outDir覆盖；Node/Python两入口拒绝E/F、UNC、链接祖先和外来继承路径。Tauri最后的CLI overlay、build.rs的有效配置watcher和rustc codegen环境统一frontendDist；CI从构建receipt所指目录归档，release从其自身run目录消费归档，release freeze保持。构建产物进入既有run生命周期，不声称自动清除历史积累。

真实并发默认npm入口证据：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/4934867edc0f/artifacts/concurrent-default-npm-builds.json`，两个同时构建继承同一个父run，分别落在f7e1563248cc与834baa43fab8，各自index.html与三张品牌PNG存在。Tauri真实CLI已成功执行beforeBuild并生成其父run中的前端资源；后续Cargo因本机MSVC linker未初始化失败，失败receipt保留在 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/4934867edc0f/artifacts/tauri-attempt.json`。现已加入仅当前子进程的声明vcvars初始化，未改全局环境；未以该修法推定Tauri完成。当前writer缺少真实rt/runtime、rt/core及其manifest，最终二进制embedding、运行与安装资格仍为UNVERIFIED，未创建假runtime，未发布或替换Green。


### 2026-10-09 当前候选恢复入口（展开副本去重）

以上候选记录保留历史日期与结论。当前批次只移除与保留ZIP逐名/大小/CRC/SHA一致的展开副本，不销毁候选内容、不切换安装版。最终执行状态以cleanup-result.json为准；6254文件/2,040,219,218 B是展开文件逻辑大小，物理回收量不据此推定。

保留原ZIP与精确成员回执：
- q04b ZIP：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/legacy-scratch-20261008/runs-dirs/candidate-q04b/ArcheAxis.Knowledge.Green-v0.0.0-q04candidate-x64.zip`；成员：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/candidate-duplicate-audit/candidate-q04b.json`。
- q04c ZIP：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/legacy-scratch-20261008/runs-dirs/candidate-q04c/ArcheAxis.Knowledge.Green-v0.0.0-q04c-x64.zip`；成员：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/candidate-duplicate-audit/candidate-q04c.json`。

执行前同时持有保留ZIP、500个目录和全部成员的句柄并重新核对内容/名称；目录与文件命名流均检查，拒绝链接、占用、只读属性和未知新增内容。逐项write-ahead日志不重写全成员计划。恢复工具：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/tmp/candidate-cleanup/candidate_cleanup.py`，使用现有项目Python加`--restore`；仅恢复这两个原展开地址，校验保留ZIP与所有成员，拒绝覆盖不同内容。恢复保持名称/内容及新文件mtime，不承诺复原ACL、creation/access/目录时间。全成员计划与实际结果存放于该批次candidate-duplicate-audit目录；失败或中断可据此恢复，无须新安装或改权限。


2026-10-09 本批实际执行结果：PASS_EXACT_EXPANDED_REMOVAL，6254个展开文件/2,040,219,218 B逻辑大小已移除，500个原展开目录均按空目录逐项移除，两个展开根现不存在。原ZIP共647,537,126 B仍在，执行后SHA-256分别40ce3440f8a3ad0e4ab7a4073f90ed40f1cd6759ff5bb994f25b182ff7396d25、e6e119e62a8e8b9c0463a180ec771d58e6f909d7a44d7234139f4b270bcf9bbd，与执行前一致。6254次mark与closed均有日志，failure=null。当前结果：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/candidate-duplicate-audit/cleanup-result.json`；完整恢复计划：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/candidate-duplicate-audit/cleanup-checkpoint.json`。物理回收字节UNVERIFIED；没有按逻辑大小宣称全盘可用空间净增，没有改ACL/杀共享进程/触碰数据库或删除ZIP。本批不改变其他唯一候选/证据/退役worktree保留判断。


构建链首次聚合真实FAIL，收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/final-build-chain/final-verify.json`：Python621 passed/5 skipped、A0十三视口三主题和其它规范门禁通过，但Vitest旧代理测试按config对象读函数，1 failed/472 passed；默认npm子进程PATH继承过长，cmd找不到node；handoff两个裸脚本名歧义。已将代理测试改为解析真实serve配置（定向1 passed），引用改完整路径。PATH正反证在 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/npm-path-probe/8e3371726cd3/receipt.json`：11555→12175字符失败，231→851字符成功；只有一个PATH键，非大小写残留。仅验证driver子进程使用实际已声明工具的有限PATH，不改全局环境。原失败收据保留，修正聚合另存，不沿用首次PASS分项充当整体成功。


第二轮聚合仍FAIL，收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/final-build-chain-repaired/final-verify.json`：473前端测试、默认npm构建（source_consistent=true）、tsc、64/64与9/9引用、十三视口三主题A0均PASS；Python620 passed/1 failed/5 skipped，唯一失败是根.vite漂移。该缓存由父执行器在仓库根启动定向Vite测试产生，仅vitest/results.json一个文件。已同盘迁至共享run/artifacts/root-vitest-cache-20261009，大小/SHA读回一致，根.vite不存在；不加忽略规则掩盖漂移。迁移收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/root-vitest-cache-migration.json`。迁移该未跟踪缓存使源码身份变更，重新冻结聚合；此前失败不改写为PASS。


第三轮冻结聚合PASS：59前端文件/473测试，Python621 passed/5 skipped/40 subtests，tsc零输出，真实默认npm路由构建三品牌PNG，source_consistent=true；64/64与9/9引用、目录/文档/仓库规范、能力目录与OSS crosswalk freshness、13视口×3主题A0均通过。源码摘要运行前后23f5054ce85c@fc5d4adc一致，failures为空；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/final-build-chain-layout-corrected/final-verify.json`。5个skip仍为skip，不改成PASS。该段仅登记最终结果，产品/构建源码未再修改；登记后单独复验文档和规范。

总体目标仍PARTIAL：本轮完成候选展开副本去重、恢复预算真实统计、运行体积定位和完整frontendDist路由；Green其它独有验收供体与恢复资产保留，主根与历史运行漂移尚未全量收敛。下一步在受控候选目录准备真实Core/runtime并完成Tauri二进制embedding/运行验证，再推进安装态与物理交互资格；不由浏览器/SYNTHETIC文档桥代签，不更改日用Green或自动发布。没有commit/push/merge/release。

2026-10-09 后续实际推进：官方vcvars自动发现SDK后，Rust Core release/locked/offline构建PASS，9,136,640 B，SHA-256 `73278d9592790fd905168f848240cce6d8ce2cc6b41f0de6983febcdede4ac09`；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-core-auto-sdk-build-20261009/artifacts/core-build.json`，该次源码摘要前后 `2be3cdf4704ef34072004823028a9e74a70cf1a4c037d31d2a22b3906a529019` 一致。之后新增构建入口修复和文档映射，故该收据保留其原测试树，不能认证后续整棵修改树。Tauri候选embedding仍UNVERIFIED。

真实运行时准备使用声明共享工具根的Python3.12.13，UV_OFFLINE=1，未联网/升级锁。失败原因为缺锁定依赖缓存，未完成候选staging；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-runtime-prepare-20261009/artifacts/runtime-prepare.json`。主公共uv及uv-desktop缓存也分别offline dry-run，两者都缺aiohttp3.14.1等CP312包；不把开发环境或旧Green运行时代充锁定候选。失败生成的rt-python-input保留，不重复运行覆盖。

本次修复 `scripts/runtime/frontend.py` 的Tauri子入口：在dev.prepare之后独立构造短PATH，再调用声明的官方vcvars；检查真实x64 kernel32/ucrt库、Windows/corecrt头文件并限制cmd PATH长度，拒绝静默缺SDK的exit0。初始化命令文件保持ASCII，Unicode路径经Windows环境传递。前一次长pytest临时路径失败保持FAIL记录；短且项目内的basetemp复验：7个受影响测试文件105 passed/2 skipped，其中真实官方MSVC覆盖超长PATH和无System32输入，缺SDK/Unicode路径为fixture。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/m4/artifacts/verification.json`。目录/文档权威/仓库规范及git diff --check再次通过，没有改全局PATH、注册表、ACL或安装工具。

五个已核定主根治理文件共15,740 B迁入合法mig类，持有精确文件句柄完成同盘rename；SHA/NTFS身份/ADS/原路径消失核对PASS，历史文档追加新旧映射，未执行所存远程清理脚本。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/remaining-layout-plan/migration-result.json`；恢复工具 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/tmp/root_layout_migrate.py` 加`--restore`，已用独立fixture验证handle rename/restore；此批只减少5项根目录漂移，不回收字节。Green两个shader缓存10文件/5,346,016 B当前属主与独占读检查已核实，实际应用再生成仍NOT_EXECUTED，继续保留；未触碰Green私人目录/数据库/唯一验收资产。

## 15. 2026-10-09 正式宿主、真实模板与恢复实证

本节追加当前实证，不把前文失败或历史收据改写为通过。已在声明的 Python 3.12.13 下按原锁准备真实候选运行时，官方锁定依赖补入项目公共 uv 缓存；没有升级锁或安装全局环境。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-runtime-locked-20261009/artifacts/runtime-prepare.json` 为 PASS/source_consistent。此前失败的 2,298 文件/48,788,850 B 输入同盘保留于失败 run 的 artifacts，不覆盖。后续逐 SHA 校验 19,510 个运行时成员、362 个 wheel 公共源码成员、32 个 worker 文件、共享文件和锁定导出正文，证实实际运行材料与源码一致；旧 staging 摘要仍保留其原树，另以 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/runtime-materials-current2-20261009/artifacts/runtime-qualification.json` 联接后续源码。

实际原生运行发现两项构建缺口：生产 Cargo 配置缺少 custom-protocol feature；Windows 绝对 frontendDist 被固定版本 Tauri 的 Url 分支解析，构建完成却打开 file URL。现由 `scripts/runtime/dev.py` 生成相对 src-tauri 的目录 overlay，`scripts/runtime/frontend.py` 验证同一配置，`src-tauri/build.rs` 比较解析后的物理路径与 canonical frontend_dist 并保持相对配置拼写，生产 feature 由 Tauri CLI 启用。官方生成器只移除四个已跟踪 JSON schema 的终端 LF；首次构建 source_consistency 失败保留，四文件生成差异逐字证明后才重新冻结。相关四组测试 48 passed/2 skipped，skip 不计通过。

冻结源码摘要 `0a19591f0f8615303d2973b7fc1d6aae9a00a3a1c3ca0f611a3bcbe891c88f79` 的真实 no-bundle/locked/offline Tauri 构建 PASS，运行前后源码一致。宿主 11,406,848 B，SHA-256 `68c723e6825fac49d4e64483f2ab231526ce4615390d4469662e8989e37fb132`；宿主资源 Core 9,136,640 B，SHA-256 `73278d9592790fd905168f848240cce6d8ce2cc6b41f0de6983febcdede4ac09`。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/tauri-build-relative-20261009/artifacts/tauri-build.json`。没有发布、安装或日用 Green 切换。

正式 WebView2 Edg/154.0.4258.62 从 http://tauri.localhost/ 加载，真实有限桥接返回 schema 11/SQLite 3.51.3。13 个视口×3 个主题的几何、单行状态、命中目标与焦点对比度全部通过；实际加载 JS/CSS/三品牌 PNG 共五资源逐字 SHA 与本轮 dist 一致，39 张 PNG 尺寸与视口及请求 DPR 一致。CDP 同 session clear/set 和明确 clip 解决了探针截取边界；前后实际 DPR 严格在 1e-6 浮点误差内，未接受 1.25 冒充 1。无 synthetic bridge/DOM 注入、无 Vite 服务。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-webview-relative6-20261009/artifacts/receipt.json`；此前错误选择器、精确浮点断言及不合格 native-surface 截图证据保留。该矩阵为 REAL_TAURI_WEBVIEW2_WITH_SIMULATED_VIEWPORT_DPI，物理 DPI/IME/人工验收仍 NOT_EXECUTED。

真实候选 WebDriver 21 步通过：原创笔记保存、宿主重开、搜索、独立核验失败态、版本依据、EPUB 历史定位、XLSX/PPTX/CSV/TAR 和其余规范格式真实 worker、负例、备份及恢复后 v3→v2/CAS 等值；五次自有宿主均正常 exit 0，自有监听释放。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/j2/artifacts/qualification.json`，原始旅程 SHA `5e6fe9aa2172f999192205ed4368999372f03fc9d44ee416f4c0df0ce1e4ca35`。探针对旧输出路径、错误的全四位 driver 匹配和含说明的对象按钮选择器作三项明确适配；Microsoft 官方兼容规则为前三级版本一致，实际 driver 154.0.4258.48 与运行时 154.0.4258.62 一致。三项修复现已落入 `scripts/probes/aaos01_tauri_webdriver_loop.py`，CI 增加 canonical run 证据路径；37 个定向测试通过。复用入口 `scripts/probes/aaos01_native_ui_matrix.py` 要求本轮构建收据、源码摘要、宿主/Core SHA 绑定，并拒绝外来产物路径。

真实模板六组（900×800、640×480各三主题）已由实际 Core 创建对象、加入三个版本绑定引用、首卡移动两次/尾卡十二次、删除重加、保存为 v2、UI 关闭重开逐坐标读回。引用目标各已实际改到 v2，模板仍解析并显示 v1 历史正文，首引用块 ID 保留。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-template-roundtrip4-20261009/artifacts/receipt.json`。随后完整结束宿主，在新隔离 WebView profile 下重启同一个自有测试库，六组对象/坐标/版本/历史正文再次全部一致，页面导航不改变对象；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-template-restart-20261009/artifacts/receipt.json`。这里的内容为合成测试资料，桥接、存储、历史版本和运行宿主均为 REAL，不代签真人学习效果。

AQ27 Core 自动部分实证为 PASS：真实 SQLite 3.51.3、第二写者被拒绝、自有进程异常结束后当前 checkpoint 恢复 WAL/SHM、完整性 ok、重启文档等值；宿主已通过同 SHA Core 的实际 system_version/备份恢复旅程绑定。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/aq27-runtime-proof/retry-native-prefix/receipt.json`，SHA `93388cf0e38a3ccaaa89a3f96f4cfb69f34d48918b31ec4f21f1f93b13353249`。这纠正前文把 AQ27 整项划给真人的叙述；不可变 acceptance 包不修改，AQ26 非开发用户环境和人工签署仍未完成。

Green 两组 shader 缓存无损恢复准备 PASS：10 文件/5,346,016 B 经名称、大小、CRC、SHA 校验及实际隔离还原；唯一 ZIP 30,476 B，SHA `dd7b3c404540adc1dab27fdec08e0c0203c2ed6f49e9bfe5280a88695484bb3a`，位于 Green 自己的 backups。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/green-remaining-audit/shader-recovery-package.json`。原缓存前后全部一致，隔离还原副本已按精确清单移除；未清理原缓存、启动日用安装或读取 DB/CAS/私人 profile。没有回收字节主张。三个截图目录原位于 D:/All projects，16 文件/816,826 B 迁移再次逐 SHA 读回通过，原路径不存在；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/clarified-screenshot-directories-readback-20261009.json`。

总体仍 PARTIAL。12 张 UI-01 页面母版未供应、物理 DPI/IME、AQ26/人工旅程、当前完整安装生命周期、用户资料完整语义迁移、独有资产的剩余目录/体积处置仍未完成。以上运行实证绑定 0a1959 冻结树；随后持久化探针与本文登记后的源码需另跑门禁，不能把旧摘要冒充最新整树。

持久化入口已在 1652ed874edb 冻结树实际复验：Tauri 新宿主 SHA `f61604a3ddb99c52b9121d03e06d0461c36540287bf87c23060996a2f5798f25`，同 SHA Core 73278d…；原生矩阵39案例/5资源再次 PASS，源码与二进制前后不变。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/tauri-build-ui-final-20261009/artifacts/tauri-build.json`、`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/native-matrix-ui-final-20261009/artifacts/receipt.json`。直接执行 `scripts/probes/aaos01_tauri_webdriver_loop.py` 携本轮 --build-receipt 完成同21步，compiled_source_binding=PASS/source_consistent=true/owned_ports_released=true，收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/webdriver-445c713e3f75/tmp/journey/receipt.json`；已不依赖临时源码适配。

该树聚合门禁真实 FAIL，不能由上述运行通过代签：473前端测试、650 Python测试及其它分项通过，1个layout测试因root build/egg-info失败，仓库规范因四schema末尾LF失败。原收据保留于 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/final-native-ui/final-verify.json`。两根条目确认为本轮 setuptools wheel 生成输出，已同盘迁入自己的run/artifacts，逐成员大小/SHA读回一致且原路径不存在；不是删除或全量clean。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/wheel-route-w1/artifacts/migration.json`。`desktop/scripts/prepare_bundle.py` 现把固定 setuptools 后端的 egg_info/--egg-base 与 build/--build-base 也路由到当前run/tmp，不仅路由wheel输出与uv环境。真实uv wheel实证362公共成员与原已安装wheel完全相同、两根路径未复生，收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/wheel-route-w2/artifacts/wheel-routing.json`；该轮复用已合格解释器，不声称重做依赖安装。四schema仅允许已审核准确SHA省略终端LF，普通文件/未知schema仍拒绝，编码/CRLF/空白检查不豁免。相关staging/naming/layout定向70测试PASS，仓库规范 issue_count=0。修复后的完整聚合另行冻结，不覆盖失败收据。
本轮最终冻结树 `2ac2e3dfa143ca2eeadf8a84105a3046c03eebaef4d508195f3b44b45c9f3340` 的完整聚合门禁 PASS：前端 59 文件/473 测试、Python 701 passed/5 skipped（跳过不计 PASS）、tsc、生产前端构建、A0、目录/文档权威/仓库规范均通过，前后源码一致。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/final-native-ui-repaired/final-verify.json`。同树 Tauri 宿主 SHA `1de8add808dbe86f3f266ff0cefa805341d11873dfceaab11db25dd816a5984b`、Core SHA 73278d…：原生矩阵 39 案例/5 资源、模板操作六组及完整宿主重启六组、持久化入口完整旅程 21 步全部 PASS。收据分别为 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/native-matrix-ui-repaired-20261009/artifacts/receipt.json`、`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-template-ui-final-20261009/artifacts/receipt.json`、`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/real-template-ui-final-restart-20261009/artifacts/receipt.json`、`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/webdriver-e6e1b654d9e2/tmp/journey/receipt.json`。旅程 compiled_source_binding=PASS、source_consistent=true、owned_ports_released=true。本段为验证结束后的文档追加，不改变上述收据所认证的测试树；未更新日用安装或发布。

16 个本任务自建的隔离 tmp/webview 目录已按精确清单清理，3,527 文件/1,424 空目录、逻辑体积 173,268,287 B，目录全部不存在、句柄全部释放；物理回收量 UNVERIFIED。六项 Windows 锁保护 fixture PASS。首次自身目录枚举 sharing 冲突时实际零删除，负收据保留，修复自有 helper 后复验才执行；未绕过真实源锁。未读/hash/归档 profile 正文，所有兄弟截图/收据/SQLite/CAS 不变；原探针可重新生成测试 profile，不承诺逐字 profile 恢复。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/test-webview-cache-audit/cleanup-receipt.json`。Green 原缓存仍保留。总体仍 PARTIAL，前述未完成范围保持有效。

2026-10-09 后续 UI 增量：全能力目录在合法成功读回后清除旧 failureReason，补失败→成功→权限失败→畸形响应回归，畸形响应继续显示未知且不保留旧权限原因，保持单一 status live region。修正详情吸收来源列表的段落嵌套；SpaceView 的180ms装饰淡入在失焦、隐藏或 reduced-motion 变化时取消，初始不聚焦/隐藏/减弱动效时不启动，清理时移除监听。六项中断/禁启动回归通过；增量前端全量480测试、tsc通过，当前增量正式宿主另行冻结复验。

已对先前合格候选宿主1de8add…/Core73278d…进行20次真实新进程/新Core测试数据/新WebView profile冷启动，OS磁盘缓存保留，P95=1.4437685000011697秒（预声明3秒预算），进程树空闲工作集最大455,127,040 B（预算1GiB），20宿主全部正常退出0，host/Core前后身份一致。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/ui-performance-current-20261009/artifacts/receipt.json`。绑定已构建2ac2e3…树，不认证随后UI增量；GPU、大PDF/长列表、安装态性能与物理DPI仍未执行，不把AQ25整体标通过。性能探针自身输出已路由canonical runs，携构建收据核对宿主/Core，不复用旧run。

后续增量冻结树 `62a18aa9216aee62283f815023358544e414cee9ffa6a592cd4bda01dc9077a5`：真实Tauri构建 PASS，宿主SHA `d1c8f730da86a3b134ae4166a3555dcb0a98fcfb994ad6ed1f0e0fbc801434fc`，同Core73278d…，运行时19,510成员/362公共wheel成员/32worker逐SHA一致，无新运行时复制。正式窗口无注入39项矩阵/5资源通过后，另做同一组件的单次模拟403→真实Core capabilities_list成功恢复；旧权限原因消失、单一status保留、组件身份未重挂，原生invoke已还原。证据严格区分 SYNTHETIC_PERMISSION_FAULT / REAL_NATIVE_RENDERING / REAL_CORE_RECOVERY，不声称真实Core制造了403。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/native-ui-recovery-motion2-20261009/artifacts/receipt.json`，source_consistent、owned_cleanup均true。首次测试尝试直接改只读模块导出，故障未注入并超时，FAIL收据保留于native-ui-recovery-motion-20261009；修复自有探针后才通过，不改产品以迎合探针。当前前端59文件/480测试再次通过，tsc和仓库规范通过；UI-04中断测试为受控DOM证据，不代替物理DPI/IME/读屏人工验收。此后仅追加恢复映射文档，不冒称后续整树已重新构建。

20个本轮性能测试自建WebView缓存已按exact清单清理：3,320文件/1,360空目录，逻辑162,736,304 B，兄弟data与日志/证据保留，物理回收UNVERIFIED。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/performance-cache-audit/cleanup-receipt.json`。正式Tauri便携候选组包仍需补齐：现有assemble_green_candidate/verify_green_candidate为冻结Avalonia，单binary Core候选工具也不是宿主组包；旧assemble_distributions未涵盖当前八项资源，不用旧入口代签完整安装资格。日用Green原件及唯一资产保持有效。

CORE-R16-EXPANSION-DEDUP-20261009执行读回PASS：严格三现行文档SHA/引用及锁门禁后，3文件97,726,878 B精确删除，展开根不存在；20,601,886 B原ZIP仍为SHA590b29d…且不变。删除后实际调用隔离--restore，3成员逐SHA与mtime一致，验证副本再精确清理，未触源快照或旁边内容；物理回收UNVERIFIED。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/core-r16-duplicate-audit/post-delete-readback.json`。本轮两批删除逻辑体积合计260,463,182 B，保留原ZIP与全部测试业务数据。总体仍PARTIAL，继续正式UI和完整候选治理，不执行commit/push/发布/日用安装替换。

2026-10-09 正式便携候选适配增量：新增 scripts/release/tauri_portable_candidate.py，按当前 tauri.conf 声明的八项backend资源绑定正式宿主/Core/构建收据，只向新canonical run生成一份中文路径候选，不覆盖已有目录、不更新Green。静态门验证完整manifest成员/未知extras/路径与链接/private拒绝、native worker routes与profile一致、portable.flag及未安装/未发布标记；保留ASSERTED_NOT_VERIFIED staging provenance而不改写成源码认证。17项合成边界用例（含Windows长路径）及现有staging/runtime authority共34测试PASS；实物成员资格与原生候选旅程随后单独冻结，不以fixture代签运行。

2026-10-09 实物候选闭环：冻结树25a73c34647b79b127851c6e15be349316703e0179de1053e6c7dec106ec6f75，宿主65aadae0fe1c457dfc35682f131bb058daa5eb0de84822f269687954a27f46ff，同Core73278d…。正式Tauri中文路径候选实际19513成员/650556145 B，逐成员hash及独立verify PASS；未生成第二展开副本或ZIP。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/formal-portable-candidate3-20261009/artifacts/portable-receipt.json` 及 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/formal-portable-verify-20261009/artifacts/portable-receipt.json`。同候选完整21步原生旅程PASS、compiled_source_binding/source_consistent/owned_ports_released通过，收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/webdriver-f2bad433ad4a/tmp/journey/receipt.json`。清除两portable override后，实际marker选中candidate/data/archeaxis.sqlite，Core进程executable与数据库参数精确匹配候选，schema11、正常退出0、原始19513成员不变、owned_cleanup/source_consistent PASS；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/formal-portable-marker2-20261009/artifacts/receipt.json`。首marker探针只轮询context.pages未泵CDP事件而超时的FAIL保留，修复自有观察循环后才通过；未改产品。首次输入硬链接拒绝和公开FastAPI .agents文件误分类两次均在复制前停止，负收据保留；仅允许确定的Cargo两链接对及准确路径/sha/bytes固定的锁定上游公共文件，候选输出独立且其它private/links继续拒绝。18个新fixture及既有staging/runtime authority共36测试PASS。

业主本轮强调的总状态：整体体积治理、Human–AI完整闭环、全部开源吸收、全部模板及前后端任务均未完成；以上仅该候选工程旅程，不升格M0/R6/AAOS全任务完成。模型端点127.0.0.1:1234本轮TCP实测不可连接，不捏造机器纠错成功。当前build可读元数据下界19,450,706,037 B，存在40项排除，不是全根50多GiB的完整测量；旧2c9b88b65f debug/deps7,135,044,713 B与debug/build475,873,184 B是新定位的GB级治理目标，尚未删除，须producer/消费者/引用与恢复门通过才落实。Green日用安装未替换，私有状态/DB/CAS和唯一资产仍保留。

2026-10-09 GB级清理已实际落实（此段更正上一段“尚未删除”的当时状态）：旧 .project-local/build/2c9b88b65f/cargo/debug/deps 的2247文件/7,135,044,713 B均已精确删除、目录不存在；删除前完整2247 ZIP成员CRC/size/SHA及逐成员磁盘实际还原SHA/mtime通过，无第二展开快照。唯一恢复件 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/recovery/cargo-debug-2c9-deps-20261009/deps.zip` 为1,665,413,711 B、SHA81b6a7cb687681c7ff3137401462e43d9fbc777a8afb28f8dd39711f7b2b5ebd；同包restore.py默认只验证，--restore只恢复原exact缺失deps目录、拒覆盖/链接。扣除本批所有恢复件、工具、清单及证据后的净逻辑减少5,464,593,646 B，physical_reclaimed_bytes=UNVERIFIED。最终收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/cargo-debug-volume-audit/final-readback.json` 与deps-cleanup-result.json；producer/引用/消费者、独占read+DELETE句柄、全部成员SHA/ID/mtime守卫通过。旧debug/build、runtime、顶层API、release及当前f714构建保留；全局50多GiB治理仍PARTIAL。

全任务未完成项的当前代码依据：MachineAnswerPanel已接纠正/复测，但真实模型服务不可达，真人前后比较/效果评价仍NOT_EXECUTED；BackupPanel无产品恢复入口；正式exchange是CanonicalLibrarySpace，成组来源/笔记/证据/学习互通及外软件回读未完成；TemplateWorkspace文档读取前100，完整跨页关系仍缺验收；开源池68来源/115冲突仅7可启用插件，索引/分类不等于吸收和生命周期全完成。正式knowledge→course→lesson缺口现补3个有限bridge命令及159字节专用learning key语法，KnowledgeCoursePanel保持candidate/human_review_required、Core版本重读/渲染、文本派生课时和现有assessment/reference；未自动接受课程、未写复习结果、未发模型请求。新增8个前端回归及全量488前端测试PASS；后续当前冻结宿主原生证据另记，不以SIMULATED测试代签真人闭环。

课程真实运行发现并修正安装布局缺口：原生宿主返回503，general course worker在portable/workers旁查repo/app而找不到锁定wheel内的课时模块；负收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/webdriver-141213df9e21/tmp/journey/receipt.json` 与course-native-diagnostic2-20261009/artifacts/receipt.json保留。worker现在仅使用源码repo或当前解释器声明的purelib，不搜索另一Python/global PATH；新增隔离子进程安装布局回归，worker/renderer 22测试PASS。真实打包Python执行DERIVED且不声明正典绑定：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/course-worker-overlay-20261009/artifacts/receipt.json` PASS_REAL_PACKAGED_WORKER。仅本writer自建rt的一份worker与manifest更新，旧公共worker/manifest可从原正式便携候选准确回退，原runtime_source/provenance保留，另加source_overlay，未重复制650MB运行时、未替换日用Green。后续宿主必须重新绑定当前worker再验收，不复用原503宿主的通过标签。

课程第三次实物运行已成功创建/读取/渲染candidate课时并实测阅读区无横向溢出（synthetic-course-lesson.png），随后发现旧知识study入口和新课程study调用顺序均错：Core create_assessment先要求card_reference，UI却先assessment。现两入口均先建立knowledge reference再创建题目，原始真实拒绝保持FAIL：`未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/webdriver-17c249cc0b90/tmp/journey/receipt.json`。新增回归按Core引用前置约束拒绝错误顺序，知识/课程定向13 tests PASS；未修改Core接受规则或把未完成写入伪装复习成绩。最终source绑定原生读回仍须后续收据。

2026-10-09 最终课程工程通路PASS：冻结树ac1b89f0ad15c7879f98ea137f7590cf3aeb56e2359b3f73279cfe49e87aace6，宿主c936bd691be170b4dad9aedb7aff5b04492b9ebc5e0d2aa9b4cb4a431d5129ac，Core73278d…。当前修复宿主22步原生旅程PASS，compiled_source_binding/source_consistent/owned_ports_released均PASS；真实Core worker创建课程、读回、课时渲染，159字节course/artifact键建立知识引用→assessment→既有学习队列，并在全宿主restart后同assessment/course读回。收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/webdriver-8a1ae8a5660c/tmp/journey/receipt.json`，构建 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/tauri-build-course-loop4-20261009/artifacts/tauri-build.json`。lesson client/scroll宽586/586、pre554/554且pre-wrap；404 missing与409未接受知识拒绝真实通过。证据严格REAL_NATIVE_HOST_CORE_WORKER + SYNTHETIC_AUTHORED，review_actor=SYNTHETIC_TEST_ACTOR_NOT_HUMAN_SIGNOFF、human_signoff=false，不代签知识真人接受/机器效果/掌握；未提交复习成绩、未调用模型。前端60文件489 tests PASS，知识课程定向13、桥12、安装布局worker/renderer22 tests PASS，diff --check PASS。原前三失败探针和诊断FAIL全部保留，不因最终成功改写。此前中文portable candidate仍是其25a73旧冻结树的历史实物；此次是未安装/未发布的新工程宿主，不替换日用Green。本文本追加发生在验收后，仅文档证据更新，不冒充新编译SHA。

本轮失败原生探针自建cache也已清理，避免验证继续膨胀：exact webdriver-015734989db1/141213df9e21/17c249cc0b90 的 tmp/journey/webview，共2140 files/857 dirs/105,103,945 B；扣新增helper/证据3,352,444 B后净逻辑减少101,751,501 B，三根absent、原收据SHA不变、15个业务data/截图/log及diagnostic/最新旅程保留项不变。metadata READ_ATTRIBUTES+DELETE/source名单/PID creation/consumer守卫PASS，无读取/hash/归档profile正文；physical UNVERIFIED。最终收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/codex-ui-governance-20261009/artifacts/failed-webdriver-cache-audit/final-readback.json`。两diagnostic没有完整PIDcreation记录暂保留；最新成功旅程保留。五份Cargo recovery包共9,950,997,762 B逐archive hash匹配、正字节成员跨包重复0，已删原件恢复KEEP；三SkiaSharp NativeAssets包656,385,903 B展开payload可由原nupkg还原，但旧Avalonia assets仍依赖，SDK共同锁/离线恢复入口未闭合，NOT_EXECUTED，不裸删package留下complete marker。

当前未完成必须继续：模板100/500双重截断贯通及101/501+跨页关系；课程工程通路成功不等于最终课时阅读UI，派生Markdown中的manifest/renderer技术信息应继续分离至诊断回执，阅读面只呈现教学内容；真实模型Human-AI纠错效果、成组互通、产品恢复/安装资格、7插件生命周期与115冲突等均仍PARTIAL/NOT_EXECUTED。无commit/push/merge/release，无用户数据库/CAS迁移或日用Green替换。

2026-10-09 课时阅读面继续收敛：KnowledgeCoursePanel现展示Core绑定的知识要点及学习目标，完整原始渲染结果经既有诊断回执按钮保留；不把manifest/renderer字段放在阅读正文。新增课程教学内容在读取与渲染之间变更时拒绝展示的回归。当前KnowledgeCoursePanel定向11 tests、tsc --noEmit、git diff --check PASS；此次是SYNTHETIC前端定向证据，尚未对新UI重建宿主及复跑原生旅程，不复用上一冻结树原生PASS。模板全量分页设计需保留现排序并绑定首屏rowid水位及摘要版本，防止同秒新文档插入漏项；实现及101/501实际Core验收仍NOT_EXECUTED。整体目标继续ACTIVE/PARTIAL。

2026-10-09 模板100/500截断已补代码及分层工程验证（更正上一段当时尚未实施的状态）：Domain/API每页500+1 lookahead，固定首屏rowid水位、keyset混合排序及snapshot_count；有限base64url cursor经长度/字段/版本/所属成员校验，不放宽任意传输；兼容迁移保留的有限旧ID与created_at表示。canonical schema、生成DTO、Tauri DocumentsList与前端已贯通；模板逐页读完整成员，按8条批次读取摘要指定历史version并校验hash，后页失败/计数不一致/重复/旧合同均拒绝完整集合。刷新失败保留草稿但撤回完整集合、数量及反链声明；A0合成成功fixture同步分页合同。未新增第二库/依赖或替换Green。

真实隔离Core路由集成3 tests PASS：0/101/500边界、501两页、同秒新插入排除、跨router重启、摘要旧版本读回、迁移旧ID恰在第500项、非法cursor；收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/template-pagination-core3-20261009/artifacts/receipt.json`，source c1dc2f0569c94e470b4d7b194e652f2662d13fbb56bdce5c45adabd07cda61d8且source_consistent=true。有限桥接14 tests PASS，收据 `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/template-pagination-bridge2-20261009/artifacts/receipt.json` 对应811b4b05…（后续UI失败状态/兼容cursor修复发生在其后，不能当最终全树原生证据）。最终前端60 files/499 tests PASS，包含101/501末项反链与关系、旧合同/后页失败/重复/计数/版本及刷新失败回归；canonical run `未跟踪 D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/f714401b40/template-pagination-frontend-final2-20261009`，source51925cf53f8dd3e8363f5a271b1ab8708d665448f6da749f9512d959992c7b98。schema矩阵8、tsc与生成check、diff检查PASS。frontend-final1因启动器cwd为repo而相对node_modules路径错误FAIL保留，final2修正显式frontend root后才通过；旧fixture缺分页字段及旧文案断言的失败亦不改写。

证据级别：Core API工程集成为INTEGRATED，模板前端合成数据为SYNTHETIC；新Core exe＋正式Tauri全量501/跨页关系/重启旅程与当前课时阅读视觉门仍NOT_EXECUTED，旧Core73278候选不含分页，不复用其PASS。下一步需串行构建新的Core和宿主、绑定运行时清单后验收；本目标仍ACTIVE/PARTIAL，无commit/push/merge/release。旧tauri/release/deps另有1,038,520,462 B公开缓存候选，但既有恢复覆盖0且旧源码缺失，暂保留，不以可重编译替代原字节可恢复证据。
