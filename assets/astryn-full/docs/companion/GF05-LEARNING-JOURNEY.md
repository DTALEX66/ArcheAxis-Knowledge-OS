# GF05 资料学习与陪伴融合（交付说明）

任务包 `ASTRYN-COMPANION-20261013` · 分支 `feat/astryn-learning-companion-v1` · 依赖 GF04（已完成）。

## 1. 交付物

| 路径 | 内容 |
| --- | --- |
| `src/learning/types.ts` (new) | GF05 域类型与纯策略：六类学习意图（尝试/提示/解释/复述/出处反馈/复习）、轮次类型（learning / knowledge-answer / companion-chat）、作者×意图约束 `intentAllowsAuthor`（尝试与复述只能本人、提示与解释只能角色、出处反馈与复习双向）、出处关联 `linkFromFragment` / `linkFromMaterial`、复习排程 `scheduleFromOutcome`、掌握度 `masteryFromOutcomes`、知识路由 `knowledgeRouting`（`autoCapture` 恒 `false`，闲聊 `COMPANION_CHAT_EXCLUDED`、无来源 `SOURCE_UNLINKED`、其余 `USER_INITIATED_ONLY`） |
| `src/learning/store.ts` (new) | `LearningCompanionStore`：材料库（登记/移除/切换话题）、学习旅程（开始/完成/放弃，一次一旅程）、轮次记录（含两道诚实不变量）、显式结果与掌握度、复习队列与提醒计划（`REMINDERS_OFF` > `FOCUS_MODE` 抑制）、上下文标签记录（上限 20，永不属于旅程）、快照缓存与订阅 |
| `src/index.ts` | 导出上述值与类型（`createLearningCompanion`、`LearningCompanionStore`、`scheduleFromOutcome`、`masteryFromOutcomes`、`knowledgeRouting` 等） |
| `dev-host/learning-panel.tsx` (new) | 开发宿主学习面板（仅呈现与显式操作转发）：材料库、旅程目标、请小栖解释（附授权片段）、尝试/复述/自查、显式自评三档、出处反馈原文对照、复习队列与主动提醒/专注开关、掌握度与下次复习、上下文标签记录（闲聊/知识回答守卫演示） |
| `dev-host/app.tsx` | 接线：独立于会话运行时的进程内学习状态；选区提供器把实时选区偏移交给合成夹具（见 §5 缺陷修复）；`modelAvailable` 如实反映"无模型"开关 |
| `dev-host/dev-host.css` | `.devhost-group` / `.devhost-input` / `.devhost-textarea`（面板专属，未混入产品呈现层） |
| `tests/learning/learning-journey.test.ts` (new, 32) | 域策略全量：意图×作者约束、出处关联两种来源、掌握度只由显式结果驱动（含"十轮角色解释后自评仍为零"）、排程（missed → 10 分钟归零；partial → 1 天归零；correct → 步进 +1，1/3/7 天上限）、复习队列、提醒与专注抑制、知识路由、快照与订阅 |
| `tests/learning/learning-panel.test.tsx` (new, 11) | 面板行为：无模型下的完整手工闭环、材料移除后引用失效、选区导入 → 解释 → 授权片段登记、内置材料（无片段）→ 未关联材料、闲聊/知识回答守卫标签、开关与禁用态 |

## 2. 验收对照（任务包 GF05 卡）

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 小栖围绕选定资料完成真实文本学习闭环 | PASS（SYNTHETIC 载体） | 浏览器实测：夹具文档选中文字 → 「合成夹具·宿主边界说明（选区）· SYNTHETIC」登记 → 开始旅程 → 请小栖解释（附授权片段，经合成会话端口流式回复）→ 记下小栖的解释（出处=授权片段，SYNTHETIC）→ 尝试/复述 → 显式自评 → 掌握度"在练 · 自评 1 次（想起 1 次）· 依据 explicit-user-outcomes-only · 下次复习 2026-10-14 15:08Z"。选定资料来自"当前选区"，载体是合成夹具（页面全程 SYNTHETIC 标记） |
| 缺模型仍保留资料与手工练习；不虚构掌握度或权威来源 | PASS | 切到"无模型"（模型芯片 `MODEL_UNAVAILABLE`）后：已登记材料与旅程不清除；尝试/复述/自评全流程可用并产出掌握度与复习排程；解释按钮禁用并标注"未接通模型：解释与对话不可用；复述、自评与复习不受影响"；会话日志保持"还没有对话"，无任何脚本回复冒充 AI。掌握度依据字段为 `explicit-user-outcomes-only`，角色轮（含解释）从不参与；角色轮只有真实附带过授权片段时才显示"授权片段"出处，否则"未关联材料" |
| 按学习意图组织尝试、提示、解释、复述、出处反馈和复习 | PASS | 六类意图在 `src/learning/types.ts` 建模并各有限制：尝试/复述只能本人记录（`INTENT_AUTHOR_MISMATCH` 拒绝角色轮），提示/解释只能角色，出处反馈与复习双向；出处反馈在面板上引用登记材料原文对照；复习队列只由显式自评排程（`scheduleFromOutcome`，missed→10 分钟、partial→1 天、correct→步进递增 1/3/7 天上限） |
| 日常陪伴与知识回答用明确类型及上下文标签，闲聊不自动入正式知识 | PASS | 轮次类型 `learning` / `knowledge-answer` / `companion-chat` 必带上下文标签；学习轮强制非空意图、闲聊与知识回答强制无意图（`INTENT_REQUIRED` / `INTENT_NOT_ALLOWED_FOR_KIND`）；知识路由 `autoCapture` 为字面量 `false`，闲聊 `COMPANION_CHAT_EXCLUDED`、无来源 `SOURCE_UNLINKED`、其余最多 `USER_INITIATED_ONLY`；面板守卫演示实测："闲聊不自动入正式知识"、"无来源：不进知识通道"；上下文标签记录（未绑定旅程）与学习旅程分离 |
| 用户可移除材料、切换话题、关闭主动提醒或进入专注 | PASS | 移除：材料删除后其旅程轮次的引用显示"（已移除）"，对已移除材料的操作被拒（`MATERIAL_NOT_FOUND`）；切换话题：`selectTopic` 明示当前话题；提醒：关闭后"主动提醒已关闭：0 项到期仅列在队列里"（只抑制提示、不清队列），专注模式"专注模式中：0 项到期提示已暂停"，优先级 `REMINDERS_OFF` > `FOCUS_MODE` |

