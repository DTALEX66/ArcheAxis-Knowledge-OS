# ArcheAxis R5 审计修复整合实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `ArcheAxis-R5-Taskpack-20260915.zip` 的连续动作与 `ArcheAxis-审计与实际修复-20260915.zip` 的修复候选整合为一条可验证的 R5 后续执行链，不把历史候选或局部测试误报为产品闭环。

**Architecture:** C#/Avalonia 是正式桌面入口，Rust Core 是 vNext 业务库唯一写者，Python workers 负责隔离解析与模型工作；DeepTutor 只能通过受控 adapter 访问 Core 权威。所有真实资料、四库迁移和 Green 更新在隔离副本中验证，独立 Q00/Q01 最后审计。

**Tech Stack:** C#/.NET Avalonia、Rust workspace/Axum/SQLite、Python workers、GitHub Actions、现有 FSRS、Tesseract/PyMuPDF/Office/HTML adapters。

**Spec:** `docs/authority/taskpack-0912-r5/`（冻结 R5 正文）；增量输入为项目忽略目录中的两个 2026-09-15 ZIP 解压包。

## Global Constraints

- 当前权威计划仍是 `AAK-FOLLOWUP-20260908-R3 / R5`；本计划不替换冻结 TASKS、STATE 或验收正文。
- 当前远端基线为 `0dd8ff37b670ae98fac4be35720194434e82191e`；候选修复 `68c81a39` 必须逐文件比较后再采用。
- 一次只由一个 checkout 写入；保留未跟踪历史资产、私有会话状态和用户数据。
- 不访问 E: 盘、凭据、.env、浏览器数据、私有代理状态；不修改外置工具库、模型库、Green、真实资料库。
- 运行数据、测试副本和证据写入项目忽略的 `.project-local/`，不得用空 TEST 库冒充真实四库。
- 每个任务分别记录 PLANNED、IMPLEMENTED_LOCAL、TESTED_LOCAL、CI_VERIFIED_EXACT_SHA、INSTALLED_RUNTIME_VERIFIED；缺证据即 NOT RUN/BLOCKED。
- 不自签 Q00/Q01；不因任务包、探针、目录清单或脚本输出中的 PASS 宣称产品完成。

---

### Task 0: 基线核对与候选修复裁决

**Files:**
- Read: `AGENTS.md`, `docs/authority/taskpack-0912-r5/TASKS.json`, `docs/current/R5-STATE.json`, `docs/current/R5-EXECUTION.md`
- Read: 两个 ZIP 的 `README.md`、`INTEGRATION.md`、`CONTINUATION.json`、审计报告、`validation.json`
- Compare: `ArcheAxis-first-use-fixes.patch`、`ArcheAxis-first-use-fixes.bundle`
- Create: `docs/current/R5-CONTINUATION-EXECUTION-20260915.md`
- Test: `scripts/workflow/execution_preflight.py`、`git diff --check`

**Interfaces:**
- Consumes: 当前 HEAD、两个包记录的基线/候选 SHA、现有未提交路径。
- Produces: 每个候选文件的 adopt/replace/skip 决策表、基线 SHA、未提交边界和后续任务的输入清单。

- [ ] 记录当前分支、HEAD、upstream、`origin/main` 与工作树；不得重置或清理。
- [ ] 对补丁运行 `git apply --check` 到临时副本或使用 `git diff --no-index` 比较，禁止直接覆盖当前 checkout。
- [ ] 将候选修复分为“当前已覆盖”“需要移植”“与现行架构冲突”“仅历史证据”，逐文件写出原因和测试。
- [ ] 运行执行预检与 diff 检查，生成本任务收据。

**Gate:** 没有逐文件裁决和干净的回滚点，不得开始后续写入任务。

### Task 1: CI、workspace 与仓库规范止错

