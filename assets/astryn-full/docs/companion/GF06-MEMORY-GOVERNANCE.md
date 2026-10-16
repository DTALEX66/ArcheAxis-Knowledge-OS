# GF06 记忆查看纠正与遗忘（交付说明）

任务包 `ASTRYN-COMPANION-20261013` · 分支 `feat/astryn-learning-companion-v1` · 依赖 GF04（已完成）；BE06 未接通。

## 1. 交付物

| 路径 | 内容 |
| --- | --- |
| `src/memory/manager.ts` (new) | `MemoryManager`：治理台封装（view / propose / correct / forget / suspendScope / resumeScope / exportEvidence）。**读回约定**：每次治理动作后经两条独立通道重读（`query(consumer×scope, candidate+confirmed)` + `listForReview(sessionId)`），期望值来自操作语义（撤销→活跃缺席/账本在场；删除→两者皆缺席；纠正→旧撤新增），`query` 被拒则该作用域记 `UNKNOWN` 并使 `verified=false`——读回不是回执复述，是新鲜读取。`ASTRYN_MEMORY_SPACES` 四空间（聊天记录/长期记忆/当前上下文/备份保留）逐条写明归属、保留与限制。 |
| `src/index.ts` | 导出 `MemoryManager`、`ASTRYN_MEMORY_SPACES` 与全部治理类型。契约文件 `contracts/memory.ts` 未修改。 |
| `dev-host/memory-panel.tsx` (new) | 记忆管理视图（仅呈现与显式操作转发）：获准作用域条（读写/授权方/期限 + 停用/恢复按钮）、登记表单（作用域×来源×摘要）与两个快捷登记（沿用旧 testid）、记录行（生命周期/作用域/来源 + 记录时间/确认回执 + 纠正/撤销/删除）、导出 JSON 面板、最近动作读回行、四空间说明、分离计数条（记忆条数 vs 学习材料/练习轮 vs 档案 revision）。 |
| `dev-host/app.tsx` | 接线：`MemoryManager` 按会话重建（账本按会话过滤）；原内联 `devhost-memory` 段整体替换为 `MemoryPanel`；边界声明新增记忆治理条目（备份保留归宿主等）。 |
| `dev-host/dev-host.css` | `.devhost-export`（只读 JSON 快照面板）。 |
| `tests/memory/manager.test.ts` (new, 8) | view 授权/来源/空间、纠正（含确认级别随原记录）、撤销保痕、删除除名、停用→拦截→恢复、分离（真实档案+学习库）、导出限制声明、**谎报端口证伪**（删除后查询仍返回记录的端口 ⇒ `verified=false` ⇒ `ok=false`）。 |
| `tests/memory/memory-panel.test.tsx` (new, 4) | 面板：四空间与分离计数、纠正+撤销+删除全链路文字、停用拦截+恢复放行、导出快照排除已删除记录。 |

## 2. 验收对照（任务包 GF06 卡）

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 显示获准偏好、目标、约定及记录来源，支持纠正、忘记、导出和停用 | PASS（SYNTHETIC 载体） | 浏览器实测：获准作用域 4 条（"偏好：读写 · 用户授权 · 长期"…）；登记偏好/约定文本任意；每行显示来源（origin）、记录时间、确认回执；纠正/撤销/删除/停用/恢复/导出逐一执行；纠正输出"✓ 撤销旧记录 cand-1 ｜ ✓ 登记替换记录 cand-2：user-stated · candidate ｜ 读回一致" |
| 删除与撤销有真实读回，当前上下文及时更新 | PASS | 撤销后读回"cand-3：活跃读取 不在 / 账本 在场"；删除升级后"cand-3：活跃读取 不在 / 账本 不在"且行消失；纠正后"读回一致（query(companion×user_preference)=1 条活跃；listForReview(dev-session-1)=2 条）"。证伪测试（`TamperingPort` 删除后仍谎报记录在场）：`readBack.verified=false` ⇒ `result.ok=false`——读回不一致时不放行 |
| 遗忘不是只隐藏一张卡，角色风格与学习事实分开 | PASS | 撤销保留审计痕迹（账本仍返回 revoked）与删除从账本除名，两者都经读回验证；分离由单测实证：遗忘全部记忆后，档案 `profileRevision` 不变、学习材料与练习轮不变（真实存储实例）；浏览器实测记忆操作前后"学习材料：1 份 · 练习轮：0（独立存储）"不变；四空间逐条说明聊天记录/长期记忆/当前上下文/备份保留 |
| 由宿主写入与撤销，不在 ASTRYN 新建长期主库 | PASS | 全部写撤删经 `AstrynMemoryPort`；回执 `issuedBy=user`；无任何本地持久化（进程内合成夹具，刷新即失）；边界声明与面板题注均如实标注 SYNTHETIC |

