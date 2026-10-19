# AAOS 视觉 QA 基线

## 2026-10-01 当前证据范围

当前用户采用提示词以 B10 最终可部署母版为最高视觉依据；B03 及其他批次只能补充，不能反向覆盖 B10。记录中的 Formal `di` 为 324 项受影响前端静态契约 PASS，`dj` 为桌面编译退出 0。已有原生 raster 渲染回读仅证明对应窗口、路由、主题可渲染，不代表完整原生交互、无障碍、动画或多 DPI 矩阵验收；这些仍 `UNVERIFIED`，整体视觉验收 `PARTIAL`。真实 Core 闭环及安装态健康也不能由上述证据推出。具体执行及发布边界见 [当前交接](STORAGE-CLEANUP-HANDOFF-20261001.md)。

下文 2026-09-22 至 09-28 的布局、PID、候选路径、测试数字和缩放读数均是历史快照。r70 的 324 项是其当时独立测试结果，不等同于 2026-10-01 `di` 的 324 项。旧 195 DIP rail 记录不代表当前源码的 280 DIP rail，也不构成当前几何验收。

## 历史 2026-09-22 基线

日期：2026-09-22
证据等级：`TESTED_LOCAL / READ_ONLY_AUDIT`。这是参考套件对照基线，不是当前 Avalonia GUI 已通过的声明。

## 1. 视觉基线

权威参考：

- `D:\\All projects\\UI套件\\03_B03_页面级UI与AAOS配色纠正_L3\\AAOS_配色纠正母版_v2.zip`
- `D:\\All projects\\UI套件\\04_B04_组件系统与DesignTokens_L4\\ArcheAxis_L4_组件系统_16张+Tokens.zip`
- `D:\\All projects\\UI套件\\05_B05_高保真产品页面_L5\\ArcheAxis_L5_12张高保真产品页面.zip`
- `D:\\All projects\\UI套件\\10_B10_最终版高保真可部署UI\\archeaxis_最终版_高保真可部署UI.zip`

| 检查项 | 验收标准 | 当前结果 |
|---|---|---|
| 背景 | 深空黑蓝 `#061118`，有层次，不是纯黑 | `PARTIAL`，当前 Avalonia 仍有纯黑层 |
| 主交互 | Aurora Teal `#1FC8C5` | `PARTIAL`，当前仍有 Indigo 硬编码 |
| 文字 | Ivory `#F3EFE6`，Muted `#96AAB4` | `PARTIAL`，存在纯白大面积使用 |
| 金色 | 只用于证据/可信/关键节点 | `NOT_ALIGNED`，尚未形成明确语义资源 |
| 面板 | Surface 层次、边框、内高光、可读密度 | `PARTIAL` |
| 页面 IA | Capture/Evidence/Original/Learning/Memory/Review 闭环 | `PARTIAL` |
| 原始证据与机器内容 | 必须有 provenance/derived 区分 | `PARTIAL` |
| 状态 | Loading/Empty/Error/Permission/Version | `PARTIAL` |
| 动效 | 低频、状态清晰、支持 reduced motion | `NOT_VERIFIED` |
| 响应式 | Desktop/Tablet/Mobile 规则 | `NOT_VERIFIED` |
| 可访问性 | 44px hit target、4.5:1、keyboard/focus | `NOT_VERIFIED` |
| GUI 回读 | 原生窗口截图、点击、状态读取 | `NOT_EXECUTED` |

## 2. 当前最明显的视觉问题

当前 Avalonia P3 更像“本地 Core 管理壳”，而不是参考套件中的 AAOS 产品工作台。问题不是缺少更多装饰，而是：

1. Token 没有集中管理，造成黑灰 + Indigo 的视觉漂移。
2. 右侧 Inspector 还不是 Evidence Reference Drawer / Source Chain。
3. 首页内容偏入口卡和状态卡，缺少最近证据、今日关注、待复习、原创进展和 Memory 摘要的产品层次。
4. Evidence、Original、Machine-derived、Learning 的来源关系没有形成统一视觉组件。
5. B09/B10 的 Command Palette、Toast、Modal、Drawer、Focus/Pressed 反馈尚未形成 Avalonia 组件契约。

