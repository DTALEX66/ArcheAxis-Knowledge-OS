# S01 越界布局逐项决策提案（2026-11-03）

状态：**只读分析提案，未移动、未删除、未改布局清单**。需要 Owner 逐组签字后再进入执行。

来源测量：`.project-local/runs/be268a2d33/storage-observation-20261103/artifacts/storage-growth-final-round30.json`（固定 v2 checkpoint 只读复核，未滚动、未替换基线）。
分类工具：`scripts/maintenance/layout_decision_report.py`（本轮修正后重跑，修正说明见下文第 1 节）。
完整 JSON 决策表：`.project-local/runs/be268a2d33/backend-qualification-20261103/artifacts/layout-decision-20261103-backend-v3.json`。

## 1. 本轮修正了什么

原决策工具用"裸名出现在任何 tracked 文件里"判定引用，于是 `c`、`p`、`dist`、`state` 这类短名/通用名会被普通正文当成引用；路径匹配用固定字符串，`.project-local/p` 还会误命中 `.project-local/proposals`。本轮把判定拆成两层并加了段边界：

- **路径限定引用**（`.project-local/<name>` 或 `.project-local/runs/<name>`，POSIX ERE 段边界）——单独成立；
- **裸名引用**——只有"独特名"（≥10 字符且含数字或分隔符）才算引用；短名/通用名仅记录为噪声，不升级为引用；
- 每一行同时保留 `reference_path` / `reference_bare_name` / `reference_note`，决策时能看到引用强度而不是一个布尔值。

新增 18 项单测（`tests/maintenance/test_layout_decision_report.py`），覆盖短名排除、路径段边界、引用强度分级与分类词汇不变。

## 2. 修正后的现状（87 项）

| 分类 | 数量 | 体积 |
| --- | --- | --- |
| REFERENCED（被引用） | 56 | 约 1,058.8 MB |
| RUNS_LAYOUT（runs/ 形状问题） | 29 | 约 495.2 MB |
| PROTECTED_OR_GENERIC（需人工确认） | 1 | 约 30.4 MB |
| UNREADABLE（ACL 不可读） | 1 | 未测量 |
| 合计 | 87 | 约 1,584.5 MB |

其中 51 项有路径限定引用，5 项只有独特裸名引用（`account-preferences`、`archive-local-only-recovery-20260926.bundle`、`build-stage-learning.py`、`consolidation-ci`、`node-manifest-guard-cases`）。

**关键结论：已不存在"无引用、可安全归档"的条目。** 上一轮已把 5 个 UNREFERENCED_CANDIDATE 归档；剩余 87 项都是"被引用的历史证据/运行根"、"runs/ 形状问题"或"ACL 不可读"，三者都需要决策而不是再次扫描。

## 3. 需要 Owner 决策的四组

### A. 56 个被引用的 `.project-local` 根条目（约 1.0 GB）

建议：**登记为 sanctioned 例外（写进布局清单并附理由），不移动**。移动会让执行记录、回执和消费者里的路径引用失效，而体积收敛应由独立清理立项（byte-preserved 归档 + MANIFEST + 引用更新）承担，而不是布局治理顺手做。

可按用途再分三类，供你逐类批准或否决：

1. **运行/工具基础设施**：`tools`、`inputs`、`staging`、`dist`、`state`、`proposals`、`audits`、`audit-tools`、`acceptance`、`probes`、`tooling`、`test-fixtures`、`c`、`p`、`inspect`、`consolidation-ci`、`cargo-home-a04`、`dotnet-home`、`appdata`、`account-preferences`、`localappdata`、`obsidian-compat`。
2. **历史证据树**（本轮最大占用）：`zcode-newcore-20261030`、`deeptutor-val`、`ui-review-20261026`、`stitch-replica`、`stitch-audit-20261026`、`m0loop`、`node-manifest-guard-cases`、`dsh-*`、`rsb24`、`installed-*`、`pdf-runtime-fix-20261029`、`ui-audit`、`probe2`、`tmp-measure`、`dp-nf-03-probe`、`motion-contract-*`、`archive-*.bundle`。
3. **单文件回执/脚本**：`closure-*.json`、`minimax-*.json`、`ui-audit-remediation-*.json`、`ui-polish-*.json`、`build-stage-learning.py`、`AAOS-UI-Preview-*`。

