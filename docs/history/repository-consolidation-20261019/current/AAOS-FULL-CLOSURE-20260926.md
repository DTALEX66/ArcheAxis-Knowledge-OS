# AAOS 全量审计-修复-清理闭环：最终记录（2026-09-26）

- 分支：`codex/aaos-p3-ui-convergence-20260922`
- 起始 HEAD：`edf9a7e5`
- **最终 HEAD：`5819cace`**（本地 = 远端）
- 最终 CI：[run 36237588182](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36237588182) — **全绿**（`gateplan` ✓ `lint` ✓ **`test (3.12)` ✓** `a0-gates` ✓）
- 证据等级：`EXACT_SHA_CI`（`5819cace`）+ `TESTED_LOCAL`（3341 passed / 0 failed）

## 1. 结果对比

| 指标 | 起始 | 最终 |
| --- | --- | --- |
| CI `lint` | ✗ 失败（尾随空格） | ✓ 通过 |
| CI `test (3.12)` | ✗ **15 failed**（且此前从未在此分支运行） | ✓ **通过** |
| CI `a0-gates` | ✗ 失败 | ✓ 通过 |
| 本地全套 | 4 failed / 3335 passed | **0 failed / 3341 passed** |
| `nightly`（main） | 连续 6 天失败 | 根因已消除（见 §3） |

## 2. 本次提交清单

| 提交 | 内容 |
| --- | --- |
| `caf4ab3c` | `install_builtin` 改为按 `to_dict()` 协议判别（消除 `isinstance` 类身份缺陷）+ 尾随空格修复 |
| `e8e6909d` | 43 个既存未提交的 doc/authority/state 文件 |
| `ddc3b27b` | 交付与遗留清单文档 |
| `ab4aa820` | 三项契约修复：`content_base64` 流式化后的断言、转换引擎适配器名、`test_axr060` 语义 |
| `340b2041` | 跟踪被已提交文档引用的审计证据 |
| `fbb674a6` | `test_desktop_launch` 补齐共享资源边界 patch（4 个测试） |
| `ee66ce85` | lint 认识「生成式审计收据」这一文件类别 |
| `d29cabf1` / `d5f4cc7b` / `5819cace` | `test_axr060` 表面划分：只对**发布声明表面**强制对象存在性 |

## 3. `nightly` 连续 6 天失败的真实根因

两个独立原因叠加，且都不在外部审计报告的诊断范围内：

1. **门禁从未真正运行** —— `main` 上最近的 CI 都是文档改动，gateplan 把 `test` 作业一直 **SKIP**；`lint` 又被 2026-09-23 引入的一个尾随空格卡住。真正跑全套的只有 `nightly` cron。
2. **契约与文档不一致** —— 仓库中**已提交的契约测试已经要求**新的文档内容，但那些文档更新**从未提交**，只存在于工作区。

## 4. 逐项修复定性

| 失败项 | 定性 | 依据 |
| --- | --- | --- |
| `install_builtin` ValueError | **产品缺陷** | 用第二个模块名重载复现，报文与 CI 逐字节一致；改为协议判别 |
| `lint` 尾随空格 | 数据缺陷 | 修复已在工作区未提交 |
| `content_base64` 断言 | 测试过时 | 实现已移到 `StreamingImportContent.cs`（流式，更优） |
| `html-adapter` / `docx-adapter` | 测试过时 | `app/workspace/service.py:193` 主动分发内置插件转换器，是预期路径 |
| `test_axr060` | 测试语义不适用 | 审计收据记录**未发布本地分支**的提交，全新检出中不存在 |
| `test_desktop_launch`（4 项） | 测试缺 patch | 同文件 L192 既有注释已指明该边界「CI 上不可用」 |
| 文档权威索引链接失效 | 数据缺口 | 被链接文件未跟踪 |

## 5. ⚠️ 事故复盘：一次数据丢失与恢复

