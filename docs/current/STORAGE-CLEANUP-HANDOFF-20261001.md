# ArcheAxis 清理与交接（2026-10-01，持续更新）

## 状态与授权

PARTIAL，目标仍 active。用户授权审计后删除无用项目输出、迁移有用资产到归属目录；禁止访问E/F，保护C/D系统软件、私人Agent状态及用户修改。完成条件是没有剩余已确认可清理项、项目关联性与所需验证通过、全部允许上传的源码/摘要/交接提交并回读远端SHA。本文件不是完成声明。

## 当前已执行结果

累计净逻辑文件载荷减少58,561,935,343 B（58.56 GB），含本报告执行链50,785,967,017 B及此前两轮7,775,968,326 B。删除源58,819,028,191 B，保留恢复载荷8,033,061,174 B，二者差额是本报告执行链净值。不是物理磁盘回收统计；少量审计收据和脚本不计。

最新元数据可访问范围（2026-10-01，runtime旧副本清理和双树编译后）：Formal24,742,074,220 B/346976files；Green9,552,880,455 B/114621files。分别491/40读取错误，private/Git与链接排除，不能等同Explorer全目录体积。按各根内NTFS文件身份去重，Formal逻辑载荷23,659,032,275 B、可读分配24,007,872,320 B；Green逻辑载荷7,367,135,312 B、可读分配7,513,395,240 B。跨根硬链接未归因，两个根各有1个allocation读取错误。近期编译恢复与验证生成的新输出已计入本次快照；累计删除账本不代表实时目录净变化。

最新三项实际清理：历史mono候选1195文件净169,743,568 B；历史worker Lib7548文件净182,288,299 B；runtime-copy2 17948文件净363,612,342 B。完整ZIP CRC/SHA、精确集合与fresh源核对后删除，原根不存在，恢复和保留证据SHA读回通过。

另有Green SDK5577文件/814目录807,336,133 B迁到 `D:\All projects\OS External Configuration\10-toolchains\dotnet-sdk-10.0.401`，全量哈希相同，原副本不存在。SDK10.0.401/Runtime10.0.12读回，既有10.0.400保留。只迁所有权，净磁盘载荷减少0。没有改变PATH、ACL、注册表或系统服务。

## 恢复边界

恢复载荷和详细收据保留于 Formal `.project-local/mig/storage-cleanup-current-20260930`，不得上传缓存或私有运行时正文。

- 新候选增量恢复依赖父包 `ui-history-direct-packed-20261001.zip` 与 `staging-ui-delta-packed-20261001.zip`、proof、helper及zip_cas边界依赖；父包仍有引用，不得删除。
- 历史mono使用 `aaos-ui-theme-candidate-packed-20261001.zip` 与manifest。
- worker Lib使用 `worker-bootstrap-lib-20261001.zip` 与manifest；三个支持元信息原件保留。
- runtime-copy2使用 `runtime-readonly-copy2-recovery-20261001.zip` 与mapping，按精确source映射还原，不将邻runtime-copy当完整等价副本。
- 其他批次恢复方式见历史清理报告；原始执行收据保持原SHA和原失败/dirty语义。

任何恢复都禁止覆盖现有文件，逐文件SHA核对；先恢复依赖对象库再重建旧ZIP。若回读不完整，保留恢复包并停止该范围继续删除。

## 验证与未完成

项目既有开发路径、外部工具链、Green manifest、scheduler launcher定向synthetic契约：首次34pass/2fail/9subtests，2项WinError206长路径；短run-id重跑失败两项2pass。两次收据保留。SDK CLI不是产品运行验证。实际安装态产品启动、用户数据库健康、全部源码受影响验证、最终上传/远端回读仍未完成。

剩余大缓存与历史构建正在逐项确认。三个alternate pytest目录约713MB缺整体原始结束收据并包含排除的私人命名项/链接，不具整根删除资格。未知归属All/WAL/SHM/lock、C/D END、历史数据库世代、当前默认及注册worktree输出、具有依赖引用的缓存保留。三个批准执行身份仍拒绝的WinError5范围约29.43MB保留，不改ACL。无引用搜索不能单独证明可删除。

本次继续清理复核：历史138 PDB、212 EXE、872 ZIP-backed精确删除集均已不存在；没有发现这些已批准集合中漏删项。223旧Desktop集合剩余4个mutable canonical DLL（1,566,064 B）原收据未授予当前删除资格；96generated集合剩余7个canonical硬链接（61,312,685 B）原收据明确KEEP，删除名称亦不等于回收其载荷。当前默认be268、注册53、现役dotnet routing及索引va5/va647继续保留。这是有限编译输出审计收敛，不代表所有剩余目录无用或产品验证完成。

