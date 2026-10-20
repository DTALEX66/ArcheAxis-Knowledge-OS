> Historical snapshot: 2026-09-27 至 2026-09-29 的过程记录，非当前状态或执行权威。
> 当前清理、交付、验证与阻塞请读 [2026-10-01 交接](STORAGE-CLEANUP-HANDOFF-20261001.md)。

## 现行解释（2026-10-01）

- B10 最终可部署母版是最高视觉依据；Aurora/黑白共用布局、状态及缩放规则。正文中此前 B03 最高或 B10 仅作风格参考的判断已被取代。
- r97/r38/r30、旧截图数、PID、HEAD、测试/构建及上传结果仅证明对应历史快照；不能推断今天界面、完整原生交互/DPI/动画或安装态已经验收。
- “49 项失败全为旧标题”是当时判断，后续发现并修复真实交互行为问题，不能沿用为全部豁免理由。
- 旧76项保留/未授权、原位展开仍在、未上传及换连接器建议都是早期阶段记录，今天以最新交接和删除回读为准；不再要求沿用旧认证建议。
- SHM PARTIAL、wheel UNVERIFIED、未知归属与历史拒绝如实保留；当前整体仍 PARTIAL，静态/编译通过不等于用户数据库或完整产品健康。

原快照源 SHA-256：`a878df3ee36e4f15f985590d46c9710ed4444b712fe92fd728b9f265e8dc2d17`。以下保留历史正文，只统一文本格式，不将旧叙述重新认定为当前真值。

---

# AAOS UI 收敛与验收状态（2026-09-29）

## 状态

`PARTIAL`。formal 与 Green mainline 当前源代码已同步本报告列出的前端写集，双主题和 16 路由均通过 Release 构建、定向合同测试与原生渲染捕获。本报告不是“母版像素级完全复刻”或“已替换 Green 根目录产品”的声明。

## 当前写集

- Capture：压缩输入入口、保留未保存草稿状态、保存入口在 Core 持久化契约未接入时保持禁用；最近捕获列表仅呈现本次真实 Core 回执。
- Search：查询与已接入筛选保留；Core 尚未投影的来源/主题/时间筛选由清楚的 unavailable 状态代替，移除窄屏无标签禁用下拉框。
- Evidence：采用分类标签与纵向来源项；无 Core Evidence anchor 时呈现明确空态，不填入母版演示条目。
- Home / Learning / Machine：Home 在窄屏采用两列 KPI，极窄宽度退回单列并压缩卡片；Learning/Machine 窄屏 KPI 高度收至 112 DIP，桌面高度不变。所有指标继续显示 Core 实际值或 unavailable，不添加样例数字。
- Icon：按 VI `Icon_System` 对照调整 Growth、Connection、Thinking 与 `NavigationDot`。使用 Avalonia 矢量绘制；图板只支持语义判断，线宽与每条路径的像素几何尚未逐图 diff。

## 验证与可视检查

- Release：formal 和 Green mainline 各一次；`0 warnings / 0 errors`。Avalonia BuildServices 尝试写用户级 `buildtasks.log` 时收到 `UnauthorizedAccessException`；为完成编译，命令设空 `UsedAvaloniaProducts` 跳过其统计/遥测目标。这一构建证明编译通过，不证明 Avalonia 统计目标通过。
- 定向 UI 合同：formal `31 passed`；Green mainline `31 passed`。各有项目现存 `PytestConfigWarning: Unknown config option: cache_dir`，不影响退出码。
- 原生捕获矩阵：Green mainline 最新 Release **64/64 PASS**，16 路由 × Aurora/Monochrome × 1440/720 DIP。清单含截图 SHA-256、PNG 尺寸、字节数、候选程序集 SHA-256 与联系表哈希；目录：`D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline/.project-local/acceptance/AAOS-UI-VERIFY-20260929/final/`。
- 125% Windows 显示缩放下已目视复核 Home、Capture、Search、Evidence、Learning、Machine 单图及四张联系表。窄屏 Home 首屏有快速捕获和今日学习入口；Search/Evidence/Capture 的空态均为真实 Core 边界。窄屏 Learning/Machine 主内容在首屏仍会延续到下方滚动区，未将母版示例数据伪造为真实内容。

## 未完成与限制

