historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**根因链闭合 —— runtime 布局不匹配**

## 1. 解析器要求什么（源码）

```rust
// desktop/src-tauri/src/runtime.rs
14:  pub fn external_dev_enabled(debug_build, value) -> bool { debug_build && value == Some("1") }
22:  fn portable_root_from_marker(exe) { exe_dir/portable.flag 存在 -> Some(exe_dir/data) }
30:  pub fn portable_root_for_executable(exe) { ARCHEAXIS_PORTABLE_ROOT / COGNITIVE_ / marker }
88:  fn resolve_runtime_for_profile(...) -> Result<RuntimeSpec, String> {
95:      if external_dev { ... 需要 .project-local/build/venv/Scripts/python.exe ... }
119:     let python = resource_dir.join("runtime/python/python.exe");    // ★【要求】
120:     if !python.is_file() {
121:         return Err("bundled Python runtime is missing: ...");          // ★【失败】
126:     if let Some(portable_root) = portable_root { ... "portable-stable" }
142:     project_root_for_resource(resource_dir).map(...) ... "installed-stable"
```

**我这次启动的条件**：

| 分支 | 是否命中 | 依据 |
| --- | --- | --- |
| `external_dev` | ❌ 不命中 | `debug_build && ARCHEAXIS_EXTERNAL_DEV=="1"` —— **我没设那个环境变量** |
| `portable_root` | ❌ 不命中 | 需要 `ARCHEAXIS_PORTABLE_ROOT` 或 exe 旁 `portable.flag` —— **都没有** |
| **默认分支** | ✅ **命中** | 于是走到第 119 行，检查 `runtime/python/python.exe` |

## 2. 实测：**要求存在，实际不存在**

```
absent  <worktree>\.project-local\rt\runtime\python\python.exe      <- 代码要求的
EXISTS  <worktree>\.project-local\rt\runtime\python.exe             <- 实际有的

absent  C:\Windows\Temp\aaos-target\debug\runtime\python\python.exe
EXISTS  C:\Windows\Temp\aaos-target\debug\runtime\python.exe
```

**注意 `tauri.conf.json` 的资源映射**：

```json
"resources": { "../.project-local/rt/runtime": "runtime" }
```

**它把 `rt/runtime/` 的**内容**映射到 `runtime/`** —— 所以 `rt/runtime/python.exe` → `runtime/python.exe`（平铺）✓
**而代码要的是 `runtime/python/python.exe`** ✗

## 3. 于是整条链闭合

```
resource_dir/runtime/python/python.exe 不存在
  → resolve_runtime_for_profile 返回 Err("bundled Python runtime is missing: …")
    → main.rs:801  record_failure 且 pending_runtime = None
      → main.rs:812  if let Some(runtime) 不成立
        → 自启线程【从不派生】
          → 没有 Core、data_file_count: 0、界面停在 RecoveryShell
```

**与我实测到的三件事逐项吻合。** 这一次不再是「现象相符」，而是**源码要求 + 实测缺失 + 结构可推**三者一致。

## 4. 一处需要说明的对照

**老 Green 的 `runtime/` 也是平铺的**（`python.exe` 直接在里面）—— 但那是
**Avalonia 宿主 `ArcheAxis.Desktop` 的布局**，**不是 Tauri 宿主 `src-tauri` 期望的形态**。
**两套宿主对资源布局的要求不同**，这正是我此前拿老 Green 的形态去推测 Tauri 形态时会出偏差的地方。

## 5. 修法（具体、在我的边界内）

**把 runtime 按代码要求**再 stage 一层**：

```
现在:  .project-local/rt/runtime/python.exe            + 资源映射 -> runtime/python.exe
应改成: .project-local/rt/runtime/python/python.exe   + 同一映射 -> runtime/python/python.exe  ✓
```

**即：在 `rt/runtime/` 下建一个 `python/` 目录，把 Python 发行版放进去。**
然后重建宿主并再跑一次 —— **这一次才可能在进程树里看到 Core。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「改正布局后 Core 一定能起来」 | 还有别的条件（worker-profile、migration、readiness）—— **未验证** |
| 「前端问题已解决」 | 前端是**独立**问题（debug 走 devUrl） |

**但这是我目前能给出的、证据最强的一条根因。**

## 7. 本轮未做

1. **未**重新 stage、**未**重建、**未**再跑（下一轮）；
2. **未**改任何实现文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. 全程**只读**。