## Git交付

本地分支codex/Audit；本轮继续前已发布的最新源码检查点为07c771bea56658ee8a24ecc18b4a09e4df0404d2，包含35个桌面源码/资产及交接文档，此前经git ls-remote回读一致。清理文档检查点为35260ad70c5c2eaf038da1dd7c53a455b104a812及244483911fe153cf0b11d39cf8eaa9cf6cbb6b74。2026-10-01此前远端main只读回读为df1a0d59961d0ced18c99dc3e31a5c5bee4a4eac；尚未把其27个后端/文档提交集成到本工作分支，不能声称main或Green双端一致。后续提交SHA需以最新Git回读为准。

既有19项tracked修改及此前未跟踪成果保护。本轮新增共享SDK路径索引、SDK迁移交接及本清理交接；OS External只最小增补忽略规则和项目工具注册表。上传应按精确任务文件集合进行，排除恢复包、缓存、运行数据库、日志、凭据与私人状态。最终必须分别记录本地提交SHA、远端分支SHA与验证范围。

追加已执行：a04历史构建净79,236,022 B；872个精确ZIP恢复成员重复生成文件净522,935,811 B。两项root readback PASS。新恢复依赖包括a04归档及872项allowlist引用的原va5/vhead ZIP，不能当旧包删除。上述体积已由两项删除后的最新metadata收据回读。

第八合成1728case和Green历史缓存508分发文件现已归档后删除，净510,306,036 B，root readback PASS。恢复依赖见历史报告最新条目。缓存failures/未知venv/索引原件保留，未执行whole cache clean。

第九合成1296case（3960文件）已删除，净61,314,716 B；Green三个已迁移包的3157个重复文件已删除，原根不存在，Formal归属副本全量SHA/集合一致。该项账本净83,247,641 B；独立复核另计722 B回读收据时净83,246,919 B。累计账本采用前者并统一排除审计收据，不混用口径。四批独立复核见本地cleanup-selected-batches-independent-readback.json，恢复ZIP逐成员CRC/SHA及原执行收据保留通过。没有把仍有引用的恢复包当缓存删除。

前端源码契约批次c2为275pass/49fail；c3复核49项仍失败，不能宣称项目已健康。已最小修复直接进入复习时首次加载被跳过，Formal c5及Green c6各1pass；这是源码契约证据，产品构建/原生运行尚未验证。其他失败包含旧断言和待核实实现问题，未统一豁免。

继续交付验证：命令面板补齐证据库、原创、人类学习、机器学习及工作区路由，旧名称作为alias保留；c7先失败、c8定向2pass。SDK10.0.401经现役build/dotnet项目命名输出根，cc的MSBuild /t:Build退出0并生成Debug/net10.0/ArcheAxis.Desktop.dll。c9/ca因缺恢复清单、cb因参数解析失败收据保留，不隐藏。编译通过不等于产品启动或安装态健康；其余源码/原生验收仍未完成。

最新验证：原生capture cd成功生成1440/960 aurora首页PNG，未启动Core/未读取用户数据库，强制减少动画，不能证明完整交互。840边界按B10 max-width语义包含等号，首页动态无障碍名称对齐“首页”；ce RED、cf定向7pass、cg重新编译退出0。ch以显式现役Core及全新项目内synthetic数据库握手，SMOKE OK并退出0；不是现有用户数据库健康验证。ci全量39份前端契约324项为276pass/48fail/1warning，完整XML本地保留，真实实现与旧契约差异正在逐项核实，不自动豁免。

四份清理公开文档已提交并推送codex/Audit，提交35260ad70c5c2eaf038da1dd7c53a455b104a812经git ls-remote回读一致；不代表本地前端修改已上传、不代表main已合并或Green全量一致。当前文档新增验证将在后续交付提交中同步。

后续核实：co既有learning-smoke在全新synthetic工作区通过，assessment/answer/FSRS/cold Core重启回读成功，mastery_projection_closed=false如实保留。cj导航点/双主题图标3pass；ck结构化来源与学习加载3pass；cl动态页头/导航/无推断语义7pass；cm首次4pass/1fail，cn修订无关旧工具条断言后Evidence真实性1pass。测试修订只针对已独立核实的表示/解析/母版差异，未跳过或xfail。品牌sidebar最小布局修复由并行writer限定两XAML，cp编译通过，cq/cr双主题1440/840原生渲染通过；截图发现长品牌文字越界，仍在修复，未宣称完整UI验收通过。

