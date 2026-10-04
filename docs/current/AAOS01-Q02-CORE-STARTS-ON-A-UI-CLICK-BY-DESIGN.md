# AAOS-01 Q02：**诊断完成 —— Core 只在「界面点一下」之后才启动，这是设计**

第 70–73 轮我一步步收窄。本轮**读到前端源码，链条闭合**。

## 1. 关键三行

```tsx
// frontend/src/app/App.tsx:27
const RECOVERY_BOOT_POLL_MS = 250;        // 启动后每 250ms 轮询

// frontend/src/components/RecoveryShell.tsx:180
<button type="button" className="primary" disabled={disabled}
        onClick={() => void perform("retry", ...)}>          // 重试是一个【按钮】

// frontend/src/runtime/recovery.ts:121
export function isRecoveryReady(status) {
  return status.state === "ready" && status.backend_available && !status.safe_mode;
}
```

**而且 `workspace.ts:301` 是唯一调用 `retry_backend` 的地方，它就在 `perform("retry")` 背后。**

## 2. 所以启动序列是

```
前端加载  →  每 250ms 轮询 recovery_status（只读）
   →  发现后端不可用  →  渲染 RecoveryShell
      →  【停下，等用户点「重试」】  →  那时才调用 retry_backend
         →  BackendProcess::launch  →  Core 启动
```

**这解释了此前每一个观察**：窗口起来了、标题正确（前端确实在跑）、
**没有 Core 子进程、数据目录 0 文件且不churn（它在静止等待，不是在崩溃重试）。**

## 3. 所以我此前那句「Core 没有起来」应当更准确地表述

| 我此前写的 | 更准确的 |
| --- | --- |
| 「Core 没有起来」（像是个问题） | **「Core 在等一个界面动作 —— 这是设计」** |

**无人值守启动时它永远不会自己起 Core** —— 因为**没有任何代码路径**在启动时调用 `retry_backend`。
**这不是缺陷，是产品选择**：核心由用户显式触发。

## 4. 因此 Q02 的交付物需要什么

要拿到「实际 Core 生命周期」，必须**真的点那个按钮**。而它是 **WebView 里的 HTML 按钮** ——
**Win32 消息点不到 HTML 元素**（那条路只能发窗口消息，如 `WM_CLOSE`）。

**任务书自己指明了工具**：

> 测试分层：既有 Rust/Python 回归 + 协议/迁移测试 + Web 内容组件交互测试 +
> **Tauri WebDriver 的真实 Windows 旅程**。

**即：这一步要用 Tauri WebDriver，而不是窗口消息。**

## 5. 于是 Q02 的状态可以精确表述了

| 项 | 状态 |
| --- | --- |
| 宿主能**构建** | ✅ 12.62 秒（无空格 `--target-dir`） |
| 宿主能**启动**、WebView2 在跑 | ✅ |
| **前端已构建并嵌入**（281,808 字节） | ✅ |
| **窗口起来、标题正确** | ✅ |
| **启动序列已由源码查明** | ✅ **本轮** |
| **Core 生命周期被观察到** | ❌ **需要 WebDriver 点一次「重试」** |

**最后一项仍是 Q02 的交付物，所以我仍不声称 Q02 通过** —— 但我现在**知道缺的是什么、以及该用什么工具**。

## 6. 本轮未做

1. **未**尝试用 Win32 去点 HTML 按钮（**做不到，且不该假装做到了**）；
2. **未**引入 WebDriver（下一轮评估：需要 `tauri-driver` + msedgedriver）；
3. **未**改任何实现文件；**未**触碰官方 Green 与资料库；
4. 全程**只监视自己的进程树、只 kill 自己的句柄**。
