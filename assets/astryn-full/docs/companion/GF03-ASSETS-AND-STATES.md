# GF03 轻量人物资产与状态表现（小栖学习伴侣 v1）

分支 `feat/astryn-learning-companion-v1` · 任务包 ASTRYN-COMPANION-20261013 · 日期 2026-10-13

任务卡要求"先复用当前原创 SVG 和九状态，改进符合宇宙主题的清晰度与尺寸表现；输出首页、半身或头像、阅读侧边三种呈现资源和 profile；外观升级保留原始源与版本；区分文本事件驱动表情与真实音频口型"。写实 / Live2D / VRM 升级资产由 MINIMAX DESIGN 生产（简报见 `docs/companion/GF03-VISUAL-ASSET-BRIEF.md`，含 §9 装载与调用约定）；本任务完成 ASTRYN 工程侧全部可独立部分。

> **N1 更新（2026-10-14）**：MINIMAX DESIGN v2 升级资产已回传并落库（`PENDING_EXTERNAL` 解除），默认渲染器切换为 `xiaoqi-raster-v2`（决策 D018/D019）。本卡下方写于 2026-10-13 的状态快照中，涉及 v2 交付状态、清单 schema、`origin` 与 `upgraded/v1/` 目录内容的陈述，以文末「v2 落库更新（N1）」节为准。

## 交付内容

| 交付物 | 位置 | 说明 |
| --- | --- | --- |
| 呈现档定义（三种） | `src/avatar/render-profiles.ts`（新增） | `AVATAR_VIEW_PROFILES`：`hero`（首页腰上半身 240×280）、`avatar`（对话头肩近景 96×99.84，viewBox `10 16 100 104` 保证完整状态环+光环入画）、`sidebar`（阅读侧边 168×196）；`avatarViewForMode('embedded'\|'panel')` 供壳层直接选档；全部 viewBox 在 120×140 源画布内以数值断言 |
| 渲染器 seam 扩展 | `contracts/avatar.ts`、`src/avatar/xiaoqi-svg-renderer.ts`、`src/avatar/xiaoqi-avatar.ts` | `AstrynAvatarRenderer.renderMarkup(frame, size?, view?)` 追加可选第三参数 `AstrynAvatarViewProfile`（加法变更：现有自定义渲染器与调用不受影响）；`XiaoqiAvatar` 按 viewBox 计算宽高比（120:140），SVG 根增加 `shape-rendering="geometricPrecision"` |
| 状态-动作映射 | `src/avatar/state-action-matrix.ts`（新增） | 九状态 → 六种身体预设之一 + `expressionDriver:'text-event-frame'`（文本事件帧驱动，非音素口型）+ `audioDriver:null` + 昂贵资源占位 `{activeAudio:1, expensiveRenderer:1}`；`interrupted/awaiting_approval/executing/failed → idle`（预设由状态环承载），`completed → nod`；`point` 明确列入 `RESERVED_BODY_PRESETS`（"解释选中内容"手势待 GF05/GF07 接线，避免静默死枚举） |
| 渲染失败回退 | `src/presentation/companion-view.tsx`、`src/presentation/astryn.css` | `AvatarView` 的 renderMarkup 抛错与 mount 抛错均捕获 → 渲染 `data-testid="astryn-avatar-fallback"` 的纯文本状态卡（`role="img"`，aria-label 注明"渲染失败，已回退文本"）；错误详情不入 DOM（测试断言 `boom-secret-detail` 不在文档中）；mount 成功路径卸载时 dispose 恰一次 |
| 壳层接线 | `src/presentation/companion-shell.tsx` | 按 `mode` 选档：`embedded→hero`、`panel→sidebar`（嵌入页与侧栏共用同一会话管理器，档位随呈现切换） |
| 角色资产清单 | `assets/character/STATE-ASSET-INDEX.json`（新增）+ `README.md` | GF03 当轮 schema `astryn.character-assets/v1`：九状态、`provenance.origin='original'`、`realPersonReference=false`（真人红线显式记录）、runtime（rendererId/三档 profile/表情驱动声明）、版本策略：`v1 original-svg-baseline ACTIVE` 与 `v2 upgraded-raster-2d PENDING_EXTERNAL`（producer MINIMAX DESIGN，targetDir `assets/character/upgraded/v1/`，deliveryRule 要求交付权属条款）；`.gitkeep` 预留。**N1 更新（2026-10-14）：已升 schema v2**——`origin='ai-generated'`、v2 `DELIVERED`（22 直用 + 3 派生 PNG 逐张 bytes/sha256 登记，`.gitkeep` 已随之移除），详见文末更新节 |
| 测试 | `tests/avatar/render-profiles.test.ts`、`tests/avatar/state-action-matrix.test.ts`、`tests/presentation/avatar-fallback.test.tsx`、`tests/boundary/character-assets.test.ts`（均新增） | GF03 当轮 7 + 6 + 5 + 6 = 24 项（详见下方对照表）；**N1 更新**：`character-assets.test.ts` 随落库扩至 11 项（落库字节/派生链/缺口登记/目录反枚举），四文件现为 7 + 6 + 5 + 11 = 29 项 |

