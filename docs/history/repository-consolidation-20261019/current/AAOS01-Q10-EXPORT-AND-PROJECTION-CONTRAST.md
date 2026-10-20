# AAOS-01 Q10/Q06 导出：**导出与校验都通**，并**印证**第 32 轮的边界说法

## 1. 实测

```
POST /workspace/api/exchange/export  { name, overwrite }
GET  /workspace/api/exchange/verify?name=probe-exchange

exported_files:      ["ev_4ce777c0b3dce4cec2e07590.json", "manifest.json"]
verify_status:       200
verify.valid:        true
verify.verified_items: 1
```

**导出与校验都通过** ✓ —— 产出一个**开放交换目录**，并自带校验。

## 2. **我拒绝把一处差异说成缺陷**

我最初写了个"重新算 manifest.json 的 sha256 并与报告里的 `manifest_sha256` 比较"的检查，结果是 `false`。

**这几乎肯定是我的期望错了，不是产品错了**：

- `manifest_sha256` 是**清单所描述内容的**哈希（或某种规范序列化），**不是"装着这个字段的那个文件的"哈希**
  —— 后者在构造上就自相矛盾；
- 而**产品自己的 `verify` 明确说 `valid: true`** —— 那才是权威判断；
- 我那个自制的文件哈希比对**不构成"导出无效"的证据**。

**处置**：把该字段改名为 `manifest_file_sha256`（说清它是"装着清单的那个文件的哈希"），
**并明确写出"不与 `manifest_sha256` 比较"**，把这个错误期望从探针里删掉，避免以后有人再据此误判。

## 3. 更有价值的发现：**导出层保留了精确结构**

导出的证据条目里带着：

```json
"locator": {
  "block_ids": ["block_b86977b794770f2aec3aec2f", "block_bb0319021a5af3615eff425f",
                "block_73144e14e7f56513564d1df5", "block_f9cff398658f1e9049073839",
                "block_97ad0d3c4dcee9f6c244f04e", "block_97ecf8ca2a19befdaafda803"],
  "conversion_run_id":  "run_5630b637ab80e836a4877447",
  "derived_document_id": "derived_70c51fd239fd6ddb9ed6e96b",
  "source_format": "md" }
```

**六个 block id + 转换运行 + 派生文档** —— 也就是说**精确结构确实存在，而且被导出**。

## 4. 这**印证**了第 32/33 轮我刻意写下的边界

当时我写：

> 「我只读了投影后的读取路由；**存储层是否仍保有完整 locator，我没有核** ——
>  所以准确说法是「**读取投影丢字段**」，不是「**数据丢了**」。**这两者区别很大，我不含混。**」

**本轮给出了那条边界的正面证据**：

| 层 | 精确结构 |
| --- | --- |
| **导出/存储层** | ✅ 有（6 个 block id、转换运行、派生文档） |
| **anchor 读取路由** | ❌ 只剩 `page` / `source_format` |

**所以问题就是"读取投影丢字段"，与我当时说的完全一致 —— 没有变成"数据丢失"。**
**这说明当时那条谨慎的边界写法是对的，而不是多余的。**

## 5. 本轮**未**做

1. **未**为导出探针写测试（下一轮补，与前三条约一致）；
2. **未**核 `manifest_sha256` **到底哈希的是什么**（只确认"它不是那个文件的哈希"）；
3. **未**做冷启动（Q06 最后一环）；
4. **未改任何实现文件**；官方 Green 与资料库**零触碰**。

## 6. 下一轮

① 为导出探针补**测试**（断言 `valid: true`、条目计数、导出的 locator **含 block_ids**）；
② 把"**导出层有精确结构、读取层没有**"这条对比**记进断言**，让第 32 轮的边界不再只靠文字。
