# AAOS-01 Q00–Q15 当前执行台账（2026-10-05）

固定提交 `72039249a41f9ea98e38542feefbf8f74e013317` 的 workflow `308098767`、run `37280918681`、attempt `1`（workflow_dispatch、force_full）已核对 headSha，全部 20 个 job 实际完成且 success。desktop-fast、desktop-build、installer-lifecycle 的目标步骤及 a0-gates 均 success，没有从 skipped/cancelled 推导通过。原始 `run.json`、分页 `jobs.json`、`summary.json`、非空 `logs.zip`（2,132,560 字节）和 `full.log`（7,280,220 字节）保存在本工作树 `.project-local/task-runtime/aaos01-ci/37280918681-1/`。首次官方日志下载 90 秒超时并显式报错；同一绑定补采成功后才采纳结论。运行期间没有提交或推送。此 CI 只证明该固定提交，不能覆盖随后未提交的 Q04–Q12 扩展。

任务编号和完成条件以 `docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md` 为准。本文件维护既有 AAOS-01 切片当前状态；不可变任务包仍是执行规格，不是完成证据。历史回执保留原始候选、SHA 和能力范围，不自动提升为本轮或安装态验收。下述扩展已完成本地验证，尚待新固定 SHA 的完整 CI；不得由前述 72039249 的结果覆盖新代码。

本轮起始 HEAD：`37bfe872ccbaed88a4825b8ff939ccf94aef8b92`，开工工作树 clean。已验证源码提交 `59b829d7724c2a1e3210e07d287ea9eb68722d4c` 的完整 CI 已执行：两桌面门禁成功，旧 NSIS 验收契约失败，因此完整运行 FAILURE。安装契约修复后的固定提交与最终 CI 结果须读回后登记；不得由 cancelled/skipped 运行推导通过。

## 当前状态与剩余缺口

