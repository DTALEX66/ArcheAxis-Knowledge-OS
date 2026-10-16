# ASTRYN 完整交接提示词（2026-10-13，M0 上传后）

> 本文件是把当前会话全部上下文压缩后可直接粘贴给新会话的交接提示词。所有数字与 SHA 均为本轮实测，不要从历史或推断改写。粘贴时整段复制。

> **时效披露（2026-10-14 第五轮追加）**：本文件的实测基线定格于 2026-10-13（M0 上传后）。此后历经第三轮（GF00–GF11 任务包）、第四轮（风险收口 R1–R4 与测试审计 A1–A3）、第五轮（MINIMAX 人物落库 N1、全量审计 N2/N3、文档轮 N4）。**§3 现场基线、§4 已交付结构、§7 验收与风险现状的逐项数字已被后续轮次超越**（保留为当时回执）；接手时以 `docs/current/STATUS.md`（含第四/五轮节）与 `docs/verification/gates.json` 为现行基线。关键漂移：tracked 106 → 194；源码树锚 64 → 108 文件；测试 118 → 353（37 文件）；CI 运行 9 次 → 14 次（10 绿 4 红，另 1 次 PR 运行绿；最新绿 run 38600518023 @ 9cfd258）；DECISIONS D001–D017 → D001–D019（D018 渲染器切换、D019 缺口资产纪律）；风险 Q1/Q2/Q7/Q9 等已完成（见 §9 注记）；默认渲染器为 `xiaoqi-raster-v2`（原创 SVG 降为回退下限）。**§5 架构不变量、§8 证据纪律、§10 坑清单、§11 绝对不做仍全部现行有效。**

---

## 0. 一句话任务

接手 Project ASTRYN｜星栖，工作目录 `D:\All projects\ASTRYN`。M0 已实现、已上远端、CI 全绿；你的任务是按 §9 队列继续推进可自主项，并在授权边界内如实回填证据。**不要只输出计划。**

## 1. 启动前必须先读（顺序有意义）

1. `AGENTS.md`、`AUTHORITY.md`、`PROJECT_CONTRACT.yaml`、`docs/current/STATUS.md`
2. `docs/tasks/M0-ACCEPTANCE-TRACKER.md`（A00–A19 逐项验收与实际证据）
3. `docs/tasks/M0-EXECUTION-HANDOFF.md`、`docs/tasks/AGENT-START-PROMPT.md`（M0 授权范围原文）
4. `docs/tasks/archive/ASTRYN-DEVELOPMENT-START-V1.0.txt` + `ARCHIVE-RECEIPT.md`（原始启动任务，只读）
5. `docs/architecture/astryn-m0.risk-quality.md`（风险登记册 Q1–Q9）、`astryn-m0.structurizr.dsl` + `.evidence.md`
6. `docs/architecture/AAOS-HOST-CAPABILITY-MAP.md`（宿主能力实测）、`docs/verification/M0-VALIDATION.md`、`DESIGN.md`

## 2. 用户原始约束（逐字，仍然有效）

> 仅写 ASTRYN；AAOS 按任务只读。不要自动 commit、push、发布、付费调用或修改全局配置。合成测试、真实模型和 AAOS 集成必须分别报告；遇到阻塞继续完成独立任务。

例外（已发生，勿重新追问）：用户下达「全部上传」构成 Git 初始化与推送授权（DECISIONS **D015**，覆盖 D003 与合同的 `no_git_initialization_or_remote_write`，原文保留以显示决策链）。**该授权不自动延伸到 force push、历史改写、分支删除或发布**；后续普通正向 push 沿用同一意图执行，但每次都要报告远端 SHA 与 CI 结果。

## 3. 现场基线（本轮实测，勿从历史推断）