- `--ui-capture` 矩阵证明 Avalonia 控件树的双主题/两窗口尺寸渲染，不替代普通启动后的键鼠/焦点/文件选择/真实 Core 联调验收。
- 动效（Hero orbit、Capture scan、Toast、Inspector drawer、Review flip、Memory edges）没有本轮录屏或动画帧差分，播放结果仍 `UNVERIFIED`；代码中的 reduced-motion 分支不等于播放验收。
- 仅当前 Windows 125% 缩放环境完成矩阵；100%/150%/200% DPI、跨显示器移动和触控验收为 `NOT_EXECUTED`。
- B03/B05 整页图包含样例数据，当前只做构图/语义参照；尚未为所有路由逐组件做像素差分。应用图标来源、完整 B01 wordmark lockup、8 个核心 glyph 的几何精确度仍有待视觉标定。
- 当前代码/构建位于 Green 内嵌任务树，Release 输出在该树 `.project-local/build/...`；Green 根的 `ArcheAxis.exe` 与现有启动入口没有被替换或覆盖。Green 根目录集成启动、真实 Core 连通和用户报告的 dotnet 异常复现状态均为 `UNVERIFIED`。

## Recovery / 写入边界

本轮不删除任何资产、不覆盖 Green 根应用、不提交或推送。验收截图与构建位于两仓忽略的 `.project-local`；旧截图仍保留在原验收路径。源代码通过双树定向修改同步；如需回退，只回退此报告列出的 UI 源码/合同测试文件，不要清理其他 dirty 文件。

## 2026-09-29 双仓 B10 主窗口壳层增量

- Formal 主仓与 Green mainline 的桌面 rail 已对齐到 B10：280 DIP 主栏、11 条 hollow-dot + visible label 导航；Home stats、hero、dashboard 共享 `<=840 DIP` 单列边界。页面实现仍有差异，`MainWindow.axaml` SHA-256 Formal `1CA20F87AEA004353E2D07C5F13287B77AE5870F28414B006D7A33B1CFF5BABC`、Green `FF967DB93A823C01064A04E3A850C2F0AFF38B9478DB17E8B5CDDD5D3F0AD13D`；这不是全写集 hash parity。
- Formal 定向 rail/responsive 合同 **8 passed**，Release publish PASS；扩展旧 UI 合同 **170 passed / 49 failed**，失败都在旧页面标题结构断言。Green mainline UI 合同 **185 passed / 2 skipped**，Release publish PASS。
- 全仓测试仍因 CI-only Python 环境缺 `pymupdf` 而在 collection 阶段中断；原生窗口、Core 联通、多 DPI 和最新截图矩阵尚未重跑。上述构建/合同结果不构成完整验收或 Green 根启动集成证明。最新体积和外溢数据见同目录 `AAOS-SPILLOVER-MIGRATION-20260928.md`。

## 2026-09-29 final-source Home hero and capture readback

- Green mainline restored the B03/B10 Home welcome hero using the already-present Aurora and Monochrome artwork; palette changes select the matching art. At `<=840 DIP`, the image collapses and the hero copy spans the row; Memory Graph remains a separate lower dashboard card.
- Current-source verification: Release self-contained `dotnet publish` succeeded with exit 0 / 0 warnings / 0 errors into `.project-local/build/aaos-ui-home-master-20260929/publish`. Desktop DLL SHA-256 `5EA4B443E2DB83D1F35D4FB833EDBE9F3A9A02466BB1B70C087DE276FC7815FB`; EXE SHA-256 `1FAB20CF029A072A9BAF5C7901231B7ABAF37A8AAE6E0615031648D9ECEED1D7`. Home artwork contracts: 2 passed.
- A fresh matrix was generated from that publish, not historical r97 or the earlier publish: `.project-local/acceptance/AAOS-UI-VERIFY-20260929-final-source/capture-manifest.json`. It covers 16 routes x 2 themes x 1440/720 DIP at current Windows 125% scaling: 64/64 PASS, 0 fail. Every PNG SHA-256 matches its manifest and IHDR dimensions; 32 desktop images are 1800x1125 px and 32 narrow images are 900x1125 px. Aurora and Monochrome Home desktop captures were visually reviewed and show different matching hero artwork.
- Current screenshot evidence is native Avalonia `--ui-capture` readback. It does not prove normal user-startup, pointer/keyboard complete flows, Core online integration, motion playback, 100/150/200% DPI, multi-monitor behavior, touch, or every component's pixel equality with B03/B05. Overall UI remains `PARTIAL`.
- Green root stable launcher remains v0.6.14; current mainline publish has not replaced the installed runtime. R6 Local Green replacement/readback/rollback/Owner gates and release freeze remain in effect.

