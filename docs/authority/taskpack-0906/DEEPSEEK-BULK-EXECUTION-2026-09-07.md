# ArcheAxis · DeepSeek 全量低风险工程执行包（2026-09-07）

> 给 DeepSeek 的直接任务：在本文边界内，把所有当前能执行的子项全部执行并验证，再统一交回 GPT。不是只写计划、只做盘点、只跑已有测试；需要实际交付测试、夹具、检查工具及符合准入条件的小修复。
> 这是用户要求的执行任务包，不授权访问 E 盘、删除资产、上传私有数据、发布或修改高风险核心。
> 若有 Superpowers，使用 executing-plans 分批执行；没有该技能按本文流程实施，无须为此安装全局组件。GPT 本轮仅编写任务包，不同时写业务代码。

**目标：** 在 GPT 接手高难度工作前，完成可独立实施的大量低风险工程，提供可运行工具、可复算样例、真实失败回归和明确的剩余阻塞。
**架构：** 正式 C#/Avalonia 桌面 + Rust 独立 vNext 数据库 + 隔离 Python worker；旧版是能力/恢复参考，不是另一条正式开发线。
**规范：** 原 `docs/authority/taskpack-0906/TASKS.json`（2026-09-06-r1）及当前项目 AGENTS；原 21 项产品任务全部保留。本包 P00—P28 共 29 张低风险工程卡，不是替换后的产品完成标准。P24—P28 是用户追加的仓库规范化、索引与非破坏性历史整理，P23 在其他可执行卡之后统一收口。
**优先关系：** 本包成为 DeepSeek 当前入口，承接 R1/R2，不重启旧包；R2 剩余文案问题并入 P01。旧 DS11—DS15 不再作为整包等待理由，但高难度前置未完成的实现仍不得擅自开始。

## 1. 起点与接手清单

- 项目：`D:\All projects\ArcheAxis-Knowledge-OS`。WORK-LAB 不是本项目，外置工具库也不是项目。
- 已知 HEAD：`2948b155db069d608e7ebd8acb7956079d8cf69f`；分支 `codex/full-loop-0906`；main 快照 `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`。接手必须重查，不强制恢复到该 SHA。
- 已有 DeepSeek 脏改动：4 个测试 Python 文件、2 个 fixture、5 个历史文档链接修改、`DEEPSEEK-RESULTS.md`、`DEEPSEEK-R2-HANDOFF.md`。其中有 untracked 文件，不能只看 git diff。
- GPT 已有交接：`HANDOFF.md`、`DEEPSEEK-TASKS.md`、`GPT-HARD-TASKS.md`、`DEEPSEEK-REWORK-R2.md` 和本文。保留，除本文明确允许的结果追加外不覆盖、不归入自身代码补丁。
- GPT 已复验 R2：91 passed、106 subtests、6 warnings，run `.project-local/runs/be268a2d33/4db0acb206f4`；两个新测试文件 Ruff 与 vocabulary drift 通过；16 个修正链接可解析。
- 这些是当前脏工作树的局部测试。源码 checkpoint `b5a0840a926b826d249ef2a8c4e320ad6436fcca` 的旧 vnext-ci 成功，不代表本轮新增修改 CI 通过。
- 正式 `apps/ArcheAxis.Desktop/MainWindow.axaml` 仍为欢迎页；Core 已有文本任务执行/取消/状态/结果接口。不能声称新 UI 或全格式已完成。
- 冻结 TASKS.json SHA-256：`1aa5c17c94f8c279987b5f4c70777e25d3614b6419fda65fd351abf71ff6bc94`。禁止编辑冻结原计划来让任务变完成。

## 2. 路径、工具和安全约束

**路径权威：** `docs/SHARED_RESOURCE_PATH_INDEX.md`，用户于 2026-09-07 明确确认。下面是手交任务包快照；本机执行先读索引、核实精确路径，不猜、不替换为同名库。路径不存在只阻塞对应能力。不得自行改变索引里的五个用户指定根路径。

| 类别 | 已知路径 / 使用约束 |
| --- | --- |
| PowerShell 7 | 最近现场为 `C:\Users\ALEX\AppData\Local\Microsoft\PowerShell\7\pwsh.exe`；先核实 `$PSVersionTable`，不盲信旧 Program Files 路径、不改回 5.1 |
| 项目 Python | `D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe`；先 imports 预检，缺依赖不能换另一解释器制造假回归 |
| 共用工具链 | 根为 `D:\All projects\OS External Configuration`，已核实工具链子目录为 `10-toolchains`；复用现有路径，不改库、不重复安装 Cargo/.NET/FFmpeg |
| 本地模型 | `D:\All projects\Model library`；本地优先，只读取项目现有 profile 指明的模型；不全盘扫描、不重复下载、不改模型库 |
| 资料副本 | `D:\All projects\ceshi`；只在已有授权的格式/路径范围内消费，不修改、不上传、不将私有正文写入 tracked 文件 |
| Green | `D:\All projects\ArcheAxis.Knowledge.Green-x64` v0.6.14；本包不操作该目录或其数据库，不替换、不清理、不启动 |
| Green 真实资料库 | `D:\All projects\资料库`；用户确认是绿色版设置的资料库；不是测试库或缓存，本包只登记/核实路径元数据，不读内容、不写、不清理、不迁移 |
| 开发状态 | 统一经 `scripts/runtime/dev.py` 进入 ignored `.project-local/`，按 worktree/run 分离 |

