# GF10 角色与真实宿主联合验收（交付说明）

任务包 `ASTRYN-COMPANION-20261013` · 分支 `feat/astryn-learning-companion-v1` · 依赖 GF08/GF09（已完成）与 BE12（宿主侧联合项）。

本卡性质：**联合验收轮**——不在本轮新增产品功能，而是把前九卡交付的角色、学习、记忆、呈现、会话在开发宿主里**联合跑一遍**，并把"真实宿主/真实模型"两半如实分开记录。任务包工作条②原文即"真实模型与主项目集成分别记录 Dev Host/fixture/实际宿主与安装证据"，因此本卡的交付物就是这份分离记录 + ASTRYN 侧可跑部分的实测证据。

## 1. 验收对照（任务包 GF10 卡）

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 「真实学习伴侣文本闭环、共享会话及有限权限通过。」 | PASS（ASTRYN 侧，开发宿主） | 联合实测：文本闭环（提交→流式回复→会话记录）；学习闭环（选区材料→解释附授权片段→记下解释→复述→显式自评→掌握度/复习排程）；共享会话（主页槽位提交后四个壳体同显同一轮回复，`logsCount=4`）；有限权限（审批链 awaiting_approval→executing→completed 全程 SYNTHETIC 回执 + 校验"通过"；记忆作用域停用即拦截登记）。「真实模型」半见 §2，仍 UNVERIFIED。 |
| 「外观会动不能替代真实模型和学习帮助。」 | PASS（防冒充条款按设计落地） | 模型徽章恒 `synthetic-fixture / SYNTHETIC`；证据标签恒 `scripted-synthetic / SYNTHETIC`；未注入模型即呈现 `NO MODEL`（单测）；掌握度只来自显式自评（`explicit-user-outcomes-only`，角色轮永不参与——单测锁定）；解释轮出处仅来自真实附带过的授权片段；无模型时解释按钮禁用并标注原因、手工练习照常。 |
| work②：Dev Host/fixture/实际宿主/安装 分别记录 | PASS（记录分离，见 §2） | Dev Host = SYNTHETIC 实测（本文 §4）；实际宿主 = BE12/宿主合同缺项 `BLOCKED_BY_HOST_CONTRACT`；安装 = `NOT_EXECUTED`。 |
| work③：语音与口型未接不阻断文本验收，如实记录 | PASS | GF09 语境：语音四通道全"未接"+ BLOCKED 原因；口型恒"文本帧"；`document.querySelectorAll('audio').length===0`；本轮文本闭环全程不依赖语音。 |

八项联合观察（九状态 / 多呈现 / 关系风格切换 / 隐藏 / 记忆 / 资料范围 / 流顺序 / 取消竞态）逐项落点：

| # | 项目 | 本轮实测证据 | 行为钉扎（既有测试） |
| --- | --- | --- | --- |
| 1 | 九状态 | 浏览器实况出现 idle / awaiting_approval / executing / completed / interrupted 五态（含顶部状态条"状态：completed"）；listen/think/speak 等亚秒态由夹具零延迟特性所限不在浏览器可捕获（GF07 既有limitation） | `tests/companion/reducer.test.ts`、`tests/avatar/state-action-matrix.test.ts`（九态-动作映射） |
| 2 | 多呈现 | 三槽位 240/168/168px + aside 168px；主页槽位提交后 aside 与三槽日志同显同一轮回复（共享会话） | `tests/presentation/host-slots.test.tsx`、`shared-session.test.tsx` |
| 3 | 关系风格切换 | 设置面板 radio 切到"女友语气（本人选择后启用）"→ 保存 → 档案 v3 · 修订 0→1，保存去向标注 `EPHEMERAL_DEV_MEMORY`（进程内，刷新即失） | `tests/companion/character-profile.test.ts`、`tests/presentation/companion-settings.test.tsx` |
| 4 | 隐藏 | 点"隐藏角色"→ `astryn-hidden-placeholder` 出现、日志长度 206 字符保留；点"恢复显示"→ 对话记录原样在场 | `tests/presentation/companion-shell.test.tsx` |
| 5 | 记忆 | 提议→纠正（撤销旧+登记替换，独立读回核对）→删除（账本除名）→停用（登记被拦，`SCOPE_SUSPENDED_BY_LOCAL_POLICY`）→恢复→导出（已删除记录不在导出、撤销痕迹在账本）；四空间分离计数在场 | `tests/memory/manager.test.ts`、`memory-panel.test.tsx`、`policy.test.ts` |
| 6 | 资料范围 | 真实 Range 选区 → 选区材料登记（`SYNTHETIC`）；同源同版本二次登记被拒 `DUPLICATE_MATERIAL`（先登记者胜、不静默覆盖） | `tests/learning/learning-journey.test.ts:86`（去重断言） |
| 7 | 流顺序 | 停止→`interrupted`；重试→先查询原请求（宿主无该请求记录）→按新请求重发→完成；迟到增量与迟到权威事件被 `SETTLED_REQUEST` 静默丢弃 | `tests/interaction/stream-retry.test.ts`、`composer-continuity.test.tsx` |
| 8 | 取消竞态 | 微任务窗内捕获停止按钮点击成功（`stopClicked=true`）→ `interrupted` → 重试条在场 → 查询-重发链完整 | `tests/interaction/stream-retry.test.ts`（含补证词测试） |

