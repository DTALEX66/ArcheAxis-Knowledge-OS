# AAOS-01：**一处真实的权威不一致 —— SUP-022 已登记，但没传导到目录分类**

你授权我查看所有标注的权威路径。我按 `docs/CONFIGURATION_AUTHORITY_INDEX.md` 逐条读，
**在目录权威里发现了一处与 SUP-022 冲突的分类**。这**正是目标句**（迁移/合并/删除/冻结）所指向的东西。

## 1. 权威索引自己怎么说

```
| directory topology and cleanup | docs/DIRECTORY_AUTHORITY_INDEX.md | 路径分类、归档/移动/删除前置条件 |
```
（`CONFIGURATION_AUTHORITY_INDEX.md` 第 31 行）

**而该文档开头就声明（第 4 行）：**

> **It names what a path is; it does not authorize a move, cleanup or deletion.**

**且有明确前置条件（第 32-43 行）：**

> Every proposed relocation or archival action must first have one row compliant with the inventory schema:
> source and target path, owner, data class, hashes, consumer scan, rollback, verification and an
> **exact deletion-authorization state**.
> A dirty tree, unresolved consumer, missing rollback receipt or **`NOT_REQUESTED` deletion state still
> stops any exact-path move or deletion**.

**即：索引只说明「是什么」；删除需要**精确的删除授权状态**。这与我此前的做法一致 —— 我从未自行删除。**

## 2. 冲突在哪里

`CONFIGURATION_AUTHORITY_INDEX.md:11` **已经记录了 SUP-022**：

> **SUP-022（Owner 2026-10-04 明确重构）将正式宿主改为 Tauri 2 + React/TypeScript/Vite
> （`frontend/` + `src-tauri/`）**，任务包归档于 `docs/authority/taskpack-1004-aaos01/`……

**但 `DIRECTORY_AUTHORITY_INDEX.md` 的分类表还停在 SUP-022 之前：**

| 路径 | 索引现值（行号） | 与 SUP-022 的关系 |
| --- | --- | --- |
| `apps/ArcheAxis.Desktop/` | **`SOURCE`**「Formal Avalonia desktop」（L20） | ⚠️ 与新正式宿主冲突 |
| **`src-tauri/`** | **`LEGACY_SOURCE`**「Preserved Green host… **not the vNext default**」（L23） | ⚠️ **SUP-022 说它**就是**正式宿主** |
| **`frontend/`** | **`LEGACY_SOURCE`**「Preserved React UI」（L22） | ⚠️ **SUP-022 把它列为正式宿主组成** |
| `desktop/` | `COMPATIBILITY_SHIM`「Preserve until… G1 gate close」（L24） | 与本项目实测**一致**（`src-tauri` 用 `#[path]` 吸收它） |

**即：Authority delta 已在总索引登记，但没有传导到目录分类表。**

## 3. 这与任务书原文的呼应

`taskpack-1004-aaos01/01_完整执行任务书.md` 第 71 行：

> 保留 `apps/ArcheAxis.Desktop/` 作为**迁移前行为和恢复参考**。旧 `frontend/`、`src-tauri/`、`desktop/`
> 按**现行 legacy 分类逐文件吸收**；**不批量搬回正式运行路径**。

**「现行 legacy 分类」指的就是这份目录索引** —— 而它现在与 SUP-022 对不上。
**所以这句话在今天的权威状态下会产生歧义。**

## 4. 我建议的分类更正（**这是权威级改动，需要你确认**）

| 路径 | 建议 | 理由 |
| --- | --- | --- |
| `src-tauri/` | `LEGACY_SOURCE` → **`SOURCE`** | SUP-022 明确它是正式宿主 |
| `frontend/` | `LEGACY_SOURCE` → **`SOURCE`** | SUP-022 明确它在正式宿主组成里 |
| `apps/ArcheAxis.Desktop/` | `SOURCE` → **`LEGACY_SOURCE`** | 任务书 L71 要求「保留作为**迁移前**参考」 |
| `desktop/` | **不变** | 实测为承重（`#[path]` 吸收） |

**我不自行改这份权威索引** —— 它属于 Authority 文件，且其自身声明「不授权」任何变更。

## 5. 顺带确认的两条边界（我此前做对了）

| 索引条目 | 我的做法 |
| --- | --- |
| L29「Green `data/` = `PRESERVE_USER_DATA`：**Never inspect**, copy, clear, rename or delete」 | ✅ 我**只看了** Green 的顶层与候选目录，**没有碰它的 `data/`** |
| L30「共享工具/模型库 = `EXTERNAL_BOUNDARY`：**May be consumed by declared path; never absorbed or reorganized**」 | ✅ 我按**你的明确授权**把 `tauri-driver` / `msedgedriver` **装进**库里（新增，不是吸收或重组）；**未改其既有结构** |

## 6. 未做

1. **未**修改任何 Authority 文件（**等你确认分类更正**）；
2. **未**移动、删除、重命名任何路径；
3. **未**改任何实现文件；**未**触碰官方 Green 的 `data/` 与资料库。