硬边界：

1. E 盘一律不访问。凭据、`.env`、`.codex`、`.hermes` 私密内容、浏览器数据、代理会话、私人记忆不读取、不复制、不上传。
2. 不删除或移动资产/证据，不 reset/restore/clean/force-push，不改 ACL，不杀共享进程。`d/All projects` 下有 `Cognitive-Loop-OS/.hermes`，保留，不为归属审查深入私密目录。
3. 不提交、不推送、不 PR/合并、不发 tag/Release、不改版本号；用户之后另有明确授权才改变此边界。现在交付本地补丁和结果。
4. 不修改生产 Rust/C#、数据库/迁移、worker 传输与调度、权限/状态机、schema/生成器/锁文件、CI 策略、AGENTS/根权威清单/正式 UI/全局主题。
5. 项目构建状态只写 `.project-local`。`.hermes` 保留旧材料，不新写，不整目录扫描；当前 R1 误写事件保留 UNVERIFIED，不冒充从未发生。
6. 一 checkout 一个 writer。用户安排本轮 DeepSeek 完成后 GPT 再执行，默认单 writer 顺序推进；有明确并行能力且可隔离时，独立 worktree、独立文件分工。未知脏改动不得采用或覆盖。
7. 静默执行；Windows 自有子进程用隐藏窗口和超时，不能把 shell 命令字符串交给未知来源拼接。缺系统级依赖只阻塞对应子例，不装全局组件。
8. 全部扫描都不跟随 symlink/junction/reparse；命中不明目录或私密路径只记 excluded，不深入求证。

## 3. 允许真正落地的工程与升级边界

允许新增/改动（每卡还须遵循更窄路径）：

