# AAOS 完整接手提示词：Stitch全量界面与前后端并行接通

> **当前最高UI决定与接收状态（2026-10-22）**：Owner明确“不要再维护旧版界面了，全面接入STITCH界面啊（这才是新版界面）”。Stitch是唯一新版；本轮已将22页、12组已有消费者的中心布局全部重排接入源码，移除旧布局偏好分支与重复导航/搜索，保留既有Core合同和业务状态。54文件660项组件回归、TypeScript与67项模拟桥浏览器检查PASS。原设计只有5个专用页面，其他页面沿同一设计语言承接已有业务，不宣称未见原稿的像素还原。完整产品仍PARTIAL：Owner批准正式审批通道后，canonical前端生产构建和资源投影检查已PASS；当前新UI实际Core、原生/安装、Owner和exact-SHA CI尚未执行。精确证据见[当前检查点](../history/project-drift-audit-20261021/stitch-ui-local-checkpoint-20261022.json)及唯一执行记录最新段。

可整体复制本文件给新会话。工作区 `D:\All projects\ArcheAxis-Knowledge-OS`。这是一份接续导航与任务要求，不是第二份进度记录。实际进度唯一写入 `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`；历史产品观测主要为2026-10-21快照；2026-10-22续接段仅对应本轮观测，首次动作仍须核现场。完整交接及详细分片都要读，不能只读摘要。

