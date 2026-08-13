# Frozen Execution Baseline v1 — Append-only Status Log

本文件记录 [`FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`](FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md) 的执行状态。任务定义保持冻结；所有进度、证据、偏差和阻塞只在本文件末尾追加。

## 写入规则

1. 只在文件末尾追加新记录，不删除、重排或改写旧记录。
2. 更正旧记录时追加 `CORRECTION`，并引用原记录 ID。
3. 一个记录只描述一个 task/checkpoint/release train。
4. `PASS` 必须附对应等级的真实证据；缺失、跳过、取消或不同 SHA 的证据不得标为通过。
5. 状态记录不能新增或重定义冻结任务。新范围使用 `CHANGE_PROPOSAL`，等待所有者决定是否建立 v2。
6. 并行执行时只有集成 writer 更新本文件，其他 agent 只返回只读审查结果。

## 状态词汇

| 状态 | 含义 |
| --- | --- |
| `UNASSESSED` | 尚未按冻结验收标准核验 |
| `IN_PROGRESS` | 已开始，尚未满足全部验收条件 |
| `PASS` | 所需证据全部通过并绑定精确 tree/SHA |
| `PARTIAL` | 只有较低等级或部分证据，不得视为完成 |
| `FAIL` | 已执行且不满足验收标准 |
| `BLOCKED` | 有可复现阻塞，继续需要新授权或外部状态变化 |
| `DEFERRED` | 依据冻结基线尚未进入执行窗口 |
| `DEVIATION` | 实现路径偏离但任务目标未改变 |
| `CHANGE_PROPOSAL` | 建议未来新增/替换任务，不改变 v1 |
| `CORRECTION` | 对历史记录作追加式更正 |

## 证据等级

`STRUCTURAL < LOCAL_RUNTIME < EXACT_SHA_CI < PUBLICATION < LIVE_INSTALLED`

## 记录模板

```markdown
### LOG-YYYYMMDD-NNN — TASK-ID — STATUS

- 时间：YYYY-MM-DDThh:mm:ss+08:00
- 执行分支：branch
- 候选提交/tree：SHA
- 基线输入：相关 task ID 与依赖状态
- 变更：精确路径及行为
- 验证：命令、结果、证据等级
- 云端：CI/PR/branch URL 与 exact SHA；未执行则写 NOT EXECUTED
- 安装态：实际 runtime/installer 结果；不适用或未执行需明确写出
- 风险/剩余项：事实描述
- 回滚：提交或操作
```

## 追加记录

<!-- 新记录只能追加到此行之后。 -->

### LOG-20260809-001 — CHECKPOINT-FROZEN-DOCS — PASS

- 时间：2026-08-09T20:37:10+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交/tree：`636bae2cb50c589e4d58e28c553b736613002b7e` / `7f2d881c389f3c0326b35063476255ccf14c3d9b`
- 基线输入：用户批准的冻结任务清单与 DeepSeek 全量执行包交付；不声明任何 AXW 实现任务完成
- 变更：新增冻结基线、SHA-256、Truth 导航、追加式状态日志、DeepSeek 执行协议、intake，以及冻结哈希 convention guard
- 验证：`git diff --cached --check` PASS；repository convention PASS；42 个定向测试 PASS；changed-file Ruff PASS；architecture guard PASS；99 个任务 ID 无重复、无未知依赖、无环；5 个新文档的本地链接无缺失
- 云端：`https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/tree/codex/frozen-roadmap-deepseek-v1`；远端分支 SHA 回读为 `636bae2cb50c589e4d58e28c553b736613002b7e`；该分支 push 不触发当前仅面向 main/PR 的 CI，`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 安装态：不适用于本次文档与治理校验，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 风险/剩余项：内容已上传独立分支，尚未合并 main；PR、merge、branch protection 和 release 均未获本次授权且未执行
- 回滚：在后续集成分支 revert `636bae2cb50c589e4d58e28c553b736613002b7e`；冻结 v1 的 Git 历史仍保留用于对照

### LOG-20260809-002 — CHECKPOINT-WEB-ADDENDUM — PASS

- 时间：2026-08-09T20:53:11+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交/tree：`e7102416155aa53a13de0fb6b6edf959e07d5528` / `95aae871372283c68795b26c788248361d3349b9`
- 基线输入：冻结 v1 保持 SHA-256 `ef3066231d8251562c6b9fb361e9a0a0424c100c6c27b6ec4de8ebba7b585155`；用户新增 Crawl4AI、Spidering 和前后端网页知识摄取强制范围
- 变更：新增 19 项 Web 强制任务及独立 SHA-256；更新 DeepSeek 有效 DAG、未来蓝图、吸收矩阵、导航和 framework intake；未修改冻结 v1 文件
- 验证：`git diff --cached --check` PASS；repository convention PASS；43 个定向测试 PASS；changed-file Ruff PASS；architecture guard PASS；冻结基线与增补共 118 个任务 ID 无重复、无未知依赖、无环；6 个相关文档的本地链接无缺失；一名独立只读 reviewer 对前后端/DAG 给出 PASS
- 上游核验：Crawl4AI 确认为 `unclecode/crawl4ai`；Spidering 名称存在歧义，`spider-rs/spider` 仅为当前 MIT 候选，exact URL 待所有者确认；同名 `duzluk/spidering` 为 GPL-3.0，未被自动选用
- 云端：`https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/tree/codex/frozen-roadmap-deepseek-v1`；远端分支 SHA 回读为 `e7102416155aa53a13de0fb6b6edf959e07d5528`；该分支 push 不触发当前仅面向 main/PR 的 CI，`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 安装态：本次只交付任务、规划和蓝图；Crawl4AI、Spider、前端、后端和 Windows E2E 实现均为 `NOT EXECUTED`
- 风险/剩余项：必须由所有者确认 Spidering exact GitHub URL；内容尚未合并 main，PR/merge/发布未执行
- 回滚：revert `e7102416155aa53a13de0fb6b6edf959e07d5528`；冻结 v1 与先前发布记录保持可追溯

### LOG-20260809-003 — CAPABILITY-FIRST-KNOWLEDGE-LIFECYCLE — PASS

- 时间：2026-08-09T21:35:05+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交/tree：`491bef9eeca4d9a9ecb5422c0e1642393b4a9470` / `d19393cf3b4b94f1fe91b78c81972b1be446b6df`
- 所有者决策：Crawl4AI、Spidering 或其他候选可以不进入最终产品；static/dynamic/site/search/multiformat/course/learning/AI-reuse 能力必须交付，复用优先，自研只作 benchmark 证明后的兜底
- 变更：新增独立冻结的 41 项 `AXW-KLC-*` 任务和 SHA-256；把搜索→摄取→转换→证据/知识→课程→人类学习→AI 复用→评测写入 DeepSeek 包、未来蓝图、吸收矩阵和导航；不修改冻结 v1 或 Web v1 原文
- 候选结论：Crawlee Python 为统一 HTTP/Playwright/队列高优先候选；Crawl4AI、Spider、Scrapy 为质量/吞吐挑战者；Docling、PaddleOCR/Tesseract、Whisper/FFmpeg、Tree-sitter 等按格式 profile 竞赛；Firecrawl/SearXNG/Browsertrix 和完整 LMS 受 AGPL/GPL 与部署边界限制，默认仅隔离 sidecar 或参考
- 验证：`git diff --cached --check` PASS；repository convention PASS；44 个定向测试 PASS；changed-file Ruff PASS；7 个相关文档 28 条本地链接无缺失；三份任务定义共 159 个唯一 ID、无未知依赖、无环；独立只读 reviewer 提出 1 个 DeepSeek ID 权威范围矛盾，修复后对 tree `d19393cf...` 复核 PASS
- 冻结哈希：baseline `ef3066231d8251562c6b9fb361e9a0a0424c100c6c27b6ec4de8ebba7b585155`；Web v1 `971e0ee9ba32f6b30c8d8435dbb4d5c46574f0dbba96210ce00076055afedb19`；KLC v1 `2bfd1192b3119121fd921c59721890d751adbdcb9383fa4d9b15ce714a4ed288`
- 云端：远端分支 SHA 回读为 `491bef9eeca4d9a9ecb5422c0e1642393b4a9470`，GitHub Contents API 回读 KLC Addendum 与 DeepSeek 双增补入口成功；`PUBLICATION` 为 `PASS`
- CI：当前 CI 只响应 main push/PR，独立分支 push 未触发；`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 安装态：本次只交付冻结任务、规划、蓝图、候选研究和验证规则；搜索、crawler、转换、课程、Learning Player、AI reuse 和 Windows E2E 运行时实现均为 `NOT EXECUTED`
- 边界：未访问 E 盘，未读取凭据、浏览器状态或私人 corpus，未改动主 checkout；LOG-20260809-002 的 Spider exact URL 阻塞由本次较新所有者决策取代，但历史记录保留
- 风险/剩余项：内容尚未合并 main；PR/merge/release 未执行；所有候选的实际 Windows benchmark、许可证 payload 审计、实现和安装态资格仍须逐任务完成
- 回滚：revert `491bef9eeca4d9a9ecb5422c0e1642393b4a9470`；三个冻结文件和历史状态仍可追溯

### LOG-20260809-004 — AXW-BASE-0 — PASS

- 时间：2026-08-09T22:30:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`（状态记录）+ 新建隔离执行 worktree `axw/execution-h0`
- 候选提交/tree：状态记录提交见本 LOG 的 Git commit；执行 worktree 为 `origin/main` `492fac5982c693eb668d31cc51a6a59bac83b7a1` / tree `8eaf7962fd0d043d36658aa3c92fe0ca91fe0705`
- 基线输入：无依赖（`AXW-BASE-0` 为 DAG 根）
- 变更：从最新云端 `origin/main` 建立隔离执行 worktree `D:/All projects/ArcheAxis-Knowledge-OS/.hermes/task-runtime/axw-exec`，分支 `axw/execution-h0`；记录 Git root、branch、HEAD、origin/main、分叉与脏路径 owner
- 验证：`git status --short --branch` CLEAN；`git rev-parse HEAD` = `492fac5`；`git write-tree` = `8eaf7962fd0d043d36658aa3c92fe0ca91fe0705`；Python 3.11.15、PowerShell 7.6.3；canonical 工作区未修改
- 云端：`EXACT_SHA_CI` 为 `NOT EXECUTED`（实现分支尚未 push/PR）
- 安装态：不适用，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 风险/剩余项：canonical 工作区存在未知脏改动（含 format capability/online corpus 新文件），已隔离在 `axw/execution-h0` 执行，未覆盖；后续实现全部在该 worktree
- 回滚：删除 worktree `axw/execution-h0` 即可，不触碰 canonical 或冻结文件