| ID / 权威任务 | 当前状态 | 已有证据与实际剩余缺口 |
| --- | --- | --- |
| Q00 现场保护与最小对账 | PARTIAL | 已复核起始 SHA、工作树与工具路径；本轮使用独立候选及全新 Core 数据根。未知用户资产、旧库与历史回执保留；完整资产/schema/writer 身份不因本轮格式测试自动完成。 |
| Q01 重构决定与目录登记 | PARTIAL | 已有 SUP-022 重构登记；本轮统一使用权威 `stage_backend_runtime.py` 产出候选，desktop-fast/build 使用相同准备步骤。此项不是旧编号中的“打包完成”；Authority 与目录完整验收仍按任务书核对。 |
| Q02 Tauri 启动与只读桥接 | TESTED_LOCAL / PARTIAL | 最终 src-tauri fmt --check PASS，cargo test 61 PASS/0 ignored，包含真实候选解释器及统一首次启动/重试选择。真实 WebDriver 连续三轮读写/重启/恢复 PASS，最终两轮使用严格失败传播探针；独立安装态完整桥接仍待新 CI。 |
| Q03 类型合同与权限 | PARTIAL | 既有启动契约、前缀隔离与权限测试保留；本轮未将单元测试提升为全部 DTO、对象权限与版本错误验收。生成合同、有限命令与对象范围需按任务书逐项读回。 |
| Q04 原件与文档保存 | TESTED_LOCAL / PARTIAL | 已实现 schema10 CAS 原件、Document/Block、同事务 editor JSON/正文投影、稳定 block IDs、未知节点保真、乐观锁409、旧版本读取及恢复生成新版本；真实 file-backed Store/API 回归通过。25个约1MB文档的目录改为六字段摘要，尚待父代理最终统一回归。独立备份演练继续见Q11；不能从API代推installedUI。 |
| Q05 阅读与证据样板 | TESTED_LOCAL / PARTIAL | Tauri 已接有限命令、PDF.js、Tiptap、稳定块与版本、canonical引用；复用旧 Tauri DataTable/Section、Avalonia 来源链/折叠处理记录与导入回执布局。前端25文件164 tests、tsc、production build PASS；真实窗口中文阅读/保存/重启 PASS。物理IME与installed qualification未完成，PDF页锚点未伪写located。 |
| Q06 A 波次多格式吸收 | TESTED_LOCAL / PARTIAL | a7独立A矩阵12/12通过：TXT/PDF/PNG/DOCX/XLSX/PPTX/HTML/Canvas/SRT/ZIP真实Core/worker/3产物/定位事实/损失及重启；PNG真实OCR文本、词boxes、stdin图像SHA已核实。WAV/MP4只media.probe头信息，不计解码、ASR或内容闭环。Office正/损坏四项均按预期成功/failed且重启一致。安装态逐格式与已知原生locator限制保留。 |
| Q07 候选审核与纠正 | PARTIAL / AWAITING_OWNER | 新版审核同事务绑定实际knowledge version，过期409、machine403工程测试通过。已从权威任务书真实Source/job/transform摘录创建一个未接受候选，等待用户明确决定；工程设置human principal不当真人审核。 |
| Q08 学习与 AI 资产闭环 | TESTED_LOCAL / PARTIAL | assessment/FSRS/幂等事件/机器任务/纠正入口已接有限Core。真实本机qwen3.5-4b经Core与候选worker回答公开工程夹具「37」，实际模型/提示版本/知识版本/任务及完全重启读回一致。该夹具审核明确AUTOMATED_FIXTURE_REVIEW_NOT_G4_HUMAN，结果unmeasured；真人决定、真人答案与纠正旅程仍缺，不虚构错误或效果。 |
| Q09 搜索与完整能力目录 | TESTED_LOCAL / PARTIAL | 正典检索/审核页已接Core；从唯一CAPABILITY_ATLAS_V2.yaml与capability-map生成16个CAP目录及两源SHA，未来能力可浏览，握手/权限/调用证据分开，未匹配旧数字ID不伪造join。九个主导航复用正典页面与旧壳；生成检查/前端回归通过，完整真人检索旅程仍未验收。 |
| Q10 导出与首个互通 profile | TESTED_LOCAL / PARTIAL | a7真实Rust Markdown/Obsidian固定两文件包、完整Document/未知节点/锚点/损失manifest、独立磁盘回读与Core重启导出相等通过。宿主有限导出仅写产品资料目录，无UI path输入。Obsidian应用尚未实际启动回读，不能把文件回读提升为外部软件验收。 |
| Q11 备份与副本恢复 | TESTED_LOCAL / PARTIAL | 现有Store一致live backup→全新独立DB与CAS副本恢复→完整文档/版本/原件读回→继续编辑/第二次重启全部PASS；原生host恢复与retry同一Core、版本3→2、CAS一致PASS。备份哈希/manifest与源CAS严格核验，损坏回滚测试通过；实际SQLite3.51.3（rusqlite=0.39.0），全workspace --locked回归PASS。安装态独立副本资格仍待。 |
| Q12 B 波次轻量扩展 | TESTED_LOCAL / PARTIAL | a7独立13/13：CSV/TSV、JSON/JSONL、YAML/TOML/XML、EPUB、EML九项，各有实际结构/原件SHA/输出字节SHA/锚点/损失/导出/重启；坏EPUB、unsafe YAML、XML DTD/外部entity、坏JSONL四项failed且无输出。EPUB章节/段落/nav/资产SHA和EML头/正文/附件SHA已逐样本断言，附件未独立解析明确loss，EPUB Core原生定位仍unverified。没有用Q06代验，安装态扩展资格仍待。 |
| Q13 性能与故障验证 | TESTED_LOCAL / PARTIAL | 真实Core四故障场景无产物且后续正常job恢复PASS；20次真实Tauri新进程/新Core根/新WebView profile启动，预先3s/1GB预算下P95=1.422s、完整自有树最大468340736字节PASS（OS磁盘缓存保留）。创建时间绑定父子进程排除旧父PID重用；CDP观察器不计入产品内存，退出命令清理不冒认WM_CLOSE。无观察器的WM_CLOSE独立PASS；安装态整机故障旅程仍缺。 |
| Q14 Windows 安装态资格化 | NOT_RUN | 本地构建、候选完整、Rust/Python 测试和 CI 均不能替代独立安装包的真实桌面旅程；尚无 Installed Qualified。 |
| Q15 第一包收口与第二包交接 | PARTIAL | 本表统一当前状态，47 份现场枚举的旧 Q02 逐轮记录已加历史指向、正文证据保留。Q14、核心完整旅程和 Owner Accepted 未完成，不能宣布第一包收口或冻结旧入口。 |

