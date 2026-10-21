# AAOS 完整接手提示词：后端闭环优先，含已连接 Stitch 前端来源

可整体复制本文件给新会话。工作区 `D:\All projects\ArcheAxis-Knowledge-OS`。这是一份接续导航与任务要求，不是第二份进度记录。实际进度唯一写入 `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`；本提示词内的观测均为2026-10-21历史快照，首次动作仍须核现场。完整交接及详细分片都要读，不能只读摘要。

## 1. 最新任务、授权与读取顺序

Owner最后要求：完成本轮后端候选收尾，接收另一会话已经跑通的Stitch设计；在本会话实测只读连接，查看截图、完整读HTML、对照项目；统一归档本会话和设计交接，并给出本完整提示词。后端全链路优先于余下UI，保留TRAE与现有前端成果；节省TOKEN，不做非必要工作、不重复无意义全量测试。按难度进行实时并行，独立读审可共享，同一checkout一个writer，独立writer隔离worktree。

先完整读取：`AGENTS.md`、`AUTHORITY.md`、`PROJECT_CONTRACT.yaml`、`docs/current/AAOS-ACTIVE-EXECUTION.json`、`docs/truth/CLOSED_LOOP_DEFINITION.md`、本文件、`docs/current/AAOS-FRONTEND-FIRST-EXECUTION-OVERLAY-20261019.md`、唯一执行记录。Task Grant以当前Owner原话、活动指针 `delivery_authorization` / `green_update_authorization`及冻结边界共同解析，未发现独立命名的Task Grant文件，不自行补造。

再读选中任务包 `docs/taskpacks/aaos-ui-first-20261009/` 的TASKPACK.md、TASKS.json、PAGE-PLAN.csv、FREEZE-REGISTER.md，补充前端/后端合同位于 `docs/authority/taskpack-20261013-frontend-ui/01-Frontend-UI/`、`docs/authority/taskpack-20261013-backend-host/`；读 `docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md`、`docs/current/AAOS-EXECUTION-BACKLOG-20261018.json`。UI-P/BE-P/RC-P是原任务的实施分片，不替换原ID或另建产品真值。

所有路径先查 `AAOS-资料索引.md`、`docs/current/AAOS-AUTHORITY-ROUTES.json`、`docs/SHARED_RESOURCE_PATH_INDEX.md`、`config/environment/capability-requirements.yaml`、`config/environment/external-resources-index.json`及具体manifest。文件缺失先查归档/ZIP成员，不猜路径或扫描Home/整盘。缺权威报告AUTHORITY_REFERENCE_MISSING。登记不是实际可用证明。

正式栈Tauri2/React/TypeScript/Vite，Rust Core唯一SQLite/CAS业务writer，Python隔离worker；保留普通Document/Block直接保存、版本/幂等/草稿/人类知识接纳边界。沿用DockWorkspace、ConsoleWindow、图谱和人物renderer，先读已有实现只补差距。不再搭壳、替换渲染器、另建能力注册中心或另起ASTRYN。

现有授权涵盖当前公开源码/文档的普通commit/push/PR，以及审阅和required exact-head CI合格后的正常merge；push不等于merge。不得force/reset/clean/改写历史。公开发布、私有材料外发、付费云模型调用、真实用户数据覆盖、未知共享进程终止未由设计接收授权。Green程序更新仅限 `D:\All projects\ArcheAxis.Knowledge.Green-x64` 且先满足资格/备份/停止/精确成员核验；本轮未更新Green。

Stitch只读：get_project/list_screens/get_screen/download_file；禁止generate/edit/delete/upload/apply/publish，不修改全局配置，不回显密钥，不重启其他会话。读取设计不是原型、宿主或产品验收。E:/F:默认禁访；不读凭据、私人原生会话/账号memory、浏览器认证。V01暂停，FT01—04及六项增量冻结；不自行恢复额度监控、创建定时或承诺后台继续。

## 2. 已承接工作与证据边界

本段由本会话可见指令、Git和项目回执梳理，不是私人原生会话逐字导出。完整旧交接已原字节保存在 `docs/history/product-loop-20261019/session-20261021-stitch/HANDOFF-BEFORE.md`，原位置见同目录MANIFEST；旧相对链接按原 `docs/current/` 解析，不据旧“前端先行”覆盖当前后端优先。

