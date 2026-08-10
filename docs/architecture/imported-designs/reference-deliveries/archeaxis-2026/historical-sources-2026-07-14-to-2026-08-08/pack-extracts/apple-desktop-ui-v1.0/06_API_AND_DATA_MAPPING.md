# API 与界面数据映射

## 当前可直接接入

| UI | API |
|---|---|
| 观心真实状态 | `/workspace/api/status` |
| 最近任务 | `/workspace/api/jobs` |
| 投递/回执 | `/workspace/api/delivery` |
| 察微审核队列 | `/workspace/api/research` |
| 藏识候选 | `/workspace/api/knowledge` |
| 学习产物 | `/workspace/api/learning` |
| Mastery/机器候选 | `/workspace/api/evolution` |
| Runtime 知识 | `/workspace/api/runtime/candidates` |
| Lifecycle | `/workspace/api/lifecycle` |
| Diagnostics | `/workspace/api/diagnostics` |

## 新增需求

### A3

- `/workspace/api/public-tasks`
- `/workspace/api/public-tasks/{ref}`
- `/workspace/api/public-tasks/{ref}/actions`
- `/workspace/api/agents`
- `/workspace/api/agents/{ref}`

### A4

- `/workspace/api/canvases/{type}`
- `/workspace/api/replays`
- `/workspace/api/replays/{ref}`

### A5

- `/workspace/api/connections`
- `/workspace/api/connections/{ref}`
- `/workspace/api/system/health-detail`

## 公共引用规则

- 与内部 ID 不同；
- 不可枚举；
- 严格读回；
- 可以失效；
- 不包含数据库语义；
- DTO exact-key validation；
- 不返回绝对路径、凭据或原始日志。
