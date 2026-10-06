# 🎯 AAOS-01：**两个 API 面，对应任务包里两件不同的事**

## 1. 源码给出了干净的答案

```python
// app/runtime_entrypoint.py
80:  def run_core(_) -> NoReturn:
81:      if os.getenv("ARCHEAXIS_DESKTOP_CONTROL") ... == "stdio-v1":
82:          _run_desktop_core()
83:      _exec_process(_uvicorn_command("app.main:app", 8000))

102:     server = uvicorn.Server(uvicorn.Config(
104:         "app.main:app", host=host, port=port, workers=1, proxy_headers=False))
```

**Core 永远服务 `app.main:app`** —— **没有多个 router 在运行时被选择**。

## 2. 所以第 104 轮的 404 是**正确行为**

| 面 | 属于 | 提供 |
| --- | --- | --- |
| **`app.main:app`** | **Python 后端** | ✅ `/api/v1/capabilities/`（我实测 200） |
| **`crates/archeaxis-api`** | **Rust 规范 Core** | ✅ `/api/v1/machine/answers` + `x-archeaxis-actor` 契约 |

**我第 104 轮拿 Rust Core 的路由去打 Python 后端** —— **404 正是应有的结果。**

**而这也与架构文档一致**：

| 文档说法 | 对应 |
| --- | --- |
| 「Rust Core = 唯一规范写入者」 | `crates/archeaxis-api` |
| 「遗留 Python 后端/BFF = 投影面」 | **`app.main:app`** ← **Tauri 宿主启动的就是它** |

## 3. 这重新划清了 Q02 与 Q03 的边界

| 任务包条目 | 内容 | 对应的面 |
| --- | --- | --- |
| **Q02** | Tauri 启动与**只读桥接** | ✅ **Python 后端 `app.main:app`** |
| **Q03** | **类型合同与权限** | ✅ **Rust Core `archeaxis-api`** |

> **所以「机器主体不得记录人工评审」这条契约属于 Q03，不属于 Q02。**
**我第 104 轮把它当成 Q02 的验收项去测，是把两件事混在了一起。**

## 4. 因此 Q02 的权限一项应当这样记

| 记法 | 说明 |
| --- | --- |
| ❌ **不应记为**「Q02 权限未测」 | **权限本来就不是 Q02 的范围** |
| ✅ **应记为**「Q02 只读桥接：已验证」 | 第 103 轮：状态与计数来自 Core |
| ✅ **并记为**「Q03 权限：尚未开始」 | 待对着 `archeaxis-api` 测 |

## 5. Q02 现状（修正后的记账）

| 验收要素 | 状态 |
| --- | --- |
| 宿主启动 | ✅ 第 102 轮 |
| 只读桥接 | ✅ 第 103 轮 |
| 读写闭环 | ⏳ 未涉及（且方向已明确：对着 `app.main:app`） |

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Rust Core 与 Python 后端功能等价」 | **未验证** —— 本文只说明「谁提供哪条路由」 |
| 「Q03 的权限契约一定成立」 | **完全没测** —— 只是现在知道该对着哪个面测 |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（读 `app/runtime_entrypoint.py`）。
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何东西**。