## 3. 视觉修复验收顺序

1. Token/resource dictionary 对齐。
2. 工作台、资料库、学习三个现有页面先完成视觉层对齐。
3. Capture Inbox、Evidence Library/Detail 形成真实首用主链。
4. 增加 ProvenanceTag、SourceChain、EvidenceBadge、ReviewCard、MachineDerivedTag。
5. 再做 Memory Graph、Original Editor、Command Palette 和统一状态。
6. 使用真实原生窗口执行截图和点击回读；在此之前不得标记视觉 PASS。

## 4. 禁止回归

- 不得重新引入米白/金色三栏合并稿、橙黑 WORK-LAB 或三项目混合主题。
- 不得把星云、行星、金色光效扩大成海报化背景。
- 不得用静态 demo 数字证明真实 Core 状态。
- 不得把 AI 生成、机器推断和原始 Evidence 画成同一种卡片。

## 5. 2026-09-23 implementation delta

This section supersedes only the matching `PARTIAL` observations above; the
native GUI screenshot/click gate remains open.

### 5.1 Old baseline to current evidence map

The table in section 1 is retained as the dated 2026-09-22 baseline. It is not
the current implementation verdict. The following map is the current
interpretation and prevents the baseline labels from drifting into a new
failure claim:

| Baseline row | Current interpretation | Evidence boundary |
|---|---|---|
| 背景 | Semantic dark AAOS surfaces and layered panel resources are implemented; remaining pure-black surfaces require native visual review | `IMPLEMENTED_LOCAL / TESTED_LOCAL_BUILD`; GUI `UNVERIFIED` |
| 主交互 | Aurora Teal semantic action/status resources and readable dark action text are implemented; remaining hard-coded Indigo is outside the audited primary path | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` |
| 文字 | Ivory/Muted semantic resources are available and primary surfaces consume them; this is not a claim that every legacy text literal is gone | `IMPLEMENTED_LOCAL`; full visual sweep `UNVERIFIED` |
| 金色 | No new gold visual expansion was introduced; semantic evidence-gold alignment remains a follow-up | `PARTIAL / UNVERIFIED` |
| 面板 | Current Home, Learning, Evidence and responsive Inspector surfaces use the tokenized panel treatment; full suite-wide density alignment remains open | `IMPLEMENTED_LOCAL / TESTED_LOCAL_BUILD` |
| 页面 IA | Core route shell and Learning/Home/Evidence states are implemented; Evidence remains truthful unavailable when the Core read model is absent | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC`; live Core/UI `UNVERIFIED` |
| 原始证据与机器内容 | Provenance and unavailable boundaries are explicit; fabricated Evidence anchors/bundles are not used | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` |
| 状态 | Loading, empty, error, permission, unavailable and unknown semantics are represented on the audited surfaces | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC`; native rendering `UNVERIFIED` |
| 动效 | Motion tokens, restrained opacity transition, selected-state feedback and reduced-motion class are implemented | `IMPLEMENTED_LOCAL / TESTED_LOCAL_BUILD`; native timing `UNVERIFIED` |
| 响应式 | Exact 1024/1280 breakpoints, narrow action reflow and Inspector overlay path are implemented | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC`; DPI/native layout `UNVERIFIED` |
| 可访问性 | Automation names, keyboard command-palette semantics and reduced-motion handling are implemented on audited controls | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC`; contrast/focus readback `UNVERIFIED` |
| GUI 回读 | Still open; no native screenshot/click/accessibility readback is claimed | `NOT_EXECUTED` |

The reference suite path `D:\\All projects\\UI套件` is a design-reference
source only. It is not a runtime resource root, was not copied wholesale into
the product, and does not replace the fixed external-resource authority index.

