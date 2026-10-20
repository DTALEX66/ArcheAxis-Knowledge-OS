# 审计、测试覆盖与产品验收差距 · 2026-10-18

结论：**PARTIAL**。已有多层工程验证，但没有“全项目通过”或“商用界面已验收”的证据。本页回应 Owner 对覆盖、标准、开源吸收和界面测试价值的质询；它是证据解释与缺陷清单，进度仍只回写 `AAOS-UI-FIRST-EXECUTION-20261009.md`。

## 1. 先纠正报告口径

- “163 文件 / 1583 用例通过”指一轮 **frontend Vitest 全套**；不包括 Python 全仓、Rust 全仓、真实模型、安装/升级、全格式往返、完整视觉和辅助技术验收。
- 100% 是该次已收集测试的通过比例，不是代码覆盖率、需求覆盖率或产品完成率。本轮没有提供可核验的分支/语句覆盖率报告，不编造百分比。
- 多轮增量测试含大量重复用例，不能把 1501、1516、1527、1533、1569、1583 相加当作独立场景数。
- 历史回执只证明其当时的提交/dirty patch 和执行条件。本次逐轮复核不等于重跑了全部历史门禁。用户转交的“156/1492”是交接声明；本页不将其当作本轮重验结果。
- 当前基线提交为 `fe18fdc3cbcab9a0f84a02c5a4db1b6bcef13f46`，工作区有未提交改动。下表共享会话阶段全套及构建绑定 patch `feb958eb2fc609561c27251c0bade7b6e3abad3dd7276f1a23192c492c2260f8`；后继诊断修复绑定 `d4b950b990528a9c145f4849bfded534aabd5c68f2dead08c4940ee49445beba`。本报告写入后，不把报告变更追改成历史执行摘要。

## 2. 可追溯的主要轮次

以下按实际验收增量归组；每次 RED、取消、source INVALIDATED 和中间运行仍在原回执内，不虚构“所有历史审计均已完整复核”。