### B. 29 个 `runs/` 形状问题（约 495 MB）

`runs/` 的契约是 `runs/<sha256(root)[:10]>/<run_id>/`。这 29 项是旧形状或身份根已失效。建议单独一次迁移：移动时带 MANIFEST、更新被引用的路径，并保留 `runs/` 预算复核；**不迁移**也可以，但 storage_report 会继续把它们报为 out-of-layout。

### C. ACL 不可读 1 项

`.project-local/runs/fulltest-final-20260913`：26 个嵌套 `.git` 拒绝读取，`Get-Acl`/`icacls` 无权限。需要管理员权限修复 ACL 后才能测量与分类；本轮未动。

### D. `backups/`（30.4 MB）

裸名只作为普通文本出现，没有路径限定引用。需要你确认它是否仍在使用：在用就加入 sanctioned；不用就走 B 类归档流程。

## 4. 我建议的执行顺序

1. 你批准 A 的清单 → 我把这些名字连同理由写进 `scripts/runtime/storage_report.py` 的 sanctioned 名单，重跑测量，确认 OUT-OF-LAYOUT 只剩 B/C。
2. 你确认 B 可以迁移 → 我按 MANIFEST + 引用更新执行一次，并重跑预算复核。
3. C 等你在有管理员权限时修复。
4. D 由你一句话定。

## 5. 本次没有做的

- 没有移动、删除或重命名任何条目；
- 没有修改 `storage_report.py` 的布局清单；
- 没有滚动增长基线，没有放宽任何门禁。

## 附录：87 条目决策表

