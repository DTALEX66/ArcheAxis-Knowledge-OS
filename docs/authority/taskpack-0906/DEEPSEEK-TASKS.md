# ArcheAxis：交给 DeepSeek 的批量低风险任务包

> 本文件可直接完整交给 DeepSeek。不需要历史聊天即可理解任务边界。
> 这是执行交接，不是已完成证明。用户授权本次拆分任务；不得借文档扩大删除、发布、真实数据迁移权限。
> 如执行环境提供 Superpowers，按 executing-plans 分批实施；没有该技能也按本文核验流程执行，不安装全局组件来凑流程。

**目标：** 承担数量较多、边界明确、可独立验证的测试、资产核对、文档修正和局部适配工作，将架构与高风险修改交回 GPT。
**架构：** 正式桌面 C#/Avalonia，Rust Core 独立 vNext 数据库，Python worker 负责计算。旧 React/Tauri/Python 是复用与恢复来源，不是第二套正式前端。
**技术：** Windows、PowerShell 7、现有 .NET/Rust/Python 工具链；不重新选择语言或发布新产品版本。
**原规范：** 仓库 `docs/authority/taskpack-0906/TASKS.json`，2026-09-06-r1，T00—T20 共 21 项。本包只分配其中的子任务，不替代原验收要求。

## 1. 项目与现场

- 源码仓库：`D:\All projects\ArcheAxis-Knowledge-OS`。不是 WORK-LAB。
- 起始工作分支：`codex/full-loop-0906`。
- 已上传交接基线：`2948b155db069d608e7ebd8acb7956079d8cf69f`。
- 源码测试基线：`b5a0840a926b826d249ef2a8c4e320ad6436fcca`，tree `c6a30d98c8f4f7ba6377d7ccc08a9cd50b01697e`。
- 上次 fetch：本地/远端工作分支一致；本地/远端 main 为 `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`；工作分支领先 main 9 个提交，未合并。接手时必须重查，不能依赖快照。
- 源码 SHA 的 CI 已成功：https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/34024333839 。不是未来修改或完整产品资格证明。
- 原任务包：`D:\All projects\ARCHEAXIS-UPDATED-FULL-LOOP-TASKPACK-2026-09-06.zip`；冻结 TASKS.json SHA-256 为 `1aa5c17c94f8c279987b5f4c70777e25d3614b6419fda65fd351abf71ff6bc94`。不要修改冻结任务来降低门槛。
- 本任务包文档可能作为上述基线后的未提交文档出现。先登记为已有交接，不覆盖、不静默合入自己的功能修改。

工具与数据位置：

| 用途 | 路径与约束 |
| --- | --- |
| Shell | `C:\Program Files\PowerShell\7\pwsh.exe`；不要用 PowerShell 5.1 替代 |
| Python | `D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe`；先确认实际依赖 |
| 工具共用库 | `D:\All projects\OS External Configuration\10-toolchains`；复用现有 Cargo/Rustup/MSVC/.NET，不在仓库下载多份 |
| .NET | `D:\All projects\OS External Configuration\10-toolchains\dotnet\dotnet.exe` |
| 模型共用库 | `D:\All projects\Model library`；只消费现有配置明确的模型，不改库、不重复下载权重 |
| 资料副本 | `D:\All projects\ceshi`；仅在用户授权范围内读取，禁止改写和上传资料内容 |
| 开发产物 | 经 `scripts/runtime/dev.py` 写入 ignored `.project-local/`；不写用户目录、桌面或系统 TEMP |
| 现有绿色版 | `D:\All projects\ArcheAxis.Knowledge.Green-x64` v0.6.14；保留，不覆盖、不清理、不拿它当测试目录 |

## 2. 已经完成什么，不要重做

已存在并有局部实测：原件 CAS 保留、单 writer/跨进程锁、数据库版本保护、事务/归档恢复；真实文本 NDJSON worker；Rust 校验输出哈希与损失回执后持久化；C# 私有启动管道和 HTTP 鉴权；持久 claim 后 202、结果读回、幂等、取消、两个活跃 worker 上限；队列满载不丢已接受任务。

