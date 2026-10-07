## 2026-10-06 本轮状态（最新，先读这一节）

状态仍 `PARTIAL`。本轮按 Owner 就"需所有者指定"的四类给出的范围执行，逐项审计后按**精确路径**删除，累积减少约 **40G**：

| 目标 | 前 | 后 | 减少 |
| --- | --- | --- | --- |
| 开发根 `.project-local` | 113G | **79G** | 34G |
| 绿色仓库 `ArcheAxis.Knowledge.Green-x64` | 15G | **9.1G** | 5.9G |

- 绿色仓库：四条旧代候选（`v18a00075`、`v82e8d28c`、`vd6bd374`、`AAOS-Tauri-578d06b78413`）连同先前的两条 worktree 一并清理；候选的 `candidate-manifest.json`/`backend-runtime-manifest.json`/`worker-profile.json` 在删除前复制进 `.project-local/recovery/green-candidates-20261006/` 并记 SHA-256。
- 开发根：`build/2611ed9ca1`(15.4G)、`build/cargo-junction`(1.7G)、`build/gc-r20`(1.2G)、`build/aaos01-tauri`(1.3G)、`candidates/AAOS-b421ddee-audit`(0.6G)，以及工作树自己的 `build/2611ed9ca1`(11.8G)、`aaos01-core`(0.9G)、`cargo-gnu`(0.2G) 与两个 `build/green-candidates`(2.1G)。每项删除前以 `git grep -F` 对**精确相对路径**查引用；`ci.yml` 引用 `build/green-candidates` 一处经阅读确认是**写入/产出**路径（`--out` + 上传 zip），故以显式 `--allow-cited --reason=…` 覆盖，并跑 `tests/test_green_candidate_assembly.py` 验证（7 passed / 1 skipped）。
- 明确保留：`build/cargo`(14G，热缓存)、`recovery/`(8G)、`mig/`(4.3G)、`cache/`(3.2G)、`task-runtime/` 与 `candidates/`（均在预算内）、`legacy-scratch-20261006/`（`realign_dev_layout.py`/`undo_layout_realign.py` 引用的恢复清单）。
- **仍受阻**：`runs/2611ed9ca1`(6.27G) 与另外 23 个 run 目录枚举/删除时 `WinError 5`。按约束不强制、不提权；等 Owner 在提权会话跑一次递归枚举并给出体积后，再并入下一批。
- 上文 2026-10-01 各节的体积数字是当时口径（可读元数据下界，权限拒绝/私有/Git 排除），**不覆盖**本节读数；本节数字来自 `du -sh` 实测。

## 继续审计与删除（2026-10-01 后续回合）

状态 PARTIAL。本回合已删除 1,886 个旧 obj/fingerprint、R6 SDK 和旧 Debug 文件，源载荷 127,910,013 B，新增精确清单和恢复包 1,994,686 B，已删批次净逻辑减少 125,915,327 B；另一个待归属复核的 28 DB 本地恢复包及映射新增 655,258 B，源没有删除，扣除此成本后本回合净逻辑减少 125,260,069 B；统一净账本累计 69,832,500,108 B。台账旧 gross/recovery 字段属于较早快照，当前累计只使用逐批一次计账的 combined_net 字段；非 NTFS 空闲增量。

- 63 个旧 obj/fingerprint 已独立读回全部不存在，现役守护与父/publish 恢复依赖保持；中间缓存不承诺历史字节原样恢复。
- 1,596 个 R6 SDK 文件与保留的原 R6 ZIP 逐字节匹配后删除；该 Python scope 仅余两个保留 pyc。此阶段正式 supersede 前阶段非选 SDK 保持期望。
- 旧 Debug/win-x64 中 32 个文件与现役父目录逐字节相同，已删除并核现役父保持。其余 191 项已逐 ZIP 成员匹配后删除，4 个独有旧应用文件先做小 delta ZIP 并核 CRC/SHA 后删除；独立读回全 227 源 absent。父 runtimes 保留；iv32 现役 Desktop/Core 原生握手通过。
- 40 个恢复 ZIP 没有整包 SHA 重复；两份 CAS 仍有恢复引用。此前限定 cleanup 收据零引用的 vr6-6f0b4cc 原包，扩查公开 R6 交接后确认仍支持已删除展开树的恢复，保持。没有以唯一 SHA 作为永久保留理由。
- 文档提交 5c6552818f510dc318f615a26e9b364977c029b5 双端 SHA 一致，CI 36801398096 success。本节后续提交需要单独回读。
- 最近一次只读体积下界（先于新增待核 28 DB 恢复包）：Formal 19,223,937,549 B / 290,040 文件；Green 8,590,728,016 B / 116,248 文件。读取拒绝 491/40、链接跳过 94/0，私有/Git排除，不能用作完整资源管理器大小。四个大混合 run 的大头已定位到 vector testcase 数据库；第一批 28 DB/157,745,152 B 缺原始生成收据，独立复核确认名称/布局和当前 producer 不能证明这批源的归属，既有其它 run 的证据不能迁移。28 源与锁保留；恢复 ZIP/映射已验证，只是归档 PASS，不是 synthetic 归属 PASS，删除暂停待全表数据域闭合核验。未知 DB、私有状态、不可读项和恢复链保留。未证明全部 C/D 项目相关目录均无可清理内容。

