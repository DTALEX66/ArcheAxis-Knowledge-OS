# 当前实施进度

状态 **RUNNING_BY_OWNER / PARTIAL**（Owner 明确要求今天停止额度监控并继续；今天不查询额度、不因额度阈值停工）。本文件是 [活动指针](AAOS-ACTIVE-EXECUTION.json) 指定的唯一进度源；按指针及 [Owner 决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md) 接续当前任务，不从旧暂停或旧 COMPLETE 推导现场事实。

最新接续见文末 **2026-10-20 UI-P02：研究引用与排版**：模板切片已经PR196合入main的5f6a845e，候选与main CI均成功；TRAE的206d56da完整保留。继续完成研究引用/引文/原件指纹的诊断分离、版本准确名称、只读诊断入口与8px排版间距；本地39项、研究页五主题宽窄10场有限浏览器通过，本片新提交的exact-SHA CI/合并待独立读回。19个本地/4个远端已合并分支的清理及6个独有patch分支的保留不变。前端总体PARTIAL，UI-P02全域及UI-P14/21/22/23/24等仍未完成，后端阶段尚未启动、Green未更新。早期FAIL/PASS保留各自源码，不从旧快照推导当前事实。

## 已实施与证据边界

| 范围 | 当前可确认的实施 | 证据与限制 |
| --- | --- | --- |
| 底座与工作台 | 正式 Tauri/React 宿主、Rust Core 单写者、隔离 Python workers；多格式、独立草稿与会话、有限本地能力接口已有增量 | [逐轮覆盖与差距](AAOS-AUDIT-TEST-COVERAGE-20261018.md)、[来源待办](AAOS-EXECUTION-BACKLOG-20261018.json)；不可按总用例数宣称产品通过 |
| BE10 本地消费者 | human只读preview/snapshot与page16阅读已实施；同仓Core/HTTP/Observer CLI进程15项通过，`b5c5d8f8`干净候选原生固定正文、诊断身份、冷重开、错身份拒绝及已打开正文到期清空通过 | [限定回执](../history/repository-consolidation-20261019/current/receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json)、[本轮跟进](../history/product-loop-20261019/follow-up.md)；真实Tauri/Core、隔离合成笔记；本地human只读工程片PASS，真实外部产品、OS URI、选区真实性、来源认证与安装资格仍未完成 |
| 常用格式选片 | `b5c5d8f8`实际候选Core/worker执行DOCX/XLSX/PPTX/文本PDF：原件字节与SHA、正文/结构/损失摘要、两处定位、独立重解析及Core重启回读一致 | [本轮跟进](../history/product-loop-20261019/follow-up.md)、[源码绑定元数据](../history/product-loop-20261019/verification-index.json)；合成输入、真实解析器，四格式选片PASS；不含OCR、原应用渲染/编辑/包往返、所有格式UI或安装验收。正式FolderIngest逐件身份/作业/损失已有入口，整批成员与结果跨重启恢复仍待实施 |
| 模型与 AI 旅程 | `ce3b04e8` 干净源码的新 Core/Host 候选完成 Tauri 原生工程链，LM Studio 27B MTP 实际回答59.25s、纠正后复测68.86s；恢复阅读、能力开关及恢复后旧授权拒绝通过；无 Ollama 自动回退 | [模型入口](AAOS-LOCAL-LLM-20261018.md)、[本轮跟进](../history/product-loop-20261019/follow-up.md)；工程链 **PASS**，总体 **PARTIAL**：纠正为测试编写、答案未独立评价，closed_loop_verified=false，Owner验收未执行。旧102.41s/56.41s候选及后置阅读失败保留，不据不同运行比较加速收益；不是安装版资格 |
| 反复工程故障 | 目录归属、旧路径断言、运行状态误跟踪、换行保全、源码读取和检查锁问题已修复；本轮再修精确摘要误报、原件 CRLF、manifest fixture 与诊断更名消费者 | [可靠性限定回执](../history/repository-consolidation-20261019/current/receipts/AAOS-RELIABILITY-CLOSURE-20261019.json)、[本轮跟进](../history/product-loop-20261019/follow-up.md)；Python定向270项及168子项通过，前端分片复验及构建通过，不能替代新 exact-SHA CI |
| 资料与入口整理 | 已将根旧报告、旧阶段快照/收据及旧规划/设计/验证目录迁入历史，现行引用同步迁移 | [本轮清单](../history/repository-consolidation-20261019/MANIFEST.json)；字节、断链、生成器、目录与回归结论见同目录验证记录，不能提升产品资格 |
| 前端信息与窄窗口 | 已统一“运行诊断”，处理任务、工作草稿与布局改用业务文案；恢复页展示草稿预览，原始身份经现有诊断核对；640×480正文可见100→116px，保持17px字体与四行门槛 | [本轮跟进](../history/product-loop-20261019/follow-up.md)、[工具实际调用](../history/product-loop-20261019/tool-usage.json)；公共源码六例定向浏览器通过并查看截图，完整A0原FAIL保留，后续全门禁仍待资格。普通页面术语未全面收敛，不称原生系统缩放或完整无障碍通过 |

## 尚需闭环

1. AI 工程链已取得上述同候选原生 PASS；仍需独立纠错/质量、实际停止与稳定性和Owner验收。保留原失败例，不擅改 profile、provider、endpoint 或预算，不把编写的纠正当实际错误判定。
2. BE10本地固定引用原生片已PASS；继续真实对端投递、OS URI、HUB004安装更新及运行准入，保持本地只读与跨产品执行权限分离。
3. 常用格式剩余UI/逐操作资格、批次成员与结果的耐久重建、扩展生命周期、特色知识库兼容矩阵，以及原生安装/Owner验收。复用正式FolderIngest→Rust Core路径，不将legacy IntakeSpace/Python batch当当前产品。完整无障碍和性能未取得完整资格。
4. 按实际 SHA 核对云端 CI、PR 与同步状态；push、CI、merge、installed 各自记账。ASTRYN 原仓、Green 和真实数据不得凭资料归档删除。

本次按39项对话主题、后继要求及FE21–25逐项核对，差距保存在[审查记录](../history/product-loop-20261019/conversation-review.md)，后继修复与命令见[跟进](../history/product-loop-20261019/follow-up.md)及[源码绑定元数据](../history/product-loop-20261019/verification-index.json)。性能监控已有生产调用方，仍缺安装环境性能基线；FE25不要求先公网部署，正式资产仍需从合格实际构建采集。GitHub About已确认正确。PR194的`ce3b04e8` CI39241950317已结束：OS测试、浏览器、安全、Core及构建等作业通过，installer-lifecycle因原生元素不可交互失败、聚合门禁随之失败；不能宣称CI全绿或安装合格。`b5c5d8f8`为本地后继探针/协议修复检查点，尚未取得该SHA云端资格；main、发布与Green资格均未提升。

2026-10-19后继结果：`b5c5d8f8b61684f9358a5b98ec86fcb641406064`干净源码的Core/Host构建、19524成员绑定和BE10原生工程片通过（34.095秒、exit0、源码一致）；四格式Core选片20.251秒通过。首次BE10等旧按钮失败，第二次实际身份拒绝被驱动误判为协议错误；两次失败与清理保留。修复成功WebDriver脚本任意JSON结果的解释，真实loopback正/负例及共享退出合同75项、5子项通过，未放宽HTTP/非脚本协议拒绝。截图已实际查看；无外部接收端、OS URI、模型推理或Owner验收推论。安装态CI失败另行定位，不以本地BE10通过替代。

安装态失败已定位并作最小修复：宽度≤1100或高度≤760时侧栏隐藏，但原导航抽屉只提供空间入口、缺少对象导航，探针随即点击隐藏按钮。现将同一ContextNav放入现有抽屉，避免重复导航/heading身份，选中后关闭并转交实际目标焦点；Escape返回触发按钮。探针走可见侧栏或真实抽屉的原生点击，不改窗口掩盖缺陷、不用JS点击、不跳过原四区焦点及数据不变断言。旧产品的新回归2 RED，应用后前端36/36、Python88项及150子项、TypeScript与Ruff定向检查通过；这些是本地/SIMULATED合同证据，新源码实际安装CI仍待验证。详见跟进与验证元数据。

主背景与主控台后继实施（Owner决定`OWNER-DESKTOP-CONSOLE-20261019`）：在既有工作区外增加单一会话内窗口，支持标题区拖动、右下角调整、方向键移动、Shift加方向键调整、Esc取消、铺满/还原/复位；尺寸和位置受可视范围约束，窄窗自动铺满。关键布局断点改按主控台实际尺寸计算，不重挂载工作区，不写业务数据或窗口持久设置。保留主背景、图谱、DockWorkspace与小栖；Windows正式宿主显式允许原生边框、调整、最大化和最小化，不增加第二桌面或通用窗口系统。

本地前端定向40/40、最终Python合同55/55、TypeScript、选定Ruff规则通过。公共产品源码的Chromium试点9项交互通过，640×480阅读/导航/检查器门槛通过，正文可见138px、字号17px，保持四行与点击可达标准；真实渲染、host/Core为受控合成fixture，证据SYNTHETIC。已实际查看内缩、调整后及最小阅读截图，本任务服务PID28216/端口50165已停止并读回关闭。前三次浏览器失败分别为测试同步/调用问题，第四次9项产品操作通过但旧顶栏四按钮合同未接纳新增两按钮；同步调用方后第五次通过，全部FAIL保留。未放宽阅读或命中门槛。

`product-loop-console-host-build-20261019`在稳定源码补丁`8225431e6374293ceffeb43c14315e0e2c2dbf4fc933db8f17e5234ccffc17c9`完成正式Host构建，exit0、source_consistent=true；其后只修改测试消费者与文档，产品源码未再变更。这是本地构建和有限浏览器通过，不是安装、真实Windows边缘拖拽/DPI、多屏或完整UI验收。新提交的exact-SHA CI仍须实际取得；总体保持PARTIAL。详细命令、失败与环境见既有跟进和验证元数据。

## 历史：2026-10-19首次额度检查点与新增要求

当时执行 **PAUSED_BY_OWNER / PARTIAL**。2026-10-19T12:12Z附近实测适用Codex窗口used85%、remaining15%，触发活动指针中的Owner条件：停止新增开发/重验证，保存已完成、失败和未完成范围，公开任务改动提交推送并读回；未经Owner明确恢复，不因额度重置自动继续。主控台及窄窗导航功能检查点为`16e46a50`；其后交接文档不代表新产品资格。活动goal已按该明确条件暂停。automation`archeaxis`的view只返回界面卡片，暂停更新因缺kind被拒绝，且登记位置无可读配置，**监视器暂停UNVERIFIED**；未伪造已停或新建替代自动任务。

最后一条Owner“所有菜单和主体文字内容的密集排列程度 文字大小等 一定给适配好了”已记入决定第十三节。只读确认的共用源码缺口：body14px/按钮13px/shell16px/portal继承不一致；命令菜单等仍有11px辅助硬编码；全局button nowrap的解除只按外层viewport；content.css与expression-board.css部分多列断点未跟随Dock/主控台；critical-layout-fixes.css最后用!important锁定网格最小400px。**静态证据PARTIAL，实际视觉复现UNVERIFIED，本项尚未修改产品**。

恢复后的下一最小范围：先统一菜单/正文/辅助字号与间距token并让portal使用，修固定列宽及真实面板断点，按正式菜单/页面建立长中文与窄窗覆盖矩阵；复用现有浏览器与定向门禁，不能把当前阅读页9项试点外推所有界面。同步核新交付SHA的CI与安装失败是否消除，再继续UF11耐久批次等原闭环任务。原生系统DPI、完整无障碍/性能、Owner验收及其余已列欠账保持未完成。

## 2026-10-19明确恢复后的密度与玻璃增量

Owner“继续”恢复了本聊天的当前范围。正文16px、菜单14px、辅助13px以rem语义token统一，shell/portal继承一致；对象导航标题与说明分行，按钮按需换行。content命名容器跟随Dock实际宽度，强制400px网格下限改为不超过面板宽度。实测发现首页宽846px超过610px面板，补width约束、标题操作区重排和顶部导航的整行标题，修复被裁切的导入按钮。菜单设置浮层虽有合格几何，却被正文层遮住；统一状态栏层级并以实际elementFromPoint命中复验，原失败保留。

局部浏览器最终39项PASS：五主题的导航抽屉/对象分行、命令和设置字号/边界/设置命中，七个主要页面在外层1600×1000、内缩640×480下的内容/操作按钮边界；另执行640×480阅读门槛和宽屏五个顶部菜单的Escape/焦点检查。真实Chromium149.0.7827.55、DPR1、reduced-motion=reduce，host/Core为受控合成fixture；不是全产品、原生DPI或完整无障碍通过。56项前端定向、最终63项Python合同、TypeScript/Vite及选定Ruff规则通过；不同运行不叠加成全量用例数。

后继玻璃反馈按决定第十四节处理：移除外扩3/5px描边及多层硬高光，单个实际圆角盒绘制1px边框/内反光，统一24px连续磨砂底材，弱化公共面板反光，补实色/减少透明效果/forced-colors回退。两主题×宽窄窗口4项有限浏览器读回PASS，已实际查看整页与圆角截图；菜单命中保留。**玻璃后未重跑完整构建、完整浏览器矩阵、原生或安装验收，视觉Owner验收UNVERIFIED。** 此前前端构建仅资格到密度/浮层修复；不将它外推玻璃后最终源码。

云端PR194 head71349655的run39250651402已结束FAIL：Python主集5564通过、88跳过、379子项通过，但唯一执行状态与两个副本矛盾导致1项失败。现删除两处可漂移状态副本，改为#/execution_control引用；保留现行暂停/恢复约束及历史状态，63项相关本地合同通过。installer-lifecycle的普通安装旅程已通过；独立冲突旅程仍在开始前失败：已在19页但hash为空，conflict_navigate仍点击隐藏侧栏。已实际查看截图/日志并定位，**修复尚未执行**，恢复后先修scripts/probes/aaos01_tauri_webdriver_loop.py的conflict_navigate，保持真实点击、警告确认、草稿冲突/恢复/重启断言，不用JS点击或扩大窗口。新源码exact-SHA CI尚待获得，当前不merge。

2026-10-19T12:48:05Z新读数used86%、remaining14%，按Owner既有条件再次停止新增开发与重验证，保全本轮失败/截图/命令及公开改动，执行已授权commit/push与SHA读回。goal工具仍为先前PAUSED，未标COMPLETE；监视器暂停继续UNVERIFIED。自有玻璃核验服务PID14268/52978已退出；密度最终服务PID21032/58276已退出，其他本轮实例关闭情况均保存在回执。总体PARTIAL；格式耐久批次、外部BE10、原生安装、完整UI/性能/无障碍和Owner验收等欠账不变。

## 历史与保留范围

此前多轮实施日志与“最新”快照已原字节保全至 [迁移前完整进度](../history/repository-consolidation-20261019/navigation-before/docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)；它保留原时点全部细节，不能覆盖本文件。其他阶段、失败证据与测试命令从 [历史入口](../history/README.md) 和 [清单](../history/repository-consolidation-20261019/MANIFEST.json) 按原路径查找，不相加称全量。

V01 继续暂停，FT01–04 继续冻结；原六项增量按活动指针冻结。当前最短闭环包含完整架构、常用格式及特色兼容能力，扩展按需接入既有能力中心。专业源文件外部导出通用图片／PDF后接入，不承诺专业结构往返。局部运行和本次整理均不代表安装、发布或 Green 替换资格。

## 2026-10-19 后继 Owner 决定：今天停止额度监控并继续

Owner 明确要求“额度监控今天停止监控 赶紧完成任务”，并再次催办。此决定覆盖上文当日额度触发的暂停；当前 RUNNING_BY_OWNER / PARTIAL。今天停止聊天额度查询，不按额度阈值停工。独立 automation 暂停接口未成功，状态 UNVERIFIED，不将其写成已暂停，也不以此阻塞产品收尾。继续当前密度、玻璃与安装探针导航修复、验证及授权交付；冻结能力和发布边界保持不变。

## 2026-10-19 密度、玻璃与安装导航最终本地收尾

后继修复已完成：安装冲突旅程以实际渲染页标记判断当前位置，同页不重复导航；跨页只点击可见侧栏或导航抽屉，等待按钮实际可见后再点。保留原生警告确认、草稿冲突逐项比较、明确保存、版本及进程重启断言；文档打开后的旧 hash 等待也改为真实页面与编辑器。只读复审未发现业务断言被绕过。

最终 TypeScript/Vite 构建通过；107项相关合同通过，可见性等待补强后44项导航/冲突合同通过。最终39项五主题/七页面密度及菜单矩阵通过；两主题×宽窄窗口的玻璃/导航8项通过，真实点击覆盖同页短路、侧栏和抽屉。使用真实Chromium、合成host/Core fixture，不能外推已安装Tauri、完整无障碍、系统DPI或Owner视觉验收。实际命令、时间、退出码和源码patch身份见本轮 verification-index.json 的 runs。首次测试路径错误未执行、脚本重载导致尺寸前提变化的超时均保留，不算产品通过。自有浏览器与Vite已关闭，端口已核实关闭；Vite按既有helper终止，退出码1不称正常退出。

本地增量PASS；新提交exact-SHA CI及独立安装冲突旅程待云端复核，尚不merge。今天不再查询额度或据额度停工；独立监控任务的暂停仍UNVERIFIED，不能将界面卡片或失败接口当作暂停成功。总体仍PARTIAL，继续由当前范围及欠账索引推进。

## 2026-10-19 云端门禁复现与后继修复

c95c46c1 的 CI39258682797 出现两处实际失败：浅色半透明栏的焦点环最低对比度1.130116未达3；Rust持久终态已写入但active登记尚未摘除时，再取消仍返回202。前者改用深蓝焦点色，原门槛未变，五主题定向复验最低3.15941177597；后者先核身份/故障，再有限回读精确job/request持久状态，终态返回200且不发送取消信号。首次workspace复验发现数据库队列阻塞会拖慢取消，保留该FAIL；现仅探测25ms，超时立即发出已登记请求的取消信号并返回202，不把未知状态称为已终止。原100ms取消响应断言保留。新稳定回归在旧行为下实际RED，修复后GREEN；身份不匹配409及故障503保护仍在。

本地完整正式浏览器门禁另发现390/640px顶部导航设置菜单被推到左侧屏外。浮层改为按完整状态栏定位，选择框在菜单内铺满；原正式设置命中/几何/字号检查三档均通过，截图已实际查看。最终正式A0浏览器门禁PASS（13档视口、5主题及既有正文/导航/键盘/原件流程）；实际Chromium配合受控host/Core fixture，不外推真实安装、物理DPI或完整无障碍。

Rust workspace正式入口离线测试PASS：915通过、0失败、0忽略，194个测试结果组；包含原先云端失败的runtime_jobs。该计数仅本轮workspace，不与其他重叠结果累加。最终TypeScript/Vite构建PASS（子运行9b2df8583560），大chunk及既有Rust警告保留。修复队列阻塞回归并格式化新增Rust代码后执行最终workspace与CI格式门禁；未改测试阈值或业务断言。格式化命令子进程exit0，因预期源码写入，dev回执标INVALIDATED；它只表示修改，不作为测试PASS。裸cargo缺link.exe、初次Rust格式检查失败、浏览器原失败均保留原回执，不改写为PASS。

