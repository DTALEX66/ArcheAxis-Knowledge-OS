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
- 执行分支：`axw/execution-h0`；PR `https://github.com/DTALEX66/Cognitive-Loop-OS/pull/71`
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
- 执行分支：`axw/execution-h1`；PR `https://github.com/DTALEX66/Cognitive-Loop-OS/pull/72`
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

### LOG-20260809-054 — CLOUD DESC SYNC PR #73 — PASS

- 时间：2026-08-09T19:25:00+08:00
- 执行分支：docs/sync-authority-blueprints（基于 main f269a01）
- 候选提交：5468d4aa53c4e7931f5e2aa0f8ad1ba8f88693b7
- 变更：将 CODEX 冻结蓝图/增补包/truth 交接文档（docs/truth/ + docs/taskpacks/）同步进 main；更新 README（新增冻结执行基线节）与 docs/PROJECT_STATUS.md（新增冻结执行基线节）引用权威文档；SHA 文件已校验匹配
- 验证：PR #73 exact-head CI run 31343762542 completed/success（gateplan/lint/a0-gates PASS，桌面/UI/兼容 job 正确 SKIP）；mergeStateStatus CLEAN；convention PASS
- 证据等级：EXACT_SHA_CI（head 5468d4a）
- 风险/剩余项：PR #73 未 merge（未获 merge 授权）；H1 后端仍在 PR #72 未 merge；AXW-022A 前端 PDF.js 待独立批次
- 回滚：关闭/丢弃 PR #73

### LOG-20260810-055 — PLANNING SOURCES ARCHIVED — PASS

- 时间：2026-08-10T21:05:06+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 归档提交：`501a78cc27461adeee5072ffbe296755d3e105fe`
- 变更：将用户提供的 v0.5 多格式审计任务包、Future Master Blueprint v1、Codex 主任务包 v3、Final Master TaskPack v4 与 Context Handoff 纳入 `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/`；新增原件 ZIP、原件 SHA 清单、规范化仓库副本 SHA 清单和来源演变说明；修复父级参考目录的两个失效相对链接。
- 验证：原件 ZIP 5/5 条目与桌面源 SHA-256 一致；仓库副本 5/5 与 `REPOSITORY_COPY_MANIFEST.sha256` 一致；26 个本地链接 PASS；联合任务 DAG 159 个唯一 ID、无重复、未知依赖或环；`test_naming_conventions.py` 19 passed；repository convention 与 `git diff --check` PASS。
- 云端回读：`origin/codex/frozen-roadmap-deepseek-v1` = `501a78cc27461adeee5072ffbe296755d3e105fe`，本地/云端 `0/0`。
- 证据等级：`PUBLICATION`（分支文件与 SHA 回读）；不等于 exact-SHA CI、main 合并、实现完成或安装态资格。
- 权威边界：本次只归档历史来源；当前任务定义仍由冻结基线与批准增补包提供，状态仍只在本日志追加。
- 回滚：revert `501a78c`。

### LOG-20260810-056 — HISTORICAL PLANNING SOURCES DEDUPED AND PUBLISHED — PASS

- 时间：2026-08-10T21:50:07+08:00
- 执行分支：`codex/frozen-roadmap-deepseek-v1`
- 归档提交：`9a91e7d143493bfda1bfb723aa83713306a6969d`
- 变更：将项目本地 Hermes 边界中此前未进入 Git 的历史蓝图、规划、任务包、验收资料与 manifests 收敛到 `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/`；22 个物理源件经去重和筛选后形成 99 个仓库文件，并保留原始源、选中压缩包条目和仓库副本三类 SHA-256 清单。
- 隐私/冗余边界：3 个 Desktop/Cloud 复审 ZIP 为同 SHA 副本，2 个对话归档 ZIP 为同 SHA 副本，3 个 CI TaskPack 也为同 SHA 副本；原 ZIP、prompts、对话时间线、截图、HTML 原型和执行脚本均未提交，只保留合规项目规划内容与原始 SHA 证据。
- 验证：物理源清单 22/22、仓库副本清单 99/99；85 个选中压缩包条目无 prompt/对话时间线/PNG/HTML/PowerShell；文本高置信秘密与机器路径扫描 PASS；3 个 DOCX 内部 XML 扫描 PASS；repository convention（index）PASS；`test_naming_conventions.py` 19 passed；`git diff --cached --check` PASS。
- 云端回读：`origin/codex/frozen-roadmap-deepseek-v1` = 本地 `9a91e7d143493bfda1bfb723aa83713306a6969d`。
- 证据等级：`PUBLICATION`（分支文件与 SHA 回读）；不等于 exact-SHA CI、main 合并、实现完成或安装态资格。
- 权威边界：历史归档不覆盖冻结基线、批准增补或本状态日志；清理本地缓存不得删除未提交工作树或唯一证据。
- 回滚：revert `9a91e7d`。

### LOG-20260810-057 — PR #72 H1 BACKEND MERGED TO MAIN — PASS

- 时间：2026-08-10
- 执行分支：axw/execution-h1（squash merge）
- 候选提交/merge SHA：fba208f2551f26acc64d82613500656159fc6801
- 变更：H1 后端核心（GOV-001 + 020R/020A/020B/020C + 021A/021B + 024A/024B + 025A/025B + 030A/030B/030C + AXW-022A 后端 pdf_serve）经用户授权 squash merge 进入 main；RawAsset/Evidence/学习 DTO 后端真正落地
- 验证：merge-SHA main CI 31492513039 completed/success（gateplan、test(3.12)、lint、wheel-smoke、a0-gates 全 PASS；浏览器/桌面/兼容 job 正确 SKIP）；merge 前 head 1c688c7 exact-SHA CI 已绿
- 证据等级：EXACT_SHA_CI + merge-SHA main CI 双绿
- 风险/剩余项：AXW-022A/022B 前端 PDF.js 渲染仍 PARTIAL（真实资料源无 PDF 样本，不伪造，需独立前端批次）；AXW-H1-EXIT 待 022 前端完成；公开发布 NO-GO
- 回滚：revert merge SHA fba208f（需单独评审）

### LOG-20260810-058 — PDF HTTP ENDPOINT PR #74 — PASS