TRAE最后总结的 `206d56dafd00d0d3ccfd949ce6a4e424a324112a` 已在当前产品历史中；术语收敛、A0竞态、安装可见导航修复等保留。不要再盲合旧整包。PR194已于2026-10-20正常收敛，PR192/193重复内容已妥善关闭；19本地/4远端等价分支清理记录在 `docs/history/product-loop-20261019/branch-convergence-20261020.json`，六个有独有内容的分支继续保留。旧25分支待传说法是历史，后续仍动态核对远端/patch/占用。

PR200产品head `a63cda6d1864b70e74f54240d1246fa0d0b2fe7e` 已merge为 `86a486719b0d7a88602ff03c5ce393d447dfd9bd`；PR CI39594971487与main CI39597792036均SUCCESS，条件skip不算安装通过。本批落实machine.answer撤销lease竞态修复、经Owner批准Pillow12.3→13（205锁记录仅1条变化，其余204不变，项目环境内验证）、Store生产tokio rt特性和有限Markdown原件标题/块精确映射。独立审阅报出的UTF-8 panic、遮罩/定义歧义及列表边界均已修复并原问题回归，不降低断言。旧FAIL及修复证据保留。

a63实际候选：Core `1a1d9b9bb892aba0dc7d940d2cce993b339c75783eb0fae5e549ce62862c837c`；正式host/portable成员资格通过，不是已安装或Green验收。真实公共检索156 HTTP步骤（Wiki/StackExchange/OpenAlex→CAS/定位/比较→工程人工知识/FSRS→恢复冷读），接同工作区常用资料/J3有限关系/明确fragment/OCR/英文WAV和MP4/导出恢复链1895步骤、3790 journal事件、严格replay与源候选一致通过。最终长链收据SHA `b0a927ecddcf9106062c31adb5e450e54ba8e8a7c954a45e270d6588cafe7e40`；汇总 `.project-local/artifacts/backend-followup-20261021/a63-full-chain-final-readback.json`。工程human是自造材料SYNTHETIC，公开网络/Core/worker实际执行REAL；speech仍PARTIAL，不称中文/视频视觉/全部识别质量合格。旧021中断1467步不能PASS或借给后继SHA。

J5本轮产品head `8475af51f55f4df085467c48f71b22eb660f70f8`：复用同一能力中心、capability_settings和Tauri bridge，提供first-party inert data-only T3 v1/v2启停、更新、回退、卸载/重装，pin/hash/snapshot/epoch围栏；停用卸载只阻止新应用，原文、引用、旧字段、知识和学习保留可用。独立review发现新增字段没显示，已修为按已存pin/fields编辑，回归先RED后GREEN；66后端、33 bridge源码harness、58 UI及相关合同定向通过，模拟native不称真实GUI。

schema13→14只加同表三列。原31-Source、47旧表的schema13备份SHA `ee3e43d48f85001e22515b3db010098b878bd632d80589d09b101fce05a8fa8c`由新Core真实恢复升级14，原a63Core独立恢复原备份13，旧列/CAS逐一相等，原备份不变。旧Core不能开14，回退用原13备份；不降级原库。升级证据 `.project-local/runs/be268a2d33/j5-real-schema13-upgrade-8475af51-retry1/artifacts/upgrade-receipt.json`。

8475 measured Core SHA `223da0b89c1aa7f7a0212058d71ea7b06295fd11888e2de4f669b63a1ec91306`，18,092,544B；独立stage `.project-local/candidates/backend-8475af51-20261021`，19479成员，manifest `4b08e3b2dee34a7410884af38460c937c32cbe4af3ca59008fcc91ac7e125c73`。实际content-policy 65 HTTP普通保存/ACK/版本/检查/备份/恢复/重启通过；实际J5 54请求在原31来源恢复工作区完成生命周期、拒绝、旧对象编辑及冷重启保留：`.project-local/runs/be268a2d33/j5-real-lifecycle-8475/artifacts/lifecycle-receipt.json`。均非安装GUI/完整新候选CL/J。自有Core stop/wait回收，不是原生正常窗口退出资格。