- `AaosTheme.axaml` now exposes Aurora Teal semantic status resources, the
  120/180/280/420ms motion token references, a restrained opacity transition for
  buttons, selected FSRS grade feedback, and a dark primary-action text brush
  to avoid low-contrast ivory text on teal.
- The Learning surface now has an explicit empty-state illustration and next
  actions to Library and Jobs. The image is a project-owned generated asset at
  `apps/ArcheAxis.Desktop/Assets/aaos-knowledge-constellation-empty-state.png`;
  it is decorative and never represents Evidence or Core data.
- Learning navigation and Recovery navigation trigger their existing read-only
  Core refresh paths on entry. Review grade buttons reflow to one column under
  the narrow-actions breakpoint and no longer overwrite the independent Core
  correctness choice.
- Stable AutomationProperties names were added for the learning answer,
  correctness result, FSRS grades, and review status.
- Evidence Center remains a truthful `UNAVAILABLE` Core-contract state, not a
  fabricated visual list. Native GUI screenshot/click/readback remains
  `NOT_EXECUTED` because the current CUA bridge exposes no native window.

## 2026-09-27 Native Icon and Artwork Check

- The formal shell now uses the B10 280px text sidebar and one reusable AAOS vector icon control. VI icon concepts were redrawn as vector geometry; they were not cropped from the reference board. Aurora Teal/Monochrome palette switching is handled by dynamic theme resources.
- Home's previous planet/orbit decorative artwork was replaced by a small connected-node schematic. The screen reader label states that it does not represent live Memory Graph data. The current icon/artwork screenshot is `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r7/AAOS-UI-CANDIDATE-20260927-r7.png`.
- Debug build: `PASS` (0 warnings, 0 errors). Targeted UI contract: `PASS` (240 tests). Native screenshot confirms the Home window renders; it also confirms the page still has the older welcome/KPI/quick-capture composition and is not a B10 page-level visual pass.
- Compact viewport capture (1000x1000 physical px) confirms the sidebar changes to the four-icon bottom bar and the action stack reflows; it is not a full set of device DPI tests. Screenshot: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r7/AAOS-UI-CANDIDATE-20260927-r7-compact.png`.
- Remaining QA: capture and compare every route in both themes; verify tablet layouts and Windows scaling; replace/rebuild each page composition and any route-specific artwork to match the B10/B05 references. Overall visual acceptance remains `PARTIAL`.


## 2026-09-27 r23 运行时截图增量

- 候选目录：`.project-local/build/aaos-ui-preview/AAOS-UI-CANDIDATE-20260927-r23/`；窗口 PID 34856，标题显示 Core offline（未发现 Core binary）。
- 当前显示缩放 125%；使用原生 HWND `PrintWindow` 回读，脚本先启用 DPI awareness。截图共 22 张，尺寸均 1818×1172，路径：`.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r23/`。
- 覆盖 Home、Capture、Evidence Library、Originals、Human Learning、Machine Learning、Workspace、Memory Map、Search、Review、Settings；每页 Aurora 与 Monochrome 各一张。PNG 已核对存在且像素尺寸一致，主题切换后页面表面采样值不同。
- Evidence Detail 因没有真实 Core evidence anchor 无法进入；没有注入演示记录。只验证当前 125% DPI 下列出页面可渲染与双主题切换，不代表像素级母版通过、150% DPI通过或 Core 联机通过。总体视觉验收仍 `PARTIAL`。

## 2026-09-27 r25 并行页面与动效回归

- 新 Release 候选发布在 `.project-local/build/aaos-ui-preview/AAOS-UI-CANDIDATE-20260927-r25/`，PID 19004；窗口标题显示 Core offline。当前 r24 验收组覆盖 11 页双主题，接触表 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r24/aurora-contact-sheet.png`。Settings Aurora 原始回读为 1800×1125，接触表用统一 1818×1172 画布缩放补齐；该单张是辅助预览，不能作为原始像素证据。r24 截图仅证明旧候选运行态，不冒充 r25 回读。
- 本轮完成共享矢量图标扩展、B10 图标重绘应用 ICO、来源阅读器与 Evidence 页面图标/来源链交互、Memory Graph 节点悬停和脉冲连线动效、Review 翻面近似动效、首页 12 秒呼吸光效；Capture 真实导入期间显示扫描光带；Toast 调为底部居中、约 1.8 秒后淡出。reduced-motion 路径仍关闭动画。
- 验证：指定 UI 契约 **257 passed**；Release `publish` 成功，0 编译错误，1 条 `NU1900`（NuGet 漏洞索引不可达）；`git diff --check` 通过。原件阅读、Evidence Detail 的运行期真实数据路径仍需 Core 在线数据才能验证。
- 视觉结论仍为 `PARTIAL`：接触表中可见多页仍偏信息面板而非 B10/B05 的高保真密度与插画布局；像素级逐页对照、全尺寸/150% DPI、交互录屏及 Core-connected 状态均未完成。不得将双主题可渲染等同一比一复刻通过。

