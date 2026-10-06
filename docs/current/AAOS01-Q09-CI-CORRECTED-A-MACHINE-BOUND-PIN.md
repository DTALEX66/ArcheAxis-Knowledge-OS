# AAOS-01 Q09：**CI 纠正了我一次"把本机行为当成产品事实"的钉定**

## 1. 发生了什么

我上一条提交里有一条测试：

```python
def test_search_is_not_reported_as_working(receipt):
    """Measured on 2026-10-04: one attempt failed with a server error, the other timed out."""
    statuses = [attempt.get("status") for attempt in receipt["searches"]]
    assert 200 not in statuses
```

依据是**我这台机器上的实测**：`temp-work` → **500**，`fixture-vault` → **超时**。

**CI 直接把它顶回来了：**

```
FAILED tests/test_capability_and_search_probe.py::test_search_is_not_reported_as_working
  assert 200 not in [200, 200]
```

**在 CI 上，两次搜索都返回 200。**

## 2. 结论：**"搜索不工作"是我的机器特征，不是产品事实**

| 环境 | 结果 |
| --- | --- |
| **本机** | `temp-work` → 500 · `fixture-vault` → 超时 |
| **CI** | **两次都是 200** |

**所以搜索在 CI 上是可用的**；本机不应答的原因（我给的那个 root 不被接受？环境差异？）**我没有查明**。

## 3. 一次非常干净的对照：**两种钉定，一存一废**

同一条提交里有两处钉定，命运不同：

| 钉定 | 依据 | 结果 |
| --- | --- | --- |
| **能力目录是空数组** | **源码里的字面量**（`system.py:107`） | ✅ **CI 通过** —— 与机器无关 |
| **搜索不工作** | **一台机器的行为** | ❌ **CI 失败** —— 另一台机器是 200 |

> **钉定"来自源码的事实"是对的；钉定"来自一次运行的行为"是错的。**
> 这条对照比任何解释都清楚。

## 4. 修法

去掉那条断言，换成**规则性**断言：

```python
def test_no_claim_is_made_about_whether_search_works(receipt):
    """Deliberately does not pin an outcome, because the outcome is machine-dependent."""
    for attempt in receipt["searches"]:
        assert "status" in attempt
```

并把这次经历**写进 docstring**，让后人知道：**同一条测试曾把本机失败当产品事实，被 CI 正确驳回。**

**结果**：6 passed，26 秒（此前 125 秒，因为我同时把搜索超时从 60 秒降到 10 秒 —— 观察不变，代价大降）。

## 5. 我的教训（诚实归因）

我确实在 docstring 里写了"Measured on 2026-10-04"，**看起来像是限定了条件** ——
**但断言本身仍然写成了一条要求**。**措辞谨慎不能替代断言设计**：

> 若一个观察**依赖环境**，它就该被**记录**，而不是被**断言**。

## 6. 本轮**未**做

1. **未查明**本机搜索为何 500 / 超时（下一轮可查：读 `VaultRootRequest` 对 root 的约束）；
2. **未改任何实现文件**；
3. 官方 Green 与官方资料库**零触碰**。
