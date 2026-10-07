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
| Q02 Tauri 启动与只读桥接 | INSTALLED_RUNTIME_VERIFIED / PARTIAL（本轮已从 artifact 自身逐字段核对） | SHA `3dc286908783930f21a83663a822c5a8fdbdeedc` 的 `workflow_dispatch` run `37358948993` 结论 success；artifact `11366214081`（`installed-native-journey-3dc28690…-1`，176,213 B，未过期）内 `receipt.json`（sha256 `3367d910488aef6ddf496c21…`）**`ok=true`**、`evidence_level=REAL_TAURI_WEBDRIVER_CANDIDATE`、**13 步**、`owned_process_cleanup=true`、`owned_ports_released=true`，另有三张截图与 `driver.log`。**安装态由收据自身字段证明**：`host.path=C:\Users\runneradmin\AppData\Local\ArcheAxis Knowledge\ArcheAxis.exe`、`installation_context="Parent installer verifier supplies installed host; this probe hashes installer only"`、`install-preflight.json.installed_interpreter=…\ArcheAxis Knowledge\runtime\python.exe`——即 `verify_nsis_install.ps1` 装好后把**已安装宿主**交给探针；绑定 `installer_sha256=91064fea…`、`host_sha256=aaed6c36…`。**未证的是完整生命周期**：`install-preflight.json.complete_lifecycle_verified=false`（Q14 同为 false）——**该维度已于 run 37471031307 收口**：`lifecycle-receipt.json` `complete_lifecycle_verified=true`（见末节"Q02/Q14/Q15 的完整生命周期维度已收口"；阶段快照仍如实为 false）。**并记录一处收据缺陷**：其 `limitations[0]` 写 `Candidate executable, not NSIS installed journey`，与本收据自身的 `host.path`/`installation_context`/`installed_interpreter` 三处字段**自相矛盾**，属过时的固定文本——我先据该句把本行下调，读到内部字段后再纠正回来，故此处保留全部原始字段而非二选一。`src-tauri` fmt/test 的 CI 通过另行保留；物理 IME 与全部阅读器交互不能由此代验。下载件在 `.project-local/task-runtime/q02-artifact-20261006/`。 |
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
| Q14 Windows 安装态资格化 | INSTALLED_RUNTIME_VERIFIED / PARTIAL（本轮已从 artifact 自身逐字段核对；完整生命周期未验） | 引用的 run/artifact 读回核对：run `37399470467` 于 `578d06b784139e86c685191ecc7d0ccdd021fb27` 结论 success、**20/20 job 全部 success**；artifact `11385093136`（`installed-native-journey-578d06b7…-1`）未过期、551,082 B；`receipt.json`（sha256 `38ce8afd4f789e8fda52e751…`）**`ok=true`**、`evidence_level=REAL_TAURI_WEBDRIVER_CANDIDATE`、**21 条具名步骤**（含 `UI same-space … without creating objects`、`Native backup restore/retry and actual version rollback with original CAS readback`、`Trusted native Ctrl+Alt+J … without issuing API writes`、`Actual EPUB Reader chapter/paragraph … result-bound locator`、`Full host restart reads every host matrix source/output/quality/origin`）、`owned_process_cleanup=true`、`owned_ports_released=true`、`remaining_owned_port_listeners=[]`、`native_restore` 版本 3→2 且 `cas_equal=true`。**安装态由收据自身字段证明**：`host.path=C:\Users\runneradmin\AppData\Local\ArcheAxis Knowledge\ArcheAxis.exe`、`installation_context="Parent installer verifier supplies installed host; this probe hashes installer only"`、`install-preflight.json.installed_interpreter=…\ArcheAxis Knowledge\runtime\python.exe`；绑定 `installer_sha256=1f7b64878768ab564c9171cbb1f97b74…`、`host_sha256=00b7ba9b187b305d650458…`、`core_sha256=a648e4d28cc8f36596c05423f0f70faa…`。**未证**：完整生命周期（`install-preflight.json.complete_lifecycle_verified=false`）——**该维度已于 run 37471031307 收口**（`lifecycle-receipt.json` `complete_lifecycle_verified=true`，含就地升级/强杀清理/卸载保留数据/重装回读全 true、`pyc_growth=0`，见末节）、物理 IME、真人 Owner、新 Green 部署与新媒体 UI，故不登记资格、不发行。**收据缺陷一并记录**：其 `limitations[0]` 写 `Candidate executable, not NSIS installed journey`，与本收据自身的 `host.path`/`installation_context`/`installed_interpreter` 三处字段自相矛盾，属过时固定文本；我先据该句下调本行，读到内部字段后纠正回来，保留全部原始字段而非二选一。下载件在 `.project-local/task-runtime/q14-artifact-20261006/`。 |
| Q15 第一包收口与第二包交接 | PARTIAL | 唯一本表维护当前事实，47份Q02与既有历史归并完成；顶层保存原则与AAOS-01权威入口已同步。本run完整门禁与原生21步通过，尚不能登记第一包收口：新Green真实部署/媒体UI、同资料审核学习纠正旅程、真人Owner、真实云核验/专业依据、音视频原件fidelity、用户旧库完整语义迁移与旧入口冻结仍缺。已审计公开文件清理实际执行，稳定恢复和未知归属资产保留；不把高难缺口改名低难交接。**本轮实证把这一判断落到实处**：Q02 与 Q14 的 artifact 逐字段核对后，两条原生旅程都由 `verify_nsis_install.ps1` 装好后跑在**已安装宿主**上（`host.path` 在 `%LOCALAPPDATA%\ArcheAxis Knowledge\`、`installation_context` 写 `Parent installer verifier supplies installed host`、`installed_interpreter` 指向安装树内解释器），installer/host/CAS 三个 SHA 均有绑定；但两者的 `install-preflight.json` 都是 **`complete_lifecycle_verified=false`**，`checks/acceptance.json` 的 AQ26/AQ27 仍 `NOT_RUN`。故"第一包收口"缺的是**完整生命周期与真人/物理交互层面的资格**，而非安装是否发生；不把高难缺口改名低难交接。（收据的 `limitations[0]` 与自身字段矛盾一事见 Q02/Q14 两行。） |


## 2026-10-07 AAOS UI 增量（源码已提交；Windows 候选未构建）

- 对应 U00–U07 → Q00/Q01/F00、Q02/Q05/Q06/Q07/Q08/Q09/Q10/Q11/Q12/Q13/Q14/Q15；不建立新进度账本，不把任务包 111 个组件规格计为能力完成数。
- 源码增量：三主题 registry/冷色 semantic tokens、主题 picker（仅持久化 UI 偏好）、Radix Dialog/Tabs 与 AAOS Button/Field adapter、Galaxy loader 局部 CSS、动态 Atlas/实现地图入口投影、同源命令搜索/能力目录/详情、稳定能力 ID 与旧路由/需求别名深链解析、可折叠全能力菜单、能力目录/搜索 tab、聚焦正文时按需隐藏 Inspector。增加真实已保存文档 tab；当前仍是单一编辑器，脏草稿阻止切换并要求先保存，不宣称并行脏草稿或分屏双文档。无第二业务写者；未改 Core writer、worker 安全边界或业务状态存储。
- 资产增量：既有 `AaosIcon` 继续使用；三套冷色 AAOS 星环 SVG 实际用于 StatusBar，资产 SHA 和引用见 `docs/current/AAOS-UI-ASSET-MANIFEST-20261007.json` 与索引。旧 Avalonia 金色 SVG 被审计为不适配本轮冷色要求，未复制；Aurora/Home PNG 有首页/装饰语义，不当成通用配图。Galaxy 按来源文件 hash 和固定许可证用于局部等待视觉；构建包含全部资产，但真实窗口尚未目视验证。
- 单一入口投影：菜单和 Ctrl+K 使用 Atlas/implementation 同一只读 projection；可复现矩阵 `docs/current/AAOS-UI-CAPABILITY-ENTRY-MATRIX-20261007.json` 由 `scripts/ui/generate_navigation_matrix.py` 从当前源码生成，列出 16 CAP 与 9 spaces；这些是当前投影计数，不设总量上限。CAP ID、Atlas `origin_requirement_ids` 旧别名和 Space/hash alias 可解析；`#capability/<stable-id>` 与旧需求别名深链保留。菜单可折叠，命令搜索可达全部条目；未实现能力可查看前提/依赖/降级/下一步详情，但无执行入口。矩阵随仓库源码/权威变化需重新生成并复核。
- 三主题入口矩阵：`black`→黑色 Surface、`white`→珍珠白 Surface、`cosmic`→科技/深空/星环 Surface。每个主题有 tokens 与状态栏品牌 SVG；success/warning/danger 语义 token 分离，状态组件保留文字标签。测试验证主题颜色契约；三主题真实窗口对比、颜色对比度实测与视觉截图均 UNVERIFIED。
- 许可与依赖：仅添加 `@radix-ui/react-dialog@1.2.0`、`@radix-ui/react-tabs@1.1.22`，peer 与当前 React 18.3.1 相符；精确锁在 `frontend/package-lock.json`，来源提交/许可证在 `THIRD_PARTY_NOTICES.md`。npm 12 `ResolveOnly` 输出 JSON 形状与旧脚本不兼容，依赖版本经 npm registry 发布元数据单独核实后才调用原安装脚本安装；未 force/legacy-peer，React/Vite/Tauri 基线未变。
- 验证：TaskPack 源码锁/完整性检查 PASS（14 个固定源码文件、111 项组件身份/主题/任务映射、21 对比度候选）；导航矩阵和正式 capability catalog `--check` PASS；严格 TypeScript `tsc --noEmit`、Vite 生产构建、Vitest 全量 40 文件/271 tests、资料库定向 28 tests、`git diff --check` 均 PASS，由项目 `scripts/runtime/dev.py` 在精确 worktree 执行。新增 dirty 窗口关闭保护测试，分组能力目录方向键/全量可达测试通过。构建初次发现主 chunk 约 1.30 MB 后，PDF.js 阅读器和 Tiptap 编辑器改为按需加载；最新生产构建主业务 chunk 413.76 KB、PDF reader 484.33 KB、DocumentEditor 404.60 KB，无 Vite >500 KB 单 chunk 告警。这里只证明打包拆分，不是运行态性能预算通过。`tests/contract/test_bulk_schema_matrix.py` 定向 pytest 未运行：项目选定 Python runtime 缺少 pytest；未安装额外测试依赖。Tauri 安装态、三主题逐屏实渲染与截图、实际键盘/焦点、减少运动、离线/失败/冲突/重启/恢复 UI 行程、2560×1440/1920×1080 与 100/125/150/200% DPI、窄窗、中文物理 IME 均 NOT_EXECUTED。此前校验时未在shell PATH发现 Rust；2026-10-07续验通过任务进程 `OS_EXTERNAL_CONFIG` 发现登记 Rust/MSVC 后，实际运行/编译仍受 Windows Access Denied 阻断，详见本节续验记录；无同 SHA Tauri/Windows候选，未借用 Green 资格。
- 阅读与资产绑定增量：`OriginalDerivedSplit` 以活动文档自身 source_id/source_revision 读取同版 CAS 原件，仅当 source identity/revision/hash 与返回原件身份一致才并排显示原件 Reader 和派生文档编辑器；展示来源 revision、原件 SHA、文档 version 与正文 SHA，彼此分离。文档 revision/hash 不匹配会拒绝原件配对但保留可编辑文档。图像/TXT/PDF/音视频走各自类型查看器，未支持格式仍保留到 CAS 并说明需从原件列表阅读。`CanonicalLibrarySpace.test.tsx` 两项 SIMULATED 回归覆盖正确配对/独立指纹与不匹配拒绝；当前没有 REAL 安装态旅程或截图回执。
- 能力边界：机器回答更正通过已有 knowledge get/review 入口形成待真人审阅候选，并验证正文/版本身份。有限 Tauri Core bridge 与生成命令 schema 已增补固定 `machine_retest` 路由；UI 仅在候选已接受后按原失败任务/原题/纠正 Knowledge ID 触发，并要求 Core 回执与任务读回一致，展示原答和复测答。相关 Vitest 使用 SIMULATED Core bridge fixture；Core/界面均不自动判定改进，实际模型复测和真人比较尚无 REAL 证据；新增 Rust bridge 路由回归已写，当前外置工具链调用在 Cargo/Tauri build 阶段受 access denied 阻断，未编译或执行该回归。学习题目前显题、显式揭晓答案后再提交，客观对错与自评分开；真实真人认可、安装态恢复及物理 IME/UIA 验收仍缺。
- 2026-10-07 续作：`CanonicalLearningSpace` 现在读取 Core assessment 的实际 question/content 快照，先答后显答案，分开输入对错反馈与 FSRS 1–4 难度自评，遵循现行 Core 一致性约束；幂等 event ID、assessment/knowledge version 绑定、Core 拒绝与未确认区分、无排期回执明示保留。学习可进入聚焦布局（收起导航、Inspector、ActivityDock），退出/离开自动复原。静态类型检查 PASS。
- 明确未闭环：AI 纠错候选经既有有限 `knowledge_get`/版本化 `knowledge_review` 提供真人接受、拒绝、接受后弃用标记；独立复测已增加单一路由到已有 Core `/api/v1/machine/retests`，不经前端 HTTP 直连、不改 Core handler/worker。UI 保留 Core 的失败任务、问题与 Knowledge ID 绑定，逐项校验复测回执及持久化读回；结果以未测评候选展示，等待真人比较，不自动生成改善结论。真实模型执行、版本/hash层面的真人比较以及 Rust bridge 编译/测试尚未验证。文档标签现可同时切换多份已保存文档，每份 Editor 维护独立内存草稿、基础版本和dirty标签；切换不会丢未保存文本，关闭未保存标签需确认，关闭主窗口仍有dirty提示。草稿仅内存且未写localStorage，强制终止/崩溃仍可能丢失；持久保存与冲突仍由现有Core CAS版本命令负责。Reader、Editor、CheckPanel、历史/恢复/ActivityDock仍复用已有接线。
- 当前验证仍 PARTIAL：未执行三主题真实窗口截图、Tauri Windows 候选、键盘/焦点/reduced-motion 实机、离线/错误/冲突/重启/恢复 UI 行程、2560×1440/1920×1080 与 100/125/150/200% DPI/窄窗/中文物理 IME；无该 dirty source 同 SHA 安装回执。源码构建级懒加载已实现并拆分大型 PDF/编辑器 chunk，尚无 Tauri/WebView2 安装态启动延迟、交互耗时和内存进程树预算结果。原始 ZIP `D:\All projects\UI套件\AAOS_UI_Taskpack_20261007.zip` 未修改，解包与开发输出在项目 ignored `.project-local` 中。
- 2026-10-07 状态语义精修（当前工作树 `codex/aaos-ui-newui-20261007`，基线 HEAD `25213bddd9885289a59b7e1cf774ef3fd62a1c9a`，含未提交增量）：三主题/default warning tokens 改为冷冰蓝/深冷蓝，与 success/danger 保持独立；新增 `AaosStatusBadge`，以内联SVG提供 warning三角、success勾、danger叉及可读文字，用于恢复、只读/可写和设置就绪状态。检查并移除珍珠白 `.badge-warning` 覆盖中的旧硬编码灰底，使其沿用主题 warning soft token。工作台“不可用/失败”状态改用 danger；“未连接/已弃用”保留 warning，并由回归用例锁定。最终源码严格 TypeScript 检查 PASS；Vitest全量42文件/281 tests PASS（含SIMULATED Core fixtures，不是REAL产品旅程）；生产Vite构建PASS（214 modules；主业务414.65KB、PDF Reader 484.33KB、DocumentEditor 404.60KB）；任务包校验、导航矩阵 `--check`、三主题品牌资产4项SHA/bytes复核及 `git diff --check` PASS。依赖先因offline cache缺 `yallist@3.1.1` 未装齐，后按现有lockfile标准 `npm ci` 恢复（267 packages，package/lock未改）；npm Windows shim转发失败，通过 `dev.py` 直接调用锁定TypeScript/Vitest/Vite JS入口完成验证。运行资格仍 PARTIAL：Playwright Chromium解包遇Windows `EPERM realpath`；Codex IAB拒绝本地 `file://` 页面并禁止绕行，所以没有实际截图、WebView/Tauri运行或Windows候选回执；物理IME、DPI、离线/冲突/重启/恢复UI旅程仍 NOT_EXECUTED。Git无法创建worktree index.lock（Permission denied），增量保持未暂存/未提交；未改ACL、未推送/合并。
- 状态：Q02/Q09 局部 TESTED_LOCAL / PARTIAL；Q05/Q06/Q07/Q08/Q10/Q11/Q12 行为实现未闭环，保持原 PARTIAL；Q13/Q14 UI 增量候选未安装验证，保持原 PARTIAL；Q15 未收口。详情、资产哈希、禁暖色合同和入口矩阵需随候选进一步验证，勿据此宣称完整 UI 或安装资格。
- 本轮独立候选工作树：`codex/aaos-ui-newui-20261007`，基于 `8519ba4e5d22bb911068b2f0bbe0d94934123f94`；UI 增量已在该分支形成可审阅本地提交，未 push/merge。构建/类型/单测/任务包校验均是本地 source 证据，不能提升为运行期资格；需对最终同 SHA Windows/Tauri 候选补跑三主题和交互恢复旅程再提升状态。
- 2026-10-07 续验（当前 worktree 在提交 `15555910` 后另含 `frontend/vite.config.ts` 缓存路径改动及本条台账增量）：按现行 `scripts/runtime/dev.py` 设置 `OS_EXTERNAL_CONFIG` 后，正式 Cargo/MSVC 工具链可发现；Windows SDK `LIB`/`CL` 仅注入单次 PowerShell 子进程。根工作区 `cargo test --workspace --offline --no-fail-fast` 完成编译、API 纯内存单测 17 项通过，但整体 exit 1、78 个 test targets 失败于 SQLite/工作区临时文件 `os error 5 PermissionDenied`；不将其写成 PASS，也不推断为代码缺陷。`src-tauri` 新增复测回归经官方 Cargo 入口尝试编译，止于外置 Cargo registry 的 `tauri` build.rs 对 global API script `canonicalize` 返回同一 Windows access denied；官方 `cargo fmt` 与直接 `rustfmt --check` 也返回 access denied。具体访问边界根因 UNKNOWN；未提权、未改 ACL。严格 TypeScript 检查 PASS；指定 `frontend/vite.config.ts` 后 Vitest 40 文件/271 tests PASS；生产 Vite 构建 PASS，chunk 为主业务 413.76 KB、PDF 484.33 KB、Editor 404.60 KB。为符合开发输出约定，Vite cache 已路由到每次 `dev.py` run 的 `.project-local/runs/<worktree>/<run>/cache/vite`，无 cache 应留在源码根目录。单独从根启动且漏传 config 的一次 Vitest 运行因未载入 jsdom/setupFiles 而失败，已纠正调用后复跑通过，不计为产品回归。真实预览仅绑定 `127.0.0.1:4179`；Codex IAB 对该地址返回 `net::ERR_CONNECTION_TIMED_OUT`，未扩大监听范围，无真实窗口截图/旅程回执。故 Q02–Q14 的旧资格不因本次 source/build 测试升级；同 SHA Windows/Tauri 候选、主题实渲染、截图、键盘/焦点/reduced-motion、离线/错误/冲突/重启/恢复旅程、规定分辨率与 DPI/窄窗/中文物理 IME 均仍 NOT_EXECUTED。
- 2026-10-07 主题资源注册表续验（源码身份 `HEAD=25213bddd9885289a59b7e1cf774ef3fd62a1c9a` + `source_patch_sha256=7afcea58fae7e85aaeeb0ac8f4558f5967389a0fb09778fc718f2638fe785c6c`）：三套主题的 AAOS 冷色品牌 SVG 映射收进 `frontend/src/design-system/theme.ts`，`StatusBar` 改消费同一 registry；主题回归锁定三个主题各自映射独立 SVG，现有资产清单同步引用路径。定向主题/导航/状态回归 4 文件/18 项 PASS；单 worker 完整 Vitest 42 文件/282 项 PASS（run `c4918fb1ef6d`；此前并行 run 的额外 worker mkdir EPERM 不复现）；严格 TypeScript PASS（`08de0300ba6a`）；生产构建 PASS（`d12b1ba7b6cc`，214 modules，主业务 414.56 KB、PDF 484.31 KB、Editor 404.60 KB）；任务包锁校验 14 源码文件、111 组件映射、21 对比度候选 PASS（`c3e2a59922de`），现行入口矩阵 `--check` PASS（`a9243ddefd22`）。Codex IAB 与 PowerShell 均无法连接本地 Vite 回环预览（超时）；服务已停止，无浏览器截图/实际渲染证据。Origin SSH 与直接 HTTPS `ls-remote` 均返回访问拒绝，本轮远端最新 HEAD 未核实；未改 remote/ref。Cargo/Tauri canonicalize 权限阻塞、Windows候选、实际三主题/DPI/IME/键盘/焦点/减少运动及离线/失败/冲突/重启/恢复旅程继续 NOT_EXECUTED；未 push/merge/release。
- 2026-10-07 Tauri Windows 构建再验证（`HEAD=25213bddd9885289a59b7e1cf774ef3fd62a1c9a` + `source_patch_sha256=2ffc5287fa2abcce3111a8164cf328cf6f02338eb50b53d6717ecdddf62bec66`，run `c2ce095e46c2`）：确认 C: 上 Windows SDK `10.0.28000.0` 的 `kernel32.lib`、UCRT lib/header 存在；一次性进程环境补入 SDK LIB/INCLUDE，并对 Rust target 显式绑定登记 MSVC `link.exe`，Cargo 已用项目 canonical `.project-local/cache/cargo` 编译依赖直至 `tauri v2.11.5` 与 `archeaxis-desktop`。仍在 `tauri/build.rs:353` 对 canonical cache 的 `tauri-2.11.5/scripts/bundle.global.js` 调 `canonicalize()` 时 WinError 5 PermissionDenied，exit 101；文件在该路径存在且 PowerShell 可读。此证据排除了此前外部 Cargo Home、缺 linker、缺 SDK LIB 三个调用问题，但不能确定 Rust 子进程 canonicalize 被拒的系统根因。未改 ACL、未复制/修改 Cargo registry 源；Tauri host 编译和测试仍 FAIL/UNVERIFIED。

