# AAOS-01 Q06：**精确定位能被写入，却在读回时被丢掉**（真实发现）

## 1. 实测（对着运行中的产品，真实文件）

样本：`.../obsidian-vault/notes/index.md`（734 B，sha256 `76fc557e…`）。

```json
{ "locator_sent":      { "block": "notes/index.md#Why this matters",
                        "char_region": [252, 268], "page": 1, "source_format": "md" },
  "anchor_status":     200,
  "anchor_response":   { "anchor_id": "ev_47389e…", "locator": <**完整回显**> },

  "readback_status":   200,
  "readback":          { "anchor_id": "ev_47389e…",
                        "locator": { "page": 1, "source_format": "md" },   <-- 只剩两项
                        "raw_sha256": "76fc557e…", "source_revision": "1" },

  "locator_round_tripped": false }
```

## 2. 两件都对的事实

- **我给的定位是准确的**：`phrase_found_at: 252`、`char_region: [252, 268]`、`phrase_actually_there: true`
  （该字符区间确实落在真实短语 `Why this matters` 上）；
- **写入侧接受并回显了完整 locator**（创建响应里四项都在）。

## 3. **问题**：读回时 `char_region` 与 `block` **被丢掉**

读回只剩 `{page, source_format}`。而源码正是如此：

```python
# app/workspace/router.py:395-403  _product_anchor_locator(...)
page = locator.get("page")
source_format = locator.get("source_format")
# ... 只投影这两项
```

**所以这不是存储失败，是"投影"按设计只取两项** —— 但客观效果是：

> **系统接受了一个精确、可解释的定位，却不把它还回来。**

## 4. 为什么这值得记下来

包内 Q06 明确要求每种格式具备「**准确可解释定位**」。**当前读路径给不出这个定位。**

而且项目**自己**在 `packages/contracts/v1/loss-receipt.schema.json` 的描述里写着：

> "**Unknown fields must never be silently dropped.**"

这里被丢掉的**不是未知字段，是已知且已接受的字段**。**对照之下更值得记。**

## 5. 我没有核实的（边界）

1. **我只读了"投影后的读取路由"**（`GET /workspace/api/evidence/anchor/{id}`）；
   **存储层是否仍保有完整 locator，我没有核** —— 所以准确说法是「**读取投影丢字段**」，
   而不是「数据丢了」。**这两者区别很大，我不含混。**
2. **未**核 `char_region` 是否为该路由的**受支持字段**（也可能它本就不是合同字段，是我的用法超出约定）；
   **这条同样没查**。

## 6. 本轮**未**做

1. **未改任何实现文件**（本轮是取证据，不是修）；
2. **未**做损失回执（`loss-receipt.schema.json` 要求的 engine/engine_version/params/loss_note/coverage）——
   本轮只做到"定位"这一环；
3. 官方 Green 与官方资料库**零触碰**。

## 7. 下一轮

把这条固化成**探针断言**（与握手、格式那两条同样的做法），断言：
- 写入侧接受精确 locator；
- **读回侧当前只剩 `page`/`source_format`** —— 把"位置读不回"这件事**记进门禁**，而不是留在我的笔记里。

然后再去取**损失回执**那一环的证据。
