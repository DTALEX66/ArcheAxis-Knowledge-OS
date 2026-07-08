# 双线映射地图

> CC = CC Source  /  CW = CW Source

## A 线 → CC/CW 映射

```text
A 线子系统            CC/CW 参考                 迁移难度    优先
──────────────────────────────────────────────────────────────
1.  捕获系统           CC FileReadTool            🟢 低      ⭐
2.  知识结构系统        CC context/migrations       🟡 中
3.  学习诊断系统        CC compact (auto)           🟢 低      ⭐ (本次)
4.  学习路径系统        CC tasks.ts (claim+block)   🟢 低      ⭐ (本次)
5.  记忆编码系统        CC Zod schema               🟡 中
6.  间隔复习系统        你已有 FSRS                 ✅ 已有
7.  知识宫殿系统        CC memdir                   🟡 中
8.  主动训练系统        CC hooks (104个)            🔴 高
9.  技能实战系统        CC BashTool/sandbox         🔴 高
10. 元认知系统          CC Thinking                 🟡 中
11. 反馈错题系统        CC toolExecution            🟢 低      ⭐ (本次)
12. 输出教学系统        CC Skill/Plugin             🟡 中
13. 学习画像系统        CC cost-tracker             🟢 低
14. 长期巩固系统        CC compact (full+session)   🟢 低      ⭐ (本次)
15. 知识迁移系统        CC bridge                   🔴 高
16. 治理系统            CC 权限模型                  🟡 中
```

## B 线 → CC/CW 映射

```text
B 线组件             CC/CW 参考                 迁移难度    优先
──────────────────────────────────────────────────────────────
1.  多 Agent 协调      CW Coordinator              🟡 中      ⭐
2.  任务编排           CC tasks.ts                 🟢 低      ⭐ (本次)
3.  并行调度           CC StreamingToolExecutor    🟡 中
4.  事件路由           CW clawhip                  🔴 高
5.  Agent 权限         CC 权限模型                  🟡 中
6.  MCP 扩展           CC services/mcp/            🟡 中
```

## 依赖关系

```text
MVP 阶段（现在）：
  [A-3 诊断] ← compact auto trigger
  [A-4 规划] ← tasks.ts claim + block
  [A-11 反馈] ← toolExecution 错误链
  [A-14 巩固] ← compact full + session

  [B-2 编排] ← tasks.ts 直接复用

第二阶段（下一步）：
  [A-1 捕获] ← FileReadTool 分块
  [A-7 宫殿] ← memdir 目录索引
  [A-10 元认知] ← Thinking 推理链

  [B-1 协调] ← CW Coordinator 架构
  [B-3 并行] ← StreamingToolExecutor
  [B-5 权限] ← permission_enforcer

第三阶段（长远）：
  [A-8 训练] ← hooks 生命周期
  [A-12 教学] ← Skill 系统
  [A-15 迁移] ← bridge 跨进程

  [B-4 路由] ← clawhip 事件总线
  [B-6 扩展] ← MCP 4 种传输
```
