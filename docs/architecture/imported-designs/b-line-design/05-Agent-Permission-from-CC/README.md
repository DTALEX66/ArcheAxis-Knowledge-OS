# CC 权限模型 → B 线 | Agent 安全控制

## 参考来源

src/Tool.ts + src/permission_enforcer.rs

## 强制权限链

每个工具调用必经：
```
Zod 校验 → tool 自检 → pre-hooks → canUseTool → 执行 → post-hooks
```

## B 线迁移

CODEX + DEEP 的 Agent 操作权限控制：
- 只读操作（search/read）→ 自动允许
- 写操作（write/edit）→ 需审批
- 危险操作（bash/delete）→ 双重确认


---

## A-Line 对齐

本组件为 B-Line 的一部分，与 A-Line (Human Learning OS) 的对接关系：
控制A线各系统的访问权限与安全边界

> 详细双线集成方案见 `/dual-system-integration/`