8475 CI39613573199失败于3个消费者仍精确断言schema13；保留原日志，不当新产品行为失败或放宽断言。后继 `2adf5724359d2d9ea03e59ae660dacb661f7e3ef`仅修两个验证文件的精确14期望及记录，本地4+1回归通过。该exact head CI39616983445于14:45:38Z SUCCESS（8 job成功/11条件skip，required语义gates全部满足，非full qualification）；独立审阅与现行规则核对后PR201已正常expected-head merge，main `fc75de866714d89e9d9605c60fba3240cba6246d`，tree `818f85ceea2d9be00c0219628c0ed958e7de8e1b`，parents86a48671/2adf5724。main自身CI及后续文档提交仍动态核对。8475实际构建不能改称2adf新构建，skip不算安装态PASS。

## 3. 当前未完成与下一轮真正切片

整体始终PARTIAL，不能用本轮归档、连接、构建、CI或局部通过宣称闭环。先动态核PR201是否已正常merge、main CI及工作树，再接必要业务缺口，不重做已完成定向回归。

1. CL-06/J4：LM Studio既有aaos-deep-27b-mtp当前候选真实尝试一次119秒超时，一次86.3秒仅reasoning_content/finish=length，无最终答案；历史旧候选回答不能借用。模型thinking/输出策略Owner决定待答；不自行换模型、改provider或自动回Ollama，不重复相同失败调用。真实云端provider/材料/端点/费用授权仍缺，明确BLOCKED；不扫凭据、不试传私人库，不拿mock冒充真实接通。
2. CL-04/J3：有限链接/块/图谱已有实际子链，全面“软件×版本×非企业特色×方向”矩阵仍欠；68项混合供体不是68款软件全兼容。Canvas几何/边保存不等于全canonical语义往返；复杂格式/引用写明损失，不静默删需求。
3. CL-05/J5：本轮只证一项first-party T3模板生命周期，不代表任意第三方代码或插件/技能/MCP各形态全接通。按同能力中心及真实消费者逐项补，复杂项具名延期，写损失/恢复条件/蓝图落点。
4. CL-02：中文自造TTS在SAPI Language804枚举HRESULT0x80045039、Speak前阻断，无中文音频/ASR资格；既有英文时间托管是有限PARTIAL，视频visual未启用。须可用正常TTS或明确批准的自造中文音频/truth/hash，不改注册表/ACL/共享环境。
5. CL-07/J6：同一最终候选的完整J1—J6、原生安装/窗口/缩放/DPI/键盘/无障碍/性能与Owner独立验收未完成。历史installer grouped UI FAIL、GetExtendedTcpTable family2 Win5等负证据保留；conditional installer skip不是PASS。只在最终候选触发必要完整资格，Green更新资格未满足，保持真实数据/程序回退。
6. BE10真实外部对端/OS URI完整资格，全面UI24分片与RC-P01—08剩余精确批次仍欠；不以治理代替产品修复。ASTRYN独有资料/Cowork全文/未命名定时身份继续UNVERIFIED，不擅自删库或扫描私人源。

新接手的最小动作：读现场 → 对照唯一执行记录中最新失败/授权 → 按当前后端15片解决可独立推进的一项实际差距；若模型/云端等待Owner，继续独立矩阵/已授权消费者或安装失败定位，不造成功。无新变化不重建冻结/派重复审计/全测。

## 4. 已接收且本会话实测可读的 Stitch 来源与前端任务

项目 `AAOS Desktop Replica`，`10243059433218383839`；页面 `AAOS 交互整合版`，`206611daf7a948edb97ea60c7a7d8654`。另一会话外部交接目录 `C:\Users\ALEX\Documents\Codex\2026-10-18\codex-codex-ui-ux-work-lab\outputs\stitch-connection-20261021`，HANDOFF-AAOS.md/REPORT.md及明确列出的HTML/PNG/三个只读脚本已按精确对象复制保全，原件不动。

