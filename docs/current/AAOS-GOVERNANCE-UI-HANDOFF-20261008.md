# AAOS 治理收敛与正式 UI 完成 — 分支交接（2026-10-08）

分支 `codex/aaos-gov-ui-20261008`，基线 `a8d2e0bb`（= `origin/main` + 22 个 UI 提交）。
本文只作导航与状态汇总：不复制任务包、不复制大表、不新建总账；数字与结论一律指向本轮实测收据与文件路径。

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
| G1 | **机器合同与 SUP-022 收敛**：`config/product/UI_CONTRACT_V2.json` 原把冻结供体写成正式壳，且被 3 个 Python 门禁 + `nightly.yml` 注释强制，导致机器权威与 `AGENTS.md` 相互矛盾而**两边全绿**。现声明 Tauri2+React/TS/Vite 为正式宿主、Avalonia 为 `donorShell`、`desktop/` 为 `recoveryEntry`；门禁改为断言"声明的入口必须存在于磁盘" | `9f552f01` | `tests/test_ui_contract_v2.py`、`tests/test_workspace_ui_design_contract.py`、`tests/test_documentation_authority_index.py` |
| G2 | **文档收敛**：`docs/current` 405→342 跟踪文件，63 项以 `git mv` 迁入 8 个带日期历史组，逐项含 source/target/bytes/sha256/consumers/owner/authorization/deletion_authorization/rollback；无删除、无改写原文，只加带日期 superseded 头 | `ec9f3b97` | `docs/history/DOCUMENT-CONSOLIDATION-20260927.json`（83 行，其中 MOVE 64） |
| G2b | 恢复验证：本轮**独立复算** 64 条 MOVE 行的原始字节 SHA-256 并核对源路径已消失 → `VERIFIED 64 / HASH_MISMATCH 0 / TARGET_MISSING 0 / SOURCE_STILL_PRESENT 0` | — | `.project-local/scratch/verify_relocation_hashes.py` |
| G3 | **过时"AUTHORITY.md 缺失"更正**：根 `AUTHORITY.md` 存在且被跟踪，7 个当前入口改为带日期更正（保留 2026-10-01 实测来源），本轮又清掉剩余 4 处现在时态断言（含 1 处 JSON `disposition` 字段，该文件另有 `evidence_level: REAL`，无测试钉住原句） | `9f747528`、`f0897492` | `docs/current/AAOS-OPEN-WORK-REGISTER-20261001.md:22` 等 |
| G4 | **五个路由问题一个现存文件**：现行索引新增该节，含"共用工具/模型从哪里解析""哪些仅历史参考"，并诚实列出"本轮无法靠搬迁收敛的重复组" | `ec9f3b97` | `docs/DOCUMENTATION_AUTHORITY_INDEX.md:68,214` |
| G5 | **外置资源解析**：`environment_registry` 的 PATH 优先（静默替换）改为声明优先并在降级时点名；修掉把 faster-whisper/rapidocr/sherpa-onnx/magika 与 ci-venv 统一认证成 `uv 0.12.23` 的探针谎言；Rust 三根合一（manifest/dev.py/cargo_test.bat 统一到 `toolchains/rust` + 导出 `RUSTUP_HOME`），`TESSDATA_PREFIX`、MSVC 探针、PowerShell 类"假 MISSING"、caption/machine-answer 端点登记全部落地；每行新增 `verification_level` 与 code/asset 许可分离字段 | `9f3fd470` | `config/environment/external-resources-index.json`（32 行：RESULT_VERIFIED 4 / VERSION_PROBED 16 / FILE_EXISTS 9 / unavailable 2 / NOT_RUN 1） |
| G6 | **死控制项修复**：`tests/runtime-paths/test_external_toolchain.py` 的 rustc 实跑测试读的是 setUp 自己清空后的 `environ`，因此**永远自我跳过**；改为读清空前快照后真实执行 `rustc --version` 与 `cargo --version` 并断言同一工具链版本 | `9f3fd470` | `1 passed in 1.27s`（原 `1 skipped`） |
| G7 | **体积分类与回收清单**：按类别分别实测（Git 历史/跟踪树/ignored 产物/各 worktree/重复占用/共用根），明说 Git 历史不可减、跟踪字节本轮**净增** 406,580 bytes；`docs/current` 收敛只是把字节搬进 `docs/history`，不是瘦身 | `9005b2d2` | `docs/current/REPOSITORY-CLEANUP-HANDOFF-20260921.md` 2026-10-08 批次节 |
| G8 | **运行不得膨胀落地到维护规范**：`docs/VERIFICATION_POLICY.md` 新增该节，规则挂到既有 `dev.py`（精确 worktree 根、忽略校验、按身份哈希分目录、per-run tmp/logs/artifacts、`ARCHEAXIS_RUN_ID`）与 junction 复用机制；未新建体系、未建定时删除器 | `9005b2d2` | — |
| G9 | **绿色仓库边界复测**：身份冲突与断链登记（见 §5） | `969c6130` | `docs/current/AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md` 2026-10-08 节 |
| G10 | 共用资源人工根索引指向唯一机器入口，消除"各写一套路径说明" | `72e2e7f1` | `docs/SHARED_RESOURCE_PATH_INDEX.md` |

