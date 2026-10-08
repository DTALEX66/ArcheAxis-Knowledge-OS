historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02：**截断悬念结清 —— 但露出一个新情况**

## 1. 上一轮的悬念结清了

第 87 轮我说「`files[:14]` 按字母序取前 14，`EBWebView` 排最前，可能把答案截掉了」。
本轮改成**不可能被截断的统计方式**：

```python
receipt["by_extension"] = dict(Counter(i.suffix.lower() for i in files))   // 按扩展名计数
outside = [str(i) for i in files if "EBWebView" not in i.parts]            // 排除 WebView 后全列
```

**结果：**

```
"total_file_count": 166
"outside_webview_count": 0
"outside_webview_files": []
```

> **scratch 目录里除了 `EBWebView` 什么都没有 → 我上一轮担心的「截断藏了答案」并不成立：那里本来就没东西。**

**这一条我应当接受：我的截断顾虑是对的，但它这次没有掩盖任何结论。**

## 2. ⚠️ 但露出一个**新**情况：本轮连 python 子进程都没有

| 轮次 | `ARCHEAXIS_PORTABLE_ROOT` | 观察到的子进程 |
| --- | --- | --- |
| **84** | 未设 | ✅ **`python.exe -B -I -m app.runtime_entrypoint migrate`** |
| **85** | 未设 | ✅ `python.exe`（命令行空） |
| **88（本轮）** | **已设** | ❌ **只有 `msedgewebview2.exe`** |

```
"child_distinct": 1
"child_lines_excluding_webview": []
"saw_migrate": false   "saw_core": false
```

**即：设了 portable root 之后，后端没有起来。**

## 3. 两种可能，我**不**判定

| 可能 | 说明 |
| --- | --- |
| **A** portable 分支下 `BackendProcess::launch` **真的失败了**（`record_failure`） | 那界面会停在恢复态 |
| **B** 子进程**存在但太短命**，我的 150 毫秒轮询没抓到 | 失败的 migrate 可能在 150 毫秒内就退出 |

**源码上 portable 分支应当成功**（`runtime/python/python.exe` 存在 ✓、`portable_root` 是绝对路径 ✓ → 返回 `Ok(RuntimeSpec{profile:"portable-stable"})`）；
**所以「解析失败」不是原因** —— 若真失败，是**启动**那一步，不是**解析**那一步。

## 4. 已确证的三件事（本轮）

| 事实 | 依据 |
| --- | --- |
| scratch 目录**只有 WebView2 状态**，没有任何迁移产物 | `outside_webview_count: 0`，按扩展名统计亦然 |
| 真实产品数据库**前后哈希一致** | `live_db_sha_before == after`（再次确认） |
| 设 portable root 后**未观察到后端子进程** | 75 秒 × 150 毫秒轮询，`child_distinct: 1` |

## 5. 下一轮该怎么查（具体）

1. **捕获宿主的 stdout/stderr**（此前我一直丢弃它们）—— 失败记录或 panic 会出现在那里；
2. **降低轮询间隔到 ~30 毫秒**，或改用一次性「枚举全部后代」的方式，避免漏掉短命进程；
3. **对照不设 portable root 的那一轮**，看差别到底出在解析还是启动。

## 6. 本轮未做

1. **未**改任何仓库文件；**未**触碰官方 Green 的 `data/` 与资料库；
2. **未**删除任何东西；
3. 全程只 kill 自己起的宿主句柄。