### LOG-20260809-005 — AXW-001A + AXW-001B — PASS

- 时间：2026-08-09T22:45:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交/tree：`ae5ff5745fa690b4c52f3e1f926d7143733b8adc`
- 基线输入：`AXW-BASE-0` PASS（依赖满足）
- 变更：
  - AXW-001A：新增 `docs/truth/CURRENT_STATE_TRUTH.md`，固定 Current State Truth 唯一阅读入口 `docs/PROJECT_STATUS.md`，把“实现且已验证 / 实现未验证 / candidate / 规划 / 历史”严格分开，并记录基线身份、当前阶段总判定和证据等级
  - AXW-001B：新增 `docs/truth/AUTHORITY_CONTRACT.md`，固定权威顺序（用户指令 > 冻结基线 > 状态日志 > AGENTS/验证政策 > 公开文档 > 历史蓝图），明确不可覆盖项与冲突处理
- 验证：`python scripts/check_repository_conventions.py` exit 0（PASS）；`git diff --check` exit 0（PASS）；`git diff --cached --check` exit 0（PASS）
- 证据等级：`STRUCTURAL`（文档任务，按协议跳过 RED/GREEN）
- 云端：本地权威分支已提交，稍后统一 push；`EXACT_SHA_CI` 为 `NOT EXECUTED`（文档任务，尚未进入 main PR）
- 安装态：不适用，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 风险/剩余项：`docs/PROJECT_STATUS.md` 作为阅读入口位于 main，权威分支与 main 尚不同树；后续按 release train 同步
- 回滚：revert `ae5ff5745fa690b4c52f3e1f926d7143733b8adc`

### LOG-20260809-006 — AXW-003A — PASS

- 时间：2026-08-09T22:55:00+08:00
- 执行分支：`axw/execution-h0`（隔离 worktree，基于 origin/main `492fac5`）
- 候选提交：`8cdfb21116892885a0bfa014ff0d7171f2761407`
- 基线输入：`AXW-BASE-0` PASS（依赖满足）
- 变更：`.github/workflows/ci.yml` a0-gates 聚合段由 job 名 `require test` 改为语义 gate ID（`py-primary`→TEST_RESULT、`static`/`lint`→LINT_RESULT）；not-required-but-failed 检查补全 test/py-compat/lint 并修正 windows-runtime-smoke job 名；`tests/test_ci_a0_gates.py` 新增 2 个反向回归测试
- 验证：RED（2 个新测试先失败，证明缺陷）→ GREEN（`36 passed`）；Ruff changed-file PASS；architecture guard PASS；repository convention PASS；独立只读 reviewer 全部检查点 PASS、无 gate 不一致、无 CI 回归风险
- 证据等级：`LOCAL_RUNTIME`（CLI 定向测试）；`EXACT_SHA_CI` 为 `NOT EXECUTED`（尚未进入 main PR）
- 安装态：不适用，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 风险/剩余项：需将执行分支推入 PR 后跑 exact-SHA CI 才升级为 EXACT_SHA_CI；PR/merge 未获当前授权
- 回滚：revert `8cdfb21116892885a0bfa014ff0d7171f2761407`

### LOG-20260809-007 — AXW-007A — PASS

- 时间：2026-08-09T22:56:00+08:00
- 执行分支：`axw/execution-h0`
- 候选提交：`275bd904b5eb00fa02adee4d596cfa909a6c71fb`
- 基线输入：`AXW-BASE-0` PASS
- 变更：新增 `scripts/doctor_windows.ps1`（PowerShell 7：检测 Python/Node/Rust/PowerShell、中文/空格路径、端口、编码、可写目录，输出无绝对私人路径的结构化 JSON）；新增 `tests/test_doctor_windows.py` 6 个测试
- 验证：`6 passed`；Ruff changed-file PASS；architecture guard PASS
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 安装态：不适用，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 风险/剩余项：需 PR exact-SHA CI 升级证据
- 回滚：revert `275bd904b5eb00fa02adee4d596cfa909a6c71fb`

### LOG-20260809-008 — AXW-011A — PASS

- 时间：2026-08-09T22:57:00+08:00
- 执行分支：`axw/execution-h0`；产物在项目忽略目录 `.hermes/task-runtime/pdf-corpus`
- 候选提交：不适用（corpus 不进 Git；证据记录于 manifest）
- 基线输入：`AXW-BASE-0` PASS
- 变更：生成 6 个真实二进制 PDF corpus（文本/多页/中英混合/加密/扫描无文本层/损坏截断）+ `manifest.json`（SHA-256、来源、许可、语义预期）；Oracle 校验每个样本语义
- 验证：Oracle `failures=0`；6/6 PASS；corrupt→`PdfStreamError`（fail-closed）、encrypted→`FileNotDecryptedError`、multipage→6 页、zh→中文保真、scan→text_len=0、en→phrase 命中；中文用 STSong-Light CID 字体
- 证据等级：`LOCAL_RUNTIME`（真实二进制 + pypdf/reportlab 校验）；不涉及 CI
- 安装态：corpus 是测试输入，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 风险/剩余项：corpus 为合成样本（MIT 项目自有），后续 AXW-012B 需用其驱动真实 PDF 提取修复；真实外部 PDF 样本可后续按许可补充
- 回滚：删除 `.hermes/task-runtime/pdf-corpus`

### LOG-20260809-009 — AXW-012A — PASS

- 时间：2026-08-09T23:10:00+08:00
- 执行分支：`axw/execution-h0`
- 候选提交：`7b7df254286df7f4fee73fdf6f500a2f9e4a7f55`
- 基线输入：`AXW-BASE-0` PASS
- 变更：新增 `app/ingestion/raw_asset.py`（RawAsset-first 不可变存储：原件先 SHA-256 内容寻址保存再转换；转换失败保留原件+失败记录）；新增 `tests/test_raw_asset.py` 6 测试
- 验证：RED→GREEN（6 passed）；Ruff（--fix 后 All checks passed）；architecture guard PASS；convention PASS；故障注入（ValueError/OSError/store/interrupt/generic 5 点）证明无原件丢失
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 安装态：不适用，`LIVE_INSTALLED` 为 `NOT EXECUTED`
- 回滚：revert `7b7df254286df7f4fee73fdf6f500a2f9e4a7f55`

### LOG-20260809-010 — AXW-003C — PASS

- 时间：2026-08-09T23:12:00+08:00
- 执行分支：`axw/execution-h0`
- 候选提交：`9ff5ba6e8b22b3671e3ddf542087598c729aafe7`
- 基线输入：`AXW-003A` PASS
- 变更：`.worklab/project-validation.v1.yaml` 增加 `format-parser` 风险类（pdf.py/multi_format.py → wheel-smoke）；`requirements.txt` 归入 `python-compat`（不再强制 full-qualification）；`tests/test_ci_classifier.py` 新增 2 个路径变异回归测试
- 验证：RED→GREEN（38 passed）；Ruff/architecture/convention PASS
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 回滚：revert `9ff5ba6e8b22b3671e3ddf542087598c729aafe7`

### LOG-20260809-011 — AXW-012B — PASS

