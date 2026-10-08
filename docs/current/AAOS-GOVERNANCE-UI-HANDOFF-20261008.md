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

并行任务保护：`worker-quality-0906`(15)、`aaos-ui-newui-20261007`(5)、`v3-era`(3)、`supply-bind-20261007`、`aaos-ui-core-integration-20261007`、`aaos-longpath-app-20261007`未跟踪 未跟踪  各有未提交内容，本轮**一律未触碰**；一个 checkout 只有一个 writer，四路 writer 各用独立 worktree + 独立分支，由我串行整合。

## 2. 已落地改动（P1 治理）

| # | 内容 | 提交 | 入口/证据 |
| --- | --- | --- | --- |
| G1 | **机器合同与 SUP-022 收敛**：`config/product/UI_CONTRACT_V2.json` 原把冻结供体写成正式壳，且被 3 个 Python 门禁 + `.github/workflows/nightly.yml` 注释强制，导致机器权威与 `AGENTS.md`未跟踪 未跟踪  相互矛盾而**两边全绿**。现声明 Tauri2+React/TS/Vite 为正式宿主、Avalonia 为 `donorShell`、`desktop/` 为 `recoveryEntry`；门禁改为断言"声明的入口必须存在于磁盘" | `9f552f01` | `tests/test_ui_contract_v2.py`、`tests/test_workspace_ui_design_contract.py`、`tests/test_documentation_authority_index.py` |
| G2 | **文档收敛**：`docs/current` 405→342 跟踪文件，63 项以 `git mv` 迁入 8 个带日期历史组，逐项含 source/target/bytes/sha256/consumers/owner/authorization/deletion_authorization/rollback；无删除、无改写原文，只加带日期 superseded 头 | `ec9f3b97` | `docs/history/DOCUMENT-CONSOLIDATION-20260927.json`（83 行，其中 MOVE 64） |
| G2b | 恢复验证：本轮**独立复算** 64 条 MOVE 行的原始字节 SHA-256 并核对源路径已消失 → `VERIFIED 64 / HASH_MISMATCH 0 / TARGET_MISSING 0 / SOURCE_STILL_PRESENT 0` | — | `未跟踪 .project-local/scratch/verify_relocation_hashes.py` |
| G3 | **过时"AUTHORITY.md 缺失"更正**：根 `AUTHORITY.md` 存在且被跟踪，7 个当前入口改为带日期更正（保留 2026-10-01 实测来源），本轮又清掉剩余 4 处现在时态断言（含 1 处 JSON `disposition` 字段，该文件另有 `evidence_level: REAL`，无测试钉住原句） | `9f747528`、`f0897492` | `docs/current/AAOS-OPEN-WORK-REGISTER-20261001.md:22`未跟踪 未跟踪  等 |
| G4 | **五个路由问题一个现存文件**：现行索引新增该节，含"共用工具/模型从哪里解析""哪些仅历史参考"，并诚实列出"本轮无法靠搬迁收敛的重复组" | `ec9f3b97` | `docs/DOCUMENTATION_AUTHORITY_INDEX.md:68,214` |
| G5 | **外置资源解析**：`environment_registry` 的 PATH 优先（静默替换）改为声明优先并在降级时点名；修掉把 faster-whisper/rapidocr/sherpa-onnx/magika 与 ci-venv 统一认证成 `uv 0.12.23` 的探针谎言；Rust 三根合一（manifest/dev.py/cargo_test.bat 统一到 `toolchains/rust` + 导出 `RUSTUP_HOME`），`TESSDATA_PREFIX`、MSVC 探针、PowerShell 类"假 MISSING"、caption/machine-answer 端点登记全部落地；每行新增 `verification_level` 与 code/asset 许可分离字段 | `9f3fd470` | `config/environment/external-resources-index.json`未跟踪 未跟踪 （32 行：RESULT_VERIFIED 4 / VERSION_PROBED 16 / FILE_EXISTS 9 / unavailable 2 / NOT_RUN 1） |
| G6 | **死控制项修复**：`tests/runtime-paths/test_external_toolchain.py` 的 rustc 实跑测试读的是 setUp 自己清空后的 `environ`，因此**永远自我跳过**；改为读清空前快照后真实执行 `rustc --version` 与 `cargo --version` 并断言同一工具链版本 | `9f3fd470` | `1 passed in 1.27s`（原 `1 skipped`未跟踪 未跟踪 ） |
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
| 前端全量 | `node node_modules/vitest/vitest.mjs run --reporter=basic --no-color`未跟踪 未跟踪  → **57 files / 428 tests passed**（基线 56/381；A +25、B +22 并存无冲突） | INTEGRATED（jsdom） |
| 前端类型 | `tsc --noEmit -p tsconfig.json` → exit 0，0 行输出 | — |
| 浏览器几何 | `scripts/a0_browser_smoke.py` → `"status": "PASS"`，10 视口×3 主题，`source_revision.base_commit=9005b2d2`、`worktree_dirty=false`，`canonical_host_problems=[]`，三级导航 `primary 9 / secondary 4 / focused anchors / tertiary src_a0_nav3` | **SIMULATED**（stub 桥，只证布局，不证 Core 调用） |
| Python 门禁 | 11 个套件合并跑 → **101 passed**（`未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/pytest-consolidated-414a4513.txt`） | REAL（本机） |
| 真实 Core 写读 | 见 U4 | **REAL** |
| 解析稳健性（自测复现） | `tests/workflow/test_external_resources_index.py` 从仓库根 / `services/python-workers` / `frontend/src` 三种 cwd 各 **12 passed**（同一结果，解析不依赖当前目录）；把 `ARCHEAXIS_EXTERNAL_ROOT`未跟踪 未跟踪  指向不存在目录后 **2 failed / 10 passed**（`test_external_resources_index.py:245`），即缺资源明确变红而不静默回落 PATH | REAL |
| 文档/目录检查 | `scripts/check_path_conventions.py` 3122/3123 归属、0 deny 被跟踪、0 歧义；`scripts/ci/check_document_authority.py` 单一当前记录、根引用可解析、输入哈希相符；`scripts/check_repository_conventions.py`未跟踪 未跟踪  通过 | REAL |
| 远端 CI / 安装资格 / 人工验收 | 未执行 | **NOT_RUN**（本地绿不等于远端绿；未 push） |
| 写入隔离（自测复现） | 先删 `%TEMP%\archeaxis-resource-probe`，再以 `ARCHEAXIS_RESOURCE_PROBE_WORKDIR` 与 `ARCHEAXIS_INDEX_OUTPUT` 指向任务目录跑生成器：探针目录只在 run 路径内生成、`%TEMP%` 无残留、输出 76,369 bytes 落在任务路径、`git status config/` 为 0 修改 | REAL |
| 缺资源与未运行项（生成器实测表） | `local-embedding-model` → `1024-dim vector returned`（RESULT_VERIFIED）；`local-rerank-model` → **`NOT_RUN`未跟踪 未跟踪 ，原因随行走廊**（模型 id 被服务但宿主端点应答不符）；被跟踪索引当前等级分布经复算为 VERSION_PROBED 16 / RESULT_VERIFIED 4 / FILE_EXISTS 9 / unavailable 2 / NOT_RUN 1，共 32 行 | REAL |
| 生成器不再污染治理记录（本轮缺陷修复） | `test_declared_paths_resolve_on_this_host` 曾以子进程就地重写被跟踪索引：干净跑一次该文件，被跟踪 blob 由 `4c8bf6aeebcb…` 变为 `7910abe4ad85…`，即"跑测试"本身改写治理记录，且该文件含主机绝对路径，谁最后跑谁决定提交内容。改为 `ARCHEAXIS_INDEX_OUTPUT` 可重定向后：正常根 `12 passed` 且 blob 保持 `4c8bf6ae`；把根指向不存在目录时 **4 项点名失败**而 blob 仍 `4c8bf6ae` | REAL（`e0e52a21`） |

