# AAOS-01 Q00–Q15 当前执行台账（2026-10-05）


## 当前结论（2026-10-06）

最新固定资格578d06b784139e86c685191ecc7d0ccdd021fb27 / workflow308098767 / run37399470467 / attempt1 已终态SUCCESS，全部20项job实际执行成功，包括desktop-fast、desktop-build、installer-lifecycle与a0-gates；等待期间未推送。官方release-candidate artifact11384832309已完整下载193,116,309B，ZIP SHA17c1a886cf7c4364373330ef3a4a73114bd1de4aa8ca5834e20a53611c2c952f，四成员CRC及固定SHA/workflow/run/attempt绑定PASS。Office四样本与保存政策九项目标断言已逐项核验，不只读取ok字段。源码资格不代替Green部署或真人/云端验收；新候选实际解包与运行验证继续执行。

本地新增识别核验：PDF通过现有锁定pypdfium2将不可变原件全页栅格送入现有模型Adapter，限64,000B原件、1–3页、8M像素与64,000B合计PNG；超界明确失败，不截取首页冒称全件通过。原件/页序/各页SHA/实际renderer版本进入engine receipt。识别忠实度的辅助搜索失败、无结果或截断单独留状态，可继续对照原件；专业依据分析仍保留自身失败/不确定语义。正式Python54项PASS（SDK/检索为SIMULATED，PDFium实际渲染），格式化后四worker套件52项再验PASS；新增SQLite重开回归1项PASS、Ruff与cargo fmt --all --check PASS。云端图/PDF模型实调NOT_EXECUTED；音视频原件云端fidelity仍不支持，实际本地ASR/抽帧识别不代替该维度。

最新清理已执行：仅既有审计清单中的934项再生Cargo中间文件实际删除525,695,796逻辑字节，全部选中路径ABSENT，26项PDB与程序/源码/恢复材料守卫不变。收据aaos01-tools/cargo-2611-934-cleanup-10e099d68bb2424ab21ffb77d0a1ecd4.json SHAa996b9f4615abdabf69f8ce7286a92acba8c4a12f755f883956eff441db84929，物理净回收UNMEASURED。Green80324项旧公开载荷续清已完成，详见下方稳定恢复目录收据。新媒体候选Green部署与原生UI增量待成功固定CI后执行；未改旧默认入口、未合并main或发布release。

26个当前SHA PDB已另行完成完整CRC与逐文件实际解压SHA/bytes验证后精确删除，342,310,912逻辑字节、26路径全部ABSENT，34项程序/源码/恢复守卫不变。稳定恢复目录.project-local/recovery/cargo-msvc-pdb-latest-20261006，ZIP76,279,893B SHA01903cf8b42e0e3a24dd11bb06faee1363293846075c03364fccdf2a61347c81；实际删除收据prune-26-pdb-4f5d600733f74c72ab8de5b53b1d5290.json SHAd896062fb8daf320afa64b631801f4e8c4e3c9548ebee3edc466ca5432b5cd51。既有1296合成案例/3960成员仅核对历史精确prune覆盖且全部ABSENT，未重复删除或累计。物理净回收仍UNMEASURED，未知资产与恢复材料继续保留。

路径/权威/报告定向收尾（2026-10-06）：文档与RuntimeDelivery入口对齐AAOS-01/SUP-022，共享资源索引明确当前Rust实际路径及旧DP边界的历史身份，Formal分支与Green描述区分源码/已部署对象，旧归并评审已标历史。47份Q02均已有历史替代头，不重复归并；相关五套权威/合同测试26项PASS，git diff --check PASS。首个测试启动命令错误与沙箱WinError5均保留失败记录，正常项目权限复验通过，未改ACL。该结果是本轮已识别具体漂移的收尾，不声明未知资产归属审计、完整旧库语义迁移或主线合并完成。

固定578d安装包本地已完成严格解包：21727个登记成员逐SHA/bytes、无额外成员、NSIS真实宿主/manifest与release-identity绑定通过；收据aaos01-tools/unpack-578d-ad69fe4b56b649ebbc39a9fdf1edf948.json，状态PASS_EXTRACTED_NOT_RUNTIME_QUALIFIED。仍未本地启动、部署新Green或通过新媒体安装态；不要把此状态提升为安装完成。

Green文档镜像核对（2026-10-06）：AAOS-01的dated权威文档镜像位于 `D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS01-文档同步-20261006`，清单 `docs/current/AAOS01-DOCUMENT-SYNC-20261006.json` 逐项登记10份镜像文件的SHA-256与字节数并记录源提交绑定。本轮修正了该绑定原先指向不含全部所哈希内容的提交，并复验Formal工作树与Green副本10项全部一致、清单自身双端字节一致。Green不是Git仓库，此镜像仅镜像文档，不代替Formal权威，不证明软件、默认入口或用户数据已迁移；与该镜像相关的docs-only运行不产生新的桌面资格，新候选本地启动与Green部署见下两段实测。

578d候选本地原生闭环与Green部署（2026-10-06）：在578d解包stage上实际启动宿主并跑canonical原生21步。首跑17/21死于 `AAK-WORKER-003 tesseract binary not found on PATH`，根因不是缺引擎而是外部根环境变量未设：`scripts/runtime/dev.py external_toolchain()` 仅在 `OS_EXTERNAL_CONFIG`/`ARCHEAXIS_EXTERNAL_ROOT` 已存在时才做发现，引擎实际位于共享根 `10-toolchains/scoop/apps/tesseract/current`（本机 scoop shim 已过期，故意跳过）。仅对子进程设置该变量后复跑；第二跑19/21，step 20 `ui_click("来源引用", …)` 返回 WebDriver stale element reference（该探针 ui_click/ui_type 全无陈旧容错，属探针竞态而非产品事实，失败收据 `aaos01-webdriver/a42e1f83381f4f46881f26821b56ae54` 保留），未改动探针直接第三跑21步全通过，收据 `aaos01-webdriver/0a442dac222f4faea307373c6cd5825a/receipt.json`（538,104B）SHA `eddac86e54dcf4a3789ee6a6e64013ee7aad4552c21b9888a9ad7e5c78733c40`，ok=true。随后 `green_tauri_preflight.py --check-only` 严格PASS，`green_tauri_apply.py --apply` 增量部署到独立目录 `D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS-Tauri-578d06b78413`：21,729文件逐SHA/bytes双次核验、全新 `data` 根、目录内启动器 `启动Tauri候选.vbs` SHA `9c1c73017849a7822d0ed168eb4a68db3ad939174ad021d818c97a97100c3f16`，`old_green_unchanged=true`，宿主SHA `00b7ba9b187b305d650458a424604dac1a38631e5ec5e7c57d8837a1c9b1f077`、载荷清单SHA `5d9eb139c5556b383351d0d114f386b762b7085ed697e16d52f315c356acfee1`，收据 `aaos01-tools/green-apply-0a2d29f9ffe6483c9d522086fac6f0b2.json`（1,255B）SHA `4520438a61bff9f73d25c83e65c2442aaac20a27dd3f6555e8cb72cada20f216`，状态 `COPIED_HASH_VERIFIED_NOT_RUNTIME_VERIFIED`——该状态在下一段实机增量前不得读作已部署合格。

部署后安装态新媒体/Inspector增量（2026-10-06）：在 `AAOS-Tauri-578d06b78413` 上以23步增量探针（非canonical21身份，绝不与之混记）实跑三轮。Run3 停在 Ctrl+Alt+I 前置断言（9步，收据36,499B SHA `e0b51474baf0ec17708cf16daab47c1df63fc10299cb14ac5562b72ca31203ac`）：失败截图显示检查器面板本就展开，`App.tsx:75 inspect()` 每次选中都会展开，故这是探针前置假设错误而非产品缺陷；改为先用产品自身的 StatusBar 触发按钮归一化到折叠态再测量。Run4（21步，收据573,362B SHA `951566d7296e798fb6ebbd1c8a07cd31a66c5fa15252ce5e885c2d01a9af1aaf`）真实可信键盘 Ctrl+Alt+I 两次展开/折叠 PASS（`inspector_precondition{initial_aria_expanded:true,collapsed_via:status-bar-trigger}`，编辑器焦点/正文/持久版本不变、零API写入），未保存历史扩展观察到真实并发版本冲突并保留实际键入草稿；随后停在 `local_media_ui_extension` 诚实性门禁：实测进程链为 `core/archeaxis-api.exe → runtime/python.exe 调度器 → runtime/python.exe 工作器`（全部 `candidate_profile_match=true`），而视频分支要求“python 祖父进程”，在 SUP-022 Rust Core 派生调度器的架构下不可能出现；改为要求链根是属主候选内的 `archeaxis-api.exe`（仍保留观测元数据、创建时序与候选SHA核验强度），并对 Run4 留存观测离线重放得 VERIFIED。Run5（22步，收据570,902B SHA `b68a30f920d9d84e3d7a1f4604a8e31eae19093908841aa1034ffecc1478f1ce`）真实视频原件（26,011,980B，输入SHA `73321c400d61a6449471181709e73f9521c91fc0d313158f2edc9313ff398558`）经默认UI按钮完成：job `read_ab9a2c22-fe0a-49f7-936a-4b993eb4ef30` 99秒 succeeded，22条原始线索/16条合法定位/6条越界疑点全量保留不冒充可靠锚点，4个视觉产物按原件字节SHA回读相等，时间锚点 checksum 匹配，整宿主重启后质量/CAS/锚点相等且未新建 job，观测解释器确为候选自带 `runtime/Lib/site-packages` 的 faster_whisper/ctranslate2/av（Python 3.12.10）。同轮真实音频（约12分钟MP3）在301秒失败，Core 记录 `worker execution deadline exceeded`：前端已按上限请求 `deadline_ms=300000`，而 `crates/archeaxis-api/src/runtime/mod.rs:474` 与 `crates/archeaxis-application/src/executor.rs:368` 把上限硬编码为 300_000ms，长音频CPU ASR 在产品路径上结构性无法完成——这是产品边界不是探针缺陷；抬高该安全上限属边界变更，未自行执行，留待所有者决定。三轮均自有进程与端口全释放，Run5 七次宿主正常 exit0；三次失败/部分收据全部保留。

历史版本 Inspector 最小复用（2026-10-06，提交 `6ab5caaf`，CI run 37407829399）：先只应用测试hunk得RED（`CanonicalLibrarySpace.test.tsx` 1 failed/22 passed，另两项竞态守卫用例在修复前即通过，故RED只计真正新增行为），再应用源码得GREEN 23/23、全量前端 34文件246测试与 `tsc --noEmit` PASS。语义为：历史读取回执绑定 generation/request 与被请求文档的 document_id/version/content_sha256，晚到回包不得覆盖新文档 Inspector；Inspector 报告历史目标自身的正文指纹，仅当 `source_id+source_revision` 命中已登记来源时才出示原件CAS哈希，正文指纹绝不冒充原件哈希；不改动草稿、最新版本与只读语义。CI run 37407829399 终态 SUCCESS，但按变更分类仅 gateplan/lint/browser-smoke/a0-gates 实际执行，rust-vnext/desktop-build/desktop-fast/installer-lifecycle/workers-vnext 等15项 skipped，故本次既未产生新候选也未获得任何桌面资格；该修复的真实窗口核验必须等待包含它且实际执行构建的完整运行。为此在23步增量中新增实窗步骤 `inspector-history-target-extension.py`（旧候选 RED 已实测：收据 `aaos01-webdriver/bea3c8ff05e84d469ea9041623cecdd4/receipt.json`，547,355 B，ok=false，21步，未保存历史证明已存在后在“只读查看历史版本”处断言失败，实测面板文本仍为当前文档“状态已保存…版本2…正文指纹 2a0996…”，正是缺少该修复的旧候选应有的表现），新候选部署后同一断言即为该项验收。

界面多维审计与修复（2026-10-06）：五路并行只读审计（设计令牌/视觉债、无障碍、交互状态完整性、UI↔Core契约真实性、响应式与测试覆盖）后只修可验证项。最严重发现是主机传输边界：`src-tauri/src/core_bridge.rs` 的超时表未列 `JobExecute`，落入默认30秒，而前端请求 `deadline_ms=300000` 且真实视频任务耗时99秒——任何超过30秒的媒体任务都会被主机提前中断并在界面报“转换未完成或产物读取失败”，而 Core 实际持久成功；已抽出 `transport_timeout()` 使该边界可断言，`JobExecute` 取320秒并新增回归测试（`cargo fmt --all --check` PASS）。其余修复：`CanonicalLibrarySpace` 的 `openDocument`/`restore` catch 缺 generation/editGeneration 守卫，被取代的旧失败会覆盖新文档成功态，已加守卫并新增“被取代读取失败不得污染新文档”用例；标签真实性——`sources_list.source_revision` 由 Core 从 sha256 列填充（`crates/archeaxis-api/src/documents.rs:180`），界面却写作“来源版本”且与相邻“原件 SHA-256”同值，改为“来源版本（原件指纹）”，`knowledge_v3` 的 `title` 实为 `knowledge_type`（`crates/archeaxis-api/src/lib.rs:1738`），候选标题改作“类型 …”；无障碍——状态栏后端徽标补 `role="status"`（后端转不可用/任务完成此前对读屏完全静默），“当前空间”由被AT丢弃的 generic `div[aria-label]` 改为 `role="group"`（保留既有 `getByLabelText` 真值断言），SettingsSpace 浏览按钮可访问名原为单个“…”，检查器新增 Escape 关闭与面板内×关闭后焦点归还触发按钮（此前焦点掉回 body）；视觉与布局——补齐此前完全无规则的 `.inspector-heading/-title/-details/-empty`（全局 margin/padding 重置后11组 dt/dd 挤成一片）、`receipt-grid`/`inspector dd` 允许64位指纹换行、声明缺失令牌 `--ax-bg-inset`、修复 `aria-current` 项自带 box-shadow 压过 `button:focus-visible` 导致选中项无键盘焦点环、≤900px 不再 `display:none` 删掉资料库唯一分区切换器而是收窄保留；命名合同——恢复页品牌“星环知识”改回合同全称。前端由 34文件246测试增至 35文件250测试全绿，`tsc --noEmit` PASS；本段新增断言在撤销对应源码修复后全部实测RED（反向验证），不以推断充当修复证据。审计修复分两次提交：`7a4d6bfe`（界面审计项）与 `20b30116`（写串行化）。

审计确认并已修的第二项BLOCKER（提交 `20b30116`）：建立版本化草稿、新建原创笔记、读取并恢复版本、两种导出与引用当前页均无在途守卫，双击会各自再持久一个文档/版本/锚点/导出；现由 `singleWrite()` 串行化并在途禁用，DocumentEditor 的 cite 同样加锁（其 save 早已有 `saving` 守卫，审计该条为部分误报，已按实测修正）。新增“在途二次点击只发一次写”用例，撤销守卫后该用例实测RED、恢复后GREEN。验证：前端 35文件250测试全绿、`tsc --noEmit` PASS、`vite build` PASS；宿主 `cargo fmt --all --check` PASS，`cargo check --manifest-path src-tauri/Cargo.toml --tests` 与 `cargo test --manifest-path src-tauri/Cargo.toml --bin ArcheAxis core_bridge` 10项PASS（含新增超时断言）。本地首次以 `dev.py` 直接调 cargo 失败于 `link.exe` 命中 coreutils link(1)（“extra operand”，WinError 归类为PATH解析而非产品或权限问题），改为先 call 共享根 vcvars64.bat 再执行；`src-tauri` 被 workspace exclude 且无 lib target，故 `-p archeaxis-desktop`/`--lib` 均不适用。构建副产物 `src-tauri/gen/schemas/*.json` 被本机重新生成，已按 HEAD 还原未提交（该再生成行为本身是已知噪声）。

审计确认但本轮未修（记录不粉饰，均待后续切片）：`CheckPanel` 写成功后紧随的回读失败会误报“核验记录未确认”；`JobContent` 失败任务只存在于折叠 details；`api/core.ts` 将400/404/422/500 全塌缩为同一句“本地核心未完成此操作”；`MediaReader` 元数据到达前的 seek 请求被静默丢弃；`--ax-fg-quaternary #737373` 实测对比度4.30:1（面板4.15、`#121212` 上3.95）低于4.5:1；无浅色主题（`color-scheme:dark` 固定且表面为叠加白 alpha，属结构而非开关缺失）；`Inspector/CanvasBoard/RealData/CommandPalette/SpaceView/SettingsSpace` 无组件级测试，且 jsdom 无布局引擎，故窄窗/系统缩放类缺陷当前不可测（`tests/test_aaos_narrow_layout_contract.py` 解析的是 Avalonia 供体 XAML，不覆盖本界面）。本轮全部前端与主机修改尚未进入 578d 部署候选，不得据本地测试声称安装态已修。

本轮我自己造成的CI回归与纠正（2026-10-06，如实记录）：把 `.context-subnav` 在≤900px改为可见后，push 的 CI run 37413006960 失败于 REQUIRED gate `browser-smoke`（`scripts/a0_browser_smoke.py` 几何合同要求手机视口 `context` 必须不存在；`desktop-fast` 与 `lint` 同跑PASS，故宿主改动本身在CI编译通过）。已按“真值测试优先于新功能”处理：不改合同迁就改动，而把让位范围收窄到 601–900px 带并在≤600px恢复隐藏（提交 `1cc51f9a`）；随后用共享 Chromium 在本地实跑该合同脚本得 `status=PASS`，四视口几何为 1440/1280 context=true、390/360 context=false、全部 `scrollWidth==clientWidth` 无横向溢出，收据 `aaos01-tools/a0-smoke-shared-browsers.log`（同时如实记录 `worktree_dirty=true` 与 diff SHA）。601–900px 带不在 A0 合同覆盖的四个视口内，故该带的实机表现仍未测，归入下述覆盖缺口。

审计复核后判为误报或归属他处的条目（避免以讹传讹）：`MediaReader` “元数据到达前的 seek 被静默丢弃”不成立，`onLoadedMetadata: locate` 会在元数据就绪时重放当前 seek，`useEffect([seek,url])` 亦覆盖后到情形，未作修改；`DocumentEditor` 的“保存草稿”早已有 `saving` 守卫，仅 `cite()` 确无守卫，已随写串行化一并加锁；`MachineAnswerPanel` 并未渲染 `knowledge_version`，硬编码 `<id>@v1` 实际位于 Core 回执 `crates/archeaxis-api/src/runtime/colearning.rs:39`（以及 :348），属 Core 侧真实身份缺口而非界面误标，本轮未改 Core 合同，留作独立切片；`spaces.ts` 的 intake/vault/exchange/settings 描述在桌面分支 `SpaceView.tsx:45-61` 实际渲染为 Canonical 表面，措辞与能力不符属实，但修正需同时改动 SpaceRail/CommandPalette/ContextNav 三处渲染与既有断言，未在本轮草率合并。

状态与标签真实性修复（提交 `5c2237e2`）：`CheckPanel.record()` 此前把已成功的核验写入与紧随的回读放在同一个 try 中，回读抛错即向用户宣布“核验记录未确认”，而写入实已持久；改为写入成功即刻如实播报、回读失败单独说明，并新增“仅回读失败不得冒充写入失败”用例（撤销修复后实测RED）。`JobContent` 的 `latestState` 被赋值却从未渲染，最近一次任务失败时界面毫无显示；现给出可见状态且不暗示此前结果不存在。`api/core.ts` 把400/404/401/403/429/5xx 全塌缩为“本地核心未完成此操作”，现按类别与操作名分别说明（`CoreBridge.test.ts` 新增四状态区分断言）。前端由 35文件250测试增至 35文件252测试全绿，`tsc --noEmit` 与 `vite build` PASS。

设计债清理（提交 `f3417b38`）：CanvasBoard 的 10 个类名此前 9 个无任何 CSS 规则（画布节点退化为裸定位文本），活动坞展开体亦无规则导致多行挤成一段，现均按令牌补齐；`--ax-fg-quaternary` 由 `#737373` 提升为 `#808080`，使其实际用点对比度自 4.30/4.15/3.95 升至约 4.8–4.9:1（达到 4.5:1 正文下限，且未触碰 MonochromeThemeContract 钉住的 `--ax-accent: #f5f5f5` 等断言）；新增 `StyleRuleCoverage.test.ts` 护栏，要求 CanvasBoard/ActivityDock/Inspector/StatusBar 的静态类名都能在 `tokens.css` 或 `content.css` 解析到规则——用修复前的 HEAD 样式表离线实测，该护栏会报出 9 个缺失类名（真实RED）。前端 36文件256测试全绿、`tsc --noEmit` PASS。仍未清理：仅存在于媒体查询内的死规则、声明未使用的令牌、图标双轨（AaosIcon SVG 与原始字形混用）、桌面分支与 `spaces.ts` 能力描述不符、以及 CanvasBoard/RealData/CommandPalette/SpaceView/SettingsSpace 的组件级测试缺口。

桌面能力描述纠正（提交 `a29e9736`）：`spaces.ts` 的 导入/知识库/交换/设置/工作台 描述沿用网页遗留措辞（“URL、文件与批量多格式导入”“本地笔记、搜索与画布”“开放交换包的导出与验证”），而桌面分支 `SpaceView.tsx:45-61` 实际把它们路由到 Canonical 资料库/知识/能力表面；新增 `spaceDescription()` 在桌面外壳内给出实际能力描述（网页开发模式保持原措辞），并接入 SpaceRail/CommandPalette/ContextNav 三处渲染与检索别名，新增 `SpaceDescription.test.ts` 双向断言。前端 37文件258测试全绿、`tsc --noEmit` PASS。

Core 回执版本字段：尝试、被证伪并已回退（未留改动）。界面审计指出 `machine` 回执的 `knowledge_version` 由 `format!("{}@v1")` 合成（`crates/archeaxis-api/src/runtime/colearning.rs:39` 与 `:348`），曾改为该知识的真实 `knowledge::review_version()`；实测 `cargo test -p archeaxis-api` 使 `contract_machine_answer` 3 项失败（147/264/273 处对状态断言失败，即端点转为错误状态，`review_version` 对回执所服务的 id 不成立），回退后该套件 8/8 PASS。结论：该字段是回执的**版本标签约定**而非伪造的正文哈希，替换它属于契约变更而不是本地修复；界面侧也从未渲染该字段。若要让回执携带真实复核版本，应新增字段而非改写既有语义，属需所有者裁决的契约变更，本轮不实施。用于跑该套件的本地口令：`cargo test -p archeaxis-api` 需 `ARCHEAXIS_PYTHON`（`lib.rs:739` 明确要求经 dev.py 运行），否则 17 项中 1 项以 “run through dev.py” 失败——此为运行方式而非产品缺陷。