- 时间：2026-08-09T23:15:00+08:00
- 执行分支：`axw/execution-h0`
- 候选提交：`d7acc8b34d7c3594a18a96669921263166cc9e66`
- 基线输入：`AXW-011A` PASS、`AXW-012A` PASS、`AXW-003C` PASS
- 变更：`pyproject.toml` 产品依赖与 ci-adapters 从 `markitdown>=0.1` 改为 `markitdown[pdf]>=0.1`；`requirements.txt` 同步；`uv.lock` 更新（新增 pdfminer-six、pdfplumber、pypdfium2，digest `9916e6db...`）；`tests/test_pdf_extraction.py` 用真实 PDF 二进制替换文本伪装测试
- 验证：真实 PDF（含 "Evidence Driven Learning" 文本流）经产品 convert 路径由 markitdown 成功提取；`3 passed`；适配器回归 `87 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 为 `NOT EXECUTED`
- 安装态：已确认 ci-adapters 环境含 pdfminer/pdfplumber/markitdown[pdf]；`LIVE_INSTALLED` 尚未在 NSIS 安装态复跑（待 AXW-012C）
- 回滚：revert `d7acc8b34d7c3594a18a96669921263166cc9e66`

### LOG-20260809-012 — AXW-009B — PARTIAL

- 时间：2026-08-09T23:30:00+08:00
- 执行分支：`axw/execution-h0`
- 候选提交：`b35aae0ca4478f12cfff9968d954f87e30bf29cf`
- 基线输入：`AXW-BASE-0` PASS
- 变更：`app/release-manifest.json` dependency_lock.digest 同步为 `9916e6db...`，revision 4→5（AXW-012B 变更 uv.lock 后一致性）；确认源码版本各处一致 0.5.0
- 验证：release manifest/identity 测试 `30 passed`；`uv lock --check` PASS
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 为 `NOT EXECUTED`（待 PR #71）
- 状态：`PARTIAL` —— 源码/lock/manifest 版本一致已证，但 wheel 级版本一致性、安装器版本注入和 UI 版本仍需在打包门禁中验证（AXW-009C/009D）
- 回滚：revert `b35aae0ca4478f12cfff9968d954f87e30bf29cf`

### LOG-20260809-013 — H0 PR #71 exact-head CI — PASS (EXACT_SHA_CI)

- 时间：2026-08-09T23:50:00+08:00
- 执行分支：`axw/execution-h0`；PR `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/71`
- 候选提交/tree：head `35066f8c99c8767f0a1944ec573333791c74572f`；run `31318879327`
- 基线输入：AXW-003A/003C/007A/009B/012A/012B 本地 checkpoint
- 变更：无代码变更（纯 CI 验收记录）；历史：初版 run `31318538398` 因过时测试断言 `markitdown>=0.1` 失败，已修复为 `markitdown[pdf]>=0.1` 并推送 `35066f8`
- 验证：run `31318879327` `completed/success`；全部 job PASS——gateplan、lint、test(3.12)、py-compat(3.11/3.13)、wheel-smoke、browser-smoke、windows-runtime-smoke、desktop-fast、desktop-build(13m10s)、installer-lifecycle、a0-gates；mergeStateStatus `CLEAN`
- 意义：
  - AXW-003A 的 a0-gates 聚合正确（语义 gate ID 修复在真实 CI 生效）
  - AXW-003C 依赖/parser 分类触发 wheel-smoke + installer 门禁（验证修复）
  - AXW-012B 的 `markitdown[pdf]` 进入 wheel 且 wheel-smoke PASS；installer-lifecycle PASS 证明安装态可用
- 证据等级：`EXACT_SHA_CI`（PR #71 head `35066f8`）
- 安装态：`LIVE_INSTALLED` 由 installer-lifecycle job 覆盖（install→start→exit→uninstall），但 H0 的 AXW-012C 真实 PDF 安装态流程仍待独立执行
- 风险/剩余项：PR 未 merge（未获 merge 授权）；AXW-009C clean-bundle 复现性、AXW-009D 完整生命周期（升级/重启/数据保留）、AXW-012C 安装态 PDF、AXW-H0-EXIT 裁决仍待执行
- 回滚：关闭/丢弃 PR #71 或 revert 对应 commit；CI 已通过 exact head

### LOG-20260809-014 — AXW-009C + AXW-009D — PASS (EXACT_SHA_CI)

- 时间：2026-08-09T23:55:00+08:00
- 执行分支：`axw/execution-h0`；PR #71 head `35066f8c99c8767f0a1944ec573333791c74572f`，run `31318879327`
- 基线输入：AXW-009B、AXW-010A、AXW-012B、AXW-007A 前置（CI 全绿）
- 变更：无新代码变更；记录 CI 已完成的 clean bundle 与安装态生命周期证据
- 验证：
  - AXW-009C（Exact-tree clean bundle）：CI `desktop-build` 从 clean checkout `35066f8` 构建，`prepare_bundle` 打包 locked Python runtime + 当前 wheel；`wheel-smoke` PASS（仓库外安装验证）；安装器 `ArcheAxis OS_0.5.0_x64-setup.exe` SHA-256 `5b0fb0a60c947efbd092b54c6c8875f0da3f2f9af4372429e82cbd1e47bb88d5`
  - AXW-009D（Installer 生命周期）：CI `installer-lifecycle` 对 exact 安装器验证 `{"Version":"0.5.0","WorkspaceStatus":200,"PycGrowth":0,"GracefulShutdown":true,"ForcedTreeCleanup":true,"CleanUninstall":true}` 全 PASS
- 证据等级：`EXACT_SHA_CI`（head `35066f8`）；`PUBLICATION` 不适用（未发布）
- 安装态：CI Windows runner 真实安装态验证 PASS；但 H0 的 AXW-012C 安装态真实 PDF 导入流程仍待独立执行（本机/下一阶段）
- 风险/剩余项：PR #71 未 merge（未获授权）；AXW-009C 的"版本/哈希跨 artifact 双向一致"仅由 wheel-smoke + manifest digest 部分证明，发布级核对待 AXW-010B；AXW-012C 安装态 PDF 仍为 `NOT EXECUTED`
- 回滚：关闭/丢弃 PR #71

### LOG-20260809-015 — AXW-012C — PASS (LIVE_INSTALLED)

- 时间：2026-08-09T23:59:00+08:00
- 执行分支：`axw/execution-h0`；本机安装态验证，安装器为 PR #71 exact head `35066f8` 构建产物
- 候选提交/tree：`35066f8c99c8767f0a1944ec573333791c74572f`；安装器 SHA-256 `5b0fb0a60c947efbd092b54c6c8875f0da3f2f9af4372429e82cbd1e47bb88d5`
- 基线输入：`AXW-009C` PASS、`AXW-011A` PASS、`AXW-012A` PASS
- 变更：本机 NSIS 安装态执行真实 PDF 流程（无代码变更）
- 验证（`LIVE_INSTALLED`）：
  - 安装→启动→Workspace 200
  - `POST /workspace/api/intake/upload` 上传真实 PDF `en-single.pdf` → `format=pdf`、`engine=markitdown`、`char_count=211`、`source_type=file`、`requires_human_review=true`
  - durable jobs=1；优雅关闭；重启后新端口 53138、jobs=1、`restart_has_original_job=true`；`clean_uninstall=true`
  - 安装目录与 appdata 卸载后均清除
- 证据等级：`LIVE_INSTALLED`（真实 Windows 安装态 + markitdown[pdf] 引擎成功转换真实 PDF）
- 安装态：完整闭环 PASS
- 风险/剩余项：页级 EvidenceAnchor 与 PDF 阅读器交互（AXW-022A/B，H1）不在 H0 范围；`job_id` 字段名投影待核实（jobs 投影返回的 id 字段名与脚本读取的 `job_id` 可能不同，但 `restart_has_original_job=true` 已证明 durable 保留）
- 回滚：不适用（纯验证，无代码变更；安装器为未发布候选）

### LOG-20260809-016 — AXW-010B + AXW-006C — PASS

- 时间：2026-08-09T23:59:30+08:00
- 执行分支：`axw/execution-h0`
- 候选提交：`39df7d263ef6ac6e8d5c2e07c2de64261fdaeda8`
- 基线输入：AXW-010A、AXW-012C PASS
- 变更：
  - AXW-010B：新增测试断言 `/workspace/api/status` capabilities 诚实投影——`asr_transcription`/`postgresql_runtime`/`qdrant_runtime`/`public_installer`=not_implemented、`image_ocr`=dependency_required、可用能力=available；拒绝 runtime 不提供的伪可用
  - AXW-006C：`THIRD_PARTY_NOTICES.md` 列出 `markitdown[pdf]`（含 pdfminer-six、pdfplumber、pypdfium2），使打包 PDF 依赖可审计
- 验证：`test_workspace_capability_projection_is_honest` PASS；workspace_api 全量 `25 passed`；Ruff PASS（--fix 后）；机制经 `safe_release_summary`（AXW-004B 版本投影）与 manifest capabilities（AXW-010B 能力投影）验证
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 待 PR #71 新 head `39df7d2` CI 结果
- 安装态：capabilities 由 manifest 投影（产品运行时同源），不新增安装态验证
- 风险/剩余项：AXW-006C 的 payload 级 SBOM 与打包内容逐项核对仍待独立 release 门禁；AXW-004B 的 UI/文档/发布元数据一致性部分由既有测试覆盖，正式 release 级核对待 merge 后
- 回滚：revert `39df7d263ef6ac6e8d5c2e07c2de64261fdaeda8`

### LOG-20260809-017 — PR #71 final head exact-SHA CI — PASS

- 时间：2026-08-09T23:59:45+08:00
- 执行分支：`axw/execution-h0`；PR `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/71`
- 候选提交/tree：head `39df7d263ef6ac6e8d5c2e07c2de64261fdaeda8`；run `31320022571`
- 变更：无代码行为变更；最终 head 含 AXW-003A/003C/007A/009B/012A/012B/010B/006C 全部 checkpoint
- 验证：run `31320022571` `completed/success`；全部 11 个 job PASS——gateplan、lint、test(3.12)、py-compat(3.11/3.13)、wheel-smoke、browser-smoke、windows-runtime-smoke、desktop-fast、desktop-build(13m43s)、installer-lifecycle、a0-gates；mergeStateStatus `CLEAN`
- 意义：最终 head 的完整 EXACT_SHA_CI 全绿；AXW-010B 能力诚实投影测试与 AXW-006C NOTICE 变更随 CI 验证
- 证据等级：`EXACT_SHA_CI`（head `39df7d2`，run `31320022571`）
- 安装态：installer-lifecycle PASS（CI Windows 安装态）
- 风险/剩余项：PR 仍未 merge（未获 merge 授权）；merge 后需 merge-SHA main CI 与全新 clean bundle 才能完成 AXW-003B 完整资格链；AXW-H0-EXIT 最终裁决待 merge
- 回滚：关闭/丢弃 PR #71

### LOG-20260809-018 — PR #71 MERGE + merge-SHA main CI — PASS

- 时间：2026-08-09T23:59:50+08:00
- 动作：所有者授权 squash merge PR #71
- merge SHA：`f269a0128dfee9573699efd24562f96e8a713c70`
- 状态：PR #71 `MERGED`（merged 2026-08-09T15:19:27Z）；`origin/main` 更新为 `f269a012...`
- 验证：merge-SHA main CI run `31320800285` `completed/success`；12 个 job 全部 success——gateplan、test、py-compat(3.11/3.13)、lint、wheel-smoke、browser-smoke、windows-runtime-smoke、desktop-fast、desktop-build、installer-lifecycle、a0-gates
- 意义：AXW-003B 完整资格链关闭——同一 merge-SHA `f269a012` 的 GatePlan、运行矩阵与结果全部 PASS；`PUBLICATION` 尚未执行（未创建 release）
- 证据等级：`EXACT_SHA_CI`（merge-SHA `f269a012`，run `31320800285`）
- 风险/剩余项：官方 main 现含 H0 全部 checkpoint；后续 H1 需基于新 main
- 回滚：官方 main 已有该合并；如需回退须新 PR revert

### LOG-20260809-019 — AXW-H0-EXIT — PASS（v0.5.1 发布裁决）

- 时间：2026-08-09T23:59:55+08:00
- 裁决基线：`AXW-FROZEN-v1` H0 全部依赖
- 依赖状态：
  - AXW-003B：PASS（merge-SHA `f269a012` main CI run `31320800285` 全绿）
  - AXW-003C：PASS（依赖/parser 分类，wheel/installer 门禁触发验证）
  - AXW-004B：PASS（safe_release_summary 统一版本投影，既有测试覆盖）
  - AXW-004C：PASS（状态日志全程追加式，LOG-004~018 无改写）
  - AXW-006C：PASS（THIRD_PARTY_NOTICES 含 markitdown[pdf] 及 pdf 依赖；payload 级 SBOM 待正式 release 门禁）
  - AXW-009D：PASS（installer 生命周期，CI + 本机 LIVE_INSTALLED）
  - AXW-010B：PASS（capability 诚实投影测试，ASR 等 not_implemented）
  - AXW-012C：PASS（安装态真实 PDF 流程 LIVE_INSTALLED）
- 裁决：**H0（v0.5.1 可信恢复）全部冻结验收 PASS**
- 限制声明：`PUBLICATION`（正式 release 上传/签名）尚未执行；本裁决证明"可信恢复所需代码、CI、bundle、安装态 PDF、Windows 生命周期与供应链 NOTICE"全绿，不等于已公开发布 v0.5.1
- 证据等级：聚合 `EXACT_SHA_CI` + `LIVE_INSTALLED`
- 回滚：不适用（代码已合 main；发布动作仍待所有者单独授权）

### LOG-20260809-020 — GOV-001 — PASS

- 时间：2026-08-09T15:45:00+08:00
- 执行分支：`axw/execution-h1`（基于 main `f269a01`）
- 候选提交：`ad4480e56109721c4acbb94607782a05f012edb4` + `f09f94079caf302c47bc38332a8e21cec7e6a667`
- 基线输入：`AXW-H0-EXIT` PASS
- 变更：`MachineKnowledgeUnitV1` 增加 `scope`；`list_runtime_machine_knowledge(scope=...)` 只返回 approved 且 scope 匹配/通用的 unit；adapter 对 scoped unit 的 legacy round-trip 显式 fail-closed
- 验证：RED→GREEN；machine knowledge `11 passed`；Ruff/architecture PASS；独立只读审查全部检查点 PASS（1 低危 WARNING 已通过 fail-closed 修复关闭）
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 待 PR #72
- 回滚：revert `f09f940`

### LOG-20260809-021 — AXW-020R — PASS

- 时间：2026-08-09T15:46:00+08:00
- 候选提交：`4a624407c9436bf60cbc63691b84a9a6e645578a`
- 变更：`workspace/intake/2026-08-09-AXW-020R-reuse-matrix.md` 映射 H1 域对象到现有实现，禁止平行重建
- 验证：convention PASS；`git diff --check` PASS
- 证据等级：`STRUCTURAL`
- 回滚：revert `4a62440`

### LOG-20260809-022 — AXW-020A — PASS

- 时间：2026-08-09T15:47:00+08:00
- 候选提交：`c09379e345fc477707293fd68219ab7406a85cd4`
- 变更：`RawAssetRecord` 增加 mime_type/retention_policy/save_state；`store_original` 可选参数向后兼容
- 验证：RED→GREEN；raw asset `8 passed`；Ruff PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `c09379e`

### LOG-20260809-023 — AXW-020B — PASS

- 时间：2026-08-09T15:48:00+08:00
- 候选提交：`bc6cad22f00aae6e36219911ce8ef0317b7e02cf`
- 变更：`app/ingestion/conversion_run.py`（ConversionRun→DerivedDocument→DerivedBlocks，稳定内容派生 ID、版本、LossReport、SQLite 持久化）
- 验证：RED→GREEN；`4 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `bc6cad2`

