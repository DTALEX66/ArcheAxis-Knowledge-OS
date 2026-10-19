# AAOS-01：CI 的候选缺少根层文件，Core 因此起不来（2026-10-05）

## 1. 观察

用真窗口产物 `ArcheAxis.exe`（资源表已含 `core`/`runtime`/`workers`/`shared`）运行：

```
CORE_EVER_SEEN=True pid=24192     ← Core 确实被启动（250ms 轮询可见）
core exe present = True
release/runtime/python.exe = False        ← 嵌套布局
worker-profile.json 在 release/ 里找不到   ← ★ 缺失
```

**Core 起得来，但立即退出。**

## 2. 对比两个候选形态

| | 权威候选（`stage_backend_runtime.py` 产出） | CI 的 `rt/`（`prepare_bundle` → `stage_runtime`） |
| --- | --- | --- |
| `runtime/python.exe` | **平铺 ✓** | 形态不同 |
| `worker-profile.json`（根层） | **有 ✓** | **无 ✗** |
| `start-backend.py` / `.cmd` | **有 ✓** | **无 ✗** |
| `backend-runtime-manifest.json` | **有 ✓** | **无 ✗** |

## 3. 根因：两个暂存器的产出形态不同

```
scripts/release/stage_backend_runtime.py      → 写全部四个根层文件
desktop/scripts/stage_runtime.py（经 prepare_bundle）→ 一个都不写
```

**Core 的调度器解释器来自 `worker-profile.json`**
（`scripts/release/backend_launcher.py:7`：「the scheduler interpreter comes from
`worker-profile.json`, which is what the Core reads」）。

**⇒ 即使在 CI 里，打包出的应用也缺这个文件 ⇒ Core 无法解析 worker ⇒ 起不来。**

## 4. 影响面与结论

- **资源表改动本身是对的**（`core`/`runtime`/`workers`/`shared` 确实被复制进产物 ✓）。
- **但产物形态不完整**：**缺根层文件**。
- **§六 合并的真实靶子是**至少三个**产出形态不一致的暂存实现**，不是两个：
  1. `scripts/release/stage_backend_runtime.py`（权威，平铺 + 根层文件）
  2. `scripts/release/assemble_green_candidate.py`（组装器）
  3. `desktop/scripts/stage_runtime.py`（CI 路径，缺根层文件）

## 5. 修法（下一步，顺序同前）

1. **先让 CI 的候选产出根层文件**（在 `prepare_bundle`/`--core-only` 之外补一步，或让
   `prepare_bundle` 调用权威暂存器的对应逻辑）；
2. **再加进资源表**：`worker-profile.json`、`start-backend.py`、`start-backend.cmd`、
   `backend-runtime-manifest.json`；
3. **本地换成权威形态的 `rt`**（用 `aaos-cand1` 或重跑权威暂存器）**再打包、再跑同一观察**，
   确认 Core **存活超过数秒**；
4. **然后**才做窗口视觉验收。

## 6. 我本轮不声称

- **未改任何代码**；**未改动资源表**；
- **未断言窗口渲染/交互有问题** —— 只观察到进程生命周期；
- **未把本地 `rt` 陈旧与 CI 缺文件混为一谈** —— 两者独立，都在上面写明。
