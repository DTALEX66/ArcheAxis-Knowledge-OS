# 星环知识系统：完整会话交接提示词（2026-10-28）

你正在接手 ArcheAxis Knowledge／星环知识系统。请先完整阅读本提示词，再核对当前项目文件。本文件是冻结交接快照；实际授权和进度仍以活动指针、最新 Owner 指令和唯一执行记录为准，不另建第二份可变任务账本。

## 0. 第一条：接收交接，保持暂停

- 当前执行状态是 PAUSED_BY_OWNER。官方订阅额度上次观察为 used90／remaining10，观察时间在 2026-10-27T21:42:44Z 之后；secondary 未知。
- Owner 指令：剩余额度 <=10% 时停止新开发、构建、测试、补拍，安全封存，整理问题、阻塞与交接，上传授权公开成果；仅合并检查和审查满足条件的必要分支，读回对应双端 SHA，然后暂停任务及额度监控。
- 任务目标和单一 heartbeat automation 均已暂停。监控 id=automation，原间隔30分钟，目标旧会话 01a1738b-5d55-78d0-8fa1-4783332f1cf4。不得建立重复监控、擅自迁移目标会话或自动重启。
- Owner 此次“梳理全部对话、给完整交接提示词、开启新会话”和“给权限／读取私有记忆索引给权限”，用于交接、新会话及本项目相关索引查询；不自行解释为恢复产品开发、放宽10%规则、付费、云端外发或全局配置授权。
- 新会话第一轮只接收、只读核对本提示词／指针／当前工作区，简要确认已接续并继续暂停。不得自动启动 CI 查询、模型、Host、VM、测试、构建、截图、清理、发布或合并。
- 只有 Owner 明确恢复后，才重新读取官方额度并按当前规则判断可执行范围。额度重置本身不是恢复指令；若仍 <=10%，保持停止。
- 若新会话有目标管理，不要另建一个活动目标来覆盖本项目的暂停。不能把换会话写成项目完成。

## 1. 项目身份、入口和执行边界

项目根：D:\All projects\ArcheAxis-Knowledge-OS
仓库：DTALEX66/ArcheAxis-Knowledge-OS
旧主会话：01a1738b-5d55-78d0-8fa1-4783332f1cf4，标题“重新审计界面与能力展示”
审计会话：01a17d5d-24fe-75f0-b799-41ca380facc0，标题“对抗审计界面设计”
审计会话链接：codex://threads/01a17d5d-24fe-75f0-b799-41ca380facc0
旧 TRAE 接续会话：01a1694a-29ee-7612-bd5f-ec5aeccc1be9，标题“1023”

必读顺序：
1. 根目录 AGENTS.md。
2. docs/current/AAOS-ACTIVE-EXECUTION.json：分别看 owner_scope_current、execution_control、permission_recovery_current、allowance_guard、active_progress。
3. docs/current/AAOS-AGENT-HANDOFF-CURRENT.md。
4. 唯一执行记录 docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md，尤其末三节：
   - 2026-10-28 额度10停止与接续交接；
   - 2026-10-28 Owner取消全量截图交付并清理副本；
   - 2026-10-28 新会话交接已整理（本次登记）。
5. docs/truth/CLOSED_LOOP_DEFINITION.md（AAOS-SHORTEST-COMPLETE-LOOP-V2）。
6. 需要实施时再读所选任务包 docs/taskpacks/aaos-ui-first-20261009/ 的 TASKPACK.md、TASKS.json、PAGE-PLAN.csv、FREEZE-REGISTER.md 及相关任务，不重读无关全套历史。

其他规范入口：PROJECT_CONTRACT.yaml、docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md（尤其19、22、23、24节）、docs/current/AAOS-AUTHORITY-ROUTES.json、docs/CONFIGURATION_AUTHORITY_INDEX.md、docs/truth/NAMING_CONTRACT_V2.md、docs/truth/CAPABILITY_ATLAS_V2.yaml。旧文件和原材料先查 AAOS-资料索引.md 及已登记历史索引；链接是导航，不产生跨目录授权。

正式宿主为 frontend/ + src-tauri/ 的 Tauri2／React；Rust Core 是唯一 canonical SQLite／CAS 业务写入者，Python 是隔离 worker。不得双写旧库或新建第二套业务真值、能力登记、Agent Runtime、进度表。V01／FT01—04和可选复杂增量按指针继续冻结。

