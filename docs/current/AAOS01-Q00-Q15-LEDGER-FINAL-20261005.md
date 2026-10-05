# AAOS-01 Q00–Q15 当前执行台账（2026-10-05）

当前固定门禁：`29e7f08b84205cedbbdace6228383e8942146eb6`，workflow308098767/run37349719826/attempt1，完整headSha与workflow_dispatch核对一致，终态FAILURE，等待期间没有推送。desktop-fast、desktop-build实际PASS；rust-vnext在根工作区fmt失败，其后测试为SKIPPED；test(3.12)的OS测试失败；installer-lifecycle与a0-gates失败。根fmt遗漏已本地修正，canonical `cargo test --workspace --locked`完整exit0；实际production route inventory遗漏checks/execute已补齐61条，定向4tests PASS。完整Windows OS回归实际3985 PASS、36 skipped、137 subtests PASS、1 FAIL（第二份路由计数仍用36/41）；该唯一断言已同步真实37/42，计数/inventory/Tauri authority/CI a0四模块canonical定向41 PASS、exit0、无skip。完整运行本身仍为FAIL，不把旧CI失败或未复跑全量改写为通过。

安装诊断artifact11362996823严格绑定上述四元组，6,243字节非空ZIP/CRC/SHA核对PASS，SHA `86b25deb619367bfc2cdb1ea69e0d91e46f89db6be03614953a5a65197efcd6e`。installed host SHA `19b7f50c2fba0459661f72024bb2ff7ce4f8cabf5c5b18c54fc05d50b3f3922a`：实际宿主/Core/WebView及可见窗口存在，WebView调试参数布尔为false，仅Core loopback监听；CDP40秒超时、steps=[]，未执行12步业务断言。proxy_environment_present=false。不能据此判NSIS产品未启动，也不能判业务成功。

针对性本地修复：Tauri仅在明确进程级 `ARCHEAXIS_WEBDRIVER_CDP_PORT` 端口合法时通过native additional_browser_args传loopback调试参数，普通启动无调试端口，任意参数/越界/特权端口拒绝；探针绑定自有动态端口。src-tauri实际65tests PASS。Microsoft上游说明WebView2 150+ elevated宿主忽略环境覆盖，API参数仍有效（https://github.com/MicrosoftEdge/WebView2Feedback/issues/5645）；本次宿主完整性未采集，该根因仍为推断，修复尚待新exact-SHA安装门禁验证，不改注册表/全局环境。

`93d9437ad75afab0b9942b6bb92b981fd1479c73`的未配置执行/显式重试实现已经包含在29e7固定提交；下文“本地未发布”及55e604是对应历史阶段记录。真正配置后的云端核验/专业检索实现正在准备，未执行真实云端调用，不能将待执行或fixture结果登记为已实现验收。

29e7同run已取得Office artifact11361698454（5,844字节，ZIP SHA `81b908cf726bd28820ef3e46cf3d6b062f583cf53ac390ce5ce1c2ba0595f154`）及policy11362017967（5,016字节，ZIP SHA `abb7d57703ee6c4d66f5d48c6245a83597b000fb0893ce928afad8899afcd7cf`），完整绑定/CRC PASS。有效XLSX/PPTX已知内容与重启相等断言true；两个损坏样本验证错误状态及重启相等true。runtime实际import openpyxl3.1.5/pptx1.0.2，module路径、Core launch python同`.project-local/rt/runtime/python.exe`，解释器SHA `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`；uv.lock SHA `0f73ea804b0eca61a251013d199f75d88f35e6322bb155eb2581b8d10f69ce52`。policy九行为断言true，含独立restore equality；cloud_not_executed=true，人工fixture不是实际真人认可。上述为真实Core/worker执行、自编样本，不是安装态完整门禁通过。

固定门禁增量：已正常推送 `55e60487aa97f2f629d081d2338b6cc5eace1e94` 并dispatch force_full，workflow308098767/run37345525360/attempt1/headSha完整核对一致；desktop-fast所有目标实际PASS，desktop-build/NSIS/候选暂存上传PASS；终态FAILURE：18个job实际成功；installer-lifecycle与a0-gates失败。安装typed artifact11360059690非空5,423字节、CRC/SHA/完整身份绑定PASS，ZIP SHA ab526ecaf480f9ccc66d856f97eb523030373f8c600234a1ece5ccf55d65326b；原生收据明确Owned attach CDP unavailable after40sec、steps=[]，失败发生在WebDriver建session之前。本地成功不能替代；尚缺失败启动时WebView真实参数/监听/窗口元数据，不能归因权限或NSIS编译feature。等待期间未推送；下面8a79是历史失败。

本地未发布增量：新增 `/documents/:id/checks/execute` 与有限桥接/明确执行与显式重试按钮，绑定原pending check、实际不可变version/SHA及latest failed attempt；未配置明确failed/not_configured/not_executed，不调用云端。沿已有machine_tasks/document_checks同事务保存，无Source虚构，无第二库，无真人认可。8项file-backed API测试（普通保存/重启历史重试/权限与注入拒绝）、domain回归、内部事务回滚测试、7项SIMULATED UI回归/tsc、完整前端32文件208tests、src-tauri fmt和64tests PASS；旧异步回执不覆盖新文档。实际云端模型+联网原件对照与专业检索尚未实现，此增量不属于当前55e604 CI。

诊断补足（未称CI根因修复）：native probe现在Popen即绑定host PID/创建时间，CDP超时采实际ownedtree/允许名单exe路径/调试参数布尔/可见窗口/两profile计数/loopback监听；未采到身份不把空集合写成清理通过，采集与强制清理失败仍写失败收据。HTTP限固定127.0.0.1、不经代理且拒外部跳转。自有Python/localhost实helper（含假proxy、外部URL/redirect、PID重用负例）PASS，实际与tested helper AST相同；Ruff和29门禁合同PASS，原12业务断言未减。代理是否导致CI失败仍UNKNOWN，未修改系统策略。

双端描述：Formal现有README保持当前Tauri方向；Green根新增README.md（SHA db869fe64b721f920990af025943e59a91f8f9b35a263f21e5414fd4a2b0bd37），明确根层旧0.6.14与旧Avalonia入口不等同当前AAOS源码，任务状态仅指向本表，未改程序/启动器/用户数据。复用20261001已审743个NuGet文件证据：当时两缓存对应文件均同fileID/hardlink，没有独立重复payload；历史1,232,333,595字节逻辑名称量不能算本轮可回收量，本轮未重审全树/归档或删除。

