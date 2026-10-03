# DSH 闭环执行交接 · 2026-10-03

执行方 DSH。分支 `codex/dsh-aaos-real-multiformat-loop-20261001`，本地 HEAD `b421ddee`（未提交改动见 §4）。
本文只记录**已实测**项；未做的写在 §6，不并入完成项。

## 1. 结论

**NOT_READY（但只剩一处人为闸门）。** 真实资料已从来源跑到入库并可在成品软件中读回；
P2–P4 的机器侧全链在**真实资料的副本**上跑通；出厂 Green 候选已组装、校验并**作为产品实跑通过**。
唯一未过的是**真实库 19 条知识候选的真人复核** —— `review-decisions` 是 human-only，执行方不得代作判断。

## 2. 真实资料闭环验收矩阵

| 阶段 | 状态 | 证据 |
| --- | --- | --- |
| P0 插件/模型运行 | 部分 | 能力就绪 13/13；本地 LM Studio 嵌入实测可用（见下） |
| P1 真实来源/转换 | ✅ | 材料根 `D:\All projects\ceshi`；staged 探针 **9/9 真实文件 CONVERTED**（md/csv/json/pdf/ocr/docx/html/canvas/mp4）；收据 `.project-local/worktrees/dsh-backend-loop-20261001/.project-local/runs/staged-matrix/staged-format-matrix.json` |
| P2 锚点/质量/检索/课件 | ✅ 机器侧 | 19 sources / 19 transforms / 38 anchors / 19 candidates；**19/19 transform 与原件字节全等**；FTS `SKILL`→13、`安全边界`→1、`Obsidian`→13；`search.semantic` 200（PARTIAL）、`courses/from-knowledge` 201 + render 200 |
| P3 真人学习 | ✅ 演练 | learning reference/assessment/review 全 201；真 FSRS `review_state=learning`、`stability=2.3065`、`correct_streak=1`、**`closed=false`** |
| P4 机器纠正/重答 | ✅ 演练 | `machine/answers` 200（935 字符真实本地模型回答）；`machine/corrections` 200（`failed_task_id=evaluation_answer_8d3f…`，新候选 `k_f3c68668…`）；`machine/retests` 200 |
| P5 持久化/迁移 | ✅ 机器侧 | 工作区 schema 8→9（新 Core 自身迁移）；M0 合成链 28/28 阶段含 online backup/restore 与 legacy migration，`legacy_db_kept=true` |
| P6 候选/安装 | 候选 ✅ / 安装未做 | 见 §9；安装/替换/回滚受 Owner Gate 约束 |