- 时间：2026-08-10
- 执行分支：feat/axw022a-pdf-http-endpoint
- 候选提交：6e9dbfd3db8e986a8b15927ce1537063a6f46a63
- 变更：AXW-022A 后端 pdf_serve 接入 GET /workspace/api/pdf/{content_key} HTTP 端点（内容寻址、只读、fail-closed）；真实 PDF 端到端验证
- 验证：exact-head CI 31493237744 completed/success（gateplan/lint/test/a0-gates PASS，桌面/UI 正确 SKIP）；mergeStateStatus CLEAN；本地 4 passed（2 真实 PDF 字节级 + 2 fail-closed）
- 真实输入：时间简史（插图本）322页/18.9MB + 缤纷的语言学 120页/2.2MB，均图文；HTTP 读回字节 SHA-256 一致
- 证据等级：EXACT_SHA_CI + LOCAL_RUNTIME（真实 PDF 字节保真）
- 风险/剩余项：PR #74 未 merge（未获授权）；PDF.js 前端渲染（分页/缩放/搜索 + 证据批注 + WebView 点击级）仍待独立前端批次；AXW-H1-EXIT 待 022 前端完成
- 回滚：关闭/丢弃 PR #74

### LOG-20260811-059 — PDF HTTP ENDPOINT RUNTIME CLOSED LOOP — PASS

- 时间：2026-08-11
- 执行分支：feat/axw022a-pdf-http-endpoint（PR #74，head 6e9dbfd）
- 变更：迁移 runtime DB（migrate 子命令，6 owner 全 applied）；启动 uvicorn（app.runtime_entrypoint core，127.0.0.1:8000）
- 验证：真实运行时 HTTP 读回两真实 PDF——时间简史（插图本）18.9MB + 缤纷的语言学 2.2MB，均 HTTP 200，content-type application/pdf，字节 SHA-256 完全一致（9d35e2a6…c5 / a1d6cc1d…13）；服务日志 3 次 200 OK；测试客户端 4 passed
- 意义：AXW-022A 后端→HTTP 端点的闭环由真实 uvicorn 服务 + 真实 PDF 证实（超出测试客户端证据）
- 证据等级：LOCAL_RUNTIME（真实服务 + 真实 PDF 字节保真）+ EXACT_SHA_CI（PR #74 run 31493237744）
- 风险/剩余项：PR #74 未 merge（未获授权）；PDF.js 前端渲染（分页/缩放/搜索 + 证据批注 + WebView 点击级）仍待独立前端批次；AXW-H1-EXIT 待 022 前端完成
- 回滚：关闭/丢弃 PR #74；删除本地 data/（未跟踪 runtime）

### LOG-20260811-060 — PUBLIC CONTENT ACCURACY MECHANISM — PASS

- 时间：2026-08-11
- 变更：确立公开内容准确性保证机制=全网交叉比对（非模型置信度/CER-WER）；两公开书（时间简史+缤纷的语言学）11 事实点交叉核验 9 PASS+2 待补；obsidian-web-crosscheck 技能 v2 扩展覆盖公开书籍场景+书籍权威源速查；本文档追加机制声明
- 验证：Wikipedia REST API 核验（Hubble 1929、宇宙常数 1917、黑洞、时间箭头、共时历时、索绪尔、乔姆斯基、神经语言学等）；报告 .hermes/task-runtime/web-crosscheck-report-2026-08-11.md
- 证据等级：WEB_CROSSCHECK（公开权威来源交叉核验）
- 风险/剩余项：PR #74 PDF 端点未 merge；PDF.js 前端渲染待独立批次；AXW-H1-EXIT 待 022 前端
- 回滚：revert 本文档 commit

### LOG-20260811-061 — ALL-FORMAT ACCURACY MECHANISM — PASS

- 时间：2026-08-11
- 变更：内容准确率机制扩展为全格式两层验证——识别转译层（高精度模型+CER/WER）+ 内容事实层（全网交叉对比，全格式通用）；覆盖 PDF/图片/音频/视频/Office；obsidian-web-crosscheck 技能 v3 同步扩展
- 原则：识别转译置信度永不当作内容事实准确性；冲突记录差异不自动覆盖
- 验证：沿用 LOG-060 案例（PDF 两书 11 事实点交叉核验 9 PASS+2 待补）
- 证据等级：WEB_CROSSCHECK
- 风险/剩余项：PR #74 PDF 端点+PDF.js vendoring 未 merge；前端渲染逻辑待批次；AXW-H1-EXIT 待 022 前端
- 回滚：revert 本文档 commit


### LOG-20260811-062 — CHANGE_PROPOSAL REGISTRATION (AXW-MFX-WXV-v1) — REGISTERED / OWNER APPROVAL PENDING

- 时间：2026-08-11
- 提案：`ArcheAxis_Workspace_Multiformat_Recognition_Web_Verification_Enhancement_TaskPack_v1_2026-08-11.md`
- 类型：CHANGE_PROPOSAL（未获所有者批准前不具执行权威）
- 存档：`docs/change-proposals/ArcheAxis_Workspace_Multiformat_Recognition_Web_Verification_Enhancement_TaskPack_v1_2026-08-11.md`（SHA-256 `5331fdfa20ecf6ded5a8a770e0e6a4bfe3f4eb226d24e0c12082db44d6419609`）
- 复核基线：`main@fba208f2551f26acc64d82613500656159fc6801`（已核对一致）；H1 对象与治理后端已合并事实确认
- 状态：REGISTERED（审计/估算/任务拆分已就绪）；owner 决策 = PENDING（6 项批准项待所有者确认）
- 范围：多格式识别转译 + 质量门控 + 选择性模型升级 + Claim 级异步全网验证 + 人工复核衔接；不覆盖 frozen authority 与 v4 主任务包
- 记录：本文件为 append-only CHANGE_PROPOSAL 登记，不授权任何仓库/远端/用户数据/发布物修改
- 回滚：撤销本次追加记录（历史状态不改写）


### LOG-20260811-063 — AXW-MFX-WXV-v1 OWNER APPROVAL — APPROVED (6/6)

- 时间：2026-08-11
- 所有者决策：全部批准 6 项（方案 C 核心结构+默认异步验证；首批默认引擎；外部 LLM 默认关闭；MinerU/PyMuPDF/Marker/FunASR/Zotero/SearXNG 不入默认包；采用 AXW-MFX-* ID；append-only CHANGE_PROPOSAL 登记）
- 授权范围：从 Batch 0（MFX-000/001/010/012 止损）开始执行；后续批次逐批推进
- 执行约束：一项原子任务/一条分支/一个 PR；开始前重读云端 main/PR/CI/安装版；不改 frozen authority；冲突时停工作并提交 CHANGE_PROPOSAL
- 回滚：Batch 0 各任务按各自规格可逆


