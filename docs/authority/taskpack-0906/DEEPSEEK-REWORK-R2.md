# ArcheAxis · DeepSeek 第二轮返修任务包（DP-R2）

> 可直接完整发送给 DeepSeek。只执行本包 R01—R09，不从头重跑旧 DS01—DS15，不进入高难度生产开发。
> 如有 Superpowers，使用 executing-plans 逐卡执行；否则依本文步骤执行，无需安装全局技能。

**目标：** 保留第一轮有价值的测试，修正独立预期、负例隔离、证据分级和历史链接，交付可审查的低风险补丁。
**架构：** C#/Avalonia 正式桌面、Rust 独立 vNext 数据库、Python worker 计算；本轮不改任何生产实现或架构。
**技术：** Windows / PowerShell 7 / 项目 Python / pytest / jsonschema / Ruff。
**规范：** 原 `docs/authority/taskpack-0906/TASKS.json` 与 `DEEPSEEK-TASKS.md`；本包只修正第一轮验收缺口，不减少 T00—T20 原始范围。

## 一、现场、依据与真实状态

仓库：`D:\All projects\ArcheAxis-Knowledge-OS`，工作分支 `codex/full-loop-0906`。
接手快照 HEAD：`2948b155db069d608e7ebd8acb7956079d8cf69f`；main 快照 `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`。必须重查，不 reset 到快照。

第一轮现有未提交内容：