## 2. Owner 的全部核心要求与最新取舍

### 2.1 UI目标

- 主要问题是菜单导航、布局、任务组织和空间分配。保留已选“顶部菜单＋浮动主工作窗＋人物／资料侧窗＋Dock”架构，避免重新换成固定侧栏模板。
- 主工作区应充分利用顶部导航和 Dock 之间的高度；围绕1920×1080检查实际可用空间、文字和溢出。不能擅自修改整个系统显示分辨率，也不能把图片缩放后冒称原生1920画面。
- 卡片底色过蓝，玻璃质感廉价：需要从面板底色、透射、遮罩、层级、模糊、边框、阴影、文字对比整体修正，不能只叠高光。降低重复套卡和说明块的竞争。
- 精修菜单归属、导航重叠、对象Tab、阅读空间、工作模式、人物收起后释放空间、教学各阶段差异、AI资产／上下文过度分栏、任务与历史回答布局。
- 处理各类交互和动画：进入／退出、悬停／按压、菜单／面板、加载、成功／失败／取消的反馈；尊重 reduced-motion、键盘焦点及可访问性。优先成熟组件，避免用动画掩盖卡顿或失败。
- 原生功能右键已存在，后续核对对象相关性和实际功能；不要又描述成“完全没有右键”。菜单不应堆满无关全局命令。
- 首次引导已存在，后续要让新用户完成有价值的实际任务，而不只是核对说明或登记表。不得再误报“完全没有首次引导”。
- 能力目录与未来蓝图已显示16族／186设计项；必须清楚区分已可用、接口、规划、延期。186项展示不是186项实现。不能因目录完整就宣布产品功能全完成。
- 普通用户界面继续统一白话，必要工程细节收进明确的诊断／高级入口，不把导入的原文或用户主动打开的诊断误报成UI泄漏。

### 2.2 错误反馈与“总日志”的正确拆解

用户原话意图：各个操作环节出问题，不要直接冒代码和工程词；用白话解释发生了什么，告诉用户内容是否保留、现在能做什么，并有统一问题记录。

- 可恢复小问题用行内／轻提示；只有真正阻断当前任务、需用户决定的错误才用弹窗，不让轮询失败反复抢焦点。
- 解释事件、影响、草稿／已保存内容、下一步；数据安全状态未知时如实说未知，不能空口保证全部保存。
- 已存在 Core 持久问题日志，并非待从零搭建。要补应用级渲染、异步／事件异常及必要前端失败的覆盖。
- 不记录正文、原始异常全文、堆栈、路径、URL、密钥或凭证到自动持久日志；详细原始回执由用户主动打开，按当前会话内存处理。
- 未确认的写入结果不得自动重试／重放；异常兜底不能通过卸载整个 App 丢掉多页面草稿。
- 用户没有要求完整的成功操作遥测／企业审计平台，不能把“总日志”扩成新大框架。

### 2.3 人物目标与取消项

- Owner不满意人物外观、大小和与工作界面的关系，希望继续深化人物质量、动作和交互。
- MiniMax 会话456614733140144“小栖管线接入”的那批素材，Owner先授权仅查看和下载，后明确说“不要了，太丑了”。这批素材已取消；不得再访问、下载、等待URL、集成或追问。
- 取消这一批不等于人物整体目标取消。当前 studio-v3／raster2D 仍为静态人物，不能称为Live2D、真实口型、动画完工或Owner已接受。
- 后续方案先研究成熟开源／合法资产和实际接入成本，结合人物可见度、工作区模式、状态动作、任务联动提出并实现有限可用方案。独立质量验收仍需Owner判断。

### 2.4 成熟方案优先与来源定位