被评审后决定不改的条目：`SpaceRail` 方向键/Home/End 在移动焦点的同时触发 `onNavigate`，审计视为键盘缺陷，但既有测试 `SpaceRail.test.tsx:68` 明确钉住“方向键即激活”的行为，且这正是 ARIA APG 允许的 tabs 自动激活模式；改动会推翻受既有断言保护的交互契约，故记录为“已评估、不采纳”，不擅自改动。

界面按真实渲染复核与两项结构性修正（2026-10-06，提交 `68c55531`）：此前界面审计是"读 CSS + 静态推断"，未逐屏看渲染，本轮补齐仪器并据此发现并修掉两类结构问题。(1) **原始后端载荷不该出现在产品界面**：清点出 11 处把未改写的后端载荷直接铺在阅读区——学习空间甚至把 `JSON.stringify(state)` 当作页面正文主体，另有能力目录来源哈希、核验引擎与检索回执、修订依据、导出损失回执、转写阶段与定位记录、机器回答持久化回执、备份来源 SHA 回执、作业损失/引擎/处理记录、最新处理状态与错误记录等。现统一收进活动坞内的**诊断控制台**（`presentation/diagnostics.ts` 环形缓冲 + `console.debug` 镜像，`DiagnosticConsole` 组件，按钮统一为"查看原始回执（诊断）"），阅读区只保留人可读摘要；唯一例外是"核验失败时的模型原始输出"仍按原文以惰性文本留在界面，因为摘要化会把失败读成判断，这是既有测试钉住的反粉饰规则，未擅自改动（如需一并收入控制台需所有者决定）。(2) **窄窗溢出实测并修复**：新增 `ui-visual-audit.py`（Playwright + `window.__TAURI__` 桩，渲染桌面态真实组件），在 1024×900 且检查器打开时测得中间列被挤到 **304px**、内部元素溢出最多 **58px**（祖先链定位到 `.app-center`/`.space-view`/列表）；按宽度分级收窄轨道/子导航/检查器、允许内容收缩与子导航换行后，**中间列 496px、全部 10 张截图的溢出项为 NONE**。另修复"文字堆叠、无区域划分"的根因：全量扫描发现 **17 个类名在任何样式表中都没有规则**——整个恢复台 11 个（卡片/标题/kicker/正文/诊断/操作/字段/确认/进度/反馈/日志）、命令面板触发与列表项、空间容器、导入块——在 `*{margin:0;padding:0}` 清零默认间距后即成为一整片无分隔文本，已按令牌补齐；护栏从 4 个组件扩到全量源码，并修正其子串匹配漏洞（`.space-card > h3` 曾让缺失的 `.space-card` 规则逃过检查），收紧后重扫为 0 缺口。验证：`tsc --noEmit` PASS，前端 **37 文件 255 测试全绿**，A0 真实浏览器几何合同 **PASS**（1440/1280 有子导航、390/360 无、四视口零横向溢出）。第一次运行可视化仪器时全部截到恢复台，原因是我的桩把恢复调用当成了 `request` 包装（实际是 `invoke(command)` 直调）——按"先怀疑仪器"处理并修正后才看到真实界面。

完整资格 run 37419358902（2026-10-06，cceae32b2b773a7482120f1c00d35dbd3a16e112，workflow 308098767，attempt 1，workflow_dispatch force_full）**19 项全部实际执行且全部 SUCCESS**，包括此前长期 skipped 的 desktop-build/desktop-fast/installer-lifecycle/rust-vnext/test(3.12)；该 run 的 `installed-native-journey-cceae32b…-1` 产物内含 CI 自己完成的**安装态真实 Tauri WebDriver 21 步**收据（`aaos01-webdriver/1db1319dd73640b8b504d792a1837e7a/receipt.json`，537,475 B，ok=true，evidence_level=REAL_TAURI_WEBDRIVER_CANDIDATE，21/21 步，自有进程/端口释放），宿主为 NSIS 安装后的 `%LOCALAPPDATA%\ArcheAxis Knowledge\ArcheAxis.exe` SHA `be39bdae244fb956fd5d6f62e0243f98c9d83ab6d547e56531bd4655b4f4c701`（11,297,792 B），安装器 SHA `8cd65b5e6d2f68c1c1df58244eae5c0af8f4749e5f5cb687a5660c79b4423ac0`（188,292,958 B）。注意该 21 步是 canonical 集合，**不含**本轮新增的历史 Inspector 目标步骤与可信 Ctrl+Alt+I 块，故这两项仍须在本部署候选上另跑增量。本地取件两次踩坑并已归类：`collect-exact-ci-artifact.py --output` 要的是**目录**（zip 与 receipt 同置其中，传文件名会造出同名目录）；其默认下载超时 180 秒对 193MB 不足，超时后收据写 FAILED 而外层 shell 的 `EXIT=$?` 显示 0——按"管道吞掉退出码"教训，必须读收据状态而不是只看退出码。

可视化台已升级为**门禁**（`ui-visual-audit.py`，退出码即判决）：13 张真实渲染截图覆盖 1440/1024/820/601/390 各宽度、检查器开与关、活动坞展开、命令面板、恢复台，逐屏断言 `scrollWidth<=clientWidth` 且无元素溢出；并断言"点击『查看原始回执（诊断）』确实把载荷发布到诊断通道"（用页面 `console` 消息捕获，不依赖坞内 DOM）。结果为 **verdict=PASS，13 屏零溢出，1 个回执按钮 → 1 条诊断消息**；新增 `DiagnosticConsole.test.tsx` 3 项断言面板确实逐字列出已发布载荷（含 openpyxl/3.1.5 与清空语义），避免"面板从未被验证"。

本地实窗核验达成（2026-10-06，权威形状本地候选）：改用 **Tauri CLI 构建**（与 CI 同法内嵌资源）取代 `cargo build`——`tauri build --no-bundle` 首次因 `beforeBuildCommand` 的 npm enoent 失败，遂以 `--config '{"build":{"beforeBuildCommand":""}}'` 跳过（前端资源早由 `vite build` 写入 `.project-local/build/frontend-dist`），构建得宿主 SHA `f111ed8231b2d54136a555bf3de5ffe5b5967409a2621eda394f86ba8886784a`（11,298,304 B，与 CI 候选的 11,298,816 B 同量级），装入本地候选 `aaos01-candidates/local-242cc4c3` 后 23 步增量顺利推进：`ordinary-checks`、`inspector-unsaved-history`、**`inspector-history-target`** 截图相继生成，即**我新增的历史 Inspector 目标断言在真实窗口中通过**。视觉证据（`aaos01-webdriver/4edc1e110c184aefb0468614e29d9839/inspector-history-target.png`）：检查器面板显示 `条目=Historical Inspector target fixture`、`来源=Rust Core 历史文档`、`状态=历史版本；只读；核验与依据分析独立记录`、`版本=1`（编辑器侧同时显示"当前持久化版本 2"）、`说明`含`历史正文指纹 bebdf9b7…`且**无"原件指纹"行**——正文指纹确实未冒充原件哈希；同图亦可见本轮修复的布局与子导航描述生效。此证据来自本地 Tauri 构建候选，**不冒充 CI/NSIS 安装态资格**；CI 侧覆盖缺口依旧（安装态 21 步不含该两条断言）。最终收据 `aaos01-webdriver/4edc1e110c184aefb0468614e29d9839/receipt.json`（583,738 B，SHA `1317b6423964e03e…`）：**23 步**（21 canonical + 我的 2 条扩展），`ok=false` 的唯一原因是**音频转写任务未在窗口内成功**（`local_media_ui_extension.py:56`，与 Run5 同签名，即已记录的 300 秒作业上限这一产品边界，属待 Owner 决策项），其余含 `native_inspector_history_target`（historical_version=1、historical_body_sha256=`bebdf9b7…`、latest_version=2、未借用原件哈希）、`native_inspector_shortcut`（2 次可信按键、展开后折叠、焦点保持、零 API 写入）与真实视频产物（18 原始线索/11 合法）均通过。

本地实窗核验尝试（2026-10-06，为不依赖被限速的CI产物下载而自建本地候选，证据级别如实标注）：把 `vite build` 产物写入 Tauri 内嵌目录 `.project-local/build/frontend-dist`，再从已部署候选复制后端树（`runtime/core/workers/shared/worker-profile.json/backend-runtime-manifest.json`，763MB）到 `.project-local/task-runtime/aaos01-candidates/local-242cc4c3`，宿主用本地构建。三轮结果与根因（失败收据全部保留）：① debug 宿主（`65e8c9a7…`）——窗口 `ERR_CONNECTION_REFUSED 127.0.0.1`，收据 `aaos01-webdriver/1be150336f1347ee885df85bfd7e0230`，根因是 debug 构建加载 `devUrl` 而非内嵌资源；② release 宿主（`5a56ff15…`，10,574,848 B）——仍为同一拒绝，收据 `4a9aff8e84f44818a13005e765f3039c`，根因是 `cargo build` 并非候选产物的正确生成方式（CI 用 `tauri build` 打包资源），故宿主仍指向本地服务；③ debug 宿主 + 本地 Vite(5173) —— **真实窗口内通过前 8 步**（含"原生备份恢复/重试与版本回滚 + 原始 CAS 回读"），收据 `aaos01-webdriver/ecc1245138f1487ea52e00e0c9ac024c`（25,979 B），随后在探针 `native_command`（`prepared-local-media-ui.py:714` 断言 `value["ok"]`）处收到 `None` 而终止；定性为 Tauri 2 按 origin 授权能力，dev-server origin 下原生命令返回不可靠，属**本地临时harness的限制**而非产品缺陷。结论：新增的历史 Inspector 目标步骤与可信 Ctrl+Alt+I 的权威实窗证据仍须在 `tauri build`/CI 产物上取得，本地 harness 仅作辅助；不把上述 8 步写成安装态资格，也不把 dev-server 结果冒充候选资格。

审计件断言纠正与 Avalonia 供体冻结（2026-10-06）：`AAOS-MERGE-CHECKLIST-20261002.md` 称"#157 与 #158 零文件重叠，无需冲突复核"——**实测证伪**：以各自 merge-base 计算，#157 涉及 650 文件、#158 涉及 14 文件，两者**重叠 10 个**（`apps/ArcheAxis.Desktop/*` 与数个 `tests/test_aaos_*`），其中 7 个内容不同；`git merge-tree --write-tree` 对两分支实测**返回冲突**（`MainWindow.axaml`、`MainWindow.axaml.cs`、`Views/SourceReaderView.axaml`、`tests/test_desktop_navigation_contract.py` 等）。同时实测 **#157 与当前 main 合并干净**（exit=0 无冲突），故第 2 步本身可行；#158 的 14 个文件**与当前 main 全部不同**（main 经 #156 已含第三条 aaos-ui-phase2 版本），三方在 Avalonia 桌面 UI 与契约测试上各自分叉。Owner 裁决：**产品主线是 Tauri/React，Avalonia 桌面作供体，确认复用复制完成后即冻结**。复用证据（已核实，含 UI 层与生命周期层）：`src-tauri/src/main.rs` 以 `#[path = "../../desktop/src-tauri/src/backend.rs"]`（并 `job.rs`/`protocol.rs`/`runtime.rs`）**直接内含** desktop 生命周期实现；UI 层则由 `frontend/src/components/AaosIcon.tsx` 首行注明 *"Geometry reused verbatim from apps/ArcheAxis.Desktop/AaosIcon.axaml.cs"*（24 单位 viewBox / 1.7 单位描边的既有 AAOS VI 几何被逐字复用），品牌资产 `aaos-brand-mark.svg` 亦已复制进 `frontend/src/assets/`。AGENTS.md 记载正式宿主复用既有 `desktop/` 生命周期实现——即被复用方是 `desktop/`，`apps/ArcheAxis.Desktop`（#158 所改）为行为/组件供体。据此 #158 **冻结不合并**：分支保留、PR 关闭并留下说明（reopen 可恢复），四主题模型与 cosmic UI 层留在冻结的供体侧；相关 `tests/test_aaos_*` Avalonia 契约测试仍在 CI 中运行，故冻结不影响其绿灯。合并顺序随之变为：#156（已完成）→ #157（干净合并）→ #158（冻结，不合并）。

已审计确认的分支清理（2026-10-06，Owner 目标"已审计确认的执行清理删除"）：删除远端三个**已交付**分支，删除前先建可恢复保留点。`codex/aaos-p3-ui-convergence-20260922`（已完整包含在 main：ahead=0/behind=64）删除，保留点本地分支 `preserve-p3-ui-convergence` = `43c2cafa1bfe57a862e90c5a77dc16832264babd`；`codex/github-delivery-docs-20260929`（#154 于 09-29 squash 交付，故其提交非 main 祖先）删除，保留点 tag `preserve/github-delivery-docs-20260929` = `aa804699`；`codex/aaos-ui-phase2-20261001`（#156 已合并、已包含在 main）删除，保留点 tag `preserve/aaos-ui-phase2-20261001`。清理后远端仅余 `main`、`codex/dsh-aaos-real-multiformat-loop-20261001`（本支，待合并）、`codex/minimax-aaos-cosmic-ui-20261001`（#158，按 Owner 裁决冻结保留为供体材料）。`codex/Audit`（已包含在 main：`1a981a44` 为 main 祖先；其作为 #158 base 的作用随 #158 冻结关闭而失效）已删除，保留点 tag `preserve/codex-Audit` = `1a981a4482b01f31989074e79c82a63400aa07a7`；至此本批共删除远端 4 个已交付分支、本地 1 个被取代分支，全部先建保留点。另：本地分支 `codex/dp-f01-20260925`（从未推送）经审计确认已被 main 取代——其 9 个文件中 8 个与 main 逐字节相同，第 9 个 `f01_quality_roundtrip.rs` 在 main 上已有同名提交 `d5f026ee`（09-25 18:39）并被 rustfmt（09-27）与功能修复（10-01）继续更新——已删除本地分支，回滚点 `793e06ee`（含 `56a76411`）。

外置库引用索引（2026-10-06，应 Owner 要求：不得再出现"找不到工具链/模型库/共用库"）：声明唯一入口仍是 `config/environment/capability-requirements.yaml`（含 `external_paths`/`healthcheck_command`/`local_only`，并有 schema `config/schemas/capability-requirements.schema.json` 与人类可读权威 `docs/environment/EXTERNAL_DEPENDENCIES.md`）；新增**已核验索引** `config/environment/external-resources-index.json`（22 条声明 / 8 条带外置路径 / 本机 **0 MISSING**），由 `scripts/environment/build_external_resources_index.py` 从声明重建，记录每条声明的解析绝对路径与存在性。**补上真实缺口**：真实转写使用的 `faster-whisper-large-v3-turbo` 权重此前**未被任何声明命名**（只能靠 `ARCHEAXIS_ASR_MODEL_DIR` 环境变量发现，正是"找不到模型库"的成因），现已在 models 类登记 `../Model library/whisper/faster-whisper-large-v3-turbo` 并解析通过。防漂移护栏 `tests/workflow/test_external_resources_index.py`（3 项）：索引条目集必须与声明完全一致、每条声明的路径必须被登记、且在有外置根时**每条都必须在磁盘上存在**；无外置根时该断言**显式 skip 并给出理由**，绝不静默通过——该护栏已在索引过期时真实失败过一次（证明其有效）。**实测发现的不一致（待决）**：schema 对 `external_paths` 的 pattern 明确禁止 `..`，而既有 `sense-voice-zh-en-ja-ko-yue` 与新加的 ASR 权重都用 `../Model library/...`（因为 Model library 在共享根之外）——即声明与自己的 schema 互相矛盾；解法二选一（扩展 schema 增加兄弟根键，或把模型库纳入共享根内），属需 Owner 定的小决策，我未擅自改 schema 或移动模型库。**解析器自纠**：首版把 `../X` 相对根的父目录再退一层，误报 1 条 MISSING；按"先怀疑仪器"改为统一以根为基准后为 0 MISSING。

开源池吸收并入的实际账（2026-10-06，按产物证据核对，不是照抄清单）：处置框架见 `docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json`（369 条目池；每条恰得 REFERENCE/ADAPTER/ABSORB/PROVIDER/SIDECAR/BENCHMARK/REJECT 之一；47 个供应链项目与 11 项能力留档），该文件自述 **"本文档不安装任何项目；裁决只是框架；逐行填充与安装是另一件事"**。**已吸收（有产物级证据）**：faster-whisper、jiwer、rapidfuzz、py-fsrs、pymupdf、markitdown、trafilatura、rapidocr（均在 `pyproject.toml` 依赖组）；**Silero VAD 实为已吸收**——`services/python-workers/media/worker_transcribe.py:161` 以 `vad_filter=True` 使用 faster-whisper 内置 Silero VAD 并在回执记 `vad_filter: True`，无需单独依赖；JSON Canvas 有归档往返测试（`crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs`）；Lucide 图标已本地化为矢量并固定 ref 与许可原文 SHA；前端 tiptap/pdfjs-dist 为直接依赖。**已吸收（续）**：Crossref/DataCite/OpenAlex/Wikidata **实为已并入**——`shared/evidence_connectors.py` 首行自述"These are ADOPT items from the absorption atlas v2"，是一方 `urllib` 实现（非 pip 依赖），带离线结构测试与 `--run-network` 联网实测（`tests/test_evidence_connectors.py`），许可登记在 `docs/truth/SUPPLY_CHAIN_LEDGER.json`（Crossref:473、DataCite:487、OpenAlex:501、Wikidata:518）。**更正**：我上一轮据 `capability-catalog.ts` 推断其"仅声明未接线"是错的——生成目录里的 dependencies 只是设计输入，实现早在 `shared/`。**仍未吸收**：Gitleaks（MIT，无需锁文件，仅需 workflow 步骤 + `.gitleaks.toml`）、pip-audit（CI 专用，需 CI 侧 uv，已有 `cargo audit` 可照抄）、Apache Tika/Crawlee（SIDECAR；Crawlee 需重生成 `uv.lock`）、Syft（与一方 `scripts/release_sbom.py` 重复，降级）；9 项 candidate 能力未吸收；9 项 REVIEW-BLOCK（MinerU/Marker/FunASR/tldraw/Firecrawl/H5P/Phoenix/SearXNG 等）按该文件要求**明确不得吸收**。吸收准入规则见 `THIRD_PARTY_NOTICES.md:68`（精确修订版 RDR + 许可文件哈希 + Windows 探针 + fixture，且须 Owner 授权）。**本机约束**：无 `uv` 且 CI venv 无 `pip` 模块，故 Gitleaks/pip-audit 以 **CI 工作流步骤**方式吸收（CI 内有 uv），不从本地改锁文件。

按审计件执行合并与仓库审计（2026-10-06）：Owner 指示"已审计确认的执行合并/清理，未审计的先审计"，并明确**继续不发布**（不打 tag、不发 release）。按 `docs/current/AAOS-MERGE-CHECKLIST-20261002.md` 的顺序执行第 1 步：#156（main ← codex/aaos-ui-phase2-20261001）先标记 ready、核对 `mergeStateStatus=CLEAN` 后合并，合并提交 `6a4386540db483f81b8889001d39b1d1a7458eaf`；`main` 由 `59498723` 前进到 `6a438654`，并实测 `1a981a44`（codex/Audit 的 tip）**已是 main 祖先**——审计件所指"Audit 的 18 个提交够不到 main"这一缺陷由此闭合。**平台门禁（更正我此前在对话中的误判）**：旧式分支保护 API 返回 `Branch not protected`，但仓库实际存在并启用 ruleset `main-protection`（target=branch，enforcement=active）与 `tag-protection`（target=tag，active）；前者强制 `non_fast_forward`、禁止删除分支，并要求**必需状态检查 `a0-gates`**（`strict_required_status_checks_policy=false`）。因此 main 的合并一直受平台门禁约束，本轮全程未使用任何 admin/绕过；`#159` 曾显示 `BLOCKED` 是因必需检查尚未上报，而非冲突（`mergeable=MERGEABLE`、`git merge-tree` exit=0）。第 2 步（#157）按审计件重定向到 main（`gh pr edit 157 --base main`）并标记 ready，但状态为 **BLOCKED**：`cargo-test` FAILURE。**审计结论：该失败是 vnext-ci 的环境缺口而非产品代码缺陷**——工人解释器实际含 `openpyxl 3.1.5`，本地用同一 worker 实跑 `cargo test -p archeaxis-application --test archive_member_formats` 得 1 passed；`ci.yml` 同时装 `ci` 与 `ci-adapters` 两组故其运行全绿；而 `vnext-ci.yml` 的 `cargo-test` 只用 `uv export --only-group ci` 构建隔离 worker venv，xlsx 成员格式因此报 `AAK-WORKER-003`（引擎缺失）。经 Owner 授权修改该 workflow（向同一 worker venv 补装 `ci-adapters` 组并断言 `openpyxl` 可导入），提交 `c55717ea` 已推送；合并 #157/#158 待该 PR 检查转绿后继续，**未使用任何 admin/保护绕过**。最终结果：修复后 `cargo-test` 转绿（37423764574，7m26s），`desktop-build` 亦通过（16m19s），`#157` 在 `mergeStateStatus=CLEAN` 下合并为 `9a7f338352dbb78c24ffcf6c346c243746a3a1da`（`main` `6a438654 → 9a7f3383`），其 `CI` 37426540024 被后续推送取消、`vnext-ci` 37426539894 成功；随后以 docs PR `#159` 落地本轮台账，`a0-gates` 通过后合并为 `a2f7e7fb66a0ec76b8fbcc801853a8d8e1862192`（`main` `9a7f3383 → a2f7e7fb`）。**按精确 head_sha 查验**（`/actions/runs?head_sha=`；`--branch main` 列表会返回陈旧运行，曾误导我一次）：当前 main `a2f7e7fb` 的 `CI` 37427227310 = completed/success，但实际仅执行 `gateplan`/`lint`/`a0-gates`、16 项按 docs-only 分类 skipped——**该绿灯只覆盖文档变更，不重新资格化桌面/候选流水线**；`#157` 内容的实质覆盖来自同一提交上的 PR 运行（`CI` 37423764115 的 18 项含 desktop-build/installer-lifecycle 全成功、`vnext-ci` 37423764574 `cargo-test` 成功）与分支上的完整 `force_full` 运行 37421275385（20 项全成功）。`#158` 按 Owner 裁决冻结未合并；无 tag、无 release。