品牌越界后续修复：sidebar显示ArcheAxis品牌词根，tooltip/无障碍使用ArcheAxis Knowledge正式名，文字限宽并允许子线换行；两树动态窗口标题同步去除旧Learning Workspace/OS外部产品名。cs编译通过，cu1440 aurora原生截图经目视确认品牌留在侧栏内。ct最新全量324项为291pass/33fail/1warning，其中新增一项是sidebar从row1迁到row0后的旧几何断言，已改为检查母版品牌位于side栏顶部且跨全高；未用该定向修订推断全量PASS。其余未完成项继续记录，不重置历史失败收据。

绿色版验证：cy在Green mainline任务树通过现有版本恢复及Debug编译，cz当前DLL的1440 aurora原生截图退出0，目视品牌/侧栏保留，无Core和真实DB访问。Formal与Green编译各自通过不等于源码或安装态全量一致。cw双主题与未知学习计数2pass，cx图谱示意/真实lineage边界及三种学习计数状态2pass，cv sidebar和导航点5pass。剩余主导航契约由限定单文件writer修订，根未并行写该文件；未设置skip/xfail。

前端源码交付检查点（WIP，非验收完成）：35个桌面源码/资产文件约8.9MB，均低于50MB，限定源码秘密模式检查未匹配。当前直接引用组件随源码保留；8张旧生成hero PNG、brand SVG及两个旧矢量组件按历史成果保留，不能称当前页面已使用或B10原包资产。最高视觉依据是用户采用提示词指定的B10最终可部署母版，B03等为较低参考，不能由旧测试反向覆盖。未提交原始UI ZIP、数据库、缓存、恢复包或私有状态。

命令面板焦点恢复失败缺回退：d2定向RED确认；两树最小补充Focus返回false时聚焦WorkspaceHeadingText，d3定向1pass、d4编译退出0。d5 C# Vocabulary harness编译通过，d6 production binding的29个wire cases通过。导航测试文件还由唯一writer修改，未放入本源码检查点；全量静态/原生交互/DPI矩阵及当前main后端整合未完成。批量测试覆写曾被自动审批拒绝，已改为精确上下文补丁保护现有dirty修改，没有绕过或整文件覆盖。

2026-10-01 前一Git只读与fetch快照：源码交付检查点提交前的基线是origin/main祖先，left/right=0/27；该段是历史快照，不能用作现在HEAD或已发布状态。远端包含新增backend和文档整合，不能把当前dirty源码直接覆盖远端。tracked改动与远端变动的交集为docs/DOCUMENTATION_AUTHORITY_INDEX.md；集成需保留远端新backend及本地UI/清理成果，解决该文档真实三方差异。未执行merge/reset，用户工作文件继续保留。

## 最新清理、验证与交付范围

旧framework候选经独立当前引用/进程审计后，先逐文件fresh校验并删除41个重复依赖456,173,680 B；scope外独立canonical长度/SHA一致，5个唯一应用文件当时保留，独立回读41源不存在、canonical全量哈希一致。随后明确旧编译字节不是必须保留成果：另外三个未绑定候选的7个EXE/DLL/PDB共4,288,288 B及framework剩余5个生成文件1,499,127 B已精确删除。对应三个源码提交仍可读，可重建功能版本，不保证相同二进制字节或旧PDB。framework5删除前fresh Win32_Process精确消费者0。47个空目录逐层确认无文件/链接后非递归移除，四个旧scope根均不存在。没有为这些无用输出再制造重复归档。

最新导航契约da：212pass。随后39份受影响前端契约db：324pass、1个Pillow弃用warning。B10依据修正旧几何/菜单断言，移动导航测试明确只证明可见入口及命令面板注册，不把隐藏菜单当原生曝光；未使用skip/xfail。dd的Ruff调用格式失败、de真实运行检出42项静态问题；仅导入排序/末尾换行及不用的局部变量被修正，dh受影响Ruff全部通过。冻结集合最终di复跑324pass、同一warning；旧候选删除后dj现役SDK/输出路径桌面编译退出0。没有把静态/编译PASS冒充原生交互/DPI/动画完整验收。

C# Supervisor d7编译、d8现有9项隔离/重启/错误凭据/短路径/带空格DB路径harness通过；Vocabulary d6为29个production-wire cases通过。均为既有测试和synthetic工作区，不是现有用户数据库或所有软件健康证明。