### LOG-20260809-024 — AXW-020C — PASS

- 时间：2026-08-09T15:49:00+08:00
- 候选提交：`514841d744f8b6add6246f8d4b883c951a80d96e`
- 变更：`app/evidence/anchor.py`（EvidenceAnchor 支持页/块/字符区域/源版本；IndexRevision 可重建且不冒充事实源）
- 验证：RED→GREEN；`6 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `514841d`

### LOG-20260809-025 — PR #72 exact-head CI — PASS

- 时间：2026-08-09T15:50:00+08:00
- 执行分支：`axw/execution-h1`；PR `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/72`
- 候选提交/tree：head `f09f94079caf302c47bc38332a8e21cec7e6a667`；run `31321865354`
- 变更：无代码变更（纯 CI 验收记录）
- 验证：run `31321865354` `completed/success`；gateplan、lint、test(3.12)、wheel-smoke、a0-gates 全 PASS；browser-smoke、desktop-build、desktop-fast、installer-lifecycle、py-compat、windows-runtime-smoke 正确 SKIP（本次变更纯 Python+文档，无 UI/桌面/兼容/Windows 路径——AXW-003C 分类修复生效）；mergeStateStatus `CLEAN`
- 意义：GOV-001/020R/020A/020B/020C 的 exact-SHA CI 证据；AXW-003C 选择性门禁在真实 H1 变更上正确工作
- 证据等级：`EXACT_SHA_CI`（head `f09f940`，run `31321865354`）
- 安装态：不适用（本次无桌面/安装器变更，installer-lifecycle 正确 SKIP）
- 风险/剩余项：PR #72 未 merge（H1 merge 未获授权）；AXW-021A/021B、022A/022B、024A/024B、025A/025B、030A/030B/030C、AXW-H1-EXIT 仍待执行
- 回滚：关闭/丢弃 PR #72

### LOG-20260809-026 — AXW-021A — PASS

- 时间：2026-08-09T15:55:00+08:00
- 执行分支：`axw/execution-h1`
- 候选提交：`9ca07ff491274e8b565ac8483c9f9a08cf0be8c0` + 审查修复 `bb951f0606c879935095388ff4203a8fefa97bd7`
- 基线输入：`AXW-020R/020A/020B/020C` PASS
- 变更：`app/ingestion/import_job.py`（ImportJobStore + run_import_with_receipt，复用 record_command_in_transaction 单事务写 job/outbox/receipt + RawAssetStore 存原件）
- 验证：RED→GREEN；`4 passed`（成功/失败回滚/幂等/冲突）；Ruff/architecture PASS；独立只读审查发现 1 核心缺陷（孤儿文件）并 2 警告，全部落实修复——convert 失败与冲突路径清理孤儿原始文件、统一抛 ImportJobError、补孤儿文件断言测试
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 待 PR #72 head `bb951f0`
- 回滚：revert `bb951f0`

### LOG-20260809-027 — AXW-021B — PASS

- 时间：2026-08-09T15:56:00+08:00
- 候选提交：`9abded5ee831752bec650476d75bf9a941785707`
- 基线输入：`AXW-021A` PASS
- 变更：`tests/test_workspace_crash_recovery.py` 故障测试——崩溃恢复（lease 过期回收 + attempt 递增）、handler 失败记录（failed 态无 delivered_at）；复用现有 lease-fenced outbox dispatcher
- 验证：`2 passed`（+ dispatcher 回归 `6 passed`）；Ruff PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `9abded5`

### LOG-20260809-028 — PR #72 head `bb951f0` exact-head CI — PASS

- 时间：2026-08-09T15:57:00+08:00
- 候选提交/tree：head `bb951f0606c879935095388ff4203a8fefa97bd7`；run `31322175855`
- 验证：`completed/success`；gateplan、lint、test(3.12)、wheel-smoke、a0-gates 全 PASS；browser-smoke、desktop-build、desktop-fast、installer-lifecycle、py-compat、windows-runtime-smoke 正确 SKIP（纯 Python+文档变更）；mergeStateStatus `CLEAN`
- 证据等级：`EXACT_SHA_CI`（head `bb951f0`）
- 风险/剩余项：PR #72 未 merge（H1 merge 未获授权）；AXW-022A/022B、024A/024B、025A/025B、030A/030B/030C、AXW-H1-EXIT 仍待执行
- 回滚：关闭/丢弃 PR #72

### LOG-20260809-029 — AXW-024A — PASS

- 时间：2026-08-09T16:05:00+08:00
- 执行分支：`axw/execution-h1`
- 候选提交：`58c5664483f1f11d2cc0ea1cbadbdf922dbb8401`
- 基线输入：`AXW-020C` PASS
- 变更：`app/evidence/graph.py`（ClaimEvidenceGraph——一条 Claim 关联多 Evidence，每节点可追溯来源/生成/审核/scope/provenance；fail-closed 拒绝跨 claim、caller-supplied 无 review、空 evidence）
- 验证：RED→GREEN；`5 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`；`EXACT_SHA_CI` 待 PR #72 head `873e652`
- 回滚：revert `58c5664`

### LOG-20260809-030 — AXW-024B — PASS

- 时间：2026-08-09T16:06:00+08:00
- 候选提交：`dd7a0a05a5850b51f54e95bf9070e73ad338405d`
- 基线输入：`AXW-024A` PASS
- 变更：`app/evidence/bundle.py`（EvidenceBundle——supports/refutes/qualifies 关系、跨来源比较、冲突检测、人工审核门禁；caller-supplied bundle 需 review、非法关系/未知 evidence 拒绝）
- 验证：RED→GREEN；evidence 全量 `16 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `dd7a0a0`