**入库实况**：`D:\All projects\资料库\workspace.sqlite`（schema 9）+ `workspace.sqlite.objects\`（19 个原件按 sha256 存放）。

**机器侧全链**：`m0_full_loop_smoke.py` → `ok=true`、`chain_stages_verified=true`、**28/28 阶段**、`validation_errors=[]`。这是 **SYNTHETIC protocol evidence**，不等于真人闭环。

**接受后链路演练**（在真实库**副本**上，脚本化 human token）：accept 200 → semantic 200(PARTIAL) → course 201 → render 200(6430 B, `canonical_bindings_verified=true`) → learning 201/201/201 → machine answer 200 → correction 200 → retest 200。收据 `.project-local/worktrees/dsh-backend-loop-20261001/.project-local/runs/post-accept-chain-receipt.json`。

## 3. 门禁

| 门禁 | 结果 |
| --- | --- |
| Rust `archeaxis-api` | **204 passed / 0 failed**（48 个 test binary） |
| Python 全量 | **3865 passed / 40 skipped / 0 failed**（264.7 s） |
| `tests/maintenance` | 179 passed / 0 failed |
| Desktop 构建（登记 SDK `dotnet-sdk-10.0.401` + 库内 NuGet） | **0 warning / 0 error** |

收敛轨迹：Python 门禁原为**收集中断（不是 PASS）** → 19 → 17 → 13 → 12 → 0。

## 4. 本会话改动（已提交并推送：`ef0104f8` → `ca718c24`）

| 文件 | 改动与理由 |
| --- | --- |
| `crates/archeaxis-api/src/lib.rs` | `evidence_anchors` 投影新增 `source_name` / `quote` / `knowledge_id` / `knowledge_status` —— 让证据行能显示真实文件名与引用，并让界面知道哪条知识待复核 |
| `crates/archeaxis-api/src/launch.rs` | 启动输入上限 4096 → **65536**（`MAX_LAUNCH_BYTES`），附测量理由 |
| `crates/archeaxis-api/src/main.rs` | 文档行同步为 64 KiB |
| `crates/archeaxis-api/tests/evidence_anchors_api.rs` | 新字段契约（2 passed） |
| `crates/archeaxis-api/tests/contract_process_model.rs` | 超限样例随阈值改到 70000 字节，仍钉“超限必须拒绝且退出 2” |
| `apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml`、`.axaml.cs` | 证据行显示真实来源与引用；“待复核”卡片由死占位改为真实计数；新增“**仅看待复核**”筛选；空态补回“未生成示例记录，缺失字段保持未提供”；宽行详情补 `AnchorId`/`SourceId`，修掉“窄行身份比宽行还多”的不一致 |
| `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` | 选中证据行时把 `knowledge_id` 带入复核输入框 |
| `scripts/release/stage_backend_runtime.py`、`scripts/launch/desktop_launch.py`、`scripts/release/assemble_green_candidate.py` | 三处 launch 档案补声明 `search.semantic` / `course.general` |
| `services/python-workers/search/semantic_ranking.py`、`course/worker_general_course.py` | 补 transport sidecar 模式（`--staging-root` → `transport.serve_stdio`），与 `machine.answer` 一致，使打包就绪检查可验证它们 |
| `docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` | 补 5 条未登记路由（§3 40→45 对）；§6 运行时路由 14→19；§7 readiness 10→**13**（按实测更正原错误模型） |
| `tests/**`（6 个 UI 契约、2 个 maintenance、1 个 OCR、1 个 desktop routes） | 按 F01 去术语方向对齐文案/绑定，**保留全部“不伪造/防削弱”断言**；OCR 用例补上缺失的环境隔离；新增路由漂移守卫 |
| `tests/test_evidence_pending_filter_contract.py`、`tests/test_worker_route_lists_agree.py` | 新增守卫 |
| `docs/current/R6-EXECUTION.md` | 追加 13 段实执行记录（mutable live 记录） |

本地 HEAD `b421ddee`，porcelain 80 项。`R6-STATE.json` 未改（不擅自重标任务状态）。

## 5. 本会话发现并修复的真实缺陷

1. **P2 两条路由在出厂产品里根本不可达。** 在产品自己的 11 条路由档案下，`POST /api/v1/search/semantic` 与 `POST /api/v1/courses/from-knowledge` 均返回 **503 derived worker is not registered**；补声明后分别为 200（真实 1024 维嵌入，endpoint `127.0.0.1:1234/v1/embeddings`）与 201。根因：worker 随包发布，但**三处**档案都没声明。
2. **Core 启动输入硬上限 4096 字节。** 13 条路由的绝对路径序列化后：短安装根 2741 B、worktree 根 3045 B、深安装根 **4405 B**；深层安装因此启动失败，界面只显示“Core 未就绪”。已提升到 64 KiB 并端到端复验。
3. **OCR worker 测试的环境耦合。** `worker_ocr.py` 先按声明式外置注册表解析 tesseract，再回落 `shutil.which`；4 条用例只 mock 了后者，于是**在产品的正确配置下失败**。属测试缺陷，已补隔离。
4. **路由清单重复三处**（见 1）。已加 AST 守卫，并**验证守卫真的会失败**。
5. **端口空闲探测与"可绑定"不是一回事。** `contract_process_model` 的 `free_port()` 用 connect 判断空闲；本机 49152 connect 被拒而 bind 被拒（WSAEACCES 10013），测试因而把不可绑定端口交给 Core，**失败原因与被钉契约无关**。改为尝试 bind。本机修复前 3/3 失败、修复后 204/0；**CI 无法发现（runner 上该端口可绑定）**。
6. **候选里装过过期 Core。** `build_candidate.py` 未指定 `--binary` 时取默认目标，组装出的候选含第 6 轮二进制。已在 r19 显式使用已验证 Core。

## 6. 未做 / 未通过（不得记成通过）

- **真实库知识复核未执行**：19 条仍为 `candidate`。因此**真实知识上的**语义检索、课件候选、真人学习、机器纠正/重答均未执行（副本演练不算）。
- **未安装 / 未替换 / 未回滚 Green**，未 push，未删除任何文件。Release 仍 **FROZEN**。
- `search.semantic` 在真实数据上返回 **PARTIAL**（重排腿 exact yes/no 不完整），不是完整语义检索。
- `mastery_projection.closed` 全程为 **false**：掌握规则未定。
- `courses/from-knowledge` 目前只支持**有 anchor 的 active accepted** 知识；无 anchor 的个人知识路径未做。
- 前端整机视觉/无障碍矩阵（键鼠焦点、IME、忙碌/禁用、减弱动效、DPI/窄窗）**未做完整真人验收**。
- 远端 `main` 未合入本次工作；双端读回见 §9 的 2026-10-03 快照。

## 7. 需 Owner 裁决

| # | 事项 | 我的建议 |
| --- | --- | --- |
| 1 | 真实库 19 条知识候选的接受/驳回 | 用证据中心“仅看待复核”筛选后逐条判断（清单见 `.project-local/…/REVIEW-WORKLIST.md`） |
| 2 | 掌握规则（`mastery_projection.closed` 语义） | 由你给定；执行方不得自行把 Good/连对变成闭环 |
| 3 | 是否提交本会话改动到 feature 分支 | 建议**先本地提交**（保护工作、后续候选可为 `tree_clean_when_built=true`）；推送与否另定 |
| 4 | 安装 / 原位替换 / 冷启动 / 回滚演练 | 需要你给出精确路径与操作授权 |
| 5 | 过期候选清理（r16、r17，各约 1.2 GB） | 需我列精确清单 + 你批准后再删 |
| 6 | 四库目录（人类学习库/机器知识库/源文件归档库/证据账本库）是否接入 vNext | vNext 目前只有单一 sqlite，四库是旧产品语义 |
| 7 | 启动上限是否改为可配置、或让 launch JSON 不带绝对路径 | 本次已提到 64 KiB；长期建议去掉绝对路径 |

## 8. 回退步骤

1. **撤销真实入库**：删除 `D:\All projects\资料库\workspace.sqlite`（含 `-wal`/`-shm`）与 `workspace.sqlite.objects\`。来源 `D:\All projects\ceshi` **从未被修改**，可按 sha256 复核。
2. **撤销源码改动**：全部在未提交工作区，`git checkout -- <paths>` 或 `git stash` 可撤；无 commit、无 push。
3. **撤销候选**：候选目录位于 `.project-local\build\gc-r18|gc-r19\`，整目录删除即可；源码快照收据在 `.project-local\runs\candidate-20261003\`。
4. **沙箱权限回归**（本会话早期修复）：`D:\All projects\dsh-acl-reports-20261003\acl-backup-326c7930….ps1` 可还原工作区根目录权限。

## 9. 产物与收据索引

| 产物 | 位置 / 标识 |
| --- | --- |
| 现行 Green 候选 `dsh-r19-20261003` | `.project-local/build/gc-r19/ArcheAxis.Knowledge.Green-vdsh-r19-20261003-x64` |
| 候选校验 | `verify_green_candidate.py --require-runtime --require-workers` → ok:true，21442 项，problems [] |
| 候选 Core | sha256 `4C7D2FEABD8C189C8ABBB6E9FE36BD1A46D04A88A75C080292195F5E2683EFC6`，97,733,107 B |
| 候选 zip | 336,449,721 B，sha256 `ABDA7394E28A179CE3FD59C36E200B12752BFABAFBDA879CD12E100A751139D2` |
| 源码快照（现行） | `.project-local/runs/candidate-20261003/source-snapshot-r19.json`，sha256 `41d67234636a96ae50d1da972f68491e6d151e97688f77ab50a5d2d7fcc3c28e`（1722 文件） |
| Core-only 候选包 | `.project-local/runs/candidate-20261003/core-candidate-r16`（**已过期**，内含第 6 轮 Core，勿用） |
| 出厂候选读回真实库的窗口捕获 | `.project-local/runs/candidate-r19-app-20261003.png`（sha256 `5445e8c8…`） |
| 复核清单 | `.project-local/worktrees/dsh-backend-loop-20261001/.project-local/runs/product-ingest-20261003/REVIEW-WORKLIST.md` |
| 真实入库收据 | 同目录 `receipt.json` / `execute-receipt.json` / `candidates-receipt.json` / `compare-receipt.json` |
| 双端读回（2026-10-03 快照） | `origin/main` `59498723`；`origin/codex/Audit` `1a981a44`；feature 远端 `0980fc7d`（CI 与 vnext-ci success，run 37024251817/37024257187）；本地 `b421ddee` 领先 1；PR #156/#157/#158 均为 open+draft |

## 10. 边界声明

- 本文中的“演练”一律指在**真实库副本**上用脚本化 human token 执行的协议验证，**不构成真人复核**；真实库 19 条候选未被改动。
- M0 全链是 **SYNTHETIC protocol evidence**，不是真实资料闭环。
- 未上传任何用户原始资料；所有日志与运行库留在 ignored `.project-local`。
- 未安装/替换/回滚 Green；Release 保持 FROZEN。

## 11. 证据分级（按 `workflow-assistance-evidence-verification` 标准自查）

分级口径：1 结构 · 2 本地执行 · 3 精确 SHA 的 CI · 4 发布 · 5 活体行为。
生命周期层：`PLANNED` → `BRANCH_PUBLISHED` → `IMPLEMENTED_LOCAL` → `TESTED_LOCAL` → `CI_VERIFIED_EXACT_SHA` → `MERGED_MAIN` → `INSTALLED_RUNTIME_VERIFIED`。

| 主张 | 状态 | 层级 | 证据（命令/路径/SHA） |
| --- | --- | --- | --- |
| 源码改动正确且不回归 | **PASS** | `TESTED_LOCAL` | `scripts\ci\cargo_test.bat -p archeaxis-api` → 204/0；`scripts\ci\run_tests.ps1 --full` → 3865/0 |
| 上述改动的 **CI** | **PASS** | `CI_VERIFIED_EXACT_SHA` | 当前 tip **`d7eb2f827dd819d7d281c0682ca40d08a2fdfe7e`**：`CI` push 37125705991、`vnext-ci` push 37125706019、`vnext-ci` PR 37125709232 **全部 success**（前一验证点 `ca718c24` 亦全绿） |
| 首轮推送的 CI（已修复） | **FAILED → 已修** | — | `ef0104f8` 的 `CI` push run 37123557549 失败于 `cargo fmt --all -- --check`；本地门禁未跑 rustfmt，CI 先发现 |
| 真实资料导入并入库 | **PASS** | 2 + 5（真实产品运行时跑真实库） | `D:\All projects\资料库\workspace.sqlite`（schema 9）19/19/38/19；FTS `SKILL`→13、`Obsidian`→13、`安全边界`→1 |
| 转换字节保真 | **PASS** | 2 | 19/19 transform 与原件 sha256 全等 |
| P2–P4 机器侧全链 | **PASS（协议级）** | 2 | 副本演练收据 `post-accept-chain-receipt.json` |
| M0 全链 28/28 | **PASS（合成）** | 2 | `m0_full_loop_smoke.py` `ok=true`；**标注 SYNTHETIC** |
| **真实库真人复核（P3 真人）** | **NOT EXECUTED** | — | human-only 路由未调用；19 条仍为 `candidate` |
| **真实知识上的语义/课件/真人学习/机器纠正** | **NOT EXECUTED** | — | 依赖上一行；副本演练不能替代 |
| 界面读回（证据/学习/复习/机器） | **PASS** | 5 | 出厂候选原生窗口捕获 `.project-local/runs/r19-*.png`、`r20-machine-label.png`（真实运行时，非源文件截图） |
| 出厂候选可校验、可启动 | **PASS** | 2 | `verify_green_candidate.py` → ok:true（21442 项）；候选自身 Desktop+Core 打开真实库并渲染 |
| 候选出处强度 | **PARTIAL** | 2 | `build_kind=debug-build`、`tree_clean_when_built=false`；非 release、非清洁树 |
| **安装/替换/冷启动/回滚** | **BLOCKED** | 未达 `INSTALLED_RUNTIME_VERIFIED` | Owner Gate：不擅自安装/替换/回滚 Green |
| 清理过期候选 | **BLOCKED** | — | 需精确清单授权 |
| 提交/推送 | **DONE** | `BRANCH_PUBLISHED` | `ef0104f8` → `ca718c24` 非 force 快进推送至 `codex/dsh-aaos-real-multiformat-loop-20261001`；远端 ls-remote 回读一致；**未 merge、未动 main（仍 `59498723`）、未 force** |

**一句话**：本会话的全部实现停在 **`TESTED_LOCAL`**。要再上一层（`CI_VERIFIED_EXACT_SHA`），**必须先提交**——按此标准，本地测试**不能**顶替 CI 层。