本会话2026-10-21T14:35:32Z起真实initialize/tools-list，核readOnlyHint及schema后get_project/list_screens/get_screen/download_file；八个HTTP响应成功，远端写入0、模型turn0。HTML97,811B SHA `8c9fba60a636ab8f9fdf9d5c1bb70dbf9dd32cba4961ade66f5aa5feb6f2ba18`，PNG2,757,978B/2560×2048 SHA `46c09bc4bc9428ae716f1159a8d263a78fce15d8b7fa856d3367ded2243f9e46`，实时下载与另一会话一致。截图实际查看，HTML1683行完整只读审查；没有执行脚本/加载外链。

项目本地快照及连接收据：`.project-local/artifacts/stitch-intake-20261021/live-read/`；原交接与脚本保全：同父目录 `received/`。公开导航、hash和比较：`docs/history/product-loop-20261019/session-20261021-stitch/README.md`、`MANIFEST.json`、`STITCH-COMPARISON.md`、`DESIGN.md`。原始设计/外部交接/运行收据保持ignored，不随公开Git上传。原生Stitch MCP会话挂载仍UNVERIFIED，本会话已证明替代只读入口可用，无须重启其他会话或重复配置。

必要刷新时先审查已保全的Read-Stitch.ps1/read_target.py/verify_stitch.py，再运行原交接或本地received中的Read-Stitch.ps1，`-OutputDirectory`给当前项目新审计目录，可`-MetadataOnly`避免下载。例：`& '.project-local\artifacts\stitch-intake-20261021\received\Read-Stitch.ps1' -OutputDirectory 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\artifacts\stitch-intake-next' -MetadataOnly`。密钥由入口仅传给自己的子进程，不打印/归档。不要直接执行verify_stitch.py主程序（其独立诊断入口会更新外部latest-verification）；Read-Stitch.ps1调用的是read_target.py，仅写给定目录。沿用既有Windows代理是客户端读取，非更改系统网络。

设计可取：星际环境留白、内缩研究主窗、右侧辅助资料/助手层级、底部应用内导航、证据选中/原文定位/冲突并列。冲突/缺口：固定桌面几何及无窄屏适配；只有5路由3设置tab；没有大地图/图谱及虚拟人物renderer；小栖只是文字窗口；connected=true/同步/解析/数量/学术结论属于模拟。不得直接替换现有React壳或把硬编码状态当真实业务。

后端优先不变，前端后续先将研究/证据比较与右侧资料联动映射已有Core对象/权限/版本和现有组件，再保留大地图、内缩主控台、独立虚拟人物窗、现有图谱/人物renderer；拆分/标签/恢复复用DockWorkspace。必要短词对齐“小栖”，工程ID/结构/JSON归运行诊断。完整UI24项全部保留，截图的五个页面不缩范围。设计技能通用禁蓝/单强调色/持续动画等建议不覆盖Owner既定五主题、cosmic和减少动画要求；DESIGN.md是项目定制参考，不建立新的权威。

## 5. 保留的完整前端24片（后端优先后接续）

**必须读取详细分片的逐项验收标准**，以下是执行目录。先核既有实现，按缺陷／缺失／待验收分类，只补必要差距：

