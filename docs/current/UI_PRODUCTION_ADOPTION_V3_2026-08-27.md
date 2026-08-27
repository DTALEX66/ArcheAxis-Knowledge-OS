# OSUI v3 生产接入与纠偏记录

- 状态：`LOCAL VERIFIED / CLOUD EXACT-SHA PENDING`
- 日期：2026-08-27
- 产品：ArcheAxis Knowledge｜星环知识平台
- 设计基线：`OSUI/archeaxis-knowledge-ui-v2/`
- 生产入口：`frontend/`（主 Tauri WebView）+ `app/workspace/ui/`（loopback Workspace）

## 1. 为什么需要本次纠偏

OSUI v3 的“证据档案室 / Archive Desk”设计于 2026-08-12 进入仓库，2026-08-13 又上传了清理后的完整 bundle，但长期被当作 `Mock Adapter / UNBOUND` 原型保留。随后 v0.6.7、v0.6.8、v0.6.9、v0.6.10、v0.6.11 五个公开版本继续发布旧 Workspace 壳层；发布门只验证功能、浏览器、Tauri 和安装生命周期，没有验证“权威设计稿是否进入生产”与“界面语言是否一致”。

这不是设计缺失，而是生产接线和验收门缺失。用户指出后，本次把视觉接入、真实数据绑定、中文一致性、路线图与设计历史一起提升为发布前置条件。

## 2. 权威设计输入

| 输入 | 作用 |
| --- | --- |
| `DESIGN-v2.md` | Archive Desk / 液态玻璃视觉命题、排版与构图 |
| `app.css` | 壳层、研究台账、阅读纸面、证据关系、学习工作台 token |
| `liquid-glass.css` | Apple 风格玻璃导航、主题、焦点和强制色模式 |
| `app-v3.js` | 16 条逻辑路由与领域组件构图 |
| `component-manifest.json` | ProductTitleBar、SpaceRail、Inspector、ReceiptDock、EvidenceMap 等组件合同 |
| `route-data-dependency-matrix.md` | 原型 Adapter 方法与真实绑定缺口 |
| `workspace-overview-v2-preview.png` | 工作台总览视觉基准 |
| `visual-lesson-studio-v3-preview.png` | 视觉课件工作室视觉基准 |
| `production-handoff-manifest.json` | 明确原设计为 mock/unbound，不能冒充生产实现 |

## 3. 已接入生产的设计语言

- 中文优先的产品标题、导航、检查器、活动坞和状态文案；仅保留产品英文名与必要领域术语。
- 冷白/雾灰底、深蓝墨色、低饱和蓝青锚点，不使用紫色营销渐变。
- 系统衬线标题 + CJK 系统正文；取消全大写英文眉题。
- 顶部玻璃栏、一级空间栏、二级导航、上下文与证据检查器、折叠活动坞。
- “研究台账 + 下一步”主工作面，替代同构指标卡片首页。
- 原件→转换块→主张→证据束关系地图。
- 视觉课件静态分镜、场景索引、时间线与证据脚注规划面。
- 空间记忆二维地图、文字等价路线和低动效替代规划面。
- 路线图与设计史页面，区分已运行底座、已吸收能力、保留规划与历史交付。

生产 CSS：

```text
app/workspace/ui/assets/osui-v3.css
app/workspace/ui/assets/osui-production.css
```

生产交互与真实 Adapter：

```text
app/workspace/ui/assets/production-ui.js
app/workspace/ui/assets/app.js
```

主 Tauri WebView 同步使用：

```text
frontend/src/app/App.tsx
frontend/src/spaces/WorkspaceSpace.tsx
frontend/src/design-system/tokens.css
frontend/src/presentation/labels.ts
```

## 4. 真实数据绑定

| 用户页面 | 真实端点/能力 | 失败边界 |
| --- | --- | --- |
| 工作台总览 | `GET /workspace/api/status` | 状态不可用，不保留旧值 |
| 资料导入 | `POST /workspace/api/intake/url`、`POST /workspace/api/intake/upload` | 原件不变，显示可恢复失败 |
| 资料库工作台 | Vault inspect/search/file/write/backups/restore | 哈希冲突拒绝写入 |
| 任务中心 | jobs、delivery、lifecycle | 不显示伪进度或内部编号 |
| 研究复核 | `GET /workspace/api/research` + approval command | 外部内容仍是候选 |
| 候选知识 | `GET /workspace/api/knowledge` | 不把候选冒充可信知识 |
| 学习路线 | `GET /workspace/api/learning` | 学习事件不提升机器真值 |
| 掌握与反馈 | `GET /workspace/api/evolution` | 人/机状态分离 |
| 机器知识 | `GET /workspace/api/runtime/candidates` | 仅已批准内容可供机器使用 |
| 证据中心 | lifecycle、PDF、EvidenceAnchor、exchange/backup | 内容寻址只读，写入需要真实回执 |
| 知识画布 | `/kb/canvas` | 候选研究不自动进入画布 |
| 系统诊断 | `GET /workspace/api/status` | 只显示聚合事实 |

