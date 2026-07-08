# CC 权限模型 → A 线 | 治理系统 + B 线 Agent 安全

## 参考来源

| 文件 | 行数 | 说明 |
|------|------|------|
| src/Tool.ts | 754 | 工具基类 + permission 接口 |
| src/hooks/PermissionContext.ts | 379 | 权限上下文 |
| src/hooks/permissionLogging.ts | 220 | 权限日志 |
| src/services/tools/toolExecution.ts | 1,745 | 工具执行链（含权限校验） |

## 核心机制：强制权限链

每个工具调用必经路径：

```text
① Zod Schema 校验（输入验证）
  ↓ 失败→返回错误
② Tool 自检（isEnabled、准入条件）
  ↓ 失败→跳过工具
③ Pre-Tool Hooks（自定义预处理）
  ↓ 阻塞→中断流程
④ canUseTool（权限判断）
  ↓ 拒绝→进入 Permission-Denied Hooks
⑤ 实际执行
  ↓ 失败→进入 Post-Tool Failure
⑥ Post-Tool Hooks（后处理）
```

### PermissionMode 模型

```typescript
type PermissionMode =
  | "bypassPermissions"  // 完全信任（自动允许）
  | "plan"              // 计划模式（审慎允许）
  | "default"           // 标准模式（交互式确认）
```

## → A 线迁移（治理系统）

| A 线子系统 | 映射 | 迁移方式 |
|-----------|------|---------|
| 16. 治理系统 | PermissionMode | 学习模式：专注(bypass) vs 复习(default) vs 考试(plan) |
| 16. 治理系统 | 权限链 | 学习规则引擎：Zod 校验 → 自检 → Hook → 执行 |

### 学习规则引擎设计

```python
class LearningRuleEngine:
    def check_action(self, action, context):
        # 类似 CC 权限链
        self.validate_input(action)    # Zod schema
        self.self_check(action)        # 规则自检
        self.pre_hooks(context)        # 学习前处理
        self.can_execute(action)       # 规则判断
        # → 执行或拒绝
```

## → B 线迁移（Agent 安全）

| B 线组件 | 映射 | 迁移方式 |
|---------|------|---------|
| 5. Agent 权限 | CC 权限链 | Agent 操作安全控制 |

### Agent 权限分级

```python
class AgentPermission:
    READ_ONLY = ["search", "read", "list"]   # 自动允许
    WRITE = ["write", "edit", "create"]       # 需确认
    DANGEROUS = ["delete", "bash", "exec"]    # 双重确认
```
