# 🎯 AAOS-01：**项目自己的架构说明 —— 六条线索一次串起**

## 1. 原文（`scripts/release/stage_backend_runtime.py:1-24`）

```
1:  """Stage a complete backend runtime root with measured bytes and asserted provenance.
3:  The repository already defines how the backend is distributed, and it is not one
4:  Python wheel. `scripts/release/assemble_green_candidate.py` and
5:  `scripts/release/verify_green_candidate.py` fix the runtime layout as sibling
6:  components:
7:
8:      core/archeaxis-api.exe     the canonical writer
9:      runtime/python.exe         the interpreter the workers run under
10:     workers/**                 services/python-workers content
11:     worker-profile.json        archeaxis.worker-profile/v1 (python, script, staging)
12:     data/                      workspace, objects and staging
13:
14: That assembler requires a built desktop, because a *product* candidate needs the
15: Avalonia shell. The backend half does not, and waiting for the shell is what left
16: "the wheel installs" standing in for "the backend runs from what was installed".
17: This script stages only the backend components, using the same layout, the same
18: profile schema and the same environment names the desktop supervisor already reads,
19: so it adds no second architecture.
21: It never downloads anything: the interpreter and every dependency come from
22: locations that are already registered and approved on this host, and each one is
23: recorded by version and content hash in the manifest.
24: """
```

## 2. 🎯 六条线索一次串起

| 我此前的困惑 | 这段文档给的答案 |
| --- | --- |
| Rust Core 的路由为什么在 Python 后端找不到（第 105 · 106 轮） | **`core/archeaxis-api.exe` 是独立编译的「规范写入者」**，与 Python 后端**并列为 sibling 组件** |
| worker profile 声明 `runtime/python.exe`（平铺），而 Tauri 解析器要嵌套（第 128 轮） | **这是**两套产物**的布局**：候选包用平铺，Tauri 安装器用嵌套 |
| `data/` 到底要不要存在（第 100 · 123 · 124 · 125 · 126 · 127 轮） | **它是候选布局的一个组件**（「workspace, objects and staging」），**脚本第 273 行确实 `mkdir` 它** |
| 第 79 轮找不到「能力↔路由」的映射 | **`worker-profile.json` 由分发时生成**（第 128 轮已证） |
| 第 123 轮我的工件缺包 | **正式分发「从不下载任何东西」**，依赖都来自**已登记已批准**的主机位置 |
| 我为什么找不到 Rust Core 的运行实例 | **它要跟 Avalonia shell 一起组装**（第 14-15 行） |

## 3. 🎯 而且最后那句直指**本类问题**

> **"waiting for the shell is what left 'the wheel installs' standing in for
> 'the backend runs from what was installed'"**

**即：把「装上了」当成「装上的东西能跑」—— 这正是我这几十轮在追的那类落差。**

**而 `stage_backend_runtime.py` 存在的理由就是**不等 shell 也能验证后端** ✓
**它的存在本身，说明项目已经把这个问题当成一等公民看待了。**

## 4. 两套产物（现在清楚了）

| 产物 | 布局 | 生产者 |
| --- | --- | --- |
| **绿色候选**（green candidate） | `core/` + `runtime/`（**平铺**）+ `workers/` + `shared/` + `worker-profile.json` + `data/` | `assemble_green_candidate.py`（**需已构建的 Avalonia 桌面**）/ **`stage_backend_runtime.py`（只做后端）** |
| **Tauri 安装器** | `runtime/**python/**`（**嵌套**）+ `ArcheAxis.exe` | `tauri build` |

**这与老 Green 的实物一致**：它既有 `-Setup.exe`，又有三个 `AAOS-v*` 候选目录 ✓

**所以「宿主跑得通」与「候选包跑得通」是**两件事**，验证手段也不同。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「两套布局中哪一套是主」 | **文档说后者「adds no second architecture」，但我未追证其一致性** |
| 「`data/` 在候选布局里的作用已完全清楚」 | **文档只说「workspace, objects and staging」** |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
