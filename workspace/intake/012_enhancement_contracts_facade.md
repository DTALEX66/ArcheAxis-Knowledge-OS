# Enhancement and Contracts Facades

## Enhancement tracer

```text
enhance_artifact(markdown)
→ shared.auto_tagger.progressive_summarize
→ knowledge_base.cards.generator.generate_from_markdown
→ shared.content_quality.audit_markdown_quality
→ EnhancementArtifact(status="candidate")
```

该 Facade 只返回内存 candidate：不写 SQLite、不索引、不调用网络或 LLM。摘要、卡片和静态质量结果都不证明事实、OCR/ASR 或人工审核正确。

## Contracts boundary

`app.facades.contracts` 按对象身份导出当前 `app.schemas` 的八个运行时对象。它不 subclass、不复制模型、不生成 JSON Schema，也不声明与 `shared-contracts` 中同名 Schema 等价。

版本号、canonical schema、legacy adapter 和 SQLite 对象迁移属于 Phase 2。

## 测试

- 真实调用三个 Enhancement delegate；
- 比较除随机 `card_id` 外的现有 delegate 结果；
- 锁定 `candidate` 状态和 draft 卡片语义；
- 逐个验证 Contracts 导出对象身份；
- 禁止提前暴露 Phase 2 surface。

## 回滚

删除两个 Facade 模块、公共导出和对应测试即可；没有数据库或外部资源回滚步骤。
