# CC toolExecution → A 线 | 反馈与错题系统

## 参考来源

src/services/tools/toolExecution.ts（1,745 行）
src/services/tools/StreamingToolExecutor.ts

## 关键模式

错误处理链：
  捕获(Capture) → 分类(Categorize) → 归因(Attribute) → 推荐(Recommend)

## A 线迁移

错题系统的反馈流水线可完全对标此链条
