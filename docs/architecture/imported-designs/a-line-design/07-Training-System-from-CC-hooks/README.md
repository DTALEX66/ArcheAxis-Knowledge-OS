# CC Hooks 系统 → A 线 | 主动训练系统 + 自动化触发

## 文件全景

| 位置 | 行数 | 说明 |
|------|------|------|
| src/utils/hooks.ts | 4,673 | Hook 核心引擎 |
| src/hooks/ | 97 个文件 | 各类 hook 实现 |

## 核心架构

### 执行顺序

```text
Pre-Tool Hooks → Tool 执行 → Post-Tool Hooks
                      ↓ 失败 →
         Post-Tool-Use-Failure Hooks
                      ↓ 权限拒绝 →
         Permission-Denied Hooks
```

### Hook 生命周期

```typescript
// 4 个关键执行函数
executePreToolHooks(toolInput)      — 工具执行前
executePostToolHooks(toolInput, result) — 工具执行后
executePostToolUseFailureHooks(toolInput, error) — 工具失败后
executePermissionDeniedHooks(toolInput) — 权限拒绝后
```

### Hook 类型

| Hook | 功能 | 应用场景 |
|------|------|---------|
| fileSuggestions | 文件路径补全 | 学习时推荐相关文档 |
| unifiedSuggestions | 统一建议 | 知识点关联推荐 |
| usePromptSuggestion | Prompt 建议 | 学习提示模板 |
| useHistorySearch | 历史搜索 | 回顾历史学习记录 |
| useCancelRequest | 请求取消 | 中断超时学习 |
| useTaskListWatcher | 任务监控 | 学习进度跟踪 |

### Hook 结果类型

```typescript
type HookResult = {
  blockingError?: HookBlockingError  // 阻塞错误（中断流程）
  newCustomInstructions?: string      // 新指令（追加到系统 prompt）
  userDisplayMessage?: string        // 用户可见消息
}
```

## → A 线迁移映射

| A 线子系统 | 映射 | 迁移方式 |
|-----------|------|---------|
| 8. 主动训练 | Pre-Tool Hooks | 学习前触发：打开文档→生成练习→计时 |
| 8. 主动训练 | Post-Tool Hooks | 学习后触发：生成摘要→更新记忆→推荐下一步 |
| 8. 主动训练 | Post-Tool Failure Hooks | 学习失败处理：记录错题→降级→重试 |
| 8. 主动训练 | Permission-Denied Hooks | 规则违反处理：学习超时→走神提醒 |

### 训练流水线设计

```python
# KB 后端参考
class TrainingPipeline:
    def execute(subject: str):
        # Pre-training hooks
        self.pre_train(subject)  # 准备材料、设定目标
        
        # 实际学习（由用户完成）
        results = self.study_session(subject)
        
        # Post-training hooks
        self.post_train(results)  # 生成摘要、更新 FSRS
        
        if results.failed:
            self.on_failure(results)  # 记录错题、推荐补救
```