源码、时间、命令与退出码见verification-index的runs及ci_repair_followup。全部自有浏览器/开发服务已结束，正式浏览器实例端口关闭已核实；停止方式沿现有helper，不称优雅退出。新提交CI及实际安装旅程资格必须绑定各自SHA，仍不从本地结果推导merge/发布/Green替换。今天不查询额度、不据额度暂停；总体PARTIAL。

后继云端安装读回：c95c46c1 的普通安装旅程通过，独立文档冲突旅程FAIL。已实际查看失败截图与native-driver日志：比较按钮可信点击成功、实际位于03页，随后探针等待旧的正文内`details pre`超时。产品已按Owner决定将原始JSON集中到运行诊断，普通比较区保留可读正文；这是尚未迁移的探针消费者。现逐区核对可读预览，再可信点击精确诊断按钮、按已选记录标签读原始JSON严格等值比较、可信关闭诊断，继续三份快照、明确保存、B独立草稿、所有正文版本及正常重启断言。49项Python合同（含错误预览/载荷、缺失/重复载荷及非法JSON拒绝）和19项现有冲突/诊断组件检查PASS；不是新安装资格。新exact-SHA CI仍须完成真实安装验证。


## 2026-10-19 Owner要求中断后收尾

本对话停止新增功能工作，完成公开记录归档与授权上传；总体仍PARTIAL。最新源码为`867d7c8a07d6e0e36895b84e3ad1490e0a58badb`，云端浏览器/Rust/Python/桌面构建已通过，CI在收尾快照时为in_progress/PENDING，不把安装或聚合未完成称为PASS。全部本对话决定、实际修复、测试边界、定时删除not_found与遗留项见[收尾归档](../history/product-loop-20261019/conversation-closeout.md)及[机器记录](../history/product-loop-20261019/conversation-closeout.json)。最终上传后独立核对本地/远端分支SHA；不自动merge、发布或替换Green，不创建后台继续任务。此收尾不恢复冻结能力，也不从历史暂停撤销Owner当日不监控额度的决定。

最终收尾读回：源码867d7c8a的CI39264199340整体CANCELLED，installer-lifecycle实际FAIL（grouped UI engineering journey，exit1）；失败证据包与未定位根因已归入本对话收尾补充。后继归档提交CI未取得完整资格；PR194保持Draft/Open，未merge/发布/替换Green，不以本地通过或云端其他作业通过覆盖安装失败。

## 2026-10-19 Green精确目录覆盖授权

Owner询问并明确允许覆盖 `D:\All projects\ArcheAxis.Knowledge.Green-x64`。现场已核该目录是共享路径索引登记的日常Green位置，存在ArcheAxis.exe、启动器、runtime、data、根archeaxis.sqlite及备份目录；release-identity.json记载v0.6.14，不能从该标签推导整个当前文件集资格。已将程序更新授权及现有exe哈希记入活动指针green_update_authorization，并同步AGENTS、共享索引、运行交付索引和接手入口。更新范围是程序文件，先保全回退，保留业务数据/数据库/备份/未知目录；公开发布不在授权内。本次未覆盖文件、未启动Green、未读取业务数据、未终止进程。当前候选安装旅程仍未取得完整资格，先修复验证再执行覆盖，不再重复索要本路径的许可。

## 2026-10-19 最快最短完整闭环定义V2落地

Owner最新完整目标与原话已归档到当前决定第十五节；规范统一为docs/truth/CLOSED_LOOP_DEFINITION.md（AAOS-SHORTEST-COMPLETE-LOOP-V2，SUP-025）。包含完整核心、常用多格式、免费百科/论坛社区/科研检索比较、全面非企业知识库特色兼容、既有开源池按需接入、本地与云端真实模型、同候选全链路；复杂能力具名延期，未完成仍记缺口。已将根权威、AGENTS、CLAUDE、GEMINI、项目合同、活动指针、文档索引与接手入口导向同一文件；复用369研究池和68项供体表面归属等既有入口，没有把库存数量称为集成数。本轮仅澄清目标与路由，不接外部服务、不安装依赖、不访问账号凭据、不改变产品实现或旧测试结论；产品总体仍PARTIAL。

闭环定义落地核验：19项权威/替代/运行导航测试通过；现行文档权威门禁和命名编码门禁通过，外部/私人4项输入仍UNVERIFIED。一次性路由核验确认正文15个本地链接、9个入口、7维度和6旅程齐全。首次路由检查误将J1与场景标题同单元格判为缺失，修正临时检查器后通过，原FAIL保留。命令、时间、退出码、源码身份与正文SHA见本轮verification-index的closed_loop_definition_registration；仅结构资格，不是产品全链路PASS。

## 2026-10-19 完整交接与前端优先分片

Owner要求新会话／其他Agent可接续的完整交接，并明确全量前端先行，再后端。已更新当前接手提示词，建立前端24分片／后端15分片及逐项验收覆盖，映射原任务；活动指针、根AGENTS和文档职责索引导向同一顺序，Owner决定第十六节保留来源。分片是实施与验证定义，既有功能须核源码／回执后只补差距；无第二实时进度或产品能力注册。

交接涵盖桌面观感／主背景和内缩主控台、原生及内部窗口调整、Dock拆分、缩放／DPI／密度／文案诊断收敛／玻璃五主题、全部页面与状态、图谱／小栖／学习／模型／能力中心、无障碍／动画性能／截图与安装资格；后端接续包含闭环七维度及J1—J6、开源与兼容矩阵、双模型、真实外部研究、批次和Green。记录共享库／工具／模型／权威／历史会话导航及未核实尾项，保留原安装FAIL和所有历史测试边界。仅文档整理，产品实现／Green不变，总体PARTIAL。

交接结构核验：19项权威／替代／运行导航检查通过，32个本地交接链接及前端24／后端15分片、先后顺序、唯一进度路由和闭环正文原SHA核对通过；命名编码门禁通过。首次文档门禁把根入口直接链接的EXECUTION命名规划文件视作竞争进度，已改从活动指针execution_priority_overlay选择，未修改门禁，原FAIL及复验PASS保留。命令、时间、退出码与源码patch身份见verification-index.frontend_first_handoff_registration；4项外部／私人来源仍UNVERIFIED。本轮无产品／模型／浏览器／安装新测试，不据此覆盖产品PARTIAL。

后继交接补齐：Owner新增分支合并、体积减重、本地／云端仓库及目录规范，已纳入RC-P01—08及活动指针repository_convergence。实查远端7个heads及3个开放Draft PR（192／193／194），tracking漏remaining-loop-stage1；大量供体不在祖先链，是否已有patch吸收待核，未合并／删除任何分支或文件。

同时读回5836b906的CI39271537141 test (3.12)两项实际FAIL：PROJECT_CONTRACT新增closed_loop_definition遗漏严格Schema登记。已本地复现2失败／3通过，随后在既有Schema精确登记并要求该规范引用，保留额外字段拒绝、Rust单写者和普通保存边界，新增拒绝旧来源／假实施成功／丢引用的回归。相关合同与权威25项通过（含原失败），仅合同一致性修复，无新后端业务实现；新exact-SHA CI待验，旧安装grouped UI FAIL仍独立未闭环。

## 2026-10-19 接手 UI-P01：现场核对与 22 角色覆盖映射

本轮为全量前端优先的**首个实施分片 UI-P01**（映射 UF00/G01/H01）；只做只读核对、覆盖盘点与基线确认，不改产品源码、不新建第二进度。

**现场核对（readback，2026-10-19，动态取 Git/远端，不据记录推导）**

- 分支 `codex/sync-20261019`，HEAD `031fcfea847691f7d3eb1aef92646538a8b3aabd`，工作树干净（`git status --short` 空）。
- 本地 HEAD = 远端 `origin/codex/sync-20261019` = `031fcfea`；`main` = `fe18fdc3cbcab9a0f84a02c5a4db1b6bcef13f46`。
- 实际远端 7 heads：`codex/sync-20261019`、`codex/character-memory-ui-20261015`、`codex/layout-preferences-20261014`、`codex/closure-integration-20261014`、`codex/remaining-loop-stage1-20261013`、`codex/ui-polish-20261013`、`main`；开放 PR 192／193／194 **均 Draft**。tracking 漏 `remaining-loop-stage1` 已于 RC 盘点记录。
- 交接失败证据判读：`5836b906` 的 CI `test (3.12)` 两项 FAIL（Schema 漏登记 `closed_loop_definition`）已由 `031fcfea` 修复并进入当前 HEAD；`867d7c8a` 的 installer-lifecycle「grouped UI engineering journey」FAIL 仍为**独立未闭环**证据，编码于 [verify_nsis_install.ps1](../../desktop/scripts/verify_nsis_install.ps1) 的 `actual installed grouped UI engineering journey failed` → `aaos01_grouped_owner_loop.py`，本轮未执行安装，不宣称已消除。
- 前端基线（本轮实测一次，不重复）：Node v24.21.0／vitest 2.1.9，`npx vitest run` → **182 文件 1844 用例全通过、无 skip、28.56s**。仅为 Vitest 前端套件，不代表 Python/Rust 全仓、安装、真实模型、视觉或需求覆盖率。

**22 语义角色 → 生产路由 → 组件映射（依 [SpaceView.tsx](../../frontend/src/spaces/SpaceView.tsx) 实际路由与 [uiPages.ts](../../frontend/src/presentation/uiPages.ts) 注册，非计划 `/reference` 号）**

| 角色ID / 页面 | space | 生产组件 |
| --- | --- | --- |
| 01 今日工作台 | workspace | CanonicalWorkspaceSpace（DockWorkspace 承载） |
| 02 知识库 | library | CanonicalLibrarySpace（purpose=library） |
| 03 阅读与编辑 | library | CanonicalLibrarySpace（purpose=reader）+ DocumentEditor/PDF/Media |
| 04 双链与图谱 | vault | CanonicalRelationSpace + CollectionPanel |
| 05 研究空间 | vault | CanonicalResearchSpace |
| 06 学习路径 | learning | CanonicalLearningJourneySpace(pageId=06) |
| 07 课程与视觉教学 | learning | CanonicalLearningJourneySpace(pageId=07)／KnowledgeCoursePanel |
| 08 教学需求 | learning | CanonicalTeachingSpace |
| 09 表达方案 | learning | CanonicalTeachingSpace |
| 10 交付与版本 | learning | CanonicalTeachingSpace |
| 11 练习/Teach-back | learning | CanonicalTeachingSpace |
| 12 反馈与修订 | learning | CanonicalTeachingSpace |
| 13 项目记忆与上下文 | ai-assets | CanonicalControlledAiSpace(pageId=13) + CharacterMemoryPanel |
| 14 纠正、评测与复测 | ai-assets | CanonicalControlledAiSpace(pageId=14) |
| 15 资源与扩展 | settings | CanonicalResourcesSpace |
| 16 导入导出与互通 | exchange | ProjectHandoffReader + CanonicalExchangeSpace |
| 17 全部能力与未来蓝图 | settings | CanonicalCapabilitiesSpace |
| 18 能力详情 | settings | CanonicalCapabilitiesSpace(selectedCapabilityId) |
| 19 设置、权限与恢复 | settings | ui-reliability-panel：BackupPanel + ModelConfigurationPanel + ConfigurationPlanPanel |
| 20 版本、来源与历史 | library | VersionSourcePanel + CanonicalLibrarySpace(purpose=history) |
| 21 画布与视觉表达 | learning | CanonicalExpressionSpace |
| 22 任务与记录 | ai-assets | CanonicalControlledAiSpace(pageId=22) |

说明：22 角色**不是 22 个独立路由**；`canonicalSurface` 将 9 个 space 收敛到 5 个 canonical surface，页面只覆盖语义角色。全 22 页 `implemented=true`（路由存在），未实现语义页由 `ui-pending-page` 兜底。

**共享壳与弹层清单（全量 UI 范围，均已存在）**：TopNavBar、StatusBar、SpaceRail、ContextNav、ActivityDock、Inspector、CommandPalette（命令搜索）、NavTrail、AaosDialog（导航抽屉）、ThemePicker、ConversationPanel（小栖侧栏）、DiagnosticCenter（唯一运行诊断中心）、ConsoleWindow（`container: console / size`）、DockWorkspace、XiaoqiPanel。

**已知未闭环／待验收（保留，不冒充通过）**：① 867d7c8a 安装 grouped UI FAIL；② 完整 A0 原 FAIL；③ 真实系统 DPI／物理 IME、完整无障碍（axe 仅部分页面）、动画/性能基线、真实 Core/模型与安装态、Owner 视觉验收；④ UI-FOLLOWUP-006 等历史项在限定浏览器范围关闭但未获全组合资格。

**结论**：UI-P01 现场核对与覆盖映射 **PASS（结构／路由／基线层）**；真实视觉、安装态、DPI、无障碍与 Owner 验收 **NOT_EXECUTED**，整体仍 **PARTIAL**。

**后续分片（本轮之后按序）**：UI-P02（工程术语收敛：普通页保留清晰中文，原始 ID/schema/payload 统一进 DiagnosticCenter）→ UI-P03—P05（主背景+内缩主控台、窗口调整、DockWorkspace 拆分，核已有实现只补差距）→ UI-P06—P08（响应/缩放、字号密度、玻璃五主题）→ UI-P09—P24。后端 BE-P01—P15 在前端阶段交付后执行；RC-P01—08 分批完成。

## 2026-10-19 UI-P02 增量：普通页工程术语收敛

背景：UI-P01 盘点确认普通业务页仍散落“合同”(contract) 等工程词。本轮只收敛**明确泄漏点**为清晰中文，不动诊断中心、兼容矩阵与能力投影页的权威词汇，不重构文案体系。

**修改（产品源码）**