当前增量（2026-10-06）：canonical Tauri CLI 宿主 SHA `05bdaeeeb869ccd3cc1a4ded2f62db6efd0c181ea49720865ab370c8ab04b85f` 实际完整12步及四次产品正常 exit0 PASS；收据 `aaos01-webdriver/8f28552761c640d8886183e99e908c30/receipt.json`（40,011字节，SHA `09a4ab1a1bb423d656d7c48342b16fa73a01469779d57e357bfd89d9df9e0b5e`）。独立无观察器 WM_CLOSE PASS，收据 `aaos01-owned-wmclose-preflight/85f62dcf00224515836feec1ccfbabe3/receipt.json` SHA `c052e36f2b4f9f723285bf9254b3fa21c6e169f0c59f7c3cbb6f5dfede62662f`，自有进程与端口无残留。

同一宿主真实媒体闭环 PASS：公开合成 WAV 原件 SHA `838522e7a1c43673f88385a172a5abc921d34d99671e43490b711958cea52ebb`；单播放器 duration=5.22839s、实际播放推进并暂停；transcribe job `read_4d20b12c-0e14-46e9-81be-c50a73b1064d` attempt1 succeeded，实际本地 large-v3-turbo/cpu/int8，cue0–4560ms；located anchor `anc_6e152eef7bdfb38eb9aabf2f` 绑定原件/job/attempt/产物SHA和UTF8 checksum。完全重启后回执/CAS/锚点相等，自动读回 cues且未新增job；两次exit0、无自有残留。收据 `aaos01-webdriver/6832d94993b54ec48fda44cbab69bf2d/receipt.json` SHA `d1d2e77bc80d08b3a9bf06bc521fea018cb218f8560d5868feebf4e3533d9130`，两张非空截图。输入SYNTHETIC、产品执行REAL；不是真人准确率、视频解码、NSIS安装态或新exact-SHA CI。a16 Python是探针解释器；本收据未独立采集worker进程解释器路径，不由探针解释器推导worker身份。

当前暂存 a16/rt/release manifest `75eedbdcc1fbb888aa1a255b2d2c756e28df8fa97d038cee236e29fadf6dc8ae`，Core `c5be10c8af4e5a582d3821c5d2af0ac203808f819ac79b082ac1a7651148729b`；19,502文件核对后只更新rt的Core及manifest，两旧文件已备份，runtime未再次整份复制。uv.lock未改。云端识别核验与专业依据分析仍只有分离的记录/保存语义；真正执行与重试尚未实现，prepared方案不算实现。旧库迁移、Owner决定及安装态完整验收仍缺。

a14/a15去重已执行：两份原runtime及两份临时恢复树精确删除，逐文件恢复证明先PASS，删除后候选/rt/release与全部保留guard SHA不变。原重复payload1,251,227,904字节，保留恢复材料9,162,245字节，恢复材料口径逻辑减量1,242,065,659字节（另有小量清理收据成本）；临时证明不额外计回收，当前a16新增空间未从此口径扣除，整仓净变化/物理回收未测。收据 `aaos01-tools/a14-a15-runtime-cleanup.json`，保留donor、Core/workers/manifest和未知数据库。

以下增量保留当时失败和修复过程；“正在重建/待实跑”属于历史状态，由上述新宿主结果更新，不能用历史构建替代当前CI。

媒体身份修复增量：abc03 宿主实测单播放器、原件 duration=5.22839 秒、play() 实际成功、时间推进后 pause；转写 job/attempt 实际 succeeded，但 UI 拒绝结果。已定位为前端错误要求 jobs_get.kind：真实该接口没有 kind，source_jobs 才提供任务类型。现改用有界来源任务列表核实际 job ID/来源/kind/state/同 attempt，保留 jobs_get、SHA、字节数及 cue 校验；真实 DTO 形状的三项回归先 RED，再相关 23 tests/tsc GREEN，未为前端另改 Core 接口。失败收据 `aaos01-webdriver/4550f95f4bfd4fb6b94d25a01f209239/receipt.json` SHA `12950cd68d01734d9b1cba5abf594eee920fa93ee39f042efec4759f20a8c2fc` 保留，不把 worker succeeded 代替整 UI 旅程通过；修正版正在重建。

新宿主验证增量：正式 Tauri CLI 生产嵌入宿主 `4af8ec822e4982c67fd1aa1a362ed8e668f256e4b5bab5b040036808762b7727` 的完整 12 步及四次正常 exit0 PASS，收据 `aaos01-webdriver/f7c6735bb4124408a3c49a7c3573e4f9/receipt.json`（40,030 字节，SHA `0465b0660872585d4b55eadd82b667cface8a8f6593c2c40e537ca351e59b793`）；独立 WM_CLOSE 收据 `aaos01-owned-wmclose-preflight/062dc38de48c4679b04bd995656a57b6/receipt.json`（2,231 字节，SHA `152ed324f70694adcd982aea123cac7dfd5fa7769b22444a233d5b9b63451346`）正常 exit0，无自有残留。此前直接 cargo release 构建漏用正式前端嵌入，导致开发地址 ERR_CONNECTION_REFUSED；错误构建两失败收据保留，不能算媒体业务失败或旅程通过。

上述宿主媒体导入后的真实截图暴露重复播放器：MediaReader 和 JobContent 同层共用来源 ID key，重新打开来源会残留重复 DOM。定向 mock 原件回归先复现三播放器失败，再改为 media:/job: 各自唯一 key 后 GREEN；相关 10 tests/tsc PASS。该失败发生在转写之前，未虚构 ASR 或播放成功；修正版正在重建实测。

正式生命周期修法已进入 canonical `scripts/probes/aaos01_tauri_webdriver_loop.py`：owned prelaunch + loopback debuggerAddress attach，保留原 12 步业务断言；退出必须经产品命令且 exit code 0，意外提前退出拒绝，最终核 PID/创建时间与调试/driver 端口释放。installer verifier 直接调用此探针，独立无观察器 WM_CLOSE 预检仍先执行且失败抛错。Ruff、29 项 CI/宿主合同回归 PASS；正式强化版本及新媒体 UI 尚待新宿主实跑与新 exact-SHA CI。

