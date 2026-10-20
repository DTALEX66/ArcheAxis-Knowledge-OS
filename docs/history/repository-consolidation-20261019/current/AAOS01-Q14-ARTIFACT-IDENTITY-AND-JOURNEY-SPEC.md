# AAOS-01 Q14：**产物身份已钉 + 旅程回执规格已提取（仍未安装）**

第 64 轮查明产物与旅程都在。本轮**在不安装的前提下**做两件扎实的事：**钉住产物身份**、
**把旅程回执的规格从验证器里提出来**。

## 1. 产物身份（只读计算，未执行任何安装）

| 文件 | 字节 | SHA-256（前 32 位） | 版本信息 |
| --- | --- | --- | --- |
| `ArcheAxis_0.5.0_x64-setup.exe` | **1,852,859** | `fadabd22b41ea7fad5f5a02d231c1399…` | **product=`ArcheAxis` · fileversion=`0.5.0`** |
| `ArcheAxis_0.5.0_x64_en-US.msi` | **2,785,280** | `bf42a9eae974639a2b1b0076ffd03e43…` | （MSI 不携带 Win32 VersionInfo） |

**两个文件都被 git 跟踪**，所以它们的身份是**可复现**的。

## 2. 旅程回执的规格 —— **从验证器自己的 26 条断言里提取**

`desktop/scripts/verify_nsis_install.ps1` 每条失败都有一句具名 `throw`。**把这些句子按顺序读下来，就是旅程。**

| 阶段 | 断言（原文摘录） |
| --- | --- |
| 前置守卫 | **`refusing to overwrite an existing ArcheAxis Knowledge installation`** |
| 前置守卫 | `NSIS installer is missing` · `release and candidate identity requirements are mutually exclusive` |
| 安装 | `NSIS installer exited with N` |
| 落盘检查 | `installed desktop executable is missing` · **`installed bundled Python is missing`** · `installed Runtime contains an invalid double runtime directory` |
| 隔离检查 | **`desktop used an unexpected Python`** · **`desktop Python isolation arguments are invalid`** |
| 启动 | `desktop shell exited before readiness` · **`installed desktop backend did not become ready`** |
| 界面 | **`desktop shell main window was not ready`** |
| 身份 | `installed Workspace returned an invalid product response` · **`installed runtime did not expose the verified public release identity`** |
| 关闭 | `desktop shell rejected WM_CLOSE` · `desktop shell did not exit after WM_CLOSE` |
| 卸载 | `NSIS uninstaller exited with N` |

## 3. 这份规格里最值得注意的两点

### (a) **验证器自己就拒绝覆盖已有安装**

```
throw 'refusing to overwrite an existing ArcheAxis Knowledge installation'
```

**这正是我第 64 轮提出的最大顾虑，而工具本身已经防住了。** 我上一轮的谨慎是对的，
但**风险比我以为的小**。

### (b) 它检查的是**隔离**，不只是「能启动」

`desktop used an unexpected Python` 与 `desktop Python isolation arguments are invalid` 这两条，
**是在验证桌面确实用了随包的 Python、且隔离参数正确** —— 对应本项目「Rust Core 唯一写者 + 隔离 Python worker」的核心主张。
**这正是「实际桌面通过」该有的分量。**

## 4. 仍然存在的风险（我没有缩小它）

**`%LOCALAPPDATA%\com.archeaxis.workspace` 已存在且已有内容。**
验证器**没有**任何一条断言与它相关 —— **所以它不保护产品数据目录。**

**结论**：安装**不会覆盖已有安装**（工具防住），但**可能写入已有产品数据**（无人防）。
**这一条仍然需要你点头。**

## 5. 本轮未做

1. **未**运行安装包；**未**写注册表；**未**动 `%LOCALAPPDATA%`；
2. **未**触碰官方 Green 与资料库；
3. **未**改任何实现文件。

## 6. 更新的选项表（比第 64 轮更精确）

| 选项 | 含义 | 现在已知的风险 |
| --- | --- | --- |
| **A** | 用跟踪的 **v0.5.0** 候选包跑一次（结束卸载还原） | 不覆盖已有安装；**可能写入已有产品数据** |
| **B** | 先解路径空格（MSVC / 迁移工作树），构建**当前版本**候选包再验 | 无（尚无产物） |
| **C** | Q14 暂缓，交别处真实 Windows 验证 | 无 |