- 2026-10-07 UI 分支并入、桌面端收口与手机端下线（当前 worktree `codex/aaos-ui-newui-20261007`，`HEAD=25213bdd`，含未提交增量）：所有者明示「UI分支可以并入到你的UI分支，UI任务按照提示词任务包进行」与「优先跑通全量执行桌面端电脑端UI，先删除手机端其他端等」，据此执行。
- 并入关系核实：`codex/aaos-ui-phase2-20261001` 与 `codex/aaos-p3-ui-convergence-20260922` 相对 `codex/aaos-ui-newui-20261007` 分别为 0/478 与 0/541（`rev-list --left-right --count`），即二者都是该分支的严格祖先，提交层面的「并入」无新增内容可并；UI 分支独有 9 个提交，与格式分支 `codex/dsh-aaos-real-multiformat-loop-20261001` 在 `9692aec9` 分叉（152/9），本轮未做跨线合并、未改任何 ref。
- 手机端删除清单（可单提交回退）：`frontend/src/design-system/tokens.css` 的 `@media (max-width: 600px)` 块 82 行（状态栏压缩、单列 `.app-body`、横向 56px 轨道条、隐藏上下文子导航、`.space-rail-item` 图标化）与 `themes.css` 同名块 11 行（侧栏 `flex-basis:190px`、`.capability-rail[open]` 固定浮层）。删除由 `.project-local/task-runtime/aaos-ui/remove_phone_end.py` 执行：花括号配平定位、要求每文件恰有一块、要求块内确含 `.space-rail`、删后复读校验无残留。601–900px 与 ≤1080/≤1200 的桌面窄窗分级保留，因为 Windows 半屏与系统缩放窗口会落进该带，它们不是「手机端」。
- 删除过程中先实测后改：交接遗留的 390px 渲染里轨道条实测高 190px 而非声明的 56px，根因是 `.navigation-sidebar .space-rail{flex:1 1 auto}`（特异度 0,2,0）压过手机块的 `.space-rail{height:56px}`（0,1,0），加上侧栏 `flex-basis:190px` 在列方向变成高度；我先按此修好（两块 `flex:0 0 auto` + 条内改行向布局），A0 合同在 390/360 得 `height=56`、`scrollWidth==clientWidth` 并通过，随后按所有者决定整块下线手机端，未把这条修复留成死 CSS。
- A0 浏览器合同变更（`scripts/a0_browser_smoke.py`，report schema v2→v3）：视口矩阵由 1440/1280/390/360 改为 8 个桌面项——1920×1080、2560×1440、1440×1000、1280×800、1024×768，以及 1920 物理屏在 125%/150%/200% 缩放后的 CSS 视口 1536×864、1280×720、960×540（`device_scale_factor` 同步断言实测 DPR）；新增断言：状态栏子元素两两零重叠、`--ax-motion-fast` 在 reduced-motion 下为 `0ms`、Escape 关闭后焦点归还 `.command-trigger`、Ctrl+K 打开后光标落在搜索框、三主题经真实 `界面主题` 选择器切换并各出一张截图（记录 `data-aaos-theme`、品牌 SVG、body 实际底色）；删除原 `width<=840` 手机分支（含「context 必须不存在」）。注：2026-10-06 该分支曾把我的改动挡回（见本节上方既有记录），本次放宽是所有者明示的范围变更，不是我为让改动通过而改合同。
- 交接现场三处纠正（均为我实测得出，非推测）：(1) `navigation-projection.test.ts` 与 `theme-preference.test.ts` 用 `process.cwd()` 拼仓库路径，而 CI 是 `working-directory: frontend` + `npm test -- --run`，会解析成 `frontend/docs/...` 与 `frontend/frontend/src/...`，即交接回执「284 全绿」来自根目录调用而非 CI 命令；改用仓库内既有的双 cwd 解析（同 `CanonicalCapabilitiesSpace.test.tsx:10`）。(2) `OsuiProductionContract.test.tsx` 的落地空间断言被改为「资料库」，那是宿主态（`App.tsx:35 desktop = window.__TAURI__` 时落地 library），无宿主桩时落地是工作台，且与同文件其余用例及既有 `App.test.tsx:97`「starts on the workspace space」冲突；恢复为工作台断言。(3) 交接 5 份回执中 `ui-final-build` 的 `source_patch_sha256=69d20e7d…` 与其余四份 `432bb2fc…` 不同，「同一棵树」的说法不成立。
- 终树回执（`HEAD=25213bdd`，dirty）：Vitest `ui-final-vitest-20261007-d` 42 文件/284 项 PASS；生产构建 `ui-final-build-20261007-d`（`tsc --noEmit` + `vite build --base ./`）PASS；两者 `source_patch_sha256` 同为 `cee812f5c41dc82a…`；A0 浏览器门禁 run `ui-browser-smoke-20261007-06` status=PASS，8 视口 + 三主题截图各一张（black `rgb(5,5,5)`、white `rgb(244,246,250)`、cosmic `rgb(8,16,32)`，珍珠白实测为冷白，无奶油/米色）。口径说明：脚本自带的 `worktree_diff_sha256=a0c0f73809be3769…` 只覆盖已跟踪 diff，dev.py 身份另含未跟踪文件内容，故两值不同属仪器口径差异而非两棵树（同一棵树两次运行该 diff 值稳定复现）。一次在源码根误跑 Vitest 留下 `.vite/` 缓存，它进入 dev.py 运行身份曾使早先一对回执 patch 值不同；该残留属本次派生物，已删除并在同一棵树重跑三项。
- 撤回我上一条的对比度结论（仪器错，不是产品缺陷）：那次矩阵探针在切换主题后 200ms 就读首个屏幕的计算样式，读到的仍是**上一个主题**的颜色（珍珠白报出黑主题的 `#a5adb3`/`#d4d4d4`，深空报出白主题的 `#28364b`），因此「珍珠白 3 个元素 2.24:1」不成立。改用逐祖先读数（`.project-local/task-runtime/aaos-ui/probe_theme_chain.py`，`.project-local/runs/theme-chain-20261007.json`）后三主题均正确：分组标题黑 `#d4d4d4`、珍珠白 `#28364b`、深空 `#d4e0f5`，各自对当前表面均为高对比。教训按「先怀疑仪器」处理并记入记忆：主题切换后的第一次计算样式读数必须作废重读。
- 矩阵探针确实查出一个真缺陷并已修：能力导航分组标题直接渲染 Core 的英文 `product_layer` 枚举（界面上出现 “Workspace”），违反任务的中文优先合同。`frontend/src/presentation/labels.ts` 新增 `PRODUCT_LAYER_LABELS`/`productLayerLabel`，`SpaceRail.tsx` 的分组 `<summary>` 改走该映射；实测渲染为「工作台」（chain 收据 `summaryText`）。
- 桌面屏矩阵（9 空间 × 3 主题 @1440×1000，真实 Chromium 渲染 + 门禁自带的 API 替身）：**27 屏零横向溢出、零元素越界**，截图 `.project-local/runs/ui-screen-matrix-20261007/screenshots/`，逐屏数据 `matrix.json`。这是浏览器渲染层证据，不是 Tauri/WebView2 安装态。
- 本批收口提交链：`db7874cd`（吸收 UI 增量 + 手机端下线 + A0 桌面合同）、`5ba42455`（上游 pin 移出当前面，修红门禁）、`9ded175d`（分组标题中文化 + 撤回对比度误判）。终态证据全部绑定在 **clean tree 的 `9ded175d`**：Vitest 42 文件/285 项 PASS（run `ui-clean-vitest-9ded175d`）、`tsc --noEmit` + 生产构建 PASS（run `ui-clean-build-9ded175d`）、A0 真实浏览器门禁 PASS（8 桌面视口 × 三主题，`worktree_dirty=false`、无 diff 即无 dirty 窗口）、目标 Python 门禁 40 项 PASS。本条为纯文档提交，不改代码，故上述代码证据继续有效。
- 2026-10-07 宿主层改判与两线合并（集成分支 `codex/aaos-ui-core-integration-20261007`，合并提交 `4da25bed`，领先 origin/main 162 个提交）：**推翻上面「本机 Rust/Tauri 编译被 canonicalize Access Denied 阻断」的判定**。以所有者交互账户 `ALEX` 实测：`cargo build --release` 产出 `ArcheAxis.exe`（11,328,512B，`Finished release profile in 44.99s`），`desktop.scripts.prepare_bundle --backend-candidate` 产出 19,505 文件、manifest SHA `b941ce8678b654f3a01dbcf015262eb2a494ba3aaf620f135c8bbf37aff115f3`，`tauri-build` 资源校验通过。先前真正的失败信息是 `resource path '..\.project-local\rt\runtime' doesn't exist`——该 worktree 从未做过 rt 暂存，与 ACL 无关；`.project-local/cache/cargo` 的 DACL 只含历次沙箱会话 SID，这解释沙箱令牌下的拒绝，但不约束本令牌。NSIS 打包另测得一处长路径问题：makensis 收到**未规范化**的资源路径，在本 worktree 下字面长 265 > MAX_PATH 260，报错文件为 litellm `guardrail_benchmarks/evals/*.jsonl`（规范化 252、可读 2,324B）；`subst W:` 反而使 tauri 把资源 canonicalize 回真实长路径并报 `doesn't exist`，故弃用。可行解是在同一 `.project-local` 根下使用短名工作树 `.project-local/wi`（根 56 字符、最坏字面 235 < 260），不改任何产品配置。合并冲突两处处理：浏览器门禁保留桌面矩阵并补回 core 线的 900/840 带守卫；台账两侧日期条目全保留。命令面板两条旧断言改为现行投影合同（Escape 走 dialog 自身键路径；空查询等于 `EFFECTIVE_NAVIGATION_ENTRIES` 全集且包含每个空间），改后合并树 48 文件/326 项 Vitest PASS、`tsc --noEmit` PASS。仍未做：`wi` 的 NSIS 结果、同 SHA 安装态旅程、物理 IME、真实系统 DPI、真人验收。
- 2026-10-07 合并候选的宿主层实测（候选 = `4da25bed` 本机新编，`ArcheAxis.exe` 11,330,048B SHA `a6efcbd56f178cee…`、NSIS 150,783,078B SHA `be6ed3522fbf6fdf…`，收据 `.project-local/task-runtime/wi-candidate/candidate-identity.json`）：`scripts/probes/aaos01_tauri_webdriver_loop.py` 在该候选上跑到 **15 步全 PASS** 后停在第 16 步——真 Tauri WebDriver 会话与窗口、UI 四区同源导航不建对象、有限 system_version bridge、导入原件字节与中文渲染阅读、文档保存、会话关闭重开持久读回、产品一致备份与列表读回、原生恢复/重试与实际版本回滚加原 CAS 回读、无来源/审阅/模型前置条件下原始笔记由 canonical writer 保存、真实 Ctrl+Alt+J 展开折叠活动坞不丢编辑器焦点且零 API 写入、关闭重开读回与持久版本相等、搜索命中未核验普通文档并打开既有编辑器而不产生知识认可、人工不确定核验与云端待请求分别记录。
- 第 16 步失败已定位到可复现边界而非猜测：断言 `structure.extractable_members` 恰为一条 `notes/known.csv` 失败，且原断言**无消息**故取证为空。无头复现（`wi/.project-local/task-runtime/wi-candidate/repro_tar_members.py`）证明 worker 只在被要求解压目录时声明成员（无 member_dir → 0 条；有 → 1 条且名称与 SHA 正确），`archive.inventory` 确在 `attempts.rs:198 ARTIFACT_ROOT_CAPABILITIES`，archive 路由用 `artifact_dir/artifact_kwarg`，候选内 staged transport 与源码逐字节相同（`666e80dea604885a`）。断言已补记录路由媒体类型/成员/是否请求解压（提交 `978395a5`），下一步以带值收据判定是 Core 未请求解压还是探针前置错误。
- 视口覆盖门禁改判（提交 `978395a5`）：原门禁要求矩阵含 ≤600 视口并与样式表手机块边界对齐，手机端下线后前提失效；改为要求样式表每个 `@media` 断点两侧都有矩阵项、不得存在隐藏 context 条的手机块、不得有 ≤600 的分支。三个破坏用例（手机分支、去掉 900 带覆盖、加回手机块）全部使门禁失败，还原后 exit 0，逐文件字节校验一致。
- 我自己造成的污染已按"归档不删除"隔离并复验：`wi/build/`（setuptools 产物 3,027 KB）、`wi/archeaxis_workspace.egg-info/`（64 KB）、两个写错位置的日志 → `wi/.project-local/task-runtime/wi-layout-quarantine-20261007/`；`tests/workflow/test_workspace_layout_contract.py` 4 项复跑 PASS。合并前后 Python 全量对照在跑，结果随后记录，不以局部通过宣称整体通过。
- 合并线 Python 全量等价性（同机、同解释器、同 `--ignore=tests/workers`）：合并前 control（`dsh-backend-loop-20261001` @45a7d17c，经 dev.py）= **3921 passed / 30 skipped / 0 failed / 400.48s**；合并后分支尖端 = 3919 passed / 32 skipped / 0 failed / 388.99s。总数同为 3951，差集为 2 项由通过变跳过；已查明是**我的调用方式而非合并**：分支尖端那次跑的是裸 `pytest`，未经 `dev.py`，`OS_EXTERNAL_CONFIG` 未注入，`tests/test_media_extractor.py` 的 ffmpeg 两项按声明探测跳过。补测同一文件在两棵树各经 `dev.py` 跑一次：均 3 passed / 0 skipped，差集归零。结论：合并线 Python 与合并前基线等价，0 失败。
- 并行只读子智能体结论复核（一条成立、两条假阳性，全部实测）：(1) 成立——F10 说话人分离在本仓无引擎/模型/代码（跨 crates/services/app grep `pyannote|diariz|speaker` 为空；仅有 faster_whisper 的 `vad_filter`，不是分离）。(2) 假阳性——"worktree 内 ASR 默认模型目录指向不存在位置"：`_model_dir()` 优先级为参数→`ARCHEAXIS_ASR_MODEL_DIR`→声明→`_root_derived_model_dir()` 兄弟根→布局默认；设 `OS_EXTERNAL_CONFIG` 时解析到 `D:\All projects\Model library\whisper\faster-whisper-large-v3-turbo` 且 `model.bin` 存在，未设时具名 fail-closed 并提示 `--model-dir`（脚本 `.project-local/task-runtime/check_asr_model_resolution.py`）。(3) 假阳性——"RapidOCR PP-OCR ONNX 缺失"：三个模型在已安装包的 `rapidocr_onnxruntime/models/` 内（det 4,745,517B / rec 10,857,958B / cls 585,532B），且 `pyproject.toml:81` 已声明该依赖，子智能体只查了 Model library 与 HF 缓存两处。
- 合并线 Rust 全量首次跑通（`cargo_test.bat test --workspace --offline --no-fail-fast`，run `wi-rust-workspace-1`，日志 `wi/.project-local/task-runtime/wi-candidate/rust-workspace.log`）：**128 个 test-result 目标、516 passed、0 failed、0 ignored、exit 0**，聚合由 `.project-local/task-runtime/summarise_cargo_log.py` 机器统计而非读尾部。此前沙箱会话记录的"78 个 test targets 失败于 os error 5 PermissionDenied"在本令牌下完全不复现，进一步证明那是会话令牌作用域而非仓库或机器事实。至此合并线覆盖：Python 全量与合并前基线等价（0 失败）、Rust 516/0、前端 42 文件/326 项、`tsc --noEmit` + 生产构建、三条契约门禁、真实浏览器桌面门禁、以及本机 NSIS 候选。
- F10 供给可行性（未下载未安装）：ModelScope 的逐文件接口确实给出 `Size`+`Revision`+`Sha256`，满足本机"固定文件且发布方自带校验和"的前置；`iic/speech_campplus_sv_zh-cn_16k-common` 模型卡 Apache-2.0，`campplus_cn_common.bin` 28,036,335B，但该仓库**只有 PyTorch 权重、无 ONNX 导出**。**本条先前"GitHub release 直链亦可达"的说法已被 2026-10-07 实测推翻**：GitHub Release 资源主机与 `huggingface.co` 在本机均不可达（前者 `http=000`/`RemoteDisconnected`，后者 120 秒超时），ModelScope 的关键词搜索接口对四个查询一律 404，磁盘上也没有任何说话人嵌入模型（`Model library` 全树零命中，`sherpa-onnx\` 下只有两个 ASR 模型）。运行侧已装 `onnxruntime 1.20.1`/`faster_whisper 1.2.1`，未装 `torch`/`sherpa-onnx`/`pyannote` —— 且 `sherpa-onnx` 在能力声明里"已声明未安装"本身是对账待办。逐条测量、发布方标识与三个可选前置见 `docs/integrations/AAOS_SPEAKER_MODEL_SUPPLY_20261007.md`（外部发布方的 40 位提交标识不放在本台账，避免被当前权威面的"只引用真实对象"检查误判）。F10 保持 `PARTIAL`，不改断言、不降级结论、不谎称已供给。
- 宿主旅程第 16 步带值复跑（run `wi-host-loop-2`，收据 `wi/.project-local/task-runtime/aaos01-webdriver/5d1c04b6eb9a426d8b724e1af1d05869/receipt.json`）：补消息后实测为 `{route_media_type: None, declared: [], member_dir_requested: None}`。已排除三种解释：候选内 staged `worker_archive.py` 与源码 **同 SHA**（不是旧载荷）；路由能力名一致（`attempts.rs:43` 的 `("archive","archive.inventory",…)` 与 `ARTIFACT_ROOT_CAPABILITIES` 第 200 行字面相同）；执行器确实对该能力传 `--artifact-root`（`executor.rs:702`）。因此读到的确是归档 worker 在**未被要求解压**情形下的收据。仍未排除的是：该 job 的 `--artifact-root` 是否在候选 profile 下被实际拼出并送达 worker，以及探针取的是否是该源的**首个**（未请求解压的）job 而非自动成员 job。下一诊断：在同一候选上直接列 `source_jobs` 与两 job 的 `params` 对照，而不是改断言迁就结果。此项未闭，故 Q14/F15 的宿主级成员链在本候选上仍记 PARTIAL，不沿用 2026-10-06 旧候选的资格。
- 第 16 步的后续：根因定位、修复与真实宿主闭环（分支 `codex/aaos-ui-core-integration-20261007`，提交 `99b8343a`/`5f1f446c`/`fa1c643a`/`8af7b34a`）。**根因是 Windows 路径长度，不是"未请求解压"**：本机实测普通 `os.mkdir` 从长度 252 起失败（251 可建），尝试目录 `archive-attempts/<64 位摘要>/1/members` 长 247 因而建成功，成员文件 `0001-known.csv` 长 262 即被拒，且报的是 ERROR_FILE_NOT_FOUND（"路径不存在"）而不是"名字太长"——这就是上条"目录存在且为空"的成因。修复覆盖同一尝试目录里的三个写入方与 Core 的读回：归档成员（262）、邮件附件（263，此前静默零成员）、旧版工作表 CSV（269，此前直接抛错使整 job 失败），以及 `container.rs` 现以 `\\?\` 逐字路径打开声明成员（非 Windows 与相对路径不加前缀；该前缀在本产品里已有先例，宿主收据的 `workspace_db` 本身就是 `\\?\D:\…`）。**三处测试都先在同一台机器上证明"该字节的普通写确实被拒"再断言修复**，复现器输出 `REPRODUCED AND FIXED`；`tests/workers` 383 passed / 0 skipped / 106 subtests。同批修掉 CI 的 `lint → static` 级联：恢复包 5 个文件按 SHA 钉入既有 `_FROZEN_ORIGINALS`（A06 哈希在仓库之外登记，故其字节不可为格式化规则改写），门禁只对**哈希已核验**的钉桩字节放开尾随空白，改一个字节仍报 `frozen-original-mismatch`、同样字节放到未钉桩路径下仍报 `trailing-whitespace`；`check_repository_conventions.py --source head` 本地 PASS，相关测试 46 passed。我自己的 Rust 测试编译错误（`Path` 无 Display）由 CI 的 cargo-test 抓到——本地只跑了 `cargo build`，它不构建测试目标，故教训是复跑必须覆盖 CI 命令面。**真实宿主复跑（候选按 `fa1c643a` 干净树重建：core→stage 19,507 文件 manifest `a610e860…`→NSIS 150,800,840B `6aaa8811…`，宿主 `1bbf8808…` 11,330,048B；staged 三个 worker 与源码同 SHA）**：run `wi-host-loop-3`，收据 `wi/.project-local/task-runtime/aaos01-webdriver/b58a82686e0a4a7a83e43b23b1662e26/receipt.json`（540,988B）`ok: true`，**21/21 步**通过（本收据中成员链是第 17 步"Known XLSX/PPTX/CSV/TAR … and automatic TAR member"，上条所称"第 16 步"是上一版探针的编号）。带值读回：容器 job `g3-format-4e50943e…` 的 `extractable_members = [{name: notes/known.csv, file: 0001-known.csv, bytes: 36, sha256: 848c4180…}]`、`losses: []`、coverage 1.0；该成员即成为独立源 `src_f52840fbba1c70610aea052d` 并派生自动成员 job `g3-format-4e50943e…-member-0001-known.csv`，其 text 与 document_structure 输出均落库。证据级别仍按收据自述：`REAL_TAURI_WEBDRIVER_CANDIDATE`，"安装态由父级安装校验器供给、本探针只对安装器取哈希"，非物理 IME、无人工验收、单次工程运行非 P95。据此 Q14 的宿主级成员链由 PARTIAL 升为**已证**；旧 `rt`/`rt-python-input`/`nsis` 均改名保留未删（`-4da25bed`、`-deeppath2` 后缀）。仍未闭：CI 对 `8af7b34a` 的最终裁决、FMT-21 逐扩展名真人验收（不可自签）、物理 IME 与真实系统 DPI。
- 整量 Python 复跑在长路径工作树上的表现（与 CI 同令 `python -m pytest tests/ -q --tb=short`，经 `scripts/runtime/dev.py` 绑定外部根）：在 `.project-local\worktrees\aaos-ui-core-integration-20261007` 得 **4263 passed / 44 failed / 32 skipped（404s）**，失败错误集中在 `FileNotFoundError`（41 条）与 `WinError 206 文件名或扩展名太长`（4 条），文件面为 `test_workspace_api` 13、`test_workspace_pipeline_multiformat` 6、`test_green_candidate_verifier` 5、`test_deeptutor_bridge` 4 等。**判别实验**：把这 44 条以短基 `--basetemp=C:/Users/ALEX/AppData/Local/Temp/aaosbt` 复跑 → **44 passed / 25.01s**，故 44 条不是代码缺陷，而是本机工作树深度（pytest 基址已 200+ 字符）；同一作业在 CI 为绿，因为检出路径短。日志 `.project-local/task-runtime/full-suite-bf3c2c20.log`、复跑 `.project-local/task-runtime/short-base-rerun.log`。**但这同时暴露真实产品面同源风险**：失败点落在 `app/workspace/migrate.py:423 target.write_bytes(payload)` 这类普通路径写入上，说明上一条的逐字路径修复只覆盖了 transfer area 的三个写入方与 Core 读回，`app/` 的吸收/迁移、备份与 sidecar 重建面在长路径工作区仍会失败（对用户真实安装路径同样成立），已登记为独立任务，不在本条里顺手改。另记我自己的残留：一次被中止的 bare pytest 在仓库根留下 `__pycache__/conftest.cpython-312-pytest-9.1.1.pyc`，令 `test_workspace_layout_contract` 的 `assert ['root: __pycache__/'] == []` 变红；已按逐项精确路径删该文件再 rmdir。dev.py 的 `source_patch_sha256` 把未跟踪文件的**文件名与内容**一并计入，所以这类残留会污染其后每张收据的身份——先清残留，再绑证据。
- 2026-10-07 逐字路径覆盖到工作区、存储与索引面，并用同一把尺子量回（分支 `codex/aaos-longpath-app-20261007`，提交 `993b0871` + `08902e66`，PR #165）：**同一深基**（pytest 基址 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\4232e62f45\<24 字符 run-id>`，与本台账第 135 行那次记的 44 failed 完全同尺）下，整量 Python 现为 **4314 passed / 32 skipped / 0 failed（409.81s）**；同日短基 **4312 passed / 0 failed**，两者相差的 2 项就是本次新增用例与合入 main 带进来的用例。覆盖类别：`app/workspace/service.py` 23 处数据库打开、四个 owner 迁移模块（research/workspace/sleep_loop/knowledge_governance）的连接与存在探测、`shared/{storage,graph_index,fts_index,index_manifest,canvas,research_store,compat/*}`、`app/{knowledge,evidence,memory,learning,evaluation,workspace,exchange,capability,ingestion,federation,archive}` 的连接/写/枚举/tempfile 面，以及 `scripts/release/*` 三道候选门禁（深基 24 passed / 短基 24 passed，修前深基 7 failed）。**测出两条真实缺陷并按根因修**：`native_path` 把 UNC 拼成 `\\?\\\server` 令 SQLite 报 `invalid uri authority: %3F`（正确形式是 `\\?\UNC\server\share`），以及**已经带前缀的名字**仍被拿去拼 `file:` URI（前缀在 URI 里无意义，必须按名打开并配 `PRAGMA query_only=ON`）；枚举处若把产出的对象重新按名打开，会同时破坏对普通根的相对比较与测试的文件系统替身——这一点是被 9 条 RED 教出来的，不是先想清楚的。**保留而不自签的缺口**：`shared/obsidian_importer.py` 有六处把枚举结果与**普通**根做相对比较，机械包装使其中 6 条测试变红，已回退到普通名并把转换件留在分支外，等一次带接缝设计的改动；`intake_upload` 生成临时文件后交给第三方解析器（转换器按普通名打开）在深路径下仍未证。**齿证**：`tests/test_workspace_service_deep_path.py` 在 264 字符的库上跑真实 intake，且去掉前缀必须重现 `unable to open database file`；`tests/test_raw_asset_deep_path.py` 补 UNC 与已前缀两条；`tests/test_migration_runner.py` 的 FTS 回滚钩子改在**普通名**上识别主连接——原来它按 `args[0]` 比对象，包装后钩子静默不再匹配，而断言仍会绿，属于最坏型绿灯。**我自己的两处越界与修法**：把短名工作树 `.project-local/wb` 与 5 个脚本放在未授权类别里，`test_workspace_layout_contract` 两条立刻变红；按逐项精确路径 `mv` 归位（未删任何文件）后 4 passed。另记一次假绿：用 `env -u OS_EXTERNAL_CONFIG` 跑的“CI 模式”验证拿到 `EXIT=0` 但日志为空——该调用根本不产出 stdout，作废后改由 CI 真实 runner 判无外置根场景。**同日外部供给与 F10**（PR #164，提交 `5ef500bc`）：能力清单 26 行里 23 行有绑定路径、`missing_on_this_host = []`；`sherpa-onnx==1.13.8` 已按 `asr-sensevoice` extra 装进 CI venv 且 `OfflineSpeakerDiarization` 可导入；同日复测可达性为 `huggingface.co`/`cdn-lfs`/`hf-mirror` 三域 `000`、ModelScope 元数据 200 但**无逐文件校验和**、其工件是 pytorch `.bin` 而非该 API 消费的 ONNX，PyPI 通道可达（安装即证据）。**并入记录**：#162 以 `cfb95133` 并入 main（22 项已运行门禁全绿，含 `a0-gates`）；#163（U05 两条齿证回归）以 `b657eed6` 并入 main，并入前审计为 0 落后 / 2 领先、仅两测试文件、`test (3.12)` 等 24 项门禁全 pass。全程无 tag、无 release、不发布。
- CI -only 前端 flake 的定位与修法（提交 `c5d9494c`）：`6df3a615` 上 push 事件那条 CI（2143/2145）全绿，PR 事件那条 CI（2144）的 `desktop-build` 作业却报 `TestingLibraryElementError: Unable to find an element with the text: 来源版本`（`src/__tests__/CanonicalLibrarySpace.test.tsx` 的"identity-bound original and derived draft"用例），本地同令 `npm test -- --run` 48 文件/327 项全绿——不是分支坏了，是**同一套断言在更慢调度下失去时序保证**：并排视图的派生文档随点击到位，身份区块要等原件自己那次读取完成才出现，两者落在不同 commit，而用例用同步 `getByText` 去取。修法是把这一组断言各自 `await` 自己的元素（断言内容与数量一条不减），同文件里"拒绝配对"用例有同样的两读依赖，一并改。改后 PR 运行的 `desktop-build` 转绿，剩余非终态作业只有 `installer-lifecycle`（合并态由 BLOCKED 变 UNSTABLE，即"无失败、仍在跑"）。这条与上面深路径事项无关，是本轮另一类"本地绿、CI 红"的真实成因，记下来免得下次又归因到分支或环境上。
- 上条的进一步事实（文件系统证据）：该次运行的成员目录**已创建且为空** `data/worker-staging/archive-attempts/23e36c66…/1/members`，说明 `--artifact-root` 与 `members` 子目录确实送达 worker，`out_dir is None` 的分支被排除；因此失败被夹在 `_extract_members` 的写出循环内部（收到的成员集合为空、或命中数量/字节上限、或被判为加密），而这三条分支都会写 problems/losses，下一步应读该 job 收据的 `member_extraction` 与 losses 原文再判定。本条不改断言、不降级结论。
- 桌面窗口下限与缩放的真实张力（未改，留所有者裁定）：`src-tauri/src/main.rs:911` 默认 `inner_size(1280.0, 800.0)` 且无 `min_inner_size`；1920 物理屏在 200% 缩放下只有 960×540 逻辑 CSS px，小于默认窗口，因此「200% + 1920」与「默认 1280×800」不能同时成立。我没有替产品新增窗口最小尺寸；浏览器门禁仍按 960 CSS px 断言布局不破。本条原写「本机 Rust/Tauri 编译仍被既有 `canonicalize` Access Denied 阻断，无法本地验证」，该判定已被下一条实测推翻，原句留痕不删，以下一条为准。
- 接收来的 UI 分支上有一个已红的 REQUIRED 门禁（不是本次改动造成）：`tests/test_axr060_completion_audit.py` 要求 `docs/current/` 内出现的 40 位十六进制必须是本仓 Git 对象，而 `64440462 Implement AAOS UI taskpack increment` 把上游仓库 uiverse-io/galaxy 的固定 commit 直接写进了 `docs/current/AAOS-UI-ASSET-MANIFEST-20261007.json`，该 SHA 在本仓 `cat-file -t` 不存在，门禁在 `25213bdd` 即 FAIL（本次证据：`1 failed, 223 passed, 2 skipped`）。按仓库既有先例处理（DeepTutor 的 `docs/integrations/DEEPTUTOR_PRODUCT_BASE.md` 用 `- Commit:` 记录外部分支并明写「不是本仓对象」），把 6 个上游 pin 生成到 `docs/integrations/AAOS_UI_UPSTREAM_PINS.md`（由任务包 `spec/pool-revisions.json` 机器生成并逐条回读校验，未手抄），清单文件改为引用该路径；react-bits 的 NOASSERTION 许可与「仅参考不吸收组件」边界一并写明。未改门禁、未放宽断言。
- 本次仍不得升格：Tauri/WebView2 安装态、物理中文 IME、系统真实 DPI 缩放（本次是 `device_scale_factor` 模拟）、离线/失败/冲突/重启/恢复的宿主级 UI 旅程、任务包 U03–U06 的旅程级证据、真人验收、同 SHA Windows 候选。未提交远端、未推送、未合并、未发布、未改 ACL、未触碰 Green 与其他项目；全部输出在项目 ignored `.project-local` 内。


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