分支审计（2026-10-06，`git fetch --prune` + PR 全状态对照，远端共 7 个分支）：#154 已合并（09-29，squash：其提交非 main 祖先属正常）、#155 已合并（10-01，即 main 原 `59498723` 的来源）、#156 本轮已合并、`codex/Audit` 已完整包含在 main、`codex/aaos-p3-ui-convergence-20260922` 已包含在 main（ahead=0/behind=64）故属可清理的已并入分支、`codex/github-delivery-docs-20260929` 内容经 #154 交付但分支未成祖先（squash 特征）、#157 本轮待合并、#158 为 clean 但 draft 且 base 仍是 `codex/Audit`。另有**本地分支 `codex/dp-f01-20260925` 从未推送、无远端**（2 提交、落后 main 120），按"未审计先审计"暂不处置。删除这两个已交付远端分支属破坏性共享操作，已列出待 Owner 确认后执行，本轮未删。

vnext-ci FAILURE 根因与 AQ27 登记（2026-10-06，只读核对 run 37404389088）：唯一失败 job 为 cargo-test，`crates/archeaxis-application/tests/archive_member_formats.rs:145` unwrap 得 `AAK-WORKER-003 xlsx engine missing (openpyxl not installed)`；该 workflow 的 worker venv 仅 `uv export --only-group ci`，而 `ci.yml` 另装 `ci-adapters`（含 `markitdown[pdf,docx,pptx,xlsx]`），故为工作流环境缺口而非产品回归，同一测试在具备适配组的环境通过；修改共享 CI 属边界变更，未自行执行。AQ27（SQLite运行版本）此前从未登记：真实候选收据 `system_version` 记录 `sqlite_version=3.51.3`、`schema_version=11`（Run1c/Run3/Run4/Run5 一致），宿主SHA `00b7ba9b…` 与 release-identity 绑定源提交 578d06b78413/树 87a3975…/run 37399470467，`Cargo.lock` 为 rusqlite 0.39.0 + libsqlite3-sys 0.37.0；checkpoint 协调实测存在于 `crates/archeaxis-domain/src/backup.rs:51` 与 `crates/archeaxis-archive/src/lib.rs:585`（`wal_checkpoint(TRUNCATE)` + `journal_mode=DELETE`），正是只读研究侧要求无 `-wal/-shm` 旁文件的条件。不可变 `checks/acceptance.json` 仍为 NOT_RUN，未改该文件，仅在此登记实测证据。

## 当前状态与剩余缺口

