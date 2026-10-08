historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02：**哈希证明产品数据库未被修改 —— 以及本轮没看到的那些**

## 1. ✅ 用哈希回答第 85 轮的未决点

```
"live_db_path":       "C:\Users\ALEX\AppData\Local\com.archeaxis.workspace\archeaxis.sqlite"
"live_db_bytes_before": 995328        "live_db_bytes_after": 995328
"live_db_sha_before": "0fe14e08a6de6018218c4fbb62726b632d98f4359bcdfdd3b661e64a777ef613"
"live_db_sha_after":  "0fe14e08a6de6018218c4fbb62726b632d98f4359bcdfdd3b661e64a777ef613"
"live_db_unchanged":  true
```

**第 85 轮我只能说「它不在修改时间列表里」，那是弱证据；**
**本轮**前后取哈希一致** —— 这是强证据。**

> **结论：我启动宿主的行为，没有修改那个产品数据库。**

## 2. ⚠️ 但本轮有几个「没看到」，我要如实列出

| 项 | 结果 |
| --- | --- |
| `saw_migrate` | **false** —— 没有任何子进程命令行里含 `migrate` |
| `saw_core` | **false** —— 同上 |
| scratch 目录增长 | **158 → 163 → 164**，但列出的文件**全是 `EBWebView\…`**（WebView2 状态） |

**即：这一轮我没有观察到后端跑迁移。** 这与第 84 轮不同（那轮明确抓到了 `-m app.runtime_entrypoint migrate`）。

## 3. 我**不**声称的（以及两种可能）

| 可能 | 说明 | 我能否判定 |
| --- | --- | --- |
| **A** 我设的 `ARCHEAXIS_PORTABLE_ROOT` **没有生效**，解析仍走 `installed-stable`，迁移对着**真实库**跑 | 若真如此，`live_db_unchanged` 仍为 true，**说明迁移是空操作** | ❌ **未判定** |
| **B** 本次后端**根本没起来**（解析失败或其它） | 那 `live_db_unchanged` 就更自然 | ❌ **未判定** |

**而「真实库未变」最可能的解释是**：那是一个**官方的、已经迁移完成**的库（972 KB 级），
**`migrate` 在这种库上是空操作** ✓ —— **所以「没变」是预期结果，不是失败的证据。**

**但这是我的推断，不是实测。**

## 4. 为什么 `ARCHEAXIS_PORTABLE_ROOT` 可能没生效

源码里 `portable_root_for_executable()` 确实优先读这个环境变量 ✓；
**但 `main.rs` 里有两个解析入口**（第 303 行的 `resolve_runtime_with_portable_root` 与第 768 行的 `RuntimeResolutionContext`）——
**我没有核实 setup 那条路是否也把 portable root 传进去。**

**这是一个具体的、可查的下一步，而不是模糊的猜测。**

## 5. 本轮的正确表述

| 可以说 | 不能说 |
| --- | --- |
| 产品数据库在本次运行前后**哈希一致** | 「本轮后端确实跑了迁移」 |
| 本轮**未观察到** `migrate`/`core` 子进程 | 「后端没有启动」 |
| scratch 目录的增长**全部来自 WebView2** | 「portable root 生效了」 |

## 6. 本轮未做

1. **未**改任何仓库文件；
2. **未**触碰官方 Green 的 `data/` 与资料库；
3. **未**从任何目录删除东西；
4. 全程**只 kill 自己起的宿主句柄**。