## 安装态完整生命周期证据落盘（2026-10-06，代码已改，待下一次完整运行产出收据）

Q02/Q14/Q15 的收口此前都卡在同一处：`desktop/scripts/verify_nsis_install.ps1` **确实**执行并断言了完整生命周期（首次安装与启动 → 可信关窗 → 就地升级 → 强杀清理 → 卸载保留用户数据 → 重装回读 → 最终卸载），任一步失败即 `throw`；但其结果只写进脚本 stdout，而 CI 只上传 `aaos01-webdriver/**`，其中 `install-preflight.json` 是在 WebDriver 会话**之前**写的阶段快照，故按设计写 `complete_lifecycle_verified=$false`。"完整生命周期已跑过"这件事因此**没有落进可下载的 artifact**，台账只能如实记成未证。

本轮只补**证据落盘**，不新增也不放松任何断言：脚本在全部尾部断言通过**之后**写入 `lifecycle-receipt.json`（schema `archeaxis/installed-lifecycle-receipt/v1`，`complete_lifecycle_verified=$true`，含 `in_place_upgrade`/`forced_tree_cleanup`/`clean_uninstall`/`uninstall_retains_data`/`reinstall_readback`/`pyc_growth` 等逐项布尔值、installer SHA-256、product/schema 版本与持久 job id）；写入位置即该次运行的 `aaos01-webdriver` preflight 同目录，故 artifact 内"阶段快照=false"与"完成记录=true"并存且语义清楚；CI 上传清单增加该文件名（`ci.yml` installer-lifecycle 步骤）。

- **边界（不夸大）**：这是**证据落盘**修复，**不产生**新的安装态资格。`install-preflight.json` 保持 `false` 不变——它是阶段快照，为求好看而改它才是不诚实。本机未跑该 CI，故新收据**尚未存在**：Q02/Q14/Q15 的完整生命周期维度在新一次 `installer-lifecycle` 运行产出 `lifecycle-receipt.json` 之前**仍记为未证**。物理 IME、真人 Owner、新 Green 部署与音频 300 秒作业上限均不由此改变。
- 护栏：`tests/test_release_manifest.py`（断言完成记录为 `$true` 且索引位置在尾部断言之后）与 `tests/test_ci_a0_gates.py`（断言上传清单含该文件名）。`checks/acceptance.json` 的 AQ26/AQ27 仍为 `NOT_RUN`，未改该不可变文件。
- 验证：相关四文件 **98 passed**；脚本经 PowerShell AST 解析 `PARSE_OK`。回滚：一次提交即可撤销。

## 更正：runs/ 的 "WinError 5 需提权" 判断有误——实为只读 git 对象，二次清理再释放 8.37 GB（2026-10-06）

前面"追加清理：runs/ 下每轮临时目录"一节把 590 个被拒目录记成**需要提权的 ACL 阻塞**（8.59 GB）。逐目录实测证明**该判断是错的**：进入其中一个 `tmp` 后可见，被拒的是 pytest 在临时目录里创建的 **git 仓库的松散对象**（`tmp/**/.git/objects/**`）；Windows 上 git 把这些文件标为**只读**，而 Windows 删除只读文件即返回 `WinError 5`（拒绝访问）。在**同一目录**里逐个删除普通文件全部成功 ⇒ 这不是当前用户缺少权限，也**不需要提权**；此前把它归为"权限阻塞"是**未追到具体对象就下结论**。

修正方式（`.project-local/task-runtime/prune-runs-scratch-20261006.py`，仅作用于 `runs/` 下名为 `tmp`/`pytest-tmp`/`pytest-cache` 的目录）：删除回调改为 `onexc`，**先清只读位再重试**，其余错误照常抛出（不吞、不强删）。重跑：

- 计划 **594 目录 / 8.37 GB**；实际**释放 8.37 GB**（`removed 160/594` 是目录计数，字节已全部释放）。
- `runs/` **13.45 → 4.86 GB**（逐文件遍历，跳过 146 个不可读项）；本批**全程未使用任何提权**，未改 ACL。
- **残留**：434 个目录仍被拒，但合计 **0.00 GB**（空目录）；它们与上一类**不同**——`os.scandir` 与 `Get-Acl` 都返回 `WinError 5`（"该操作需要提升的权限"），是**真正的受限 ACL**（连 ACL 都读不到），非只读位。因其为零字节且来源不明（未证实归属），**按"未知资产保留"不强行处置**，仅登记；即便提权，可回收字节也约为 0。
- 审计清单 `.project-local/task-runtime/runs-scratch-prune-20261006-pass2-audit.json`。
- 教训（与既有"先怀疑仪器"一致）：把 `WinError 5` 一律读成"需要提权"会掩盖真实对象；应进入目录、单独试删同类项，再判定。

## 归属实测：Green mainline 属沙箱身份、runs/ 残留属受限 ACL（2026-10-06）

清理中两处"动不了"的目标，本轮追到**具体原因**，以免今后继续按猜测重试：

- `ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline`（**6.24G**）：其所有者是 `DESKTOP-L26E3AC\CodexSandboxOnline`（SID 尾 `-1004`），当前用户是 `DESKTOP-L26E3AC\ALEX`（尾 `-1001`）；`git` 直接以 `detected dubious ownership` 拒绝一切读写。要操作它必须加 `safe.directory` 全局配置——那是**改全局配置**，不做；且它本就非当前身份资产，**按"保留 + 标注未解决"处理**，删除需 Owner 决定。
- Green 的 `ArcheAxis-Knowledge-OS` worktree（**2.51G**）与 `minimax-aaos-cosmic-ui-20261001`（**0.65G**）所有者均为 ALEX（可操作）；前者 WIP 已固化为归档，属"可删除待裁决"；后者按 Owner 裁决保留为供体。
- `runs/` 下 434 个残留目录：`Get-Acl` 本身即被拒（"该操作需要提升的权限"），是**受限 ACL**；因其零字节，即便提权可回收也约为 0。

## 追加清理：未被引用的 build/ 根（3.05 GB）与一次前端测试探查（2026-10-06）

对开发根 `build/` 的每个较大条目做**精确路径**引用核对（在跟踪工作树内按名字检索），删除四条**在 `build/` 路径下无任何引用且可再生**的构建产物：

- `build/22cad761f8`（2.43G）：它是**已删除** worktree `aaos-ui-phase2-integrate` 的按 worktree 构建根（含 `cargo/`+`dotnet/`+`phase2-d6bd374-publish-20261001/`）。两处文档提到 `22cad761f8` 时指向的是 `.project-local/runs/22cad761f8/...`（收据截图），**那是另一棵树且已保留**——已实测 `runs/22cad761f8/ui-icon-preview-20261001/icons.png`（11,971 B）仍在，`phase2-d6bd374` 在 `docs/` 下零引用。
- `build/desktop-publish-r20`（0.21G）、`build/ui-detail-20261003-v2`（0.20G）、`build/ui-detail-20261003-v3`（0.20G）：三条 dotnet publish，在跟踪工作树内**零引用**（同名的 `ui-detail-20261003` 被引用故保留）。
- 只用精确路径（无 glob、无父目录递归），清只读位后重试删除；审计清单 `.project-local/task-runtime/prune-uncited-build-roots-20261006-audit.json`。`build/cargo`、`build/dotnet`、`build/rust-msvc` 等工具链/缓存与所有被引用条目**未动**。测试节点 `build/be268a2d33`（主检出构建根，被 `AAOS-AUDIT-SNAPSHOT` 等引用）保留。

**前端测试探查（如实记录，未改产品代码）**：新增五个组件/路由测试（共 28 项本地通过），补齐审计曾点名的组件级测试缺口——`frontend/src/__tests__/RealData.test.tsx`（7，数据原语与"失败体不得是原始引擎串"）、`CommandPalette.test.tsx`（6，快捷键/过滤/选择导航/Escape/开时对壳层设 `inert`）、`CanvasBoard.test.tsx`（6，投影与"终点缺失的连线不绘制"、编辑提交、删除连带边）、`SpaceView.test.tsx`（5，桌面/网页两态路由契约：库类走 CanonicalLibrary、知识类走 CanonicalKnowledge、工作台附 BackupPanel）、`SettingsSpace.test.tsx`（4，加载/失败/就绪三态与就绪步骤标签、备份控件在命名前禁用）。

另**加固一处既有门禁**：`StyleRuleCoverage.test.ts` 的类名查表写成 `new RegExp("." + name + "(?![\\w-])")`，前导点未转义即成了**通配符**——只要样式表里存在“以该类名为结尾”的规则（如 `.supercard` 之于 `.card`），它就会被判为“已有样式”，真实缺口被掩盖。已改为转义点（`"\\."`）并**证伪**：独立脚本对 `.supercard{…}` 用旧写法得 `styled=true`（掩盖缺口）、新写法得 `false`（正确报缺口）；对 `.card` 与 `.card-muted` 两写法一致。当前仓库两种写法都是 0 缺口，故此洞此前是**潜伏**的——本次是加固，不是修复既有漏报；同时补一条用例把“长选择器不得掩盖短类名”钉住。

**这批测试已在 CI 实际执行并通过**：head_sha `99e6bbe6…` 的 pull_request 运行 37475869337 中 `test (3.12)` 车道 `completed/success`（该车道会跑前端套件）。本机那处 `CanonicalLibrarySpace` 超时**未在 CI 复现**，佐证其为**慢机时序抖动而非产品缺陷**。

## 开源吸收：gitleaks 由“仅报告”转为**强制**（2026-10-06，含一次自我纠错）

**先纠正我上一轮的错判**：我此前记“Gitleaks 未吸收、本机无二进制约无法验证”，依据是 `.gitleaks.toml` 不存在、且我只看了 `security-targeted` job。**实测证伪**：`.github/workflows/ci.yml` 的 `test` job 早已有 gitleaks 8.30.1 步骤（钉版本 + 上游 sha256 校验，`continue-on-error: true` 仅报告），许可也已登记在 `docs/truth/SUPPLY_CHAIN_LEDGER.json` 的 `A024`——**吸收早已发生，缺的只是“跑干净后可转为强制”那一步**。这是我漏看既有接线导致的重复发现，如实记录。

**本轮补齐的正是那一步**（按该步骤注释里的既定判据）：

- **取得并核验二进制**：从上游 release 下载 `gitleaks_8.30.1_windows_x64.zip`，与上游 `gitleaks_8.30.1_checksums.txt` 对拍一致（sha256 `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`）；包内 `LICENSE`（MIT，1069 B，sha256 `e3884b252b3bfc…`）。只落在被忽略的 `.project-local/task-runtime/aaos01-secret-scan-20261006/`，**不提交二进制**。
- **先证伪仪器再用**：向临时 fixture 注入假的 AWS Key 与 GitHub PAT，gitleaks 报出 2 项（`aws-access-token`、`github-pat`）——证明扫描器确在工作，再采信其“干净”结论。
- **真值判定**：以 `git archive HEAD` 导出**与 CI 完全相同的跟踪树**（2964 文件 / 41.88 MB）扫描 → 发现 1 项误报（`apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml` 的 Avalonia 主题键 `AaosSurface2Brush`，`apps/` 不在我早前的逐目录清单里，漏扫暴露）；`detect` 扫 **2480 个提交**又发现 1 项误报（旧文档里作为脱敏标记的单词 `REDACTED`）。两者都在 `.gitleaks.toml` 中**按字面值命名**，且该 allowlist 只用具体值/一个 docs-only 提交，**从不放行任何源码目录**。
- **转为强制**：给既有步骤加 `--config .gitleaks.toml` 并**去掉 `continue-on-error`**（`--exit-code 1` 本就保留），使发现真实凭据即失败；`pip-audit` 因本机无 `uv` 无法验证干净，**仍保持仅报告**。
- **护栏**：新增 `tests/workflow/test_secret_scan_config.py`（4 项）——默认规则必须开启、allowlist 只能命名具体值而不得放行源码目录、扫描步骤钉版本+校验且**必须非 report-only**。
- **连带修复**（都被既有门禁抓到，未绕过）：`.gitleaks.toml` 是新跟踪路径，需同时登记进 `.worklab/project-validation.v1.yaml` 的 `ci-policy` 风险类（`tests/test_ci_classifier.py` 要求每个跟踪路径恰有一类）与 `docs/current/R5-PATH-DISPOSITION.json` 的 `top_level_disposition` 的 build-configuration 规则及其 `current_ownership` 度量（`unowned_paths/count/by_root`）。三类检查现已全部通过。
- **验证**：`tests/test_ci_classifier.py`、`tests/test_ci_a0_gates.py`、`tests/workflow/`、`tests/test_approved_paths.py`、`tests/test_mfx001_supply_chain_ledger.py` 合计 **163 passed**；路径约定 2963/2964 已归属、1 未归属且已登记。**并在 CI 端到端复核**：head_sha `096c5c55…` 的 pull_request 运行 37481106438 中 `test (3.12)` 车道 **success**，其步骤列表实测含 `✓ Secret scan (gitleaks 8.30.1, pinned and asset-hash verified)`（job 112330106378，6m40s）——即去掉 `continue-on-error` 后该步骤**在 CI 真跑且通过**，吸收不再只是“仅报告”。跑整个前端套件时 `CanonicalLibrarySpace.test.tsx` 的"reads hashed original…"一项失败（`waitFor` 1s 超时，用时 1146ms）。**已核实为本机时序抖动而非产品缺陷**：失败断言要求 `anchor_create` 的 `body.revision` 等于 `sha256("原文样板")=d74012a2…`，而实测收到的调用**正是**该值且 `source_id=src_test` 正确——行为已发生，只是慢于 1 秒阈值；该文件我未改动，单独运行同样超时，与本次新增无关。**故不宣称前端套件在本机全绿**，并留作后续可在慢机上放宽该 `waitFor` 的独立切片。

**权威 Python 套件的一个本地假失败（已定位，非回归）**：以 `scripts/ci/run_tests.sh --full` 跑得 **4214 passed、30 skipped、1 failed**，失败项为 `tests/workflow/test_workspace_layout_contract.py::test_no_entry_sits_outside_the_documented_layout`，其 `out_of_layout=['root: __pycache__/']`。**根因是本地裸跑 pytest 所致**：我此前用 `python -m pytest …` 直接调用（未经 `-B`/`PYTHONPYCACHEPREFIX`），pytest 编译根 `conftest.py` 时在仓库根写出 `__pycache__/conftest.cpython-312-pytest-9.1.1.pyc`。删除该目录并以 `PYTHONDONTWRITEBYTECODE=1` 重跑，四项全过（4 passed）。`scripts/ci/run_tests.sh` 走 `dev.py`（设 `PYTHONPYCACHEPREFIX`）故权威路径不会产生该假失败。结论：**非产品/仓库回归，属裸调用卫生问题**；后续本地跑套件应经 `scripts/ci/run_tests.sh` 或加 `-B`。

## Q02/Q14/Q15 的完整生命周期维度已收口（2026-10-06，实测 artifact）

前面"证据落盘"修复已在一次**完整资格运行**中产出收据。`workflow_dispatch force_full` run **37471031307**（head_sha `ccf0a4bc48aff0054d1d6717877faf10d7312941`，attempt 1）**19/19 全部 job success**，含此前长期被 skip 的 desktop-build/desktop-fast/installer-lifecycle/rust-vnext/test(3.12) 等重车道。从该 run 下载 artifact `installed-native-journey-ccf0a4bc…-1`，其中三份关键文件**并存且语义清晰**：

- `aaos01-webdriver/4c20cb0b…/receipt.json`：`ok=true`、`evidence_level=REAL_TAURI_WEBDRIVER_CANDIDATE`、**21 步**、`owned_process_cleanup=true`、`owned_ports_released=true`（安装态真实 Tauri WebDriver 旅程）。
- `aaos01-webdriver/70b8f307…/install-preflight.json`：`complete_lifecycle_verified=false`、`next_operation=independent_webdriver_session` —— **阶段快照，按设计保持 false，未被粉饰**。
- `aaos01-webdriver/70b8f307…/lifecycle-receipt.json`：**本轮新增**，`complete_lifecycle_verified=true`，逐项 `graceful_shutdown`/`in_place_upgrade`/`forced_tree_cleanup`/`clean_uninstall`/`uninstall_retains_data`/`reinstall_readback` 全 `true`、`pyc_growth=0`。绑定 `head_sha=ccf0a4bc…`、`run_id=37471031307`、`installer_sha256=2eec221fa5b4c958266c111bfd177bdd468b4e92969164017ab1a0869c2aac10`、`product_version=0.6.14`、`core_schema_version=11`、`persisted_job=installer-lifecycle-210ff2bf2d36b9f0`；收据 SHA-256 `aeae1bd3512edf0a5766924a9b318586a4cd279930ce54e83e57a0477b01fa24`（630 B）。下载件 `.project-local/task-runtime/q02-lifecycle-artifact-20261006/`。

**由此闭合"完整生命周期"这一证据缺口**：安装态旅程、就地升级、强杀后宿主/端口零残留、卸载保留用户数据、重装回读、最终卸载干净——由**同一次**运行内的具名布尔与绑定 SHA 共同给出；阶段快照的 `false` 与完成记录的 `true` 并存，不靠改快照达成。

**仍未收口（不夸大）**：`checks/acceptance.json` 的 AQ26/AQ27 仍为 `NOT_RUN`（该文件不可变，未改）；物理 IME、真人 Owner 交互、新 Green 实际部署、音频 300 秒作业上限、用户旧库完整语义迁移均不由此改变；本收据来自 CI 安装态，不代替 Green 部署或真人验收。

## 更正：本机**有** uv，交接前提失效；pip-audit 实报的 5 项已升到修复版（2026-10-06）

交接件 §4.1/§5.1 写“本机无 uv，无法证明跑干净”，并据此把 pip-audit 转强制列为需 Owner 授权。**实测证伪**：`uv 0.12.23 (2026-10-03)` 在 PATH（`/c/Users/ALEX/.local/bin/uv`），`uvx` 同版本；因此不需要“引入 uv”也不需要改 CI 依赖，Owner 的那一项授权前提不成立。同一条更正也适用于 `Crawlee 需重生成 uv.lock` ——锁文件本机可重生成。**这是既有教训的又一次命中：断言“做不了”之前先实测工具是否存在。**

判据不靠本机感觉，靠 CI 既有报告：完整资格 run `37471031307` 的 `test (3.12)` job `112294372735` 日志第 3084 行原文为 `Found 5 known vulnerabilities in 2 packages`——`urllib3 2.7.0`（PYSEC-2026-4175/4176/4177，修复 2.8.0）与 `soupsieve 2.8.4`（PYSEC-2026-4170/4171，修复 2.9.0+）。两者都是传递依赖（urllib3 ← courlan/htmldate/requests，soupsieve ← beautifulsoup4），`pyproject.toml` 未对其设上限，故**按修复版升级而不是加 `--ignore-vuln` 放行**：`uv lock --upgrade-package urllib3 --upgrade-package soupsieve` 得 `urllib3 2.8.0`、`soupsieve 2.10`，`uv.lock` 仅 7 行变动（版本与哈希）。

**顺带查出一处 CI 仪器缺陷（比“仅报告”更弱）**：该步骤写成 `pip-audit … | tee "$artifacts/pip-audit-report.txt"`，而 runner 默认 shell 是 `bash -e {0}`（**不带 pipefail**），管道退出码取自 `tee`——即 `tee` 恒为 0。因此**即便日后去掉 `continue-on-error`，该步骤也无法因发现漏洞而失败**。已加 `set -o pipefail` 使管道的真实状态得以保留；`continue-on-error` 在同一次改动里去掉——前提见下一段（本机已按 CI 同法证得“旧锁报 5、新锁干净”）。

本机复跑的根因也定位了（不是索引缺版本）：`uv tool run` 默认挑了 **CPython 3.14.7**，而 `onnxruntime==1.20.1` 没有 cp314 轮子，pip 在临时 venv 里解析失败并被 pip-audit 报成 `Failed to install packages`——这是**运行方式**问题；改为 `--python 3.12`（对齐 CI 的 3.12.14）后，同一个钉版本 pip-audit 对**同一份 CI 导出的 locked-ci.txt**给出结论：

- 旧锁导出 → `AUDIT_EXIT=1`，报告逐行等于 CI 的那 5 项（urllib3 2.7.0 ×3、soupsieve 2.8.4 ×2）——**先证伪仪器**；
- 新锁导出 → **`No known vulnerabilities found`，`AUDIT_EXIT=0`**。

**据此把该步骤转为强制**：去掉 `continue-on-error`（`--strict` 与 `--exit-code` 语义保留），并加 `set -o pipefail` 使管道真的能把步骤弄红。护栏新增 `tests/workflow/test_dependency_scan_config.py`（4 项：钉版本+`--strict`、非 report-only 且必须 pipefail、命令体内不得用 `--ignore-vuln` 点名放行、审计对象是 `uv export --frozen --only-group ci` 的锁导出而非 pyproject 区间）。**三项注入实测各自只弄红对应那一项**（改回 report-only / 删 pipefail / 在命令里加 `--ignore-vuln PYSEC-2026-4177`），还原后 4 项全过；ci.yml 以字节还原并断言一致。
升锁连带命中一条**真值测试**：`tests/test_release_manifest.py::test_release_manifest_is_packaged_truth_and_matches_dependency_lock` 断言 `app/release-manifest.json` 的 `dependency_lock.digest` 必须等于 `sha256(uv.lock)`——它不是被我改坏的，而是**如实发现了清单与锁漂移**。按仓库既有约定（提交 `79332377` 只改 digest、`revision` 保持 8）用脚本重算并回写摘要，写后重新读回断言相等；该套件回到 **35 passed / 0 failed**。
**CI 侧读回已取得**（head_sha `5e5d102b`，push run `37490490651`，job `112361733929`，日志第 3079 行）：强制状态下的该步骤**实际执行**并输出 `No known vulnerabilities found`，随后正常进入 gitleaks 步骤——即“去掉 `continue-on-error` 后仍能通过”已由 CI 自己证明，不再只是本机结论。

**同一个 job 因我自己引入的一处回归而 FAILURE（如实记录，非他人改动）**：失败项是 `tests/maintenance/test_active_output_boundaries.py::test_active_sources_do_not_embed_machine_absolute_roots_or_legacy_runtime_output`。根因是我新增的 Rust 测试夹具把样例正文的来源写成 `.hermes/task-runtime/ingest-samples/...`，而该门禁把 `crates/` 等**活动源码**里出现遗留运行输出根路径判为违规。按“真值测试优先于新功能”处理：**不动门禁**，只把夹具里的来源改为中性的 `ingest-samples/oxford-meaning.pdf`（该项断言的是 `core_objects → not_merged`，与此字符串无关）。复验：该门禁 **1 passed**，`cargo test -p archeaxis-migration --tests --offline` 六个套件合计 **27 passed / 0 failed**。教训：往活动源码里写“真实历史路径”之前，应先跑该边界门禁。

## Green 暗工作树按 Owner 裁决删除（2026-10-06，逐项精确路径）

Owner 裁决“删（归档已复核）”。删除前**独立重跑**保留点核验（`.project-local/task-runtime/green-dark-worktree-20261006/verify-preservation.py`，全项 PASS 才允许删除）：`archive_sha256`（zip 101,071 B = `681bd720…`）、`patch_sha256_in_archive`（336,622 B = `81dc481d…`）、`untracked_members_match`（21 项逐哈希）、`live_head`（`7282e5a9…` 未变）、`live_modified_match`/`live_untracked_match`（现场未提交状态与清单一致，未新增 WIP）、`untracked_bytes_unchanged`（21 个未跟踪文件磁盘哈希仍相符）。

执行（先 dry-run 出清单再 `--apply`；审计 `prune-audit.json` + `finish-audit.json`）：