## 2. 分离记录（work②的逐项如实口径）

| 面 | 状态 | 依据 |
| --- | --- | --- |
| Dev Host（双合成夹具：`VITE_ASTRYN_ALLOW_SYNTHETIC` + `VITE_ASTRYN_SYNTHETIC_HOST`） | **EXECUTED / SYNTHETIC** | 本文 §4 全部实测读数；夹具回执 `authority='synthetic-fixture'`，界面恒显 SYNTHETIC。 |
| fixture（单元/组件测试） | **EXECUTED** | 36 文件 / 319 测试全绿（§3 门禁）。 |
| 实际宿主（AAOS 联合） | **BLOCKED_BY_HOST_CONTRACT** | 宿主八端口未接（GF04）；正式槽位 FE18 未接线（GF08）；会话流 BE05、档案持久化 BE06/BE01、记忆长期库 BE06、语音 BE01 均缺位；任务包依赖项 BE12 为宿主侧工作，本仓不代做。 |
| 真实模型（A05 口径） | **UNVERIFIED** | 本会话未配置/未获准上游凭据；`OpenAiCompatibleConversationPort` 与 dev 代理只有测试覆盖（`tests/adapters/openai-compatible.test.ts`、`sse.test.ts`），无真实调用证据。 |
| 安装（正式打包分发） | **NOT_EXECUTED** | 与既往各卡同口径；不安装正式程序。 |

