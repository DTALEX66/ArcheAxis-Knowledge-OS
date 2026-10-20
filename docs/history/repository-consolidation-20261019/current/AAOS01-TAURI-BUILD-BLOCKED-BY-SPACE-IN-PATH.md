# AAOS-01 Q02：staged runtime 已就位，构建推进到 `tauri-winres`，**卡在路径中的空格**

## 1. 本轮做的

用**正当工具**（`scripts/release/stage_backend_runtime.py`）把宿主需要的运行时暂存到它声明的位置：

```
--core     <已构建的 Rust Core（对 HEAD 最新）>
--runtime  <共用外置工具库的 CPython>
--workers  services/python-workers
--out      <worktree>\.project-local\rt
--version 0.6.14   --source-commit <HEAD>   --source-tree <HEAD^{tree}>

-> STAGE_EXIT=0
-> files: 2799   manifest_sha256: f34f0c7d...
-> <worktree>\.project-local\rt\runtime 存在（DLLs/ Lib/ libs/ Scripts/ tcl/ ...）
```

这与两个 Tauri 清单声明的一致：`"../.project-local/rt/runtime": "runtime"`。

## 2. 结果：**那个资源错误消失了**，构建推进得更深

```
cargo check --manifest-path src-tauri/Cargo.toml
  -> 工作区错误：已消失（第 28 轮修的）
  -> resource path 错误：已消失（本轮暂存运行时）
  -> 构建一路推进到 tauri-winres（编译图标/资源脚本）
```

**这是该构建在本机上走到过的最深位置。**

## 3. 新阻塞：**路径里的空格**（环境问题，不是产品缺陷）

```
cc1.exe: fatal error: projects\ArcheAxis-Knowledge-OS\.project-local\build\aaos01-tauri
                      \debug\build\archeaxis-desktop-567f84f5935f4d6a\out: No such file or directory
windres: preprocessing failed.

tauri-winres-0.3.6 panicked at src\lib.rs:543:
  Failed("windres failed to compile \"resource.rc\"")
```

**注意那行错误里的路径**：`projects\ArcheAxis-Knowledge-OS\...` —— **开头的 `D:\All ` 被吃掉了**。

> 路径 `D:\All projects\...` 里**有空格**，而 `windres`/`cc1` 在该调用里没被正确转义，**在空格处断开了**。

**这是 GNU 工具链 + 含空格路径的限制，不是产品的缺陷。**
CI 上路径形如 `D:\a\...`（无空格），所以**CI 不会有这个问题** —— **这是本机特有的**。

（另见一条提示性输出：`package.metadata does not exist`，来自 tauri-build，非致命。）

## 4. 这对后续意味着什么（**重要，必须写清**）

**在本工作树 + GNU 工具链下，Tauri 宿主无法完成构建。**

所以第 28 轮我定下的原则 —— 「**改接前先让宿主可编译**」—— 在本机遇到了一个**我无法用改代码解决**的障碍：

| 可选路径 | 说明 |
| --- | --- |
| A | 改用 **MSVC** 工具链（若本机有 VS 构建工具） |
| B | 把工作树移动到**无空格路径**下验证 |
| C | **承认本机无法验证宿主构建，把改动交给 CI 验证**（但 CI 也不构建 Tauri，因为它在 workspace 之外） |

**我没有选任何一条** —— 这需要你或环境所有者决定。
**在它解决之前，我不对 `BackendProcess::launch` 做无法验证的改动。**

## 5. 附带：构建又把那 4 个生成文件改脏了

与第 28 轮同一现象（丢失末尾换行）。**已再次还原**，未提交。

## 6. 本轮**未**做

1. **改接仍未做**，且现在**有明确的、环境层面的理由**；
2. **未**尝试 MSVC；**未**移动工作树；
3. 官方 Green 与官方资料库**零触碰**（`--runtime` 用的是**共用外置工具库**的 CPython，不是 Green）。
