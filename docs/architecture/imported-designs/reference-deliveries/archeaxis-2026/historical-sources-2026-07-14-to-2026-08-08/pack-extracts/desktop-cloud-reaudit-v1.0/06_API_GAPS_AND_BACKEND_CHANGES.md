# Agent Desktop 所需 API 缺口

## 1. 当前已有

- `/workspace/api/status`
- `/workspace/api/jobs`
- `/workspace/api/delivery`
- `/workspace/api/research`
- `/workspace/api/knowledge`
- `/workspace/api/learning`
- `/workspace/api/evolution`
- `/workspace/api/lifecycle`
- `/workspace/api/runtime/candidates`
- 资料导入和当前治理动作。

这些足够完成 Desktop A1。

## 2. A2 必须新增

### Public Task Summary

```json
{
  "schema_version": "v1",
  "items": [
    {
      "public_ref": "case_xxx",
      "activity": "资料导入",
      "state": "succeeded",
      "delivery_state": "delivered",
      "review_state": "candidate",
      "updated_at": "ISO-8601"
    }
  ]
}
```

`public_ref` 不得等于内部 job_id、command_id、event_id 或 package_id。
必须有服务端严格绑定和防枚举策略。

### Task Detail

```json
{
  "schema_version": "v1",
  "public_ref": "case_xxx",
  "title": "用户可理解标题",
  "kind": "intake.research",
  "status": "succeeded",
  "timeline": [],
  "artifacts": [],
  "inspector": {
    "context": {},
    "sources": [],
    "evidence": [],
    "permission": {},
    "trace": {},
    "evaluation": {},
    "audit": []
  }
}
```

### Capabilities

控制按钮必须由后端返回：

```json
{
  "can_pause": false,
  "can_resume": false,
  "can_retry": true,
  "can_approve": false,
  "can_replay": false
}
```

前端不得根据状态字符串自行推断可执行动作。

## 3. A3 必须新增

### Canvas Projection

```json
{
  "schema_version": "v1",
  "canvas_type": "research",
  "nodes": [],
  "edges": [],
  "read_only": true
}
```

节点 ID 应为公开投影 ID，不暴露内部主键。

### Replay Projection

- 稳定的阶段顺序；
- 输入输出摘要；
- Evidence 引用；
- Evaluation；
- Human decision；
- Retry lineage；
- 不返回凭据、绝对路径、数据库路径和内部 provenance ID。

## 4. 禁止

- 直接把 SQLite 行返回前端；
- 直接暴露内部 ID；
- 把日志文本当 API 合同；
- 前端用时间估算伪进度；
- 为了好看虚构 Agent 名称、模型、Token、成本；
- 没有后端能力时提供 Pause/Resume 假按钮。