权威暂存新 release 候选 a16：manifest SHA `75eedbdcc1fbb888aa1a255b2d2c756e28df8fa97d038cee236e29fadf6dc8ae`，Core SHA `c5be10c8af4e5a582d3821c5d2af0ac203808f819ac79b082ac1a7651148729b`；声明 source 4f747f03，声明来源仍 ASSERTED_NOT_VERIFIED，不冒充 exact-SHA CI。候选 `runtime/python.exe` 真实 import 四引擎 PASS（openpyxl3.1.5/pptx1.0.2/markitdown0.1.6/pytesseract0.3.13），各模块来自候选内部。a16 与当前 .rt 的 19,502 文件逐 SHA 对比仅 Core 不同；计划只备份/更新 Core 和 manifest，不整份复制运行时。

2026-10-06 增量：现有资料库接入本地媒体播放器、独立 transcribe 入口及时间段引用；播放器使用已核 SHA 原件的 Blob URL，来源切换释放 URL，不自动播放。转写时间段在展示前核实际 job/source/attempt、loss_report UTF-8 内容 SHA 与字节数；创建引用后再核 Core 返回的版本、任务与位置身份，后续失败保留此前成功回执。前端 30 文件 201 tests、TypeScript、production build PASS；src-tauri fmt --check 与 cargo test 63 PASS/0 ignored。以上是组件/编译验证，尚未把新增播放器或转写入口计为真实 Tauri、安装态验收；来源重开后读取已持久转写结果正在补齐。固定 CI 仍为下述 8a79 失败运行，未以本地结果替代。

来源重开读回已补齐：仅从 source_jobs 最近 50 条选择成功 transcribe，重新验证实际 job/输出/transform 回执，不自动重跑；最新失败独立展示，异步旧读回不能覆盖新执行。新增三项 mock 回归加相关整合共 32 tests PASS，tsc 和更新后的 production build PASS；仍待新宿主真实窗口验证。

生命周期修法本地实测：既有 e677 宿主的 owned prelaunch/WebDriver attach 完整原 12 步旅程 PASS，四次产品退出均真实完成；独立无观察器 canonical WM_CLOSE PASS。两收据分别 `aaos01-webdriver/e8d284a5bf9b487bb25ad40afdd1e692/receipt.json`（38,657 字节，SHA `a47045b403673508cb87a0a4eaa960920143bd343c72df802c1463c26b3f4156`）与 `aaos01-owned-wmclose-preflight/0975bee9b624449e80b2258f2ed5f7cc/receipt.json`（2,205 字节，SHA `a612d6227883abe848bda14e615356850e97ee88b3d5560dd5319fbfc0369c2c`）；精确 PID/创建时间读回无残留。仅本地既有宿主，不含新增媒体 UI/时间锚点 Core，尚未提升为安装 CI 成功。此前两次错误关闭方式的失败收据保留。

体积归属增量：复用既有精确清单核对，40 份 ZIP 历史总量 5,338,514,368 字节，位于 Formal 项目而非 Green 根目录。两份候选 ZIP 共 626,642,213 字节，opaque solid 压缩实际 CRC/恢复整包 SHA 通过，但仅理论节省 19,287,762 字节（3.08%）；原件保留，精确移除试点归档及两份恢复临时副本，保留 manifest/收据/log。`Formal .project-local/mig/storage-cleanup-current-20260930/solid-two-candidate-20261005/cleanup-receipt.json` 为 DISCARDED_LOW_BENEFIT，原始项目载荷净减少 0，不把临时清理算作回收。28 个归属证明不足的旧 SQLite 保留；已不存在的旧溢出路径不重新计为本轮删除。

时间锚点已完成针对性实现与真实验收：Core 校验不可变来源版本、实际完成 transcribe job/latest attempt、request 输入 SHA、loss_report 内容/metadata SHA、cue 序号、精确时间范围及 cue 文本 checksum；缺 checksum 保持 unverified，旧绑定不跟随后续 attempt 漂移。Rust API 全模块 --locked 回归 exit0，定向三项 PASS（含明确 seeded receipt 负例，不冒 ASR 执行）。权威暂存 a15 使用新 debug Core SHA `50d33fc20d8cf10b20f2afcea9f497d20571ad5cb866a5bd05496d41d70d23e5`，manifest SHA `7ba094a5909ff528a68ee2ead9aa47d2cebb374dd5e483d7c4c8358955dffed5`，来源8a79加实际 dirty。真实公开合成语音经新 Core 转写、HTTP创建 located/拒绝错范围错SHA错来源/缺checksum unverified、完全重启读回锚点及三产物均 PASS；receipt `aaos01-asr/c675095d718a46b9917e68aeddd58b90/receipt.json` 13,522字节、SHA `027cecaef2a4dad2d48fe6735aba044a2f827ebe29526359963d760e57871f50`。定位关联成立不代表识别忠实度、专业支持或真人准确率；本地 debug 候选不提升为安装态或固定 SHA CI。

历史固定提交 `8a79ac3b1e00cb522d02bf64bf03a6616048d105`，workflow `308098767`、run `37329333950`、attempt `1`，workflow_dispatch(force_full)，完整 headSha 已读回。终态 FAILURE：18 个 job 实际 success，desktop-fast 的 fmt/test、真实引擎 import、Office、普通保存与独立核验、Q12、导出和恢复步骤均实际成功；desktop-build 的 NSIS 构建成功；installer-lifecycle 与汇总 a0-gates failure。等待期间未推送。初次安装窗口/Core/关闭/数据库通过，WebDriver 首次握手仍缺 DevToolsActivePort、steps=[]，UI 旅程未执行。显式调试参数实际传入且1/10/30秒宿主/Core/WebView均存活，约60秒Driver连接失败后主动清理；不证明宿主先崩溃，也不证明权限差异因果。typed artifact11354099441/7931字节/ZIP SHA dbcfe7541662654e8cae280cae7e272be52c15b9b2a581a5a78fcfa36ad6c763 校验通过；首次120字节失败残片不作证据。完整安装资格仍失败。以下已终态运行按各自 SHA 保留为历史证据。