1. UI-P01：生产页面×状态×尺寸覆盖与已有FAIL证据，PAGE-PLAN的22角色不是必须新建22路由。
2. UI-P02：信息架构和所有业务文案，清理“正典任务”等工程词；ID／schema／协议／JSON／日志进运行诊断，保留必要业务来源和版本。
3. UI-P03：最新大地图／主背景＋内缩主控台，像桌面工作空间，但不接管系统桌面／任务栏／全局快捷键。
4. UI-P04：内部主控台与原生窗口分别测移动、边角调整、铺满还原复位、键盘等价、Esc／pointercancel取消、防拖出可视区与草稿保护。
5. UI-P05：复用DockWorkspace做左右／上下拆分、分隔条、标签、关闭／重开、独立滚动、布局复位；窄屏退为标签或单栏；已有保存合同须验重启和失效几何恢复。
6. UI-P06：外层窗口／主控台／Dock／portal按实际容器响应，窄矮组合、长中文、Windows DPI和应用／浏览器缩放分别测，不整体缩小字体。
7. UI-P07：菜单／正文／辅助字／按钮／portal字号行距密度和点击区一致，长标题／路径／URL／表格可读，无失控溢出。
8. UI-P08：玻璃磨砂／透明度／阴影与同圆角边框高光，修错位／重复描边；五主题、对比与减少透明／高对比回退。默认cosmic以活动指针核，不按旧blueprint改回。
9. UI-P09：全部导航／抽屉／设置／命令菜单／tooltip／弹层实际命中、边缘定位、遮挡、关闭和焦点返回，不JS点隐藏按钮掩盖失败。
10. UI-P10：Tab/Shift+Tab/Enter/Escape、快捷键范围、中文IME、文本选择、键盘拖动等价、焦点陷阱与还原。
11. UI-P11：加载／空／失败／超时／取消／未知／离线／权限依赖缺失／重试／部分成功，防重复提交；202请求取消和未确认保存不报成功。
12. UI-P12：工作台／知识库／列表筛选排序／导入批次／格式损失／逐件失败／导出恢复入口，临时数组不冒充耐久批次。
13. UI-P13：阅读编辑、PDF／图片／媒体、分屏、引用定位、保存、草稿、三方比较／版本／重启；原始JSON从诊断读。
14. UI-P14：免费百科／社区／科研检索、结果详情／原文／引用、证据比较／冲突／保存与失败；模型生成链接不是检索证据。
15. UI-P15：现有图谱布局／视觉算法、缩放平移／选中聚焦、密集遮挡／中文标签、详情联动；保留renderer，尽可能合法还原供体效果。
16. UI-P16：学习路径／课程／教学需求／方案审阅／交付／Teach-back／反馈修订连续页面，复用OpenMAIC quiz M1，核对象版本、返回和状态。
17. UI-P17：本地／云端模型选择、连接加载推理区别、材料授权、依据回答、纠正复测、停止重试；BUFFERED不称token流，迟到片段缺口显式记。
18. UI-P18：同一能力中心整合插件／技能／模板／MCP／未来蓝图，可用／未配置／缺依赖／未接入／延期真实区分，底层库不假装可安装插件。
19. UI-P19：小栖直接适配AAOS，移动／收起／缩放／聊天／焦点／遮挡，复用资产和模型；不另起ASTRYN开发。
20. UI-P20：诊断／系统可靠性／来源历史版本／受限任务回执／备份恢复收敛，正常业务清爽、错误仍可发现并回跳。
21. UI-P21：所有生产页axe＋必要键盘／屏幕阅读检查，标签播报对比焦点和点击区，保留incomplete；自动扫描不是全面合规。
22. UI-P22：展开收起／连续中断／减少动画，大列表图谱性能；记录设备、规模、方法、结果，装工具不等于接性能监控。
23. UI-P23：全页面主题／尺寸／状态视觉回归，保存并真正看截图，记录浏览器字体DPR主题数据；首次基准不等于正确、不更新掩盖差异。FE25可本地采素材，不为此强行公网部署。
24. UI-P24：同候选隔离实际安装，窗口菜单键盘草稿冲突诊断重启，关闭grouped UI失败；交付前端覆盖、未测及后端接口阻断，不能报全产品闭环。

全量包含22业务语义角色及共用壳、状态栏、对象侧栏、命令菜单、Inspector、splitter、设置、人物浮层；详细分片列齐。角色合并在同页时按语义验，不制造新页凑数。前端阶段不得绕过Core写库；fixture只证明隔离UI，缺API明确登记并继续其他独立项。

## 6. 当前优先后端15片

