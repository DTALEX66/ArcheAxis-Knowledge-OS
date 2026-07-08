# CW clawhip → B 线 | 事件路由与自动触发

## 参考来源

https://github.com/Yeachan-Heo/clawhip

## 关键功能

clawhip 监控并路由：
- git commits → 触发代码分析
- tmux 会话 → 状态监控
- GitHub Issues/PRs → 自动响应
- Agent 生命周期事件 → 通知 Relay
- Discord 频道 → 人机接口

## B 线迁移

取代当前的手动 CODEX + DEEP 触发方式：

```text
事件源 → clawhip → 路由规则
  ├── git push → 自动触发 DEEP 测试流水线
  ├── 定时器 → 每日学习诊断
  ├── Discord 指令 → CODEX 任务分配
  └── Agent 完成事件 → 通知下一阶段
```


---

## A-Line 对齐

本组件为 B-Line 的一部分，与 A-Line (Human Learning OS) 的对接关系：
在A线各子系统之间路由事件与数据流

> 详细双线集成方案见 `/dual-system-integration/`