## 2026-09-29 final-source v2: Home header + hero

- Mother-page audit found and fixed the Home heading row hidden by `WorkspaceHeadingBar.IsVisible = section != "home"`. Home now shows title, descriptor and route actions before the welcome hero; the desktop capture was visually checked against B03/B10. Formal and Green mainline share this visibility fix.
- Green mainline focused contracts: `pytest tests/test_home_heading_visible_contract.py tests/test_home_b10_master_composition_contract.py tests/test_home_uses_motherboard_art_direction.py -q` -> **3 passed**. Release self-contained publish to `.project-local/build/aaos-ui-home-master-20260929/publish` exit 0, no warnings/errors.
- Final matrix is `.project-local/acceptance/AAOS-UI-VERIFY-20260929-final-source/capture-manifest.json`, generated `2026-09-29T05:05:48` local. Current DLL SHA-256 `86AC5F0F68C319CD32C065FD5391A640378128212E97DE965A987CBBA3478EB9`; EXE SHA-256 `1FAB20CF029A072A9BAF5C7901231B7ABAF37A8AAE6E0615031648D9ECEED1D7`. 16 routes x 2 palettes x 1440/720 DIP -> **64/64 PASS**. All screenshot hashes and dimensions read back: 32 x 1800x1125 px + 32 x 900x1125 px at 125% Windows scale.
- `home-aurora-1440x900.png` and `home-monochrome-1440x900.png` are now available for visual review. The Home hero collapses at <=840 DIP; the narrow screenshots were captured, but no per-route pixel-diff against all B03/B05 assets is claimed. Complete keyboard/pointer workflows, real Core first-use integration, motion playback, 100/150/200% DPI, multi-monitor and touch remain unverified. UI remains `PARTIAL`.
- This is still source/publish + Avalonia native capture evidence, not ordinary Green-root launcher, Core-connected use, crash reproduction, installation, or rollback evidence. Green root remains stable v0.6.14 and unchanged.

## 2026-09-29 Evidence 指标响应式复核

- Formal 与 Green mainline 的 Evidence 指标卡统一使用响应列数：内容宽度 `<900 DIP` 时为双列，`<420 DIP` 时为单列，其余四列；每张卡显式重排到正确 Grid 行列，避免窄窗四列挤压标签。
- 双仓 Release build（`--no-restore -p:SelfContained=false -p:RuntimeIdentifier=`）均 PASS，0 warnings / 0 errors。输出位于各自 `.project-local/build/dotnet/ArcheAxis.Desktop/bin/Release/net10.0/`。
- Green mainline 当前构建成功捕获 Aurora Evidence 1440×900 与 720×900 DIP，以及 Monochrome 720×900 DIP，截图位于 `.project-local/acceptance/current-evidence-responsive/`；图像复核显示 Aurora 桌面指标四列、窄屏双列，Core 离线状态如实呈现。Monochrome 桌面图本次未形成文件，不能据此声明该增量截图覆盖双主题全尺寸。
- `pytest` 本次未执行：Formal `.venv` 的 uv trampoline 在受限执行环境返回 `permission denied`，可用的 Codex Python 不含 `pytest`，uv cache 初始化遇到本机既有路径冲突；没有安装依赖或修改用户级路径。当前有编译证据，无该合同测试的执行证据。
- 整体 UI 仍 `PARTIAL`：本次只收敛该缩放缺口，不代表 B05 全路由像素差分、交互/动效录制、多 DPI/跨屏/触控或 Green 根发行版集成已完成。

## 2026-09-29 母版插画与应用资源打包审计