| 条目 | 分类 | 文件数 | MB | 引用强度 |
| --- | --- | --- | --- | --- |
| fulltest-final-20260913 | UNREADABLE | 0 | 0 | 路径引用 |
| stitch-research-stage-20261022 | RUNS_LAYOUT | 4834 | 250.53 | 路径引用 |
| stitch-shell-node-20261022 | RUNS_LAYOUT | 2549 | 133.94 | 路径引用 |
| installed-av-04b3aa2f | RUNS_LAYOUT | 654 | 92.33 | 路径引用 |
| fulltest-clean-20260913 | RUNS_LAYOUT | 92 | 7.56 | 路径引用 |
| backup-regression-20260914 | RUNS_LAYOUT | 145 | 6.22 | 路径引用 |
| deeptutor-run-root-regression | RUNS_LAYOUT | 26 | 1.35 | 路径引用 |
| deeptutor-bridge-20260914 | RUNS_LAYOUT | 16 | 1.35 | 路径引用 |
| ruff-regression-20260914 | RUNS_LAYOUT | 16 | 1.35 | 路径引用 |
| green-39b627c4 | RUNS_LAYOUT | 5 | 0.35 | 路径引用 |
| security-boundary-20260914 | RUNS_LAYOUT | 8 | 0.05 | 路径引用 |
| lm-studio-profile | RUNS_LAYOUT | 47 | 0.03 | 路径引用 |
| report-regression-20260914 | RUNS_LAYOUT | 24 | 0.03 | 路径引用 |
| asr-path-regression | RUNS_LAYOUT | 12 | 0.02 | 路径引用 |
| phase0-root-regression | RUNS_LAYOUT | 18 | 0.02 | 路径引用 |
| media-root-regression | RUNS_LAYOUT | 6 | 0.02 | 路径引用 |
| report-root-regression-final | RUNS_LAYOUT | 12 | 0.02 | 路径引用 |
| benchmark-root-regression | RUNS_LAYOUT | 38 | 0.01 | 路径引用 |
| ssot-docs-regression | RUNS_LAYOUT | 10 | 0.01 | 路径引用 |
| report-root-regression | RUNS_LAYOUT | 10 | 0.01 | 路径引用 |
| post-ruff-20260914 | RUNS_LAYOUT | 45 | 0.01 | 路径引用 |
| entrypoint-regression-20260914 | RUNS_LAYOUT | 43 | 0.01 | 路径引用 |
| run-root-entry-regression | RUNS_LAYOUT | 15 | 0.01 | 路径引用 |
| adapter-tests-20260913 | RUNS_LAYOUT | 17 | 0 | 路径引用 |
| adapter-tests-20260913b | RUNS_LAYOUT | 1 | 0 | 路径引用 |
| path-regression-20260914 | RUNS_LAYOUT | 1 | 0 | 路径引用 |
| ssot-a0-regression | RUNS_LAYOUT | 4 | 0 | 路径引用 |
| boundary-regression-20260914 | RUNS_LAYOUT | 1 | 0 | 路径引用 |
| stitch-research-outlet-20261022 | RUNS_LAYOUT | 0 | 0 | 路径引用 |
| claude-frontend-execution-20261018 | RUNS_LAYOUT | 0 | 0 | 路径引用 |
| inputs | REFERENCED | 325 | 237.79 | 路径引用 |
| zcode-newcore-20261030 | REFERENCED | 5692 | 231.81 | 路径引用 |
| tools | REFERENCED | 917 | 101.68 | 路径引用 |
| deeptutor-val | REFERENCED | 3173 | 78.78 | 路径引用 |
| staging | REFERENCED | 6 | 74.3 | 路径引用 |
| ui-review-20261026 | REFERENCED | 302 | 70.64 | 路径引用 |
| m0loop | REFERENCED | 207 | 60.49 | 路径引用 |
| node-manifest-guard-cases | REFERENCED | 1248 | 53.88 | 独特名引用 |
| archive-local-only-recovery-20260926.bundle | REFERENCED | 1 | 35.65 | 独特名引用 |
| acceptance | REFERENCED | 389 | 27.8 | 路径引用 |
| audit-tools | REFERENCED | 1614 | 21.34 | 路径引用 |
| c | REFERENCED | 476 | 11.91 | 路径引用 |
| stitch-replica | REFERENCED | 18 | 10.77 | 路径引用 |
| dist | REFERENCED | 5 | 10.51 | 路径引用 |
| ui-audit | REFERENCED | 47 | 7.62 | 路径引用 |
| audits | REFERENCED | 1143 | 5.81 | 路径引用 |
| ci-replay | REFERENCED | 16 | 4.75 | 路径引用 |
| rsb24 | REFERENCED | 30 | 3.49 | 路径引用 |
| ui-audit-remediation-mapping-final.json | REFERENCED | 1 | 2.29 | 路径引用 |
| stitch-audit-20261026 | REFERENCED | 8 | 2.03 | 路径引用 |
| proposals | REFERENCED | 155 | 1.85 | 路径引用 |
| pdf-runtime-fix-20261029 | REFERENCED | 94 | 0.75 | 路径引用 |
| dsh-audit | REFERENCED | 17 | 0.44 | 路径引用 |
| probes | REFERENCED | 31 | 0.37 | 路径引用 |
| tmpuf_amolv | REFERENCED | 1 | 0.3 | 路径引用 |
| inspect | REFERENCED | 15 | 0.28 | 路径引用 |
| ui-audit-remediation-v13-grouped-capture-missing-map.json | REFERENCED | 1 | 0.27 | 路径引用 |
| dsh-recon-20261001-bytes | REFERENCED | 12 | 0.27 | 路径引用 |
| dsh-recon-20261001 | REFERENCED | 8 | 0.25 | 路径引用 |
| state | REFERENCED | 4 | 0.22 | 路径引用 |
| local-pinned-sandbox-20261029 | REFERENCED | 20 | 0.11 | 路径引用 |
| installed-native-correction-20261029 | REFERENCED | 16 | 0.1 | 路径引用 |
| account-preferences | REFERENCED | 1 | 0.08 | 独特名引用 |
| obsidian-compat | REFERENCED | 1 | 0.04 | 路径引用 |
| tooling | REFERENCED | 41 | 0.04 | 路径引用 |
| motion-contract-pytest-cache | REFERENCED | 5 | 0.02 | 路径引用 |
| installed-post-ai-recovery-orchestrator-20261029 | REFERENCED | 5 | 0.02 | 路径引用 |
| dotnet-home | REFERENCED | 21 | 0.02 | 路径引用 |
| closure-27b-matched-20261013.json | REFERENCED | 1 | 0.01 | 路径引用 |
| probe2 | REFERENCED | 1 | 0.01 | 路径引用 |
| closure-delivery-blocker-20261026.json | REFERENCED | 1 | 0 | 路径引用 |
| motion-contract-final-cache | REFERENCED | 4 | 0 | 路径引用 |
| p | REFERENCED | 1 | 0 | 路径引用 |
| tmp-measure | REFERENCED | 1 | 0 | 路径引用 |
| minimax-avatar-owner-declined-20261027.json | REFERENCED | 1 | 0 | 路径引用 |
| AAOS-UI-Preview-20261026-launch.json | REFERENCED | 1 | 0 | 路径引用 |
| build-stage-learning.py | REFERENCED | 1 | 0 | 独特名引用 |
| AAOS-UI-Preview-20261026.cmd | REFERENCED | 1 | 0 | 路径引用 |
| localappdata | REFERENCED | 4 | 0 | 路径引用 |
| ui-polish-protected-source-seal.json | REFERENCED | 1 | 0 | 路径引用 |
| archive-local-branch-candidates-20260918.bundle | REFERENCED | 1 | 0 | 路径引用 |
| consolidation-ci | REFERENCED | 1 | 0 | 独特名引用 |
| appdata | REFERENCED | 1 | 0 | 路径引用 |
| cargo-home-a04 | REFERENCED | 2 | 0 | 路径引用 |
| test-fixtures | REFERENCED | 2 | 0 | 路径引用 |
| dp-nf-03-probe | REFERENCED | 1 | 0 | 路径引用 |
| backups | PROTECTED_OR_GENERIC | 26 | 30.36 | 无强引用 |