| 轮次 / 证据入口 | 实际覆盖与验证要点 | 结论与边界 |
| --- | --- | --- |
| 9/23 商业 UI 审计，[原报告](../history/repository-consolidation-20261019/current/AAOS-UI-COMMERCIAL-AUDIT-20260923.md) | 当时 Avalonia 宿主及 UI 参考包；状态、焦点、响应、动效、空状态和真实 Core 入口；构建、142 项定向合同与 headless 学习 smoke | 局部实现及工程验证；原生 GUI/辅助技术 NOT_EXECUTED，完整学习及冷启未验。该旧宿主现为供体，不能作为当前 Tauri 的商业验收 |
| 10/03 独立审计，[进展](../history/repository-consolidation-20261019/current/AAOS-INDEPENDENT-AUDIT-20261003.md)、[缺口](../history/repository-consolidation-20261019/current/AAOS-CLOSURE-GAP-AUDIT-20261003.md) | 候选成员、Rust workspace 400/后继集成419、隔离迁移/回滚、课程与检索及其持久化；各自源码和运行条件独立 | NOT_READY。来源仍含 fixture；同一真实资料完整旅程缺失；Python full 收集4 errors/3 skipped，不能算通过；不把早期400/419覆盖后续新增代码 |
| 10/05 审计纠错，[更正总表](../history/repository-consolidation-20261019/current/AAOS01-AUDIT-CORRECTIONS-20261005.md) | 复核 CI run/attempt、引擎断言实际执行、格式处理能力与完成声明是否相符 | 撤回 Q04 完成、音视频内容完整闭环等过度结论；CI 有取消/skipped及 desktop failure，Q14 NOT_RUN。该轮产出主要是纠正证据口径，不能计为新增功能 PASS |
| 10/10 AI 阶段，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-AI-STAGE-20261010.json) | 资产/版本/恢复 fence、模拟 UI，240 视觉场景聚合；两次真实4B路由推理 | 最后布局修改前的836项前端不是最后源码全套；后继仅定向/构建/视觉。实际模型身份 UNKNOWN、语义质量未测、安装交互未验 |
| 10/11 特定安装候选，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-FC-CI-INSTALLED-QUALIFICATION-20261011.json) | SHA `fc940dc89c431d275eec1e9b748dbfab02b0288f`，CI `38077876660` 的20 jobs与隔离安装生命周期；保存/重启/备份及部分格式 | 该 SHA 的安装工程资格 PASS；排除后继完整 grouped 旅程、物理 IME、真实用户数据及 Owner；不能挪作10/18候选资格 |
| 10/12 前端回归，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-FRONTEND-REGRESSION-20261012.json) | 127文件1225项及后继1226项、TypeScript；各自源码摘要 | SIMULATED_FRONTEND；不含实际云调用、模型质量、安装 Green、Owner |
| 10/13 原生模型闭环，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-CONVERSATION-CLOSURE-20261013.json) | commit `5cfeb17622b77598c9ba7e08c5b49369ebf52759`；实际4B/27B合成材料首答/复测、冷启 | 对应候选工程 PASS；答案 `EXECUTED_CANDIDATE_NOT_EVALUATED`，provider stop UNKNOWN；复测取消未获 native 资格。历史成功不能关闭当前新失败 |
| 10/14 集成，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-INTEGRATION-CLOSURE-20261014.json) | 26本地门禁、143文件1285项前端、实际SQLite及native compile | SIMULATED frontend / SYNTHETIC workers；本增量无actual AI；浏览器另一个patch，完整安装/互通仍缺 |
| 10/15 并行整合，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-PARALLEL-INTEGRATION-FINAL-20261015.json) | 本地quick27、148文件1396项，历史HEAD `4fc9006a`（完整身份保留于原回执，不要求fresh clone仍含退役分支对象） | LOCAL_PASS，但 CI `38757310107` 的browser/Python/Rust/installer/aggregate FAIL；本地成功不覆盖云端失败 |
| 10/16 顶部导航，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-TOP-NAVIGATION-20261016.json) | 10 个真实 Chromium 场景；导航呈现、主题/窄窗、焦点、命中；quick 受影响检查及当时前端套件 | 局部门禁 PASS；Host/Core 是 fixture，没有重建原生宿主，不是安装态验收 |
| 10/16 双栏与保全状态，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-WORKBENCH-READY-CHECKPOINT-20261016.json) | 10 浏览器场景、73 项工作状态定向、8 项 CSV/Markdown Core/worker；发现等值 flush 已获 ACK 却一直显示待保存 | 修复并定向 PASS；当时前端 152/1466。安装 CI 38804704425 仍 FAIL：另一分组冷启动文档入口裁剪。不能用局部通过抵消 |
| 10/18 交接首修，[执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md) | F02 六处恒真断言换为真实组件交互；F04 协议目录、响应形状、模型存在性、迟到响应；RED 15 / GREEN 18；前端 156/1501、TypeScript/Vite | SYNTHETIC/Core 与 fetch mock；真实用户旅程尚未由此完成 |
| 10/18 接管复验，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-TAKEOVER-VALIDATION-20261018.json) | 前端 158/1516；文档/浏览器工具 24；13 视口、5 主题的既定浏览器矩阵；目录重选、选区恢复、取消迟到响应、性能接线、键盘与检查器 | 同一 dirty patch 局部 PASS。真实 Chromium + 模拟 Host/Core；不是每页面×每主题×每宽度的全组合，也不是完整 WCAG |
| 10/18 来源、导入与运行时，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-PROJECT-CLOSURE-VALIDATION-20261018.json) | 资料路径/哈希与包身份、生产 OSS 证据；单文件/目录上传字节摘要绑定；前端 159/1527；若干 Python/Rust 定向；真实 Core/worker 4 常用格式 + 两波 25 案例；宿主/Core 构建 | 各门禁保留各自 patch；不是同一次全栈全仓运行。PDF 仅文本提取；音视频部分只 probe；不证明 OCR/ASR/原生编辑/往返。真实 4B/27B 原生学习旅程仍有 FAIL |
| 10/18 模型诊断与小栖首接，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-CONTINUATION-20261018.json) | 前端 160/1533、worker/运行策略 95、加载保护 4、文档 16；人物九态静帧、worker 失败诊断 | 源码定向 PASS；九态图不等于动画/语音；当阶段新代码尚未部署至旧候选 |
| 10/18 本地 27B MTP，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-LOCAL-LLM-20261018.json) | 实际 LM Studio SDK 加载参数/草稿接受统计、当前 Python worker 合成材料推理；30.07 秒、73 输出 token、完整最终答案 | REAL 本地 SDK/worker PASS；不是 Core→原生 UI→学习复测闭环，更不是质量准确率 |
| 10/18 用途通道与请求恢复，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-MODEL-LANES-20261018.json) | 前端 162/1569；LM Studio 八项缺失绑定草稿、DEEP 空配置拒绝、原请求恢复五项 RED→GREEN；原生配置保存及冷重开 | 源码、构建和指定候选配置旅程 PASS。原生配置旅程没有启动模型；用户实际工作区绑定仍 UNVERIFIED；首跑保存超时根因没有被“重跑成功”抹去 |
| 10/18 共享会话最新，[回执](../history/repository-consolidation-20261019/current/receipts/AAOS-SHARED-COMPANION-20261018.json) | 新增 14 项共享生命周期回归，前端全套 163/1583；TypeScript/Vite/Tauri/Core 构建；真实原生 home/sidebar/reader 共享草稿及折叠重开 | 组件全套 PASS；原生旅程 **FAIL**：展开侧栏陪伴后导航被压至零高，page14 未到达；未调用模型/worker。不能宣称三槽完整原生验收通过 |

## 3. “全量”的边界与真正验证目标

