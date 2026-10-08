historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# 🎉 AAOS-01 Q02：**Core 起来了 —— 根因判断被证实**

## 1. 实测：宿主真的派生了后端

```json
"child_count": 2,
"children_of_host": [
    { "name": "msedgewebview2.exe", "pid": "4768" },
    { "name": "python.exe", "pid": "29660",
      "command": "\"\\\\?\\C:\\Windows\\Temp\\aaos-target\\debug\\runtime\\python\\python.exe\"
                  -B -I -m app.runtime_entrypoint migrate" }
]
```

**这就是 Q02 要的「实际 Core 生命周期」的第一步。**

## 2. 为什么这是**我改布局**的直接证据

**命令行里的路径是**：

```
…\debug\runtime\**python\python.exe**        <- 【我刚刚创建的那一层】
```

**在我改布局之前**，这个文件不存在 → 解析失败 → 自启线程不派生（第 83 轮已从源码证明该链路）。
**改完之后它立刻派生** —— **因果链闭合，而且是可复现的结构关系，不是巧合。**

## 3. 它跑的是 `migrate`，不是 `core`

```
-B -I -m app.runtime_entrypoint **migrate**
```

**`-B`**（不写 bytecode）、**`-I`**（隔离模式）—— 与「隔离 Python worker」的架构一致 ✓；
**`migrate`** 说明启动序列是**先迁移、后就绪** ✓（第 28 轮读到的 `BackendProcess::launch` 会走迁移 + 就绪等待）。

**所以下一步要观察的是**：它是否继续走到 `core`、以及 readiness 是否达成 ✓。

## 4. `data_file_count: 0` 也有了合理解释

我探针把 `ARCHEAXIS_DATA_DIR` 指向自己的临时目录，但**解析器默认分支并不用它**：

```rust
142:  let data_dir = project_root_for_resource(resource_dir)
143:      .map(|root| root.join(".project-local/task-runtime/desktop-installed"))
144:      .unwrap_or_else(|| local_data_dir.to_path_buf());
```

**即：数据写在 `project_root/.project-local/task-runtime/desktop-installed`** ——
**所以我的探针目录是空的，而这不是故障。**

## 5. 现在的 Q02 状态（相当完整了）

| 组成 | 状态 |
| --- | --- |
| 宿主**能构建**（无空格 `--target-dir`） | ✅ |
| 宿主**能启动**、WebView2 在跑 | ✅ |
| 前端已构建并嵌入 | ✅ |
| **runtime 解析成功**（布局修正后） | ✅ **本轮** |
| **宿主派生了后端进程**（`python.exe -B -I -m app.runtime_entrypoint migrate`） | ✅ **本轮** |
| 后端走到 `core`、readiness 达成、数据落盘 | ⏳ **下一轮** |
| 前端页面正确加载（debug 走 devUrl 的问题） | ⏳ 仍是独立问题 |

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Q02 通过」 | 交付物是**完整**的 Core 生命周期；目前只观察到**迁移**这一步 |
| 「前端问题解决了」 | 它仍是独立问题 |
| 「改布局是唯一修法」 | 我也没排除其它条件（worker-profile 等） |

**但这一轮从一个「从未起来过」的状态，第一次走到了「后端由宿主派生」。**

## 7. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 把 Python 发行版移到 `rt/runtime/python/` 下 | `<worktree>/.project-local/rt/` | **项目自有开发 staging**，不是产品文件 ✓ |

**没有改任何仓库内的实现文件或配置** —— 只是把我自己的 staging 摆成代码要求的样子 ✓。

## 8. 本轮未做

1. **未**观察后端是否走到 `core` 与 readiness（下一轮）；
2. **未**改任何仓库文件；**未**触碰官方 Green 的 `data/` 与资料库。