## 2026-09-28 r48 Human Learning B05 / responsive readback

- Reference: B05 `06_人类学习_Human_Learning_1920x1080.png`; screenshot: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r48/human-learning-1280x900.png`.
- Native route was invoked through Windows UI Automation and captured with `PrintWindow` at 1280×900 physical px while Windows scaling is 125%. Four metric cards render as two filled columns with all labels contained. The main study-plan/growth composition remains responsive; support details are collapsed but retain their Core-bound controls.
- `PrintWindow` succeeds and image was visually inspected. The candidate window reports Core offline; KPI values and history trend therefore remain truthful empty states. This is a single-page, Aurora-theme, single-window-size readback, not the full 12-route dual-theme/DPI matrix. Overall remains `PARTIAL`.
- Release build: `0 warnings / 0 errors`. Targeted route/UI contracts: `43 passed, 190 deselected`, one existing pytest warning (`cache_dir` option unsupported by the isolated UI runner).

## 2026-09-28 r50 Machine Learning B05 / responsive readback

- Reference: B05 `07_机器学习_Machine_Learning_1920x1080.png`; runtime screenshots `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r50/machine-learning-runtime.png` and `machine-learning-1280x900.png`.
- UI Automation invoked the Machine Learning route, and native `PrintWindow` captured 1818×1172 and 1280×900 physical px at current Windows scaling (125%). Four metric cards fill four columns at wide width and two columns at compact width; Knowledge Supply and the trend surface stack responsively.
- The page retains actual Core-backed status, but Core is offline and publishes no readiness overview or historical series. The B05 plotting area is present with a centered unavailable state; no demo values or trend line are fabricated. Single-route Aurora readback only; monochrome and additional DPI values remain unverified.
- Machine/Human Learning targeted contracts: `6 passed`; Release build `0 warnings / 0 errors`. Overall AAOS visual state remains `PARTIAL`.

## 2026-09-28 r51 theme token readback

- Selected Memory Graph node outline now uses `AaosGoldBrush`, which maps to Aurora gold and monochrome grayscale through the existing theme palette.
- Machine Learning page was captured at 1818×1172 in Aurora and Monochrome after switching through the live Settings selector: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r51/machine-learning-aurora.png` and `machine-learning-monochrome.png`.
- Current selected page is Machine Learning in Monochrome; PID 29992 responds. This verifies theme application on this page, not every route. Full acceptance remains `PARTIAL`.

## 2026-09-28 r56 runtime route / motion integration