a14 实际 ASR：产品 runtime 真实 import faster_whisper1.2.1/ctranslate2 4.8.1/av18.0.0，现有本地 turbo 模型只读执行；公开短语合成 WAV 经 Core transcribe job 得到“The value is 37, the value is 37.”及一个合法时间段，完全退出重启后三产物/状态/质量一致。receipt `aaos01-asr/212083ed93e84b71a1c586ef9c63ca42/receipt.json` SHA `c17fafea62bc18982b92497552585b62e1900cd16c0313e2aff31ad31b42fd78`。独立三秒静音例保留空正文、空 cues 与明确 no speech loss，重启一致；receipt `aaos01-asr/9219ba3eb2e24d19ad15b9392c74e0b3/receipt.json` SHA `86050cd38e926244cddd500bdb5b4b188395f6519a0b432361d66511563424af`。这是实际模型/Core 调用、SYNTHETIC 输入，不是真人准确率、安装态、视频解码或 verified 时间锚点验收；A 矩阵原 WAV/MP4 仍仅 media.probe。

a14 新版 Obsidian 导出已在真实外部软件独立 profile/vault 中打开，正文、来源版本、Evidence records 和 Document 身份可见，复制文件与源 SHA 相等，退出后自有进程为零。receipt `aaos01-obsidian-readback-a14/a9e3f5a722924e0f99816338560067ed/receipt.json` SHA `e9f92433214cd3fc4a374944e1cf37e6c96c07bce2f70be647aad3c77874a77e`，非空截图 SHA `6b0fbf963153aa19c4e657751c9a181cdc3a6c3f7b5ddac565582f19db4ddef2`。未知节点实际 codec 为 preserved_unknown，按同目录 manifest-and-exit-validation.json 核对保留；不等同 Markdown 富文本无损。external_navigation_unavailable loss 保留，未宣称链接回跳通过。

新增体积清理：a12/a13 两份废弃 runtime 各自实际恢复、全树 SHA 相等后，删除两个原重复目录及两个临时恢复副本；原重复 payload 共 1,251,227,904 字节。保留 a3 donor、12 个独有 overlay（80,464 字节）、精确恢复清单/recipe/回执以及候选 Core/workers/manifest；当前 a14/rt 保留。清理收据 `aaos01-tools/a12-a13-runtime-cleanup.json` 四路径 absent 且18个保留 guard 文件 SHA 不变，恢复证明 SHA `e64c1ae513adacaa607eaae38515080b35d276f3db77d153bdd7f7bc6d4dcce9`。未实测物理回收量，不把临时恢复副本额外计入原项目净减量。

历史运行：固定 `a32003a08bc6b769d274f25c8f98dfff7c0bbc4d`，workflow308098767/run37320533049/attempt1，force_full终态FAILURE；18任务实际success，installer-lifecycle/a0-gates failure。等待期间未推送。Native artifact11350478412/7895字节/ZIP SHA `0e16968b824238a42311e410dd2ea991d407657501981f67ba1b4d6f628765e6`，非空CRC/身份校验通过。普通安装前置窗口/Core/WM_CLOSE/退出/数据库均真实通过；WebDriver首会话仍DevToolsActivePort缺失、steps为空。1/10/30秒同一宿主/Core/WebView实际存活，session-1 profile/EBWebView存在、Core数据目录无EBWebView；两候选位置port文件始终不存在。CI宿主/driver/rootWebView实测elevated=true，60秒后Driver连接失败并终止宿主树。故障边界已定位为运行中WebView与调试连接；权限差异因果未验证，不写根因已确认。

本轮Office四件重启与Contentpolicy九断言通过；receipt SHA分别 `e65a523ec1211dd5514d95bf9448ba26a17dc42b98d32043b5fc38509e39dc54` / `a467a204628067fbe3a948cd09ef816cc232352c18c0960ce988f70339cdcfc2`。当前source.changes仅四Tauri schema：从固定a320 HEAD各去一个末尾LF所得Git blob全部精确等于CI worktree_blob，故本轮dirty为生成换行变化；不能据此自动提升旧run的归因。证据根 `.project-local/task-runtime/aaos01-ci-artifacts/37320533049-a1/`。

本轮本地实现：archive成功后复用Core成员导入与排队，成员目录按job/attempt隔离；临时worker cwd保留浅层，修复实际候选暴露的Windows267深路径失败。Python与Core分别限制64MiB，真正截2000条清点；嵌套仅保留不递归，扩展失败记录machine失败。生产排队先RED（0而非2）后GREEN；容器3项/executor9项/有界来源任务API2项通过。权威a14 manifest SHA `e948876c84de37eed789cf0dadaa270170780d1ba5394b0f7d4a8f3893ab0792`，Core SHA `67f3b01dd5a103699db313489e95a7561847068ddf69e393cb8c3474f7081bd5`，uv.lock未改。A波次12样本真实Core执行/重启通过，其中WAV/MP4仅media.probe；ZIP真实自动成员原件/queued子作业/正文/锚点/损失/关系/CAS重启一致。最终receipt SHA `4e83a55d6a5a6ef02f199aed76493744b0a461dcf171b9b4ea898ebd53c721c4`，位于 `.project-local/task-runtime/aaos01-light/76c8d51443054987a0d0d1de45a5b42d/receipt.json`。

旧UI复用新增落位：活动坞改读有限source_jobs正典任务，API每来源最多50条且标截断，按20来源串行有界读取，失败清除旧快照；资料选择向既有Inspector传实际来源/SHA/版本，普通保存仍不冒充审核；复用Avalonia180ms导航淡入，减动禁用且不强制重建草稿。PNG/ZIP/Canvas/字幕/XML及媒体探测接已有worker入口，媒体/容器显示范围限制。前端全量183项通过，随后新增7格式入口定向全部通过，tsc/Vite通过；src-tauri全63项与fmt检查通过，Python打包相关38项通过。19502项打包文件SHA已核对并清release缓存后重建，新正式host SHA `e67780fa9d1b5c1f9c3c4cc28757a64a3c306099c41a73e24dc9d39755c5fb57`。本地真实WebDriver12步骤通过（4次自有会话启动，包含保存/重启/恢复/原创笔记/两独立维度/修订依据），receipt `.project-local/task-runtime/aaos01-webdriver/ef6f08dfe874489fb0ed3eb734deaa1d/receipt.json`。新官方webviewOptions显式本机debug参数已本地执行，不据此声称CI153根因或安装态已修复。本地结果不覆盖上方当前固定 CI 的安装态结果。