## 3. 门禁与封存（GF10 终局）

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261014-000834.log`：**lint=0 typecheck=0 test=0 build=0 record=0 anchors=0**（六阶段全 0，一次通过）。
- 测试：**36 文件 / 319 通过**（与 GF09 相同——本卡零源码改动，含既有全部回归）。
- 封存收据 `docs/verification/gates.json`：源码树 **100 文件**，树哈希 `8027cfe9186a9c4d265a8074faca1b2933c95f9b5c6f3641245a582bae0771ff`（与 GF09 逐字节相同，证明本轮未改源码）；`allGreen: true`；`git.head` `e1cacd5`（GF09 提交，即本轮提交前的分支头）。
- 构建产物（实测磁盘字节）：`index-P5YjlFx8.js` 295,268 B，sha256 `03e4f907786bb3c3811038ff7109106005a63d9c9521a61fd0f91652c4925574`；`index-P5YjlFx8.js.map` 845,331 B，sha256 `c4f7ad965d8dd56f53eaf963f373804476d58d88f54c27f60be6c7051cfdba06`；`index-PqCch4VI.css` 11,670 B，sha256 `3e8d7372f43837ecad034ac17102b90fa1a51fa5d13dddb4dfc680fe3ff6ec64`。

测试截图（`.project-local/artifacts/`，磁盘字节）：

| 文件 | 字节 | sha256 |
| --- | --- | --- |
| `m0-browser-07-gf10-learning.png` | 816,233 | `9fe2ca304cce72e4c16f97aa3ec7993d531e9ea652b8c5b15384f6b894c79a8e` |
| `m0-browser-08-gf10-memory.png` | 863,326 | `4b0f025fc6b080ef6dc3fa16ecc0ead6005811c8202cd47addf7a2863db8b165` |
| `m0-browser-09-gf10-persona-settings.png` | 55,133 | `c2902ed326ed0ec9a4d768b838fc1a43f1866f91bae2f95333ddce2f9013e884` |
| `m0-browser-10-gf10-joint.png` | 930,308 | `2883cdd99a7c199f2ef20662fda06fb37b4b3d7e11c37535c78ed8e66592b4a4` |

## 4. 浏览器实测（Dev Host 联合序列，DOM 读数）

环境：`VITE_ASTRYN_ALLOW_SYNTHETIC=1 VITE_ASTRYN_SYNTHETIC_HOST=1`，Vite `127.0.0.1:5288`；两段页面实例（实例 1 做共享会话/审批基线，实例 2 重载后按"选区优先"顺序全链复演）；实测后 netstat PID 5780 终止、端口释放；控制台 3 条（vite debug×2 + React DevTools info），**0 错误**。

1. **共享会话与多呈现**（实例 1）：三槽 240/168/168px；主页槽位提交一句 → aside 与三槽日志同显同一轮回复（`logsCount=4`，同一 sessionId）；证据标签 `scripted-synthetic / SYNTHETIC`；模型徽章 `synthetic-fixture / SYNTHETIC`。
2. **审批链**（两实例各一遍）：`devhost-request-action` → `任务：awaiting_approval · syn-task-1` + 审批卡（approve/deny）→ 批准 → `任务：executing` → 合成推进"执行中"→"完成回执" → `任务：completed`；状态条 `审计：应用 20 · 丢弃 0 · 回执 通过`。
3. **学习闭环**（实例 2）：夹具文档真实 Range 选区 → 「已登记材料「合成夹具·宿主边界说明（选区）」（SYNTHETIC）」→ 开始旅程 → 「请小栖解释（附授权片段）」可用（解释按钮此前在样例材料（无片段）下禁用并给出原因——负例亦实测）→ 回复落入会话 →「已把当前回复记为「解释」轮」；轮次出处逐条在场：解释轮 `出处：合成夹具·宿主边界说明 v1（授权片段，SYNTHETIC）`、复述轮 `（登记材料，SYNTHETIC）`；复述→自评"想起来了"→掌握度 `在练 · 自评 1 次（想起 1 次）· 依据：explicit-user-outcomes-only · 下次复习 2026-10-14 16:06Z · 步进 1`。
4. **同源去重**（负例）：先登记样例全文后，同源同版本选区登记被拒 `材料登记被拒：DUPLICATE_MATERIAL`（两实例各见一次）——一次来源一份材料，先登记者胜，不静默覆盖。
5. **记忆治理**：提议 cand-1（偏好）→ 纠正 → 读回 `✓ 撤销旧记录 cand-1：已撤销（原 user_preference）｜ ✓ 登记替换记录 cand-2：user-stated · candidate ｜ 读回一致（query(companion×user_preference)=1 条活跃；listForReview=2 条）｜cand-1：活跃读取 不在 / 账本 在场；cand-2：活跃读取 在场 / 账本 在场` → 提议 cand-3（虚构剧情）→ 删除 cand-2 → `✓ 删除 cand-2：已从宿主账本删除 ｜ 读回一致（query=0 条活跃；listForReview=2）｜cand-2：活跃读取 不在 / 账本 不在` → 停用作用域 → 提议被拦 `✗ 登记候选（user_preference）：SCOPE_SUSPENDED_BY_LOCAL_POLICY：本机已停用该作用域；恢复后才能登记。宿主授权变更仍 BLOCKED_BY_HOST_CONTRACT。` → 恢复 → cand-4 登记成功 → 导出 JSON：`records` 含 cand-1（revoked）/cand-3/cand-4，**cand-2 不在**；`suspendedScopes` 复原为空；分离计数 `记忆记录：2 条（经宿主接口）学习材料：1 份 · 练习轮：2（独立存储）`。
6. **取消竞态与重试**：微任务窗内点停止成功 → `状态：interrupted` + 重试条 → 点重试 → `已先查询原请求（宿主无该请求记录）：按新请求重发。` → 回复完成、`状态：idle`，日志出现重发轮的提问与回复。
7. **隐藏与恢复**：`隐藏角色` → 占位出现、日志保留（206 字符）；`恢复显示` → 原对话在场。
8. **关系风格与档案**：切"女友语气（本人选择后启用）"radio → 保存 → `已保存（修订 1）→ 进程内（开发回退）· EPHEMERAL_DEV_MEMORY（进程内，刷新即失，仅开发宿主）`、`档案版本 v3 · 修订 1`（保存前修订 0）。

以上读数与截图 07–10 对应；截图 10（fullPage）同帧包含：aside 壳体（任务 completed）、三槽位、宿主八端口读数节（5 行未接 + 3 行 ASTRYN seam）、语音未接节、学习面板（旅程与轮次）、记忆治理（记录与读回）。

## 5. 诚实边界

- **"真实宿主"半未发生**：本卡在 AAOS 侧的一切（正式槽位 FE18、八端口真实调用、BE05/BE06/BE01 合同）均 `BLOCKED_BY_HOST_CONTRACT`；依赖项 BE12 属宿主仓工作。本卡的"联合"是 ASTRYN 全部子系统之间的联合 + 对合成宿主收发侧的真实验证，**不是**与 AAOS 的联合。
- **"真实模型"半未发生**（A05 `UNVERIFIED`）：所有回复由零延迟合成夹具产生，界面全链路以 `SYNTHETIC` 标注；书面结论不随"外观会动"升级。
- **亚秒状态不可捕获**：夹具零延迟使 listen/think/speak 在浏览器中不可稳定观测；九态语义由单测钉住（GF07/GF03 同口径 limitation）。
- **`devhost-new-session` 不重置学习/记忆进程内存储**：本轮实测换会话后掌握度累计（2 次）仍在，整页刷新才重置；这是开发宿主的演示接线行为（非正式产品语义），正式持久化归宿主合同。
- **草稿是每视图本地状态**（既有限制）：aside 与三槽各有一份输入草稿，不跨视图同步。
- **本卡未新增测试**：本轮观察到的全部行为（去重拒绝、停用拦截、查询-重发、撤销留痕/删除除名）都已有既有测试钉住（§1 表右列），故不重复造测试；本卡交付物是联合实测证据与分离记录本身。
- **安装 `NOT_EXECUTED`**：不对应任何安装面（未打包分发、未安装正式程序）。

## 6. 回滚

本卡不产生源码变更：`git revert` GF10 提交即可回到 GF09 终局（提交仅含本文档、PROGRESS.json、STATUS.md 与刷新后的门禁收据）。树哈希 8027cfe9 在 GF09/GF10 两轮相同可自证源码零漂移；截图属 `.project-local/artifacts/`（惯例不提交，更新器按字节校验其在场）。
