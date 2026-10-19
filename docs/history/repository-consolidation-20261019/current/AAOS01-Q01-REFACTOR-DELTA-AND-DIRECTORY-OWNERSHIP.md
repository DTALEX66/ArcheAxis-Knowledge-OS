# AAOS-01 Q01 Authority delta 与目录归属（2026-10-04）

包：`AAOS_01_快速重构_多格式闭环_20261004`。本文件是 **Q01（重构决定与目录登记）** 的交付，同时给出用户要求的**详细对比规划**（迁移 / 合并 / 删除清理 / 冻结）。

## 1. Authority delta（登记，不改写旧包）

**决定**：正式宿主由 `apps/ArcheAxis.Desktop/`（C#/Avalonia）**变更为** Tauri 2 + React/TypeScript/Vite（`frontend/` + `src-tauri/`）。Rust Core + SQLite/CAS + 隔离 Python workers **不变**，Core 仍是**唯一 canonical 写者**。

**性质**：这是**现有 Authority 的可追溯 delta**，不是重写。不可变的 R6 / M0 历史与 current 台账身份**保持不动**。

**明确不包含的授权**（包内 00 号原文明列）：重构**不自动**等于正式库覆盖、公开发布、或替用户审批知识候选。

**依据**：启动提示词第 3 行（"用户已明确选择重构…不要再问是否重构"）；`00_两包共同架构与交接规则.md` 第 3 段（"用户按重构来已经取代旧文件里继续纯 Avalonia…的限制。实施者将其登记为现有 Authority 的可追溯 delta"）。

## 2. 目录归属（**用证据定，不是用提问定**）

本轮实查：**没有任何分支在这三个目录里有 HEAD 之外的提交或差异**。

```
codex/aaos-ui-phase2-20261001            commits there not in HEAD: 0   | diff in dirs: none
codex/minimax-aaos-cosmic-ui-20261001    commits there not in HEAD: 0   | diff in dirs: none
codex/Audit                              commits there not in HEAD: 0
main                                     commits there not in HEAD: 0
```

**结论**：`frontend/`、`src-tauri/`、`desktop/` 目前**没有并发写者**，单写者问题不存在；可在此分支推进而不与其他分支冲突。上一轮我把这条列为"需要 Owner 裁决"，**实查后发现它可查证，不需要裁决** —— 记在此以免下次又去问。

## 3. 详细对比：三棵树的真实角色

| | `frontend/` + `src-tauri/` | `desktop/` + `desktop/src-tauri/` | `apps/ArcheAxis.Desktop/` |
| --- | --- | --- | --- |
| 追踪文件 | 53 + 13 | 32 | 56 |
| `productName` | **`ArcheAxis Knowledge`** | `ArcheAxis Knowledge Recovery` | （Avalonia 程序） |
| `identifier` | `com.archeaxis.workspace` | `com.archeaxis.workspace.recovery` | — |
| 前端 | React 18 + Vite 5 + TS 5.5 | `../bootstrap`（静态） | `.axaml` |
| Tauri | **v2**（`schema.tauri.app/config/2`），CLI 2.11.4 | v2，CLI 2.11.4 | — |
| capabilities | `core:default` / `event` / `window` —— 注释写明 **"no direct filesystem or shell access"** | "Recovery Shell: query backend info over IPC" | — |
| CSP | 严格；`connect-src http://127.0.0.1:*`（连 Core HTTP） | 较宽（style `unsafe-inline`） | — |

**关键事实**：**正式的 Tauri 2 宿主已经存在**（`frontend/`+`src-tauri/`），且其 `frontendDist` 指向 `.project-local/build/frontend-dist`、`beforeBuildCommand` 调用 `frontend` 的 build —— 两侧**已经接好**。

## 4. 四个动作的结论（用户要求："该迁移的迁移，该合并的合并，该删除清理的就删除清理掉，该冻结的冻结"）

| 动作 | 结论 | 依据 |
| --- | --- | --- |
| **迁移** | 需要迁移的是**产品 UI 的实现**：`apps/ArcheAxis.Desktop/`（Avalonia，56 文件）→ `frontend/`（React）。**Tauri 宿主本身不需要新建或迁移**，它已在位并已接好。 | §3 的 `tauri.conf.json` 事实 |
| **合并** | **不合并。** `desktop/` 是**明确分离的 Recovery Shell**（独立 identifier、静态 bootstrap、IPC 查询）。把它并进正式宿主会**摧毁包内要求保留的恢复参考**。 | 两个 `productName`/`identifier`/capabilities 的差异 |
| **删除清理** | **本轮不删任何目录。** 三棵树都有**已声明角色**；包内 00 号明文"**不做强制清理**"，启动提示词第 11 行"**不为目录漂亮大搬迁**"。 | 包内原文 |
| **冻结** | (a) `desktop/` 作为 recovery **保持冻结、不合并**；(b) `apps/ArcheAxis.Desktop/` 应在 **Tauri UI 真正接管之后**冻结为参考 —— **现在不能冻**，迁移尚未发生。 | 同上 |

## 5. 本轮**不**声称的事

1. **没有读 `frontend/src/` 的内容**，所以**不判断**它离"可用产品"有多远 —— 只核了配置层的角色与接线。
2. **没有构建或运行**任何 Tauri 产物（`npm`/`cargo tauri` 本轮未执行）。
3. **没有改任何实现文件**；本提交只新增本文件。
4. `desktop/bootstrap` 与两个 `gen/`、`icons/` 的内容**未读**。

## 6. 下一项（Q02）与其前置

**Q02 = Tauri 启动与只读桥接**：让 Tauri 壳真正拉起 Core 并列出资料。前置是 Q01（本文件）✓。

实施前必须先读 `frontend/src/` 的现有结构与 `src-tauri/src/` 的命令面，确认**已有什么**再接 —— 按包内"已存在且合格的实现直接复用，只修缺口"。
