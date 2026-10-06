historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**我的 release 假设被否 —— 真正的开关是 `tauri build`**

## 1. 实测：release 构建**仍然**是 Chromium 错误页

我构建了 release 版并**用 WebDriver 读它的界面**：

```
"session_status": 200            // 驱动成功接管了 release 宿主
"page_status": 200               // 页面拿到了
"page_len": 317612
"is_chromium_error": true        // 【仍然是 Chromium 错误页】
"title_present": false           // 页面里没有「星环知识平台」
"page_head": "<title>127.0.0.1</title>" + Chromium 错误页样式
```

**所以第 76 轮我那句「debug 走 devUrl、release 用 frontendDist」是错的。**
**release 构建同样去加载 `http://127.0.0.1`，同样是错误页。**

## 2. 为什么

**dev/prod 的选择不是由 cargo 的 profile 决定的**，而是由 **`tauri-build`** 在构建时、
按 **`tauri` CLI 传入的标记**决定的。

```
cargo build            -> 走 dev 路径（加载 devUrl）
cargo build --release  -> 【也是 dev 路径】
tauri build            -> 生产路径（用 frontendDist 嵌入前端）
```

**即：我一直用错了工具。** 这个仓库的 `tauri.conf.json` 里写着 `beforeBuildCommand`
（`npm --prefix ../frontend run build`）与 `frontendDist` —— **那些字段本来就是给 `tauri build` 用的** ✓
**而我却试图用 `cargo build` 绕过它们。**

## 3. 这解释了此前的一连串现象

| 现象 | 现在的解释 |
| --- | --- |
| 窗口标题正确 | **`main.rs:807` 写死的**，与加载什么无关 |
| WebDriver 读到 Chromium 错误页 | 两种 cargo 构建**都走 devUrl** |
| 后端未就绪 / 界面停在恢复态 | 前端根本没加载 → 前端不会调 `retry_backend` |
| 第 76 轮我说「debug 走 devUrl」 | **半对**：写 debug 是对的，**把 release 排除掉是错的** |

## 4. 好消息：工具已经就位

`@tauri-apps/cli` **已经在 `frontend` 的 devDependencies 里**（我在第 74 轮读到过）✓；
前端产物**也已经构建好了**（281,808 字节）✓。

**所以下一步就是用 `tauri build`，而不是 `cargo build`。**

## 5. 我要认的

> **我构建了 release、验证了它有 `ArcheAxis.exe` 和嵌套 runtime，就以为「release 会解决前端」——
> 而没有先验证 release 到底加载了什么。**
> **又是「先假定机制、再拿构建成功当证据」。** 本轮是**读了界面**才发现假设不成立的。

## 6. 本轮未做

1. **未**运行 `tauri build`（下一轮）；
2. **未**改任何仓库文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. **未**删除任何东西；只 kill 自己起的驱动与宿主句柄。
