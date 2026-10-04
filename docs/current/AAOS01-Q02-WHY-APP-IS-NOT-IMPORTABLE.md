# 🎯 AAOS-01 Q02：**完整机制 —— `app` 为什么不可导入**

## 1. 源码事实（`desktop/src-tauri/src/backend.rs`）

```rust
21:  const SANITIZED_ENVIRONMENT: [&str; 28] = [
22:      "PYTHONPATH",              // ★ 第一个就被清除
23:      "PYTHONHOME",
24:      "VIRTUAL_ENV",
25:      // canonical ARCHEAXIS_* and legacy COGNITIVE_* are both stripped
281: fn runtime_command(runtime: &RuntimeSpec) -> Command {
282:     let mut command = Command::new(&runtime.python);
288:     command.creation_flags(0x08000000);   // CREATE_NO_WINDOW
290:     command.arg("-B");
291:     if runtime.isolated {
292:         command.arg("-I");              // ★ 隔离模式
293:     }
294:     command.current_dir(&runtime.cwd);    // ★ cwd = 数据目录
295:     for name in SANITIZED_ENVIRONMENT {
296:         command.env_remove(name);         // ★ PYTHONPATH 被移除
297:     }
298:     command
299:         .env("ARCHEAXIS_DATA_DIR", &runtime.data_dir)
309:         .env("PYTHONDONTWRITEBYTECODE", "1")
310:         .env("PYTHONNOUSERSITE", "1")
319: }
```

## 2. 四个事实凑成同一个结论

| # | 事实 | 来源 |
| --- | --- | --- |
| 1 | **`PYTHONPATH` 被显式移除** | `SANITIZED_ENVIRONMENT` 第 22 行 + 第 295-297 行 |
| 2 | **`-I` 隔离模式**（`runtime.isolated` 为真时） | 第 291-293 行 |
| 3 | **`current_dir` = `runtime.cwd`** —— 我这条分支上是**数据目录**，不是仓库根 | 第 294 行 + `runtime.rs:142-152` |
| 4 | **`app/` 在仓库根**，**构建输出里没有它** | `app\runtime_entrypoint.py` 存在；release 输出只有 `runtime/`、`ArcheAxis.exe` |

**合起来**：

```
python -B -I -m app.runtime_entrypoint core
   cwd = 数据目录（无 app/）
   PYTHONPATH 被移除；-I 隔离；no-user-site
      → app 不在任何可导入路径上
         → ModuleNotFoundError: No module named 'app'
```

**与第 94 轮应用自己给出的错误原文完全一致。**

## 3. 这说明启动命令**依赖** `cwd` 下有 `app/`

`-m` 会把 **cwd** 放进 `sys.path` —— 所以**设计意图**是：**`runtime.cwd` 里应当有 `app/`**。

| 分支 | `runtime.cwd` | 里面有 `app/` 吗 |
| --- | --- | --- |
| `portable-stable` | `portable_root` | 取决于 stage |
| **`installed-stable`（我命中）** | `project_root/.project-local/task-runtime/desktop-installed` **或** `local_data_dir` | ❌ **没有** |

**而 `app/` 实际在仓库根** —— 既不在数据目录、也不在构建输出里。

## 4. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「这是产品缺陷」 | 也可能**只在我的 fallback 分支**上成立 —— 真实安装布局下 `cwd` 可能与 `app/` 同处一地 |
| 「修法是 X」 | 有两条路（把 `app/` 送到 `cwd`，或让 `cwd` 指向有 `app/` 的地方），**需要判断哪条是设计意图** |

**我能确证的是机制**：这四项事实**必然**导致该错误。**不能确证的是「在产品本来的安装形态下是否也如此」。**

## 5. 这解释了 Q14 验证器的那句断言

`verify_nsis_install.ps1` 里有一条 **`installed desktop backend did not become ready`** ——
**即安装态下后端**应当**就绪**。那说明安装布局里 `app/` 是到位的；**我这条 fallback 分支不是那个布局**。

## 6. 本轮未做

1. **未**去改布局或配置（需先判断设计意图）；
2. **未**改任何仓库文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. **未**删除任何东西。