| 项 | 实测值 |
| --- | --- |
| 远端 | `https://github.com/DTALEX66/ASTRYN`，**public**，分支 `main`；推送均为快进，未 force、未改写历史 |
| HEAD 一致性 | 每次推送后 `git ls-remote` 与 `git rev-parse HEAD` 逐字符比对；最后一次已验证对：`0f63c93` @ run 38393747795 success。**本文件自身所在的提交会让 HEAD 前移一次，这是预期而非笔误——新鲜度永远以 `git ls-remote` 为准** |
| CI 规则 | 结论一律写成 `run N @ SHA`，不写"当前绿"（见 §8）；截至 `0f63c93`：main 上 9 次运行 = 5 绿 4 红，逐次归因在台账 A18 |
| tracked 文件 | 106（含本文件；`git ls-files \| wc -l`，远端 tree blob 数应与之相等） |
| 源码树锚 | `gates.json.sourceTree`：64 文件，sha256 `f843508d56f3385696b1…`（scopes 只含 `contracts/src/dev-host/tests` + 7 个根文件，**不含 `scripts/` 与 `.github/`**） |
| 门禁 | lint/typecheck/test/build 退出码全 0；`Test Files 14 passed (14)`、`Tests 118 passed (118)`；build 67 modules，`206.39 kB / gzip 67.48 kB`，443 ms |
| 归档原件 | `docs/tasks/archive/ASTRYN-DEVELOPMENT-START-V1.0.txt` 在 HEAD 处 **20960 字节 / 527 行**，SHA-256 `866C151DB45E0D0ADFCAFA9F059A836DF859D830420B65AB95673FDD4B08450F` == 收据；在 `b42eee2` 处曾被规范化成 **20434 字节** |
| 依赖 | lockfile 320 包，许可总账见 `docs/development/DEPENDENCIES.md`（无 GPL/AGPL/LGPL；唯一 CC-BY-4.0 是构建期 `caniuse-lite`） |
| Dev 端口 | `http://127.0.0.1:5183/` |

**环境绑定（PATH 里没有 node/npm，必须显式绑）**

```bash
export PATH="$HOME/AppData/Local/hermes/tools/node-26.7.0-win32-x64:$PATH"   # Node 26.7.0 / npm 11.19.0
export npm_config_cache="D:/All projects/ASTRYN/.project-local/runs/cache/npm"
```

- Git 全局：`core.autocrlf=true`、`init.defaultBranch=master`、`url.git@github.com:.insteadof=https://github.com/`（所以 HTTPS 实际走 SSH）。**不得修改全局配置**；仓库用 `.gitattributes` 压制：`* text=auto eol=lf`，`docs/tasks/archive/** -text -eol`。
- 提交身份沿用已有 `DTALEX66`。
- 本地产物一律进 `.project-local/runs/` 与 `.project-local/artifacts/`（已 gitignore，不作正式证据）。
- AAOS 本地根存在且为 Git 仓库（核验时 HEAD `0574c3ac`、分支 `codex/conversation-closure-20261013`、工作树干净）；E:、F: 禁止未授权访问。

## 4. 已交付结构（105 个文件的骨架）

- `contracts/`（12 个 ts，不依赖 React）：`protocol.ts`（`astryn-1` 信封、`isTaskAuthoritative`、`parseAstrynEventEnvelope`）、`events.ts`（`KindToPayload`、`createEvent` 注入 `kind`）、`state.ts`、`character.ts`（`XIAOQI_PROFILE`）、`memory.ts`、`action.ts`、`avatar.ts`、`presentation.ts`、`conversation.ts`、`context.ts`、`host.ts`、`index.ts`
- `src/`（24 个文件 + `.gitkeep`，与 `git ls-files src | wc -l` = 25 一致）：`companion/{reducer,session-guard,prompt-composer}.ts`、`interaction/companion-controller.ts`、`adapters/{aaos-bridge,openai-compatible,sse,model-registry,synthetic-conversation,synthetic-host,synthetic-script,conversation-event}.ts`、`avatar/{xiaoqi-avatar,xiaoqi-svg-renderer,state-visuals}.ts`、`presentation/{companion-shell.tsx,companion-view.tsx,mode-registry.ts,use-companion.ts,astryn.css}`、`memory/{policy,synthetic-fixture}.ts`、`context/synthetic-context.ts`、`index.ts`
- `tests/`（14 个测试 + `setup.ts`）：`companion/{reducer,guard,authority}`、`adapters/{sse,openai-compatible}`、`interaction/controller`、`memory/policy`、`context/selection`、`presentation/{companion-shell,approval-flow}`、`boundary/{no-sensitive-apis,presentation-modes,design-tokens,architecture-risks}`
- `dev-host/`：`index.html`、`main.tsx`（StrictMode）、`app.tsx`、`dev-config.ts`、`dev-host.css`、`server/dev-model-proxy.mjs`
- `docs/`：`architecture/`（AAOS 能力图谱、所有权矩阵、Structurizr DSL + understanding + evidence、风险登记）、`verification/`（S0 基线、M0 验证报告、design-a11y、gates.json）、`research/OPEN-SOURCE-MATRIX.md`、`development/`、`authority/DECISIONS.md`（D001–D017）、`current/STATUS.md`
- 根：`DESIGN.md`、`design.qa.yaml`、`PROJECT_CONTRACT.yaml`、`AUTHORITY.md`、`AGENTS.md`、`README.md`、`vite.config.ts`、`tsconfig.json`、`eslint.config.js`、`.gitattributes`、`.env.example`、`scripts/record-gates.mjs`、`.github/workflows/ci.yml`

