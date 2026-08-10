# 全局信息架构与路由

## 路由组

```yaml
guanxin:
  overview
  activity
  approvals

agents:
  agent-center
  agent-detail
  skills
  models
  tools
  permissions

tasks:
  inbox
  running
  approval
  completed
  failed
  task-detail

canvas:
  research-canvas
  knowledge-canvas
  execution-canvas

replay:
  replay-list
  replay-detail

research:
  dashboard
  sources
  packages
  claims
  evidence
  conflicts
  unknowns
  review-queue

knowledge:
  library
  knowledge-editor
  graph
  learning
  mastery
  machine-knowledge
  review

workflow:
  workflows
  taskpacks
  schedules
  unattended
  runs

connections:
  models
  mcp
  github
  local-folders
  browsers
  skills
  usage

system:
  overview
  jobs
  delivery
  migrations
  backup
  security
  logs
  release
```

## 当前真实能力映射

- `overview` → `/workspace/api/status`
- `tasks/inbox` → `/workspace/api/jobs`
- `tasks/delivery` → `/workspace/api/delivery`
- `research/dashboard` → `/workspace/api/research`
- `research/lifecycle` → `/workspace/api/lifecycle`
- `knowledge/library` → `/workspace/api/knowledge`
- `knowledge/learning` → `/workspace/api/learning`
- `knowledge/mastery` → `/workspace/api/evolution`
- `knowledge/machine-knowledge` → `/workspace/api/runtime/candidates`
- `system/overview` → `/workspace/api/status`

其余路由必须标记为 Planned，直到后端提供正式投影。