任务持续授权（用户2026-10-05明确授予，至撤销或任务结束）：允许提交、正常推送至 `codex/dsh-aaos-real-multiformat-loop-20261001`，触发 workflow_dispatch(force_full)、gh run rerun 与读取运行结果；等待固定 CI 时禁止推送。禁止 force push、改写历史、合并或直接推 main、发布 release。此授权不扩展至付费云端调用或真人认可。

本地实际重建包含品牌与九项线性图标的生产 Tauri host，SHA `696e6fc58d8569b15743819524acbd97e04bcc233cd0d1bd7387341c9c46494f`；构建前仅清指定release缓存资源，随后Core/profile分别匹配a11 `494493ab...faad820` / `79093169...e46ad`。候选内 `runtime/python.exe` 实际 import 四模块成功，仍不是installed qualification，未拉起窗口。Office/Contentpolicy收据补充变化公共源码路径、HEAD对象和工作树blob，不保存diff正文；实际变化识别和五项敏感路径拒绝检查PASS。新生成四schema经字节比对只有尾换行，精确恢复原字节；其patch SHA `f423b6089e64716c19950dda56f6ff335b0a6fbe4a5c22c0006e87e2ffcda679`不等于旧CI6087，旧dirty来源仍UNKNOWN。

历史固定提交 `6776eaec695254b9c3768b8c42190cec9bc9fc0c`，workflow `308098767`、run `37313542770`、attempt `1`，workflow_dispatch(force_full)，headSha 已完整读回。最终 FAILURE：18 个 job 实际 success，installer-lifecycle 与 a0-gates failure。desktop-fast 的普通保存与独立核验、真实 Office、Q12/导出/故障、Rust fmt/test 目标步骤全部执行成功；desktop-build 实际构建 NSIS 成功，不能代替安装态资格。

本次安装态第一次 POST /session 约60秒失败，DevToolsActivePort 不存在，steps=[]。typedartifact 已校验身份、非空 ZIP、CRC 与 SHA：native 包 `0af817deff5fe3227ff3fef6bfc028587756eafabe8cc67568d1d292c53aa04b`（6383字节）；native-driver.log 3596字节，driver.log 0字节不作证据。能力已带正确安装 exe 和独立 session-1 userDataFolder，匹配工具153.0.4234.48；因此此前目录分裂修复已生效，但不能解释或宣称修复此次失败。进程诊断自身超时，宿主早退、WebView创建失败及驱动连接失败尚不能区分。等待期间没有推送。

Office typedreceipt SHA `98e4db8e9f6e72ca1120acb6b806a3f456f7a9682054583f80503d2b7b7b5327`：正常 XLSX/PPTX succeeded，损坏两件 failed/AAK-WORKER-003，四件重启一致；实际产品解释器与 worker 同为 `.project-local/rt/runtime/python.exe`，真实 import openpyxl3.1.5、pptx1.0.2，uv.lock SHA 未变。Contentpolicy typedreceipt SHA `3588d2c71ae1d89074ccc617e7c549a66c99368d0bf44bb29fe08c356e3b54a7`：九项断言通过，含无 Source 保存、未核验搜索、权限、版本依据、实际 job SHA/位置、重启与独立恢复。两 receipt 的 source.commit 匹配6776，但 dirty=true/patch SHA `6087d25363e7462a66ca2dc25cb74fe9542eaad5c7369be287c16924a6a419a2`，未归因前不冒称干净候选。release-candidate 包下载180秒超时，保留失败收据和部分文件，不当完整产物证据。以上证据位于 `.project-local/task-runtime/aaos01-ci-artifacts/37313542770-a1/`；没有采集本 run 原始 CI 日志。

下面较早固定运行与候选记录按其原始 SHA 保留，不能覆盖本段最新失败结论。

品牌标识后续已从 Avalonia Assets 原字节复用至当前 React 顶部状态栏，源/目标 SHA 同为 `4dfa88385b608811d0166e5af6f41b86b6b3d44b1675cd06116d7d9daa5bc08e`；替换临时字符，按现行 Naming Contract 使用“星环知识平台”。素材随 Vite 离线打包，无外部图片请求。相关24 tests、tsc、生产构建通过；不提升为已部署 Green 或安装态证据。

后续实际复用 Avalonia `AaosIcon.axaml.cs` 的九项原始矢量路径，接入 React 主导航、二级导航和命令面板，替换几何字符；保留24-unit/1.7笔画 VI 与键盘行为。完整前端26文件176 tests、tsc、生产构建 PASS。此为源码和构建产物，尚未更新实际 Green；未声称菜单、动画全部复用。安装探针用 Win32 创建时间绑定进程元数据替代超时的 CIM，记录1/10/30秒与会话结束时的自有树、宿主存活及两profile存在性；只查询自有进程的 elevation 布尔，不读取访问令牌正文、命令行或浏览器正文。安装脚本在 WebDriver 前另存已完成的初始窗口/Core/WM_CLOSE事实。定向16 PASS、PowerShell parse/Ruff PASS；增强进程观察的真实本地12步窗口旅程 PASS（016dc5144a6345f2940b663e83b6388d，receipt SHA `1cc7a74de4a5f5ec1a9240eea226e9ec34929493745c9f0fd722f03d78ba3148`），四次自有 host/WebView 树采集无错误；后加 elevation 当前进程实际读回 false，该追加pytest受默认沙箱路径解析WinError5未执行，不伪报全项测试。随后通过平台审批按同一canonical入口完成包含elevation追加断言的16项回归PASS（aaos01-diag-delivery-approved），未改ACL或系统权限。远端安装根因仍 UNKNOWN。