## 5. 架构不变量（改代码前先复述一遍）

- 所有权：**ASTRYN** 拥有人格、陪伴互动、角色表达、渲染呈现；**AAOS** 拥有模型服务、记忆、上下文、任务、权限、权威存储。
- 只经**有类型、有版本、有权限**的 Host Adapter 通信。**禁止**直接写 AAOS SQLite/CAS、**禁止**第二套正式前端、**禁止**第二长期记忆主库（Dev Host 只是开发工具）。
- 八类 Port：`AstrynHostPort`、`AstrynConversationPort`、`AstrynMemoryPort`、`AstrynActionPort`、`AstrynContextPort`、`AstrynAvatarRenderer`、`AstrynPresentationMode`、`AstrynCharacterProfile`。
- 事件信封 `astryn-1`：`protocol / eventId / sessionId / requestId / taskId / seq / originSeq / source / trust / emittedAt / payload`。
- **任务状态权威三重防线**（D008）：① 类型层不存在"模型可表达任务完成"的类型；② 信封层 `isTaskAuthoritative()` 要求 `trust=authoritative` 且 `source ∈ {host-action, host-task}`；③ 校验层无 `AstrynReceiptVerifier` 即降级为 observed。模型正文说"任务已完成"不得改变 `task.status`。
- 守卫拒收原因（`session-guard.ts` 判定顺序）：`PROTOCOL_MISMATCH`、`INACTIVE_SESSION`、`INVALID_EVENT_KIND`、`TASK_EVENT_NOT_AUTHORITATIVE`、`TASK_EVENT_MISSING_TASK_ID`、`SETTLED_REQUEST`、`UNKNOWN_REQUEST`、`NON_MONOTONIC_SEQ`、`OUT_OF_ORDER_ORIGIN_SEQ`；校验器另发 `REPLAYED`。
- 三类边必须区分：**权威事件边**（host-task/host-action 回执，唯一能改任务状态）、**观测事件边**（会话流式，`trust=observed`）、**合成边**（`SYNTHETIC` 夹具）。宿主合同缺失处显式标 `BLOCKED_BY_HOST_CONTRACT`，不得用夹具冒充。
- 渲染 seam：UI 必须经 `AVATAR_RENDERERS` 注册表 + `selectAvatarRenderer()` 取驱动（D012），不得直接 import 具体渲染实现；`originSeq` 用于跨请求乱序检测。
- 控制器构造**无副作用**，宿主订阅只在 `attach()` 建立（D009）。
- 呈现模式：M0 只实现 `embedded` / `panel`，其余带 `blockedBy` 声明。
- 密钥面：真实凭据只进 dev 代理进程环境，不进浏览器、不进仓库；代理只监听 loopback 并做 Origin 白名单（D017：测试与文档中不得出现字面凭据样式串，需要时运行时拼装）。

## 6. AAOS 宿主实测事实（只读核验，2026-10-13）

- **无通用流式 chat completion**；会话只有 `POST /api/v1/machine/answers`（一次性、无流式）。AAOS 自己用双方法 404 测试断言该面不存在。
- 记忆写入只能作为 candidate：`POST /api/v1/knowledge-items`；晋升永远 human-only；**Consumer 是闭枚举且不含星栖** ⇒ 星栖侧 `AaosMemoryPort.probe()` 返回 `BLOCKED_BY_HOST_CONTRACT`。
- 上下文：`GET /api/v1/machine/contexts` + `POST /api/v1/ai/context-packets`；**无"当前选区/授权选择"合同**。
- 任务链：`POST /api/v1/jobs` → `POST /api/v1/jobs/{id}/executions`（需 `idempotency-key`、`deadline_ms` 1..300000，**202 = 持久化声明而非完成**）→ 轮询状态 → `GET /api/v1/jobs/{id}/outputs/{kind}`（带 `sha256` 与 `authority_effect: candidate_or_measurement_only`）。
- **宿主无事件推送面**，只能轮询；另有 `/api/v1/system/version`、`/api/v1/capabilities`。
- 技术栈事实：Tauri 2.11.5，SQLite `SCHEMA_VERSION=12`。
- 这些假设会过期 ⇒ 风险 Q2，漂移检查脚本尚未做。

## 7. 验收与风险现状