## 3. 已落地改动（P2 UI 与门禁）

| # | 审计问题 | 处置 | 证据 |
| --- | --- | --- | --- |
| U1 | 两项静态真相门禁可被"清空正文/空扫描列表"骗过 | 抽出唯一扫描器 `frontend/src/__tests__/support/productSourceScan.ts`，正反用例共用；空集、少于下限、必需目标缺失、根不存在一律 **throw** 而非返回空 offender 列表；反向用例改为驱动生产扫描函数 | `9b306242`；用例数 3→15、4→17；`vitest-integrated.txt` |
| U2 | 原始 payload 仍在阅读面 | `CanonicalLearningSpace.tsx:96` 历史 JSON、`CanonicalCapabilitiesSpace.tsx:89` observation JSON 改为人类可读摘要 + 既有 `RawReceiptButton`；未新建诊断系统。全树 `grep '<pre>{JSON'` 现只剩 `DiagnosticConsole.tsx:33` | `da952cd5` + 本轮 grep 自证 |
| U3 | 多个 `role="status"` 并存（Exchange 最多 4 个） | 按播报事件收敛：持续态/静态派生/占位句去掉 role（可见文本保留），失败态合并为一个区域；`failureReason` 无 role 的修正保留；知识页 `getAllByRole('status')==1` 未削弱并扩到学习页与能力页 | `LiveRegionBudget.test.tsx`（15 用例）、`CoreFailureStates.test.tsx` 扩展 |
| U4 | 真实 Core 闭环 | `scripts/verification/core_roundtrip.py`：真实 **release** Core（9,115,136 bytes，`sha256 4ada192d…`）上 `document_create` 201 → `document_draft` 200 → **停进程、同数据根重启** → `document_get`/`document_version` 200，`version=2`、`content_sha256 c59ddc38…`、`editor_json` 与历史 v1 逐字节一致，`roundtrip_errors=[]` | `c94c7259`；`.project-local/coredemo/receipt/run2/RESULT.md` |
| U5 | 浏览器门禁依赖临时 Shell 环境 | `a0_browser_smoke.py` 的 `shutil.which('node')` 失败即哑叫"缺 Node"，改为回落声明索引 `ext.toolchains.nodejs-lts`；反证：PATH 清到只剩系统目录时仍解析出 `24.18.0/node.exe`，把索引指向不存在路径时返回 `None` 并在错误里列出已查询源 | `fd3754d8` |

## 4. 验证（本轮实跑，分级）

