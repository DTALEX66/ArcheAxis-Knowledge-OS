# 🎉 AAOS-01 Q14：**打包流水线跑通，产出安装器工件**

## 1. 本轮做了什么

`tauri build`（**带打包**）—— 目标 `nsis`，另附 WiX/MSI。

```
Finished `release` profile [optimized] target(s) in 22.72s
Built application at: ...\release\ArcheAxis.exe
Running candle for "...\release\wix\x64\main.wxs"
   Info Patching ...ArcheAxis.exe with bundle type information: nsis
Running makensis to produce ...\bundle\nsis\ArcheAxis Knowledge_0.6.14_x64-setup.exe
Finished 2 bundles at:
    ...\bundle\nsis\ArcheAxis Knowledge_0.6.14_x64-setup.exe
```

## 2. 产出的工件

```
--- artifacts ---
ArcheAxis Knowledge_0.6.14_x64_en-US.msi  24.06 MiB  sha256=55a1123265591d32
ArcheAxis Knowledge_0.6.14_x64-setup.exe  16.38 MiB  sha256=0dcfec8f39e5e23c
--- bundled app exe ---
ArcheAxis.exe  21.25 MiB  sha256=f4e2593676ac283b
```

## 3. 为什么这对 Q14 重要

| Q14 需要 | 本轮状态 |
| --- | --- |
| 一个**可安装的产物** | ✅ **NSIS setup** 与 **MSI** 都已产出 |
| 与**当前树**对应 | ✅ 版本 **0.6.14**，来自当前工作树 |
| 打包**可复现** | ✅ 一条 `tauri build` 即可（NSIS 取自外置工具库） |
| **执行安装** | ❌ **未做** —— 那需要涉及本机安装，**等你决定 3** |

**此前 Q14 的参考物是老 Green 的三个候选**（晚于仓库里 tracked 的 v0.5.0 安装器）；
**现在，当前树自己也能产出 0.6.14 的安装器了。**

## 4. 顺带解决的两个障碍

| 障碍 | 处置 |
| --- | --- |
| **`os error 32`（文件被占用）** | 我此前四轮遗留了 4 个 `uvicorn` worker → **按内容判据识别并逐个 kill** |
| **构建churn** | `tauri build` 会重写 `src-tauri/gen/schemas/*` → **`git checkout -- src-tauri/gen` 还原**，保持 TREE-CLEAN |

**第二条值得记成惯例**：每次带打包的构建之后，都要还原这两个生成物目录。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「安装能成功」 | **未安装** —— 只产出工件 |
| 「安装后后端能就绪」 | **未验证** —— Q14 的旅程规格有 26 条断言待执行 |
| 「产物已签名/可用于发布」 | **未涉及**，且**发布不是本任务范围** |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 产出安装器工件 | `C:\Windows\Temp\aaos-target\release\bundle\`（**临时构建目录**） | **工件，未安装** |
| 还原生成的 schema 文件 | 仓库内 `src-tauri/gen`（`git checkout`） | **保持 TREE-CLEAN** |

**未改任何仓库源文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