- Owner反复要求：先检查已有成果、网上成熟方案、开源项目和官方API，能直接集成就优先集成或适配，避免重复自研拖慢项目。
- 评价适配、许可、维护、免费范围、依赖、隐性成本；不因为开源就认定托管API免费无限。
- 来源记录是为了回查、定位、多源比较与纠错，尤其防止模型识别／转换错误。它不天然高权威，也不是唯一事实源。
- 忠实度对照原件，事实主张和疑点通过百科／维基、社区论坛、学术科研多源比较；保留支持、反对、分歧和可修订性。
- 网络结果不得自动覆盖原件，普通保存／展示／学习不得以联网成功或人工事实审批为前置。
- 已更新定位、描述和相关规范：SUP-029、Owner决定24节、PROJECT_CONTRACT.yaml.content_policy、PRODUCT_IDENTITY_V2。规范更新不代表百科／论坛等所有真实API已接通。
- 软件配置的权威、Core单写者、人工知识晋升和材料外发权限，仍是各自独立边界。

### 2.5 并行和沟通

- Owner明确要求实时并行智能体，不要反复提醒后才并行。
- 恢复实施后，对独立任务分派独立writer，避免共享文件并发覆盖；源身份冻结期间不要交叉改源码。并行不等于同时启动多个Host／安装环境。
- 清楚中文，先结论，再依据、影响和下一步。必要澄清不要反复要同一权限；普通可逆实现细节自行判断。
- 长任务至少每60秒提供有意义进展，不能把反复检查或规划当交付。
- 本次接续只做交接接收，不因为这些工作偏好突破暂停。

## 3. 最新截图决定：任务已取消，不得重新启动

Owner最新原话：“补齐最新截图包 不要再做了 该删掉的删掉 随你修复更新UI界面的时候自行截图审计 昨天已经审计完成了”。

- 已撤销独立的完整截图包任务、31项缺图补拍、全菜单全环节重采、离线图库重做和云端外发包制作。记录为Owner取消，不是未完成阻塞，也不是采集全覆盖PASS。
- Owner确认昨天审计已完成。沿现有审计结果修复UI；以后只对本次改动相关页面／状态按需截图、自查、改正、保留必要证据。
- 不重做已完成的整轮静态审计，不追齐历史31项，不建立周期截图或截图包自动化。
- 曾经制作的V13双包绑定87777c77源，不绑定a45。1,149张原图仍保留在各自原始运行目录。
- 本次已删除4个冗余交付目标：.project-local/ 下“星环界面审计-20261028-87777c77-V13-原始PNG”目录、“云端JPEG90”目录及对应两个ZIP。
- 删除4,714个文件、2,513,748,573逻辑字节（2.341GiB）；这是逻辑量，不冒称磁盘空闲空间净增。
- 原图1,149份已逐张哈希核对，删除后再次核对；18份清单／说明／附加审计元数据已按原字节保留。原始收据、独有失败截图、审计报告、原件、业务数据、最新候选和构建缓存未删。
- 清理计划／结果：
  .project-local/runs/be268a2d33/ui-audit-package-retired-20261028/artifacts/cleanup-plan.json
  .project-local/runs/be268a2d33/ui-audit-package-retired-20261028/artifacts/cleanup-result.json
- 历史V13 ZIP链接已失效，不得再次给用户当可下载完整包。保留历史记录和失败，不改写旧回执为PASS。
- 旧审计截图集与V13运行图是不同来源；不能混图绑定源码。不要为节省空间删除尚无替代的唯一失败证据。

## 4. 分支、上传和当前未提交文件（要特别保护）

当前本地实际读回：
- branch：trae/20261024
- HEAD 与本地 origin/trae/20261024：a45de651cfbb3604acd82a61a01a9a10ad6cbbfd
- local main 与 origin/main：8d367bac4a85bebfbb523503678ade0838faa73e
- PR203：https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/203
- 当前SSH remote：git@github.com:DTALEX66/ArcheAxis-Knowledge-OS.git（真正执行时仍核当前URL／rewrite／SSH覆盖）

最后一次真实远端读回为2026-10-27T21:48:23.4399844Z：本地HEAD／origin跟踪／真实远端分支／PR head均a45，main对应两端均8d367bac；PR OPEN／BLOCKED。此后没有再次联网确认，不能把这份快照冒称新会话实时远端状态。
收据：
.project-local/runs/be268a2d33/allowance10-handoff-a45de651/artifacts/delivery-readback.json
SHA256：41403aa8f08335f63b755f7b48586c1aedcea79b8969662f0873b6e556ec461a

