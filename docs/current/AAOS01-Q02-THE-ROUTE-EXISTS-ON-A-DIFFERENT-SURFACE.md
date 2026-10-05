historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**路由存在，但不在我启动的那个 API 面上**

## 1. 第 104 轮的 404 现在解释清楚了

grep 结果（`crates/` 下的 `.rs`）：

```
"/api/v1/machine/answers"           出现在 machine_answer.rs 的多处（含测试）
:54:    .route("/api/v1/machine/answers", post(machine_answer))   // 注册【存在】
```

**但我的实时 Core 对它返回 404** —— 而**同一个 Core** 对 `/api/v1/capabilities/` 返回 200。

**所以不是路径写错，而是「我启动的实例挂载的是另一个路由表」。**

旁证：grep 里存在**多个** router 构造函数：

```
:33:   pub fn router(executor: Executor) -> Router
:48:   pub fn router(state: Store) -> Router
:107:  pub fn app(db_path: &str) -> Result<Router, StoreError>
```

## 2. 因此存在至少两个 API 面

| # | 面 | 我是否跑过 |
| --- | --- | --- |
| 1 | 提供 `/api/v1/capabilities/` 的那个 | ✅ **本轮与第 101/104 轮都跑的是它** |
| 2 | 提供 `/api/v1/machine/answers` 的那个 | ❌ **没跑过** |

**而第 104 轮我读到的 actor 校验（400/403）与 `x-archeaxis-actor` 处理也在面 2 那一侧。**

**所以第 104 轮我标「未测」是对的 —— 现在我明白了原因：不是路径错，是面不对。**

## 3. 一个我自己的小失误（记录在案）

我那条 PowerShell 命令里对路径做子串截取时**偏移写错了**，输出里的文件名被切得不对
（例如显示成 `hine_answer.rs`）。**内容可信，路径显示不可信。**
正确做法是用 grep 工具而不是拼字符串截路径 —— 我已经改用 grep 工具。

## 4. 下一轮（具体）

**只读地确认 Core 进程实际挂载的是哪个 router** —— 即 `app/runtime_entrypoint.py` 的 `core` 路径
最终构造/启动的是哪一个（哪个 crate、哪个 `router`），然后**对着那个面**重跑权限测试。

**目标**：真正测到「机器主体不得记录人工评审」这条契约 —— 要么通过，要么失败，**不再停留在「未测」。**

## 5. Q02 现状（不变）

| 验收要素 | 状态 |
| --- | --- |
| 宿主启动 | ✅ 第 102 轮 |
| 只读桥接 | ✅ 第 103 轮 |
| **权限 / actor 合同** | ⚠️ **仍开放** —— 但**原因已查明**：面选错了 |
| 读写闭环 | ⏳ 未涉及 |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep 源码）。
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何东西**。
