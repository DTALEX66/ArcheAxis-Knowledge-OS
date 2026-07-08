# CC StreamingToolExecutor → B 线 | 并行任务调度

## 参考来源

src/services/tools/StreamingToolExecutor.ts（~300 行）

## 关键设计

LLM 还在输出 token 时，StreamingToolExecutor 已开始并发执行已知工具：
- 收到工具调用 → 立即调度执行（不等待 LLM 完成）
- 只读工具（Read/Grep/Search）可以完全并行
- 写操作（Write/Edit）需要串行互斥

## B 线迁移

DEEP 并行任务调度可借鉴此模式：
- DEEP-02 ingest（只读）和 DEEP-03 frontend（只读）可以并行
- DEEP-01 backend（写操作）需要串行

Agent 间通信使用兄弟 abort 机制：一个 Agent 失败 → 通知同组其他 Agent 取消


---

## A-Line 对齐

本组件为 B-Line 的一部分，与 A-Line (Human Learning OS) 的对接关系：
并行执行A线多个子系统任务，提升效率

> 详细双线集成方案见 `/dual-system-integration/`