## 本轮工程与样本证据

扩展真实回执均位于本工作树 `.project-local/task-runtime/`：

- A波次：`aaos01-light/c4e55d437151428fb9cb42cc5eb47ac7/receipt.json`；B独立13项：`aaos01-light/2abdb56432b5462d88f86c9d0a008c8f/receipt.json`。
- 固定两文件导出：`aaos01-exchange/c2b974c7f75348e5ad8d32830d3de506/receipt.json`；Core四故障：`aaos01-fault/e5f45e99c58a4a19bab843891063c68f/receipt.json`。
- a8一致备份/全新独立恢复/继续编辑：`aaos01-document-backup/e933f6b69f8b4278bc580b1a43dbb9cd/receipt.json`；本机真实机器回答/任务重启：`aaos01-machine/actual-local-04/receipt.json`。
- 最终host SHA `1fba0a18e120737e36474325b25e325f978490861f393c36aec02c62a78d9db5` 的WebDriver严格探针两轮：`aaos01-webdriver/f146721e318c4fe8a2fe5af875461f9c/receipt.json`、`aaos01-webdriver/f56dfc1cd70c40ea910d25969845ce59/receipt.json`，均包含16并发实际原件/引用响应、中文阅读、保存、重启、原生恢复/重试、版本回退、CAS及实际进程句柄退出；不是NSIS/物理IME/真人验收。
- 真实CDP窗口保存/产品退出/重启：`aaos01-tauri-window/9cccae55acc04aa1abf34edf279eacc1/receipt.json`；无观察器WM_CLOSE：`aaos01-native-close/0b152274bdd24750b3f154a7c400ebc0/receipt.json`。CDP附着时WM_CLOSE探针的超时原记录保留，不能把退出命令提升为WM_CLOSE通过。
- UI性能：`aaos01-ui-performance/8920b7e9657f4c5bb834377df2ac3dd4/conditions.json`及`receipt.json`，20个完整样本；此前`cf5fc01cd1674c2eb955195f21d189ef`把父PID重用的旧外部进程误计入产品，原失败保留，不作为有效产品树内存结论。

修复的实际产品根因包括：首次启动/恢复CLI/重试统一Core选择；旧重试曾启动Python并使文档404。宿主并发reader原先用try_lock把正常原件+引用并行读取误拒为recovery busy，现短阻塞锁绑定刷新与workspace身份，普通HTTP前释放，export到发布保持锁。真实并发窗口回归通过。探针最终关闭失败显式ok:false/nonzero，CI工具回执统一receipt.json；失败/0字节/未执行均不当PASS。

界面吸收沿已有资产进行：Tauri导航、命令面板、检查器、恢复壳继续复用；DataTable/Section用于实际结构分页，Avalonia SourceReader/EvidenceCenter的来源链、定位事实及折叠记录布局迁入同一前端，不另建永久客户端。Tiptap3.31.4、PDF.js6.4.299为锁定依赖，未知节点/来源原件不丢。开源池WeKnora在既有registry仍是UX_DONOR/REFERENCE且upstream未固定、license未核验，不将登记项冒认已集成，不盲目复制代码。

当前本地候选：工作树 `.project-local/a8` 与 `.project-local/rt`，manifest SHA-256 `5bd3e69f30b7e432b98e871e7d42f906b67e7c57fb16723839fc62e1765438c0`，Core SHA-256 `5e5cb4f6b1afe27c1eec05c892d9e5e6a5c8e1f9457fc0b7c4e674d1045b6b4c`；解释器 `runtime/python.exe`，Python3.12.13。候选声明源为72039249且实际暂存时worktree dirty，仅是本地组件实测，不能伪称新提交的exact源码候选。既有uv.lock导出/install的a3干净donor经权威暂存器进入runtime，未重复增加Office依赖。锁SHA-256 `0F73EA804B0ECA61A251013D199F75D88F35E6322BB155EB2581B8D10F69CE52`；新CI将以新固定SHA重新准备候选。

引擎断言由产品候选解释器执行真实 import，输出模块路径与版本，检查模块来自 runtime 内部，并核对 profile 与宿主 nested/flat 选择规则；失败非零。四模块为 openpyxl、pptx、markitdown、pytesseract。引擎负向测试失败非零，原文件字节已恢复；这不是 OCR 样本资格。

