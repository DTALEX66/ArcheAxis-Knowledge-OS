# AAOS-01 Q03 **撤回第 19 轮**：握手早已存在，我的模块是重复品

## 1. 事实

```
app/workspace/system.py:5    * GET /api/v1/system/handshake — product identity + runtime facts
docs/truth/EXECUTION_STATUS_LOG.md:1224   RUN-203 Handshake：app/workspace/system.py
```

`app/workspace/system.py`（134 行）已有完整实现，而且**比我的更完整**：

| 字段 | 它怎么来 | 我的模块 |
| --- | --- | --- |
| `backend_version` | 读 **`pyproject.toml`**（单一真源） | 由调用方传入 |
| `source_commit` | **真实执行 `git rev-parse --short HEAD`** | 由调用方传入 |
| `schema_version` | **`PRAGMA user_version`**，且以 **`mode=ro` 只读**打开 | 由调用方传入 |
| `workspace_id` | 运行时数据根的稳定 hash | 由调用方传入 |
| `migration_state` | 反映 **supervisor 真实状态**（migrating/failed/ready） | 由调用方传入 |
| 访问控制 | `dependencies=[Depends(_require_local_request)]` | 无 |

**所以第 19 轮的 `app/workspace/compat_handshake.py` 是重复品，本轮撤回。**

包内明文："**已存在且合格的实现直接复用，只修缺口，不为目录漂亮大搬迁**"。

## 2. 我的错误是什么（根因，不是借口）

第 9 轮我检索：

```
git grep product_id|api_contract|migration_state -- crates/archeaxis-api/src   -> 零命中
```

然后我写下"这些字段名在 Core 源码里零命中"，并**推论"没有握手"**。

> **错在搜索范围**：我在**一个栈**（Rust Core）里找**字段名**，却把结论推广成了**整个仓库没有这个端点**。

**教训（可复用）**：

**这是本会话第六次由测量纠正判断，也是第二次由我自己的搜索范围错误造成**（第一次是第 15 轮在 `router.py` 里找连接）。

## 3. 但这也**收窄**了 Q03 —— 是好事

握手**不是缺口**。缺口回到第 15 轮那条：

- **Tauri 宿主启动的是旧 Python 后端**（`python -m app.runtime_entrypoint core`），
- **那个后端提供这套握手**（`app/workspace/system.py`、`app/workspace/router.py`、BFF）；
- **Rust Core 不提供** —— 它只有 `/api/v1/system/version` 三字段，且自述 outline。

**所以问题不是"缺一个握手"，而是"前端现在连的那套（Python BFF）与想成为唯一写者的那套（Rust Core）不是同一套"。**

**这比第 19 轮的理解更清楚，而且不需要我新写任何东西。**

## 4. 本轮动作

1. **删除** `app/workspace/compat_handshake.py` 与 `tests/test_compat_handshake_satisfies_the_shell.py`（新提交删除，**不改写历史**）；
2. 记录本文件。

## 5. 本轮**未**做

1. **未**核 `app/workspace/supervisor.py` 与 `_require_local_request` 的行为；
2. **未**实际调用一次真实握手（未启动任何服务）；
3. 第 13 轮起欠的 `RuntimeClient.test.ts` 仍未读（**已按第 17 轮声明降级为条件任务**）。