> **最新范围决定（2026-10-22，优先于下文旧后续顺序）**：Owner明确可选开源池、第三方API和具名软件特色扩展“这些都是后期内置市场里的了”。停止按兼容矩阵自动补功能；当前不建市场、不新增扩展包或各形态运行时，仅沿已有合同收敛专业接口约定，落实已接收Stitch UI与已有核心业务接通、修复和验收。详见[决定第十八节](AAOS-OSS-INTEGRATION-DECISION-20261019.md#十八后期内置市场与本期范围收敛2026-10-22)与活动指针`execution_priority_overlay.scope_control`。旧段中的“下一步继续矩阵／其他扩展”是历史顺序，不能再次自动执行。现有实现、负例和长期目标保留；接口预留不等于扩展已实现。

> **历史运行证据（2026-10-22；不能借给本轮Stitch UI）**：document-tags-portable-03是最近已组装并做过局部实际集成的候选；后继标签排序/层级/折叠仅有组件及构建资格，未取得新候选实际集成验收，不继续派生开发。完整CL/J及Stitch逐页视觉落实仍PARTIAL。监控aaos按既有规则执行；Git只读交付阻塞未解除，不称双端一致。

> **历史共用UI局部修复（2026-10-22；已由顶部本轮证据接续）**：Owner明确要求加速并行，三组并行只读核对设计、消费者/焦点与工具环境，主线程唯一writer接收。已将主窗内伪留白及内嵌检查器改为Stitch主窗＋右上小栖＋右下来源检查独立窗，窄屏辅助窗按需互斥，保留DockWorkspace、草稿和现有Core接线；修复重复切换、缩窗隐藏焦点与放宽窗口抢焦点。最终组件57/57、TypeScript及15项隔离浏览器自动布局/焦点检查PASS；浏览器是SYNTHETIC，不能代表真实消费者、全22页视觉、原生或安装验收。回执`.project-local/runs/stitch-shell-node-20261022/artifacts/receipt.json`，SHA256 `0936283cbc4129d9e9dcd09b8b8f35d2a695882df479ba1bc7266493ab90c4b7`。本轮没有新增业务/扩展或后端功能。

> **最新权限修复与验证（2026-10-22）**：Owner明确允许平台正式审批通道。Python 3.13.14与Git元数据唯一临时文件写入/删除均PASS；默认沙箱仍受限，未修改ACL、全局配置或索引。原canonical前端生产构建、原资源投影--check、16项合同及18项资源UI回归PASS。7处历史引用现指向HEAD中3份精确原始字节，原hash/资格状态不变，不能当作当前运行资格。详见[本轮检查点](../history/project-drift-audit-20261021/stitch-permission-recovery-20261022.json)。161项公开任务成果已提交并推送，代码检查点d388801b96f851a20e68d796db276c49f4aae586经Git与native GitHub双重核对一致，工作树在回读时干净。此交付回读另存后续文档提交；当前最终SHA现场读Git/native GitHub，不伪造提交自指SHA。该代码SHA未取得CI证据。原生宿主、安装和同候选CL/J仍待验收。

> **本轮本地恢复路由（2026-10-22）**：固定155个公开任务文件，来源为原113文件交付白名单加经本轮审阅的42个UI/范围文件。当前包 .project-local/artifacts/stitch-ui-recovery-20261022-final/public-task-files.zip，manifest .project-local/artifacts/stitch-ui-recovery-20261022-final/MANIFEST.json，逐成员回读验证 .project-local/artifacts/stitch-ui-recovery-20261022-final/verification.json。仅在verification.json为PASS且manifest/ZIP/成员hash均相符时确认本地快照可用；它不表示上传、Git同步、构建或产品闭环。包不含凭据、私人会话、运行数据库、缓存或大回执，旧快照保留。

## 当前后续顺序（2026-10-22 Stitch唯一新版）

1. 保持当前新UI和已有业务状态；不要回到旧布局维护或重新按兼容库存派生功能。
2. 已通过Owner批准的正式审批通道完成canonical前端生产构建和资源投影检查；7处引用通过精确历史字节归档修复，未改hash/资格。后续沿原流程资格化当前原生host/Core，不把本地前端构建当安装验收。
3. 对同一合格新候选，接真实既有Core消费者、CL-01—07/J1—J6、原生/安装与Owner验收；当前67项只是SYNTHETIC浏览器布局/状态检查。
4. 公开任务代码检查点d388801b96f851a20e68d796db276c49f4aae586已commit/push，Git及native GitHub回读PASS。此回读随后保存到文档提交，当前最终branch SHA现场核对。main未合并，CI/安装不由push推断；155文件ZIP为修复前历史快照，保留但不重复打包。
5. 本轮正式额度used45%、剩55%，secondary UNKNOWN，未触发20%；准确观测边界读活动指针，监控aaos沿用原规则，无新功能授权。

## 1. 最新任务、授权与读取顺序

Owner最新要求：接手并对照“接手AAOS全链路执行”的会话、历史和权威审计漂移；结合审计修复更新任务、交接及实现，“全部按照新的UI进行打通”。采用已接收Stitch设计覆盖全部现有业务页面和共用壳，前后端同步并行接通真实消费者，统一验证。更早后端优先与前端先行顺序均为历史。保留TRAE及既有成果，独立组只在各自授权write set／提案目录写入，主checkout一个writer串行接收；不改Agent模型/provider配置。

先完整读取：`AGENTS.md`、`AUTHORITY.md`、`PROJECT_CONTRACT.yaml`、`docs/current/AAOS-ACTIVE-EXECUTION.json`、`docs/truth/CLOSED_LOOP_DEFINITION.md`、本文件、`docs/current/AAOS-FRONTEND-FIRST-EXECUTION-OVERLAY-20261019.md`、唯一执行记录。Task Grant以当前Owner原话、活动指针 `delivery_authorization` / `green_update_authorization`及冻结边界共同解析，未发现独立命名的Task Grant文件，不自行补造。

再读选中任务包 `docs/taskpacks/aaos-ui-first-20261009/` 的TASKPACK.md、TASKS.json、PAGE-PLAN.csv、FREEZE-REGISTER.md，补充前端/后端合同位于 `docs/authority/taskpack-20261013-frontend-ui/01-Frontend-UI/`、`docs/authority/taskpack-20261013-backend-host/`；读 `docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md`、`docs/current/AAOS-EXECUTION-BACKLOG-20261018.json`。UI-P/BE-P/RC-P是原任务的实施分片，不替换原ID或另建产品真值。

所有路径先查 `AAOS-资料索引.md`、`docs/current/AAOS-AUTHORITY-ROUTES.json`、`docs/SHARED_RESOURCE_PATH_INDEX.md`、`config/environment/capability-requirements.yaml`、`config/environment/external-resources-index.json`及具体manifest。文件缺失先查归档/ZIP成员，不猜路径或扫描Home/整盘。缺权威报告AUTHORITY_REFERENCE_MISSING。登记不是实际可用证明。

正式栈Tauri2/React/TypeScript/Vite，Rust Core唯一SQLite/CAS业务writer，Python隔离worker；保留普通Document/Block直接保存、版本/幂等/草稿/人类知识接纳边界。沿用DockWorkspace、ConsoleWindow、图谱和人物renderer，先读已有实现只补差距。不再搭壳、替换渲染器、另建能力注册中心或另起ASTRYN。

现有授权涵盖当前公开源码/文档的普通commit/push/PR，以及审阅和required exact-head CI合格后的正常merge；push不等于merge。不得force/reset/clean/改写历史。公开发布、私有材料外发、付费云模型调用、真实用户数据覆盖、未知共享进程终止未由设计接收授权。Green程序更新仅限 `D:\All projects\ArcheAxis.Knowledge.Green-x64` 且先满足资格/备份/停止/精确成员核验；本轮未更新Green。

Stitch只读：get_project/list_screens/get_screen/download_file；禁止generate/edit/delete/upload/apply/publish，不修改全局配置，不回显密钥，不重启其他会话。读取设计不是原型、宿主或产品验收。E:/F:默认禁访；不读凭据、私人原生会话/账号memory、浏览器认证。V01暂停，FT01—04及六项增量冻结；额度监控已由Owner后继明确授权并实际创建；按活动指针20%规则执行，不另建重复监控或据此启动无关开发。

## 2. 已承接工作与证据边界

本段由本会话可见指令、Git和项目回执梳理，不是私人原生会话逐字导出。完整旧交接已原字节保存在 `docs/history/product-loop-20261019/session-20261021-stitch/HANDOFF-BEFORE.md`，原位置见同目录MANIFEST；旧相对链接按原 `docs/current/` 解析，不据旧“前端先行”或“后端优先”覆盖当前全量并行接通。

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

新接手的最小动作：读现场 → 对照唯一执行记录中最新失败/授权 → 按当前Stitch全量UI24片与后端15片并行解决实际差距；若模型/云端等待Owner，继续独立矩阵/已授权消费者或安装失败定位，不造成功。无新变化不重建冻结/派重复审计/全测。

## 4. 已接收且本会话实测可读的 Stitch 来源与前端任务

项目 `AAOS Desktop Replica`，`10243059433218383839`；页面 `AAOS 交互整合版`，`206611daf7a948edb97ea60c7a7d8654`。另一会话外部交接目录 `C:\Users\ALEX\Documents\Codex\2026-10-18\codex-codex-ui-ux-work-lab\outputs\stitch-connection-20261021`，HANDOFF-AAOS.md/REPORT.md及明确列出的HTML/PNG/三个只读脚本已按精确对象复制保全，原件不动。

本会话2026-10-21T14:35:32Z起真实initialize/tools-list，核readOnlyHint及schema后get_project/list_screens/get_screen/download_file；八个HTTP响应成功，远端写入0、模型turn0。HTML97,811B SHA `8c9fba60a636ab8f9fdf9d5c1bb70dbf9dd32cba4961ade66f5aa5feb6f2ba18`，PNG2,757,978B/2560×2048 SHA `46c09bc4bc9428ae716f1159a8d263a78fce15d8b7fa856d3367ded2243f9e46`，实时下载与另一会话一致。截图实际查看，HTML1683行完整只读审查；没有执行脚本/加载外链。

项目本地快照及连接收据：`.project-local/artifacts/stitch-intake-20261021/live-read/`；原交接与脚本保全：同父目录 `received/`。公开导航、hash和比较：`docs/history/product-loop-20261019/session-20261021-stitch/README.md`、`MANIFEST.json`、`STITCH-COMPARISON.md`、`DESIGN.md`。原始设计/外部交接/运行收据保持ignored，不随公开Git上传。原生Stitch MCP会话挂载仍UNVERIFIED，本会话已证明替代只读入口可用，无须重启其他会话或重复配置。

必要刷新时先审查已保全的Read-Stitch.ps1/read_target.py/verify_stitch.py，再运行原交接或本地received中的Read-Stitch.ps1，`-OutputDirectory`给当前项目新审计目录，可`-MetadataOnly`避免下载。例：`& '.project-local\artifacts\stitch-intake-20261021\received\Read-Stitch.ps1' -OutputDirectory 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\artifacts\stitch-intake-next' -MetadataOnly`。密钥由入口仅传给自己的子进程，不打印/归档。不要直接执行verify_stitch.py主程序（其独立诊断入口会更新外部latest-verification）；Read-Stitch.ps1调用的是read_target.py，仅写给定目录。沿用既有Windows代理是客户端读取，非更改系统网络。

设计可取：星际环境留白、内缩研究主窗、右侧辅助资料/助手层级、底部应用内导航、证据选中/原文定位/冲突并列。冲突/缺口：固定桌面几何及无窄屏适配；只有5路由3设置tab；没有大地图/图谱及虚拟人物renderer；小栖只是文字窗口；connected=true/同步/解析/数量/学术结论属于模拟。不得直接替换现有React壳或把硬编码状态当真实业务。

前后端现已并行，全量界面按Stitch映射生产能力；先将研究/证据比较与右侧资料联动映射已有Core对象/权限/版本和现有组件，再保留大地图、内缩主控台、独立虚拟人物窗、现有图谱/人物renderer；拆分/标签/恢复复用DockWorkspace。必要短词对齐“小栖”，工程ID/结构/JSON归运行诊断。完整UI24项全部保留，截图的五个页面不缩范围。设计技能通用禁蓝/单强调色/持续动画等建议不覆盖Owner既定五主题、cosmic和减少动画要求；DESIGN.md是项目定制参考，不建立新的权威。

## 5. 与后端并行接通的完整前端24片

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

## 6. 与全量UI并行的后端15片

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

V01暂停，FT01—04及活动指针六项增量冻结，展示蓝图不激活运行。10/19停监控及旧15%均为历史；Owner 10/22明确新增的heartbeat `aaos` 已实际创建，ACTIVE、每30分钟，剩余≤20%先完成当前已启动可验证单元和清理，再停止新任务，整理会话/后续任务/交接并普通commit/push本轮公开文件，逐SHA核实双端。最新已记录订阅剩余69%未触发（2026-10-21T20:36:28Z读回），后续必须现场读回；UNKNOWN不是0。监控静默于未变化/无行动状态，只通知重要变化、完成、失败或需Owner处理；收尾后暂停等待明确恢复。原archeaxis删除not_found和未命名卡片身份仍是历史UNVERIFIED，不代表新aaos监控失败。ChatGPT账号记忆／个性化未确认同步；不上传私人会话原文、凭据或运行数据。

E:/F:默认禁访，读到旧脚本不构成进入许可。不扫Home／磁盘，不改全局账号、模型、provider、认证、网络或服务配置；路径登记不授予跨项目或私人数据权限。

## 10. 验证、交付和首次动作

先读canonical gate及变更风险，不默认全仓pytest或npm test。已知入口：项目.venv/Scripts/python.exe、scripts/runtime/dev.py、Windows scripts/ci/run_tests.ps1、Rust scripts/ci/cargo_test.bat（裸cargo可能缺MSVC）；前端manifest的build／tauri走scripts/runtime/frontend.mjs。每次核实际版本／入口，不新装替代环境。

回执示例：`.venv/Scripts/python.exe -B scripts/runtime/dev.py --run-id <唯一ID> -- <确切可执行文件> <相关参数>`，具体门禁以当前manifest为准。权限／锁／编码失败先分类，不改ACL／换身份绕过拒绝。产物.project-local/，公开脱敏摘要按现行目录记录并回链唯一进度，不能覆盖旧FAIL。

每分片写清原问题／预期／实测→必要修改→最小回归，阶段终验再跑规定门禁。全量必须定义边界、用例目标、核心业务／风险、未测；随机点击只探索，有价值问题转为可复现缺陷。截图保存并实际查看，不能仅凭无障碍树、首次基准或工具样例报产品通过。

状态PASS/PARTIAL/BLOCKED/NOT_EXECUTED/UNVERIFIED；证据NO_EVIDENCE/SIMULATED/SYNTHETIC/INTEGRATED/REAL。源码结构、本地单测、浏览器合成桥、真实Core、原生、安装、exact-SHA CI、Owner验收分别报告，失败／取消／required skip不算PASS。记录源SHA／patch、命令、时间、退出码、截图回执、未测与回退。

**当前首次接手行动（Owner 2026-10-21后继改序）**：先核现场Git/CI与唯一执行记录中的失败，读取[审计快照](../history/project-drift-audit-20261021/REPORT.md)及[本轮设计实施约束](AAOS-STITCH-UI-INTEGRATION-20261021.md)，修复已证漂移并按Stitch接通全量UI与后端；以同候选CL-01—07/J1—J6统一收口。保留既有前端与TRAE成果，不能以交接、局部浏览器通过或旧候选替代原生安装和Owner验收。结束核diff／status、自建PID与端口，更新唯一执行记录。

## 11. 补充必须交付：分支合并、体积清理与双端规范

Owner后继明确要求把“分支合并”“体积清理、本地和云端仓库规范化、目录规范化”一并纳入。详细分片第五节RC-P01—08规定逐项验收，继承G01／UF13／交付范围；先只读盘点，UI和后端供体按当前并行任务吸收，不能用整理代替产品接通或陷入无止境审计。

1. RC-P01 动态列本地与**实际远端**分支、PR、worktree、独有提交／修改与归属，保留所有未知脏内容。
2. RC-P02 比较未合入内容、patch等价／squash／cherry-pick、供体效果与冲突；非祖先不等于没吸收，不能盲合旧整包把旧权威带回来。
3. RC-P03 核PR192／193／194重叠，逐项定保留／后继已包含／拆分，合格审阅＋required exact-SHA CI后合入main并复验。不能只push不完成合并，也不能绕过失败强合。
4. RC-P04 合入并证实无独有内容、无占用后，按授权清理确切已合并本地／远端分支和已妥善处理的PR，读回；不删未吸收／未知分支、不改写历史。
5. RC-P05 分开量化源码工作区／tracked大文件／Git历史对象／构建缓存证据／云端CI产物和release，写时间、字节、归属、再生性，不把共享模型资料算可删缓存。
6. RC-P06 清理先列原路径／hash／大小／归档或替代／重建方法；保全独有原件、失败证据和有效回退，只处理核实项目所有且可再生／重复对象。压缩验成员和hash，普通删文件不等于Git历史减小，历史改写未授权。
7. RC-P07 按DIRECTORY_AUTHORITY.yaml和职责索引规范源码／合同／current导航／历史／供体许可／忽略运行产物，更新活动引用、查孤儿旧入口、原位不留第二可变副本，不乱搬不可变TaskPack。
8. RC-P08 分别读回本地／远端／main／PR／release身份和清理前后字节，公开源码文档才同步。云端artifact按证据价值、期限和精确授权处理，保留失败／待审候选；不改可见性、保护规则、付费存储或擅自发布。

本轮冻结对话归档校验使用维护入口：`.venv/Scripts/python.exe -B scripts/maintenance/verify_owner_dialogue.py --require-local-attachments`；冻结目录中的原校验器保留原字节，迁移由现行manifest解释，不复活退休路径。

### 2026-10-22 本轮接续定位

当前根分支`codex/sync-20261019`，基线`8d367bac4a85bebfbb523503678ade0838faa73e`；本轮新增Stitch全局菜单/八域Dock/独立小栖及全部22既有语义角色接入，研究证据/原文/相关材料联动、knowledge_get参数修复和漂移修复。实际验证、负例、Git交付状态及后续次序仅见唯一执行记录末尾本轮段；不要重复实施已接收提案，别将旧a63 Core子链、合成浏览器或本地build换称新候选原生完整闭环。

本轮最终本地验证已归入唯一执行记录2026-10-22段：前端190 suites/1996项、Python91项、生产构建、Stitch矩阵167项及完整A0均PASS，候选运行期间源码一致；证据层仍是本地组件/SYNTHETIC或SIMULATED_HOST_CORE_FIXTURE，不冒充新候选实际Core/原生/安装或exact-SHA CI。原失败保留，下一步按同候选CL/J缺口执行，不重复搭壳。Git交付以活动指针current_delivery_readback及唯一执行记录为准。

**2026-10-22交付阻塞**：当前平台将本仓库.git列为只读；普通逐路径git add实际返回index.lock Permission denied，首次49个公开文件未commit/push，后继实现后现为72个公开路径。基线本地/远端branch/main均8d367bac，但dirty工作未上传，不称双端一致。完整公开恢复包与hash清单在.project-local/artifacts/drift-audit-20261021/delivery/；不含私人或runtime数据。先在正常允许写本仓库Git元数据的环境核对现场与manifest再完成已授权commit/push，禁止提权、改ACL、换协议或远程半交付绕过当前限制。当前产品和同候选CL/J仍PARTIAL，阻塞不等于产品完成。

2026-10-22后继真实候选已完成：stitch-portable-current-01内新Stitch宿主f7689a33…/Core223da0b8…，构建绑定patch ba038f1e…、19482成员hash验证；同候选研究26请求及四格式内容/定位/重解析/重启子链PASS。精确命令、路径、hash与限制仅见唯一执行记录最新段和ignored stitch-current-candidate-chain.json。未执行新候选原生/安装/模型或完整CL/J；Git提交推送仍受.git只读阻塞。接续先补BE-P06/07、UI-P13的实际Obsidian嵌入呈现缺口，不重跑无变化的上一轮全量测试，不以生产已有目标解析替代实际呈现。


2026-10-22后继嵌入片已实现并定向验证：正式阅读/历史可读取固定Document/Block/Source嵌入，关系草稿勾选、旧关系精确升级及updated计数、严格合同/真实coreCommand/投影/portable已接通。唯一执行记录末段与ignored embed-integration-summary.json保存39领域/4HTTP/111前端/47桥接子集/142合同/生产构建及8项浏览器证据，负例和截图缺陷保留。只读固定快照区域≠原位排版保真或全面Obsidian兼容。上一便携候选不含本片，下一步按当前源码构建并资格同候选实际链，别重复已补实现或借旧包结论。当前72公开路径尚未上传，.git只读仍阻塞；公开恢复包已按最新文件刷新。全目标PARTIAL、额度监控aaos保持原规则。

### 2026-10-22 最新接续：嵌入实际运行与独立恢复

当前可用候选是.project-local/runs/be268a2d33/embed-portable-candidate-02/artifacts/星环便携候选（宿主8ebbc340…/Core8e61bf49…，构建patch5d13833f…，19482成员）；不是旧stitch-portable-current-01。固定嵌入真实Core49 HTTP、独立完整备份恢复及最终构建UI16实际读取已PASS，标题工程文案已修复、相关17回归通过，截图实际查看。API49在前一嵌入包执行，最终包仅宿主变化，19481后端成员逐manifest相等；原生窗口/安装/模型和完整CL/J仍PARTIAL，不拼作全闭环成功。图谱基线错误的首次FAIL、未覆盖标题的浏览器PASS和标题真实RED均保留。

唯一执行记录最新段与ignored embed-current-candidate-chain.json保存精确命令入口、hash、证据层和自有进程/端口清理。下一步用此候选做必要的研究/多格式/知识学习贯穿，随后继续全面兼容矩阵及CL/J实缺；不重复搭壳、嵌入或无变化全量测试。现73公开路径未commit/push，.git只读未解除；最新普通远端读回exit128，native只确认分支名无SHA，旧8d367bac远端观察不冒充当前。公开恢复包已刷新逐成员验证，运行库和私人原文不上传。额度18:28:51Z剩余72%未触发，aaos继续原阈值规则。

### 2026-10-22 最新接续：同工作区研究／四格式／知识学习与UI修正

当前候选已前进至`.project-local/runs/be268a2d33/learning-radio-portable-01/artifacts/星环便携候选`：宿主`cb981daca66921d6d8bfff86b4b87ffe5beab303ea9823f6e4eb4e35f83a8dbc`，Core仍`8e61bf4901367da6b69de36197114760f8204ee99b41ea301c7fc43e380e02ad`，构建patch`eef3a3ac19010e831d0b828ce0095a3d1f31df8c856182b90837afe2ca1e76a2`。19482成员已资格，19481后端成员与上一嵌入候选逐manifest相同，只改宿主。旧候选及失败均保留；本段替代上一段的“当前候选”定位，不改写旧测试时点。

`aaos_research_learning_runtime.py`在同一隔离工作区接入四格式自编资料、实际社区／科研来源及原始API响应共8原件、公开未接纳候选、仅合成个人定义的模拟人工接纳、FSRS练习、研究及固定知识嵌入；103次实际HTTP、重复提交与409、重启及独立完整恢复逐值回读PASS。公开知识一直为candidate，未做真实Owner／专业接纳。该103次在上一相同后端候选执行，最终候选的正式构建UI又做29次实际Core读取，并打开校验公开原文、知识嵌入和实际学习项；原生壳／工作状态／租约仍模拟，不能写成Tauri IPC或安装验收。

公开检索两次实际FAIL/partial保留：百科分别offline/network_unavailable与failed/transport_or_policy；首关键词社区为空、科研只有元数据，改用历史有效`spaced repetition`后社区与科研有实际内容，百科仍失败。未将局部继续改称三类全通或完整J2。实际截图另暴露学习单选框宽816px、圆点与文字分离；仅`ui-first.css`两条局部规则修复，最终1440×1000和640×480均16px单选框／44px标签，点击与方向键通过，实际学习历史未变。新候选首次浏览器误等局部原文区，实际原文走全局固定引用且已200；修测试定位后PASS，不算产品修复。首次lint未用import失败，删除后定向Ruff PASS。

精确入口、回执hash、截图和清理见唯一执行记录末段及ignored`research-learning-current-candidate-chain.json`。下一步在这些同源对象上补“已接纳合成知识→实际课程候选／正式课件→正常课程练习入口→重开／恢复”，不要只依赖本片手工构造学习key；随后继续百科可达性及现有软件×版本×特色×方向矩阵、本地／云端模型、原生／安装／Owner等CL/J实缺。未跑无变化的1996项／167矩阵／完整A0，不因额度未触发而缩减最终目标。当前75个公开路径未上传；Git只读与远端SHA未刷新仍阻塞交付。约18:59Z正式订阅读回仍剩72%，aaos未触发；公开恢复包随本次文档刷新，私人／运行资料不上传。

### 2026-10-22 最新接续：课程正常入口、独立恢复与额度规则

本段替代上段“当前候选／下一步课程”定位。当前候选为`.project-local/runs/be268a2d33/course-dock-portable-01/artifacts/星环便携候选`，宿主2c0a9244fd0f6744c804d24e25542a3cb69a5be1604a1f2e59c11cd533ac866f，Core仍8e61bf4901367da6b69de36197114760f8204ee99b41ea301c7fc43e380e02ad，构建patch e5056ba2a23cfe372142e9cba8f0221a8d946ea816f50af0449e12989a0f43a0；19482成员逐成员资格，只有宿主相对上一包变化，19481后端成员相同。原候选及失败保留，文档后续patch不等于构建patch。

新公开入口`aaos_course_continuation_runtime.py`从已有独立恢复的合成工作区接续67实际Core HTTP：未接纳公开知识生成课程409，合成已接纳个人知识生成课程／native-lesson、Core返回学习身份／原题、FSRS幂等事件、8原件与旧研究正文经重启和独立完整恢复均一致。公开知识与课程仍candidate，合成人工判断不代表Owner或专业接纳，不重跑已有联网／四格式／103链。

真实浏览器首次FAIL暴露Dock06／07分宿主导致课程选择留在隐藏页面；Dock回归红1FAIL/22PASS后，仅PanelRegistry一行合并此业务会话，5套81项回归PASS。新候选正式构建UI＋实际Core的33请求，课程列表→课时→建立原问题→11练习→返回固定课程→关闭，截图已看、历史／正文未变、自有进程与服务回收PASS。存在严格绑定合成对象的幂等reference／assessment写入；不是33次纯读，也未写复习成绩。宿主IPC／工作状态／租约仍模拟，原生、安装、Owner和全CL/J仍PARTIAL。详情、负例和hash只路由唯一执行记录末段及ignored`course-continuation-current-candidate-chain.json`。

下一步继续全面兼容矩阵、百科可达性与格式质量等CL/J实际缺口，不重做课程或无变化全量门禁。本地模型最终答案、云端配置／费用／材料授权、原生／安装／Owner及exact-SHA CI仍未资格。当前78公开路径未上传，.git只读的index.lock拒绝仍阻塞普通commit/push，远端SHA未刷新，不能称双端一致；恢复包在文档更新后重建校验。现有aaos heartbeat已核为ACTIVE、每30分钟、≤20%完成已启动单元后停新任务并交接上传核SHA，随后暂停等待明确恢复；19:14Z附近正式剩余71%未触发。禁止私人原文／凭据／运行库上传和权限绕过。

### 2026-10-22 最新接续：扫描全文质量与70%额度观察

最新增量为`aaos_chinese_scan_quality_runtime.py`与chinese-scan-quality-01：两页冻结自造中文真值，实际Core/OCR处理PNG、JPEG及双页无文字层PDF；四结果去空白CER为1.5152%/3.1496%/1.5152%/3.9370%，原始CER20%—20.7407%，保留标点宽度差异。工程样本门槛PASS不代表自然扫描总体准确率或Owner接纳。重启/独立完整恢复后识别、原件及原课程/研究/学习对象相等；自有Core已回收。当前候选与前段course-dock-portable-01相同，未改产品构建或共享OCR配置。详细回执由唯一执行记录和ignored`chinese-scan-quality-current-candidate-chain.json`路由。

下一步核实扫描来源在正常UI的原件、持久化OCR与定位消费；目前只有源码观察，未确认UI缺陷。其余CL/J缺口、冻结及发布边界沿用前段。监控aaos经API复核ACTIVE，每30分钟；19:38:47Z正式剩余70%，未触发≤20%收尾规则。当前79公开文件未上传，Git元数据只读阻塞已授权commit/push；恢复包在本文之后重建，双端一致尚未达成，权限拒绝不得绕过。

### 2026-10-22 最新接续：扫描原图阅读修复与新候选

本段替代上一“当前候选”定位：`.project-local/runs/be268a2d33/scan-preview-portable-02/artifacts/星环便携候选`，宿主5b86c89e643773d29d7ae5114aee6033b7da5e6f5ee926e72e97f6c19a0a23d8，Core仍8e61bf4901367da6b69de36197114760f8204ee99b41ea301c7fc43e380e02ad；构建patch a3d33a801d9be196e68a97344747d1c64ef7063983a92805c418e19604fcb0fd，19482成员资格PASS，相对课程包仅宿主变化。后续文档dirty patch不冒充此构建patch。

实际旧候选UI45次读取后暴露03页在来源尚无Document时不显示扫描原图。红4FAIL/1PASS后，仅CanonicalLibrarySpace复用已校验来源预览，新增CanonicalSourcePreview定向回归；5套35项和最终5项PASS，测试类型参数错误导致的首次tsc失败已修正并保留。新构建正式UI+实际Core的88次GET验证PNG/JPEG原图字节、保存OCR与切来源、扫描PDF两页翻页，原研究/学习历史未变、自有进程/端口回收PASS，8图已看。自动滚动截图存在部分原图被页签遮住；640×480只核了图片宽度，未把它称为完整窗口可用性。壳/工作状态/租约仍模拟，原生/安装/Owner/CI仍未资格。独立全文质量仍沿前片原证据，不修改OCR或全局配置。

精确入口/hash/负例与限制读唯一执行记录最新段及ignored`scan-preview-current-candidate-chain.json`。下一步补OCR定位的实际阅读UI消费、完整视口/键盘，再推进其余CL/J实缺；不重复无变化全量测试。当前80公开文件未上传，Git元数据只读阻塞与旧远端SHA状态不变；恢复包随后刷新。额度仍沿19:38:47Z正式剩余70%的已记录观察及ACTIVE的aaos监控，完整闭环PARTIAL。

### 2026-10-22 最新接续：OCR固定引用到原图定位与监控读回

本段替代上一“当前候选/下一步OCR定位”路由：.project-local/runs/be268a2d33/ocr-location-portable-01/artifacts/星环便携候选，19482成员/694698894逻辑字节；宿主ba5267dec4bae833434b9cfa98f6ca22fcc38f7ed047fe7490e6a33248272e4b、Core仍8e61bf4901367da6b69de36197114760f8204ee99b41ea301c7fc43e380e02ad，构建patch55cfa8b5bf6160d3ffe9fd0faaad5fe30397c6e547de904b114d12b73fe3bee6。正式tsc/Vite/Tauri及资源闭包、便携逐成员资格PASS，相对扫描预览包仅宿主变化。文档后改不等于构建patch，未执行新宿主原生/安装资格。

新增OcrImageReader与ocrReference，读取已保存引用的固定job/attempt，核来源版本、定位、三项制品hash、Unicode码点文字及坐标，再次核CURRENT；不回退最新job，不新增业务真值。保留旧UI无入口、切来源旧读取、首次高亮越出视口等FAIL，定向修复后最终10项组件PASS。scan-location-final-ui-01在最终候选实际Core+对应正式UI完成75次GET：PNG旧固定引用原文/区域、桌面及640×480引用可见、Enter/Tab、正常菜单切JPEG后旧高亮清除/新位置正确；三图实际查看，原研究及学习历史不变、自有进程/端口回收。壳/工作状态/租约仍模拟，证据INTEGRATED_REAL_CORE_WITH_SIMULATED_HOST_TRANSPORT，不称全窗口/无障碍/原生/安装/Owner/CI完成。详细负例、hash与限制只读唯一执行记录末段及ignored ocr-location-current-candidate-chain.json。

下一步先核扫描PDF父来源→OCR页子来源→普通阅读定位，再继续现有兼容矩阵、百科、模型、其他能力形态及J6实缺；不要重做PNG/JPEG位置或无变化全量检查。CL-01—07/J1—J6仍PARTIAL。84公开路径未上传，Git元数据只读阻塞授权commit/push，远端SHA仍旧观察，双端一致未达成；公开恢复包在最终文档后重建。aaos已现场读回ACTIVE/每30分钟/完整20%规则，不重复创建；最新正式额度观察20:06:32Z剩70%，未触发。收尾上传范围仅公开任务源码与脱敏文档，不含私人正文、凭据或运行库，拒绝不得绕过。

### 2026-10-22 最新接续：扫描PDF正常逐页阅读与刷新并发修复

本段替代上段“当前候选/下一步PDF页链”路由。当前候选.project-local/runs/be268a2d33/pdf-page-portable-final-01/artifacts/星环便携候选，19482成员/694699406逻辑字节；宿主e5526895502bfab937d0c317c472f414ec525c30f348e6004ff713e02eebf423、Core仍8e61bf4901367da6b69de36197114760f8204ee99b41ea301c7fc43e380e02ad，构建patch c026290e411e392f2bd18064ed5c0ca777acccaa4ba806fbe6661c80283b762c，正式构建/资源闭包/逐成员资格PASS，相对上一OCR图片包仅宿主变化。后改文档不冒充构建patch。

旧UI39GET复现03阅读页缺少逐页识别消费者。仅复用既有PdfPageRecognition与OcrImageReader：逐页正文、页图实际SHA/引用版本核对、双向父PDF页同步、切页清除旧高亮、固定job/attempt及迟到丢弃。首轮正常UI66GET通过后，复审新增刷新并发回归1FAIL/16PASS，修复请求释放条件；最终四套37项PASS。最终候选Core+对应正式UI68GET通过，两页原文/页图/固定区域正确、父PDF实际像素改变、640×480目标区域可见；故意延迟真实页清单响应后翻页，旧响应丢弃且刷新恢复/可重读。三图已实际查看，原研究/学习历史不变，自有进程/端口回收。证据INTEGRATED_REAL_CORE_WITH_SIMULATED_HOST_TRANSPORT，壳/工作状态/租约及延迟注入模拟；不称自然扫描质量、完整窗口/无障碍、原生、安装、Green、Owner或CI合格。详情及负例/hash只读唯一执行记录末段及ignored pdf-page-ocr-current-candidate-chain.json。

下一步转现有软件×版本×特色×方向矩阵的实际消费者缺口，继续百科/双模型/其他扩展/完整J6，避免重做扫描PDF或无变化全量测试。CL-01—07/J1—J6仍PARTIAL。86公开路径未提交/上传，Git元数据只读阻塞不变，远端SHA仍历史观察；最终文档后重建公开恢复包，不能称双端一致。20:36:28Z正式剩69%未触发≤20%，沿既有ACTIVE aaos监控完成已启动单元后停新任务/交接上传核SHA规则；私人原文、凭据、运行库不上传，权限拒绝不绕过。


## 2026-10-22 接续导航：保存版集合阅读与最新候选

本段替代前段当前候选/下一步集合消费者路由，实际进度仍只在唯一执行记录。当前候选.project-local/runs/be268a2d33/collection-reader-layout-portable-final-01/artifacts/星环便携候选，19482成员；宿主25f05b3f202291569a9855a4f537d50c62f259136bf8b7c4d99296a3301eb303、Core8e61bf4901367da6b69de36197114760f8204ee99b41ea301c7fc43e380e02ad，正式构建a00a8d95c177/patch 1bd638c5af6341c8f110ab4aa998af11024b7989efbddc3c35661793d28c5e42及资源闭包PASS。后端19481成员与PDF候选相同，仅宿主改变；不能借此宣称所有前序链在新source重跑。

正常02→03与历史/兼容入口复用CollectionPanel reader模式，固定保存版本读取原Core的五种视图/筛选/排序/公式/分页，并打开固定记录引用。受控编辑与Document唯一保存链不变。先8项RED，最终四套51项PASS；实际Core51HTTP在独立自造集合库完成26条、20+6、过滤5、公式、v1引用/v2当前、重启和独立恢复。中间34GET数据PASS后实际截图发现306px编辑器重叠，追加真实浏览器RED24GET，再修CSS固有高度，不能沿用旧34GET冒充布局合格。最终34GET/六视图几何、窄画廊及固定v1通过，最终三图已查看；Core/浏览器/端口回收，原研究/学习/集合不变。证据为真实Core+合成host transport，非原生IPC/安装/Owner/CI。API及只读浏览器探针已公开，完整参数见各自wrapper execution.json；ignored汇总collection-reader-current-candidate-chain.json绑定回执hash和负例。复跑用独立新run，不改冻结输入库。

兼容种子仍REQUIRED_NOT_FINISHED；外部软件版本和方向矩阵未取得完整资格。日期视图是原有日期分组，不称完整月历/拖拽；标签与跨文档集合导航仍欠。下一片先从现有矩阵选择具名真实消费者，继续百科/双模型/扩展形态/完整J6，不重复已通过集合或PDF全链、不新建平行业务真值。整体CL/J仍PARTIAL。90公开任务文件待同步，.git只读/既有index.lock拒绝不绕过，不能称双端一致。21:06:37Z正式剩68%未触发≤20%，既有aaos每30分钟监控已回读；触发后完成当前单元/清理再停新任务，交接并普通提交上传公开任务文件、核双端SHA，收尾后暂停等Owner恢复；私有原文/凭据/运行库不上传。只回退本片hunks，不批量restore/删库/替换Green。

最终仓库约定检查collection-reader-conventions-final-01发现本轮PowerShell内Python默认换行写入造成4文件CRLF，已按exact四路径转回LF；转换前后git binary patch SHA相同、逻辑内容逐字相同，未改变构建语义或重跑产品构建。原FAIL保留，后继final-02门禁另存；ignored collection-reader-lf-normalization.json记录各文件计数及不变证明。


## 2026-10-22 最新接续：集合发现已接入，当前监控有效

后继进度以唯一执行记录末节为准。02“集合文档”与侧栏入口已按新壳接入真实保存文档摘要，再按实际ID进入03保存版集合。Core派生可选has_collection与当前保存version/SHA同行；旧生产者缺字段是UNKNOWN，分页/错误/标题筛选不能误报全库为空。未新增业务存储或另一套编辑器，标签导航和完整日历交互仍未完成，软件×版本×特色×方向矩阵仍REQUIRED_NOT_FINISHED。

最新可验证单元：前端27、Core8、合同61通过/77未选中；正式构建2e3a379e7d3f，source patch f90deb7684c2284618a11d8e4137134bb93118e27e8af27c4c6cf5862fe71efc，host37ea0abe82fa3a585acaf78f4e1522cd6e30359ccf3e37be46499d0fd0fb2a24，Core26c45f4338d448e7dedc45acc51634d317b2e8dc1d219c463f4036d4cb91f282。collection-discovery-portable-01候选19482成员/694702990字节，实际Core52请求验证标记无→有→无、历史版本、重启/独立恢复及前片对象保全；真实Core+模拟宿主浏览器34GET验证02→03、六视图/固定v1/窄画廊，四图已查看。三个Core及浏览器自有Core均reaped，但terminate码1、不称优雅退出。02截图可见模拟布局快照LAYOUT_DTO_INVALID: Snapshot；消费者证明不代替整页/原生/安装/Green/Owner/CI验收。

本轮失败保留：RED0测试过滤无效、真实RED失败、合同投影过期阻止启动、新旧暂存Core不符阻止构建、34d083f622ff测试参数TypeScript失败；均有后继定向修正。暂存仅在项目.project-local生成区可逆切换，旧包保存collection-discovery-stage-01/artifacts/previous-runtime，data均空，staging-switch.json记录；CIM盘点UNVERIFIED，没有权限绕过/未知进程终止。此前PDF/OCR/学习等候选仅保留各自原资格，不借新SHA升级全部旅程。

监控已回读：aaos ACTIVE每30分钟，21:41:34Z剩余67%（used33），未触发≤20%。触发时先完成已启动可验证单元及必要自有清理，停止新任务，整理会话决定/失败/后续顺序与完整交接，正常commit/push公开任务文件并核本地远端SHA；未知额度不算0，私人原始会话/凭据/运行库不上传。收尾后停止并暂停监控，等Owner明确恢复。Git元数据当前只读、先前index.lock拒绝，未重试/提权/绕过；公开恢复包位于.project-local/artifacts/drift-audit-20261021/delivery/，每次最终文档检查后逐成员重建并以MANIFEST.json为准；当前94个公开任务路径，不得称已上传或双端一致。

接手从本节和唯一执行记录继续，不重跑已证无变化全量测试。先选下一个真实兼容消费者并补现有具名软件/版本/特色/方向矩阵，再处理百科、双模型最终答案、其他扩展及完整J6；沿用既有待决与授权边界。整体CL-01—07/J1—J6为PARTIAL，未完成目标，不因本片通过结案。


## 2026-10-22 最新接续：兼容矩阵已有现行入口，下一步接真实标签消费者

现行CL-04/J3矩阵为docs/current/AAOS-KNOWLEDGE-COMPATIBILITY-MATRIX.json（活动指针resource_navigation及职责/路径索引已连）。它沿冻结种子保留35平台及全部原发现维度，不修改历史；35不是全部市场软件上限。10个官方文档为其中六类补18项具名检查，其余29类未开始，所有软件/方向仍须版本化实际资格；两份AAOS集合自造材料回执只是独立观察。不要把原种子route_verified、官方文档、CommonMark规范、Notion API示例版本、API v3或本地消费者当真实外部软件兼容。14能力轴、五方向与源/目标版本未知完整保留，不把企业排除扩成整个软件排除；整体inventory_complete=false/CL/J PARTIAL。

新增现有文档门禁检查漏项/种子改字节/误报通过/私人路径，定向27测试通过，负例见唯一执行记录最新节；缺ignored回执时CI只报UNVERIFIED，不借本地资格。本片仅验收库存/检查器/导航，没有产品代码、依赖或候选更新，不重跑前一候选构建/全量产品测试。pyreadline3退出析构异常保留为终端清理现象，未改全局环境。

下一片完成Obsidian/Markdown标签与属性的实际02/03消费者；先核已导入原件→保存版Document中原样内容/属性，再处理行内与tags属性、代码/转义/URL假标签、Unicode、嵌套/大小写、保存/重启/导出损失，沿现有writer和草稿/版本围栏。不能用另一份前端临时标签数组作业务真值，也不能把普通全文检索当标签语义。标签之外的原35平台特色继续发现，百科/双模型最终答案/扩展/完整J6仍缺。监控aaos每30分钟，最新正式读取仍21:41:34Z剩67%未触发，未追加轮询或新监控。

当前97公开任务路径仍未commit/push，.git只读及已记录拒绝不绕过；恢复包仍只在.project-local/artifacts/drift-audit-20261021/delivery/，按最终MANIFEST核成员及hash，不称双端一致。保留所有原候选与失败，不替换Green或真实资料库。


### 2026-10-22 最新接续：保存版标签／属性与同文档重开修复

本段替代上段“下一步标签”及当前候选定位；完整CL/J仍PARTIAL。当前候选.project-local/runs/be268a2d33/document-tags-portable-03/artifacts/星环便携候选，host 9891880b9150b0a30c7d0bb173e3b148ea556b55f76ceac7f98e1583224fe210，Core 38aef8f51d6addbd28392ca09556349bfb4d2bce02f15c0f5cb887ef4a3248ff，构建patch d1c193d600974af87571b8766e519676bc20b76e28fe831e8a06a86efd9c0808；19482成员／695183758逻辑字节资格PASS，相对首标签包19481后端成员相同，旧集合包Core不同。最终真实Core57HTTP与正式构建UI29GET通过，覆盖02父标签筛选→03保存属性／实际关联→API保存v2→正常列表刷新和重开v2→v1历史、导出／portable／重启／独立完整恢复，原研究／课程／学习对象保持。3图已看，窄屏仅标签区域／视口和横溢核验；壳、工作状态、租约与布局模拟，材料自造，不称原生／安装／Owner／外部Obsidian兼容／全CL/J完成。

实现复用固定版本Markdown、YAML和Unicode库，在原不可变editor上只读派生，Rust仍唯一writer；没有标签新库／写入通道，来源许可及缓存边界见intake和SUPPLY_CHAIN_LEDGER A051—A053。无效／超限元数据明确PARTIAL，保留原文；摘要16KiB截断不影响完整文档标签。02已加载文档筛选、03属性／标签关联和历史已接通，完整属性编辑／批量改名／全库索引及真实外部软件版本往返未完成。导出原frontmatter优先且显式记录投影损失。

首次真实验证36HTTP仅同hash跳转未刷新列表FAIL；第二次38HTTP发现列表v2但保留reader同ID停在v1的实际产品缺陷。首次激活修复仍在runtime-03 FAIL（02／03共享宿主没有激活事件），补共享页面角色切换RED后，干净文档在重新激活或重新进入阅读角色时重读，脏草稿／写入不覆盖；最终领域9、HTTP17、合同138，以及最终界面／草稿／Dock六套58项PASS，重叠不相加，各自patch保留。索引超时取消、旧断言失败／manifest投影未刷新与首次清理观察均保留。只跑定向检查，精确命令／收据hash／截图／cleanup由唯一执行记录及ignored document-tags-current-candidate-chain.json导航。

后续继续兼容矩阵其他具名软件／版本／特色／方向、真正外部往返，以及百科、双模型最终答案、其他扩展形态和完整J6；不重做标签或无变化全量门禁。监控aaos已核ACTIVE每30分钟，≤20%完成当前已启动可验证单元后收尾停止，写全会话／后续／交接、上传公开任务文件核双端SHA再暂停等Owner恢复；22:58:28Z正式剩余65%未触发。当前109公开任务路径未上传，.git只读仍阻塞授权commit/push，旧远端SHA非当前一致；恢复包文档后刷新校验。禁止绕过Git权限、私人原文／凭据／运行库上传、自动merge／发布／Green替换。

2026-10-22 Owner再次确认监控规则：复核既有aaos为ACTIVE、每30分钟，未创建重复任务；2026-10-21T23:07:14.338Z官方订阅窗口used36%／remaining64%，NOT_TRIGGERED。当前上传与双端一致仍为BLOCKED／UNVERIFIED，保留本地公开任务恢复包；只读Git权限未解除，不因监控承诺上传成功。活动指针已记录本次实测，历史观察保留。


### 2026-10-22 最新接续：当前候选三类公开来源与界面贯穿复验

本段接续标签／属性，替代“当前候选百科尚未取得实际内容”的旧缺口描述；候选仍document-tags-portable-03，host/Core及成员不变。当前仅显式进程级ARCHEAXIS_PUBLIC_RESEARCH_PROXY=http://127.0.0.1:7890（既有登记路径）执行公开关键词spaced repetition；没有改系统网络、CA/TLS、默认provider或安装配置。旧失败记录漏传该选项，本轮不再次盲试direct。三类都返回complete且有摘录／正文和原始响应：Wikipedia Spaced repetition、Academia Stack Exchange问题、OpenAlex论文摘要；不是完整网页或全文通用承诺。

当前42实际Core HTTP完成六份原始／派生来源、固定引用／位置、研究草稿保存、重启、package/export及备份预检；新Core不沿借旧格式资格，再执行四种小型自编DOCX/XLSX/PPTX/文本PDF内容／位置／重解析／重启，约30秒通过。随后110请求贯穿三类公开来源与四个人工编写资料、个人定义的模拟工程接纳／FSRS幂等及冲突、公开知识candidate保留、重启／备份／独立maintenance restore逐值回读通过。未独立核验公开论断，未将公开候选自动接纳。

新增可公开复跑入口scripts/probes/aaos_research_learning_browser.py，在现有正式构建dist及同候选／恢复库上36实际读取（含只读POST list/read），05恢复原请求不重搜、三类状态与结果、三类固定原件和百科原API、03公开candidate／个人知识嵌入及06复习／键盘通过；五截图已实际查看。壳／IPC／布局／租约／工作状态存储均模拟，工作状态scope仅取实际Core；界面顶部草稿告警由模拟持久化围栏保留，不冒充原生工作状态合格。材料数动态读取，避免旧10项断言漏掉百科；runtime probe已移除写死“百科失败”的错误描述，完整／部分状态分别记录。

路径：.project-local/runs/be268a2d33/tags-public-research-proxy-01/artifacts/public-research-receipt.json；四格式内层a452b86f672e/artifacts/common-formats.json（外层tags-common-formats-01）；tags-research-learning-01/artifacts/research-learning-runtime.json；tags-three-public-browser-01/artifacts/real-research-learning-browser/receipt.json。以上均在同runs根；精确输入／命令／hash、五图、清理和负例由.project-local/artifacts/drift-audit-20261021/three-public-current-candidate-chain.json导航。公开API42步／贯穿110步／浏览器36读取分开计，不当独立质量、完整J2或全部CL/J验收。所有自有Core terminate/wait已回收（returncode1，非正常优雅退出），浏览器与server端口退出，候选未变。

本片只改验证入口与文档，不重构产品／重复构建／全量测试。下一步保留安装态显式网络通道配置／默认direct实测、独立比较质量及知识人工判断、本地与云端分别最终答案、35平台版本／特色／方向及外部往返、其他扩展形态、同候选完整J6。百科在本受控路由下的实际内容已证，不再重复把它列为“没有通道”；安装态无自动代理配置仍是实际限制。完整CL/J继续PARTIAL，未更新Green。

当前110公开任务路径未commit/push，Git只读阻塞未解除，双端一致UNVERIFIED；本地恢复包按最终manifest核验，不上传私人原文／凭据／运行库。额度沿23:07:14.338Z正式剩64%的观察，aaos ACTIVE每30分钟；≤20%收尾停新任务规则保持，不因本片另外创建监控。

### 2026-10-22 最新接续：FAST本地最终回答与额度监控复核

接续上一节：同document-tags-portable-03候选未变，已在独立maintenance-restored验证库，以实际OpenAlex摘要完成本地FAST固定版本提问。新增config/model-profiles/lm-studio.json的fast-local（qwen3.5-4b／aaos-fast-4b，4096上下文、单并发、显式GPU ratio1、TTL1800）并逐项有效加载读回；既有deep-mtp及Agent/provider/global设置未改，没有替换已有实例。产品material/fast绑定只保存于该验证库，真实用户工作区未覆盖。

公开复跑入口scripts/probes/aaos_local_material_model_runtime.py；首答案worker71.17秒，作者补充范围约束后v2答案42.4秒，均取得content最终回答、stop且未截断，仍candidate且不授予知识接纳。fast-public-material-model-01保留首成功后probe路由错误HTTP405；02保留规范化block attrs比较错误、无新推理；03以--resume-receipt恢复01原请求，不重推首题，36实际HTTP完成第二答案、导出、v1/v2、重启及原研究／公开candidate／学习不变，wrapper LOCAL_PASS/source_consistent=true。精确hash、输入／负例／清理见.project-local/artifacts/drift-audit-20261021/local-fast-current-candidate-chain.json；两个自有Core已terminate/wait回收，非优雅宿主退出；LM Studio实例保留显式空闲TTL。

该子链为REAL_LOCAL_CORE_WORKER_MODEL_PUBLIC_MATERIAL，未独立判定模型质量，不是完整CL/J、deep／云端、原生UI或安装验收。后续保留cloud真实实现／所需授权、deep及模型比较、纠错和人工知识判断、默认网络与安装配置、35平台版本／特色／方向及外部往返、其他扩展和完整J6。不要重做已证三类公开来源／标签／本地FAST，也不能以新摘要试验缩减整体目标。

Owner本次监控要求已核：既有aaos ACTIVE每30分钟，≤20%完成当前已启动可验证单元后停新任务、整理会话／后续／完整交接、上传任务所属公开文件核双端SHA再暂停等明确恢复；64%正式剩余未触发（23:30:25Z—23:32:35Z测量）。当前113公开任务路径仍未上传，Git只读阻塞未解除，双端一致UNVERIFIED；delivery恢复包已逐成员校验，私人原文／凭据／运行库不上传，不重复创建监控，不绕过权限或替换Green。
