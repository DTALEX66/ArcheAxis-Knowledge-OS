# AAOS-01 Q12（B 波次轻量扩展）：**7 个真实新样本 + 一处我自己的误标**

## 0. 先读任务书，不凭记忆

```
| Q12 | B 波次轻量扩展 | Q06、Q11 | 按收益扩展结构文本、EPUB、EML 等 | 不拖慢主闭环，不伪造新增数量 |
```

**两个约束**：「按收益扩展」、**「不伪造新增数量」**。这一条决定了本轮的两半。

## 1. 新增的 7 个真实样本（矩阵 17 → 24）

全部是**仓库内已跟踪的真实文件**，无一合成：

| 样本 | 产物 format | 引擎 | 结果 | 原件哈希 |
| --- | --- | --- | --- | --- |
| `sample.srt` | **`unknown`** | **`markitdown`** | carried | ✅ |
| `overlap.srt` | **`unknown`** | **`markitdown`** | carried | ✅ |
| `sample.vtt` | **`unknown`** | **`markitdown`** | carried | ✅ |
| `defaults.yaml` | **`unknown`** | **`passthrough`** | carried | ✅ |
| `capability-map.json` | **`unknown`** | **`passthrough`** | carried | ✅ |
| `broken-edge.canvas` | — | — | **422** | — |
| `zh-group.canvas` | — | — | **422** | — |

## 2. 三条值得记下的结论

1. **字幕（srt/vtt）确实经由引擎 `markitdown` 处理**，但 **format 仍报 `unknown`** ——
   **产品承运了它们，却不声称「认识」它们。** 与 `.apkg` 同一种诚实。
2. **YAML / JSON 走的是 `passthrough`**，证据原话是 **「content carried, not parsed」** ——
   **即：承运，但不解析。** 我没有把它写成「支持结构化数据」。
3. **两个 canvas 被拒（422）**，原因文本是 **`No engine could convert canvas file …: json-canvas…`** ——
   **是引擎试过但转换失败**，不是引擎缺失。

## 3. 我**自己**的一处误标（本轮抓出并修）

我的探针里，`classify()` 原本这样写：

```python
if "requires" in lowered or "install" in lowered or "no engine could convert" in lowered:
    return ENGINE_MISSING, text[:240]
```

**我把「引擎跑了但转不动」和「引擎没装」归成了同一个标签。**
于是 **一个损坏的 canvas 被我的探针报成了「缺依赖」** —— **这是对产品的错误描述。**

改为：

```python
if "no engine could convert" in lowered:
    return CONVERSION_FAILED, text[:240]   # 引擎在，转不动
if "requires" in lowered or "install" in lowered:
    return ENGINE_MISSING, text[:240]      # 引擎不在
```

**新增标签 `conversion_failed`**，并更新了测试的允许集合。

**这条比新增样本更重要**：我的标签一度**把「产品转不动这个文件」说成「产品缺依赖」**。

（核查：此前那几条 `engine_missing` —— png/wav/mp4 —— 的文本是「requires Tesseract」一类，**标签仍正确**，
**所以已经提交的数据没有错**；错的只是本轮新出现的 canvas 那条路径。）

## 4. EPUB / EML：**没有样本，所以不做声称**

任务书点名 EPUB 与 EML。我**查遍了仓库**：

```
git ls-files | Select-String '\.(epub|eml|mobi|msg)$'  ->  NONE
```

**没有任何真实的 EPUB 或 EML 样本。**

**所以本轮对这两种格式不作任何声称** —— 这**正是**任务书那句「**不伪造新增数量**」的要求。
**我不会为了凑数去合成一个 EPUB，然后「测」它。**

## 5. 结果

```
architecture guard passed
9 passed in 7.34s
```

## 6. 本轮未做

1. **未**合成 EPUB/EML 样本（**有意为之**，见 §4）；
2. **未**改任何实现文件；**未**触碰官方 Green 与资料库。
