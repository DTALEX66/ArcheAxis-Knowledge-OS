# 仓库使用规范化与体积治理（2026-10-06）

状态：`CONTRACT_DEFINED / ENFORCED_BY_SCRIPT_AND_TEST`。本文件是**规范**，不是一次性清理记录；
清理记录仍在 `AAOS01-CLEANUP-EXECUTED-AND-PENDING-20261005.md` 与
`.project-local/task-runtime/storage-report-20261006.json`。

## 1. 为什么要立这条规范

上次整理后目录**又乱了，而且体积持续膨胀**：本轮实测（`scripts/runtime/storage_report.py`）：

| 类 | 实测 | 结论 |
| --- | --- | --- |
| 项目本体（Formal 源码树，排除 `.project-local`） | **2.7 GB** | 正常 |
| 被忽略的开发根 `.project-local`（本工作树） | **41 GB** → `build/` 18.3、`task-runtime/` 10.7、`candidates/` 2.0、`runs/` 1.5、`cache/` 0.7、`a3-python-input/` 0.6、`mig/` 0.01 | 见 §3 预算 |
| 其中 cargo 目标目录 | **14 GB** | **有意保留**：它是让构建 37–95 秒完成的热缓存 |
| 绿色仓库 `ArcheAxis.Knowledge.Green-x64`（仓外部署面） | **15 GB** | 见 §5 待决 |
| `.project-local` 根下**无归属散落** | **217 项**（一次性脚本、日志、`tmp/`、`verif/`、`test-fallback-run/` 等） | 本轮已归档 197 项 |
| 仓库根生成物 | `build/`(3.0 MB pip bdist)、`__pycache__/`、`archeaxis_workspace.egg-info/` | 本轮已归档并加入 `.gitignore` |

膨胀的真正危害不是 GB，而是**未分类的体积**：它让"可再生的缓存"和"被引用为证据的文件"混在一起，
于是既不敢删也不会清。所以规范的核心是**先分类，再谈清理**。

## 2. 布局契约（三问：放哪、谁负责、留多久）

| 类别 | 位置 | 谁写 | 保留规则 |
| --- | --- | --- | --- |
| 受控源码 | `crates/ services/ frontend/ src-tauri/ apps/ scripts/ config/ docs/ tests/ packages/` 等**由 Git 决定** | 开发者，经 PR | 永久；根条目以 `git ls-files` 为准，不由人手维护白名单 |
| 开发输出（忽略） | `.project-local/{build,runs,task-runtime,candidates,recovery,mig,cache,worktrees,a<编号>*,rt*,tmp,legacy-scratch*}` | `scripts/runtime/dev.py` 与各探针 | 见 §3/§4 |
| 本地运行数据 | `data/`（忽略） | 产品本地运行 | 便利副本，**永远不是真值来源**，可重建 |
| 部署面 | 仓外的 Green 树 | 仅经审计的部署步骤 | 不属本仓；见 §5 |

**禁止写入**（无需再讨论）：另一个 worktree 的 `.project-local`；Green 部署树（除非正是部署步骤）；
`E:\`；用户主目录；`%TEMP%` 父目录（归属不明者保留并标注）。

## 3. 预算与超限含义

`storage_report.py` 对以下类给出预算（GB）：`build` 22、`task-runtime` 12、`candidates` 4、
`runs` 2、`recovery` 4。**超限不是删除触发器，而是"这一类需要一次决定"的信号**；任何一类都只在
有**逐项审计清单 + 可恢复保留点**的前提下才做清理。

## 4. 清理规程（四步，缺一不可）

1. **测量**：`python -B scripts/runtime/storage_report.py --json <path>`；退出码非零即有越界项。
2. **分类**：每项归为 可再生缓存 / 被引用的证据 / 可再解包的输入 / 归属不明。
3. **引用校验**：对每个候选做**精确路径**引用检查（`git grep -F '<相对路径>'`）。
   此规则是被一次真实事故逼出来的：本轮首版用子串判断并直接移动了 220 项，其中 `.project-local/a10`
   是清理文档写明的**恢复目标**、`rt`/`a1`/`a1-python-input` 被交接与探测记录引用——**已全部移回**。
   **有引用的路径不得移动**，只能"先建保留点、后按清单清理"。
4. **归档而非删除**：`realign_dev_layout.py` 把散落项**移动**到
   `.project-local/legacy-scratch-<日期>/` 并写 `manifest.json`（源路径、字节、文件 SHA-256、
   恢复指令）。本轮 197 项 + 3 项根生成物即按此归档，**零删除**。

## 5. 仍待所有者给出范围的事项

- **Green 仓 15 GB**：各代候选自带 `candidate-manifest.json` 且被台账引用，属证据 → 可回收 0；
  四个旧代（`v82e8d28c` 947 M、`v18a00075` 867 M、`vd6bd374` 864 M、`f151f4c7998a` 679 M）在外的
  "接受度/归属"需逐一确认后才谈处置；`EBWebView`（42 M）归属不明，保留。
- **`.project-local` 中 `candidates/`(2.0 G)、`build/green-candidates`(1.3 G)、`candidates/` 等输入类**：
  同盘存在可解包 ZIP，可回收，但会牺牲复跑便利；需所有者指定。
- **cargo 热缓存 14 G**：按"提高缓存命中率"的要求保留。

## 6. 强制手段

- `scripts/runtime/storage_report.py`：测量 + 越界告警（根目录对照 `git ls-files`，不做人手白名单）。
- `tests/workflow/test_workspace_layout_contract.py`：断言无越界项、`.project-local` 无散落、预算字段存在；
  越界即测试失败，因此"又乱了"会先被 CI 发现而不是靠人眼。
- `scripts/runtime/realign_dev_layout.py` / `undo_layout_realign.py`：归档与回退（均写清单）。
