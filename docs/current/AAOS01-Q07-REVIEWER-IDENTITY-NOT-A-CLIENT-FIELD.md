# AAOS-01 Q07：冒充真人审阅者**在结构上就不可能**

Q07 要的是候选由**人**处置。包内明令「**不伪造真人证据**」。本轮先查授权路径，
得到的答案比预期更好。

## 1. 审批路径（两层守卫）

```python
# app/workspace/router.py:950-956
@router.post("/api/runtime/approve", dependencies=[Depends(_require_desktop_write_request)])
def approve_runtime_candidate(command: RuntimeApprovalCommand, request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(
        lambda: service.approve_runtime_title(
            command_id=command.command_id, title=command.title, db_path=DB_PATH
        )
    )
```

| 层 | 内容 | 依据 |
|---|---|---|
| 写凭据 | 需要**桌面启动令牌**；仅当**未配置**凭据时 TestClient / browser-smoke 才被豁免 | router.py:99-113 |
| 本机调用 | `_local_principal(request)` | 同上 |

## 2. 决定性的一行

```python
# app/workspace/router.py:255
"""Caller intent; reviewer identity is deliberately not a client field."""
```

**「审阅者身份」故意不作为客户端字段。**
而审批请求体 `RuntimeApprovalCommand` 只带 `command_id` 与 `title` —— **没有任何「我是谁」的字段**。

## 3. 所以这是**结构性**的，不是政策性的

| 通常做法 | 这里 |
|---|---|
| 客户端传 `approved_by`，服务端信任 | **不接受该字段**：调用方无权声明自己是谁 |
| 靠政策禁止冒充 | **接口层面就没有可冒充的入口** |

> **我不能通过 API 把自己说成人类审阅者 —— 不是因为我守规矩，而是因为接口没给我这个入口。**

**这比「政策要求」强得多，也正是包内「不伪造真人证据」想要的形态。**

## 4. 因此本轮**没有**尝试审批（两层理由）

1. 写操作需要**桌面启动令牌**，而我的现场是**直接起 uvicorn**（无令牌）；
2. 更重要：**即便有令牌，我也不会以人类身份签署** —— 而本轮查明**接口也不允许我这样做**。

**Q07 的「真人处置」需要**真人在真实桌面环境里做。这不是我能代劳的，也不该由我代劳。**

## 5. 本轮未做

1. **未**实际调用审批（理由见上）；
2. **未**读 `service.approve_runtime_title` 内部（谁被记为审阅者、从哪来）；
3. **未**取「版本冲突」证据（Q07 另一项要求）；
4. **未改任何实现文件**；官方 Green 与资料库**零触碰**。

## 6. 下一轮

1. 读 `service.approve_runtime_title`：查明审阅者身份**从哪来**（令牌？环境？固定值？）；
2. 取机器候选侧**可测**的部分：`GET /workspace/api/runtime/candidates` 的真实输出；
3. **明确登记**：真人处置一环需 Owner 或真人在真实桌面执行，**我不代签**。