| ID / 权威任务 | 当前状态 | 已有证据与实际剩余缺口 |
| --- | --- | --- |
| Q00 现场保护与最小对账 | PARTIAL | 已复核起始 SHA、工作树与工具路径；本轮使用独立候选及全新 Core 数据根。未知用户资产、旧库与历史回执保留；完整资产/schema/writer 身份不因本轮格式测试自动完成。 |
| Q01 重构决定与目录登记 | TESTED_LOCAL | 已有 SUP-022 重构登记；本轮统一使用权威 `stage_backend_runtime.py` 产出候选，desktop-fast/build 使用相同准备步骤。此项不是旧编号中的“打包完成”；现行Directory/Language/RuntimeDelivery/ProjectContract及schema已按SUP-022最小同步，schema/引用回归PASS。 |
| Q02 Tauri 启动与只读桥接 | INSTALLED_RUNTIME_VERIFIED / PARTIAL（本轮已从 artifact 自身逐字段核对） | SHA `3dc286908783930f21a83663a822c5a8fdbdeedc` 的 `workflow_dispatch` run `37358948993` 结论 success；artifact `11366214081`（`installed-native-journey-3dc28690…-1`，176,213 B，未过期）内 `receipt.json`（sha256 `3367d910488aef6ddf496c21…`）**`ok=true`**、`evidence_level=REAL_TAURI_WEBDRIVER_CANDIDATE`、**13 步**、`owned_process_cleanup=true`、`owned_ports_released=true`，另有三张截图与 `driver.log`。**安装态由收据自身字段证明**：`host.path=C:\Users\runneradmin\AppData\Local\ArcheAxis Knowledge\ArcheAxis.exe`、`installation_context="Parent installer verifier supplies installed host; this probe hashes installer only"`、`install-preflight.json.installed_interpreter=…\ArcheAxis Knowledge\runtime\python.exe`——即 `verify_nsis_install.ps1` 装好后把**已安装宿主**交给探针；绑定 `installer_sha256=91064fea…`、`host_sha256=aaed6c36…`。**未证的是完整生命周期**：`install-preflight.json.complete_lifecycle_verified=false`（Q14 同为 false）。**并记录一处收据缺陷**：其 `limitations[0]` 写 `Candidate executable, not NSIS installed journey`，与本收据自身的 `host.path`/`installation_context`/`installed_interpreter` 三处字段**自相矛盾**，属过时的固定文本——我先据该句把本行下调，读到内部字段后再纠正回来，故此处保留全部原始字段而非二选一。`src-tauri` fmt/test 的 CI 通过另行保留；物理 IME 与全部阅读器交互不能由此代验。下载件在 `.project-local/task-runtime/q02-artifact-20261006/`。 |
| Q03 类型合同与权限 | TESTED_LOCAL | 本轮按任务书逐项读回。**生成 DTO**：四个契约检查全 exit 0（`generate_vocabulary.py --check` → `{"status":"pass","drift":[]}`；`generate_core_document.py --check`；`generate_capability_catalog.py --check`；`check_media_window_policy.py --check` → 2 处 Core 上限一致），产物为 `packages/contracts/v1/*.schema.json` 与 `frontend/src/api/generated/{core-contract,capability-catalog}.ts`，其中两项已接入 CI。**有限命令与对象权限**：经跟踪入口 `scripts/ci/cargo_test.bat test -p archeaxis-api --tests --offline` 实跑 48 个测试二进制、**232 passed / 0 failed**、exit 0，含 `contract_auth_boundaries`、`launch_auth`、`contract_absent_surfaces`（未挂载 404 与已挂载 405 的区分）、`contract_process_model`、`contract_constant_fields`、`contract_job_outputs`、`api_closed_loop`。**残留**：这是工程/契约层证据，不含 UI 运行期读回（未把 `src-tauri/gen/schemas/capabilities.json` 当作权限证据读取），安装态资格仍由 Q02/Q14 承担。 |
| Q04 原件与文档保存 | TESTED_LOCAL | 本项历史完成状态曾被**撤销**（更正 C34：当时证据只证明候选能力调用，不能证明 Document/Block、草稿保存与恢复一致性）。本轮以**不同类型的证据**读回：`scripts/ci/cargo_test.bat test -p archeaxis-api --test document_draft_loop` → **8 passed / 0 failed**（`document_draft_is_atomic_versioned_conflict_checked_and_restorable_after_restart`、`original_notes_and_version_bound_checks_remain_independent_and_restorable`、`versioned_human_review_refuses_machine_and_stale_versions_without_partial_writes`、`check_history_pagination_exposes_every_record_without_inheriting_new_version`、`large_document_library_lists_bounded_metadata_and_reads_one_full_snapshot`、`live_owned_writer_backups_are_human_only_pathless_and_independently_restorable`、`completed_real_recognition_is_not_a_fidelity_basis_or_human_approval_by_itself`），`-p archeaxis-store-sqlite --test staging` → **1 passed**（`staging_reads_are_bounded_and_reject_nonregular_or_aliased_objects`）。单一写者另有 3 项通过（硬链接别名不能取得第二写者、同 workspace 独占至最后一个 router 克隆释放、他进程被拒且崩溃 owner 不留陈旧锁）。日志 `.project-local/task-runtime/q04-cargo-tests-20261006.log`。实现面保留：schema11 CAS 原件、同事务 editor JSON/正文投影、稳定 block IDs、乐观锁 409、旧版本读取及恢复生成新版本。**残留**：不能从 API/契约代推 installed UI（编辑器运行期读回未做），独立备份演练见 Q11，真人学习闭环见 Q08。 |
| Q05 阅读与证据样板 | INSTALLED_RUNTIME_VERIFIED（自行记录，本轮未重做）/ TESTED_LOCAL（本轮实测） | 本轮以**仓库内可复核**的证据读回"证据样板"：`evidence_anchors_api` **5 passed**（`evidence_anchor_list_surfaces_the_quoted_selection`、`evidence_anchor_list_projects_persisted_core_rows`、`epub_locator_requires_exact_receipt_identity_and_retains_old_anchor`、`time_anchor_binds_actual_receipt_and_preserves_old_attempt`、`subtitle_time_anchor_binds_unicode_quote_and_attempt_after_reopen`）、`source_transform_readback` **4 passed**（`a_pdf_transform_is_readable_through_the_source_scoped_route`、`a_source_that_does_not_own_the_job_is_refused`、`a_job_that_did_not_succeed_is_still_not_readable`、`every_extraction_kind_that_stores_a_projection_is_readable`）、Python 证据套件 **20 passed / 1 skipped**。要点：锚点绑定**真实回执**且保留旧锚点，来源不拥有该 job 会被拒——证据不能与其来源分离，这与"机器候选不等于真人认可"是同一条线的两端。**残留**：安装态那一段（d91 21 步、四区导航、Ctrl+Alt+J）本轮未重做，其收据不在仓库内，只作自行记录、不计入本轮实测；物理 IME、完整旧菜单动画/原件视觉与真人 Owner 仍缺。日志 `.project-local/task-runtime/q05-tests-20261006.log`。 |
| Q06 A 波次多格式吸收 | INSTALLED_RUNTIME_VERIFIED（自行记录，本轮未重做）/ TESTED_LOCAL（本轮实测） | 本轮实测 A 波次工程证据：`tests/test_format_matrix.py` + `tests/test_multiformat_extraction.py` + 9 个 `tests/workers/test_bulk_*` 套件（text/structured/office/pdf/ocr/media/html/legacy_adapters/quality）→ **296 passed、0 skipped、104 subtests passed、exit 0**（30.32s）。**关键环境条件**：此前的 9 项跳过不是工具缺失，而是本 shell 未绑定外部根——`config/environment/external-resources-index.json` 声明的 ffmpeg（解析为 scoop 8.1.2）与 tesseract（5.5.0）均 `exists: true`，绑定 `ARCHEAXIS_EXTERNAL_ROOT` + `TESSDATA_PREFIX` 后 9 项全部真跑（未绑定 287 passed / 9 skipped → 绑定 296 passed / 0 skipped）。这是"磁盘上存在 ≠ 已绑定"的一次实测。格式侧：本轮按代码更正了格式矩阵 **F10**（音频转写路由已存在、MP3/M4A/FLAC 可达）与 **F11**（视频解码与字幕路由已存在），矩阵各组 `gap` 仍是"每种声明格式还缺什么"的权威表述。**残留**：C35 的降级边界（音视频**内容**处理曾只到头信息探测）已由 ASR/视频路由与窗口化覆盖，但矩阵列明的实质缺口仍在（片段级而非词级时间、采样帧而非穷尽帧事件、超预算即 `not_attempted`、无说话人分离）；安装态收据不在仓库内，只作自行记录；人工语义质量与新 Green 部署仍缺。日志 `.project-local/task-runtime/q06-full-bound-20261006.log`（未绑定对照 `q06-tests-20261006.log`）。 |
| Q07 候选审核与纠正 | PARTIAL / AWAITING_OWNER（工程半已实测，Owner 决定仍待） | 本轮实测（`cargo_test.bat test -p archeaxis-api --test knowledge_actor_guard --test contract_conflict_rules --test contract_review_cost --offline`，exit 0）：`knowledge_actor_guard` **2 passed**（`machine_cannot_self_accept_or_act_without_identity`、`machine_cannot_review_or_record_human_learning`）、`contract_conflict_rules` **1 passed**（`the_contract_conflict_rules_hold`、`an_execution_that_is_already_running_conflicts_with_a_second_key`）、`contract_review_cost` **3 passed**（含 `human_personal_definition_may_start_accepted_without_evidence`、`a_review_that_spawns_a_scheduler_takes_longer_than_one_that_does_not`）。含义：机器身份不能自我接受、不能代替真人审核或记录人的学习；真人个人定义可在无证据时起始；冲突与成本规则成立。**这半不能替代 Owner 决定**：候选仍需真人明确接受/拒绝，工程里设 human principal **不等于**真人认可；已创建的未接受候选继续等 Owner 裁示，故本项保持 `AWAITING_OWNER`，不登记为完成。日志 `.project-local/task-runtime/q07-tests-20261006.log`。 |
| Q08 学习与 AI 资产闭环 | TESTED_LOCAL / PARTIAL | 本轮实测（Rust `learning_events_api` + `contract_machine_answer` + `contract_machine_correction` + `contract_machine_retest` → **34 passed / 0 failed**，4 个二进制、exit 0）：关键断言 `persisted_answer_correction_review_and_retest_form_one_chain`（回答→纠正→审核→重测**是一条链**）、`a_free_text_context_is_refused_because_grounding_is_the_point`（拒绝自由文本上下文，必须接地）、`candidate_and_deprecated_knowledge_are_refused_before_inference`（候选/已废弃知识不得进入推理）、`active_personal_knowledge_is_allowed_but_superseded_knowledge_is_not`、`an_answer_is_either_a_labelled_candidate_or_a_named_failure`、`a_disabled_capability_refuses_before_the_model_runs`。Python `co_learning_loop`/`dual_mastery`/`desktop_machine_learning_journey`/`knowledge_to_learning_artifact` → **22 passed / 1 skipped**。即 M0 循环中"机器使用同一 Knowledge → Evaluation → Correction → Retest"这一段本轮有工程证据。**残留**：真人那一半仍缺——真人决定、真人答案与纠正旅程未做；本机 qwen3.5-4b 夹具审核明确记为 `AUTOMATED_FIXTURE_REVIEW_NOT_G4_HUMAN` 且结果 `unmeasured`，不夸大亦不虚构效果。日志 `.project-local/task-runtime/q08-tests-20261006.log`、`q08-python-20261006.log`。 |
| Q09 搜索与完整能力目录 | INSTALLED_RUNTIME_VERIFIED（自行记录，本轮未重做）/ TESTED_LOCAL（本轮实测） | 本轮实测：Rust `contract_semantic_search` + `contract_capability_registry` → **20 passed / 0 failed**（exit 0），关键断言 `a_capability_whose_worker_is_absent_is_unusable_rather_than_unhealthy`、`an_unknown_capability_is_a_not_found_rather_than_the_nearest_match`、`enable_is_recorded_rather_than_asserted_and_fallback_is_still_absent`、`health_sends_no_job_and_does_not_change_provider_selection`、`the_usable_provider_answers_even_when_a_broken_one_was_registered_first`、`an_empty_or_misspelled_body_never_silently_disables_a_capability`——即目录对"缺席"老实回答，不把缺失读成不健康、不把未知读成最接近项。Python `test_capabilities` + `test_capability_absorption_registry` + `test_capability_and_search_probe` + `test_capture_search_mother_contract` → **21 passed**（exit 0）。目录生成：`generate_capability_catalog.py --check` exit 0（16 CAP 目录与两权威源一致、无漂移）。**残留**：专业联网检索的根因仍未定——DDG 固定公开工程查询真实超时，而官方 SQLite 在同安全策略下 HTTP 200，目标特异连接/TLS/路由 `UNKNOWN`，不伪造搜索成功；安装宿主收据（f471）不在仓库内，只作自行记录；全量开源供体许可/upstream 固定与真人检索验收仍缺。日志 `.project-local/task-runtime/q09-tests-20261006.log`、`q09-python-20261006.log`。 |
| Q10 导出与首个互通 profile | TESTED_LOCAL / PARTIAL | a14真实Rust Markdown/Obsidian固定两文件包、完整Document/未知节点/锚点/损失manifest、独立磁盘回读与Core重启导出相等通过。宿主有限导出仅写产品资料目录，无UI path输入。a14新版导出在独立Obsidian实际窗口回读已知正文、Source身份与Evidence records通过（本表上方新收据与截图）；未知节点在manifest保留，external_navigation_unavailable loss明确，外部引用导航仍缺。578d exchange自己的两固定文件/投影SHA/未知节点/锚点/损失/重启证据通过；外部应用实际回读仍仅a14，导航缺口保留。**本轮实测（仓库内可复核）**：`cargo_test.bat test -p archeaxis-archive --tests --offline` → 21 passed / 0 failed，含 `obsidian_vault_roundtrip_keeps_bytes_names_and_links_and_states_the_gaps`、`the_export_names_every_table_it_must_carry`、`a_fresh_workspace_has_every_exported_table`、`origin_rows_survive_export_and_restore`；Python 导出/备份探针六文件合计 51 passed（与 Q11/Q12 共用一次运行，见该两行）。日志 `.project-local/task-runtime/q10-q12-rust-20261006.log` / `q10-q12-python-20261006.log`。 |
| Q11 备份与副本恢复 | INSTALLED_RUNTIME_VERIFIED / PARTIAL | 现有Store一致live backup→全新独立DB/CAS副本恢复→完整文档/版本/原件读回→继续编辑/第二次重启PASS；3dc独立安装host真实backup/restore/retry、版本回退及CAS读回PASS，另候选Core独立副本恢复收据通过。备份哈希/manifest与源CAS严格核验，损坏回滚测试保留。正式用户旧库的迁移回退仍需定义语义及验收，不由全新夹具证明。578d独立恢复六行为及本run原生rollback/CAS已核验；旧库intake一行迁移不代表完整旧库迁移。**本轮实测**：同一批 `archeaxis-archive --tests` 21 passed / 0 failed 里含备份安全断言 `existing_target_is_preserved_byte_for_byte`、`constraint_failure_does_not_publish_partial_database`、`corrupted_table_rejected_without_creating_target`、`corrupt_manifest_and_false_zero_rows_are_rejected`、`original_bytes_survive_source_removal_restart_and_archive_restore`；Python 备份/恢复探针与 Q10/Q12 共用一次运行、合计 51 passed。旧库迁移语义仍缺，不由全新夹具证明。**本轮补测迁移包**：`cargo_test.bat test -p archeaxis-migration --tests --offline` → **24 passed / 0 failed**，含 `non_empty_legacy_library_stages_notes_and_learning_history_without_touching_the_source`（非空旧库把笔记与学习历史**暂存**且不触碰源库）、`legacy_db_never_modified`、`staging_never_modifies_the_legacy_database_bytes`、`inventory_readonly`、`manifest_table_removal_is_rejected_before_any_write`、`tampered_jsonl_is_rejected_before_any_write`、`export_refuses_to_overwrite_existing_snapshot`；Python `test_migration_runner` + `test_migrate_rowidless_tables` + `test_axw_data403_migrate` → **51 passed / 0 failed**（operator 侧 36 用例：apply/rollback 来源证明、owner 租约、漂移 fail-closed、并发单一 owner）。**由此把残留收窄**：旧库迁移的**机制**（只读源库、暂存笔记/学习历史、manifest 具名未读表、写入前拒绝）已有提交证据；仍缺的是**验收口径与回滚契约**——对 Owner 真实旧库何为"迁移完成"、失败如何回退——而非机制缺失。日志 `.project-local/task-runtime/q11-migration-{rust,python}-20261006.log`。**本机 3dc 收据已逐字段核对**（同 Q02 下载件）：`backup` = `{backup_id a7bd0631…, 270336 B, schema archeaxis-core-backup-1}`、`recovery_before_restore` = `{state ready, safe_mode false, message "Core is ready"}`、`restore_command_receipt = {status restored}`、`retry_command_receipt = {ready true}`、`native_restore` 版本 3→2 且 `cas_equal=true`、`system_version_after_retry.schema_version = 11`。**同时记录收据自带的边界**：`native_restore.scope` 写 `Only this fresh product data root; not independent restore`——即"真实备份/恢复/重试与 CAS 读回"成立，但**不是独立恢复验证**；原行"独立副本恢复收据通过"应收窄到此口径。 |
| Q12 B 波次轻量扩展 | INSTALLED_RUNTIME_VERIFIED（自行记录，本机收据已核对不存在）/ TESTED_LOCAL（本轮实测） | 本项自己的578d收据原引 `artifact11384741425 / aaos01-light/25fc0b22c204403fabe1bc1b76f677e9/receipt.json` 与 `typed-format-final/typed-1.json`；**本轮实例核对：两者在本机均不存在**——`25fc0b22…` 在 `.project-local` 下（maxdepth 5）检索无命中，`typed-format-final/typed-1.json` 亦无命中；`aaos01-light/` 下确有 **12 个 run 目录**（各含 `receipt.json`，10 个 `ok=true`、2 个 `ok=false`），但**没有**被引用的那个 id。本轮清理批次未触及 `aaos01-light`（本会话删除项已逐条列入台账"本轮按授权范围的清理"），故该缺失**不能归因于本轮**，也不外推原因。原行所述"九正/四负格式、三输出200/404、locator/anchor、CAS/export/重启"等断言因此**失去本机可复核的收据来源**，保留为自行记录、不计入实测。**本轮实测取仓库内证据**：`archeaxis-archive --tests` 21 passed / 0 failed 含 `archive_roundtrip`、`real_worker_output_archive_restores_exact_bytes_and_idempotency`（重启后逐字节相同且**幂等**）、`the_previously_omitted_rows_survive_a_round_trip`；Python 侧与 Q10/Q11 共用一次运行、合计 51 passed。真人质量与复杂 Reader 布局仍缺。 |
| Q13 性能与故障验证 | TESTED_LOCAL / PARTIAL | 真实Core四故障场景无产物且后续正常job恢复PASS；20次真实Tauri新进程/新Core根/新WebView profile启动，预先3s/1GB预算下P95=1.422s、完整自有树最大468340736字节PASS（OS磁盘缓存保留）。创建时间绑定父子进程排除旧父PID重用；CDP观察器不计入产品内存，退出命令清理不冒认WM_CLOSE。无观察器的WM_CLOSE独立PASS；安装态整机故障旅程仍缺。578d四故障收据实际无产物且nextjob恢复：三项注入、一项真实坏字节；不声称安装态整机故障旅程完成。**本轮实测（仓库内可复核）**：Rust `import_media_budget` → 1 passed（`known_six_and_twenty_six_mib_originals_import_and_read_back_exactly`，6 MiB 与 26 MiB 原件导入并逐字节读回）；Python `test_verification_performance` + `test_workspace_browser_failure_retry_replay` + `test_workspace_crash_recovery` + `test_ocr_failure_paths` → **13 passed**，exit 0。**残留**：那条 P95=1.422s / 468 MB 的整机实测与四故障注入收据在 `.project-local` 与交接记录里、不在仓库内，故只作自行记录；安装态整机故障旅程仍缺。日志 `.project-local/task-runtime/q13-rust-20261006.log`、`q13-python-20261006.log`。**本机性能收据已逐字段核对**（`.project-local/task-runtime/aaos01-ui-performance/8920b7e9657f4c5bb834377df2ac3dd4/receipt.json`，39,458 B，sha256 `43935702519e34e9aa3f7c5f…`）：`ok=true`、`samples=20`、`startup_p95_seconds=1.422`、`idle_tree_max_bytes=468340736`、`conditions.startup_p95_budget_seconds=3`、`conditions.idle_tree_budget_bytes=1073741824`、冷启动定义"每样本新 host 进程/新 Core 数据/新 WebView profile；保留 OS 磁盘缓存"、内存口径为自有进程树工作集之和 —— 与原行数字**逐项一致**，故本行的整机数字由"自行记录"升为"已核验"。 |
| Q14 Windows 安装态资格化 | INSTALLED_RUNTIME_VERIFIED / PARTIAL（本轮已从 artifact 自身逐字段核对；完整生命周期未验） | 引用的 run/artifact 读回核对：run `37399470467` 于 `578d06b784139e86c685191ecc7d0ccdd021fb27` 结论 success、**20/20 job 全部 success**；artifact `11385093136`（`installed-native-journey-578d06b7…-1`）未过期、551,082 B；`receipt.json`（sha256 `38ce8afd4f789e8fda52e751…`）**`ok=true`**、`evidence_level=REAL_TAURI_WEBDRIVER_CANDIDATE`、**21 条具名步骤**（含 `UI same-space … without creating objects`、`Native backup restore/retry and actual version rollback with original CAS readback`、`Trusted native Ctrl+Alt+J … without issuing API writes`、`Actual EPUB Reader chapter/paragraph … result-bound locator`、`Full host restart reads every host matrix source/output/quality/origin`）、`owned_process_cleanup=true`、`owned_ports_released=true`、`remaining_owned_port_listeners=[]`、`native_restore` 版本 3→2 且 `cas_equal=true`。**安装态由收据自身字段证明**：`host.path=C:\Users\runneradmin\AppData\Local\ArcheAxis Knowledge\ArcheAxis.exe`、`installation_context="Parent installer verifier supplies installed host; this probe hashes installer only"`、`install-preflight.json.installed_interpreter=…\ArcheAxis Knowledge\runtime\python.exe`；绑定 `installer_sha256=1f7b64878768ab564c9171cbb1f97b74…`、`host_sha256=00b7ba9b187b305d650458…`、`core_sha256=a648e4d28cc8f36596c05423f0f70faa…`。**未证**：`install-preflight.json.complete_lifecycle_verified=false`（完整生命周期未验）、物理 IME、真人 Owner、新 Green 部署与新媒体 UI，故不登记资格、不发行。**收据缺陷一并记录**：其 `limitations[0]` 写 `Candidate executable, not NSIS installed journey`，与本收据自身的 `host.path`/`installation_context`/`installed_interpreter` 三处字段自相矛盾，属过时固定文本；我先据该句下调本行，读到内部字段后纠正回来，保留全部原始字段而非二选一。下载件在 `.project-local/task-runtime/q14-artifact-20261006/`。 |
| Q15 第一包收口与第二包交接 | PARTIAL | 唯一本表维护当前事实，47份Q02与既有历史归并完成；顶层保存原则与AAOS-01权威入口已同步。本run完整门禁与原生21步通过，尚不能登记第一包收口：新Green真实部署/媒体UI、同资料审核学习纠正旅程、真人Owner、真实云核验/专业依据、音视频原件fidelity、用户旧库完整语义迁移与旧入口冻结仍缺。已审计公开文件清理实际执行，稳定恢复和未知归属资产保留；不把高难缺口改名低难交接。**本轮实证把这一判断落到实处**：Q02 与 Q14 的 artifact 逐字段核对后，两条原生旅程都由 `verify_nsis_install.ps1` 装好后跑在**已安装宿主**上（`host.path` 在 `%LOCALAPPDATA%\ArcheAxis Knowledge\`、`installation_context` 写 `Parent installer verifier supplies installed host`、`installed_interpreter` 指向安装树内解释器），installer/host/CAS 三个 SHA 均有绑定；但两者的 `install-preflight.json` 都是 **`complete_lifecycle_verified=false`**，`checks/acceptance.json` 的 AQ26/AQ27 仍 `NOT_RUN`。故"第一包收口"缺的是**完整生命周期与真人/物理交互层面的资格**，而非安装是否发生；不把高难缺口改名低难交接。（收据的 `limitations[0]` 与自身字段矛盾一事见 Q02/Q14 两行。） |


## 历史执行记录

以下记录保留各自运行、SHA及当时状态；其中“当前”“正在执行”“未提交”等只指该记录时点，不替代上方当前结论，也不证明不同SHA的资格。

最新固定资格为7e8896447dfbfd5feda3f19fdb35d38a5462dd50 / workflow308098767 / run37397560144 / attempt1，已终态FAILURE：17项job实际success，desktop-build与a0-gates failure，installer-lifecycle skipped。desktop-build在中文界面合同步骤失败：capability-map已增加media.video而生成catalog仍旧SHA。已使用canonical generate_capability_catalog.py重新生成并通过--check，当前前端34文件243tests、tsc与生产构建PASS；尚需下一固定SHA完整CI，失败或跳过候选不得部署。当前普通内容迁移、媒体链和保存政策的实际范围见下方各自收据；不能将历史成功外推为新候选安装态。

真实旧库普通内容迁移：已知89业务表旧库kb_documents/kb_cards均0行，独立intake scope仅ir_intake_cards实际1行完成typed原类型保留→Core普通Document v1/v2→过期写409→历史版本→重启一致；其余表仅schema/原库保留，不声明全库迁移。CLI两正七负9项PASS、Rust scope五项PASS，原DB SHA b318c99e5a58107f3fe57249b50e2560563b0dc6cca606505ef61ad19f64b411前后相同。原迁移收据dd761720734fa43f5c5c8d0f78d83cd81ea426f43d0128b2ceb733bdb23eb446的limits文案误指两空表，原件保留；独立只读重启收据aaos01-legacy-readback/cd9f954ff41a49fe8f538d2decdd2920/receipt.json SHA46eb5824bceb0712279757c4e0efdbd4efe2d4dc829a0a85221548bad48b7009绑定原证据/typed行/实际intake scope，五断言PASS，0重复导出/0新Document。无伪Source或真人认可；自有Core按creation退出/端口释放，不冒称产品正常退出资格。

固定9a6/workflow308098767/run37395636243/attempt1已终态FAILURE：17job实际success，test(3.12)/rust-vnext/a0-gates失败；desktop-fast/build/installer-lifecycle实际PASS，完整结论不可登记成功。Python注释定位过时video/QuickTime/有限预算/README权威以及漏报能力归属，原路径定向42PASS；Rust本地完整workspace执行到route_capabilities实际两失败（旧video未注册断言），终态CI内存脱敏提取也确认仅同两测试215/233行失败，不保存或回显原日志。修复后该8项及application/其余七crate全PASS，API全套在前轮实际PASS。新scope/合同修复仍本地未推送，等待期间未推送或取消目标运行，需下一固定SHA完整资格。

Green旧候选续清最新PASS：活动守卫fresh为0后仅续删20324项/861,807,904逻辑字节，全部80324选中路径ABSENT，总原逻辑3,437,316,559B；四ZIP/manifest/恢复helper/原计划/失败partial receipt守卫不变，未知/私人内容及目录保留。收据主项目.project-local/recovery/green-phase2-public-20261006/cleanup-continuation-4d2cba1a31b6449f91307e489831f62c.json SHA8ecf4b0fd4e56d64a22743046f0feb3e4458cbc9ae53306d24dfd936b2985c66，物理净回收UNMEASURED。以下60000后停止记录为历史，不再是当前阻断。新固定9a6c42c6cd733220251e4d9bcad81f2693fe57ad/workflow308098767/run37395636243/attempt1正在执行，期间禁止推送；本段清理增量未属于该提交。

再生缓存清理实际PASS：按既有审计清单fresh SHA，6个变化中间文件及1个变化PDB KEEP；仅3160未变对象实际删除2,210,835,389逻辑字节，selected全ABSENT、7项KEEP与恢复ZIP/manifest/helper守卫前后相同。收据cargo-2611-unchanged-subset-cleanup-08ec9b09b3264567b35f36e721231232.json SHA275efe71b062c3d0967a1d95ef01e452d1216b1f9b18a04730190fe1207fcd18，物理净回收UNMEASURED。Green续清仍受其他项目活动消费者守卫阻断，未绕过守卫。

并行界面复用增量：复用旧Avalonia检查器Ctrl+Alt+I到现React共享toggle，保护repeat/IME/AltGraph/命令面板与卸载监听，保持草稿/焦点/导航不变；三新增测试先实际RED，修复后App23项与全前端34文件243项PASS，tsc及生产构建PASS。仍为SIMULATED源码验证，下一固定候选原生部署待验。两个已知data/cognitive_os.sqlite只读schema核对同SHA b318c99e5a58107f3fe57249b50e2560563b0dc6cca606505ef61ad19f64b411，89业务表/90SQLite表、无workspace_meta，不是交接称98表；未读取行正文，vec_episodes因vec0不可用，实际全表保留/语义迁移仍未完成，98表精确路径UNKNOWN。

最新保存政策验证：当前源码真实产品HTTP链47次调用通过，普通无Source/Evidence内容、未复核识别、疑点/版本、独立专业依据状态、权限拒绝与重启/备份恢复均留证；aaos01-content-policy/0dfef89652784a6b9f793eba124d9992/receipt.json SHA f583c5accf825b0de5f4e188675f6a0bfd5876b3e72722696f5a1aeeaa968712，执行Core SHA1ada9ebbae13569d918c610fcc92f402322093c8d02fff9b0277d9d3050dc20d。云端未配置明确not_executed，未伪造实际云核验。新增document_cloud_loop五项Rust回归全部PASS，DNS/timeout/policy/HTTP503/零结果回执重启保存与重试不阻塞正文；这部分失败响应为SYNTHETIC协议夹具。首轮夹具错误状态及第二轮非零退出契约遗漏均实际失败保留，修正夹具后通过，没有放宽生产校验。

当前非媒体治理增量：README历史区误指R6为当前入口已修为唯一AAOS-01台账；Formal远端description实际核对正确，Green根实际不是Git仓库，不猜测远端。旧库typed preservation工具已进入当前源码，完整17项canonical Rust测试PASS，保留SQLite类型/原始字节/rowid/未知表/schema/同一只读快照，固定SHA文件名与64KiB流式hash；尚未读取或语义迁移真实98表用户库。Green四旧候选80324公共文件恢复证明通过，已实际删除60000项后守卫发现4个其他项目Python进程而自动停止；收据green-phase2-public-20261006/cleanup-31ddbf4882c54c55bad2e99fe38c8c24.json，remaining20324已准备精确续清、未执行。所有ZIP/清单/目录/未知及私人内容保留；不能报总3,437,316,559B已回收或物理净量。

字幕最新实际GREEN：新Core SHA f5e0cf384957ec29c9b682ba1da04646f557fe39680b3165d5bff12ac3362622，SRT/VTT各294句逐毫秒0偏差，time anchor201/located，各五类错绑400，原件/全部输出/锚点独立重启相等；收据aaos01-subtitles/c1294089b64f4224b5b2aeb7e4592210/receipt.json SHA860c7957fa84bc525aa5525989026a1ede1d22d894091c83acbc7a8a52538031。复用实际MP3 ASR经产品HTTP导出父结果，没有新ASR/模型调用；仅验证派生字幕声明与持久化，不冒称原ASR人工准确率。当前媒体/字幕/路由55Python PASS，字幕/evidence anchors5Rust PASS，MOV旧probe兼容3Rust PASS，前端全量34文件239PASS；Core两crate扩大回归首轮在旧MOV/MKV类型断言失败，已针对真实命名/读取边界修复并定向通过，未将该首轮整体称PASS。

2026-10-06 最新音视频实际状态（以下较早记录按其原运行保留，不覆盖此状态）：真实717426ms MP3，以及同一真实视频全时长衍生WAV/M4A/FLAC/OGG/OPUS，均已实际完成import→job→ASR→Core持久化→合法时间锚点/错绑拒绝→重启读回；五音频矩阵收据real-audio-matrix/matrix-30dc18b4ce614142bba34b51da345c1c/receipt.json SHA3352579bb43011560ee527a82f61e5a68497bb625493ad668a1f642dedf210e4。WAV44raw/36合法/8疑点、M4A12/11/1、FLAC13/13/0、OGG15/11/4、OPUS37/37/0，全部原始文本保留，疑点未冒充可靠定位。

真实MP4新媒体job实际succeeded/81.391秒，duration83046ms，22raw/16合法/6疑点，3帧实际LM Studio qwen2.5-vl-7b-instruct返回stop。Rust Core将3帧与完整16k单声道音轨登记既有Source/CAS，原worker输出字节及digest保持不变，Core派生引用由quality.core_artifact_adoption读取；初验脚本访问已清理临时路径、继而读错loss DTO两次失败均保留，没有重复ASR。补充产品HTTP验收18断言PASS：四派生原件SHA/bytes、两次重启、独立备份恢复；收据real-video-core/readback-ec8acbb249c74d07ad90f37841338709/receipt.json SHA301b731570aac25d9fe1f1b55cc77b2fedec104c9e05ad23e3c19e9275e190f1。执行Core SHA c7a6d93ade0871ad97a7ccf54a452dddb6f7581fc65bc89f15539177562e2d1b，新增quality投影读回Core SHA81d1c749134095fbfd05b49151c5988b3e3b7bab888fc2cd3e43f7ab7e261193。均为REAL混合本地源码worker/产品Python，不是最新安装态或真人语义准确率；抽样帧不声称连续视频全覆盖。MOV/MKV/WebM正在逐格式实际执行，未提前登记PASS。

MOV/MKV/WebM各独立完整Core链已3/3 PASS，真实运行分别84.406/93.391/82.078秒：MOV22raw/16合法/6疑点、MKV21/19/2、WebM38/38/0；每项3帧LM Studio实际stop，四CAS原件/重启/独立备份恢复18断言通过。矩阵收据real-video-core/matrix-3593ed4d4db94f3c972bdbe2cd10189b/receipt.json SHA42898178fb32b70adf4d2668fe6b026b84e1e326d0dbcfdcdf3261ba095eea18。损坏MP4负例实际PASS：import成功、job failed、输出404，原件与错误重启一致；收据real-video-core/02d758378d91488ab9769d496175ed3b/receipt.json SHA4f96556d7b2135f682c70d35df0bcc31831b8058872726e54cb3a3c9029790d0。无音轨视频与独立字幕链仍在执行，不提前登记。

完整去音轨MP4实际负例12断言PASS：派生SHA3f01af4df233ed821ebdb287859356460f1383b1b984c2ea2e1cca71af404f4d/25,496,293B，job40.672秒succeeded但pipeline partial，ASR failed/audio_track_unavailable_or_decode_failed、0raw/0cues/空转写；3帧真实模型stop及CAS原件、重启、独立恢复均通过。收据real-video-core/56b57dfdf42b4de28781a3d07248da5f/receipt.json SHA4ae783e56b2e6a6155b72a6c4dd63b6ee11fac7cac94ce9bbbbdb7092d450f99，不把视觉可用冒称语音成功。独立SRT/VTT真实链已发现每格式67个毫秒偏差及时间锚点未支持，尚未闭环PASS；正在针对性修复，不重复ASR。

当前增量验证：Tauri cargo fmt --check与完整70tests PASS，资源校验无custom build command失败；媒体CAS事务/备份/原件来源21项Rust PASS；媒体partial/定位/视频管线22项Python PASS；路由/导航/传输/项目合同245项Python PASS；转写UI9项PASS，当前tsc/生产Vite构建PASS。ASR生成器中途异常现在保留已产原文与合法cues，processing partial与alignment独立，零片段异常仍非零失败。uv.lock未改，SHA0f73ea804b0eca61a251013d199f75d88f35e6322bb155eb2581b8d10f69ce52。本批媒体修改尚未提交，不能借用d91的CI成功；新增媒体安装态与真人核验仍待验。

2026-10-06 当前用户修正：音视频不再以 media.probe 作为闭环验收；需实际解码、ASR/时间定位、视频抽帧 LM Studio 识别、Rust Core 持久化与重启读回。PROJECT_CONTRACT.yaml 已增加本轮要求，未修改不可变任务包，以下历史 probe PASS 仅保留为头信息子步骤，不代表新媒体闭环通过。实际共享 faster-whisper-large-v3-turbo + Green 产品解释器执行真实83秒用户视频音轨：修复后22个原始片段全部保留，16个合法定位片段、6个越界疑点，alignment_status=partial；不裁改时间戳、不伪造全文可靠锚点。真实收据 aaos01-media-real/aec9dfec8ed8427a89d14e1c9b7c55ed/receipt.json，输出SHA71b05847b24edfc1101c683d3f61c91fdca80800214810ad6be1e73234b7e61f。定向回归3PASS；Core与安装UI媒体闭环仍NOT_EXECUTED。LM Studio qwen2.5-vl-7b-instruct 已实际执行帧识别，语义忠实度UNVERIFIED，不等于连续视频理解。

固定d91ab8b1c1507f5408172cb355cfc1bf8c547fe2/workflow308098767/run37386325921/attempt1 已终态completed/success：20个job实际SUCCESS，含desktop-fast、desktop-build和installer-lifecycle。等待期间未推送，当前音视频增量不在该SHA。该运行安装typed制品11379058524非空550,651B、ZIP SHAa4bbc367784773e2ef02162d9e3c72dcdbcea801e27c9e9debebc5b0b75f2f3a、CRC10members通过，原生21步骤均实际完成，新增快捷键六字段通过；尚未将新候选安装到Green，不把该CI成功外推新增媒体验收。

真实完整MP3导入首轮实际HTTP413（5,849,401B，source SHA6e90d59a01c9e18aab5ddbba5133d7880c38b62fa956cb8a90ec49fd6ce0781d）；未创建job，原件前后相同、引擎真实import通过，自有Core身份退出与端口释放通过。当前已针对性统一64MiB原件/90MiB导入JSON及有限桥接原件请求读回、媒体worker输入64MiB，其他操作和1MiB协议帧不变；真实HTTP 6/26MiB合成二进制导入及逐字节原件读回回归1PASS，当前Core --locked build通过，真实课程重跑待验。该有界整块导入不是无限大小或流式能力，不裁短课程规避限额。WAV/M4A/FLAC/OGG/OPUS/MOV/MKV/WebM八份全时长补样已生成并逐SHA/ffprobe/源前后校验，收据aaos01-media-derived/d54f4f6f7a364001bf44f43247a7b309/receipt.json；仅PASS_DERIVED_ONLY，不代表各格式Core闭环通过。

615项已审计MSVC debug/deps PDB已实际精确删除24,737,148,928逻辑字节，收据主项目.project-local/recovery/cargo-msvc-pdb-20261006/cleanup-receipt.json为PASS_SELECTED_ABSENT_RETAINED_GUARDS_UNCHANGED，30项保留guard SHA不变。逐文件恢复已验证的稳定归档4,859,179,621B/SHAf32c976fb2c0c1428f0b52eab619b4145cfe8d325356adb32449f60710a06bc1保留；源减归档逻辑差额19,877,969,307B，物理释放UNKNOWN，不推导整仓净量。

真实完整MP3当前混合本地Core链已PASS：原件717426ms，actual ASR258.297秒，294 raw/294合法cues/0alignment issues；实际时间anchor、wrong range HTTP400、两次Core重启读回一致。收据aaos01-tools/real-audio-core/readback-154bbc0706504c37a65755a92a279411/receipt.json SHA1461baf2c80e5d318fc3dfc9866ef08da68d531ad834891dd89d3ef96a739e9c，补充验收0新ASR job复用已保存成功任务；首probe错误把quality engine当握手identity，失败收据保留，实际quality为python-worker-transcribe/0.1.0。此为REAL混合本地，不是安装态或真人准确率。视频旧Core实际import202后83.329秒InvalidReceipt，三输出404，收据real-video-core/8119be9e96484aa8b228313c86aaa20e/receipt.json SHA3767f04a5901f06f8b9469eb7c0c130fbd3089363c2b35350ef2cca73087212c；独立源码证实ENGINE_PROFILES遗漏video项，已补精确python-worker-video/0.1.0，仍需新Core验证，不能仅凭共用错误文案排除其他structure/coverage原因。当前前端全量34文件238PASS、tsc/生产Vite PASS；Tauri预算回归1PASS、两个Rust预算回归各1PASS、fmt工作区及Tauri PASS。所有真人/安装态新增媒体仍待验。

最新固定9940b981ca916021b6f8018f5a0d62673adfe028/workflow308098767/run37384994749/a1已终态FAILURE：17success/2failure/1skipped，desktop-fast、Rust、Python及合同实际PASS；desktop-build的Inject CI candidate identity失败，后续打包与installer-lifecycle未执行，不能按完整通过登记。根因已真实CLI复现：CI默认cwd D:/a/k为junction，身份注入遗漏canonical cwd override，触发既有link拒绝；相同CLI junction exit1且manifest未变/identity不存在，ordinary路径exit0登记成功，证据identity-junction-fixture-20261006/receipt.json。已一行修为github.workspace，不放宽链接或清单守卫；待下一固定SHA验证。

精确Formal主Cargo中间清理实际PASS：10920项/6,352,845,335B全部ABSENT，清单SHA bd38b557f58eee2f6000899c777d632d3e0f603af85bdfa7b194fe5d871b52cc；fresh CIM0、顶层程序与源码guard前后SHA不变，收据cargo-2611-intermediate-cleanup-receipt.json。PDB/exe/DLL/lib/exp、build未知输出、58未知fingerprint及锁/资源保留；不重复已清空incremental及已ABSENT release资源，不宣称字节可重建或物理净量。

安装端快捷键验收已接入现有WebDriver探针：保留此前20项断言，新增真实W3C Ctrl+Alt+J键操作及trusted事件、展开/收起、正文焦点、内容、无API写入、正典版本不变检查。现有shell合同4PASS、Ruff PASS；ignored Green预检严格兼容已知20/21完整序列，2正/16负结构用例PASS。新21步骤尚未实际执行，不把静态检查登记为原生通过；物理IME仍未验收。

当前检索错误增量：document_check仅为既有retrieval_failure回执增加受控failure_code/failure_stage/http_status，不持久化异常正文或URL，不改变权限、SSRF、代理或网络配置。隔离worker定向27PASS、Ruff PASS；新字段实际Core持久化未验收。产品解释器执行当前worker公开检索实际约8秒后非零，安全分类timeout/transport，收据public-retrieval/c4e84fc7925d4c9f8e2af16deb5c8f8d/receipt.json SHA df7cc5255bdac76682cd6b93c77fc3c56fa23c7959bdbc3e8a1130bfdb560cf1。独立官方SQLite页面同一安全HTTP链实测200/27068B；不能归因为全网不可用，也不能宣称专业检索或云核验成功，目标服务具体超时原因UNKNOWN。

当前固定门禁：已正常提交并推送f471584b041163ff20add16676943aac576353a0，workflow308098767/run37377966094/attempt1，workflow_dispatch(force_full)全四元组核验PASS；终态completed/success，20个job全部实际SUCCESS，含desktop-fast、rust-vnext、test(3.12)、desktop-build及installer-lifecycle。等待期间未推送。同SHA自动push37377840593/eventpush终态completed/cancelled，取消运行不计PASS。本地未提交增量不属于该SHA产物。OCR成功b收据SHA59bc4a88d41da0bd54ac9b231fbdc7f7fcd0bafab1c9af1f14d4bb8bbe78d3dd；首轮a生成引擎/安装包逐SHA及fresh无消费者后清除，仅保留失败收据，不计历史项目减重。

固定f471安装态实际资格：artifact11373902215非空549920B、ZIP SHA0a712ec20b553f1b916f02763b267dd21f0fc36885ca0c16fa69c11534f4634a，typed receipt535911B/SHA17f31df391c3e648b1de280a55a29debdcf1f72b3b6a3a2f35464c5c8e4316d3，ok=true且20个完整原生步骤均实际完成。Source/Document/Anchor/Version四区导航actual_focus_verified且sources/documents unchanged均true；五次正常product_exit_application exit0、自有进程身份及端口释放均true。安装host SHA3520bd18749d534ea91827ca9b6419be7da9348369f5e4bd4e9fa8e319d8ff28。固定版本OCR准备步骤SUCCESS且artifact内ocr-receipt.ok=true。新CI候选完整解包与本地/Green路径资格待执行；该成功不代表Green已安装或真人Owner认可。

当前安装包合同缺口：f471官方NSIS实际解包21729文件，权威清单及host预期21728文件，唯一未登记项runtime/release-identity.json。原注入器真实exit0但完整集合不等，不能以CI成功替代Green严格资格。现有注入器已增加显式--manifest，复用权威暂存器路径/哈希规则，先验证原完整清单后登记identity到同一files表；CI传入权威清单。身份及发布合同回归41PASS/1SKIP（fixture symlink权限），新增实际CLI commit/tree错绑拒绝及登记回归8PASS/1SKIP，仍待下一固定SHA安装包及Green验证；未放宽额外文件断言。

GNU精确中间产物清理实际PASS：仅本worktree .project-local/build/cargo-gnu内58882个编译中间文件删除6,465,395,761B；313项exe/PDB/locks及顶层产物逐SHA保留，fresh无消费者，errors为空，收据cargo-gnu-cleanup-proof/receipt-fa6cc08587e84a068207058a8cfd3927.json。与本轮另外两批合计原文件逻辑删除8,958,317,221B；不等于整仓净量或物理释放。296项公开GNU构建exe已稳定归档，逐文件实际解压与源前后SHA全部一致；随后root精确删除14,358,913,436B，selected全部ABSENT、17项顶层/locks等保留SHA不变，cleanup-receipt.json为PASS_SELECTED_ABSENT_RETAINED_GUARDS_UNCHANGED。稳定恢复目录为主项目.project-local/recovery/cargo-gnu-binaries-20261006，archive3,252,315,372B/SHA7218c14f829393ea89660767d1a24be76d08e447107f148b034fc8cc30fd497e；此批源减archive的逻辑差额11,106,598,064B，物理释放UNKNOWN。首轮sandbox CIM拒绝在删除前终止，正常获准Windows身份fresh CIM后执行通过；未关闭或绕过消费者守卫。

文档治理实际执行：既有索引明确为早前逐轮记录的五份THE-*已逐字节归档到docs/history/aaos01-20261005/，15,109字节、五个原始SHA全部读回相同；原路径保留兼容链接与superseded-by到唯一台账。收据aaos01-tools/archive-five-history-receipt.json；不重复47份Q02标记及三旧台账归档，不将该动作计作磁盘减重。Green备份backups/inplace-maintenance-wal-20260902的runtime/python/Lib/site-packages/.hermes已在入口停止遍历，未读取正文；整树公开载荷归属未证实，原件KEEP。正在仅按公开安装文件清单证明可回收闭包，不把私人子树作为缓存删除。

固定f471的两项独立Core证据已采集：run37377966094/a1的Office artifact11372014258非空5904B、ZIP SHA0377ccae54ca65d2da2d8f965d03cbd7b6a532c9202b8b31cd1cabf8ed8307ff，真实产品解释器SHA4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a实际import openpyxl3.1.5/python-pptx1.0.2；XLSX/PPTX正样本succeeded、损坏样本failed且四项restart_equal=true，uv.lock SHA0f73ea804b0eca61a251013d199f75d88f35e6322bb155eb2581b8d10f69ce52。内容政策artifact11372408900非空5019B、ZIP SHAbff924bc483affc5cb1fc361d009b61bbab98deb10b3c8a6208a5d12a6a3c74f，九项保存/独立核验/历史/权限/恢复断言实际true；真实云调用与真人审核未执行。首次沙箱下载401失败保留，正常获准认证路径重试PASS；仅typed receipts、不读取原始日志。该两项采集时CI尚非终态，随后独立安装态及终态证据见顶部，不由收据采集代推安装资格。

等待期间本地未提交UI增量：复用Avalonia活动回执Ctrl+Alt+J，当前Canonical/Legacy ActivityDock共享鼠标键盘切换；真实CommandPalette open状态通过StatusBar/App传递，忽略repeat/isComposing/AltGraph及命令面板已开，卸载移除监听，切换不导航/写入/刷新任务。三新增SIMULATED回归先RED后GREEN，相关28PASS、全前端33files/231PASS、tsc/Vite build PASS；原生键盘及物理IME未验收，该增量不属于固定f471产物。首轮测试执行器GBK输出失败不算回归RED，使用-Xutf8及实际Vite配置后的三项失败才是RED证据。

两项既有目标清理已执行读回PASS：host-restore-target/debug三个精确编译中间目录及991个deps中间文件回收3455文件/1,914,603,483B，唯一历史host/PDB、manifest全部payload及启动文件逐SHA前后不变，fresh无消费者，收据host-restore-target-cleanup-proof/cleanup-receipt-d0a0e51317694383a2cbcfac005d06e6.json。首次预检误拒合法文件名含..，未删任何文件；修为真实路径段与resolved边界后完整预检及执行PASS。Green旧维护备份仅17028个RECORD哈希匹配公开文件回收578,317,977B，全部selected ABSENT，.hermes入口未读且存在、两个旧host不变；唯一实际恢复临时副本也删除但不计原项目回收，收据green-maintenance-public-recovery/c084709848754a6886816ad927faeba9/cleanup-receipt-9c27c16710494ff9a491b7046443bbd3.json。203,025,470B恢复ZIP与3,877,895B清单保留，旧备份使用前必须恢复；稳定主项目恢复存储迁移已执行，证据见下一段。两批原文件逻辑删除总量2,492,921,460B，不等于整仓净量或物理释放。

稳定恢复存储迁移已执行：主项目D:/All projects/ArcheAxis-Knowledge-OS/.project-local/recovery/green-maintenance-wal-20260902/保留同SHA公开ZIP/manifest、自包含restore_public_runtime.py及三份原始证明/删除/迁移收据，均读回SHA一致；新恢复脚本check-only实际17028成员CRC/精确源ABSENT/哈希通过，不依赖临时worktree。Green恢复指示已更新到普通稳定路径且读回SHA3a45c32d072a31e616419942217df38d443cc1fa67f15ade57691339e9267124；旧worktree相同archive已移除，不重复计减重。迁移收据stable-recovery-migration-681ca2b2d03047e1beafb68160a8674d.json。单次当前体积元数据读回：Formal可读逻辑125512826458B（.project-local123763757908B），Green19804102634B（.ui-task-tree15023268252B）；排除private/reparse/访问失败，缺同覆盖即时前测，整仓净量/物理占用UNKNOWN，不能宣称仓库治理已完成。

安装OCR修复已本地验证：scripts/ci/prepare_windows_ocr.py + windows_ocr.lock.json固定官方release Tesseract5.5.0.20241111安装包SHA和57binary/DLL逐SHA，7zip只项目内解包、不执行安装器、不改registry/machinePATH，固定eng4.1.0 SHA；实际重新下载/解包/版本/语言/黄金PNG OCR全部PASS，aaos01-ocr-tools-local-20261006-b/ocr-receipt.json ok=true，真实OCR GOLDEN ANCHOR匹配。首轮a因实际版本含v导致断言FAIL原收据保留，精确版本正则修后b通过。installer job先准备此引擎再安装链，GITHUB_ENV仅job引擎变量；Linux OS引擎语言目录从dpkg实际唯一eng.traineddata解析。五测试改读配置TESSDATA_PREFIX保留原fallback与skipguard，原23OCR skips真实重跑23PASS/0skip，收据b3dc1d418b1b45b38b61d6fe247236db SHA bed4b604bb9d266222457efbaaac4c2468fee11b2650aa60f90e5f9c6eafacb2。其余13skip仍原限制；所有本地结果非下一SHA CI/Green部署。

完整本地OS tests终态：4021PASS/137subtestsPASS/36SKIP/0failures/0errors，426.82秒，canonical70f0e2edfd57，证据aaos01-os-verification/fc2a33c317574887a4b3f58a621228b1/receipt.json SHA135b0135435c80ad80d390311719b15818f03a904293e6582b5f509468c75a9b，JUnit SHA0b5bfb720cf8e55d7f38aa65e84a70b210fecb217f4aacb8097134de6f3eb746。23OCR缺引擎/语言目录、7symlink权限、2network未启用、4外部材料/显式捕获条件skip不算通过。d6固定安装artifact11372215630非空348279B/CRC PASS/ZIP SHA3f13dfeccd06a6495ae3a74a6151b67e6f55d3c54f88d5fee31aea4d3a5c4ba7；bff347322b9641e19c0922528167d866 receipt SHA12dadbac03b0009fc270f2d26f17121ca7ec81c3ec46552dc0fce7985deeec6f为ok=false，15steps完成但黄金PNG真实OCR job失败AAK-WORKER-003:tesseract binary not found on PATH，后续matrix/final restart未完成。四次正常host exit0/身份与端口清理通过；非握手/退出失败。当前按已声明OCR依赖准备项目scope固定Tesseract，不执行全局安装、不跳断言；尚未修完或推送。

产品解释器公开检索实测：Green f151 runtime/python.exe -I -B实际执行当前document_check.retrieve_context，有界SQLite公开工程查询（无用户内容、无模型调用）两次均retrieval_failed/非零，cd8876及119fe收据保留；正常Windows路径第二次仅诊断SafeHTTPError，约15秒、无search/article回执，内部网络/DNS具体原因UNKNOWN。证据仅REAL公开检索失败，不外推云核验或专业分析成功；不放宽safe_http保护或修改代理/全局网络配置。

固定d6门禁新增失败定位：test(3.12) job111978585525的Run OS-level tests失败，typed check annotation指向tests/test_tauri_security_contract.py:122旧固定value.len()>128断言；本地同断言RED已复现（CI rawlog未读）。待提交测试修复明确job_id200/其余128、job-only点号及拒绝点路径，产品守卫未改；canonical ci-id-contract-green-20261006-c静态合同5PASS。前次root带conftest触发沙箱SQLite Win5未算复现，参数解析失败未算测试；定向noconftest适用于此纯源码合同，不替代完整OS门禁。当前CI已终态FAILURE，修复未推送，未取消目标；其余成功项不能覆盖该失败。

待提交二级导航实现：ContextNav→App→SpaceView→CanonicalLibrarySpace接入资料库来源原件/已保存文档/来源锚点/文档版本四项同空间导航，聚焦已有真实对象区域且保留编辑器挂载、dirty及原有对象切换守卫；未选对象显示空状态，不制造来源或版本。定向20tests、全前端33文件/228tests、tsc及生产Vite构建 PASS（SIMULATED UI，canonical runs library-object-nav-test/full/type/build-20261006-a），原生探针保留既有断言并加入四项对象区域实际焦点与来源/文档未增加断言，AST/Ruff PASS、原生执行NOT_EXECUTED；未进入当前d6固定CI或Green候选，不登记原生部署验收。Green既有dotnet审计只补exact ArcheAxis.Desktop/obj恢复证明：当前23文件2,277,423字节，压缩914,144字节、CRC/实际恢复逐SHA PASS，bin79文件SHA不变，producer历史终态UNKNOWN仅作限制，合同未将它设为永久门槛；fresh Git核实该Green mainline有19项tracked修改，实际dirty守卫阻止清理，因此保留原obj，不把历史820MB当可删体积。仅清除本次自有restore临时副本，归档/manifest/receipt保留；不计项目减重。

已完成旧候选重复运行时清理：epub-members-20261006/runtime 的19,473文件/625,614,246逻辑字节经 donor f151f4c7998a + 六文件40,526字节overlay完整恢复、逐SHA相等，并真实导入openpyxl3.1.5/pptx1.0.2 exit0后删除；成功临时恢复runtime同步删除，但不计入原项目减重。清理收据aaos01-tools/epub-runtime-cleanup-c9b3015bb64245a7a2350dab1493e071.json PASS、两目标ABSENT，recipe/overlay/恢复脚本/历史manifest/Core/host及donor保留。初次沙箱CIM失败未删除，正常Windows执行fresh检查无生产者/消费者后完成；打开句柄UNVERIFIED，物理释放及整项目净变化UNMEASURED。三项本轮清理合计21,286,212,907逻辑字节，不包含新增候选副本或历史已删路径。

普通Green独立入口最新读回：4694a92106674e01b69bb7181b445a99/receipt.json SHA `0e7eb8dff5d28e44778c1be4850a97f3559c75fe034312e8a889e3e9808c307c`；45秒有界ready轮询实际2次观察“后端状态：本地可用”，正常工作台标记存在、恢复/不可用/浏览器开发标记false；实际VBS无调试可见窗口/schema11/host exit0/自有PID与端口释放通过。ok=true但整体status=PARTIAL：启动短命Python子链未观察到，不从profile推断actual interpreter execution；该限制不抹去独立Green实际格式worker/产物链cb21收据，也不把它外推为普通启动子链证据。warm restart保留首轮所创建空data，没有删除或迁移旧库。前次状态栏断言失败收据原样保留。

外部服务状态：GitHub官方summary API `https://www.githubstatus.com/api/v2/summary.json` 当前报告Actions degraded_performance，incident3q1yb5m7ltvb从2026-10-05T19:11:58Z开始，19:50更新确认hosted runner分配延迟跨配置影响启动。此前未接单annotations与现象一致；本目标内部归因仍为推断，Rust已接单后的30分钟执行超时不因该事故自动变成通过。固定d6 run现已queued/gateplan queued，无已执行目标断言；已取代的自动push run37371567271已终态cancelled，正常cancel请求已获终态，不再是此前queued状态。等待仍禁止推送。