- 口径为**逐文件遍历求和（跳过不可读项）**：删除前 `2,692,920,775 B`（=2.51 GiB，与交接一致）。
- 经**属主检出** `git worktree remove --force` 移除，其管理项 `.git/worktrees/ArcheAxis-Knowledge-OS1` 一并消失；`git worktree list` 由 6 项降为 **5 项**。该命令在深层缓存上返回 `Invalid argument`，故按既有做法以 `\\?\` 扩展前缀补完剩余条目并清只读位重试。
- 实际移除 **3703 个条目**，残留 **13 个条目 / 16,716 B**（占原体积 0.0006%）：uv 的 `sdists-v9/editable/**/archeaxis_workspace-0.6.14-0.editable-py3-none-any.whl`（16,716 B，属主 ALEX、模式 644 **非只读**，清只读位与 `\\?\` 均仍 `WinError 5`）与若干 `pytest-cache`/`pytest-temp` 空目录（`GetFileAttributesW` = `0x10`，无重解析点）。**与上一轮 `runs/` 的 434 个零字节受限目录同类**，判为被句柄/ACL 持有的再生缓存，**未提权、未改 ACL**，按“未知资产保留并标注”登记。
- 净效果：暗工作树内容与 worktree 注册关系**已消失**，Green 侧只剩一个 16.7 KB 壳；`.ui-task-tree/ArcheAxis-Knowledge-OS-mainline`（6.24 GB，CodexSandboxOnline 所有）与 `minimax-aaos-cosmic-ui-20261001`（Owner 裁决保留）**未触碰**。
- 回滚配方写入审计件：`git worktree add …-Green….ui-task-tree\ArcheAxis-Knowledge-OS 7282e5a9…` + 应用 `green-ui-task-tree-7282e5a9-20261006.patch` + 从归档 zip 复原 21 个未跟踪文件。

## Q11 旧库逐表审计与**选择性并入**（2026-10-06，Owner 裁决：有用的并入主线，没用的去掉）

Owner 没有选“旁路只迁笔记”，而是给出判断准则：**先审计，有用并入，无用去掉**。据此做了三步，全部只读源库、写在**旁路暂存库**里（Rust Core 仍是唯一规范写者；未写产品主库、未双写）。

**1）逐表实测**（`.project-local/task-runtime/q11-legacy-table-audit-20261006/audit_legacy_tables.py`，SQLite 以 `mode=ro` URI 打开）：`data/cognitive_os.sqlite`（3,223,552 B，`b318c99e…`）**审计前后 SHA 相同**；**89 张表 / 67 张 0 行 / 22 张有行**。加载产品同款 `sqlite_vec` 扩展后 `vec_episodes` 可读（5 行）。

**2）内容判读（纠正我自己的一处先验）**：我原以为“episodic 内容全空、向量整条无价值”，实测**episodic_memory 5 行中仅 2 行为空**，且 5 条向量里 **3 条是非零向量**（非零字节 1534/756/1535）——**假设被自己的仪器证伪**。进一步读正文：3 条有内容的行来源分别是 `.hermes/task-runtime/ingest-samples/oxford-meaning.pdf`、`manual-test`、`.hermes/task-runtime/ingest-samples/course.docx`，即**导入样例与手工测试夹具**，不是用户本人的知识。据此定的“有用/无用”判据是内容层面的、可复核的：

| 表 | 处置 | 依据 |
| --- | --- | --- |
| `ir_intake_cards` | **并入** | 1 行是真人撰写的吸收决策（考霸学习法 - 目标设定模块，含“吸收/不吸收”清单、目标仓库、风险） |
| `machine_lessons` | **并入** | 1 行是机器教训（模式/类型/今后约束/证据链），按合同只能作为**机器候选** |
| `core_objects`/`episodic_memory`/`memory_records`/`execution_traces` | 不并入，保留在保真导出 | 正文即上述样例；`memory_records`/`episodic_memory` 与 `core_objects` 同 id 同正文，重复并入只会造出重复知识 |
| `vec_episodes*` | 不并入，保留在保真导出 | 主线**尚无向量表**；这些是上述内容行的向量影子 |
| `*_fts_config`/`*_fts_data` | 去掉 | 全文影子存储，由内容表重建 |
| `schema_migrations`/`migration_operator_runs` | 去掉 | 旧库记账；vNext 记自己的历史 |
| 67 张 0 行表 | 去掉 | 无内容可携带 |

**3）实现与证据**：`crates/archeaxis-migration` 新增 `stage_legacy_library_selectively`（+ `LegacyTableDisposition`/`SelectiveStageResult`）。它**先** `verify_export`（清单摘要 + 逐文件哈希 + 行数 + 拒绝未登记 `.jsonl`），**再**写暂存库；写入走 `archeaxis_domain::knowledge::create_knowledge_v3`（不手搓 INSERT），因此受合同约束：人类旧库内容 → `PERSONAL_DEFINITION` + `source_type=imported_legacy` + `owner=human`；机器教训 → `OBSERVATION` + `source_type=machine_candidate` + `owner=machine`（validate_v3 明确禁止机器候选被自动接受）；两者 `status='candidate'`、`support_level='none'`（不虚构支持度）、`requires_human_review=1`。`created_by` 携带 `legacy_cognitive_os:<表>:<旧行 id>` 保证同一正文的不同旧行不合并，且重跑只计 `reused`。**每一张表都得到恰好一条具名处置**（merged/discarded/not_merged + 理由），所以“去掉”是被记录的判断而不是静默丢失。

- 新增测试 `crates/archeaxis-migration/tests/selective_legacy_stage.rs`（3 项）：`useful_tables_merge_and_every_other_table_is_named`（含“未合并表也各有处置项、处置数=导出表数+不可读表数”）、`tampered_export_is_rejected_before_any_staging_write`（篡改后**不创建**暂存库）、`the_legacy_library_bytes_are_untouched`。
- 实测：`cargo test -p archeaxis-migration --tests --offline` → 本 crate **27 passed / 0 failed**（新 3 + 原 24）；`cargo fmt --all --check` **PASS**。
- **真实旧库跑通**（`crates/archeaxis-migration/examples/selective_stage.rs`，对象为上文 89 表保真导出，清单摘要 `597027d4…` 经 Rust `verify_export` 接受，即跨语言哈希等价再次成立）：`intake_cards_staged=1`、`lessons_staged=1`、`row_errors=0`、处置合计 **merged 2 / discarded 77 / not_merged 10**；暂存库回读两行确为 `('PERSONAL_DEFINITION','candidate',…,'imported_legacy','human','none',1)` 与 `('OBSERVATION','candidate',…,'machine_candidate','machine','none',1)`，中文正文与“吸收/不吸收”列表逐字在位（收据与 270,336 B 暂存库在 `.project-local/task-runtime/q11-selective-stage/`，sha256 前缀 `35443751…`）。
- **边界**：这是**旁路暂存**并入，未触碰产品主库；把暂存内容交给正式 Core 数据根、以及“这次迁移算完成”的判断，仍属 Owner 验收（与 Q07 的“机器不能自我接受”同一条线）。样例内容（3 条导入夹具正文）**未被并入**，若 Owner 认为它们也该进主线，走的是同一函数，判据需由 Owner 明确。
- 交接件 §5 的第 4、5 项本轮不重开：300 秒作业上限已由既有裁决“保持上限 + 窗口化”落地，`build/cargo` 在 Owner 限定的“非 cargo、超预算”范围之外；失败模型原始输出 Owner 裁决**继续留在界面内**（反粉饰规则不变）。

## F08 图表数据 与 F13 ODF/RTF 读通（2026-10-07，均无需新依赖）

**先纠正继承来的清单**：上一轮子智能体把 F04 说成“未知扩展名被拒”，实际 `R15-FORMAT-STATUS.json`
里 F04 是**图像族**（原图/OCR框/阅读顺序/图示描述）。所以本轮**以 JSON 的 `gap` 原文为准**逐族核对，
没有按那份分类表施工。另一个纠正：F13 原文写“其余格式仍 custody-only，`.epub`、`.ods` 等无路由名者被拒”，
但 EPUB 早已有 spine 章节读取，而 `grep -r opendocument crates services config shared app` **零命中**——
即 **ODF 在产品路径里从来没有实现过**，`app/ingestion/multi_format.py` 里的 odt/rtf 属遗留兼容面。

**F08 PPTX 图表数据**（提交 `4d781b7e`）：worker 用标准库直接解析包内 `ppt/charts/chartN.xml`，
经幻灯片自己的 `.rels` 把 chart part 归到对应幻灯片，投影出 `Series <名称>: <类别>=<值>`，
并给出 `slide_chart` 结构锚点；数值**是文件自带的缓存**，回执里以 `chart_data_source` 明说，
只有链接工作簿而无缓存的系列被具名为“no cached values”而不是补数。新增
`tests/workers/test_pptx_chart_data.py` 3 项（含“缓存清空后不得出现数值”“无图表包不得虚报”），
与既有 office 套件合计 **9 passed**。

**F13 ODF + RTF**：`crates/archeaxis-application/src/attempts.rs` 为 `odt/ods/odp/rtf` 命名媒体类型并
加入 `text.extract` 接受集；`worker_text.py` 把四者交给 light-format 读取器；新 `odf()` 先校验
`mimetype` 条目**与文件名声称的类型一致**（不一致即拒），再读 `content.xml`：标题按 `text:outline-level`
带层级、正文段落、表格单元格携带文件自存的 `office:value` 与 `span`、演示页 `draw:page` 成为可寻址路径，
`table:number-rows/columns-repeated` 超过 512 时**按上限报出并留损失项**而不是展开成假数据；
`rtf()` 用**已声明的** `striprtf`（`pyproject.toml:39`）剥控制字并锚定段落。安全边界沿用 EPUB 的做法：
条目数/展开字节上限、拒绝穿越名与符号链接成员、重复路径拒绝。

**两条真值测试因世界改变而更新，不是为了让改动通过**：`route_capabilities.rs` 的
`a_binary_container_name_is_refused_because_no_route_can_read_it` 原把 `sheet.ods` 列为“必须被拒”，
其前提是“没有路由能读它”——该前提现已不成立，故只保留 `mail.msg` 并把原因写进注释；
`accepted_media_types("text.extract").len()` 由 13 改为 17，并**补上四个显式成员断言**（含
“ODF/RTF 不得进入 image 路由”），使该断言不再只是一个计数。验证：`cargo test -p archeaxis-application
--test route_capabilities --offline` **8 passed / 0 failed**，`cargo fmt --all --check` PASS，
`scripts/check_format_matrix.py --matrix ...` **exit 0（16 组，14 partial，2 custody_only）**，
Python 侧 ODF/RTF 新 7 项与相邻三套格式套件合计 **35 passed**。

## 吸收核对仪器的两处相反缺陷（2026-10-07，含一条被钉住的错分类）

`Apache Tika` 因词根 `apache` 命中许可证文本而被记成“已声明”（本仓库根本没有该 sidecar），
`Mozilla Readability` 因搜索词是 `mozilla` 而只匹配到文档域名，**且
`tests/workflow/test_oss_disposition_evidence.py` 把 `MENTIONED_IN_SOURCE` 当断言钉住**——
错的搜索词配一条通过的测试比失败的更危险。改词后实测：`A011` 得 `DECLARED` 且定位到
shared/adapter_fixtures.py:153（`readabilipy` 确在 `pyproject.toml:82` 声明），
`A010` 得 `NONE`，`A001` 因 `shared/models` 补入 vendor 根而得 `DECLARED_AND_VENDORED`；
分布由 {"DECLARED": 25, "STUB_IN_SOURCE": 2, "MENTIONED_IN_SOURCE": 2, "IMPLEMENTED_IN_SOURCE": 6, "NONE": 12} 变为 {"DECLARED": 24, "DECLARED_AND_VENDORED": 1, "STUB_IN_SOURCE": 2, "MENTIONED_IN_SOURCE": 1, "IMPLEMENTED_IN_SOURCE": 6, "NONE": 13}。
护栏改为断言事实，反证是改前那次运行本身。`A004 RapidOCR` 的“桩还是真用”歧义**本轮未裁定**。
详见 `docs/current/AAOS-OSS-DISPOSITION-EVIDENCE-20261006.md` 新增的“更正三”一节。

## 外溢数据追踪清理（2026-10-07，先审计后逐项精确路径）

只读审计（子智能体）+ 本机复核后，**只删了两项已证实的**，其余全部保留：

- 删除 `C:\Users\ALEX\AppData\Local\Temp\aaos-real-embed-4fzxe8g7\real.sqlite`
  （**4,251,648 B**）：与主检出根 `.project-local/task-runtime/wsr/real-embed/real.sqlite`
  **SHA-256 逐字节相同**（`6cebf2be…`），空父目录一并移除。
  注意过程：审计件给的“归档副本”路径**不存在**，删除脚本据此**拒绝执行**；改正为核实到的真实路径
  并重算哈希后才删——fail-closed 在这里救了场，子智能体的路径转述不可直接采信。
- 删除主检出根 `D:\All projects\ArcheAxis-Knowledge-OS\__pycache__`（**5,247 B**，
  仅 `conftest.cpython-312/313-pytest-9.1.1.pyc` 两项）：这正是此前
  `tests/workflow/test_workspace_layout_contract.py` 报 `out_of_layout=['root: __pycache__/']`
  假失败的来源；删除前逐项核对成员名，非预期成员即拒绝。
  合计释放 **4,256,895 B**（4,251,648 + 5,247；两项分两次运行删除，第二次的审计件里
  `__pycache__` 已记为 `already_absent`，故审计件的 `freed` 字段只含前者，不能当作总量）。
- **更正一条旧记录**：`%LOCALAPPDATA%\ArcheAxis Knowledge` **在本机不存在**（也不存在
  `ArcheAxis`/`Programs\ArcheAxis Knowledge`/Roaming 变体），故“旧安装宿主残留在本地安装目录”
  不成立；本机唯一 archeaxis 相关项是 `com.archeaxis.workspace`（41,626,516 B，被
  `RUNTIME_DELIVERY_AUTHORITY_INDEX.md:45` 与 `tauri.conf.json` 引用）——现役宿主状态，**不动**。
- **保留并标注**：`%TEMP%` 下 3 个 `aaos-*` 目录属**真·ACL 拒绝**（`GetNamedSecurityInfoW` 连读
  owner 都返回 error 5，非只读对象类，与 runs/ 那 434 个零字节同类），非提权不可且不宣称可回收字节；
  `D:\All projects\dsh-acl-reports-20261003`（83,329 B）是对 Formal 库做过 ACL 写入的**唯一回滚载荷**，
  全仓无归档副本，**必须保留**；`C:\Users\ALEX\.dsh`（339,240,921 B）是外部工具的家目录，非本项目资产；
  主检出根 `.venv`（960,392,331 B）虽 git-ignored 且可再生，但**绑定解释器且可能有并行会话在用**，
  本轮不动。审计与删除清单：`.project-local/task-runtime/spillover-audit-20261007/`。

## 我自己引入的一处 Rust 真值测试回归（2026-10-07，本地全量抓到并当场修正）

给 `odt/ods/odp/rtf` 命名媒体类型后，只跑 `route_capabilities` 是全绿的，但 **`cargo test -p archeaxis-application --tests --offline` 全量跑到 `office_job_end_to_end.rs:87` 失败**：
`office_names_select_the_office_route_and_the_legacy_formats_are_refused` 把 `old.rtf` 与
`old.doc/old.ppt/old.xls` 放在同一组，断言它们**连媒体类型都无法命名**（`cannot name a media type`）。
RTF 现在有命名路由，拒绝理由随之变成“该路由不接受此媒体类型”——**拒绝仍然发生，但原因不同**，
所以这条断言的旧前提（RTF 无任何读取器）已不成立。

处理方式遵循“真值测试优先”：没有把整条断言放宽，而是**把 RTF 从“无名遗留二进制”组里分出来单独断言**，
并且是**收紧**：`.rtf` 必须经 `text` 路由解析成功，同时 `office` 路由必须以 `cannot accept media type`
拒绝它——即“命名了它”不得让 RTF 冒充 Office 包进入读 Office 的路由（那正是原测试要守的不变量）。
`old.doc/old.ppt/old.xls` 三条原样保留。验证：`cargo fmt -p archeaxis-application` 后
`cargo test -p archeaxis-application --tests --offline` **21 个测试二进制结果全部 ok、CARGO_TEST_EXIT=0**。
教训（与既有“本地跑子集不足以证明”一致）：**跨媒体类型表的改动必须跑该 crate 的全量测试**，
只跑与改动直接相关的那一个测试文件会漏掉别处对同一张表的断言。

## F13 的一处**假支持**由 CI 抓到、F10 词级时间落地（2026-10-07）

**我引入的缺陷，CI 抓到的，本地没抓到**：F13 那一次我给 `attempts.rs` 命名了 `odt/ods/odp/rtf`，
也改了 worker 的读取器，却没有改 `services/python-workers/transport/text_ndjson.py` 里那份
**自己独立的** `media_types` 白名单。本地跑的相关套件全绿，而 CI 的 `workers-vnext` 与
`test (3.12)` 直接把 ODF 作业拒在 worker 边界（`AAK-VAL-002`）——也就是说我当时交付的是
“**Core 声称支持、worker 实际拒绝**”的假支持。修正在提交 `679c8292`：补齐 transport 白名单，
并给 `scripts/check_format_matrix.py` 加**两侧一致性检查**（该能力在 Core 命名而 worker 不接受 → 红；
worker 接受而 Core 从不命名 → 也红）。门禁先证伪再用：删掉 `application/rtf` 得
`the Core names media types the worker rejects: ['application/rtf']`；塞进一个 Core 从未命名的
`application/x-invented-type` 得反向失败；两处还原后 exit 0。同时把 F13 的四条路由**写进证据主张**
（此前记录只声明 `text/plain`，所以门禁对它无话可说——这就是漏检能存在的结构性原因）。

**同一轮 CI 还抓到第二处**：`striprtf` 只在项目主依赖里，两条 CI 车道都只装 `ci`/`ci-adapters`，
于是 RTF 用例在 CI 里必红（本地因装了主依赖而看不出来）。按 xlsx 那次 `AAK-WORKER-003` 的先例处理：
把 `striprtf>=0.0.32` 加进 `ci-adapters`（`b5bbfd84`），`uv lock` 仅 +2 行，manifest 摘要按既有约定只改
digest；并让被引擎门控的用例**具名 skip**，另加一条不依赖引擎的用例断言“缺引擎必须以 RuntimeError 失败作业”，
所以两条车道都仍在覆盖这段代码。**审计口径**：`uv export --frozen --only-group ci` 与升级后逐行相同
（本机 diff 为空），故 pip-audit 的“干净”结论沿用，未被这次锁变更作废。

**F10 词级时间（本条为真增量，不是记录）**：词时间沿 `split` 同一条参数通道走完全链——
HTTP 体 `words`（可选，默认 false）→ Core 请求身份（`/parameters/words` 参与幂等比较，
片段回执不得冒充词回执的应答）→ `Request::word_timings()`（非 `media.transcribe` 直接拒绝）→
transport 校验并传参 → `_segment_cues(word_timestamps=…)` 记录每个词的毫秒级起止 →
`offset_cues` **同时平移词时间**（漏掉就会让后窗口的词时间与全局 cue 错位），并拒绝平移后为负的
词跨度。回执同时声明 `word_timings_requested` 与 `word_timings_produced`，模型没给词时间时**不会被读成已给**。
验证：新增 `tests/workers/test_word_timings.py` 6 项（含“未请求就不发 flag 也不记词”“具名拒绝未知参数/
`words:false`/非转写能力”）与 Rust 用例 `word_timings_reach_the_transcribe_request_and_are_refused_elsewhere`；
`cargo test -p archeaxis-sidecar-protocol -p archeaxis-application -p archeaxis-api --tests --offline`
**75 个结果全 ok**（含新用例实测执行），`cargo fmt --all --check` PASS，Python 侧相关三套 **16 passed**。
**仍未闭合（不粉饰）**：说话人分离仍无引擎亦无处置行；词时间的**界面开关**按 Owner 指令（前端任务暂停）未做，
目前只在 HTTP 边界可用。**真实引擎已实测**（不只是接线）：
`tests/workers/test_word_timings.py::test_the_real_model_produces_word_timings_when_the_engine_and_model_are_bound`
用项目声明的 `faster-whisper-large-v3-turbo`（权重路径经 `config/environment/external-resources-index.json` 的
`resolved`+`exists` 解析；第一版我从检出目录猜父级，会在 worktree 里**静默跳过**，被自己的 -rs 输出抓出后改正）
对 `tests/fixtures/golden/golden-audio-anchor.wav` 实跑：`word_timings_requested=true`、`word_timings_produced=true`，
词时间 0–500 / 500–1180 / 1180–1800 ms 对应 Learning/Evidence/Anchor；该文件 **8 passed、0 skipped、16.11s**。
仍未实测：窗口化与词时间的组合（需一段真超上限录音；偏移逻辑目前有单元层与“负跨度即报错”两层覆盖）。


## 格式切片 F01 + F06（2026-10-07，提交 09f68a9c 与 41a34d3d，回归修复 6237c5f1）

**F01 源代码符号（真增量）**：`.py` 现在沿完整路由链走到符号解析——
`attempts.rs` 名称表与 `text.extract` 接受集（18 项）→ `text_ndjson.py` 的 `media_types` 声明 →
`worker_text.py` 的结构化媒体集 → `worker_light_formats.python_source()`。符号取自解释器自带的 `ast`，
是**该文件自身语法树的事实**：类、函数、异步函数、import 各带声明行；锚点仍是行基，符号只作为
`loss_receipt.params.format` 里上报的事实存在。解析失败如实写 `parsed:false` + `parse_error` 且
**符号列表为空**，正文仍按文本投影——不编造一份看起来合理的符号表。

**F06 词尾那一环（真增量）**：OCR 结果现在回到它来时的那一页。每个链式页源以
`import` 原点 `<pdf source_id>#page-N` 入库，并且**核验该关系确实落库**（原点是 INSERT OR IGNORE，
静默丢弃会被读成"已记录"）；`ocr::pages_of` 与 `GET /api/v1/sources/:id/pages` 按页回答该页 OCR 出来的文本。
未跑的页以 `recognised:false` + 无文本报告，`received_at` 保持 NULL——时钟值不虚构。

**验证（数字取自当次日志）**：
`cargo test --workspace --offline` → **120 个套件全部 ok，496 项通过、0 失败**；
修复前一次同范围运行 71 套件 / 338 项亦全绿；
新增两套 Rust 用例分跑 **2 套件 / 5 项全 ok**，
且 `a_scanned_pdf_chains_into_a_real_ocr_job_and_its_text_is_stored` **未被跳过**（日志无 skipping 行，
真实 tesseract + PyMuPDF 样本，3 项 4.11s）；
`cargo fmt --all --check` PASS；
Python 全量 `tests`（dev.py 车道）**4211 passed, 30 skipped, 14 warnings, 146 subtests passed in 467.60s (0:07:47)**；
`check_format_matrix.py` exit 0（13 core routes / 12 worker routes 双向对齐）、
`scripts/check_path_conventions.py` 与 `scripts/ci/check_document_authority.py` exit 0；
CI 选择集的 ruff（`--select E9,F63,F7,F82`）对 services/tests/crates 全绿。
矩阵 F01/F06 两行只改 `implemented_now`/`gap`/`evidence`，`required_output` 逐字未动。

**我自己造成的缺陷，两处，如实登记**：
(a) **分支遮蔽**：名称表里 `"py"` 原本已存在于**更早**的 `"txt" | … | "py" | …` => `text/plain` 分支，
我新加的 `"py" => "text/x-python"` 因此永不可达——文件仍按纯文本走，而四张表看上去都"命名了它"。
Python 侧三层用例当时全绿，只有 Rust 侧内容断言暴露它（`left:"text/plain" right:"text/x-python"`）。
除了从旧分支删掉 `"py"`，我把 `resolve_media_type("text","tool.py")` 写成内容断言，并让 Python 用例
直接检查 `text/plain` 分支不得再含 `"py"`；17→18 的计数守卫保留，但已不是该行为的唯一守卫。
教训：**往 first-match 的表里加项，必须同时检查更早的分支是否已覆盖它**，"表里有"不等于"分支可达"。
(b) **上一轮词时间提交破坏了已提交用例**：`tests/workers/test_transport_window_request.py` 的 fixture worker
是真实 worker 的替身，签名缺 `word_timestamps`，而 transport 两条路径都无条件传该参数，于是该用例红
（`TypeError: extract_split() got an unexpected keyword argument 'word_timestamps'`）。
CI 当时未判（PR #161 pending），由本地全量 `tests/workers` 抓到。替身按真实契约补齐并记录其值，
**新增 split+words 用例**——窗口化与词时间的组合此前零覆盖。已在 6237c5f1 单独提交。

**仍未闭合，不粉饰**：符号解析只覆盖 Python，其余源代码语言仍按纯文本投影、不声称符号（这里没有它们的解析器）；
容器成员路径复用同一名称表（`crates/archeaxis-application/src/container.rs:140` 调 `attempts::resolve_media_type`），
按代码推断一个 `.py` 成员现在也会被命名为 `text/x-python`，但**没有成员级用例实测该组合**，故不记为已验证；
transport 对 `text/x-python` 只由"该类型在其声明集内" + 矩阵双向门禁保证，未加经 `execute()` 的用例。
F06 的回写是**关系而非合并**：文本仍住在页源上，PDF 自己的锚点仍只覆盖其文本层，
扫描页在 PDF 文档内部没有可寻址区域；`pages_of` 的 HTTP 面尚无界面消费者（前端任务按 Owner 指令暂停）。

**回滚**：`git revert 41a34d3d` 与 `git revert 09f68a9c` 各自独立可回；回归修复 6237c5f1 不建议回退，
回退它会重新引入那条红用例。


## 格式切片 F13 邮件附件（2026-10-07，提交 e52fc4c3）

**这是真增量**：`.eml` 的附件不再只是"列出+哈希"。有 Core 给的转移区时，worker 把每个附件写到
`<attempt root>/members/<扁平安全名>`，并**按容器同一张声明表**上报 `{name,file,bytes,sha256}`
（`params.structure.extractable_members`）；Core 侧复用现成的 `container::expand_members`：逐项校验
摘要与字节数、以 `import` 原点 `<mail source_id>#<附件名>` 把附件导入成自己的 source，并按**附件自己的文件名**
选路由队一个作业。实测链：`notes/index.md` → 自有 source + `job-mail-member-0001-index.md` → 执行后
`transforms.text` 含 6371；`opaque/blob.bin` 无路由可读 → 保留为 custody-only 且 `readable` 仍为 false。
**被否证的旧声明**：矩阵 F13 行原文写着"listed, explicitly not extracted"，本轮改为事实描述；
`gap` 里"no attachment extraction for mail"同步删除，换成新的真实边界。

**三层路由知识（缺一层就静默不支持）**：
1. `attempts::media_type_for_name` 是 **first-match** `match`——往表里加项必须检查更早的分支是否已覆盖它（F01 就栽在这）。
2. 只有列在 `attempts::ARTIFACT_ROOT_CAPABILITIES` 的能力，executor 才会把转移区路径通过 `--artifact-root` 交给 worker；
   本轮把 `text.extract` 加进去，而**是否真的写转移区由 transport 的路由表按 media type 决定**
   （`member_dir_by_media` 只声明 `message/rfc822`），其余文本格式拿到根目录也不建目录、不声明成员——
   这条不变性有专门用例（`an_ordinary_text_job_declares_no_members_and_creates_no_chain`、
   `test_a_non_mail_media_type_is_never_handed_a_transfer_directory`）。
3. `worker_text.extract(..., member_dir=…)` 只有 `message/rfc822` 才走抽取；
   并且一旦真的抽取，就必须**删掉** mail() 那句"independent extraction is not performed"的损失行，
   否则回执里留下一条已被自己行为否证的假话。

**验证（数字取自当次日志）**：
`cargo test --workspace --offline` → **121 套件全部 ok / 498 项通过**；
新增 `crates/archeaxis-application/tests/mail_member_chain.rs`（真实 transport+真实 worker，
1 套件 / 2 项 ok，含"附件自有作业执行后可读、custody 项不被冒充为已读"）；
新增 `tests/workers/test_mail_attachment_members.py` 7 项（扁平安全名、真名留在声明里、预算 50/51 具名报告、
无转移区不声明、非邮件 media 不得拿到目录、transport 层双向用例）；
`cargo fmt --all --check` PASS；`tests/maintenance` **184 passed, 2 skipped, 2 subtests passed in 10.55s**（合同数字一致性 + 路由清单双向）；
Python 全量 `tests` **4218 passed, 30 skipped, 14 warnings, 146 subtests passed in 482.76s (0:08:02)**。
**门禁反证**：往 F13 行注入一条不存在的 `application/x-not-a-route` 路由声明后
`scripts/check_format_matrix.py` **rc=1** 并指名该三元组，说明"每条声明都在表里"这条断言不是空转；
恢复后 rc=0。`check_document_authority.py`、`check_path_conventions.py` 亦 exit 0。

