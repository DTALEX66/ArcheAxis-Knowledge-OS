# 🎯 AAOS-01 Q03：**挂载条件被证实 —— 以及一条版本警示**

## 1. 🎯 挂载条件：**取决于有没有 worker profile**

```rust
// crates/archeaxis-api/src/main.rs
221:         match archeaxis_application::executor::Executor::open_routes(
222:             std::path::Path::new(db_path),
223:             &profile.staging, &profile.python, &profile.script, &extra_refs,
228:         .await
230:             Ok(executor) => (
231:                 executor.store().clone(),
232:                 archeaxis_api::runtime::router(executor),      // ★ runtime 路由（含两张表）
233:             ),
234:             Err(_) => { eprintln!("failed to initialize execution workspace"); exit(1); }
238:     } else {
240:         match archeaxis_store_sqlite::writer::Store::open(std::path::Path::new(db_path)) {
241:             Ok(store) => (store.clone(), archeaxis_api::projections(store, false)),  // ★ 只有主表
246:     };
```

**而 `runtime/mod.rs` 把 projections **合并进自己**：**

```rust
// crates/archeaxis-api/src/runtime/mod.rs
34: let projections = crate::projections(executor.store().clone(), false);
88: .merge(projections)
```

**所以两张路由表是**包含关系**，不是并列关系**：

```
有 worker profile:
   runtime::router  =  runtime 表  +  merge(projections 表)      -> 两表都在
没有 worker profile:
   projections      =  projections 表                            -> 只有主表
```

## 2. 🎯 于是第 136 轮那条推断**成立，且更准确**

我第 136 轮写：

> 「挂载条件很可能是启动文档里有没有 `text_worker`」—— **并明确标为推断**。

**本轮读了组合处，它是事实。** 而且更准的表述是：

> **条件不是「有没有 `text_worker` 这个字段」，而是「能不能据它打开一个 executor」** ——
> **`open_routes` 成功 → runtime 路由；否则（含根本没有 profile）→ 只有 projections。**

**我的启动文档没声明 `text_worker`** ✓ → **走 `else`** ✓ → **只有主表** ✓ →
**`capabilities` / `machine/answers`（在 runtime 表）→ 404** ✓，**`evidence/anchors`（在主表）→ 200** ✓

**观测与源码逐条吻合。**

## 3. ⚠️ 但必须记一条**版本警示**

```
候选二进制 LastWriteTime:      2026-10-01 12:45:49

改到 runtime 路由或 main 组合处的提交：
  ef0104f8  2026-10-03  Close the real-multiformat loop: reachable routes, …
  b421ddee  2026-10-03  Fix AAOS co-learning persistence …
  574831dd  2026-10-02  R7 G2: classify vault members …
  6842d130  2026-10-02  R7 G2: store the vault link graph …
  ed47205c  2026-10-02  R7 G2: parse the Obsidian link graph …
  c3b86628  2026-10-02  R7 G4: a retest route that links to the failed task …
```

**二进制是 10-01 的，而改到这条路由的提交是 10-02 与 10-03 的** ——
**所以这个二进制**早于**那些改动** ✓

**含义**：

| 我本轮的实测 | 适用范围 |
| --- | --- |
| 启动契约（stdin JSON · v2 字面量 · actor 校验） | **该二进制** —— 我读的源码与之吻合，但**未逐版本核对** |
| 凭据模型（单头 · 常数时间 · origin 403） | 同上 |
| **路由集与挂载条件** | ⚠️ **源码是当前的**，而**二进制是 10-01 的** —— **两者可能有差异** |

**所以严格说：我验证了「一个 10-01 构建的行为，与当前源码一致」；
而「当前源码编译出的二进制会怎样」我**没有验证**。**

**这不削弱本轮结论**（挂载条件的源码证据是当前的、明确的），
**但它限定了「实测」二字能覆盖的范围。**

## 4. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「10-01 二进制与当前源码完全一致」 | **二进制早于三个相关提交** |
| 「声明 `text_worker` 后这两条路由一定可用」 | **未试** —— 那需要一份真实的 worker profile |

## 5. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（读 `main.rs` + `git log`）。
**未改任何仓库文件**；**Green 目录内未创建/修改/删除任何文件**；**未触碰官方 Green 的 `data/` 与资料库**。