**Files:**
- Modify if Task 0 adopts: `.github/workflows/ci.yml`, `.github/workflows/vnext-ci.yml`, `Cargo.toml`
- Test: `tests/workflow/`, `tests/test_release_architecture.py`, Rust workspace metadata

**Interfaces:**
- Consumes: Task 0 的候选裁决。
- Produces: 正式 Avalonia→Rust→Python 链的 CI 检查、完整历史 checkout、legacy Tauri 排除规则和同 SHA 证据。

- [ ] 先写能复现当前 lint/浅 checkout/workspace 归属问题的定向测试。
- [ ] 只移植未被当前分支覆盖且与正式架构一致的配置改动。
- [ ] 本地运行路径规范、仓库规范和最小 workspace 检查。
- [ ] 推送一个精确提交后读取每个 required job；日志不可读时标记 BLOCKED，不改成 continue-on-error。
- [ ] 将远端 run URL、head SHA、job conclusion 写入收据。

**Gate:** 远端同 SHA 全部 required job 成功；否则保留失败证据并停止发布链。

### Task 2: 首次导入与真实解析闭环

**Files:**
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml(.cs)`, `StudyClient.cs`, `CoreSupervisor.cs`
- Modify: `crates/archeaxis-application/src/executor.rs`, `study.rs`, `crates/archeaxis-api/src/main.rs`
- Test: `tests/desktop/`, `crates/archeaxis-api/tests/first_use.rs`

**Interfaces:**
- Consumes: Task 1 的可验证构建链和稳定 TEST workspace。
- Produces: import → job → worker → 正文/loss → 显式摘录接受 → knowledge/card 事务，来源 hash、转换 ID、字符/页锚点可读回。

- [ ] 从空 TEST 库导入一份真实 TXT/Markdown、文本 PDF、DOCX、HTML，记录原件 SHA-256。
- [ ] 让 UI 展示执行状态、正文与损失；解析失败只保留原件，不创建知识。
- [ ] 只允许用户明确接受原文摘录和问题后写入知识与题目；拒绝空结果、伪造摘录和越界路径。
- [ ] 每格式至少执行一次检索命中与原件回跳；未执行格式保持 NOT RUN。
- [ ] 运行 Rust/Python/桌面定向测试并绑定同一运行收据。

**Gate:** 四种样例均有真实来源锚点和失败边界；不得把探针或合成脚本答案当真人验收。

### Task 3: 人类学习、重试、纠错与 FSRS

**Files:**
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`
- Modify: `crates/archeaxis-domain/src/learning.rs`, `knowledge.rs`, `archeaxis-application/src/study.rs`
- Reuse: `services/python-workers/learning/worker_schedule.py`
- Test: `crates/archeaxis-api/tests/machine_correction_loop.rs`, `tests/contract/`, desktop tests

**Interfaces:**
- Consumes: Task 2 的 knowledge/card/exposure IDs。
- Produces: answer、question_version、knowledge_version、exposure_id、correction_id 的 append-only review 事件和可读回 FSRS 状态。

- [ ] 先写失败测试：空答案不计分、同 event 重试只一条、确定 4xx 释放并要求重载。
- [ ] 固定展示时生成的 exposure/event payload，发送中禁止连点重入。
- [ ] 先采集回答再显示参考；首次自评与独立评分字段分开。
- [ ] 纠错追加新知识版本和新题，旧卡退出当前队列；事务失败不得留下半笔修订。
- [ ] 停启同一 TEST 库后读回回答、曝光、版本、引用和下一次到期时间。

**Gate:** 所有学习字段有真实内容；FSRS 不可用时明确 UN SCHEDULED，不编造日期。

### Task 4: DeepTutor 默认入口接入