**合同联动（新增 HTTP 路由必须一起动的数字）**：`GET /api/v1/sources/:id/pages` 使
`AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` 的 §3 标题 61→**62** pairs、§3 表新增编号 **43** 行、
§6 "42 projection pairs (37 unconditional mounts)"→**43 (38)**、§6 "61 addresses (41 base + 20 runtime)"→
**62 (42 + 20)**、正文"41 base … total 61"→**42 … total 62**；对应测试常量
`projections 37→38`、`len(base) 41→42`、`len(wrapper|base) 42→43`、`documented_routes() 61→62`。
2026-10-05 那句"extended … to 61 pairs"是**历史记录**，不改写，另加一行 2026-10-07 的 62 说明。
两处 gate 在我只改部分数字时确实报红，改全后才绿——所以这组数字是被验证过的，不是照着猜的。

**仍未闭合，不粉饰**：附件抽取只有一层——附件本身是容器时会被导入但不再展开（`route_for_member` 明确不做嵌套）；
只有附件、没有正文的邮件以 `ValueError("EML has no readable text body")` **失败作业**而非空成功；
`.msg` 二进制容器仍无 reader；抽取上限 50 个/64 MiB（与容器同一套预算），超限项在损失里具名而不是消失；
`GET /sources/:id/pages` 尚无界面消费者（前端任务按 Owner 指令暂停）。

**回滚**：本轮 F13 代码一次提交可独立 revert；合同数字与其同属该提交，revert 即一起回到 61/42/37。


## 格式切片 F07 DOCX 标题分层（2026-10-07，提交 807f6d8a）

**真增量**：读取段落的样式与其**在文件里定义的**大纲级别，优先级为
段落自身 `w:outlineLvl` → 所引用样式定义的 `outlineLvl` → 内建标题样式名（`heading 1` / `标题 3` 中英文皆读）。
回执新增 `style_definitions`、`paragraph_count`、`heading_count` 与 `headings`（级别/样式/字符数，上限 200 项）。
**级别一律来自文件自身的声明**：不从文本、长度或大写"猜"标题——那是伪造目录的开始。
样式只在 `word/styles.xml` 存在时才解析；段落引用了未定义的样式时，回执报的是**文件里真实存在的标识**
（例如 `标题 3`），不会替它编一个显示名。
`kind`/`path` 逐字未变（仍 `paragraph-N`），所以这仍是"上报事实"，不是新的寻址层——导航仍按行锚。

**验证**：新增 `tests/workers/test_docx_heading_styles.py` 5 项（golden 夹具、样式定义给级别、段落级优先、
中文样式名、无声明即无标题、kinds/paths 不变），`tests/workers` 全量 **316 passed, 106 subtests passed in 57.91s**；
`cargo test --test office_job_end_to_end --test mail_member_chain --offline` **2 套件 /
5 项 ok**（office 端到端未被我的结构改动破坏）；`check_format_matrix.py` exit 0；
Python 全量 `tests` **4223 passed, 30 skipped, 14 warnings, 146 subtests passed in 485.17s (0:08:05)**。
**改一处矩阵行差点误伤另一处**：F07 与 F08 引用同一组 office 测试，未限定行范围的替换会有两个合法匹配；
改成只在 `"format_id": "F07"` 与 `"format_id": "F08"` 之间做替换，并**反向断言 F08 的引用列表未被改动**。
（第一次的自检断言本身写错了——它假设 F08 只引用 2 项，而 F08 本轮已合法地引用 3 项；
修正的是我的断言，不是被检查的对象。）

**仍未闭合，不粉饰**：run 级直接格式（不走段落样式）不读；列表编号不还原；样式表缺失时只能靠样式名；
F07 主缺口"结构作为寻址层"仍未动——那是 anchor 契约变更，会同时影响 F05/F08/F09/F12 四行的同类子句，
应作为独立一刀做，不在本切片顺手改。

**回滚**：`git revert 807f6d8a`（worker、测试、矩阵行一起撤回；F08 行不受影响）。


## 格式切片 F12 与 F14（2026-10-07，F12 提交 3cc446c1，F14 提交 a75d3487）

**F12 画布事实**：节点除几何外还带回文件自己声明的 `color` 与 `style`（非空字符串才记，空白不是颜色），
坐标必须是数字（字符串/null 直接丢弃，不强行换算）。**矩阵原句"canvas geometry is not projected（worker 自己这么说）"
是过期的**：worker 已多轮把 x/y/width/height 作为事实上报；同时它的损失句声称"ports 未投影"也不实——
边是**逐字保留**的，所以 fromSide/toSide/fromEnd/toEnd 本就跟边一起走。两处都按代码改正，
并加 `tests/workers/test_canvas_node_facts.py` 把"实际做了什么/没做什么"钉住（含 golden 夹具字节不被改动）。

**F14 `.xls`（新引擎真正吸收）**：`xlrd 2.0.2` 进 `ci-adapters`（BSD，LICENSE 3,771 B
sha256 b5a5dbce…；METADATA `License: BSD`；两条 BSD 条款），`office.structure` 新增
`application/vnd.ms-excel`，读取按 xlrd 自己的类型表把单元格分成 text/number/date/boolean/error/empty，
日期用工作簿自带的 datemode 换算；**转换件**为每表一份 CSV，走 F13 刚验证过的成员通道声明（`{name,file,bytes,sha256}`），
Core 校验后导入成自己的 source 并排队文本路由；**损失报告**点名转换带不走的东西
（公式不重算、数字格式/样式/合并区/图表/图片/透视/宏）。
`uv lock` 仅 +11 行；`uv export --only-group ci` 与被审计的 `locked-ci.txt` **去注释排序后逐行相同**
（diff 0 行），所以 pip-audit 的结论沿用；release manifest 只按既有约定改 `dependency_lock.digest`。

**四张表 + 一处真相测试一起改**：名称表、`accepted_media_types`、`ARTIFACT_ROOT_CAPABILITIES`、
executor 的展开门；以及 `office_job_end_to_end.rs` 里断言 `old.xls` **必须被拒绝**的那条真相测试——
它是"无 reader 就不命名"的守卫，如今 reader 存在，因此把 `.doc/.ppt` 留在拒绝列表、
把 `.xls` 改为按名解析并**新增一条反向不变量**：`.xls` 不得走文本路由（二进制被当文本解只会产生噪声）。
另外 xlrd 的 `on_demand` 会**占住在 Windows 上写出的视图文件**，测试里临时目录删除直接失败
（WinError 32）；正解是 `book.release_resources()`——我先写的不存在的 `book.release()` 也被同一个测试当场抓出。

**夹具来源如实写**：`tests/fixtures/golden/golden-xls-anchor.xls`（5,632 B，sha256 3225b8bb…，
manifest 已登记）是本轮用 `xlwt 1.3.0` 一次性生成的**项目自造合成件**；xlwt 只在生成时当工具用，
**装完即卸**（现在 venv 里 xlwt=False、xlrd=True），不进任何依赖声明。因此 FMT-21（.doc/.xls/.ppt
逐扩展名用真实样本验收）仍是 **NOT_RUN**：自造件证明的是接线与读表能力，不等于 Excel 亲笔件的保真度。

**顺带纠正的既有错账**：重算 `disposition_summary` 时发现，旧账把 1 个 `REFERENCE` 组件记成了 `CURRENT`
（旧摘要 CURRENT 12 且无 REFERENCE 项；组件实际为 CURRENT 11 + REFERENCE 1）。现在按组件重算：
`CURRENT 12（含 xlrd）/ REFERENCE 1 / ADOPT 13 / EVALUATE 9 / SIDECAR 3 / REVIEW-BLOCK 9 / REJECT-CORE 1 = 48`。
另一次我误用 donor 文档的词表给 ledger 写了 `ABSORB`，被 `tests/test_mfx001_supply_chain_ledger.py`
以"invalid disposition"直接判红——两套词表不是一个东西，改回 ledger 自己的 `CURRENT` +
`qualification ["source","installed"]`（不宣称 release 级，因为本轮不发布）。

**验证**：`cargo test --workspace --offline` **122 套件全绿 / 500 项通过**；`xls_member_chain.rs` **1 套件 / 2 项 ok**
（两个转换表都成为 source、各有自己的作业、执行后正文含 `星环 知识平台`、`members_of` 读回可读；
`.doc/.ppt` 仍被拒）；`tests/workers` + 合同/分类器合跑 **374 passed, 106 subtests passed in 61.20s (0:01:01)**；`tests/workers/test_canvas_node_facts.py`
与既有画布/字幕套件 **328 passed, 1 warning, 106 subtests passed in 66.37s (0:01:06)**；门禁（release manifest / 供给链 ledger / workflow / maintenance）**334 passed, 2 skipped, 2 warnings, 2 subtests passed in 68.50s (0:01:08) — 同一条门禁在前一步曾判红：它拒了我给 ledger 写的 `ABSORB`（那是 donor 文档的词表），所以这里引的是改正后重跑的那次**；
`cargo fmt --all --check` PASS；矩阵检查 exit 0 且**状态计数与行一致**（16 组：0 complete / 15 partial / 1 custody_only）；
文档权威与路径约定门禁通过；Python 全量 **4239 passed, 30 skipped, 14 warnings, 146 subtests passed in 431.64s (0:07:11)**。

**被 F14 反过来照出的第二处过期账**：`tests/test_format_matrix.py::test_a_hidden_gap_and_a_stale_summary_are_refused`
硬编码拿 **F14** 当"没有路由声明的行"来注入 `status: complete` 违规。F14 一旦合法获得路由，
这条注入就不再产生预期违规——门禁没坏，是**门禁自己的样本假设过期**（全量 Python 套件把它照了出来，
而不是我事先想到）。修法与同文件里另一条守卫一致：**动态挑一条无路由声明的行**，
并把"改了状态却没改摘要"的第二项断言写成不绑定具体桶名的形式
（消息取自实跑输出，不凭记忆编造）。修完 `tests/test_format_matrix.py` 12 项全绿。

**仍未闭合，不粉饰**：`.doc`/`.ppt` 无 reader 故仍命名拒绝；F14 的"转换件"是值级 CSV，不是版式或渲染；
CSV 转换上限 32 表/64 MiB，超限在损失里具名；FMT-21 真实样本验收 NOT_RUN；
"把 worker 结构升级为寻址层"这一条同时卡在 F05/F07/F08/F09/F12，需要 anchor 契约变更，本切片刻意未动。


## 格式切片 F02+F03 URL 抓取（2026-10-07，工作树于 f53dc28e 之后）

**这次补的是"抓取时间"的来源，不是又一个能力**：F02 的 gap 原文是"没有任何东西去抓 URL，
抓取时间无法从文件本身得知（import origin 的 received_at 正是它的归处）"。
Core 的导入接口**早就接受** `origin_kind="url"` + `origin_ref` + `received_at`（`ImportBody`，
`ALLOWED_ORIGIN_KINDS` 含 url），缺的从来只是"有人去抓"。所以这一刀没动 Core 契约、没加 capability：
`scripts/ingest/url_snapshot.py` 走 F15 目录驱动同一形状（脚本说 HTTP，不抢产品路由），
调已有的有界快照 worker，导入时把**正文到达的那一刻**写进 `received_at`，再按 html 排队。

**先补安全，再谈可达**：`worker_webpage.py` 原本只查 scheme/超时/字节上限，会把
`http://127.0.0.1/`、`169.254.169.254`（链路本地元数据）、`::1`、`::ffff:127.0.0.1`、`10/172.16/192.168`
一律当普通网址放过去，而且 urllib 会**自己跟重定向**——公网页面完全可以把内网地址递进来。
现在加的是：`public_addresses()`（字面 IP 直接判定；主机名要求**每一个**解析答案都是公网单播，
部分指内网即整体拒绝）+ `_GuardedRedirects`（每个重定向目标重新过政策，非 http(s) 直接拒）。
**限制照实写进代码与 gap**：政策是在解析那一刻检查的，DNS rebinding 不在它的射程内——真正的边界是网络层 egress 政策。
超上限的正文改为**拒绝并写明未写快照**（原来是悄悄截断还落盘）。

**可测性逼出的一处真缺陷**：`public_addresses(host, resolver=socket.getaddrinfo)` 把默认值**绑在 import 时刻**，
测试无论怎么 patch 模块属性都换不掉它——于是该决策在代码里不可注入。改成 `resolver=None` + 调用时绑定，
测试才真正在测政策而不是测 DNS。同时承认两条我自己写错的期望（`example.com` 实解析出 Cloudflare 两台、
`/v2/api` 的尾段是 `api` 不是 `v2`），改的是断言以符合**实测行为**，不是改行为迁就断言。

**失败面**：抓取失败 → 收据记 `status=failed`、`source_id/job_id` 为 null、**不写 received_at**（没有到达就没有到达时间），
且一次 Core 调用都不发；导入 413 → 记失败并带上游状态；`--dry-run` 不碰 Core 但仍如实报 received_at。

**验证**：新增 `tests/test_url_snapshot_driver.py` 13 项 / 20 子测试（政策拒绝 12 类内部地址、重定向再检查、
scheme 规则、上限不落盘、文件名不可逃逸/不无名、导入体携带 final_url 与 received_at、失败不外呼、
dry-run 外呼为 0、收据逐行 JSONL）；`tests/test_worker_reachability.py + tests/maintenance` 合跑 **204 passed, 2 skipped, 22 subtests passed in 10.56s**；
`check_format_matrix.py` exit 0（F02/F03 两行只改 implemented_now/gap，required_output 逐字未动）；
路径约定与文档权威门禁通过；Python 全量 **4252 passed, 30 skipped, 14 warnings, 166 subtests passed in 443.34s (0:07:23)**；单元合跑（`tests/test_url_snapshot_driver.py + tests/test_worker_reachability.py`）在**已提交状态**下为 **20 passed, 20 subtests passed in 0.22s**，rc 0。**过程如实记录**：写作中途那次合跑曾报 `2 failed, 12 passed, 19 subtests passed in 0.21s`，两处失败是我自己写错的两条期望（`example.com` 实解析出两台 Cloudflare、`/v2/api` 的尾段是 `api` 不是 `v2`），改的是断言以符合实测行为，不是改行为迁就断言；该数字是中间态，不作为本切片的验收证据。
**F02/F03 仍 partial**：F02 的抓取是驱动级，产品路由**依然**不持网络（这是选择不是缺口）；
F03 要的是渲染与分页/滚动覆盖，本仓库无浏览器，抓到的"未脚本化的正文"不等于渲染后的页面。

**回滚**：`git revert` 本切片提交即可（驱动 + worker 政策 + 两行矩阵 + 测试同属一次改动）。


## 嵌套容器 + 无正文邮件（2026-10-07，工作树于 863fd3e6 之后）

**这一刀修的是"具名拒绝"，不是新增能力。** `container::route_for_member` 把 `zip`/`tar` 写成
`None`，并且有一条**已提交单元测试**断言"nested.zip 没有作业"；矩阵 F13 的 gap 于是把这规则
描述成"附件抽取只有一层"。实测（下面的新测试）：邮件里的 `.zip` 附件此前**拿不到作业**，
它内部的文件在任何深度都不可达——不是被拒绝读取，是根本不会被打开。

**边界是新加的、可命名的，不是"放开"**：`CONTAINER_DEPTH_LIMIT = 2`。深度不是猜字符串，
是从**已记录的 origin 链**walk 出来：成员关系是 `"<容器 source_id>#<成员名>"`，
walk 只认 `origin_kind = "import"` 且**父 id 必须在 `sources` 里真实存在**，
否则链到此为止（一条 `path` 来源里出现 `#` 不会被当成容器父级）。walk 上限 16 只是防退化，
超过限额的判断不依赖它。超限的成员容器**仍然被导入并保留**，只是不再展开它自己。

**为什么不叫它 custody-only**：`custody_only` 的既有含义是"没有路由能读它的字节"，
而嵌套容器的路由**确实存在**——把它算进 custody 就是谎报能力缺失。所以 API 新增
`nesting_limited`（每个成员）与 `nesting_limited_count`（总计），note 里写明其含义；
`custody_only_count` 改为 `成员数 − 可读 − 嵌套限额`。HTTP 契约 §表中该行的描述同期补齐
（此前只写"Source members."）。

**我改了三处已提交的测试断言，逐条说明，不含糊**：
1. `crates/archeaxis-application/src/container.rs` 的模块单元测试：`nested.zip`/`nested.tar`
   从"必须 None"改为"必须 archive"；同一条测试**保留** `video.mp4`/`audio.wav`/`unknown.bin`
   仍必须无作业。改的是被本切片替换掉的那条规则的前提，不是把期望调低。
2. `crates/archeaxis-application/tests/archive_member_formats.rs`：**夹具原本是假字节**
   （`b'PK opaque nested container'`、`b'opaque nested tar'`）——旧规则下它们不会被打扰，
   新规则下作业会诚实地失败。夹具改为**真 ZIP / 真 TAR**（stdlib `zipfile`/`tarfile` 生成），
   作业总数断言从 6 改为 **10**（8 个直属成员作业 + 每个嵌套容器内 1 个文件作业），
   并**新增**"`media.wav` 仍无作业"的断言与"嵌套容器自己的 `members_of` 里出现
   `deep/inside.txt` / `deep/tarinside.txt`"的断言——即测试现在比改之前更能证明第二层真被打开。
3. `tests/workers/test_mail_attachment_members.py` 里
   `test_a_mail_with_only_attachments_still_fails_rather_than_succeeding_empty`：
   它断言的正是本切片要取消的旧行为，替换为 5 项覆盖四种形状的新用例。

**邮件那半刀（F13 要求的"邮件头"此前会一起丢）**：`worker_light_formats.mail()` 对
"无 text part 的邮件"抛 `ValueError("EML has no readable text body")`，作业整体失败，
于是**邮件头也一起丢**——而 F13 的 required_output 逐字包含"邮件头"。现在：
无正文邮件投影**它自己的邮件头块**（`From/To/Subject/Message-ID/Date` 里非空的项，
顺序固定），锚点是 `mail_header`；损失句区分两种真实形状——"no text body part exists"
与"every text body part is empty"；并且不再说 "mail MIME body decoded"（那种情况下那是假话）；
`has_readable_body`/`text_body_parts` 进 receipt；**既无正文、又无邮件头、又无附件**才拒绝
（新错句 `EML has no readable text body, headers or attachments`）。
附件仍照常抽出并入队；`worker_text` 里"independent extraction is not performed"那句在附件
被抽出后照旧被剔除，两种分支共用同一条规则。

**顺带修正的措辞**：`worker_archive` 的损失句 "are listed, not opened" 会让 Core 已经开始展开
嵌套容器后的收据变成误导，改为 "are listed, not opened **by this worker**; any opening is the
Core's own member expansion"——保留 `tests/test_worker_archive_route.py` 所断言的子串，
不改那条测试。

**仍未闭合，不粉饰**：F15 的成员关系仍是 origin 引用（不是一等 container→file 边，
只能一次查一个容器）；被读到的成员仍未升级为知识；目录批量仍是脚本；
F13 的二进制 `.msg` 容器仍无读取器，ODF 样式/字段/内嵌对象/链接目标仍未跟随，RTF 表格/脚注
仍未重建；`.doc`/`.ppt` 仍无 reader；FMT-21 逐扩展名真实样本验收仍 NOT_RUN；
`CONTAINER_DEPTH_LIMIT` 的**数值**是本轮的选择（每层各有一套 50 项/64 MiB 预算），
未由真人验收。

