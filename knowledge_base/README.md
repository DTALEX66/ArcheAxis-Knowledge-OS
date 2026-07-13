# Knowledge-Base

Knowledge-Base 是 Cognitive-Loop-OS 的知识资产与学习运行层，不再作为独立、无边界增长的 API 集合维护。

## 领域结构

```text
knowledge_base/
├── api.py                 FastAPI 组合入口与遗留兼容路由
├── routers/
│   ├── composite.py       pipeline/garden/analytics/evidence/export 等稳定复合入口
│   ├── quality.py         准确率、处理总账、内容证据、多源核验
│   └── projection.py      Obsidian 投影兼容层
├── cards/                 知识卡片
├── search/                FTS5 + sqlite-vec 混合检索
├── reviews/               SM-2 复习
├── mistakes/              错误模式与修正
├── machine_knowledge/     A→B 转译和机器知识单元
└── tests/                 KB 独立回归测试
```

## 双主线

| 线 | 资产流 |
|---|---|
| A 线：人类学习 | Document → Card → Review → Mistake → Mastery |
| B 线：机器知识 | ContextPack → TaskPack → MachineKnowledgeUnit |

## API 原则

- 新能力必须优先进入 `routers/` 下的复合入口。
- 遗留细粒度路由只做兼容，不再复制一套新路由。
- 用户输入的数据库表名必须经过白名单和标识符校验。
- 无人工真值时 accuracy 为 `unverified`；调用者证据返回 `caller_supplied_candidate`、`server_verified=false`、`requires_human_review=true`；静态来源建议标记为 `recommended_sources_only_not_verified`。
- 文件/证据操作默认只读或 dry-run，正式写入必须显式请求。

## 验证

```bash
cd knowledge_base
python -m pytest tests -q --tb=short
```