## 验收对照

| 验收条目 | 证据 |
| --- | --- |
| 每种状态可辨 | 既有 `companion-shell.test.tsx` 九态两两可辨（环色+眼型+嘴型+字形四元组唯一，且 `renderXiaoqiMarkup` 产物两两不同）；新增 `state-action-matrix.test.ts`：九状态全覆盖校验、同帧确定性（同帧两次渲染 markup 相同）、帧序列 0–3 逐帧互异（离散帧可辨且不随机） |
| 隐藏暂停无用渲染 | 既有壳层测试：点击 `astryn-hide` 后 `astryn-avatar-host` 从 DOM 消失、`astryn-show` 恢复；GF02 的 `session-manager.test.ts`：零视图 `renderingPaused=true` 快照推送暂停、在途流照常入账（本任务未改动该链路，回退路径也不引入常驻渲染——失败态是纯文本节点） |
| 渲染失败可回退 | `avatar-fallback.test.tsx`：renderMarkup 抛错 → 回退文本卡出现且含当前状态名；mount 抛错 → `waitFor` 出现回退卡；错误详情不出现在 DOM；正常渲染器不误触回退；view profile 透传至 DOM（`viewBox="10 16 100 104"`、`width="96"`）；确认挂载成功路径卸载 dispose 恰一次 |
| 不把文本帧推进宣称成中文音素口型 | `state-action-matrix.test.ts`：九态 `expressionDriver==='text-event-frame'`、`audioDriver===null`，且 STATE_ACTIONS JSON 中无 `/viseme|音素/` 字样；`character-assets.test.ts`：清单 runtime.expressionDriver 与代码同源值为"text-event-frame（…非音素口型，不得宣称音素口型）"；`describeXiaoqiFrame` 输出同步携带 `expressionDriver` |
| 不把参考真人作为已获权利人物资产 | `character-assets.test.ts`：GF03 当轮断言 `provenance.origin==='original'`、`realPersonReference===false`、note 含"真人"红线句；v2 升级版本 `PENDING_EXTERNAL` 且 `deliveryRule` 含"权利"（交付前必须给出权属条款，未回传不解锁）。**N1 更新**：断言随落库升级——`origin==='ai-generated'`（外部 AI 生产、平台条款，非真人参考）、`realPersonReference===false` 不变、v2 `DELIVERED` 且 `deliveryRule` 仍含"权利"（现行断言见该文件「来源为 AI 生成并如实登记缺口，真人素材红线被明文声明」一例） |

## 证据（本机实测）

### 门禁

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-224417.log`（首跑 224036 为代码定稿；本份为合同档更新后的终版重封，两级树哈希均可复算）
- 阶段：`STAGE=lint EXIT=0`、`typecheck EXIT=0`、`test EXIT=0`、`build EXIT=0`、`record EXIT=0`、`anchors EXIT=0`
- 回执：`docs/verification/gates.json`，78 个源文件（scopes: contracts/src/dev-host/tests + 7 个根文件），终版树哈希 `59d3d7a1b2f3c2e696fc8f5f30f82fbd5fd1a5b07a26f4f21bb2bef35cadc4b4`（PROJECT_CONTRACT.yaml 在扫描范围，合同档更新后按终版重封），全绿=true；封存时 `git.head` 为 `7e9c2d62cb7c`（GF03 简报提交，本任务代码提交落在其上）
- 锚点：`.project-local/runs/anchors.json` head `7e9c2d62cb7c5f36d27ac4223726f7b1109b3735`，trackedFiles 130，problems `[]`
- 测试：23 个文件 171 通过（GF02 基线为 19 文件 147 通过；+4 文件 +24 项）
- 构建产物：`index-h1SbPDct.css` 8.58 kB（gzip 2.04 kB）、`index-0m_KqSw4.js` 222.42 kB（gzip 73.28 kB；GF02 为 221.05 kB，增量来自映射表与回退分支）

### 开发宿主浏览器实测（DOM 结构化读数）

- `npm run dev` → `http://127.0.0.1:5183/`（日志 `.project-local/runs/dev-gf03.log`、`dev-gf03b.log`）
- 面板档（默认 `mode=panel`，即 sidebar profile）：`astryn-avatar-host > svg[data-testid=astryn-avatar]` 实测 `width="168"` `height="196"` `viewBox="0 0 120 140"` `data-visible-state="idle"`；无 `astryn-avatar-fallback` 节点；`.astryn-root` scrollWidth 358 = clientWidth 358，`documentElement` scrollWidth 396 = clientWidth 396（无横向溢出）
- 嵌入档（点击 `devhost-mode-embedded` 后重读）：svg `width="240"` `height="280"` `viewBox="0 0 120 140"`（hero profile）；无回退节点；396/396 无溢出
- 控制台（服务器存活时新开导航后读数）：3 条消息 = vite connecting/connected（debug）+ React DevTools 提示（info），0 错误 0 警告
- 进程卫生：两次 dev server 均按 PID 终止（34956、38604），终止后 `netstat` 无 LISTENING 残留
- 如实说明：该表面无截图能力，以上为结构化 DOM 读数（与 GF02 同口径）；服务器终止后曾出现 13 条 `ERR_CONNECTION_REFUSED`（HMR/资源对已终止端口的重连），非页面缺陷，fresh 导航读数已隔离该噪声

