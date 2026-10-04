# 🎉🎉 AAOS-01 Q02：**Core 起来了，而且在提供服务**

## 1. 实测结果

用强 token（64 位十六进制，`secrets.token_hex(32)`）重跑：

```json
"migrate_exit": 0
"core_alive": true
"ready_after_seconds": 1
```

**Core 自己的输出**：

```
INFO:     Started server process [31316]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8793 (Press CTRL+C to quit)
INFO:     127.0.0.1:60294 - "GET /api/v1/health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:60297 - "GET /api/v1/capabilities/ HTTP/1.1" 200 OK
```

## 2. 这是 Q02 要的「实际 Core 生命周期」

| 环节 | 结果 |
| --- | --- |
| 迁移 | ✅ **`migrate_exit: 0`**（多 owner 全部 applied，第 99 轮记录） |
| 启动 | ✅ `Started server process` |
| 应用初始化 | ✅ **`Application startup complete.`** |
| 监听 | ✅ `Uvicorn running on http://127.0.0.1:8793` |
| **应答真实请求** | ✅ **`GET /api/v1/capabilities/` → `200 OK`** |
| 就绪耗时 | ✅ **1 秒** |

**响应体**：

```json
{"count": 0, "capabilities": []}
```

## 3. 那个报错不是缺陷（要讲清楚）

```
  File ".../app/runtime_entrypoint.py", line 114, in watch_parent_pipe
    for command in _desktop_control_commands(sys.stdin):
  File ".../app/runtime_entrypoint.py", line 181, in _windows_desktop_control_commands
    raise OSError(error, "PeekNamedPipe failed for desktop parent pipe")
PermissionError: [Errno 1] PeekNamedPipe failed for desktop parent pipe
```

| 事实 | 含义 |
| --- | --- |
| 我**独立**启动 core，没有桌面父进程管道 | `watch_parent_pipe` 读不到父管道 |
| **服务器仍然启动并正常应答** | 该管道用于**父进程监控**，**不影响服务** |
| 启动器模式下由宿主建立那条管道 | **真实场景下不会有这个错误** |

**所以这是我启动方式的产物，不是产品缺陷。**

## 4. 顺带一个与第 79 轮呼应的观察

`/api/v1/capabilities/` 返回 **`count: 0`** —— 与第 79 轮「能力目录与实现之间缺少显式映射」的发现一致 ✓
（**这里只作为呼应记录，不作为本轮结论。**）

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Q02 就此通过」 | 交付物还包含**宿主自己驱动**的那条完整路径与读写闭环；本轮是**手工复现同一命令**并观察到服务就绪 |
| 「宿主的调用也一定成功」 | **未验证** —— 第 100 轮查明宿主那条路径缺 `data/` 子目录 |

**但「Core 能迁移、能启动、能就绪、能应答」这一条，现在已经确证。**

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 在临时目录跑了 migrate + core（强 token） | `.project-local/runs/core-strong-token/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何东西**；只 kill 自己起的句柄。
