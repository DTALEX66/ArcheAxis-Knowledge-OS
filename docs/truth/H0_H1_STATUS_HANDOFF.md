# Cognitive-Loop-OS 冻结执行 — H0/H1 状态与交接文档

> 文档日期：2026-08-09
> 任务包：`DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`
> 基线：`AXW-FROZEN-v1-2026-08-09`
> 权威分支：`codex/frozen-roadmap-deepseek-v1`
> 执行分支：`axw/execution-h0`（已 merge）、`axw/execution-h1`（PR #72，未 merge）
> 状态日志：`docs/truth/EXECUTION_STATUS_LOG.md`（追加式，LOG-004~048）

本文是任务包要求的状态交接文档，汇总 H0/H1 全部任务的验收状态、证据等级、阻塞与收口路径。所有 PASS 均绑定真实 exact-SHA/CI/审查/安装态证据；未完成项如实标 `PARTIAL`/`UNVERIFIED`，不冒充完成。

**权威源文件（相对本文件）：**

- 冻结基线：[`FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`](FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md)
- 追加式状态日志：[`EXECUTION_STATUS_LOG.md`](EXECUTION_STATUS_LOG.md)
- 权威契约：[`AUTHORITY_CONTRACT.md`](AUTHORITY_CONTRACT.md)
- 当前状态 Truth：[`CURRENT_STATE_TRUTH.md`](CURRENT_STATE_TRUTH.md)
- 执行任务包：[`../../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`](../../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md)
- Web 增补：[`../../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`](../../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md)
- Capability-first 增补：[`../../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`](../../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md)

## 1. 仓库与分支基线

| 项目 | 值 |
|---|---|
| canonical 项目 | `D:/All projects/Cognitive-Loop-OS` |
| 基线基点 | `origin/main` = `492fac5982c693eb668d31cc51a6a59bac83b7a1` |
| H0 merge-SHA | `f269a0128dfee9573699efd24562f96e8a713c70`（PR #71） |
| H0 main CI | run `31320800285` 全绿 |
| H1 分支 | `axw/execution-h1`（PR #72，head `78091cc`，15 checkpoint） |
| H1 exact-head CI | run `31322840300` 全绿（head `78091cc`） |
| 权威分支 | `codex/frozen-roadmap-deepseek-v1` at `ba4cd81` |
| 用户 WIP | canonical 主工作区未触碰 |

## 2. H0（v0.5.1 可信恢复）— 已完成并 merge

| 任务 | 状态 | 证据等级 | 证据 |
|---|---|---|---|
| AXW-BASE-0 | PASS | LOCAL+推送 | LOG-004 |
| AXW-001A/001B | PASS | STRUCTURAL | LOG-005 |
| AXW-003A | PASS | EXACT_SHA_CI | CI + 独立审查 |
| AXW-003C | PASS | EXACT_SHA_CI | PR #71 CI |
| AXW-007A | PASS | LOCAL | LOG-007 |
| AXW-009B | PASS | LOCAL | LOG-012 |
| AXW-009C/009D | PASS | EXACT_SHA_CI+LIVE | installer lifecycle |
| AXW-010B | PASS | LOCAL | LOG-016 |
| AXW-011A | PASS | LOCAL | 6/6 PDF Oracle |
| AXW-012A | PASS | LOCAL | LOG-009 |
| AXW-012B | PASS | EXACT_SHA_CI | markitdown[pdf] |
| AXW-012C | PASS | **LIVE_INSTALLED** | 安装态 PDF 流程 |
| **AXW-H0-EXIT** | **PASS** | 聚合 | LOG-019 发布裁决 |

H0 已合并到 main（`f269a01`），全部冻结验收 PASS。`PUBLICATION`（正式 release 上传/签名）未执行，符合"可信恢复"边界。

## 3. H1（RawAsset、Evidence、早期学习闭环）— 后端核心完成

