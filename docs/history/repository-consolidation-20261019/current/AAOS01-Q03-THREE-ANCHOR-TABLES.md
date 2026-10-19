# AAOS-01 Q03 schema 核对：**三张锚点表**，前端建在 Python 那张上

## 1. 三张表

```
crates/archeaxis-store-sqlite/src/lib.rs:71    CREATE TABLE IF NOT EXISTS anchors           <- Rust Core
shared/knowledge_governance_migration.py:349  CREATE TABLE IF NOT EXISTS anchors_v2        <- 第三张
app/evidence/anchor.py:65                     CREATE TABLE IF NOT EXISTS evidence_anchors  <- Python 面
```

## 2. **前端建在 Python 那张表的形状上**

```python
# app/evidence/anchor.py:108
"SELECT raw_sha256, source_revision, locator_json FROM evidence_anchors WHERE anchor_id=?"
```

对照第 14 轮前端的要求：`anchor_id` + **`raw_sha256`** + `source_revision` + **`locator` 对象**。

**`raw_sha256` 与 `locator_json` 正是前端要的字段** —— 所以：

| | 表 | 关键列 |
| --- | --- | --- |
| **前端期望的形状** | `evidence_anchors`（Python） | `raw_sha256`、`locator_json` ✓ |
| **Rust Core 读的** | `anchors` | `s.sha256`、**`a.position`** ✗ |

**两者列名与语义都不同**（`locator_json` 是结构化定位，`position` 是不透明偏移）。

## 3. 因此 C 的真实形状**不是**"投影到 Core HTTP"那么简单

之前我（第 16 轮）说 C = "新写一个对着 Core HTTP 的投影层"。**本轮发现中间还缺一层**：

```
前端 --需要--> evidence_anchors 形状（raw_sha256 + locator）
Rust Core --提供--> anchors 形状（sha256 + position）
                    ↑ 这里存在真正的数据模型落差
```

**所以 C 的工作包含"数据模型映射"**，而不只是路径与字段改名：`position`（不透明偏移）

## 4. 对"单写者"的重新理解（第 16 轮的延伸）

第 16 轮我说"两个写者对同一个 DB"。**本轮要收窄措辞**：

- Python 栈维护 **`evidence_anchors`** + **`anchors_v2`**；
- Rust Core 维护 **`anchors`**；
- **它们是不同的表**，所以**不是同一行的并发写冲突**，而是**两套并行数据模型**；
- **而且它们是否在同一个数据库文件里，我没有核实** —— Rust Core 的库路径来自启动参数（argv），Python 的是 `shared.storage.DB_PATH`，**两者是否同一文件未查**。

**所以准确的说法是**：当前接线存在**两套并行数据模型**，且**是否共用同一文件未证实**。

## 5. 本轮**未**做

1. **未核** Python 的 `DB_PATH` 与 Rust Core 启动参数指向的是否同一文件（§4 最后一条）；
2. **未核** `anchors_v2` 的用途与归属；
3. **未核** `app/workspace/service.py` 是否写（连续第二轮未做）；
4. **仍未读完** `RuntimeClient.test.ts`（**连续第五轮**）—— 我把它降级为"低优先但持续欠账"，**不再每轮承诺**，改为**在其真正阻塞判断时才读**。

## 6. 下一轮

**核实 Python `DB_PATH` 与 Rust Core 库路径是否同一文件。** 这是"单写者"命题的最后一块砖：

- 若**同一文件** → 两套模型共库，问题严重，必须先统一；
- 若**不同文件** → 存在两套独立数据，问题变成"哪一套是 canonical"，**同样需要裁决**。

两种结果都指向同一个行动：**先定 canonical 数据模型，再谈传输层映射** —— 即包内说的"**共享合同先定归属**"。