**本机实测的另一条线索（记录以免下一轮重复探测）**：`.doc` 的候选 reader 在**本机确实存在**——
`C:\Program Files\Git\mingw64\bin\antiword.exe`（284,448 B，自报 `Version 0.37 (21 Oct 2005)`，
GPL，映射表在 `mingw64\share\antiword\`），但它**只能读 `.doc`，不能读 `.ppt`**；
`soffice`/LibreOffice、`catdoc`、`wv`、任何 Tika jar 在本机扫描范围内**实测都不存在**；
`olefile` 在三个解释器里都**未安装**。是否把它登记为处置行、如何绑定（它随 Git 发行而来，
不是本机自装的工具链登记项），下一片单独裁。

**验证（度量口径）**：Rust 全 workspace `cargo test --workspace --offline`
**123 组 ok / 503 passed / 0 failed**（本切片前一次全量是 500 passed，增量为
`nested_container_budget` 1 项 + `mail_member_chain` 1 项 + `source_members_api` 1 项）；
`cargo fmt --all --check` PASS；
新增 `crates/archeaxis-application/tests/nested_container_budget.rs` 1 passed、
`crates/archeaxis-application/tests/mail_member_chain.rs` 3 passed、
`crates/archeaxis-application/tests/archive_member_formats.rs` 1 passed、
`crates/archeaxis-api/tests/source_members_api.rs` 3 passed、
`tests/workers/test_mail_attachment_members.py` 11 passed；
`check_format_matrix.py` exit 0（0 complete / 15 partial / 1 custody only，F13/F15 两行的
required_output 逐字未动，只改 status 之外的字段）；`check_document_authority.py` exit 0；
Python 全量 4256 passed, 30 skipped, 14 warnings, 166 subtests passed in 438.62s (0:07:18)。

**回滚**：`git revert` 本切片提交即可（Core 深度决策 + API 字段 + worker 措辞 + 矩阵两行 +
夹具与测试同属一次改动）；夹具改为真容器是**测试数据**变更，revert 后回到假字节 + 旧 6 项断言。


## 提交范围核对：5e5d102b 的消息低估了自己携带的内容（2026-10-07 实测）

**这条是被核出来的，不是猜的。** 该提交的标题与正文只讲一件事：把 `urllib3`/`soupsieve`
升到 pip-audit 点名的修复版本，并按 `79332377` 的旧例改发布清单的锁摘要。
按 `git show --numstat 5e5d102b` 逐文件实测，它同时携带了：
- **Rust Core（archeaxis-migration）**：合计 +556 行 — `crates/archeaxis-migration/src/lib.rs` +290/-0; `crates/archeaxis-migration/tests/selective_legacy_stage.rs` +241/-0; `crates/archeaxis-migration/examples/selective_stage.rs` +25/-0
- **Python 测试与门禁**：合计 +62 行 — `tests/workflow/test_dependency_scan_config.py` +62/-0
- **CI 工作流**：合计 +9 行 — `.github/workflows/ci.yml` +9/-4
- **锁文件与发布清单**：合计 +8 行 — `uv.lock` +7/-7; `app/release-manifest.json` +1/-1

**消息里一个路径都没点到、且不属锁文件/记录文件的**：
- `crates/archeaxis-migration/src/lib.rs` +290/-0
- `crates/archeaxis-migration/tests/selective_legacy_stage.rs` +241/-0
- `tests/workflow/test_dependency_scan_config.py` +62/-0
- `crates/archeaxis-migration/examples/selective_stage.rs` +25/-0
- `.github/workflows/ci.yml` +9/-4
- `app/release-manifest.json` +1/-1

**为什么这条要记**：`crates/archeaxis-migration` 是迁移车道，CI 里跑它的作业（migration-targeted）
与依赖扫描（pip-audit / security-targeted）是两件事；一次以“升依赖”为名的提交把 556 行 Rust 迁移代码、
它自己的 241 行测试、25 行 example、CI 工作流 +9/-4 行与依赖扫描测试 +62 行塞进同一提交，
评审人按标题看不到它，回滚也只能整块回——这与本项目“一次改动、一个可回滚提交”的要求相反。
该提交里的迁移代码本身是验证过的（`cargo test -p archeaxis-migration --tests --offline` 六套件
27 passed，见同快照 `migration_crate` 条目），**问题只在范围声明，不在质量**。

**处置**：不改写历史（已推送，不 force push）。以此为界采纳自我约束：后续每次提交在正文里
逐一点名被改动的权威文件（矩阵行、HTTP 契约、供给链台账、发布清单、CI 工作流），
依赖与许可变更写进标题，同一提交不混做“依赖升级 + Core 功能”。
同一规则已写入审计快照的 `checkpoint.open`，供后续切片自检。


## 遗留二进制引擎的本机实测（2026-10-07，只测不装）

**`.doc` 有候选**：`C:\Program Files\Git\mingw64\bin\antiword.exe` 实测存在，284,448 字节，sha256 `d30a37489c64ada474d8d5aa5abb0778a6955d3ce6cdbb7c8c659e37b89d3da9`，自报 `Version: 0.37  (21 Oct 2005)`、`Status: GNU General Public License`、`Author: (C) 1998-2005 Adri van Os`；字符映射表目录 `C:\Program Files\Git\mingw64\share\antiword` 实测含 30 个 `*.txt`（含 `UTF-8.txt`）。它能读 Word 97 的 `.doc`，**不能读 `.ppt`**；它是 **Git for Windows 自带的 mingw64 包**，不是本机自装的工具链登记项，因此**尚未**写进 `config/environment/capability-requirements.yaml`，也**尚未**进供给链台账——绑定它需要一次单独的处置决定（登记为外置引擎并规定探针与环境变量，还是仅按 `PATH` 探测）。在它被登记之前，产品不得假设它存在：当前 `.doc` 仍是**具名拒绝**，这是事实而非缺口修复。

**`.ppt` 与 Tika 侧车在本机不可达**：JVM 实测缺席——`C:\Program Files\Java`、`C:\Program Files\Eclipse Adoptium`、`C:\Program Files\Microsoft\jdk`、`D:\All projects\OS External Configuration\10-toolchains\java` 均无内容，`where java` 退出码 1（where.exe 的“未找到匹配文件”消息以 GBK 控制台编码返回，此处不复写其乱码字节）；扫描范围内也没有任何 Tika jar。台账 A010（Apache Tika, `document-legacy`, SIDECAR, qualification `[source]`）因此**不能**在本机升档：升它需要装系统级 Java，而本轮边界明确禁止装系统级软件。结论写死：`.ppt` 在本地没有合法读取路径，除非引入一个不需要 JVM 的读取器并另行验证——**不做无样本的自造实现**。

**这条记录的作用**：把两条反复被引用却没有度量的判断（`.doc`/`.ppt` 无 reader、Tika 待装）换成有哈希、有字节数、有退出码的实测，并标明仍未决的是**处置**而不是**是否存在**。


## `.doc` 切片：把具名拒绝换成"按名路由 + 探针式外部 sidecar"（2026-10-07）

**这一刀改变的是证据的性质，不只是多了一个格式。** `.doc` 此前在四层表里都**不命名**，
所以它是具名拒绝；现在它命名，并交给一个**探针式外部二进制**（antiword）去读。
关键不是"能读了"，而是**产品不再假装依赖存在**：
解析顺序 `ARCHEAXIS_ANTIWORD_CMD` → 已声明的能力清单 → `PATH`；
拿到候选以后先问它"你是谁"（`-h` 里必须自报 `MS-Word`），答不上来就当不是引擎；
配置了却指向不存在的路径 → **具名失败，绝不改用别的二进制**（这正是 `tool_paths` 自己写的规则）；
解析不到 → 作业以 `doc engine missing (…)` 失败，**不投影任何东西**。

**踩到的坑全部来自实测，不是想象**（一条一条都进了代码注释或用例）：
1. `-m <绝对路径>` 被 antiword **截到 32 字符**再接 `.txt` —— 53 字符的路径变成
   `C:/Program Files/Git/mingw64/sha.txt` 并退出 1。所以产品**不请求映射文件**，
   用引擎默认映射；实测默认映射还会**保留 `’`（U+2019）**，而 `-m UTF-8.txt` 把它压平成 ASCII。
2. **批处理退出码不可信**：一份有效 + 一份无效 + 一份有效的混合批次**整体退出 0**，
   错误只在 stderr。因此一律**一个进程读一个文件**（用例断言命令里只有一个文档参数）。
3. `-x db` 对**不是 Word 的**输入仍然吐出 164 字节 XML 前导再退出 1 —— 有输出不等于读到了。
   本切片只用 `-t`，且以**退出码为准**。
4. 引擎把**输入绝对路径回显**在拒绝消息里（`<path> is not a Word Document.`）。
   收据里剥掉路径前缀，只留引擎自己的理由：存下来的证据不该带着这台主机的目录结构。

**夹具的证据强度换了一次**：`.xls` 的夹具是项目自造（`xlwt` 一次性写出，我已在账本里认过这一点）；
`.doc` 用**真的 Word 文档**——Apache Tika 3.3.2（钉到 commit `b8a6916e…`）的
`testWORD.doc`，32,768 字节，sha256 `5ca19b67…`，git blob `c1f4f3d0…`，
OLE2 魔数 `D0CF11E0A1B11AE1`、Word97 `nFib 0x00C1`、注册块 `Word.Document.8`。
它在 Apache-2.0 下带署名再分发，出处与哈希写进 `tests/fixtures/golden/manifest.json` 与
`THIRD_PARTY_NOTICES.md`。**这是对我此前被纠正的"自造夹具"问题的一次实质改正。**

**我改了两处已提交断言**（前提正是本切片替换的规则）：
`office_job_end_to_end.rs` 与 `xls_member_chain.rs` 都把 `old.doc` 从"必须拒名"里移出，
`.ppt` 保留拒绝；两处都新增 `.doc` **必须**命名为 `application/msword`、且**不得**当纯文本读。
`route_capabilities.rs` 新增按内容断言；另在 Python 侧新增**首表可达性守卫**——
读 `attempts.rs` 源码，要求 `"doc" => "application/msword"` 存在、
且 `"doc"` **不出现在它之前的任何分支**里。这是 `.py` 那次"四张表都说支持、实际被更早分支遮蔽"
事故的制度化，不是装饰。

**我自己的两处缺陷，写在这里**：
1. 更新 golden manifest 时我又用 `json.dumps` 整档重写，导致 **63 行无关重排**
   （把别的紧凑 `expected` 对象展开）。已改回**按行插入**并复验 `git diff --numstat` 为
   **+12/-0**。这与本账本此前记过的"整文件重写"教训同类，属于复发，不是新认识。
2. 探针用例第一版用一个不存在的配置路径去测"引擎缺失"，与我刚立的"配置的绝对路径不存在即具名失败"
   互相矛盾——修的是测试（改用 tmp 下真实存在的假二进制），**不是放宽产品行为**。

**仍未闭合，不粉饰**：
- antiword **没有**写进 `config/environment/capability-requirements.yaml`，也**没有**进供给链台账。
  原因是**上游身份没实测到**：`packages.msys2.org` 的搜索 API 对 `antiword` 返回空结果、
  包页面返回 307 重定向，我没有拿到可信的 canonical URL / 版本 / 许可版本，
  因此**不写台账行**（编一个来源比缺一行更糟）。绑定它需要的下一步是把包身份钉死，
  再决定是否把二进制放进外置工具库。
- `.ppt` 在这台机器上**没有合法读取路径**：唯一候选是 JVM 侧车，而本机无 JVM 且本轮不许装系统级软件。
- CI 侧车缺席 → `test_the_real_sidecar_reads_the_real_word_document` 在无 antiword 的运行环境里
  会**skip**；skip 是关于主机的陈述，不是通过。本机这次它是**真跑过**的（12 passed 里含它）。
- FMT-21 逐扩展名真人验收仍 NOT_RUN；`.doc` 的投影是引擎文本，**没有**标题级/样式/图片信息，
  也不宣称有。

**验证（度量口径）**：Rust `cargo test --workspace --offline` → cargo test --workspace --offline: 123 suites ok / 503 passed / 0 failed；
Python 全量 `dev.py --pytest tests -q` → 4270 passed, 30 skipped, 14 warnings, 166 subtests passed in 423.30s (0:07:03)；
新增 `tests/workers/test_doc_engine.py` **14 passed**（含真实引擎读真实 Word 文档那一项，
以及一条走**真实 transport** 的端到端用例：输出三件套齐、`params.worker_structure` 保留 24 条、
transport 自己派生的 60 条行锚其中 24 条非空——两者数量与含义都不同，收据里写明谁是谁）；
`route_capabilities.rs` 3 passed、`office_job_end_to_end.rs` 8 passed、`xls_member_chain.rs` 2 passed；
媒体/路由/传输选择集 248 passed 1 skipped；golden/fixture/notices 选择集 77 passed 3 skipped；
`check_format_matrix.py` exit 0（F14 只改 implemented_now/gap/evidence，
required_output 与 formats 逐字未动）；`cargo fmt --all --check` **PASS**（0 处 diff）。

**回滚**：revert 本切片提交即可（worker 探针 + 四层命名 + 夹具与 manifest 行 +  notices 段 +
两处断言更新同属一次改动）；回滚后 `.doc` 回到具名拒绝的旧状态。


## 寻址层切片：worker 自己描述的位置成为可验证锚点（2026-10-07）

**这条横跨 F05/F07/F08/F09/F12 的缺口是同一句话**："结构是**被报告的事实**，不是**寻址层**"。
它此前被我反复写进"本切片刻意未动"，因为动它要动锚点契约。这一刀动了，但**是加性的**：

- 锚点存储本来就把 `position` 当作**没有 schema 的不透明 JSON**
  （`anchors(anchor_id, source_id, source_revision, position)`，`position` 无 CHECK、无 kind 词表），
  所以**不需要迁表、不需要新枚举**；
- 新增的是**第四种 position 类型** `worker_structure`：`{type, job_id, attempt, kind, path[]}` + checksum；
- 验证条件全部落在**已经存在**的数据上：该 attempt 必须是这个 source 的**最新 succeeded**
  （有更新的尝试即拒）；请求线里 `inputs[0].sha256` 必须等于所声明的 revision；
  收据的 `params.worker_structure` 必须把这对 `kind`+`path` **恰好命名一次**；
  它记录的 span 在**同一次尝试的 text 输出**里切出的字节必须 hash 成所声明的 checksum，且不得是纯空白。

**为什么不重算任何已有锚点**：`anchor_id` 由 `source|revision|position_json` 派生，
knowledge 的 `receipt_hash` 又混入 `anchor_id`。因此我**只加类型、不改任何已有 position 的形状**——
改形状会静默地让历史锚与知识收据的哈希全部失效，那才是真正的破坏性变更。

**刻意不吹大的四条边界**：
1. span 是 worker 自己报的。锚点证明的是"这段文字确实在这份 projection 的这个位置"，
   **不是**独立推出的页号；
2. F13 的 ODF/EPUB/邮件位置在 `params.format.locations` 里，**不在** `worker_structure` 里，
   所以 F13 与 F01 的旧措辞**没有被顺手改掉**——写记录的脚本里放了断言防止我越界
   （`assert "navigation level" in rows["F13"]["gap"]`、`assert "anchors remain line based" in rows["F01"]["gap"]`）；
3. 界面层没有消费它（前端按 Owner 指示暂停），所以这条目前**只在 HTTP 边界成立**；
4. 表格里"单个 cell"仍不是一个位置（worker 报的是 `sheet_row`）。

**这些用例证明了什么、没证明什么（重要）**：种入数据用的是**手写的 `job_attempts`/`job_outputs` 行**
（按契约形状写请求线、text 输出、canonical 行锚与 loss 收据），所以它们证明的是
**锚点契约本身**——接受条件、拒绝条件与不重算旧锚的边界；
"把某个真实 worker 的真实结构一路接到真实锚点"的端到端一条**仍未做**，不写成已完成。

**验证（度量口径）**：新增 `crates/archeaxis-api/tests/structure_anchor_api.rs` **5 passed**：
段落/标题可寻址；sheet_row、slide、text_node、cue、pdf_page 五种族路径用同一机制可寻址；
路径被命名两次 → 拒；span 只含换行 → 拒；路径不存在 → 拒；checksum 不符 → 拒；
出现更新的 succeeded 尝试后旧定位 → 拒；不带 checksum → 仍**存下**且写 `unverified`。
既有锚契约没有被削弱：`evidence_anchors_api.rs` 4 passed、`contract_constant_fields.rs` 5 passed。
Rust `cargo test --workspace --offline` → 124 suites ok / 508 passed / 0 failed；
`cargo fmt --all --check` PASS；
`tests/maintenance + tests/workflow` **282 passed, 2 skipped, 2 subtests passed in 63.44s (0:01:03)**；
`check_format_matrix.py` exit 0（**只改五行 gap 与五行 evidence 列表**，
required_output / formats / release_scope 逐字未动，计数仍 0 complete / 15 partial / 1 custody only）；
`check_document_authority.py` 与 `check_path_conventions.py` rc 0。

**契约文档**：`POST /api/v1/sources/(:source_id)/anchors` 那一行原先只写 "Anchor creation."，
现在逐字列出四种 position 类型（`text`/`time`/`epub`/`worker_structure`）与各自验证条件，
以及 `400` 与 `unverified` 的语义——加性变更不留隐式契约。

**回滚**：revert 本切片提交即可（verifier 分支 + 新 suite + 五行矩阵 gap/evidence + 契约一行）。


## 锚点切片的两条补充：一个我写错的度量单位，和一条我自己欠下的端到端（2026-10-07）

**A. 度量单位写错（保守方向的错，但理由是错的）**
`worker_structure` 的 `char_start`/`char_end` 是**字符**偏移——那是 Python 侧 `str` 索引的语义。
我第一版 verifier 用 Rust 的 `&text[a..b]`，而 Rust 的字符串切片按**字节**。
后果：**任何非拉丁文本的位置都会被"落在码点中间"为由拒掉**。
失败方向是保守的（不会误接受一个假位置），但**拒绝的理由是错的**，
而对一个中文文档来说等于"这个位置不存在"。
现在按字符切片，并要求切出的**字符数与跨度相符**；新增用例用中文段落钉住两个方向：
`星环 知识平台` 是 7 个字符、19 个字节，按字符的 digest **必须通过**，
按字节截出来的那串东西的 digest **必须被拒**——单位不是可以商量的余地。
**这条必须写清**：是我在写端到端用例时自己发现的，不是评审指出的，也不是 CI 报的。

**B. 上一节我承认没做的那一条，现在做了**
`crates/archeaxis-api/tests/structure_anchor_live_worker.rs`：用真实 `Executor` 跑真实 worker
（仓库里已提交的 DOCX 夹具 → `office.structure` → 真实 `job_outputs`），
然后**读回 worker 自己报的第一个位置**——`kind`、`path`、`char_start/char_end` 一律不硬编码——
经 HTTP 建锚并校验 digest；再用一段"别处来的文本"的 digest 断言必须 `400`。
它证明的是**约定的连通性**：将来任何一侧改了 span 约定而另一侧不动，这条会红。
F07 的 evidence 列表同期加上这条（矩阵里只改 evidence 数组一处，required_output 逐字未动）。

**验证（度量口径）**：`structure_anchor_api.rs` 由 5 → **6 passed**（新增中文段落用例）；
新文件 `structure_anchor_live_worker.rs` **1 passed**；
`cargo test --workspace --offline` → 125 suites ok / 510 passed / 0 failed；
`cargo fmt --all --check` 在提交前为 **PASS**（中途 9 处 diff 是我手写对齐，格式化归零）。

**边界没有变**：span 仍是 worker 自报的（锚点证明"这段文字确实在这个位置"，不是独立推出的页号）；
`params.format.locations` 那一族（F13 的 ODF/EPUB/邮件、F01 的符号）仍**未**并入；
界面层没有消费（前端按 Owner 指示暂停）。


## 更正我自己上一条"上游身份没实测到"（2026-10-07，同日）

上一条记录写着："packages.msys2.org 搜索 API 返回空结果、包页面 307，我**没有**拿到可信的
canonical URL / 版本 / 许可版本，因此**不写台账行**"。**前半句是查询写错了参数**：
那个 API 要的是 `query=` 而不是 `q=`，我第一次发出去的请求里 `query` 是空的
（返回体里能看到 `"query":""`），所以"搜不到"是**我的探针缺陷**，不是上游不存在。
改用正确参数后实测得到：包 `mingw-w64-antiword`，版本 **0.37-3**，
许可 **['GPL3+']**，仓库 clang64, clangarm64, ucrt64，
打包源 `https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-antiword`，索引给出的上游页 `http://www.winfield.demon.nl/`（本次未抓取，故只记为索引所述）。

**因此台账补了一行 A025**（处置 `SIDECAR`、档位 `installed`）：
证据里写的是本机实测的二进制 `284,448` 字节 / sha256 `d30a37489c64ada4…` /
30 个映射文件，以及三条塑造了代码的实测坑（映射绝对路径被截到 32 字符、
批处理退出码会盖住被拒文件、引擎把输入路径回显进自己的拒绝消息）。
**"不编一个来源"这个判断本身保留**——错的是我当时据以下判断的那次探测。

**仍未闭合的边界照实写**：A025 说的是**处置**，不是**绑定**。
`config/environment/capability-requirements.yaml` 里**依然没有** antiword 条目，
所以现在解析顺序里的第二档（已声明清单）永远是空的，实际生效的只有环境变量与 `PATH`；
把它放进外置工具根需要该清单三个读取方一致，那是单独一刀。


## 寻址层第二族：`params.format.locations` 的位置也可以被锚定（2026-10-07）

上一节我明确写着"locations 那一族（F13 的 ODF/EPUB/邮件、F01 的符号）**未**并入"。这一刀把它接上，
用的仍是**加性**办法：新增第五种 position 类型 `format_location`，验证条件全部落在已有数据上——
该 attempt 是这个 source revision 的**最新 succeeded**、请求线里的 `inputs[0].sha256` 等于声明的
revision、收据 `params.format.locations` 里 kind+path **恰好命中一次**、被报告的值**确实出现在
这一次的投影文本里**且 digest 与声明一致。

**两处刻意的"不放宽"**：
1. **歧义就拒**。一个 Python 源里所有 import 共用 `path=/symbols/import`；不按更多字段收窄时，
   这个 path 什么也没指。定位符因此可以带一个 `where`，但只允许**用收据已经报过的字段**
   （如 `name`）做**精确相等**收窄；我没有发明序号、行号或任何新判别器。收窄不成立就 `400`，
   而不是挑一个看起来对的。用例把三侧都钉住：不收窄被拒、按 `name` 收窄通过、
   按收据里没有的 `name` 收窄仍被拒。
2. **值必须真在投影里**。`xml_path` 一条被我故意写成"收据说有、正文里没有"，它必须被拒——
   这条防的是"结构漂移被当成位置"。

**这一族与上一族的差别被写进契约**：`worker_structure` 校验**字符跨度**，`format_location` 校验
**值本身**（那些 worker 报的是值而不是跨度）。契约里 `POST /sources/(:source_id)/anchors` 那一行
现在把五种类型各自的验证条件逐字列出。

**度量口径**：新增 `crates/archeaxis-api/tests/format_location_anchor_api.rs` **4 passed**；
`cargo test --workspace --offline` → 126 suites ok / 514 passed / 0 failed；`cargo fmt --all --check` PASS。
矩阵只改 **F01 与 F13 的 gap 措辞与 evidence 列表**（`required_output` 逐字未动，计数仍 0/15/1）；
`check_format_matrix.py`、`check_document_authority.py` exit 0。

**仍未闭合**：锚点证明的是"这个值确实在这份投影里、这条收据确实这么命名它"，
**不是**独立推出的页号或单元格坐标语义；locations 列表本身受 worker 的上限截断，
被截掉的位置不可寻址；界面层没有消费（前端按 Owner 指示暂停）。


## F15 的"未闭合"被改写得更准（2026-10-07，查证后）

矩阵原文写"被读取的成员**仍未升级为知识**"。这句话容易被读成"没有升级路径"。
**实测不是这样**：产品**已经有**这条路径——`POST /api/v1/knowledge-items/from-transform`，
而且它是严格的：必须是 `human` 行为者（机器行为者 `403`），
`quote` 必须与**已持久化的 transform 文本**在给定 UTF-16 偏移处逐字相符，
否则 `400`；产出的对象状态是 `candidate` 且 `requires_human_review: true`——
也就是说它**从不**把一次抽取自动升格为真理。

**真正缺的是链**：没有任何一次运行把"容器成员 → 已读 → 经这条路由升为 Candidate"走完。
所以 F15 的剩余项现在按事实写成三段：路径存在、路径严格、**从成员出发的端到端一条未跑**。
这个区别决定下一刀是**写一条新路由**（错）还是**把已有的三段接起来证明**（对）。
矩阵只改这一句 gap 的措辞；`status` 仍是 `partial`，`required_output` 逐字未动。


## 容器成员 → 已读 → 知识 Candidate 这条链跑通了（2026-10-07）

上一刀我只把 F15 的措辞改准（"路径存在、路径严格、**链未跑**"）。这一刀把链跑了：
`crates/archeaxis-api/tests/member_to_knowledge_chain.rs` 用**真实**执行器与**真实** worker——
真 ZIP 被 `archive.inventory` 展开 → 成员 `notes/index.md` 成为自己的 source 并取得**按名选定**的
text 作业 → 该作业执行后 `transforms` 里有它的读数 → 以 **human** 行为者调用
`POST /api/v1/knowledge-items/from-transform`，把读数里 `"6371 km"` 这一段按 **UTF-16 偏移**引为 quote
升为对象。

**它证明了什么，就只写什么**：
- 产物是 `status=candidate` 且 `requires_human_review=true`，锚点 id 已铸造；
  **升为被接受的知识仍是人的动作，产品不能替人做**——这一条我没验，也就不写；
- 晋升**不打断来源关系**：成员的 origin 引用在晋升之后仍是
  `{容器 source_id}#notes/index.md`，且仍然 `readable`；
- 两道拒绝都成立：**machine 行为者 `403`**；把 quote 换成"偏移处不是这段话"（`9312 km`）
  → `400`，拒绝消息点名是 quote 与持久化 transform 不符。
  这两道就是"抽取不会被自动升格为真理"的机制保证，不是我的口头承诺。

**F15 仍 partial**，理由照实列：没有界面入口（前端按 Owner 指示暂停）；关系仍是 origin 引用
而不是可查询的一等边；驱动是脚本；超上限成员不展开；驱动认不出类型的文件仍不带作业。

**度量口径**：`cargo test --workspace --offline` → 127 suites ok / 515 passed / 0 failed（新套件 1 passed，首跑即过）；
`cargo fmt --all --check` PASS；矩阵只改 F15 的 gap 一句 + evidence 一项，`required_output` 逐字未动。

**回滚**：revert 测试文件那一次提交即可（链本身只是断言，不改行为）。

## 一整份状态在重启后仍是同一批身份（2026-10-07）

**为什么单独做这一刀**：格式那几刀都改了锚点身份的来源——`worker_structure`/`format_location`
是**新增**的 position 类型，而 anchor_id 与 `knowledge.receipt_hash` 都是从**存下来的 position 字符串**
派生的。位置 JSON 一旦被重新规范化（键序变动、Unicode 转义、空白压缩），所有指向它的引用都会
**安静地改指到别处**。没有一条测试断言过"关掉存储、再打开两次，同一条记录还是同一条"。

**新增套件**：`crates/archeaxis-api/tests/state_identity_restart.rs`（1 个测试
`a_whole_state_keeps_every_identity_through_two_reopens`）。它一次写入本项目**每一类**所有权记录，
然后经**发布这些身份的表面**读回三遍（写连接已释放后一遍，之后**刻意**再开两次）：

- 两级容器关系：外层包 → 成员 `notes/index.md` 成为自己的 source → 成员里的 `inner/note.md`
  又是第三层 source；读回经 `GET /sources/:id/members` 断言成员仍是那个 `source_id`、
  仍 `readable`、`origin_ref` 仍是 `{容器}#notes/index.md`；第二层的 `origin_ref` 经 SQL 读回；
- transform 文本（经 `transforms.text` 逐字比对）；
- **三种 position 类型**：`worker_structure`、`format_location`、`text`——三者 id 都要在
  `GET /sources/:id/anchors` 里仍列着，且存储里的 position JSON **逐字仍含** `"worker_structure"`
  与 `paragraph-2`（没有被改写）；
- 人的候选：`GET /knowledge-items/:id/v3` 的序列化里仍出现它自己的锚点 id；
- 机器收据：`machine_tasks` 的 `outcome=failed` 与失败文本里的 "nesting budget" 仍在；
- 原始字节：成员 source 的 `sha256` 与写入时一致。

**顺带钉住的一条去重语义**：同一 (source, revision, position) 再写一次得到的是**同一个 anchor_id**，
不是第二条记录——`INSERT OR IGNORE` + 内容派生 id 的组合，测试直接断言返回值相等。

**这条测试不声称什么**（写死，避免以后被误读）：它**不**证明"经 HTTP 路由写的 position 与经
领域函数写的 position 派生同一个 id"。路由会把 `location_status`（有校验和时还有 `checksum`）
**写进** position，所以那本来就是不同的字符串、不同的身份。要验那一条得走 `structure_anchor_api.rs`
那类路由测试，而它验的是拒绝与定位，不是重启。

**度量口径**（数字由脚本从该次运行的日志解析，非手抄）：
`scripts/runtime/dev.py -- scripts/ci/cargo_test.bat test --workspace --offline`
→ **128 个 `test result:` 行合计 516 passed / 0 failed / 0 ignored**
（上一条记录写的是 127 行 / 515 passed，即本套件加入之前；+1 行 +1 passed 恰为本刀新增的那一个测试，
对得上）；日志 `.project-local/task-runtime/workspace-test-20261007-final.log`；`cargo fmt --all --check` PASS。
新套件本身首跑即过（`-p archeaxis-api --test state_identity_restart` → 1 passed / 0 failed），
两处编译警告（未使用的 `post` 助手、多余的 `mut`）清掉后复跑仍 1 passed；
上面那一次全量运行**在清警告之后**启动，所以数字绑定的是最终提交的字节。
另记一条口径缺陷与修正：本仓以往把 cargo 输出称为"127 suites"，实为 `Running` 行 120 条 +
`test result:` 行 128 条两种计数，以后按 `test result:` 行数报，不再混称。

**PR #161 读回**（head `235f6eda`，`gh pr checks` 39 条）：**无任何 failure**；
`cargo-test`/`rust-vnext`/`lint`/`test (3.12)`/`a0-gates` 全 pass；
`mergeable=MERGEABLE`，`mergeStateStatus=UNSTABLE`——成因为一条 `desktop-build` 仍 pending
加多条按路径/标签跳过的 `skipping`。**按边界"非 CLEAN 不合并"，本轮不合并，也不做任何提权绕过。**

**回滚**：revert 这一次提交（测试文件 + 账本/快照两段文字）即可；未改任何产品行为。

## antiword 从"探测到"变成"声明绑定"（2026-10-07）

**这一刀的前提是我自己写下的一条未完成**：F14 的缺口原话是"sidecar 尚未绑定在
`config/environment/capability-requirements.yaml` 或 `docs/truth/SUPPLY_CHAIN_LEDGER.json` 里，
所以处置未定"。也就是说 `.doc` 能读，靠的是本机恰好有个 Git-for-Windows 副本在 `PATH` 上——
**盘上有 ≠ 绑定**，这在别处已经是我的教训。

**测出来的硬事实（全部 stripped PATH 实测，2026-10-07）**：
- 复制出去的 `antiword.exe` 与源**字节相同**（284,448 B，sha256 `d30a37489c64ada474d8d5aa5abb0778a6955d3ce6cdbb7c8c659e37b89d3da9`），
  `-h` 也能自报身份，但**读文档直接失败**：exit 1、零输出、
  `I can't open your mapping file (UTF-8.txt)`——它只到 `$HOME/.antiword` 与 `/usr/share/antiword` 找映射表；
- `-m` 传绝对路径**不能用**：引擎把名字截断后再去那两处找（实测报出被截断的名字），仍失败；
- 把 `HOME` 指向一个含 `.antiword/*.txt` 的目录，**同一份复制体读取真样本成功**
  （exit 0，1,218 字符严格 UTF-8，首行 `Sample Word Document Title`）。

所以绑定必须是**两条一起**：只声明二进制会得到"解析成功而读取失败"。

**做了什么**：
- 在外置工具根就位 `10-toolchains/antiword/antiword.exe` ＋ `10-toolchains/antiword/.antiword/`
  （30 个映射表，306,272 B，含 `UTF-8.txt`）；放置脚本先断言目标目录不存在再写，未删除任何东西；
- `capability-requirements.yaml` 新增 `antiword` 与 `antiword-mappings` 两条 engines
  （`local_only: true`、`install_method: system`、`license: GPL-3.0-or-later`、source_url 用 A025 里
  已登记的 MSYS2 打包页，不另编 URL）；
- `worker_office._antiword_mapping_home()`：解析 `antiword-mappings`，目录名必须是 `.antiword`，
  把其父目录作为 HOME 交给引擎，并把用了哪个 HOME 写进损失收据的 `mapping_home`；
  **没有声明就不碰环境**（原地安装的引擎继续用自己的前缀，CI 上也就不存在伪绑定）；
- 重新生成 `config/environment/external-resources-index.json`：两条都是 `exists: true`。
  这里要如实记一条**我自己的操作失误**：我先用 `dev.py -- <script.py>` 直接跑生成器，得到
  `[WinError 193] %1 不是有效的 Win32 应用程序`（exit 2，什么都没生成）；实际生成索引的是
  `tests/workflow/test_external_resources_index.py` 内部对生成器的调用。**先怀疑仪器，再下结论**
  ——这次是仪器的用法，不是数据的毛病；