| 任务 | 状态 | 证据等级 | 证据 |
|---|---|---|---|
| GOV-001 | PASS | LOCAL+审查+CI | scope 过滤，独立审查全 PASS |
| AXW-020R | PASS | STRUCTURAL | 复用矩阵 |
| AXW-020A | PASS | LOCAL | RawAsset 完整合同 |
| AXW-020B | PASS | LOCAL | ConversionRun/Derived |
| AXW-020C | PASS | LOCAL | EvidenceAnchor/IndexRevision |
| AXW-021A | PASS | LOCAL+审查 | 导入 Job/Outbox，孤儿文件修复 |
| AXW-021B | PASS | LOCAL | 崩溃恢复故障测试 |
| AXW-024A | PASS | LOCAL | Claim/Evidence 核心图 |
| AXW-024B | PASS | LOCAL | CrossValidation Bundle |
| AXW-025A | PASS | LOCAL | 学习目标/检索练习 |
| AXW-025B | PASS | LOCAL | Teach-Back/迁移 |
| AXW-030A | PASS | LOCAL | 稳定 DTO/API |
| AXW-030B | PASS | STRUCTURAL | Canonical Shell IA |
| AXW-030C | PASS | STRUCTURAL | Truth 驱动 UI |
| **AXW-022A** | **PARTIAL** | LOCAL | 后端 PDF 字节服务就绪；前端 PDF.js 渲染未实现 |

### AXW-022A PARTIAL 说明

- **后端已交付**：`app/evidence/pdf_serve.py` 提供内容寻址 PDF 字节服务（sha256 key、只读、限大小、不暴露路径），`3 passed`，已过 PR #72 CI
- **前端未交付**：PDF.js 渲染（分页/缩放/搜索/证据批注）需下载大型外部库 + 打包进 wheel/desktop + WebView 点击级验证，属独立前端批次
- 前端是纯静态 JS（无 npm 构建），PDF.js 需作为静态资源放入 `app/workspace/ui/assets/` 并更新 `pyproject.toml` package-data + NOTICE（许可证审计）

## 4. 独立只读审查记录

| 审查 | 结论 | 处置 |
|---|---|---|
| AXW-003A（CI gate identity） | 全部检查点 PASS，无回归风险 | 无需修复 |
| GOV-001（scope 过滤） | 全部 PASS，1 低危 WARNING | WARNING 已修复（adapter fail-closed） |
| AXW-021A（事务一致性） | 1 核心缺陷 + 2 警告 | 孤儿文件已修复 + ImportJobError 统一 + 补测试 |

## 5. 关键决策与偏差记录

任务包要求：实现路径变化（目标仍有效）记录 `DEVIATION`；建议新增/替换记录 `CHANGE_PROPOSAL`。本轮决策：

| 类型 | 记录 | 说明 |
|---|---|---|
| DEVIATION | AXW-022A 前端 PDF.js 渲染延迟到独立批次 | 目标（PDF 阅读器）仍有效；先交付后端内容寻址 PDF 字节服务（`pdf_serve.py`）作为可证子集，前端渲染因需下载大型外部库 + WebView 验证而独立成批 |
| DEVIATION | AXW-030A/030B/030C 复用现有实现 | 现有 `bff.py`（版本化 DTO）、前端导航（Canonical IA）、`app.js`（Truth 投影）已满足验收，补测试而非重写 |
| CHANGE_PROPOSAL | 无 | 本轮未提出需要新增/替换冻结任务的定义 |
| 未授权动作 | H1 merge 保持未执行 | 用户对 H1 merge 授权未明确选择，按 fail-closed 未执行（PR #72 保持 OPEN） |

### 历史增补决策（已记录于冻结发布）

- `LOG-003`：Capability-first 增补（AXW-KLC-*，41 项）——能力优先于品牌，Crawlee 为统一候选
- `LOG-002`：Web 增补（AXW-WEB-*，19 项）——网页知识摄取强制范围
- 历史 `LOG-002` 的 Spider exact URL 阻塞由 `LOG-003` 较新所有者决策取代，历史记录保留