1. BE-P01：核心对象／版本／保存／未知ACK／冲突／幂等／备份恢复，复用Rust单写者。
2. BE-P02：常用格式矩阵、解析OCR转写位置损失、真实样例与对外承诺操作。
3. BE-P03：正式FolderIngest→Core耐久批次、逐文件身份作业结果／重试取消／重启，不以legacy流程替代正式真值。
4. BE-P04：百科／社区／科研三类真实免费检索，核官方API／许可／账号／免费范围／限流／元数据摘要全文，复用原候选。
5. BE-P05：去重与来源独立性、定位引用、支持反对冲突、人工知识接纳／学习及重启关联。
6. BE-P06：软件／版本／非企业特色／方向兼容矩阵，不适用／损失／具名延期，不能只留好测项目。
7. BE-P07：兑现特色，通用机制核心、协议适配器、视图算法插件、流程技能、结构模板、外部工具MCP。
8. BE-P08：LM Studio本地＋云端真实模型、真实增量／材料权限／取消超时迟到事件／恢复；无云端授权凭据如实BLOCKED。
9. BE-P09：HUB004真实扩展生命周期、依赖权限版本、安装更新回退禁用卸载与原对象保全；复用HUB001—003。
10. BE-P10：图谱与OpenMAIC已有成果接同一Core和真实业务数据，不另建画布或课堂平台。
11. BE-P11：BE10外部对端／OS URI、用途身份、选区固定版本、过期撤销重启，不以本地human资格替代。
12. BE-P12：同一候选完整J1—J6和失败恢复。
13. BE-P13：稳定CI，源码／生成物／合同／探针同步，原问题回归再阶段门禁，不减断言／required skip求绿，不连续无意义push取消重型CI。
14. BE-P14：合格候选Green更新、哈希读回、数据保全和程序回退。
15. BE-P15：企业／复杂项蓝图、资料会话缺口／账号设置／未命名定时尾项单独标识，治理不反复阻塞产品。


## 7. 各类库、模型和工具路径

路径唯一依据是docs/SHARED_RESOURCE_PATH_INDEX.md及config/environment/capability-requirements.yaml；config/environment/external-resources-index.json只代表时点观察。登记≠安装≠会话发现≠连接≠真实调用。

| 资源 | 精确登记位置／边界 |
| --- | --- |
| 主项目／产物 | D:\All projects\ArcheAxis-Knowledge-OS；通过scripts/runtime/dev.py放.project-local/，不写旧.hermes/。 |
| 日常Green | D:\All projects\ArcheAxis.Knowledge.Green-x64，和CI隔离NSIS不同。 |
| 模型库 | D:\All projects\Model library，共享只读，按索引取，不迁移删除或再下载一套。 |
| 共享工具库 | D:\All projects\OS External Configuration，共享只读；工具链子目录10-toolchains，具体位置核manifest。 |
| 真实材料／样本 | D:\All projects\资料库、D:\All projects\ceshi；仅本任务明确批准的隔离样本可用，登记不是内容读取／上传／修改许可。 |
| 资料／兼容来源 | D:\All projects\Record、D:\All projects\Obsidian-Assistance，只按manifest读具体对象，不扫描根目录。 |
| ASTRYN | 旧D:\All projects\ASTRYN及云端NOT_READY_TO_DELETE，AAOS人物适配不证明原资料全迁完。 |
| 其他软件与库 | GPT导出、Claude Code/Cowork、Codex会话只沿本项目索引最小读取，不扫Home或凭据。WORK-LAB／DESIGN-LAB独立，不随本项目授权写入。 |

模型入口docs/current/AAOS-LOCAL-LLM-20261018.md、config/model-profiles/lm-studio.json、scripts/runtime/lm_studio_profile.mjs；既有LM Studio http://127.0.0.1:1234/v1，**不自动回Ollama**。27B MTP／GPU比例／context等按实际profile与加载readback核，不凭历史配置宣称成功或加速，不改Agent provider／endpoint。

当前视觉工具根C:\Users\ALEX\.codex\tools\visual-tool-lab。已装技能C:\Users\ALEX\.codex\plugins\cache\alex-local-tools\visual-audit-tools\1.0.0\skills\visual-project-audit\SKILL.md，先核references/runtime.json实际绑定，读工具README.md、INSTALL-MANIFEST.md、CAPABILITY-MATRIX.md、BROWSER-USAGE.md、PROJECT-GUIDANCE.md及脚本。旧C:\Users\ALEX\Documents\Codex\2026-10-18\codex-codex-ui-ux-work-lab只是迁移来源，不作运行入口。

