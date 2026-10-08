historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# 🎯 AAOS-01 Q02：**WebDriver 通了，而且它揭穿了真正的根因**

## 1. WebDriver 会话成功建立

```
"status_code": 200
"status_body": {"build": {"version": "154.0.4258.48"},
                "message": "msedgedriver ready for new sessions.", "ready": true}
"session_status": 200
"session_id": "c9adb3e38a5091ed0a32b7ffc77e9a33"
"session_body": {"browserName": "webview2", "browserVersion": "154.0.4258.48", ...}
"page_source_status": 200   "page_source_len": 317612
```

**即：宿主已经在 WebDriver 控制之下，而且我能读到它的 DOM。** 这一步成了。

## 2. 但 DOM 告诉我的，是一件我没料到的事

```html
<html dir="ltr" lang="zh"><head>
  <title>127.0.0.1</title>
  <style>/* Copyright 2017 The Chromium Authors
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file. */
```

**这是 Chromium 的「无法访问此网站」错误页。**

```
"mentions_retry": false      <- 页面里没有「重试」
"data_file_count": 0
```

## 3. 所以真正的根因是

```
宿主是【debug 构建】  →  Tauri 用 devUrl 而不是 frontendDist
   →  它去加载 http://127.0.0.1:5173   →  那里【没有服务器】
      →  WebView 显示错误页  →  没有 React 应用
         →  没有人调用 retry_backend  →  Core 从不启动
```

**`tauri.conf.json:8` 就是那行**：

```json
"devUrl": "http://127.0.0.1:5173"
```

**我第 72 轮辛苦构建的 `frontend-dist`，在 debug 构建里根本用不上。**

## 4. 我要更正自己第 73 轮的推断

第 73 轮我看到窗口标题正确，就写下：**「前端确实加载并渲染了」**。

**那个推断是错的。** 证据是：

| 我看到 | 我当时以为 | 实际是 |
| --- | --- | --- |
| 窗口标题 `星环知识平台（ArcheAxis Knowledge）` | 前端渲染出来了 | **Tauri 的窗口配置标题** —— 与加载了什么页面**无关** |

**标题正确只证明「窗口存在」，不证明「页面加载成功」。** 我用一个更弱的证据下了更强的结论。
**这次是 WebDriver 读到的 DOM 把真相摆出来的。**

## 5. 修法（两条，都很干净）

| 方案 | 做法 |
| --- | --- |
| **A（推荐）** | **`cargo build --release`** —— release 构建用 `frontendDist`，即我刚构建好的那 281,808 字节 |
| **B** | 在 5173 起一个 Vite 服务器（`npm --prefix frontend run dev`），让 dev 构建能连上 |

**A 更干净**：不引入常驻开发服务器，正好也符合任务书「不依赖开发服务器」的要求。

## 6. 本轮未做

1. **未**做 release 构建（下一轮）；
2. **未**改任何实现文件；**未**触碰官方 Green 与资料库；
3. 全程**只关闭自己起的进程句柄**（`driver.kill()` + `DELETE /session`），**未按进程名杀进程**。

## 7. 顺带记下的工具事实

| 事实 | 值 |
| --- | --- |
| `tauri-driver` 的 `/status` | 200，`ready: true` |
| 会话能力 | `browserName: webview2`，`browserVersion: 154.0.4258.48` |
| 原生驱动 | `msedgedriverVersion: 154.0.4258.48`（**与运行时精确匹配**） |
| `debuggerAddress` | `localhost:60575` |