公开历史清理MD限定18份，经独立内容审计后可发布。5份历史文档已纠正VS Code修复前后快照、容量元数据越界事件措辞、跨位置净值口径及已移除worktree提交保护方式；保留真实事件，不写“所有C/D软件健康PASS”。完整本地收据、数据库、恢复ZIP/CAS、原始私人正文仍不上云。两份依赖未公开UI母版输入的测试（test_aaos_icon_b10_contract.py、test_b10_shell_fidelity_contract.py）需先处理可移植输入交付，当前不能当成已可在云端裸检出的测试。

公开56文件检查点c09c845f82d47fcf011798ba26852fa21b38cf45已推送codex/Audit，ls-remote完整SHA一致。精确SHA CI run36776964083终止FAIL：3401pass/4fail/35skip/137subtest；lint为SVG末尾换行与一份测试UTF-8 BOM两项编码问题，桌面专项gate在该doc/test检查点被计划跳过，不能称全部CI验证通过。

已按失败根因处理：两份旧主题测试改为分别约束用户授权Monochrome/Aurora及真实资源切换；导航manifest仍7page_id，但现役19sections必须精确列明；补正式窗口双语无障碍名称，两树一致，未改变B10可见布局；旧import/learning文案断言对齐实际动作入口。dk新名称契约先RED；dl三份受影响测试29pass；dp四份变更测试Ruff PASS。dm正式树编译通过；Green gd1不存在本地.venv入口为NOT_EXECUTED，使用既有正式Python启动其dev脚本的gd2编译通过，未新增环境。编码问题最小去BOM/补LF，不改内容语义。修复版本远端CI仍待新提交验证。

原runtime-readonly-copy经完整1545源SHA与已保留copy2 ZIP指定子集CRC/SHA/length核验，删除78,973,372 B及116个空目录，原根不存在，原run execution/source快照保留。独立回读1545源全absent、恢复映射/ZIP未变、指定成员全PASS、只计账一次。复用runtime-readonly-copy2-recovery-20261001.zip和既有mapping；恢复时按新的original-equivalence映射回runtime-readonly-copy根，不按copy2原mapping默认根恢复，也不恢复ZIP中超出1545子集的额外文件。没有新增恢复包。

## 2026-10-01 继续清理：旧 Core 编译缓存

已执行逐文件删除551项：`.project-local/runs/be268a2d33/aaoscorebuildrelease/artifacts/cargo-target/release/build` 与 `release/.fingerprint` 内独立审计列明的缓存。执行前核对全部路径、SHA-256、文件身份、硬链接闭合和活动进程；执行后551源路径全部不存在，当前 `build/cargo/debug/archeaxis-api.exe` SHA-256 `71f90c25b03773aa55a8b542e252d2232066ba8cab5eaec33df92e80028da41c` 保持不变。未删除源码、当前Core、旧顶层Core制品或用户数据。

本批逻辑净减66,708,946字节；按文件身份去重的内容大小35,772,904字节，未测量实际磁盘释放量。累计清理台账逻辑净减58,628,644,289字节。该运行历史exit101仍记录为失败；缓存可由保留的源码及Cargo.lock重新构建，不承诺恢复历史相同字节。未新增恢复压缩包。

本批执行前的元数据快照：Formal可读范围25,553,736,290字节，Green可读范围9,602,973,787字节；排除私有目录、链接及不可读取项，是下界，不能当成完整资源管理器容量。后端验证新构建增加了部分输出。本记录不是全部清理或全部运行健康完成声明。

本地详细证据位于 `.project-local/mig/storage-cleanup-current-20260930/new-core-cache-reviewed-20261001.json`、`new-core-cache-prune-20261001.json` 和 `round-total.json`。完整本地缓存/日志/恢复包不上传。

同轮追加：3个已结束运行的VBCSCompiler/AnalyzerAssemblyLoader临时影子副本39文件已按独立清单删除，逻辑24,030,984字节，源全absent，当前Core SHA不变；SDK/NuGet原件和产品源码未动。累计清理台账逻辑净减58,652,675,273字节。本轮新增两批合计590文件90,739,930字节。证据：`vbcs-cache-reviewed-20261001.json` 与 `vbcs-cache-prune-20261001.json`。旧Green NuGet去重候选在删除前核验发现canonical文件缺失/文件身份差异，资格门禁停止，尚未执行该缓存批次；不能把早先匹配统计当成当前可恢复证明。

NuGet候选补充核实：先前canonical缺失系263字符路径的非扩展Python调用错误，正常身份扩展路径元数据确认文件存在；样本source/canonical共享同卷同fileID、nlink=2，属于硬链接。共享名称不能按1.23GB重复路径统计为实际回收；旧dev.py也仍绑定其缓存用于未来restore。本轮不删除这种共享缓存名称，避免恢复时重新下载导致真实占用增长；只审计独立文件身份可回收子集。
`green-old-nuget-duplicate-reviewed-20261001.json` 完整743项复核完成：全部source/canonical共享同文件身份，独立单硬链接可删子集0项；1,232,333,595字节为名称逻辑总和，不是重复分配空间。本轮全部保留，未计入减量。

