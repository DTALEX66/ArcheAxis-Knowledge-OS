historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**假设被否 + 我又犯了一次截断错误**

## 1. 我的假设被否：`ARCHEAXIS_PORTABLE_ROOT` **确实**传到了解析

第 86 轮我提出「portable root 可能没生效」，并把它列为「具体可查的下一步」。本轮查了：

```rust
// src-tauri/src/main.rs
759:  let portable_root = match std::env::current_exe() {
760:      Ok(executable) => runtime::portable_root_for_executable(&executable),  // 读环境变量
768:  let resolver = RuntimeResolutionContext { manifest_dir: legacy_manifest,
770:      resource_dir: resources, local_data_dir: local_data.clone(),
772:      portable_root, };
779:  let resolved_runtime = resolver.resolve();
```

```rust
// main.rs:293-308
297:      portable_root: Option<PathBuf>,
308:          self.portable_root.as_deref(),       // 【传进去了】
```

**所以 portable 分支确实会被命中，数据应当写到我的 scratch 目录。**
**我第 86 轮那个猜测是错的 —— 这一步本来就没问题。**

## 2. ⚠️ 而真正的问题是：**我把答案截断掉了**

第 86 轮我的探针输出写的是：

```python
receipt["portable_dir_files"] = files[:14]      // 按字母序取前 14
```

**而 `EBWebView\...` 在字母序里排在最前** —— 于是：

```
"portable_dir_files": [ "EBWebView\Crashpad\metadata",
                       "EBWebView\Default\Cache\...", ... ]   // 前 14 个全是它
"portable_file_count": 164                                    // 初始 158 → +6 个
```

**那 +6 个文件是什么，我根本没看。** 而它们**正是能回答「迁移写没写」的东西。**

> **这与第 54 轮我截断自己的 JSON 是同一类错误：为了控制输出长度，把结论本身切掉了。**
**我该做的是按扩展名统计、或排除 `EBWebView`，而不是取前 N 个。**

## 3. 所以现在的状态是

| 问题 | 状态 |
| --- | --- |
| portable root 是否生效 | ✅ **生效**（源码确认，通道完整） |
| 迁移是否写进了 scratch 目录 | ❌ **未知 —— 我把能回答它的输出截断了** |
| 第 86 轮「没看到 migrate」 | ⚠️ **可能是同一原因**：命令行也是按集合取的，但那次我确实看了全部 `child_lines[:10]` |
| 真实产品数据库 | ✅ **哈希一致**（第 86 轮已证） |

## 4. 下一轮（正确做法）

重跑一次，但输出改成：

```
按扩展名统计 scratch 目录        // .sqlite / .sqlite-wal / .json / .lock 各几个
排除 EBWebView 后列出全部文件    // 而不是前 14 个
子进程命令行按「含 migrate / 含 core / 其它」分类统计
```

**这样无论文件多少，答案都不会被截掉。**

## 5. 本轮未做

1. **未**重跑（下一轮）；
2. **未**改任何仓库文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. **未**删除任何东西。