## 6. AXW-H1-EXIT — 当前 BLOCKED

冻结依赖：`GOV-001`、`AXW-021B`、`AXW-022B`、`AXW-024B`、`AXW-025B`、`AXW-030C`

- ✅ 已 PASS：GOV-001、021B、024B、025B、030C
- ❌ 阻塞：**AXW-022B**（证据批注）依赖 AXW-022A 前端 PDF.js 渲染，前端未实现
- 故 AXW-H1-EXIT **未裁决**（须 022 前端完成 + H1 merge 授权后裁决）

## 7. 收口路径与可操作执行队列（H1 完成剩余）

### A. AXW-022A/022B 前端批次（当前唯一实现阻塞）

1. **PDF.js 集成**：下载 PDF.js 单文件构建（Apache-2.0）到 `app/workspace/ui/assets/pdf.min.js`；更新 `pyproject.toml` package-data 的 `app.workspace` 条目（`ui/assets/*.js` 已含，确认覆盖）
2. **许可证审计**：`THIRD_PARTY_NOTICES.md` 新增 PDF.js（Apache-2.0）；记录 source revision/license（AXW-006C）
3. **后端端点**：在 `app/workspace/router.py` 新增只读 `GET /api/pdf/{content_key}`，调用 `app/evidence/pdf_serve.resolve_pdf_bytes`；绑定项目 `.hermes` RawAsset 根
4. **前端页面**：在 `page-evidence` 或新增 `page-pdf` 实现分页/缩放/搜索，用 `pdf_serve` 内容 key 加载原件；读取失败显示"不可用"（Truth 投影，AXW-030C）
5. **证据批注（022B）**：文本/区域选择生成 `EvidenceAnchor`（复用 `app/evidence/anchor.py`）；从 Claim/Evidence 回跳
6. **验证**：本地 `uv run --frozen --only-group ci pytest` + browser-smoke；WebView 点击级验证（分页/缩放/搜索/批注）
7. **推送 PR → exact-head CI → 征求 merge 授权**

### B. H1 收口

1. 征求 **H1 merge 授权** → merge-SHA main CI（run 需全绿）
2. **AXW-H1-EXIT 裁决**：同一 PDF 形成 RawAsset→派生块→Evidence→学习记录→受控 AI 候选，安装态重启后成立

### C. H2 续接（H1 完成后）

H2 首个依赖安全任务：`AXW-023A`（DOCX Adapter）——复用 `app/ingestion/conversion_run.py` + `app/evidence/pdf_serve.py` 模式，建立 DOCX fixture/Oracle → Adapter 合同 → 缺依赖降级 → 源码测试 → bundle/安装态资格。每格式独立完成，不互相冒充。

## 8. 交付物清单（H0 + H1，供后续批次引用）

### H0 交付物（已 merge main，`f269a01`）

H0 分支相对基线基点 `492fac5` 新增/修改 15 文件，766 行。核心变更：

| 文件 | 职责 | 对应任务 |
|---|---|---|
| `app/ingestion/raw_asset.py` | RawAsset 不可变存储（最小） | AXW-012A |
| `scripts/doctor_windows.ps1` | Windows/PowerShell 7 doctor | AXW-007A |
| `pyproject.toml` / `requirements.txt` / `uv.lock` | `markitdown[pdf]` PDF 依赖 | AXW-012B |
| `app/release-manifest.json` | 依赖锁 digest 同步 | AXW-009B |
| `.github/workflows/ci.yml` | ci-verdict 语义 gate ID | AXW-003A |
| `.worklab/project-validation.v1.yaml` | 依赖/parser 分类 | AXW-003C |
| `THIRD_PARTY_NOTICES.md` | PDF 依赖 NOTICE | AXW-006C |

配套测试：`test_ci_a0_gates`、`test_ci_classifier`、`test_doctor_windows`、`test_pdf_extraction`、`test_raw_asset`、`test_workspace_api`。

### H1 交付物（PR #72，未 merge）

