# AAOS-01 Q07：**版本冲突证据 —— 命令 id 是幂等键，且带命名冲突检查**

Q07 要求「版本冲突证据」。本轮**从代码读到了这个机制**，而且**读它不需要冒充任何人**。

## 1. 机制（`app/workspace/service.py:1534-1551`）

```python
existing = connection.execute(
    "SELECT candidate_id, decision FROM machine_knowledge_approval_events_v1 "
    "WHERE approval_id=?",
    (command_id,),
).fetchone()
if existing is not None:
    unit_row = connection.execute(
        "SELECT unit_json FROM machine_knowledge_candidates_v1 WHERE id=?",
        (str(existing["candidate_id"]),),
    ).fetchone()
    if unit_row is None:
        raise RuntimeError("machine knowledge decision receipt lost its candidate")
    unit = MachineKnowledgeUnitV1.model_validate_json(str(unit_row["unit_json"]))
    if unit.title != title or str(existing["decision"]) != decision:
        raise RuntimeError(
            "workspace command id conflicts with an existing runtime decision"
        )
    return {"title": unit.title, "status": decision}
```

## 2. 这段代码保证了什么

| 性质 | 实现 |
| --- | --- |
| **幂等** | 同一个 `command_id` 再次提交 → **返回已记录的结果**，不重复生效 |
| **冲突即拒绝** | 同一个 `command_id` 若换了 **title** 或 **decision** → **抛错**，错误信息**点名冲突** |
| **收据不可悬空** | 决策收据指向的候选若丢失 → **抛错**，而不是静默返回 |

**注意：冲突校验的维度是「标题」与「决定」，不是版本号。** 我按字面描述，不替它升级含义。

## 3. 与第 40/41 轮合起来，运行时候选路径的完整面貌

| 维度 | 事实 |
| --- | --- |
| 审阅者身份 | **无此字段**；主体固定 `local-workspace` / `local` |
| 写保护 | 需要桌面启动令牌（未配置时有窄豁免） |
| 幂等与冲突 | **命令 id 为幂等键**，title/decision 不一致即拒绝 |
| 副作用 | 该函数**打开可写连接**（`sqlite3.connect(database)`）—— 与第 16 轮「Python 面会写库」一致 |

## 4. 因此 Q07 的两项要求各自的状态

| 要求 | 状态 |
| --- | --- |
| **候选由人处置** | ❌ **需要真人**（第 41 轮已说明：我不签，接口也不给我入口） |
| **版本冲突证据** | ✅ **机制已在代码中定位并引用**（本条） |

**并且我要说清：我提供的是「机制存在」的证据，不是「它被真实触发过」的证据。**
要后者需要一次真实的冲突提交 —— 而**运行时候选路径需要桌面令牌**，我没有。**所以我不声称已触发。**

## 5. 本轮未做

1. **未**取 `GET /workspace/api/runtime/candidates` 的真实输出（下一轮）；
2. **未**触发一次真实冲突（需要桌面令牌；且**不伪造**）；
3. **未改任何实现文件**；官方 Green 与资料库**零触碰**。

## 6. 下一轮

取 `GET /workspace/api/runtime/candidates` 的真实输出（**只读，不需要任何身份**），
把它与本轮的代码机制对照 —— **只读能测到什么就测到什么，测不到的明确写成未测**。
