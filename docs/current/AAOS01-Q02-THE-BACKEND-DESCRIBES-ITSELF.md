# AAOS-01 Q02：**后端自我描述 —— 完整路由清单**

## 1. 方法：不再猜路径，直接问后端

```
GET /openapi.json   ->  200
```

**后端返回了它自己的路由表。** 这是**应用自己的说法**，不是我推断的。

## 2. 路由清单（按域分组）

### 系统 / 设置
```
/api/v1/system/status          /api/v1/system/handshake      /api/v1/system/restart
/api/v1/setup/preflight        /api/v1/setup/status
/api/v1/workspace/api/status   /api/v1/workspace/api/diagnostics
```

### 知识 / 证据 / 学习
```
/api/v1/workspace/api/knowledge                     /api/v1/workspace/api/knowledge/start-learning
/api/v1/workspace/api/evidence/anchor               /api/v1/workspace/api/evidence/anchors
/api/v1/workspace/api/evidence/anchor/{anchor_id}   /api/v1/workspace/api/evidence/bundles
/api/v1/workspace/api/evidence/bundles/{id}/inspection
/api/v1/workspace/api/learning                      /api/v1/workspace/api/learning/practice
/api/v1/workspace/api/research                      /api/v1/workspace/api/research/approve
/api/v1/workspace/api/commands/promote-research     /commands/record-practice /commands/start-learning
```

### 原件 / 转换 / 导入
```
/api/v1/workspace/api/intake/upload                 /api/v1/workspace/api/intake/url
/api/v1/workspace/api/batch/import                  /api/v1/workspace/api/batch/{id}/pause|resume|shutdown|status
/api/v1/workspace/api/library                       /api/v1/workspace/api/library/{raw_sha256}/content
/api/v1/workspace/api/library/{raw_sha256}/converted  /…/conversion-run
/api/v1/workspace/api/pdf/{content_key}             /api/v1/workspace/api/cases/{artifact_id}
```

### 备份 / 交换 / 运行
```
/api/v1/workspace/api/backup/create                 /api/v1/workspace/api/backup/verify  /backup/restore
/api/v1/workspace/api/exchange/export               /api/v1/workspace/api/exchange/import  /exchange/verify
/api/v1/workspace/api/runtime/candidates            /api/v1/workspace/api/runtime/approve
/api/v1/workspace/api/runtime/deprecate             /api/v1/workspace/api/runtime/knowledge
/api/v1/workspace/api/jobs                          /api/v1/workspace/api/jobs/{job_id}
/api/v1/workspace/api/delivery                      /api/v1/workspace/api/delivery/dispatch  /delivery/retry
/api/v1/workspace/api/planner/preview               /api/v1/workspace/api/planner/execute
/api/v1/workspace/api/lifecycle                     /api/v1/workspace/api/evolution
/api/v1/workspace/api/audit/stream
```

### 前端视图
```
/api/v1/workspace/api/v1/home       /api/v1/workspace/api/v1/activity
/api/v1/workspace/api/v1/objects/{public_ref}
/api/v1/workspace                       /api/v1/workspace/api/_desktop/ready
```

## 3. 这一份清单的价值（对我此前的工作）

| 用途 | 说明 |
| --- | --- |
| **不再猜路径** | 第 104/105 轮的 404 就是因为我在猜；现在有权威清单 |
| **Q02 读写闭环有了入口** | `/api/v1/workspace/api/knowledge`、`intake/upload` 等 |
| **呼应第 79 轮那个缺失的连接** | 这张表是**运行时真相**；atlas 是**已批准目录**；两者之间仍缺映射 |

**第 79 轮我说「能力与实现之间缺少可机读的映射」—— 现在实现侧有了权威来源**
（应用自己给出的路由表），**但声明侧（atlas）依然没有指向它**。

**所以那个缺口现在更清楚了：不是缺数据，是缺一张把两边对起来的表。**

## 4. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「清单完整」 | 我的输出被截断，只读到约 60 条；**总数未确认** |
| 「读写闭环已通过」 | **本轮只读了 schema，没有实际写** |

## 5. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑 migrate + core、取 `/openapi.json` | `.project-local/runs/readwrite/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**；只 kill 自己起的句柄。
