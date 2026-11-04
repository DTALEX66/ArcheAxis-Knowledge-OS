# S01 剩余 `runs/` 形状条目：只读决策表与迁移草案（2026-11-04）

状态：**只读决策文档，未移动、未删除任何文件**。本轮只做现场测量、逐项分类与迁移草案，供 Owner 或后继有精确授权时执行。

## 1. 依据

- 活动指针 `execution_control.owner_full_authorization_20261103.authorized` 第 2 条只覆盖 S01 附录 B/C（87→30 的登记/冻结/scratch 归档），**不包含**迁移剩余 29 个 `runs/` 条目，也没有 `bulk_delete` 授权。
- 本会话提示词 P1 明确要求：先读基线并逐项确认引用与消费者；迁移需 MANIFEST 且更新被引用路径；风险高时只出只读决策表与脚本草案，不动文件。
- `runs/` 契约（`tests/workflow/test_workspace_layout_contract.py` 与 run 分配器）：`runs/<sha256(checkout root)[:10]>/<run_id>/`。剩余条目全是旧命名/失效身份的**根级 run 目录**，不符合该形状。

## 2. 现场测量（2026-11-04，只读）

- 报告：`.project-local/runs/be268a2d33/s01-runs-survey-20261104/artifacts/storage.json`
- 决策表：`.project-local/runs/be268a2d33/s01-runs-survey-20261104/artifacts/decision-table.json`（schema `aaos.layout-decision-table/v1`）
- `storage_report.py` 退出码 1 是它表达 `REVIEW_REQUIRED` 的方式，不是测量失败；`measurement_status=PARTIAL`、`deletion_authorized=false` 保持原样。
- `OUT-OF-LAYOUT` 共 **31** 项：`EMPTY` 1、`RUNS_LAYOUT` 29、`UNREADABLE` 1；合计 **519,300,111 B**（约 495 MiB）。
- **31 项的 `referenced` 全为 true（`reference_path: true`，即被仓库内文件按路径引用）**。这一条决定迁移成本：移动任何一项都必须同步更新引用，不能先搬后查。
- 体积前三：`stitch-research-stage-20261022`（4,834 文件 / 262,696,865 B）、`stitch-shell-node-20261022`（2,549 文件 / 140,450,170 B）、`installed-av-04b3aa2f`（654 文件 / 96,811,294 B）。其余条目多在 KB–MB 级。
- ACL 条目：`fulltest-final-20260913` 读取抛 `PermissionError`（26 个受保护嵌套 `.git`），按既有决定列为"需高权限修复的已知项"，**不尝试绕过**。
- 与本轮上次测量（`OUT-OF-LAYOUT` 30）相比新增 1 项根条目 `.screenshots/`（0 文件 / 0 B，`EMPTY`，被路径引用）。它不是本轮任何命令创建的，按"归属不明先保全"原则保留并标记待分类，**不删除**。

## 4. 现状：布局契约测试在本地失败（不是本轮引入）

`.venv\Scripts\python.exe -B -m pytest tests/workflow/test_workspace_layout_contract.py -q` 本地结果 **3 failed / 4 passed**（约 2 分钟）：

- `test_no_entry_sits_outside_the_documented_layout`：同一批 29 个 runs 条目 + `.screenshots/`。
- `test_no_run_directory_sits_at_the_wrong_depth`：7 个不在基线快照内的条目（`claude-frontend-execution-20261018`、`green-39b627c4`、`installed-av-04b3aa2f`、`lm-studio-profile`、`stitch-research-outlet-20261022`、`stitch-research-stage-20261022`、`stitch-shell-node-20261022`），并提示用 `scripts/runtime/realign_dev_layout.py`。
- `test_growth_budgets_are_recorded_and_respected`：`build/` 与 `runs/` 超预算，要求"决定"，不是自动删除。

CI 在干净检出上不包含 `.project-local`，所以这些本地失败不会出现在 rust-vnext/lint；它们反映本机载荷真实状态，也是迁移必须先解决的部分。该失败集在本轮开工前就存在（基线测量 30 项时同样如此），不是本轮改动引入。

## 5. 决策

1. **本轮不迁移、不删除**。理由：全部条目被引用；`runs/` 契约要求目录身份与 run 分配器一致；迁移需与原字节 MANIFEST、引用更新、回滚路径同批完成；且当前授权不含批量移动/删除。
2. `.screenshots/` 归为待分类条目（属性：根级、空、被引用），等 Owner 或产生它的会话确认归属；空目录不等于可删证据。
3. ACL 条目维持"需高权限修复"状态，普通令牌下不重试。
4. 若后继确认迁移，按下面草案执行；草案本身不授权移动。

## 6. 迁移草案（未执行）

目标布局：把每个旧根级 run 目录 `runs/<old-name>/` 迁到 `runs/<sha10(old-run-root)>/<old-name>/`，其中 `sha10` 用与分配器相同的"checkout 根路径 sha256 前 10 位"算法，避免造出第二种命名。

步骤（每一步都可单独回滚）：

1. 冻结快照：对每个条目计算文件数、总字节、逐文件 SHA-256 与树哈希，写入 MANIFEST（`aaos.runs-migration/v1`：原路径、目标路径、文件数、字节数、树哈希、引用清单）。
2. 引用清单：从决策表 `reference_path` 出发，逐个文件确认引用是文档、脚本常量还是测试基线；测试基线需同步更新，不能只改文档。
3. 预演：只读复制到目标位置并逐文件校验，原位置保持不变（不移动）。
4. 同位校验通过后，同批提交：目标目录 + MANIFEST + 全部引用更新；此步骤需要一次性授权与单独审查。
5. 校验：`storage_report.py` 复测 `OUT-OF-LAYOUT`、`tests/workflow/test_workspace_layout_contract.py` 通过、引用目标可达；失败按 MANIFEST 反向恢复原位置。
6. ACL 条目在获得管理员权限前不进入任何批次。

## 7. 未验证项

- 未确认 29 条目各自的消费者是否仍在使用（决策表只证明"被引用"，不证明"仍需要"）；迁移前需逐项核对消费者。
- 未测量迁移后的增长复核影响（文件总量不变，但 `runs/` 分桶统计会变化）。
- 未验证 `.screenshots/` 的生成者与生命周期。