固定修复提交 `ff17047289e7a7e77f947419da75353e45fcc79a`，workflow `308098767`、run `37302789036`、attempt `1`，force_full最终FAILURE：前18个job均实际success；installer-lifecycle和a0-gates失败。安装态新原生日志3355字节、SHA-256 `72308ba5d01cc11a18ec633144ea95a4bcb3c10812b7b283adf06cada7d108d0`，实际InitSession报DevToolsActivePort file不存在，steps为空，仍不是安装UI通过。匹配153.0.4234.48工具回执成功。等待期间未推送。随后确认probe环境覆盖目录与driver能力目录分裂，改为官方tauri:options.webviewOptions.userDataFolder单一目录；本机154匹配工具真实七项窗口旅程PASS（aaos01-webdriver/4cb75755b42e447980c224ab11326da0/receipt.json），两次握手1.344/1.297秒，远端充分修复仍待新固定SHA。

标准dev.py --pytest完整Windows回归3982 PASS、36 skipped、137 subtests PASS，exit0（aaos01-full-canonical-2150.log）。此前绕过--pytest额外嵌套临时目录的aaos01-os-final-full-2130运行45FAIL记录保留，不归因Q01、不冒称PASS。后续Language/RuntimeDelivery权威及引用20项定向PASS；宿主实现未再改动。

Q01现行PROJECT_CONTRACT及schema、Directory/Language/RuntimeDelivery/CurrentArchitecture按SUP-022同步正式React/Tauri有限桥，Avalonia仅供体参考；Rust Core唯一writer和Owner Gate保留。没有改写R6/M0历史或UI旧合同。

Q10后续显式修复：导出器不能生成无handler的archeaxis://可点击链接。保留用户原文投影、两固定文件及完整manifest，导出plain source/revision/anchor/position JSON记录并登记external_navigation_unavailable loss。真实Rust Router四项PASS，a10新Core实际两profile/文件读回/重启PASS（aaos01-exchange/ad8fba43066e405aa716960130d8342c/receipt.json）。a10 manifest SHA-256 `c149cb26e7dd7b9f061a2d6507dfdd39e568851524fd7c63d13117d6ad1b105f`，声明ff170但暂存时dirty，仅本地组件资格。原先Obsidian软件回执只覆盖旧正文和标签显示，不能覆盖新的导出或外部导航；外部导航仍未实现。

固定扩展提交 `7c5a9a0fd2a434ad431e83772d02b647a6d20011`，workflow `308098767`、run `37297859142`、attempt `1`，force_full最终FAILURE：desktop-fast/build成功；test、workers、contracts、lint、installer-lifecycle及a0-gates失败。已按用户限定授权下载该run失败日志，六份均非空并记录SHA，仅显示脱敏摘要。安装态首次WebDriver握手45秒超时，UI旅程未执行，根因UNKNOWN；不得由旧720提交全绿代替本次结论。等待期间未推送。

本次后续修复统一schema登记/$id、35挂载/58方法路径的真实路由合同、启动/重试Core安全断言、架构路径规则、CSV/TSV定位说明与真正loss的区分；有限宿主payload只接对象且默认空对象。针对性108测试及29子测试PASS，宿主62测试和fmt PASS。原生driver诊断日志纳入安装态artifact，首次握手独立有界120秒，失败仍非零，不声称超时根因已修。最新重建宿主真实WebDriver c023206cafe64edda23737a0946bff84完整读写/并发/重启/备份恢复PASS。新固定SHA门禁待执行。

当前较新本地worker候选a9 manifest SHA-256 `79cc58171213459badd2c93fdb185a65eaa1644c3a5a6da24f164892a7b6647e`，声明源7c5且暂存时dirty，仅证明组件实测。a8/rt为此前宿主验证资源，不冒称最终新SHA候选。全Windows pytest曾3971 PASS/8 FAIL，七合同类失败已针对性修复；一个深临时路径rmtree清理失败保留为本地fixture缺口，不声称全Windows测试通过。

固定提交 `72039249a41f9ea98e38542feefbf8f74e013317` 的 workflow `308098767`、run `37280918681`、attempt `1`（workflow_dispatch、force_full）已核对 headSha，全部 20 个 job 实际完成且 success。desktop-fast、desktop-build、installer-lifecycle 的目标步骤及 a0-gates 均 success，没有从 skipped/cancelled 推导通过。原始 `run.json`、分页 `jobs.json`、`summary.json`、非空 `logs.zip`（2,132,560 字节）和 `full.log`（7,280,220 字节）保存在本工作树 `.project-local/task-runtime/aaos01-ci/37280918681-1/`。首次官方日志下载 90 秒超时并显式报错；同一绑定补采成功后才采纳结论。运行期间没有提交或推送。此 CI 只证明该固定提交，不能覆盖随后未提交的 Q04–Q12 扩展。

任务编号和完成条件以 `docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md` 为准。本文件维护既有 AAOS-01 切片当前状态；不可变任务包仍是执行规格，不是完成证据。历史回执保留原始候选、SHA 和能力范围，不自动提升为本轮或安装态验收。下述扩展已完成本地验证，尚待新固定 SHA 的完整 CI；不得由前述 72039249 的结果覆盖新代码。

本轮起始 HEAD：`37bfe872ccbaed88a4825b8ff939ccf94aef8b92`，开工工作树 clean。已验证源码提交 `59b829d7724c2a1e3210e07d287ea9eb68722d4c` 的完整 CI 已执行：两桌面门禁成功，旧 NSIS 验收契约失败，因此完整运行 FAILURE。安装契约修复后的固定提交与最终 CI 结果须读回后登记；不得由 cancelled/skipped 运行推导通过。

## 2026-10-05 产品保存原则实施与体积治理

顶层 `PROJECT_CONTRACT.yaml` 与对应严格 schema 已纳入用户本日修正，权威索引/当前架构同步，普通保存不以外部 Source/Evidence、云端复核、专业支持或人工认可为门槛。不是取消鉴权、正典结构校验或专用知识认可流程。原创 Document 的 source 字段可为空；已有来源双字段仍必须成对且验证真实 CAS。schema10 非空迁移保留原有来源/版本/块，schema11 核验记录由同一 Rust/SQLite 写者管理。

识别忠实度与专业依据独立、绑定实际版本和内容 SHA；问题位置与真实完成 job 输出 SHA 校验，修订依据关联历史版本/check。云端申请当前 **pending / not_executed / execution_verified=false**，尚未接通真实模型和联网检索，不能据此宣称完成云端核验或专业自动论证。manual 记录明确为手动报告，不冒充专用真人认可。改版不继承旧结论，历史记录分页可读；普通文档可搜索/阅读/编辑。

