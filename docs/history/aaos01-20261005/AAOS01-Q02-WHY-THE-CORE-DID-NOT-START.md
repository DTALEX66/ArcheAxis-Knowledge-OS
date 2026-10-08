historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02：**Core 为什么没起来 —— 根因找到了（源码 + 配置）**

第 70 轮我如实写了「宿主起来了但 Core 没起来，**为什么尚未查明**」。本轮**查明了**。

## 1. 决定性的一条：Core 由**前端调用的命令**启动

```rust
// src-tauri/src/main.rs
467: #[tauri::command]                                        <- 前端调用的命令
470:   tauri::async_runtime::spawn_blocking(move || retry_backend_blocking(state))
...
526:     let launched = match BackendProcess::launch(&runtime) {   <- Core 在这里被拉起
528:         Err(error) => { record_failure(&state, &error);
530:             return Err(RECOVERY_RETRY_FAILED.to_owned()); }
```

**`BackendProcess::launch` 是在 `retry_backend_blocking` 里被调用的，**
**而那个函数由 `#[tauri::command]` 暴露给前端。**

> **也就是说：Core 不是宿主自动启动的，是前端调用命令后才启动的。**
**没有前端 JS，就没有那个调用 —— 也就没有 Core。**

## 2. 而前端**根本没有被构建**

```json
// src-tauri/tauri.conf.json
 8:  "devUrl": "http://127.0.0.1:5173",
 9:  "beforeBuildCommand": "npm --prefix ../frontend run build",
10:  "frontendDist": "../.project-local/build/frontend-dist"
```

| 事实 | 含义 |
| --- | --- |
| `beforeBuildCommand` = **`npm --prefix ../frontend run build`** | 前端由 **npm** 构建 |
| **裸 `cargo build` 从不运行它** | **所以我没有前端产物** |
| `frontendDist` = `../.project-local/build/frontend-dist` | 前端应落在这里 |

**实测那个路径**：`**不存在**`

## 3. 所以完整因果链是

```
裸 cargo build  →  只产出 Rust exe，不跑 npm  →  没有 frontend-dist
   →  WebView 没有前端可加载  →  前端从不调用 retry_backend
      →  BackendProcess::launch 从不被调用  →  Core 从不启动  →  不建库
```

**这与我第 70 轮观察到的现象逐项吻合**：宿主活着、WebView2 起来了、但**没有 Core 子进程、没有数据文件**。

## 4. 我第 70 轮猜错的那一次，与这次的分别

| 轮次 | 我的猜测 | 结果 |
| --- | --- | --- |
| 70 | 「resources 没被打包」 | ❌ **实测否掉**（`runtime/` 就在 exe 旁边） |
| 71 | 「前端没有被构建」 | ✅ **源码 + 配置 + 实测三者吻合** |

**差别在于这一轮我是先读调用链，再看配置，最后才实测的** —— 而不是先猜再验。

## 5. 因此正确的下一步是明确的

```
npm --prefix frontend run build        # 产出 .project-local/build/frontend-dist
（然后重新构建宿主，或改用 tauri build）
```

**这也解释了为什么 `devUrl` 指向 `http://127.0.0.1:5173`** ——
**开发时前端由 Vite 提供，生产时才用 `frontendDist`。两条路都需要前端先存在。**

## 6. 本轮未做

1. **未**运行 npm 构建（下一轮；注意 npm 缓存需指向项目内，见第 30 轮的教训）；
2. **未**改任何实现文件；**未**触碰官方 Green 与资料库；
3. 全程**未按进程名杀进程**。
