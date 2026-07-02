# 12｜每日 GitHub AI 项目筛选表模板

## 目标

每天筛选 5–10 个 GitHub AI 项目，优先服务：

```text
Knowledge-Base
Inspiration-Research
Cognitive-OS
Obsidian-Assistance
Codex / Claude Code / DeepSeek / Ollama / MCP / RAG / Agent 工作流
```

## 表格字段

| 字段 | 说明 |
|---|---|
| 日期 | 筛选日期 |
| 项目名 | owner/repo |
| 类别 | Agent / RAG / MCP / 文档解析 / 爬虫 / 观测 / 向量库 / UI 等 |
| 简介 | 一句话说明 |
| 当前用途 | 当前系统能怎么用 |
| 吸收方式 | 直接用 / Adapter / 只参考 / 暂缓 |
| 推荐接入层 | IR / KB / Cognitive-OS / Obsidian-Assistance / C线 |
| 成熟度 | demo / early / usable / mature |
| 维护状态 | active / slow / unknown |
| 许可证风险 | low / medium / high / unknown |
| 安全风险 | low / medium / high |
| Token 节省价值 | 0–5 |
| 效率提升价值 | 0–5 |
| 可本地化程度 | 0–5 |
| 与当前系统匹配度 | 0–5 |
| 综合分 | 自动计算 |
| 建议动作 | 收集 / 建 IntakeCard / 建 EngineeringContract / 暂缓 / 拒绝 |

## 评分公式

```text
综合分 =
  Token节省价值 * 0.20
+ 效率提升价值 * 0.20
+ 可本地化程度 * 0.20
+ 系统匹配度 * 0.25
+ 成熟度修正 * 0.10
- 风险惩罚 * 0.15
```

## 分级

```text
S级：立即建 IntakeCard，可进入 EngineeringContract
A级：加入候选池，补调研
B级：只参考设计
C级：暂缓
Reject：许可证 / 安全 / 方向不匹配
```

## 输出示例

```text
每日 GitHub AI 项目筛选表
日期：YYYY-MM-DD

今日推荐：
1. MarkItDown：文档转 Markdown，适合 IR/KB 输入层
2. Docling：高质量 PDF 解析，适合文档处理 Adapter
3. Crawl4AI：网页转 LLM-ready Markdown，适合 IR 研究输入
4. LiteLLM：多模型网关，适合 B线 model router
5. Langfuse：Agent / LLM Trace 观测，适合 Cognitive-OS observability
```

## 进入系统流程

```text
筛选表
  ↓
ProjectCandidate
  ↓
OpenSourceProjectProfile
  ↓
IntakeCard
  ↓
EngineeringContract
  ↓
KB experimental
```
