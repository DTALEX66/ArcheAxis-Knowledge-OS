# AAOS-01 §六 合并 · 可审查清单：`reject_reparse` 同名两实现（2026-10-05）

§六 要求「先列具体重复实现及消费者」。本清单只做这个，不做改动。

## 1. 两处实现与消费者

| | A：后端暂存器 | B：产品组装器 |
| --- | --- | --- |
| 文件 | `scripts/release/stage_backend_runtime.py` | `scripts/release/assemble_green_candidate.py` |
| 函数 | `reject_reparse(path)` | `_reject_reparse(path)` |
| 调用点 | 定义 :109；调用 :128（`validate_tree`）· :252 · :275 · :292 · :294 · :304 · :420 | 定义 :101；调用 :66 · :79 · :173 · :174 · :176 · :178 |
| 消费者 | 后端候选的分发暂存 | 绿色候选的组装 |

**两者互不调用，各自独立实现。**

## 2. 语义差异（第 149 轮实测，逐条）

| 检查项 | A 暂存器 | B 组装器 |
| --- | --- | --- |
| reparse / symlink | ✅（`S_ISLNK` 或 `st_file_attributes & 0x400`） | ✅（同） |
| **`PRIVATE_NAMES`** | ✅ **查** | ❌ **完全不查** |
| `.env*` 前缀 | ✅ 查 | ❌ 不查 |
| `..` 穿越 | ✅ 查 | ❌ 不查 |
| UNC `//` | ✅ 查 | ❌ 不查 |
| `e:` 盘符 | ✅ 查 | ❌ 不查 |
| `/.project-local/agents/` | ✅ 查 | ❌ 不查 |
| **递归范围** | **对 `runtime`/`workers`/`dep_source` 递归**（`validate_tree`） | **只浅层**（对 desktop/core/runtime/workers 各调一次） |
| 错误文本 | `protected staging path` / `linked staging path rejected` | `reparse point is not allowed in candidate input` |

**结论**：**同名，但检查项与范围都不同** —— A 明显更严，B 只保留了链接那一半。

## 3. 为什么这不是纯粹的风格问题

**同一套输入，A 拒绝、B 接受**（第 148/150 轮实测：`fastapi/.agents`、`litellm/proxy/auth` 被 A 拒；A 修好后两者都过）。
**因此「用哪个脚本」会改变产物是否可生成** —— 这是行为差异，不是重复劳动。

## 4. 收敛方案（**待评审，本轮不实施**）

1. **抽出一个共享模块**（例如 `scripts/release/_path_safety.py`），**唯一实现**下列分层：
   - `reject_links_along(path)` —— 只查链接（上游文件/包内部适用；**本轮已在 A 中新增**）
   - `reject_root_private_names(path)` —— 只查**根位置**的私有名/`.env`/越界（输入根适用）
   - `reject_staging_input(path)` —— 两者相加（对外入口，保持 A 现有语义）
2. **A 与 B 都改为调用共享模块**；B 获得 A 的额外检查（**这是行为变更，需要单独评审**，不能当作纯重构）。
3. **保留两处错误文本的现有字符串**（有测试断言：`tests/test_backend_runtime_safety.py` 断言「在任何文件系统访问之前拒绝」）。

## 5. 回滚点

两文件各自独立，任一改动都可单提交回退；`tests/test_backend_runtime_safety.py`（33 项）是现成的回归门。

## 6. 我**不**声称的

- **未改动任何代码** —— 本清单只是 §六 要求的「先列具体重复实现及消费者」。
- **未判定 B 的「不查私有名」是缺陷** —— 它可能是有意的（组装器只从已核验的输入组装）。
- **未确定收敛后的正确语义** —— 需要产品决定「谁该更严」。
