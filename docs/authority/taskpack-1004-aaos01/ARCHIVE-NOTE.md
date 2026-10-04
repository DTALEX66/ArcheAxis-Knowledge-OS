# AAOS_01 任务包归档说明（2026-10-04）

本目录是 Owner 于 2026-10-04 交付的任务包原件的**仓库内归档**。

## 1. 归档来源与完整性

| 项 | 值 |
| --- | --- |
| 来源 | `D:\All projects\Record\AAOS_01_快速重构_多格式闭环_20261004.zip`（28,588 字节） |
| 配套启动提示词 | `D:\All projects\Record\AAOS_01_快速重构_多格式闭环_启动提示词_20261004.txt` |
| 完整性 | 按包内 `SHA256SUMS.txt` 逐件校验：**10/10 通过，0 不匹配** |
| 归档方式 | **原样保存**，未改动任何包内文件 |

## 2. 这是**又一次变化更新**，且 **UI 前端是重点**

包内 `prompts/00_启动提示词.txt` 第 3 行原文：

> 用户已明确选择重构：**Tauri 2 + React + TypeScript + Vite**；Rust Core + SQLite/CAS；隔离 Python workers。**不要再提 Avalonia/Tauri 二选一，不要再询问是否重构。**

包内 `00_两包共同架构与交接规则.md`：

> 用户"按照重构来"**已经取代**旧文件里继续纯 Avalonia、不新建 React/Tauri 的限制。实施者将其登记为**现有 Authority 的可追溯 delta**；不要重写旧不可变任务包，也不要再问是否选择重构。

**对 UI 前端的变更**：正式产品宿主由 **C#/Avalonia**（`apps/ArcheAxis.Desktop/`）**变为 Tauri 2 + React/TypeScript/Vite**（`frontend/` + `src-tauri/`）。

## 3. Authority delta 已登记

| 登记项 | 位置 |
| --- | --- |
| **SUP-022** | `DECISION_SUPERSESSION_LEDGER.yaml`（取代 SUP-021 的正式壳优先级） |
| 权威索引更新 | `docs/CONFIGURATION_AUTHORITY_INDEX.md` |
| 本归档目录 | `docs/authority/taskpack-1004-aaos01/` |

**SUP-022 明确保留的边界**（一项都没放松）：

- Rust Core **仍是唯一 canonical 写者**；Python 仍是隔离 worker；**每文件一个 writer**；
- **不把旧 Python 后端重新接成权威**；
- **仍只有一个默认壳**（`desktop/` 依旧是独立 recovery 入口，其自身 manifest 标识为 `com.archeaxis.workspace.recovery`）；
- **不替换正式库、不发布、不替 Owner 审批知识候选**；
- **M0 无发布边界与 A16 Owner Gate 不变**；
- **不删除历史资产**；
- Avalonia 应用**只在 Tauri 壳真正接管之后**才成为冻结参考。

**关于索引里"不创建并行 TaskPack"**：本归档**不是执行者自建的并行计划**，而是 **Owner 直接交付并指示归档**的更新；SUP-022 即为该指示的登记。执行者**不自签**审计与 Owner Gate。

## 4. 与已产出回执的对应

| 本包任务 | 已产出 | 位置 |
| --- | --- | --- |
| Q00 现场保护与最小对账 | ✅ | `docs/current/AAOS01-Q00-SCENE-RECEIPT.md` |
| Q01 重构决定与目录登记 | ✅ | `docs/current/AAOS01-Q01-REFACTOR-DELTA-AND-DIRECTORY-OWNERSHIP.md` |
| Q02 Tauri 启动与只读桥接 | 🔶 现场核对与改接范围已定 | `docs/current/AAOS01-Q02-*.md` |
| Q03 类型合同与权限 | 🔶 诊断完成（写者/数据模型冲突已定性） | `docs/current/AAOS01-Q03-*.md` |
| Q04–Q15 | NOT_RUN | — |

## 5. 已知待办（不在本归档内解决）

- **canonical 数据模型**尚未裁决（Core 的 `anchors` vs Python 的 `evidence_anchors`）；
- 工作树 `data/` 中实际存在的是 `cognitive_os.sqlite`，与配置的 `data/archeaxis.sqlite` **不同名**，两者关系未查明；
- Tauri 宿主当前启动的是**旧 Python 后端**，**改接未做**；
- 前端 16 套件 / 119 用例基线为**改接前**结果（`docs/current/AAOS01-FRONTEND-BASELINE-16-119.md`）。
