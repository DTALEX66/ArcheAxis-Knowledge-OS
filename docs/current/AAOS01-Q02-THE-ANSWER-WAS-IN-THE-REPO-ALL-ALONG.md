# AAOS-01 Q02：**路径空格的解法就在仓库自己的文档里 —— MSVC 工具链齐备**

## 1. 我一直在问的那个「三选一」，其实**不需要你选**

第 29 轮查明：本机 GNU 工具链在 `D:\All projects\` 的**空格**上失败（`windres: preprocessing failed`），
而 CI 路径无空格所以能过。我当时把它记成「需要你裁决：MSVC / 迁移工作树 / 别处验证」。

**本轮读了仓库文档，发现答案早就写在 `crates/README.md:28-30`：**

```powershell
cmd /c "call \"D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat\"
       && cd /d D:/All projects/ArcheAxis-Knowledge-OS && cargo test"
```

**注意 `cd /d D:/All projects/...` —— 带着那个空格。**
**也就是说：本仓库的官方验证路径本来就是 MSVC，而 MSVC 能处理这个空格。**
**我一直用的 mingw 是我自己的偏离，不是默认。**

## 2. 只读核查：需要的都在

| 需要的东西 | 实测 |
| --- | --- |
| `vcvars64.bat` | ✅ `OS External Configuration\10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat` |
| `cl.exe` | ✅ `…\VC\Tools\MSVC\**14.44.35207**\bin\Hostx64\x64\cl.exe` |
| **msvc Rust 工具链** | ✅ `stable-x86_64-pc-windows-msvc`（与 gnu 并存） |
| `rust-toolchain.toml` | `channel = "stable"`（按宿主默认解析） |

**所以四个条件全部满足 —— MSVC 路线不只是「可选」，它就在磁盘上。**

## 3. 本轮已启动的动作

用**仓库自己文档里的方式**构建那个卡住的宿主：

```
call <msvc>\vcvars64.bat
cd /d <worktree>            # 带空格的路径
cargo +stable-x86_64-pc-windows-msvc build --manifest-path src-tauri\Cargo.toml
```

**第一次尝试失败，原因两层，都已查清：**

1. **`cmd /c` 的引号转义把输出吞了** —— 我只看到 `BUILD_EXIT=1`，没有诊断信息。
   改成**写一个 `.bat` 文件**再跑（不在 PowerShell 里嵌套转义）；
2. **改成 bat 后拿到真错误**：

```
--- cl.exe on PATH: D:\...\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe   <- MSVC 正常
--- building src-tauri with the msvc toolchain
CARGO_EXIT=9009
'cargo' is not recognized as an internal or external command
```

**即：MSVC 那一半是好的（`cl.exe` 确实在 PATH 上），只是 `cargo` 不在那个 bat 的 PATH 上。**

**cargo 的位置也查到了**：

```
C:\Users\ALEX\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe   <- 存在
C:\Users\ALEX\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin\cargo.exe    <- 我此前一直用这个
```

**所以修法是：在 bat 里把 msvc 工具链的 bin 加进 PATH，再构建。** 已在后台重跑。

## 4. 如果构建成功，意味着什么

| 影响 | 说明 |
| --- | --- |
| **Q02 解锁** | 宿主能构建 → 启动与只读桥接可实测 |
| **Q03–Q05 解锁** | 依赖链上游通了 |
| **Q14 的「当前版本候选包」可行** | 不必再用 v0.5.0 旧产物 |
| **Q15 可收口** | 依赖 Q14 |

> **也就是说：这一个发现可能一口气解开整条剩下的链。** 我此前把「路径空格」列为需要你裁决的事项，
> **现在看，那是我没先读仓库自己的验证说明。这个责任在我。**

## 5. 本轮未做

1. **未**改任何实现文件；
2. **未**触碰官方 Green 与资料库；
3. **未**装任何东西（MSVC 工具链**本就在项目外部配置目录里**）。
