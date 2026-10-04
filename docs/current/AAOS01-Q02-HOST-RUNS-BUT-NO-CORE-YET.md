# AAOS-01 Q02：**宿主能启动、WebView 是真的 —— 但它没有拉起 Core**

Q02 的期望产物是「**实际 Core 生命周期和资料列表**」。本轮**第一次真的把它跑起来**并观察。

## 1. 实测：宿主活着，WebView 真在工作

```
"host_pid": 21644
"host_alive_after_5s": true
"host_alive_after_10s": true
"host_exit_code": null        （观察 24 秒后仍在运行）
```

它派生了**唯一一个**子进程：

```
msedgewebview2.exe
  --embedded-browser-webview=1
  --webview-exe-name=ArcheAxis.exe
  --webview-exe-version=0.6.14
```

**这说明 Tauri 外壳是真的、WebView2 真的起来了、版本号也对。**

## 2. **但是：Core 没有被拉起**

| 观察 | 值 |
| --- | --- |
| `child_count` | **1**（只有 WebView2） |
| **有没有 Python / Core 子进程** | ❌ **没有** |
| `data_file_count` | **0** |
| 24 秒内创建的数据文件 | **无** |

**即：界面起来了，但后端 Core 生命周期没有开始，也没有建库。**

## 3. 我先猜了一个原因，**猜错了**

我猜「裸 `cargo build` 不会带上 `tauri.conf.json` 声明的 `resources`，所以宿主找不到 runtime」。

**实测否掉了：**

```
C:\Windows\Temp\aaos-target\debug\
  ArcheAxis.exe
  WebView2Loader.dll
  runtime/          <- 【在】，就在 exe 旁边
```

工作树里 staged 的 runtime 也在（14 个条目）。**所以资源不是原因。**

## 4. 从构建警告里读到一条线索

构建时那三条 warning 里有一条很说明问题：

```
warning: associated items `failed`, `safe_mode`, `may_start_core`,
         `may_run_migrations`, and `recovery_operations_available` are never used
         --> src\recovery.rs:873
```

**`may_start_core` 这个函数从来没被调用过** —— 也就是说，
**宿主里那套「恢复态下是否允许启动 Core」的门并没有接上。**
这**不是**「被恢复态挡住了」，而是**那道门根本没接线**。

## 5. 所以我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「宿主有缺陷」 | 未成立 —— 更可能是**它需要界面交互**才启动 Core |
| 「Core 起不来」 | 未测到 Core 的启动路径 |
| 「资源缺失」 | **已实测否掉** |

**我能确定的只有**：**无人值守地启动它，24 秒内它没有拉起 Core、也没有建库。**
**为什么，尚未查明。**

## 6. 下一轮的路径（已由现有资产指明）

`desktop/scripts/verify_nsis_install.ps1` **早就知道该怎么做**：它 `Wait-ArcheAxisWindow` **等到窗口出现**，
然后**用 Win32 去驱动界面**。
**所以「驱动界面」才是让 Core 起来的下一步** —— 而不是继续等它自己动。

## 7. 纪律说明（§82）

本轮**只监视自己创建的进程树**、**只 kill 自己的句柄** —— **全程没有按进程名枚举或终止任何进程**。
这是我在第 66 轮发现自己的违规后，**实际改成的做法**。

## 8. 临时遗留物

| 路径 | 处置 |
| --- | --- |
| `C:\Windows\Temp\aaos-junction`（junction，第 69 轮为验证「源路径」而建） | **已删除** —— 它已被证明不是问题所在 |
| `C:\Windows\Temp\aaos-target`（无空格构建目标） | **保留** —— 后续构建仍需要 |

## 9. 本轮未做

1. **未**改任何实现文件；
2. **未**触碰官方 Green 与资料库；
3. **未**用 `tauri build`（下一轮可考虑，用于 Q14 的当前版候选包）。