### 边界核对

- `tests/boundary/character-assets.test.ts` 校验清单与代码同源（states 集合 = 会话态 + 任务态去 `none`；renderProfiles 键 = `AVATAR_VIEW_PROFILES` 键；rendererId = `xiaoqiSvgRenderer.rendererId`；targetDir 在磁盘存在）
- 既有 `no-third-party-assets` 断言保持：SVG 不引用外链素材（`<image|href=|xlink:href=` 均无）。**N1 更新**：`assets/character/upgraded/v1/` 已落 22 张直用 PNG + `derived-alpha/` 3 张派生件，全部逐张登记并由 C11 目录枚举测试从反方向钉住（磁盘上出现未登记 PNG 即红）

## 如实记录的设计决定

1. **回退卡只显示状态名，不显示底层错误**：错误文本可能携带宿主/模型细节，进入 DOM 等于把内部信息暴露给页面；测试以"抛错消息不在文档中"作为显式断言。
2. **`point` 预设保留但声明为未接线**：九状态里没有"指向"态，若静默舍弃该预设则枚举死亡无告警；改为 `RESERVED_BODY_PRESETS` 带原因说明，并由测试锁死"保留集与已达集无交集且 point 在其中"。
3. **契约扩展只加可选第三参数**：`renderMarkup(frame, size?, view?)` 是加法变更，第三方/宿主自定义渲染器无需改动；`hero/sidebar` 共用全画布，"清晰度"增量来自 viewBox 精确比例与 `geometricPrecision`，不新造素材（N1 更新：MINIMAX v2 已于 2026-10-14 落库并成为默认渲染器，D018 由此履行；v1 SVG 按本条承诺保留为回退下限）。

## 阻塞与残余

- **MINIMAX v2 升级资产已交付并落库（N1，2026-10-14）**，原 `PENDING_EXTERNAL` 解除，详见文末更新节；残余项：MINIMAX 侧 429 重试仍需显式授权、`pose_listening` 本地去背推导如实中止（`ABORTED_BG_NONUNIFORM`）、生成种子未暴露（`seedExposure=NONE`，无法复现同批画面）。
- **浏览器证据为结构化读数**（该表面无截图），与 GF02 同一口径；像素级走查待有截图能力的表面（GF10 联合验收时统一补）。
- 三档 profile 的"宇宙主题清晰度"工程侧只保证几何（viewBox/比例/无外链/性能属性）；审美升级依赖 v2 资产，不在本任务宣称。

## v2 落库更新（N1，2026-10-14）

- 清单升 `astryn.character-assets/v2`：`provenance.origin='ai-generated'`（producer MINIMAX DESIGN，平台条款），`realPersonReference=false` 与真人红线句保留；`runtime.defaultRendererId='xiaoqi-raster-v2'`（九态位图静帧驱动），`xiaoqi-svg-v1` 降为注册表 index 0 回退下限（D018）。
- 落库：`assets/character/upgraded/v1/` 22 张直用件 + `derived-alpha/` 3 张本地派生件（thinking/completed/failed，登记算法与来源链、来源哈希闭合），逐张 bytes/sha256 双向核对（清单→磁盘、磁盘→清单；未登记 PNG 即红）。
- 缺口如实登记（D019）：四张 429 去背失败件中 3 张本地推导（`DERIVED_LOCALLY`）、`pose_listening` 中止（`NOT_LANDED_RUNTIME`）；圆形头像安全区 `MEASURED`（躯干下缘 2.48% 像素出界、头部完整，报告 `.project-local/runs/avatar-safe-area-report.json`）；口型帧 `SKIPPED`（无音素口型，不得宣称）。
- 渲染链：位图加载失败有图像级回退（`data-renderer-fallback=image-error`）与未注册 id 的显式回退（v1），scenes 注册表同源由门禁测试钉住。
- 本节事实的登记处：`assets/character/STATE-ASSET-INDEX.json`、`docs/authority/DECISIONS.md` D018/D019、`tests/boundary/character-assets.test.ts`（12 项）。