当前固定门禁：已正常推送`d6fbc751dd8f12f8f8a7c65bbffd5dd67c58eb95`，workflow308098767/run37371593899/attempt1，workflow_dispatch(force_full)完整身份核对PASS；终态FAILURE：20jobs=13success/3failure/4cancelled；Rust、desktop-fast/build、Green候选等SUCCESS，test(3.12)、installer-lifecycle及汇总a0失败；migration-targeted/py3.11/lint/wheel取消不算PASS。等待期间未推送；目前先收敛安装失败与本地完整OS结果，再固定下一SHA。同SHA自动push run37371567271已终态cancelled；平台调度内部归因仍为推断。下面新增状态及authority索引纠正为本地待提交文档，未用docs-only推送取消固定目标。

清理实际增量：按用户重建前资源清理约束，仅删除精确`.project-local/build/2611ed9ca1/cargo/release/{runtime,core,workers,shared}`，19,557文件/635,745,356逻辑字节；执行时无Cargo/rustc/rustfmt或该release程序消费者，无链接或用户DB/private文件。四目标ABSENT、锁文件/保留release宿主与manifest/profile、新Green宿主/manifest/Python SHA前后相同，收据aaos01-tools/release-resource-prune-20261006.json REMOVED_READBACK_PASS。保留release的旧宿主现在需要权威资源重建后才能启动，不能把残留宿主当完整候选。与此前20,024,853,305增量缓存清理合计逻辑20,660,598,661字节；物理释放和整个项目净体积仍UNMEASURED，不隐去新增候选和Green副本。文档既有47/47旧Q02 superseded-by标记已经执行，未重复审计或重写历史交接。

本轮落地增量：本地提交`f151f4c7998ae7bab9b4a447afe1840b64c4c9eb`当前完整权威暂存候选`aaos01-candidates/f151f4c7998a`，manifest SHA `26ead3754fd7cf5ae0635d3fc12785fceda9502baf64895e1d42a8da0efdca69`，真实候选19步收据1033f0cde1504ac58589d2deae4f1c98 SHA `4ff829963dccb7efa59769fe6a7c620e4880b60ace4d779c5d54b5518a18b137` PASS。已实际创建Green独立`AAOS-Tauri-f151f4c7998a`，19,507程序/manifest文件逐SHA与字节数复制读回通过，独立VBS及新data已创建；旧根程序/启动器/数据库均未覆盖。Green实际宿主再次完成19steps、6主格式proof及21matrix全重启读回，收据cb21b1e39ab64273aca682bfe6a207f6 SHA `2b5d821a0a58a1b3655ccb8e5c375ffdc8bd4a11936614c7a1d4ea690a3505b2`，5次正常exit0/端口释放PASS。普通VBS无调试启动已观察到可见Tauri窗口、Core loopback、schema11及正常WM_CLOSE exit0；其UIAutomation就绪文本断言仍FAIL（5e40/93020/0da25诊断原件保留；初始JSON单对象归一化和RecoveryShell文本选错已修，但真实状态栏采集未通过），短命Python子链未采到，不伪造normal-launch全PASS。此为本地debug部署，不是installed/Owner资格。新增两候选及Green复制逻辑量不从20GB清理量隐去，整项目净变化仍UNMEASURED。

后续本地修复（尚未进入上述f151部署）：核验失败时保留<=32KB UTF8原响应及有类型校验的引擎元数据，超限只保留SHA/bytecount/明确省略原因，失败不提升成功；worker三模块28tests PASS（SDK模拟）。Core失败回执真实SQLite drop/reopen及重试追加旧原文不变回归实际1PASS，云执行模块定向exit0。既有CheckPanel以纯文本展示模型原文及失败回执，Library有限document_version提供只读历史正文/修订依据，不恢复、不覆盖草稿；两模块29tests及tsc PASS，前次缺DTO必填字段fixture FAIL原件保留，修后GREEN。真实云端和真人认可仍未执行。

2026-10-06最新本地真实桌面增量：候选宿主SHA `0e70ff43bdcc877f390d01f035a032326bef0f30216d8feb5a972e37773344ab`，收据`aaos01-webdriver/320f8a22a6a64a79aad55f127e8c91e8/receipt.json` SHA `98cdf1f95b6ad3009ef245614e6f2d40ee2a82f659bd8bb01f0769bc85c7bf3f`，ok=true，19步骤、6项格式主证明及21项剩余矩阵全部完成完整宿主重启读回，5次正常exit0，自有进程/端口释放PASS。覆盖XLSX/PPTX已知单元格/页文本、CSV、TAR/ZIP自动成员、EPUB实际Reader段落及引用跳转；四损坏样本预期失败且错误/原件重启相等，WAV/MP4仅media.probe头信息。此次是本地debug候选，不是NSIS安装、Green部署或exact-SHA CI；收据步骤中的历史installed措辞由明确candidate路径限定，不推导安装事实。首次真实新增TAR验证40a03收据失败CORE_COMMAND_ID_INVALID，修复Tauri job_id与Core合法点号/200字节契约，保留路径穿越拒绝，RED→8项bridge GREEN后本次真实通过。中文成员/长parent自动job采用稳定有界ASCII身份，真实worker/Core/reopen专项PASS，但该最新Core修改尚未进入本候选Core。中间e358运行本地权限/清理失败且无最终收据，不计证据；探针现已捕获该清理异常并保留失败状态。

当前云端图片增量：既有document_check及LiteLLM adapter接入有界PNG/JPEG原件字节，保留Core64KB预算、原SHA/尺寸与版本绑定，不替换为OCR文本、不改provider。canonical图片/cloud/fidelity 24tests PASS，SDK/network为SIMULATED，未进行真实云端付费调用；大图、PDF、裁剪定位仍未完成。普通保存不受此核验失败阻塞。最新全量前端33文件/223tests（0failed/0pending）及tsc PASS，收据aaos01-frontend-verification/f132e22506ed4bff9ba909df15df6e6d/receipt.json SHA `6a05a20256a3d05f2dffb770b3aaf80d4360c321c967a0e387c5a7d44d82abb7`；src-tauri全量69tests、根及Tauri cargo fmt --check PASS。a2固定CI已终态FAILURE：14success/6cancelled，五项未取得runner，Rust超过30分钟执行上限；完整门禁未通过。等待期间未推送，终态后将按授权固定新提交并启动完整门禁。平台调度内部根因及具体Cargo耗时根因仍UNKNOWN。

固定门禁历史：`5fdbfb48005cfcfd2939bff583ab1266f0909f0e`，workflow308098767/run37362818749/attempt1终态FAILURE；授权rerun的attempt2也已终态FAILURE，完整身份采集PASS，20jobs=14success/6cancelled，不能作为完整通过证据。desktop-fast/build实际成功；五取消项平台报告hosted runner多次未接单；rust-vnext job111951627582已获得Windows runner，但平台明确超过30分钟执行上限，cargo test步骤未完成。调度内部原因及具体Cargo耗时根因UNKNOWN，不据另一vnext-ci运行推导占用。等待两个attempt期间均未推送。重跑后首次采集API仍返回attempt1时显式EXACT_CI_IDENTITY_MISMATCH，未把旧attempt当新证据。当前批次将Rust门禁预算60分钟，保留全部断言，不用cancelled/skipped登记通过。