## 3. 门禁与封存（GF06 终局）

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-231754.log`：**lint=0 typecheck=0 test=0 build=0 record=0 anchors=0**（六阶段全 0，一次通过）。
- 测试：**30 文件 / 278 通过**（其中 GF06 新增 12：manager 8 + panel 4）。
- 封存收据 `docs/verification/gates.json`：源码树 **91 文件**，树哈希 `0075b9e1eff08655125bfdda41f6571e2a6b688c46a427ecd43d0f067386696d`；`allGreen: true`；`git.head` `077e6fd`（GF06 提交前的分支头）。
- 构建产物（实测磁盘字节）：`index-BId_1Wxf.js` 275,424 B，sha256 `160da66951dafa0e1bf68268bfe29f89fff3d5559edd83a1d7a6582f0ae78e70`；`index-C_KIL2tT.css` 9,221 B，sha256 `3d2b2d71c984dd6f3778a8b8453178d4013f1427975558f5daca8c793cc73a9c`。

## 4. 浏览器实测（Dev Host，DOM 读数）

`VITE_ASTRYN_ALLOW_SYNTHETIC=1` 起 Vite（127.0.0.1:5183），实测后按 netstat PID 15604 终止、端口释放：

- 面板渲染：4 条获准作用域条 + 四空间说明（含备份保留 `BLOCKED_BY_HOST_CONTRACT`）+ 分离计数条。
- 登记 → 纠正：`登记偏好候选` 产生 cand-1；行内纠正为"晚上九点后少打扰（浏览器修订）"⇒ cand-1 已撤销、cand-2 候选（旧为候选故替换保持候选），读回双条目一致。
- 撤销 → 删除：虚构候选 cand-3 先撤销（账本在场）、再删除升级（账本不在，行从列表消失）。
- 停用：`偏好` 条变"本机已停用"且活跃记录被真实撤销；再登记被拒（"SCOPE_SUSPENDED_BY_LOCAL_POLICY：本机已停用该作用域；恢复后才能登记。宿主授权变更仍 BLOCKED_BY_HOST_CONTRACT。"）；恢复后放行（cand-4）。
- 导出：`kind=astryn-memory-export`；records `cand-1:revoked / cand-2:revoked / cand-4:candidate`；文本不含 `cand-3`；limitations 3 条（SYNTHETIC、备份保留 BLOCKED、删除除名/撤销保痕）。
- 分离回归：先在 GF05 学习面板登记示例材料 → 记忆操作刷新后分离条显示"学习材料：1 份 · 练习轮：0（独立存储）"，记忆记录数独立变化。
- 控制台：全新加载 3 条（2 条 vite debug + 1 条 React DevTools info），**0 错误**。
- 证据形态：结构化 DOM 读数（本会话无截图面）。

## 5. 诚实边界

- **确认（confirmed）属宿主治理面**：开发宿主不提供"确认"按钮，候选不会自行变为已确认；合成夹具的 confirm 路径仅在单元测试中演练（模型生成内容确认须 `aaos-core` 在可信签发方列表内）。
- **停用是本机治理**：先真实撤销该作用域活跃记录，再拦截星栖侧登记；宿主 grant 本身的变更 `BLOCKED_BY_HOST_CONTRACT`（grant 条只读展示，实测停用前后 read/write 均不变）。
- **备份保留归宿主**：星栖不可见、不可改；导出明确不含备份内容。
- **真实长期记忆库（BE06）未接通**：账本载体是进程内合成夹具（SYNTHETIC，刷新即失），正式记忆库只能由 AAOS 权威存储承载。
- 已知盲区：`dev-host/memory-panel.tsx` 有专门组件测试，但 `dev-host/app.tsx` 接线本身仍无测试载体、仅浏览器实测（与 GF05 记载同一盲区）。

## 6. 回滚

`git revert` GF06 提交（分支 `feat/astryn-learning-companion-v1` 上单个提交）。全部为增量：新文件 `src/memory/manager.ts`、`tests/memory/manager.test.ts`、`tests/memory/memory-panel.test.tsx`、`dev-host/memory-panel.tsx`；`app.tsx` 为段落替换（回滚后回到旧内联 devhost-memory 段）；契约与产品呈现层零改动。