本地证据位于 `.project-local/runs/be268a2d33/`：Rust 聚合 `1947625d8f22`、HTTP runtime `7664b552a9fc`、C# 静默实链 `03d6b700515a`、合同测试 `d9024ec5cfa9`、架构 `93cc316ebf75`。原始日志不上传；报告结果不等于重新执行了这些测试。

没有完成：完整多格式链、真正可用的 Avalonia 工作台、研究/知识/人类学习/机器反馈闭环、非空迁移、全面目录规范化与瘦身、安装态全链路资格。Avalonia 仍有初始内容，不能给用户展示为完成品。

## 3. 强制边界

1. 不访问 E 盘；不读凭据、`.env`、私有代理目录、浏览器数据、会话数据库或私人记忆。不为确认模型可用性打印密钥。
2. 不修改 `AGENTS.md`、根契约/目录权威、冻结 TASKS.json、生产协议 schema、生成器、Rust 存储/执行器、CoreSupervisor、依赖锁或 CI 安全策略。需要改这些，提交证据给 GPT。
3. 不删除/搬移用户资产，不整体清理 `.hermes` 或 `.project-local`，不改权限、不杀共享进程、不 reset/clean/force-push。
4. 不发布新版本、tag、Release，不合并 main，不替换 Green。提交、推送等动作以用户在你的执行环境中的明确授权为准；本任务包默认交付本地修改与报告。
5. 一 checkout 一个 writer。GPT 当前已停工；确认无人写才可接手。若并行，使用独立 worktree，不能共享修改主 checkout。保留 `.project-local/worktrees/worker-quality-0906` 中的旧修改，不复用或清理它。
6. 一次只执行一个小批次。先读代码/样例，扩充测试，再修已经复现且确属本卡范围的问题。若牵涉业务语义、资源安全或多模块契约，停止该卡并继续其他独立卡。
7. 不把 fixtures、配置名、文件头抽样、静态检查、SKIP 或没有抛异常，解释为真实能力已通过。
8. 用户要求黑白明暗主题；不擅自更换为绿色/蓝色主主题，不重画品牌、不增第二套 UI。测试尽量静默；不弹命令行窗口。

## 4. 起步与测试命令

在 PowerShell 7 中执行以下已核实入口。工作目录须为本次 owning checkout；若是独立 worktree，替换 Set-Location，不把测试误跑回主库。

```powershell
Set-Location -LiteralPath 'D:\All projects\ArcheAxis-Knowledge-OS'
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
Get-Content -LiteralPath 'AGENTS.md'
$aakPython = 'D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe'
& $aakPython -B scripts/runtime/dev.py -- $aakPython -c 'import sys, pytest, jsonschema; print(sys.executable); print(sys.version)'
& $aakPython -B scripts/runtime/dev.py --pytest -- tests/workers -q
& $aakPython -B scripts/runtime/dev.py --pytest -- tests/contract -q
& $aakPython -B scripts/runtime/dev.py -- $aakPython scripts/check_repository_conventions.py --source worktree
```

按所改 owning module 缩小测试文件，不每张任务卡跑全量。命令失败立即记录 exit code、run ID 和错误层；环境缺失是 ENVIRONMENT_FAIL，不自动换全局 Python。本仓库未找到 `scripts/workflow/execution_preflight.py`；不要照抄通用指令调用不存在的脚本。规范检查真实路径为 `scripts/check_repository_conventions.py`，不是 `scripts/ci/check_repository_conventions.py`。

先读取配置权威入口：`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`、`docs/DIRECTORY_AUTHORITY_INDEX.md`。只读所需文件，不扫描私密旧运行目录。原 TASKS.json 中 planned 表示冻结计划，真实进度看 EXECUTION.md；两者不可互相改写。

## 5. 可立即开始的低风险批次

