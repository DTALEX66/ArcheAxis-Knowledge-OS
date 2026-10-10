# AAOS-01 Q07：**两条审批路径，一条不能冒充，另一条正是不能冒充的地方**

第 40 轮查明「审阅者身份故意不作为客户端字段」。本轮把**身份从哪来**读清楚了，结果分成**两条不同的路径**。

## 1. 运行时候选路径：**没有审阅者，且主体是固定的**

```python
# app/workspace/router.py:288-291
def _local_principal(request: Request) -> dict[str, str]:
    """Trust only direct loopback requests in the local-first workspace."""
    _require_local_request(request)
    return {"subject": "local-workspace", "role": "local"}
```

```python
# app/workspace/service.py:1575-1584
def approve_runtime_title(*, command_id: str, title: str, db_path: str | Path) -> dict[str, object]:
    """Approve one uniquely titled machine candidate without exposing its ID."""
    return _decide_runtime_title(command_id=command_id, title=title,
                                 decision="approved", db_path=db_path)
```

**没有 `reviewer_id` 形参**；主体是固定的 **`local-workspace` / `local`** —— **不是某个人的身份**。

## 2. 研究提升路径：**确实接收 `reviewer_id`**

```python
# app/workspace/service.py:1136
def promote_research_source(*, command_id: str, source: str, reviewer_id: str, rationale: str, ...)
# app/workspace/service.py:1154
def promote_research(*, command_id: str, package_id: str, reviewer_id: str, rationale: str, db_path)
```

而且它会**核对** `(package_id, reviewer_id, decision, rationale)` 是否与记录一致（一致性检查，不是身份认证）。

## 3. 这个对照正是 Q07 的关键

| 路径 | 审阅者身份 | 我能不能冒充 |
|---|---|---|
| **运行时候选** `/api/runtime/approve` | **无此字段**；主体固定为 `local-workspace` | **不能** —— 接口没给入口 |
| **研究提升** `/api/research/approve`、`/api/commands/promote-research` | **接收 `reviewer_id`** | **能 —— 所以我绝不这么做** |

> **第一条路径由结构保护；第二条路径的 `reviewer_id` 是我**唯一**可能凭空捏造真人身份的地方 —— 因此这一轮我把它点明，并且不调用它。**

## 4. 本轮**没有**调用任何审批，理由

1. **运行时候选路径**：需要桌面启动令牌，我的现场没有（且它的主体是 `local-workspace`，不代表真人）；
2. **研究提升路径**：**它要求 `reviewer_id`** —— **我没有任何真人身份可填，也不会编一个**。

**所以 Q07「候选由人处置」这一环，仍然需要真人在真实桌面环境执行。**
**我现在能说清的是：架构上哪一条路径安全（结构保护），哪一条路径需要人自觉（我来点明并回避）。**

## 5. 本轮未做

1. **未**取 `GET /workspace/api/runtime/candidates` 的真实输出（下一轮第一件事）；
2. **未**取「版本冲突」证据（`_decide_runtime_title` 是否有一致性/冲突检查**未读**）；
3. **未改任何实现文件**；官方 Green 与资料库**零触碰**。

## 6. 下一轮

1. 取 `GET /workspace/api/runtime/candidates` 真实输出（**只读，不需要任何身份**）；
2. 读 `_decide_runtime_title`：看它是否做**版本/冲突**校验 —— 这正是 Q07 要的「版本冲突证据」，而且**读它不需要我冒充任何人**。
