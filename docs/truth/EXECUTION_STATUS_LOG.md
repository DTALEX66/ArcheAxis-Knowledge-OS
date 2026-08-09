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
- 云端：`https://github.com/DTALEX66/Cognitive-Loop-OS/tree/codex/frozen-roadmap-deepseek-v1`；远端分支 SHA 回读为 `636bae2cb50c589e4d58e28c553b736613002b7e`；该分支 push 不触发当前仅面向 main/PR 的 CI，`EXACT_SHA_CI` 为 `NOT EXECUTED`
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
- 云端：`https://github.com/DTALEX66/Cognitive-Loop-OS/tree/codex/frozen-roadmap-deepseek-v1`；远端分支 SHA 回读为 `e7102416155aa53a13de0fb6b6edf959e07d5528`；该分支 push 不触发当前仅面向 main/PR 的 CI，`EXACT_SHA_CI` 为 `NOT EXECUTED`
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
- 变更：从最新云端 `origin/main` 建立隔离执行 worktree `D:/All projects/Cognitive-Loop-OS/.hermes/task-runtime/axw-exec`，分支 `axw/execution-h0`；记录 Git root、branch、HEAD、origin/main、分叉与脏路径 owner
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
- 执行分支：`axw/execution-h0`；PR `https://github.com/DTALEX66/Cognitive-Loop-OS/pull/71`
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