已上传主提交：
- a45de651：Clarify local error feedback and seal allowance handoff，9个公开文件。
- 4c8cdc1f6902c595ded194c473a2b998cfce92cb：Repair CI fixtures and preserve native exit diagnostics，8文件。
- 87777c773dd103bea4a613f45f7db621b3f28edd：V13交付／规范。
- 9b92625cb5120a16f371c548319e270aca4fc740：契约／启动。
- 146a2dc641210d86032bcdb6e81249a02810cf41：持久问题日志／文案。

旧 codex/sync-20261019 的 b4588d7669cd469ea5d1efed379a93676e92d2cb 已核为4c8祖先，后继已包含；不要重复合并、重置或清理分支。

本次取消截图与交接导航改动尚未提交／推送：
- docs/current/AAOS-ACTIVE-EXECUTION.json
- docs/current/AAOS-AGENT-HANDOFF-CURRENT.md
- docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md
- 本提示词 docs/history/session-handoff-20261028-ui-followup/README.md（新文件）
这些是本轮交接拥有的写集，未来交付时只能显式stage相关文件，不能git add .。暂停时不为“工作树整齐”擅自提交推送。

以下6项是原有dirty/untracked，已保全，不纳入本轮提交、不回滚、不删除：
1. docs/history/project-drift-audit-20261021/MANIFEST.json
   92f18d734f2bd3c035455f8798702600d479c62413efed357addb42ba4797112
2. docs/history/project-drift-audit-20261021/stitch-visual-pause-20261022.json
   7a6e77ca238de17c245fcf76e7f05481befde39b38b8fb08252dcaae2b7ed8d0
3. scripts/probes/aaos_collection_reader_browser.py
   589817a29353755a587b3dbee702b9b2fad50a378f3e564a2f0567a37777eabd
4. scripts/probes/aaos_collection_reader_runtime.py
   b95c0a520c6538d993ec72790db34541fe0d513727c0d47d1ec12c8df0e711c5
5. frontend/src/assets/brand/aaos-logo-light.svg（原untracked）
   e570f7fc4e598692ddbb72a243f8e5df441fb6e1e1de1e9069542cd52ca8e6c0
6. workspace/intake/20261025-codex-handoff.md（原untracked）
   68ec28efe04d4a8b464a43cf05ab3110f5e58213ec1713bb1b4cd2ca63fbe7ca

保全清单：.project-local/ui-polish-protected-source-seal.json
保护项补丁身份：54d4c73f21e624418b1cc00844aeaeb20ff20b346be06c96b6b3318d35723db8
不可把“对应提交曾双端一致”写成整个工作区无改动或所有文件已上传。运行数据、日志、缓存、虚拟环境、截图及便携候选不上传Git。

## 5. 已完成的实施与验证，各层分开

### 5.1 原始af1审计与后继修复

原版本af1ac68b／PR203的五项：
- P1：多页共享legacy草稿状态导致B保存可能解除A保护。
- P2：备份创建清单不限制，读取却拒绝>1MiB；15,000来源合成已超阈值。
- P2：不存在的相对TESSERACT_CMD误判可用阻断回退；重排文字与“保持原序”回执冲突。
- P2：SVG末尾换行／探针sys.path检查失败，PNG／ICO声明大小及摘要不符。
- P2：菜单12px与有效标准至少14px冲突，不能直接放松断言。

已有对应源码修复和分层验证：独立页面草稿标识／生命周期保护，备份一致预算与坏备份隔离，实际OCR可执行验证与回执，资产／规范修补，菜单>=14px。曾对15,000来源实际CAS备份创建／列出／预览／恢复及坏邻居验证；但不因此宣布所有大库风险结束。

原始全量结果必须保留：
Python6030通过／18失败／124跳过／12初始化错误；
前端2198通过／1失败；
Rust1035通过／16失败。
环境修正及后继测试另列，不能覆盖原始结果，也不能把风险写成已发生真实数据事故。

### 5.2 V13原生UI与候选

- 导航16项隔离检查通过：22页、7菜单>=14px、5主题、3布局、3条引导路径、10参考步骤、4类原生右键、能力启动台／16族／186设计项、多页草稿与原生取消／保存退出等。
- 18格式只读重开119图通过；教学6条保存状态只读重开，不是新模型／转换／教学写入，第5条assisted=false差异原样保留。
- 分组只读采集437张部分画面，parent仍FAIL／child仍原RUNNING，18条派生页面索引修正有来源；31项缺图任务现已取消，不需要再补。
- 原生持久问题日志：真实只读404→自动受限日志→冷重启保留→主动清空→第二次重启为空，三次Host正常退出且清场。
- 这些都是隔离合成环境的对应候选证据，不是Owner视觉验收、全部业务闭环或当前最新源码安装资格。