实际入口：`frontend/package.json` 的 `test = vitest run`，`frontend/vite.config.ts` 默认 `environment: jsdom`。`frontend/src/test/setup.ts` 明确 Range/ResizeObserver 使用无布局的测试实现。

| 验证层 | 重要目标及代表用例 | 仍未证明 |
| --- | --- | --- |
| 前端 Vitest 全套 | 导航及操作调用；中文输入/未知 block 保留；导入摘要不符拒绝；取消迟到响应；权限与恢复阻断；丢 ACK 后冻结原请求防重复；共享会话单次发送 | 原生 CSS 几何、真实磁盘/Core、真实模型、PDF 字形与文本层、冷重启及商业可用性 |
| Python 定向 / quick / full profile | 按实际 targets 验证 worker、启动、目录/归档/供应链工具；`scripts/ci/run_tests.ps1` 解析到 `local_verify.py` 或 `dev.py` | 指定 targets 的 PASS 不能称 Python 全仓 PASS；full profile 也不能自动覆盖前端、所有 Rust、安装和模型矩阵 |
| Rust 路由及集成定向 | 特定 API 的身份、版本、幂等、拒绝、Core/CAS/worker 内容与定位、失败/取消/重开 | 不代表全部 crate/所有格式已验证，也不证明 UI 可操作 |
| TypeScript/Vite/Tauri/Core 构建 | 类型、打包、编译和候选静态成员完整性 | 不证明用户能完成业务、默认路径安装/升级成功或运行性能达标 |
| 真实浏览器渲染 | 既定页面、主题/宽度下焦点、点击命中、滚动、遮挡和几何 | fixture 不能证明真实 Core/模型；有限矩阵不是全应用视觉一致性 |
| 原生候选旅程 | 真正宿主和 Core 上的预定按钮操作、API 结果、内容读回、指定重启/恢复；保留截图、动作和失败 | `--no-bundle` 候选不等于安装版；工程样本不等于新用户测试；没运行的模型/安装分支不计通过 |
| 商用产品验收 | 应检验首次使用、日常闭环、错误恢复、数据安全感、可理解性、性能、安装生命周期和辅助技术 | 当前无完整验收证据，状态 PARTIAL/NOT_EXECUTED；不能由测试数量推导 |

代表代码：`UserJourneys.test.tsx` 明示 SIMULATED 且 mock Core；`CanonicalLibrarySpace.test.tsx` 覆盖 lost-ACK 冻结重试；`CompanionSession.test.tsx` mock Core 并验证共享状态；`DockWorkspace.test.tsx` 将业务 SpaceView 替换为输入框；`PdfReader.test.tsx` mock PDF.js。它们有回归价值，但边界必须明示。

当前核心闭环应逐段核验：保管原件 → 提取/定位 → 阅读编辑保存 → 模型理解/练习 → 人工判断/认可 → 学习复测 → 退出重开/恢复/导出。当前有各段工程证据，尚缺同一当前候选上完整、真实且可恢复的连续验收。普通文档保存不新增模型或人工审批前置条件。

## 4. 商用界面的标准对齐

本次已核对下列原始来源。规范、设计建议和产品自身验收不能互相冒充；ISO 仅核对官方公开说明，没有宣称读取付费全文或取得认证。