本地三模块 Rust 回归 306 PASS，非空10→11迁移/真实job/1001条核验分页/独立备份恢复通过；前端172 PASS、tsc/Vite PASS；合同81 PASS及29 subtests。独立产品解释器 a11 真实 Core probe `aaos01-content-policy/b682754152484eb7aa8d7c1cb9a1249d/receipt.json`（45,871字节，SHA `dbcc878dd97631de93ce8fcce3e8d5be15691828b447b732e820c0decfb968d5`）9断言通过；原创无Source保存、pending不丢正文、人工疑点位置、修订历史、重启及独立restore/CAS一致。属于真实本地集成，不是安装态或真人认可。

完整Python回归 `aaos01-policy-full-final.log` 实际3979 PASS、4 FAIL、36 skipped、137 subtests PASS。四失败分别是当前语言边界文案精确引用、增加核验路由后的第二份计数断言、探针XPath被绝对路径守卫识别，以及README遗漏开发版本锚点；已做最小真实一致性修复，保留所有守卫，定向39 PASS（aaos01-full-failure-regression2）。该旧完整运行仍为FAIL，不写成新全量PASS；后续固定SHA完整CI必须实际执行验收。

同一 a11 Office probe `aaos01-office/072df220fadb49c38a1d30c083ab70f1/receipt.json`（43,527字节，SHA `0370e807f2390b78ccece998fb624a4fe0f73258659129f1492a3156e18ad517`）：XLSX/PPTX正样本成功，损坏两例failed符合预期，4/4重启一致。a11 manifest `34d5662561223b43c2adbb4561d51051b5b5c467be621b7c7591a597adf90d99`，Core `494493ab150c1d3f852ed7a4b80fd31f06cc8822c9cb235dd6135f116faad820`；uv.lock未改。来源为ff170加dirty diff，各receipt保留patch哈希，不能提升为固定SHA证据。

a11 真实 Tauri 窗口旅程 `aaos01-webdriver/e4236d2bedb44a5882f2c03b480feb08/receipt.json`（30,348字节，SHA `6c6b8c7da8711f81057b248034e366b56865ae9e960992d73ed7abdfc3ada3a2`）12/12步骤PASS，宿主SHA `d7e3d4e1993edca20d36925090d1c1e503a52965e054acc58e580b8bfe5477d9`、target Core/profile与a11一致。新增五步写入由真实WebDriver界面操作，Core只读取对账；手动记录为工程样板，云端未执行。早先失败回执保留，恢复后的UI状态须冷重启才握手。后续两个未保存文字竞态已取得真实RED并修复：内部关闭/切换显式保护dirty，create/read/restore晚到响应校验编辑generation。定向18 PASS、完整前端176 PASS、同锁tsc/Vite PASS。最终宿主SHA `750a226bb8d658922a830c3cbfb867591324c2e9a2c5ac7a2df729d6257dcee3` 的真实窗口重验 `f1ba9492e2e84c1691b9514b33a0b39d/receipt.json`（32,557字节，SHA `7c7d3d0c4351c2a673c1e4f40bc7bd84e17baae86795d4f663f8573a9c4f471d`）12/12 PASS；四次会话各用独立driver-owned WebView profile，同一Core数据根重启读回，四host退出确认。先前prefs文件写失败保留；竞争锁的原因仍为推断，未自动重试掩盖失败。

三份已失效旧台账原字节归档25,089字节、SHA相等，原路径兼容入口保留；唯一当前状态仍为本表。README及GitHub About/topics按现行Tauri/React + Rust Core和独立两维核验更新；默认分支README未因About更新而自动落地。旧内容与库不删除。历史28项已删路径仍不存在，合格未执行旧清单为空，28个归属不明数据库保留。本批仅清理12个已核实Cargo缓存子目录，14,060文件/4,241,169,479字节逻辑载荷，逐文件SHA清单非空、12/12删除后独立absent；运行Python、父目录、deps、数据及历史程序保留。另对 a8/a9/a10 历史 Python 副本先按精确文件/目录清单从保留 donor 真实重建并全树SHA相等，再删除3份 runtime；其Core/worker/shared/清单/回执保留，历史候选冻结为须按已保留recipe恢复后重运行。两批成功逻辑载荷合计6,117,890,639字节，证据/recipe新增29,106,016字节，时点净逻辑减量6,088,784,623字节（其他小文档变化另计）。物理磁盘释放量与用户所述全项目100GB/Green几十GB尚未全量测量，不重复累计历史69.83GB。执行路径与保留项详见现有清理文档，未新增第二份状态真值。

## 当前状态与剩余缺口

