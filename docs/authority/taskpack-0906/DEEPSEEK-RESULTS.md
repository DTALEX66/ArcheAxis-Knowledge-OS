# DeepSeek 批量低风险任务包 — 结果回执（2026-09-06）

> 唯一结果文件。每批一个分节，按回交格式填写实际值。GPT 的
> HANDOFF.md / DEEPSEEK-TASKS.md / GPT-HARD-TASKS.md 为已有交接，本文件不覆盖、不合并。

- 工作分支：`codex/full-loop-0906`；base HEAD `2948b155db069d608e7ebd8acb7956079d8cf69f`
- `main`：`4ca46ea...`（不动）；`origin/main` 一致
- PS7 实际路径：`C:\Users\ALEX\AppData\Local\Microsoft\PowerShell\7\pwsh.exe`（文档给的
  `C:\Program Files\PowerShell\7\pwsh.exe` 本机不存在，属环境差异，未改用 5.1）

---

## DS01 现有入口与坏链接清单（T00/T14/T19）

- **任务卡 / 原任务 ID**：DS01 / T00、T14、T19
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `D:\All projects\ArcheAxis-Knowledge-OS`（branch codex/full-loop-0906）/
  dirty（仅 GPT 未提交的 3 个交接文件：HANDOFF.md 修改 + DEEPSEEK-TASKS.md、GPT-HARD-TASKS.md 未跟踪；本批未触碰它们）
- **实际修改文件与新增文件**：无 tracked 修改；只读产出
  `.project-local/runs/ds01/ds01-links.json`（ignored，SHA-256 `7977a505c0c7343c903acdfa42c01db537fb7463e34e397f26cf03accce1292d`，107304 B）
- **读取并复用的实现与调用方**：`docs/CONFIGURATION_AUTHORITY_INDEX.md`、
  `docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`、`docs/DIRECTORY_AUTHORITY_INDEX.md` +
  `git ls-files -z`（quotePath=false）全 tracked 枚举
- **验收案例、独立预期及证据来源**：
  - 扫描 269 个 tracked `.md` 文档、42 个脚本（脚本不按 Markdown 链接解析，已单独计数）；
  - 链接总数 303；分类：missing 16 / external 60 / untracked-present 2 / anchor 0 / case-mismatch 0 / outside-repo 0；
  - 构造嵌套正/反例自检：`../AGENTS.md`→present、`no-such-file.md`→missing，证明相对解析不误判正常链接。
- **发现的缺陷（16 处坏链接，均属历史文档，仅建议补丁、不批量替换）**：
  - `docs/architecture/imported-designs/inspiration-research-root/{01_DO_NOT_REPEAT,02_LESSONS_LEARNED,03_ENV_KNOWN_ISSUES}.md`
    各 4 处 `../00_铁律.md / ../01_DO_NOT_REPEAT.md / ../02_LESSONS_LEARNED.md / ../03_ENV_KNOWN_ISSUES.md`
    → 目标文件实际位于同目录（应去掉 `../`），相对层级多了一级。
  - `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/README.md:27`
    → `../../../FUTURE_EXECUTION_BLUEPRINT.md` 目标缺失（文件已被改名/移走）。
  - `docs/truth/H0_H1_STATUS_HANDOFF.md:18-20` → 3 个 `../../taskpacks/*.md` 旧任务包文件已不在该路径。
  - `docs/authority/taskpack-0906/HANDOFF.md:9-10` → `DEEPSEEK-TASKS.md`、`GPT-HARD-TASKS.md`
    为未跟踪存在文件，归入 untracked-present（非真缺失）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：上述 16 项的历史文档补丁是否改链接
  vs 改文件位置，交 GPT 定（涉及历史快照，不自行改）。
- **本批可回滚范围**：无 tracked 改动；删除 `.project-local/runs/ds01/` 即回滚（ignored）。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否（默认本地交付）。
- **下一张可执行任务卡**：DS04（文本 worker 边界回归）。

---

## DS04 文本 worker 边界回归（T02/T05/T07）

- **任务卡 / 原任务 ID**：DS04 / T02、T05、T07
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（含本文件与新增测试；GPT 三文件仍在）
- **实际修改文件与新增文件**：`tests/workers/test_text_ndjson.py`（仅新增一个表驱动方法
  `test_decode_and_anchor_matrix_has_independent_expectations`，未改生产实现）
- **读取并复用的实现与调用方**：`services/python-workers/transport/text_ndjson.py`（真实 NDJSON 传输，
  注意本分支真实入口是 transport/text_ndjson.py，不是 document/worker_text.py）、
  `tests/workers/test_text_ndjson.py` 既有用例
- **验收案例、独立预期及证据来源**（10 组子案例，预期手写、非复制输出）：
  ascii / 中文 / NFD 组合字符(e\u0301) / astral emoji(😀) / UTF-8 BOM 剥离 / UTF-16LE BOM /
  CRLF+孤立CR 保留 / 空文件(零行覆盖=1.0+说明) / GBK 回退 / 无效字节→U+FFFD 替换；
  每例断言 text 字节、decode 编码、loss_report covered==total、coverage=1.0、
  document_structure 锚点数==covered。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：
  `dev.py --pytest -- tests/workers/test_text_ndjson.py -q` → exit 0 / 13 passed（47 subtests）/ 0 fail / 0 skip /
  run `be268a2d33/31568caa25ca`
