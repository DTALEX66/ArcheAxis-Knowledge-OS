# AAOS-01：**老 Green 里有什么能用 —— 逐项清点**

你让我看看老 Green 有没有能用的。**有，而且不少。** 以下全部**只读**取得，未改它一个字节。

## 1. 已验证的发布身份（**这正是 Q14 验证器要断言的东西**）

```json
// D:\All projects\ArcheAxis.Knowledge.Green-x64\release-identity.json
{ "schema_version": "3.0.0",
  "release": {"tag": "v0.6.14", "version": "0.6.14", "channel": "stable", "public": true,
              "url": ".../releases/tag/v0.6.14"},
  "source": {"commit": "c202c5b5a4789f0dc21accaa7ccbfed4676f0573",
             "tree": "8150692f81883f647806bdb234cedf7d20b31aa1",
             "verification_ci_run_id": 33261549586, "release_run_id": 33262172637},
  "artifacts": [{"name": "ArcheAxis.Knowledge-v0.6.14-Windows-x64-Setup.exe", "kind": "installer"},
                {"name": "ArcheAxis.Knowledge-v0.6.14-Windows-x64-Green.zip", ...}] }
```

**Q14 的验证器有一条断言是「installed runtime did not expose the verified public release identity」** ——
**这就是那条身份的实物，连产物名都在。**

## 2. 三个**真实的「候选」**（Q14 要的「独立候选安装包」已经存在）

```
AAOS-v18a00075-20261001-x64\
AAOS-vd6bd374-20261001-x64\
AAOS-v82e8d28c-20261002-x64\    <- 最新（10-02）
```

最新那个的内容：

| 目录 | 内容 |
| --- | --- |
| **`core/`** | **`archeaxis-api.exe`** —— Rust Core **作为独立可执行文件** |
| **`desktop/`** | **225 项**：`ArcheAxis.Desktop.exe/.dll` + `Avalonia*.dll` —— **Avalonia 桌面** |
| **`workers/`** | **12 项**：`contracts` `document` `evaluation` `learning` `machine` `media` |
| **`runtime/`** | **14 项**：`python.exe` + `DLLs` + `Lib` —— **随包 Python** |
| `shared/` | `learning_scheduler.py` |
| `data/` | `worker-staging` |

**`candidate-manifest.json`（3.48 MB）**：

```json
{ "schema": "archeaxis.green-candidate/v1",
  "version": "dsh-82e8d28c-20261002",
  "provenance": {"source_commit": ..., "source_tree": ..., "source_snapshot": ...},
  "files": { "core/archeaxis-api.exe": ..., "desktop/ArcheAxis.Desktop.dll": ..., ... } }
```

**即：一个带 schema 版本、带 provenance、带逐文件记录的候选清单。**
**这比我在 Q14 里跟踪的 v0.5.0 安装包更新、更完整、更贴近任务书要的形态。**

## 3. **`worker-profile.json` —— 直接对应我发现的「能力目录缺口」**

```json
{ "schema": "archeaxis.worker-profile/v1",
  "python": "runtime/python.exe",
  "script": "workers/transport/text_ndjson.py",
  "staging": "data/worker-staging",
  "routes": [ {"capability": "archive.inventory", "script": "workers/document/worker_archive.py"},
              {"capability": "canvas.structure",  "script": "workers/document/worker_canvas.py"}, ... ] }
```

**这正是 `Executor::open_routes(capability, worker)` 要的东西**（我在 Q09/Q13 读过那段源码）——
**也就是 Python 面握手报 `capabilities: []` 那个缺口的来源。**

**它给了「能力 → 脚本」的真实映射，而且不止一个能力。**

## 4. 还有

| 项 | 内容 |
| --- | --- |
| **构建好的前端** | `frontend/` = `assets/` + `index.html` —— 可与我的 `frontend-dist` 对照/复用 |
| **可运行的 release 宿主** | `ArcheAxis.exe` **8.67 MB**（我的是 debug） |
| **vNext 数据库实物** | `aaos-vnext-data*/workspace.sqlite` + `-wal`/`-shm` + `writer.lock` |

## 5. 这些**没有**改我此前的结论，但**扩展**了它们

| 我此前的结论 | 老 Green 给出的补充 |
| --- | --- |
| Core 由宿主按需启动 | 候选里 Core 是**独立 exe**（`core/archeaxis-api.exe`），**不靠 `python -m`** |
| 能力目录有硬编码缺口 | **`worker-profile.json` 里有真实的 `routes` 映射** |
| Q14 需要一个当前版候选 | **已经有三个候选，最新的是 10-02** |
| Q14 要「发布身份」 | **`release-identity.json` 就是** |

## 6. 我**没有**做的

1. **未写入**老 Green 任何位置（全程只读）；
2. **未**复制它的文件到仓库；
3. **未**改任何实现文件；
4. **未**执行它的 `ArcheAxis.exe`（那是另一件事，需要你点头）。

## 7. 下一轮可选的入手点（按价值排序）

1. **把 `worker-profile.json` 的 `routes` 与我发现的握手缺口对上** —— 这可能**同时解掉 Q09 的一个缺口**；
2. **用候选的 `frontend/` 与我的 `frontend-dist` 对照** —— 验证我的构建产物是否正确；
3. **看候选能否作为 Q14 的验证对象**（它比 v0.5.0 新且完整）。
