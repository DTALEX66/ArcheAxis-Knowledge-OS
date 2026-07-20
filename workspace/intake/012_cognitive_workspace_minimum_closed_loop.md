# 012 - Cognitive Workspace 最小闭环 MVP

## 目标

提供一个可通过浏览器和受认证 HTTP API 运行的最小受治理闭环：

```text
persisted ResearchPackage
→ Knowledge candidate promotion
→ Learning candidate
→ approved learning cards
→ practice evidence
→ MasterySignal
→ MachineKnowledge candidate
→ audit timeline
```

## 公共入口

- `GET /workspace`：最小浏览器工作台。
- `GET /workspace/api/diagnostics`：复用安全的版本化运行状态。
- `POST /workspace/api/commands/promote-research`
- `POST /workspace/api/commands/start-learning`
- `POST /workspace/api/commands/approve-learning`
- `POST /workspace/api/commands/record-practice`
- `GET /workspace/api/cases/{artifact_id}`

所有 mutation 请求只接受业务 command 字段；`reviewer_id` 不是请求契约的一部分。路由从 `request.state.identity` 取得认证主体，并在 `auth_method=none`、无 subject 或 readonly 身份时 fail closed。

## 数据与边界

- 没有向 legacy `graph_entities` / `graph_relations` 写入。
- Research promotion 复用 `knowledge_candidate_governance_events_v1` 的持久审批 receipt。
- Learning candidate 复用 `knowledge_candidate_learning_artifacts_v1` 的持久 approval ID。
- Practice 复用确定性 review ID，Mastery 和 Machine candidate 均由现有受治理领域服务产生。
- 已有 promotion、learning candidate 与 practice command ID 会先与持久 receipt 比对：同语义重放返回原结果，改变 package/unit/reviewer/rationale/quality 的重放返回 `409 conflict`。
- API 只暴露最小 IDs、状态和 event type；不暴露数据库、备份或 provenance 文件路径。

## 运行前提

通过唯一运行入口启动，确保所有现有 schema owner 已迁移：

```text
python -m app.runtime_entrypoint core
```

Workspace mutation 必须使用已有的 API-key/JWT 认证边界。前端提供一个仅在当前页面内存中使用的密码输入框以发送既有 API key/JWT；它不写入 localStorage、cookie、数据库、日志或项目文件。

## 验收

`tests/test_workspace_api.py` 覆盖：

1. 页面与安全 diagnostics 可访问；
2. no-auth 匿名 mutation 返回 `401`；
3. 已认证 HTTP 请求从持久化 ResearchPackage 走到 Mastery 与 Machine candidate；
4. audit endpoint 能在同一持久化 case 中读到 machine candidate 事件。

完整发布仍必须通过 Root、Knowledge Base、Integration、Ruff、Architecture Guard、convention、精确树审查和 CI。