### 发生了什么

我执行 `git revert 340b2041` 以撤销「把审计证据入库」时，**误以为 revert 只会撤销索引变更**。实际上那 10 个文件当时已在该提交中被跟踪，因此 revert 把它们的**工作区副本一并删除**：

```
AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json : False
AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json : False
AAOS-FROZEN-DONOR-HASH-AUDIT-20260926.json : False
AAOS-HISTORY-PATH-DISPOSITION-20260926.json : False
AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md : False
AAOS-UNTRACKED-LINEAGE-METADATA-20260925.json : False
DSH-DP-TASK-ASSIGNMENTS-20260925.md : False
SESSION-RESTART-2026-09-12.md : False
```

**如果这是错的，错在哪里**：我未在破坏性 git 操作前确认「目标文件是否已被跟踪」。`git revert` 对**已跟踪**文件会写工作区，对**未跟踪**文件则不会；这两者的差别正是我判断失误的地方。正确做法是先 `git ls-files` 确认跟踪状态，或改用 `git revert` 后立即校验文件存在性。

### 如何恢复

数据未真正丢失——内容存在于提交 `340b2041` 的 blob 中。恢复过程有三次尝试，前两次**失败**并已记录：

1. `Set-Content -Encoding utf8` → 字节不精确
2. PowerShell 重定向 `>` → 写出 **UTF-16**，文件体积翻倍（665 KB vs 324 KB）
3. **Python `write_bytes` → 全部 `EXACT`**

```
EXACT    324896 bytes  AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json
EXACT     75846 bytes  AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json
EXACT     52326 bytes  AAOS-FROZEN-DONOR-HASH-AUDIT-20260926.json
EXACT    338714 bytes  AAOS-HISTORY-PATH-DISPOSITION-20260926.json
EXACT     34874 bytes  AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md
EXACT    111785 bytes  AAOS-UNTRACKED-LINEAGE-METADATA-20260925.json
EXACT      9225 bytes  DSH-DP-TASK-ASSIGNMENTS-20260925.md
EXACT      8392 bytes  SESSION-RESTART-2026-09-12.md
EXACT      1106 bytes  branch-batch-03-archive-correction-20260926.md
EXACT      1603 bytes  2026-09-25-r6-formal-shell-authority-reconciliation.md
ALL EXACT
```

校验方式：`git hash-object` 与 `git rev-parse 340b2041:<path>` 逐文件比对，10/10 一致。

同时丢弃了那个未推送的坏 revert 提交（`git reset --hard d29cabf1`），因为保留它会让已提交文档的链接悬空。

## 6. `test_axr060` 的最终语义（本次最重要的判断）

**原测试要求**：`docs/current/` 下每个 40 位 SHA 都必须是**本检出中的真实对象**。

**问题**：`docs/current/` 承载**分支治理审计收据**，它们记录的是**本地已审计、但未发布**的分支状态。这些提交在全新克隆里**根本不存在**，因此该要求对这类收据**不可能满足**——不是数据错误，而是测试语义用错了地方。

**最终划分**：

- **发布声明表面**（`SYSTEM_BOUNDARY.md`、`reports/current/`、显式声明的 release 与 R5 source 对象）→ **保持完整的对象存在性强制**
- **审计收据**（声明 `aaos-*` schema，或自述 `FROZEN AUDIT SNAPSHOT / NON-AUTHORITY`）→ 排除于扫描之外

**为什么这不是削弱防护**：这些收据是**历史治理证据**，不是当日的发布声明；把它们逐字改写以迎合 lint 或测试只会**伪造审计记录**。

**反证（两个方向都验过）**：

- 在发布表面注入虚构哈希与截断哈希 → **仍然失败**，并指名可疑哈希（此处不复写这两个哈希值，以免它们本身被扫描面收录）：
  ```
  AssertionError: current surfaces cite hashes that are not real objects in this repository: [...]
  ```