V13候选绑定：
source87777c773dd103bea4a613f45f7db621b3f28edd + protected patch54d4；
Host SHA256 7eb72f70c99ebef5a0146a8bdbe1041c4d5d9bc5ab8eb71bcf519771ed60abbf；
Core SHA256 40b563626a07c5bd9658da9b1b8a8c2289bf930e4d9fbbf4b39b20fe7909db30。
便携程序：
.project-local/runs/be268a2d33/ui-audit-remediation-v13-portable/artifacts/星环便携候选/ArcheAxis.exe

.preview入口：
.project-local/AAOS-UI-Preview-20261026.cmd
r3 --check已通过，入口目标更新到V13，但没有因此实际启动；既有Owner预览与其数据不擅自操作。新会话不因看到路径就打开。

### 5.3 持久问题记录与最近两处文案

Core已有工作区问题存储 workspace_meta.operation_failure_log_v1：
- 最近50条／64KiB预算，有限操作、原因、状态、时间、次数；
- 工作区／恢复epoch／日志generation事务校验，清空后迟到记录不得复活；
- SQL截断受限读取，65537边界拒绝大于预算的原值；
- 自动摘要不持久化正文／路径／URL／秘密；原始回执主动查看；
- Core离线或工作区身份未知时只留会话记录，不伪称已持久化。

a45两处组件：
- BoundedJobPanel：状态读取失败用白话，保留已接受任务、处理进度与未知写入结果；详细异常仅内存主动查看，不自动重试。
- CollectionPanel：JSON／结构／引用验证失败显示白话并保留输入，原始原因仅主动诊断；原规则继续拒绝非法内容，不扩大自动日志采集。
- 两份对应现有测试更新，新增真实组件故障用例。
- 40项组件测试及TypeScript均通过，观察源码4c8+fd4053ad2015c82ec4686d4c61319ef2031f0b96e195af36e5ed205262e81bf8。
- 没有对这两处最新组件重新构建／原生验证。不能把V13旧像素改绑a45。

相关源码：
frontend/src/main.tsx
frontend/src/app/App.tsx
frontend/src/components/BoundedJobPanel.tsx
frontend/src/components/CollectionPanel.tsx
frontend/src/lib/（沿现有错误和日志实现查找，不新建第二库）
相关需求拆解：
workspace/intake/20261028-plain-language-errors-and-activity-log.md

## 6. CI、安装失败和最后修补：必须分清版本

### 6.1 a45最新CI

run40589633273：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/40589633273
head a45de651cfbb3604acd82a61a01a9a10ad6cbbfd。
暂停时仍in_progress、无终态，之后没有查询。不写“当前仍在跑”、不假定成功或失败。仅Owner明确恢复后读取真实最新head／终态。

### 6.2 4c8完整CI实际终态FAILURE

run40583820273：
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/40583820273
15成功／2失败／3策略跳过：
- installer-lifecycle job122481188911失败；
- a0-gates job122483805089为依赖汇总失败，不是另一个独立产品根因。
实际日志：
- Python3.12：6175通过／0失败／116跳过／14warnings／485子测试通过；
- contracts：261通过／29子测试／10warnings；
- Rust：214条Cargo汇总合计1074通过／0失败／0ignored，含8条doctest汇总。
日志中个别旅程UNCOMMITTED标签保留，不扩大为installed资格；实际CI是PR临时合并checkout，不冒称本地持久提交。

最近安装失败：
- 普通保存、多页草稿旅程均ok并正常清场。
- 分组在学习者自评SELECT前置指针证明失败；pointerdown命中SELECT，约678ms后pointerup／click到DIV，按键尚未发送，没有重放。
- failure.png实际显示原生下拉已展开且占位项未变。一般按钮“三事件同目标”证明不适配这次原生SELECT情景；DIV具体身份和重定向机制未知，不能直接判产品按钮坏。
- 该次退出ACK32ms、请求至等待返回172ms、Host0且进程／端口清场；没有独立Core GRACEFUL报告。
- 还没到旧 capability_refusal_recovery→restart→第二退出路径，因此不证明旧退出超时已修复。