## 附录 B：A 组处置清单草案（待确认，未改任何文件）

把 57 个 `.project-local` 根条目（A 组 56 + `backups`）按内容抽查与引用强度分为四类。这是**建议**，不是已执行动作；`storage_report.py` 的布局清单没有改动。

### B1 建议登记为 sanctioned（21 项，约 517 MB）

运行、工具、状态与输入根，被脚本/测试/回执路径引用；建议加入布局清单并注明理由，不移动（移动会让执行记录里的路径失效）。

`acceptance`(27.8 MB)、`account-preferences`、`appdata`、`audit-tools`(21.3)、`audits`(5.8)、`backups`(30.4)、`cargo-home-a04`、`ci-replay`(4.8)、`consolidation-ci`、`dist`(10.5)、`dotnet-home`、`inputs`(237.8)、`inspect`、`localappdata`、`obsidian-compat`、`probes`、`proposals`(1.8)、`staging`(74.3)、`state`、`tooling`、`tools`(101.7)。

其中三项建议再单独判断：`dist`（构建产物，可重建）、`staging`（staging 副本）、`backups`（保留价值取决于是否还有消费者）。

### B2 建议归档（6 项，约 12.2 MB）

明确的临时/探测残留，不属于证据：`c`(11.9 MB，内部是 `p-*` pytest 临时目录)、`p`、`probe2`、`test-fixtures`、`tmp-measure`、`tmpuf_amolv`。建议沿用既有做法：移入 `.project-local/archives/s01-scratch-20261103/`，附 MANIFEST（原路径/字节/哈希），不删除字节。