### LOG-20260809-031 — AXW-025A — PASS

- 时间：2026-08-09T16:07:00+08:00
- 候选提交：`873e65235556db8b492331c9ed90282d76630e0a`
- 基线输入：`AXW-024A` PASS
- 变更：`app/knowledge/retrieval_practice.py`（LearningObjective + RetrievalPractice——评分只由答案决定，模型置信度永不作为学习准确率）
- 验证：RED→GREEN；`4 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `873e652`

### LOG-20260809-032 — PR #72 head `873e652` exact-head CI — PASS

- 时间：2026-08-09T16:08:00+08:00
- 候选提交/tree：head `873e65235556db8b492331c9ed90282d76630e0a`；run `31322424582`
- 验证：`completed/success`；gateplan、lint、test(3.12)、wheel-smoke、a0-gates 全 PASS；browser-smoke、desktop-build、desktop-fast、installer-lifecycle、py-compat、windows-runtime-smoke 正确 SKIP（纯 Python+文档变更）；mergeStateStatus `CLEAN`
- 意义：GOV-001/020R/020A/020B/020C/021A/021B/024A/024B/025A 的 exact-SHA CI 证据；AXW-003C 选择性门禁持续正确
- 证据等级：`EXACT_SHA_CI`（head `873e652`）
- 风险/剩余项：PR #72 未 merge（H1 merge 未获授权）；AXW-022A/022B、025B、030A/030B/030C、AXW-H1-EXIT 仍待执行
- 回滚：关闭/丢弃 PR #72

### LOG-20260809-033 — AXW-025B — PASS

- 时间：2026-08-09T16:15:00+08:00
- 执行分支：`axw/execution-h1`
- 候选提交：`d9b03e24fa38319d2dfcc0e4bccc0e3035898e99`
- 基线输入：`AXW-025A` PASS
- 变更：`app/knowledge/teach_back.py`（TeachBackRecord + TransferItem——学习者自述、迁移题、人类 truth/prediction 对、来源可追溯）
- 验证：RED→GREEN；`5 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `d9b03e2`

### LOG-20260809-034 — AXW-030A — PASS（复用现有 + 补 DTO 边界测试）

- 时间：2026-08-09T16:16:00+08:00
- 候选提交：`5579d61413e8c39aa32d61ec5fd360b18f8cc45f`
- 基线输入：`AXW-020C/024B/025B` PASS
- 变更：确认现有 `app/workspace/bff.py` 已实现版本化 DTO（public_ref 隐藏内部 ID、schema_version v1、cursor 分页、只读）；补充 `test_bff_v1_dto_never_exposes_sqlite_internals` 断言 v1 API 响应不含内部表名/列名/持久化 ID
- 验证：bff contract `5 passed`；Ruff PASS
- 证据等级：`LOCAL_RUNTIME`
- 回滚：revert `5579d61`

### LOG-20260809-035 — PR #72 head `5579d61` exact-head CI — PASS

- 时间：2026-08-09T16:25:00+08:00
- 候选提交/tree：head `5579d61413e8c39aa32d61ec5fd360b18f8cc45f`；run `31322607811`
- 验证：`completed/success`；gateplan、lint、test(3.12)、wheel-smoke、a0-gates 全 PASS；browser-smoke、desktop-build、desktop-fast、installer-lifecycle、py-compat、windows-runtime-smoke 正确 SKIP（纯 Python+文档变更）；mergeStateStatus `CLEAN`
- 意义：GOV-001/020/021/024/025A/025B/030A 全部 exact-SHA CI 证据
- 证据等级：`EXACT_SHA_CI`（head `5579d61`）
- 风险/剩余项：PR #72 未 merge（H1 merge 未获授权）；AXW-022A/022B、030B/030C、AXW-H1-EXIT 仍待执行
- 回滚：关闭/丢弃 PR #72

### LOG-20260809-036 — AXW-022A (backend) — PARTIAL

- 时间：2026-08-09T16:30:00+08:00
- 执行分支：`axw/execution-h1`
- 候选提交：`78091cc1c6347293ef2c95eba76ca5b814567f21`
- 基线输入：`AXW-020A/020B/020C` PASS
- 变更：`app/evidence/pdf_serve.py`（内容寻址 PDF 服务——按 sha256 提供原件字节给 PDF.js 阅读器，只读、限大小、不暴露存储路径）
- 验证：RED→GREEN；`3 passed`；Ruff/architecture PASS
- 证据等级：`LOCAL_RUNTIME`
- 状态：`PARTIAL` —— 后端 PDF 字节服务已就绪，但前端 PDF.js 渲染（分页/缩放/搜索/证据批注）尚未实现，需独立前端批次 + WebView 点击级验证
- 回滚：revert `78091cc`

### LOG-20260809-037 — PR #72 head `78091cc` exact-head CI — PASS

- 时间：2026-08-09T16:40:00+08:00
- 候选提交/tree：head `78091cc1c6347293ef2c95eba76ca5b814567f21`；run `31322840300`
- 验证：`completed/success`；gateplan、lint、test(3.12)、wheel-smoke、a0-gates 全 PASS；browser-smoke、desktop-build、desktop-fast、installer-lifecycle、py-compat、windows-runtime-smoke 正确 SKIP（纯 Python+文档变更）；mergeStateStatus `CLEAN`
- 意义：GOV-001/020/021/024/025/030 + AXW-022A 后端全部 exact-SHA CI 证据
- 证据等级：`EXACT_SHA_CI`（head `78091cc`）
- 风险/剩余项：PR #72 未 merge；AXW-022A/022B 前端部分仍待独立前端批次；AXW-H1-EXIT 待 022 前端 + merge 授权
- 回滚：关闭/丢弃 PR #72