以下每卡中的文件为已有输入或明确拟新增输出；新增路径不存在是正常的，代码符号必须从实际文件核实。统一回执追加到拟新增 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md`。大清单/日志/语料只存 ignored 运行目录，在回执引用其相对路径和哈希。

### DS01：现有入口与坏链接清单（T00/T14/T19）

- [ ] 从 `git ls-files` 枚举 tracked 文档/脚本，排除凭据与私密路径；读取三份配置/语言/目录索引及其直接引用。
- [ ] 按文档所在目录解析相对链接；区分缺目标、锚点、历史路径、外部地址、大小写和 URL 编码，不从仓库根错误拼接。
- [ ] 将每项写成 source、line、target、是否当前入口、证据、拟修复；输出运行目录下 `ds01-links.json`。
- [ ] 仅可修 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md` 中自己的链接；其他文档给出明确补丁建议供 GPT 集成，不能批量替换旧历史。
- 验收：构造目录嵌套下正确/错误相对链接各一例，证明扫描不会把正常链接误判；报告总检查数和排除数，不宣称全盘规范化完成。

### DS02：旧能力、调研与复用证据表（T17/T13）

- 输入：`LEGACY_MANIFEST.yaml`、`docs/authority/legacy/`、tracked 旧代码/测试；包含 OpenHuman、DeepTutor 及已有其他调研能力，不能仅找这两个名字。
- [ ] 以原清单为起点，每批 20 项读实际实现、调用方、测试，登记 Git 对象/路径/符号、能力、风险、新端目标、缺口。
- [ ] 区分“有文档”“有旧实现”“新链已调用且有证据”；测试缺失必须显式标记。未读正文不能计作语义审查。
- [ ] 生成运行目录下 `ds02-reuse.jsonl`，回执列出本批真正审过的项数及 GPT 待裁决项。
- 验收：每行可回溯来源与当前消费者；不复制整库、不删除旧代码、不擅自把未吸收能力标完成。

### DS03：已有设计、LOGO、界面状态素材整理（T18）

- 输入：tracked `docs/design/`、旧 `frontend/`、现有 `apps/ArcheAxis.Desktop/Assets/` 和相关已入库设计文档；只读取非私密项目资产。
- [ ] 每批登记素材哈希、许可/来源状态、主题、页面、交互状态、现有消费者；未找到的历史 GPT 设计写“未获得”，不补造。
- [ ] 列全加载、空态、失败、重试、取消、冲突、只读、不可用、键盘、缩放、减少动效场景及已有证据。
- [ ] 输出运行目录 `ds03-design-assets.json` 和回执；不重新设计、不修改正式 UI 或生成新 LOGO。
- 验收：同名文件按哈希区分；黑白主题作为用户约束保留；实际组件与效果图分别标记。GPT 据此做设计裁决。

### DS04：文本 worker 边界回归（T02/T05/T07）

- 输入：`services/python-workers/document/worker_text.py`、`tests/workers/test_text_ndjson.py`、`tests/workers/test_quality_regressions.py`。
- 允许：上述测试文件及小型非私密 fixture；生产实现仅在 GPT 明确回交局部修正卡后修改。
- [ ] 增补中文、组合字符、emoji、BOM、CRLF/LF、空文件、坏编码、截断的表驱动案例；先核对已有覆盖避免重复。
- [ ] 对原字节、解码文本、归一化、行锚、损失回执分别断言；不得把输出自身复制为期望值。
- [ ] 运行所改测试文件；真实产品失败保留失败案例并交 GPT，不能改期望/跳过消红。
- 验收：每案例有独立期望、保留/损失理由；原始指标与归一化指标分开。

### DS05：Canvas 与字幕解析案例扩充（T05）

- 输入：`services/python-workers/document/worker_canvas.py`、`worker_subtitles.py`；先读真实入口，不假定函数签名。
- 允许新增：`tests/workers/test_document_fixture_matrix.py`，小型 fixture 放原计划 `tests/fixtures/vnext/documents/`。
- [ ] Canvas 覆盖文本/文件节点、关系、中文、缺节点；字幕覆盖重叠时段、空轨、畸形时间、Unicode、无末尾换行。
- [ ] 在测试中调用现有真实 parser；明确断言结构、边界与失败，不只检查非空。
- [ ] 局部错字/确定性非语义 bug 可在这两个 worker 内修，须先有失败回归；需要改 schema、时间语义、覆盖算法或安全限制就升级 GPT。
- 验收：重复运行结果可比；破损输入不假成功；这是解析器测试，不是已接入 Core。

