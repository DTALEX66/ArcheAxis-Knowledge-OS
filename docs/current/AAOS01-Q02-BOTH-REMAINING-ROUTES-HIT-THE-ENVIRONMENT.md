historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**两条路都撞到环境 —— 我停在这里，并说清为什么**

第 74 轮查明：Core 由**界面点「重试」**触发（设计如此）。本轮评估两条能拿到「Core 生命周期」的路。

## 路一：Tauri WebDriver（任务书点名的那条）—— **两样东西都不在**

| 需要 | 实测 |
| --- | --- |
| `tauri-driver` | ❌ **不在 PATH**，也不在 rustup 工具链或 `.cargo\bin` 里 |
| `msedgedriver.exe` | ❌ **Edge 根目录下没有** |
| 仓库里有可用配置吗 | ❌ 只有任务书**提到**它，**没有**任何现成装置 |

**要补齐它，需要**：`cargo install tauri-driver`（**全局工具链变更**）+ 从微软**下载** `msedgedriver`（**网络下载**）。
**两条都越过我的边界** → **需要你点头**。

## 路二：宿主**自己的**生命周期测试 —— 编译过了，跑不起来

我找到 `desktop/src-tauri/tests/backend_lifecycle.rs` —— **它直接调用 `BackendProcess::launch`**，
看起来正是「实际 Core 生命周期」的现成证据。

**结果**：

```
Compiling archeaxis-desktop-shell v0.6.14
Finished `test` profile in 49.55s
Running tests\backend_lifecycle.rs
error: test failed
  process didn't exit successfully (exit code: 0xc0000139, STATUS_ENTRYPOINT_NOT_FOUND)
```

**它编译通过，但测试二进制起不来**（`STATUS_ENTRYPOINT_NOT_FOUND` = 某个 DLL 的入口点对不上）。

我按 mingw 的常规修法把 `libgcc_s_seh-1.dll` / `libwinpthread-1.dll` / `std-*.dll` 复制到旁边 ——
**同一个错误依旧**。

## 我为什么在这里停手（而不是继续挖）

1. **这是测试**运行环境**的问题，不是产品的问题** —— 二进制能编译、能链接，只是加载期 DLL 解析失败；
2. 我在这个会话里**已经有过「越挖越偏」的教训**（第 69 轮前后）；
3. **更重要的**：即便把它跑通，它验证的也只是 **`BackendProcess::launch` 这一层**，
   **不是**任务书要求的那种「**Tauri WebDriver 的真实 Windows 旅程**」——
   **任务书自己就把这两者分开**（「浏览器通过不等于 Tauri 安装态通过」）。

**所以我不会拿一个组件级测试去冒充 Q02 的交付物。**

## 于是 Q02 的精确状态

| 项 | 状态 |
| --- | --- |
| 宿主**能构建**（无空格 `--target-dir`） | ✅ 12.62 秒 |
| 宿主**能启动**、WebView2 在跑、**窗口标题正确** | ✅ |
| **前端已构建并嵌入** | ✅ 281,808 字节 |
| **启动序列已由源码查明**（点「重试」才起 Core） | ✅ 第 74 轮 |
| **Core 生命周期被观察到** | ❌ **需要 WebDriver 或你的决定** |

## 需要你选（Q02 的收尾方式）

| 选项 | 你需要的动作 | 之后我能做的 |
| --- | --- | --- |
| **A** | 允许 `cargo install tauri-driver` **并** 下载 `msedgedriver` | 用任务书点名的方式跑真实桌面旅程，**点一次「重试」**，拿到 Core 生命周期 |
| **B** | 接受「**组件级**生命周期证据」（我继续修那个 DLL 环境问题） | 拿到 `BackendProcess::launch` 层面的生命周期，**但明确标注它不等于真实桌面旅程** |
| **C** | 交给别处有完整 WebDriver 环境的机器 | Q02 不在本机收尾 |

**我倾向 A** —— 它是任务书指定的工具，也是唯一能真正闭合 Q02 的路径。**但它需要你放行两项全局动作。**

## 本轮未做

1. **未**安装 `tauri-driver`、**未**下载 `msedgedriver`（**越界，等你**）；
2. **未**继续深挖 DLL 问题（**有意停手**，理由见上）；
3. **未**改任何实现文件；**未**触碰官方 Green 与资料库；
4. 全程**只监视自己的进程树、只 kill 自己的句柄**。

## 临时遗留物

`C:\Windows\Temp\aaos-target`（无空格构建目标）—— **保留**，后续仍需其构建宿主；
其中 `debug\` 下多出三个从 gnu 工具链复制的 DLL（**仅为排查，未生效**）。