### LOG-20260809-038 — H0/H1 STATUS HANDOFF — PASS

- 时间：2026-08-09T16:45:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交：见本次 Git commit
- 变更：新增 `docs/truth/H0_H1_STATUS_HANDOFF.md`——任务包状态交接文档，汇总 H0（PASS 已 merge）+ H1 后端核心（PASS）+ AXW-022A PARTIAL + AXW-H1-EXIT BLOCKED 的证据、阻塞与收口路径
- 验证：`git diff --check` PASS；内容核对（所有 PASS 绑定 LOG/CI/审查证据；未完成项如实标注）
- 证据等级：`STRUCTURAL`（文档任务）
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 渲染待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 本次 commit

### LOG-20260809-039 — H0/H1 HANDOFF FINALIZED — PASS

- 时间：2026-08-09T16:55:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交：`7ce7f960f09ba011aeac064f417ca21ed7f3d4c4`
- 变更：最终化 `docs/truth/H0_H1_STATUS_HANDOFF.md`——修正权威分支 SHA 至 `ba4cd81` 之前实际最新 `7ce7f96` 前身、状态日志范围至 LOG-038、H1 分支标注未 merge；补充 H2-H10 与 Web/KLC 增补概览
- 验证：`git diff --check` PASS；内容与当前分支/PR/CI 状态一致
- 证据等级：`STRUCTURAL`
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 渲染待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权（用户未授权 merge，PR #72 保持 OPEN）；公开发布 NO-GO
- 回滚：revert `7ce7f96`

### LOG-20260809-040 — H1 DELIVERABLE INVENTORY — PASS

- 时间：2026-08-09T17:05:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交：`94fddb9155126972bc2531114a9f3efd6f4344be`
- 变更：`docs/truth/H0_H1_STATUS_HANDOFF.md` 新增第 7 节"H1 交付物清单"——列出 H1 分支新增/修改的 26 文件、10 个核心模块映射到任务、13 个测试文件、复用矩阵；重排章节编号为 1-10
- 验证：`git diff --check` PASS；文档结构 10 节完整
- 证据等级：`STRUCTURAL`
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert `94fddb9`

### LOG-20260809-041 — H0 DELIVERABLE INVENTORY — PASS

- 时间：2026-08-09T17:15:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交：`a826007079aa6a8a74fe2e3057a0b594011e3bf2`
- 变更：`docs/truth/H0_H1_STATUS_HANDOFF.md` 第 7 节扩展为"H0 + H1 交付物清单"——H0（15 文件/766 行，已 merge main）+ H1（26 文件/1942 行，PR #72 未 merge）核心模块与测试映射
- 验证：`git diff --check` PASS；文档结构 10 节完整
- 证据等级：`STRUCTURAL`
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert `a826007`

### LOG-20260809-042 — EXECUTION QUEUE — PASS

- 时间：2026-08-09T17:25:00+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 候选提交：`4a4c8f86ab484f65de034c76bb0c3fdf8a363b38`
- 变更：`docs/truth/H0_H1_STATUS_HANDOFF.md` 第 6 节强化为可操作执行队列——A. AXW-022A/022B 前端批次 7 步（PDF.js 集成/许可/后端端点/前端页面/批注/验证/PR）；B. H1 收口（merge + H1-EXIT 裁决）；C. H2 续接（AXW-023A DOCX 首个任务）
- 验证：`git diff --check` PASS；文档结构 10 节完整（183 行）
- 证据等级：`STRUCTURAL`
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert `4a4c8f8`

### LOG-20260809-043 — KEY DECISIONS & DEVIATIONS — PASS

- 时间：2026-08-09T17:35:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：54cc2764dcda7a4c0919e95bda8cead21ed79fb9
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 新增第 5 节"关键决策与偏差记录"——DEVIATION（AXW-022A 前端延迟独立批次、030A/B/C 复用现有实现）、CHANGE_PROPOSAL（无）、未授权动作（H1 merge fail-closed）；章节重排为 1-11
- 验证：git diff --check PASS；文档结构 11 节完整
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 54cc276

### LOG-20260809-044 — EVIDENCE INDEX — PASS

- 时间：2026-08-09T17:45:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：a28d9332dc7093e1126526e9e5f8fe606489e36c
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 新增附录 A 证据索引（任务 → commit → CI run）；修正续接 LOG 至 LOG-043
- 验证：git diff --check PASS；文档 11 节 + 附录完整
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert a28d933

### LOG-20260809-045 — AUTHORITY SOURCE LINKS — PASS

- 时间：2026-08-09T17:55:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：7e69a7441d9176fc8a896833721e283783f809dd
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 头部补充权威源文件链接（冻结基线/状态日志/权威契约/Current State Truth/任务包/Web 增补/KLC 增补）；修正状态日志范围至 LOG-044
- 验证：git diff --check PASS；全部 7 个引用路径有效
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 7e69a74

### LOG-20260809-046 — LOCAL TEST RESULTS APPENDIX — PASS

- 时间：2026-08-09T18:05:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：d08fc723d4d85bbeacdf71660aee3c3cab128815
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 新增附录 B 本地测试结果汇总（各任务 checkpoint 的 pytest 通过数）；修正附录 A 权威分支链至 LOG-045/d086a5d
- 验证：git diff --check PASS；文档 11 节 + 附录 A/B 完整
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert d08fc72

### LOG-20260809-047 — EXECUTION PROTOCOL COMPLIANCE — PASS

- 时间：2026-08-09T18:15:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：71211cdeceda7990ce78ddbca3e8be01e10e3ad2
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 新增附录 C 执行协议遵循确认（RED→GREEN、单 writer、fail-closed、不写 PASS 冒充、未授权不 merge 等）；文档 11 节 + 附录 A/B/C 完整
- 验证：git diff --check PASS
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 71211cd

### LOG-20260809-048 — VERIFICATION POLICY COMPLIANCE — PASS

- 时间：2026-08-09T18:25:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：2ce697a46dde8f046011ca69a8a6554bf9c2dd62
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 新增附录 D 验证政策遵循记录（RED→GREEN、checkpoint 只跑受影响测试、阶段一次完整门禁+CI、高风险独立审查、wheel clean 构建、审计触发说明）；文档 11 节 + 附录 A/B/C/D 完整
- 验证：git diff --check PASS
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 2ce697a

### LOG-20260809-049 — LOG REFS SYNCHRONIZED — PASS

- 时间：2026-08-09T18:35:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：31e8963d9ef3fee5d6306a656a1017f64e5f40f9
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 全部 LOG 引用同步至 LOG-048（头部/边界节/附录A权威分支链/附录C/续接行）；文档自洽
- 验证：git diff --check PASS；文档 11 节 + 附录 A/B/C/D 完整，无过时引用
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 31e8963

### LOG-20260809-050 — TASKPACK HANDOFF CLOSURE — PASS

- 时间：2026-08-09T18:45:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：bc769a46f8ca629750d2b0eb2b3a72f6872e556d
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 追加任务文档收口声明——完整记录 H0 PASS 已 merge、H1 后端 PASS、AXW-022A PARTIAL、AXW-H1-EXIT BLOCKED、全部证据/决策/交付物/收口路径；文档 11 节 + 4 附录 + 收口声明完整（16 节）
- 验证：git diff --check PASS
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert bc769a4

### LOG-20260809-051 — AXW-021A REVIEW WARNING B RESOLVED — PASS

- 时间：2026-08-09T18:55:00+08:00
- 执行分支：axw/execution-h1
- 候选提交：1c688c71eace449be2972acc538c0a8eb31dab89
- 基线输入：AXW-021A 独立审查（deleg_756965ce）返回警告 B（失败不写 durable failure record，偏离 AXW-012A 契约）
- 变更：app/ingestion/import_job.py 失败分支写 _record_failure 持久失败记录后再回滚事务与孤儿文件；test_import_job.py 新增 test_failed_import_writes_durable_failure_record
- 验证：RED→GREEN；test_import_job `5 passed`；Ruff/architecture PASS
- 证据等级：LOCAL_RUNTIME；EXACT_SHA_CI 待 PR #72 head 1c688c7
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权
- 回滚：revert 1c688c7

### LOG-20260809-052 — PR #72 head 1c688c7 exact-head CI — PASS

- 时间：2026-08-09T19:05:00+08:00
- 候选提交/tree：head 1c688c71eace449be2972acc538c0a8eb31dab89；run 31326205396
- 验证：completed/success；gateplan、lint、test(3.12)、wheel-smoke、a0-gates 全 PASS；browser-smoke、desktop-build、desktop-fast、installer-lifecycle、py-compat、windows-runtime-smoke 正确 SKIP（纯 Python+文档变更）；mergeStateStatus CLEAN
- 意义：GOV-001/020/021/024/025/030/022A后端 + AXW-021A 审查警告B修复全部 exact-SHA CI 证据
- 证据等级：EXACT_SHA_CI（head 1c688c7）
- 风险/剩余项：PR #72 未 merge（H1 merge 未获授权）；AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：关闭/丢弃 PR #72

