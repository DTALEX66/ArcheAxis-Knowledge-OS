# Knowledge and Research Facades

## 目标

建立真实、可安装、可回滚的 Knowledge/Research 公共边界，不复制搜索或 Intake generator 逻辑。

## Knowledge tracer

```text
query_knowledge(keyword)
→ knowledge_base.search.keyword_search
→ shared.storage.fts5_search
→ KnowledgeQueryResult
```

当前稳定合同只承诺 `keyword`。standalone `/search` 与 Facade 对同一输入的 ID、排序和 keyword score 可比较；vector/hybrid 尚未提升为 Facade 合同。

## Research tracer

```text
ingest_candidate
→ inspiration_research.intake.generator.generate_intake_card
→ intake_id 显式映射为 SQLite id
→ shared.storage.insert(ir_intake_cards)
→ ResearchIntakeResult
```

旧 `/intake-card` 委托同一 Facade。结果是 candidate，不是已审核知识。

## Packaging

业务实现通过 `git mv` 迁到 canonical `inspiration_research/` 并纳入 wheel。`Inspiration-Research/api.py` 只是 deprecated source-checkout launcher，不保存第二份路由或业务逻辑。主脚本、Docker、Compose 和测试均使用 canonical import。

## 验证边界

真实 SQLite 测试在全新子进程启动前设置唯一 `COGNITIVE_DATA_DIR`，证明 insert、FTS5、Facade 查询、Intake round-trip 与旧入口兼容，不 mock storage、FTS 或 generator。wheel smoke 在源码目录外验证 canonical package、IR API 与 Facade。

## 回滚

逆向迁移 package 和调用方，并恢复旧 API 实现即可回滚；不得删除已经写入的 IntakeCard 行。
