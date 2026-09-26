# AAOS 接管检查点 — 2026-09-26（DSH / DeepSeek 执行）

- 仓库：`DTALEX66/ArcheAxis-Knowledge-OS`
- 分支：`codex/aaos-p3-ui-convergence-20260922`
- 本检查点 HEAD：`14a2788c5fa03233473fbcd0877cc042c6815f3e`（本地 = 远端）
- 对应 CI：[run 36239548637](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36239548637) — **success**（`gateplan` / `lint` / **`test (3.12)`** / `a0-gates` 全部 success）
- 证据等级：`EXACT_SHA_CI` + `TESTED_LOCAL`（3351 passed / 0 failed）

## CURRENT_STATE

接管基线（只读核对，非历史报告数字）：

| 项 | 实测值 |
| --- | --- |
| cwd / toplevel | `D:\All projects\ArcheAxis-Knowledge-OS` |
| branch | `codex/aaos-p3-ui-convergence-20260922` |
| HEAD / tree | `14a2788c…` / `ca69e860…`（接管时为 `8da5dca0` / `ca69e860`） |
| 已跟踪改动 | **无**（`git status --porcelain=v1 -uno` 为空） |
| worktree | 5 个（主 + `.project-local/worktrees/{dp-f01-20260925,v3-era,verify-0c9c,worker-quality-0906}`） |
| git | 2.54.0.windows.1 |
| 远端 main | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`（交接核验时同值） |

**与交接快照的增量**：接管时 HEAD 为 `8da5dca0`；本轮新增 `14a2788c`（见 DONE）。`origin/main` 未变动。

## DONE（本轮，已推送并 CI 验证）

**D-1 `test_axr060` 校验边界修复** — `14a2788c`

复核 `5819cace` 中的实现，确认提示词列出的缺陷真实存在，其中第 3 条是**可利用漏洞**：

- 旧实现按文件前 600 字符的正文标记识别收据，**无路径限制**，且对所有表面生效。
- 在隔离 fixture 上验证：`SYSTEM_BOUNDARY.md` 内放入 `FROZEN AUDIT SNAPSHOT / NON-AUTHORITY` 标记后，其中的伪造 40 位 ID **对旧算法不可见**（`False`），对**新算法可见**（`True`）。
- 同一对比在真实仓库上运行：两者覆盖**完全相同的 246 个标识符**（差异 0）→ 修复无副作用。

修复内容：

1. 锁定表面（`SYSTEM_BOUNDARY.md`、`reports/current/`）**永不可豁免**；路径判定先于任何正文读取。
2. 收据豁免需同时满足**获准目录** + **精确 `schema_version` 值**；`aaos-` 前缀不再构成通行证。
3. 分类器接受显式 `root`，可测试且不能被模块常量改写（这本身是第二个真实缺陷：旧实现用模块级 ROOT，在任意 root 下恒返回 None）。
4. 远端探测加**有界超时**并区分结局；明确 `ls-remote` 只描述远端**当前**状态，**不能**证明分支曾经存在。
5. 保留既有优化（批量 `cat-file --batch-check`、单次 `ls-remote`），未退回逐 SHA/逐分支子进程。

新增 9 项回归（A / A2 / B / C / D / E / E2 / F / G），反例只放隔离 tmp fixture，未污染正式 current 文档。

## DONE（承接自上一轮，未重新修改）

尾随空格 lint、`install_builtin` 协议化、已提交文档/契约缺口、流式导入断言、适配器名称、`desktop_launch` 边界、GC、10 文件恢复 —— 均按提示词要求**默认关闭**，仅在其出现新复现证据时才重开。

## OPEN

**O-1 `machine_assets` 页面未接通**（阶段 D 的第一个真实缺口）

- `config/desktop/routes-v1.json` 定义 7 个规范页面。
- `MainWindow.axaml.cs` 命中数：`knowledge` 460、`learning` 221、`jobs` 73、`settings` 57、`recovery` 38。
- **`machine_assets` 0 处**，`/api/v1/machine/assets` 端点**从未被调用**。
- 同类：`source_reader` 作为 **page_id** 为 0 处（功能存在于 `Views/SourceReaderView.axaml`，但路由 id 未登记）。

**O-2 正式 UI 纵向切片**

- 正式实现：`apps/ArcheAxis.Desktop/`（C#/Avalonia，中文优先，黑底白灰深色基线）。
- 现有：`MainWindow.axaml` 810 行 + `MainWindow.axaml.cs` 4727 行、`Themes/AaosTheme.axaml`、已拆出 `Views/SourceReaderView` 与 `Views/EvidenceCenterView`、`Contracts/Generated/Vocabulary.g.cs`。
- 待做：按当前路由/导航/设置/恢复入口建立**完整页面清单**（不得套用旧 12 页面列表），再实现「启动 → Capture → 导入反馈 → Reader/Evidence → 知识绑定 → 学习/Review → 重启读回」的高质量切片。

**O-3 设计资产缺失** — **UNVERIFIED_REFERENCE**

仓库内**未找到** `DESIGN-SPEC`、`B10`、`B09` 资产文件。提示词要求的「实际查找 B10/B09 资产和当前 DESIGN-SPEC」结果为：**不存在**。按规则记为 `UNVERIFIED_REFERENCE`，**不自行生成替代图**后宣称一比一还原。现有设计权威为 `config/product/UI_CONTRACT_V2.json`、`docs/current/UI_V3_PRODUCT_ROADMAP.md`、`docs/current/AAOS_VISUAL_QA.md`、`docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md`。

## BLOCKED

**B-1 main/nightly 集成 —— `BLOCKED_BY_OWNER`**

本地依赖核对已完成（只读，未写 main）：

- `origin/main` 是 HEAD 的**祖先**：`git rev-list --left-right --count origin/main...HEAD` = **`0  187`** → 积分是**纯快进**，无需 merge，无冲突面。
- 集成门禁计划（`scripts/ci/classify.py`，215 个变更文件，`unknown_paths: []`）：

```
ci-verdict, contracts-vnext, desktop-build, desktop-fast, desktop-vnext,
format-targeted, installer-lifecycle, lint, py-primary, release-verify,
rust-vnext, security-targeted, static, wheel-smoke, workers-vnext
```

- **关键差异**：当前分支 CI 只实际运行 `gateplan` / `lint` / `test (3.12)` / `a0-gates`；上列 `rust-vnext`、`desktop-vnext`、`contracts-vnext`、`workers-vnext`、`installer-lifecycle`、`wheel-smoke`、`security-targeted`、`format-targeted` 在本轮分支运行中均为 **SKIPPED**，**未验证**。
- 因此：**分支修复已验证 ≠ main 集成完成 ≠ main 新 SHA 的 nightly 已通过**。本轮**未**更新 main、未建 PR、未碰 release 守卫。
- 需要的授权：Owner 明确的 main 集成授权（快进或 PR）。

**B-2 平台覆盖** — 本机为 Windows；`macos` / `windows` 运行时、桌面构建、安装器生命周期作业在本轮为 **SKIPPED / NOT_RUN**，不得把 Linux Python CI 推广为 Windows/macOS 通过。

## DECISIONS

| ID | 决策 | 依据 |
| --- | --- | --- |
| DEC-1 | 锁定表面优先于正文标记：路径判定先行 | `SYSTEM_BOUNDARY.md` 加标记即可自我豁免是**可利用漏洞**，已用隔离 fixture 复现 |
| DEC-2 | 收据豁免用**精确 schema 白名单**，非 `aaos-` 前缀 | 前缀会开出一张通用免检通行证 |
| DEC-3 | 分类器改为显式 `root` 参数 | 旧实现依赖模块常量，导致任意 root 下不可用且不可测 |
| DEC-4 | `ls-remote` 只支持「当前未公布」，不足以证明「已删除」 | 远端探测无法回溯历史；错误分类须显式失败而非静默通过 |
| DEC-5 | 补 `contract-bearing-docs` 风险类（仅精确路径） | `docs/PROJECT_STATUS.md` 等被契约测试断言，却只跑 `[static]`；宽 glob 会迫使所有散文改动跑主套件 |
| DEC-6 | main 集成**不执行**，记 `BLOCKED_BY_OWNER` | 本提示词明确「不新增 merge/push 权限」 |
| DEC-7 | 不生成 B10/B09/DESIGN-SPEC 替代资产 | 资产不存在 → `UNVERIFIED_REFERENCE`，自造会变成假的一比一宣称 |

## ERRORS

| ID | 现象 | 根因 | 影响 | 修复 | 防复发 |
| --- | --- | --- | --- | --- | --- |
| ERR-1 | 规范检查报 `tests/test_axr060_completion_audit.py: crlf` | **本文件的编辑工具把全文统一写成 CRLF**；HEAD 中该文件本来只有 311 个 CRLF（混合行尾），被改成 547 个纯 CRLF | 会阻塞 CI `lint` | 将该文件规范化为 LF（547 → 0 CRLF） | 改动后先跑 `check_repository_conventions.py --source worktree` 再提交 |
| ERR-2 | `test_docs_only_classifies_static` 失败 | 该测试用 `docs/PROJECT_STATUS.md` 作为「纯文档」示例，而它**实际被契约测试断言** | 分类修正被过时示例挡住 | 改为真正普通文档 `docs/history/notes.md`，并新增 `contract-bearing-docs` 回归 | 分类变更必须同时更新承受该分类的测试示例 |

未解决但已记录：`crates/archeaxis-api/tests/maintenance_cli.rs` 的 CRLF 是**既存且本轮未触碰**；CI 的 `--source head` 检查历史通过，`--source worktree` 会报。本轮未处理（不在授权范围）。

## EVIDENCE

| 证据 | 位置 / 标识 |
| --- | --- |
| exact-SHA CI（全绿） | run `36239548637` @ `14a2788c` |
| 全绿 run 的作业结论 | `gateplan` ✓ `lint` ✓ `test (3.12)` ✓ `a0-gates` ✓ |
| 本地全套 | 3351 passed / 46 skipped / 0 failed |
| 边界修复 RED 反证 | 隔离 fixture：旧算法 `False` / 新算法 `True`；真实仓库覆盖差异 0（246 == 246） |
| 集成门禁计划 | `scripts/ci/classify.py --paths <215 files>` → `unknown_paths: []`，`full_qualification: false` |
| 门禁注册表 | `.worklab/gate-registry.v1.yaml`；聚合门 `a0-gates` |
| 运行输出根 | `.project-local/runs/`（各次 run id 见执行输出） |

## NEXT（新会话可直接接续，勿重复已完成项）

1. **O-1**：接通 `machine_assets`（`/api/v1/machine/assets`）与登记 `source_reader` page_id。先读 `config/desktop/routes-v1.json` 与 `MainWindow.axaml.cs` 的现有路由模式，按同一模式补，并加 C#/Python 合同测试。
2. **O-2**：从当前实际路由建立完整页面清单，再实现纵向切片（启动 → Capture → 导入反馈 → Reader/Evidence → 知识绑定 → 学习/Review → 重启读回）。每步先跑最小相关测试。
3. **O-3**：向 Owner 确认 B10/B09/DESIGN-SPEC 是否存在于仓库之外；在确认前保持 `UNVERIFIED_REFERENCE`。
4. **B-1**：取得 Owner 授权后再执行 main 快进/PR，并对新 main SHA 取 exact-SHA 证据；**不得**用旧 SHA 的结果声称新 main 已验证。
5. **B-2**：Windows/macOS 原生验收需相应环境；不得用 Linux CI 代替。

### 复现命令

```powershell
# 基线
git rev-parse HEAD; git rev-parse "HEAD^{tree}"; git status --porcelain=v1 -uno
git rev-list --left-right --count origin/main...HEAD

# 契约/分类回归
.\scripts\ci\run_tests.ps1 tests/test_axr060_completion_audit.py tests/test_ci_classifier.py -q
.\.venv\Scripts\python.exe -B scripts/check_repository_conventions.py --source worktree
.\.venv\Scripts\python.exe -B scripts/ci/classify.py --paths docs/PROJECT_STATUS.md

# 集成门禁计划（只读）
.\.venv\Scripts\python.exe -B scripts/ci/classify.py --paths (git diff --name-only origin/main HEAD)
```