| ID / 权威任务 | 当前状态 | 已有证据与实际剩余缺口 |
| --- | --- | --- |
| Q00 现场保护与最小对账 | PARTIAL | 已复核起始 SHA、工作树与工具路径；本轮使用独立候选及全新 Core 数据根。未知用户资产、旧库与历史回执保留；完整资产/schema/writer 身份不因本轮格式测试自动完成。 |
| Q01 重构决定与目录登记 | TESTED_LOCAL | 已有 SUP-022 重构登记；本轮统一使用权威 `stage_backend_runtime.py` 产出候选，desktop-fast/build 使用相同准备步骤。此项不是旧编号中的“打包完成”；现行Directory/Language/RuntimeDelivery/ProjectContract及schema已按SUP-022最小同步，schema/引用回归PASS。 |
| Q02 Tauri 启动与只读桥接 | TESTED_LOCAL / PARTIAL | 最终 src-tauri fmt --check PASS，cargo test 62 PASS/0 ignored，加1项有限核验分页边界测试5/5 PASS，包含真实候选解释器及统一首次启动/重试选择。最终05bda宿主正式owned attach完整12步及四次exit0、独立WM_CLOSE实际PASS，见上方非空收据；独立安装态完整桥接仍待新CI。 |
| Q03 类型合同与权限 | PARTIAL | 既有启动契约、前缀隔离与权限测试保留；本轮未将单元测试提升为全部 DTO、对象权限与版本错误验收。生成合同、有限命令与对象范围需按任务书逐项读回。 |
| Q04 原件与文档保存 | TESTED_LOCAL / PARTIAL | 已实现 schema11 CAS 原件、Document/Block、同事务 editor JSON/正文投影、稳定 block IDs、未知节点保真、乐观锁409、旧版本读取及恢复生成新版本；真实 file-backed Store/API 回归通过。25个约1MB文档的目录改为六字段摘要，全workspace --locked回归已PASS。独立备份演练继续见Q11；不能从API代推installedUI。 |
| Q05 阅读与证据样板 | TESTED_LOCAL / PARTIAL | Tauri 已接有限命令、PDF.js、Tiptap、稳定块与版本、canonical引用；复用旧 Tauri DataTable/Section、Avalonia 来源链/折叠处理记录与导入回执布局。前端26文件176 tests、tsc、production build PASS；真实窗口中文阅读/保存/重启 PASS。物理IME与installed qualification未完成，PDF页锚点未伪写located。 |
| Q06 A 波次多格式吸收 | TESTED_LOCAL / PARTIAL | a14独立A矩阵12/12通过，ZIP已走生产成员子任务：TXT/PDF/PNG/DOCX/XLSX/PPTX/HTML/Canvas/SRT/ZIP真实Core/worker/3产物/定位事实/损失及重启；PNG真实OCR文本、词boxes、stdin图像SHA已核实。矩阵WAV/MP4只media.probe头信息；另a14合成语音真实ASR与静音负例/重启通过，ASR时间锚点a15 debug真实验收通过；播放器/合成语音原生闭环见当前增量；视频解码、真人质量及安装态仍缺。Office正/损坏四项均按预期成功/failed且重启一致。安装态逐格式与已知原生locator限制保留。 |
| Q07 候选审核与纠正 | PARTIAL / AWAITING_OWNER | 新版审核同事务绑定实际knowledge version，过期409、machine403工程测试通过。已从权威任务书真实Source/job/transform摘录创建一个未接受候选，等待用户明确决定；工程设置human principal不当真人审核。 |
| Q08 学习与 AI 资产闭环 | TESTED_LOCAL / PARTIAL | assessment/FSRS/幂等事件/机器任务/纠正入口已接有限Core。真实本机qwen3.5-4b经Core与候选worker回答公开工程夹具「37」，实际模型/提示版本/知识版本/任务及完全重启读回一致。该夹具审核明确AUTOMATED_FIXTURE_REVIEW_NOT_G4_HUMAN，结果unmeasured；真人决定、真人答案与纠正旅程仍缺，不虚构错误或效果。 |
| Q09 搜索与完整能力目录 | TESTED_LOCAL / PARTIAL | 正典检索/审核页已接Core；从唯一CAPABILITY_ATLAS_V2.yaml与capability-map生成16个CAP目录及两源SHA，未来能力可浏览，握手/权限/调用证据分开，未匹配旧数字ID不伪造join。九个主导航复用正典页面与旧壳；生成检查/前端回归通过，完整真人检索旅程仍未验收。 |
| Q10 导出与首个互通 profile | TESTED_LOCAL / PARTIAL | a14真实Rust Markdown/Obsidian固定两文件包、完整Document/未知节点/锚点/损失manifest、独立磁盘回读与Core重启导出相等通过。宿主有限导出仅写产品资料目录，无UI path输入。a14新版导出在独立Obsidian实际窗口回读已知正文、Source身份与Evidence records通过（本表上方新收据与截图）；未知节点在manifest保留，external_navigation_unavailable loss明确，外部引用导航仍缺。 |
| Q11 备份与副本恢复 | TESTED_LOCAL / PARTIAL | 现有Store一致live backup→全新独立DB与CAS副本恢复→完整文档/版本/原件读回→继续编辑/第二次重启全部PASS；原生host恢复与retry同一Core、版本3→2、CAS一致PASS。备份哈希/manifest与源CAS严格核验，损坏回滚测试通过；实际SQLite3.51.3（rusqlite=0.39.0），全workspace --locked回归PASS。安装态独立副本资格仍待。 |
| Q12 B 波次轻量扩展 | TESTED_LOCAL / PARTIAL | a9独立13/13（aaos01-light/2b89a2fce76a4a67b8c0226b59b9b995/receipt.json）：CSV/TSV、JSON/JSONL、YAML/TOML/XML、EPUB、EML九项，各有实际结构/原件SHA/输出字节SHA/锚点/损失/导出/重启；坏EPUB、unsafe YAML、XML DTD/外部entity、坏JSONL四项failed且无输出。EPUB章节/段落/nav/资产SHA和EML头/正文/附件SHA已逐样本断言，附件未独立解析明确loss，EPUB Core原生定位仍unverified。没有用Q06代验，安装态扩展资格仍待。 |
| Q13 性能与故障验证 | TESTED_LOCAL / PARTIAL | 真实Core四故障场景无产物且后续正常job恢复PASS；20次真实Tauri新进程/新Core根/新WebView profile启动，预先3s/1GB预算下P95=1.422s、完整自有树最大468340736字节PASS（OS磁盘缓存保留）。创建时间绑定父子进程排除旧父PID重用；CDP观察器不计入产品内存，退出命令清理不冒认WM_CLOSE。无观察器的WM_CLOSE独立PASS；安装态整机故障旅程仍缺。 |
| Q14 Windows 安装态资格化 | FAILED_CI / PARTIAL | 本地构建、候选完整、Rust/Python 测试和 CI 均不能替代独立安装包的真实桌面旅程；尚无 Installed Qualified。 |
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

历史本地候选：工作树 `.project-local/a8` 与 `.project-local/rt`，manifest SHA-256 `5bd3e69f30b7e432b98e871e7d42f906b67e7c57fb16723839fc62e1765438c0`，Core SHA-256 `5e5cb4f6b1afe27c1eec05c892d9e5e6a5c8e1f9457fc0b7c4e674d1045b6b4c`；解释器 `runtime/python.exe`，Python3.12.13。候选声明源为72039249且实际暂存时worktree dirty，仅是本地组件实测，不能伪称新提交的exact源码候选。既有uv.lock导出/install的a3干净donor经权威暂存器进入runtime，未重复增加Office依赖。锁SHA-256 `0F73EA804B0ECA61A251013D199F75D88F35E6322BB155EB2581B8D10F69CE52`；新CI将以新固定SHA重新准备候选。

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