- A025 台账行的 evidence/decision 重写为"已按声明绑定"，`qualification` **没有**升档（仍是
  `["installed"]`——绑定改变的是解析方式，不是资格层级）；
- F14 矩阵的 `gap` 删掉"尚未绑定"那句、换成绑定后的真实剩余（外部二进制、不随项目分发、
  Git 更新不同步此副本、无声明的主机仍报引擎缺失）；`status` 仍 `partial`，`required_output` 逐字未动；
- `docs/environment/EXTERNAL_DEPENDENCIES.md` 同步一行（清单与人类可读文档必须两处一致）。

**新增 4 条测试**（`tests/workers/test_doc_engine.py` 14 → 18）：声明了 `.antiword` 时 HOME
确实被交出且收据记名；什么都没声明时**环境一字不动**；声明的目录不叫 `.antiword` 就**不去猜** HOME；
以及一条真正走声明的对偶测试——两条声明都在时，用**声明里的二进制＋声明里的映射**读真 Word 文件，
exit 0 且出文，缺任一即按解析器的原话 skip（skip 是这台机器的属性，不是 PASS）。

**度量口径**：`tests/workers/test_doc_engine.py` → 18 passed；
全量 Python 套件 → 4274 passed, 30 skipped, 14 warnings, 166 subtests passed in 423.04s (0:07:03)（日志 `.project-local/task-runtime/py-full-20261007-final.log`）。
**这条数字绑的是哪一版字节**：`_doc_text` 的 env 传递在套件第一次跑到 9% 时被我改写了一次
（把 `**({"env": env} if env else {})` 换成显式的 kwargs 组装，行为不变），
所以我把整套**重跑了一遍**，上面这个 4274 passed, 30 skipped, 14 warnings, 166 subtests passed in 423.04s (0:07:03) 来自重跑那一次，测的是最终提交的字节；
两次计数一致（4274 passed / 30 skipped / 166 subtests），
这本身就是"该改写没有改变行为"的证据——脚本会比对两份日志的这三个数，不一致就拒绝记录。
`tests/workflow/test_capability_requirements_manifest.py + test_external_resources_index.py +
test_environment_registry.py` → 12 passed；`tests/test_mfx001_supply_chain_ledger.py` → 5 passed；
矩阵门禁（与 CI 同样的 `--matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json`）exit 0，
16 组 / 0 complete / 15 partial / 1 custody-only。Rust 侧本轮未改，故未重跑。

**PR #161 在 `37d87487` 的读回**：`mergeable=MERGEABLE`，`mergeStateStatus=UNSTABLE`，
39 条里除一条 `installer-lifecycle` 仍 pending 外全部 pass 或按路径跳过，**无 failure**；
仍按"非 CLEAN 不合并"不动。

**仍未闭合，照实写**：`probe` 这一栏在宿主清点里会是 `available: true, probe: probe_failed`——
通用探针给命令追加 `--version`，而 antiword 用 exit 1 的用法文本回应，这不是引擎坏了，也不是绑定失败，
是探针的形状容纳不下这个引擎；`.ppt` 仍无 JVM 路径；FMT-21 的逐扩展真人验收仍 NOT_RUN。

**回滚**：revert 这一次提交即撤销声明、worker 的 HOME 通道与记录；外置根里那两个目录是本机放置，
删除需要单独授权（本轮不删）。

## F03 的"没有浏览器"是假的：渲染通道接通了（2026-10-07）

**被推翻的判断**：账本与矩阵里 F03 的缺口写的是 `there is still no browser`。实测本机
`ArcheAxis-Knowledge-OS-ci-venv` 里 **playwright 1.61.0 已安装**（且 `pyproject.toml` 两个依赖组
已声明 `playwright>=1.61,<1.62`、`uv.lock` 已锁——**没有新增依赖**），
`C:\Users\ALEX\AppData\Local\ms-playwright` 里有 `chromium-1208/1228` 与两个 headless shell；
启动得到 **Chrome 149.0.7827.55**（`chromium-1228/chrome-win64/chrome.exe`）。
同一份脚本页：JS 开启时 `#rendered-only` 的文本可读，**关闭 JS 后该节点是 None**——
所以"渲染后才有"与"服务端给了什么"是两件事，这一点是被测出来的，不是被说出来的。

**做了一条什么通道**：
- `worker_webpage.py` 的 `render()`：先按原有边界做**取字节**（策略、上限、时间戳都不变），
  再用本机无头 chromium 打开同一 URL、按预算滚到底，把**渲染后的 DOM 与可见文本**写在服务端字节旁边，
  收据记浏览器构建号、滚动覆盖（`scrolls / final_scroll_height / height_stabilized / budget_exhausted`）、
  两个摘要，以及 `served_vs_rendered.same_digest` 是否为假；
- **地址策略跑三次**：请求主机、重定向落点主机、以及浏览器**实际停在**的主机。
  浏览器会自己跟随重定向，不询问这个 worker，所以取字节时放行不等于浏览器落地时放行；
- 渲染出的 DOM 仍受 `MAX_BYTES` 约束，超限就**不写任何渲染件**；
- 起不来的浏览器是**具名拒绝**，绝不把取字节的结果改名当成渲染；
- `scripts/ingest/url_snapshot.py --render [--scroll-limit N]`：导入的是渲染文档，
  同时把服务端摘要的 sha256/字节数一并记在凭证里（`mode: rendered`）。

**踩到并修掉的两个我自己的坑（如实记）**：
1. 第一版真机测试**跳过**：`PLAYWRIGHT_BROWSERS_PATH` 被会话指到项目内
   `.project-local/cache/playwright`，而那里**没有** `chromium_headless_shell-1228`，
   Playwright 只查自己的注册表。修法是给引擎一个**具名环境变量**
   （`ARCHEAXIS_CHROMIUM_CMD`，形状与 antiword 一致，解析顺序 env→注册表，
   指到不存在的文件就是具名错误，绝不猜），而不是偷偷改全局环境或再下载一份浏览器；
2. 第一版断言**失败**：我用"标记串不在服务端 HTML 里"证明差异，而标记就写在内联 `<script>` 文本里，
   所以那句话本来就是假的。把样本改成**文本由第二个请求 `/late` 交付**（只有执行了脚本的页面才会去取），
   服务端字节里任何位置都不含该串，断言才真正成立。这两次都是**样本/仪器的错，不是产品的错**，
   改的是测试与解析入口，没改产品规则。

**新增测试**：`tests/workers/test_webpage_render.py` 11 passed（含那条真机证明），
`tests/test_url_snapshot_driver.py` 原有 13 条与 20 个 subtest 仍全过。
**度量口径与偏离**：新套件是在 **dev.py 之外**用 CI venv 解释器跑的，
因为 dev.py/conftest 会把 `PLAYWRIGHT_BROWSERS_PATH` 指到空的 project-local 缓存，
用 sanctioned runner 只会让真机那条 skip（全量套件里确实是 1 条 skip）；
理由记在这里，不是忘记走 runner。
- 全量 Python 套件（经 dev.py，**在矩阵 F03 行改写之前**启动）：4284 passed, 31 skipped, 14 warnings, 166 subtests passed in 420.49s (0:07:00)（日志 `.project-local/task-runtime/py-full-20261007-render.log`）；
- 绑定最终提交字节的重跑：`tests/maintenance` 184 passed / 2 skipped（含读矩阵的那几条门禁测试），
  `tests/workers/test_webpage_render.py + tests/test_url_snapshot_driver.py +
  tests/workers/test_doc_engine.py` **42 passed / 0 skipped**
  （11 条渲染 + 13 条驱动 + 18 条 `.doc`，日志 `.project-local/task-runtime/web-doc-final-20261007.txt`）。
  两次全量的计数差也对得上：新增 11 条里有 1 条在 dev.py 环境下 skip，
  所以净增正好是 10 passed（4274 → 4284）与 1 skipped（30 → 31）。
矩阵门禁 exit 0：16 组 / 0 complete / 15 partial / 1 custody-only（F03 仍 `partial`，
`required_output` 逐字未动，只改 `implemented_now`/`gap` 与 evidence 的 `code`/`tests`）。

**仍未闭合**：截图不在这一条里；点击/登录后才出现的内容、以及超出滚动预算的懒加载列表仍拿不到
（预算耗尽会报 `budget_exhausted`，不会假装到底了）；浏览器仍是**具名的宿主引擎**，
没有进 `capability-requirements.yaml` 的声明清单；整条通道由脚本驱动，界面按 Owner 指示暂停。

**回滚**：revert 这一次提交（worker 的 render/`_browser`/scroll、driver 的 `--render`、
`tool_paths.OVERRIDES` 的 chromium 一项、新测试与两份记录、矩阵 F03 行）。取字节通道本身未改行为。

## 补记：上一条里"浏览器尚未声明"这句，20 分钟后就不成立了（2026-10-07）

**上一条的哪一句作废**：`浏览器仍是具名的宿主引擎，没有进 capability-requirements.yaml 的声明清单`。
写它的时候确实如此；随后我去看外置工具根，发现 **`10-toolchains/playwright/` 里本来就有**
`chromium-1228/chrome-win64/chrome.exe`（4059648 字节，sha256 `b798f9e53a98d29eb7f36f8c409f905d3184780a04d2bcb56989067194784bd1`）
与 `chromium_headless_shell-1228/`——清单里也**已经有** `playwright-chromium` 这一条，
只是它**没有 `external_paths`**，所以名字在、位置没人读。这是"盘上有 ≠ 绑定"的第三种形态：
**声明了名字 ≠ 声明了位置**。

**改了什么**：
- `playwright-chromium` 条目补上 `external_paths: ["10-toolchains/playwright/chromium-1228/chrome-win64/chrome.exe"]`，
  `required_by` 加 `conversion`（渲染通道确实是转换侧使用者），重新生成索引：该路径 `exists: true`；
- `worker_webpage._browser()` 的解析顺序定为 **`ARCHEAXIS_CHROMIUM_CMD` → 声明清单 → Playwright 注册表**，
  失败消息里点名 `browser source=`；声明不存在时不猜、不用别的浏览器顶替；
- worker 侧新增 `_declared_browser()`，与其他 worker 一样从自己树里的 `tool_paths.py` 读声明
  （清单读不动就抛错，绝不当成"没声明"）。

**决定性验证（这一条才是买到的东西）**：
`scripts/runtime/dev.py --pytest tests/workers/test_webpage_render.py …` ——
**不设任何浏览器环境变量**、且 dev.py 会把 `PLAYWRIGHT_BROWSERS_PATH` 指到空的 project-local 缓存，
渲染套件 **20 passed in 7.77s**（日志 `.project-local/task-runtime/render-declared-final-20261007.txt`）。
也就是说：真机那条浏览器证明现在**由声明本身**跑通，而不是由我临时导的一个变量跑通。

**顺带记一条门禁的行为**：第一次跑索引对比测试**失败**（`assert [] == ['10-toolchai…chrome.exe']`），
那不是回归，是**索引陈旧守卫**在正常工作——它拿已提交的索引和新改的清单对账；
重新生成后再跑同一命令即 20 passed（12 条渲染 + 8 条清单/索引门禁），0 skipped。这一守卫两次拦住我把"声明了但没人读"当成已绑定，值得点名。

**全量套件的对照数（同一台机、同一个 runner，只差这一条声明）**：声明之前
`tests` 报 **4284 passed / 31 skipped**，声明之后报 **4286 passed / 30 skipped**
（日志 `.project-local/task-runtime/py-full-20261007-browser.log`）。
差值恰好是 +2 passed 与 -1 skipped：新增的一条"配置路径失败时不得改用声明浏览器"测试，
加上那条原本因空缓存而 skip 的真机渲染现在**由声明本身跑通**。
这两个数字是同一口径下唯一被我拿来当证据的全量计数，绑定的是本次提交的字节。

**矩阵与快照同步**：F03 `gap` 里"浏览器尚未声明"那句替换为解析顺序与构建号耦合的事实
（升级 Playwright 会让这一条声明失效，而不是安静地换一个浏览器）；
`status` 仍 `partial`，`required_output` 逐字未动。快照的未决条目与 `next_action` 同步更正。

## Chromium 进供给链台账，以及我自己写坏的一次台账（2026-10-07）

**做了什么**：渲染通道用的浏览器现在有据可查——新增 **A049 Chromium**
（`SIDECAR` / qualification `["installed"]` / capability `web-render`），
身份是从盘上读的：`10-toolchains/playwright/chromium-1228/chrome-win64/chrome.exe`，
**4,059,648 字节，sha256 `b798f9e53a98d29eb7f36f8c409f905d3184780a04d2bcb56989067194784bd1`**，
启动自报 **149.0.7827.55**。`component_count` 49 → 50，
`disposition_summary` 的 SIDECAR 4 → 5，**两个数都由行表现算出来，不是手填**。
`playwright` Python 包本身是本仓**已锁**的第一方依赖（`playwright>=1.61,<1.62`），
这一行记的是产品实际启动的那个二进制。

**我自己造成的破坏（如实写）**：追加行的脚本用了"任何含 `SIDECAR` 的字典都是计数表"这个匹配，
于是把台账里 **`disposition_labels`（每个处置标签的**定义**，含两个当前没人用的标签
`ADOPT_PRODUCT_BASE`、`DEFER`）整体覆盖成了计数**。
在提交**之前**读 `git diff` 时发现：那一段 -9/+7 是定义文本没了。
处理方式：从 `HEAD` 逐字节恢复定义，只在 `disposition_summary` 上重算计数，
并让计数**按标签表全词汇展开**（没人用的标签显示为 0，而不是从表里消失）。
所以这次提交里没有留下损伤；但**缺陷发生过，就必须进账本**。

**这条破坏暴露的真缺口，以及它的补法（已落地，不是待办）**：
`tests/test_mfx001_supply_chain_ledger.py` 原本 5 passed 全程没拦住它——该测试校验行字段与处置词汇，
**不校验 `disposition_labels` 是"字符串定义映射"、也不校验 `disposition_summary` 的键集合**。
补了一条 `test_disposition_labels_stay_definitions_and_summary_covers_them`（现 6 passed），
并**先证伪再用**：把台账临时改成我这次实际造成的那种破坏（labels ← 计数），
该测试如期 FAILED 1 条；随后从哈希一致的备份恢复（`restored identical: yes`）。
没有这一步，"补了个门禁"只是一句自我声明。

**可复用的教训**：改一份机器可读台账时，"这个字段看起来像计数表"不能替代
"我知道这个字段是什么"。**任何覆盖式写入前先看一次 HEAD 里该键的类型**；
以及 `git diff` 要在 commit 前读，而不是 commit 后。

## `.ppt` 不再是"本机无合法读取路径"（2026-10-07）

**这条判断被推翻的过程**：账本连续几轮写着 `.ppt` 无 reader，理由是"唯一候选要 JVM，而本机无 JVM，
且本轮不许装系统级软件"。三句当时都真。但**边界禁的是"系统级安装"，不是"放进外置工具根"**——
而目标里明写"缺工具下载到工具库"。于是这一刀先做的是**核对可达性与校验和**，不是写代码。

**实测就位过程（每一步都留了数）**：
1. Temurin 的 API 给出与 Adoptium 同形的 `package.checksum`，**但它的下载主机在本机不可达**
   （`curl` 到 github.com 释放域名 → http=000；urllib 则 `RemoteDisconnected`）。
   记录这一点，是因为"官方优先"不等于"官方主机在本机可达"，换一个发行方不是降级，
   而是把来源说清楚。
2. 改取 **Azul Zulu Community JRE 21.0.12.1（build 21.52.203）**：Azul 的每包元数据 API
   直接给 `sha256_hash`；下载 49,264,410 字节，**算得的 sha256 与元数据一致**才解包。
   许可**不凭印象**：从分发自带的 `legal/java.base/LICENSE` 与 `ASSEMBLY_EXCEPTION` 读出
   GPLv2 + Classpath Exception。
3. **Apache Tika 4.1.0 官方发行包** `tika-app-4.1.0.zip`（55,617,982 字节），
   与站内发布的 `.sha512` 逐字节核对；解出的 jar 只有 122,724 字节，
   真正跑起来靠同批的 `lib/` 与 `plugins/`，所以**不能只看 jar 大小**（Maven 上那个同名 thin jar
   不是可执行体）。许可取自包内 `LICENSE`（Apache-2.0）。
4. 样本仍走已被接受的路子：**不是自造件**——Apache Tika microsoft-module 的
   `testPPT.ppt`，固定在**已经在用的那个提交** `b8a6916ea…`（tag 3.3.2），
   16,384 字节，sha256 `499ccd0de7c0778afa4f6ed08793afd2406b62547373a619a5a78658ae65c4b7`，
   git blob `b48cfaf2bd7045c21c5f65e1478725e8cee84ed7`。
   容器判据也实测过：OLE2 魔数 + **UTF-16LE 的 `PowerPoint Document` 流名**
   （我用 ASCII 字节搜它时守卫直接拒绝过——一个搜不到的守卫比没有守卫更糟，改的是守卫）。

**产品侧落成的形状**（刻意复用 antiword 那一刀的教训）：
- 五层全打通：`.ppt → application/vnd.ms-powerpoint`（`media_type_for_name`，注释里那句
  "`.ppt` is still deliberately NOT named" 已替换为事实）、`office.structure` 的 media_types、
  transport 的 `suffix_by_media`、worker 的 `extract` 分派；
- **两条一起声明**：`zulu-jre` 与 `apache-tika`。只声明 jar 会"解析成功而跑不起来"，
  与 antiword 缺映射表同形；索引重生成后两条都 `exists: true`；
- 引擎先自报身份再交文档：`java -version` 必须说出自己是哪个 JVM，
  jar 必须答 `Apache Tika <版本>`；答不出就是具名拒绝，**不出文**；
- 一个进程只读一个文件；退出码在这里是可信的（与 antiword 的批模式不同，这里只传一个具名文件），
  失败消息取 stderr 里**非 INFO/WARN 的那一行**，而不是引擎的日志噪声；
- 投影只取 stdout；损失报告点名 Tika 单文件模式**自作主张开启的非默认特性**（TIKA-2374/4017/4354/4472）。

**度量口径**：`tests/workers/test_ppt_engine.py` **12 passed**（含真机用例；经 sanctioned runner，
没有导任何环境变量，解析完全由声明完成，日志 `.project-local/task-runtime/ppt-tests-20261007.txt`）；
全量 Python 套件 4299 passed, 30 skipped, 14 warnings, 166 subtests passed in 496.44s (0:08:16)（日志 `.project-local/task-runtime/py-full-20261007-ppt.log`）；
`tests/workflow` 里那条把 A010 钉成 `NONE` 的断言**如实改了预期**——
它原先钉的是"仓库里没人提 Tika"，现在 worker 真的调用它，
所以 `IMPLEMENTED_IN_SOURCE` 才是对的分类，改的是**样本过期**而不是放宽标准（代码里写了原因）；
供给链台账门禁 6 passed（含上一刀补的标签定义守卫）；矩阵门禁 exit 0（16 组 / 0 complete /
15 partial / 1 custody-only），F14 仍 `partial`，`required_output` 逐字未动；
台账新增 **A050 Azul Zulu JRE**，A010 的 qualification 由 `[source]` 升为 `[source, installed]`，
`component_count` 50 → 51，SIDECAR 5 → 6，两个数都由行表现算，**`disposition_labels` 未触碰**。

**我改了两条已提交的 Rust 断言，逐条写清**：`.ppt` 一进名，两条把"没有 reader 的族"钉成清单的测试
就撞上了——`office_job_end_to_end.rs::office_names_select_the_office_route_and_the_legacy_formats_are_refused`
与 `xls_member_chain.rs::the_formats_with_no_reader_stay_unnamed_rather_than_reaching_a_route`，
两处都是 `unwrap_err()` 收到 `Ok("application/vnd.ms-powerpoint")`（第一次跑 RUST_EXIT=101）。
这两条断言的前提是"本仓没有 `.ppt` 的 reader 也没有声明 JVM"，该前提已被本刀**主动改变**，
所以改的是**过期的例子**而不是放宽标准：拒绝清单换成本来就仍无路径的 `.pps`，
并新增 `.ppt` 必须被点名、且**不得**作为 text 通过的断言。改完两条各自 3 passed / 2 passed。

**Rust 侧度量口径**：`cargo fmt --all --check` PASS（先前我写的一行断言超长，fmt 先失败，
按格式化后的多行形状改好后再检）；
`cargo test --workspace --offline` 在最终字节上 **128 个 `test result:` 行合计 516 passed / 0 failed**
（日志 `.project-local/task-runtime/rust-ppt-final2.log`；上一轮在旧字节上是 73 行 / 329 passed 且
带 1 条 FAILED，那条 FAILED 就是上面这双过期断言之一）。

**一条我没有归因清楚的数**：全量 Python 从 4286 passed / 30 skipped 变成 4299 passed, 30 skipped, 14 warnings, 166 subtests passed in 496.44s (0:08:16)，
净增 **13**，其中 **12** 条确实是新增的 `tests/workers/test_ppt_engine.py`
（`--collect-only` 实测 12 tests collected）。余下 1 条我没有把解释编出来：
查过 `test_bulk_office.py`（读清单但不按夹具参数化，6 collected）、
`test_p1_quality_matrix.py`（11）、`test_f01_real_quality.py`（5）、
`test_worker_reachability.py`（7），都不是按夹具条目或媒体类型展开的参数化，
所以这一条在此**只报数、不给理由**。

**仍未闭合**：`.ppt` 的**版式语义**（母版、备注、图表、嵌入对象）不进投影；
FMT-21 逐扩展名真人验收仍 NOT_RUN；`.xls` 夹具仍是自造件；
JVM 与 Tika 是**本机外置根里的放置件**，换机器需要重新供给，产品不代装。

**回滚**：revert 这一次提交即撤销 `.ppt` 路由、worker 侧车通道、两条声明、夹具与记录；
外置根里的 `10-toolchains/java/…` 与 `10-toolchains/tika/…` 是新增目录，删除需单独授权（本轮不删）。

## 我让 CI 红了一次，原因值得单独记（2026-10-07）

**现象**：`5fa65075` 推上去之后 CI 报红两条——`test (3.12)` 的 `Run OS-level tests` 与
`a0-gates`（后者是对前者的裁决，不是独立故障）。失败断言只有一条：
`tests/test_axr060_completion_audit.py::test_tracked_current_surfaces_only_reference_declared_release_delta_or_source_objects`，
消息是"current surfaces cite hashes that are not real objects in this repository: ['b8a6916e…']"。

**成因（两条叠在一起，缺一不可）**：
1. 我在 A010 台账行与快照的"当前面"里写了**上游 Apache Tika 的 40 位提交号**。那句话是真的，
   但它断言的是"本仓有这个对象"，而本仓没有——`git cat-file -t` 直接失败。
2. 更关键的是**这条门禁读 HEAD（已提交树），不读我的工作树**。我在提交前跑了全量套件，
   4299 passed，于是我以为它是绿的；它绿的是**上一版已提交状态**，不是我要推的那一版。

**这正好是仓库里已经写着的那条规矩的实例**："提交之后、在冻结的树上复验"。
我之前只在**文档类**改动上这么做过，没把它当成对**门禁**的强制步骤。

**修的方式**：不把门禁放宽、也不把引用删掉——把可核验的锚换成本仓真能解析的东西
（发行标签 `3.3.2` ＋ `tests/fixtures/golden/manifest.json` 里那条夹具登记，
哈希作为**关于夹具的数据**留在那里是合法的，作为**关于本仓对象的断言**留在当前面就不合法）。

**随之而立的规矩**：凡改动会被 `test_axr060_completion_audit`、`check_document_authority`
这类**读 HEAD 的门禁**覆盖的，验证顺序必须是"提交 → 在 HEAD 上跑门禁 → 通过才 push"，
而不是"工作树跑绿 → push → 让 CI 告诉我"。这条在本轮生效：修完先提交，在 HEAD 上跑该门禁，
确认它绿了再推。

## 蓝图附录 5 条 SOURCE_MISSING 全部回来了，我上一轮的判定是错的（2026-10-07）

**Owner 直接给了原件**：`D:\All projects\Record` 下的 4 个 zip 与 4 个 md。其中
`QODER_AAOS_RECOVERY_20261007.zip` 就是**附录那 5 条**的恢复包：`sources/` 三条
（A01 快速重构与多格式闭环、A02 未来延展与可持续架构、A06 CONTENT-COPY-V2）与
`records/` 两条（U01、U02 的**规范化恢复导出**）。

**我上一轮那条"按内容哈希检索仍未找到"是错的**，而且错得值得记：
那次我扫了 Record 递归 + 一个目录的 zip 成员 + 资料库，**没有把这些文件所在的这组恢复包/新落位文件算进范围**，
于是把"我没扫到"写成了"按内容不存在"。这与 A04 那次 `maxdepth 5` 漏判是同一类错——
**证否的强度只等于扫描范围的强度**，而我两次都把范围当成了全集。
（这次连附件的时间戳都是当天 09:2x，也就是文件在上一轮检索之后才到位；但"当时没找到"
不等于"可以断言不存在"，我当时的措辞已经越界。）

**归档与核验（不丢内容）**：
- 落位 `docs/history/aaos-appendix-sources-20261007/`，四个包**逐成员**展开：
  68 条登记、按 sha256 去重后 **61 个存储文件**、**59 条与该包自带的 `SHA256SUMS.txt` 声明值相符**、
  0 条缺失；每条登记都带来源包 sha256、成员 CRC32、解出字节的 sha256。
  清单：`ARCHIVE-MANIFEST.json`。
- zip 内文件名是**未置 UTF-8 标志的 UTF-8 字节**，`zipfile` 按 cp437 解出乱码；
  解出时做了 `cp437→utf-8` 复原，并对"已是正确名"的情形保留原名（否则会把好名字改坏）。
- 重复内容只存一份，别名逐条留在清单里（例如附录 A07 的合并阅读版与包内
  `AAOS_完整任务包_合并阅读版.md` 同哈希）。

**来源表改判**（`docs/current/AAOS-INPUT-SOURCES-20261006.json`）：
9 条全部 `VERIFIED_MATCH`，0 条 `SOURCE_MISSING`。逐条哈希：
A01 `7ecda3e3…`、A02 `771b1897…`、A06 `7d475862…` 与**蓝图附录登记的预期值一致**；
U01 `71219c25…`、U02 `a3d94956…` 与恢复包自带 `SHA256SUMS.txt` 一致。
**限定语没有松**：U01/U02 记的是"这份规范化恢复导出的哈希可核验"，
**不是**"原始聊天全文被找回"——恢复包自己也这么写。摘要句与 `checkpoint.open` 条目
由脚本从表里再生成，ids/条数与表不符即中止。