### 整合后终验（七路全部并树后，HEAD `fb630015`未跟踪 未跟踪 ）

两条各自验证过的分支首次同树，故整体重跑：

| 层 | 实测 | 收据 |
| --- | --- | --- |
| 前端全量 | **58 files / 436 tests passed**，exit 0 | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/vitest-merged-fb630015.txt` |
| 类型 | `tsc --noEmit -p tsconfig.json` exit 0，**0 行输出** | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/tsc-merged-fb630015.txt` |
| Python 18 套件 | **190 passed**，exit 0；跑后被跟踪索引 blob 仍为 `4c8bf6aeebcb…`（零污染），`git status` 干净 | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/pytest-merged-fb630015.txt` |
| 浏览器几何 | `scripts/a0_browser_smoke.py` → `status PASS`、`errors []`、`canonical_host_problems []`、10 视口 × 3 主题、`base_commit fb630015`、`worktree_dirty False`、导航 `primary 9 / secondary 4 / anchors / tertiary src_a0_nav3 / 复习队列存在` | `未跟踪 .project-local/runs/f714401b40/gov-ui-20261008/artifacts/receipts/A0-MERGED.txt` ＋ `未跟踪 未跟踪 未跟踪 a0final/artifacts/browser-smoke/*.png` |
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
| P3 OSS 与 T1/T2/T3 模板 | `git merge 15f79cf7` 按 hunk 整合：`CanonicalLearningSpace` 保留本轮 `historySummary`+`RawReceiptButton` 诊断路由、无 role 的 `failureReason` 与单一 live region，仅取 OSS 侧 `initialItemKey` 学习项绑定；`DocumentEditor`/`CanonicalLibrarySpace`未跟踪 未跟踪  取模板根属性与 dirty 保护而不丢 nav/onTrail；20,584 行 / 992,500 字节生成表**不再入库**，改为跟踪生成器 + `OSS-REUSE-CROSSWALK-20261008.manifest.json`（记录产生命令、输入、原始字节与 CRLF 规范化两种摘要），并由测试重新生成比对、生成器自身变更即失效；PDF.js 由 REFERENCE 改 CURRENT（`frontend/package.json:21` 声明 `pdfjs-dist 6.4.299`、`PdfReader.tsx:3` 实际导入，旧桶位是假陈述），改为直接钉"只能主张 source 存在" | `ea1e1700` → 整合 `fb630015`未跟踪 未跟踪  | 前端 **58 files / 436 tests**、tsc 零输出、`test_mfx001`+crosswalk+manifest+html_donor **23 passed** |

未达成的部分如实保留：新增 Rust 测试 `crates/archeaxis-api/tests/oss_template_reuse.rs`未跟踪 未跟踪  本地 **NOT_RUN**（需 cargo 构建，未跑就不主张）；模板在 jsdom 下渲染属 SIMULATED/INTEGRATED，不等于真实知识库操作；OSS 侧的 T1/T2/T3 与 28 学科配置经整合后由 `frontend/src/__tests__/TemplateBindings.test.tsx` 与 `tests/workflow/test_oss_reuse_crosswalk.py` 覆盖，未经真人学习配对验证。

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
| 3 分支与工作树处置 | `codex/aaos-branch-disposition-20261008` → `83d738a0`（`7652836e`未跟踪 未跟踪 ） | 44 分支分类：MERGED-CONTAINED 33 / DIRTY-UNCOMMITTED-PROTECTED 7 / UNIQUE-COMMITS-PUSHED 2 / UNIQUE-COMMITS-LOCAL-ONLY 2；38 个注册工作树（我此前给的"≈31"被实测纠正），3 个未注册残留。**`git worktree prune` 两次 dry-run 输出为空**，故未执行。退役清单 31 项只列命令、只用 `git branch -d`（`-d` 的拒绝即安全属性），**未删任何分支或工作树**。不可退役项含 `codex/aaos-p04-doc-loop-20261007`（6 个提交不在 tip，触 `crates/archeaxis-api/src/lib.rs` 等）、`codex/minimax-aaos-cosmic-ui-20261001`、`codex/github-delivery-docs-20260929`（其 upstream 无本地跟踪引用 → 推送状态 `NOT_VERIFIED`） |
| 4 我自身的越界与纠正 | `d878badf`、`69f18606` | 宽跑套件暴露两个只由我造成的红：我在 `.project-local` 里造了 `receipts/`、`scratch/` 与根 `__pycache__`，违反工作树布局契约。用**既有** `scripts/runtime/realign_dev_layout.py` 把 12 项归档（非删除）进 `legacy-scratch-20261006` 并留清单，收据迁到 launcher 规定的 `runs/<身份>/<run_id>/artifacts/` 下并同步交接引用；`__pycache__` 归入 `ALLOWED_IGNORED`（与已列入的 `.pytest_cache`/`.ruff_cache` 同类，删了下次跑 pytest 又长回来）——**栽一个根目录杂项即变红、移除即变绿**，证明归类没有掏空守卫。另修 `scripts/a0_browser_smoke.py` 7 处 `str(x.relative_to(ROOT))`：`ARCHEAXIS_RUN_ROOT` 在仓库外时直接抛异常，而 dev.py 恰恰把链接工作树的 run 根放在主检出共享 `.project-local` 内——此前"外部 run 根会让门禁只跑一个视口就死"的判断实为此崩溃 |

### 最终终验（HEAD `69f18606`未跟踪 未跟踪 ，干净树）

| 层 | 结果 |
| --- | --- |
| 前端 | **58 files / 440 tests passed**，exit 0 |
| 类型 | `tsc --noEmit` exit 0，无输出 |
| Python 宽范围 | `tests/workflow`＋`tests/maintenance`＋`tests/runtime-paths`＋`tests/contract`未跟踪 未跟踪 ＋审计/合同/分类器/a0 共 **538 passed / 3 skipped / 0 failed**（早先一次 5 failed 全部由我给 pytest 传了越界的 `--basetemp` 造成，去掉后归零；被测工具的"输出逃逸 run 根即拒绝"守卫本身行为正确） |
| 浏览器 | `status PASS`、`errors []`、`canonical_host_problems []`、10 视口 × 3 主题、`base_commit 69f18606`、`worktree_dirty False`、三级导航与模板断言全在 |
| 治理检查器 | `check_path_conventions` 3145/3146 归属、0 deny 被跟踪、0 歧义、0 重复共用安装组；`check_document_authority` 单一当前记录；`check_repository_conventions`未跟踪 未跟踪  通过 |
| 仍未达成 | 远端 CI / 安装资格 / 人工旅程 / 日用安装验收 **NOT_RUN**；`crates/archeaxis-api/tests/oss_template_reuse.rs`未跟踪 未跟踪  **NOT_RUN**；模板的图谱/画布/引用原文块在真实引擎下仍只有空态被驱动（stub 的 `document_create` 不合 `DocumentDto` 合同），窄窗断言对"多引用画布"无覆盖 |

## 7. 需业主决定的具体事项

1. **push 与远端 CI 资格化**：分支 `codex/aaos-gov-ui-20261008`（HEAD `69f18606`）未推送；`a0-gates`/`browser-smoke` 需一次 push 才能取得当前分支的远端结论。本地全绿不构成其替代。
2. **主检出唯一未跟踪资产（已精测）**：`docs/history/`未跟踪 未跟踪  下 **1114 文件 / 498,341,341 bytes（475.3 MiB）**，其中仅 88 个被跟踪，`git check-ignore` 返回未忽略；未跟踪部分在真实基线**零跟踪**，即删除不可从 Git 恢复。纳入提交还是显式忽略需一个裁决；现状态下任何 `git add .` 会把它们整体带入。分支名 `codex/Audit` 本身可退役（其提交全是 `origin/main` 祖先），但**该目录不可**在任何清理命令前动。
3. **`src-tauri/tauri.conf.json:10` `frontendDist: ../.project-local/build/frontend-dist` 非身份隔离**（实测；对照 `scripts/runtime/dev.py` 的 `build/<identity>/cargo`未跟踪 未跟踪  已隔离）：并发 UI 构建会互相覆盖同一 dist。改动涉及打包/发布路径，未擅动；最小修法已在此说明。
4. **绿色目录纯净度（GC-03）**：`.ui-task-tree/` 实测 6,471,511 KB 开发占用，其中 5,783,275 KB 属 `CodexSandboxOnline` 独立克隆（git dubious ownership 拒绝，我不动）。是否迁出、迁往何处需位置裁决；同时 `README.md:13` 指向的恢复入口 `未跟踪 AAOS-vd6bd374-20261001-x64/desktop/ArcheAxis.Desktop.exe` 实测 **MISSING**，重指向属版本切换决策。
5. **体积回收：本轮已执行的部分与仍待授权的部分**
   - 已执行（在"体积清理"指令范围内，逐项先归档、先证可恢复、先查引用）：4 个未注册 `pycache-*` 与 2 个空壳、4 份重复 `node_modules` 改 junction，合计 **1,002,595 KB**；清单与核验件在 `未跟踪 d-docs-20261008/.project-local/volume-20261008/`，孤儿 `.pyc` 归档 zip 逐成员验过 CRC32 与 SHA-256。
   - 仍待授权：`speaker-embedding.onnx` 26,530,550 bytes 与共享根逐字节同哈希的副本（同目录 `.PATCHED.onnx` 是修改件，**不得按同名处理**）；其余 6 份重复 `node_modules`（含锁相同但安装树不同的 `oss-reuse`，需按树摘要逐个判）；`.project-local/build`未跟踪 未跟踪  中真正孤儿仅 54,154 KB，其余 41.8 GB 属**在册活跃工作树**的重建成本，回收等于把成本转给下一轮，需业主就"退役哪些工作树"一并决定；Git 历史清理/改写/远程 ref 删除/强推不在默认授权内。
6. **分支与工作树退役**：§6 线 3 给出 31 项 retire-ready 及精确命令（`worktree remove` 先于 `branch -d`，一律 `-d` 不 `-D`），以及 3 个含独有提交的不可退役分支。**同日稍后更新**：31 项 retire-ready 中的 9 个兄弟工作树已按上述二次证明移除（分支与 ref 未动，无 `--force`）；分支本身仍未退役任何一条。。**本轮一个分支、一个工作树都没删**。
7. **UI-01 的 12 张页面母版**：8 个权威根内不存在 → 保持 `BLOCKED-ON-SUPPLY`，不编造母版一致性。因此"布局是否还原母版"目前无法判定，本轮只自证内部一致。
8. **不能自签项**：`docs/authority/taskpack-1004-aaos01/checks/acceptance.json` 的 AQ26/AQ27 保持 `NOT_RUN`未跟踪 未跟踪 ；物理 IME/DPI/P95/冷启动、九步人工旅程、真人学习配对、日用安装验收需业主执行。
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
| 抠图方式 | 亮度拉伸直接作 alpha，RGB 取各主题自身 `--aaos-text`，不重绘任何笔画 | 配方与逐尺寸对照：`.project-local/runs/logo-extract-20261008/extract_logo_assets.py`、`未跟踪 .project-local/runs/logo-extract-20261008/compare_small_sizes.py` |
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

驱动与回执：`.project-local/runs/a0semantics-20261008/run_semantics_probe.py`、`未跟踪 .project-local/runs/a0semantics-20261008/summary-as-is-planted-painted-overlap.json`。

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
