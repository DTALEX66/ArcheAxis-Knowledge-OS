# CC Compact 系统 — A 线诊断+巩固参考

## 文件全景（8 文件，3,454 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| compact.ts | 1,579 | 主引擎：全量压缩 + 部分压缩 |
| autoCompact.ts | 313 | 自动触发策略（基于 token 阈值） |
| microCompact.ts | 480 | 微压缩（快速轻量版） |
| apiMicrocompact.ts | 134 | API 专用微压缩 |
| sessionMemoryCompact.ts | 568 | 会话记忆压缩 |
| prompt.ts | 289 | 压缩提示词模板 |
| grouping.ts | 60 | 消息分组工具 |
| postCompactCleanup.ts | 74 | 压缩后清理 |

## 核心压缩流程

```
触发 → PreCompact Hooks → Token 估算 → Forked Agent 压缩 → 结果校验 → PostCompact Hooks
```

## 自动触发逻辑（autoCompact.ts）

```
getEffectiveContextWindowSize(model)
    ↓
tokenCountWithEstimation(messages) > autoCompactWindow
    ↓
trySessionMemoryCompaction() → 尝试记忆压缩
    ↓ 失败则
compactConversation() → 全量压缩
    ↓
runPostCompactCleanup() → 清理
```

核心参数：
- `MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000`（压缩输出 token 预算）
- `POST_COMPACT_TOKEN_BUDGET = 50_000`（压缩后 token 预算）
- `POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000`
- `POST_COMPACT_MAX_FILES_TO_RESTORE = 5`
- 环境变量 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 控制阈值

## 5 种压缩策略

### 策略 1：全量压缩（compactConversation）
适用：对话达到上下文窗口上限
过程：将全部消息发给 LLM → LLM 生成摘要 → 替换为摘要消息
特点：最彻底，但最贵

### 策略 2：部分压缩（partialCompactConversation）
适用：只需要压缩对话的早期部分
过程：指定 direction → 只压缩早期部分 → 保留近期对话原样
特点：保留近期上下文不丢失

### 策略 3：自动压缩（autoCompact.ts）
适用：自动监控，达到阈值即触发
过程：检查 token 数 → 超过窗口 → 自动调用全量或记忆压缩
特点：用户无感，后台执行

### 策略 4：微压缩（microCompact.ts）
适用：小型对话的快速压缩
过程：轻量级 prompt → 只压缩关键信息 → 快速返回
特点：开销小，适合频繁调用

### 策略 5：会话记忆压缩（sessionMemoryCompact.ts）
适用：长时间跨度的记忆压缩
过程：只压缩记忆相关消息 → 保留对话上下文
特点：记忆优先，对话无损

## 压缩结果结构

```typescript
type CompactionResult = {
  messages: Message[]           // 压缩后的消息
  preCompactTokenCount: number  // 压缩前 token 数
  postCompactTokenCount: number // 压缩后 token 数
  summaryResponse: AssistantMessage // LLM 生成的摘要
}
```

## → A 线迁移映射

| A 线子系统 | CC 映射 | 迁移方式 |
|-----------|---------|---------|
| 3. 诊断 (Diagnose) | autoCompact.ts 阈值检测 | 学习薄弱点检测：错题率 > 阈值 → 触发诊断 |
| 3. 诊断 (Diagnose) | microCompact.ts 快速压缩 | 每日快速诊断：5 分钟轻量评估 |
| 14. 巩固 (Consolidate) | compact.ts 全量压缩 | 周/月深度巩固：全量回顾 → 生成巩固包 |
| 14. 巩固 (Consolidate) | sessionMemoryCompact.ts | 长期记忆巩固：只压缩掌握的概念，保留薄弱点 |
| 14. 巩固 (Consolidate) | partialCompactConversation | 增量巩固：只处理新增知识点 |
