# AXW-DATA-403 — 旧单库迁移设计（cognitive_os.sqlite → 四资产域布局）

> 状态：设计 v1（2026-08-15）。实现跟随 AXW-DATA-401 Workspace Manifest 落地后开始。
> 原则（任务包 §13）：不直接重命名文件造成历史数据丢失；备份 → 迁移 → 完整性 → 回滚回读。

## 1. 现状

- SQLite 默认 `data/cognitive_os.sqlite`（旧单库语义，P1-1）
- 备份 kind、volume id 等仍保留旧命名（兼容读取保留）
- 新工作区布局：四资产域 + Ledger/State DB

## 2. 迁移目标

```text
旧：data/cognitive_os.sqlite（单库，含知识/证据/学习/AI 资产表）
新：
  <Workspace>/evidence-ledger/ledger.sqlite       事务真相源（Claim/Evidence/版本）
  <Workspace>/source-archive/                     原始资料（原件只读 + 哈希登记）
  <Workspace>/human-learning-vault/               开放文件（Markdown/Canvas）
  <Workspace>/ai-asset-vault/                     memory/rule/skill（审阅层）
```

## 3. 迁移流程（fail-safe 顺序）

1. **一致性备份**：`VACUUM INTO '<backup>/cognitive_os.pre-<ver>.sqlite'`（SQLite 原子备份）
   ——失败即中止（任务包 §18 暂停条件：迁移无法产生一致性备份）
2. **迁移 dry-run**：只读连接旧库 → 生成迁移计划（表清单/行数/预计目标）→ 校验目标目录可写
3. **快照迁移**：事务内逐表复制（INSERT INTO ... SELECT）→ 完整性检查（行数对比 + FK 检查）
4. **迁移后回读**：新库打开 → 关键表抽样断言 → 生成迁移 manifest（源/目标/行数/校验和）
5. **旧库保留**：旧文件改名 `cognitive_os.sqlite.migrated-<ts>`（不删除）——兼容读取路径仍在
6. **回滚**：如果新库验证失败 → 恢复备份候选（VACUUM INTO 的备份直接可打开）
   ——`restore-activate` 语义沿用 runtime_entrypoint 现有 restore-candidate 链

## 4. 数据语义映射

| 旧表/kind | 新目标 | 备注 |
|---|---|---|
| 知识/证据类 | evidence-ledger/ledger.sqlite | Claim/EvidenceBundle/版本语义 |
| 原始文件引用 | source-archive | 原件不复制——引用 + 哈希登记 |
| 学习资产（Markdown 等） | human-learning-vault | 开放文件为主，事务状态由 ledger 管 |
| AI 资产 | ai-asset-vault | 未经证据绑定 + 人工批准不得生效 |

## 5. 兼容与回退

- 新布局下旧单库仍可读（只读兼容路径，任务包 P1-1："兼容旧数据库可以保留"）
- 显示/新写入一律走新语义（不直接改名文件）
- 回滚：备份候选恢复 + 旧程序目录保留（§13.3 语义）

## 6. 验收映射（任务包 §19 #15）

- [ ] 旧库升级：备份 → 迁移 → 回读全链测试（含旧数据完整性断言）
- [ ] 回滚：恢复备份候选后旧库可打开、数据一致
- [ ] 长路径：迁移目标含空格/中文/长路径（>240 字符）验证