绿色版mainline旧Release追加清理：独立审计300项820,039,830字节，删除前全量fresh SHA/单硬链接/路径/进程复核后逐文件删除，源全部absent。保留Debug DLL、当前Core、MainWindow.axaml及MainWindow.axaml.cs，执行前后哈希一致。70项589,410,039字节另与保留Debug全SHA相同，其余是可从保留源码及SDK/NuGet重建的旧产物；不承诺重现旧dirty构建字节。没有修改安装根或数据库。证据：`green-mainline-release-reviewed-20261001.json` 与 `green-mainline-release-prune-20261001.json`。

本次继续执行共3批890文件910,779,760字节；累计台账净逻辑减少59,472,715,103字节，实际NTFS释放量未测。旧清单的漏执行项为0不代表全部项目已无可清理项，整体任务仍PARTIAL。
清理后本次fresh元数据：Formal可读范围25,464,354,609字节（25.46GB），Green8,782,933,957字节（8.78GB），读取错误仍491/40。均排除私有状态/Git/reparse，属于观察下界；未冒充全部软件/用户数据库健康或完整资源管理器大小。

## 2026-10-01 下一继续回合

已删除Formal四个旧.NET Release/bin/obj精确范围1,039文件777,160,641字节，独立review清单为 `formal-old-dotnet-release-reviewed-20261001.json`（SHA087fc5d2dcd02566832ccbeeda12208a9fab9b54cf83b87267f81ccb89e3fbe1）。执行前重新核全部SHA/身份/单硬链接/路径/活动进程；执行后1,039源路径全absent，现役Debug、Core413与两份前端源码哈希不变。可从保留源码/SDK/NuGet重建，不保证旧dirty历史二进制逐字节恢复。累计净逻辑减少60,249,875,744字节；实际磁盘释放量未测。

隔离集成验证iv11为476pass/1skip/1warning/9subtest，运行源413ad3a0+当前两份测试修复dirty补丁；skip原因Windows file symlink unavailable，Pillow弃用警告保留。这不是纯413提交或用户DB/安装态全量健康证明。iv10文档/runner为16pass/1fail，缺Sept29归档导航尚未发布；双主题/B10权威断言已按真实用户方向修复，未设置skip/xfail。后续发布需包含经过内容审计的导航与链接依赖，并按精确提交重新CI验证。

本继续回合进一步执行：24个已确认tmp_path生成的旧合成testcase，339文件134,267,763字节已删；原3execution与Core哈希保持。首次执行因审计run日期后缀不匹配在删前门禁停止，核正exact audit-r5-full-20260927后重新全量门禁通过再执行，不隐藏失败调用。旧candidate-current-final安全生成子集17,839文件794,582,943字节已复用保留原ZIP全量成员CRC/SHA/length核验后删除；精确恢复映射新增13,792,199字节，计账净780,790,744字节。另旧current-source候选中间编译1055文件547,398,411字节已删（闭合硬链接集合）；227项可由保留索引ZIP精确恢复，其他缓存可再生；映射573,752字节，计账净546,824,659字节。恢复ZIP/当前Core/DB/WAL/私有/截图/原执行收据全部在删集外；无需新ZIP。

累计台账净逻辑减少61,711,758,910字节，包含两份大恢复映射成本，仍排除小型审计收据；实际NTFS释放未测。当前剩余对象不因名字或总大小直接获删资格。

公开交付准备：22份Sept29项目历史包文件及两份母版资产通过内容审核，不是私人原生session/凭据/数据库。Sept29原ZIP14成员与unpacked全字节一致；其格式/BOM/EOL由精确SHA门禁和定向Git属性保留，4份自有派生审核文档只规范格式，保留原内容与原包。母版HTML/图标板迁为tests/fixtures/aaos-ui-mother的readonly参考，原SHA保留，两份测试不再依赖本机.project-local输入。HTML demo localStorage/随机图谱/示例值不得充当Core真值或直接生产应用。

iv12已有受影响文档/runner/母版契约26pass；iv13命名/路径62pass；iv15加入包成员/母版精确SHA验证后90pass。iv16 Ruff发现import排序/异常抑制两项，修复后iv17 Ruff PASS，未改产品行为。后续正式提交及远端精确SHA CI仍需回读，不能提前称已上传/已健康。
