# CC Task 系统 → B 线 | DEEP 任务编排

## 参考来源

cc-code/src/utils/tasks.ts（779 行）

详见 A-Line/03-Plan-Revision-from-CC-TaskSystem/README.md

## B 线迁移要点

DEEP-01~99 的任务流水线直接映射为 CC Task：

| DEEP 任务 | Task 映射 |
|-----------|-----------|
| DEEP-00 repo_fix | task: repo_fix, owner: agent_A |
| DEEP-01 backend_api | task: backend_api, blockedBy: [repo_fix] |
| DEEP-02 ingest | task: ingest, blockedBy: [repo_fix] |
| DEEP-03 frontend | task: frontend, blockedBy: [backend_api] |

并行性：无依赖的 task 可以同时被多个 Agent claim
安全性：文件锁保证不会重复执行