### DS06：Office、静态网页、截图与媒体样例账册（T05/T06）

- 输入：现有 `services/python-workers/document/worker_office.py`、`services/python-workers/web/`、`vision/`、`media/` 及已有授权 fixture。
- [ ] 枚举支持声明与实际引擎探针，记录测试能否启动；不因库已安装就标格式通过。
- [ ] 在本地授权语料中分层选样：表/嵌图/多栏/扫描与文本混排、网页快照、截图、音轨/字幕/关键帧；只记录许可和来源状态，不上传私有内容。
- [ ] 使用现有接口做最小只读试跑，产物经 dev.py；发现需要新浏览器、模型、外部网络权限或进程树支持则记录依赖，不自行扩装/升级。
- 验收：输出运行目录 `ds06-format-cases.json`，每条有输入哈希、场景、预期覆盖、探针/执行/质量三种独立状态。不得宣称“全格式支持”。

### DS07：质量指标独立复算与负例（T07）

- 输入：`services/python-workers/evaluation/`、`tests/workers/test_quality_regressions.py`、`tests/evaluation/`（先确认现有内容）。
- [ ] 补可手算 CER/WER 样例：完全相同、插入、删除、替换、空参考、错误数大于参考长度、中文与数字。
- [ ] 预期写明分子/分母和空参考定义；禁止将误差率强行夹到 1；对未定义边界请 GPT 裁决。
- [ ] 已有真实金标与自动生成候选严格分开；独立留出集不得混入开发调优。
- 允许：测试/fixture；公式、精度门槛、模型 profile 的语义变化交 GPT。
- 验收：每指标可从原预测与确认金标复算；未确认音频转写不得作为总体精度证明。

### DS08：跨语言合同用例补齐（T02）

- 输入：`packages/contracts/v1/`、`tests/contract/`、`scripts/contracts/generate_vocabulary.py`。
- 允许：新增 `tests/contract/test_deepseek_contract_cases.py` 及独立 fixture；不改权威 schema/生成代码。
- [ ] 在现有规范下扩充未知状态、错版本、字段缺失、哈希形状、坐标范围正反例；区分 schema 可检查与业务运行时才可检查。
- [ ] 使用真实 jsonschema validator，不做字符串包含断言；运行现有 vocabulary drift check。
- 验收：合法/非法样例被正确接受/拒绝；若现规范不能表达需求，报告协议缺口，不自行制定协议。

### DS09：缓存保全账目复核，绝不删除（T20）

- 输入：`scripts/maintenance/inventory_project.py` 和已有 T20 回执。先读其参数与边界，再按原允许范围运行 dry-run；不新增全盘扫描。
- [ ] 复核 bytes、单位、算术、错误路径；按可重建缓存/唯一资产/未知分别计量，不遍历 junction。
- [ ] 每候选列精确路径、owner、类型、引用、哈希证据、重建证据、回滚方式、授权状态。
- [ ] 大清单存 ignored 运行目录；回执保留 4 个旧路径错误是否仍存在，不能把无法读到当零字节。
- 验收：19,676,885,323 logical bytes 是旧受限盘点，不是仓库总量/释放量；不称已瘦身，不进行删除/移动。

### DS10：现有测试的批量执行与失败归属（T01/T15）

- [ ] 按 DS04—DS08 实际改动合并一次定向测试；先验证精确解释器和所需 imports。
- [ ] 对失败记录最小命令、exit code、run ID、来源 SHA、dirty 状态、环境/产品/样例问题类别；不反复盲跑全量。
- [ ] 将每个产品失败映射到 GPT 卡；若只是本卡新增测试自身语法/导入错误，可在本卡修复并重新运行。
- 验收：测试数量、PASS/FAIL/SKIP/BLOCKED 可核对；已有历史通过不替代当前测试。此卡不能签发安装态资格。