| 层 | 命令 / 结果 | 级别 |
| --- | --- | --- |
| 前端全量 | `node node_modules/vitest/vitest.mjs run --reporter=basic --no-color` → **57 files / 428 tests passed**（基线 56/381；A +25、B +22 并存无冲突） | INTEGRATED（jsdom） |
| 前端类型 | `tsc --noEmit -p tsconfig.json` → exit 0，0 行输出 | — |
| 浏览器几何 | `scripts/a0_browser_smoke.py` → `"status": "PASS"`，10 视口×3 主题，`source_revision.base_commit=9005b2d2`、`worktree_dirty=false`，`canonical_host_problems=[]`，三级导航 `primary 9 / secondary 4 / focused anchors / tertiary src_a0_nav3` | **SIMULATED**（stub 桥，只证布局，不证 Core 调用） |
| Python 门禁 | 11 个套件合并跑 → **101 passed**（`.project-local/receipts/pytest-consolidated-414a4513.txt`） | REAL（本机） |
| 真实 Core 写读 | 见 U4 | **REAL** |
| 解析稳健性（自测复现） | `tests/workflow/test_external_resources_index.py` 从仓库根 / `services/python-workers` / `frontend/src` 三种 cwd 各 **12 passed**（同一结果，解析不依赖当前目录）；把 `ARCHEAXIS_EXTERNAL_ROOT` 指向不存在目录后 **2 failed / 10 passed**（`test_external_resources_index.py:245`），即缺资源明确变红而不静默回落 PATH | REAL |
| 文档/目录检查 | `check_path_conventions.py` 3122/3123 归属、0 deny 被跟踪、0 歧义；`check_document_authority.py` 单一当前记录、根引用可解析、输入哈希相符；`check_repository_conventions.py` 通过 | REAL |
| 远端 CI / 安装资格 / 人工验收 | 未执行 | **NOT_RUN**（本地绿不等于远端绿；未 push） |
| 写入隔离（自测复现） | 先删 `%TEMP%\archeaxis-resource-probe`，再以 `ARCHEAXIS_RESOURCE_PROBE_WORKDIR` 与 `ARCHEAXIS_INDEX_OUTPUT` 指向任务目录跑生成器：探针目录只在 run 路径内生成、`%TEMP%` 无残留、输出 76,369 bytes 落在任务路径、`git status config/` 为 0 修改 | REAL |
| 缺资源与未运行项（生成器实测表） | `local-embedding-model` → `1024-dim vector returned`（RESULT_VERIFIED）；`local-rerank-model` → **`NOT_RUN`，原因随行走廊**（模型 id 被服务但宿主端点应答不符）；被跟踪索引当前等级分布经复算为 VERSION_PROBED 16 / RESULT_VERIFIED 4 / FILE_EXISTS 9 / unavailable 2 / NOT_RUN 1，共 32 行 | REAL |
| 生成器不再污染治理记录（本轮缺陷修复） | `test_declared_paths_resolve_on_this_host` 曾以子进程就地重写被跟踪索引：干净跑一次该文件，被跟踪 blob 由 `4c8bf6aeebcb…` 变为 `7910abe4ad85…`，即"跑测试"本身改写治理记录，且该文件含主机绝对路径，谁最后跑谁决定提交内容。改为 `ARCHEAXIS_INDEX_OUTPUT` 可重定向后：正常根 `12 passed` 且 blob 保持 `4c8bf6ae`；把根指向不存在目录时 **4 项点名失败**而 blob 仍 `4c8bf6ae` | REAL（`e0e52a21`） |

### 整合后终验（七路全部并树后，HEAD `fb630015`）

两条各自验证过的分支首次同树，故整体重跑：

| 层 | 实测 | 收据 |
| --- | --- | --- |
| 前端全量 | **58 files / 436 tests passed**，exit 0 | `.project-local/receipts/vitest-merged-fb630015.txt` |
| 类型 | `tsc --noEmit -p tsconfig.json` exit 0，**0 行输出** | `.project-local/receipts/tsc-merged-fb630015.txt` |
| Python 18 套件 | **190 passed**，exit 0；跑后被跟踪索引 blob 仍为 `4c8bf6aeebcb…`（零污染），`git status` 干净 | `.project-local/receipts/pytest-merged-fb630015.txt` |
| 浏览器几何 | `a0_browser_smoke.py` → `status PASS`、`errors []`、`canonical_host_problems []`、10 视口 × 3 主题、`base_commit fb630015`、`worktree_dirty False`、导航 `primary 9 / secondary 4 / anchors / tertiary src_a0_nav3 / 复习队列存在` | `.project-local/receipts/A0-MERGED.txt` ＋ `a0final/artifacts/browser-smoke/*.png` |
| 可视复核 | 我打开两帧确认：library 帧显示资料库（4 个对象分组、人类可读文案、无 JSON），learning 帧显示学习页（失败态"不兼容：本地核心的返回不符合当前合同，已停止而未按成功显示"）——文件名与画面内容一致 | 同上 |
| 未跑项 | 新增 Rust 测试 `crates/archeaxis-api/tests/oss_template_reuse.rs` **NOT_RUN**（未跑就不主张）；远端 CI、安装资格、真人旅程、日用安装验收 **NOT_RUN** | — |

依赖变化：**无**。`package.json`/`package-lock.json`/`Cargo.toml`/`Cargo.lock`/`pyproject`/`uv.lock`/`.csproj` 均未被本轮改动（`git diff --name-only` 过滤实证）；新 worktree 经 junction 复用既有 `node_modules`，未复制大型共用资源。

## 5. 诚实性与 OSS 整合（已落地，原为在飞）

两路 writer 中途停摆且未提交，由我停止其代理、接管各自 checkout 后收口（保持"一个 checkout 一个 writer"）。