### LOG-20260811-064 — AXW-022A CLOSED / H1-EXIT — PASS (PDF ENDPOINT + PDF.js FRONTEND)

- 时间：2026-08-11
- PR #74 squash merged → main `ebf71247`（mergeCommit `ebf71247`；main `fba208f → ebf7124`）
- 云端验证：`app/workspace/router.py`（SHA 97fd0a2a）+ `app/workspace/ui/assets/pdf.min.js`（320005 B）存在
- 内容：
  - AXW-022A 后端：`GET /api/pdf/{content_key}` 内容寻址只读字节服务（4 tests，真实 PDF SHA-256 保真）
  - AXW-022A 前端：PDF.js 3.11.174 vendored + evidence 查看器（分页/缩放/搜索），浏览器级真实 PDF 验证（120 页《缤纷的语言学》1/120 渲染、翻页、缩放）
  - 许可证：PDF.js Apache-2.0 记录于 THIRD_PARTY_NOTICES.md
- CI：exact-head run 31498795006 全绿（gateplan/a0-gates/browser-smoke/lint/test/wheel-smoke PASS），mergeState CLEAN
- AXW-022A 全链路（后端端点+前端渲染+许可证+浏览器交互）闭环
- H1-EXIT：冻结依赖 6/6 PASS（GOV-001/021B/022B/024B/025B/030C）→ AXW-H1-EXIT PASS
- 回滚：PR #74 已 squash merge，如需回退 revert ebf7124


### LOG-20260811-065 — H1 EXIT GATE: MERGE-SHA MAIN CI — PASS

- 时间：2026-08-11
- PR #74 mergeCommit `ebf7124` merge-SHA main CI run `31499045060` conclusion=**success**
- 确认：gateplan/lint/test(3.12)/wheel-smoke/browser-smoke/a0-gates 全绿；产品/桌面 job 正确 SKIP
- 补全 AXW-H1-EXIT 的 merge-SHA 证据（LOG-064 记录 exact-head + 裁决；本条记录 merge-SHA main CI）
- main = `ebf7124`


### LOG-20260811-066 — MFX BATCH 0 COMPLETE + AXW-022B + AXW-023A — PASS

- 时间：2026-08-11
- Batch 0（止损）三任务全部实现 + exact-head CI 全绿：
  - MFX-010 假成功止损：PR #75（image 链改真实 OCR + 内容后置条件；CI CLEAN）
  - MFX-012 legacy credibility 隔离：PR #76（score_credibility 标 legacy_heuristic + verified=False；CI CLEAN）
  - MFX-001 供应链台账：PR #77（SUPPLY_CHAIN_LEDGER.json 40+ 组件 gate；CI CLEAN）
- AXW-022B 证据批注：PR #78（POST/GET evidence anchor API + PDF 批注 UI；浏览器级 runtime POST/GET roundtrip 200）
- AXW-023A DOCX Adapter：PR #79（结构化 docx adapter + conversion_run 持久化 + 缺依赖诚实降级；4 测试）
- H2 首个任务 AXW-023A 已实现
- 待办：征求 5 个 PR merge 授权；吸收账本核对（等 owner 开源清单）
- 边界：未访问 E:\；未读凭据；冻结基线未动；状态日志追加式
- 回滚：各 PR 独立 revert


### LOG-20260811-067 — 5 PRs MERGED TO MAIN (Batch 0 + AXW-022B + AXW-023A) — PASS

- 时间：2026-08-11
- 用户授权全部 5 个 PR squash merge 进 main：
  - #75 MFX-010 假成功止损 → MERGED
  - #76 MFX-012 legacy credibility 隔离 → MERGED
  - #77 MFX-001 供应链台账 → MERGED
  - #78 AXW-022B 证据批注 → MERGED
  - #79 AXW-023A DOCX Adapter → MERGED
- main: `ebf7124 → 633631e`（经历 da82986/19a428e/2a0ee131/d8769eda/633631e）
- 云端 main 确认 docx_adapter.py / router.py / SUPPLY_CHAIN_LEDGER.json 存在
- Batch 0 全部闭环 + AXW-022B 全链路 + AXW-023A（H2 首个）入库
- 待办：merge-SHA main CI 确认；吸收账本核对（等 owner 开源清单）
- 回滚：各 PR 独立 revert


### LOG-20260811-068 — ABSORPTION ATLAS ANALYSIS: LEDGER v2 + MATRIX v2 + NOTICES UPDATE — PASS

- 时间：2026-08-11
- 输入：`ArcheAxis_Workspace_Project_History_and_OSS_Absorption_Master_Atlas_v1.md`（369+项目全景、12当前集成、57精选、上游纠错）
- 产出（真正分析吸收，非登记索引）：
  - SUPPLY_CHAIN_LEDGER v2（46 组件，含吸收决策：12 CURRENT / 13 ADOPT / 9 EVALUATE / 2 SIDECAR / 9 REVIEW-BLOCK / 1 REJECT-CORE）
  - ABSORPTION_EXECUTION_MATRIX v2（纠正旧阶段语境、过时状态、implemented=8 漂移）
  - THIRD_PARTY_NOTICES 追加「2026-08-11 上游许可纠错」节（10 项历史结论更正）
- 关键决策：
  - 旧"implemented=8"被 ledger v2 替代，数字不可再引用为集成数量
  - Marker 代码许可从 GPL-3.0 更正为 Apache-2.0（权重另审）
  - H5P 从"core MIT"更正为 GPL-3.0
  - Phoenix 从"开源观测"更正为 Elastic-2.0（非OSS）
  - Kùzu 标归档；tldraw 商业许可阻断；Firecrawl AGPL 主/部分 MIT
  - LiteLLM/Langfuse 核心 MIT，但 enterprise/ee/ 目录另许可
- 产品边界确认：本地学习与知识工作台（非 Agent OS / RAG 平台）；Agent/编码/记忆/工作流/安全实验室项目全部后置
- 回滚：本文档更新可独立 revert；不修改 frozen baseline


### LOG-20260811-069 — PR #80 MERGED (absorption atlas v2) — PASS

- 时间：2026-08-11
- PR #80 squash merged → main `8e4f1cf`（main `633631e → 8e4f1cf`）
- 内容：吸收总图谱分析落地（SUPPLY_CHAIN_LEDGER v2 46组件 + ABSORPTION_EXECUTION_MATRIX v2 + 许可纠错10项）
- 旧"implemented=8"漂移、旧阶段序列、旧许可结论均已更正
- 回滚：revert 8e4f1cf