a45最小探针修补：
scripts/probes/aaos01_grouped_owner_loop.py 首次自评一处调用，由 ui.keys(select,Down×3Enter) 改为已有 click_selector→click_native_option，明确选择value='3'“一般”。
产品原选项是占位＋1忘记／2困难／3一般／4轻松共5项。未改产品、不放松通用button证明、不改其他keys、不新增宽泛SELECT框架、不重放旧业务。
tests/test_grouped_native_owner_probe.py 增加AST实际调用验证。
ci4c8-select-option-narrow：5通过／74未选／6子测试，无Host／浏览器；只构成局部验证，仍需新原生与安装检查。
收据：
.project-local/runs/be268a2d33/ci4c8-select-option-narrow/artifacts/execution.json

### 6.3 旧877 CI失败另留

run40572616434：12成功／5失败／3策略跳过。
旧原生安装有15秒正常退出超时，发生于capability_refusal_recovery重启后；第二次清理请求正常0不能将首次超时改判PASS。根因当时UNKNOWN，Core关闭阶段证据不足。
4c8加入退出被动诊断，未增加15秒期限、未增加IPC或改变Host策略。
旧fixture153个摘要引用／CI临时checkout分类／Rust格式等已经4c8修复；不再把它们误列成尚未改源码。真实后继CI仍按各head判定。

## 7. 已完成静态审计的24项，继续做修复，不重做整轮审计

审计报告：
.project-local/runs/be268a2d33/ui-adversarial-20261027-r2/artifacts/UI-对抗性审计报告.md
同目录 findings.json、findings.csv、audit-receipt.json、审计证据.html。

原审计为764图清单核验、32张总览、67张原图精读；24项=7P1／15P2／2P3。它是静态设计／源码审查，不是24个已复现的软件故障，报告自身没有重新做交互、axe、性能或安装验收。

P1：
UI-01 导航职责和页面归属不统一；
UI-02 页面外壳挤压阅读正文；
UI-03 人物模式不对应工作空间模式；
UI-04 教学阶段沿用同一登记表；
UI-05 AI资产／上下文四窄列；
UI-06 保存状态所属对象不明；
UI-07 任务页运维配置突出、历史回答过窄。

P2：
UI-08 图谱被控制说明推后；
UI-09 依赖对象详情误作平级入口、空态缺下一步；
UI-10 页内详情与全局检查器重复占位；
UI-11 Tab只按功能页累积、对象／阶段不清；
UI-12 导入入口与故障规则混排；
UI-13 学习对象藏在禁用动作之后；
UI-14 引导入口未突出首先获得的价值；
UI-15 提示卡透底影响可读性；
UI-16 可用能力与未来规划动作暗示相似；
UI-17 能力详情被治理说明淹没；
UI-18 开发供体登记占普通资源首页；
UI-19 页面／能力／内容搜索类型层级不足；
UI-20 对象菜单混入大量全局命令；
UI-21 原件／转换／笔记／其他文档之间来源连续性不足；
UI-22 画布节点／连线／保存历史纵向分离。

P3：
UI-23 套卡、边框、说明块同权重；
UI-24 日常时间、ID与术语工程化。

有些后继已有源码和隔离原生改善，必须按最新源码／实际页面逐项确认；旧24项映射绑定8b89，不得直接把全部CLOSED。Owner视觉接受仍未完成。不要为追求形式上的全绿再做一遍全量截图包。

## 8. 未完成任务与明确恢复后的执行顺序

以下是剩余目标，不是现在启动指令。

P0／交付资格：
1. 核实际git状态、保护6项、当前PR head和a45后继真实CI；不要重跑已经成功且未变化的检查。
2. 修复真实剩余CI故障，复验原生自评选项路径与旧退出路径；保留旧失败，分清探针缺陷／产品缺陷／环境问题。
3. 必需审查及检查通过后才正常提交、推送、合并，逐端读回SHA。不要强推、admin绕过、为合并而放宽断言。
4. 最新候选、安装、业务闭环和Owner验收仍分别有缺口，不能由CI通过自动发布或替换Green。