| 项 | 落地 | 提交 | 实测 |
| --- | --- | --- | --- |
| 审计项 5 引用完整性 | `scripts/audit/reference_validation.py`（580 行，带 `--record/--scan-evidence/--root/--json` CLI）取代按 basename 全树 `rglob` 的旧法：精确路径 + 声明根内解析、按记录哈希或提交核身份、同名歧义列双方并拒绝、裸 basename 永不通过、绝对路径与越出根的 `..` 一律拒、历史引用可解析但标记且不被同名件自动满足、判定类不折叠 | `15f0e6de` | `tests/test_reference_validation.py` **18 passed**，含"旧规则对这些故障全盲"的反证用例 |
| 审计项 6 生成器诚实性 | `scripts/audit/emission_discipline.py`：数字必须来自 resolver（模板里留字面数字即构造期拒绝）、不可重算者以 `CLAIM`/`INSUFFICIENT-EVIDENCE` 具名输出、手写标记被 `scan_unproduced` 拒、`check_written` 复核**落盘字节**、生成器打印自己算出的 tally 而不再声称"全部由磁盘重算" | `15f0e6de` | `tests/test_emission_discipline.py` **13 passed**（把审计里 `（前端 365、Rust 526）`、`PASS/CI(force_full)` 原文当作栽入故障） |
| 审计项 4 证据哈希 | 台账新增带日期更正节：`receipt.raw.log` 4,114 B / `0cf9deba…`、`summary.json` 1,865 B / `0294d344…`、记录值 `2d3c69a5…` 对两者任何可辨识形式均不匹配且穷举 artifacts 无命中 → 来源记为**不可证**，不猜测、不重跑凑值；同时记捕获缺陷（JSON 正文恰在 char 4000 截断，与 `coverage_caveat` 的"从未截断"矛盾，该条改判 REFUTED，而 `machine.answer` 的 REAL 判定按回执内容与 Core 身份保留）；原工件与旧值未改 | `15f0e6de` | 两个哈希由我本轮 `sha256sum` 独立复算，非转述 |
| P3 OSS 与 T1/T2/T3 模板 | `git merge 15f79cf7` 按 hunk 整合：`CanonicalLearningSpace` 保留本轮 `historySummary`+`RawReceiptButton` 诊断路由、无 role 的 `failureReason` 与单一 live region，仅取 OSS 侧 `initialItemKey` 学习项绑定；`DocumentEditor`/`CanonicalLibrarySpace` 取模板根属性与 dirty 保护而不丢 nav/onTrail；20,584 行 / 992,500 字节生成表**不再入库**，改为跟踪生成器 + `OSS-REUSE-CROSSWALK-20261008.manifest.json`（记录产生命令、输入、原始字节与 CRLF 规范化两种摘要），并由测试重新生成比对、生成器自身变更即失效；PDF.js 由 REFERENCE 改 CURRENT（`frontend/package.json:21` 声明 `pdfjs-dist 6.4.299`、`PdfReader.tsx:3` 实际导入，旧桶位是假陈述），改为直接钉"只能主张 source 存在" | `ea1e1700` → 整合 `fb630015` | 前端 **58 files / 436 tests**、tsc 零输出、`test_mfx001`+crosswalk+manifest+html_donor **23 passed** |

未达成的部分如实保留：新增 Rust 测试 `crates/archeaxis-api/tests/oss_template_reuse.rs` 本地 **NOT_RUN**（需 cargo 构建，未跑就不主张）；模板在 jsdom 下渲染属 SIMULATED/INTEGRATED，不等于真实知识库操作；OSS 侧的 T1/T2/T3 与 28 学科配置经整合后由 `TemplateBindings.test.tsx` 与 `test_oss_reuse_crosswalk.py` 覆盖，未经真人学习配对验证。

### 已核实的门禁边界（对我先前一句过宽说法的收窄）

穷尽 `grep TemplateLauncher frontend/src` 的结果只有三处：`CanonicalLibrarySpace.tsx:16` 导入、`:385` 挂载、`TemplateBindings.test.tsx:5/:71` **独立渲染该组件**。因此准确说法是：

- **已有守卫**：`TemplateBindings.test.tsx` 覆盖组件自身逻辑，包括"拒绝放弃脏模板属性时保持展开"这条真实行为（`window.confirm` 返回 false → `details.open` 仍为 true、草稿值保留）。
- **确实无守卫**：**没有任何测试断言资料库页面挂载了它**（`grep 学科模板 frontend/src/__tests__/*.tsx` 为空），浏览器门禁也不覆盖。删掉 `:385` 那一行，58 文件 / 436 测试与 A0 全绿。
- 该缺口由并行线 2（`codex/aaos-ui-templates-20261008`）关闭，要求含"拆掉挂载必须变红"的反证；本轮不在我的工作树重复实现，以免与它在前端文件上互相覆盖。

