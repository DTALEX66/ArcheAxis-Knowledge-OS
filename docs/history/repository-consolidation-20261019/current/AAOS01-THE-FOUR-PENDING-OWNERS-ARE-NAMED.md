# 🎯 AAOS-01：**那 4 个 pending 是谁 —— 有名有姓**

## 1. 答案（来自 `migration-status` 的完整输出，6,337 字节，逐项列出）

```
item count: 10

  core.sqlite                  sqlite_core       applied   op=apply  applied=1
  fts.cards                    fts               pending   op=None   applied=None   <-- *
  fts.documents                fts               pending   op=None   applied=None   <-- *
  knowledge-governance.sqlite  sqlite_knowledge  applied   op=apply  applied=10
  research.sqlite              sqlite_research   applied   op=apply  applied=1
  sleep-loop.sqlite            sqlite_sleep      applied   op=apply  applied=2
  taskpack.sqlite              sqlite            applied   op=apply  applied=2
  vector.cards                 vector            pending   op=None   applied=None   <-- *
  vector.documents             vector            pending   op=None   applied=None   <-- *
  workspace.sqlite             sqlite_workspace  applied   op=apply  applied=2

state counts: {applied: 6, pending: 4}
```

## 2. 所以 `{applied: 6, pending: 4}` 的**确切实义**

| 项 | 内容 |
| --- | --- |
| **条目数** | **10** = 注册的 owner 数（`status()` 遍历 `registry.owners`） |
| **applied: 6** | 6 个 SQLite owner 各自报告其迁移已全部应用 |
| **pending: 4** | **`fts.cards` · `fts.documents` · `vector.cards` · `vector.documents`** |

**那 6 个 applied 的**，连同它们已应用的迁移数：

```
core.sqlite                  1
knowledge-governance.sqlite 10
research.sqlite              1
sleep-loop.sqlite            2
taskpack.sqlite              2
workspace.sqlite             2
```

## 3. 🎯 关键区别：它们**从未被应用过**，不是「陈旧」

4 个 pending 项的 `operation` 与 `applied_migrations` **都是 `None`** ——
**说明它们没有任何应用记录** ✓（对比其余 6 项都有 `op=apply` ✓）。

**所以准确的表述是：全文检索与向量索引这两类 owner，从未被迁移过。**

## 4. 我**不**判定这是不是缺陷（这次要格外谨慎）

**一个很可能的良性解释**：**FTS 与向量索引常常是**按需惰性创建**的** ——
在还没有内容要索引时，没有索引表、也没有迁移记录，是完全正常的。

**另一条观察**（只作记录，不作结论）：

| 事实 | 轮次 |
| --- | --- |
| 我已把 `sqlite-vec`（向量扩展）装进随包 runtime | 第 98 轮 |
| 而本轮这套环境里，`vector.*` 仍然 pending | 本轮 |

**这可能只是因为「没有内容、所以还不需要」** —— **我不据此断言向量支持不可用。**

## 5. 这条线索的**最终定性**

```
"applied: 6 / pending: 4"
   = 10 个注册 owner 的状态计数
   = 6 个 SQLite owner 已应用（core/knowledge/research/sleep/taskpack/workspace）
   + 4 个【从未应用】的 fts/vector 索引 owner
   -> 这是一条【完整、可解释】的读数，不是异常
```

**这条线索可以结案了** —— 它从第 115 轮的一个疑问，走到了有名有姓的答案。

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「fts/vector pending 是缺陷」 | **惰性创建是常见设计** —— 我没有反证 |
| 「向量检索不可用」 | **未测** —— pending 的只是迁移记录 |
| 「换一个数据根也一定是 6/4」 | 我只在这一次读数里见过 |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件 + 解析上轮已存盘的文件）。
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何东西**。

**注**：本轮我**没有**重新运行任何东西 —— **答案就在第 119 轮存盘的 `status-after.json` 里**，
我只是解析了它。**这符合我自己定的规则：先写文件，再解析文件。**