按当前可用性调用visual-project-audit、ui-ux-pro-max、web-design-guidelines、Playwright、gh-fix-ci、workflow-assistance-github-delivery等。文件存在不代表会话加载，更不代表产品通过；不重复安装浏览器／升级依赖／改全局Skills、MCP、Hooks、PATH。样例browser.mjs只服务样例（41730—41739及profile／输出受限），不改限制接管产品。产品专用脚本、独立profile、空闲127.0.0.1端口、一浏览器一worker，记自建PID／命令／时间，只结束自己的实例。启动前核脚本不会安装／迁移／写真实业务或连正式服务；有副作用就用其他安全路径。

## 8. 开源池、会话和历史资料入口

- docs/truth/CAPABILITY_ATLAS_V2.yaml、CAPABILITY_ABSORPTION_REGISTRY.yaml、SUPPLY_CHAIN_LEDGER.json；docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json的68项是混合供体库存，不是已装插件数。
- 历史369池、供体取舍、研究映射的精确链接见闭环定义第八节，不重复搜索／引入。先核许可，不能把源码可见当可商用或改名规避许可；付费能力取合法替代／独立实现或具名延期。
- [UI供体分析](AAOS-OSS-UI-DONORS-20261019.md)：[Neural Creator](https://github.com/Linye-ai/neural-creator-dashboard)、[GlassBoard/win-.-](https://github.com/SENLIN-SAMA/win-.-)、[OpenMAIC](https://github.com/THU-MAIC/OpenMAIC)。重点图谱交互和视觉算法、合法效果还原，复用原renderer与quiz M1，不重做整课堂／多Agent／第二画布。
- docs/current/AAOS-CODEX-SESSION-INDEX-20261018.md、AAOS-SESSION-RECONCILIATION-20261018.md、[39主题原话映射](../history/owner-dialogue-20261019/README.md)是授权脱敏派生物，不是全部私人逐字正文；Cowork完整正文UNVERIFIED，恢复任务包不等于恢复会话。
- 根AAOS-资料索引.md、docs/history/record-archive-20261009/INDEX.md及MANIFEST.json；原始字节.project-local/archives/record-20261009/忽略，不上传。
- docs/history/README.md、repository-consolidation-20261019/MANIFEST.json：旧交接／提示词／摘要／目录按原路径和hash查档，不在原位重建副本；清理先查现有引用及唯一证据，更新活动引用后只处理确证冗余，不删未知文件。
- docs/history/product-loop-20261019/下conversation-closeout.md/.json、conversation-review.md、follow-up.md、verification-index.json、tool-usage.json保留前轮实测与失败；后继决定走活动指针，不让旧“停止新增”覆盖当前指令。

## 9. 授权、冻结和未核实尾项

commit／push／PR／merge按活动指针delivery_authorization与当前任务核对；merge须当前审阅及required CI合格，push不代表main已合并。仅上传授权公开源码／文档，不上传密钥、.env、私人会话／记忆、浏览器认证、运行数据库或真实材料。

Owner明确允许D:\All projects\ArcheAxis.Knowledge.Green-x64的**程序文件更新**，无需再问同一路径；授权不是候选资格。先修安装FAIL、核合格候选／成员、目标停止、保全hash标识程序回退；按清单替换并核哈希／启动身份。保留data、根archeaxis.sqlite、backups、用户资产／偏好／未知目录；不偷做真实数据覆盖／不兼容迁移／公开发布／终止未知共享进程。v0.6.14标签不证明当前安装成员一致。

V01暂停，FT01—04及活动指针六项增量冻结，展示蓝图不激活运行。2026-10-19不查额度、不据额度停工；其他日期按当时Owner决定核，不自行恢复监控。已知archeaxis删除返回not_found，不证明截图未命名卡片已删，该身份仍UNVERIFIED，不阻塞产品、不重建定时、不承诺后台工作。ChatGPT账号记忆／个性化没有确认成功，不写已同步；仓库可验证决定与客户端真正加载分别验。

E:/F:默认禁访，读到旧脚本不构成进入许可。不扫Home／磁盘，不改全局账号、模型、provider、认证、网络或服务配置；路径登记不授予跨项目或私人数据权限。

## 10. 验证、交付和首次动作

先读canonical gate及变更风险，不默认全仓pytest或npm test。已知入口：项目.venv/Scripts/python.exe、scripts/runtime/dev.py、Windows scripts/ci/run_tests.ps1、Rust scripts/ci/cargo_test.bat（裸cargo可能缺MSVC）；前端manifest的build／tauri走scripts/runtime/frontend.mjs。每次核实际版本／入口，不新装替代环境。

回执示例：`.venv/Scripts/python.exe -B scripts/runtime/dev.py --run-id <唯一ID> -- <确切可执行文件> <相关参数>`，具体门禁以当前manifest为准。权限／锁／编码失败先分类，不改ACL／换身份绕过拒绝。产物.project-local/，公开脱敏摘要按现行目录记录并回链唯一进度，不能覆盖旧FAIL。

每分片写清原问题／预期／实测→必要修改→最小回归，阶段终验再跑规定门禁。全量必须定义边界、用例目标、核心业务／风险、未测；随机点击只探索，有价值问题转为可复现缺陷。截图保存并实际查看，不能仅凭无障碍树、首次基准或工具样例报产品通过。

状态PASS/PARTIAL/BLOCKED/NOT_EXECUTED/UNVERIFIED；证据NO_EVIDENCE/SIMULATED/SYNTHETIC/INTEGRATED/REAL。源码结构、本地单测、浏览器合成桥、真实Core、原生、安装、exact-SHA CI、Owner验收分别报告，失败／取消／required skip不算PASS。记录源SHA／patch、命令、时间、退出码、截图回执、未测与回退。

**当前首次接手行动（Owner 2026-10-21改序）**：先核现场Git/CI与唯一执行记录中的失败证据，按后端15分片推进同候选J1—J6及完整闭环，保留既有前端与TRAE修改。前端视觉可以缓缓，只补业务消费者和阻断修复；前端24分片保留欠账，不因改序宣称已交付。不得拿新一轮长审计或重复全测代替产品修复。结束核diff／status、自建PID与端口，更新唯一执行记录，给下一步和阻断；不能用交接、归档、测试数量或模型加载宣布产品完成。

## 11. 补充必须交付：分支合并、体积清理与双端规范

Owner后继明确要求把“分支合并”“体积清理、本地和云端仓库规范化、目录规范化”一并纳入。详细分片第五节RC-P01—08规定逐项验收，继承G01／UF13／交付范围；先只读盘点，UI相关供体按前端顺序吸收，不能用整理代替当前后端业务修复或陷入无止境审计。

1. RC-P01 动态列本地与**实际远端**分支、PR、worktree、独有提交／修改与归属，保留所有未知脏内容。
2. RC-P02 比较未合入内容、patch等价／squash／cherry-pick、供体效果与冲突；非祖先不等于没吸收，不能盲合旧整包把旧权威带回来。
3. RC-P03 核PR192／193／194重叠，逐项定保留／后继已包含／拆分，合格审阅＋required exact-SHA CI后合入main并复验。不能只push不完成合并，也不能绕过失败强合。
4. RC-P04 合入并证实无独有内容、无占用后，按授权清理确切已合并本地／远端分支和已妥善处理的PR，读回；不删未吸收／未知分支、不改写历史。
5. RC-P05 分开量化源码工作区／tracked大文件／Git历史对象／构建缓存证据／云端CI产物和release，写时间、字节、归属、再生性，不把共享模型资料算可删缓存。
6. RC-P06 清理先列原路径／hash／大小／归档或替代／重建方法；保全独有原件、失败证据和有效回退，只处理核实项目所有且可再生／重复对象。压缩验成员和hash，普通删文件不等于Git历史减小，历史改写未授权。
7. RC-P07 按DIRECTORY_AUTHORITY.yaml和职责索引规范源码／合同／current导航／历史／供体许可／忽略运行产物，更新活动引用、查孤儿旧入口、原位不留第二可变副本，不乱搬不可变TaskPack。
8. RC-P08 分别读回本地／远端／main／PR／release身份和清理前后字节，公开源码文档才同步。云端artifact按证据价值、期限和精确授权处理，保留失败／待审候选；不改可见性、保护规则、付费存储或擅自发布。