- DeepSeek：修改 `tests/workers/test_text_ndjson.py`、`tests/workers/test_quality_regressions.py`；新增 `tests/workers/test_document_fixture_matrix.py`、`tests/contract/test_deepseek_contract_cases.py`、`tests/fixtures/vnext/documents/canvas-zh-group.canvas`、`tests/fixtures/vnext/documents/sample-overlap.srt`；新增 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md`。合计 **6 个测试/样例文件 + 1 个结果文件**。
- GPT：修改 `HANDOFF.md`，新增 `DEEPSEEK-TASKS.md`、`GPT-HARD-TASKS.md`，以及本 `DEEPSEEK-REWORK-R2.md`。均保留，不覆盖、不纳入 DeepSeek 自己的功能修改。
- 没有 commit/push/merge；未发布、未修改 Green。本包也不授权这些动作。

GPT 接收审查证据：

- 实际重跑第一轮定向测试：**88 passed、106 subtests passed、0 fail、0 skip、6 warnings**；run `.project-local/runs/be268a2d33/04b9af6216ff`，19.11 秒。这是当前脏工作树的局部测试，不是精确 SHA CI 或安装态资格。
- 合同正例现场检查：worker 与 anchor 基础样例本身合法，run `a22cef9cc235`。问题不是它们全部“假通过”，而是坏 SHA 用例同时破坏 URI，无法单独约束哈希校验。
- Ruff：run `4989e67a0124` 有 5 项。新增 `test_deepseek_contract_cases.py:14` 的 F401 属第一轮；另 4 项位于原有代码（I001、SIM117×2、UP012），不得全归责给 DeepSeek。
- 16 处链接目标确实不存在，8 个去重后的正确目标都已核实存在。
- `d/All projects` 并非空目录，下面已有 `Cognitive-Loop-OS/.hermes` 子目录。只核验了这几级的元数据，未读取其私密内容。
- DS02 的 20 行仍是 `head-read` / `head-read+callers`，capability 为空、risk 未评估、测试未核验，不能称完成原来的语义核对任务。
- DS03 关键词命中不证明交互可用，zoom=0 只表示扫描没找到相应证据，不证明软件没有缩放能力。
- DS09 将 `.project-local/runs` 等整体列为可重建缓存缺少依据；其中包括本轮证据，不得据此删除。

## 二、硬边界与修改白名单

禁止访问 E 盘；禁止读凭据、`.env`、浏览器数据、私人记忆和代理会话。禁止进入上述误生成目录的 `.hermes` 内容，禁止改权限或借链接跨域。
禁止删除/移动任何目录、缓存、模型、资料、用户资产；不下载模型、不安装软件、不改全局配置、不弹终端/GUI、不执行新版本构建或全量 CI。
禁止改生产实现、schema、生成器、Rust、C#、数据库、锁文件、CI 策略、`AGENTS.md`、根契约、冻结 TASKS.json。生产失败保留测试并回交 GPT。

本轮只允许修改：

1. 第一轮四个测试 Python 文件及其两个 fixture（仅确需修正时）。
2. `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md`，追加 R2 回执并修正当前总结；历史证据原值保留。
3. R02 指定的五份文档，仅替换列明的 16 个链接目标，其他字节/内容尽量不动。
4. 经 `scripts/runtime/dev.py` 创建的本轮 ignored run 目录中的派生证据/检查脚本；不覆盖旧 ds01—ds09 的证据文件，不新增顶层 `runs/dsXX`。

一 checkout 一个 writer。发现新的未知修改或其他执行者正在写同一文件，停止重叠卡，其余独立只读卡可继续。工作区当前不是干净基线，禁止 `git add .`、restore、reset、clean。

## 三、统一执行入口

上次现场实际 PowerShell 7 路径是 `C:\Users\ALEX\AppData\Local\Microsoft\PowerShell\7\pwsh.exe`；旧文档里的 Program Files 路径未通过现场存在性检查。重新定位实际 pwsh，不切回 5.1，也不自动安装。

在 PowerShell 7 中：

```powershell
Set-Location -LiteralPath 'D:\All projects\ArcheAxis-Knowledge-OS'
git status --short
git branch --show-current
git rev-parse HEAD
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$dpPython = 'D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe'
& $dpPython -B scripts/runtime/dev.py -- $dpPython -c 'import sys,pytest,jsonschema; print(sys.executable); print(sys.version)'
```

这些环境变量仅限执行进程，不修改系统配置。工具库 `D:\All projects\OS External Configuration\10-toolchains`、模型库 `D:\All projects\Model library`、资料副本 `D:\All projects\ceshi` 保持原位；本轮不需要扫描它们。
本仓库没有 `scripts/workflow/execution_preflight.py`，不要复制通用模板调用不存在的文件。标准规范检查是 `scripts/check_repository_conventions.py`。
如新建本轮证据脚本，用编辑工具写在项目 ignored 目录，通过 dev.py 执行；脚本所有输出使用它接到的 `ARCHEAXIS_RUN_ROOT`，不手写用户 TEMP。

## R01 · 修正结果分级与回执准确性

- [ ] 在 `DEEPSEEK-RESULTS.md` 追加“R2 接收审查纠偏”；保留第一轮测试实测数字，不篡改历史结果。
- [ ] 当前结论中 DS02 改为 PARTIAL，直到 R03 补足；DS03 标结构/关键词候选证据，非运行验收；DS09 标 PARTIAL，未完成保全/重建证明。
- [ ] DS04/DS08 写明已通过测试但新增覆盖尚待 R04/R05 加固；不要写成生产已失败。
- [ ] 将第一轮“6 文件”表述统一为“6 测试/样例 + 1 回执”；不把 GPT 文件计入自己的修改。
- [ ] 对“`.hermes` 只读未新写（一处误写已删）”的矛盾，依据已有可公开执行记录填写确切路径、操作、结果；证据不足标 UNVERIFIED，不为找证据读取私密 `.hermes` 内容或日志。不得继续宣称从未写入。
- 验收：事实、计划、当前测试、未测、推送/CI/安装态分别列出，无相互矛盾的“全部完成”。

## R02 · 精确修复 16 个历史文档链接，不搬文件

只改下表列出的链接目标字符串，保留历史正文、结论、日期和原测试 SHA。不全仓替换。

| 源文件（相对仓库根） | 原目标 | 正确目标 | 预计数量 |
| --- | --- | --- | --- |
| `docs/architecture/imported-designs/inspiration-research-root/01_DO_NOT_REPEAT.md` | `../00_铁律.md`、`../01_DO_NOT_REPEAT.md`、`../02_LESSONS_LEARNED.md`、`../03_ENV_KNOWN_ISSUES.md` | 分别移除开头 `../`，指向同目录对应文件 | 4 |
| `docs/architecture/imported-designs/inspiration-research-root/02_LESSONS_LEARNED.md` | 同上四个目标 | 同上 | 4 |
| `docs/architecture/imported-designs/inspiration-research-root/03_ENV_KNOWN_ISSUES.md` | 同上四个目标 | 同上 | 4 |
| `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/README.md` | `../../../FUTURE_EXECUTION_BLUEPRINT.md` | `../../../../FUTURE_EXECUTION_BLUEPRINT.md` | 1 |
| `docs/truth/H0_H1_STATUS_HANDOFF.md` | `../../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md` | `../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md` | 1 |
| `docs/truth/H0_H1_STATUS_HANDOFF.md` | `../../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md` | `../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md` | 1 |
| `docs/truth/H0_H1_STATUS_HANDOFF.md` | `../../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md` | `../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md` | 1 |

- [ ] 先从旧 `.project-local/runs/ds01/ds01-links.json` 读这 16 行，与当前源文件逐行比对；不一致的行单独报告，不强行替换。
- [ ] 从每个文档所在目录解析新目标，确认文件存在且没有跨出仓库，再应用精确补丁。
- [ ] 重扫这五份文档；输出新的链接回执，不覆盖旧报告。保留“扫描范围只有这五份”的限定。
- 验收：16 处目标可解析，diff 只含这些链接修正；不能凭本卡说全仓所有链接已正确。

## R03 · 补完 20 项旧资产的最低语义审阅（不做架构迁移）

输入仍是 `.project-local/runs/ds02/ds02-reuse.jsonl` 的原 20 项，不扩大资产数来代替深度。

- [ ] 每项读实际函数体、至少一个现有调用方及相关测试；空 `__init__` 可标 EMPTY_MODULE，不要求虚构能力。
- [ ] 能力用可观察行为描述，填写函数/行、输入输出、现有测试符号与断言内容、风险依据。不要仅按导入名猜实现。
- [ ] 读到的事实与 GPT 待裁决分列：`capability_observed`、`implementation_symbols`、`callers_verified`、`tests_read`、`tests_run`、`risk_observed`、`target_proposal`、`gpt_decision_needed`、`review_scope`。
- [ ] 可以建议 Rust 领域/存储或 Python 计算适配目标，但不得修改代码/权威清单；目标未批准不妨碍完成事实核查。
- [ ] 一个文件太大可按函数切片并列明确未审范围；不能以函数切片声称全文件已审。能力/测试找不到写 NOT_FOUND 与搜索范围，不写假完成。
- 验收：20 项每项有实际语义证据或明确不适用原因，未知项单列；不得仍全部 `capability=null` 然后宣称完成。新明细保存本轮 run 目录。

## R04 · 文本锚点与坏编码使用独立精确预期

文件：`tests/workers/test_text_ndjson.py`。保留第一轮真实子进程测试结构，不改 production worker。

- [ ] 为新增表格增加独立预期锚点，逐条断言 `kind/path/char_start/char_end`，不要从输出 text 调用生产算法计算“期望”。
- [ ] 以下常量按 Unicode 字符而非 UTF-8 字节计数；可直接作为用例预期：

```python
expected_ranges = {
    "ascii": [(0, 5)],
    "chinese": [(0, 2)],
    "nfd_combining_preserved": [(0, 3)],
    "astral_emoji": [(0, 1)],
    "utf8_bom_stripped": [(0, 2)],
    "utf16le_bom": [(0, 2)],
    "crlf_and_lone_cr_preserved": [(0, 3), (3, 5), (5, 7)],
    "empty_file": [],
    "gbk_fallback": [(0, 2)],
    "invalid_bytes_replaced": [(0, 3)],
}
# 原输入 b"\x81\xff\x81" 的 UTF-8 replacement 解码预期：三个 U+FFFD。
expected_invalid_text = b"\xef\xbf\xbd" * 3
```

- [ ] 用手写范围生成结构字典，列表顺序和 `line-1` 等 path 必须一致：

```python
expected_structure = [
    {"kind": "line", "path": [f"line-{i}"], "char_start": start, "char_end": end}
    for i, (start, end) in enumerate(expected_ranges[name], start=1)
]
self.assertEqual(structure, expected_structure)
```

- [ ] 坏编码分支从“非空且不同原文”改成精确字节；断言其 `losses` / `loss_note` 明确记录 U+FFFD。BOM、GBK 和正常 UTF-8 按现有 worker 定义区分，不发明新的解码政策。
- [ ] 5000 行截断已有旧实测用例，保留即可，不重复创建第二个同样大案例。
- [ ] 加一个测试断言的负控制：对预期结构副本将 `char_end` 偏移 1，确认比较失败。只改变测试内副本，不修改生产/fixture 伪造缺陷。
- 验收：坏坐标不能靠 loss/structure 同步错误而通过；精确文本/坐标正确；新增用例可能直接 PASS，这是覆盖加固，不声称已修产品 bug。

## R05 · 合同负例单字段化，证明 SHA 校验真正被测到

文件：`tests/contract/test_deepseek_contract_cases.py`。不改 schema、生成器或跨语言生产代码。

- [ ] 对 worker/job/anchor 等负例先断言各自合法基础样例通过；保留已经正确的其他合同案例。
- [ ] 将当前坏 URI + 坏 SHA 的组合拆成两个独立负例。示例使用现有 `_errors` 与 `WORKER_RESPONSE`：

```python
from copy import deepcopy

