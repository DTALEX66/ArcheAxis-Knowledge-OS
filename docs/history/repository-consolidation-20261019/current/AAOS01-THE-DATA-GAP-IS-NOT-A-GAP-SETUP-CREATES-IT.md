# 🎯 AAOS-01：**`data/` 那个「缺口」不是缺口 —— 答案是 setup/initialize**

## 1. 三轮的问题，本轮结清

| 轮次 | 记录 |
| --- | --- |
| 100 | 启动器写 `ARCHEAXIS_DB_PATH=data/archeaxis.sqlite`（相对），而 `%LOCALAPPDATA%\com.archeaxis.workspace\data` **不存在** |
| 123 | 安装器的 NSIS 脚本里**没有**创建 app data 目录或 `data/` 子目录 → 我称其为「真实缺口」 |
| **124（本轮）** | **应用自己的 setup/initialize 步骤创建目录** —— **不是缺口** |

## 2. 证据（`app/setup/setup_status.py`）

```python
189: def _paths_writable_step() -> dict[str, str]:
190:     base = workspaces_base()
191:     try:
192:         base.mkdir(parents=True, exist_ok=True)          // ← 创建目录
193:         probe = base / ".setup-write-probe"
194:         probe.write_text("ok", encoding="utf-8")           // ← 并探测可写
195:         probe.unlink()
196:     except OSError as exc:
197:         return {"id": "paths_writable", "state": "blocked",
200:                 "message": f"workspace data path is not writable: {exc}",
201:                 "action_hint": "grant write permission on the data directory"}
203:     return {"id": "paths_writable", "state": "ready",
206:             "message": f"workspace data path is writable ({base})"}
```

```python
347: def initialize_workspace(request: SetupRequest | None = None) -> dict[str, object]:
348:     """Create the workspace (idempotent — an existing valid workspace is
349:     returned as-is). Raises ``ValueError`` when an existing manifest is
350:     invalid (fail-closed)."""
356:     manifest = create_workspace(workspaces_base(), WORKSPACE_NAME, domain_paths=…)
```

## 3. 而且**产品自己会告诉你该怎么做**

```python
179:     "action_hint": "POST /api/v1/setup/initialize to create the workspace first",
```

**这条提示出现在「发现遗留数据库但工作区不存在」时** —— 产品明确指向那一个路由 ✓

## 4. 路由与门禁（与第 118 轮的路由清单对上）

```python
// app/setup/router.py
55:  @router.post("/preflight")
56:  def post_setup_preflight(payload: SetupInitializeRequest | None = None):
64:  @router.post("/initialize", dependencies=[Depends(_require_desktop_write_request)])
65:  def post_setup_initialize(payload: SetupInitializeRequest | None = None):
```

| 路由 | 需要写授权吗 | 性质 |
| --- | --- | --- |
| `POST /api/v1/setup/preflight` | ❌ 否 | **只报告**各步骤状态 |
| `POST /api/v1/setup/initialize` | ✅ **是** | **创建**工作区（幂等） |

## 5. 🎯 所以整条链是这样闭合的

```
安装器不建 app data / data\  -> 【正确】，因为那是应用首次运行时的职责
应用启动 -> 前端探测 setup 状态（/preflight）
   -> 需要时调用 /initialize（带桌面写授权）
      -> _paths_writable_step 里 base.mkdir(parents=True, exist_ok=True)
         -> 目录就位 -> 启动器的相对 DB 路径可解析
```

**所以那不是产品的设计缺口，而是**我此前跳过了 setup 步骤**。**

**而第 102 轮我「手工把数据根指到一个含 `data/` 的目录」，本质上就是在替代这一步。**

## 6. 我要更正第 123 轮的措辞

第 123 轮我写：

> 「**这是一条从安装态到启动态的真实缺口。**」

**那句话下得太重了。** 准确的说法是：

| 我当时的观察 | 仍然成立 |
| --- | --- |
| 安装器不创建那两个目录 | ✅ **成立** |
| 启动器期望 `<数据目录>/data/` 存在 | ✅ **成立** |
| **「这是缺口」** | ❌ **不成立** —— **创建目录是应用 setup 的职责，产品里有这段代码** |

**我当时只查了安装器，没有查应用的 setup 流程就下了「缺口」的判断。**
**这正是我该避免的那类推断：从「我没看到」推出「不存在」。**

## 7. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「实际安装后一定会走 setup」 | **未安装、未验证** —— 我只读了源码路径 |
| 「`workspaces_base()` 就是数据根下的 `data/`」 | **我没有核对该函数** |

## 8. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