P1／错误与草稿可靠性：
5. 应用级渲染兜底，异步／事件错误处理，有限前端失败纳入现有问题记录；保护多页草稿，不用重挂整个App丢缓冲。
6. 验证白话反馈真正回答“发生什么、影响什么、内容状态、下一步”，适当弹窗而不滥弹；技术详情主动打开。
7. 多页面恢复前的草稿检查要具体验收，不以普通退出保护通过替代恢复场景。

P1／UI结构和视觉：
8. 依原24项审计优先修导航／对象模型、正文空间、人物与空间模式、教学分阶段体验、AI工作区、任务与历史回答；再做材质、颜色、动效、术语和可访问性。
9. 引导、右键、目录都已存在，继续按新手真实任务完善与必要交互验证，不从零重复造壳。
10. 人物整体质量方案与有限实现，禁止重启被取消的MiniMax素材任务。
11. 只对当次修复按需截图审计，无“补齐完整截图包”待办。

P2／原审计专项风险：
12. 大库恢复完整RSS／SQLite C侧内存占用；
13. 恢复与授权失效处理之间的物理断电／崩溃窗口；
14. 多栏OCR代表性样本的顺序、回退和处理回执一致性。
这些属于未验证风险，不是已发生用户数据事故；要按最小有效实验实证。

本期业务必备：
15. 同一合格候选完成下列人类＋AI＋两侧授权复用、三类真实免费检索、本地真实模型与专业云接口、本期常用格式、保存／重启／导出／恢复。
16. 核清已承诺格式和已选非企业知识库特色的实际能力／方向／损失，不用格式扩展名识别或Markdown导入冒称全面兼容。
17. 复杂扩展保留具名延期，不因开源库存很多无限扩张当前任务；兼顾快速可用和长期目标。
18. 清理仅在有明确归属、可再生／替代证据、没有占用且Owner授权的范围内进行，保留最新构建缓存，不反复进行大盘扫描。

## 9. 完整业务闭环不能缩水，也不能扩大首版硬门槛

总状态 PARTIAL。以 CLOSED_LOOP_DEFINITION.md 为唯一完整定义：
CL-01 核心一致性；CL-02 常用多格式；CL-03 百科／社区论坛／科研三类免费实际检索与比较；CL-04 已选成熟知识库个人特色；CL-05 成熟开源吸收及有限扩展；CL-06 模型接口；CL-07 同候选可靠性。

人类侧：资料进入→识别定位→研究比较→知识候选／必要接纳→展示学习复习→纠正→重启／导出／恢复。
AI侧：经验候选和证据接收→验证去重→冲突／适用性审查与必要审批→知识资产→授权检索使用→纠正复测修订→重启恢复。
双侧：按权限复用同一来源／版本知识与证据，不把AI输出自动当权威，不把教学记录等同人的掌握度。
外部原始跨项目／Agent上下文 provider 仍 NOT_CONNECTED；离线候选导入不代表外部连接已通。

本期首版模型门槛：既有本地模型真实使用＋专业云端接口边界。
Owner2026-10-24已明确真实云推理延期，不是当前首版硬阻塞；不得再次等待用户选云服务商才做可用产品。也不能假装云端已接通。
沿既有LM Studio路线和原配置；不擅自换provider／端点／模型／鉴权，不自动回退Ollama，不借凭据、不付费、不发私有资料。

J1混合资料→知识→重启导出恢复；
J2三类检索→比较冲突→候选接纳→重开；
J3本期知识库特色实际使用与关系连续性；
J4本地真实模型／纠正复测与云接口边界；
J5本期扩展的真实消费者及停用／回退；
J6隔离安装／升级／异常／恢复／性能与回滚。
所有维度按本期有限清单验收，同候选和真实对象贯穿，不能把不同旧分支局部PASS拼成完整闭环。

## 10. 证据路由与工具注意事项