## 3. 门禁与封存（GF05 终局）

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-231006.log`：**lint=0 typecheck=0 test=0 build=0 record=0 anchors=0**（六阶段全 0）。
- 测试：**28 文件 / 266 通过**（其中 GF05 新增 43：learning-journey 32 + learning-panel 11）。
- 封存收据 `docs/verification/gates.json`：源码树 **87 文件**，树哈希 `db462aab7c055528ec73754e10b3ff7909fa7c28047fe31b7dd6d824e46df4e0`；`allGreen: true`；`git.head` `abb1f47`（GF05 提交前的分支头）。
- 构建产物（实测磁盘字节）：`index-CiX15iyT.js` 260,657 B，sha256 `cf1f653b442f424d…`；`index-s_cYDZFx.css` 9,005 B，sha256 `b6d69791044e0646…`。
- 首跑并非全绿：`tsc` 揪出 3 处真实错误（面板两处联合类型收窄 `?? ` 误用、`noUncheckedIndexedAccess` 下的数组下标），vitest 不会类型检查所以此前未暴露——已逐项修复后重跑全绿，**未做任何豁免**。

## 4. 浏览器实测（Dev Host，DOM 读数）

`VITE_ASTRYN_ALLOW_SYNTHETIC=1` 起 Vite（127.0.0.1:5183），实测后按 PID 终止、端口释放：

- 回归：宿主八端口读数仍为 5 行"未接 + `HOST_CONTRACT_MISSING`（星栖不猜测宿主现场）"+ 3 行 ASTRYN seam 可用（GF04 行为未回归）。
- 学习闭环（合成会话）：材料登记 → 旅程 → 尝试/复述各一条（出处=登记材料，SYNTHETIC，"仅本人手动可登记（永不自动）"）→ 自评"想起来了"→ 掌握度"在练"、`explicit-user-outcomes-only`、下次复习与步进展示。
- 授权片段链：选中夹具文字 → 登记选区材料 → 请小栖解释（附带授权片段，经合成会话端口流式回复，日志标注 `SYNTHETIC[合成夹具]`）→ 记下解释为角色轮，出处显示"授权片段，SYNTHETIC"；该角色轮不改变自评计数（仍 1 次）。
- 守卫演示：无来源知识回答"不进知识通道"；闲聊"不自动入正式知识"；两者只进上下文标签记录。
- 开关：主动提醒关闭 → 队列保留；专注模式 → 提示暂停；恢复后回到正常提示文案。
- 无模型：整条手工闭环可跑（见 §2 第 2 行）。
- 控制台：全新加载后仅 2 条 vite debug + 1 条 React DevTools info，**0 错误**。
- 证据形态：结构化 DOM 读数（本会话无截图面），逐条文案与计数均从页面读出。

## 5. 诚实边界与开发宿主缺陷修复

- **学习状态为进程内**（刷新即失）；正式持久化归宿主，`BLOCKED_BY_HOST_CONTRACT`——面板题注如实标注，不做假保存。真实宿主合同（BE01/BE03/BE05/BE06/BE07/BE12）缺项不冒充已接通。
- **修复 M0 遗留死路径**（本次浏览器实测发现）：`dev-host/app.tsx` 原以 `selection: null` 构造合成上下文夹具，导致浏览器内"解释选中内容/登记选区"通道无论选区与否恒 `NO_SELECTION`——真实与合成选区均不可用（M0 浏览器验证只覆盖了"未选中即拒绝"路径，见 `docs/verification/M0-VALIDATION.md` 第 35 行）。现改为每次调用把实时选区偏移交给夹具（仍全程 SYNTHETIC 标记）；"真实选区"依旧 `BLOCKED_BY_HOST_CONTRACT`，未用合成数据冒充真实接入。
- **修复模型开关不同步**：学习面板 `modelAvailable` 原取配置解析结果、忽略"切到无模型"开关；现与全会话端口一致（`conversationPort !== null && resolved.info.available`），无模型时解释按钮禁用并给出原因。
- 两处修复均属开发宿主接线，`tests/` 无 dev-host 应用级测试载体，故仅经浏览器实测（本条为已知测试盲区，不是豁免声明）。
- 掌握度语义保守：无显式自评时恒"未评定"（`basis=explicit-user-outcomes-only`），角色文本、材料存在与否都不影响它。

## 6. 回滚

`git revert` GF05 提交（分支 `feat/astryn-learning-companion-v1` 上单个提交）。变更对 GF00–GF04 全部为增量：新目录 `src/learning/`、`tests/learning/`、新面板组件与 dev-host 接线，契约只新增导出；两处 dev-host 修复独立可回滚（回滚后回到"选区通道恒拒绝 + 面板误报可用"的旧行为，不影响产品层）。