| 依据 | 应落实到本项目的判据 | 当前差距 |
| --- | --- | --- |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/)：键盘、焦点、对比度、reflow、目标尺寸、错误识别、状态消息 | 全应用重要操作键盘可达；焦点可见且不被遮挡；文本/控件可读；缩放/窄窗不截断任务；状态可被辅助技术理解 | 当前是部分自制规则和场景；没有全流程屏幕阅读器、缩放/DPI、主题和真实组合的完整验收 |
| [W3C 评估工具说明](https://www.w3.org/WAI/test-evaluate/tools/selecting/) 与[符合性评估](https://www.w3.org/WAI/test-evaluate/conformance/) | 自动化与人工评估结合，明确评估范围和方法 | 工具 PASS 不能升级为完整可访问性符合性声明 |
| [NN/g 十项可用性原则](https://www.nngroup.com/articles/ten-usability-heuristics/) | 用户语言、系统状态、控制/撤销、一致性、防错、识别优于记忆、简洁、错误恢复 | request ID/sequence/BUFFERED 等工程信息四散；新用户能否找到主路径尚无任务观察记录 |
| [Windows 设计指南](https://learn.microsoft.com/en-us/windows/apps/design/) | 明确的信息层级、一致交互、响应布局、可访问性，从整体任务检验各组件组合 | 主题/组件复用已经存在，但展开陪伴挤掉导航说明组合布局未过实际验收 |
| [ISO 9241-210:2019 官方说明](https://www.iso.org/standard/77520.html) | 以实际使用情境和用户任务组织设计、迭代与评价 | 没有完整证据证明已做目标用户任务可用性验证；不能用预先知道按钮的开发者点击替代 |
| [ISO/IEC 25010:2023 官方说明](https://www.iso.org/standard/78176.html) | 质量需求需被明确指定、测量和评价；为可靠性、性能等设置具体项目指标 | 现有单元阈值不等于真实运行基线；缺少代表负载、长时间运行与验收阈值的闭合报告 |

不能说项目完全没有相关知识或调研：已有焦点、键盘、对比度、主题、草稿保护和真实浏览器几何规则。但现有证据**不足以证明已经把商用标准系统地转成“条款/用户任务→页面状态→测量/断言→失败阻断”的完整矩阵**。本次质询前未交付完整专项对齐结论，执行上偏重组件/合同/路由资格；这是应纠正的验收组织缺口，不能让 Owner 反复替项目发现基础体验问题。

“诊断中心”同属产品信息架构：业务页面留结果、范围、实际模型/目的地和可行动恢复；工程状态、ID、原始载荷集中在唯一中心；构建/测试/迁移证据留仓库。该段差距发现时统一中心未实现；第8节记录后继源码、组件与原生修复结果，不回写历史失败。

## 5. 开源吸收为何没有自动变成商用品质

当前研究池 369 候选、701 跨表记录、68 来源和 115 原冲突，是来源与资格台账，不能换算成功能完整度。已有锁定 Radix、Dockview、Tiptap、PDF.js 等实际依赖，也有算法/交互供体、格式规范、未来候选和未采用对象。

实际缺口位于组合与验收：

1. 采用组件不等于继承上游完整产品的信息架构、首次使用、空/忙/失败/恢复状态与用户引导。
2. 上游正确不保证 AAOS 的 CSS、生命周期、模型绑定、Core 权限与持久化组合正确；本轮导航零高和不可见诊断入口是直接反例。
3. 候选登记、包依赖、源码命中和实际产品入口/完整任务验收此前有混淆；已发现并修复扫描器将 XYFlow 的测试正则计作生产吸收。历史资格文件也存在 hash/路径漂移，现按原字节保留，未伪绑当前代码。
4. 目前没有完整证据证明每项已采用 donor 均完成“版本/许可→产品调用点→用户路径→异常/恢复→退出替换”的闭合核验；资产许可与代码许可还需分开。

因此问题不应归结为“再找更多开源项目”。应将已选能力在实际产品主路径中验收；其他候选按原有适配/worker/延期边界保留，不批量安装，不再引入第二数据库或默认模型平台。

## 6. 界面操作实际产出了什么

现有脚本多为固定目标、定位器和断言的旅程，不是全部随机点击；但开发者知道入口的脚本不能证明普通人理解流程。截图/启动次数本身不算测试结论。

| 问题 | 发现与实际证据 | 闭环状态 |
| --- | --- | --- |
| 工作草稿已成功 flush 却不回 ready | 10/16 等待 30 秒、追踪真实 200 ACK；补状态发布，73 定向 + ready 浏览器场景 | 对应源码局部已修复/验证；历史安装分组失败独立保留 |
| 640px 检查器挤占正文 | 真实 Chromium 窄窗失败；被删媒体查询恢复，9 个指定主题/宽度场景重验 | 对应修复 PASS；不是全应用窄窗通过 |
| 顶部搜索打开模拟结果/快捷键职责重叠 | 生产调用点审查；接既有 CommandPalette/Core 搜索，43 定向及构建 | 源码回归 PASS；不推导完整 installed 验收 |
| 导入错误摘要也显示成功 | 控制错误回执复现，修字节摘要绑定，74 定向 | 组件回归 PASS/SYNTHETIC；真实 CAS/格式旅程证据另列 |
| 原生学习回答为空/503/超时 | 真实模型原生旅程保留 worker/请求错误；后继 worker 可区分失败，27B 单独恢复 MTP 并完成 SDK/worker 实测 | 完整当前原生学习闭环仍 FAIL/PARTIAL；不能用 SDK PASS 关闭 |
| 配置保存确认首跑超时 | 原生失败后诊断重跑成功 | 根因 UNVERIFIED；重跑成功不构成原因闭环 |
| 新增：侧栏展开后导航不可操作 | `webdriver-7bd21c8466f0`：真实 1280×800 候选，home/sidebar/reader 五段共享快照通过；父导航13单次原生点击失败。导航自身有矩形，但 overflow 祖先 `space-rail` / `ui-page-navigation` 高度为 0，被展开陪伴挤压 | **OPEN / FAIL**。产品布局缺陷；helper 的 rendered 判定也漏判祖先裁剪。未到 page14、未推理；禁止改 hash/JS click 绕过而写 PASS |
| 新增：原生回执无可见归宿 | `ActivityDock.tsx` 仅 Legacy 挂 DiagnosticConsole；按钮仅 publish，native 无统一中心 | **OPEN / 静态确认**。集中诊断及业务文案收敛待实现 |
| 测试工具误报/资源竞争 | auto 包装层误当唯一滚动容器已修工具且保留 hidden/clip 反例；一次并行重构建造成5项超时，串行同源码1583通过 | 工具问题与产品问题分开；未增超时，不删除失败；不能将工具修复计作产品功能 |

最新原生失败：`.project-local/runs/be268a2d33/webdriver-7bd21c8466f0/tmp/journey/{receipt.json,shared-companion-receipt.json,failure.png}`；失败前后几何在 `journey.navigation_to_full.observations`。清理回读 `remaining_owned=[]`、`cleanup_error=null`。首轮 `webdriver-7c8330edeb2c` 失败也保留。

更精确的原生事实：无模型 baseline `webdriver-e66c56692989` 包含109个记录动作及导入/编辑/审核/学习/复习/恢复读回，工程PASS但 `closed_loop_verified=false`、distill未执行。`webdriver-9d04f7a6575e` 首答实际完成，复测503 `NO_FINAL_ANSWER`；`webdriver-702b412276a4` 复测503 `WORKER_FAILED`。不能把这两项写成“所有首答都失败”。`webdriver-b56cc86a3ef9` 已保存首答和复测，随后 helper 报 `No reachable scroll container`；该报错自身不足确定产品不可达，原因与本轮零高度证据区分。

关闭缺陷需四项同时具备：可重现路径与预期 → 明确根因及变更 → 原始路径重验通过 → 相关反例回归。只有发现、截图、方案或重跑偶然成功，都不标 CLOSED。

## 7. 本次纠偏后的执行要求

继续沿现有队列处理：优先导航可达与诊断入口，随后在同一候选上重验既定关键路径。每次 UI 运行须事先说明目标、起始状态、样本/分辨率/主题、预计断言及禁止副作用；同源无新证据不反复启动。探索性操作先登记发现，再固化确定性回归。

后续每次报告明确：实际 command/targets、源码与候选绑定、mock 边界、PASS/FAIL/skip、证据路径、未执行层级。只有修复公共壳/共享状态或达到阶段关口才重跑相应完整套件；定向测试不包装成全量。全产品商用验收仍需首次使用/日常闭环、失败与取消恢复、退出重开、全流程键盘与辅助技术、真实资源负载、安装升级和许可/退出验证。

本页产出为证据复核与公开标准对齐，**不是新的产品测试 PASS**；未发布、安装、上传原始会话或替换 Green。

## 8. 本轮实际修复与同源重验

[诊断中心收据](../history/repository-consolidation-20261019/current/receipts/AAOS-DIAGNOSTIC-CENTER-20261018.json)绑定 patch `d4b950b990528a9c145f4849bfded534aabd5c68f2dead08c4940ee49445beba`。最终前端165文件1596项全部通过、无skip；每项真实执行名称、源文件和结果已写入[逐用例清单](../history/repository-consolidation-20261019/current/receipts/AAOS-FRONTEND-TEST-CASES-20261018.json)，原始Vitest JSON及日志按SHA引用。这是用例执行清单，仍不是代码/需求覆盖率。

- 唯一App级诊断中心接入native与恢复壳入口，按运行连接/操作回执/对象来源分类；页面按钮打开同一面板，原始payload不改写、不再镜像console。记录只在内存保留，最多50条，非审计持久化库。工作区恢复中的旧记录先隔离，只由恢复后独立`ui_state_read`校验当前epoch/provider/workspace/restore身份后解锁；失败可显式核对，普通CAS或恢复前悬挂读取不能解除隔离。
- 会话页收敛ID、sequence和BUFFERED；冻结确认仍保留问题、材料稳定身份/版本、范围、模型、目的地与预算。候选地址不冒充实际选定地址。共享只读文档展示实际未保存快照，无法预览的未知块显示保留提示，结构原样可查；这不宣称完整富文本渲染。
- 导航保留180px最小高度，展开陪伴有最大高度和自身滚动。新宿主SHA `58de6e036806c2fbd10e4dd247e0761867f3d41fa4add5284ab8f9001080fa24`；宿主/Core/前端全套使用同一patch，TypeScript/Vite/原生编译通过。候选19524、开发运行时19522成员核对通过；旧组件ZIP逐成员保全，不替换Green。
- 原生`webdriver-8c18135a8067`：23个有目标的操作、11份共享状态快照、同进程home/sidebar/reader/full四槽连续性；原失败的parent13→page14实际单次点击通过，完整页编辑返回亦通过。顶部与会话两个入口均只有一个dialog，原始会话payload与只读Core历史核对一致，关闭后焦点返回。限定该1280×800合成工作区，两个原缺陷状态为`CLOSED_FOR_TESTED_NATIVE_CANDIDATE`。进程及端口清理读回为空。
- 本轮无模型、worker或预览执行，冷启0次、草稿不声称持久化；安装/Owner/完整商业验收仍未执行，整个项目仍PARTIAL。更早的模型503/超时与配置首跑超时没有被这轮UI通过关闭。

本轮失败保留：首次12项失败包括旧console出口断言、文案/样式不匹配及两处首个编辑器就绪等待；后者定向通过，限制4个worker后全套通过，未提高等待超时。后继一轮还有文件夹用例在首文件导入后提前断言全批次完成的1项失败；已改为等待第二文件实际结果，保留原哈希/任务ID/来源/数量断言。新恢复竞态另增独立读取和Provider交错回归；最终1596项与构建/原生使用同一patch。不能将这些不同快照的数量相加。

### 从标准到验收目标的当前映射

| 依据/目标 | 本次已得到的证据 | 仍未完成的商业验收 |
| --- | --- | --- |
| WCAG 2.1.1、2.4.3、2.4.7、2.4.11：键盘与焦点 | 诊断Escape/底层检查器不被误关/焦点回落组件回归；两个native入口焦点返回 | 全应用键盘顺序、全主题焦点可见性、屏幕阅读器任务验收 |
| WCAG 1.4.3、1.4.11：文本/控件对比；1.4.10：reflow | 既有局部主题、窄窗与几何场景；当前原生导航零高原路径回归 | 代表页面及全部重要状态的对比度测量、缩放/高DPI/窄窗组合 |
| WCAG 2.5.8：目标尺寸；3.3.1、4.1.3：错误/状态 | 既有部分目标规则与模拟错误/状态断言 | 全流程目标尺寸/例外核验、真实辅助技术中的状态读出 |
| ISO 9241-210 / Windows任务设计 | 能明确列出使用情境、业务路径与工程诊断分层；本轮修复确定缺陷 | 新用户首次使用和代表用户任务观察、成功率/耗时/错误恢复记录 |
| ISO/IEC 25010：可靠性与性能等质量目标 | 明确数据持久化、请求幂等、恢复与性能证据层 | 当前候选连续闭环、代表负载/长时运行、安装升级/回滚、全格式往返和答案质量 |

这些是项目的工程验收映射，不是ISO认证或完整WCAG符合性声明。此前未找到覆盖这些基线并逐条完成验收的专项成果；已有局部知识不能被表述为已对齐商业产品标准。改正重点是将标准落到具体任务和失败阻断，不再追加空泛“全量测试”承诺。

## 9. 本次质询的补充源码核验

本节仅记录只读审计发现，不新增产品测试 PASS，不改写旧失败。10/18 最新1596项前端与原生诊断证据仍绑定第8节源码及候选。

- **真实模型旅程尚未覆盖保存后的用途通道。** `scripts/probes/aaos01_grouped_owner_loop.py:1412` 的 `selected_model` 操作“兼容模式本地回答模型”，没有在该路径先保存 FAST/DEEP 用途绑定。`frontend/src/runtime/modelBinding.ts` 在 revision=0、FAST 时返回 null；`MachineAnswerPanel.tsx:372` 在已有用途配置时使用其模型和预算。因此兼容路径的真实推理 PASS，不能证明“保存绑定→选择通道→首答/复测→冷启”已经完成。配置保存旅程和推理旅程各自通过，也不能拼成这条连续旅程通过。
- **失败诊断没有端到端透传。** 当前 `services/python-workers/machine/worker_machine_answer.py` 已生成安全白名单失败元数据，但 `crates/archeaxis-application/src/executor.rs:428-447` 将失败收敛为 `machine failure: CODE`；`crates/archeaxis-api/src/runtime/colearning.rs` 再保存该字符串并生成503。因此 worker 诊断改进不能表述为 Core/UI 已能还原 provider 失败阶段。这是当前已确认的诊断缺口；历史503的底层原因仍 UNVERIFIED，不能据此臆断是超时或输出预算不足。
- **三次原生失败不同。** `webdriver-9d04f7a6575e` 原答完成而复测 `NO_FINAL_ANSWER`；`webdriver-702b412276a4` 原答完成而复测 `WORKER_FAILED`；`webdriver-b56cc86a3ef9` 原答和复测均完成，随后重启后的文档入口点击失败。最后一项不能归入推理失败。最新诊断旅程未调用模型，也未重走该重启后文档入口，不能关闭这些原失败。
- **质量与执行独立。** canonical harness 对实际模型任务核验身份、授权、非截断、持久化、原答与复测区别及恢复后的旧授权拒绝；工程编写纠正并不证明原答确实错误、纠正提升准确率或模型权重学习。该路径将推理结果明确标为 `EXECUTED_CANDIDATE_NOT_EVALUATED`。

后续使用“全量”一词时，必须同时给出：suite/profile 与实际 targets、源码/候选身份、环境和 fixture 边界、样例及配置范围、实际收集与 PASS/FAIL/skip/deselected 数量、逐用例结果、未执行层级。测试策略的需求基线仍是[前端验收合同](../authority/taskpack-20261013-frontend-ui/01-Frontend-UI/ACCEPTANCE.md)的五条用户旅程和十一种状态；目前没有完整需求覆盖率分母，不发布需求或代码覆盖百分比。


## 10. 模型失败测量信息贯通及候选更新

[失败诊断回执](../history/repository-consolidation-20261019/current/receipts/AAOS-MACHINE-FAILURE-DIAGNOSTICS-20261018.json)记录原答、复测、资料提问、小栖会话四条调用路径：worker白名单测量经typed Executor保留，API失败和持久化失败记录一致，前端统一诊断中心可查。重新筛选字段，剔除正文/推理文本/异常body/stderr；旧String接口兼容。取消或cleanup未确认仍保留UNKNOWN屏障，三次重试上限与只读历史不触发推理保持。资料/会话失败收据在Core重开后原样重放且worker计数不增加。

定向验证：Rust API29项、application42项、durable claim6项、Python合同/worker88项、前端7文件89项全部PASS。各组source patch保留；b组后仅修正前端测试类型收窄，c组构建/前端/native绑定`f6e53ec26fcd5db6292ce5608bb9d50d3a0f3ce1e226dc73391cba96933891d4`。不是全仓测试、代码覆盖率或商用验收。首轮缺字段RED、前端缺字段RED、新测试误用旧按钮文案及TypeScript收窄失败均保留。

TypeScript/Vite/Tauri/Core构建PASS；当前候选host `76a6198e2d9fc364d323d7b1da6cf0618a24731ca91b866fad39a5671eaed7a9`、Core `750c44943ecc8a6f7e3c691992490a6ce75d3a83eadbc99a2c3d24931fdee681`。候选19524/开发运行时19522成员校验通过，八个旧组件逐成员ZIP保全。新原生`webdriver-56d2937cd8bf`固定23步、11份共享快照、导航及诊断入口重验PASS，进程/端口清理为空；该native旅程仍无模型、worker、冷启或安装，不冒充失败provider的原生注入验证。

LM Studio在`2026-10-18T12:56:04.816Z`实际SDK检查在线、loaded LLM为空；这是该时点状态，已下载/已配置不等于驻留或推理资格。历史503底层原因、已保存用途绑定后的真实模型连续学习闭环、安装/完整辅助技术和商业验收仍未完成。本节取代第9节“当前仍丢失”在本次新源码及候选上的描述，历史失败不改写。整体RUNNING_BY_OWNER/PARTIAL；没有提交、推送、发布或替换Green。

## 11. 原生目录 CORS 缺陷与保存 DEEP 绑定的连续验证

[本轮回执](../history/repository-consolidation-20261019/current/receipts/AAOS-SAVED-DEEP-NATIVE-20261018.json)补齐第9节指出的工程覆盖缺口：canonical 原生旅程现在显式在全新隔离合成工作区保存 answer/retest 的 DEEP 用途绑定，经真实界面选通道后执行；不再用兼容模型选择代替保存绑定。已有配置不允许被该探针覆盖。冻结请求、Core解析快照、模型身份、1024输出预算/120秒超时均有断言；配置保存和目录读取不派发推理。

新增路径首跑 `webdriver-d799a69c1103` 发现真实产品缺陷：设置页“测试连接”显示 `Failed to fetch`，在保存/推理前停止。LM Studio目录HTTP200、有所选模型，但两个Tauri Origin观察均无 `Access-Control-Allow-Origin`；此前fetch mock没有覆盖原生CORS。修复为有限原生只读目录命令，仅数值loopback、无凭据GET、禁止跳转、5秒/1MiB/256项上限；不改LM Studio全局设置，不新增推理或自动回退。原失败、截图和只读HTTP观察保留。

验证分组而非“全量”：前端5文件48项（SYNTHETIC/jsdom）、Rust原生目录5项（真实受控loopback HTTP，95项filtered）、探针合同50项及145 subtests分别PASS，保留各自源码摘要。TypeScript/Vite/Tauri/Core构建PASS；最终构建及native绑定patch `700392b0e69d8a94ddaced49bce142260f2250ace62a59469894391f23764bc1`，host `824c800dfe9cca18d9c288eb97da58d581a922959d51f9b6af53f0924c0cf587`、Core `750c44943ecc8a6f7e3c691992490a6ce75d3a83eadbc99a2c3d24931fdee681`。候选19524/开发运行时19522成员核对，八个旧组件ZIP逐字保全。首次测试launcher不支持test命令、Rust测试缺路由frontend配置是设置失败/NOT_EXECUTED，均未计为产品PASS。

原路径重验 `webdriver-8a003abdb645`：172个记录动作、6次宿主启动，目录检查→保存DEEP→首答→作者编写的纠正与采用→复测→普通重启读回→备份恢复读回→旧授权拒绝，工程断言PASS。实际27B `aaos-deep-27b-mtp` 两次推理均 requested/observed一致、finish=stop、未截断；首答92.25秒、258输出token，复测45.88秒、137输出token。配置保存本身推理0次；重开/恢复不新增推理，旧授权返回 `RESTORED_GRANT_FENCED` 且任务不增加。拥有进程及端口清理读回为空。CORS缺陷在此候选原路径范围为 `CLOSED_FOR_TESTED_NATIVE_CANDIDATE`。

必须保留的限制：该旅程仍明确 `engineering_status=PASS`、`status=PARTIAL`、`closed_loop_verified=false`；作者纠正不构成原答确实错误、纠正提升质量或模型学习的独立证据，结果为 `EXECUTED_CANDIDATE_NOT_EVALUATED`。本轮只是文本/Markdown合成材料、真实本地模型及未安装候选；没有完整五旅程/十一状态、安装生命周期、物理IME、完整辅助技术、性能和全格式往返验收，也未读取或修改用户实际workspace绑定。历史503与首跑保存超时的原因仍UNVERIFIED。最近一次前端全套仍是第8节1596项旧快照，本次48项不能替代它或宣称新源码全套PASS。


## 12. UI 工具审计整改与同源复测

[整改回执](../history/repository-consolidation-20261019/current/receipts/AAOS-UI-AUDIT-REMEDIATION-20261018.json)绑定 HEAD `fe18fdc3cbcab9a0f84a02c5a4db1b6bcef13f46` + dirty patch `cf2e605e09574acdd4c10560a0ee3a07750be20c46e14c2eb2e51513cb7bb204`。本轮五项：顶部设置接受保护导航、Dockview兄弟关闭控件消除交互嵌套、命令搜索改为任务目的、窄窗按需检查器及冷恢复单组标签、平台快捷键提示统一。原五项在限定生产bundle/模拟Core浏览器范围为PASS；整体仍PARTIAL。

最终前端**168文件1632项**全通过，无skip；最终定向11文件143项、TypeScript/Vite构建和浏览器13项通过。四组输入patch一致。axe10扫描0违规但有15条incomplete；15张截图实际查看。全套仅指Vitest前端测试集，不代表全仓、需求覆盖率、原生安装或真实Core/模型资格。精确命令、时间、退出码、失败历史、文件hash及清理在 `.project-local/runs/be268a2d33/ui-remediation-browser-1018c/artifacts/ui-pilot/REPORT.md` 与机器回执。历史168/1631属于前一patch，未替代此最终结果。

窄窗640×800在脚本先修正hash冷启动和标签定位后，仍实测正文y831.5失败；根因是恢复后活动组未建立，普通导航意外另开分栏。新增RED（实际2组）→明确选择已有组within→保留用户主动分栏/浮动，最终正文y655.5、宽536，检查器显式开关与键盘回焦通过。所有原失败保留。

**UI-FOLLOWUP-006 / P2 / PARTIAL**：标签关闭/切换后全局标题仍可能显示原页面，实际Dock已回退其他页；07b截图标题17/内容01。HEAD和当前都没有活动面板向App导航状态同步，只读复核确认原有独立缺陷。下一最小修复须覆盖草稿/恢复/文档身份/业务家族与同页重开，不能简单回调绕过保护。未把该项、通知头像静态问题、完整辅助技术/性能/全格式/安装写为完成。三轮拥有进程和端口全部退出；本轮无提交/推送/发布/Green替换。


## 13. 2026-10-19 图谱吸收及 UI-FOLLOWUP-006 收敛


[图谱/界面报告](AAOS-OSS-UI-DONORS-20261019.md)与[收据](../history/repository-consolidation-20261019/current/receipts/AAOS-NEURAL-GRAPH-ABSORPTION-20261019.json)记录 Neural Creator 固定SHA的MIT几何/视觉适配：星团展开、稳定布局、邻域、曲线/粒子、缩放平移及动画降级接入现有SVG，固定引用与Core写边界保留。中文标题、密集曲线有界及展开卡片遮挡已修复。UI-FOLLOWUP-006 已在本次限定浏览器范围关闭，保留草稿/恢复/文档对象/导航保护，锁定迟到读取和显式恢复身份有回归。

最终HEAD `fe18fdc3cbcab9a0f84a02c5a4db1b6bcef13f46` + dirty patch `0c32b22ef72b3a11f94164019166154e5a0484f85d0c30ad3165901670edc87d`：前端171文件1661项、TypeScript/Vite、14浏览器检查PASS；14组axe0违规/23条incomplete，20张截图实际查看。浏览器是真实Chrome+生产bundle、SYNTHETIC Core；新图谱原生/安装、真实Core、上游逐像素、FPS/GPU/内存与完整辅助技术未验。拥有进程与41730端口退出读回为空。历史失败不重写，整体仍PARTIAL。

三个固定版本已归档：Neural43成员完整源码；GlassBoard3Markdown，因主源码/许可缺失仅设计参考；[OpenMAIC研究](AAOS-OPENMAIC-ABSORPTION-20261019.md)保全18个关键源码，建议先课程/测验adapter，完整Next/Postgres课堂服务、任意HTML、语音视频HOLD，适配尚未实施。增量任务与验收见`workspace/intake/20261019-oss-graph-and-classroom.md`，不另建权威队列。无提交、推送、发布、安装或Green替换。