常用证据根：.project-local/runs/be268a2d33/
- ui-audit-remediation-v13-native-navigation/artifacts/native-ui-remediation/receipt.json
- ui-audit-remediation-v13-persistent-log-20261028-r2/tmp/journey/receipt.json
- ui-audit-remediation-v13-readonly-grouped-20261028-r4/tmp/journey/receipt.json
- ui-audit-remediation-v13-readonly-formats-20261028-r1/tmp/journey/receipt.json
- ui-error-copy-consumers-20261028-r1/artifacts/（40组件）
- ui-error-copy-consumers-types-20261028-r1/artifacts/（类型）
- ci4c8-select-option-narrow/artifacts/execution.json
- ui-ci4c8-head-preflight/artifacts/local-ci.json（4c8的20检查，不是a45）
- ui-ci4c8-python-connector-r1/artifacts/decoded-job.log
- ui-ci4c8-rust-contracts-seal/artifacts/rust-contracts-seal.json
- ui-ci4c8-installer-artifact/artifacts/installed-native/（原始失败）
- allowance10-handoff-a45de651/artifacts/delivery-readback.json
- ui-audit-package-retired-20261028/artifacts/cleanup-result.json

以上关键路径在交接中核对；具体哈希、候选源和限制以各原始收据为准。勿对巨大 source_before.file_sha256 整体打印，曾导致输出膨胀；只选head、patch和结论。

开发输出按 scripts/runtime/dev.py 放ignored .project-local/，Python用 .venv/Scripts/python.exe -X utf8 -B。
Node已用：
D:\All projects\OS External Configuration\10-toolchains\scoop\apps\nodejs-lts\24.18.0\node.exe
Rust沿 scripts/ci/cargo_test.bat／项目target；不得改全局PATH或共享工具配置。
rg在此环境曾shim失败，失败时改用 scoped git grep／git ls-files／Select-String；不全盘搜home。

工具可用性必须新会话重新核实。Stitch／设计类插件、视觉审计技能、Playwright、截图、GitHub交付／CI技能此前已用过；不能假定新会话工具或浏览器连接自动继承。先读实际适用SKILL.md，再做对应工作，不为加载技能而重做已完成审计。
成熟参考：React官方Error Boundary、W3C APG alert／alertdialog、W3C WebDriver原生控件、Selenium交互文档；使用时核对应实际版本。

Windows清理必须用同一PowerShell链路，验证绝对目标在授权根内、拒绝越界reparse，不用跨shell拼删除命令、不凭文件名认领其他软件缓存。
不杀共享进程、不关闭Owner窗口、不发全局Esc、不碰浏览器凭证／cookies。
已拥有的V13 Host／Core／driver已正常清场；历史Sandbox STOP_REQUESTED_NOT_CONFIRMED问题不可自动写成已解决，不再建新VM／安装环境直到确认旧句柄及授权。
Green程序未替换，公开发布未做；条件性Green精确路径授权不等于现在已经合格或可以覆盖真实数据。

额度工具是 get_usage_limits：优先rateLimitsByLimitId，适用非空订阅窗口取最小remaining=100-usedPercent。未知不是0，余额不是订阅额度。新会话不要在暂停状态自行轮询或恢复自动化。

## 11. 交付纪律与第一条回复

- 任何完成结论区分：方案／实现／局部测试／构建／原生Host／真实集成／安装／精确SHA云CI／Green／Owner接受。
- 原始失败独立保留，复测另列；不能用后继定向通过覆盖原全量失败。
- 普通保存不强制外部证据／云端／事实审批；原件和草稿保全优先，人工知识接纳另记状态。
- 当前任务未完成，暂停不是阻塞审计的替代词，更不是完成。
- 本冻结提示词和当前文档在本地，尚未提交上传。要远端同步时先核当前授权和实际状态，保护6项并显式stage，不传运行包或私有记忆。
- 本轮Owner单独授权查询与本项目相关的私有记忆索引；实际只查了 C:\Users\ALEX\.codex\memories\MEMORY.md 的有关条目，未修改记忆，也不授权无关私人内容。新会话不把路径登记当广泛访问许可。
- 无需再向Owner索要已存在路径或MiniMax URL，也不要又问是否继续制作完整截图包。

新会话第一条回复应简短确认：
“已接收完整交接，确认截图包与MiniMax该批素材任务已取消，开发和监控保持暂停；未完成任务、未提交文档及六项保护材料已识别。等待明确恢复后按CI／可靠性、错误兜底、UI与人物、业务闭环顺序并行推进。”

本文件之后如有Owner新指令，以新指令和活动指针的实际更新为准，不把上述建议顺序固化为新的权限。
