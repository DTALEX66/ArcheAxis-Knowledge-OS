# AAOS-01：**写入可复现；重启测试失败；并露出一条迁移新事实**

## 1. ✅ 写入可复现

第二次独立运行得到同样的 **200** 与同样的 `review_evidence` 结果 ✓

```
node_id: persist-node-1
action:  review_evidence
state:   human M0 / M0 SEEN, machine NONE, evidence unverified
reason:  evidence is not current - outranks mastery
```

## 2. ⚠️ 但我的重启测试**没生效**（`restarted: false`）

| 步骤 | 结果 |
| --- | --- |
| 首次启动 | ✅ `first_start: true` |
| 写入 | ✅ 200 |
| kill + 重启 | ❌ **`restarted: false`** |

**所以「写入在冷启动后仍然存在」这一点，我**没有验证**。**

**我不把它说成通过，也不说成失败 —— 它是**未测**。**
（很可能是端口仍被占用、或第二次启动没在时限内就绪 —— 但**我没有查证**，所以只记现象。）

## 3. ✅ 「learning 为空」是**设计使然**，不是失败

```
GET /api/v1/workspace/api/learning  ->  200
{"schema_version": "v1", "items": []}
```

**这与第 114 轮的发现一致**：tick 返回 `action: review_evidence`，
`reason: evidence is not current - outranks mastery` —— **它故意不推断、也不落掌握度。**

**所以「learning 里没有条目」正是它该有的样子。**

**这也修正我第 114 轮的一处措辞**：我当时写「读写闭环完整了」。
更准确的说法是：**「一次写入被接受并得到应答」** —— 而**不是**「数据已落盘」✓

## 4. 🎯 新事实：迁移**没有全部应用**

```
GET /api/v1/workspace/api/status  ->  200
  release:    {status: unreleased, public: false, channel: development, version: 0.6.14}
  migrations: {applied: 6, pending: 4}
  components: {api: available, ...}
```

| 字段 | 值 |
| --- | --- |
| `migrations.applied` | **6** |
| `migrations.pending` | **4** |
| 合计 | **10** |

**这是产品自己报告的迁移状态** —— **而它说明迁移并未完成。**

**这与第 99 轮的手工迁移记录（当时多 owner 全部 `applied`）不矛盾** ——
**两次的库不同**：第 99 轮是我手工建的新库，这次是另一条路径下的库。
**但「applied: 6 / pending: 4」本身值得记下来** —— 它是一个具体的、可追的缺口。

**我不判定「是缺陷还是正常中间态」** —— 只报它。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「写入已持久化」 | **重启测试失败，未验证** |
| 「迁移有缺陷」 | **只是一个状态读数**，我不判定成因 |
| 「learning 为空说明写失败」 | **恰恰相反** —— 那是设计使然 |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑两次 migrate + core、写一次、读三处 | `.project-local/runs/persistence/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**；只 kill 自己起的句柄。