以下为较早阶段记录。
## 最新继续清理读回（2026-10-01）

状态 PARTIAL。本继续回合已复核并完成 1,761 个旧构建/测试/运行时产物删除，源载荷 569,360,961 B，扣恢复归档和映射 41,965,609 B，净逻辑减少 527,395,352 B；已计账累计 69,707,240,039 B。此口径不是 NTFS 空闲增量。

- 五组旧 Cargo API、旧 proc-macro PDB、登记 53 scope 的父 bin/publish，以及两组旧测试产物已按精确清单清理。必要旧二进制先归档并验证 ZIP SHA/CRC/成员映射；现役 Core/Desktop 与源码守护保持。恢复包仅保留本地，不上传。
- 676 个旧 R6 stage 文件已删除并独立读回，原 R6 ZIP 保留。两项排除标签与精确清单重叠已更正；1,598 个非选公开文件两次删除后 SHA 稳定，但缺删除前全量 SHA，不声称前后全部相等。历史 stage 运行需先恢复成员。
- 最后 558 个小缓存删除前的可读元数据：项目 19,351,439,223 B（292,442 文件），绿色版 8,590,728,016 B（116,248 文件）。权限拒绝 491/40，链接跳过 94/0，私有状态和 Git 排除；这些数字为可读下界，不等于资源管理器全目录体积。
- iv30 原生 Core 握手、iv31 合成学习答案保存/FSRS/Core 重启通过；mastery_projection_closed=false。没有据此宣称全部 UI、真实数据库或绿色版安装验收通过。
- 另 558 个旧 Cargo 描述/import 缓存已精确删除并独立读回，40 项守护 SHA 保持；此类缓存只可重新编译生成，不承诺历史字节恢复；四个大混合运行目录缺公共终止证据，未知数据库、用户私有状态、恢复依赖和权限拒绝项保留。没有证明全部剩余内容均不可清理。

以下为较早检查点，当前数据以本节及之后真实读回为准。
# 本次继续回合：已结束合成产物与编译缓存

状态 PARTIAL。四批 4,527 文件真实删除并独立回读，源 221,028,064 B − 新 mapping/gzip 2,367,867 B = 净逻辑减少 218,660,197 B；统一账本累计 69,179,844,687 B。少量审计收据不在台账口径，实际 NTFS 释放未测。

批次为旧 Cargo 编译库 10 项（46,250,574 B）、Green 旧构建环境公开 `.pyc` 265 项（4,826,825 B）、be268 公开测试生成的合成文件 1,551 项（110,289,787 B）。前两批扣除新映射，第三批可从公开精确 test nodes 重跑，无新增恢复载荷。旧编译缓存不能逐字节恢复；所有实际程序/符号、公开 Python 源码、环境入口、原始结束收据、锁文件及当前 Core 均保护。共享硬链接不冒充可物理回收副本。

最新元数据 Formal 19,874,568,829 B / 293,586 文件；Green 8,590,728,016 B / 116,248 文件。491/40 个读取拒绝与私有/Git/链接排除，不能视作完整目录体积。iv28/iv29 Core握手及合成学习闭环通过，答案保存/FSRS/重启回读成功，`mastery_projection_closed=false`；不代表真实用户 DB 或安装态全界面验收。

本地证据目录 `.project-local/mig/storage-cleanup-current-20260930/`：`old-cargo-library-cache-prune-20261001.json`、`green-old-build-venv-pycache-independent-readback-20261001.json`、`be268-synthetic-source-isolated-next-independent-readback-20261001.json`、`storage-after-further-cleanup-20261001.json`、`prune-eight-association-followup-20261001.json`、`three-spill-roots-current-readback-20261001.json`。不上传数据库、恢复包/CAS、缓存及私有正文。