- 自己已有的测试和本包明确新增的 `tests/workers/test_bulk_*.py`、`tests/contract/test_bulk_*.py`、`tests/maintenance/test_bulk_*.py`；合成 fixture 放 `tests/fixtures/vnext/`。
- 新建工具：`scripts/maintenance/bulk_fixture_factory.py`、`bulk_evidence.py`、`bulk_link_audit.py`；这些是本包拟新增路径，不是声称仓库已存在。各工具必须有同名测试，不能只生成静态报告。
- 追加唯一回执 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md` 的“BULK-0907”段；更新现有 `DEEPSEEK-R2-HANDOFF.md` 的当前摘要/范围，不再创建多份相互竞争的结果文档。
- 已证实纯路径笔误的非权威说明文档链接，可在 P04 条件下做精确修正；其他当前权威/历史内容只给补丁建议。
- 用户追加允许 P24 对指定索引做已经由当前 AGENTS/决策账本证明的事实性链接、分类、当前/历史入口修正；不制定新的架构、权限或语言规则。P25—P28 的非破坏性归档/索引整理按各卡执行，源文件保留。
- 生产 Python 的局部确定性修复仅按下方准入规则，在 `document/worker_text.py`、`document/worker_canvas.py`、`document/worker_subtitles.py`、`web/worker_html.py` 四文件内进行。不是四文件的改动均自动低风险。

局部修复须同时满足：独立预期来自已有规范或明确格式标准；现存接口不变；无新依赖；不改权限、路径信任、资源安全、编码回退政策、排序/覆盖/质量定义；只改一个局部函数及其回归；已有消费者测试通过。任何一条不满足则升级 GPT。不要为了“实际写代码”硬造生产修改。

所有新测试都走 RED/基线缺口 → 独立预期 → 最小实现（如准入）→ GREEN/保持真实 FAIL。只增加覆盖而生产已经正确，可直接 PASS，但不能称修复 bug。禁止更改期望以掩盖产品错误、xfailed/skip 充数、mock 成功冒充真实集成。

## 4. 执行机制：不因单项阻塞收工

状态：READY / RUNNING / DONE / PARTIAL / BLOCKED / NOT_APPLICABLE。只有最后三种状态都写清具体证据与范围才有效。

- 先建本轮子项清单，粒度为一个格式案例、一个 schema、一个资产、一个链接或一个检查工具；记录输入版本/哈希、依赖、允许路径、验收、状态和证据。
- 每批推进 10—20 个相关子项，保存结果。已完成且输入与检查范围未变的结果可复用，但需给出哈希/命令/覆盖证据，不能只凭旧标题。
- 缺模型/权限/真实来源只阻塞对应测试；继续文本、静态网页、Office 已有引擎、合同、设计资料和其他独立任务。
- 全部 READY 子项处理后重新评估 BLOCKED：本轮是否已补足前置；已补足则继续。没有条件可推进时才统一回交。
- 不要求无限扩展新功能，也不反复跑相同失败。每个失败先最小复现，能本轮低风险修则修，否则留下稳定回归和精确 GPT 接手点。
- 不能只生成一堆报告就算全包完成：P02/P03/P04 的工具与测试、P08—P17 的独立案例及可执行回归都是交付内容。

## 5. 任务卡 P00—P28

### P00 · 接手和环境预检（T00/T19）

- [ ] 核验 Git 根、分支、HEAD、全部 tracked/untracked 差异；登记已有 GPT/DeepSeek 文件，记录本轮开始前每个拟编辑文件的哈希。
- [ ] 读取项目 AGENTS、配置/目录/语言权威索引及 `docs/SHARED_RESOURCE_PATH_INDEX.md`；五个资源根逐一按职责登记，只核验本次所需路径元数据，不扫描用户账户状态或真实资料内容。
- [ ] 通过精确 Python + dev.py 检查 pytest/jsonschema/Ruff，以及每个格式要用的 imports；记录已验证路径和缺失项，不声称已安装即已可用。
- 产出：本轮 ignored `worklist.json` / `baseline.json`，每次追加实际状态；新工具/测试准备必须在此确认后执行。此卡不做云端 fetch 或认证读取。

### P01 · R2 小缺口一次收口（T00/T14）

- [ ] R08 标 PARTIAL；DOCX 引擎明确为 `worker_office._docx_text` 标准库 ZIP/XML；补齐结果表遗漏的 `test_quality_regressions.py`。
- [ ] 按实际路径重算 R1/R2/本轮文件数，不再写“6 个文件”却列 3 测试 + 5 文档 + 回执；回滚描述按本轮差异而不是整文件恢复。
- [ ] 原始证据目录保持，不写“删除 run 目录即回滚”；R1 误写保留 UNVERIFIED，不为补证读私密历史。
- 允许文件：现有 RESULTS 与 R2-HANDOFF；验收：两个入口当前结论一致，历史结果不改写，仍不声明全部产品完成。

### P02 · 可复现证据收集工具（T01/T07/T15）

- [ ] 新建 `scripts/maintenance/bulk_evidence.py` 与 `tests/maintenance/test_bulk_evidence.py`。最小功能：记录确切 argv、cwd、解释器、开始/结束时间、exit code、source SHA/dirty、输入/输出 SHA-256、引擎版本、stdout/stderr 相对证据位置。
- [ ] 只接受项目已定义的程序/输入与当前 run 内输出，argv 列表、shell=False；拒绝 E/UNC/reparse、越界输出和缺 run 环境。不能成为任意 shell 代理或绕开 dev.py 的新 launcher。
- [ ] 不记录环境全集、不接受含凭据的参数；只用于本包本地非敏感测试。已有 wrapper 提供进程执行时复用它，证据工具优先消费其结果，不重写复杂调度。
- [ ] 单测使用项目临时文件验证正确哈希、被篡改哈希拒绝、非零退出保留、遗漏输出显式报错、缺环境零写入。输出与命令相互可追溯，清理不是功能。
- 验收：真实一次成功 + 一次失败有机器可读回执；失败不能只因最后汇总命令成功而变 PASS。

### P03 · 合成夹具工厂（T05/T06/T07）

- [ ] 新建 `scripts/maintenance/bulk_fixture_factory.py` 与 `tests/maintenance/test_bulk_fixture_factory.py`；按当前需要的最小格式逐步实现，禁止先搭大框架。
- [ ] 接受固定 seed 和当前 run 内目标目录；生成中文/数字/表/段落/关系/时间等合成样例及独立预期。已有小 fixture 直接复用，不生成同质副本。
- [ ] 文本/JSON/Canvas/SRT/VTT/HTML 字节确定；ZIP 格式控制时间等元数据；图像固定参数。第三方格式不能保证字节确定则明示原因并验证语义稳定，不能假报确定性。
- [ ] 小型无敏感 fixture 可纳入 `tests/fixtures/vnext/`，大图/媒体生成在 run 内并以脚本+种子重建；不把模型/资料副本入库。
- 验收：同 seed 两次生成可比，预期不从被测 parser 输出复制；坏输入来自明确损坏操作并保留原样例哈希。

### P04 · 批量文档链接检查器（T14/T19）

- [ ] 新建 `scripts/maintenance/bulk_link_audit.py` 与 `tests/maintenance/test_bulk_link_audit.py`，输入 tracked 文档列表，离线解析文档相对路径、fragment、URL 编码、带空格/中文目标；不递归扫描磁盘。
- [ ] 测试嵌套正确链接、失效链接、代码围栏假链接、外部 URL、锚点、同名不同目录与越界/reparse 拒绝。实现不了的 Markdown 语法记 UNSUPPORTED_SYNTAX，不误算链接正确。
- [ ] 对 tracked 非私密说明文档运行；外部链接不联网，登记 EXTERNAL_NOT_CHECKED。缺路径与缺 fragment 分开。
- [ ] 仅在唯一同义目标已核实、既有迁移记录支持时修链接，不能只因文件名相同就认定去向。AGENTS/根契约/权威索引、历史证据正文或不明确目标只输出建议。
- 验收：修复数、未修数、排除数自洽；原 16 处不重新修改；不移动历史文件或新增另一个权威目录。

### P05 · 全 tracked 归属与旧入口清单（T00/T14/T19/T20）

- [ ] 以 `git ls-files` 和已有目录权威为全集，分类 source/test/config/design/history/generated/unknown；敏感名称只按路径排除，不读内容。
- [ ] 检查脚本实际入口及运行产物配置引用，标记旧 `.hermes`、写用户 TEMP、固定根路径、多个前端入口候选；配置命中不证明实际外溢。
- [ ] 每条异常附来源文件/行、消费者、已有规则和最小修复建议，未知保持 unknown。不直接改 launcher、根 authority 或 build 配置。
- 验收：全部 tracked 项被分类或明确排除/待核验；原始结果在 run 内。此卡不进行全盘体积扫描，不声称 ignored 运行边界已全面合格。

### P06 · 旧资产全量低风险语义核对（T17/T13）

- [ ] 复用 LEGACY_MANIFEST 和 R03 的 20 项；既有有证据的语义结果按 source/blob 对比复用，不退回文件头抽样。
- [ ] 对剩余授权 tracked 资产按类别分批：代码读实际函数与调用方/测试；文档读决策和适用期；样例读用途；设计资产核来源。空包/纯 re-export 明确归类。
- [ ] 为每项登记 observed capability、source blob、代码/测试符号、现有调用者、行为差异、是否新链实用、建议目标和待裁决点。大文件只审一部分则列未审部分。
- [ ] 复杂安全/状态机/迁移语义不独立裁决；仍完成可观察事实，不把“需 GPT”用作所有字段留空的理由。
- 验收：全集每项有处理状态，声明语义完成的项有正文证据；20 项不能充当全部 1246 项完成。数量以现场 manifest 为准，不强凑旧计数。

### P07 · 既有调研能力与 UI/LOGO 证据汇聚（T17/T18/T12）

- [ ] 从项目已保存资料抽取 OpenHuman、DeepTutor 及其他全部已记录参考项目的能力要求，区分名字、必须吸收能力、当前代码、差距和许可未知。
- [ ] 对已有设计/LOGO/截图记录哈希、来源/许可、实际引用、主题和页面状态；不能把关键词命中当交互完成，未拿到的 GPT 设计写未获得。
- [ ] 提取现有黑白主题 token 候选、状态/键盘/缩放/减少动效约束，产为候选对照而非新设计裁决；不修改主窗口/全局资源/品牌图标。
- 验收：GPT 可直接据表决定复用与页面职责；文档需求和真实可操作组件分列。无需重新联网调研或画第二套 UI。

### P08 · 文本/编码/锚点扩展回归（T02/T05/T07）

- [ ] 在已有 `test_text_ndjson.py` 基础增加尚未覆盖的 Unicode 分隔符、BOM、数字/emoji、空白、边界截断和坏编码案例；复用 R2 的独立坐标断言。
- [ ] 逐例明确原字节、解码、投影文本、字符位置和损失；不以 output 与 output 相互一致作为准确性证据。
- [ ] 输出哈希、字节数、重放幂等的已有充分测试只复用，不重复跑十份同质案例。
- 允许新增 `tests/workers/test_bulk_text.py`；测试失败若涉及编码政策/资源预算交 GPT，只有局部非语义错误才按准入修。

### P09 · Canvas、JSON 结构与字幕边界（T05）

- [ ] 复用 `worker_canvas.py`/`worker_subtitles.py`，扩文件/链接/分组节点、断边、重复 ID、Unicode、空轨、多行字幕、边界时间、重叠、VTT 元信息等可独立期望。
- [ ] 每例分别验证内容、结构、时序/关系和明确失败；不执行 Canvas 内路径/链接，不以支持 JSON 等于理解任意 JSON。
- [ ] 新增 `tests/workers/test_bulk_structured.py`，使用 P03 合成输入，stdout JSON 与退出码分别验收。
- 验收：独立函数/worker 级案例完备，不宣称已接入 Rust Core；新格式语义定义交 GPT。

### P10 · Office 多场景功能回归（T05）

- [ ] DOCX 使用真实标准库 ZIP/XML；PPTX/XLSX 先 probe 当前引擎。合成段落、中文、表格、嵌图清单、备注、合并单元格、公式文本与缓存策略案例。
- [ ] 输出顺序、表/页/slide/sheet 结构、锚点与遗漏逐项检查；未提供公式计算引擎不能把缓存值当实时计算。
- [ ] 新增 `tests/workers/test_bulk_office.py`；破损 ZIP、缺必要 XML、无正文、错误后缀给真实失败案例，不修改高风险 ZIP/解析安全策略。
- 验收：每格式不只命中一个英文子串；输入/输出哈希与引擎版本可复跑。缺依赖仅阻塞对应格式，不阻塞 DOCX。

### P11 · PDF 页面类型与损失样例（T05/T06）

- [ ] 用已安装引擎和合成文件构造文本页、图像页、混合页、横竖版、多栏/表/旋转、空页/破损样例；不得用无授权真实 PDF。
- [ ] 当前 `worker_office.py` 可读部分用实测，逐页记录文本/图片/顺序/锚点和缺失；混合 OCR 未接入应保留失败或明确未实现，不自行写整套编排。
- [ ] 新增 `tests/workers/test_bulk_pdf.py`，将“功能提取”“阅读顺序”“OCR”“精度”分层。
- 验收：至少每种当前可执行类型有独立期望与限制；不能因能打开 PDF 就称管线通过。

### P12 · 静态 HTML 与离线网页边界（T05）

- [ ] 调用现有 `web/worker_html.py` 和保存的本地快照，新增中文实体、嵌套标签、script/style/template、链接、列表/表格/空正文/坏 HTML 案例。
- [ ] 新增 `tests/workers/test_bulk_html.py`；明确目前仍缺的正文去噪、动态 DOM、截图覆盖，测试不伪造这些能力。
- [ ] `web/worker_webpage.py` 只做已有接口的离线参数/响应解析单元检查；不能发真实网络请求、搭绕过 SSRF 的假服务或修改 URL 信任策略。
- 验收：静态快照真实提取且不执行脚本；局部明确 bug 可按四文件准入修，抓取安全/动态浏览器留 GPT。

### P13 · 本地 OCR/截图可复现小样（T06/T07）

- [ ] 复用现有 `tests/workers/test_ocr_profile.py`、项目模型 profile 和已有 OCR 入口；只调用已验证的本地模型/引擎，不自动下载、联网或开 GUI。
- [ ] 先补 R08 缺命令/输出哈希的既有合成 OCR 单例；随后固定字体/版本/种子生成中文、数字、低清、旋转、背景与表格小样。
- [ ] 可知源文本是合成金标；区分文字识别、布局和视觉推断。缺中文字体/引擎时该组 BLOCKED，其余英文/数字仍推进。
- [ ] 新增 `tests/workers/test_bulk_ocr.py`，每例有限时限、输入体积与批量上限；超时不杀共享模型服务，记录故障退回 GPT。
- 验收：回执记录真实模型/引擎配置、CER/数字错误与未识别区域；纯 OCR 不冒充图示理解。

### P14 · 字幕/音频/视频既有能力小样（T06/T07）

- [ ] 已有合成音频优先重跑补命令/输出哈希；调用已配置本地 ASR，不下载模型/音频、不建立常驻服务。
- [ ] 可用 FFmpeg 时生成短时长静音/已知字幕或计时帧样例，单个媒体输入不超过 30 秒，先验证调用路径和退出清理；不能让无管控后代进程长期运行。
- [ ] 只验证现有 worker 可读音轨/字幕/帧的实际行为；没有人工确认的转写不作准确率真值，视频内容理解/多模态对齐仍留 GPT。
- [ ] 新增 `tests/workers/test_bulk_media.py`；无可验证的安全运行入口则标该执行组 BLOCKED，但字幕/元信息/样例生成等独立组继续。
- 验收：运行与质量分层，静音或未提取输出不能假成功；输出来源与时间范围可复查。

### P15 · 质量指标与报告验证（T07）

- [ ] 复用 evaluation worker 与现有 CER/WER 回归，扩独立手算插删替、空参考、数字/专名、Unicode、归一化前后；不将误差率夹到 1。
- [ ] 小批金标/预测复算结果，分文件列最差例与分布；缺 gold 必须 unmeasured，不凭模型自评填准确率。
- [ ] 新增 `tests/workers/test_bulk_quality.py`，验证报告 schema、NaN/Infinity 拒绝、分母与单位、来源哈希、丢失归一化信息负例。
- 验收：各项数值可独立重算；不改质量门槛/统计定义/生产评价公式，定义不清交 GPT。

### P16 · 全部现有合同的批量正反例（T02）

- [ ] 枚举当前 `packages/contracts/v1/*.schema.json`；复用现有合法样例，逐 schema 登记业务实例能否构造、required/enum/type/boundary 等实际约束。
- [ ] 新增 `tests/contract/test_bulk_schema_matrix.py`：每个负例从已通过正例出发只改一处，断言相关 validator/path，覆盖内部/跨文件 refs 离线解析。
- [ ] 没有足够规范的 schema 标缺合法业务实例，不凭生成随机 JSON 通过就称业务验收。runtime-only 约束不能强加为 schema bug。
- [ ] 在内存中移除选定约束验证测试敏感性，不修改磁盘 schema；词汇生成器只跑 --check，不手改生成文件。
- 验收：所有 schema 有实例/已覆盖/缺证据状态；新增真实负例有效，不把 fixture 验证叫跨语言运行通过。

### P17 · 既有 Python 传输与局部失败回归（T02/T04）

- [ ] 基于现有文本 NDJSON 稳定入口，补当前没覆盖的多余字段、错 request/attempt/hash、输出缺失、无效 JSON/非有限值等小型负例。
- [ ] 复用现有安全测试 harness 的 stdin/stdout、超时和项目临时目录，不新造无上限子进程/任意可执行路径接口。
- [ ] 新增 `tests/workers/test_bulk_transport.py`；当现有 fixture/harness 能真实注入错误时才宣称已验证，否则记录测试设计缺口交 GPT。
- 验收：真实拒绝、输出不落成功；不改生产 transport、Core/Store、状态机或进程隔离。

### P18 · 既有领域适配器的差异案例（T09/T10/T11/T13/T17）

- [ ] 根据 P06 已审源码，扩 Anki/Zotero、DeepTutor、source/claim/evidence、学习与机器记录等纯函数适配器案例：往返保留字段、深拷贝、缺字段、未知枚举、重复 ID、中文内容。
- [ ] 新增 `tests/workers/test_bulk_legacy_adapters.py`，按实际 import 调用，测试不得打开真实旧库或写真实工作区。
- [ ] 新旧行为如果意义不同，记录差异而非擅自选一方作为真值；只测已有契约，不发明未来 Rust 类型。
- 验收：确定性低风险适配器有真实正反例与消费者证据；事实未接入新链就明确未接入，不能宣称已实现双侧学习。

### P19 · 合成迁移与双侧业务的案例准备（T08/T09/T10/T11/T13）

- [ ] 在 `tests/fixtures/vnext/` 下整理不触碰真实数据库的逻辑数据样例：原件、附件、关系、修订、学习/机器反馈、研究来源；只用当前存在的契约。
- [ ] 列原件哈希、引用一致性、保留字段和损坏引用；可写 `tests/contract/test_bulk_business_fixtures.py` 验证这些自身约束。
- [ ] 状态转换、FSRS 时间、迁移 ID 映射、角色撤销还没冻结的，输出具体现有输入及待裁决问题，不填写想象的预期迁移结果。
- 验收：GPT 可直接使用样例做后续领域设计/非空迁移；本卡完成不等于迁移实现或真实库验收。

### P20 · 清理候选与证据保全复核（T20/T14/T19）

- [ ] 优先消费既有受限 inventory，必要时仅一次同范围增量复核；不重新递归扫描整个盘或跟随链接。
- [ ] 按 PRESERVE_EVIDENCE / REBUILD_CANDIDATE / SOURCE_OR_UNIQUE / UNKNOWN 分类，列 owner/reference/hash/bytes/错误/重建证据和授权状态。
- [ ] 不将 `.project-local/runs`、Green、源码父目录、`.venv` 或打包混合目录整类视为垃圾；没有重建证明即 false，不为证明可重建跑多个大构建。
- [ ] 原始 25,457,767,687 logical bytes 仅为旧受限观测，保留 4 个错误及未测 allocated/file identity；未知项不得按零字节。
- 验收：候选清单供 GPT 决策，完全无删除/搬移；字节算术准确但不能称瘦身完成。

### P21 · 轻量门禁与耗时证据（T01/T15）

- [ ] 只读现有 `.github/workflows/`、分类器与测试命令，建立路径变化→现有检查映射；记录遗漏和重复，不改工作流/远端规则。
- [ ] 对本轮实际执行记录按环境启动/测试/格式工具/汇总拆时，重复样例以相同条件比较，不从配置名推断性能原因。
- [ ] 汇总可复用的未受影响证据和最后需跑的精确定向命令，避免每卡跑整仓/桌面构建；使用实际 run 输出，不手写 PASS。
- 验收：GPT 有依据收敛门禁，而不是再加一层重复检查；本卡不是 CI 或安装态资格。

### P22 · 全部本轮改动的一次集成回归（T01/T15）

- [ ] 汇总 owning test 文件，先运行本轮新增/修改测试，最后与现有 tests/workers、tests/contract、tests/maintenance 做一次定向聚合；不要反复跑不相关整个项目。
- [ ] P06 关联旧测试先检查副作用，只对已确认合成/本地安全范围的文件执行；需要真实服务/模型/用户数据的单列阻塞。
- [ ] 新增文件 Ruff 无新增错误；存量 4 项 Ruff 仍按 baseline 分离，本包不要求全文件 --fix。
- [ ] 校验 fixture manifest、schema drift、文档本地链接、冻结 TASKS 哈希、最终 diff/状态和新文件内容。
- 验收：实际测试数量/PASS/FAIL/SKIP/warnings/run ID 与命令逐一匹配；失败与阻塞保留，不因为全包难度大就收缩原目标。

### P23 · 就绪任务穷尽审计与一次性回交（T00/T15/T16）

- [ ] 对 P00—P22、P24—P28 每个子项检查：DONE 是否有证据，PARTIAL/BLOCKED 是否已有前置变化，READY 是否仍有未做。重新执行被本轮解锁的组；P23 始终最后收口，不能按数字顺序做完 P23 就跳过追加卡。
- [ ] 只有再无当前可安全推进的 READY 项才收口；无法完成的明确具体缺少什么，不只写“等 GPT”。
- [ ] 更新唯一 RESULTS 的 BULK-0907 段和已有交接入口，列所有改动路径、输入/输出证据、模型版本、未测范围、精确 GPT 任务、回滚补丁边界。
- [ ] 保留原始证据、不整理成需要另开新项目才能理解的索引网络；给 GPT 一个可直接检查的结果摘要和同源机器清单。
- [ ] 明确没有 commit/push/merge/Release/Green 更新；本地工作树有意保留待审补丁，不声称双端一致。
- 验收：执行完所有当前适配任务与“完成整个产品”严格区分，GPT 接手不需要重做全量低风险工作。

### P24 · 当前权威索引实际更新（T00/T14/T19）

- [ ] 接 P04/P05 结果，核对允许文件：`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`docs/DIRECTORY_AUTHORITY_INDEX.md`、`docs/DOCUMENTATION_AUTHORITY_INDEX.md`、`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`、`docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md`。先读完整文件，登记更改前哈希和本轮逐条差异。
- [ ] 只按已批准 `AGENTS.md`、`PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml` 修正事实：正式 Avalonia/Rust/Python 职责、旧壳历史/恢复属性、`.project-local` 开发根、当前 0906 执行入口、用户五库索引。不得自行发明新默认实现或覆盖根契约。
- [ ] 同一索引里“顶部已说旧计划退役、表格仍标旧计划 Current”等冲突必须收敛；把旧条目转入有日期/原证据 SHA 的 Historical 区，而不是删除历史证明。
- [ ] `docs/SHARED_RESOURCE_PATH_INDEX.md` 的五个根以用户确认值为准；其他索引链接到它。禁止重新创建另一份运行默认表或因为找不到程序改根路径。
- [ ] 不改历史冻结状态文件、测试 receipt 内的旧 source SHA，不为通过链接检查创建内容空壳。现有规则冲突无法由批准来源裁决时，标出冲突两端交 GPT。
- 验收：当前与历史条目不互相冒充，索引链接和锚点按文档所在目录可解析；所有更改有已批准来源依据。产出是实际索引补丁，不只报告。

### P25 · 历史文档分类与非破坏性归档（T14/T17/T20）

- [ ] 全集使用 P05/P06 的 tracked 非私密文档，不另扫用户目录/私密会话。逐项标 CURRENT / HISTORICAL / SUPERSEDED_BY_EXPLICIT_DECISION / UNKNOWN，附日期、Git blob、现有消费者、替代依据。仅“日期旧”不代表过期。
- [ ] 对已证实退役的普通说明文档，在当前文档索引标历史归属、原位置、查阅/恢复方式；不移动源码/数据库、冻结协议、根指令或旧测试证据。
- [ ] 在当前 run 内创建选定历史普通文档的只读归档包与 manifest，保留仓库源文件原位。每成员记录仓库相对路径、源 Git blob/工作树哈希、字节数、分类依据、引用和恢复目标。
- [ ] 只纳入明确可公开的 tracked 项目文档；禁止夹入 `.env`、认证、模型、学习资料、浏览器/代理历史或整个 `.hermes`。新归档不入 Git；索引不能只指向易失的 ignored 包，仍保留 tracked 源路径/Git 对象可恢复性。
- [ ] 在 run 内独立 staging 目录读回归档，核对成员数、逐文件 SHA-256、内容可读和源文件哈希不变；拒绝绝对路径/父目录跳转的归档成员，不向真实目录恢复。
- 验收：当前入口不再错误引用退役执行方案，历史资料完整可查且归档可读回。称“非破坏性归档/导航清理”，不得称已物理瘦身或已从 Git 历史删除。

### P26 · 重复文档与过期入口收敛（T14/T17）

- [ ] 使用 P06 的公开 tracked 文档哈希找字节级重复，按来源/日期/引用确认是副本、历史快照还是不同职责；同名不同哈希不得并作重复。
- [ ] 已有明确 canonical 的条目，在 P24 允许索引中将当前入口收敛到 canonical，历史副本仍标来源和用途；没有权威裁决的仅提供候选，不能靠长度/新旧时间选择胜者。
- [ ] 对普通非权威 README/交接导航里的旧入口修正指针，保持有效历史正文和原版本证据；新增/修改声明不得把未完成任务改成 DONE。
- [ ] 不删除重复源文件、不创建到外部库的 junction、不用 symlink 替换真实目录；归档动作仅 P25 所准许的复制与读回。
- 验收：重复的当前导航被实际收敛，副本/快照关系可追溯，无引用丢失；不能以“去重清理”为理由丢原件。

### P27 · 索引与归档回归工具（T01/T14/T19）

- [ ] 复用 P04 的 `bulk_link_audit.py` 和测试，不加第二套扫描器。增加对 P24 指定索引当前/历史分区、相对路径与项目资源索引入口的定向检查。
- [ ] 如确需归档工具，允许新增 `scripts/maintenance/bulk_history_archive.py` 与 `tests/maintenance/test_bulk_history_archive.py`：明确文件列表输入、run 内输出、拒绝敏感路径/reparse/越界成员、计数/哈希读回；无删除功能。
- [ ] 正反例覆盖：正确历史副本、内容被篡改、缺成员、重复成员、绝对/父路径逃逸、同名不同内容、没有 runtime 环境零写入。禁止为测试而创建真实 E 盘路径。
- [ ] 测试里的路径常量只用合成字符串验证拒绝；本机五库检查只做已批准根元数据，不让测试自动遍历真实模型或资料库。
- 验收：索引和归档问题可用小测试复现与阻断；不添加新的重型 CI 工作流或全局门禁，不把工具 PASS 当产品 runtime PASS。

### P28 · 整理收口与物理删除候选隔离（T14/T20）

- [ ] 输出两张独立表：本轮已实施的索引/链接/归档动作；尚未实施的物理删除/搬移候选。候选遵循 `docs/current/AX_DIR_010_INVENTORY_SCHEMA.md` 的字段要求，但其旧路线描述不能覆盖 0906 已批准决策。
- [ ] 已实施表列精确文件、before/after 哈希、消费者、验证和逐补丁回滚；未实施表明确 deletion_authorization=NOT_REQUESTED / rebuild_verified 状态。
- [ ] `.hermes`、`.project-local/runs`、`d/All projects`、Green、`D:\All projects\资料库`、共享工具和模型库都不得成为本轮物理清理对象。实际库的索引登记不是内容处理授权。
- [ ] 目录不再作为当前入口与目录已经从磁盘删除是两种不同结果；无删除就填写 released_bytes=0 / deletion=NOT_EXECUTED，不把归档包大小算节省空间。
- [ ] 新归档也有体积成本，列输入/归档字节和保留位置，不制造大量重复备份。已生成同内容且哈希验证通过的包复用，不反复打包。
- 验收：项目当前导航/索引已实改且可核验，历史保全无损；剩余物理清理只交精确候选，交 GPT/用户按路径裁决。完成后回到 P22/P23 做定向聚合与统一回交。

## 6. 最小工具接口和回执约定

三个新增工具的目标是小而实用：

- `bulk_evidence.py`：消费本轮命令/输出元数据并校验、生成 receipt；不实现新 agent/runtime。
- `bulk_fixture_factory.py`：指定格式与固定 seed 的合成样例生成；无已装依赖时返回明确缺依赖，不自装。
- `bulk_link_audit.py`：解析明确传入的 tracked Markdown 文件清单；不爬网、不跟随跨域链接。

用户追加历史归档卡如需新工具，第四个 `bulk_history_archive.py` 仅按 P27 的复制/校验契约实现，不含删除与原地恢复。能复用既有工具就不新增。

先核实相邻现有脚本是否可复用；若有同功能实现，复用并在回执指明，不能重复造工具。命名若确实冲突，停该工具卡并交精确冲突，其他卡继续。

每个子项的回执至少含：

```json
{
  "task": "P10",
  "subtask": "docx-table-zh",
  "status": "READY",
  "source_sha": "2948b155db069d608e7ebd8acb7956079d8cf69f",
  "dirty": true,
  "input_refs": [],
  "changed_paths": [],
  "command_argv": [],
  "exit_code": null,
  "run_id": null,
  "evidence_refs": [],
  "coverage_limit": "尚未执行；READY 不是通过",
  "blocker": null,
  "gpt_followup": null
}
```

示例只是待执行结构；实际执行后必须替换字段，不能复制空数组作为完成证据。JSON schema 可作为内部工具测试数据，不新增产品 schema 权威。

## 7. 已核实的命令入口

PowerShell 7；本轮会更换 owning worktree 时需同步工作目录，不能测试跑回另一个 checkout。

```powershell
Set-Location -LiteralPath 'D:\All projects\ArcheAxis-Knowledge-OS'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$dpPython = 'D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe'
git status --short
git rev-parse HEAD
& $dpPython -B scripts/runtime/dev.py -- $dpPython -c 'import sys,pytest,jsonschema; print(sys.executable); print(sys.version)'
& $dpPython -B scripts/runtime/dev.py -- $dpPython services/python-workers/document/worker_office.py --probe
& $dpPython -B scripts/runtime/dev.py --pytest -- tests/workers tests/contract tests/maintenance -q
& $dpPython -B scripts/runtime/dev.py -- $dpPython scripts/contracts/generate_vocabulary.py --check
& $dpPython -B scripts/runtime/dev.py -- $dpPython scripts/check_repository_conventions.py --source worktree
git diff --check
git diff --stat
git status --short
```

上面聚合命令用于 P22，不要求 P00 起步就全部执行；新测试先按单文件运行。每条失败分别处理，Shell 最后一个命令成功不代表整组成功。新文件还须逐一 Ruff 与内容核验，untracked 内容不保证被规范扫描覆盖。`scripts/workflow/execution_preflight.py` 在本库未找到，禁止照抄模板调用它。

## 8. 原产品任务覆盖与 GPT 保留职责

| 原任务 | 本包可执行子任务 | 不得越权替代的 GPT 工作 |
| --- | --- | --- |
| T00 | P00/P01/P05/P23 | 最终基线/方向裁决 |
| T01 | P02/P21/P22 | CI 策略、锁定构建与发布权限 |
| T02 | P08/P16/P17 | 生产跨语言协议、权限/版本语义 |
| T03 | P18/P19 | Store、事务、归档/恢复安全 |
| T04 | P17 | 进程树、资源/取消/终态与自动恢复 |
| T05 | P03/P08/P09/P10/P11/P12 | 多格式 Core 集成、复杂解析编排 |
| T06 | P03/P11/P13/P14 | OCR/视觉/视频编排与进程隔离 |
| T07 | P02/P13/P14/P15 | 质量门槛/模型定型与复杂精度决策 |
| T08 | P07/P19 | 真实联网交叉核查与来源独立性 |
| T09 | P18/P19 | 知识修订、检索政策、撤销传播 |
| T10 | P18/P19 | 人类重型学习、FSRS 时间/掌握语义 |
| T11 | P18/P19 | 实际 MCP/机器反馈与权限预算 |
| T12 | P07 | 正式 Avalonia 工作台、服务绑定 |
| T13 | P06/P18/P19 | 非空迁移映射/事务与真实库切换 |
| T14 | P04/P05/P20/P24/P25/P26/P27/P28 | 新规则/冲突裁决与全仓最终规范化资格 |
| T15 | P02/P21/P22/P23 | 同候选 Windows 全链路资格 |
| T16 | P23 | 可逆使用版交付、授权发布 |
| T17 | P06/P07/P18 | 复用目标批准与新链集成 |
| T18 | P07 | UI/LOGO/主题/动效设计裁决 |
| T19 | P00/P05/P24/P27 | 生产运行根与隔离规则 |
| T20 | P05/P20/P25/P28 | 删除/迁移授权、重建/保全决策 |

## 9. 停止条件

不是“完成前十张卡”就停，也不是“发现一个缺少模型”就停。只有所有当前可独立执行子项完成并留有证据，其他子项均有已核实的精确阻塞，且没有本轮可解锁的剩余任务，才能统一回交。

本包不要求用光额度、不要求绕开用户停工设置。执行器达到用户自己的资源阈值时保存本地进度并停止，不以假完成掩盖中断。对 GPT 的此前额度停工要求仍有效；用户的本次请求仅授权 GPT 准备交接，DeepSeek 执行后 GPT 再按用户安排接手。