- Candidate: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r56/`; normal Release build, DLL SHA-256 `267DE1A3F68307FD02985AE72F9B3992549ED5E868C9D4C5B99EA64BB214CA79`.
- UI Automation confirms a responsive visible window (1818×1172 physical px, 120 DPI / 125% scaling), Core offline title, the updated `ArcheAxis 轨道星品牌标记`, and Capture route controls including `快速捕获` and `最近捕获回执列表`.
- Import scan motion is connected to the real import lifecycle and app reduced-motion preference. Runtime visual pixels are not captured: `PrintWindow` returns a blank surface and cropped `BitBlt` is unavailable in this host. No screenshot is represented as visual proof.
- Focused contracts: 269 passed. This route/runtime readback is partial and does not complete the full page/theme/viewport acceptance matrix.

## 2026-09-28 r57 B03/B05 primary navigation readback

- Desktop rail width: 195 DIP (13.5% of 1440 DIP base canvas), matching the reference composition. All 11 primary routes render an icon and Chinese label. Desktop lockup includes `KNOWLEDGE OS · EVIDENCE · MEMORY`; mobile collapses to the bottom rail and hides the desktop tagline.
- Live r57 UI Automation readback found all 11 labels and the tagline in the visible window. Window responded at 120 DPI/125% scaling; Core remains offline. This validates runtime controls and navigation structure, but not pixels because native screen capture remains blocked by this host.
- Ten targeted suites: 277 passed. Release candidate and exact DLL hash are recorded in `AAOS-UI-FIDELITY-STATUS-20260927.md`; overall status remains `PARTIAL`.

## 2026-09-28 Avalonia-native dual-theme route raster readback / r70

- Added candidate-only `--ui-capture <png> <route>` startup mode. It sets reduced motion, routes the existing Avalonia window, applies the selected palette (`AAOS_UI_CAPTURE_THEME`), then renders the attached Window visual tree through `RenderTargetBitmap` at its current `RenderScaling`. It bypasses OS desktop capture permissions and does not affect normal launch. Candidate source paths: `apps/ArcheAxis.Desktop/Program.cs`, `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`.
- A 16-route matrix × Aurora Teal / 黑白深色 was rasterized to `.project-local/tmp/<route>-<aurora|mono>.png`: Home, Capture, Library, Search, Source Reader, Knowledge, Original Editor, Memory Map, Human Learning, Review/FSRS, Evidence, Machine Learning, Workspace, Settings, Jobs and Recovery. All are 1800×1125 px at the current 125% display scale. Pixel samples confirm theme backgrounds Aurora `#091821` and Monochrome `#101316`. Contact sheet: `.project-local/tmp/aaos-16-routes-contact-sheet.png`.
- Raster review found the Review schedule chart's narrow y-axis label overlapping and clipping. Replaced the rotated/stacked label with a concise `张` unit marker and retained the full accessible name and tooltip `数量（张）`. Rebuilt and recaptured Review in both palettes; the label is legible and no longer overlaps. Runtime frames: `.project-local/tmp/review-aurora.png`, `.project-local/tmp/review-mono.png`.
- Final y-axis marker after the image-review iteration is `张` (full unit retained in accessible name and tooltip). Candidate publish: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-native-capture-r70/`; Release, self-contained win-x64. DLL SHA-256 `1BFC1F4F577FB583F58FB09B2090DA8A968906AF999D083E6AAF5D261A4BF26D`. Build emits only environmental NuGet vulnerability-index warning `NU1900`.
- Release verification: 26 focused UI and visual contract files, `324 passed in 1.92s`; `git diff --check` and Avalonia XAML parse pass. Normal r64 preview was separately launched and reports Core offline and responding.
- The PNGs show the Avalonia Window visual tree without native OS frame, and capture mode does not synthesize route data; unavailable states remain visible. Full interaction animation and multi-DPI matrix, and exhaustive page-by-page comparison against every B03/B05 reference, remain incomplete. Overall acceptance remains `PARTIAL`.

## Historical screenshot archive

The Green old-checkout r7 acceptance screenshots referenced above are retained inside `D:\All projects\Record\AAOS-project-archives\2026-09-29\green-old-checkout-acceptance.zip` at `acceptance/AAOS-UI-CANDIDATE-20260927-r7/`. The archive SHA-256 and exact restore steps are recorded in [the cleanup audit](../history/storage-cleanup/2026-09-29/green-old-checkout-acceptance-compaction.md).