- 直接查阅 B10 母版页面：其知识图为内嵌 SVG，母版没有可单独打包的首页 PNG/行星照片类光栅图。当前 `MainWindow.axaml` 使用 `AaosMemoryGraphView` / Canvas 矢量控件；`AaosHomeHeroOrbit` 是未挂到主窗口的组件。
- 源码引用审计发现，应用仅将 `Assets/aaos-app-icon.ico` 用作窗口图标。`ArcheAxis.Desktop.csproj` 已由递归 `Assets/**` 改为只嵌入此 ICO；Formal/Green mainline 两端 csproj SHA-256 一致。其他图像仍保留在各自 Assets 源目录供审计与迭代，不再无差别嵌入应用资源包。
- Formal Assets 为 12 files / 9,887,224 B；Green mainline 为 14 files / 11,823,692 B。除 22,964 B ICO 外，其余 11 个 Formal 文件均未被页面引用；Green 另有两个未引用 Earth 版本图片。经 Release 编译后读取程序集字节流，两个 DLL 均包含 ICO 资源名，不含三个抽样首页/品牌图文件名；源码资源项清单是主要排除证据。
- 双端 `Release` 编译验证通过，均为 0 warnings / 0 errors（为避免本轮锁定/生成 apphost，使用 `SelfContained=false, UseAppHost=false`；因此这是程序集与资源项编译验证，不是自包含绿色版发布验证）。实际独立发布包减量尚未测量；不能把源图逻辑字节总数等同于发布包减量。
- **更正前文的素材说法：** 本报告早先曾记“Home 使用 Aurora/Monochrome artwork”。本次当前源码逐引用复查没有找到这些文件的 UI 引用，所以不应把那条历史描述当作当前绑定证据。矢量图形是否达到 B10 图板的像素级复刻仍未验收。

## 2026-09-30 历史发布输出归档与 DLL 哈希时间线

- 仅将两个非当前的 Green mainline 发布目录迁出 build：`aaos-ui-home-capture-draft-20260929` 与 `aaos-ui-earth-hero-20260929`。home-master 当前目录保留。两个源目录合计 450 个文件 / 454,415,128 B；未发现数据库、WAL/SHM、日志、锁、data 子目录或重解析点，遍历无错误。删除前进程名检查未发现 `ArcheAxis.Desktop`/`dotnet` 进程；系统进程路径查询返回拒绝访问，因此这是名称级检查。
- 归档位于 `D:\All projects\Record\AAOS-project-archives\2026-09-30\green-mainline-historical-publish-20260930.zip`，170,123,195 B，SHA-256 `01DB0A64AB6D2BC96982E5B15F53F086D6676D4CE64C91860FB9B48598489BEB`。ZIP CRC、450 个成员路径集合、每成员长度与 SHA-256、源文件删除前复核均为 PASS。精确清单：`D:\All projects\Record\AAOS-project-archives\2026-09-30\green-mainline-historical-publish-20260930.preflight.json`；最终回执：`D:\All projects\Record\AAOS-project-archives\2026-09-30\green-mainline-historical-publish-20260930.final.json`。
- 两个归档候选的 Desktop DLL SHA-256 分别为 draft `1766E5424B6797D9A4DD762C07193467D863CFE58994375E2A2816C678CF85A3`、earth-hero `4BD7CA8869425907B1789E11F6619E77AE601A844C79A1388CEFE6D08A0E840E`；它们是不同历史构建，未当作彼此或 home-master 的重复包。
- DLL 哈希时间线复核：较早的 Current-source publish 记录值为 `5EA4B443E2DB83D1F35D4FB833EDBE9F3A9A02466BB1B70C087DE276FC7815FB`；随后 2026-09-29 05:05:48 的 final-source 验收矩阵记录 DLL `86AC5F0F68C319CD32C065FD5391A640378128212E97DE965A987CBBA3478EB9`。2026-09-30 00:54:38 只读回读 home-master 原路径，当前 DLL 为 `86AC...3478EB9`（10,690,560 B，mtime 2026-09-29 05:03:32），EXE 为 `1FAB20CF029A072A9BAF5C7901231B7ABAF37A8AAE6E0615031648D9ECEED1D7`，与 final-source 记录一致。报告中的 `5EA4...` 保留为较早发布哈希；它不是当前 DLL 的哈希。此处据顺序记录为同名输出后续重建，不推断未记录的构建步骤。
- Green mainline 两个历史目录现已不存在。恢复命令：先将 ZIP 解压到空的隔离目录，再按 preflight 清单校验 450 个文件路径、字节数和 SHA-256；校验通过后，将归档顶层两个目录移回 `D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline\.project-local\build\`。不要覆盖 home-master。
- D 盘可用空间读数从归档前 167,531,474,944 B 到删除后 167,392,899,072 B（整盘净变化 -138,575,872 B，受并发磁盘活动影响）；本项目 build 展开量与归档量的逻辑净缩减为 284,291,933 B，不将整盘读数宣称为清理收益。