### B3 建议冻结并登记为历史证据（19 项，约 522 MB）

历史候选/审计/实验树，被旧记录引用：`deeptutor-val`(78.8)、`zcode-newcore-20261030`(231.8)、`ui-review-20261026`(70.6)、`m0loop`(60.5)、`node-manifest-guard-cases`(53.9)、`stitch-replica`(10.8)、`ui-audit`(7.6)、`rsb24`(3.5)、`stitch-audit-20261026`(2.0)、`pdf-runtime-fix-20261029`、`dsh-audit`、`dsh-recon-20261001`、`dsh-recon-20261001-bytes`、`installed-native-correction-20261029`、`installed-post-ai-recovery-orchestrator-20261029`、`local-pinned-sandbox-20261029`、`motion-contract-final-cache`、`motion-contract-pytest-cache`、`dp-nf-03-probe`。

建议：原地冻结（不再写入），在布局清单里作为"frozen legacy evidence"单独记录，不混进基础设施。若你要收敛体积，再单独立项做 MANIFEST 归档 + 引用更新。

### B4 建议冻结的根级回执（11 项，约 38 MB）

`AAOS-UI-Preview-20261026-launch.json`、`AAOS-UI-Preview-20261026.cmd`、`archive-local-branch-candidates-20260918.bundle`、`archive-local-only-recovery-20260926.bundle`(35.7)、`build-stage-learning.py`、`closure-27b-matched-20261013.json`、`closure-delivery-blocker-20261026.json`、`minimax-avatar-owner-declined-20261027.json`、`ui-audit-remediation-mapping-final.json`(2.3)、`ui-audit-remediation-v13-grouped-capture-missing-map.json`、`ui-polish-protected-source-seal.json`。

建议：与 B3 同属冻结证据，登记后不再新增同类根文件；后续新回执一律写进 `runs/<identity>/artifacts/`。

### 建议的清单改动形态（尚未应用）

```python
DEV_ALLOWED = {...,
    # 2026-11-03 S01-A: infrastructure roots that tooling, state and recorded receipts
    # already name; sanctioned instead of relocated so citations stay valid.
    "acceptance", "account-preferences", "appdata", "audit-tools", "audits", "backups",
    "cargo-home-a04", "ci-replay", "consolidation-ci", "dist", "dotnet-home", "inputs",
    "inspect", "localappdata", "obsidian-compat", "probes", "proposals", "staging",
    "state", "tooling", "tools"}
# 2026-11-03 S01-A: frozen historical evidence, listed separately from live infrastructure.
FROZEN_LEGACY = {"deeptutor-val", "zcode-newcore-20261030", ...}
```

只要 B1–B4 获批，`OUT-OF-LAYOUT` 会从 87 降到 **30**（29 个 `runs/` 形状 + 1 个 ACL 不可读），且不移动任何被引用的证据。

## 附录 C：布局清单补丁（**已于 2026-11-03 应用**）

> 应用记录（2026-11-03，Owner"全部授权"）：`scripts/runtime/storage_report.py` 已加入
> `S01A_INFRA`（含 `handoff`）、`S01A_FROZEN` 两个受控清单与 `layout_class()`，
> 报告新增 `s01_allowlist`；`tests/workflow/test_workspace_layout_contract.py` 增加清单契约用例。
> 7 个 scratch/探针条目（`c`、`p`、`probe2`、`test-fixtures`、`tmp-measure`、`tmpuf_amolv`、
> 会话写入探针文件）已按字节保全移入 `.project-local/archives/s01-scratch-20261103/`
> （含 MANIFEST，483 个文件 / 约 13.1 MB，未删除字节）。
> 复测：`OUT-OF-LAYOUT` **87 → 30**（29 个 `runs/` 形状 + 1 个 ACL 不可读），`dev_strays` **0**；
> 移动/归档的只有 scratch，所有被引用的证据原地未动。

