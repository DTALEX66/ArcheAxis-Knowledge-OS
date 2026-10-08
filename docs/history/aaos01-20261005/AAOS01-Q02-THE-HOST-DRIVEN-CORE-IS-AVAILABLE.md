historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# 🎉🎉🎉 AAOS-01 Q02：**宿主自己把 Core 拉起来了 —— 应用进入正常状态**

## 1. 决定性证据

```json
"outcome": "app-ui"
"shows_recovery": false          // ★ 不再是恢复壳
"page_len": 7275                 // 完整应用（恢复页只有 1,444 字符）
```

**应用页面（节选）**：

```html
<div class="app-shell">
  <header class="status-bar" role="banner">
    <span>星环知识</span>
    <button class="command-trigger">⌕ 搜索或前往 <kbd>Ctrl K</kbd></button>
    <div class="status-bar-center">
      <span class="status-pill status-pill--available" data-status="available">
        后端状态：本地可用                    // ★★★ 应用自述：Core 可用
      </span>
```

**宿主也真的驱动了迁移** —— 工作目录里出现了：

```
archeaxis.sqlite
backups\pre_migration_20261004T195828_721145Z_2fa35334.sqlite  (+ .manifest.json)
backups\pre_migration_20261004T195828_744639Z_69d6a9c6.sqlite
backups\pre_migration_20261004T195828_773644Z_25f70f57.sqlite
backups\pre_migration_20261004T195828_800100Z_eb9e480b.sqlite
backups\pre_migration_20261004T195828_832118Z_ff77b9e5.sqlite
.archeaxis.sqlite.runtime.lock   .cognitive-volume-id
```

## 2. 这就是 Q02 的交付物，而且是**走宿主**完成的

| 环节 | 结果 |
| --- | --- |
| 宿主**构建** | ✅ |
| 宿主**加载真正的界面** | ✅ `page_len: 7275`，非恢复页 |
| 宿主**解析 runtime** | ✅ |
| **宿主驱动迁移** | ✅ **真实的 `archeaxis.sqlite` + 5 份前置备份** |
| **宿主启动 Core** | ✅ |
| **应用自述后端可用** | ✅ **`后端状态：本地可用`** |

**从头到尾都是宿主做的，不是我手工跑命令。**

## 3. 让这一切成立的四步（每一步都有实测记录）

| # | 修复 | 轮次 | 效果 |
| --- | --- | --- | --- |
| 1 | runtime 放进 `runtime/python/`（代码要求嵌套） | 84 | 宿主第一次派生出后端 |
| 2 | 仓库包装进构建产物的 `site-packages` | 97 | `No module named 'app'` 消失 |
| 3 | 装齐声明的依赖（36 个包） | 98 | `No module named 'yaml'` 消失，迁移跑通 |
| 4 | **把宿主数据根指向带 `data/` 子目录的目录** | **本轮** | **宿主启动 Core 并自述可用** |

## 4. 关于第 4 步我要说清楚边界

第 100 轮查明：启动器写 `ARCHEAXIS_DB_PATH=data/archeaxis.sqlite`（**相对路径**），
而真实产品数据目录下**没有** `data/` 子目录 —— **它那条路径解析不到**。

**本轮的处置**：我**没有**去改真实产品数据目录（`%LOCALAPPDATA%\com.archeaxis.workspace`），
而是用 `ARCHEAXIS_PORTABLE_ROOT` 把宿主的数据根**引到我自己的 scratch 目录**，
**在那里建了 `data/`** ✓ —— 于是相对路径能解析，而**真实产品数据分毫未动** ✓

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Q02 全部验收项通过」 | Q02 的验收还包含**读写闭环、权限、只读桥接**等；本轮确证的是**生命周期** |
| 「真实产品数据目录下不需要 `data/`」 | **未判定** —— 也可能是安装器本该创建它，那属于安装布局问题 |

**但「宿主能构建、能加载界面、能迁移、能启动 Core、并自述可用」—— 这条链现在是通的。**

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根并跑宿主 | `.project-local/runs/host-driven-core/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**（只用环境变量把宿主引开）；**未删除任何东西**。