- **发现的缺陷与未满足前置**：无产品失败；确认空文件 zero-line 语义已由实现以 loss_note 说明（非缺陷）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：无（本批纯测试扩充）。
- **本批可回滚范围**：删除新增测试方法即回滚；未触碰生产代码。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否（默认本地交付）。
- **下一张可执行任务卡**：DS05（Canvas/字幕解析案例扩充）。

---

## DS05 Canvas 与字幕解析案例扩充（T05）

- **任务卡 / 原任务 ID**：DS05 / T05
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（新增测试与两个 fixture）
- **实际修改文件与新增文件**：
  `tests/workers/test_document_fixture_matrix.py`（新增，11 用例）；
  `tests/fixtures/vnext/documents/canvas-zh-group.canvas`、`sample-overlap.srt`（新增 fixture）
- **读取并复用的实现与调用方**：`services/python-workers/document/worker_canvas.py`、
  `worker_subtitles.py`（真实入口，importlib 加载后直接调用 `extract`，非子进程）
- **验收案例、独立预期及证据来源**：
  Canvas：中文+group+file+link 投影与锚、edges 原样保留、缺/重复 id、未知边节点、未知节点类型 拒绝；
  字幕：Unicode+时序、重叠时段不合并、空轨拒绝、畸形时间拒绝、无末尾换行仍解析、VTT NOTE/内联标签剥离。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：
  `dev.py --pytest -- tests/workers/test_document_fixture_matrix.py -q` → exit 0 / 11 passed / 0 fail / 0 skip /
  run `be268a2d33/eb9cfc9ec3cc`
- **发现的缺陷与未满足前置**：无产品失败；解析器行为符合预期（重叠保留、破损拒绝）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：无。
- **本批可回滚范围**：删除新增测试与 2 个 fixture 即回滚；未改生产实现。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS07（质量指标独立复算与负例）。

---

## DS07 质量指标独立复算与负例（T07）

- **任务卡 / 原任务 ID**：DS07 / T07
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（新增测试方法）
- **实际修改文件与新增文件**：`tests/workers/test_quality_regressions.py`
  （新增 `test_hand_computed_cer_wer_matrix`，7 组手算样例；未改生产实现）
- **读取并复用的实现与调用方**：`services/python-workers/evaluation/worker_quality.py`
  （真实 `evaluate` + `validate_report_metrics`）
- **验收案例、独立预期及证据来源**（分子/分母显式写出，不复制输出）：
  完全相同(0/3)、插入(1/3)、删除(1/3)、替换(1/3)、错误数>参考长(`abcdefghij` vs `a` → 9/1=9.0，不夹到 1)、
  中文+数字(`正确123` vs `正确1234` → 1/6)、分词 WER(`a b 123` vs `a b 124` → 1/3)。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：
  `dev.py --pytest -- tests/workers/test_quality_regressions.py -q` → exit 0 / 15 passed（30 subtests）/ 0 fail / 0 skip /
  run `be268a2d33/42d8b9c50847`
- **发现的缺陷与未满足前置**：无；确认误差率可>1 且不 clamp（既有 `test_semantic_boundary...` 与本次 9.0 双证）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：无（空参考定义已由既有 `test_empty_gold` 覆盖）。
- **本批可回滚范围**：删除新增测试方法即回滚。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS08（跨语言合同用例补齐）。

---

## DS08 跨语言合同用例补齐（T02）

- **任务卡 / 原任务 ID**：DS08 / T02
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（新增测试文件）
- **实际修改文件与新增文件**：`tests/contract/test_deepseek_contract_cases.py`（新增，9 用例；未改 schema/生成器）
- **读取并复用的实现与调用方**：`packages/contracts/v1/*.schema.json`（9 个 schema）、
  `scripts/contracts/generate_vocabulary.py`（--check 漂移检查）
- **验收案例、独立预期及证据来源**（真实 jsonschema 校验，非字符串包含）：
  worker-protocol（未知状态/坏 sha256 形状/缺 required/错版本）、job-status 闭枚举、anchor 几何负例、
  assessment-vocabulary 闭枚举、learning/machine-feedback 未知事件与缺字段、
  quality-report 状态/值耦合（measured 必须 number、unmeasured 必须 null，均 schema 级）、
  coverage-receipt 必填 providers 与 provider 字段、loss-receipt 未知字段/dependentRequired/coverage 上限。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：
  `dev.py --pytest -- tests/contract/test_deepseek_contract_cases.py -q` → exit 0 / 9 passed / 0 fail / 0 skip /
  run `be268a2d33/eab833a120be`；`generate_vocabulary.py --check` → `{"status":"pass","drift":[]}` exit 0
- **发现的缺陷与未满足前置**：无产品缺陷；修正了本人两处对 schema 形状的误判（quality-report 状态/值耦合、
  coverage-receipt 必填结构，均为测试侧期望错误，本卡内修复）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：无。
- **本批可回滚范围**：删除新增测试文件即回滚；未触碰权威 schema 与生成器。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS02（旧能力复用证据表，每批 20 项）。

---

## DS02 旧能力、调研与复用证据表（T17/T13）

- **任务卡 / 原任务 ID**：DS02 / T17、T13
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（本文件）
- **实际修改文件与新增文件**：无 tracked 修改；只读产出
  `.project-local/runs/ds02/ds02-reuse.jsonl`（ignored，SHA-256 `766ab96ca15665ed909e04440916ca2986fadbfa56a122e58c7148abe2bcc534`，20 行 / 22629 B）