收据对标补足 7/8 原关联缺口；仅 staging-ui-delta 旧执行绑定仍 UNVERIFIED，源已不存在，不重复计删除。四个 be268 大目录 `ce3921cec208`、`37a9bb9d7cab`、`1547cc4f23f2`、`full-python2-20260915` 缺公共终止收据，限定证据位置无完整 JUnit/exit/command，保持 KEEP。读取拒绝及未知数据不能以名称定归属。E/F 禁访；未修改 ACL、系统配置、其他软件或用户数据。

上一公开提交 `3d0c24439b523d563bdd574e0b5c04b752d71821` 精确 CI run `36795015416` 完成 success。当前文档更新须以新提交回读为准。以下章节保留较早检查点，较早累计和大小不代表最新值。

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

## 2026-10-01 继续清理读回

已审计旧清单921、17,839、1,055文件集合回查剩余普通文件均为0，未发现漏执行。此次新增18个明确tmp_path/fake-data测试case的36个数据库及锁文件，89,137,152字节，删除前全量SHA、文件身份、单硬链接和进程复核通过，删除后全部absent；原3执行收据与当前Core保持。证据为remaining-formal-vector-six-second-reviewed/prune-20261001.json。

两个无当前绑定的direct2/direct3旧Cargo Release target新增797文件77,870,696字节，逐项SHA和闭合硬链接集合复核后已删除；全部absent，当前Core、两处Desktop Debug、Cargo.toml/Cargo.lock保留哈希一致。原历史执行结束收据未定位，UNKNOWN保持；资格依据为生成归属、当前路由迁出、可再生和无进程消费者，不把未知写为成功。证据为old-direct-release-targets-reviewed/prune-20261001.json。

本回合新增833文件167,007,848字节；累计净逻辑减少61,878,766,758字节，实际磁盘空闲增量未测。删除前元数据快照可读Formal27,138,273,706字节、Green8,783,888,264字节；排除Git/私有/不可读/reparse，读取错误491/40，不能当完整资源管理器体积。Formal新增本轮精确源码Rust测试构建导致增长；新Cargo Debug是现役验证产物，保留。旧candidate展开仍在进行逐成员原ZIP恢复审计，未声称全部清理完成。

源码与公开39文件交付已推送codex/Audit，提交2a15f830d0dae6d5cbb7e9e3aa1c4aca735aa5e2经ls-remote一致。该SHA本地Desktop Debug编译与Rust workspace测试退出0，远端vNext CI成功；常规CI截至该快照未最终读回。原生启动验证iv20退出1，未启动桌面：共享资源校验器错误地从嵌套worktree父目录推导固定资源根，需修复，不以绕过preflight称健康。整体状态PARTIAL；不代表双端安装态/真实数据库/UI完整验收。

旧候选桌面公共生成副本追加清理644文件567,079,733字节：三处精确源均与保留va5原ZIP对应成员SHA/CRC/length一致；当前Core/Desktop SHA与ZIP不变，全部源absent，独立readback PASS。独有4/70文件、敏感名称、manifest/core/runtime/workers/DB在删集外。恢复映射619,574字节计为成本，净566,460,159字节。累计净逻辑减少62,445,226,917字节；本回合1,477文件净733,468,007字节。旧历史候选需按映射恢复后才能重跑。证据：remaining-candidate-expanded-post-17839-review/prune-20261001.json。

旧run Cargo Release top/deps追加113文件49,374,483字节已精确清理，全部源absent，现役Core及原exit101执行收据SHA保留；独立复核PASS。累计净逻辑62,494,601,400字节。本回合1,590文件净782,842,490字节。runtime/workers的20,689文件原ZIP映射执行门禁先后因manifest命名错误、保留父目录命名停止，均在删除前，源删除0；正在保守排除保留父目录子集，不取消guard。

保守过滤后旧va5 runtime/workers公共副本20,688文件651,263,385字节全量fresh源SHA/ZIP成员CRC/长度、单硬链接、路径与进程门禁通过后已删，全部absent。候选manifest、原ZIP及现役Core/Desktop SHA不变；保护父目录下1文件13,665字节和原99敏感排除项保留。filtered映射19,911,641字节及保留的原始失败前mapping19,911,841字节均计入成本，避免虚报净量。此次运行副本净611,439,903字节；本回合合计22,278文件净1,394,282,393字节，累计净逻辑63,106,041,303字节，实际磁盘空闲增量仍未测。证据：remaining-va5-runtime-workers-public-filtered-reviewed/prune-20261001.json。

