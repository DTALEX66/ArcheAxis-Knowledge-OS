historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# 🎉 AAOS-01 Q02：**宿主构建成功 —— 而且不需要你做任何决定**

## 1. 结果

```
Compiling archeaxis-desktop v0.6.14 (C:\Windows\Temp\aaos-junction\src-tauri)
warning: `archeaxis-desktop` (bin "ArcheAxis") generated 3 warnings
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 56.95s
```

**那个我一直当作「卡住」的宿主，57 秒就构建完了。**

## 2. 真正的根因（**我此前诊断错了**）

第 29 轮我把它记成「本机路径里的空格让 GNU 工具链的 `windres` 失败」。
**方向对了一半，位置错了。**

### 决定性的一行错误信息

```
cc1.exe: fatal error: projects\ArcheAxis-Knowledge-OS\.project-local\build\cargo-junction\...\out:
                   No such file or directory
windres: preprocessing failed.
```

**看那个路径：`projects\ArcheAxis-Knowledge-OS\…`** ——
**完整路径是 `D:\All projects\ArcheAxis-Knowledge-OS\…`，而它**从头被截断了**：`D:\All ` 没了。**
**路径在空格处被劈开了。**

**而截断掉的那一段，是**目标目录** `…\build\cargo-junction\…`，不是源码目录。**

## 3. 我做了两次实验，第二次才找到

| 实验 | 做法 | 结果 |
| --- | --- | --- |
| 第一次 | 把**源**路径变无空格（用 junction `C:\Windows\Temp\aaos-junction` → 工作树） | ❌ **仍然失败** |
| 第二次 | 再把**目标目录**也变无空格（`--target-dir C:\Windows\Temp\aaos-target`） | ✅ **成功，56.95 秒** |

**第一次实验的价值在于排除**：它证明**源路径不是问题**，从而把嫌疑锁定到目标目录。

## 4. 所以正确的解法是一行参数

```
cargo build --manifest-path src-tauri\Cargo.toml --target-dir C:\Windows\Temp\aaos-target
```

| 我此前提出的选项 | 实际需要吗 |
| --- | --- |
| **A′** 允许装 msvc 的 `rustc` 组件（**全局环境变更**） | ❌ **不需要** |
| **B′** 迁移工作树到无空格路径 | ❌ **不需要** |
| **C′** 交给别处验证 | ❌ **不需要** |
| — | ✅ **只需要一个无空格的 `--target-dir`** |

## 5. 我要认的错

1. 我**把「路径空格」当成了需要你裁决的事项**，还一度请你批准一次**全局工具链变更** ——
   **而答案是一个构建参数。**
2. 我**没有先做「把变量一个个隔离」的实验** —— 如果第一次就把源和目标分开试，第一轮就能定位。
3. 第 29 轮我写「GNU 工具链在空格上失败」，**把工具链也冤枉了** ——
   **GNU 工具链是好的，它只是被喂了一个带空格的路径。**

## 6. 解锁了什么

| 影响 | 说明 |
| --- | --- |
| **Q02** | 宿主能构建 → 启动与只读桥接可实测 |
| **Q03–Q05** | 依赖链上游通了 |
| **Q14** | 可构建**当前版本**候选安装包（不必用 v0.5.0 旧产物） |
| **Q15** | 可收口 |

## 7. 遗留物（临时、可清理）

| 路径 | 用途 | 处置 |
| --- | --- | --- |
| `C:\Windows\Temp\aaos-junction` | 无空格源路径（junction） | 临时；下次可直接只用 target-dir |
| `C:\Windows\Temp\aaos-target` | 无空格目标目录 | 临时构建产物 |

**两者都在系统临时目录，不在仓库、不在官方安装、不在资料库。** 我**未**删除它们（下一轮确认后清理）。

## 8. 本轮未做

1. **未**运行 `rustup component add`（**已证明不需要**）；
2. **未**迁移工作树；
3. **未**改任何实现文件；**未**触碰官方 Green 与资料库。