asset = {
    "kind": "text", "uri": "job://output/" + "a" * 64,
    "sha256": "a" * 64, "media_type": "text/plain", "byte_length": 1,
    "schema": "archeaxis.text/v1", "authority_effect": "candidate_or_measurement_only",
}
valid = {**WORKER_RESPONSE, "outputs": [asset]}
assert not _errors("worker-protocol.schema.json", valid)
bad_hash = deepcopy(valid)
bad_hash["outputs"][0]["sha256"] = "zzz"
assert _errors("worker-protocol.schema.json", bad_hash)
bad_uri = deepcopy(valid)
bad_uri["outputs"][0]["uri"] = "job://output/zzz"
assert _errors("worker-protocol.schema.json", bad_uri)
```

- [ ] 检查 validation error 的嵌套 context，确认哈希 case 命中 outputs/0/sha256 的 pattern，而不是无关 required/字段错误。
- [ ] 加内存负控制：deepcopy 加载的 worker schema，只移除 `$defs.response.properties.outputs.items.properties.sha256.pattern`；用同一合法 URI + 坏 SHA 验证，此时应被接受。这证明测试能检测校验被移除。绝不写回 schema 文件。
- [ ] 修正文件开头“measured-null coupling 为 runtime-only”的过时注释，现有测试已证明 schema 强制该约束；不要改正确 schema 去配合注释。
- [ ] 删除新增未使用的 `import pytest`（若用于新增断言则保留且实际使用），消除本批 F401。
- 验收：正例通过；每个负例只破坏一个关注点；schema 弱化负控制在内存完成；其他既有合同测试不回退。

## R06 · 测试临时文件 fail-closed 与轻量静态检查

文件：`tests/workers/test_document_fixture_matrix.py`。
当前 `_write` 使用 `tempfile.mkstemp(dir=os.environ.get("ARCHEAXIS_RUN_ROOT"))`，缺环境变量会回落系统 TEMP，而且没有逐例清理。正常 dev.py 运行没越界，不等于缺环境也安全。

- [ ] 为两个 TestCase 增加如下 setUp，改两处 `_write` 的 `dir=self.tmp.name`：

```python
def setUp(self):
    self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
    self.addCleanup(self.tmp.cleanup)