清理后fresh元数据：Formal可读范围25,933,370,955字节（25.93GB）314,368files；Green8,595,662,287字节（8.60GB）116,813files。读取错误491/40，Git/私有/reparse仍排除；是可读取范围观察值，不是全部目录/实际空闲空间。源代码未修改；仅公开交接文档追加本回合证据，git diff --check通过。
# 继续清理更新：2026-10-01

本次继续实际删除 16,813 文件，源载荷 5,868,787,521 B，扣除新增恢复映射后净 5,855,143,187 B；统一账本累计净逻辑减少 68,961,184,490 B。均非 NTFS 空闲空间增量。另 5,916 空目录非递归删除，独立回读不存在，不计文件载荷。

已执行批次：5,963 个历史公共 runtime/.NET 副本（原恢复 ZIP 精确成员校验）、696 个已结束合成 full_db 测试产物、8 个历史编译符号、Record 3 个与正式归档精确相同的文件、Green 6 个与 canonical 精确相同的旧前端资产、9,838 个现行 Cargo 编译缓存、5 个顶层库/旧示例产物。逐批执行前复核范围、SHA、文件身份、硬链接和进程，执行后独立回读；本地清单/收据保留在 `.project-local/mig/storage-cleanup-current-20260930/`，不上传。

当前 Core、PDB、Desktop、Green EXE、源码、锁文件及依赖原包保持。旧符号/库/示例及编译缓存没有逐字节恢复备份，可从保留源码重新编译；重复资产从 canonical 或已保留原 ZIP 恢复，禁止覆盖未知现存文件。真实/未知 DB、WAL、私有状态、恢复 CAS/ZIP 继续保护。

资源索引修复提交 `62f23189c3bd607967f3313d7809e4d636f58f1b` 已发布且远端 SHA 回读一致，CI `36791031910` 成功；干净工作树 iv23 的 29 项回归通过。最终清缓存后 iv26 握手、iv27 学习闭环通过，答案保存、FSRS、Core 冷重启均回读成功；合成工作区，`mastery_projection_closed=false`，不能代表真实用户 DB、完整 UI 验收或 Green 安装态一致。二进制构建于 2a，Desktop/Cargo/crates 源码到 62f 无变化。

最新独立元数据快照 Formal 20,156,983,331 B（298,089 文件）、Green 8,595,554,841 B（116,513 文件），先于最后两批收尾；491/40 项读取拒绝，私有/Git/reparse 排除，仅为可读取下界。正在刷新快照及继续审计剩余大目录，整体 PARTIAL，未证明再无可清理项。E/F 禁访，权限拒绝未通过改 ACL 绕过。

以下内容为此前检查点，较早体积、失败及待办须结合本更新阅读。

## 最后两批收尾

已追加删除 290 个 AXW 合成测试产物（71,209,994 B）和 4 个由保留 vui3 ZIP 精确恢复的旧桌面文件（1,486,204 B，新增映射 4,975 B），独立回读通过。另 18 个 Cargo 空目录删除并回读，现役守护 SHA 保持。以上摘要累计已包含两批增量；元数据体积快照早于这两批，不能视作最新完整大小。vui3 ZIP 仍是恢复依据，保留。整体仍 PARTIAL，未知/私有/拒绝项不凭名称清理。

## 本回合最后编译缓存批次

另已删除旧 Cargo procedural-macro DLL/配对描述/fingerprint 2,701 项，源 59,660,878 B − mapping 1,481,161 B = 净 58,179,717 B（上述四批总数已包含）。27 DLL 实际导出 procedural-macro 声明，13 API 实际依赖无对应导入，全部闭合硬链接及进程门禁通过；53 个 EXE/PDB/源码锁文件和 15 个根标记 SHA 保持。其 697 个清单祖先空目录非递归删除，独立读回不存在；五 scope 根与 30 非空容器保留。精确收据 old-cargo-proc-macro-and-build-cache-independent-readback-20261001.json、old-cargo-2701-ancestor-empty-independent-readback-20261001.json。旧编译缓存可从源码重建，不能恢复历史相同字节。
