historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02：**MSVC 路线只差一样东西 —— 而它需要你点头**

## 0. 先更正我上一轮的话

上一轮我写「**需要的都在**」。**那句话说早了** —— 我检查的是**工具链目录存在**，
**没有检查它是否完整**。实际构建才暴露出真相。

## 1. 真相：msvc 工具链**只有 cargo，没有 rustc**

| 工具链 bin 目录 | 内容 |
| --- | --- |
| `stable-x86_64-pc-windows-**msvc**\bin` | `cargo.exe` · `cargo-clippy.exe` · `clippy-driver.exe` —— **没有 `rustc.exe`** ⚠️ |
| `stable-x86_64-pc-windows-**gnu**\bin` | `cargo.exe` · **`rustc.exe`** · `rustdoc.exe` · `rustfmt.exe` · 若干 DLL ✅ |

**所以构建报的是**：

```
error: could not execute process `rustc -vV` (never executed)
Caused by: program not found
```

**一字不差地对应**：cargo 找到了、跑了，但它要调 `rustc`，而**这个工具链里没有**。

## 2. 因此 Q02 的真实状况（比我之前说的精确得多）

| 条件 | 状态 |
| --- | --- |
| 项目自带 MSVC 工具集（`cl.exe` 14.44.35207） | ✅ **在** |
| `vcvars64.bat` | ✅ **在**，且实测 `cl.exe` 进了 PATH |
| 仓库文档给出的官方验证命令 | ✅ **就是 MSVC 路线**（`crates/README.md:28-30`） |
| **msvc 的 `rustc`** | ❌ **缺** |
| gnu 的 `rustc` | ✅ 在（但它就是会在空格路径上崩的那个） |

## 3. 所以现在只差**一件事**，而它**越界**

补上它要用 `rustup` 安装 msvc 的 `rustc` 组件 —— 那会**写入 `~/.rustup`（全局开发环境）**。

**我的边界里有「不做全局环境变更」这一条**，所以**我停在这里，不自行安装**。

## 4. 给你的决定，现在具体到一行

| 选项 | 你需要的动作 | 之后我能做什么 |
| --- | --- | --- |
| **A′** | 允许我执行 **`rustup component add rustc --toolchain stable-x86_64-pc-windows-msvc`**（或你指定等价命令） | 用 MSVC 构建宿主 → **Q02 可实测** → 链上 Q03–Q05 打开 → Q14 可产**当前版本**候选包 |
| **B′** | 把**工作树迁到无空格路径**（如 `D:\AAOS\`），其余不动 | 用**现有的 gnu 工具链**即可构建 —— **不改任何全局状态** |
| **C′** | 交给别处有完整 MSVC Rust 环境的机器验证 | 我不再尝试本机构建 |

**我倾向 B′**：它**不需要改全局工具链**，而且能顺手消掉这个空格问题对**所有**工具（含 `windres`）的影响。
**但迁移工作树会改变路径，影响面更大 —— 所以这个我不替你做主。**

## 5. 本轮未做

1. **未**运行 `rustup component add`（**越界，等你**）；
2. **未**改任何实现文件；**未**触碰官方 Green 与资料库。
