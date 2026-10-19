# 🎯 AAOS-01：**权威分发脚本的两条硬规矩**

## 1. 它拒绝 reparse point（junction / symlink）

```python
244:     shared_donor = args.shared or args.workers.parent.parent / "shared" / "learning_scheduler.py"
245:     for candidate in (args.core, args.runtime, args.workers, shared_donor, args.out,
246:                       args.dep_source, args.archive):
247:         if candidate is not None:
248:             reject_reparse(candidate)
249:     # Preflight all recursive donors before producing even a partial output root.
```

**`reject_reparse` 的实现**：
```python
108: def reject_reparse(path: Path) -> None:
109:     """A staged runtime must not follow a link out of its own tree."""
110:     raw = str(path).replace("\\", "/").lower()
111:     if raw.startswith(("e:", "//")) or ".." in raw.split("/"):
112:         raise ValueError("unsafe staging path")
113:     path = Path(os.path.abspath(path))
114:     full = str(path).replace("\\", "/").lower()
115:     if full.startswith(("e:", "//")) or any(part in PRIVATE_NAMES or part.startswith(".env") for part in full.split("/")) or "/.project-local/agents/" in full:
116:         raise ValueError("protected staging path")
117:     for part in (*reversed(path.parents), path):
118:         try:
119:             info = part.lstat()
120:         except (FileNotFoundError, NotADirectoryError):
121:             continue
122:         if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
123:             raise ValueError("linked staging path rejected")
```
**即：junction 与 symlink 被**明确拒绝**。**

**而我的 staging 恰恰是 6 个 junction。**

| 我的做法 | 权威工具的态度 |
| --- | --- |
| 用 junction 把仓库包挂进 `site-packages` | ❌ **`reject_reparse` 会拒绝** |
| 预期做法 | ✅ **`copy_distribution(name, dep_source, site_packages)` —— 复制真实目录** |

**所以第 123 轮我那句「junction 不会被 `tauri build` 打进安装器」是对的，
而且更进一步：**权威脚本连 junction 这个输入都不接受**。**

## 2. 它按分布名逐个复制依赖

```python
222:     parser.add_argument("--dep-source", type=Path,
223:                         help="site-packages the approved dependencies are copied from")
224:     parser.add_argument("--dep", action="append", default=[],
225:                         help="distribution name to stage into the runtime (repeatable)")
283:     site_packages = root / "runtime" / "Lib" / "site-packages"
289:             dependencies.append(copy_distribution(name, args.dep_source, site_packages))
```

**「已批准的依赖」是**显式列举**的** —— 不是我那样一个个 `pip install` ✓

## 3. ⚠️ 一条值得记下的**路径不一致**

```python
291:     profile = {
292:         "schema": PROFILE_SCHEMA,
293:         "python": "runtime/python.exe",        // ← 平铺
294:         "script": TEXT_WORKER_RELATIVE,
295:         "staging": "data/worker-staging",
296:     }
```

**而这个 profile 里声明的是 `runtime/python.exe`（平铺）** ——
**与 Tauri 解析器要求的 `runtime/python/python.exe`（嵌套，`runtime.rs:119`）不一致。**

| 消费者 | 路径 |
| --- | --- |
| **Tauri 宿主解析器** | `<resources>/runtime/**python/python.exe**` |
| **这个 worker profile** | `<root>/runtime/**python.exe**` |

**我不判定这是缺陷** —— **它们可能服务不同的产物**
（宿主进程 vs 候选包的 worker 启动器）✓。
**但我把它记下来，因为我自己在第 84 轮为这个嵌套结构折腾过。**

## 4. 它还生成我第 79 轮找过的那样东西

```python
297:     declared_routes = present_routes(root)
298:     if declared_routes:
299:         profile["routes"] = declared_routes
300:     profile_path = root / "worker-profile.json"
```

**分发时会把「已存在的路由」写进 `worker-profile.json`** ✓ ——
**这正是第 79 轮我说「能力与实现之间缺少一张表」时，实现侧的那张表。**

**它由分发脚本生成，不是我该手工臆造的** ✓ —— 这也解释了为何我当时找不到它。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「两处路径不一致是缺陷」 | **可能服务不同产物** —— 我未追证 |
| 「`present_routes` 就是能力↔路由的正式映射」 | **它是路由清单**，**是否与 atlas 对齐我没查** |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读文件）。
**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
