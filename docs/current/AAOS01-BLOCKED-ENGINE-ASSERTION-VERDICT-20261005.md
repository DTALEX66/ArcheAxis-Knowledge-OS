# AAOS-01 未决阻塞：CI 未产出引擎断言结论（2026-10-05，R249）

## 阻塞本身

为判定「`xlsx`/`pptx` 失败源于**陈旧候选**还是**流水线漏装**」，
在 `desktop-build` 增设了引擎断言（`0b6865ff`），随后多次尝试取得其结论，**均未成功**：

| 尝试 | 结果 |
| --- | --- |
| `0b6865ff` 的原始运行 `37262571828` | **被我自己后续推送取消** |
| `gh run rerun 37262571828`（第 1 次） | 被后续推送取消 |
| `gh run rerun 37262571828`（第 2 次） | **GitHub 拒绝**：`This workflow run cannot be retried` |
| `3a0fef82` 的运行 `37262727101` | **`desktop-build` 被 GatePlan 跳过**（该提交只改 `tests/fixtures/`） |
| `b0a7c1e3` 的运行 `37262959180` | **`desktop-build` 停滞**：连 `Prepare the installed Python runtime` 都仍为 `pending`，连续约 8 轮未推进 |

## 关键判别条件

**只有改动 `.github/workflows/`、`src-tauri/`、`desktop/`、`crates/` 等路径的提交会触发 `desktop-build`。**
只改 `tests/` 或 `docs/` 的提交**不会**，其运行里该 job 为 `skipped` —— **从这类运行里读断言结论是徒劳的**（我为此浪费过一轮）。

## 结论与后续

**该判定的结论目前不可得**，原因在 CI 侧（运行被取消 / 被跳过 / 停滞），**不在本机**。
**本机因此无法区分**：
- **陈旧候选**：锁（10-01）已含 `openpyxl`/`python-pptx`，而所测候选 `runtime/` 为 **07-29**；
- **流水线漏装**：`prepare_bundle` 的安装步骤未把锁定依赖落盘。

**倾向性证据（非结论）**：候选 `runtime/` 早于锁两个月 ⇒ **陈旧候选更可能**；
且同一候选里已发现过**陈旧嵌套解释器**残留（同类问题第三次）。

**下一步（不依赖 CI）**：**在本机用 `uv` 做一次全新暂存** —— 但**本机未找到 `uv`**
（已查：`~/.local/bin`、`~/.cargo/bin`、`~/AppData/Roaming/uv`、`~/scoop/shims`、外部共享库 scoop/shims、CI venv、工作树 venv，以及作为 Python 模块），
**故该判别同样受阻于本机工具缺失**。

**因此正确的处置是把它作为明确未决项交接，而不是继续等待或反复重试。**