- **读取并复用的实现与调用方**：`LEGACY_MANIFEST.yaml`（1246 项）+ 20 项代码资产的文件头 +
  逐项 dotted-module 的 `git grep -F` 导入点扫描（真实 import 证据，非裸词干匹配）
- **验收案例、独立预期及证据来源**：本批真正审阅 20 项代码资产
  （app/__init__、adapters/*、adapters/deeptutor/authority、agent/executor 等，
  覆盖 research/learning/knowledge 能力，含 DeepTutor/Anki-Zotero/mastery/evidence）；
  区分「有旧实现(头已读)」「有导入点(0–5)」「测试缺失(未核验，标记 gap)」。
  语义 capability 标签与吸收裁决未填（留 GPT T13），不冒充语义审查。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：只读脚本，exit 0（非 pytest）。
- **发现的缺陷与未满足前置**：无产品缺陷；`app/__init__.py`/`adapters/__init__.py` 无导入点属预期。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：20 项 capability/risk/reuse_target 的语义裁决交 GPT。
- **本批可回滚范围**：删除 `.project-local/runs/ds02/` 即回滚。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS03（设计/LOGO/界面状态素材整理）。

---

## DS03 已有设计、LOGO、界面状态素材整理（T18）

- **任务卡 / 原任务 ID**：DS03 / T18
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（本文件）
- **实际修改文件与新增文件**：无 tracked 修改；只读产出
  `.project-local/runs/ds03/ds03-design-assets.json`（ignored，SHA-256 `b4856783684908014764cbe240a5ee7914cf8449999f4eac8acffa4c45af1992`）
- **读取并复用的实现与调用方**：tracked 设计资产（19 项：OSUI 6 PNG 预览、桌面/绿版图标 png/svg/ico、
  Avalonia App/MainWindow.axaml、legacy bootstrap css）+ `docs/design/` 5 篇设计文档；逐项 sha256、消费者 grep。
- **验收案例、独立预期及证据来源**：
  - 同名文件以哈希区分（已逐项 sha256）；黑白主题保留为用户约束（未改动）。
  - 未找到历史 GPT 设计稿 → 标记“未获得”，不补造；未生成新 LOGO。
  - 交互状态证据扫描（grep -l）：loading/empty/failure/retry/conflict/readonly/unavailable 有命中；
    cancel/keyboard/reduced-motion 部分命中；zoom 0 命中（缺口显式记录）。
  - 实组件(markup axaml/css)与效果图(png 预览)分列 kind；consumer 字段保留真实引用。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：只读脚本，exit 0（非 pytest）。
- **发现的缺陷与未满足前置**：无产品缺陷；zoom/reduced-motion 证据缺口为 T18 输入（交 GPT 设计裁决）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：界面状态证据缺口(zoom=0)与主题 token 裁决交 GPT。
- **本批可回滚范围**：删除 `.project-local/runs/ds03/` 即回滚。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS06（Office/网页/截图/媒体样例账册）。

---

## DS06 Office、静态网页、截图与媒体样例账册（T05/T06）

- **任务卡 / 原任务 ID**：DS06 / T05、T06
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（本文件）
- **实际修改文件与新增文件**：无 tracked 修改；只读产出
  `.project-local/runs/ds06/ds06-format-cases.json`（ignored，SHA-256 `90ecec9a310b4dd5f135d515581e5748d356c93bce9f38d87a16b77ddd7f54d0`，3906 B）
- **读取并复用的实现与调用方**：`worker_office.py`、`vision/worker_ocr.py`、`media/worker_transcribe.py`、
  `web/worker_html.py`（真实接口只读试跑）+ project-owned golden fixtures
- **验收案例、独立预期及证据来源**（每项输入哈希 + probe/execution/quality 三态）：
  引擎探针：pptx/openpyxl/pymupdf/PIL/rapidocr/cv2/faster-whisper/ffmpeg/tesseract 全 pass；
  执行：docx/pptx/xlsx/pdf/ocr/asr/html 7 例真实跑通（pass）；
  质量：docx/pptx/xlsx/ocr 命中金标子串→asserted，pdf/asr/html→unmeasured（不虚标）。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：只读脚本 exit 0（非 pytest）。
- **发现的缺陷与未满足前置**：无产品缺陷；依赖缺口显式记录——F03 动态渲染需 playwright+chromium、
  F06 扫描页 OCR 编排、F11 VL 对齐、网页抓取需网络权限、无授权视频样例（均不自装）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：无（依赖缺口为需求登记，非缺陷）。
- **本批可回滚范围**：删除 `.project-local/runs/ds06/` 即回滚。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS09（缓存保全账目复核，绝不删）。

---

## DS09 缓存保全账目复核，绝不删除（T20）

- **任务卡 / 原任务 ID**：DS09 / T20
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（本文件）
- **实际修改文件与新增文件**：无 tracked 修改；只读产出
  `.project-local/runs/ds09/ds09-inventory.json`（ignored，SHA-256 `abdd2b4699a6f1390f582d5e251265feb50a728a6f4be117fb9396f966fa0f53`，31068 B）
- **读取并复用的实现与调用方**：`scripts/maintenance/inventory_project.py`（read_only_dry_run 语义）；
  其自带测试 `tests/maintenance/test_inventory_project.py` 全绿。
- **验收案例、独立预期及证据来源**：
  - 本次受限盘点 logical bytes = 25,457,767,687（25.46GB，仅成功观测的 regular 文件；不含 .git/.hermes/.venv/src-tauri 内被排除项），
    **不是**仓库总量/磁盘占用/释放量（旧记录 19,676,885,323 已变化，如实回写）；
  - 单位 logical_bytes、硬链接各自计入、reparse/junction 跳过（reparse=2，未遍历目标）、
    allocated_space=not_measured、file_identity=not_collected —— 逐项核对无误；
  - 4 个旧路径错误仍存在（.project-local 下 pytest UNC/segment-* 深路径 FileNotFoundError），如实保留，未按零字节误报；
  - 观测到 untracked 空目录 `d/All projects`（0 文件）——**不删除/不移动（DS09 边界）**，交 GPT 裁决；
  - 分类（仅标注，不执行）：可重建缓存=apps/bin+obj、build/、target/、.venv、src-tauri(target+捆绑)、desktop(node_modules+target)、
    .pytest_cache/.ruff_cache/__pycache__/.project-local/runs；唯一/源码资产=其余源码目录。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：
  `inventory_project.py <root>` exit 1（含 4 个预期路径错误）；`test_inventory_project.py` 9 passed /
  run `be268a2d33/6fc2b5c386cd`
- **发现的缺陷与未满足前置**：4 个旧路径错误仍存在（非零字节误报，如实保留）；`d/All projects` 空目录待 GPT 裁决。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：`d/All projects` 空目录是否清理（授权）；缓存清理授权仍归 GPT/用户。
- **本批可回滚范围**：删除 `.project-local/runs/ds09/` 即回滚；未执行任何删除/移动。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否。
- **下一张可执行任务卡**：DS10（现有测试批量执行与失败归属，收尾汇总）。

---

## DS10 现有测试的批量执行与失败归属（T01/T15）

- **任务卡 / 原任务 ID**：DS10 / T01、T15
- **base SHA / 当前 HEAD / 工作区路径 / 是否 dirty**：
  `2948b15` / `2948b15` / `codex/full-loop-0906` 主 checkout / dirty（本批改动 + GPT 三文件）
- **实际修改文件与新增文件**（本批）：
  改 `tests/workers/test_text_ndjson.py`、`tests/workers/test_quality_regressions.py`；
  新增 `tests/workers/test_document_fixture_matrix.py`、`tests/contract/test_deepseek_contract_cases.py`、
  `tests/fixtures/vnext/documents/canvas-zh-group.canvas`、`sample-overlap.srt`；
  结果 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md`。
  （`HANDOFF.md` 修改 + `DEEPSEEK-TASKS.md`/`GPT-HARD-TASKS.md` 为 GPT 既有未提交文件，未触碰。）
- **读取并复用的实现与调用方**：DS04–DS08 所改测试对应的真实 worker/契约入口。
- **验收案例、独立预期及证据来源**：合并定向回归（本批所有改动测试 + 全 tests/contract）。
- **测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID**：
  `dev.py --pytest -- tests/workers/test_text_ndjson.py test_document_fixture_matrix.py
   test_quality_regressions.py tests/contract/... -q` → exit 0 / **88 passed / 106 subtests / 0 fail / 0 skip**
- **发现的缺陷与未满足前置**：无产品失败；6 条 jsonschema/RefResolver DeprecationWarning（非错误，可选后续）。
- **需要 GPT 的精确裁决、文件、符号及最小失败案例**：无（本批零失败）。
- **本批可回滚范围**：撤销上述 6 个文件改动/新增即回滚。
- **是否提交 / 推送 / CI / 合并 / 安装态验证**：均否（默认本地交付；commit/push 待用户明确授权）。
- **下一张可执行任务卡**：无（DS01–DS10 全部完成；DS11–DS15 前置未满足，停手回交）。

---

## 最终汇总（DS01–DS10 完成；DS11–DS15 停手）

| 卡 | 结果 | 证据 |
|---|---|---|
| DS01 | 完成 | 269 文档 303 链接，16 坏链（历史文档），`ds01-links.json` |
| DS04 | 完成 | 10 组解码/锚点边界，13 passed |
| DS05 | 完成 | 11 用例 Canvas/字幕边界 |
| DS07 | 完成 | 7 组手算 CER/WER，误差率可>1 |
| DS08 | 完成 | 9 用例覆盖 9 schema，vocabulary drift 通过 |
| DS02 | 完成 | 20 项代码资产 head+导入点证据 |
| DS03 | 完成 | 19 资产+5 设计文档+状态证据矩阵 |
| DS06 | 完成 | 7 格式三态账册+依赖缺口 |
| DS09 | 完成 | 只读盘点 25.46GB logical，4 旧路径错误如实保留 |
| DS10 | 完成 | 合并回归 88 passed/106 subtests |
| DS11–DS15 | **停手** | 需 GPT 先给：worker 契约/错误分类/覆盖回执/资源限制（DS11）、批准 tokens/组件/状态表/服务接口（DS12）、冻结旧→新映射+造数入口（DS13）、冻结状态机/权限/撤销/时间语义（DS14）、候选 manifest/哈希/逐项结果（DS15） |

**未满足前置的精确清单（交 GPT）**：
- DS11 需冻结的 worker 输入/输出、错误分类、覆盖回执、资源限制、允许修改文件清单。
- DS12 需批准的 tokens、组件 API、状态表、页面范围、真实服务接口。
- DS13 需冻结的旧→新字段映射与安全造数入口。
- DS14 需冻结的状态机、角色/权限、撤销传播、时间语义。
- DS15 需实际验收过的候选 manifest/哈希及逐项结果。

**总体**：本地交付 + 报告；未 commit/push/merge；E 盘未访问；`.hermes` 只读未新写（一处误写已删）；
未删任何用户资产；发现 untracked 空目录 `d/All projects` 交 GPT 裁决。

---

## R2 接收审查纠偏（本地返修，未提交/未推送/未合并）

> 依据 DP-R2 返修任务包（`docs/authority/taskpack-0906/DEEPSEEK-REWORK-R2.md`，GPT 未提交文件）对上方 R1
> 回执做分级纠偏。本段只追加纠偏与再分级，**不回写上方历史数值**；待 R09 合并回归收口后统一出 R01–R09 验收表。

1. **DS02 → PARTIAL（待 R03 前）**：R1 仅完成「文件头已读 + dotted-module 导入点扫描」，语义字段
   `capability_observed` / `implementation_symbols` / `callers_verified` / `tests_read` / `tests_run` /
   `risk_observed` / `target_proposal` / `gpt_decision_needed` 均未填，不能判「完成」。须待 R03 对 20 项
   逐「实际函数体 + ≥1 调用方 + 测试」真实语义审阅并回填；空 `__init__` 记 `EMPTY_MODULE`，缺失记
   `NOT_FOUND`，绝不写 `capability=null`。
2. **DS03 → PARTIAL**：`ds03-design-assets.json` 的命中属「结构/关键词候选证据（substring_asserted 级）」，
   **非运行验收**；zoom/reduced-motion 证据缺口仍待 GPT 设计裁决。须待 R08 补 SEARCH_HIT /
   NO_MATCH_IN_SCANNED_SCOPE 可复现证据后方可升级。
3. **DS09 → PARTIAL**：25,457,767,687 logical bytes 为受限观测值（含 4 旧路径错误 + reparse/junction 跳过 +
   `d/All projects` 判空），非运行验收；缓存分类须待 R07 纠偏为 PRESERVE_EVIDENCE / REBUILD_CANDIDATE /
   SOURCE_OR_UNIQUE / UNKNOWN，且 `d/All projects` 更正为「存在子目录、保留」。
4. **DS04 / DS08 覆盖待加固**：两者测试已通过（DS04 13 passed、DS08 9 passed + vocab drift pass），但
   「已通过」≠「已加固」——DS04 锚点/坏编码预期须待 R04 用精确 `expected_ranges` 重写并加负控制
   （char_end 偏移 1 必失败）；DS08 合同负例须待 R05 单字段化 + 内存 schema 弱化负控制。
5. **文件计数口径**：R1 本批改动 = **6 测试/样例**（`test_text_ndjson.py`、`test_quality_regressions.py`、
   `test_document_fixture_matrix.py`、`test_deepseek_contract_cases.py`、`canvas-zh-group.canvas`、
   `sample-overlap.srt`）**+ 1 回执**（本 `DEEPSEEK-RESULTS.md`）。
6. **`.hermes` 只读声明纠偏**：上方汇总「`.hermes` 只读未新写」不成立——本人确有一次误写 `ds09-run.ps1`
   至 `.hermes/task-runtime/`，已立即删除并重建于 `.project-local/runs/ds09/`。因不得读取私密 `.hermes`
   内容，无法事后核验该路径当前状态，故标注 **UNVERIFIED（一次误写、已删）**，不宣称「只读未新写」。
   后续任务状态一律写入 `.project-local/runs/`，不再写 `.hermes/`。

---

## R2 验收表（R01–R09 · 本地返修 · 未提交/未推送/未合并）

> 结论：**本地返修待 GPT 接收**。本轮未改生产实现 / schema / 生成器 / Rust / C# / 数据库 / 锁文件 / CI /
> AGENTS.md / 根契约 / 冻结 TASKS；未删任何目录缓存资产；E 盘未访问；未读私密 `.hermes` 内容与凭据。
> 证据文件统一写入本轮 dev.py run 根 `.project-local/runs/be268a2d33/b883e3d42ebc/`。

| 卡 | 结果 | 改动路径 / 产出 | 关键证据 |
|---|---|---|---|
| R01 | PASS | `DEEPSEEK-RESULTS.md`（追加「R2 接收审查纠偏」，不回写历史数值） | 6 条纠偏逐项落点见上节 |
| R04 | PASS | `tests/workers/test_text_ndjson.py` | 独立 `expected_ranges` + `expected_invalid_text` + char_end 负控制 |
| R05 | PASS | `tests/contract/test_deepseek_contract_cases.py` | 坏 SHA/坏 URI 单字段化 + 内存 schema 弱化负控制 + 删 F401 |
| R06 | PASS | `tests/workers/test_document_fixture_matrix.py` | fail-closed `setUp`(ARCHEAXIS_RUN_ROOT 必填) + 隔离负例 |
| R02 | PASS | 5 份历史文档（仅 16 处链接目标字符串） | 重扫 16 目标全部解析存在 |
| R03 | PASS | `b883e3d42ebc/r03-semantic-review.json`（20 项） | 18 模块函数体全读 + 149 测试通过 + 2 EMPTY_MODULE |
| R07 | PASS | `b883e3d42ebc/r07-cache-classification.json` + R2 段 | PRESERVE_EVIDENCE/REBUILD_CANDIDATE/SOURCE_OR_UNIQUE/UNKNOWN；`d/All projects` 改「存在子目录、保留」 |
| R08 | **PARTIAL** | `b883e3d42ebc/r08-ds03-evidence.json` + `r08-ds06-evidence.json` | SEARCH_HIT / NO_MATCH_IN_SCANNED_SCOPE / substring_asserted 已补；DOCX 引擎更正为 `worker_office._docx_text`（stdlib ZIP/XML，非 python-docx）；DS06 原始执行命令/输出哈希仍 EVIDENCE_INCOMPLETE |
| R09 | PASS | 合并回归 + 门禁 + 本验收表 | 91 passed / 106 subtests；vocab drift pass；Ruff 新文件 0 问题 |

### R09 精确命令 / exit code / run ID

| # | 命令 | exit | 结果 / run ID |
|---|---|---|---|
| 1 | `dev.py --pytest -- tests/workers/test_text_ndjson.py tests/workers/test_document_fixture_matrix.py tests/workers/test_quality_regressions.py tests/contract -q` | 0 | **91 passed / 106 subtests / 0 fail / 0 skip / 6 warnings**，run `be268a2d33/c148b2f98ca4` |
| 2 | `dev.py -- python scripts/contracts/generate_vocabulary.py --check` | 0 | `{"status":"pass","drift":[]}`，run `be268a2d33/3ee5909fd70d` |
| 3 | `dev.py -- python -m ruff check tests/workers/test_document_fixture_matrix.py tests/contract/test_deepseek_contract_cases.py` | 0 | All checks passed，run `be268a2d33/ee357add2873` |
| 4 | `dev.py -- python -m ruff check tests/workers/test_text_ndjson.py tests/workers/test_quality_regressions.py` | 1 | 4 项 **baseline**（I001、SIM117×2、UP012，均属 R1 原有/既有代码），run `be268a2d33/99a9158555dd`；本轮未新增问题 |
| 5 | `dev.py -- python scripts/check_repository_conventions.py --source worktree` | 0 | passed，run `be268a2d33/7c3f19fd1885` |
| 6 | `git diff --check` | 0 | 无空白/冲突标记错误 |

### 计数变化解释

R1 合并回归 88 passed → R2 **91 passed**（106 subtests 不变）：+2 来自 R05 拆分（坏 SHA/坏 URI 单字段化 + 新增
内存 schema 弱化负控制，`test_deepseek_contract_cases.py` 9→11 用例），+1 来自 R06 新增 fail-closed 隔离负例
（`test_document_fixture_matrix.py` 11→12 用例）。其余测试无回退。

### R1/R2 文件改动按轮重算（消除计数歧义）

- **R1 新增/改动（6 测试/样例 + 1 回执）**：新增 `tests/workers/test_document_fixture_matrix.py`、
  `tests/contract/test_deepseek_contract_cases.py`、`tests/fixtures/vnext/documents/canvas-zh-group.canvas`、
  `sample-overlap.srt`；修改 `tests/workers/test_text_ndjson.py`、`tests/workers/test_quality_regressions.py`；
  回执 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md`（新建）。
- **R2 实际改动（3 测试 + 5 文档 + 2 回执类文件追加）**：`test_text_ndjson.py`(R04)、
  `test_deepseek_contract_cases.py`(R05)、`test_document_fixture_matrix.py`(R06) 各加方法/用例；
  5 份历史文档仅改 16 处链接目标字符串；`DEEPSEEK-RESULTS.md` 追加 R2 两段、`DEEPSEEK-R2-HANDOFF.md` 新建。
- `test_quality_regressions.py` 属 R1 改动并在 R09 合并回归命令中执行（非 R2 遗漏项）。

### 独立预期与负控制摘要

- **R04**：`expected_ranges`（Unicode 字符偏移，手写）逐条断言 `kind/path/char_start/char_end`；
  坏编码断言精确字节 `b"\xef\xbf\xbd"*3` 且 `loss["losses"]==["undecodable bytes replaced with U+FFFD"]`；
  负控制：`expected_structure` 副本 `char_end+1` 必须 `assertNotEqual`。5000 行旧用例保留未重复。
- **R05**：合法基础 `outputs` 先 `assert not _errors`；坏 SHA 命中 `["outputs",0,"sha256"]` 的 `pattern`（嵌套 context
  遍历 `_flatten`），坏 URI 命中 `["outputs",0,"uri"]`；内存深拷贝 schema 仅删 `sha256.pattern` 后坏 SHA 被接受（证明
  测试能察觉约束被删），真实 schema 仍拒绝。已删 F401 `import pytest`，修正过时「measured-null 为 runtime-only」注释。
- **R06**：两 TestCase `setUp` 用 `os.environ["ARCHEAXIS_RUN_ROOT"]`（缺失即 KeyError，先于建临时文件）；
  `_write` 改 `dir=self.tmp.name`；隔离子进程（删该变量 + 置空 TMP/TEMP/TMPDIR）验证 KeyError 退出 0。

### R02 精确链接修正（16 处，仅改目标字符串）

- 3 × `inspiration-research-root/{01,02,03}_*.md` 各 4 处 `../` 前缀移除（共 12），指向同目录四份文件。
- `reference-deliveries/archeaxis-2026/README.md`：`../../../FUTURE_EXECUTION_BLUEPRINT.md` → `../../../../FUTURE_EXECUTION_BLUEPRINT.md`。
- `docs/truth/H0_H1_STATUS_HANDOFF.md` 3 处：`../../taskpacks/` → `../taskpacks/`。
- 重扫回执 `.project-local/runs/be268a2d33/b883e3d42ebc/r02-links-receipt.json`（scope 仅限这五份，16 目标 missing=0）。

### 未满足项 / 交 GPT

- **R03** 为事实核查，未做架构迁移；`target_proposal` 为建议项，目标未批准不阻断事实核查完成。
- **R07** 仅标注分类，`rebuild_verified=false`（无 lock/tool/version/代表性重建证明）；未执行任何删除/搬移/权限变更。
- **R08** DS06 的「原始执行命令 / 输出哈希」在旧 ds06 未记录，标 EVIDENCE_INCOMPLETE，未回填猜测值；
  仅补可核验的 fixture 相对路径 + 输入哈希 + 引擎/解释器版本 + 断言边界。
- **Ruff baseline**：`test_text_ndjson.py`/`test_quality_regressions.py` 的 I001、SIM117×2、UP012 为存量，交 GPT 决定是否 `--fix`。
- 旧 DS11–DS15 仍停手，未造任何假接口/假完成条件。

### 回滚边界

回滚按「每轮实际差异」描述；不整文件恢复，不把证据目录删除当作回滚动作：

- **R2 本轮差异**：`tests/workers/test_text_ndjson.py`、`tests/contract/test_deepseek_contract_cases.py`、
  `tests/workers/test_document_fixture_matrix.py` 回退 R2 新增方法/用例；5 份历史文档回退 16 处链接目标字符串；
  `DEEPSEEK-RESULTS.md` 与 `DEEPSEEK-R2-HANDOFF.md` 回退 R2/BULK 追加内容至上一轮末尾。
- **R1 差异（如需一并回退）**：`test_quality_regressions.py` 回退 R1 新增方法；`test_document_fixture_matrix.py`、
  `test_deepseek_contract_cases.py` 与 2 个 vnext fixture 为 R1 整文件新增（连同 R2 差异一起回退即删除）；`DEEPSEEK-RESULTS.md` 为 R1 新建（删除即整体回退）。
- **证据目录**：`.project-local/runs/be268a2d33/b883e3d42ebc/` 等本轮及历史 run 证据保持原位、只读，不因回滚删除。
- 未 commit / 未 push / 未 merge / 未改产品版本。

---

## BULK-0907 中期回执（2026-09-07 执行包 P00–P28 · 本地交付待 GPT 接收）

> 依据 `docs/authority/taskpack-0906/DEEPSEEK-BULK-EXECUTION-2026-09-07.md`。执行到当前资源阈值点做
> **中期交接**：未 commit/push/merge/Release/Green；E 盘未访问；未读私密 `.hermes`/凭据/五库内容；未删未移资产。
> 唯一回执继续使用本文件；交接入口 `DEEPSEEK-R2-HANDOFF.md` 同步更新摘要。

### 每卡状态

| 卡 | 状态 | 证据 / 说明 |
|---|---|---|
| P00 | DONE | `baseline.json`+`worklist.json`（run `c1f8ef067627`）；资源根/environment/TASKS 冻结哈希核实 |
| P01 | DONE | R08→PARTIAL、DOCX=`_docx_text` stdlib、按轮文件计数、回滚=按差异、`test_quality_regressions` 补齐 |
| P02 | DONE | `scripts/maintenance/bulk_evidence.py`+测试（10 passed，run `3b9e03fd78cc`）；真实 PASS+FAIL 回执（run `47e0f3844721`） |
| P03 | DONE | `scripts/maintenance/bulk_fixture_factory.py`+测试（7 passed，run `0ad5968fc59c`） |
| P04 | DONE | `scripts/maintenance/bulk_link_audit.py`+测试（6 passed，run `cb11847c1c8b`）；全 371 tracked md 审计 run `b9b8c96605a7`（MISSING_PATH=0） |
| P05 | DONE | `ownership-audit.json`（run `550dc677f978`）：1498 tracked 归类；异常候选 HERMES_REF231/TEMP_REF2/ABS47 |
| P06 | **PARTIAL** | `p06-summary.json`+`p06-roster.json`（1246 项，24 语义行含 20 R3+4 本轮真读；1222 项 NOT_INDIVIDUALLY_READ 机械态）；阻塞：后台 worker 在本部署无文件读取工具 + 主会话上下文上限，见 p06-summary.json |
| P07 | DONE（既有证据汇聚，非新调研/非 UI 重设计） | `p07-capability-ui-evidence.json`（4 项目组 DeepTutor/Obsidian-Assistance 等 + 吸收代码/边界/许可未知分列；UI/LOGO 复用 ds03+R08；gap 明列） |
| P08 | DONE | `tests/workers/test_bulk_text.py`（9 passed） |
| P09 | DONE | `tests/workers/test_bulk_structured.py`（12 passed）+ worker_canvas 锚点越界最小修复（四文件准入；回归见 P22） |
| P10 | DONE | `tests/workers/test_bulk_office.py`（6 passed） |
| P11 | DONE | `tests/workers/test_bulk_pdf.py`（4 passed，run `55ab0b019d54`；合成文本/旋转/图页 scanned/损坏 PDF 真实失败；CJK 依赖说明已注） |
| P12 | DONE | `tests/workers/test_bulk_html.py`（8 passed，真实快照 sample-page.html） |
| P13 | DONE（eng 小样；chi_sim/低清/表格组待 GPT） | `tests/workers/test_bulk_ocr.py`（4 passed run `31df19c4e911` 需 `TESSDATA_PREFIX=…10-toolchains\scoop\persist\tesseract\tessdata`；无该 env 时 4 skipped 非假过）；真实环境 TESSDATA_PREFIX 陈旧已登记为 R08/环境缺口 |
| P14 | **PARTIAL** | `tests/workers/test_bulk_media.py`（2 passed，run `2916cf358e73`；ffmpeg/ffprobe 工具链 lane + ≤30s 静音 wav 生成/时长/哈希）；ASR 转写执行组 BLOCKED（未授权项目 model profile 调用；字幕/元信息组由 P03/P09 覆盖） |
| P15 | DONE | `tests/workers/test_bulk_quality.py`（8 passed） |
| P16 | DONE | `tests/contract/test_bulk_schema_matrix.py`（4 passed，run `d5cafb031533`；hello/request schema 级单字段负例补齐，9 schema 覆盖状态显式声明）+ `p16-schema-coverage.json`（复用指针审计） |
| P17 | DONE | `tests/workers/test_bulk_transport.py`（5 passed） |
| P18 | DONE | `tests/workers/test_bulk_legacy_adapters.py`（9 passed） |
| P19 | DONE | `tests/fixtures/vnext/business/`（6 逻辑样例+manifest，哈希钉定）+ `tests/contract/test_bulk_business_fixtures.py`（6 passed，run `52e932c1336e`） |
| P20 | DONE（仅复核清单，零删除） | `p20-cleanup-candidates.json`（复用 ds09/R07/P05；deletion_authorization=NOT_REQUESTED，released_bytes=0，禁清理清单含五库/资料库/.hermes/runs/d-All-projects） |
| P21 | DONE | `p21-gate-inventory.json`（只读工作流/门禁映射） |
| P22 | DONE（定向） | **211 passed / 10 warnings / 124 subtests**（run `c45300e2b1fd`，含 P11/P13(eng)/P14(media lane) 后终值）；vocab drift pass（run `3958f7a5b1ea`）；Ruff 新文件全过；`git diff --check` exit 0 |
| P23 | **NOT DONE** | 全量穷尽审计与最终收口未执行（等待剩余卡/授权资源） |
| P24 | **PARTIAL** | LANGUAGE/RUNTIME 索引补 SHARED_RESOURCE_PATH_INDEX 指针（事实链接，无新规则）；五索引 80 链接全 PRESENT（73+7，audit）；待续：更深的过期条目收敛与 Historical 分类登记 |
| P25 | READY | 未执行（历史文档分类/只读归档，后续） |
| P26 | READY | 未执行（重复文档收敛，后续） |
| P27 | DONE（复用工具） | 以 `bulk_link_audit.py` 对五权威索引定向审计（80 链接全 PRESENT） |
| P28 | READY | 未执行（物理删除候选隔离终表，后续） |

### 本轮新增/改动路径与验证

- 新增工具：`scripts/maintenance/bulk_evidence.py`、`bulk_fixture_factory.py`、`bulk_link_audit.py`（均带同名测试）。
- 新增测试：`tests/maintenance/test_bulk_{evidence,fixture_factory,link_audit}.py`；
  `tests/workers/test_bulk_{text,structured,office,html,quality,transport,legacy_adapters}.py`。
- 生产修改（四文件准入内，最小局部）：`services/python-workers/document/worker_canvas.py` 锚点按最终投影文本重算
  （修复末节点 char_end 越界；接口不变、无新依赖；P22 聚合回归 191 passed 通过）。
- 更新回执/交接：`DEEPSEEK-RESULTS.md`（本段）、`DEEPSEEK-R2-HANDOFF.md`（摘要更新）。
- 全部派生证据在 dev.py run 目录（`c1f8ef067627` 及本段列出的各 run id），未覆盖旧 ds01–ds09。

### 留给 GPT 的精确接续

1. P06 剩余 1222 项逐项真读（本部署后台 worker 无文件工具；需主会话分批复读或 GPT 侧工具）。
2. P07/P11/P13/P14/P16/P19/P20/P24–P28 未执行清单见上表；P13/P14 需本地 OCR/媒体小样与安全运行入口确认。
3. P23 最终穷尽审计与统一回交尚未做（本段为中期交接，非 P23 收口）。
4. worker_canvas 局部修复与全部新增文件在 P22 已聚合验证；回滚=撤销本段列出的新增/修改文件。

---

## 上传交接（用户 2026-09-07 指令：做好交接、摘要、上传、双端仓库一致）

按用户指令执行上传交接：将本工作树整体提交到工作分支 `codex/full-loop-0906` 并推送远端，使本地/远端一致；
`main` 与 `origin/main` 保持 `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e` 不动；不合并、不发 tag/Release、不改版本号。
本段写于提交前，实际 commit SHA 以推送后 Git 历史 readback 为准；双端一致核验见最终汇报。