## 6. 需业主决定的具体事项

1. **push 与远端 CI 资格化**：分支 `codex/aaos-gov-ui-20261008`（HEAD 见 §7）未推送；`a0-gates`/`browser-smoke` 需一次 push 才能取得当前分支的 CI 结论。
2. **主检出 468 MB 唯一未跟踪资产**：`docs/history/{task-artifacts 817 文件 344,955 KB, desktop-attachments 17/124,520 KB, evidence 68/1,028 KB, closure-tasks 12/68 KB, skill-call-index.json 1/4 KB}` 在真实基线**零跟踪**（我逐目录核对），即删除不可从 Git 恢复，且当前既未跟踪也未被忽略——纳入提交还是显式忽略，需一个裁决；现状态下任何 `git add .` 会把它们整体带入。
3. **`src-tauri/tauri.conf.json:10` `frontendDist: ../.project-local/build/frontend-dist` 非身份隔离**（实测；对照 `dev.py` 的 `build/<identity>/cargo` 已隔离）：并发 UI 构建会互相覆盖同一 dist。改动涉及打包/发布路径，未擅动；最小修法已在此说明。
4. **绿色目录纯净度（GC-03）**：`.ui-task-tree/` 实测 6,471,511 KB 开发占用，其中 5,783,275 KB 属 `CodexSandboxOnline` 独立克隆（git dubious ownership 拒绝，我不动）。是否迁出、迁往何处需位置裁决；同时 `README.md:13` 指向的恢复入口 `AAOS-vd6bd374-20261001-x64/desktop/ArcheAxis.Desktop.exe` 实测 **MISSING**，重指向属版本切换决策。
5. **回收清单执行授权**（全部未执行）：`pycache-*` 4 目录 186,871 KB、10 份重复 `frontend/node_modules`（≈1.87 GB 同锁文件重复安装）、与共享根逐字节同哈希的 `speaker-embedding.onnx` 26,530,550 bytes 副本（同目录 `.PATCHED.onnx` 是修改件，**不得按同名处理**）。Git 历史清理/改写/远程 ref/强推不在默认授权内。
6. **UI-01 的 12 张页面母版**：8 个权威根内不存在 → 保持 `BLOCKED-ON-SUPPLY`，不编造母版一致性。
7. **不能自签项**：`checks/acceptance.json` 的 AQ26/AQ27 保持 `NOT_RUN`；物理 IME/DPI/P95/冷启动、九步人工旅程、真人学习配对、日用安装验收需业主执行。
8. **cross-encoder 重排**：fail-closed 属业主模型装载，非代码缺陷；caption/embedding/rerank 属 loopback 端点，`11434` 关闭而 `1234` 曾被证实可用，不得称"Ollama 阻塞"。

## 7. 整合顺序与回退

```
基线 a8d2e0bb
 └─ 5ab344f1 integrate uigates   (9b306242)      frontend/src/__tests__ + support 扫描器
 └─ 1d38e938 integrate uia11y    (da952cd5)      spaces/components + LiveRegionBudget
 └─ 93e335cb integrate resindex  (9f3fd470)      config/environment + scripts + services + tests
 └─ b3cf63cd integrate docs      (ec9f3b97,9f747528) docs/current→docs/history
 └─ 9f552f01 合同收敛  969c6130 绿色复测  9005b2d2 体积与规则  fd3754d8 node 解析  f0897492 断言更正
 └─ 414a4513 integrate coredemo  (c94c7259)      scripts/verification/core_roundtrip.py
 └─ 待：honesty、oss 整合
```

五路 writer 路径互不重叠，整合**无冲突**（`git merge --no-ff` 五次全部 exit 0）。回退：任一分支提交可单独 `git revert`；文档搬迁的回退由清单逐行给出（`git mv` 反向 + 目标字节与哈希比对）；未使用任何破坏性操作，故不存在需要恢复的用户数据。

工作树占用说明：本轮为并行 writer 新增 7 个 worktree（`gov-ui` 与 `a-gates`/`b-surfaces`/`c-resources`/`d-docs`/`e-honesty`/`f-oss`/`g-coredemo`）。它们**本轮不删除**：其中 4 个的 `frontend/node_modules` 是指向 `f15-folder-ingest-20261007` 共享安装的 junction，而递归删除会跟随 junction 删掉共享源。安全顺序是先 `cmd /c rmdir <junction>`（只卸链接，不碰目标），再 `git worktree remove`；分支提交仍在，随时可重开工作树。此清单已列入 §6 待授权项，执行前需逐项确认链接方向。