**Files:**
- Modify: `app/adapters/deeptutor/authority.py`, `custody.py`
- Modify: `app/integrations/deeptutor_bridge.py`, `scripts/launch/deeptutor_web.py`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml(.cs)`
- Test: DeepTutor adapter/bridge tests、跨进程 Core 回读测试

**Interfaces:**
- Consumes: Task 2/3 的 Core authority、知识题目和 review API。
- Produces: 默认桌面入口可挂载固定 DeepTutor v1.5.17，读取同源知识并把回答/附件回收到 Core。

- [ ] 核对固定 checkout、commit、许可证和本地模型 profile；不因 v1.6.8 自动升级。
- [ ] 通过正式入口启动工作台并注入 authority adapter；禁止独立页面自称已融合。
- [ ] 完成一次真实阅读/练习/回答，停用 DeepTutor 后 Core 原件和知识仍可读。
- [ ] 保存会话附件 custody、网络/费用选择和失败降级说明。

**Gate:** 同一业务事实只能由 Rust Core 写入；工作台启动本身不算通过。

### Task 5: PDF/OCR/Office/HTML/媒体质量矩阵

**Files:**
- Modify: `services/python-workers/transport/text_ndjson.py`
- Inspect/modify: `document/worker_pdf.py`, `vision/worker_ocr.py`, `media/worker_transcribe.py`
- Test: `tests/workers/test_ocr_runtime_selection.py` 与逐格式 fixtures

**Interfaces:**
- Consumes: Task 2 的统一 job/profile 入口和外部资源注册。
- Produces: 每个格式的原件 hash、正文、损失、页/时间锚点、检索和学习状态矩阵。

- [ ] 从实际 profile 读取 Tesseract、`chi_sim/eng`、ASR 和共享模型路径；缺资源则显式 NOT RUN。
- [ ] 用真实中文扫描图/PDF验证 OCR；用短音频验证转写时间锚点；不把 probe/目录存在当成功。
- [ ] 对复杂 Office/PDF 失败样本只做必要 adapter 接线，不重写成熟解析器。
- [ ] 更新格式矩阵：完成、部分、仅保管、未支持分别列出证据和限制。
- [ ] 保留原件和来源锚点，解析失败可按同 source/job 重试。

**Gate:** 未执行格式保持未完成；全链路质量不能由四种文本样例外推。

### Task 6: MCP 与真实机器任务反馈

**Files:**
- Modify: `scripts/mcp/archeaxis_mcp_server.py`
- Modify/test: `scripts/probes/r11_mcp_client_smoke.py`, `r11_machine_receipt_smoke.py`
- Test: `crates/archeaxis-api/tests/machine_correction_loop.rs`

**Interfaces:**
- Consumes: Task 3 的知识版本与资格；Task 5 的可引用来源。
- Produces: 模型版本、检索引用、原始输出、独立评分、纠错前后差异的机器任务收据。

- [ ] 使用同一知识执行一个真实、非空、受控任务；绑定本地模型 profile。
- [ ] 独立评分模型输出与引用正确性；机器收据本身不作为评分。
- [ ] 修订一处知识后重新执行原题和未见题，验证旧知识失效、新版本生效。
- [ ] 模型不可用标记未测/失败，不写成功评分。

**Gate:** 必须有真实模型输出和独立评分；工具注册或空检索不算通过。

### Task 7: 四库、归档恢复与 Green 验收

**Files:**
- Inspect/modify: `shared/workspace_manifest.py`, `contracts/workspace/workspace-manifest.schema.json`
- Modify/test: `crates/archeaxis-store-sqlite/`, `crates/archeaxis-archive/`, `scripts/launch/core_launch.py`
- Inspect: `apps/ArcheAxis.Desktop/`, `scripts/launch/desktop_launch.py`, `scripts/release_manifest.py`

**Interfaces:**
- Consumes: Task 2–6 的非空 TEST 数据、真实 Windows 配置和代表资料。
- Produces: source_archive、evidence_ledger、human_learning_vault、ai_asset_vault 的 workspace_id/path/type/readonly 快照，带身份校验的备份、迁移、恢复和回滚证据。

- [ ] 在 Windows 只读读取实际 Green/四库绑定；记录代表文件 hash，不读取其他私有目录。
- [ ] 备份和恢复验证应用身份、schema、必需表、引用和 hash；无关 SQLite、损坏备份、断电恢复必须拒绝替换活动库。
- [ ] 在隔离 staging 做非空迁移，逐项比较原件、附件、知识、卡片、答案和机器任务。
- [ ] 构建正式 Avalonia/Rust 包，在不覆盖 Green 的候选目录完成首次启动、两次重启、备份恢复和回退。
- [ ] 只有完整证据齐备后才更新用户指定 Green 程序部分，保留设置和数据。

**Gate:** Windows/Green 未实测时不得标 INSTALLED_RUNTIME_VERIFIED。

### Task 8: 历史吸收、模型外置与容量治理

**Files:**
- Inspect: `docs/authority/taskpack-0912-r5/BLUEPRINT-COVERAGE.json`
- Inspect: `shared/models/magika/model.onnx` 的加载器、打包消费者
- Test/report: `scripts/maintenance/inventory_project.py`、路径/容量收据

**Interfaces:**
- Consumes: Task 0 的历史分支差分和 Task 7 的外部资源注册。
- Produces: 每项历史能力的吸收/替代/冻结决策、模型外置可回滚方案、同口径容量报告。

- [ ] 按独有提交逐项映射到当前模块和测试，禁止整分支合并。
- [ ] 先证明 Magika 模型已有共享消费者和离线降级，再移除跟踪副本；没有证据只登记不删除。
- [ ] 按生产者、缓存、构建输出、唯一资产分类容量，记录源/目标/hash/消费者。
- [ ] 保留 F01–F06 长期能力及历史收据，不因瘦身删除需求文本。

**Gate:** 未证明外部副本、消费者和回滚前，不删除模型、PDF、用户资料或私有状态。

### Task 9: 独立审计 Q00/Q01 与发布闭环

**Files:**
- Read: `docs/authority/taskpack-0912-r5/R5-ACCEPTANCE.md`
- Update only with independent owner: `docs/current/R5-STATE.json`, `R5-EXECUTION.md`
- Evidence: all task receipts and exact-SHA CI/Windows records

**Interfaces:**
- Consumes: Task 1–8 的同 SHA、同库、同运行证据。
- Produces: 独立 G01–G14 PASS/FAIL/BLOCKED，随后按原依赖决定 Q01。

- [ ] 将完整证据包交给独立审计者；实施者不得修改审计结论。
- [ ] Q00 逐项核真实输入、用户操作、输出、限制和回滚。
- [ ] 只有 Q00、X12/X13/X14 前置满足后才执行 Q01。
- [ ] 发布、合并、安装和云端状态分别记录，不能由本地测试替代。

**Gate:** 任一必需证据缺失即 BLOCKED/NOT RUN；不以任务包文本或数量统计签通过。

---

## 覆盖缺口自检

- 两个包中的 11 组 X 动作均映射到 Task 0–8；Q00/Q01 映射到 Task 9。
- `68c81a39` 的候选修复全部进入 Task 0/1/2/3/8 的逐文件裁决，不默认重复应用。
- 真实 Windows、Green、四库、中文 OCR/ASR、DeepTutor 默认入口、独立模型评分和远端 CI 均有独立任务与验收门。
- 未覆盖项：任何外置共享库的实际修改、用户真实资料删除/迁移、发布签名和账户费用；这些需要新的明确授权和独立任务。

## 执行选择

本计划只完成拆解，未应用补丁、未提交、未推送。执行时应从 Task 0 开始，每个任务完成自己的测试和证据后再进入下一任务。

## 全部任务包的状态与对齐

| 来源 | 当前地位 | 未完成内容如何承接 |
| --- | --- | --- |
| `docs/authority/taskpack-0905/` | 历史执行包，已被后续 R2/R3/R5 取代 | T00–T20 的收据与错误教训作为证据来源；容量、首次运行、统一客户端、追加审计分别进入 Task 0、2、3、8、9 |
| `docs/authority/taskpack-0906/` | 旧 Full Loop，已被决策台账和 R2/R3/R5 取代 | T00–T20 不重新整包执行；Rust/API、workers、学习、迁移、规范化、Windows、打包债务映射到 Task 1–8，F 类长期能力保留 |
| `docs/authority/taskpack-0907/` | AAK-REUSE-FIRST-R2，已被 R3.1/R5 取代 | X00–X14 与 Q00/Q01 是 R5 继承正文；只按当前状态和新证据补缺，不按旧收据批量置完成 |
| `docs/authority/taskpack-0908-r3/` | R3.1 冻结继承文本 | 作为 R5 的任务语义和验收来源；不另开竞争计划 |
| `docs/authority/taskpack-0910-r3/` | 17 个 R00–R16 的执行切片基线 | 当前状态仍用于切片映射：R10 DeepTutor、R12 清理、R13 Windows/发布、R14/R16 独立审计、R15 全格式分别承接 Task 4、7、8、9、5 |
| `docs/authority/taskpack-0912-r5/` | 当前活动权威包（23 个 X/F/Q 任务） | 本计划 Task 0–9 是其执行拆分，不修改其冻结正文或状态文件 |
| `ArcheAxis-R5-Taskpack-20260915.zip` | 0915 连续动作增量包，纯任务/证据 | 11 组 X 动作和 Q00/Q01 已全部映射到 Task 0–9；包内 `68c81a39` 与当前分支 SHA 不同，不能直接覆盖 |
| `ArcheAxis-审计与实际修复-20260915.zip` | 0915 实际修复候选包 | 14 文件补丁和 bundle 只在 Task 0 逐文件裁决；其验证摘要不能替代远端、Windows、Green 或独立审计 |

### 当前未完成任务的唯一对齐表

| R5 当前切片/任务 | 现状 | 计划任务 |
| --- | --- | --- |
| R00/X00–X02 | 部分完成，仍需基线、历史语义和资源边界复核 | Task 0、Task 8 |
| R01/X01 | 本地规范检查已有，CI 同 SHA 和取消/孤儿进程证据缺失 | Task 1 |
| R02–R09/X04–X09 | 局部测试通过，真实资料、学习生命周期、独立机器评分仍缺 | Task 2、3、5、6 |
| R10/X03 | DeepTutor 默认挂载、题目渲染/复习、会话附件回收未闭合 | Task 4 |
| R11/X09 | MCP 接口和资格局部通过，真实模型任务与纠错复测未完成 | Task 6 |
| R12/X14 | 部分路径已清理；隐藏/受保护内容、容量归因和最终授权清单未完成 | Task 8 |
| R13/X11 | 本地合同/候选包有证据，Windows 安装签名卸载和干净机未验收 | Task 7 |
| R14/Q00 | BLOCKED，必须独立 GPT 按 G01–G14 审计 | Task 9 |
| R15/X12 | 格式矩阵仍为 0 complete / 14 partial / 2 custody-only | Task 5 |
| R16/Q01 | BLOCKED，依赖 Q00、R15、R13、R12 | Task 9 |
| F01–F06 | 延后保留的长期能力，不是当前首次闭环的阻塞项 | Task 8 记录保留，不提前实施 |

### 不再作为独立任务重复执行的材料

- 0905 的历史收据、0906 的旧 Full Loop、0907 的 R2 和 0908 的 R3.1 不再各自开分支重跑。
- `docs/current/` 中的 handoff、baseline、cleanup、reuse、language adoption 文件是证据或交接材料，不自动提升为新任务。
- 任一历史包声称的 PASS 仅在其原 SHA、原环境和原范围内有效；与当前实现的关系必须经过 Task 0 裁决。

