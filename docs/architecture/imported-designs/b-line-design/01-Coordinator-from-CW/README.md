# CW 多 Agent 协调 → B 线 | CODEX + DEEP 编排

## 参考来源

D:\Project Directory\claw-code\rust\crates\runtime\src\

## 关键组件

Coordinator 架构（来自 Claw Code Rust 源码）：

```
OmX (工作流编排)
  ↓ 指令分解
Coordinator (主协调器)
  ├── Agent A (工具集 + Task 系统)
  ├── Agent B (工具集 + Task 系统)
  └── Agent C (工具集 + Task 系统)
  ↓ 结果归并
clawhip (事件路由) → Discord / git / CI
```

## B 线迁移

当前 CODEX 手动触发 → 升级为 OmX 自动编排
当前 DEEP 串行执行 → 升级为并行多 Agent

### 实现路径

1. CODEX 作为 Coordinator
2. DEEP 任务作为 Agent 任务池
3. CC Task 系统作为任务调度层
4. clawhip 模式作为事件通知层


---

## A-Line 对齐

本组件为 B-Line 的一部分，与 A-Line (Human Learning OS) 的对接关系：
协调A线各子系统（捕获→诊断→规划→编码→宫殿→反馈→画像→训练→执行→治理）的运作流程

> 详细双线集成方案见 `/dual-system-integration/`