历史a4 Office 回执：工作树 `.project-local/task-runtime/aaos01-office/93fd87f7648840e1940021ca99f1db95/receipt.json`，`ok: true`；本轮扩展Core的a6 Office回执 `aaos01-office/7ab841aa95444f50b043125a9c2adf7f/receipt.json` 同样通过。证据级别 `REAL_CORE_WORKER_INTEGRATION_AUTHORED_FIXTURES`；这是自制已知内容样本在实际产品Core/worker执行，不是私人真实资料或安装态验收。

- 有效 XLSX/PPTX：导入 → job → worker → Core 持久化 → 完全重启读回；已知工作表/单元格、页/文本、native 位置、canonical 锚点、损失与三类输出 SHA 校验通过。
- 损坏 XLSX/PPTX：均 failed，错误 `AAK-WORKER-003`；这是预期失败行为通过，不是格式内容提取成功。
- 四项作业重启后状态、质量与输出快照一致；默认 UUID32 长数据根已通过，此前长路径失败不再作为当前候选结果。

组合回归 `fda7d77ffa15`：89 PASS，覆盖暂存安全、两桌面门禁同准备、Desktop staging 与 Windows 真实 worker 长路径；变更 Python 文件 Ruff PASS。架构门禁与 source=worktree 仓库规范最终再次 PASS。以上为本地结果。src-tauri 的最终 fmt 与 56 项测试见上表 Q02。

## CI 与不可自签边界

`workflow_dispatch(force_full)`，workflow `308098767`，run `37277234733`，attempt `1`，headSha `59b829d7724c2a1e3210e07d287ea9eb68722d4c`：完整结果 FAILURE。desktop-fast/build 各目标准备、Tauri、真实 import、Office 持久化与打包步骤均实际 success；installer-lifecycle 的旧 nested Python / Python backend 验收失败，a0-gates 因此 failure，不计完整通过。

固定 SHA Office 回执：`.project-local/task-runtime/aaos01-ci/37277234733-1/office/38bc0fb8b7554b82b132075d2c37abc1/receipt.json`，40,779 字节，SHA-256 `c95ab7dcd4219b72a62a34fc687a2ee79542d0c73b2a1160a2d4def0ab3aa950`；有效两格式 succeeded、损坏两格式 failed、四次冷启动快照一致。全部 worker 文件及锁文件哈希与固定提交逐项一致，启动解释器与 import 解释器一致。回执 source dirty=true 如实保留，不隐去；worker 哈希匹配仅证明这些文件，未推断未记录的 dirty diff。

日志采集首次 gh 汇总超时显式失败；已通过官方 run/attempt ZIP 接口恢复，`logs.zip` 2,133,874 字节、`full.log` 7,281,586 字节，非空验证通过。未在等待该运行期间推送。

后续安装验收修复：按 profile 与宿主规则识别实际解释器、核精确 Core 进程与 401 认证边界，保留 WM_CLOSE、强杀、字节码、升级、卸载保留与重装；使用安装内权威 launcher 独立合法 v2 session 读写宿主同一 `archeaxis.sqlite`，不读取宿主 token。候选 `.project-local/a5` 上的真实 helper seed/冷启动同 DB 读回通过（`.project-local/task-runtime/aaos01-installed-helper-local-2/helper-receipt.json`）；实际进程/CIM/401 helper 通过（`.project-local/task-runtime/aaos01-cim-auth-local/receipt.json`），均未执行本机 NSIS。受影响回归 109 PASS（run `f1256bcdf96b`）。新完整门禁待新固定 SHA，不把这部分本地验证记作安装生命周期通过。

旧 98 表 Python 库与 Core `workspace_meta.schema_version` 不兼容。迁移与只读接入的数据语义仍须明确；保留原库与独立新数据根，不以泛化修复授权推断具体内容舍弃或映射。普通暂存布局与实现合并已授权自主处理，不再列为待用户决定。

历史纠偏出处保留在 `AAOS01-AUDIT-CORRECTIONS-20261005.md`、交接文件与 Git 历史；不在本表保留互相矛盾的 done/撤回当前状态。回退使用本次提交前代码与已保留旧候选/旧数据副本，不让旧程序打开新 schema；本轮未发布、未安装资格化、未声称 Owner Accepted。