```

- [ ] 无 `ARCHEAXIS_RUN_ROOT` 时必须在创建临时文件前抛错；在隔离子环境测试此负例，不删除整个父进程环境、不调用真实系统 TEMP 写入。
- [ ] 执行新增文件的 Ruff；两个已有修改文件中的原始 I001/SIM117/UP012 只报告为 baseline，禁止全文件 `--fix`/格式化造成噪音。
- 验收：新文件 Ruff 无新增问题，正常矩阵通过、逐例临时文件清理；无 launcher 环境时无任务文件外溢。

## R07 · 缓存分类纠偏与目录保留裁决

只修 `DEEPSEEK-RESULTS.md` 和生成新的受限分类证据，不再全量扫磁盘，不删任何目录。

- [ ] `.project-local/runs` 是运行证据混合区，不能整体标 disposable cache；`.venv`/模型依赖/打包目录也不能仅因名字断言可重建。
- [ ] 分类采用 PRESERVE_EVIDENCE、REBUILD_CANDIDATE、SOURCE_OR_UNIQUE、UNKNOWN；候选没有 lock/tool/version/代表性重建证明，`rebuild_verified=false`。
- [ ] 旧 25,457,767,687 logical bytes 保留为当时受限观测；不写成仓库总量、物理占用或释放量。4 个错误、reparse=2、未测 allocated/file identity 保留。
- [ ] 将 `d/All projects` 改为“存在子目录、所有权/内容未完成核验，保留”，不要声称空目录可删。禁止读取其 `.hermes` 内容追索所有权。
- 验收：每项允许证据范围和未知原因清楚；无删除/搬移/权限变更；不把整改文档写成瘦身完成。

## R08 · DS03 / DS06 可复现证据补充，避免扫描冒充验收

输入：旧 `ds03-design-assets.json`、`ds06-format-cases.json`；不覆盖原文件，只产生本轮派生台账。

- [ ] DS03：将关键词命中标为 SEARCH_HIT，将 zoom=0 标 NO_MATCH_IN_SCANNED_SCOPE；给出扫描范围、排除范围与原命令，不据此断言 UI 可用或缺失功能。
- [ ] DS06：为 7 个格式条目补 fixture 相对路径、输入哈希、真实执行命令、解释器/引擎版本、输出定位/哈希、断言边界。已有证据不足则标 EVIDENCE_INCOMPLETE，不重新填写猜测值。
- [ ] 可复用已存在且可核实的非私密执行证据；若需重跑，先检查依赖、只跑缺证据单例，经 dev.py；不装浏览器/模型，不跑网络/真实账号，也不拓展到媒体全链。
- [ ] 将“金标子串命中”写成 substring_asserted，不能当全文/版式/覆盖准确率。pdf/asr/html 的 unmeasured 保持，不强行升格。
- 验收：接收者可找到同一 fixture 并复跑；所有非完整精度结论有范围标签；这只是局部探针/worker 证据，不是 Core/桌面集成通过。

## R09 · 合并定向回归与一份 R2 回执

每卡开发只跑对应文件，最后合并定向测试一次；不人为凑 88，新增案例导致计数变化须解释。

```powershell
& $dpPython -B scripts/runtime/dev.py --pytest -- tests/workers/test_text_ndjson.py tests/workers/test_document_fixture_matrix.py tests/workers/test_quality_regressions.py tests/contract -q
& $dpPython -B scripts/runtime/dev.py -- $dpPython scripts/contracts/generate_vocabulary.py --check
& $dpPython -B scripts/runtime/dev.py -- $dpPython -m ruff check tests/workers/test_document_fixture_matrix.py tests/contract/test_deepseek_contract_cases.py
& $dpPython -B scripts/runtime/dev.py -- $dpPython scripts/check_repository_conventions.py --source worktree
git diff --check
git diff --stat
git status --short
```

逐命令记录 exit code；不要用最后 git status 成功掩盖之前 Ruff/测试失败。另检查两个旧测试文件的 Ruff，将存量和新增问题分别列出，不声称全绿。

- [ ] R2 证据全部位于 dev.py 分配的运行根，清单列路径/哈希/run ID/原始命令；不读取无关任务日志。
- [ ] 规范扫描可能不覆盖所有 untracked 内容，新增文件必须逐一核验，不能只依赖 `git diff --check`。
- [ ] 在唯一 `DEEPSEEK-RESULTS.md` 追加 R01—R09 的验收表：PASS/PARTIAL/FAIL/BLOCKED、改动路径、精确命令、exit code、run ID、独立预期、未满足项、回滚边界。
- [ ] 不提交、不推送、不合并，不改产品版本。告诉用户“本地返修待 GPT 接收”，不要写“全部项目完成”。

## 四、执行顺序与交回条件

R01 → R04/R05/R06（测试返修）→ R02（精确链接）→ R03（20 项事实核对）→ R07/R08 → R09。
测试返修、资料审阅按批次推进，不需要重新全盘调研。遇到生产缺陷保留最小失败例、标明所属 GPT 高难度卡，继续其他独立卡。

旧 DS11—DS15 仍未放行：worker 协议/资源与集成、正式 UI 架构/设计、真实迁移、权限与双侧状态机、候选资格均留 GPT。本包没有给这些任务制造假接口或假完成条件。
完成 R2 后，直接将 `DEEPSEEK-RESULTS.md` 的 R2 段及实际 diff 交回；无需为了等 GPT 而另建新版本、新权威索引或下一轮任务包。