下面是这一应用对应的代码形态（用于复核）：

### C1 新增两个常量（放在 `DEV_ALLOWED_PATTERN` 之后）

```python
# 2026-11-03 S01-A: `.project-local` roots that tooling, state and recorded receipts
# already cite. Sanctioned in place because relocating them would invalidate the paths
# the execution record and its receipts use.
S01A_INFRA = {
    "acceptance", "account-preferences", "appdata", "audit-tools", "audits", "backups",
    "cargo-home-a04", "ci-replay", "consolidation-ci", "dist", "dotnet-home", "inputs",
    "inspect", "localappdata", "obsidian-compat", "probes", "proposals", "staging",
    "state", "tooling", "tools",
}
# 2026-11-03 S01-A: historical evidence trees and root receipts frozen in place. They
# are listed apart from live infrastructure so the report can say which entries are
# frozen evidence rather than working state.
S01A_FROZEN = {
    "deeptutor-val", "dp-nf-03-probe", "dsh-audit", "dsh-recon-20261001",
    "dsh-recon-20261001-bytes", "installed-native-correction-20261029",
    "installed-post-ai-recovery-orchestrator-20261029", "local-pinned-sandbox-20261029",
    "m0loop", "motion-contract-final-cache", "motion-contract-pytest-cache",
    "node-manifest-guard-cases", "pdf-runtime-fix-20261029", "rsb24",
    "stitch-audit-20261026", "stitch-replica", "ui-audit", "ui-review-20261026",
    "zcode-newcore-20261030",
    "AAOS-UI-Preview-20261026-launch.json", "AAOS-UI-Preview-20261026.cmd",
    "archive-local-branch-candidates-20260918.bundle",
    "archive-local-only-recovery-20260926.bundle", "build-stage-learning.py",
    "closure-27b-matched-20261013.json", "closure-delivery-blocker-20261026.json",
    "minimax-avatar-owner-declined-20261027.json",
    "ui-audit-remediation-mapping-final.json",
    "ui-audit-remediation-v13-grouped-capture-missing-map.json",
    "ui-polish-protected-source-seal.json",
}
```

### C2 `dev_allowed` 接受这两个受控清单

```python
def dev_allowed(name: str) -> bool:
    return (name in DEV_ALLOWED or name in S01A_INFRA or name in S01A_FROZEN
            or bool(DEV_ALLOWED_PATTERN.match(name)))
```

### C3 报告里区分"活动基础设施"与"冻结证据"

`measure()` 的 `dev_classes` 记录增加 `layout_class` 字段，报告顶层增加清单快照：

```python
"layout_class": ("sanctioned_infrastructure" if name in S01A_INFRA
                 else "frozen_legacy_evidence" if name in S01A_FROZEN
                 else "declared" if dev_allowed(name) else "stray"),
...
"s01_allowlist": {"infrastructure": sorted(S01A_INFRA), "frozen_legacy": sorted(S01A_FROZEN)},
```

### C4 预期效果与需要同步的测试

- 应用后 `.project-local` 的 57 项里：51 项转为 sanctioned（21 基础设施 + 30 冻结证据），剩 6 项 scratch 仍报 out-of-layout，直到按 B2 归档（byte-preserved + MANIFEST）后才归零。
- 总 `OUT-OF-LAYOUT`：87 → 6 + 29 runs + 1 ACL = 36；B2 归档完成后 → 30。
- 需要同步 `tests/workflow/test_workspace_layout_contract.py` 的断言与基线（它当前依赖 87 项现状），并在 `docs/current/AAOS-ACTIVE-EXECUTION.json` 的布局记录里登记 s01_allowlist 版本。
- **不改变**任何删除/移动行为：清单只影响报告的"越界"判定，不授予删除权。

### C5 不批准时的退路

保持现状（87 项越界）也能运行；否则按 B2 先归档 6 项 scratch（这一步不依赖 sanctioned 清单，风险最低）。
