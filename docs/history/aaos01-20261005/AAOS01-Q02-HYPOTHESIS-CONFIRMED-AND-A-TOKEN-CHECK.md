historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# 🎯 AAOS-01 Q02：**假设被证实 + 核心只差一个强 token**

## 1. ✅ 第 99 轮那个假设，本轮被证实

```
EXISTS  C:\Users\ALEX\AppData\Local\com.archeaxis.workspace
absent  C:\Users\ALEX\AppData\Local\com.archeaxis.workspace\data      // ★ 不存在
```

| 环节 | 值 |
| --- | --- |
| 启动器设的数据库路径 | **`data/archeaxis.sqlite`（相对）** |
| 它相对谁解析 | `command.current_dir(&runtime.cwd)` = **数据目录** |
| 那个数据目录下有 `data/` 吗 | ❌ **没有** |

**所以启动器的数据库路径指向一个不存在的目录** —— 这就是**它失败、我成功**的环境差异。

**第 99 轮我把这条标为「假设，未验证」。本轮验证了。**

## 2. 🎯 `core` 给出了完整 traceback（界面给不出的那个）

```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File .../app/runtime_entrypoint.py, line 338, in <module>
    raise SystemExit(main())
  File .../app/runtime_entrypoint.py, line 334, in main
    return int(args.func(args) or 0)
  File .../app/runtime_entrypoint.py, line 82, in run_core
    _run_desktop_core()
  File .../app/runtime_entrypoint.py, line 94, in _run_desktop_core
    raise RuntimeError("desktop core requires a strong launch token")
RuntimeError: desktop core requires a strong launch token
```

**这是界面截断掉的那段 traceback 的全文。** 它说明：

| 事实 | 含义 |
| --- | --- |
| 模块**加载成功**、`main()` **进入**、`run_core` **被调用** | 前面所有修复都到位 ✓ |
| 失败点是**鉴权校验**，不是导入、不是迁移 | **代码在主动拒绝我的弱 token** |
| 我给的 token 是 `local-diagnostic-token` | **是我的问题，不是产品缺陷** |

**所以：用一个强 token 重跑，Core 就有可能真的起来。**

## 3. 本轮的位置

```
宿主构建 ✓  →  界面加载 ✓  →  runtime 解析 ✓
   →  迁移 【MIGRATE_EXIT=0】 ✓
      →  core  【鉴权：token 强度】← 现在卡在这一格，而且是可修的
```

## 4. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「换上强 token 就能就绪」 | **未验证** —— 鉴权之后还有 readiness 等条件 |
| 「已经找到全部问题」 | 这一路一直是「修一个、前移一格」 |

## 5. 一个我自己的小失误（记录在案）

我的探测脚本里用了 `timeout /t 1 /nobreak`，在被管道接管的 pwsh 下会报
`Input redirection is not supported` —— 那是我脚本写法的问题，**与产品无关**；
而且它不影响结论（core 的 traceback 已经写进了文件，我读到了）。

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 在临时目录跑了 migrate + core | `.project-local/runs/core-manual/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**（只**只读地**检查了 `data/` 是否存在）；
**未删除任何东西**；只 kill 自己起的进程。