**这一刀的产物**：内容侧的解析与梳理另见
`docs/history/aaos-appendix-sources-20261007/`（原件）与随后的对账纪要；
本轮**尚未**据这些新文档改动任何规划权威文件——先把来源闭掉，再谈吸收，
免得把没核过来源的东西直接写进当前记录。
2026-10-07 用户后续指令修订交付边界：本 UI 增量留在本地工作树完成，不提交、不推送、不合并或发布。此前记录的 worktree Git index 写权限阻塞不再是本轮交付项；源码级验证仍绑定各自记录的精确 dirty source identity，真实 Windows/Tauri、IME、屏幕旅程继续按实际证据判定。

2026-10-07 本地续验（测试源码身份 `HEAD=25213bddd9885289a59b7e1cf774ef3fd62a1c9a` + `source_patch_sha256=fa882225060c643a50fa09c69ef1f059a6738363b8c3c9c76df8caaf4bf194b1`）：新增 StatusBar 集成回归，逐项切换黑色/珍珠白/科技深空，核实 `documentElement[data-aaos-theme]` 与正在渲染的品牌 SVG URL 同步采用 `AAOS_THEME_REGISTRY`；此测试和主题契约定向 2 文件/11 项 PASS。完整前端 Vitest 42 文件/284 项 PASS，严格 TypeScript PASS；`dev.py` 均记录相同 dirty source identity。生产实现代码与上次 214 modules Vite 构建相同，本续验只增测试及记录，因此构建结果仍可复用作实现代码证据，不能替代真实窗口。继续 NOT_EXECUTED：三主题可视截图、Tauri/WebView 候选、分辨率/DPI/物理 IME、离线/冲突/重启/恢复视觉旅程；本地预览在 Codex IAB 仍超时，未生成截图。

2026-10-07 动态入口目录纠偏（定向源码身份 `HEAD=25213bddd9885289a59b7e1cf774ef3fd62a1c9a` + `source_patch_sha256=c0274bf78247161b4003f8344824a86f7477ac7bb7b44d00a0a694ff515c4311`）：移除 `SpaceRail.test.tsx` 中固定 16 项断言，改为 capability projection 的去重集合与投影长度核对；导航按组排序，故不要求与 Atlas 原始序列相同。SpaceRail/导航投影定向 2 文件/9 项 PASS，覆盖完整菜单集合、键盘遍历及激活。前次 42 文件/284 项完整套件已覆盖产品实现和同套件；本项仅改断言，相关定向用例对当前精确 dirty identity 复验通过。

2026-10-07 UI 增量续验（分支 `codex/aaos-ui-newui-20261007`，源码 `HEAD=25213bddd9885289a59b7e1cf774ef3fd62a1c9a` + `source_patch_sha256=c6a19e1391f5a59425ce045dea55ddda7a672ad84fe96d877701f10c7f04f6ff`）：修正全局命令面板对未实现能力的错误 `aria-disabled`，未来条目继续保留“查看详情 · 尚未实现”且可通过键盘选择进入正式 Atlas 详情；新增回归验证入口状态、Enter 选择、用途/前提/依赖/降级与下一步详情，App 与能力目录定向 2 文件/29 项 PASS。完整前端 Vitest 42 文件/283 项 PASS，严格 TypeScript 检查 PASS，Vite 生产构建 PASS（214 modules；主业务 414.67 KB、PDF Reader 484.33 KB、DocumentEditor 404.60 KB）。运行回执均绑定上述脏源码身份；证据限本地源级测试/类型/打包，不代表真实 Tauri、WebView、安装候选或 Windows 旅程。`scripts/runtime/dev.py` 分配独立 `.project-local/runs/`，源码无测试缓存产物。远端 HEAD 仍 UNKNOWN；Git index 写入此前被 Windows 权限拒绝，提交资格仍 UNVERIFIED，当前增量未提交。Native Tauri 构建继续受外置 Cargo registry canonicalize WinError 5 阻断；不修改 ACL、不复制缓存绕行。本轮 UI Windows DPI/IME/离线/失败/冲突/重启/恢复实机旅程 NOT_EXECUTED，既有 Q 状态不升级。

\n
2026-10-07 本地续验回执（`HEAD=25213bddd9885289a59b7e1cf774ef3fd62a1c9a` + dirty patch SHA-256 `432bb2fc783f98756b0fbf3ca43854ed95264273a77c4af14682edaedf382e76`）：修复旧 `OsuiProductionContract` 测试假定首页固定为工作台的问题；Vitest 多例共享 URL hash，且真实产品必须尊重已有空间/能力深链。断言现在验证主内容区的稳定壳和空间无关 landmark，不清理或覆盖深链。全前端 Vitest 42/42 文件、284/284 项 PASS；TypeScript `tsc --noEmit --project frontend/tsconfig.json` PASS。任务包源码/组件/主题/依赖完整性校验 14 锁定源文件、111 规格映射、21 对比候选 PASS；全能力入口矩阵 `--check` PASS。所有运行由 `scripts/runtime/dev.py` 在隔离 `.project-local/runs/` 内执行，相关 execution.json 绑定相同 dirty identity。Playwright CLI 前置要求 npx；此主机无 `npx`/`npm` 命令，且 Codex IAB 回环预览此前超时，按技能要求未另装浏览器依赖或伪造截图。三主题真实窗口截图、Tauri/WebView 同SHA候选、DPI/物理IME、离线/失败/冲突/重启/恢复旅程仍 NOT_EXECUTED；实际完整性验收保持 PARTIAL。

2026-10-07 容器成员升链入口落地（分支 `codex/aaos-member-chain-20261007`，提交 `29350898`，基线 `origin/main=a767ae39`）：F15 记录缺的是"没有界面驱动这条链，只能跑脚本"。新增 `frontend/src/components/ContainerMemberChain.tsx` 并挂到库空间选中来源详情之后：读 `source_members`（把"Core 404 未登记容器"与"容器为空"分成两句说），点可读成员读该成员自己的 `source_job_transform`，人在识别结果里选中原话后以 UTF-16 偏移提交 `knowledge_from_transform`；回执必须同时是 `status=candidate` 且 `requires_human_review=true` 才显示为已登记候选，否则明说"未登记任何知识"。原始 SHA/offset/回执继续只进诊断控制台。未改 Rust、schema、宿主桥或权限：三个操作都在既有合同与 `packages/contracts/v1/core-command.schema.json` 内。验证：定向 Vitest 3 项 PASS（含 404 与拒绝两支），完整前端 49 文件/332 项 PASS，`tsc --noEmit` PASS；Vitest 与 tsc 由声明工具根 `10-toolchains/scoop/apps/nodejs-lts/24.18.0/node.exe` 运行，依赖按 `package-lock.json` 以 `npm ci` 安装在该工作树 `frontend/node_modules`（164 包，项目内，不外溢），此两项未走 `dev.py`，因此无对应 dirty-identity 回执，绑定的是提交 `29350898`。NOT_EXECUTED：真实 Tauri 窗口内该入口的鼠标/键盘旅程、把候选经真人复核升为已接受知识、安装候选与同 SHA 实机验证；成员与容器仍按既有关系寻址，未新增可查询边类型。

2026-10-07 逐字路径：Obsidian 导入接缝按根因收口（分支 `codex/longpath-importer-20261007`，提交 `8523155a`，并入 `origin/main=b82caf79` 后为 `671bc1fc`）：台账第 136 行点名的两处缺口之一已闭。`shared/obsidian_importer.py` 的四处——`scan_vault` 枚举、`_build_target_index` 枚举、`_attachment_facts` 存在判定与读字节、`import_file` 存在判定与读取——改为**在带 `\?\` 前缀的根上枚举、并对同一个前缀根求相对**，因此枚举可得、IO 可开，而写入报告/存储的仍是普通相对名；`import_course_to_cards` 同样按前缀根 glob，`source_doc_id` 继续用普通根拼出，未把前缀漏进任何存储值。上次卡住的"机械包装会让 6 条测试变红"没有重现，因为这次改的是**比较基准两侧同源**，不是给名字加前缀。新增 `tests/test_obsidian_importer_deep_path.py` 4 项：夹具把笔记与附件放到 260 界限之外（Vault 根仍普通可建 ≤251，笔记所在目录 279 字符），并先断言普通名 `exists()` 为假——即缺陷前提成立。**齿证**：四处逐一去掉前缀，对应 4 项各自变红（`1 failed`），还原后字节一致；控制组 4 passed；既有 `test_obsidian_importer.py`/`test_obsidian_projection.py`/`test_obsidian_vault.py` 共 100 项仍绿；整量 Python `4321 passed / 32 skipped / 166 subtests passed（537.50s）`，`dev.py` 运行目录 `.project-local/runs/41a087a409/d50e75d759e8`，退出 0。仍点名为未闭：`intake_upload` 生成临时文件后交给第三方解析器（转换器按普通名打开）在深路径下仍未证——那需要一条接缝决定（短基临时目录或交给 worker 的是字节而非路径），本轮未自签完成。

2026-10-07 F04 内容判定路由落地，并测出 F10 已并入件其实不可达（分支 `codex/f04-detect-20261007`，基线 `origin/main=b82caf79`）：为"扩展名说不出类型就只能拒绝"这条 F04 逐字缺口补上证据式命名。新增 `services/python-workers/document/worker_detect.py`（引擎 `python-worker-detect`），跑仓库内**已入库并自带测试**的 Magika 本体 ONNX（`shared/file_detection.py`，Apache-2.0，`shared/models/magika/`），回执只报模型自己的 label/group/score、被判定字节的 SHA-256 与模型 SHA-256；**不产出媒体类型**，因为随仓库的 `config.min.json` 没有 mime 表，在这里造一张表就是需求拒绝的"猜"。Core 侧新增作业种类 `detect`，且 `resolve_media_type` 只对 `document.detect` 接受"名字说不出类型"的来源，其它路由照旧拒绝（既有拒绝断言未动）。
**本轮最重的发现，也是上一条 F10 记录的真实边界**：作业路由要真能被产品抵达，需要四张表同时点头——`routes.json`、`config/capability-map.v1.json`、Rust `attempts.rs`（`ROUTES`/`ROUTE_MEDIA_TYPES`/`ENGINE_PROFILES`/`resolve_media_type`）、`executor.rs` 的 `KNOWN_WORKER_IDENTITIES`——**再加第五处** `services/python-workers/transport/text_ndjson.py::ROUTES`。PR #166 把前四处都补齐了，第五处没有，所以真作业到worker时被回 `unsupported capability`；同时该 worker 的 CLI 只收一个位置参数，而 Core 是按 `--staging-root <目录>` 拉起并用 stdin 传请求的（输入还是内容寻址、**没有扩展名**），并且 `LossReceipt` 带 `deny_unknown_fields`，只允许 `engine/engine_version/params/loss_note/losses/covered/total/coverage`——`claim`/`state`/`reason`/`missing_artifacts` 这些诚实字段必须放进 `params`，否则作业以 `invalid loss receipt` 死掉。这几条不是推测：`detect_job_end_to_end.rs` 第一版依次报 `unrecognized arguments: --staging-root`、`invalid line structure`（需 `contract_adapter: True` 才能把 worker 自己的结构挪到 `params.worker_structure`、由传输层派生规范行锚）、`invalid loss receipt`，逐个按根因修后才 PASS。
**齿证与拒绝语义**：拒绝改为**抛出**而不是返回空结果——空文本 + `state=unavailable` 会以 `succeeded` 落库，下游读起来就是"这段录音没人说话"。`diarize_job_end_to_end.rs` 因此断言：无模型时作业必须失败，且消息里点名 `segmentation-3.0.onnx` 与 `speaker-embedding.onnx`（PASS）。新增门 `test_the_transport_dispatches_exactly_the_declared_routes`：已声明又无传输表条目的能力，只有当 Rust 里没有任何作业种类指向它时才允许豁免（derived 三件即此情形），否则变红——把本轮这个洞钉成回归。Python 定向 `tests/workers` 全量 401 passed / 106 subtests；`-p archeaxis-application` 25 个目标全 ok；两个新 e2e 各 2 passed；`cargo fmt --all --check` 0；整量 Python `4331 passed / 32 skipped`（413.13s）退出 0。合同 §7 计数改为 16 声明 = 12 import/transform + 1 内容判定 + 3 derived，并写明 `media.diarize` 仍未就绪。**仍未闭**：F10 的两个 ONNX 资产（同日实测 GitHub 侧 `k2-fsa/sherpa-onnx` 的 speaker-diarization 发行件只有 wasm 包，不含这两个 ONNX；HF 三域 000、ModelScope 无逐文件校验和且为 pytorch 权重）；判定结果目前没有界面入口。

2026-10-07 逐字路径：intake 上传接缝按根因收口（分支 `codex/longpath-intake-20261007`，提交 `eb5af3b1`，基线 `origin/main=6a8de766`）：台账第 136/… 行点名的第二处缺口闭。`app/workspace/service.py::intake_upload` 三处改按逐字名——`intake_uploads` 目录 `mkdir`、`NamedTemporaryFile(dir=…)`、交给 `_convert_file_for_intake`/`detect_format`/`build_workspace_conversion_run` 以及 `unlink`/`replace` 的路径；入库与回执仍只用普通名，前缀不进任何存储值。**测出来的两条真实伪装**：深基下 `upload_dir.mkdir` 直接抛 `FileNotFoundError`（父目录链在普通调用里不存在），而把普通名交给第三方转换器时报的是 `No engine could convert xlsx file '…'` —— Windows 路径上限被伪装成"引擎缺失"，运维会去重装引擎而不是改名。新增 `tests/test_intake_upload_deep_path.py` 2 项：其一断言**转换器拿到的必须是逐字名**（与主机是否开启长路径无关的接缝断言），其二在深库上跑完整入库并逐字回读 `intake_uploads` 里的归档副本；同时保留"临时文件名由 `mkstemp` 生成，因此任何长度阈值都不许用来决定是否加前缀"这条既有规则。**齿证**：去掉 dir 前缀、去掉 mkdir 前缀，对应断言各自变红，还原字节一致；"把普通名交给转换器"与现写法在本主机等价（temp 目录已带前缀），因此不为它单独立断言，避免造一条没有牙的门。相邻 `test_workspace_pipeline_multiformat.py`/`test_workspace_api.py`/`test_workspace_audit_regressions.py` 共 42 项仍绿；整量 Python `4326 passed / 32 skipped / 166 subtests passed（476.63s）`，`dev.py` 运行目录 `.project-local/runs/af347e20ee/…`，退出 0。未闭项改记为：无（本条点名的两处已闭）；Windows 长路径注册表策略、真实 Tauri 与真人验收继续按实机证据判定，不在本地自签。

2026-10-07 F09 工作簿单元格成为自己的位置（分支 `codex/f09-cell-anchor-20261007`，提交 `f928c928`，并入 `origin/main=ec502cf3` 后为 `0d1b27f4`）：跨 F05/F07/F08/F09/F12 那句"结构是被报告的事实，不是寻址层"里，F09 那一格此前是反的——xlsx 投影最小可寻址单位是**行**（一行里若干格以 `" | "` 相连），引一句单格原话只能锚到连邻居一起被主张的位置；`.xls` 更糟，投影单位是**整张表体**，行列都不可寻址。两个引擎现在都填 Core 已有的通用合同 `params.format.locations`：唯一 `path` 为 `工作表名!坐标`，`value` 就是该投影实际显示的那个 token（xlsx 为 `A1=值`，xls 为引擎显示文本被投影自己的 `repr` 引号包住），并附带可用于收窄的 `sheet/coordinate/row/column`（xls 另带引擎自报的 `cell_type`）。上限 5000 写在回执里而不是静默截断：xlsx 说明溢出部分仍可按行寻址，xls 说明溢出部分不可寻址，因为那个投影没有行单位。`crates/archeaxis-api/tests/format_location_anchor_api.rs` 加入同一行两格（`半径!A1`、`半径!B1`），使 cell 这一族在锚点机制里被证而不是只被期待。
**齿证**：分别删掉 xlsx 与 xls 的 `locations.append` 块，各自 2 项变红（`2 failed, 5 passed`，红在"必须有位置"与"值必须出现在投影里"两处断言），还原后文件字节一致（`restored byte-for-byte: True`，`git status` 该文件 0 行改动）。**验证**：`tests/workers` ＋ `test_text_format_facts.py` ＋ `test_worker_route_lists_agree.py` ＋ `test_obsidian_importer_deep_path.py` 共 `425 passed / 106 subtests`（51.10s）退出 0；`-p archeaxis-api --test format_location_anchor_api --test evidence_anchors_api` 分别 `4 passed`/`5 passed`，`cargo fmt --all --check` 退出 0；Rust 经追踪入口 `scripts/ci/cargo_test.bat` 与声明工具根（`ARCHEAXIS_RUST_TOOLCHAINS=10-toolchains`、`ARCHEAXIS_MSVC_VCVARS=10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat`、canonical `ARCHEAXIS_CARGO_HOME`）执行，未改 ACL 未复制缓存。**仍未闭**：产品作业里对 xlsx/xls 单格提交锚点并读回 `location_status=located` 的界面旅程 NOT_EXECUTED；FMT-21 逐扩展名真样本验收仍 NOT_RUN（`.xlsx` 夹具为仓库内 `tests/fixtures/sample.xlsx`，`.xls` 为 `tests/fixtures/golden/golden-xls-anchor.xls`，SHA `3225b8bb…2353` 已由既有测试钉住）；`>5000` 格的溢出路径只有断言与文案，未在真实大表上实测。

2026-10-07 暂存残留清理读回与静默期决定（分支 `codex/cleanup-readback-20261007`，基线 `origin/main=881657be`）：本条全部数字由脚本 `os.walk`/`getmtime` 现测现取，来源记录是 `.project-local/task-runtime/` 里的 `staging-residue-audit-20261007.json`、`staging-cleanup-candidates-20261007.json`（41 项逐条判定）、`staging-cleanup-citation-check-20261007.json` 与 `staging-cleanup-executed-20261007.json`。

**更正此前状态**：之前记的"未执行删除"已过期。执行回执 `executed_utc=2026-10-07T08:34:08Z`，`items_removed=22`，`mib_freed=4165.6`，`complete=true`；今日对回执里 22 条精确路径逐一 `exists()` 复核，**22 条确已不存在**。

清单原判 deletable 共 34 项；今日仍在盘上 12 项，已消失 22 项。仍在的按可否引用分两类：
（一）**被引用的恢复/证据目标 3 项，不得删**：
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\be268a2d33\evidence-build-20260925` 135,364,699 B（mtime 2026-09-25T05:03:15）；引用：`docs/current/R6-EXECUTION.md:2622` 记录其中 `bin/ArcheAxis.Desktop.dll` 的受测 SHA-256
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\be268a2d33\aaos-ui-theme-20260926-02` 133,572,310 B（mtime 2026-10-06T21:15:32）；引用：`docs/history/storage-cleanup/2026-09-30/storage-cleanup-current-goal-20260930.md:162` 记其已归档后删除
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\r10-live-retry-20260915\deeptutor-web` 81,901,290 B（mtime 2026-09-15T23:15:54）；引用：`docs/current/R5-EXECUTION.md:1564`、`apps/ArcheAxis.Desktop/DeepTutorSupervisor.cs:89`、`scripts/launch/deeptutor_web.py:135` 的启动回执路径

（二）**今日由活动切面写出、未过静默期的 9 项，合计 1,572,068,859 B（1499.2 MiB），本轮不删**。这些是运行目录，可再生，但写出时刻都在今天，可能有进程仍持有；精确路径逐条列出（处理时只按逐条精确路径，不用 glob、不用按目录名递归删）：
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\2611ed9ca1\f1eef714ef4e` 236,151,391 B（mtime 2026-10-07T11:56:03）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\95ab4b1752\d34b6b30803f` 235,316,592 B（mtime 2026-10-07T12:09:55）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\9db175b4c0\ba67d14fc1ba` 235,304,630 B（mtime 2026-10-07T12:02:56）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\9db175b4c0\wi-pytest-nofail-1` 233,570,746 B（mtime 2026-10-07T11:40:29）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\95ab4b1752\bf3c2c20-full-suite` 231,514,140 B（mtime 2026-10-07T13:56:57）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\2611ed9ca1\control-premerge-pytest-1` 230,135,765 B（mtime 2026-10-07T11:48:24）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\4232e62f45\ceba3de4d827` 56,691,866 B（mtime 2026-10-07T14:31:43）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\4232e62f45\c08ef054d93f` 56,691,865 B（mtime 2026-10-07T14:54:28）
  - `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\4232e62f45\7d8d8479eab6` 56,691,864 B（mtime 2026-10-07T14:53:48）

preserve 今日仍在 6 项：`ArcheAxis.Knowledge.Green-v0.0.0-q04candidate-x64` 1,069,447,659 B；`ArcheAxis.Knowledge.Green-v0.0.0-q04c-x64` 970,771,559 B；`candidate-current-final` 292,921,821 B；`build-current` 222,491,231 B；`artifacts` 100,330,152 B；`core-candidate-r16` 97,726,878 B。
decide：`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\be268a2d33\f6998359de9b` 今日仍在，实测 133,536,505 B；判定理由原文：2 child path(s) could not be read; recoverability is not proven yet
**点名的未解事实冲突**：`aaos-ui-theme-20260926-02` 今日仍在盘上，而 2026-09-30 的历史记录称该精确历史目录已"完整归档后删除"（1,195 源文件 / 58 目录 / 264,282,128 B，恢复件 `aaos-ui-theme-candidate-packed-20261001.zip` + manifest）。本轮既不删也不改写那段历史，只把矛盾交出来待裁决。
再生路径（可恢复性）：run 目录由 `scripts/runtime/dev.py` 或 `scripts/ci/run_tests.ps1|.sh` 依已提交配方再生；`cargo build -p archeaxis-api --release`；`tauri build --bundles nsis`；`uv sync --frozen` 与 `python -m desktop.scripts.prepare_bundle`。**不得动** `.project-local/cache/*`（含 cargo 注册表，只能重下）、`.project-local/wi`、`.project-local/rt*`，以及 `D:\All projects\OS External Configuration` 下的共享工具根。本轮未删除任何文件、未发布、未改 ACL、未提权。

2026-10-07 F10 分离模型资产真实落库，并把"拒绝"从主机环境改成受控场景（分支 `codex/f10-supply-20261007`，基线 `origin/main=0b4024c0`，提交 `93f29b80` ＋格式化提交）：此前记录说"两枚 ONNX 资产缺、发布方在本机不可达"，两处都需要更正。**可达性不是问题，元数据才是**：`hf-mirror.com` 可取，`csukuangfj/sherpa-onnx-pyannote-segmentation-3-0/model.onnx` 与 `csukuangfj/speaker-embedding-models/wespeaker_en_voxceleb_resnet34_LM.onnx` 都带 sherpa 真正读取的元数据（分割件 15 键含 `sample_rate/window_size/receptive_field_*/num_speakers/powerset_max_classes/num_classes`；嵌入件含 **`framework`**，注意 sherpa 的报错文案说 `model_type` 是误导，`speaker-embedding-extractor-impl.cc:60` 读的是 `framework`）。反面证据同样重要：`onnx-community/pyannote-segmentation-3.0` 那份**零元数据**，sherpa 在 `offline-speaker-segmentation-pyannote-model.cc:Init` 直接 `exit(-1)`；WeSpeaker 原始导出也零元数据，而它更危险——`process()` 在短件上返回 1 段（nullptr 抽取器造成的**假通过**），在 16 秒双说话人件（`1-two-speakers-en.wav`）上以 `0xC0000005` 崩溃。所以本轮只放发布方自带元数据的两份，不放"补出来的"。
**入库位置与凭证**：`D:\All projects\Model library\sherpa-onnx\speaker-diarization\`，按 worker 的既有命名 `segmentation-3.0.onnx`（5,992,913 B，SHA-256 `220ad67c…938e1079`，与发布方 LFS 值一致）与 `speaker-embedding.onnx`（26,530,550 B，`e9848563da86f263117134dfd7ad63c92355b37de492b55e325400c9d9c39012`，同样与 LFS 声明一致；前 26,530,309 B 与 WeSpeaker 原件逐字节相同，多出的 241 B 只是元数据）；`LICENSE.segmentation.txt` 首行 `MIT License / Copyright (c) 2022 CNRS`，嵌入件的上游卡写 `license: cc-by-4.0`（卡文件 SHA `af2f6592…`），并**如实记下缺口**：k2-fsa 镜像仓本身不含任何许可证文件（列 26 文件、`cardData` 为空）。同目录 `PROVENANCE.md` 记 URL/重算 SHA/许可原文/元数据键/实跑结果，完整逐条证据在忽略根 `.project-local/inputs/diarization-candidates-20261007/manifest.json`。
**产品侧实跑（不是自制脚本）**：以 `ARCHEAXIS_MODEL_LIBRARY_DIR` 指向该库，`worker_diarize.probe()` → `capability: true`；`0.wav`（16 kHz 单声道 5.612 s）→ `state=diarized`、1 段 `SPK1 0.031–4.992`；`1.wav` → `state=diarized`；`8k.wav` → 仍按采样率如实拒绝（"the diarizer consumes 16000 Hz, this file is 8000 Hz; resampling is not done here"）。
**由此暴露并修掉的测试缺陷**：`diarize_job_end_to_end.rs` 的"无模型必须失败并点名两枚资产"依赖**主机恰好没有**这两枚资产——资产一入库，该测试在本机变红（`panic: a diarization with no models must not settle as success`），这是测试缺陷不是产品缺陷。改为让场景自己钉住供给：测试在临时目录生成一个薄壳，清空两个环境名后 `runpy` 执行真实 worker（`__file__` 仍是真路径，传输层解析照旧），拒绝从此与主机无关。**验证**：同一测试在"环境有模型库"与"无模型库"两种情况下均 `2 passed; 0 failed`；`tests/workers/test_diarize_worker.py` `7 passed`；`cargo fmt --all -- --check` 退出 0；`scripts/ci/check_document_authority.py` 与 `check_repository_conventions.py` 通过（合同 §7 的 `media.diarize` 行改写为"宿主事实 vs 候选事实"，未动任何路由计数）。
**明确未主张**：两枚资产**尚未**进入 `config/environment/capability-requirements.yaml` 的声明清单（声明即要求该路径在 CI 主机也解析成功，这一步单独做、单独受门），所以本轮的 ready 是"持有该库的主机"级，不是候选级；F10 的**准确率**依旧没有主张——说话人数与边界必须有人工 truth/prediction 对，未做；真实 Tauri 旅程与真人验收 NOT_EXECUTED。本轮未删除、未移动、未发布。