当前本地增量（未提交、不属于上述固定SHA）：EPUB沿既有解析回执加入Core段落锚点校验及现有Reader段落分页/引用跳转，绑定source/revision/job/attempt/产物SHA/段落checksum。独立真实HTTP收据aaos01-light/4a9c5e7b143143148bf72eda077e1259/receipt.json为PASS：五种错绑返回400，正确锚点、CAS、产物、损失与导出重启相等。使用新debug Core、当前source workers、a16产品Python，明确不是staged/installed；自有两PID创建身份与端口释放通过，terminate返回1，不冒认产品正常exit0。界面16项定向SIMULATED测试及tsc PASS；安装态尚未执行，原件CSS/图片/视觉分页未渲染。

当前实际清理：精确自有`.project-local/build/2611ed9ca1/cargo/debug/incremental`删除113,861文件、20,024,853,305字节逻辑量，目标不存在readback PASS；删除前确认无Cargo/rustc/rustfmt生产者及reparse，保留Cargo/uv锁、Core程序、a16解释器/profile等SHA前后相同。收据aaos01-tools/owned-incremental-prune-20261006.json；物理释放及整项目净变化UNMEASURED。随后canonical dev.py仅对项目子进程设置CARGO_INCREMENTAL=0，25PASS/1SKIP/9subtests与实际环境读回PASS；不改全局环境。未知DB、Green备份及唯一迁移恢复CAS继续KEEP，不重复计历史已删路径。

同批验证：前端全量33文件/218tests、tsc、生产构建PASS；EPUB版本/错绑/无checksum/旧锚点历史专项API协议测试PASS（SIMULATED），已有来源任务/transform/锚点9回归PASS。source_members新增有限读取沿现有id权限守卫，复用实际origin_ref投影及生成DTO；7项bridge测试、生成drift/tsc与6项归档真实worker/重开回归PASS。安装探针保留全部48原断言并增加XLSX/PPTX/CSV/TAR及成员origin_ref/完整宿主重启断言，尚未在安装产物执行，不登记为安装格式通过。canonical Q12探针升级EPUB自身located/五负例/独立重启锚点断言，保留原九格式与四负例。

当前完整本地候选为`.project-local/task-runtime/aaos01-candidates/epub-members-20261006`：权威stage_backend_runtime接受a16 runtime，19,505文件，manifest SHA `75514e34285dd15e181dcda6b2c81ca6295dc5d37239c75f88f1751b4f647776`，Core SHA `8cec3e0f837fd42e2778a33d6baa62e0690a9c565a55200a8f3606f2a6db42e4`，来源明确5fdb+dirty/ASSERTED_NOT_VERIFIED。该候选canonical Q12全13样本PASS，receipt481c7c07e2804027b110232829bfe98f SHA `1f8c8b8cabd84a06e0b7fbfba5faef5d7eec99c01f3e4b7fe4ed4386f89c2cd8`，含EPUB located/五错绑400/独立重启anchor、CAS、产物和export相等；Office四样本PASS，receiptd672e502b1824cc68ab2f2fc6673eb9b SHA `89b3131ba1ab48ef4f6fdcb4a03968a6a6fb3516752a8c85f25483aa808e7d55`。实际import openpyxl3.1.5/pptx1.0.2 exit0，模块位于此候选runtime，Core launch同一解释器（SHA `88b9e780cfdc38597c7f53e20f7165262befa28d9a5e9470360d349e172ecf37`），uv.lock保持 `0f73ea804b0eca61a251013d199f75d88f35e6322bb155eb2581b8d10f69ce52`。此为staged Core/worker本地验收，不是NSIS安装或Green部署；新增候选载荷不从逻辑清理量中隐去。Tauri全量68tests PASS。界面空locations、同source改扩展名不重读及旧enqueue跨上下文继续执行三负例先RED，再22项相关tests/tsc GREEN，未用SIMULATED代替上述真实worker证据。

最新完整门禁通过：固定`3dc286908783930f21a83663a822c5a8fdbdeedc`，workflow308098767/run37358948993/attempt1，四元组与workflow_dispatch(force_full)核对PASS，终态SUCCESS，20个job全部实际SUCCESS，包括rust-vnext、desktop-fast、desktop-build、installer-lifecycle、a0-gates；等待期间未推送。安装artifact11366214081非空176,213字节，CRC/绑定PASS，ZIP SHA `89e4c86d6ff3831a0846d5b85d3039ff37c5b331e76bf4afcf3b019a5d6f32bf`。内层095b9a268600438b974468411f4ecd15收据ok=true，13项真实安装UI断言全部执行成功；四次产品正常exit0，自有PID创建身份采集及端口释放PASS，无残留。installed host SHA `aaed6c36fa54886531ff5ef762bc6f9b1c82108e654a390f0d48cb56340d240a`，installed Core `ec2d77d621b7c4cbd6a976e735fa9d29e15f61113a521598ef2e7525d015af9f`，NSIS SHA `91064feab3fbefa96f3a0e39d19df4de816155adcecd39197649409606a083af`；独立非调试启动可见窗口/后端ready/WM_CLOSE/自有Core退出/新正典库存在均true，profile runtime/python.exe对应安装目录runtime/python.exe。这是安装资格证据，不是已替换用户Green或Owner真人认可。

同run样本typed证据：Office11366013681/5904字节/ZIP SHA `087caef0d1f5f03e26323f0dd044505f80557a7bc233d299e235d2c8cd6f0ec4`，有效XLSX/PPTX已知内容、结构/损失与重启相等均true；损坏两样本failed/无输出并重启相等true。实际import openpyxl3.1.5/pptx1.0.2的路径与Core launch同`.project-local/rt/runtime/python.exe`，Python SHA `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`；uv.lock `0f73ea804b0eca61a251013d199f75d88f35e6322bb155eb2581b8d10f69ce52`。该fast Core SHA b4deceee4c1401b6919af0a0caede6c54737cae49891816edca31c9ce250dbf7与上述独立installer构建明确区分。policy11365399588/5007字节/ZIP SHA `38028699a94db29150a33f016ee6aa68842d63c5547068890b19d05c69a8e671`九行为断言全部true，仍cloud_not_executed，fixture不是实际人审。

Q12本身格式证据：artifact11366740397/19784字节/ZIP SHA `3d4a9c274026687b6c256b5f66146dbd60ded31a4dfab50a128b6c0e4603d691`，四个各自receipt均ok=true；light5e6de52d8222470d87ab50063965144a明确task=Q12、wave=B，csv/tsv/json/jsonl/yaml/toml/xml/eml/epub九个正文扩展及四个负样本验证。独立document backup/restore、exchange文件读回、注入故障各有自己的收据，不用“同Q06”替代；EPUB native locator仍未验证、EML附件保管等限制保留，音视频只登记media.probe，Obsidian未在此CI启动。Office/策略下载起初因run未终态被采集器显式拒绝，失败目录保留；终态后新*-final目录采集成功，不以0字节/旧收据替代。

后续本地未发布归档增量：未压缩TAR复用existing archive.inventory与成员持久化，完整有界预检拒绝逃逸/链接/特殊项/名称冲突/超限，不递归。12Python/12JobContent UI定向、6archive端到端与3container成员回归PASS；debug Core+当前source workers+a16产品Python的独立HTTP两进程正文/原件CAS/located锚点/损失/损坏失败与重启相等PASS，收据96a4e419ec1544909ab08a06b7fc977b SHA `0cd609a1954c32d7edeefa28efdb061fe15da999c2d831857c3bad97614e264e`。生命周期仅自有Core PID创建身份/端口释放，terminate返回1，不冒认产品exit0/全树清理；不是staged/installed。归档成员现复用Office/HTML/Canvas/字幕已支持路由，明确.canvas与普通.json分流；XLSX/PPTX/HTML/Canvas/SRT/JSON六类实际worker/Core原件SHA/正文/格式结构锚点/loss/origin+Store重开精确读回PASS，nestedZIP/TAR/WAV仅保管。DOCX/HTM/XHTML/VTT本轮只有路由覆盖，尚无该成员真实样本；压缩TAR仍不支持。新Rust成员测试所需ci-adapters沿已有uv.lock安装，setup-python之后刷新同解释器接线，不新增依赖声明。此增量不属于已通过3dc固定CI，须下一完整SHA门禁。

历史固定门禁记录（2026-10-06）：`514f606aff1157fa7b6a2c7bac078c7aed041e81`，workflow308098767/run37353509272/attempt1，完整身份核对一致，终态FAILURE；等待期间未推送。18个job实际SUCCESS，包括rust-vnext、test(3.12)、desktop-fast、desktop-build；installer-lifecycle和a0-gates失败。安装typed artifact11363709234为172,524字节，CRC/四元组绑定PASS，ZIP SHA `267a35ab301989a4b45deee1c7ce713af0073bb1e3452aa36b956f63f1c6d562`。四次WebDriver实际启动成功，前十项安装态业务断言通过；第十一项寻找旧按钮“申请或重试识别云端核验”失败，后续未执行。已本地同步实际按钮名称，保留原十二项并增加显式执行/重试失败持久化断言；新十三项尚未安装态执行，不将修复写成CI通过。

本地实际实现更新（未发布）：Rust Core沿现有document_checks/machine_tasks执行版本绑定核验，Python复用LiteLLM、SafeHTTP与检索/正文提取donor，两维分别记录识别忠实度及专业依据；原件文字是识别对照，联网仅辅助背景。普通保存不等待核验。宿主固定数据根config/document-check.json提供非秘密provider/model/额度配置，无默认模型；无配置或非法配置不阻断保存。显式执行/重试、失败恢复与历史展示已接入现有UI，不虚构真人认可。实际根工作区完整cargo test exit0、src-tauri fmt和67tests PASS；联网/配置20回归PASS、相关Ruff PASS，SDK/HTTP传输夹具属于SYNTHETIC，未执行真实云端或付费调用。识别原件当前仅有界UTF-8文本，PDF/图片/媒体原件核验仍PARTIAL；实际provider/model/额度选择与真实服务验收待用户配置。以下旧“尚未实现”记载为当时阶段，不代表当前实现状态。

本轮精确清理：tauri-driver2.1.0的自有target/release五个编译中间目录已删除，639文件、212,379,120字节逻辑量，路径不存在readback PASS；已安装driver与官方重建配方SHA前后相同，收据aaos01-tools/driver-build-prune.json。物理回收及整仓净变化UNMEASURED。既有审计的framework候选现已不存在，不能重复计清理；未知数据库与Green唯一恢复材料继续保留，不据备份推导所有权。

收拢验证：前端全量32文件/213tests、tsc与Vite生产构建PASS。合法材料预检失败现沿已有failed receipt链持久化，4项实际file-backed API测试PASS，覆盖65,001字正文完整保存、无worker调用、明确重试和重启失败读回；非法权限/SHA不新增attempt。桌面仅document_check_execute使用160秒有界等待，覆盖worker120秒加20秒清理预算，普通操作仍30秒。最终src-tauri fmt/67tests、根fmt及route inventory/数量/Tauri Authority/a0合同回归PASS。新安装态十三项仍待下一固定提交实际运行。

历史固定门禁：`29e7f08b84205cedbbdace6228383e8942146eb6`，workflow308098767/run37349719826/attempt1，完整headSha与workflow_dispatch核对一致，终态FAILURE，等待期间没有推送。desktop-fast、desktop-build实际PASS；rust-vnext在根工作区fmt失败，其后测试为SKIPPED；test(3.12)的OS测试失败；installer-lifecycle与a0-gates失败。根fmt遗漏已本地修正，canonical `cargo test --workspace --locked`完整exit0；实际production route inventory遗漏checks/execute已补齐61条，定向4tests PASS。完整Windows OS回归实际3985 PASS、36 skipped、137 subtests PASS、1 FAIL（第二份路由计数仍用36/41）；该唯一断言已同步真实37/42，计数/inventory/Tauri authority/CI a0四模块canonical定向41 PASS、exit0、无skip。完整运行本身仍为FAIL，不把旧CI失败或未复跑全量改写为通过。

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

