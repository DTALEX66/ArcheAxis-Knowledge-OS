# 🎉 AAOS-01：**挂载条件在当前构建上证伪不了 —— 反而被证实**

## 1. 我先解决了第 137 轮留下的问题：**从当前源码构建**

```
cargo build -p archeaxis-api --bin archeaxis-api --release
  Finished `release` profile [optimized] target(s) in 52.35s
  CARGO_EXIT=0   CORE_EXE_OK
```

**只用了 52 秒，只有 2 条 dead-code 警告** ✓ —— **所以「版本警示」这一条**我可以直接消除**。**

## 2. 🎉 「无 worker」分支：**与第 137 轮预测逐条一致**

```json
"no_worker": {
  "capabilities":     [404, ""],                 // 与预测一致
  "machine_answers":  [404, ""],                 // 与预测一致
  "evidence_anchors": [200, "{\"items\":[]}"],   // 主表确实被服务
  "up": true, "output": ["archeaxis-api ready on http://127.0.0.1:8831"]
}
```

| 第 137 轮我从源码推的 | 本轮在当前构建上实测 |
| --- | --- |
| 无 profile → 只有 projections 表 | ✅ **`evidence/anchors` 200** |
| runtime 表的 `capabilities` 不挂载 | ✅ **404** |
| runtime 表的 `machine/answers` 不挂载 | ✅ **404** |

**所以第 137 轮那条「版本警示」可以解除**：**条件在与源码一致的二进制上成立。**

## 3. ⚠️ 「有 worker」分支：走了**另一条**错 —— 而且这条错很有信息量

```json
"with_worker": {
  "exit": 2,
  "output": ["worker profile file missing"],
  "up": null
}
```

**`open_routes` 不满足于启动文档里的 `text_worker` 块 —— 它要一个 **`worker-profile.json` 文件**。**

**这正是第 131 轮的那个结论**：

> 「`worker-profile.json` 是**分发产物**，由 `stage_backend_runtime.py` 在分发时生成。」

**本轮从**另外一端**印证了它**：**运行时确实在找那个文件。**

**而且我的 `worker_script_exists` 是 `false`** ——
**说明我猜的脚本路径 `workers/transport/text_ndjson.py` 在仓库里不存在**（那是**分发后的**相对路径 ✓）。

## 4. 因此下一轮很具体

```
只读地找「worker profile file missing」的抛出点，看它期望那个文件在【哪里】
  -> 然后放一个真实的 worker-profile.json 进去
     -> 再用当前构建实测「有 worker」那一侧：capabilities 应当从 404 变成 200/405
```

**那将是挂载条件的**闭环实证**：同一二进制、两份启动输入、两种路由集。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「放上 profile 后 capabilities 一定可用」 | **未试** |
| 「`workers/transport/text_ndjson.py` 不存在」 | **我只查了那一个路径** |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| **从当前源码构建了 `archeaxis-api.exe`** | `C:\Windows\Temp\aaos-target\release\`（**临时构建目录**） | **构建产物，未改仓库** |
| 用两条启动输入各跑一次 | `.project-local/runs/mount-condition/` | **项目自有开发输出** |

**未改任何仓库源文件**；**Green 目录内未创建/修改/删除任何文件**；
**未触碰官方 Green 的 `data/` 与资料库**；**未执行任何安装**。
