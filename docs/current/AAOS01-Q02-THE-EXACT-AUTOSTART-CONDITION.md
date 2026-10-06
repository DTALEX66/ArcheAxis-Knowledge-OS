historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**自启的确切条件 —— 解析失败就整段跳过**

## 1. 决定性的一段（`src-tauri/src/main.rs`）

```rust
780:  let webview_data_dir = resolved_runtime       // runtime 解析【早于】建窗口
          .as_ref().map(|r| r.data_dir.clone())
          .unwrap_or_else(|_| local_data.clone());
787:  let pending_runtime = match resolved_runtime {
788:      Ok(runtime) => { ...; Some(runtime) }
801:      Err(error) => { record_failure(&startup_backend, &error); None }   // 【失败 → None】
806:  WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
807:      .title("星环知识平台（ArcheAxis Knowledge）")                        // 【标题在这】
812:  if let Some(runtime) = pending_runtime {      // 【None 就整段跳过】
814:      std::thread::spawn(move || {
819:          match BackendProcess::launch(&runtime) {
```

**即**：

```
runtime 解析失败  →  record_failure  →  pending_runtime = None
   →  if let Some(runtime) 不成立  →  自启线程【根本不派生】
      →  没有 Core、没有数据文件、界面停在恢复态
```

**这与我实测到的三件事**逐项吻合**（无子进程、`data_file_count: 0`、RecoveryShell）。**

## 2. 顺带闭合一处此前的更正（拿到精确行号）

```rust
807:  .title("星环知识平台（ArcheAxis Knowledge）")
```

**窗口标题就是这行写死的** —— 与**加载了什么页面无关**。
这**正是我第 76 轮更正的依据**（第 73 轮我从标题推断「前端已加载」，那是过度概括），**现在有确切行号了**。

## 3. 另一条线索：`WebviewUrl::App("index.html")`

代码请求的是 **`index.html`**（应用内资源），**不是** `devUrl` 字面量；
但 Tauri 会按构建模式把 `App("index.html")` 映射到**开发服务器**或**嵌入资源**。
**我的 debug 构建走了前者 → 127.0.0.1:5173 → 无服务 → Chromium 错误页。**

**所以第 76 轮的结论（debug 走 devUrl）仍然成立，只是机制现在更清楚了。**

## 4. 因此方向很明确

**关键在 `resolved_runtime` 是怎么来的** —— 它在第 780 行**之前**就已经是 `Ok`/`Err` 了。
**那个解析器要求什么目录形态，就是下一轮要读的。**

**而老 Green 的形态是最可能的答案**（`runtime/`、`frontend/`、`ArcheAxis.exe` 平铺在一起，
旁边还有 `worker-profile.json` 的对应物）—— **这与权威索引 L14 说的「应用旁 worker-profile.json」一致**。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「我的构建就是因为 runtime 解析失败」 | **未验证** —— 我只证明「解析失败会导致整段跳过」这一机制 |
| 「前端已无问题」 | 前端是**独立**问题（debug 模式映射到 devUrl） |

**机制已证实；我的现场是否命中该机制，尚未证实。**

## 6. 本轮未做

1. **未**读解析器本身（下一轮）；
2. **未**改任何实现文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. 全程**只读**。