现行任务状态见上方[当前状态与剩余缺口](#当前状态与剩余缺口)，此处不保留第二份任务表。

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

## 长音频分段执行（用户裁决落地）

用户裁决：音视频不切分必然慢，界面要显示当前转换所需时间、由用户选择是否切分并按其选择执行。
按此落地，不再把 300 s 作业上限当作不可逾越的缺口，也未抬高上限。

- 界面：`JobContent` 先按同一策略给出原件时长与整体执行预计；整体在上限内时可整体执行，也可切分执行；整体预计超上限时整体动作显式停用（保留可见，避免误触上限），切分动作标注段数与可续跑。分段进度只从任务自身损失回执读取；重开一份仅覆盖部分录音的转写时，转写区直接说明未完成段，不把局部当整段。
- 计划归属：窗口计划由 worker 用声明的 ffmpeg 探测录音真实时长后在本地派生，请求只携带“是否切分”。调用方传入的计划已被拒绝——一个留下空洞却格式合法的计划会静默丢掉洞内音频。
- 复用与预算：已完成窗口以录音摘要为键落在 Core 自身 staging 下（不按作业编号，否则每轮重跑），单次执行在作业剩余时间内只启动仍有余量的窗口，遇到第一个放不下的窗口即停并把其余尾部窗口显式记为未完成——单次有界执行总是从录音开头推进，不跳段去解码更小的尾窗。
- 通道边界：`parameters` 仅 `media.transcribe` 可携带且只允许 `{split:true, staging}`；解码器由声明的 capability manifest 解析，不由请求提供（否则等于让请求指定任意可执行文件）。

真实证据（非单元测试）：`.project-local/task-runtime/aaos01-split-20261006/proof-output.txt`，SHA-256 `3c7964942375cd977a67cb122bbf4b54ee655545b1ea571cfa8c99af879d471b`，脚本 `prove-split.py` SHA-256 `0e4dbc109f160dabe2469ef4facc9fb6ac19d0c93ddfab1fdb55adf3a75efff3`，退出码 0。真实 ffmpeg 8.1.2 探测 300 s 合成音（9,600,044 字节），真实 faster-whisper 1.2.1 + faster-whisper-large-v3-turbo 解码：

- 第 1 次 invocation（预算 150000 ms）：`split.duration_ms=300000`、`windows_total=3`、`window_audio_ms=140000`、`whole_exceeds_ceiling=true`；回执 `status=partial`、`windows_missing=[1,2]`；staging 仅 `window-0000.json`。
- 第 2 次 invocation（无预算）：`status=complete`、`windows_missing=[]`、`windows_resumed=[0]`；staging 三个窗口文件；`alignment_status=complete`、`duration_ms=300000`。

测试面：Rust 侧新增协议窗口边界、claim 持久化与 HTTP 窗口语义用例；Python worker 146 项 unittest 与 33 项 pytest 全通过；前端 270 项全通过，`tsc --noEmit` 通过。提交 `b8db1a34`、`22e3536b`、`02e15eff`、`a807ed27`，分支 `codex/dsh-aaos-real-multiformat-loop-20261001` 已推送。

边界：本机未执行安装态/NSIS 验收，未发布，未新增 tag 或 release；合成音不含语音，因此该证据证明的是窗口计划、真实解码、预算中止与跨轮复用，不是识别质量。

## 真实遗留库迁移的当前边界（AQ23）

对象：项目内 `data/cognitive_os.sqlite`，3,223,552 字节，SHA-256 `b318c99e5a58107f3fe57249b50e2560563b0dc6cca606505ef61ad19f64b411`（本轮前后实测同一值，大小与 mtime 亦未变）。

做法：不做整体删除或原地改写，先取字节副本再动。副本 `.project-local/task-runtime/aaos01-legacy-migration-20261006/snapshot/cognitive_os.sqlite` 与原件 `cmp` 相等、SHA 相等，随后只用只读连接清点、导出。

结果（证据 `…/aaos01-legacy-migration-20261006/dryrun-log.txt`，SHA-256 `dd5386e16762fc1e02d0b7c1fb392010c9f93097bf2fd434c33479402806005e`）：

- 清点出 **88 张可读用户表**，并**指名**一张读不了的表：`UNREADABLE vec_episodes: no such module: vec0`。
- 该库使用 `sqlite-vec` 的 `vec0` 虚拟表；本构建不含该模块，因此 `export_jsonl` 在它上面中止（`export failed: sql: vec_episodes: no such module: vec0`），**逐表 JSONL 保留导出未完成**。
- 值得记下的事实：vec0 的影子表本身是可读的——`vec_episodes_id_map` 5 行、`vec_episodes_rowids` 5 行、`vec_episodes_info` 4 行、`vec_episodes_chunks`/`vec_episodes_vector_chunks00` 各 1 行。即向量内容仍在盘上，缺的是解释虚拟表的模块，不是数据。

本轮顺带修掉一个真实缺陷：`archeaxis-migration` 的 `inventory()` 遇到不可读表会整体中止，把"一张表缺扩展"报成"这个库读不了"。现新增 `inventory_reporting_unreadable()`：返回可读表清单与逐表原因；`inventory()` 保持全有全无语义（错误信息改为指名该表，仍全有全无），`legacy_dryrun` 示例改用新函数并按名列出不可读表。新增用例 `an_unreadable_table_is_named_beside_the_readable_ones`；`archeaxis-migration` 全部测试通过（20 项）。

**这不是语义迁移**：现有代码只做保真导出与清点（`TypedExportManifest` 的 disposition 自述 `PRESERVED_NOT_SEMANTICALLY_MIGRATED`），本轮未把任何行并入 vNext 模式。要真正并入 `vec_episodes` 的向量内容，需要先决定是否引入 sqlite-vec 依赖（本构建不含），或改由影子表读取；两者都是待定决策，不在本轮擅自动手。

边界：原作字节未变；未删除、未移动、未改写原始库；未发布。

## 开源池处置实测核对（本轮）

新增只读核对脚本 `scripts/audit/oss_disposition_evidence.py` 与证据报告 `docs/current/AAOS-OSS-DISPOSITION-EVIDENCE-20261006.md`，逐条核对 `AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json` 的 47 条供应链处置。证据 `.project-local/task-runtime/aaos01-oss-evidence-20261006/report.txt`（SHA-256 `3eb0634b11ac1eb355d55822765fee3fc7a93507e44cdeded54e7666b314beee`）与 `disposition-evidence.json`（SHA-256 `158c1d800fe038c0622bbab43c08bce8647e1f25a795e739995adce592843711`）。

实测：`DECLARED` 24、`IMPLEMENTED_IN_SOURCE` 9、`DECLARED_AND_VENDORED` 1、`VENDORED_ONLY` 1、`NONE` 12。12 条无证据中 9 条 `REVIEW-BLOCK`、1 条 `EVALUATE`（自洽），另两条值得追问：`A012 Crawlee Python`（判定 `SIDECAR`）、`A022 Syft`（判定 `ADOPT`）。

更根本的问题：文档 `rule` 与 `verdict_definitions` 定义 `REFERENCE/ADAPTER/ABSORB/PROVIDER/SIDECAR/BENCHMARK/REJECT` 七个判定，但 47 行实际使用 `ADOPT/CURRENT/EVALUATE/REFERENCE/REJECT-CORE/REVIEW-BLOCK/SIDECAR`——其中 5 个判定词**文档从未定义**，仅 2 个重合。故该表当前不可逐条核对；本轮只提交事实，不改写该文档、不虚填 369 行、不安装任何捐赠项。

自查纠错两处：核对脚本首版按子串匹配，`vad` 命中无关包名，把无声明项误判为已落地；且只查依赖清单，把已在 `.github/workflows/ci.yml` 实际调用的 pip-audit 与 Gitleaks 误判为未吸收。现改为整词匹配并把**流水线调用**与**源码实现**各列为独立证据来源；`C008 sqlite-vec` 一行另记：它在 Python 侧确有声明，而 Rust Core 读不了遗留库的 `vec0` 表（见上文遗留库一节）——"已声明"不等于"需要它的组件可用"，两者不可互推。

## Q06 A 波次多格式读回 + 一次"存在≠已绑定"实测（2026-10-06）

`format_matrix` + `multiformat_extraction` + 9 个 per-format bulk 套件在**绑定外部根**时：296 passed / 0 skipped / 104 subtests / exit 0；不绑定时 287 / 9。差异的 9 项不是工具缺失：声明项 `10-toolchains/scoop/apps/ffmpeg/current/bin/ffmpeg.exe` 与 tesseract 在索引里 `exists: true`，只是本 shell 没有 `ARCHEAXIS_EXTERNAL_ROOT`（`TESSDATA_PREFIX` 同理）。这既纠正了"跳过=缺工具"的误读，也说明**同一套件在不同环境绑定下会给出不同的通过数**——引用通过数时必须连同环境条件一起引用。

格式矩阵同期按代码更正 **F10**（`media.transcribe` 路由存在、MP3/M4A/FLAC 可经 `attempts.rs:137-140` 到达）与 **F11**（`media.video` 接受 MKV/WebM、`subtitles.structure` 存在）；矩阵各组 `gap` 是"每种声明格式还缺什么"的权威清单，仍未收敛为 complete（16 组：0 complete、14 partial、2 custody-only）。

**权威 runner 的绑定条件（已追到代码，非猜测）**：`dev.py:97 external_toolchain()` 只在环境里**注册了根**时才生效（读 `OS_EXTERNAL_CONFIG` / `ARCHEAXIS_EXTERNAL_ROOT`，`dev.py:110-116`；无根即返回 `{}`）；发现到的 MSVC/Rust/TESSDATA_PREFIX/PATH 由 `environment()` 在 `:266` 合并，子进程以 `env = dict(os.environ)` 继承后覆盖（`:413` / `:467`），所以**操作者自己导出即可生效**。本机这两个变量实测均为 None ⇒ `run_tests.sh --full` 会静默跳过这些格式用例，`cargo_test.bat` 也必须手工传参——这不是工具缺失，也不是代码缺陷。仓库自己的索引 `config/environment/external-resources-index.json` 已记录根路径且 `root_present: true`，但 dev.py **有意**不信任它：两个测试把该契约钉住（`test_no_registered_root_discovers_nothing` 断言无根时返回 `{}`；`test_complete_root_discovers_all_four` 断言键集合恰为四项）。因此"让权威 runner 自动回退到索引"是一次**契约变更决定**，不是可顺手改的实现细节；在此之前，本地覆盖率取决于是否导出 `ARCHEAXIS_EXTERNAL_ROOT`。

## 追加清理：runs/ 下每轮临时目录（保留全部收据）（2026-10-06）

`runs/` 远超其 2 GB 预算（实测 16.3 GB），本轮按 §4 只清**可再生临时目录**，收据原地不动。只处理三种目录名且只作为 run 目录的直接子目录：`tmp`、`pytest-tmp`、`pytest-cache`；`artifacts/`、`logs/`、`runtime/`、`data/` 等一律不碰。

- 计划命中 **6,452 个目录 / 10.44 GB**；实际删除 **5,862 个 / 释放 1.59 GB**，**590 个被拒**（`WinError 5`，未强删未提权）。
- **仍被阻塞的临时目录 = 8.59 GB**（`tmp` 6.90 GB + `pytest-tmp` 1.69 GB）——这正是此前只笼统记为"23 个目录约 6.27 GB"的那一类，本轮把可从普通枚举得到的部分也列了出来，数字更可执行。
- 位置：`runs/` 16.3 → **13.45 GB**；审计清单 `.project-local/task-runtime/runs-scratch-prune-audit-20261006.json`。
- **度量口径更正**：本轮改用逐文件遍历求和（`os.walk` + 跳过不可读项）替代 `du -sh`，得到主仓开发根 **75.66 GB**（其中 worktrees 37.3 GB = 本工作树及其嵌套开发根）。此前 `du -sh` 曾读出 113/79/41 GB 三个互不相同的值，故**不采用 `du` 总量**；需要总量时报遍历值并注明跳过的不可读项。

## 追加清理：未被引用的 a&lt;编号&gt; 运行时副本（2026-10-06）

对开发根每个 `a<编号>`/`rt*` 目录做**精确路径**引用检查（`git grep -F .project-local/<名>`），只删除既无引用、又确为运行时副本的目录：

- 删除 8 个：`a6`(608.2MB)、`a7`(608.2MB)、`a11`(609.6MB)、`a16`(608.6MB)、`a12`(11.9MB)、`a13`(11.9MB)、`a14`(11.9MB)、`a15`(15.2MB)，共 **2.43 GB**。每个都先确认含 `backend-runtime-manifest.json` 与 `core`/`runtime`/`data`（即运行时副本而非源码），且无 `.git`；保留点由结构保证——现役 `rt` 与 `a1` 仍在。
- 保留（有引用即不动）：`rt`（`.github/workflows/ci.yml`、`release.yml` 引用）、`a1`、`a3`、`a3-python-input`、`a5`、`a8`、`a9`、`a10`（台账与清理/保留记录引用）。
- **一处冲突按"文档胜过本机检索"处理**：`a1-python-input` 在本轮 grep 中**无引用**，但 `REPOSITORY-LAYOUT-AND-RETENTION-20261006.md` 的勘误明确记载它是上一次 220 项批量移动**误删过的恢复目标**，故**不删**。这正是该文件记录的教训，不能因为检测器这次没命中就重犯。
- 审计清单 `.project-local/task-runtime/a-bundle-prune-audit-20261006.json`（先写清单再删）。工作树开发根 `du` 读数 39G → **37G**（口径见前节提示：`du` 总量不逐轮可比，按条目字节记账）。

## Green 工作树未提交工作的保留点（2026-10-06）

绿色仓库 `.ui-task-tree/ArcheAxis-Knowledge-OS`（HEAD `7282e5a947df`，detached）此前被记为"34 行 dirty，需先固化差异"；**本轮实测远不止于此**：13 个已修改文件（**+2308 / −649**）与 21 个未跟踪文件（品牌标记/图标/记忆图谱/复习图等 Avalonia 视图、`AAOS-UI-FIDELITY-STATUS-20260927.md`、8 个桌面契约测试）。原记录把 porcelain 的**条目数**当成了改动行数。

保留点已落仓，使该工作树进入"可删除待裁决"状态（约 2.0 GB）：

- `docs/history/worktree-preserved-diffs/green-ui-task-tree-7282e5a9-20261006-preserved.zip`（101,071 B）内含 `git diff` 全量补丁（336,622 B）与 21 个未跟踪文件的**原始字节**；
- 同目录 `...-inventory.json`（LF）记录：工作树 HEAD、13 个修改路径、21 个未跟踪路径各自的 `green_sha256`、补丁 SHA-256 与归档 SHA-256；
- **为什么是 zip**：统一 diff 必然引用原文含行尾空白，无法通过本仓"非 Windows 命令文件仅 LF 且不得有行尾空白"的文本约定；归一化会破坏补丁、按哈希豁免则是特例。归档是二进制，文本扫描器跳过它且字节完全保真。
- 读取绿色仓库全程只读（仅 `git diff` 与读文件），未改其索引或工作树；本批未删除绿色仓库任何内容，删除该工作树仍需 Owner 决定。

## 追加清理：未被引用的 rt-before-* 快照（2026-10-06）

按 `REPOSITORY-LAYOUT-AND-RETENTION-20261006.md` §4（逐项清单 + 可恢复保留点）删除三条**未被任何提交引用**的 before 快照，保留点由结构保证：每条都是 *before* 状态，其 *after* 状态是仍在的 `rt`。

- 守卫：对精确相对路径做 `git grep -F`（三条均 0 命中）、同目录的继任者 `rt` 必须存在、目录内不得有 `.git`；删除用 `\\?\` 扩展路径（这些树含深 site-packages，普通 rmtree 在 Windows 会上 MAX_PATH）。
- 删除：`rt-before-longpath-fix`(627.3 MB/20,585 文件)、`rt-before-expanded-720`(608.8 MB/19,559)、`rt-before-codex-20261005`(81.3 MB/2,769)，共 **1.29 GB**。审计清单 `.project-local/task-runtime/rt-before-prune-audit-20261006.json`。
- **保留（被引用即不动）**：`rt`(651M，继任者)、`legacy-scratch-20261006`（台账与清理交接文档引用）、`a1`/`a10`/`a1-python-input`（交接与探测记录引用）。
- **量测口径提示**：本批后 `du -sh` 读出工作树开发根 39G、主仓开发根 41G，而更早几轮同命令读出过 113G 与 79G。差额中一部分是真实删除，另一部分是 `du` 在**权限拒绝子目录**上的行为差异（本机 23 个 WinError 5 目录无法枚举）。故此处只登记**已删条目与其字节数**，不据此宣称开发根的精确总量；总量应以 `scripts/runtime/storage_report.py` 的分类结果为准。

## Q11 旧库迁移的验收与回滚口径（2026-10-06 草案，待 Owner 裁决）

把"仍需定义"的部分写成可裁决条目；依据是本轮实跑的迁移包断言（见 Q11 行）。**本轮未对 Owner 任何真实旧库执行迁移**，本节不冒认执行。

一次旧库迁移判为**完成**，建议同时满足：

1. **源库逐字节不变**：迁移前后对源 SQLite 主文件与 `-wal`/`-shm` 取 SHA-256 相等。机制已有断言（`legacy_db_never_modified`、`staging_never_modifies_the_legacy_database_bytes`），但对**真实库**需另出一份实测收据，不能以夹具代证。
2. **每张表都有归属**：要么迁移，要么在 manifest 中**具名**列为未读/未迁移并给出原因（`an_unreadable_table_is_named_beside_the_readable_ones`、`an_unreadable_table_is_named_in_the_manifest_and_the_rest_is_still_exported`）。不接受"静默少表"。
3. **笔记与学习历史进入暂存层**且不被跳过（`non_empty_legacy_library_stages_notes_and_learning_history_without_touching_the_source`）。
4. **写入前拒绝**四种情况：manifest 被改、JSONL 被篡改、出现未列文件、目标快照已存在（对应用例已具备）。
5. **phase4 research schema 由 `MigrationOperator` 应用**（不得直接调 `research.migrate`），且 operator 侧 `status` 可读回。
6. **回滚口径**：源库只读，故回滚 = 丢弃暂存层与新建库、源库保持原样；若已应用 phase4，则按 operator 的 rollback 事务回退并核验来源证明（`test_migration_runner` 的 rollback/漂移/fail-closed 用例已覆盖机制）。
7. **验收人**：由 Owner 确认，不接受"工程跑通即完成"；迁移收据须绑定源库 SHA、时间、operator 版本与 run 标识。

**待 Owner 定**：适用哪一份旧库；允许就地迁移还是仅旁路副本；未读表保留为 custody 还是要求补齐后再迁移。

## Q05 证据样板读回（2026-10-06）

本轮只做"仓库内可复核"的那一半：`evidence_anchors_api` 5/5、`source_transform_readback` 4/4、Python 证据套件 20/1 skipped。断言本身即结论——`time_anchor_binds_actual_receipt_and_preserves_old_attempt` 与 `epub_locator_requires_exact_receipt_identity_and_retains_old_anchor` 要求锚点绑定**真实回执**并保留旧锚点，`a_source_that_does_not_own_the_job_is_refused` 要求来源不拥有该任务即被拒。**安装态那一段（d91 21 步、四区导航、Ctrl+Alt+J）本轮未重做**：它的收据在 `.project-local/` 与交接记录里，不在仓库内，因此只保留为自行记录，不并入本轮实测结论——这正是此前 Q04 被撤销的那类错误边界。日志 `.project-local/task-runtime/q05-tests-20261006.log`。

## Q04 文档保存读回（2026-10-06）

历史状态撤销的**原因**是原证据只证明候选能力调用；本轮换用能证明该结论的证据类型并逐项读回：`document_draft_loop` 8 passed / 0 failed、`archeaxis-store-sqlite::staging` 1 passed，另有单一写者 3 项通过。要点在于有一条断言直接对应撤销的实质——`completed_real_recognition_is_not_a_fidelity_basis_or_human_approval_by_itself`：完成的机器识别**不等于**保真依据，也不等于真人认可，这正是当初被误当完成的边界。因此 Q04 可从"撤销"回到 `TESTED_LOCAL`，但**不含** installed UI 运行期读回（见 Q02/Q14），也不代替 Q11 备份演练与 Q08 真人闭环。完整日志：`.project-local/task-runtime/q04-cargo-tests-20261006.log`（忽略目录，不入库）。

## Q03 契约与权限读回 + 本轮权威套件（2026-10-06）

- **契约/权限（Q03）**：`scripts/ci/cargo_test.bat test -p archeaxis-api --tests --offline` → 48 个测试二进制、**232 passed / 0 failed**、exit 0；完整日志落忽略目录 `.project-local/task-runtime/q03-cargo-tests-20261006.log`（不入库）。
- **DTO 漂移检查**：`generate_vocabulary.py --check`（drift 为空）、`generate_core_document.py --check`、`generate_capability_catalog.py --check`、`check_media_window_policy.py --check`，四者 exit 0。
- **权威全量套件**（`scripts/ci/run_tests.sh --full`）在干净提交 `921bd8c7`（dirty=0）上：**4168 passed、70 skipped、144 subtests passed、0 failed**，485.06s。与更早一次同口径运行相比，收集总数相同（4238）但 **11 项由 passed 变为 skipped**；已核查这些测试的跳过条件**不**引用本轮删除的 `candidates/`、`build/green-candidates`，故不是清理所致，成因未定——如实记录，不当作已知。
- **本轮自身两次失误，均已发现并修正**：把 cargo 输出管道给 `tail`，只留下末 25 行、汇总丢失（已改为重定向到文件后重跑，取回 232/0）；守门脚本在一次编辑中丢失了引用检查（同回合内发现并恢复）。

## Q00 现场身份只读核验与门禁（2026-10-06）

Q00 的三项 `UNVERIFIED` 已按**只读**方式补核并落入 `docs/current/AAOS01-Q00-SCENE-RECEIPT.md` §6：声明位置（`config/defaults.yaml:11-13`，`data/archeaxis.sqlite` + `data/backups`）与实际磁盘内容（`data/cognitive_os.sqlite`，3,223,552 B，sha256 `b318c99e…`，`schema_version=121`，90 张表，旁带 `-shm`/`-wal`）**不一致**，该差异已登记为"必须登记的事实"而非当成已知；共享模型根只有环境变量声明（`capability-requirements.yaml:283`）且在本 shell **未绑定**——"存在≠已绑定"；CAS 根与备份 manifest 仍 `UNVERIFIED`（未声明、无 manifest、本轮未执行备份，属写操作需另行授权）。

复核方式为**副本**读取（`.project-local/task-runtime/q00-identity-20261006/`），原库与官方数据根未写、未启动任何进程。

新增门禁 `tests/workflow/test_q00_scene_receipt.py`：配置声明的每个存储位置、以及声明目录中实际存在的每个 `*.sqlite`，都必须在 Q00 回执里被点名；否则测试失败。**已依纪律先行证伪**——把声明路径临时改成未登记值后，测试如期失败并指出未登记项，随后恢复配置（`git diff config/defaults.yaml` 为空）。此项对应 Q00 完成条件"没有覆盖未知现场；现有可用项已标证据"；Q00 的其余未知项（CAS 根、备份恢复点、现役数据根是否即 `cognitive_os.sqlite`）仍需运行期读回，故 Q00 仍未整体完成。

## 绿色仓库已审计清理（2026-10-06）

先做只读清点（逐项 `du`、`git worktree list` 注册核对、`origin/main` 可达性、记录引用核查），再按**精确路径**移除两条干净且已交付的注册 worktree，每条先建保留点：

- `ArcheAxis.Knowledge.Green-x64/.ui-task-tree/aaos-ui-phase2-integrate`（分支 `codex/aaos-ui-phase2-20261001` @ `1a981a44`，dirty=0，为 `origin/main` 祖先）→ 保留点 `preserve/aaos-ui-phase2-integrate` = `1a981a4482b01f31989074e79c82a63400aa07a7`，随后 `git worktree remove` 该精确路径；
- `ArcheAxis.Knowledge.Green-x64/.ui-task-tree/AAOS-integration-verification-413ad3a0`（detached `62f23189`，dirty=0，为 `origin/main` 祖先）→ 保留点 `preserve/AAOS-integration-verification-413ad3a0` = `62f23189c3bd607967f3313d7809e4d636f58f1b`，随后移除。

结果：Green 根 15G → 13G。全程未按目录名批量删除、未用 glob、未 `rm -rf`（符合 Green `README.md` 第 9、25 行"不按目录名整删"的约束）；未推送任何 tag。

仍保留并记录原因：`ArcheAxis-Knowledge-OS` worktree（2.0G，34 行未提交改动，需先固化差异）、`ArcheAxis-Knowledge-OS-mainline`（4.4G，其文档禁止当作临时目录清理）、四个候选包 `AAOS-v18a00075`/`AAOS-v82e8d28c`/`AAOS-vd6bd374`/`AAOS-Tauri-578d06b78413`（约 3.4G，README 禁止按目录名删除，需逐项决定）、`minimax-aaos-cosmic-ui-20261001`（673M，Owner 已决定保留为供体）、以及 `data`/`backups`/`runtime`/`AAOS-Tauri-f151f4c7998a` 等被记录引用的目录。

## 本轮按授权范围的清理（2026-10-06，Owner 选定三类）

Owner 就"需所有者指定"的四类给出范围：绿色仓库四个旧代候选包、开发根 `candidates/` 与 `build/green-candidates`、`build/` 中非 cargo 的超预算产物；并选择"由 Owner 自己提权后提供 23 个权限拒绝 run 目录的枚举结果"。据此执行，全程逐项核对并以**精确路径**删除（无 glob、无递归模式）：

- **绿色仓库**：删除 `AAOS-v18a00075-20261001-x64`(0.80G)、`AAOS-v82e8d28c-20261002-x64`(0.88G)、`AAOS-vd6bd374-20261001-x64`(0.80G)、`AAOS-Tauri-578d06b78413`(0.71G)。删除前先把各自的 `candidate-manifest.json`/`backend-runtime-manifest.json`、`worker-profile.json` 等元数据文件复制到保留类 `.project-local/recovery/green-candidates-20261006/` 并记 SHA-256。绿色仓库 **15G → 9.1G**。
- **开发根**：删除 `build/2611ed9ca1`(15.36G)、`build/cargo-junction`(1.70G)、`build/gc-r20`(1.23G)、`build/aaos01-tauri`(1.25G)、`candidates/AAOS-b421ddee-audit` 残留(0.64G)。每项删除前用 `git grep -F` 对**精确相对路径**查引用，全部 0 命中；`be268a2d33`（本会话工具链所用的构建根）列入 KEEP 不动。开发根 **113G → 93G**。审计清单：`.project-local/task-runtime/build-root-prune-audit-20261006.json` 与 `candidate-prune-audit-20261006.json`。
- **被守卫拒绝、未动**：`build/green-candidates` —— `git grep -F` 命中 `.github/workflows/ci.yml:801/809/816`；核对该处是 CI 的**写入/产出**路径（`--out` 生成并上传 zip），且 `tests/test_green_candidate_assembly.py` 只用 `tmp_path` 构造同名路径、不读真实目录，故早期脚本的半删不影响测试；剩余 220 个文件保留待明确。`legacy-scratch-20261006` 被独立盘点的子代理列为 SAFE，但本仓自身证据相反（`realign_dev_layout.py`、`undo_layout_realign.py` 与台账都引用它，是该次布局归档的**恢复清单**），故按"有引用不得移动"保留，不采纳子代理建议。
- **受阻未完成**：`runs/2611ed9ca1`(6.27G) 删除时 `WinError 5`，与另外 23 个权限拒绝 run 目录同因；按约束不强制、不提权，等 Owner 提供枚举结果后再分类。

- **同轮追加（同日第二批）**：主盘点继续沿同一守卫清理工作树自己的开发根——`.project-local/worktrees/dsh-backend-loop-20261001/.project-local/build/2611ed9ca1`(11.82G)、`aaos01-core`(0.85G)、`cargo-gnu`(0.23G)，共 12.90G，三项均 0 引用；保留该工作树**在用**的 `build/cargo`(14G，热缓存)。随后处理两个 `build/green-candidates`（主 0.88G、工作树 1.18G，共 2.07G）：守卫按其 `ci.yml` 引用拒绝，改用新增的 `--allow-cited --reason=…` 显式覆盖，理由已记录在被引用的审计 JSON 里——`ci.yml:801/809/816` 用 `--out` **写入**该路径并上传产物 zip，属产出路径而非依赖；实测该删除后 `tests/test_green_candidate_assembly.py` **7 passed / 1 skipped**，证明不影响测试。
- **累计**：开发根 `.project-local` **113G → 79G**（-34G），绿色仓库 **15G → 9.1G**（-5.9G），合计约 **40G**。两次批次的审计 JSON 因脚本第二批复用了同名文件而只保留了后一批，两批清单以本节为准。

## 开源吸收核对脚本修订与来源更正（2026-10-06 复核）

核对脚本 `scripts/audit/oss_disposition_evidence.py` 已修订，分布随之更正（上文原文保留不改写）：`DECLARED` 24→25、`IMPLEMENTED_IN_SOURCE` 9→6、新增 `STUB_IN_SOURCE` 2、新增 `MENTIONED_IN_SOURCE` 2、`VENDORED_ONLY` 1→0、`DECLARED_AND_VENDORED` 1→0、`NONE` 12 不变。原因：原脚本把"整词命中任一来源"当实现、把"文件名含该项词"当实拷，并把 `__pycache__/*.pyc`、README 词与生成目录字样计为证据；又因整词匹配，`crossref` 匹配不到 `CrossrefClient`，四条真客户端（A018—A021）的判定实际由 `.pyc` 与文档字符串支撑。现改为按标识符判定、注释与文档字符串只算提及、编译产物与生成目录排除、桩按命中处附近的不可用标记判定、`shared/` 移出 vendor 根；`tests/workflow/test_oss_disposition_evidence.py` 已加断言固定命名/桩/提及/实现四态。详见 `docs/current/AAOS-OSS-DISPOSITION-EVIDENCE-20261006.md` 第五节，修订前后两份证据的 SHA-256 并列记录在该文档首部。

同轮更正两处输入来源判定：**A04**（`AAOS_完整历史规划蓝图吸收池与当前状态总报告_2026-09-29.md`）原记 SOURCE_MISSING，实为本仓 `docs/history/planning-blueprint-absorption/2026-09-29/package-unpacked/` 内文件、哈希与蓝图附录逐字节一致——上一轮按 maxdepth 5 检索而该路径深度为 6，故漏判；**A01/A02/A06** 经内容哈希检索（Record 121 个文件 + 该目录下 29,896 个 zip 成员 + 资料库）确认无字节相同副本，SOURCE_MISSING 由"按文件名未找到"升级为"按内容哈希未找到"。来源记录见 `docs/current/AAOS-INPUT-SOURCES-20261006.json`。

## 601–900 视口带补测并修正门禁边界（本轮）

A0 浏览器门禁 `scripts/a0_browser_smoke.py` 原视口矩阵为 1440/1280/390/360——从 1280 直接跳到 390，**601–1200 整段从未被任何门禁渲染**，而此前一处 CSS 修复正落在 601–900。本轮补入 900×800 与 840×800，并加用例 `test_the_viewport_matrix_covers_the_stylesheets_own_breakpoints` 把矩阵与样式表自身的断点绑在一起（须含 ≤600、601–900、>1200 三类，且窄屏判据必须等于样式表隐藏上下文条的那个断点）。

补测立即发现一处真实不一致：门禁用 `width <= 840` 判定"窄屏"，断言该宽度下应出现手机布局（轨道满宽、无上下文条）；而样式表的手机布局是 `max-width: 600px`，840 属 601–900 带——产品在此**有意保留上下文条**，因为"完全隐藏会去掉库空间唯一的区段切换器"。即门禁在 840 要求了产品故意不做的布局。按"门禁与样式表用同一个断点"修正为 `width <= 600`，并为 601–1200 带补上"正文列不小于样式表声明的最小值 280px"断言。

实测（真实 Chromium，六档）：1440/1280 桌面轨道 200px；900 轨道 148px、正文列 584px、上下文条可见；840 轨道 148px、正文列 524px、上下文条可见；390/360 手机布局（轨道满宽 56px、无上下文条）。六档 `scrollWidth == clientWidth`，无横向溢出，`errors` 为空，门禁 PASS。截图在 `.project-local/task-runtime/browser-smoke/canonical-shell-*.png`。

## 分段策略单一来源与漂移门禁（本轮）

分段转录的三个策略常量此前被手工镜像在三处：worker 的 `window_plan.py`（执行并强制）、界面的 `mediaEstimate.ts`（向用户展示预计）。两处数字一旦不同，用户看到的耗时就不再是 worker 实际切分的依据，且运行时不会有任何提示——这是本项目最不愿出现的一类缺陷。

现改为：`config/defaults.yaml` 新增 `media.window_policy`（`ceiling_ms` 300000、`overhead_ms` 20000、`realtime_factor` 2.0）作为**唯一声明来源**；新增 `scripts/contracts/check_media_window_policy.py` 把每一个镜像与声明逐字段比对，并额外比对 **Core 自身的截止上限**（`crates/archeaxis-api/src/runtime/mod.rs`、`crates/archeaxis-application/src/executor.rs` 的 `deadline_ms > 300_000`）——若声明上限与 Core 实际拒绝的上限不同，声明就是假的，故一并门禁。两处镜像与声明处均加注指针。门禁已接入 `ci.yml` 与 `vnext-ci.yml`（紧随既有 vocabulary 漂移检查），路径 `scripts/contracts/**` 与 `config/**` 均已由 `.worklab/project-validation.v1.yaml` 分类，`unknown_paths` 为空。

新门禁按本项目既有做法先**自我证伪**再采用：`tests/workflow/test_media_window_policy.py` 逐项注入漂移并断言报错指向确切文件与字段（界面常量、worker 常量、Core 上限，以及"声明了一个无人强制的上限"），另断言 Rust 的 `300_000` 下划线字面量被整体读取——门禁首版正是把它读成 300 并报出一次并不存在的漂移，该 bug 由这一断言固定。

验证：策略检查与 vocabulary 漂移检查均 pass；43 项 pytest 与 2 项跳过通过；`tsc --noEmit` 通过；相关前端 29 项通过。

## 外置引用索引的"假通过"与其修复（本轮）

本轮实测发现：`config/environment/external-resources-index.json` 为 `faster-whisper-large-v3-turbo` 记录
`"resolved": "D:\All projects\Model library\whisper\faster-whisper-large-v3-turbo", "exists": true`，
而运行期解析器 `tool_paths.tool_path("faster-whisper-large-v3-turbo")` 直接抛 `ToolNotFound`。同一份声明有两个读取方，
索引声称"能找到"、worker 实际找不到——**索引认证的正是它本该拦下的那类失败**，属假通过。

根因是三方读取规则不一致：`tool_paths.py` 与 `scripts/workflow/environment_registry.py` 都拒绝 `external_paths` 里的 `..`，
而索引生成器 `build_external_resources_index.py` 自己把 `..` 解析掉了。同时该声明形式本就被 schema 禁止
（`external_paths` pattern 含 `(?!.*\.\.)`），
`tests/workflow/test_capability_requirements_manifest.py` 记录的偏差清单里就有它，而该测试此前一直在失败——
是我上一轮新增该声明时引入的偏差、当时未跑这条门禁。

修复方式不是放开 `..`（那会为了索引好看而让外置根边界失效），而是给共享 Model library 一个**声明式的家**：

- schema 新增顶层 `sibling_roots`（名字 → 恰好 `../一个目录`）与条目级 `sibling_root`；`external_paths` 继续禁止 `..`。
- 清单新增 `sibling_roots: {model-library: "../Model library"}`；两个模型条目改为 `sibling_root: model-library` +
  相对路径（`whisper/faster-whisper-large-v3-turbo`、`sherpa-onnx`），`install_method` 改为枚举内的 `system`
  （host 从共享库提供，非本项目安装）。
- **三方读取方按同一规则解析**：worker 解析器、宿主清点 `environment_registry`、索引生成器；索引额外记录 `sibling_roots`
  与每个路径命中的 `sibling_root`，不再自己走 `..`。

实测（三处一致）：worker `tool_path` 解析出两个模型；`environment_registry` 报两模型 `available=True`；
索引 `with_external_paths=8 missing=0`，两个模型条目均带 `sibling_root: model-library`。schema 偏差清单由 3 条降为 1 条
（仅剩 `plugins minItems:1`——那是治理决策，未擅自修）；`worker_transcribe --probe` 仍报同一模型目录。

新增门禁（均先证伪再用）：`test_the_index_and_the_runtime_resolver_agree_about_every_declared_path` 逐条比对
"索引说存在"与"运行期是否真能解析"，无外置根时显式 skip 而非静默通过；
`test_a_traversing_declaration_is_refused_by_both_readers` 用真实存在的目标目录证伪两个读取方对 `..` 的拒绝。

回归：`tests/workflow`、`tests/workers`、`tests/maintenance` 共 523 项通过、2 项跳过、106 项子测试通过。

## 遗留库保真导出完成（带具名缺口）——取代上文"导出未完成"

上文记录"逐表 JSONL 保留导出未完成"。本轮改为：**单张表读不了不再中止整份导出**，而是把它记进清单并继续。

实现：`ExportManifest` 新增 `unqueried_tables`（表名 → 引擎原话）；`export_jsonl` 改用 `inventory_reporting_unreadable`，可读表照常导出、不可读表进入 `unqueried_tables`；
`manifest_digest` 把缺口一并计入摘要，否则"有缺口"的清单会与"无缺口"的清单摘要相同，后来者只比对摘要就分辨不出丢过表。
`legacy_dryrun` 退出码区分三态：0 完整保留、3 带具名缺口保留、1 失败——把部分保留报成"完成"或"失败"都会掩盖实际发生的是哪一种。

真实结果（对象为项目内 `data/cognitive_os.sqlite`，3,223,552 字节，SHA-256 `b318c99e5a58107f3fe57249b50e2560563b0dc6cca606505ef61ad19f64b411`，本轮前后同值、大小与 mtime 亦未变）：

- **88 张可读表全部导出**，合计 65 行；缺口具名一条：`vec_episodes: no such module: vec0`。
- 清单摘要 `manifest_sha256=5ed6c025aef744f6adcdac2b16f43674de4a9d2933b00be6809953167cb3cbc3`；导出目录 `.project-local/task-runtime/aaos01-legacy-migration-20261006/preserved-jsonl`（89 个文件 = 88 表 + 清单，3.9 MB）；日志 `preservation-log.txt` SHA-256 `2efe6b9e858ff68a9afc6f61c2d7c0baa182a1da6dd42af446607dbbeb58212f`。
- 实测顺带得到的事实：该库可读内容很小（13 行 schema_migrations、6 行 migration_operator_runs，其余多为空表）；`vec_episodes` 的影子表本身可读且已导出。

仍未做、也不应冒充的：**未做语义迁移**（把任何行并入 vNext 模式）。要真正并入 `vec_episodes`，需先决定是否引入 sqlite-vec 依赖；这是待定决策，不在本轮擅自动手。

## 更正：`vec0` 缺口属读取工具而非数据，且已有可用通路

上两节曾写"要真正并入 `vec_episodes` 的向量内容，需先决定是否引入 sqlite-vec 依赖"。**该结论有误，现更正。**

实测：`sqlite_vec` **已安装**（CI venv 内 0.1.9，可加载扩展 `sqlite_vec/vec0.dll`），且**产品自身已在使用**——`app/workspace/migrate.py::_load_available_extensions` 尽力加载该扩展、读取不了的表按名上报；`app/memory/vector_db.py` 同样在连接上加载它。`shared/migration_runner.py` 对 vec0 表专门跳过。

因此正确表述是：**缺口属于 `archeaxis-migration` 这个 Rust 审计读取器，不属于数据、也不属于产品。** 用产品既有通路重读同一份快照：

- `vec_episodes` 可读，**5 行**，列为 `(rowid, embedding)`，每行 embedding 为 **1536 字节 float32（1536 维）**；快照读后 SHA 不变（`b318c99e…`）。

即：无需引入新依赖、无需 schema 决策即可保留这最后一张表。已加用例 `tests/workflow/test_legacy_vec0_readability.py` 固定这一区分：
产品读取器对含 vec0 的库报"零张不可读"；而**不加载扩展**时同一张表抛 `no such module: vec0`——后者正是 Rust 清单里那条 `UNQUERIED` 的成因，说明它是关于读取器的陈述，若被读成"数据无法恢复"就错了。

## 遗留库保留补齐：89 张表全部落地（本轮）

补上最后一张表：新增 `scripts/maintenance/fill_unqueried_tables.py`，读取 Rust 导出清单里的 `unqueried_tables`，
用**产品自身已加载的 sqlite-vec 通路**把这些表补导出来，并回写清单（表项、缺口、摘要）。它是与 Rust 导出**组合**而非取代：
Rust 侧拥有逐表 sha256 与清单语义，本工具只补它读不了的，保证一份清单仍然描述整份导出。

实测（对象为项目内 `data/cognitive_os.sqlite` 的只读快照，原件 SHA 仍为 `b318c99e…` 且未变）：

- 补出 `vec_episodes`：**5 行**，`rowid` + 1536 字节 float32 embedding（hex 编码，与 Rust 导出对 BLOB 的写法一致）。
- 清单由 88 表/1 缺口 → **89 表/0 缺口**，`manifest_sha256 5ed6c025…` → `597027d419dd6ff5d77aaef5d911b181ffecdcc577ab3c2f076d85419575ee2a`。
- 完整性自检：清单 89 表 = 磁盘 89 个 `.jsonl`，无未登记文件、无缺失文件、逐表 SHA 全部相符。

**跨语言摘要等价已实测**：用 Python 按本工具口径重算 Rust 记录的 `5ed6c025aef744f6adcdac2b16f43674de4a9d2933b00be6809953167cb3cbc3`，结果逐字节相同——
即回写后的清单仍能通过 Rust 的 `verify_export`（该函数同时拒绝任何清单未登记的 `.jsonl`，故文件名规则也按 Rust 的 `export_filename` 镜像实现）。
用例 `tests/workflow/test_fill_unqueried_tables.py` 固定：摘要布局金值、补洞后清单自洽、已完整导出不动原文件、越界路径被拒。

回归：`tests/workflow` + `tests/maintenance` 共 250 项通过、4 项跳过。

仍未做、也不应冒充的：**未做语义迁移**——没有把任何行并入 vNext 模式。`stage_demo_semantic_import` 只暂存 `notes`，其余表按设计记为 leftover；本轮的成果是"整库保真保留完成"，不是"已迁移"。

## 布局归档的"恢复点"此前不可恢复（本轮自查修正）

`171981a44` 之后那批"清理 197 项未被引用条目"的破坏性动作之所以可接受，是因为留了可恢复归档。本轮实测发现**该归档用不了**：

- `scripts/runtime/undo_layout_realign.py` 的归档路径写的是 `.project-local/task-runtime/legacy-scratch-20261006`，而归档因超出 task-runtime 预算已迁到 `.project-local/legacy-scratch-20261006`；
- 更关键：清单里每条 `scratch_path` 记的是**迁移前的绝对路径**，恢复时按它查找必然不存在，于是 `continue` 跳过每一条、打印"restored 0 of 197"，**并返回 0**。

即"报告成功、实际什么都没恢复"——正是最不该出现的一类保留点。修正：

- 归档位置改为按候选列表定位并**要求确实存在**，找不到就具名失败（不再返回一个不存在的路径）；
- 每条的位置由**自身的 `source`** 相对归档布局推导（`.project-local/<x>` → `archive/project-local/<x>`，其余 → `archive/repo-root/<x>`），从而使归档可被搬动；记录的旧绝对路径仅作后备；
- 结果如实分列 restored / refused（已存在）/ MISSING；只要存在缺失或被拒，退出码为 1 而非 0，审计模式同样如此。

实测（真实归档）：`entries: 197`、`referenced (must stay): 0`、`archived copy missing: 0`，审计退出 0——即 197 项全部可恢复。

用例 `tests/workflow/test_layout_archive_restore.py`（5 项）固定：能定位迁移后的归档；记录的陈旧路径不掩盖真实副本；恢复真的把字节放回；**副本缺失时审计与恢复都返回 1**（回归的那一条）；归档不存在时具名失败而非返回假路径。

回归：`tests/workflow` + `tests/maintenance` + `tests/runtime-paths` 共 304 项通过、5 项跳过、11 项子测试通过。

## 自查：新门禁把 CI 弄红了（本轮已修）

本轮新增的 `Reject media window policy drift` 步骤在 CI 的 `cargo-test` job 直接失败：`ModuleNotFoundError: No module named 'yaml'`。
原因是该 job 只装隔离 worker 环境、不含 PyYAML（相邻的 vocabulary 漂移检查之所以一直通过，是因为它只用标准库）。
我在本地用带 yaml 的解释器验证，因此没发现——**本地通过不等于 CI 通过**，这次是 CI 先发现。

修法不是加依赖，而是让门禁**不依赖任何第三方包**：`read_policy()` 用受约束的窄解析读取 `media:` → `window_policy:` → 三个数值键，
认不出就具名失败；并用 `-S`（不加载 site-packages，等价于 CI 条件）实测通过。
同一处还暴露并修掉一个真 bug：`read_policy` 首版在离开 `media:` 段时清空了已收集结果，导致线上文件也读不到值——
现改为只停止收集、不清空，并加了"与 PyYAML 结果一致"的对照断言。

验证：`python -B check_media_window_policy.py --check` 通过；`python -S -B ...` 同样通过；新增门禁用例 21 项通过、2 项跳过。

## CI 抓到的两处自身缺陷（本轮已修）

上一批提交把 CI 弄红了两处，本地都没发现——**本地只跑了我以为相关的东西**：

1. `rust-vnext / cargo fmt --all -- --check` 失败：本轮改动与更早两轮的 Rust 编辑未过 rustfmt（长行换行）。我先前只跑了指定 crate 的 `cargo test`，从未跑 `fmt`。
   已 `cargo fmt --all` 重排 6 个文件（`archeaxis-api/tests/runtime_jobs.rs`、`archeaxis-application/tests/attempts.rs`、`archeaxis-migration/{src/lib.rs,examples/legacy_dryrun.rs,tests/migration_dry_run.rs}`、`archeaxis-sidecar-protocol/tests/worker_protocol.rs`），`--check` 现通过。
2. `lint / Validate architecture boundaries` 失败：`scripts/runtime/realign_dev_layout.py:21` 触发 `forbidden-sys-path-mutation`——那是本目标早前（`d31897f0`）我写的 `sys.path.insert(0, ...)`，用来 import 同目录的 `storage_report`。
   已改为按文件路径 `importlib.util` 加载（与 worker 侧加载同目录助手的既有做法一致），不再改动 `sys.path`；本地 `check_architecture.py` 现输出 `architecture guard passed`。

另按仓库声明的完整 ruff 配置（`pyproject.toml` 的 E/F/W/I/N/UP/B/SIM）清理了本轮新增代码的 7 处问题（未用 import、未绑定参数、lambda 赋值、raise 未带 from、zip 缺 strict）。CI 的 lint 只用窄集 `E9,F63,F7,F82`，这些本不会挂 CI，但声明配置就是标准；已同时确认 CI 的窄集命令在全仓范围通过。

教训（值得记住）：本轮三次"CI 抓到、本地没抓到"分别是 —— 门禁需要 PyYAML（CI 环境无）、Rust 未跑 fmt、架构守卫拦 `sys.path`。本地绿灯的边界只覆盖我实际跑过的命令。

## 跨栈 WAL 阻断已解除（本轮实测）

`docs/current/AAOS01-CROSS-STACK-WAL-BLOCKER.md` 记录的"Core 的 WAL 旁文件让 Python 只读直接拒绝 / 两栈在同一库上无法共存"，
本轮按其 §6 自己提出的下一步做完并得到相反结论。已在原文顶部加"已解除"状态说明（保留原测量文本不删改）。

实测（真实被杀死的写者，不是模拟；脚本走项目自身代码路径）：

- 子进程以 WAL 写入并 `os._exit(0)`（等价于被终止的 Core）后：`-wal` **12,392 B**、`-shm` **32,768 B**；
- 执行 `shared/backup.py::prepare_runtime_database()`（应用每次启动、取得唯一运行时租约后即执行）后：**两个旁文件全部消失**；
- 紧随其后的 `validate_schema()` 越过"不带旁文件"的检查，只因该玩具库没有真实 schema 而报出下一层错误（`phase4 research schema migration is pending`）——即启动路径已正常推进。

根因澄清：`_require_offline_database` 本就会**读写打开（自动恢复残留 WAL）→ `wal_checkpoint(TRUNCATE)` → `BEGIN EXCLUSIVE` 证明无他写者 → 删除旁文件**。
所以障碍是**活着的写者**（`BEGIN EXCLUSIVE` 正确拒绝，这是单写者纪律），而不是旁文件的存在。
本文档原来的表 3（"只读路径拒绝带旁文件的库"）为真，但由它推出的第 4 条（"两栈无法共存"）把"同时"与"任何时候"混为一谈。

用例 `tests/workflow/test_offline_database_recovery.py`（2 项）固定两半：被杀写者的旁文件在下次启动被恢复+清理+数据仍在；写者活着时 `prepare_runtime_database()` 抛 `requires the app to be offline`，写者一走同一调用即成功。

未做、也不应冒充的：未把 Python 侧改为经 Core HTTP 读取，也未让两栈同时写同一库——单写者纪律不变。

## 28 个待归属数据库：归属已解答（不自行删除）

清账项：`AAOS01-CLEANUP-EXECUTED-AND-PENDING-20261005.md` 第 22 行的 28 个数据库（157,745,152 字节），原判 `OWNERSHIP_PROOF_INSUFFICIENT`，理由是只能得到"家族相似"。
缺口在于那份审查只记了 `path/exists_now/bytes_now/historical_bytes`，**没看内容**。本轮读内容（经产品自身 sqlite-vec 通路，理由同前文 `vec0` 一节）。

结论（证据文档 `docs/current/AAOS01-PENDING-DB-OWNERSHIP-EVIDENCE-20261006.md`）：

- 28 条全形如 `.project-local\runs\be268a2d33\<run>\pytest-tmp\pytest-of-ALEX\pytest-0\<测试名>0\runtime.sqlite`，即 **pytest 自己的临时目录工厂**。
- 内容全是测试词汇：`doc-new / verified candidate content / test`、`doc-old / previous active content`、`foreign-active / foreign-candidate / foreign-backup`，`migration_operator_runs` 记 `owner=vector.documents`、`recorded_at=2026-09-15`。无一条像真实用户内容。
- 该词汇**在整个仓库只出现在 `tests/test_migration_runner.py`**，28 个库名与其中五个具名测试逐一对应。即：**产生者被指认 + 数据自证**，不是相似。

故归属问题已解答：类别 = pytest 临时 scratch，产生者 = 那五个具名测试，输入 = 合成夹具，按定义可再生。
**但本轮不删除**：上一轮对该批的明确动作是 `KEEP`，推翻一个明确的保留裁决需要业主背书。若业主同意，删除前取 28 条逐路径清单（含 bytes/sha256）存档作恢复引即可。
`tests/workflow/test_pending_db_ownership_evidence.py`（3 项）固定证据链的支点——合成词汇只由那一个文件携带、五个产生者测试仍存在、证据文档同时载明产生者与"删除仍待业主"——以免文档结论悄悄过期。

## 权威修复与双端描述同步（AAOS 专项，本轮）

按外部执行提示词与输入蓝图（字节 SHA-256 `2c99e7ae…1ed9`，与提示词要求一致）执行文档/治理修复。范围仅限文档与治理：不改产品架构、不装依赖、不发布。

**根入口**：新建 [`AUTHORITY.md`](../../AUTHORITY.md)，使两处记录的 `AUTHORITY_REFERENCE_MISSING` 可解析；它是导航入口而非新真值源，母定义直接引用蓝图 §2 原文。

**唯一 current**：修复三处指向冲突——`docs/truth/README.md` 原把 R6 写作"当前活动基础包"、`docs/taskpacks/README.md` 原自称"唯一当前推进任务包"、`docs/DOCUMENTATION_AUTHORITY_INDEX.md` 的 "Active forward work" 行同样指向 R6。
按现行 `AGENTS.md` §6 更正为：当前任务包 `taskpack-1004-aaos01`，R6 为**前一个**任务包（约束与回执继承），AAOS-01 唯一实时进度记录仍为本表。
**本执行者自身纠错**：我首版曾把 R6 当当前包（沿用了会话开始时那份较旧的 AGENTS 摘录），是新门禁比对现行 AGENTS 后指出并更正的——记录在此，不隐藏。

**描述真伪**：README 把 PDF.js(C001) 列在"已吸收"，而 `SUPPLY_CHAIN_LEDGER.json` 记 `REFERENCE`。实测以证据判定**账本是过期的一方**：`frontend/package.json` 声明 `pdfjs-dist 6.4.299`、`frontend/src/components/PdfReader.tsx` 正在导入、且有专门测试；账本行成于 2026-08-29，前提是"React/Tauri 界面已退役"，该前提被 SUP-022（正式宿主改为 Tauri+React）取代。
故新增 `DECISION_SUPERSESSION_LEDGER.yaml` **SUP-023** 取代 C001 的前提与判定，历史行原样保留；README 保留该条并加指向 SUP-023 的说明。

**可重复审计**：新增 `scripts/ci/check_document_authority.py`（已接入 `ci.yml` lint job），四项门禁——live 路由文档只能指向一个 progress 记录与一个任务包；根入口引用必须可解析；输入记录哈希须与主机一致；覆盖矩阵不得漏 ID。**先证伪再用**：`tests/workflow/test_document_authority_gate.py` 7 项注入各自命名，含"重新长回冲突指针"一项。
配套 `docs/current/AAOS-COVERAGE-MATRIX-20261006.md`（CAP 16 / Q 16 / F 15 / I 6 逐项）、`docs/current/AAOS-INPUT-SOURCES-20261006.json`（3 VERIFIED_MATCH、6 SOURCE_MISSING）、`docs/current/AAOS-AUDIT-SNAPSHOT-20261006.json`。
另记一个易错点：本仓 `R15-FORMAT-STATUS.json` 的 `F01—F16` 是格式覆盖切片，**不是**蓝图 §17.2 的 `F00—F14`，矩阵中已分别标注以防误配。

**来源可得性**：蓝图附录 9 条中 3 条本机取哈希逐字节相符（A03、A05、A07），6 条 `SOURCE_MISSING`（U01、U02、A01、A02、A04、A06）——**未声称已读**未找到者。
`scripts/maintenance/extract_docx_text.py` 为可复现的 .docx 文本提取命令（两次提取逐字节一致）。

验证：门禁 exit 0；文档/权威/维护与 workflow 套件 291 passed, 4 skipped（含 7 项门禁证伪）；`check_architecture.py` exit 0；ruff 通过。
