# AAOS-01：**两条 status 路由 —— 我又看错了地方**

## 1. 本轮先确认了一件事：`_migration_state()` **不是**那个计数

```python
// app/workspace/system.py
78:  def _migration_state() -> str:
79:      """Reflect the supervisor's schema-migration phase for the handshake."""
80:      state = supervisor.state
81:      if state is BackendSupervisorState.MIGRATING:
82:          return "migrating"
83:      if state is BackendSupervisorState.FAILED:
84:          return "failed"
85:      return "ready"
```

**它是一个**监督器阶段**（migrating / failed / ready），不是一个数字。**
**我第 117 轮以为 `applied: 6` 的算法在这里 —— 猜错了。**

## 2. 产品有一条自己的迁移状态命令

```bat
"%PY%" -B -I -m app.runtime_entrypoint migration-status
```

| 时机 | 退出码 |
| --- | --- |
| 首次迁移**之前** | **1**（那时还没有库） |
| **迁移之后** | **0**，并返回结构化状态 |

返回体里是**按 owner** 的清单：

```json
{"database": "…\migstatus\archeaxis.sqlite",
 "status": [{"kind": "sqlite_core", "operation": "apply", "owner": "core.sqlite",
             "provenance": {"applied_migrations": ["core_sqlite_baseline_v1"], …}}, …]}
```

**即：这个命令报的是「每个 owner 应用了哪些迁移」** —— **粒度是按 owner 的** ✓

**这支持了第 117 轮我标为「推断」的那个方向**（计数是 owner 维度），**但仍未证实**。

## 3. 🎯 本轮真正找到的：有**两条** status 路由

| 路由 | 实现 | 内容 |
| --- | --- | --- |
| `/api/v1/**system**/status` | `app/workspace/system.py:112 system_status()` | **监督器状态**：state / uptime / pid / 日志尾部 |
| `/api/v1/**workspace**/api/status` | **（待读）** | **就是带 `migrations: {applied: 6, pending: 4}` 的那条** |

**我前几轮把 `applied: 6` 归给 `system.py` —— 那是错的。**
**那个读数来自 **workspace** 那条路由，它的处理器我还没读。**

**这是一处方法教训**：两条路由名字都像「状态」，我**没有先确认是哪一条**就开始找实现。

## 4. 所以下一轮**非常具体**

```
读 /api/v1/workspace/api/status 的处理器，找到 migrations.{applied,pending} 的计算方式
```

**然后与 `migration-status` 的按-owner 清单对照** —— 缺口即可定性。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「`applied: 6` 就是某 owner 的计数」 | **仍未证实** —— 处理器还没读 |
| 「`migration-status` 与那条路由用同一套数据」 | **未验证** |

## 6. 我的输出**又**被截断了（第四次记）

`migration-status` 的返回体有 6,337 字节，**我只看了一部分**。
**但这次我遵守了第 117 轮定的规则：先写文件，再用 Python 解析文件** ✓ ——
所以**我不报总数**，只报我看到的结构。

## 7. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑 `migration-status` 与 `migrate`（输出**写入文件**） | `.project-local/runs/migstatus/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**。
