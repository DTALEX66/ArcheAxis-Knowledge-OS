# AAOS-01 Q09：**握手把 `capabilities` 写死成空数组**（缺口已定位）

## 1. 决定性证据（源码 + 实测两侧）

```python
# app/workspace/system.py:96-109
def system_handshake() -> dict[str, object]:
    """Product identity + runtime facts for the desktop shell (launch gate)."""
    return {
        "product_id": PRODUCT_ID,
        ...
        "workspace_id": _workspace_id(),
        "capabilities": [],          # <-- 字面量，不是计算值
        "migration_state": _migration_state(),
    }
```

实测（对着运行中的产品）：

```json
{ "handshake_capabilities": [] }
```

**所以不是"尚未接线"，而是"写死成空"。**

## 2. 这让 Q09 的缺口变得精确

| 一侧 | 事实 |
| --- | --- |
| **Rust Core** | **有**能力注册表：`crates/archeaxis-api/src/capabilities.rs`（含 `CAP-*` 与 health 字段） |
| **BFF 握手** | `system.py:107` **硬编码 `[]`** |

> **前端因此永远收到一份空的能力目录，与 Core 实际知道什么无关。**

这正是包内 Q09「**完整能力目录**」所指的缺口，而且它**不是靠推断得出，是有源码行号与实测值两侧支撑的**。

## 3. 搜索：**我两次猜错了请求形状，如实记下**

BFF 的搜索路由是 `POST /api/vault/search`（`router.py:483`）。我试了两种请求体，**都 422**：

```
1) {"query": "Why this matters"}
   -> 422  loc:["body","root"]  msg:"Field required"

2) "Why this matters"          （裸值）
   -> 422  loc:["body"]  msg:"Input should be a valid dictionary or object to extract fields from"
```

**这两次是我的用法错，不是产品错。** 错误信息确实给了线索（期望一个对象、且提到字段 `root`），
**但正确的请求形状我这一轮没有找到**。

**所以：搜索能力仍未测得。我不把它写成"可用"或"不可用"。**

（这也是本会话的老模式：**先猜形状再验证，代价是往返**。更好的做法是先读 `router.py:483` 附近的请求模型定义。）

## 4. 本轮**未**做

1. **未改任何实现文件**（`capabilities: []` 是发现，不是我这轮去改的）；
2. **未**读 `/api/vault/search` 的请求模型定义（下一轮第一件事）；
3. **未**为搜索写探针（形状未知，写不了有意义的断言）；
4. 官方 Green 与官方资料库**零触碰**。

## 5. 下一轮

1. **读 `router.py:483` 附近的请求模型**，确定搜索的正确请求形状，再取真实搜索证据；
2. 把 **`capabilities` 硬编码为空** 这条固化成**探针断言**（断言它当前是 `[]`），
   这样一旦有人把它接上真实注册表，**测试会失败并提醒更新** —— 与冷启动那条同样的做法。