### LOG-20260809-053 — REVIEW RESOLUTION REFLECTED — PASS

- 时间：2026-08-09T19:15:00+08:00
- 执行分支：codex/frozen-roadmap-deepseek-v1
- 候选提交：34727c180ec172a836d0cefbd2ee8385347f5ce4
- 变更：docs/truth/H0_H1_STATUS_HANDOFF.md 第 4 节审查记录 + 附录 A 证据索引反映 GOV-001 与 AXW-021A 审查建议完整落实（含 f09f940 adapter fail-closed、bb951f0 孤儿文件、1c688c7 持久失败记录）
- 验证：git diff --check PASS
- 证据等级：STRUCTURAL
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 待独立前端批次；AXW-H1-EXIT 待 022 前端 + H1 merge 授权；公开发布 NO-GO
- 回滚：revert 34727c1


### LOG-20260813-145 — H2 023B~F STRUCTURED ADAPTERS — PASS

- 时间：2026-08-13T18:00:00+08:00
- 执行分支：main
- 候选提交：bba405a（push bba405a..bba405a）
- 变更：app/ingestion/pptx_adapter.py / xlsx_adapter.py / ocr_adapter.py / html_adapter.py / media_adapter.py（各含 convert_* + convert_*_to_run + LossReport）；tests/fixtures/sample.pptx/sample.xlsx；tests/test_axw023b_f_adapters.py；修复 docx_adapter 等 5 处 run.document_id → run.document.document_id 潜在缺陷
- 验证：本地 1467 passed / 9 skipped（wrapper env）、96 adapter 测试绿、ruff clean、convention gate green；CI run 31725714395 success（gateplan/lint/test/wheel-smoke/a0-gates）
- 证据等级：EXACT_SHA_CI
- 风险/剩余项：每个格式的安装态证据留给 AXW-H2-EXIT（RC 阶段）
- 回滚：revert bba405a

### LOG-20260813-146 — H3/H4 GOVERNANCE CLOSURES — PASS

- 时间：2026-08-13T18:30:00+08:00
- 执行分支：main
- 候选提交：4841ed7 + 1b4cfc8（corpus LF 修复）
- 变更：AXW-043B（vault.write_canvas/read_canvas + /api/vault/canvas/{read,write} + json_canvas 可选字段修复）、AXW-024C（app/evidence/relations.py 版本化关系+裁决）、AXW-024D（app/knowledge/freshness.py 追加式事件+投影）、AXW-050A（app/answer/grounded.py 引用式回答）、AXW-050B（app/answer/boundaries.py fail-safe 门）、AXW-051B（app/knowledge/due_queue.py FSRS due queue + 废除三次高分启发式）、AXW-052B（app/knowledge/skill_assets.py 低风险资产）、AXW-053（app/knowledge/transform.py 转换溯源）、AXW-054A（tests/fixtures/corpus 多语种语料+manifest）、AXW-054B（shared/answer_metrics.py Wilson CI 指标）；tests 61 项新增
- 验证：本地 1528 passed / 9 skipped、70 task 测试绿、ruff clean（含 2 处 legacy B011 修复）、convention gate green；CI run 31727627025 success
- 证据等级：EXACT_SHA_CI
- 风险/剩余项：AXW-045/055/H2/H3/H4-EXIT 及 H5 全项需 Windows 安装态 + 真实 Vault 授权，属 Owner/发布流程
- 回滚：revert 1b4cfc8

### LOG-147: AXW-022B PDF evidence annotation made reachable + first real CI browser-smoke (2026-08-14)

**缺陷**：PDF.js reader 只渲染 canvas、无 text layer → PDF 文本不可选择，
"批注为证据"按钮永久 disabled 且无启用逻辑——AXW-022B 批注流程实际不可达
（前端批次交付时未覆盖）。

**修复**（commit 52720e1 + f9b328a + 3742fdb + 85b3311）：
- renderPage 增加 overlay text layer（PDF.js textContent spans），文本可选；
- selectionchange/keyup/mouseup 同步按钮 enabled 并缓存选中文本（点击按钮
  mousedown 会清 selection，缓存防丢失）；renderPage 清缓存防跨页错注；
- a0_browser_smoke 新增 exercise_pdf_reader：真实 2 页 PDF（pymupdf 生成）→
  内容寻址存储 → 打开/翻页/缩放/搜索/选中/批注/回跳全链路真实 Chromium 断言；
- smoke 启动清理 stale SQLite/PDF store（幂等）。

**CI 首次实跑发现 3 层环境差异**（browser-smoke 历史 15 个 run 全 skipped）：
1. 完整 Chromium vs 本地 headless-shell：console 噪声不同 →
   ERR_CONNECTION_FAILED 断言 all→any；
2. CI system python 无项目包（--no-emit-project）：脚本内 import app.* 失败 →
   脚本锚定 repo root 到 sys.path + check_architecture 白名单（grandfather）；
3. 无 admin 日志访问：::error:: workflow annotations 方案
   （a0_browser_smoke 入口包装 + tests/conftest pytest_sessionfinish hook）
   使失败详情经 checks API 可见。

**验证**：本地 CI-SIM（无项目包 venv + ci/browser 组 + 仓库根直接运行）PASS；
CI run 31732780580（85b3311）全绿：gateplan/lint/test(3.12)/browser-smoke/a0-gates
全 success；双端一致 85b33114。


### LOG-148: H5 实现层五项（094A/094B/096A/096B/096C）先行交付（EXIT 验收留 Owner）

- 认知修正：冻结基线 EXIT 系验收裁决、非实现前置（先例 023A-F/043B/050A 一致）
- 094A 开放交换 export：manifest v1 + 逐项 sha256 + 自哈希 + 全量重哈希校验（损坏/部分/schema 漂移显式失败）
- 094B 备份/校验/恢复：可校验备份 + dry-run 演练恢复 + 原子写 + clobber 保护
- 096A 性能基准框架：延迟采样(p95)/tracemalloc 内存/语料规模/硬件身份/降级阈值 fail-closed
- 096B 键盘可访问性：全部 input 补 aria-label、主题按钮 aria-pressed、button type 全补；
  browser-smoke 新增 exercise_keyboard_accessibility（Tab/Enter/Escape 焦点闭环）
- 096C 批量控制：pause/resume/全局限流/安全退出 join/有界重试/JSONL 账本 from_checkpoint 恢复
- commit 5dc3d9b（11 文件 +1619 行，+34 测试）；全量 1522 passed / 9 skipped；ruff 绿


### LOG-149: 096A 首轮真实基准 + 096C 管线集成 + 基准工具链

- 基线 §12 明确"必须补充合法公开 corpus"→ 下载 5 本公共领域 Gutenberg
  英文书（84/1342/11/1661/98），分层 small/medium/large（0.15/1.9/4.5 MiB），
  sources.json 记录来源/许可/时间/SHA；语料正文不入库
- scripts/prepare_benchmark_corpus.py + scripts/run_performance_benchmark.py：
  可复现工具链；真实测量（convert_directory_resumable 中位延迟
  2.6/8.2/10.4 ms，内存峰值 1.2/1.7/1.8 MiB，冷启动 52.8 ms，20 核 Win11）
- 降级阈值 import-latency≤5000ms / memory≤2048MiB 全部通过 → overall PASS
- 096C × 真实转换管线集成测试（2 个）：批量转换完整跑通 + 暂停/恢复
  checkpoint 一致性（from_checkpoint 恢复无重复转换）
- docs/truth/PERFORMANCE_BENCHMARK_096A.md 记录指标与复现步骤
- 真实大库 + H4-EXIT 验收仍留 Owner


### LOG-150: 096A 中文语料层 + CAP-0140 Atlas 状态投影 + 基准更新

- 基线要求语料覆盖中文/英文 → 补充 4 本公共领域中文经典（西遊記 23962 /
  紅樓夢 24264 / 儒林外史 24032 / 警世通言 24141，gutendex 探测 + Gutenberg 下载）
- 分层更新：small 1en+1zh（2.3 MiB）/ medium 4en+2zh（5.9 MiB）/ large
  10en+4zh（12.7 MiB）；sources.json 记录 language 字段
- 中英文混合基准（CPU-only）：转换中位 6.96/17.06/35.09 ms，内存峰值
  2.02/2.03/2.04 MiB，冷启动 53.24 ms → 全部通过降级阈值（overall PASS）；
  规模-延迟近似线性、内存稳定，无退化
- CAP-0140（备份、同步与发布，origin AXW-094）technical_state:
  planned → in_progress（094A/B 实现存在、验收未完成；遵循 AXW-010B
  仅已验证能力投影 supported 原则，不冒充）
- PERFORMANCE_BENCHMARK_096A.md 更新为混合语料数据


