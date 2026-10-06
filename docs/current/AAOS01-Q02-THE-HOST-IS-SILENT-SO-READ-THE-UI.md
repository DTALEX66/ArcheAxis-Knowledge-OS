historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**宿主是沉默的 —— 所以要读界面；并据此修正策略**

## 1. 本轮结果

```
"mode": "portable"
"child_distinct": 1
"non_webview_children": []
"host_stdout_lines": 0          // 【宿主一个字都没输出】
"host_stdout_tail": []
"non_webview_files": []
"host_alive": true
```

**设了 portable root 之后**：不派生子进程、不写文件、**也不输出任何东西**。

## 2. 这告诉了我一件有用的事

我此前一直丢弃宿主的 stdout/stderr，以为是漏掉了诊断信息。**本轮留下了它，结果是空的。**

**原因在源码里**：宿主把失败**内部记录**（`record_failure`），供**界面显示**：

```rust
// main.rs
801:  Err(error) => { record_failure(&startup_backend, &error); None }
// 前端 RecoveryShell 的文案表：
27:  retry: "本地核心重试失败，请检查安全诊断后重试。"
36:  retry: "正在重试本地核心…"
41:  const RECOVERY_MESSAGES: Record<RecoveryStatusDto["state"], string>
```

**所以失败原因**不在 stdout**，而在界面里** —— 而界面有一条现成的读取通道：**`recovery_log_tail`** ✓
（`workspace.ts:293` 就是它）。**我正好已经有 WebDriver 能读 DOM。**

## 3. 因此我修正策略

| 路线 | 实测结果 | 结论 |
| --- | --- | --- |
| **默认模式**（不设 portable root） | ✅ **派生了 `python.exe -m app.runtime_entrypoint migrate`**（第 84 轮） | **可行** |
| 默认模式下的数据安全 | ✅ 真实库**哈希不变**（第 86 轮） | **已证安全** |
| **portable 模式**（设 `ARCHEAXIS_PORTABLE_ROOT`） | ❌ 既不派生、也不写、也不输出 | **暂不可行** |

**所以我不再追 portable 路线** —— 那是我为了「避开真实产品目录」自己想出来的绕道；
**而默认路线本来就能走通，而且已经用哈希证明它不动那个数据库。**

## 4. 下一轮（修正后的计划）

走**默认模式**，同时做三件事：

```
① 启动前 / 后对 archeaxis.sqlite 取哈希        // 安全护栏，每轮都做
② 30 毫秒轮询子进程命令行                    // 看 migrate 之后是否出现 core
③ 用 WebDriver 读界面的 recovery 状态与日志   // 失败原因在那里，不在 stdout
```

**目标**：确认后端是否从 `migrate` 走到 `core`、readiness 是否达成 —— **那才是 Q02 的交付物**。

## 5. 本轮未做

1. **未**改任何仓库文件；**未**触碰官方 Green 的 `data/` 与资料库；
2. **未**删除任何东西；
3. **未**走默认模式重跑（下一轮）。
