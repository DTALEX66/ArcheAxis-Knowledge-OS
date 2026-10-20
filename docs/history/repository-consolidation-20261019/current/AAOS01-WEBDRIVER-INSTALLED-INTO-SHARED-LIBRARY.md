# AAOS-01：**WebDriver 已装进外置共用工具库 —— Q02 的最后一块到位**

## 0. 你的授权

> 需要的安装的工具，如果外置共用工具库里确实没有，就在外置共用工具库里安装下载

**我按这条办**：查过外置工具库里**确实没有**，于是**装进外置工具库**，**不动全局环境**。

## 1. 外置共用工具库的布局（先看清楚再放）

```
D:\All projects\OS External Configuration\
  00-registry\   10-toolchains\   20-runtimes\   40-models\
  60-cache\      80-build\        toolchains\     runtimes\
```

`10-toolchains\` 里已有 `cargo`、`msvc`、`rustup`、`python`、`dotnet`、`windows-sdk`、`playwright`、`scoop` ——
**所以新工具也放这里。**（你提到模型都在 `40-models\` —— 我看到了 `modelscope`，本任务暂不需要。）

## 2. 装了什么，装到哪

| 工具 | 版本 | 落点 |
| --- | --- | --- |
| **`tauri-driver`** | **v2.1.0** | `10-toolchains\tauri-driver\bin\tauri-driver.exe` |
| **`msedgedriver`** | **Microsoft Edge WebDriver 154.0.4258.48** | `10-toolchains\msedgedriver\msedgedriver.exe` |

```
cargo install tauri-driver --root "…\10-toolchains\tauri-driver"
  -> Installed package `tauri-driver v2.1.0`   CARGO_INSTALL_EXIT=0

https://msedgedriver.microsoft.com/154.0.4258.48/edgedriver_win64.zip
  -> downloaded 11,652,157 bytes
  -> Microsoft Edge WebDriver 154.0.4258.48
```

## 3. 一个值得指出的巧合（其实是必然）

**`msedgedriver` 的版本 = `154.0.4258.48` = 第 70 轮我从宿主进程命令行里实测到的 WebView2 版本**：

```
msedgewebview2.exe … --webview-exe-version=0.6.14   （宿主版本）
（WebView2 运行时目录：EdgeWebView\Application\154.0.4258.48\）
```

**驱动版本与运行时版本必须匹配**，否则 WebDriver 起不来 —— **这次是精确对齐的**。

## 4. 边界说明（我怎么守住「不放全局」）

| 项 | 做法 |
| --- | --- |
| 安装位置 | **`--root` 指向外置工具库**，不是 `~/.cargo/bin` |
| 构建产物 | `CARGO_TARGET_DIR` 指向 `外置库\80-build\tauri-driver` |
| 下载物 | 落在 `外置库\10-toolchains\msedgedriver` |
| 全局环境 | **未改 PATH、未改注册表、未装到系统目录** |

**即：工具在库里，库外无痕。**

## 5. 于是 Q02 的最后一块到位了

第 74 轮查明：**Core 只在界面点「重试」之后启动**，而 Win32 消息点不到 HTML 按钮。
**现在有了 WebDriver，就能真的去点它。**

| Q02 的组成 | 状态 |
| --- | --- |
| 宿主能构建（无空格 `--target-dir`） | ✅ |
| 宿主能启动、WebView2 在跑、窗口标题正确 | ✅ |
| 前端已构建并嵌入 | ✅ |
| 启动序列已由源码查明 | ✅ |
| **驱动界面的工具** | ✅ **本轮到位** |
| **Core 生命周期被观察到** | ⏳ **下一轮就去点** |

## 6. 本轮未做

1. **未**改任何实现文件；**未**触碰官方 Green 与资料库；
2. **未**改全局环境；
3. 全程**只监视自己的进程树、只 kill 自己的句柄**。

## 7. 下一轮

用 `tauri-driver` + `msedgedriver` 启动宿主会话，**点一次「重试」**，
**观察 Core 是否随之启动**（进程树 + 数据文件）—— **那才是 Q02 的交付物。**