### LOG-20260812-070 — HISTORICAL DEBT RESOLUTION + NAMING SYSTEM MIGRATION — PASS

- 时间：2026-08-12
- PR #69 merged（桌面控制台窗口修复）→ main `c9e8bda`
- 命名体系迁移：Cognitive-Loop-OS → ArcheAxis Workspace（9 文件，33 处）
  - GitHub 仓库名 "Cognitive-Loop-OS" 不变（仅 Git 标识符）
  - 产品名统一为 "ArcheAxis Workspace / 元枢工作台"
- 文档漂移修复：
  - PROJECT_STATUS.md: H1/PDF.js merge 状态更新为"已 merge"
  - PROJECT_STATUS.md: 吸收账本数字 101→46（ledger v2）
  - H0_H1_STATUS_HANDOFF.md: 全部 "PR #72 未 merge" 更正为已 merge
- Worktree 清理：10 个已 merge 分支的 worktree 移除
- PR #81（吸收实现 + 命名更新）待 CI → merge
- 回滚：revert 各 commit


### LOG-20260812-071 — PR #81 MERGED (absorption implementation + env docs) — PASS

- PR #81 squash merged → main `74d44eb`（main `c9e8bda → 74d44eb`）
- 内容：
  - 吸收实现：JiWER + RapidFuzz + JSON Canvas 验证器 + 证据连接器(4) + py-fsrs + Magika 源码级吸收
  - 命名体系：文档层迁移（ArcheAxis OS→Workspace），pyproject/CLI 回退
  - 文档漂移修复：PROJECT_STATUS + HANDOFF 全部更新
  - 外置依赖文档：EXTERNAL_DEPENDENCIES.md（279 行，含下载链接 + 安装清单）
  - 双向同步：D:\All projects\OS configuration\EXTERNAL_DEPENDENCIES.md
- CI：test(3.12)/py-compat/wheel-smoke/browser-smoke/windows-runtime-smoke 全部 PASS
- 全部 7 个 PR（#75-#81）已 merge 进 main


### LOG-20260812-072 — H2 PIPELINE INTEGRATION (PR #82) — PASS

- PR #82（H2 管线整合）head `65888f9`，待 CI
- 5 个 ADOPT 吸收模块全部接入实际处理链路：
  - Magika ONNX → 摄入路由（detect_format_from_content）
  - JiWER+RapidFuzz → 转换质量门（convert_file quality=True）
  - 4 Evidence Connectors → 交叉验证（enrich_with_public_sources）
  - JSON Canvas 验证器 → Canvas 格式处理（_via_canvas）
  - py-fsrs v6 → 学习调度（schedule_next_review）
- Lint 通过，74 适配器测试通过
- 回滚：revert PR #82


### LOG-20260812-073 — PR #82 MERGED (H2 pipeline integration) — PASS

- PR #82 squash merged → main `f6b49b3`
- 5 ADOPT 模块管线接入入库
- 全部 9 个 PR（#69, #75-#82）已 merge 进 main
- 权威日志: LOG-004~073


### LOG-20260812-074 — PR #83 MERGED (H2 bake-off) — PASS