## v2 资产补齐与验收更新（2026-10-15）

- `pose_listening` 缺口闭合：v2 二次背景场拟合法本地派生成功（derived-alpha 第 4 件，`DERIVED_LOCALLY`，runtimeUsable=false 作 C 组体态参考）；四张 429 全部有本地过渡件，原生去背 retry 仍在交接清单 H1（需授权）。同日边缘质量 v3：软边带内按颜色投影重估 alpha（只缩不增、实心区与 v2 逐位一致），软边 30851→22320 px、疑似光晕 5889→3519 px，暗底放大目视对比通过（注：灰蓝发色接近背景灰，光晕计数含合法发缘）；回执 `.project-local/runs/derived-alpha-v3/derive-report-pose-listening-v3.json`。
- E 组口部/眨眼帧：`SKIPPED` 解除为本地候选——口闭合/口半开/双眼闭合三帧（对 speaking 母版高斯捏合，ROI 外零差异像素机验 PASS + 目视 PASS，`ACCEPTED_LOCAL`，runtimeUsable=true）；口张开/眼睁帧 = 母版本身不另存。帧交换接线属宿主 UI（CODEX 范围），规格与素材清单见 `docs/companion/CODEX-HANDOFF.md` C1，不在此宣称。回执 `.project-local/runs/derived-frames/acceptance-e-frames.md`。
- A3 头部补充页：从 `turnaround_3d_sleepwear_v3` 裁正/侧/背头部特写拼版（derived-refs，runtimeUsable=false，分辨率受源图限制已标注）。
- D 组三呈现构图本地派生（简报 §D，全部从 idle 母版原生像素画布重排，无缩放无重绘；派生前清除母版 10 粒去背残点 264px，已登记）：home 4552×2528（主体左 1/3、右侧 2/3 全透明机验）、avatar 904×904（眼线 45.9%H、头宽 523≤圆内径 777 机验）、sidebar 1255×2510（1:2、左右边距 175/177px 机验、顶留白 18%H）；runtimeUsable=false 供 CODEX 侧呈现参考；回执 `.project-local/runs/derived-refs-d/derive-report-d-group.json`。
- v1 SVG ↔ v2 raster 状态视觉一致性盘点（只读）：`STATE_VISUALS` 九态键集合 = 契约 `AstrynVisibleState` = raster `STATE_IMAGES` 键集合；九态运行时文件 sha256/bytes 与登记全对账 PASS；v1 各态 eye/mouth 语义与简报九态表情表逐条对应无冲突。已知差异如实记录：① v1 的 ringColor/glyph（! ? > ✓ ×）不进入位图（红线：环与字形由 UI 叠加）；② v1 speaking 为四帧 MOUTH_CYCLE 矢量口型循环，v2 为静帧，E 组候选帧是未来帧交换素材；③ failed 态 v1 eyeMode 为 closed-glitch，位图实为歉意垂眼（语义近似，非缺陷）。
- 概念图两件（写实机甲方向）登记于 concepts 节，仅参考永不进运行时；2026-10-16 用户确认两套造型并存，机甲线立为第二服装线（H4 定夺），生成材料（身份块/机甲服装块/参考图/M-A1'/M-B 提示词/命名/落库要求）已备于简报 §10，待 MINIMAX 侧生成。

## derived-alpha 三件过渡件 v3 回灌（2026-10-16）

- 复用 `pose_listening` v3 的颜色投影细化（平场变体）回灌 thinking/completed/failed 三件过渡件：软边带内按颜色投影重估 alpha（只缩不增）；不变量 6 项全成（实心计数与字节、原背景保持与字节、未变更软边字节逐一不变）。三件均有实益故替换落库：软边 30996/37490/32153→21495/24658/20235 px、疑似光晕 17586/14650/14479→7211/5196/5889 px（暗底 before/after 全图 + 3 组 2× 放大对比逐一目视 PASS）。
- 碎点评估：三件 detached 碎点经 4× 放大接触表目视判为发丝残段（艺术内容），不做 despeckle（与 listening 母版处置不同）；近背景色发缕可能被细化淡出，如实记录。清单三条目 bytes/sha256/算法/注记已同步（runtimeUsable=true 保持）。
- 回执 `.project-local/runs/derived-alpha-states-v3/derive-report-states-v3.json`，脚本 `.project-local/runs/derive-alpha-states-v3.py`。

## 回滚

本任务线性提交于 `feat/astryn-learning-companion-v1`；回滚 = `git revert` 本提交。契约变更（renderMarkup 可选参数、`AstrynAvatarViewProfile`）为加法，回滚不破坏 GF00–GF02。未改写已推送历史。