- [CanonicalExchangeSpace.tsx](../../frontend/src/spaces/CanonicalExchangeSpace.tsx#L104)：`目录没有分页合同；未返回的身份不能当成不存在…` → `当前目录没有分页；未返回的记录不能当成不存在，也不能改用同名文件。`
- [CanonicalTeachingSpace.tsx](../../frontend/src/spaces/CanonicalTeachingSpace.tsx#L266)：`由真实学习合同承接` → `由真实学习流程承接`（并规范 `Teach-back`/`Python` 间距）
- [CanonicalWorkspaceSpace.tsx](../../frontend/src/spaces/CanonicalWorkspaceSpace.tsx#L30)：抛错 `工作区内容合同不兼容` → `工作区内容结构不兼容`
- [ContextNav.tsx](../../frontend/src/components/ContextNav.tsx#L71)：`只显示缺少的合同…假入口` → `只显示缺少的条件…虚假入口`
- [CharacterMemoryPanel.tsx](../../frontend/src/components/CharacterMemoryPanel.tsx#L47)：`输入超出记忆合同…` → `输入超出记忆允许范围…`
- [core.ts](../../frontend/src/api/core.ts#L131)：ApiError `本地核心内容合同不兼容。` → `本地核心内容结构不兼容。`
- [workspaceRestore.ts](../../frontend/src/api/workspaceRestore.ts#L6)：`恢复预检合同无效` → `恢复预检结果无效`；L14 `恢复完成合同无效` → `恢复完成结果无效`
- [bindings.ts](../../frontend/src/templates/bindings.ts#L106)：`文档分页合同不完整` → `文档分页结果不完整`
- 测试消费者同步：[CharacterMemoryPanel.test.tsx](../../frontend/src/__tests__/CharacterMemoryPanel.test.tsx#L64) 正则 `/输入超出记忆合同/` → `/输入超出记忆允许范围/`

**验证**：定向 5 文件 **107 项 PASS**；`npx tsc --noEmit` **exit 0**；全套 `npx vitest run` **182 文件 1844 用例全通过、无 skip、29.00s**。仅 Vitest 前端套件，不代表视觉、安装态或真实 Core。

**边界**：兼容矩阵/诊断页按需出现的 SHA/ID/回执等权威词**保留**，原始结构仍集中 `DiagnosticCenter`；“五类交换合同”等位于能力目录投影（`uiCapabilityIntent.ts`/`capability-catalog.ts`，改动需连同 fixture 同步），本轮未动，留 UI-P02/UF06 后续处理。

**结论**：UI-P02 局部 **PASS**；普通页术语未全域收敛（兼容/能力投影域仍有工程词），整体仍 **PARTIAL**。

## 2026-10-19 UI-P03—P05 复核 + A0 真实浏览器门禁（当前 HEAD）

**UI-P03—P05 复核结论：实现已存在，本轮只核差距（不改产品源码）**

- **UI-P03 主背景＋内缩主控台**：[ConsoleWindow.css](../../frontend/src/components/ConsoleWindow.css#L1) 建立 `container: console / size`；[glass-cabin.css](../../frontend/src/design-system/glass-cabin.css#L27-L38) 的 `cabin-shell` 按 `cqh/cqw` 内缩单圆角盒；背景用 `deep-space-background-20261015.png`。A0 geometry（1920×1080）实测主控台 `x96 y54 w1728 h972`，5 bands（top_navigation/status/rail/center/dock）无 clipped/overlap/escaped。
- **UI-P04 窗口调整**：[ConsoleWindow.tsx](../../frontend/src/components/ConsoleWindow.tsx) 已实现标题区拖动、右下角 resize、方向键移动、Shift＋方向键调整、Esc／pointercancel 回滚、`constrainConsole` 防拖出可视区（最小 640×480）、窄窗（≤900×600）自动铺满。原生系统窗口边缘/标题栏调整属宿主职责，未在本轮原生/安装态验收。
- **UI-P05 工作区拆分**：[DockWorkspace.tsx](../../frontend/src/workspace/DockWorkspace.tsx) 已实现左右/上下分栏、分隔条、标签、关闭/重开、浮动/停靠/最大化、锁定、预设/重置/保存/读取/应用/确认恢复布局，面板独立滚动（`.dock-slot{overflow:auto}`）；窄屏 `data-compact-reader` 隐藏标签。A0 canonical host surface 的 narrow-dock library/reader 在限定视口通过。

**A0 真实浏览器门禁（Chromium 1228，SIMULATED host/Core fixture）**

- 三次对照：run1（含本轮改动）**FAIL**（[a0_browser_smoke.py](../../scripts/a0_browser_smoke.py#L1843) 的 `read_narrow_dock_library` 在正文载入前抢先断言）；run2（暂存本轮前端改动＝HEAD 原样）**PASS**；run3（恢复本轮改动）**PASS**。
- 证据：`scripts/a0_browser_smoke.py`，schema `archeaxis/canonical-browser-smoke/v4`，`status=PASS`，`errors=[]`，`base_commit=031fcfea847691f7d3eb1aef92646538a8b3aabd`；13 档视口×5 主题的几何/焦点/对比/品牌身份/导航抽屉/状态栏可访问性 + canonical host surface。
- 判定：run1 失败是**正文载入竞态（测试侧）**，与本轮文案改动**无关**——失败路径不经过任何改动文件，且 run3 携带相同改动仍 PASS。原失败保留；建议后续给 `read_narrow_dock_library` 增加正文等待（**不改断言**），本轮**未修改门禁**以免掩蔽。
- 边界：真实 Chromium + 合成 host/Core，**非**安装态 Tauri/WebView2、**非**物理 IME/DPI、**非** Owner 验收。故系统 DPI（UI-P06 物理部分）、真实后端（UI-P11/13/14）、安装态（UI-P24）仍 **NOT_EXECUTED**。

**结论**：UI-P03—P05 **PASS（结构层＋A0 真实浏览器几何/主题）**；安装态、物理 DPI、Owner 视觉验收 **NOT_EXECUTED**，整体仍 **PARTIAL**。

## 2026-10-19 RC-P01/P02 分支与 PR 盘点（只读，未合并／未删除）

Owner 明确要求"分支合并、体积清理、双端仓库及目录规范"。本轮执行 **RC-P01/P02 只读盘点**（不合并、不删除、不改写历史）。

**现场（fetch 后实测）**

- 远端 7 heads：`main`=fe18fdc3、`codex/sync-20261019`=031fcfea、`codex/character-memory-ui-20261015`=02368f0e、`codex/layout-preferences-20261014`=9daf1221、`codex/closure-integration-20261014`=015a5cff、`codex/remaining-loop-stage1-20261013`=b2e283b6、`codex/ui-polish-20261013`=a69a55f7。
- 本地 26 heads、1 worktree（仅主检出 `031fcfea [codex/sync-20261019]`）。本地 tracking 原缺 `remaining-loop-stage1`，`git fetch origin` 已补全（只读刷新）。
- 开放 PR 均 Draft：192(layout-preferences, `CONFLICTING`)、193(character-memory-ui, `CONFLICTING`)、194(sync-20261019, `MERGEABLE`)。

**patch 等价（`git cherry HEAD origin/<branch>`；`-`=已吸收，`+`=未吸收）**

| 分支 | HEAD 祖先 | 独有 `+` | 判定 |
| --- | --- | --- | --- |
| codex/remaining-loop-stage1-20261013 | 是 | 0 | 已并入 current 线 |
| codex/layout-preferences-20261014 (PR192) | 否 | 0（6/6 `-`） | 内容已吸收 |
| codex/closure-integration-20261014 | 否 | 0（7/7 `-`） | 内容已吸收 |
| codex/character-memory-ui-20261015 (PR193) | 否 | 0（55/55 `-`） | **完全吸收** |
| codex/ui-polish-20261013 | 否 | 1（`a69a55f7`） | 唯一未吸收提交 |
| `codex/sync-20261019` (PR194) | — | 当前 HEAD | 待审阅＋required CI |

`ui-polish` 的 `a69a55f7` 含 `frontend/src/design-system/ui-polish.css`(≈350 行) 及 App/main/SpaceRail/tokens/ui-first/CanonicalWorkspaceSpace 与文档改动，与活动指针 `frontend_execution_overlay.ui_commit=a69a55f7` 记录的"独立 UI 分支纳入合并"一致。

**结论与后续条件（本轮未执行 RC-P03/P04）**

- **不盲合旧整包**：PR192/193 内容已 patch 吸收且仅 Draft+CONFLICTING，"非祖先"不等于缺功能；处置须审阅 ＋ required CI 后再定（保留/后继已包含/拆分）。本轮**未合并、未关闭、未删除**任何分支或 PR。
- **PR194**：`MERGEABLE`，可入 main，但须**当前审阅 ＋ required exact-SHA CI 合格**；本轮未取得该 SHA 合格，**未 merge**。
- **ui-polish 的 1 个 `+` 提交**：`+` 仅表示 patch 不重复、**不等于内容缺失**；需与 HEAD 逐文件比对后再定 cherry-pick/merge 或判为已演化覆盖。本轮未处置。
- **本地 25 个非 HEAD 分支**（多为本地未推送）需逐分支 patch 等价与归属核对（RC-P02 后续）；本轮未删除任何分支/文件。
- **RC-P04 清理条件**：证实无独有内容 ＋ PR 妥善处理 ＋ worktree/Agent 不占用 ＋ 授权读回；本轮不满足全部条件，**不执行删除**。

## 2026-10-19 RC-P05 体积基线与归属（只读计量，未删除）

测法与时间：PowerShell `Get-ChildItem -Recurse -File | Measure-Object Length -Sum`（**逻辑字节**，未计硬链接/共享）；Git 用 `git count-objects -vH`。2026-10-19。

**全仓顶层（MB）**：`.project-local` **70670.5**、assets 997.4、`.venv` 903.9、docs 553.8、`.git` **442.7**、frontend 254.5、data 97.6，其余均 <15。Git 对象：in-pack 36493 对象／**size-pack 439.48 MiB**，loose 126／654.27 KiB。
→ Owner 历史所说"50多GB"主体是 `.project-local` 的开发输出，不是工作区源码或 Git 历史。

**`.project-local` 子项（MB／文件数）**

| 子项 | MB | 文件数 | 归属/再生性初判 |
| --- | --- | --- | --- |
| build | 40368.5 | 74205 | Tauri/Core/frontend 构建输出 → 可重建 |
| audits | 11767.4 | 28498 | 审计产出/证据 → **需逐项核是否含唯一失败证据** |
| runs | 7104.2 | 73694 | 运行证据/候选 → 部分被回执引用 |
| candidates | 4634.1 | 136671 | 构建候选 → 可重建 |
| archives | 3595.5 | 560 | `record-20261009` 原始字节保全 → **KEEP** |
| rt / rt-python-input | 616.0 / 594.7 | 19523 / 19097 | 运行临时/输入 → 可再生 |
| cache | 518.9 | 15374 | 缓存 → 可再生 |
| g | 298.7 | 1 | 单文件，身份**待核** |
| inputs / task-runtime / tmp | 237.8 / 234.5 / 112.0 | 325 / 2744 / 1364 | 输入/运行临时 → 可再生 |
| dep-src-clean / gh-cache / npm-cache / uv-cache | 93.3 / 2.2 / 0 / 0 | … | 依赖/缓存 → 可再生 |

**分类（待授权，本轮未执行任何删除）**

- **KEEP**：`archives`（原字节保全）、`backups`、`state`、被唯一执行记录/回执引用的失败证据。
- **REGENERABLE_DELETE_CANDIDATE**：`build`、`candidates`、`cache`、`tmp`、`rt`、`rt-python-input`、`dep-src-clean`、`gh-cache`、`npm-cache`、`uv-cache`（构建缓存/候选，可重建）。
- **UNRESOLVED**：`g`（单文件 298.7MB，身份未核）、`audits`/`runs` 内是否含**唯一**失败证据（须逐项核后再定）。

**边界**：仅逻辑字节、未计共享；**未删除任何对象**；大范围删除需精确路径授权（活动指针 `bulk_delete=EXACT_PATH_GRANT_REQUIRED`；S01.A 明确"大量删除不在默认许可内"）。压缩/历史改写未授权。

## 2026-10-19 RC-P06 本地减重（Owner 已明确授权，已执行）

授权：Owner 明确"全部授权给你，不要打扰我"。范围＝可重建构建缓存（保留 archives、backups、被回执引用的证据与未知对象）。

**执行与结果**

- 删除：`.project-local/` 下 `build`(40368.5MB)、`candidates`(4634.1MB)、`tmp`(112.0)、`rt`(616.0)、`rt-python-input`(594.7)、`dep-src-clean`(93.3)、`gh-cache`(2.2)、`npm-cache`、`uv-cache`、`uv-cache-agent-icon`。
- 读回：`.project-local` **70,670.5 MB → 23,730.9 MB**，释放 ≈ **46,939.6 MB（≈45.8 GB）**。
- **PARTIAL/DENIED**：`.project-local/cache` 仅部分删除；`cache/pytest` 与 `cache/uv/sdists-v9/<hash>/.../archeaxis_workspace-0.6.14-0.editable-py3-none-any.whl` 返回 **Access denied**（≈518.9MB 未释放）。按治理**未改 ACL、未换身份绕过**，列为 **UNRESOLVED**。
- **保留**：`archives`(3595.5MB，`record-20261009` 原字节保全)、`backups`、`state`、`runs`、`audits`、`inputs`、`task-runtime`、`staging`、`acceptance`、`g`(298.7MB 待核) 等。

**边界**：仅逻辑字节（未计硬链接/共享）；**Git 历史未改写**；未删除任何未知/共享对象；远端与 Actions 产物未处理（留 RC-P08）。

## 2026-10-19 交付与门禁：提交、CI、A0 竞态修复

- **提交并推送**：`5a2d5e6e605c600787b51bdb69d48301f5c41772`（UI-P02 术语收敛 8 处＋测试消费者＋本执行记录）已推送到 `origin/codex/sync-20261019`；远端读回 `5a2d5e6e`，**双端一致**。工作树干净。
- **CI（新 SHA）**：`5a2d5e6e` 的 run `39280943472` 为 **queued／gateplan pending**（此前 `39271537141` 等为 cancelled）。**required exact-SHA CI 未完成** → PR194 不合并、不发布（RC-P03 继续受阻）。
- **A0 门禁竞态修复**：[a0_browser_smoke.py](../../scripts/a0_browser_smoke.py#L1845-L1850) 的 `read_narrow_dock_library` 增加“等实际正文出现再断言”的 `wait_for_function`（检查编辑器 `innerText`），**断言不放宽**。复跑 A0：`status=PASS`、`errors=[]`、`base_commit=5a2d5e6e`。
- **过程保留**：第一次尝试用 `get_by_text(...).wait_for()` 等待不可见、超时失败——方案无效已替换为 `innerText` 等待后通过；原始 run1 FAIL 与本次中间 FAIL 均保留，不改写成 PASS。
- **前端生产构建**：`node scripts/runtime/frontend.mjs build` → **PASS**（exit 0，"✓ built in 2.90s"；产物 `.project-local/runs/be268a2d33/c4fd968edc9b/artifacts/frontend-dist`，子运行 `bt-fd39d9af` PASS）。大 chunk（index ≈1.9MB）与既有 Rust 警告保留，未改阈值。

## 2026-10-19/20 installer-lifecycle 根因定位与修复（BE-P13 / UI-P24）

**CI 失败定位（run 39275027426，head 031fcfea）**：唯一真实失败门禁是 **installer-lifecycle**（`a0-gates` 只是聚合器，因 required `installer-lifecycle`=failure 而 exit1；其余 12 门禁 success，5 个 skipped）。下载 `installed-native-journey` 产物 readback：

- 失败 receipt `ok=false`，`error="WebDriverProtocolError: element not interactable"`。
- traceback：`aaos01_grouped_owner_loop.py` `run_grouped_loop` → `ui.page("16")` → 点 `.navigation-sidebar button[data-page-id="15"]`（父入口）→ 隐藏侧栏不可交互。
- **根因**：安装态窗口高度 ≤760px（容器断点）时产品**按设计隐藏** `.navigation-sidebar`、改用“打开产品导航”抽屉；grouped 探针仍直接点隐藏侧栏。这正是 UI-P24「先定位既有 grouped UI 安装失败」的对象。

**修复**：[aaos01_grouped_owner_loop.py](../../scripts/probes/aaos01_grouped_owner_loop.py#L558-L601) 的 `page()` 改为**可见导航面**——侧栏可见用侧栏，否则走 `.ui-navigation-drawer`；父/子两步都在可见面完成，抽屉激活后重新展开。**不使用 JS click 或 hash 绕过，断言不放宽**。

**验证**：`py_compile` exit 0；探针合同测试 **71 passed**（test_native_preview_ci / test_owned_webdriver_transport / test_probe_identity_regression / test_native_owned_descendant_drain）。**安装态真实旅程资格仍待新 exact-SHA CI**（本地无法运行 NSIS 安装）→ 状态 **CANDIDATE_FIX / UNVERIFIED_RUNTIME**。

## 2026-10-20 UI-P06—P15 状态核查（只补差距）

- **UI-P06/P07/P08**：核心项（外层/主控台/Dock/portal 的容器响应、字号密度 token、玻璃单圆角盒＋五主题、对比/焦点）已由 **A0 13 档视口×5 主题**覆盖；物理系统 DPI 与 Owner 视觉验收属 **M01 → NOT_EXECUTED**。`tokens.css` 中按 viewport 的 `@media` 是**为 portal（位于 `console` 容器外）保留的有意设计**，不改为 `@container`。
- **UI-P09 全导航/弹层**：A0 覆盖导航抽屉、设置菜单的命中/几何/字号；OK。
- **UI-P10 键盘/输入**：App/ConsoleWindow 实现 IME composition 守卫、Esc 取消进行中手势、方向键移动/调整；组件测试覆盖。
- **UI-P11 状态/反馈**：保存/未确认走 `workingNotice` 与 Core ACK 语义；202 取消/未确认不报成功有回归。
- **UI-P12 导入**：`CanonicalExchangeSpace`/`FolderIngest` 已逐件结果与失败；**耐久批次跨重启**属 BE-P03 → 待后端。
- **UI-P13 阅读编辑/版本**：`CanonicalLibrarySpace`(reader/history) + `VersionSourcePanel` 已有。
- **UI-P14 免费检索界面**：**缺独立的外部（百科/社区/科研）检索 UI**；Crossref/OpenAlex/Wikidata 仅存在于生成的 `resource-catalog`/`capability-catalog` 与能力详情。真实三源检索属 **BE-P04** → **BLOCKED（后端未接线，前端不伪造）**。
- **UI-P15 图谱**：`CanonicalRelationSpace` + `ConstellationGraph`（Neural 供体）已有；组件/几何测试覆盖；**FPS/GPU/内存性能未测**。

**结论**：UI-P06—P15 组件/结构层基本就绪且有 A0 几何/主题覆盖；UI-P14 为具名后端阻断。整体仍 **PARTIAL**。

## 2026-10-20 BE-P01/BE-P03 与 UI-P16—P24 源码核查（只读）

**BE-P01 核心保存/恢复——已实现**：`archeaxis-api/src/documents.rs` create(`create_request_id`)/save(`expected_version`)/restore；`archeaxis-domain/src/document.rs` 幂等（`request_id`→`doc_req_*` 重复创建检测）＋版本冲突 `Error::Conflict(current)`；`archeaxis-store-sqlite/src/writer.rs` 单线程有界写队列（唯一 canonical writer）；`backup.rs`/`workspace_backup.rs` 备份 create/list/preview/restore（Online Backup API、sha256 与对象校验）。测试：`archeaxis-api/tests/document_draft_loop.rs`、`document_pagination.rs`、`archeaxis-domain/tests/backup_safety.rs`、`archeaxis-store-sqlite/tests/writer.rs`。

**BE-P03 批次耐久——部分实现，真实缺口＝批次成员列表不持久化**：FolderIngest 逐文件 `source_import`＋`job_enqueue`（内容寻址 `job_id`），冻结请求经 `JobJournal` 跨重启找回（[FolderIngest.tsx](../../frontend/src/components/FolderIngest.tsx#L269)）；但 [FolderIngest.tsx:283](../../frontend/src/components/FolderIngest.tsx#L283) **明确声明“当前队列是本页面会话状态，不声称重启恢复”**——即**“哪些文件属于本批次”不跨重启重建**。补齐需 Core 批次 schema＋命令（较大改动，本轮**未实施**，避免未验证半成品破坏 Rust 构建/合同）。

**UI-P16—P24——组件层已存在**：`presentation/uiPages.ts` 全 22 页 `implemented=true`，`SpaceView.tsx` 均有生产组件（无 `ui-pending-page` 兜底命中）；UI-P16 `CanonicalLearningJourneySpace`/`CanonicalTeachingSpace`/`KnowledgeCoursePanel`/`ImportedCoursePanel`；UI-P17 `ModelConfigurationPanel`/`MachineAnswerPanel`/`CanonicalAiJourneySpace`；UI-P18 `CanonicalCapabilitiesSpace`/`CanonicalResourcesSpace`；UI-P19 `XiaoqiPanel`/`XiaoqiAvatar`/`ConversationPanel`；UI-P20 `DiagnosticConsole`/`BackupPanel`/`VersionSourcePanel`。**缺口**：UI-P21 无障碍扫描仅覆盖少数页面（非全 22 页）；UI-P23 无全页面自动视觉回归（仅 A0 脚本）；UI-P22 性能基线未测。

## 2026-10-20 TRAE承接与前端覆盖修复

本轮映射 **UI-P01/UF00/G01/H01、UI-P04/UF01/02、UI-P07/08/S01、UI-P21/23/UF13**。没有重新搭壳、替换Dock/图谱renderer或扩写后端。接手时工作树干净，原分支`codex/sync-20261019`、HEAD`206d56dafd00d0d3ccfd949ce6a4e424a324112a`；Owner补充的TRAE最后总结明确以该SHA为交付终点。本轮直接基于此SHA，保留UI-P02术语、A0正文等待和grouped可见导航修复及原记录，不重复实施。

**现场CI与安装失败的后继结果**：GitHub REST及连接器日志实查[run39344981292](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39344981292)成功，installer-lifecycle/a0-gates成功；5个not-required作业skipped，不称全部作业执行。run关联PR头206d56da，实际checkout是临时PR合并对象`733c5005`，其完整身份、tree与父提交保存在[历史CI对象回执](../history/product-loop-20261019/ci-39344981292-checkout.json)，不能要求后继fresh clone仍包含旧PR临时对象；父提交为main`fe18fdc3`和206d56da，合并候选tree与该头相同。安装日志三段原生旅程`ok=true`，产物ID`12231488177`。因此TRAE总结时仍在跑的安装失败已有后继工程回归通过；旧FAIL保留，不继续当成当前未修源码。此CI**不覆盖本轮新增代码**，也不证明日常Green已更新或完整业务闭环。

**本轮原问题、修改与回归**：

- 新增`scripts/probes/aaos_ui_coverage.py`，复用A0的正式前端、隔离host/文档fixture、回环Vite和进程回收；从生产UI_PAGES发现22语义角色。通过实际可见侧栏/抽屉导航；角色18由能力目录卡片进入详情，不能凭空寻找侧栏18。未知fixture操作明确501；拦截外部请求，无真实模型、私有材料或业务库写入。保留每页文本状态、几何、axe原始violations/incomplete、截图、浏览器/DPR/字体和源码身份。
- 实际发现并修复：Dock组与正文同名地标、页面标题跳级、搜索/诊断按钮可见文字与朗读名称不符、画布滚动区缺少合法role。窗口帮助移到现有导航地标内，不把整应用嵌入新的region；保留main/banner/contentinfo层级。诊断按钮名称随可见文案变化，组件测试与A0/原生安装探针消费者同步；严格JSON、身份、版本、保存和重启断言不降低。
- 截图发现Dock浅色主题仍沿用深灰标签、13px字。新增字体门槛先RED：white/640×480实测13px、未选底色rgb(45,45,45)。在现有Dock样式中将所有标签状态映射到AAOS语义颜色及14px菜单字号；五主题×知识库/研究10项定向GREEN，实际查看浅色修复截图。未换Dockview主题体系或渲染器。
- 内部主控台原只有右下角调整柄。补其余四边/三角，拖左/上时固定对边，保持640×480下限、可视范围、Esc/pointercancel回滚、原键盘等价与草稿宿主。新增回归先RED（缺边柄），修复后5项组件通过；cosmic/white真实Chromium对八边角共16次可信指针调整、命中与Esc还原通过。原生Windows边缘调整仍属独立资格，不能外推。

**源码与验证边界**：最终产品补丁在dev.py回执中的`source_patch_sha256=cad6de5f884fd7508129d5d1ff9254e7fa527b629da159e0af8bc46886d1bf0d`，base=206d56da；以下最终运行source_consistent=true。本节后继文档不改变产品源码，实际交付SHA须从Git现场读回。

| 检查 | 本轮结果与范围 |
| --- | --- |
| 全页面入口态覆盖 | 22角色×cosmic/white×1600×1000及640×480＝88项；其余三主题×22角色×640×480＝66项，报告均PASS_AUTOMATED_ONLY、无pageerror/外网请求。属于各自源码时点；后继Dock/边角变更分别由定向与最终A0复验，不伪称完整状态笛卡尔积或同候选J1—J6。 |
| 读取失败状态 | 最终补丁对sources_list/documents_list注入503，cosmic/640×480下22角色遍历通过；实际查看知识库错误与重试截图，不把失败显示成空目录成功。其他操作未配置fixture不是产品后端缺失的证据。 |
| axe | 使用本机已登记axe4.14.0；保留color-contrast等incomplete，88项有184条incomplete规则结果、66项有138条、读取失败22项有49条。无已报告violation不代表完整合规，屏幕阅读器/物理IME/DPI未测。 |
| 截图 | 保存上述页面截图并实际查看四张全页联系图及重点页面原图；首轮截图是覆盖快照，尚无批准的像素差异基准，UI-P23仍PARTIAL。 |
| 最终A0 | `ui-a0-final-20261020` PASS，13档视口/五主题及原导航、正文、焦点等断言；真实Chromium、SYNTHETIC host/Core，319.86秒，exit0。 |
| 最终前端套件 | `ui-frontend-final-suite-20261020`：182文件/1845项通过，无skip，exit0。首次全套有3项名称/标题消费者失败，定向修复后才执行本次最终套件；历史失败未删除。 |
| 探针合同 | `ui-probe-consumers-20261020`：114项及150子项通过；退出时pyreadline3析构句柄警告保留，进程exit0。仅合同层，非新原生安装通过。 |
| 类型/构建/lint | 最终TypeScript、正式frontend.mjs build及选定Ruff错误规则通过；构建子运行346cba7ba83a，既有大chunk警告保留，未改阈值。 |

证据统一在`.project-local/runs/be268a2d33/<run-id>/`的`artifacts/execution.json`及日志；页面run为`ui-coverage-baseline-20261020`、`ui-coverage-final-20261020`、`ui-coverage-other-themes-20261020`、`ui-read-failure-20261020`，Dock为`ui-dock-density-red/green-20261020`，窗口为`ui-console-edges-red/green-20261020`及`ui-console-edges-browser3-20261020`。首次探针等待隐藏侧栏、18入口误判、axe临时frame初始化fixture及过早读React几何的失败均保留并修正探针；未关闭axe规则或放松业务断言。浏览器和自有Vite由既有helper关闭，各覆盖报告port_closed=true；Vite被terminate后的exit1不称正常退出。原始截图/日志仅本地保留，不提交运行资料。

**RC-P01/02推进**：实际远端仍7heads，PR194 Draft/Open，main=fe18fdc3；本地27heads（含当前与main）、唯一worktree。逐一对25个其他本地分支查git cherry：19个无`+`，6个仍有不等价patch，共10提交；`+`不直接证明缺功能。涉及ASTRYN、machine取消、glass、旧Avalonia cosmic、窄窗Inspector、ui-polish。main已为当前HEAD祖先；ui-polish导入/导航图标、glass本地搜索/布局恢复、窄窗Inspector等关键消费者可在当前源码找到，但尚不能据此批量删分支。精确提交/逐分支结果保留于`ui-a0-final-20261020/artifacts/branch-readback.json`。本轮未合并/关闭PR、未删分支/资料、未新增减重；RC-P03—08继续按候选资格及精确清单分批处理。

**当前仍PARTIAL**：UI-P02全域术语、UI-P05窄窗拆分与布局真实重启、UI-P14三类外部检索界面/真实接线、UI-P21辅助技术人工检查、UI-P22性能、UI-P23批准视觉基准及UI-P24本轮候选安装/Owner验收尚未全量收口。保持前端先行；前端阶段未交付，不启动BE-P01—15或缩减CL-01—07/J1—J6。真实云端模型、耐久批次、外部研究和扩展生命周期欠账保留。未覆盖Green、发布或真实用户数据。回退仅针对本轮列明文件，保留TRAE基线与全部历史证据；不执行整工作区reset/restore。

后继交付与CI：产品/覆盖切片已提交并正常推送`66a59d1f36a0f113142e67e121dd4772c023011a`，远端SHA读回一致，直接父提交206d56da。其[CI39414692550](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39414692550)实际FAIL：lint的architecture guard拒绝新增覆盖脚本的sys.path修改，并将直接写出的HTTP路径`/workspace/api/`判为外部绝对路径；后续required作业skipped，不当PASS。现改用项目包导入，A0同时兼容包导入/直接入口，并复用已有API_PREFIX/WORKSPACE_PREFIX；没有修改门禁或加入豁免。`ui-coverage-architecture-fix-20261020`架构门禁通过，`ui-architecture-import-regressions-20261020`原A0/架构31项通过，`ui-ci-ruff-final-20261020`与CI同命令Ruff通过，`ui-coverage-package-import-20261020`实际white/640×480知识库试点通过并回收自有服务。此后继仅调整审计脚本的导入/路由引用，产品源码未改变；新exact-SHA CI仍须另行取得，PR194/main未合并、Green未更新。

## 2026-10-20 UI-P05：已开标签分栏、窄窗退回与失效布局保护

映射UI-P05/UF02/UF12、UI-P06/10/11及UI-P01/G01的失败接续。基线为0e5755b4，TRAE的206d56da完整保留。本轮只修改既有DockWorkspace与有限布局适配，不换Dockview/业务renderer、不扩写后端。

- **复现与修复**：先以实际浏览器和组件测试复现“03阅读与17能力已作为标签打开，再点左右分栏只激活标签”；existing分支忽略direction。现移动既有面板；已有两组时移动组以切换左右/上下轴，不凭空多开业务会话。左右/上下使用各自Dockview API实际方向（新增below与移动bottom分别适配）。
- **窄窗**：ResizeObserver读取真实`.dock-surface`宽高，按各分支比例及320×180最小正文区域判断；不足时临时合并为标签，提供可见说明，空间恢复后恢复原分组。原始布局偏好、对象绑定和锁定保留；窄窗保存不会偷偷覆盖为临时单栏。用户主动关闭/新增标签后检查即时panels，避免延迟layout事件导致关闭标签在放大时复活；关闭/重开仍是同一草稿DOM/业务会话。窄窗临时标签期间不允许拖拽/再浮动来制造不可见组。
- **负例保护**：新增失效保存布局（重复业务宿主）回归；初次实现恢复前停车导致拒绝时正文被隐藏，RED后修复为先完成验证/布局替换再变更响应偏好，保留同一正文及输入。Dock旧slot只停车仍由自身持有的宿主，避免过期清理抢走新slot。
- **已有CI失败接续**：[run39415324811](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39415324811)的head0e5755b4已出现两个required失败：browser-smoke在1280×720缩放语义知识库测到首项高度0（行位于折叠线下）；现先真实滚动到文档按钮再保留原命中/24px断言，并在断言前留截图。test(3.12)两项对象门禁失败源于旧PR临时merge对象不在fresh clone；完整SHA/tree/父提交经GitHub REST重读后保全到历史CI对象回执，当前记录引用该历史证据。未修改门禁、豁免规则或降低断言。其他已通过作业不能抵消失败；installer-lifecycle当时仍运行，PR194仍Draft/Open、无已提交review，main仍fe18fdc3。

| 验证 | 实测与边界 |
| --- | --- |
| 原问题RED | `ui-dock-split-red-20261020`两项失败、`ui-dock-browser-red-20261020`实际分栏失败；原截图/日志保留。失效布局RED为`ui-dock-rejected-red-20261020`。 |
| 最终定向 | `ui-dock-rejected-green-20261020`：3文件/34项PASS，含窄窗保存、关闭不复活、同一草稿、浮动对象身份与拒绝布局；native command由fixture模拟，不能称真实持久化。 |
| 浏览器实际输入 | `ui-dock-browser-final4-20261020`：Chromium149.0.7827.55、DPR1、reduced-motion，cosmic/white各自左右/上下轴几何、640×480标签/阅读切换、1600×1000恢复均PASS；入口03共2项PASS_AUTOMATED_ONLY，axe无violation、4条incomplete保留。实际查看10帧联系图及纵向/窄窗/恢复原图。仍是SYNTHETIC host/Core。 |
| 最终前端套件 | `ui-dock-final-suite2-20261020`：182文件/1851项通过，exit0，36.20秒。 |
| 固定源码A0 | `ui-dock-a0-final2-20261020`：正式完整A0 PASS，13档视口/五主题及既有业务/导航断言，312.92秒、exit0、source_consistent=true；源码补丁4a4d0ba2eb80357a5badcca10943ebabb87aeb1d6eab5dbd63978c9bf347c20f，base0e5755b4。此前`ui-dock-a0-20261020`运行期间源码变动/HMR并在模板按钮测量时报DOM脱离，保留FAIL，不重命名为成功。 |
| 合同与文档 | `ui-dock-ci-contracts-20261020`：原A0/架构31项PASS；`ui-dock-audit-20261020`：对象门禁15项PASS（使用既有正常SSH只读核远端）；Ruff按CI同命令PASS。pyreadline3退出析构句柄警告仍保留，不影响exit0。 |
| 类型/构建 | TypeScript PASS；最终正式frontend.mjs build的run为d156ac815141，PASS，原大chunk警告保留。 |

证据仍在`.project-local/runs/be268a2d33/<run-id>/`；浏览器报告自有Vite PID33708、端口63301已关闭，terminate后exit1不称优雅退出。探针曾把多个保留/隐藏space-view当单页、以及summary范围过宽而失败，已改为实际可见正文与布局自身summary；所有FAIL保留，没有用隐藏点击绕过产品入口。没有宣称原生DPI、物理IME、屏幕阅读器、真实Core重启布局或Owner验收完成，UI-P05及前端总体仍PARTIAL。下一独立前端片为UI-P02能力中心工程文案与运行诊断分离；不启动后端阶段。未合main、未清理分支/数据、未覆盖Green。

## 2026-10-20 UI-P02能力中心：中文语义、诊断保真与详情焦点

本片映射UI-P02/UF04/UF06、UI-P09/10/18/21，基于本地checkpoint28533c26；没有替换能力目录、更新生成合同或新增注册器。目录身份、路由、16项父能力与186条原始设计输入/原SHA均保留，按原始编号和原始短语的搜索继续可用。

**产品修改**：普通目录去掉内部入口编号与Atlas/implementation措辞；详情用中文表示已有声明/尚未接入、运行未知、独立证据未核验。资料访问、指纹校验、样例、错误率、降级、恢复点等前提改用清楚中文。原atlas/implementation完整进入“能力登记与运行声明”，复用来源完整进入既有运行诊断，186条原文及来源指纹可逐父能力完整读出。原始运行错误码/UNKNOWN/UNVERIFIED及完整权限观察保留到诊断，普通页仍明确禁用、未知和未验证，不把连接或目录登记升格为业务成功。内置扩展说明保留版本/依赖/许可，分别标发布者、许可审查、业务与运行未知；完整manifest和校验信息进入同一诊断通道。

**实际截图发现的额外缺陷**：从目录下方选择能力后，详情沿用目录滚动位置，标题可完全离屏；自动axe没有替代该视觉结论。新增焦点RED（原body持焦）、浏览器标题裁切断言，并修为选中详情后等待Radix Presence完成一次渲染帧，再聚焦/定位所选标题。手动标签切换不设置该请求，不抢走正常Tab焦点。首次直接effect过早聚焦的FAIL及测试误用exact选项造成的类型失败均保留；最终定向与正式构建通过。未删除/放松命中、裁切、未知状态或未来禁用断言。

| 检查 | 本地证据与界限 |
| --- | --- |
| 文案RED与消费者 | `ui-capability-copy-red-20261020`复现内部ID/枚举直接出现在普通详情。`ui-capability-copy-final-20261020`9文件/124项通过；后继原始186项改由真实诊断通道逐父能力核对，不修改原始fixture或仅放宽匹配。 |
| 全套与失败修复 | `ui-capability-final-suite-20261020`182文件/1852项，1846通过、6个旧名称/措辞消费者失败，保留FAIL。随后只重跑失败/受影响门禁：`ui-capability-consumers-final2-20261020`3文件/40项通过；不把两个运行相加虚称一次完整1852项绿。 |
| 焦点最终定向 | `ui-capability-focus-green2-20261020`6文件/98项通过，包括App、未来能力、原始设计、状态过期/错scope、模板路由与新标题焦点；属于SIMULATED command的本地测试。 |
| 最终浏览器 | `ui-capability-heading-final-20261020`：现有16能力×cosmic/white×1600×1000及640×480＝64项PASS_AUTOMATED_ONLY；每项详情标题完整可见且实际命中，axe无violation、192条incomplete保留，无pageerror/外网请求。Chromium149.0.7827.55、DPR1、reduced-motion；SYNTHETIC host/Core、source_consistent=true，patch=d30d71e9ebd21ff616038ca8b64cdd16bd073d6948886910431eecdbb4e7bc76，base28533c26。实际查看修复前后联系图及窄窗/宽窗原图，不称已批准像素基准或全面无障碍合规。 |
| 探针修正与保留 | 全能力探针按实际目录枚举，不另建16项注册表；先以8秒冷启动超时失败，现对齐原A0的30秒导航预算，交互仍8秒。`ui-capability-all-details2-20261020`64项axe通过但截图暴露标题缺陷；后继`ui-capability-heading-all-20261020`明确FAIL，最终修复后才得到上述新断言通过。所有旧FAIL/截图保留。 |
| 构建与门禁 | 最终正式frontend.mjs build为959a32e99802，TypeScript/构建PASS，既有大chunk警告保留。A0/架构合同`ui-capability-probe-contracts-final-20261020`31项通过；架构guard、CI同命令Ruff、文档Authority通过（外部/私人4项仍UNVERIFIED）。本片未再跑P05完整A0，新聚合SHA由CI重新资格。 |

证据仍在`.project-local/runs/be268a2d33/<run-id>/`，截图与运行资料不提交。最终浏览器自有PID16756、端口50356已回收，port_closed=true；terminate后的exit1不称优雅退出。旧0e5755b4的CI39415324811最终FAIL，installer-lifecycle成功、a0-gates失败，不能合入main。两个新前端checkpoint拟合批正常推送，实际SHA/CI由现场读回，不把本地commit称双端一致。

**仍待接续**：UI-P02全域工程术语（模板需求、部分图谱/表达/系统说明等）、UI-P05真实Core重启与原生几何、UI-P14三类免费检索界面/接线、UI-P21人工辅助技术、UI-P22性能规模数据、UI-P23正式视觉基准、UI-P24新候选原生安装/Owner验收继续PARTIAL/UNVERIFIED。前端尚未阶段交付；不据目录/截图恢复被冻结能力，不进入BE-P01—15，不缩减CL-01—07/J1—J6。RC-P01—08原账保留；本片不删分支、文件或远端产物、不改main、Green、模型/provider或共享资源。回退按本片文件/提交反向修订，保留TRAE基线及所有失败证据。


本片结束检查补充：第一次worktree目录规范仅因Add-Content引入CRLF失败，已将本唯一执行记录规范为UTF-8无BOM/LF，保持原内容与失败记录。对应复验见ui-capability-record-conventions2-20261020；未修改规范规则。

## 2026-10-20 RC-P03/P04：主线合并与分支收敛

Owner后继明确要求“该合并的合并啊”。本轮完成已获授权的主线交付和精确分支清理，不以全量前端尚未完成为由搁置合格切片。完整分支头、逐分支等价patch、保留项、恢复档及现场读回见[不可变分支收敛证据](../history/product-loop-20261019/branch-convergence-20261020.json)；实际进度仍只更新本文件。

| 对象 | 本轮实测与处置 |
| --- | --- |
| PR194候选 | head2574b40d；[CI39423295711](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39423295711)最终SUCCESS，含browser-smoke、Rust、系统测试、desktop-fast、Windows构建、installer-lifecycle及a0-gates。5个非required作业skipped，不称执行了全矩阵。实际CI checkout为4b749b6b，其tree与head相同，完整身份在上述回执。 |
| 审阅 | 冻结2574b40d，完成Dock/主控台/能力详情改动及分支等价核对；依VERIFICATION_POLICY的权限/恢复触发，另完成一次只读定向review，核Observer有限只读/路径、workspace/epoch/version/hash/过期、machine准入/取消/清理UNKNOWN及固定bridge命令，未发现该范围阻断缺陷。GitHub无已提交approval/未解决thread；实际main ruleset要求a0-gates，无审批人数要求。源码审阅不称全仓安全审计或运行验证。 |
| main | [PR194](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/194)已以merge方式合入52147d6b，父提交为原main fe18fdc3及候选2574b40d；tree815228eb与CI候选完全相同。正常fetch后，本地main/origin/main读回一致，TRAE206d56da仍是main祖先。 |
| main后继CI | [CI39427148307](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39427148307)已触发；本回执写入时尚未完成，**UNVERIFIED**，须现场读回后才称main该SHA CI通过。PR候选通过与main后继CI分别记账。 |
| PR192/193 | 原头9daf1221/02368f0e分别6/55个非祖先提交均有等价patch、无独有patch。PR194合入后，已将两者以“被后继包含”关闭并保留后继链接；没有把旧冲突整包再合一次，也不伪称这两个PR自身merged。 |
| 分支清理 | 再核精确头、main等价补丁、无独有merge解决、唯一worktree/无占用后，删除19个本地分支与4个远端分支。远端删除为character-memory-ui、layout-preferences、closure-integration、remaining-loop-stage1各原日期分支；完整名字/SHA在回执。读回本地27→8 heads、远端7→3 heads；main及当前writer分支保留。 |
| 保留6分支 | astryn/integration、closure-machine、glass-cabin、旧Avalonia minimax-cosmic、reader-inspector-responsive、ui-polish仍有不等价patch，共10提交。已发现部分功能在后继实现中存在，但尚未证明所有原件/补丁均可退役，因此本轮保留；不盲merge或删除。 |

**回退与归属**：精确原分支先归档到本项目忽略运行目录`.project-local/runs/be268a2d33/rc-merge-readback-20261020/artifacts/branch-recovery.bundle`，3,292,510字节，SHA-256为`4710efae60761a471889e76f84f64c9ba952d89c6e953b13c5ac9c26ffc77721`；git bundle verify通过，删除前再次核大小/hash。它只保存列明旧分支的必要恢复对象，依赖已在main的历史；按回执先验hash，再以bundle原ref fetch回指定分支。该恢复档、清理前清单、资格清单、review及后继读回均归本轮项目证据，不能自动当缓存删除。未执行git gc、历史改写、未知文件/失败证据/云端artifact清除；本轮仅清引用，不宣称Git历史体积缩小。RC-P05—08的剩余空间治理仍单独分批处理。

**验证和边界**：接手新增206d56da..2574b40d的diff检查通过；整个继承main差异有保全历史/不可变源文件的空白及EOF诊断，按cr-at-eol解读仍263条，明确保留PARTIAL而未为求绿规范化原件。CI正式lint/目录/架构/安全门禁通过，没有修改断言或豁免。自动审查曾拒绝强制移动本地main的命令；该命令未执行，随后核实main无独有提交，改用git switch及merge --ff-only安全快进成功，无权限阻断遗留。源码交付**MERGED_MAIN**；本轮CI Windows安装旅程为真实宿主/合成材料，不是日常Green、真实模型完整业务链或Owner验收。前端全阶段与UI-P14/21/22/23/24等原欠账继续PARTIAL；不据本次合并启动后端或激活冻结能力。

记录及历史回执更新后的定向验证：`rc-merge-conventions2-20261020`工作树目录规范PASS、`rc-merge-authority-20261020`单一记录/链接/仓内hash PASS（外部私人4项仍UNVERIFIED）、`rc-merge-object-guards-20261020`原对象门禁15项PASS，dirty diff检查PASS。首个目录命令误用`--scope`而非现有`--source`导致usage/exit2，原运行保留；修正调用后通过，未改产品或规范。新文档提交及后继CI/PR以现场实际SHA读回，不重复产品全量本地测试。

**清理后的fresh clone补查与修复**：按实际剩余3个远端heads计算可达对象，`rc-source-reachability-red-20261020`发现现行覆盖说明仍写退役4fc9006a的完整SHA，资源overlay仍绑定退役7897bbd3；本机对象门禁因对象尚未gc而通过，不能替代fresh clone可达性。完整历史身份已在原并行整合回执和上述分支收敛回执中保留。覆盖说明改用短名及原回执；资源绑定改为main已有的980f9796，两个布局提交的git patch-id --stable完全相同，并新增原身份JSON pointer及修复日期/限定说明。68项资源、115条原冲突、全部entries/selected_scope/资格/激活声明逐值不变；现有生成器同步只读resource-catalog的来源hash及metadata，没有改门禁或生成器。

`rc-source-reachability-green-20261020`的当前声明缺失对象为0；`rc-resource-projection-green-20261020`16项原投影合同PASS，`rc-resource-ui-green-20261020`资源页/供体2文件20项PASS。生成步骤`rc-resource-regenerate-20261020`的child exit0，但因预期改写生成文件，被dev.py正确记SOURCE_INVALIDATED/exit3，**不称验证PASS**；后继只读投影/消费者门禁才是通过证据。Python退出时已有pyreadline3句柄析构警告仍保留，进程exit0。此补查修复纳入后继PR195重新资格，不凭82f420f3那次仅文档CI通过直接合入新源码。

后继文档Authority与生成投影`--check`通过。`rc-source-conventions-final-20261020`另发现本轮Python生成的分支回执工作副本为CRLF；Git已提交blob为LF，数据没有差异。已逐字节核对后将本轮工作副本对齐原已提交LF blob，未修改历史记录数据、生成规则或云端blob；该FAIL保留，后继规范复验另记。

## 2026-10-20 UI-P02：模板需求与诊断分离

现场先核main仍为726842c8、无开放PR；PR195由5302e764合入726842c8，候选CI39429508062及main后继[CI39431380394](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39431380394)均SUCCESS。原main52147d6b的CI39427148307在后继推进后取消，不能记PASS。当前writer分支codex/sync-20261019由5302e764安全快进到main基线，无未知脏修改；未重合旧包、未清理保留分支。

本片映射UI-P02，并补UI-P10/18/20/21相关有限回归：模板需求表不再直接显示处理协议、内部能力编号、原始权限/健康字段；显示中文用途、已登记实现、连接允许、禁用、未就绪、权限未知、未接入、未读取和读取失败。模板声明由内置操作承担但尚未关联目录的情况单独说明；纯需求不冒充已实现，连接允许不冒充实际处理成功。完整模板声明、解析行、运行状态及能力反向对应记录由现有RawReceiptButton送入同一运行诊断。未改resolver、TEMPLATES、目录或保存准入，没有新注册器/诊断抽屉。能力跳转仍传原稳定身份；缺增强能力时创建、字段编辑和实际保存调用保持可用。

修改范围：`frontend/src/templates/TemplateWorkspace.tsx`、`frontend/src/presentation/templateCapabilities.ts`、既有`capabilityCenter.ts`显示名、`CanonicalCapabilitiesSpace.tsx`模板反向列表、原`TemplateCapabilityRequirements.test.tsx`消费者与回归，以及现有`aaos_ui_coverage.py`的可选模板路径。浏览器扫描发现原h4需求标题越级，改为h3并增加原问题断言；没有放宽axe规则。

| 验证 | 实际结果与边界 |
| --- | --- |
| 原问题RED | `ui-template-copy-red-20261020`1项FAIL：阅读区暴露Core/worker/CAP/协议名，保留日志。新增回归同时要求诊断JSON与原始模板、解析行和运行读取逐值一致。 |
| 最终定向 | `ui-template-heading-tests-20261020`4文件64项PASS，包括原resolver严格身份、不借相似名、模板创建/引用/保存、无新增播报区、资源页及App→能力路由；SIMULATED接口，不是实际安装或真实Core持久化验收。 |
| 类型/构建 | `ui-template-types-20261020`TypeScript PASS；`ui-template-build-20261020`正式frontend.mjs构建PASS（内层0f3bae57512c，含最终TypeScript），原大chunk警告保留，不据build宣称runtime。 |
| 最终浏览器 | `ui-template-browser-evidence-20261020`4项PASS_AUTOMATED_ONLY：正式资源页15→学科模板→需求详情/诊断→Escape焦点返回→能力详情→资料库→资源模板；cosmic/blueprint-light×1600×1000/640×480，实际点击，按钮完整高度/可达，页面无横向溢出。Chromium149.0.7827.55、DPR1、reduced-motion=reduce，SYNTHETIC host/Core。axe4.14.0无violation；每场color-contrast及label-content-name-mismatch的incomplete完整保留，不称全面合规。已实际查看heading运行的4张入口图及evidence运行的4张需求行图，窄窗通过滚动查看长中文，不缩小字号。 |
| 来源与关闭 | 浏览器base726842c8、dirty diff SHA256 `4a4e108c023c60ee5b1320a0e06216c69c4780e6633dd269aeeb962c89be4bc4`；当时新增显示模块尚未进入index，另核文件SHA256 `b2c69d38be8b20fd6379b5edc72d72f7856f0032669550a1de1c46ea8bf7c470`。自有PID40532、127.0.0.1:49294结束，port_closed=true；terminate退出1仅为服务回收，不称优雅退出。无pageerror/外网请求。 |
| 失败保留 | 首轮误将模板置于阅读页，第二轮精确label查询失配，第三轮返回资料库命中三个同名标题；修正为正式资源标签、combobox可访问名及业务面板限定，未改产品规避。随后四场操作PASS但axe标题越级FAIL，修复后再资格。原运行ui-template-browser、browser-route、browser-labels、browser-final均保留；browser-heading为修复后首次4场通过，browser-evidence补需求行截图与按钮完整可达断言。 |

所有run在本项目忽略目录`.project-local/runs/be268a2d33/<run-id>/`。前端代码本轮定向审阅确认仅显示投影/诊断入口改变，原能力判定、禁用/未知边界及真实保存调用未改。新提交/PR/required exact-SHA CI/main合并以本片交付后的远端读回为准；以上测量在交付前完成，不将本地通过当云端通过。

**未完成与下一步**：UI-P02其他业务面仍有工程术语，UI-P14三类免费检索真实接口缺口保留，继续独立前端，不造空检索成功；UI-P21人工辅助技术、UI-P22规模性能、UI-P23全域视觉基准、UI-P24同候选安装和Owner验收仍PARTIAL/UNVERIFIED。前端未阶段交付，不进入BE-P01—15；Green、真实数据、模型/provider/endpoint未变。RC-P05—08剩余对象/体积/目录治理另按精确清单分批推进，不能取代产品修复。回退为对本片显示模块、两页面、原测试/探针消费者作反向修订；不回退已合入TRAE及主线基线，不删除失败证据。

交付前附加门禁：`ui-template-conventions-20261020`工作树目录/编码规范PASS，`ui-template-authority-20261020`单一记录/引用/仓内7个hash PASS（外部私人4项仍UNVERIFIED），`ui-template-final-lint-20261020`CI同选项Ruff PASS，diff --check PASS。原始运行材料和截图保持本地，不提交。

## 2026-10-20 UI-P02：研究引用与排版

**上一片交付读回**：[PR196](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/196)的4cd755ae经[CI39437490872](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39437490872)SUCCESS，required a0-gates及browser-smoke/lint通过；按本轮路径分类未要求的安装等作业skipped，不称完整矩阵。源码审阅无阻断，PR无review/未解决inline意见，实时ruleset20849492只要求a0-gates。已正常merge为main的5f6a845e，tree14504d23与候选及CI合成合并树完全一致；[main CI39438919433](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39438919433)亦SUCCESS。本地main和当前writer经switch/--ff-only安全快进，writer远端同步5f6a845e；没有强制移动或清理占用分支，TRAE祖先保留。以下研究片基于该已合并基线，不借上一片资格称新改动CI通过。

研究阅读区改用对象名称与固定版本说明，完整引用身份、原件指纹、引文定位及CRLF原文快照由同一运行诊断查看。名称仅匹配相同文档和版本、相同原件及内容指纹；未读取名称就明确说明，不拿新版标题解释旧引用。引用跳转和保存仍使用原身份/版本/块/指纹。改写保存冲突、未知属性、原件核对失败等业务说明，实际保存请求/核验边界不变。另一视图持有写入租约时，在禁用表单外保留只读引用诊断入口，不夺写入租约或放开保存。

截图另发现引用说明与按钮0px相贴；新增局部`research.css`，复用现有间距/主题token，引用行和引文操作区flex换行、8px间距，区分正文和操作；不改壳、Dock、图谱渲染器或字号基线。修改为`CanonicalResearchSpace.tsx`、该局部CSS、原研究测试和既有覆盖探针；本片没有新增Core操作、后端接口或真实外部检索。

| 验证 | 实际结果与限制 |
| --- | --- |
| RED与原保护 | `ui-research-copy-red-20261020`2项FAIL复现原始身份外露及缺少旧版本名称说明；`ui-research-readonly-red-20261020`1项FAIL复现只读无可达诊断入口。`ui-research-copy-green-20261020`首次全片30/33通过，旧GraphRAG/metadata/定位编号显示消费者3项FAIL；同步消费者，历史定位改从诊断逐值核对，不删除原始身份断言。 |
| 最终定向 | `ui-research-spacing-tests-20261020`3文件39项PASS：研究34、真实租约消费者2、诊断3；含CRLF/表情原文不变、完整诊断逐值一致、旧引用不借新版名、只读保存禁用/租约不转移/零写入，以及既有幂等重试/冲突/迟到响应/历史只读。SIMULATED command，不是实际Core持久化或安装验证。 |
| 间距RED/GREEN | `ui-research-spacing-red-20261020`真实640×480取样gap=0 FAIL；局部样式后`ui-research-spacing-green-20261020`四场均gap=8 PASS。没有降低字号或完整按钮可达门槛。 |
| 最终浏览器 | `ui-research-five-themes-20261020`研究页05，cosmic/blueprint/blueprint-light/black/white×1600×1000/640×480共10场PASS_AUTOMATED_ONLY。实际点开合成研究对象、引文诊断、Escape焦点返回、读取实际合成原字节并核SHA、原件诊断、再次焦点返回；原引文textContent逐字含CRLF/表情一致，诊断完整身份一致，间距均8px、按钮完整可达。真实Chromium149.0.7827.55、DPR1/reduced-motion=reduce；SYNTHETIC host/Core，0 axe违规，20条incomplete原样保留，无pageerror/外网请求。实际查看五主题窄窗及cosmic/blueprint-light宽窗共7张引文截图，不称全页面五主题、原生DPI或完整无障碍通过。 |
| fixture与失败保留 | 初始`ui-research-browser-20261020`暴露探针单页05缺父导航、列表fixture错误返回完整文档；修正为真实知识组父入口及严格summary字段，不改产品校验。其后补齐具名合成来源的空任务列表，避免把fixture未登记当实际任务故障。`ui-research-qualified-browser-20261020`窄窗一次诊断关闭后即时焦点断言失败；保留原FAIL，改用8秒内同一精确按钮最终焦点断言，不改产品、不跳过检查；单场readback及上述最终10场全部通过。不从先前部分PASS拼成一次全绿。 |
| 构建 | `ui-research-qualified-build-20261020`正式frontend.mjs build PASS，内层fcbb4fc6aba9，含TypeScript；既有大chunk警告保留。后续仅探针焦点取样/本记录改变，前端源码和CSS未再修改。 |

最终浏览器base5f6a845e、dirty diff SHA256 `e9d024322217bca8d45a117f4c4955ccc860ed2def883f506bbe3360f22dff1c`；当时新增CSS尚未入index，单独SHA256 `a0fc6ec47681335622b956bd8d803669553b8ede32aa548ef17549397298a310`。dev.py source_consistent=true、child/exit0；自有PID32580、127.0.0.1:50119已关闭，port_closed=true，terminate退出1不当优雅退出。原始运行和所有旧FAIL/截图留在`.project-local/runs/be268a2d33/<run-id>/`，不提交原始数据、浏览器profile或构建缓存。

**仍未完成**：UI-P02其余页面和本地知识结果编号/引文定位枚举等尚需收敛；UI-P14三类免费外部检索与比较没有真实接线，不能把本地search或合成引文当检索成功。UI-P21人工辅助技术、UI-P22规模性能、UI-P23全域视觉基准和UI-P24同候选安装/Owner验收继续PARTIAL/UNVERIFIED；前端未阶段交付，后端队列不启动。原六项冻结、V01/FT状态、Green、真实数据及模型配置不变。回退仅反向修订本片研究显示、局部CSS及消费者/探针，保留已合入模板片、TRAE和失败证据。本片新提交的exact-SHA CI及合并待独立现场读回。

交付前`ui-research-conventions-20261020`工作树规范、`ui-research-authority-20261020`单一记录/引用/仓内7个hash、`ui-research-delivery-lint-20261020`CI同选项Ruff及diff --check均PASS；外部私人4项仍UNVERIFIED。定向审阅确认只读诊断仅展示已读取对象，不新增读取权限或改变写入租约/保存保护。

## 2026-10-20 UI-P02/10/11/14：研究核验状态与引用选择

**上一片现场交付**：[PR197](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/197)候选841f595c经[CI39443271934](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39443271934)SUCCESS，required a0-gates及lint/browser-smoke通过；未选中的作业不算已验。源码审阅无阻断，live规则要求a0-gates，未发现review/inline阻断。普通merge成为main的69f7cae6，tree14113ac4与候选及CI合成合并树一致；[main CI39449002023](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39449002023)SUCCESS。当前writer在保留本片dirty修改时--ff-only快进69f7cae6，前后已提交tree相同，工作树binary diff逐字相同；本地main暂仍5f6a845e，待干净后安全快进。TRAE的206d56da仍为HEAD祖先，不覆盖其修改。

本片把引文定位枚举转为中文，并保留“仅核对定位、不表示内容证实”的边界。核验结果、时间、原引用及完整返回对象进入既有运行诊断；缺少定位/版本或身份不匹配保留失败返回，不显示定位有效。核验期间编辑、保存、切换或后继消息发生后，迟到结果不能覆盖新保存反馈。历史引文、CRLF/表情、原定位指纹和严格保存保护均保留。

本地知识选择区明确区分未检索、正在检索、实际空结果、读取失败及关键词已变化。查询冻结在原请求，输入变化后旧结果不可选择或添加；同名结果按序号区分，原knowledge_id仅在诊断中，保存仍绑定所选确切身份。原文档/原件选择和并发保护沿用，不把本地search解释为免费外部检索。

五主题扩展检查发现嵌套弹层真实键盘缺陷：诊断已聚焦，Radix下层document Escape监听仍可能先关闭引用选择器，诊断未关闭。只等待焦点不能消除问题，未以sleep/重复按键/点击关闭替代断言。DiagnosticCenter在打开时用layout effect登记有范围的window capture监听，仅处理实际位于诊断内容内的Escape，先隔离下层；普通Escape只关闭诊断，组合输入Escape不关闭。监听随关闭/卸载移除，不接管其他页面或其他弹层快捷键。

| 验证 | 实际结果与限制 |
| --- | --- |
| RED | `ui-research-state-red-20261020`4项FAIL；`ui-research-query-red-20261020`3项FAIL，定位缺失负例原已通过。`ui-diagnostic-ime-red-20261020`组合输入Escape误关FAIL。各原日志保留。 |
| 最终定向 | `ui-research-state-tests-qualified-20261020`3文件49项PASS（研究42、诊断5、真实租约消费者2）；含固定身份、原文逐值、迟到响应/保存、失败不冒充空、同名第二项实际保存，以及可关闭的父picker在第一次Escape保留输入/焦点、第二次才关闭。SIMULATED command，不是Core耐久持久化验收。 |
| 真实浏览器 | `ui-research-keyboard-browser-20261020`正式研究页05，五主题×640×480/1440×900共10场PASS_AUTOMATED_ONLY。引文原文及核验/原件诊断逐值、四次Escape焦点返回、同名选择、空/失败/旧查询、按钮完整可达/8px间距均通过。实际Chromium149.0.7827.55，DPR1、reduced-motion=reduce；SYNTHETIC host/Core，无pageerror或外网请求。页面及两个picker状态各扫axe4.14.0，0违规，60条incomplete原样保留（渐变/伪元素对比等需人工核验），不称全面合规。实际查看最终blueprint/blueprint-light/white窄窗选择图、cosmic窄窗失败图及black宽窗引文图。 |
| 失败矩阵 | `ui-research-state-matrix-20261020`命令参数误用逗号，argparse退出2，未运行场景；改为独立参数。`ui-research-state-matrix-final-20261020`6/10场PASS、4场Escape FAIL；`ui-research-dialog-ready-20261020`显式要求诊断关闭按钮自然获得焦点后仍7/8场PASS、1场嵌套Escape FAIL。两批均整体FAIL保留，不拼成全绿；产品修复后的最终10场独立通过。 |
| 构建 | `ui-research-keyboard-build-20261020`因新增测试用了Testing Library不支持的exact参数，TypeScript四处FAIL；移除无效参数（字符串name仍严格匹配），最终`ui-research-state-build-final-20261020`正式frontend.mjs build PASS，内层5ae157f2c28e，含TypeScript，既有大chunk警告保留。最终49项测试在修正后重跑通过；产品源码/CSS与上述10场浏览器一致。 |

最终浏览器base69f7cae6、dirty diff SHA256 `129a78e34040a00c6869fe22a7d72fc3e9c6e1d11ca2adcdfa63ea4de8bfbf12`，dev.py source_consistent=true、exit0。自有PID6584/127.0.0.1:59685已回收，port_closed=true；服务terminate退出1不当优雅退出。原始证据仍在`.project-local/runs/be268a2d33/<run-id>/`，不提交profile、运行日志或缓存。

**RC-P05只读分批清点**：`rc-footprint-readonly-20261020/artifacts/footprint.json` SHA256 `79d2c71b5b3056b251b40cad01b1239f48c8d422ad8d0773c0fa45c09395efbc`，精确登记此前3份可重建前端dist及26份运行日志/证据根，共135422112字节，逐文件hash、归属、保留理由及重建/回退保留。仅此范围，非全工作区体积；tracked普通文件lstat合计1228579841字节，Git loose+pack分配462879744字节，分别记录，不相加冒充整体。`cloud-artifacts.json` SHA256 `ce7e0748421bf291eb2b8a8ac73c23ea98fdb7c170dca866698de144ce5afc93`，只读3个指定CI run的首分页18份artifact元数据/服务端digest，共756636037字节，非整个云端、未下载验证归档字节。全部RETAIN，无删除/GC/历史改写、共享模型工具或未知资料操作；后继新增运行不在这批快照，不能借此清理。

**继续执行/阻断**：UI-P14百科/社区/科研检索独立界面仍缺，当前正式CoreOperation无三类检索操作；既有document_check的DuckDuckGo文章获取和模型核验不能替代免费三类通道。后继前端需公开关键词/范围、来源/限流/未知、结果详情和去重/支持反对冲突比较；后端阶段补具名检索响应、出处/取得内容/许可/失败、取消迟到隔离和Rust单写者落库/固定引用合同，未接线期间不得生成结果或把0当失败。UI-P21人工辅助技术、UI-P22性能规模、UI-P23全域视觉基准、UI-P24同候选原生安装/Owner验收仍PARTIAL/UNVERIFIED；尚未前端阶段交付，不启动BE-P01—15。Green/真实数据/模型配置和冻结项未变，CL-01—07/J1—J6不缩减。新候选exact-SHA CI/合并待单独读回；回退本片研究状态/局部CSS、诊断键盘及消费者，不退TRAE/已合入基线，不删失败证据。

## 2026-10-20/21 UI-P14：三类公开检索前端与作者对照

**前片交付**：[PR198](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/198)候选c5f4d35a的[CI39452223018](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39452223018)SUCCESS，required a0-gates及lint/browser-smoke均完成通过；未选中的安装/后端作业为skipped，不计资格。实时ruleset20849492只要求a0-gates，无审阅数量规则，PR无review/inline阻断；已审源码，候选与合成合并树均c75a0be6，按expected head正常merge为main的7ca69cc8。writer随后--ff-only快进同一tree，binary dirty diff及两个新文件hash前后相同；TRAE仍保留。main的后继CI待单独读回，本片不继承c5f4d35a资格。

在既有研究页05加入`PublicResearchPanel`，不增主壳、产品路由、来源/能力注册表或后端操作。生产态明确百科/社区/科研接口尚未接线，检索按钮禁用，结果未知且没有示例结果。关键词初始为空，不自动取研究问题、正文、附件或模型链接。可手动选择三类范围，把检索计划显式放入现有未决草稿；此操作不调用任何外部检索，仍需现有“保存研究草稿”才写入Rust合同，references为空，不冒充固定来源或已采用知识。

独立呈现层支持逐来源完成/限流/失败/离线/未知、仅元数据/摘录/全文筛选、取得时间/许可未知/免费条件未知、原文定位缺失说明和完整诊断。相同地址只作显示分组，所有返回记录/时间/内容差异仍保留，不按同名猜测同一来源或宣称来源独立。最多6个地址并列作者对照，可标支持/反对/冲突/不确定；文字只显式加入未核验、未绑定固定原件的未决草稿。旧关键词/范围、后继返回和只读状态隔离选择及添加，拒绝添加时原选择保留。上述结果状态使用纯UI输入/回调测试，**没有对应生产transport，更不是已执行外部检索**。请求取消回调只显示停止等待/远端停止未知，不伪造取消成功。

| 验证 | 实际结果与限制 |
| --- | --- |
| RED与修复 | `ui-public-research-entry-red-20261020`缺公开检索入口1项FAIL；首次green48/50通过，两个失败为新增测试的toHaveValue不支持不对称匹配器、原保存测试假设全页只有一个status。修正为逐字值包含及具名“研究操作状态”，保留原保存反馈内容/角色断言；首次类型检查因vi.fn空参数推断FAIL，精确声明text参数后修复。`ui-public-research-channel-red-20261020`复现一个来源重复完成/失败被误当完整空检索，改为每来源唯一complete才认定完成，保留该负例。 |
| 最终定向 | `ui-public-research-final-tests-20261020`4文件60项PASS（研究43、公开呈现10、诊断5、租约2）；包含真实保存调用的公开计划读回结构、零外部操作、三个范围只传明确关键词、完整同地址记录保全、作者冲突/反对记述、部分空/歧义状态不冒充完成、旧查询不可选、拒绝/只读/六项上限/后继返回隔离。SIMULATED Core/呈现输入，非真实免费检索与Core耐久重开。 |
| 浏览器 | `ui-public-research-browser-20261020`4场生产页面准备/加入未决通过；查看截图后修复范围checkbox与中文标签纵向分离，改为同排40px标签目标，复用现有token。最终`ui-public-research-final-browser-20261020`cosmic/blueprint-light×640×480/1440×900共4场PASS_AUTOMATED_ONLY：关键词初始空、检索禁用、明确未接线、选择百科/科研范围、计划逐字加入未决草稿/无重复添加。axe4.14.0无违规，8条incomplete保留，无pageerror/外网请求。实际查看最终两主题窄窗图；结果/对照视图仅有组件测试，未以准备界面截图称完整结果视觉验收。Chromium149.0.7827.55、DPR1/reduced-motion=reduce，SYNTHETIC host/Core，非原生DPI/安装。 |
| 构建 | `ui-public-research-final-build-20261020`正式frontend.mjs build PASS（内层0388df96cd06，含TypeScript）；既有大chunk警告保留。最终测试、浏览器和构建均source_consistent=true，不改断言求绿，不重跑全仓测试。 |

最终浏览器基于c5f4d35a（与当前7ca69cc8的committed tree相同），dirty diff SHA256 `ca5671dc5ec6a5c3d72f9e4a0c35847d830e924cfad80a9fe5def81576e0cbbe`；当时两个新文件未入index，另核PublicResearchPanel.tsx SHA256 `c39e89a8be48f373c69eebe5450f8a0ee88388820ee4a969bc5c4dcaff4301f5`、其测试 `4e9f3b52cc80a0a8c02dd0a83df93420f42ad140a1f97e073571555c6908865a`。自有PID24100/127.0.0.1:61158回收，port_closed=true；服务terminate退出1，不称优雅退出。所有原始运行/失败/截图在同一`.project-local/runs/be268a2d33/<run-id>/`保留，不提交。

交付前`ui-public-research-conventions-20261021`工作树及随后index规范PASS，`ui-public-research-authority-20261021`单一记录/引用/仓内7个hash PASS，外部私人4项仍UNVERIFIED；changed probe的CI同选项Ruff及diff --check PASS。前片main7ca69cc8的[CI39453613855](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39453613855)已启动，写此条时仍in_progress，不写作PASS。

**UI-P14仍PARTIAL**：准备入口及结果/对照独立呈现已实现本地；真实三类检索、来源/限流/许可/可得内容合同、请求取消/迟到响应控制、原文打开、落库固定引用、去重身份及重启导出仍BLOCKED于BE-P04/05所需正式接线，不能以纯UI回调冒充集成。后端阶段前需完成结果/对照真实浏览器视觉与键盘检查；不能只以禁用入口结束该项。前端全阶段未交付，继续其他UI分片及原生/DPI/人工无障碍/性能欠账；BE-P01—15暂不启动。六项冻结、Green、真实数据及模型/provider保持原状，完整CL-01—07/J1—J6目标不变。回退仅本片独立呈现组件、研究页嵌入/局部CSS、测试和探针消费者，不回退TRAE/前片已合并修复，不删除证据。

## 2026-10-21 Owner改序：后端全链路及完整闭环优先

Owner最新明确：“加快速度，实时并行智能体，按照任务难度理解和模型等级推理强度进行适配”；随后“前端界面可以缓缓，优先确保后端全链路的打通跑通，优先闭环”。后者覆盖2026-10-19前端先行的执行顺序，不删原UI/BE/RC任务、不缩CL-01—07/J1—J6。活动指针与根AGENTS/完整交接/分片顶部同步当前选择，唯一进度仍本文件。已完成前端保留，PR199/b4a4b9b9已上传、CI39454302421写此条时尚运行，不把push当merge；main7ca69cc8的CI39453613855也待终结读回。

并行按实际难度分配：高难核心链路/耐久批次使用gpt-6-astra high；三类检索worker/官方接口使用gpt-6.1-sol high；有界CI与本地模型现场探针使用gpt-6-luna medium。只对本次子任务选择模型/推理，不修改Agent provider、认证、endpoint或全局配置。源码writer隔离在项目忽略目录`.project-local/wt/be-batch`和`be-research`；root负责正式检索Core/合同和最终整合，每checkout一个writer。原有共享模型/工具只引用，不复制/升级。

**已定位并修复本地的BE-P03来源丢失**：source_origins主键不含原名，FolderIngest原来同批所有成员共用origin_ref，CAS相同字节只留一个来源；原fixture按文件名造source_id掩盖此问题。隔离片改为batch+编码完整relative_path成员身份、origin_name保留完整relative，保留CAS去重；fixture改按真实内容身份去重及真实来源主键折叠。`.project-local/runs/99371d31e4/be-origin-red-20261021`3 FAIL/28 PASS，green31/31、adjacent4文件36/36、typecheck PASS，均source_consistent=true、patch SHA256 `164068ff0e9092b2235cdf2bf5825f3d520c9f092aa71aa301876e4f41f43f54`。worktree Git index写入因沙箱文件权限拒绝，未提权/改ACL/强制绕过；root核对应两文件无dirty后按精确路径接收相同字节。此小修不等于耐久批次：正式batch/member表、有限API、重启恢复和原文件需重选的合同正在独立实现，job终态复用现有真值，不复制第二作业系统。

**BE-P04真实免费来源预检**：仅用无凭据公开关键词的小请求，Wikipedia搜索及固定revid、StackExchange Academia withbody、OpenAlex works均HTTP200；原始API/版权/限流已查官方资料，未发私有正文，未用付费全文接口。此为REAL匿名接口可达/返回内容，不是产品集成完成。正式worker正在隔离实现，固定host安全HTTP、有界输入/响应/超时、逐来源失败/限流状态与原响应bytes；Core将把原API响应与明确标注的派生文本分别保全，不能把重建摘要/去HTML后偏移伪称原始JSON字节锚点。

**BE-P08本机真实合成推理**：LM Studio声明端点/v1/models现场HTTP200，但不据库存称已加载。`inspect`回执`.project-local/runs/lm-studio-profile/1792512710668-inspect.json` SHA256 `036e5135744459fe4e21aee3516a8c6f4ee8212d0cdc506049df5241cc78398a`，目标和其他实例loaded=0。随后按本次授权沿既有deep-mtp profile加载qwen3.8-27b/aaos-deep-27b-mtp，仅运行脚本固定合成输入，profile SHA256前后均`7aa8d2f6e30099461f274369fb096f2cd165e4bff95d2956f9dfaaada3713394`；未修改profile/provider/端点/凭据或调用云端。dev run ab29512f536f，source b4a4b9b9、当时4项authority dirty、source_consistent=true、exit0。smoke回执`.project-local/runs/lm-studio-profile/1792512866521-smoke.json` SHA256 `f3eeaa994200cbd5ffc029bf0b4a607fa7df3a9efd55fa1bf8d807a4b2353f82`，PASS_SYNTHETIC_SDK_SMOKE / REAL_LOCAL_SDK_NOT_APPLICATION_QUALIFICATION：固定literal匹配，effective GPU0.4/strict VRAM、KV CPU、context2048、parallel1、FlashAttention/MTP生效，12.564秒、TTFT3.403秒、4.594 tok/s、MTP drafts32/accepted26/rejected6。仅单次观测不称加速收益、准确性或稳定性能。实例按原TTL1800驻留，未停止/卸载共享服务。正式Core/同候选业务推理仍NOT_EXECUTED，后续以聚合候选重验；云端真实provider及逐材料/目的地授权与预算仍需具体接线/资格，未读取秘密或产生付费调用。


### 2026-10-21 BE-P03/04/05：耐久批次、正式免费检索与研究来源导出

**主线读回**：PR199 head `b4a4b9b9c39c836ed0225be360c66c784c928235` 的 CI39454302421、required a0-gates、lint/browser-smoke均SUCCESS；独立审阅未发现阻断，reviews/inline threads为空，ruleset20849492当前仅要求a0-gates。自动审批首次以旧CI状态及后端未完成为由拒绝；补充exact-SHA运行元数据及当前授权证据后，正常expected-head合并为main `32291ad4285bef12a58f8bec56824a835a68ce29`，未绕过审批。main后继CI39459828056亦SUCCESS。root保护全部dirty、核提交树无差异后仅--ff-only到此基线；TRAE继承仍在，不把本轮未提交后端算进已合并UI资格。

**实现**：BE-P03追加schema13的batch/member表、5项有限操作及原FolderIngest消费者。成员路径/字节长度/排除原因分块登记，最多10000成员、每次200；未完整登记不能上传/入队。原件、成员绑定和job绑定由单Rust事务完成，CAS及jobs复用原真值；重复确认幂等、异内容冲突。重开可显式读取历史及逐页成员，文件句柄不承诺跨重启恢复，未传内容需重选并核原路径/数量/大小。登记ACK等待中停止仍会自动上传的问题保留RED后修复，不在只读恢复中自动执行。

BE-P04/05新增 `research.public` 固定worker路由，联入原CAP-0030和原能力中心生成目录；Core公开search/read/list/cancel/materialize及canonical schema/生成DTO/有限host bridge。请求只接受显式公开query/families/limit及workspace/restore/request身份，不收文档正文、附件、任意地址、密钥或模型fallback。首请求冻结后不静默重执行；pending中断为UNKNOWN，终态精确回读。取消/总90秒（含两类排队）/1MiB输出/能力撤回/restore迟到隔离，owned process及精确临时文件清理有界；cleanup_failed/task_failed保留UNKNOWN，不假称远端已停止。

三类provider固定为Wikipedia、StackExchange Academia、OpenAlex，分别保留固定修订导言wikitext、问题正文、科研摘要/元数据，绝不冒充百科全文/论坛所有讨论/论文付费全文。Core验证实际query/limit/固定参数、ID/URL/revision、UTC时间/类型/nullable必填、枚举及字节上限。原HTTP实体bytes独立CAS（可能gzip），派生UTF8另存并明示未核验，只有用户显式选择才物化；不把派生偏移伪称原JSON位置，不自动采用知识。

**真实网络路由差异**：先前safe_http直连Wiki失败；仅查询.NET公共目标代理元数据，确认已有数值loopback路径127.0.0.1:7890，未读取认证/系统设置正文、未改VPN/系统代理/TLS。新增仅检索worker可显式接收的launch变量ARCHEAXIS_PUBLIC_RESEARCH_PROXY，默认direct；只允许无认证http数值loopback CONNECT及三个固定官方HTTPS目标，默认CA/hostname/SNI、无redirect，无非法后fallback。独立源码审阅后只对公开query做受控probe，原失败证据保留。安装态并未据此自动配置代理。

**实际集成发现并修复**：真实Core初次检索返回worker_exit_failed；定向-I入口回归确认Python隔离模式不包含脚本目录，原普通sibling import失败。改用固定Path sibling的importlib加载，未放宽-I或恢复PYTHONPATH；RED与修复后66项PASS保留。首次source-process探针误用未登记的text子目录导致启动拒绝，随后按源码实际document/worker_text.py纠正，原启动失败保留，不算产品修复或成功。

**研究封包缺口修复**：原portable_document只包顶层source/expression media，研究材料虽保存引用却丢原件。`be-research-package-red-20261021`实际导出0对象、期望2失败；现沿既有package收集research明示source refs（材料/各段/结论），校验对象完整与bytes，导入重映射。派生与原API分别作为材料随包；原quote/anchor身份在historical_anchors及原封包保留，新库不伪注册有效锚点或知识采用。独立文档/知识依赖不因此获跨库重建资格。

| 验证 | 当前实际结果与证据级别 |
| --- | --- |
| root批次消费者 | be-batch-aggregate-ui-corrected-20261021：FolderIngest34+JobJournalRecovery6=40 PASS，SIMULATED桥接；此前误在repo根启动Vitest扫描.hermes被拒，未提权/改权限，改用原frontend/vite.config.ts正确根。 |
| root domain | be-domain-aggregate-20261021：batch2+public10=12 PASS，含schema12→13、重开、原始/派生CAS、真实响应离线回放和协议负例；离线回放不是本轮联网证据。 |
| root研究包 | be-research-package-green-20261021：portable3+research metadata4=7 PASS，丢成员拒绝且无部分注册、重开幂等、历史引文与原库不变。 |
| root正式API | be-public-api-green-20261021：4 PASS，实际Store/API及合成worker；公开query闭包、原件选择、重开精确回读、取消、drop请求UNKNOWN不重跑、restore后不发布旧结果。 |
| root Python worker | be-public-isolated-entry-green-20261021：66 PASS；pyreadline3析构WinError警告保留，进程exit0，不把该警告消去。 |
| 隔离executor | .project-local/runs/57489feb27/research-executor-final5-20261021：16 PASS，source_consistent=true；Windows redirector终止传播及精确file/emptydir readback<=500ms，持stdin后代返回cleanup_failed，未杀共享进程。 |
| 受控三源worker | .project-local/runs/8dcecc427b/public-research-proxy-real-1：三路complete且非空，REAL公网worker，无产品写；原响应SHA256 8620d38f642d47482a7aab9b2e4a80d9816d912c5a03c44e030e5693ef9b369b。 |
| 当前Core真实链 | be-public-core-live-entry-fixed-20261021：REAL三源→Core单写者原始/派生6来源→研究Document→封包6原件SHA/bytes→正常关闭重开→receipt/document/package/6原件逐值相等，22次HTTP操作均符合期望；仅debug源码Core集成，不是安装候选/Owner验收。source_commit32291ad4+dirty patch 5c7b123a2eca4652e8d05cb43012ccf76fec8993897c356d39ddf06cee3c557b，source_consistent=true；Core EXE SHA256 b8f29099a4e74839a8a0b7a79d1b372a6505986459330dc499232eef16898a8f。完整回执artifacts/public-core-live.json SHA256 2fe681c1b15bbfa61fe2cdfd2b76403f043c022b443bc866bdc7510e81f5fd07，自有Core已停止。 |
| 候选J2探针 | scripts/probes/aaos_public_research_runtime_loop.py已实现；隔离离线10例通过，尚未对正式同候选执行。不把探针文本或直接Core PASS替代J1—J6。 |

以上root run均在忽略目录`.project-local/runs/be268a2d33/<run-id>`，原失败和raw返回不提交。各run自身source_consistent均读回true；后继代码改变后只作为对应切片证据，最终frozen tree仍需独立资格。Git worktree索引权限拒绝的子agent未提权/改ACL/提交；root按精确SHA接收并增量合并共享schema/bridge，未整包覆盖其它writer。base64使用锁内既有0.22.1，无依赖升级。

**仍BLOCKED/PARTIAL**：聚合 `be-api-aggregate-first-20261021`中batch API3 PASS、完整backup/restore1 FAIL（code5 PermissionDenied），Cargo先停该target，其后的public API另独立执行4 PASS。独立`.project-local/runs/99371d31e4/be-batch-hardlink-diagnostic-20261021`确认同D卷owned临时目录os.link被拒；原backup汇总错误未标具体IO语句，该具体位置仍UNKNOWN，不将推断写实测，不改实现/断言/ACL求绿。隔离native route编译分别缺有效frontend overlay、随后缺真实rt/workers，未跑到route测试，不造假资源。正式同候选/原生安装、实际窗口、备份恢复、J2人工比较/知识/学习、J3全部特色矩阵与J5轻量扩展消费者仍待验；云端真实provider/材料目的地授权/预算仍缺，不调用付费服务、不扫描凭据。当前本地LM Studio SDK PASS不等于J4完成。前端只补业务接线，不恢复视觉优先；CL-01—07/J1—J6整体仍PARTIAL。


**后继聚合验证（2026-10-21）**：`be-public-executor-aggregate-20261021`在root正式源码16项PASS，source_consistent=true。正式研究页只补后端消费者：固定五项Core操作、显式空查询、历史记录读取、新旧workspace/restore隔离、物化后再次校验当前scope，原始与派生来源分别加入现有研究草稿；不做视觉换壳。`be-public-consumer-first-20261021`真实Vitest发现18 FAIL/58 PASS，主要为新增fixture使用非法workspace/restore身份及不支持的断言匹配器；未放宽生产validator。修正合法fixture并补六项非法scope负例后，`be-public-consumer-corrected-20261021`四文件82项PASS，SIMULATED Core，source_consistent=true。`be-functional-consumer-build-20261021`正式frontend.mjs构建（内层bc202b4c7310）含TypeScript PASS，既有大chunk警告保留；不能替代原生业务验收。

**同一公开研究工作区的真实本地模型**：按既有deep-mtp声明重载实例，回执`.project-local/runs/lm-studio-profile/1792516213130-load.json`为PASS_LOAD_READBACK，未卸载其它实例或修改profile。`be-public-material-local-model-20261021`沿前述真实三源工作区，通过Core创建绑定OpenAlex派生来源的Document、预览并确认冻结材料计划、真实调用LM Studio aaos-deep-27b-mtp、再从正式status读取同一耐久回答，四次HTTP符合期望。回答返回实际材料前三词，工程绑定检查通过；这是REAL_LOCAL_MODEL_THROUGH_CORE_ON_SAME_PUBLIC_RESEARCH_WORKSPACE，不代表独立质量、云端或安装候选资格。source32291ad4、patch ca67c002571ea6fb48d98f904ee182efde006883465c9e8026bcc2f6b30045b0，source_consistent=true，Core仍为b8f29099a4e74839a8a0b7a79d1b372a6505986459330dc499232eef16898a8f，自有进程已停止。材料180字节，usage由provider报告187输入/73输出，费用UNKNOWN；无知识接纳和云端发送。原始回执为该run的artifacts/public-material-model-live.json，SHA256 60d36285b450078f678b3f5cfe696d81d613d8cd28996e60344638e300bf7cf0，不提交原返回正文。

**候选准备现场差距**：RC-P06已删除旧rt/candidates，当前无可复用完整runtime；不得套用历史PASS。现有Python基底3.13.14可解析，116项现有依赖闭包不缺包，但soupsieve2.8.4/urllib3 2.7.0偏离uv.lock的2.10/2.8.0，不能直接复制称锁一致。正式prepare_bundle使用既有stage路径与frozen/hash校验，尚未执行新候选。另已定位portable assembler误读cargo_build而canonical host实际使用tauri_build，以及构建收据缺当场Core哈希的资格缺口；正按原入口修复，未手写PASS。能力中心research.public健康探针亦需实际输入无关hello，不能把普通NDJSON握手失败当provider故障。以上仍为本地未提交后端改动，未冒充已合并/已安装。


**独立审阅后的产品修复**：研究包A→B→C二次导出原来漏掉B的revision_basis.portable_import.historical_anchors，`be-research-reexport-red-20261021`真实失败。现export合并继承历史位置并去重，沿原5000条/16MiB边界，不注册有效anchor或知识。同时`be-research-alias-red-20261021`证明相同create_request_id可在不同库形成同Document ID但不同内容，研究包原样导入会误绑目标已有对象；本slice不打包Document/Knowledge依赖，因此明确拒绝此类研究引用的便携导入，原包可留存，不冒充跨库引用支持。`be-research-roundtrip-green-20261021`portable4+research4=8 PASS，保留原件bytes、历史quote、无部分来源/文档注册、无anchor/知识采用及原库不变。此拒绝属于具名边界：损失为含此类依赖的研究包暂不能跨库导入；恢复条件为实现workspace来源与内容hash绑定、依赖对象闭包传输和引用重映射后再验往返；落点仍原研究/知识库兼容能力，不另建队列。

能力中心`research.public`原走generic NDJSON握手产生假故障；继承现有有界owned进程runner，增加实际导入检索/HTTP/代理模块后的input-free hello，2秒/4KiB、null stdin、固定协议身份及未执行标志、无网络/查询/模型。root首次命令误用了不存在的public_research_executor test target，编译器在运行测试前拒绝；按实际lib/target纠正后，`be-public-health-corrected-20261021`专用4+既有health6=10 PASS，`be-public-query-after-health-20261021`query16 PASS；`be-public-python-final-20261021`72 PASS。均source_consistent=true，协议就绪不等于provider可达。

**候选构建接线**：已修原dev.py/frontend.py/portable assembler，同一source/commit/tree/patch下，`--qualify-core-build`只接受固定release/locked/offline archeaxis-api命令，并在完成时记录实际Core path/bytes/hash；原旧回执无此字段不能追认。正式host通过`--core-build-receipt`核stage与Tauri实际复制字节，assembler消费真正tauri_build/release及完整阶段、hash绑定，不接受旧手写status=PASS。root `be-build-handoff-aggregate-20261021`新资格及相邻正常构建16 PASS/16未选中，SIMULATED工具进程，尚未当实际候选构建。donor完整既有相关回归71 PASS/5 FAIL/3 SKIP；5项分别为junction/hardlink/owned进程清理权限失败，不减断言、不算PASS。后者测试未记PID，后继CIM读取亦拒，最终退出状态UNKNOWN；不把120秒自然sleep期限当实测，不杀共享进程。

**锁定Python准备**：`be-locked-python-runtime-20261021`离线在aiohappyeyeballs==2.7.1缓存缺失处FAIL，未冒用旧venv。随后`be-locked-python-online-20261021`从官方PyPI、frozen导出和require-hashes安装至独立`.project-local/rt-python-locked-20261021`，116项依赖及本项目wheel安装/隔离import检查PASS，source_consistent=true；soupsieve2.10/urllib3 2.8.0已按锁安装，开发.venv/共享工具/Green未改。uv的hardlink降级copy警告保留；这与产品backup硬链接失败分开，不据运行时安装PASS取消backup阻断。旧失败rt-python-input仅是部分Python基底及requirements，不能当合格候选或删除未知资料。

**合同与预检**：归档合同受manifest固定hash保护，先前直接追加导致document-authority FAIL，已恢复原20261001文件SHA256 96a969cb8f9cde04cc4edc3ccf48c3b6b82ef22f9d02d57f1f51300f89f0acb6；现行130 pair维护派生合同在AAOS-PRODUCTION-HTTP-CONTRACT-20261021.md，三维护测试指向现行库存，并保留历史OBSERVED资格边界，不更新历史manifest冒充原件。donor CRLF曾使conventions FAIL，精确LF修正后root `be-backend-contract-final-lf-20261021`完整preflight PASS（含29逐接口/计数/核验映射），结构门禁不等于业务闭环。`be-backend-ci-ruff-20261021`与CI同select规则PASS；此前额外全规则lint15条告警保留，不称全规则通过。全部本轮变更已纳已有GatePlan分类，unknown_paths空；仍需提交后exact-SHA CI和同候选J1—J6，未公开发布/未更新Green。


**根目录排除修复**：独立审阅证实relativeOf剥掉选中根名，直接选择node_modules/.venv/.project-local/build/target会绕过既有排除。新选择及历史重选、Core register/executable_member现统一拒绝排除根及任意以点开头的根，历史read/list继续可用，拒绝时保留原批次，不标作已处理。普通“My node_modules notes”不误伤。两轮donor RED分别在node_modules及.hidden-folder真实断言失败；root首轮 `be-batch-excluded-root-ui-20261021`52 PASS（Folder46+Recovery6）、`be-batch-excluded-root-domain-20261021`4 PASS。后继generic hidden root增量的root终验待新run，不把donor静态检查称UI通过。

**许可范围标注修复**：OpenAlex数据集元数据CC0不外推为摘要原文字句许可；官方属性说明[abstract_inverted_index](https://help.openalex.org/data/works/attributes/)明确其摘要表达边界。worker重建摘要现在license=null（未知），无摘要metadata-only仍CC0，原始HTTP响应bytes不变。donor RED2 FAIL后，root `be-public-license-final-20261021`29 PASS，source_consistent=true；不修改历史捕获/旧收据，也不把该标注当法律核验或付费全文准入。


**提交前聚合终验**：`be-backend-consumers-final-20261021`六文件137 PASS（研究82+Folder49+Recovery6），含generic隐藏根/历史重选拒绝与普通相似名字通过；`be-backend-domain-final-20261021`batch4+portable4+public10+research4=22 PASS。均source_consistent=true，仍为对应本地测试级别。当前本轮提交目标是BE-P03/04/05与真实调用消费者/候选构建接线的可审阅检查点，backup权限失败、同候选安装与J1—J6、云端和独立质量验收继续保留，不标完整闭环。回退可按该检查点反向撤销代码；schema13为加表升级，不对真实数据自动降schema或覆盖旧库，现有Green未更换。

### 2026-10-21 后端优先续行：PR200、真实runtime与失败收敛（PARTIAL）

Owner明确前端可缓，先打通后端全部业务链；沿CL-01—07/J1—J6，保留既有UI实现及冻结边界。检查点`09dfc9966ac57861d1d0e1f65f0ff5ef20571000`已commit/push并附PR200，远端head核同；TRAE `206d56dafd00d0d3ccfd949ce6a4e424a324112a`为其祖先，未盲合历史整包。PR200仍Draft/未合并。exact-head CI run39468562331失败：contracts-vnext九项fixture source hash漂移；desktop-fast仅cargo fmt失败；rust-vnext两项真实解析器冷导入消耗合成transport夹具检索预算；primary11 FAIL/5648 PASS，其中同九fixture、probe schema12与当前13不一致、gitleaks测试依赖CI不具备的历史孤立commit。a0-gates为派生失败。其余已选成功不覆盖失败；installer-lifecycle等未选skips不算合格安装。未以push当merge。

fixture只刷新153处合法core schema source hash，57cases正负例不变，root `be-contract-fixtures-final-20261021`123 PASS。content-policy probe声明同步schema13；gitleaks保留冻结回执及原allowlist，映射两组旧finding到当前HEAD可达且tree/路径/内容摘要完全一致的commit，并验不可达及错tree/path/hash负例；root `be-os-probe-digest-root-final-20261021`12 PASS，source_consistent=true。pyreadline3退出析构警告保留，不把它当用例失败，也不宣称修过。bridge仅按Tauri edition2021 canonical Cargo fmt修空白，`be-native-bridge-fmt-final-20261021`PASS；不冒充native cargo tests。`be-cloud-contract-prepared-final-20261021`8 PASS只为合成transport/真实解析器协议测试，产品10秒budget与负例不改；独立审阅发现清理路径仍需有界处理，后续修复与再验未由本条追认。真实冷启动性能尚未验收。

普通保存B v2的revision_basis为空会再丢导入v1历史位置，已补从同Document不可变v1读取指定historical_anchors，未改变普通保存/审批；`be-research-save-history-final-20261021`portable4+public10+research4=18 PASS。但后继独立审阅发现删除/替换B全部当前refs时，保留的历史位置可能失去包内原件闭包，已列阻断修复；该18 PASS不能替代删除引用场景。

**真实候选后端子链**：clean09df的`be-core-qualified-canonical-20261021`在正式固定release/locked/offline入口PASS，Core17221120B，SHA256 ea3723e1c1c5e530ebb2e8a3af92349b14e8f05ff3e8153208fde08b89518b38；先前forward-slash绝对batch路径被literal资格检查拒绝，仅为命令不匹配，不是产品失败。`be-backend-runtime-stage-20261021`以锁定Python构成19477个manifest成员。`be-public-staged-runtime-real-20261021`同一clean09df后端runtime完成39项预期HTTP：三类真实公开检索→6原始/派生CAS→3定位anchor与resolve/原文回跳→6来源研究草稿→6对象精确bytes/hash包及Markdown→终止/重开后逐值核receipt/doc/package/export/anchors/sources。source_consistent/candidate_consistent=true，级别REAL_CORE_PUBLIC_NETWORK；支持/反对标签是待人工判断草稿，不是独立语义比较/知识接纳或完整J2。该run没有云端、恢复或安装宿主验收。

**退出证据纠正**：此前记录的“正常关闭”强于实测；backend_launcher.stop实际为terminate、必要时kill、wait，不证明产品正常宿主退出。新正式probe与ignored目录probe记录PID、实际actions、returncode及wait_reaped，graceful_exit_verified=false；离线helper验证不能冒充候选实跑。旧39HTTP收据保留自己的probe hash及未记录返回码边界，不回填新字段伪造旧实测。

**候选保全与重建**：09df runtime全部19478文件（含manifest）646334075B已先核精确成员/每项hash/无额外或链接、数据为空，再同卷Move-Item归档到`.project-local/candidates/backend-09dfc996-20261021`；manifest SHA256 ee7c156baeded7545a34940af234d8aed9cc96e1112b6922e59ce81b9009b6df，移动后复核相同。原`.project-local/rt`不存在，映射及完整清单在`.project-local/artifacts/runtime-rotation-20261021.json`（ARCHIVED_VERIFIED）；没有删除、没有重建旧alias。回退仅可在rt仍不存在且无占用时原路移动，不能覆盖新候选。当前portable修复改变来源，须新clean SHA重新取得Core/host/portable资格，旧收据不能借用。

**native准备边界**：`be-host-qualified-20261021`前端TypeScript/Vite成功后离线native构建因项目Cargo缓存缺getrandom失败，未生成合格host。直接网络locked fetch超时后仅中断自有会话，run无完成execution收据，不写PASS；后续`be-native-locked-cache-proxy-20261021`沿已登记127.0.0.1:7890、process-only CARGO_HTTP_PROXY取得锁定依赖PASS，source_consistent=true，未改全局proxy/TLS、依赖版本或共享工具。缓存已具备不等于build/runtime通过。backup/restore既有PermissionDenied仍BLOCKED，不改ACL/断言。云端服务/模型/费用授权问题仍待Owner答复；本地模型历史真实子链不能代表同候选或云端。Green和真实用户数据未更改，完整闭环继续PARTIAL。

**后继阻断修复与终验**：portable删除/替换全部当前refs的两个新回归先真实RED（0 PASS/2 FAIL），现仅识别明确schema/source_sha/read_snapshot绑定的research_citation历史引用，从同文档不可变导入v1的已生成source_mapping解析历史别名，并把原件并入既有128项/2MiB、16MiB序列化包预算。导入同样严格验证历史闭包，缺件/错hash/冲突在事务前拒绝；opaque字段不触发CAS访问，不注册当前anchor或知识。独立只读审查最终hash无阻断；root首次误用不存在的public_research/research_workspace target被Cargo在执行前拒绝，按真实target纠正后`be-portable-source-closure-corrected-20261021`portable6+public_research_runs10+research_metadata4=20 PASS，source_consistent=true。此证据取代只编辑question的狭窄回归，不把前次命令错误写作产品失败。

解析器夹具最终撤销外部OnceLock预热及其无界wait清理路径，改在同一实际worker进程、main原ready握手后、原execute前准备真实bs4/trafilatura，确保模块实际复用；第二例继续先完成原ready/release时序。root `be-cloud-sameprocess-root-final-20261021`原8例全部PASS、source_consistent=true。未修改5秒ready、10秒retrieval或Core30秒总期限；后者仍包含解析器准备，证据是SYNTHETIC transport协议/事务集成，不是冷启动性能或新SHA CI资格。`be-followup-contract-preflight-20261021`完整preflight（含29接口维护）LOCAL_PASS/source_consistent=true；后续新产品文件仍需最终diff/适用门禁。

**备份产品修复接续**：已核锁内tempfile3.26.0的Windows persist_noclobber使用同卷MoveFileExW且无REPLACE_EXISTING/COPY_ALLOWED，CAS既有写入已使用；正复用这一机制替换backup的三处hard_link发布，保留不覆盖、原件先/数据库后/manifest最后、失败清理及恢复验证，不走普通copy降级、不改ACL。原Win5日志未细分CAS/DB两语句，仍不声称原失败已精确到其中一行；新回归及真实backup/restore尚未由本条追认。原生测试工具现场存在，明确传入共享tauri-driver（SHA256 50f9774d5b8e4247426996970534a8140e70ddd1e2d08714a67e3fa6a5fbb0d3）及项目EdgeDriver155.0.4283.60（SOURCE/执行版本相符）；只是probe默认旧路径缺失，无需重装。tauri-driver不支持--version，未据文件存在编造版本。Stitch完整提示词在隔离只读设计lane整理，不阻塞后端写入。

**备份修复交付前结果**：上条tempfile版本观察纠正为当前Cargo.lock的3.27.0；3.26.0只是项目缓存旧源，未升级锁/依赖。独立核3.27源码仍为Windows原子no-replace/no-copy MoveFileExW，复用CAS既有库，不改系统权限。domain原件、DB及API manifest三处现用同一owned同步暂存文件发布helper；碰撞保留既存目标，失败按原Publication只清本次owned成员，Drop清理仍是best-effort，不许据此保证所有IO异常无残留。root `be-backup-domain-root-final-20261021`原14 PASS，`be-backup-api-root-final-20261021`原失败的ingest_batches_api4项+新增workspace_backup_publish1项=5 PASS，`be-backup-publication-unit-root-20261021`碰撞回滚单项PASS，均source_consistent=true。前者包含原件/DB恢复，API含manifest原件核对及重开；尚不等于正式安装候选跑过。

独立审阅实测新helper漏Windows大小写别名，donor `backup-case-alias-red`1 FAIL：应拒绝却case-only rename返回Ok；误删仅风险推断，并非该RED实测。最终在取得TempPath前canonicalize完整既存target，拒绝同文件，除NotFound外的规范化异常直接失败；root `be-backup-casealias-root-final-20261021`15 PASS（含原14及casealias），source_consistent=true，最终hash独立复审无阻断。Rust workspace与Tauri canonical fmt各PASS；changed Python CI-select lint PASS；`be-backup-followup-final-preflight-20261021`结构预检及29接口维护LOCAL_PASS/source_consistent=true。只针对有新变化/新失败的门禁再验，不重跑无关全量套件；exact-head CI仍待新提交，完整安装、业务质量及Owner验收仍未完成。

Stitch完整中文可复制提示词已交到ignored `.project-local/artifacts/stitch-design-prompt-20261021.md`，34455B，SHA256 7e723c43575f4e2e0ca00725c474d729bd515bbf329ea012cad9956867cc7f82；含母提示词/五主题/22角色/24分片映射。未远端生成，不变产品优先级。另已在隔离lane编写ignored同工作区研究→工程审核→FSRS→同份备份/真实Core维护恢复→重开探针，只完成10项离线helper与语法/help，真实candidate/网络/恢复NOT_EXECUTED；工程human测试不替代Owner事实验收。正式候选与上述同对象链是提交后的下一执行点，完整闭环继续PARTIAL，Green未替换。


### 2026-10-21 clean54a正式候选、同对象研究/多格式恢复与CI续修（PARTIAL）

本条接续前述NOT_EXECUTED，保持Owner后端优先及CL-01—07/J1—J6全部定义。clean检查点`54a08fb7c9a31cb784bb027f7779be272828a5a0`已commit/push，PR200仍Draft/Open，远端head核同；实际base/main为`32291ad4285bef12a58f8bec56824a835a68ce29`。TRAE既有206d56da仍在祖先链，未重搭前端、未盲合历史分支。

**正式候选构建（实际构建，不是手写PASS）**：`be-core-qualified-54a08fb7-20261021`Core release/locked/offline PASS，17233920B，SHA256 `f8c08b7352a518925f7f5984330bec84134867e2ffcced473455e874e8d24343`；`be-runtime-stage-54a08fb7-20261021`19477成员，manifest SHA256 `21882a46436b82eba34fea001eedd367992202c03937831d526e10b1377b6a57`。`be-host-qualified-54a08fb7-20261021`正式Tauri host编译PASS、47280640B，SHA256 `255406417c9857f0b51f545b4237be3489b462df2048b4db77003781115dd821`，host-build收据绑定Core、stage和当场source；stager本身ASSERTED_NOT_VERIFIED字段不升级。`be-portable-54a08fb7-20261021`正式assembler PASS，19480成员/693627515逻辑字节，候选为该run的artifacts/星环便携候选；完整成员manifest和portable-receipt（SHA256 `9cd84fbc5b76929e01f9a40af508d954f72e520e00de4375480367c6255e879d`）保留。均source_consistent=true；未安装NSIS/未覆盖Green/未公开发布。

**同候选公开研究→知识工程审核→FSRS→真实恢复（REAL后端子链）**：`be-public-learning-54a08fb7-real-20261021`156次预期HTTP，通过已登记process-only proxy取得百科/社区/科研真实内容，原始/派生6件CAS、来源定位、研究Document、封包与导出，3项来源绑定知识候选和版本化工程human审核、3项FSRS事件及幂等重放；同份备份经同候选Core `--maintenance-restore`到新owned副本，实际exit0/reaped，新epoch、旧scope409、sentinel404、对象/原文/知识/审核/事件/调度逐值回读，再冷重开。ok/backend_subset_passed/same_objects_after_restore_and_restart/source_consistent/candidate_consistent均true，收据SHA256 `d107bd38ba1975927acc6f0ee088b89cd2ff9d5c66bafbccc45f462477f6e622`。支持/反对标签和工程审核是SYNTHETIC actor，非Owner事实/比较质量验收；未调用模型。三次owned Core均terminate/wait/reaped，returncode1，graceful_exit_verified=false。

**同一恢复工作区继续多格式文件夹与个人资料（REAL Core/worker，作者自造样本）**：`be-folder-research-54a08fb7-real-20261021`440次预期HTTP（399×200、22×202、9×201、6×409、3×400、1×404），覆盖两路径同字节Markdown、CSV、DOCX、PDF、XLSX、PPTX的真实解析、完整批次/排除/失败及显式路径大小重选、重启续做；将新个人资料来源定位关联到原研究Document，旧研究/知识/FSRS仍同对象。备份CAS闭包包括原6件与新件，实际maintenance restore到另一新owned副本exit0/reaped、新epoch及旧scope拒绝，逐值回读后再重开一致。ok/required_checks_passed/backend_subset_passed/same_objects_after_restore_and_restart/source_consistent/candidate_consistent均true；收据SHA256 `2695017ede7d3512b94f5f7ad67ad22ef355b3783dd28885a15afc37dd5c080f`。未新增学习事件、未做新知识接纳或模型调用；没有公共source_origins读API，不能由batch member核对外推其内部行。五次owned Core均terminate/wait/reaped、非正常宿主退出。这里只覆盖明确样本，不冒充全部格式/J1—J6。

**同候选真实本地模型失败保全**：沿未改的LM Studio deep-mtp profile（SHA256 `7aa8d2f6e30099461f274369fb096f2cd165e4bff95d2956f9dfaaada3713394`）加载aaos-deep-27b-mtp，load回读PASS且无其它实例卸载。`be-local-study-54a08fb7-real-20261021`同一公开研究恢复工作区、709B来源材料经正式Core plan/questions真实请求，119秒返回持久化material_model_timeout，未取得答案。`be-local-study-v2-54a08fb7-real-20261021`先从实际Core重启后读回旧失败doc/task/status，再以简化问题/256token预算执行一次，86.3秒，provider报告334输入/256输出，finish_reason=length、answer_source=reasoning_content、material_no_final_answer，answer=None，未把思考文本升格答案。两失败收据SHA分别`78e0df06114f3ce3918a10aa9f83f30a366da01b8a665d9f122d5bab3fa3c0d8`、`c791eb6f95016e8027990566852776f45b783ac19e3abf01daa3988ea25e204c`，source/candidate一致。后续SDK只读processing-state样本显示idle/queued0，只证采样时空闲，不证明timeout瞬间provider已停止。未无限重试、切Ollama、改共享模型/reasoning/provider/global配置；关闭思考/替换模型策略及云端服务/模型/费用选择待Owner明确回复。先前dirty debug前三词回答保留自己的SHA，不能代替当前模型验收。

**原生宿主失败（不降低断言）**：`be-native-closure-54a08fb7-20261021`绑定上述正式host/Core，显式现有tauri-driver及Edge155.0.4283.60启动隔离数据；driver/WebView155.0.4283.62同前三段版本匹配。nested `webdriver-0e5d491b6327`在首次业务步骤前GetExtendedTcpTable family2返回Win5，steps为空，NOT_EXECUTED业务验收；cleanup也未在原15秒内确认，owned tree9PID保留失败/UNKNOWN，不称正常退出或安装成功。未提权、改ACL或重复该权限失败。后继只读exact PID handle查询全部OpenProcess87仍记UNKNOWN，未把87当已退出；19:08:32Z成功完整Toolhelp32原始快照（terminal ERROR_NO_MORE_FILES=18）中9PID均不存在，记录为NONE_PRESENT_AT_SNAPSHOT，原失败不回填PASS，未再终止共享/未知进程。两份followup JSON与原失败收据同目录保留。

**54a exact CI及最小测试修复**：run39474988973 FINAL FAILURE，rust-vnext Windows Server2025 runner中2项后代持管测试失败，a0-gates为派生失败；其余已选门禁SUCCESS，installer-lifecycle/migration/security/compatibility/windows-runtime等SKIPPED不算安装资格。实查旧夹具依赖Windows tempfile共享DELETE及固定sleep，不能据输出推导真实清理失败。仅`executor/public_research.rs`测试段现用真实无SHARE_DELETE stdin锁、ready/observed/release握手及两个对照；产品非test前缀逐字节未变，SHA256 `f247ee51c1c04cb9e51540a99bb078382f06d2ee34c0deebbb2ffd8d96f699c1`。活体捕获并持有OwnedHandle，仅WAIT_OBJECT_0证明退出；OpenProcess错误含5/87、WAIT_FAILED或异常均UNKNOWN且使测试失败。原500ms预算、timeout/cleanup_failed与退出断言未减，新增UNKNOWN故障注入RED→GREEN；独立只读复审最终文件SHA256 `eebd6993dbb0ac3c6e13ecbd904d07b50ef9899909812842e9ab90f753f99334`无合并阻断。

root `be-public-process-observer-root-20261021`在CI两线程模式19 PASS，`be-public-health-root-corrected-20261021`integration target4 PASS，`be-public-process-fmt-root-20261021`canonical fmt PASS，均source_consistent=true；首次health误用lib过滤器实际0例，保留收据、不称health通过。以上仅对应本地SYNTHETIC回归，后继提交需新exact-SHA CI；54a候选/真实子链收据保持旧源码身份，不冒充新SHA已安装。同候选云端、J3兼容/扩展生命周期、真实语义质量与Owner验收仍PARTIAL/BLOCKED/UNVERIFIED；当前main/PR200不得因本地PASS盲合。回退仅反向撤销该测试修复及本条记录；失败证据、候选、旧runtime归档及共享资源均保留。

`be-process-followup-preflight-20261021`完整结构预检及29接口维护PASS/source_consistent=true；pyreadline3退出析构WinError告警保留，未当用例失败或声称修复。最终write set仅测试文件与唯一执行记录，diff --check通过；新提交身份按实际Git/PR读取。


### 2026-10-21 后继CI与开放归档闭包修复（本地检查点，PARTIAL）

`f65e59c38b0d54c954099d4db003bff45f7a1d6f`已commit/push、PR200转Ready但未合并。exact CI39481611471最终FAIL：Windows rust-vnext job118832080579确认head/run匹配，前述两个持管清理回归已通过；后继teaching_archive_roundtrip为1 PASS/4 FAIL，当前/历史恢复实际schema13而旧测试仍期待12，并把13当future。required a0-gates job118839599112据rust失败正确FAIL；其它选中门禁SUCCESS，installer-lifecycle、migration、security、windows-runtime等非选SKIP不算通过。只读CI回报首次误写18:23时间已更正为同job实际19:23，未凭旧job判当前失败。PR200未达到合并资格，不强合。

root进一步定位为产品归档缺口，非仅断言：当前DB13但开放JSONL归档仅携旧31表，遗漏ingest_batches/ingest_batch_members/public_research_runs；archive_tables只接历史10/11及当前13，旧v12的31表无分支；恢复仍用hard_link，本机实际Win5。`be-archive-schema13-red-20261021`原5项2 PASS/3 FAIL（两个历史恢复Win5及当前13≠12）；新`be-archive-newtable-red-20261021`3项全部真实RED，分别缺批次表、当前出口不完整、v12 unsupported；`be-store-schema13-red-20261021`1 PASS/1 FAIL及`be-store-writer-schema13-red-20261021`4 PASS/1 FAIL定位其余旧12期待，source_consistent=true，不把本机Win5说成CI同一失败值。

产品修复：归档当前34表完整携新增3表，sources/jobs先于batch成员，固定literal v12=31表与v10/v11=28逐项保留；按版本与精确表集合验收，缺件/额外/未知/future仍拒绝，不推造缺失数据。将已验证domain backup的owned原子no-clobber函数体移到store raw_objects供两出口复用，domain原pub wrapper保持；无依赖/锁/SQL schema升级，使用已锁tempfile3.27。完整existing target alias检查仍在接管TempPath前，非NotFound错误failclosed，原件先/DB最后，碰撞保原目标，仅清本次owned文件、非递归目录清理。原未来负例改为当前+1（14），历史v10/v11数据/FK/原件/触发器断言未削减，bounded迁移夹具真实移除post-version新增表。新v12自造历史布局测试明确不是原生产备份，并验证恢复后新表存在但无虚构rows；新current往返逐值核批次与research请求/receipt/状态/时间列、原CAS字节、两次重开及目标碰撞。

`be-archive-schema13-green-20261021`archive全部targets共30 PASS，`be-store-migration-schema13-final-20261021`受影响teaching2+writer5=7 PASS，`be-backup-shared-publish-regression-20261021`backup_safety15 PASS，`be-archive-schema13-fmt-check-20261021`canonical fmt PASS，均source_consistent=true。范围为本地真实Rust/SQLite/CAS与作者自造fixture，不是新安装候选/公开检索或模型实跑。格式化写入命令`be-archive-schema13-fmt-20261021`child_exit0但改动源码，外层INVALIDATED/exit3/source_consistent=false，未当测试PASS。扩大store all-targets的`be-store-schema13-green-20261021`在既有cas_bounded_read创建链接Win5处FAIL（此前lib3 PASS），不改ACL/提权或放宽断言，整组不能称PASS；后继原问题targets另跑如上。

独立只读复审7文件逐hash匹配（清单`.project-local/artifacts/backend-followup-20261021/archive-schema13-freeze.json`），确认原发布函数体除路径限定/函数名及空白外等同、固定布局/事务/FK/恢复授权fence与owned回滚保留，无阻断。旧预发布schema13但缺三表的31表归档不猜补为完整13，需保留并从仍完整源库重新导出；既有全SQLite备份与失败证据不删除、不追认旧不完整出口无损。此检查点未push、未新CI/新候选、未merge/Green更新。J3来源链接消费者与材料异步生命周期在独立f65工作树进行，不把donor测试计入root或完整J3/J4；根串行接收/聚合后再定向与exact-SHA交付，仍不缩CL-01—07/J1—J6。


## 2026-10-21 后端优先：J3 原资料关系与材料异步任务聚合检查点

Owner 的最新决定保持后端全链路和 CL-01—07/J1—J6 优先；前端视觉优化暂缓。本条接收的是两个独立 f65 工作树的具名产品修改，不重搭界面，不扩展冻结项目。现场 PR200 仍 Open/Ready、head=f65e59c38b0d54c954099d4db003bff45f7a1d6f、未合并；实际 main=32291ad4285bef12a58f8bec56824a835a68ce29。f65 CI run39481611471 的 rust-vnext/required a0-gates FAIL，已由前条 archive74修复覆盖其原始失败，尚无本聚合 SHA 的 CI，不据本地绿灯合并。TRAE206d56da已核为当前分支与该main祖先。

**J3 API/持久层（IMPLEMENTED_LOCAL，非完整J3）**：严格冻结 manifest `1a9ffc925e43c1d21123dd02ee27b46eb6ae9812b7cd23008e903945e96193ee` 的22文件按原字节hash验证并留本地快照 `.project-local/artifacts/backend-followup-20261021/j3-v2-receive/frozen/`。新增有限 `ingest_member_relations_apply`；只在同批次、原CAS、明确Source/Document固定身份及scope/version/hash校验后单事务追加既有canonical关系。保留编辑正文、手工属性及关系；旧version包括重放一律409，重新读取后的相同绑定可no-op；不自动重基、猜测目标、访问任意文件或接纳知识。portable包携带Source关系原件并重映射，未打包Document/Knowledge依赖在任何目的写入前拒绝。独立复审实际复现的嵌套括号/转义label误连均有稳定RED；v2定向两例2PASS、source_consistent=true，22冻结文件前后hash同，原INVALIDATED scratch保留、不算资格。具名loss保留块/标题fragment、复杂Markdown目标、原生Vault往返及未实现的全面软件兼容。

**材料异步生命周期（IMPLEMENTED_LOCAL）**：新增 `material_question_submit` / `/api/v1/material/questions/submissions`，显式async才启用，旧sync行为及120秒上限、provider/model/endpoint/thinking不变。202仅表示耐久claim与单个受限槽位已受理；HTTP/UI离开不取消Core所有权，应用保持运行是必要条件。明确取消仅针对owned worker，provider停止仍UNKNOWN；旧pending失去owner或restore失效保持UNKNOWN，绝不自动推理。独立审阅P2发现历史终态被当前配置/恢复校验阻挡；稳定RED后，精确接收2文件修复（material_questions.rs dc6a90a6…、API tests 041d8082…），先严格匹配原请求、存储plan hash/确认及receipt/journal身份，只读返回原终态。新id/新执行仍走当前材料/配置/恢复围栏。作者13API+1publication PASS、source_consistent=true，独立只读复审核hash及原RED/GREEN收据后PASS。证据为真实Rust Core/SQLite与受控SYNTHETIC worker，绝非真实模型或J4闭环。

**root聚合验证**：共享合同/有限bridge/core消费者按基线三方合并，generated DTO由canonical生成，非整包覆盖；现行库存132 method/path pairs，历史冻结合同不变。`be-j3-async-contract-union-20261021` 143PASS；`be-j3-domain-root-20261021` 关系7+portable8+projection7=22PASS；P2接收后 `be-j3-async-api-union-20261021` API关系1+batch4+旧Vault7+材料13=25PASS；普通文案将Core术语移出该异步入口后 `be-material-async-ui-copy-20261021` 34PASS。以上收据均在 `.project-local/runs/be268a2d33/<run>/artifacts/execution.json`，source_consistent=true，各自仅证明该时点本地范围。pyreadline3退出析构WinError告警保留、子进程exit0；既有unused警告未顺手重构。前条archive30/store定向7/backup15保持原源码身份，fullstore链接权限FAIL不追认全绿。

**仍未交付**：J3 source_get与批量入口/关系消费者phase2另在独立工作树接续；本片新增原生bridge单元测试尚NOT_EXECUTED，尚无本聚合新候选/安装/Green/Owner验收。54a的156+440次实际业务HTTP、两次真实本地模型失败、原生Win5及cleanup证据仍属于54a，不挪作本片PASS。CL-06还缺真实cloud adapter与服务/材料/费用授权；本地模型策略问题待Owner回复，不改thinking/服务配置、不反复推理求绿。J2比较判断尚未结构化绑定已物化原件、常用OCR/音视频和其他轻格式的同候选资格、成熟知识库全面非企业兼容、HUB004真实扩展生命周期亦继续PARTIAL/BLOCKED/UNVERIFIED。后续按必要业务消费者→新同候选定向→exact-head CI/review合格再正常merge；不发布、不覆盖真实用户数据、不删除失败证据。回退限本检查点反向撤销；耐久原件/历史回执不通过删库或schema降级回退。

聚合提交前补验：`be-j3-async-tsc-union-20261021` TypeScript noEmit与`be-j3-async-fmt-union-20261021` canonical Rust fmt check均LOCAL_PASS、source_consistent=true；未执行原生新增route测试，不外推为build/runtime。