`production-ui.js` 不包含 Mock 数据；未具备调用上下文的方法返回明确的“不可用/请选择真实对象”，不会构造样例成功。

## 5. 中文优先词典

| 旧混杂文案 | 生产文案 |
| --- | --- |
| LOCAL ONLY | 仅限本机 |
| CONTEXT & EVIDENCE | 上下文与证据 |
| LOCAL JOB CENTER | 本地任务中心 |
| HUMAN REVIEW QUEUE | 人工复核队列 |
| Outbox / Receipt | 待投递记录与回执 |
| Mastery Feedback | 掌握与反馈 |
| Approved Runtime Knowledge | 已批准的机器知识 |
| Status / Source / Evidence | 状态 / 来源 / 证据 |
| JOB / DELIVERY / REVIEW | 任务 / 投递 / 复核 |
| TRUTH BOUNDARY | 真值边界 |
| Roadmap | 产品规划 |

允许保留但需中文语境：`ArcheAxis Knowledge`、`Claim（主张）`、`Evidence（证据）`、`Canvas（画布）`、`PDF`、`API`、`FSRS/BKT`。

## 6. 规划能力的呈现规则

视觉课件和空间记忆属于正式保留产品层，但当前只展示：

- 设计结构；
- 数据/证据依赖；
- 静态和无障碍替代；
- 开放前置条件。

禁止展示播放、生成、三维漫游等假操作。只有真实对象、能力探针、失败恢复、性能、无障碍和学习效果证据全部通过后，才可改为“已接入”。

## 7. 生产验收

- 新增 `tests/test_workspace_ui_design_contract.py`，阻断 Mock/UNBOUND、旧英文眉题和 OSUI 资产未加载。
- A0 Chromium 必须验证 OSUI 主工作面、中文可见文案、真实接口读回、视觉课件/空间记忆规划入口和 console 0 error。
- 视觉截图必须与 `workspace-overview-v2-preview.png` 对比，不再仅凭 DOM selector 和功能绿测验收。
- Tauri/NSIS 发布门必须在 UI 视觉门之后运行。

### 本地执行证据

- React/Vitest：`74 passed`，覆盖中文一级空间、Archive Desk 构图、恢复壳、状态翻译、首运行空 workspace id、单一 launch-token 认证，以及视觉课件/空间记忆规划入口。
- Frontend production build：TypeScript + Vite PASS。
- Loopback A0 Chromium：工作台、键盘、PDF、投递、六空间学习循环 PASS。
- OSUI 多尺寸真实 Chromium：4 个路由 + 390×844 + 360×640，console/page errors = 0；报告位于 `.hermes/task-artifacts/ui-redesign/osui-v3-visual-acceptance.json`。
- Tauri frontendDist + 真实本地 API：1280×800 PASS；报告位于 `.hermes/task-artifacts/ui-redesign/tauri-frontend-osui-v3.json`。
- Windows Rust：`cargo check --all-targets` 与 release build PASS。
- **真实原生 Tauri WebView**：External Dev 启动后发现并修复两项首运行阻断：客户端重复发送 Authorization + launch token、以及 dev WebView origin 未进入精确 token 认证分支；修复后原生窗口显示“后端状态：本地可用”，并完成“工作台 → 资料库”真实点击读回。
- 原生主工作台截图：`.hermes/task-artifacts/ui-redesign/tauri-native-osui-v3.png`，SHA-256 `f044523cb762373df45eb61f883df544e5fd8ae3f245bb38bcf103435320e9bd`。
- 原生资料库点击截图：`.hermes/task-artifacts/ui-redesign/tauri-native-osui-v3-library.png`，SHA-256 `69f070ff4019250260f1576b484cfefef84eba80e92ac444f27f473060b652d8`。

当前尚未完成的层是 GitHub exact-SHA CI、NSIS candidate lifecycle 和后续版本公共资产 readback；因此本地 UI 可判 PASS，但不得声称修复已经发布。

## 8. 不可重犯

后续发布不得仅因功能、测试、CI 和 installer lifecycle 全绿就宣称产品完成。只要权威设计未进入生产、界面仍混用语言、规划/历史/底座不可见，发布门就必须失败。
