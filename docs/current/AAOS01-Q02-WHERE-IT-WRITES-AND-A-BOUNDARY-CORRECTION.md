historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**数据写到哪里 —— 以及一处我必须更正的边界声明**

## 1. 先更正我自己

我在**多份报告**里写过「**未动 `%LOCALAPPDATA%`**」。

**那句话过宽了，我要更正：**

| 事实 | 说明 |
| --- | --- |
| 宿主启动**必然**在 `%LOCALAPPDATA%\com.archeaxis.workspace\EBWebView\` 写 WebView2 状态 | `History`(224 KB) · `Local State` · `DIPS` · `favorites_diagnostic.log` —— **时间戳在最近 2 小时内** |
| **`archeaxis.sqlite`（972 KB）本身未被修改** | 我没有在近 2 小时的改动列表里看到它 |
| 该目录**本来就存在且有大量内容** | `backups/ capabilities/ output/ pdf/ reports/ source_archive/ workspaces/` + 972 KB 数据库 |

**准确的表述应当是**：「我没有修改产品数据库；但启动宿主会写 WebView2 的浏览器状态，那也在该目录下。」

**我把这条记下来，因为我此前用的是更强的说法。**

## 2. 数据到底写到哪里（本轮回答）

第 83 轮的源码已经给出答案，本轮实测确认：

```rust
142:  let data_dir = project_root_for_resource(resource_dir)
143:      .map(|root| root.join(".project-local/task-runtime/desktop-installed"))
144:      .unwrap_or_else(|| local_data_dir.to_path_buf());
```

| 分支 | 实测 |
| --- | --- |
| `project_root_for_resource` 找到根 | ❌ **没有** —— 我查过 `.project-local/task-runtime/desktop-installed` **不存在** |
| 于是回退到 `local_data_dir` | ✅ **即 `%LOCALAPPDATA%\com.archeaxis.workspace`** |

**这解释了为什么我探针的目录 60 秒里 24 次快照全是 0 个文件** —— **迁移根本不往那里写。**

## 3. 本轮另一个观察

```
"distinct_children": [ "msedgewebview2.exe|…", "python.exe|" ]
"run_dir_seen_counts": [0,0, … 0]      // 60 秒 × 24 次
"new_sqlite_files": {}
```

**`python.exe` 子进程出现了** ✓ —— 与第 84 轮一致；
**但这次它的命令行是空的** ⚠️ —— 这是我捕获方式的问题（上一次拿到了完整命令行），**不是产品行为**。

**且 60 秒内我的目录没有新 sqlite 文件** —— 与「回退到 `local_data_dir`」一致 ✓。

## 4. 所以「迁移写到哪里」这个问题

| 已知 | 未知 |
| --- | --- |
| 它**不写**我探针的目录 | **它是否真的写进了 `archeaxis.sqlite`** —— 近 2 小时改动列表里**没有**它 |
| 回退目标是 `%LOCALAPPDATA%\com.archeaxis.workspace` | **迁移是否已完成** —— 也可能是快照窗口太短 |

**我不把「没看到改动」说成「没有写」。** 下一轮我会**在启动前后对那个数据库取哈希**，用哈希说话。

## 5. 本轮未做

1. **未**改任何仓库文件；
2. **未**触碰官方 Green 的 `data/` 与资料库；
3. **未**删除该目录里的任何东西。