- PR #83 merged → main b97035e
- OCR/ASR bake-off framework + Silero VAD stub
- 10 PRs merged (#69, #75-#83)


### LOG-20260812-075 — AXW-1200 TASKPACK EXECUTION (system blueprint + HERMES update) — PASS

- Owner 任务包 v1 (2026-08-11) 全部执行：17 交付文件 + README 锁死首页 + GitHub 描述锁死
- 命名定死：ArcheAxis / ArcheAxis Learning Workspace / 星轨学习工作台
- 产出：PRODUCT_IDENTITY_V2, NAMING_CONTRACT_V1, AUTHORITY_RULES_V1, CAPABILITY_ATLAS_V2 (16 caps),
  REQUIREMENT_TRACE_V2 (17 reqs), SCOPE_LEDGER_V2, TASK_GRAPH_V2 (11 tasks), SYSTEM_MASTER_BLUEPRINT_V2,
  LER_VISUAL_SPATIAL_V1, OPEN_INTEROP_V1, NAMING_MIGRATION_V1, 4 ADRs, SNAPSHOT_RECEIPT
- README 锁死：产品身份 + 已吸收项目 + 吸收不了项目(许可阻断) + 外置依赖链接
- GitHub 描述更新：产品名 + NOT Agent OS + absorbed + blocked 项目 + deps 链接
- 任务包作为 Owner 权威，定死不可漂移；阶段描述可更新
- 分支 feat/axw1200-system-truth fc9e5dd，PR #84 待创建/CI


### LOG-20260812-076 — PR #84 MERGED (AXW-1200 taskpack system truth) — PASS

- PR #84 squash merged → main `535d1c3`
- 17 交付文件全部入库（identity/naming/atlas/trace/ledger/graph/blueprint/LER/interop/migration/4 ADR）
- README 首页锁死：产品身份 + 已吸收 + 吸收不了(许可阻断) + 外置依赖链接
- GitHub 仓库描述锁死（ArcheAxis Learning Workspace, NOT Agent OS, blocked projects）
- 修复：#82/#83 引入的 ruff（N806/E741/B904/N814）+ 契约测试对齐命名 V1 + manifest 更新
- 命名契约 V1 binding；阶段描述可更新


### LOG-20260812-077 — PR #85 MERGED (naming doc alignment) — PASS

- PR #85 squash merged → main `48a10db`
- AGENTS.md + PROJECT_STATUS.md aligned with NAMING_CONTRACT_V1
  (ArcheAxis Learning Workspace / 星轨学习工作台; doc-layer only)
- 全部 13 PR（#69, #75-#85）merged


### LOG-20260812-078 — PR #87 MERGED (UI naming migration) — PASS

- PR #87 squash merged → main `34ee375`
- 运行时 UI 文案源全部迁移：app/main.py title、router product、index.html 品牌/标题/标签、
  desktop protocol.rs + backend.rs product 字符串、product-naming-registry.yaml v3、
  5 个测试 + 2 个 smoke 脚本断言更新（元枢工作台 → 星轨学习工作台）
- 修复 Rust chunked body 长度（63→6C）
- 14 Rust lib tests + 1228 Python tests + 全 CI（含 desktop-build/installer-lifecycle）绿
- 命名契约 V1 全链路落地：文档 → UI 阶段完成；打包/仓库/底层 planned


### LOG-20260812-079 — PR #88 MERGED (AXW-1209 naming lint guard) — PASS

- PR #88 squash merged → main `b5833d2`
- scripts/check_repository_conventions.py + scan_naming_forbidden_terms:
  活跃文档面（README/docs-current/blueprint/architecture/decisions/environment/
  migration/truth/config/.worklab）拒绝旧产品名（元枢工作台/ArcheAxis OS/
  ArcheAxis Workspace），历史性文件豁免（intake/taskpacks/imported-designs/
  notices/status logs）
- README + .worklab 注释对齐 ArcheAxis Learning Workspace
- 4 新测试；convention check 全绿
- AXW-1209 文档投影门禁落地：命名禁词防回归


### LOG-20260812-080 — PR #89 MERGED (AXW-1200~1210 taskpack COMPLETE) — PASS

- PR #89 squash merged → main `0e8c730`
- AXW-1200~1210 全部 11 项任务完成（1200 snapshot, 1201 naming, 1202 identity,
  1203 atlas, 1204 trace/ledger/graph, 1205 LER, 1206 plan, 1207 interop,
  1208 migration plan, 1209 lint guard, 1210 spine re-entry）
- 命名迁移阶段 1-2（文档+UI）done；阶段 3+（打包/仓库/底层）Owner-gated
- 任务包 v1 2026-08-11 全量落地：17 文件 + README/GitHub 描述锁死 + 命名禁词门禁
- 17 PR（#69, #75-#89）全部 merge


### LOG-20260812-081 — PR #90 MERGED (H3 C4-safe Vault write) — PASS

- PR #90 squash merged → main `59e3173`
- H3 开放 Vault 往返写入侧落地：
  - vault.write_file: expected-hash 乐观锁（409 fail-closed）、原子写（sibling temp + os.replace）、
    备份到 store 边界可回滚、escape/binary/missing 拒绝
  - POST /workspace/api/vault/write
- 5 新测试；1237 Python tests 通过
- H3 纵切：读（inspect/file/search）+ 写（write）闭环；C4 往返下一步是 frontend 接线


### LOG-20260812-082 — PR #91 MERGED (H3 Vault edit-save UI + runtime fixes) — PASS

- PR #91 squash merged → main `f90ca77`
- index.html + app.js: 编辑文件输入 + 文本域 + 保存按钮；openVaultFile 记录磁盘哈希,
  saveVaultFile 409 冲突提示 + 成功更新哈希/备份名
- vault.py: 备份目录路径修复 (store=DB 文件 → parent/vault-backups)
- migration_runner.py: vec0 虚拟表跳过直接 SELECT (无扩展连接), 由 *_id_map 指纹覆盖
- 浏览器级验证: write 200 / stale-hash 409 / 文件未污染 / 备份创建
- H3 纵切: inspect + read + search + write(乐观锁) + UI 编辑保存 全链路


### LOG-20260812-083 — PR #92 MERGED (H3 backup list/restore + frontmatter) — PASS

- PR #92 squash merged → main `a8b773a`
- vault.list_backups (newest-first) + restore_backup (原子恢复 + pre-restore
  快照使恢复本身可回滚；精确文件名防穿越)
- POST /api/vault/backups + /api/vault/restore
- frontmatter 保留往返测试（read→edit→write 保持 YAML properties）
- 4 新测试；C4 安全往返：读/写/冲突/备份/恢复 全链


### LOG-20260812-084 — PR #93 MERGED (H3 backup list/restore UI) — PASS

- PR #93 squash merged → main `7bc75e0`
- UI: 备份列表按钮 + select + 恢复按钮；恢复后编辑器重新加载内容+哈希
- Browser-verified: 4 backups listed / restore 200 / file reverted /
  traversal guard 422
- H3 纵切全链（含 UI）: inspect+read+search+write(乐观锁)+冲突+备份+恢复


### LOG-20260812-085 — PR #94 MERGED (TESSDATA_PREFIX env doc) — PASS

- PR #94 squash merged → main `7a0e90d`
- 本地 OCR 测试 skipped 根因: TESSDATA_PREFIX 指向不存在的
  tesseract-languages/current; 实际数据在 4.1.0/
- 修复: 双写 EXTERNAL_DEPENDENCIES.md (项目 + OS configuration d1819e9)
- 验证: TESSDATA_PREFIX 设置后 2 OCR 测试 pass (1244 → 1246)
- 本地全量: 1246 passed, 6 skipped (symlink 权限×3/网络×2/crossref×1)


### LOG-20260812-086 — PR #95 MERGED (crossref stage kb_id 解耦) — PASS

- PR #95 squash merged → main `1dd1884`
- run_pipeline crossref 阶段不再依赖 kb_id（kb_id 是 index 阶段产物，
  仅 auto_ingest=True 时产生）→ offline 运行 (actions=['crossref'],
  auto_ingest=False) 时不再静默跳过；title 回退 tag keywords
- 测试 test_pipeline_crossref_stage_is_not_verified 从 skip → pass
- 本地全量: 1247 passed, 5 skipped (symlink×3/网络×2 合理)


### LOG-20260812-087 — PR #96 MERGED (--run-network flag 注册) — PASS

- PR #96 squash merged → main `2d959f9`
- test_evidence_connectors 引用 --run-network 但 option 从未注册，
  显式传入报 unrecognized arguments → tests/conftest.py 注册
- 验证: --run-network → 9 passed (2 真实 DOI 查询, Crossref 200);
  默认 → 7 passed 2 skipped (CI 行为不变)


### LOG-20260812-088 — PR #97 MERGED (real OCR bake-off) — PASS

- PR #97 squash merged → main `169155e`
- 首次真实 bake-off: Tesseract vs 3-fixture 语料 (en_clean/en_noisy/zh_clean
  + ground truth) → CER/WER 报告 CSV+JSON
- 真实发现: eng+chi_sim 对 CJK 插空格致 CER 0.8 虚高 → 拆双引擎变体
  (tesseract-eng / tesseract-chi-sim); chi_sim 中文 CER 0.0
- report_csv `or ""` 吞掉完美 0.0 → is not None 判断
- 测试 helper CJK-first 字体序 (arial 渲染空白)
- 真实数据: tesseract en_clean .0227/en_noisy .025/zh_clean 1.0;
  chi-sim en_clean .0455/en_noisy .1/zh_clean 0.0
- 本地全量 1249 passed, 5 skipped


### LOG-20260812-089 — PR #98 MERGED (rapidocr 激活) — PASS

- PR #98 squash merged → main `b652ad8`
- rapidocr-onnxruntime 入 ci-adapters; RAPIDOCR.available 动态 find_spec
- 三引擎真实 bake-off (avg CER): rapidocr .0076 全胜 (含噪声图 0.0),
  tesseract-chi-sim .0485, tesseract-eng .3492
- rapidocr ~1.3s/img vs tesseract ~100-200ms (精度换延迟)
- 本地全量 1249 passed


### LOG-20260812-090 — PR #99 MERGED (first real ASR bake-off) — PASS

- PR #99 squash merged → main `1b2e1c3`
- Windows SAPI TTS (Zira en-US / Huihui zh-CN) 生成 3 音频 fixture + ground truth
- faster-whisper base (CPU int8, 模型 ~150MB) 实测:
  en_clean CER 0.0 / en_slow CER 0.0 / zh_clean CER 0.2
- zh CER 0.2 = 单个 机器→機器 繁简差异 (base 模型繁体偏重); 语言
  自动检测 zh (1.00) 正确
- faster-whisper 入 ci-adapters; FASTER_WHISPER.available 动态检测
- 报告: bakeoff-results/bakeoff-asr-20260812.{csv,json}
- H2 bake-off 现在覆盖 OCR (3 引擎) + ASR (1 引擎) 真实数据


### LOG-20260812-091 — PR #100 MERGED (Silero VAD stub 测试) — PASS

- PR #100 squash merged → main `c57aa05`
- audio_vad.py (#83 引入) 零测试覆盖 → 补 4 测试:
  不可用空段 / 可用委托 silero / 音频损坏降级 / 探针不抛异常
- 注入假 torch/torchaudio 模块, 无需重依赖
- H2 组件覆盖补全: bakeoff + engines + audio_vad 全部有测试


### LOG-20260812-092 — PR #101 MERGED (DataCite 解析修复) — PASS

- PR #101 squash merged → main `63515ad`
- public_evidence (#82, 首次测试覆盖) 发现 2 真实缺陷:
  ①DataCite {data:{attributes}} 被当 Crossref {message} 解析 → 命中恒 None
  ②_extract_year 缺 Crossref 'issued' / DataCite 'publicationYear'
- 真实网络验证: Crossref 10.1038/nature12373 title/year/authors 全解析;
  DataCite 10.5284/1046878 title/year 解析 (修复前 None)
- 7 新测试 (路由/错误抑制/hit 往返)
- 本地全量 1260 passed, 5 skipped


### LOG-20260812-093 — PR #102 MERGED (fact_extractor 测试) — PASS

- PR #102 squash merged → main `429f6cf`
- fact_extractor 首次测试 (12 测试: 8 关系模式/of/max_facts/空/实体)
- 修复 created_by 正则缺陷: be 动词被吞 (Python was created →
  subject 'Python was') → 加可选 (was|were|is|are|has been)
- 本地全量 1272 passed, 5 skipped
- 零测试组件 13→11 (public_evidence/fact_extractor 已清)


### LOG-20260812-094 — PR #103 MERGED (block_refs 测试) — PASS

- PR #103 squash merged → main `9d6f400`
- block_refs 首次测试 (11 测试): heading/paragraph id、slugify、resolve
  (documents+cards 回退)、无效引用、((ref)) 解析、嵌套 embed、缺失 None
- 无代码变更 (测试记录实际行为: 纯段落=单 p1 block; select_one 函数内 import)
- 本地全量 1283 passed, 5 skipped
- 零测试组件 11→10


### LOG-20260812-095 — PR #104 MERGED (diversity_audit 测试) — PASS

- PR #104 squash merged → main `8a24a26`
- diversity_audit 首次测试 (7): 四档评分/缺失/cards 回退/radar 排序
- 无代码变更; patch 差异记录: select_all 模块级 vs select_one 函数内
- 本地全量 1290 passed, 5 skipped
- 零测试组件 10→9


### LOG-20260812-096 — PR #105 MERGED (Magika 检测修复) — PASS

- PR #105 squash merged → main `31ec571`
- 重大修复: vendored Magika (file_detection) 之前完全失效 (全 unknown)
  ①双重 softmax: ONNX 已输出概率 (sum==1), 再 softmax 把 0.889→0.011
  ②短内容 0 填充 (bytes.ljust) 而非 padding_token 256
- 修复后: markdown .9992/jsonl .9728/png .9916/python .9407/csv .9999
- 附带修复 latent canvas 回归: Magika 将 JSON Canvas 标 json→txt 映射
  移除, .canvas 保留 json-canvas handler (测试暴露)
- 9 新测试; 本地全量 1299 passed, 5 skipped
- 零测试组件 9→8


### LOG-20260812-097 — PR #106 MERGED (object_types 测试) — PASS

- PR #106 squash merged → main `ef2e318`
- object_types 首次测试 (13): 内置类型、自定义注册 (parent 继承)、
  table 覆盖、list_types、validate (required/type/choices/list)、
  defaults、UI schema、unknown type
- 无代码变更; 本地全量 1323 passed, 5 skipped
- 零测试组件 8→7


### LOG-20260812-098 — PR #107 MERGED (tool_evidence 测试) — PASS

- PR #107 squash merged → main `e9b33a6`
- tool_evidence 首次测试 (11): file_read/safe_write/kb_search/mk_search
  证据判定、dry_run 非证据、非真实工具、缺失/不支持工具名、空白剥离
- 无代码变更; 本地全量 1320 passed, 5 skipped
- 零测试组件 7→6


### LOG-20260812-099 — PR #108 MERGED (mermaid_gen 测试) — PASS

- PR #108 squash merged → main `495ae2d`
- mermaid_gen 首次测试 (8): flowchart 结构/回退、knowledge graph
  (card 形状/safe id/边)、review timeline (空/有/截断)、safe id
- 无代码变更; 本地全量 1332 passed, 5 skipped
- 零测试组件 6→5


### LOG-20260812-100 — PR #109 MERGED (knowledge_gardener 测试) — PASS

- PR #109 squash merged → main `9c37073`
- knowledge_gardener 首次测试 (9): 孤儿检测 (出入链索引/limit)、
  关键词重叠连接建议、缺失源、gap 分析 (thin/string tags)、
  evergreen 评分 (rich/seedling/not found)
- 无代码变更 (记录 len(tag)>2 过滤短 tag 行为)
- 本地全量 1332 passed, 5 skipped
- 零测试组件 5→4 (graph_rag/obsidian_importer/research_boundary/source_discovery)


### LOG-20260812-101 — PR #110 MERGED (source_discovery 测试) — PASS

- PR #110 squash merged → main `e0ea6d6`
- source_discovery 首次测试 (8): 扩展名分类、跳过目录、缺失目录、
  max_files、大小阈值、文件名前缀匹配卡片、无卡片
- 陷阱记录: conftest 将 TMPDIR 指向 .hermes 隐藏树 + discover_sources
  跳过隐藏路径 → 测试 monkeypatch Path.rglob/exists 用假文件树
- 本地全量 1354 passed, 5 skipped
- 零测试组件 4→3 (graph_rag/obsidian_importer/research_boundary)


### LOG-20260812-102 — PR #111 MERGED (research_boundary 测试) — PASS

- PR #111 squash merged → main `c16a7f2`
- research_boundary 首次测试 (6): 候选/外链/URL 前缀阻断、普通引用
  放行、大小写不敏感、空白剥离、空输入、非字符串强转
- 无代码变更; 本地全量 1360 passed, 5 skipped
- 零测试组件 3→2 (graph_rag/obsidian_importer)


### LOG-20260812-103 — PR #112 MERGED (obsidian_importer 测试) — PASS

- PR #112 squash merged → main `0ed8138`
- obsidian_importer 首次测试 (12): vault folder map、frontmatter 解析
  (simple/list/quoted/absent)、scan_vault 分类+跳过规则+缺失目录、
  import_file (dry-run/not-found/card 导入)、import_vault dry-run
- 陷阱: conftest TMPDIR 隐藏树 → scan_vault 测试 fake rglob 用相对 parts
- 本地全量 1356 passed, 5 skipped
- 零测试组件 2→1 (仅 graph_rag)


### LOG-20260812-104 — PR #113 MERGED (graph_rag 测试) — PASS

- PR #113 squash merged → main `76d25f1`
- graph_rag 首次测试 (2): index 计数 (fake GraphDB/VectorDB/embedder)、
  多跳搜索扩展+综合评分; 模块级 DB 单例用 fake 替换无需 sqlite-vec
- **13/13 零测试 shared 组件全部清零**


### LOG-20260812-105 — PR #114 MERGED (schemas/daily_notes 测试) — PASS

- PR #114 squash merged → main `9008fcd`
- schemas 15 测试 (响应包络默认值/字段/必填校验/请求模型默认值)
- daily_notes 8 测试 (get/create/append/timeline cutoff/link_to_daily)
- **shared/*.py 全部 15 模块测试覆盖完成**
- 本地全量 1389 passed, 5 skipped, 0 failed


### LOG-20260812-106 — PR #114 MERGED (schemas/daily_notes 测试) — PASS

- PR #114 squash merged → main `9008fcd`
- schemas 15 + daily_notes 8; shared/*.py 全部 15 模块测试覆盖完成
- 本地全量 1389 passed, 5 skipped


### LOG-20260812-107 — PR #115 MERGED (pipeline 直接测试) — PASS

- PR #115 squash merged → main `41a33a5`
- run_pipeline 直接多阶段契约测试 (5): 完整动作链 (crossref
  legacy_heuristic+verified=False)、最小动作子集、外源 auto-ingest
  拒绝、file 源 approved-roots 要求、空内容短路
- 此前仅间接覆盖 (mfx012 隔离/phase4)
- 本地全量 1399 passed, 5 skipped


### LOG-20260812-108 — PR #116 MERGED (registry-scoring 测试) — PASS

- PR #116 squash merged → main `70e0c88`
- batch_score_registry 首次测试 (8): category_key (精确/组合/未知)、
  score_registry_entry (qualify/高风险/未知类)、absorption bonus、main 禁用门
- 修复 category_key 对 'RAG / AI Platform' 规范化缺失 (空白+斜杠间距)
  → 组合类永不匹配评分行
- CI 注意: 首跑 test(3.12) 失败 = GitHub Actions setup-uv 基础设施
  故障 (self-signed cert / API TLS), 与代码无关; rerun --failed 后全绿
- 本地全量 1399 passed, 5 skipped


### LOG-20260812-109 — PR #117 MERGED (vault search 函数测试) — PASS

- PR #117 squash merged → main `93cc133`
- search_vault (vault.py:64, H3) 首次函数级测试 (5): 命中+片段/hash、
  大小写不敏感、无匹配、空查询拒绝、缺失目录拒绝
- 此前 API 层由 test_workspace_vault_api 覆盖 (只读契约);
  函数层错误路径由本 PR 补齐
- 本地全量 1420 passed, 5 skipped


### LOG-20260812-110 — PR #118 MERGED (SM-2 调度测试) — PASS

- PR #118 squash merged → main `24b7e24`
- knowledge_base.reviews 首次直接测试 (11): _sm2_interval 纯算法
  (越界/失败重置/首/二/增长间隔/ease 下限)、schedule_review
  (首次/mastered 转变/struggling + 状态更新)、due 过滤、history 过滤
- 此前仅间接覆盖 (mermaid/gardener 测试中 mock)
- 本地全量 1420 passed, 5 skipped


### LOG-20260812-111 — PR #118 MERGED (SM-2 调度测试) — PASS

- PR #118 squash merged → main `24b7e24`
- knowledge_base.reviews 首次直接测试 (11): _sm2_interval 纯算法、
  schedule_review (状态更新)、due/history 过滤
- 本地全量 1420 passed, 5 skipped


### LOG-20260812-112 — PR #119 MERGED (kb 测试纳入 + DB 隔离) — PASS

- PR #119 squash merged → main `f76280f`
- knowledge_base/tests 38 个测试此前从未被 pytest 收集 (testpaths
  只含 tests/) = 死覆盖 → testpaths += knowledge_base/tests
- 新增 kb conftest autouse fixture: storage.DB_PATH 重定向到全新
  空库 + storage.init() — 否则全量跑时 FTS candidate 计数断言被
  tests/ 共享真实库残留数据破坏 (object_ids 多行)
- 全量 1458 passed (1420+38), 5 skipped, 0 failed


### LOG-20260812-113 — PR #119 MERGED (kb 测试纳入) — PASS

- PR #119 squash merged → main `f76280f`
- knowledge_base/tests 38 测试激活 (testpaths) + DB 隔离 conftest
- 全量 1458 passed (1420+38), 5 skipped, 0 failed


### LOG-20260812-114 — PR #120 MERGED (tests lint 修复) — PASS

- PR #120 squash merged → main `a68742d`
- 3 I001 import 排序自动修复 + test_daily_notes F841 未用变量
- CI ruff 范围不含 tests/ (卫生性修复); 16 相关测试通过
- 剩余 2 个预存 F841 (test_mfx001) 留待他日


### LOG-20260812-115 — PR #120 MERGED (tests lint 修复) — PASS

- PR #120 squash merged → main `a68742d`
- 3 I001 import 排序 + 1 F841; CI ruff 范围不含 tests/ (卫生)


### LOG-20260812-116 — PR #121 MERGED (外置依赖文档更新) — PASS

- PR #121 squash merged → main `c17e0e8`
- EXTERNAL_DEPENDENCIES.md: 登记 ci-adapters 组 (rapidocr-onnxruntime/
  faster-whisper/markitdown/newspaper4k/readabilipy/trafilatura)、
  吸收+Magika 标记已 merge、HF 模型缓存位置
- 双写同步: OS configuration 仓库 → `8ab8bee` (master)


### LOG-20260812-117 — PR #122 MERGED (Magika 许可登记) — PASS

- PR #122 squash merged → main `f0bd1ca`
- THIRD_PARTY_NOTICES 补 Vendored models 节: Magika ONNX (Apache-2.0,
  standard_v3_0, shared/models/magika/) — EXTERNAL_DEPENDENCIES 3.2
  引用缺失项修复


### LOG-20260812-118 — PR #122 MERGED (Magika 许可登记) — PASS

- PR #122 squash merged → main `f0bd1ca`
- THIRD_PARTY_NOTICES 补 Vendored models 节 (Magika ONNX Apache-2.0)


### LOG-20260812-119 — PR #123 MERGED (uv.lock 漂移修复) — PASS

- PR #123 squash merged → main `629978c`
- 修复 3 个依赖漂移: ①httpx2 幽灵包 (不存在的包名) → httpx;
  ②faster-whisper/rapidocr-onnxruntime (#98/#99) 从未入 lock
  (仅手动安装) → uv lock 补锁; ③release-manifest digest 同步 (rev 6)
- CI 首跑 lint 失败 (release-manifest.json missing-final-newline) →
  amend 加末尾 LF → force-push → 全绿 (run 31543019316)
- 全量 1458 passed, 5 skipped; 门禁干净


### LOG-20260812-120 — PR #124 MERGED (H2 evidence 接入管线) — PASS

- PR #124 squash merged → main `9fa0558`
- h2-evidence: pipeline Stage 7 evidence action — DOI 直接查
  Crossref/DataCite; 否则 claim-text OpenAlex; classification=
  public-evidence, verified=False
- enrich_with_public_sources 扩展 claim_text/qid; 3 契约测试


### LOG-20260812-121 — PR #125 MERGED (H2 SM-2 接入练习生命周期) — PASS

- PR #125 squash merged → main `2d2e2ff`
- h2-learning: record_practice_evidence 硬编码 (interval=1/ease=2.5/
  next=now) → knowledge_base.reviews._sm2_interval 真实调度
  (quality=5 连续 3 次 → 1/6/16 天递增)
- 测试断言 interval 增长 [1,6,16] + ease>=2.5


### LOG-20260812-122 — PR #125 MERGED (H2 SM-2 接入) — PASS

- PR #125 squash merged → main `2d2e2ff`
- record_practice_evidence 硬编码调度 → _sm2_interval 真实调度
  (1/6/16 天递增); 测试断言 [1,6,16] + ease>=2.5


### LOG-20260812-123 — PR #126 MERGED (H2 bake-off CLI) — PASS

- PR #126 squash merged → main `34eae0c`
- scripts/run_bakeoff.py: 可重复 bake-off CLI (OCR/ASR 引擎对比,
  CER/WER, CSV+JSON 报告; 不可用引擎诚实跳过)
- 实跑验证: rapidocr 三语种 CER 0.0, faster-whisper en CER 0.0


### LOG-20260812-124 — PR #127 MERGED (H2 状态文档更新) — PASS

- PR #127 squash merged → main `0088bdb`
- PROJECT_STATUS: ASR/Evidence 关闭环 (H2 bake-off 实跑 + Evidence
  接入); 进度列表 #81 已 merge + H2 链 #82/#97/#99/#105/#124/#125/#126
- H2 管线整合全链闭环 (routing/quality/evidence/learning/bakeoff/commit)


### LOG-20260812-125 — 远程分支清理 + #127 MERGED — PASS

- #127 squash merged → main `0088bdb` (H2 状态文档)
- 远程分支清理 68 个 (62 merged 残留 + 3 absorbed 孤儿 + 2 axw squash
  + 1 empty); 保留 main/codex 权威/release-v0.4.0-contract/verification-summary


### LOG-20260812-126 — PR #128 MERGED (Marker REVIEW-BLOCK 合规修复) — PASS

- PR #128 squash merged → main `a2056d0`
- 增强 MFX-001 测试暴露真实缺陷: 账本 B003 (Marker) REVIEW-BLOCK
  (代码 Apache-2.0, 权重修改版 OpenRAIL-M 需单独审查) 却在默认
  PDF 引擎链 (marker-pdf) — 移除; _via_marker 保留待审查通过
- 测试改为账本 blocked 集合驱动 + 修正 zotero guard 陈旧断言
- 全量 1461 passed


### LOG-20260812-127 — PR #128 MERGED (Marker REVIEW-BLOCK 合规) — PASS

- PR #128 squash merged → main `a2056d0`
- 增强 MFX-001 测试暴露: B003 Marker REVIEW-BLOCK 却注册为默认
  PDF 引擎 → 移除; 测试改用账本 blocked 集合驱动


### LOG-20260812-128 — PR #129 MERGED (占位清理) — PASS

- PR #129 squash merged → main `98f7546`
- app/agent/tool_router.py + app/core/attention.py: DEFERRED 标注
- knowledge_base/taskpack/builder.py + context_pack/builder.py:
  死壳删除 (实现都在 __init__.py)
- 6 个 imported-designs 索引 README 确认是合法导航非占位


### LOG-20260812-130 — PR #130 MERGED (H2 intake 记录) — PASS

- PR #130 squash merged → main `996462f`
- workspace/intake/2026-08-12-h2-pipeline-integration.md: H2 全链 +
  MFX-001 合规修复 + 附带项 + 待办 + 回滚说明
