# AAOS-01 Q02：**修掉一个真实阻塞** —— Tauri 宿主此前**根本无法被编译**

本轮本来要做「改接」（把宿主启动目标换成 Rust Core）。**动手前先验证「能不能编译」** —— 结果发现**根本不能**。

## 1. 阻塞是什么

```
cargo check --manifest-path src-tauri/Cargo.toml
error: current package believes it's in a workspace when it's not:
  current:   <worktree>\src-tauri\Cargo.toml
  workspace: D:\All projects\ArcheAxis-Knowledge-OS\Cargo.toml
```

而工作区清单**本来就是故意排除它的**：

```toml
[workspace]
resolver = "3"
# Legacy Tauri keeps its own lockfile and build boundary.
exclude = ["src-tauri", "desktop/src-tauri"]
```

**矛盾点**：工作区说「它自己有自己的构建边界」，但**两个 Tauri 清单都没有声明 `[workspace]`** ——
于是 cargo 认为它「在 workspace 里又不是成员」，**直接拒绝**。

**后果**：`src-tauri` 与 `desktop/src-tauri` **既不在工作区、也无法独立编译** —— **任何对宿主的改动都无法验证**。
这解释了为什么第 19–27 轮我始终没有真正改接：**改了也验不了**。

## 2. 修法（**与工作区自己的声明意图一致**）

给两个清单各加一个空的 `[workspace]` 根 —— 正是 cargo 错误信息给出的第一条建议，也**正是那句注释的含义**：

```toml
# The root workspace excludes this crate on purpose, so the crate has to declare its own workspace
# root. Without this cargo refuses the manifest as being in a workspace when it is not, which is why
# the Tauri host could not be checked or built at all.
[workspace]
```

**注意：我没有把它们并进主工作区** —— 那会把 Tauri 2 的依赖拉进工作区构建，可能影响 CI。
本修改让它们**各自成为独立工作区根**，因此**主工作区构建完全不受影响**。

## 3. 修好的证据

```
cargo check --manifest-path src-tauri/Cargo.toml
  -> 工作区错误消失
  -> 构建一路推进到 tauri-build（生成权限文件、cfg(dev)、TARGET_TRIPLE 等）
```

**阻塞确实被移除了** —— 构建从「立刻拒绝」变成「进入 Tauri 自己的构建脚本」。

## 4. 但暴露出**下一个**阻塞（更具体）

```
resource path `..\.project-local\rt\runtime` doesn't exist
warning: build failed, waiting for other jobs to finish...
```

`tauri.conf.json` 声明了一个资源路径 `.project-local/rt/runtime`，**而它不存在**。
**所以宿主构建需要一份「已暂存的运行时」**（与我在上一任务包里见过的 staged runtime 是同一个概念）。

## 5. 本轮**未**做

1. **改接仍未做** —— 但原因变了：不是「没时间」，而是**宿主构建还缺一份 staged runtime**；
2. **未**创建 `.project-local/rt/runtime`（需要弄清用哪个 staging 工具、以及它的输入）；
3. **未**构建成功任何 Tauri 产物；
4. 官方 Green 与官方资料库**零触碰**。

## 6. 下一轮

1. 找到生成 `.project-local/rt/runtime` 的**正当工具**（可能是 `scripts/release/stage_backend_runtime.py` 的 dev 路径，或 `scripts/runtime/dev.py`）；
2. 让它就位 → **让 `cargo check src-tauri` 真正通过**；
3. **只有那时**才动 `BackendProcess::launch` 的启动目标 —— 否则改动无法验证。