H1 分支相对 main 新增/修改 26 文件，1942 行。核心模块：

| 模块 | 职责 | 对应任务 |
|---|---|---|
| `app/evidence/anchor.py` | EvidenceAnchor + IndexRevision | AXW-020C |
| `app/evidence/graph.py` | Claim/Evidence 核心图 | AXW-024A |
| `app/evidence/bundle.py` | CrossValidation Bundle | AXW-024B |
| `app/evidence/pdf_serve.py` | 内容寻址 PDF 字节服务 | AXW-022A（后端） |
| `app/ingestion/raw_asset.py` | RawAsset 不可变存储 + 完整合同 | AXW-012A/020A |
| `app/ingestion/conversion_run.py` | ConversionRun/DerivedDocument/Block | AXW-020B |
| `app/ingestion/import_job.py` | 导入 Job/Outbox/Receipt 同事务 | AXW-021A |
| `app/knowledge/machine_knowledge.py` | scope 过滤 + 治理 | GOV-001 |
| `app/knowledge/retrieval_practice.py` | 学习目标/检索练习 | AXW-025A |
| `app/knowledge/teach_back.py` | Teach-Back/迁移证据 | AXW-025B |

配套测试（13 个新测试文件）覆盖：`test_evidence_anchor/bundle/graph/pdf_serve`、`test_conversion_run`、`test_import_job`、`test_retrieval_practice`、`test_teach_back`、`test_raw_asset`、`test_machine_knowledge_*`、`test_workspace_bff_contract`、`test_workspace_crash_recovery`。

设计文档：`workspace/intake/2026-08-09-AXW-020R-reuse-matrix.md`（对象复用矩阵）。

## 9. 边界与安全确认