- 收据本身 → 通过

**仍存的残余风险（如实记录）**：`deleted_tips` 的接纳依赖 `git ls-remote` 判定分支已被删除。若远端不可达，测试会以明确报错失败而非静默通过（`assert remote.returncode == 0, "git ls-remote failed; cannot judge branch deletion"`）。若判定错误，错在「把远端不可达误认为分支已删除」——该场景已用断言封堵。

## 7. 数据质量修正（顺带发现）

| 文件 | 问题 | 处理 |
| --- | --- | --- |
| `docs/current/R6-EXECUTION.md:2901` | 树 SHA 被损坏（`4fc581e5` 开头、后缀错误），**该文件自己已在 L2905 记明这是转录错误** | 修正为经验证的 `4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9`（保留错误说明作为审计轨迹） |
| `docs/current/AAOS-EXTERNAL-AUDIT-VERIFICATION-20260926.md` | 引用了一个 repack 后已不存在的 pack 文件名（形如 40 位 SHA，污染扫描） | 改为遍历当前 `.idx`，不再写易变的 pack 名 |

## 8. 清理结果（`git gc`）

| 指标 | 前 | 后 |
| --- | --- | --- |
| `garbage` | 5 个 `tmp_pack_*` | **0** |
| `size-garbage` | 8.95 MiB | 0 |
| 松散对象 | 13 | 0 |
| `in-pack` | 27309 | 27044 |
| `size-pack` | 447.59 MiB | 447.31 MiB |

- **99 个引用逐条比对完全未变**（`refs-before-gc.txt` vs `refs-after-gc.txt`）
- `refs/codex/**` 42 条完好
- 四个巨型对象**全部仍在**（`aab1ec6f…` 154,127,053 B；`9a8a093c…` 154,436,574 B；`8899944a…` 78,979,668 B；`c97b1a1d…` 24,159,628 B）——gc 只是把它们重新打包进 `pack-13c78b2c`（444.1 MB）

**清理不缩小 447 MiB 主体**：体积来自 `refs/codex/turn-diffs/checkpoints/**` 引用的检查点快照，属 **Codex CLI 自有状态**，`AGENTS.md` §3 禁止越权处置。任何声称 `git gc` 能缩掉这部分体积的说法都是错的。

## 9. 明确驳回的外部审计处方

| 处方 | 驳回理由 |
| --- | --- |
| `git for-each-ref … \| grep -v master \| xargs -P4 -n1 git branch -D` | 干跑证明会命中**全部 27 个本地分支**（含 `main`）；过滤器写 `master` 而本仓库默认分支是 `main` |
| `git-filter-repo --sensitive-data-removal` | 无敏感泄露证据；会重写全部 99 个引用并需 force push |
| `fast_mode=true` / `shell_snapshot=true` | 该 Codex CLI 中**不存在**这两个键 |
| `preferred_auth_method` / `web_search=false` | `config.toml` 中**不存在**这两个键 |
| 安装 `@softspark/dsh-codex@1.4.0` | 面向 DSH `0.1.1-rc.2`，本机 host 为 `0.1.5-rc.2` |
| `reflog expire --expire-unreachable=now` 作为回滚手段 | 方向相反：它**清除**恢复信息 |

## 10. 未验证边界

- `macos` / `windows` 运行时、桌面构建、安装器生命周期、`rust-vnext` 等作业在本轮为 **SKIP**，未验证。
- `shared/provider_routing.py` 仅行尾漂移（`git diff --numstat` 为空），**故意未提交**。
- `docs/history/` 未跟踪的保留历史资产**未处置**：既有记录明确标注 `AX-DIR-010 为 SCHEMA ONLY / NO MOVE OR DELETE AUTHORISED`，本轮未越权移动或删除。
- `nightly` 的下一次 cron 才是验证 `main` 恢复的最终证据；本轮只修复了其根因。
