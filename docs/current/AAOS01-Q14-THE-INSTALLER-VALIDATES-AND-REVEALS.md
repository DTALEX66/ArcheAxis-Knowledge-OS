# AAOS-01 Q14：**安装脚本验证了此前修复，并暴露一处缺口**

## 1. 我读了**安装器自己生成的脚本**（未安装任何东西）

```
C:\Windows\Temp\aaos-target\release\nsis\x64\installer.nsi   (894 KB)
C:\Windows\Temp\aaos-target\release\wix\x64\main.wxs        (1188 KB)
```

## 2. ✅ 三条验证（对 Q14 与我此前的结论都有意义）

### (a) 安装根

```nsis
504:  StrCpy $INSTDIR "$LOCALAPPDATA\${PRODUCTNAME}"
```

**即 `%LOCALAPPDATA%\ArcheAxis Knowledge`** —— **与 `desktop/scripts/verify_nsis_install.ps1` 文档里的安装根一致** ✓

### (b) 🎯 Python runtime 放在**嵌套**目录 —— 验证我第 84 轮的发现

```nsis
641:  CreateDirectory "$INSTDIR\runtime\python\tcl\tcl8.6\tzdata\America\Kentucky"
643:  CreateDirectory "$INSTDIR\runtime\python\Lib\curses"
648:  CreateDirectory "$INSTDIR\runtime\python\Lib\site-packages\pip-26.1.2.dist-info\..."
```

**安装器把 Python 放在 `runtime\python\`** —— **正是 `runtime.rs:119` 要求的 `runtime/python/python.exe`** ✓✓

> **所以我第 84 轮那个修复（把 runtime 放进 `python/` 子目录）**符合产品设计**，不是我的权宜之计。**
**这一条从「我推测的」变成了「安装器自己摆的」。**

### (c) 安装器**带 `site-packages`**

```nsis
648:  ...\runtime\python\Lib\site-packages\pip-26.1.2.dist-info\...
```

**与第 96/97 轮我的结论一致**：「已安装布局」包含 Python 包目录 ✓

## 3. ✅ 并且暴露一处**真实的缺口**

**安装器既不创建 app data 目录，也不创建 `data/` 子目录：**

```nsis
48:   !define BUNDLEID "com.archeaxis.workspace"
6736: RmDir /r "$APPDATA\${BUNDLEID}"        // 仅【卸载】时、且勾选时才清
6737: RmDir /r "$LOCALAPPDATA\${BUNDLEID}"
```

**全文里没有创建 `$LOCALAPPDATA\com.archeaxis.workspace` 或其中 `data\` 的语句。**

**而启动器写的是 `ARCHEAXIS_DB_PATH=data/archeaxis.sqlite`（相对路径）** ——
**它相对 `cwd`（数据目录）解析 → 那个目录下需要有 `data/`。**

**第 100 轮我实测：`%LOCALAPPDATA%\com.archeaxis.workspace\data` 不存在。**

> **两边对上：安装器不建它，启动器却期望它。这是一条从安装态到启动态的真实缺口。**

**我仍不判定谁该负责** —— 可能是启动器该自己建、也可能是安装器该建 ✓

## 4. ⚠️ 一条我必须划清界限的观察

我在 NSIS 文件表里**没有**找到 `site-packages\app` / `archeaxis` / `shared`：

```
=== does it ship the python packages into site-packages? ===
(无输出)
```

**如果照此安装，应用很可能仍会遇到 `No module named 'app'`** ⚠️ —— **但我不据此下结论**，因为：

| 原因 | 说明 |
| --- | --- |
| **这个工件的包内容来自**我的 staging**** | 我 stage 的是**裸 Python 发行版** + 我在构建产物里补的包（第 97 轮用 junction） |
| **junction 不会被 `tauri build` 打进安装器** | 所以文件表里看不到它们，**这是预期的** |
| **正式发布流程可能另有准备步骤** | 我没有证据说明正式流程如何处理这一步 |

> **所以准确的说法是**：「**我这个工件**（基于我的 staging）**不会带上仓库包**」——
> **而不是「产品发布也会缺包」。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「安装后会失败」 | **未安装** —— 上一条只是我这个工件的内容观察 |
| 「安装器有缺陷」 | 它不建 app data 是**常见做法**（应用首次运行时自建） |
| 「正式发布缺包」 | **无证据** —— 工件反映的是我的 staging |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（读生成的安装脚本）。
**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