**台账**：A00 PASS、A01 PASS、A02–A04 PASS(SYNTHETIC/画面 REAL)、**A05 NOT_TESTED / NO_EVIDENCE**、A06–A08 PASS(SYNTHETIC)、A09–A10 PASS、A11/A12 星栖侧 PASS + 宿主侧 BLOCKED、A13 PASS、A14 PASS、A15 PASS、A16 PASS(AAOS 零写入)、**A17 UNVERIFIED**、A18 PASS、**A19 NOT_EXECUTED**。**整体 M0 = PARTIAL**；A05/A17 未过不得写成全项 COMPLETE。

**风险登记册**：Q1 `dispatch` 未收窄（权威事件仍可被同 realm 构造）、Q2 AAOS 假设漂移未监测、Q3 版本锚点（已闭环）、Q4 `evidenceLevel` 由实现自填、Q5 记忆/选区真实接入缺位、Q6 真实模型从未跑过、Q7 reduced-motion 只有 CSS 声明级证据、Q8 CI 从未运行（已闭环）、**Q9 CI 无字节保真步骤**。

## 8. 证据与回执纪律（用户会逐条核对，历史上已三次被推翻）

- 级别词只用：`NO_EVIDENCE / SYNTHETIC / INTEGRATED / REAL`；状态词只用：`PASS / PARTIAL / BLOCKED / NOT_TESTED / NOT_EXECUTED / FAIL / UNVERIFIED`。构建 ≠ 运行，测试 ≠ 宿主集成。
- **报告只转录本轮从工件读到的数**，不重述记忆里的结论；引用一个 PASS 必须同时给出它绑定的 SHA 与范围。
- CI 结论写成 `run N @ SHA`：docs-only 提交会再触发一次 CI，"当前绿"永远会被自己过期。
- 回执必须绑定被测量字节；`record-gates.mjs` 必须带 `--stage name=EXIT`，**空 `stages` 现在会 exit 2**；阶段码从日志解析，不手写。
- 已知且有意为之的滞后：`gates.json` 的 `git.head` 是**测量时刻**的 HEAD，承载这份回执的提交必然前移一位。判断回执是否有效看 `sourceTree.sha256` 是否等于当前源码字节，而不是看 head 是否等于最新提交。
- 长链命令写日志文件再读回执；`set -o pipefail`；不要用 `head/tail` 的退出码当结论（曾把 `"node" 不是内部或外部命令` 的空跑误报成 `test=0`）。
- 追正本身是新断言：写"CI 拦下了 X"之前先 `gh run view --json jobs` 读失败步骤名（本轮就是靠它发现旧归因错了）。
- 40 位 SHA / 树哈希一律脚本生成后回读，不手敲。
- 公开仓库里不得出现 Windows 用户名、`E:\`/`F:\` 私人路径、内部交接词、字面凭据样式。

## 9. 任务队列（按真实缺口排序；未获授权的不自动推进）

| # | 任务 | 完成定义 | 所需授权 |
| --- | --- | --- | --- |
| 1 | **Q9 CI 字节保真步骤**：`ci.yml` 增加对收据内每个归档文件断言 `git cat-file -s` + `sha256sum` | 植入一次字节改动即变红，正常态绿 | 可自主（先做，成本最低且是已发生过的缺陷） |
| 2 | **Q1 收窄 `dispatch`**：权威事件只能经 `ingestReceipt` 进入 | 有"直接 dispatch 伪造权威事件在架构上不可达"的负向测试 | 可自主 |
| 3 | **Q2 AAOS 漂移检查**：只读脚本比对 AAOS HEAD 与能力图谱记录，纳入 `npm run verify` | 漂移自动变红 | AAOS 侧只读即可自主 |
| 4 | **Q7 reduced-motion 真机验证**：CDP `Emulation.setEmulatedMedia` 实测动画停止 | 有一条浏览器级证据 | 可自主 |
| 5 | **Q4 `evidenceLevel` 由宿主签发** | 端口不再自填 | 可自主，但建议与 P1 挂载一并定 |
| 6 | **A05 真实模型验证** | 一次真实流式 + 一次取消 + 一次上游错误，记录非敏感参数，不存私人正文 | **用户提供 base URL/凭据/模型名；付费调用需明确许可** |
| 7 | **A17 / P1 AAOS 集成与原生挂载** | 同一 AAOS 工作区跑通一次角色交互闭环，任务态来自真实 job 状态 | **修改 AAOS 正式源码需单独授权** |
| 8 | floating/pet/voice-only、口型/打断（P2） | 不在近期范围，只保留接口 | 后续单独任务 |
| 9 | **A19 用户验收** | 由你（用户）判定 | 人类 |

**2026-10-14 队列状态注记**：第 1–4 项（Q9/Q1/Q7/Q2）已于**第四轮全部完成**并各配回归证据与浏览器级实测（见 `risk-quality.md` §整改序与 `STATUS.md` 第四轮节）；第 5 项（Q4）仍未做，建议随 P1 挂载一并定；第 6 项待用户凭据、第 7 项待 AAOS 集成授权、第 8/9 项同原状。

## 10. 本轮踩过的坑（不要重复付出学费）

1. **jsdom 全绿 ≠ 浏览器正确**：控制器在构造函数里订阅宿主，React 18 StrictMode 会重跑 `useState` 初始化器，被丢弃的实例消费掉一次性回执（`verify()` 标记 receiptId），真实实例拿到 `REPLAYED` → 审批卡永不出现。修成纯构造 + `attach()`，并加"构造控制器不得订阅宿主"回归测试。
2. **手搓信封漏 `payload.kind`**：守卫接受、reducer 静默空转。加 `INVALID_EVENT_KIND`，`ingestReceipt` 改用 `createEvent`。
3. shell 在 `deps` 变化后仍复用旧 controller；`cancel()` 先 settle 再派发 `turn.cancelled` 导致自拒；abort 时未 `reader.cancel()` 使 pending `read()` 不结。
4. **axe 报 0 违规但 `color-contrast` 对 19–21 个节点是 incomplete**（文字压在径向渐变上）——"未判定"不是"通过"；把渐变移出文字层后 incomplete 归零。
5. `::placeholder` 未声明（3.73:1）与 disabled 用 0.45 透明度（3.82:1）都不过 WCAG；375px 有横向溢出（scrollWidth 414）需 `min(380px,100%)` + `@media(max-width:420px)`。
6. `el.focus()` 不触发 `:focus-visible`，会误报"缺焦点环"；要真键盘 `Tab`。
7. **绝对路径与 ROOT 二次拼接**会让递归静默返回空（`record-gates.mjs` 曾报 26 文件而非 64；boundary 测试同病）；`fileURLToPath(import.meta.url)` 在 jsdom 里失败，改 `process.cwd()` + package.json 存在性守卫。
8. vite `root=dev-host` 导致 vitest "No test files found"，需显式 `test.root`。
9. `core.autocrlf=true` 破坏归档字节（20960→20434），靠 `-text -eol` 修；**CI 看不见这类缺陷**（Q9 由来）。
10. CI 秘密扫描四次红都是拦我们自己的文档：正文引用字面凭据样式即命中。
11. `record-gates.mjs` 裸调用写出 `stages:{}` 的退化回执却仍"成功"。
12. 文档里两处把 markdown 表格切成两段的空行（`DECISIONS.md`）——编辑表格行时不要在行尾多带换行。
13. 技能插件缺 `fast-glob`/`yaml`：装在 `.project-local/runs/node-libs` + `module.register()` 解析钩子（不动插件缓存、不装全局包；钩子里对目录要 `nextResolve` 委托、URL 空格要 `%20`）；playwright-core 要的浏览器修订本地没有时显式传 `executablePath`，**不下载运行时**。

## 11. 绝对不做

不 `git init` 之外的破坏性 Git 操作（不 reset --hard、不 clean -f、不 force push、不改写已发布历史、不删分支）；不发布/上线；不付费调用；不装全局包或改全局配置/SSH/凭据；不读取凭据与私人会话；不提交密钥、模型权重、用户资料、个人对话、运行数据库；不访问 E:/F:（除非 exact path + exact operation 授权）；不修改 AAOS 正式源码；不因"看起来缺"就自行采用新基线。

## 12. 收尾报告格式（必须给全）

1. 本轮实际执行的命令与**逐阶段退出码**（引用日志文件路径）
2. `git status` / `git diff --numstat` 的范围核对 + 本地 HEAD 与 `git ls-remote` 的比对结果
3. CI：`run N @ SHA` 与各作业步骤结论
4. 逐项验收状态变化（哪些从 X → Y，证据级别是什么）
5. 未执行项与原因（明确区分"没授权"与"没想到"）
6. 新增/修正的断言及其证据位置（文件:行）
7. 下一轮可直接粘贴的任务提示词

**判定不变**：整体 M0 = **PARTIAL**。A05 需你的凭据，A17 需集成授权，A19 由你判定；其余缺口全部在 §9 的 1–5 项里，可自主推进。