- 未访问 `E:\`；未读取/输出任何凭据、token、私钥、cookie 或私人正文
- 冻结基线、增补包、SHA 文件未改动；状态日志严格追加式（LOG-004~048 无改写）
- canonical 主工作区与用户 WIP 未触碰；`.hermes/` 外的仓库文件未改动
- PR #71 已 merge（H0，获授权）；PR #72 未 merge（H1，未获授权）
- 无遗留 ArcheAxis 进程；安装测试已彻底卸载

## 10. 后续阶段概览（H2-H10 与增补）

冻结基线定义后续 Horizon；每阶段需完成其冻结任务后进入下一 Horizon：

- **H2（多格式适配）**：DOCX/PPTX/XLSX/OCR/HTML/音视频 6 个 Adapter，每格式独立 fixture/Oracle/bundle/安装态证据；`AXW-H2-EXIT` 依赖 `AXW-H1-EXIT` + Web/KLC 增补前置
- **H3（Obsidian/Markdown/Canvas C4）**：C0-C4 读写链 + 冲突/回滚 + 安装态资格；依赖 `AXW-H1-EXIT`
- **H4（双学习闭环）**：引用式 AI 回答 + FSRS 调度 + Approved-only Assets + 评测 corpus；依赖 H2/H3 完成
- **H5（稳定 v1.0）**：导出/备份/升级/性能/a11y/release qualification；`AXW-H5-EXIT` 依赖全部前序
- **H6-H10**：Parking Lot，默认 `DEFERRED`，需所有者显式激活 + 独立 TaskPack + 风险审查
- **Web 增补（AXW-WEB-\*）** 与 **Capability-first 增补（AXW-KLC-\*）**：搜索/摄取/课程/学习/AI 复用全生命周期，按各自冻结依赖在 H0/H1 后的对应 Horizon 激活

### 增补前置依赖关系

- `AXW-WEB-EXIT` 是 `AXW-H2-EXIT`、`AXW-055`、`AXW-060` 的强制补充前置
- `AXW-KLC-EXIT` 是 `AXW-055`、`AXW-060` 的强制补充前置
- H1 的 RawAsset/Evidence/Learning 后端（已交付）是 H2-H5 与增补的共享基础

## 11. 最终状态判定

```text
H0（v0.5.1 可信恢复）：PASS（已 merge main）
H1 后端核心：PASS（GOV-001 + 020/021/024/025/030 全部）
H1 前端 PDF 阅读器：PARTIAL（后端就绪，前端待独立批次）
AXW-H1-EXIT：BLOCKED（待 022 前端 + merge 授权）
H2-H5 与 Web/KLC 增补：UNASSESSED（依赖 H1 完成）
公开正式发布：NO-GO（未授权，H0-H5 未完）
```

本文是任务包的状态交接文档；后续执行从 LOG-043 之后的下一依赖安全任务继续。


## 附录 A：证据索引（任务 → commit → CI）

| 阶段 | 任务 | 候选 commit/tree | CI run / 证据 |
|---|---|---|---|
| H0 | 全部（13 项） | merge `f269a01`（PR #71） | main CI `31320800285` 全绿 |
| H1 | GOV-001 | `ad4480e`+`f09f940` | 独立审查 PASS；PR #72 CI |
| H1 | AXW-020R/020A/020B/020C | `4a62440`/`c09379e`/`bc6cad2`/`514841d` | PR #72 CI |
| H1 | AXW-021A/021B | `9ca07ff`+`bb951f0`/`9abded5` | 独立审查（孤儿文件修复）；PR #72 CI |
| H1 | AXW-024A/024B | `58c5664`/`dd7a0a0` | PR #72 CI |
| H1 | AXW-025A/025B | `873e652`/`d9b03e2` | PR #72 CI |
| H1 | AXW-030A | `5579d61` | PR #72 CI |
| H1 | AXW-022A（后端） | `78091cc` | PR #72 CI `31322840300` |

权威分支提交链：`codex/frozen-roadmap-deepseek-v1`（LOG-004~048，最新 `dd499ae`）。
H1 分支：`axw/execution-h1`（PR #72，head `78091cc`，15 checkpoint，未 merge）。


## 附录 B：本地测试结果汇总（命令 → 结果）

各任务 checkpoint 的本地定向测试结果（均在锁定 CI 环境 `uv run --frozen --only-group ci` 下执行，Ruff/architecture/convention 门禁全过）：

| 测试文件 | 结果 | 对应任务 |
|---|---|---|
| `test_ci_a0_gates.py` + `test_ci_classifier.py` | 38 passed | AXW-003A/003C |
| `test_doctor_windows.py` | 6 passed | AXW-007A |
| `test_pdf_extraction.py` | 3 passed | AXW-012B |
| `test_raw_asset.py` | 8 passed | AXW-012A/020A |
| `test_machine_knowledge_contract.py` + `test_machine_knowledge_candidates.py` | 11 passed | GOV-001 |
| `test_conversion_run.py` | 4 passed | AXW-020B |
| `test_evidence_anchor.py` | 6 passed | AXW-020C |
| `test_import_job.py` | 4 passed | AXW-021A |
| `test_workspace_crash_recovery.py` + `test_workspace_outbox_dispatcher.py` | 6 passed | AXW-021B |
| `test_evidence_graph.py` | 5 passed | AXW-024A |
| `test_evidence_bundle.py` + `test_evidence_graph.py` + `test_evidence_anchor.py` | 16 passed | AXW-024B |
| `test_retrieval_practice.py` | 4 passed | AXW-025A |
| `test_teach_back.py` | 5 passed | AXW-025B |
| `test_workspace_bff_contract.py` | 5 passed | AXW-030A |
| `test_pdf_serve.py` | 3 passed | AXW-022A（后端） |

全部 checkpoint 均通过 `ruff check`（changed-file）、`scripts/check_architecture.py`（PASS）、`scripts/check_repository_conventions.py`（PASS）。


## 附录 C：执行协议遵循确认

本执行周期（H0 + H1）严格遵循 `DEEPSEEK_FULL_EXECUTION_TASKPACK_v1` 的执行协议：

| 协议要求 | 遵循情况 |
|---|---|
| 每轮先读 AGENTS.md、冻结基线、状态日志尾部、验证政策 | ✅ 每任务 checkpoint 均执行 |
| 冻结基线/增补/SHA 文件不改动；状态日志只追加 | ✅ 全程追加式 LOG-004~048 |
| 不访问 E:；不读/输出凭据、.env、私钥、token | ✅ 全程遵守 |
| 一个 checkout 一个 writer；并行用独立 worktree/branch | ✅ H0/H1 用隔离 worktree |
| 新行为 RED → GREEN → 定向回归 → 项目门禁 | ✅ 每 checkpoint 均执行 |
| 不把 PARTIAL 写成 PASS | ✅ AXW-022A 前端如实标 PARTIAL |
| 未授权不 merge/推送 main/发布/签名 | ✅ H1 merge 未授权保持 OPEN |
| 输出区分 PASS/PARTIAL/FAIL/NOT EXECUTED/BLOCKED | ✅ 本文档全部分类 |
| 临时数据/下载/缓存/证据写忽略 .hermes/ | ✅ 全程遵守 |

### 单 writer 与续接

- 本周期为单 writer（本会话），所有 checkpoint 顺序提交到 `axw/execution-h1`（后端）与 `codex/frozen-roadmap-deepseek-v1`（权威状态）
- 审查 reviewer 为只读后台 delegation，不写入
- 续接从 LOG-048 之后的下一依赖安全任务开始


## 附录 D：验证政策遵循记录

本周期遵循 `docs/VERIFICATION_POLICY.md`：

| 政策要求 | 遵循情况 |
|---|---|
| 开发中每个新行为一次定向 RED→GREEN | ✅ 每 checkpoint 均执行 |
| TaskPack checkpoint：只跑受影响测试 + changed-file Ruff + diff/convention | ✅ 每 checkpoint 均执行（不重复全量套件） |
| 阶段 Release Train：冻结聚合 diff，一次完整门禁 + 一次 CI | ✅ PR #71（H0）/PR #72（H1）各一次 exact-head CI 全绿 |
| 高风险（打包/依赖/DB/安全）：每个独立 frozen tree 立即完整门禁 + 审查 + push + exact-SHA CI | ✅ AXW-012B（依赖）/AXW-021A（事务）独立审查 + CI |
| Wheel：从 clean checkout 构建 | ✅ desktop-build 从 clean SHA 构建，wheel-smoke PASS |
| 证据保留：本地只留定向 RED/GREEN + 对应 CI run URL | ✅ 状态日志记录每 checkpoint commit/run |
| 不复制易过期测试数量到多个报告 | ✅ 本文档一次性汇总，Git/CI 为执行证据 |

### 审计触发

按验证政策，仅当新 Phase 建立基线/架构或安全边界改变/发现新违规类别时执行完整仓库审计。本周期（H0/H1）未触发完整仓库重审，因为：无架构方向改变、无 schema 破坏性迁移（均为新增表）、无新违规类别；每 checkpoint 用增量门禁阻断。


---

## 任务文档收口声明

本文档完成于 2026-08-09，作为 `DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09` 当前执行周期的正式状态交接文档。它完整记录：

- H0（v0.5.1 可信恢复）：**PASS 并已 merge main**（13 项任务 + AXW-H0-EXIT 发布裁决）
- H1 后端核心：**PASS**（GOV-001 + 020/021/024/025/030，14 项，含 3 次独立只读审查）
- AXW-022A：**PARTIAL**（后端 PDF 字节服务已交付并通过 CI；前端 PDF.js 渲染待独立前端批次）
- AXW-H1-EXIT：**BLOCKED**（阻塞：022 前端 + H1 merge 授权）
- 全部证据（commit/CI run/测试/审查）、决策/偏差、交付物清单、执行/验证政策遵循、收口路径

后续执行按本文档第 7 节（收口路径）从 LOG-049 之后继续；如需续接，读本文档 + `EXECUTION_STATUS_LOG.md` 尾部即可恢复上下文。