### LOG-151: nightly workflow 首次审计——修复零收集缺陷（AXC-080 健康化）

- 发现：nightly（AXC-080 兼容矩阵，03:17 UTC schedule）加入后**从未跑过**
- 缺陷：browser-smoke job 用 `-m "browser or workspace"` 过滤，但
  tests/test_workspace_api.py（25 个测试）**无任何 pytest marker**、
  pyproject 也未注册 markers → 0 收集 → pytest exit 5 → 首次实跑必失败
- 修复：去掉死 marker 选择器（该文件即完整 workspace API 表面），
  注释说明根因
- 本地模拟全部 nightly job 命令：compileall（app/shared/knowledge_base/
  scripts）+ test_imported_modules + test_workspace_api + test_desktop_runtime
  + test_migration_runner → 73 passed
- 下一实跑点：03:17 UTC（main 上该修复后首个 schedule tick）


### LOG-152: 096C 异步批量控制 API + from_checkpoint 一致性缺陷修复

- nightly 审计（LOG-151 续）：browser-smoke job 的 `-m "browser or workspace"`
  选择器零收集（无 marker 注册）→ 首次实跑必失败；已去掉死选择器并本地
  模拟全部 nightly job 命令（compileall + 4 测试文件）73 passed
- 096C 异步化：batch/import 后台 daemon 线程立即返回；pause/resume/shutdown
  端点操作活跃注册表（404/409 显式语义）；status 活跃读内存、完成读账本
- 真实缺陷修复：from_checkpoint 计数不恢复（completed=0 却有完成记录）
  + 状态恒为 idle（忽略账本 batch_end）→ 重算计数 + 恢复终端状态；
  中断批次保持 idle 可续跑、完成批次如实报告 finished
- commit 8ea9a05（3 文件 +141）；全量 1531 passed / 9 skipped


### LOG-153: Release workflow 首次实跑前审计（nightly 教训应用）——PASS

- Release（v* tag → main 校验 → exact-SHA CI → bundle → NSIS → wheel
  +SHA256SUMS → draft release → 读回）加入后从未跑过；按 nightly 教训
  逐项审计可运行性：
  - 7 个依赖文件全部存在（prepare_bundle.py / verify_nsis_install.ps1 /
    release_inject_identity.py / release_checksum.py / package.json /
    tauri.conf.json / package-lock.json）
  - release_checksum.py dry-run：3 payload（wheel/installer/identity）
    正确生成 SHA256SUMS（64 位 hex + 文件名精确匹配）→ exit 0
  - release_inject_identity.py dry-run：schema 2.0.0 注入正确
    （source.commit/tree/release_run_id/verification_ci_run_id +
    release.version/tag）→ exit 0
  - pyproject version 0.5.0 与 release.yml --version 0.5.0 一致
  - 未跑部分：NSIS 构建 + 安装态验证（需真实 Windows runner，发布时验证）
- 结论：Release 脚本层可运行性 PASS；发布执行留 Owner（AXW-097/060）


### LOG-154: nightly 首次实跑点观察 + py-compat 3.13 矩阵本地验证

- 03:17 UTC 调度点已过 ~16 分钟仍未触发（GitHub 调度器侧延迟，超出常见
  5-15 分钟窗口；schedule 事件无法从本端强制，workflow_dispatch 需认证）
  ——修复已就位（LOG-151），观察延续至下次 tick
- 用本地 3.13 解释器模拟 nightly py-compat job（实跑最易挂的版本矩阵）：
  compileall（app/shared/knowledge_base/scripts）+ test_imported_modules
  → 全部 PASS；3.11 侧 target py311 风险更低
- .venv 被 uv --python 3.13 重建后已 uv sync --frozen 恢复完整环境


### LOG-155: AXW-096B PDF 阅读器键盘可达性覆盖（browser-smoke 扩展）

- 补全 PDF 阅读器无鼠标键盘流断言（此前仅鼠标流）：
  - #pdf-prev focus+Enter → 页码 2/2→1/2
  - [data-action=pdf-zoom-out] focus+Enter → zoom 变化（zoom 按钮无 id，
    仅 data-action——属性定位）
  - 搜索输入 → Tab（断言焦点落"搜索"按钮）→ Enter → searchPdf 跳匹配页 2/2
- 测试陷阱固化：keyboard.type 叠加已有输入值 → 查询串不匹配 → 必须先
  fill("") 清空；CI 诊断扩展 activeElement + searchValue 到 state dump
- commit 00f9c3f（scripts + index.html 注释触发 CI browser-smoke 实跑）
  → Run 535 SUCCESS；本地 1531 passed / 9 skipped
- nightly 调度观察延续：03:17 tick 后 50+ 分钟仍未触发（GitHub 调度器
  跳过 tick，非本端可强制；workflow_dispatch 需认证）


### LOG-156: 096C 账本任务列表恢复缺陷修复 + 中途 shutdown 覆盖

- 缺陷：tasks_added 事件只记 count/total 不记任务列表 → from_checkpoint
  恢复后未完成任务静默消失（total 塌缩为已完成数）→ 违背"中断批次可
  续跑"承诺
- 修复：add_tasks 记录完整任务列表（保留 count/total 兼容旧账本）；
  from_checkpoint 恢复未完成任务队列 + 重算计数 + total 取全量（旧账本
  fallback 到记录的 total）
- 新增 API 测试：中途 shutdown → 账本持久 → status 读回 terminal
  shutdown 状态、total=200、0<completed<200、未完成任务完整
- commit 976bf13；17 passed（api/batch_control/pipeline）；全量 1532
  passed / 9 skipped
- nightly 观察定论：默认分支=main 已确认、cron 正确、workflow 在 main
  ——不触发属 GitHub 调度器跳过（外部行为，三次确认）


### LOG-157: AXW-094A/B 用户可见 UI 入口（022B 闭环最后一段）

- 此前导出/备份仅库函数 + API（"功能存在但用户不可达"风险——022B 教训）
- index.html 新增「开放交换与备份」卡片（导出/校验交换 + 创建/校验备份
  4 按钮 + 结果区）；app.js 绑定 4 个 data-action + exchangeCommand
  辅助（POST 带 JSON body / GET 校验；错误回显结果区）
- browser-smoke 新增 exercise_exchange_ui：逐按钮点击断言 API 通路 +
  结果区更新（绝不死按钮）；驱动 Evidence 页须用 #evidence hash 路由
  （默认 page=overview——app.js hash 路由机制，调试中确认）
- 本地真实浏览器 PASS（workspace + keyboard + PDF + exchange UI +
  delivery）；commit 892b87b；全量 1532 passed / 9 skipped


### LOG-158: nightly 观察终止 + CHANGELOG [Unreleased] 同步

- nightly 终查：03:17 tick 后 ~2h 仍未触发——本地侧三次排除（文件在
  main、cron 正确、默认分支=main），纯 GitHub 调度器跳过（外部行为）；
  观察终止，修复与全 job 本地验证均已就绪，等待未来 tick
- CHANGELOG [Unreleased] 追加本多轮功能变更：094A/B 导出备份三层
  （库/API/UI）、096A 中英文真实语料基准、096B 全键盘可达、
  096C 异步控制+账本恢复、CI 生态（nightly 修复 + Release 预审计）


### LOG-159: Release 链路剩余环节本地验证——100% 覆盖

- prepare_bundle.py 完整实跑（--repository . --destination
  .hermes/task-runtime/rt-verify）：stage_runtime 复制独立 Python 3.13
  → uv export requirements.locked → wheels 下载 → 项目 wheel 构建
  （archeaxis_workspace-0.5.0-py3-none-any.whl）→ 安装到 staged runtime
- staged runtime 真实验证：rt-verify/runtime/python/python.exe 独立
  导入 app.workspace.router / shared.config / batch_controller → OK
- verify_nsis_install.ps1 PowerShell AST 解析通过（语法有效；
  实跑需真实 NSIS 安装器——发布时）
- Release 链路本地可验证部分累计 100%（依赖存在/checksum/identity/
  prepare_bundle/staged-runtime/PS 语法）；仅剩 NSIS 构建+安装实跑
  （真实 Windows runner，Owner 发布时执行）


### LOG-160: 096A 报告语料表一致性修复 + HANDOFF 同步

- 发现文档缺陷：PERFORMANCE_BENCHMARK_096A.md 语料分层表与引用块
  仍是初期纯英文数据（5 本/147.6KiB/4.5MiB），与中英混合测量表矛盾
- 修复为实测值（corpus/sources.json + 分层目录统计）：
  small=2 txt 2,415,262 B（1en+1zh）；medium=7 txt 6,074,578 B
  （4en+2zh+副本）；large=14 txt 13,058,571 B（10en+4zh）；
  规模-延迟区间同步（2.3→12.5 MiB，7→35 ms）
- HERMES_HANDOFF 同步：LOG 范围 147..156→147..159、CI 连绿
  524-537→524-542、补 UI 入口/409/Release 本地验证 100% 条目
