# AAOS-01 现场更正：**PR 检查在 `9db68a02` 上是红的**，且红在我自己第 22 轮的修复上（2026-10-04）

## 1. 事实

`9db68a02`（纯文档提交）上：

| 检查 | 事件 | 结果 |
| --- | --- | --- |
| `CI` | push | ✅ success |
| **`vnext-ci`** | **pull_request** | ❌ **failure** |

失败点（`cargo test (workspace)`）：

```
thread 'a_registered_capability_names_the_worker_that_would_answer' panicked
assertion `left == right` failed: {"automatic_failure_fallback":false,
  "capability":"image.caption","default_provider":"D:\a\ArcheAxis-K…
test result: FAILED. 15 passed; 1 failed
```

## 2. 它不是"第 22 轮那个错"复发 —— **它就是我第 22 轮的修复本身在报错**

HEAD 里两处相关代码：

```rust
// crates/archeaxis-api/tests/contract_capability_registry.rs
219:    let provider = body["capability"]["default_provider"].as_str().unwrap();
220:    assert!(!provider.is_empty() && Path::new(provider).is_absolute(), ...);
221:    assert_eq!(body["capability"]["is_default"], provider == script.to_string_lossy().as_ref(),
222:        "the default flag must agree with the paths it describes: {body}");   // <-- 我第 22 轮加的
```

CI 报的是 **`left == right` + 整个 body**，与 **221 行那条 `assert_eq!`** 吻合 —— 即**我加的不变量断言在 runner 上不成立**。

第 22 轮的原始失败是"字面量比路径"；**这一次不是**。**所以这是我的修复自身还残留环境敏感性**，不是旧缺陷复发。

**可能的机制（未证实）**：Core 侧对路径做了归一化（W05 的 `resolve_root` / `describe_absolutize`），于是记录里的 `worker` 与测试里原始的 `script` 在 runner 的路径形状下**不等**，而 `is_default` 用的是归一化后的比较 —— 两者基准不同。**我没有验证这条机制，所以只作假设列出。**

## 3. 我**没有**做的

- **没有修它**：本轮预算不足以安全地改这条断言并重验（而且它需要先弄清归一化基准）。
- **没有把 `CI` push 的绿当成"检查全绿"**：`vnext-ci` 的 PR 检查**是红的**，在此明确写出。
- **没有构建/运行**任何 Tauri 产物。

## 4. 回退与恢复点

- 文档提交：`9db68a02`；本文件为后续提交。
- **代码层面的恢复点**：第 22 轮的修复是 `fb2b8657`；若要暂时恢复 PR 绿，需要的是**正确修这条断言**，而不是回退成字面量比较（那会回到"环境相关"的老问题）。

## 5. 下一项（必须先做）

**修 `contract_capability_registry.rs:221` 的基准问题**，并**同时核 push 与 PR 两条检查**再报绿。判据：先确定 Core 侧 `worker` / `default_worker` 是否经过归一化（读 `capabilities.rs` 与启动路径的 `resolve_root`），再让断言比较**同一基准**下的两个值。