## 6. 需 GPT 先提供契约/设计后才能开始的批次

### DS11：确定性适配器接线（T04/T05/T06）

前置：GPT 给出已冻结的 worker 输入/输出、错误分类、覆盖回执、资源限制及每个允许修改文件。随后按每格式一批，为现有 parser 增加薄包装和正反例；只能改被明确分派的 `services/python-workers/` 文件及对应测试。不得直接写数据库、复制另一套执行器或跳过输出校验。验收：真实 worker 通过协议验证；集成到 Core 与异常生命周期由 GPT 复核。不满足前置就继续 DS01—DS10，不假接口实现。

### DS12：已批准 Avalonia 组件的重复性实现（T12/T18）

前置：GPT 提供批准的 tokens、组件 API、状态表、页面范围和真实服务接口。随后实现明确指定的 Views/ViewModels 小组件、文案、键盘与可访问性标注；不改 App 全局资源、CoreSupervisor、根主题或接口契约。验收：所分配组件真实状态可操作、减少动效有效、失败不显示成功。完整工作台架构与视觉验收留 GPT。

### DS13：固定非空迁移样本与字段对照（T13）

前置：GPT 冻结旧→新映射和安全造数入口。随后在项目测试目录构造合成的原件/知识/关系/附件/学习/机器反馈样本，填写预期映射与计数；不读取真实用户库、不实现迁移事务。验收：源样本哈希不变、每个关系有预期目标、坏引用负例齐全。真实迁移与回滚留 GPT。

### DS14：双侧学习/研究业务案例（T08/T09/T10/T11）

前置：GPT 冻结状态机、角色/权限、撤销传播与时间语义。随后编写指定服务的表驱动案例：来源撤销、个人定义、重复转载、用户纠正、到期复测、预算不足、权限拒绝。只改被分配测试与合成 fixture；不访问真实云端账号。验收：明确业务输入与预期事件，不把 RAG/提示更新叫参数微调。

### DS15：候选交付说明和证据装配（T15/T16）

前置：GPT 提供实际验收过的候选 manifest/哈希及逐项结果。随后按事实编写支持矩阵、限制、启动/退出、备份/恢复/回滚说明，核对所有引用。不得重建候选、改二进制、发布或虚填 PASS。验收：每项能力能指向同候选证据；未测和失败单列。

## 7. 执行顺序、升级与回交

顺序：DS01 最小入口核对 → DS04/DS05/DS07/DS08 测试批次 → DS02/DS03 资产批次 → DS06/DS09 → DS10 汇总。DS11—DS15 等各自明确前置完成再执行；不是把所有开发都阻塞在资料盘点。

每批结束统一检查：

- [ ] 已列改动路径且无越界/未知用户修改。
- [ ] 已运行最小测试或只读检查；未执行项给出理由。
- [ ] `git diff --check`、`git diff --stat`、`git status --short` 已核验；新文件也逐个检查。
- [ ] 失败原样回交，不放宽门禁、不删除失败案例。
- [ ] 更新一份 `DEEPSEEK-RESULTS.md`，不要每条任务生成另一套权威索引。

回交格式（每批一段，以下字段全部填写实际值）：

```text
任务卡 / 原任务 ID：
base SHA / 当前 HEAD / 工作区路径 / 是否 dirty：
实际修改文件与新增文件：
读取并复用的实现与调用方：
验收案例、独立预期及证据来源：
测试命令 / exit code / PASS、FAIL、SKIP 数 / run ID：
发现的缺陷与未满足前置：
需要 GPT 的精确裁决、文件、符号及最小失败案例：
本批可回滚范围（不含既有用户修改）：
是否提交 / 推送 / CI / 合并 / 安装态验证（分别填写）：
下一张可执行任务卡：
```

交付不要求先等 GPT 在线。把可独立完成的卡做完后保留结果；高风险卡明确停手。不要声称 GPT 已跑完高难度任务，也不要声称 DeepSeek 已完成整套 T00—T20。
