# 全分支与后端全链路可合并性审计 — 2026-09-27

> 本文保留修复前的审计证据及当时结论。后续修复、选择性迁移、合并与清理
> 状态见 `SEPTEMBER-BACKEND-INTEGRATION-20260927.md`；下述缺陷不应被直接
> 当作整合后 HEAD 仍未修复的结论。真实 R6/M0 资格仍不能由分支合并替代。

## 结论

**不能把所有分支整体并入主线；当前也没有证明 R6/M0 产品全链路闭环。**

本次状态：`PARTIAL`（审计有明确发现，远端 PR/CI 无法读回）；产品闭环：`NOT_READY`；后端增量合并：`BLOCKED`（须先修复本报告的具体缺陷并补足对应门禁）。这不否认已有 Rust/Python 能力，也不要求所有长期蓝图完成后才能合并一个独立工程修复。

主要依据：

1. `dsh/backend-r5` 包含 `dsh/backend-20260927`，存在可保留的后端增量，但启动器和 M0 成功判定有已复现缺陷。
2. 部分历史分支已被包含或 patch 等价吸收；部分旧治理、命名、发布分支存在真实合并冲突，不能整支导入旧规范。
3. 当前 Rust 全 workspace 测试、格式检查及同次 journey 收据身份校验通过；Python 全集本次不是全绿。测试和 fixture 收据均不等于真人、真实模型与 Green 替换闭环。
4. Git SSH 读取成功；GitHub API 被当前进程的 `GH_TOKEN` 认证拒绝，PR、必需检查和保护规则是 `UNVERIFIED`，不能签发可合并结论。

## 范围、边界与受测身份

审计对象为当前仓库的全部本地分支和 `origin` 分支、Git 图、差异、现行权威/语言/目录/验证规则，以及正式后端的导入、转换、知识、检索、学习、机器回路、持久化、恢复、迁移和打包入口。

本次执行 `git fetch origin --no-tags` 和两次 `git ls-remote --heads origin`。2026-09-27 16:23（北京时间）记录了 **12 个本地分支、11 个远端分支，共 23 个非符号引用、14 个不同分支名、10 个登记 worktree**。没有删除、移动、归档 worktree，没有 commit、push、PR 或 merge。`merge-tree --write-tree` 只计算合并结果树，不更新分支、索引或工作区；它会产生本地 Git 对象。

| 对象 | 本次身份 |
| --- | --- |
| 审计工作分支 | `codex/Audit` |
| 主检出 HEAD / origin/main / 远端 main | `43c2cafa1bfe57a862e90c5a77dc16832264babd` |
| 本地 main 指针 | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`，落后 origin/main 222 个提交；未移动 |
| 后端受测分支 | `dsh/backend-r5` |
| 后端受测 HEAD | `75f2dd1fb8d646ac04fd2e838a4faeec687bf539` |
| 后端受测 tree | `967b78bc451a46f0e7f6972cf90d29ba364d5ecc` |
| 后端受测工作区 | `.project-local/worktrees/dsh-backend-r5`，测试前后 clean |
| 保留的前端改动 | `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` 原有 ` M`；Git 内容 diff 为空，CRLF 提示仍存在；本次未改动 |

未触碰 Codex 现有前端实现、真实 Green、真实资料库、共享模型和原始 Legacy 数据。未读取私人会话/认证文件，未输出真实令牌。两个位于项目根之外的登记 worktree 只检查 Git 对象中的提交关系，没有进入其目录。测试生成物位于项目 `.project-local`；正式新增文件只有本报告。没有改写 R6 状态、Authority、TaskPack 或 A15/A16 签署。

## 逐分支处置

“落后/独有”为 `origin/main...分支` 的左右提交数，不表示功能遗漏；patch 等价和树差异另行核对。远端同名分支与本地尖端一致者合并在同一行。

| 分支 | SHA | 落后 / 独有 | 当前处置 |
| --- | --- | --- | --- |
| `codex/Audit` | `43c2cafa` | 0 / 0 | 与主线相同；本次报告尚未提交，无待合并代码 |
| `codex/aaos-p3-ui-convergence-20260922` | `43c2cafa` | 0 / 0 | 已与主线相同，不重复合并；保留未提交前端 |
| `dsh/backend-audit-20260927` | `43c2cafa` | 0 / 0 | 已与主线相同，不重复合并 |
| `main`（本地） | `e3875db0` | 222 / 0 | 仅本地指针陈旧；不是独立成果，不需反向合入远端主线 |
| `codex/worker-quality-0906` | `4ca46eaf` | 1143 / 0 | 提交已全部包含在主线，不需合并 |
| `codex/dp-f01-20260925` | `793e06ee` | 56 / 2 | `git cherry` 两个提交均为 `-`；模拟合并树与 main 没有文件差异，成果已等价吸收 |
| `dsh/backend-20260927` | `7503195b` | 1 / 13 | 被 r5 包含；修复和审查以 r5 为唯一接续线，不重复合并 |
| `dsh/backend-r5` | `75f2dd1f` | 1 / 15 | 模拟合并无文本冲突；99 个路径，前端受保护目录差异为零；**须先修复 F01–F05、校正 F06，补足 gates** |
| `dsh/governance-drift-alignment-20260927` | `ca26bcf5` | 0 / 3 | 两个文档、可快进；可作为分析材料择取，但须显式区分 main 的 v2 与后端分支 v3、格式门禁状态，不能直接升为生效规则 |
| `codex/execution-reliability-standards` | `affc0abc` | 1592 / 2 | 模拟合并 4 处冲突，涉及 AGENTS、验证策略、执行日志和交接；只择取仍适用内容，禁止整支覆盖现行规范 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | 1594 / 149 | 137 个路径、12 个冲突路径；没有 patch 等价提交不代表内容全未吸收。旧基线已被现行 R6/M0 取代，保留历史供体，不整支并入 |
| `docs/verification-summary-2026-08-09` | `8cc9c690` | 1594 / 1 | 技术上无冲突，只新增旧验证摘要；内容仍写旧项目名、旧路径及旧版本，可按历史文档归档，不能当当前验收 |
| `origin/feat/naming-step3` | `bc4a234f` | 1526 / 1 | 7 个冲突路径，含 CI、app、旧 Tauri 配置等；含前端/壳路径，不满足本次前端保护边界，禁止整体合并 |
| `origin/release/v0.4.0-contract` | `75cb72ef` | 1713 / 4 | release workflow 和测试冲突；非合并提交中 1 个 patch 等价、2 个不等价。旧发布路线与当前 no-release 不能混用，保留历史 |

四个 detached worktree 的 HEAD 均已是 main 祖先：`663d7d5f`（落后 18）、`968c4795`（1122）、`cdc07cd0`（581）、`7282e5a9`（14）。这只证明已提交历史被包含，不证明其未提交文件可删除；本次全部保留。

## 合并阻断发现

下面源文件行号以 **r5 的 `75f2dd1f`** 为准。新后端文件应在 `.project-local/worktrees/dsh-backend-r5/` 下读取，不能误看主检出的旧实现。

### F01 / P1：M0 成功判定没有验证全部关键阶段

位置：`scripts/probes/m0_full_loop_smoke.py:565–609`，以及 `:471`。

最终 `chain_stages_verified` 只要求部分状态码、备份恢复和迁移条件；搜索、纠正、后继接受、重启读回的状态及内容并没有全部进入成功条件。纠正失败时 retest 还会用 `successor_id or knowledge_id` 回退到旧知识。`schedule_ok` 只观察是否出现 fsrs，未要求完整状态和重启一致性。

本次把生产文件的最终判定 AST 原样取出，在隔离的合成输入中令 `search`、`human_correction`、`restart_learning_state`、`restart_knowledge_v3` 全部为 HTTP 500，其他被检查条件成立，得到 **`ok=true`、`chain_stages_verified=true`**。

证据为判定逻辑的可执行反例，不是声称真实 Core 已返回这些错误。它足以否定“该 ok 值证明 26 阶段全部通过”的推论。应逐阶段 fail closed，检查引用身份、答案/排程/锚点/纠正后继和 retest 关系，并对缺阶段、错误状态、内容不一致添加负例。

### F02 / P1：普通后端启动把访问凭据打印到 stdout

位置：`scripts/release/backend_launcher.py:156–160、219–240`。

`start()` 把 `launch_token`、`machine_token` 放入 receipt；只有 `--smoke` 分支会 pop 掉它们。普通启动直接 JSON 打印 receipt。Core 的认证层使用这些令牌决定 human/machine 权限，控制台及日志中的泄露不是普通诊断信息。

本次使用合成占位令牌、模拟 start 返回值执行普通 main 分支，确认 stdout JSON 同时包含两个凭据字段；没有生成或显示真实运行凭据。应让凭据只经过受控私有传递渠道，公开 receipt 不含它们。

### F03 / P1：启动超时无法约束阻塞的 readline

位置：`scripts/release/backend_launcher.py:130–149`。

循环前的 deadline 检查之后执行阻塞 `child.stdout.readline()`；Core 若保持存活却不输出换行，30 秒超时不能触发。stderr 也未并发消费，子进程可能因 stderr 缓冲区填满而停住。

隔离假子进程将 readline 延迟 0.3 秒，启动器限时设置为 0.03 秒，仍在 0.301 秒后返回成功。此反例只验证超时控制流，没有启动真实 Core。应使用有界异步读取、双流消费和可靠的 kill/wait/句柄回收；普通启动也需要明确进程所有权与退出生命周期。

### F04 / P1：同名 worker profile 的跨语言校验不一致，运行隔离可被继承环境覆盖

位置：`scripts/release/backend_launcher.py:45–67、78–96`；`crates/archeaxis-application/src/scheduler.rs:73–159`；对照现有 `apps/ArcheAxis.Desktop/WorkerProfile.cs:23–100`。

正式 C# profile 拒绝未知/重复字段、危险路径、链接及过大输入；新增 Python parser 接受未知字段、重复 python 字段和 `../`。本次三个本地合成 profile 全部被接受。Rust 新 resolver 使用 `serde_json::Value`，仅校验 schema、python 非空与 is_file，未共享同等严格合同；配置失败还会继续寻找其他候选 profile。

同时 `build_environment()` 复制父环境，只移除 `ARCHEAXIS_PYTHON`，保留 `PYTHONPATH` 和 `PYTHONHOME`。本次 sentinel 验证二者确实被保留；与该文件“从自身 root、从不使用继承 PYTHONPATH”的声明不符。应在后端修复并用统一正/负例约束各语言，保持现有前端不动。未尝试访问受保护路径。

### F05 / P2：官方 dev 路径与 worker/evidence 守卫在 linked worktree 上不闭合

位置：`scripts/runtime/dev.py::layout`；`scripts/ci/check_vnext_workers.py:41–46`；`scripts/maintenance/bulk_evidence.py:120`。

dev.py 正确按 Git common-dir 把运行输出分配到主仓库 `.project-local/runs/<worktree-id>/`，但后两个脚本把合法边界硬编码为各自 checkout 的 `.project-local/`。r5 工作树的真实 worker gate 因此抛出 `ARCHEAXIS_RUN_ROOT must stay inside .project-local`。

全套测试中 5 个 bulk evidence、1 个 worker-path、1 个 directory-batch 失败对应此类路径约定；同组相关测试在主检出运行 40 passed。该缺陷有既有基础，并非全部由 r5 引入，但会阻断当前分支按声明入口复现交付。应统一从 canonical dev resolver 获取边界，不放宽到任意外部路径。

### F06 / P2：给前端的后端合同落后于同分支实现

位置：`docs/current/DSH-BACKEND-CONTRACT-20260927.md` §1、§3、§9.2；`DSH-BACKEND-AUDIT-INDEX-20260927.md` §2、§4、§5。

合同仍要求 Supervisor 必须注入 ARCHEAXIS_PYTHON，未同步新 profile resolver；把含大量 POST 的表称为只读投影，并将手工 receipt 示例混入正式执行说明。索引还把已经受跟踪并处于 main 的审计提示词称为未跟踪，把含 packager 代码变动的 `ad89858c` 列作 doc-only，以及把 r5 继承的启动器说成本轮新增。

这些不等于接口全部不可用，但会误导 Codex 前端接线、代码归属和二进制身份审计。应基于最终源码重写一份一致合同，保留历史证据日期与 SHA；不要求改前端。

### F07 / P2：暂存工具的链接防护顺序与声明不一致

位置：`scripts/release/stage_backend_runtime.py:179–185` 及 `copy_tree()`。

工具先 `candidate.resolve()`，再 `reject_reparse()`，原始根链接可能已被解析掉；递归 copytree 默认跟随内部链接，未逐成员拒绝。输出根也先 resolve。这与“暂存运行时不跟随链接出树”的说明不一致。此项是源码确认、未做链接运行测试；应先检查原始路径与祖先，再在遍历时拒绝内部链接/重解析点，并验证输出根。

## 规范、语言与治理审计

当前权威入口存在：`PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml`、配置/语言索引、R6 冻结 TaskPack、R6 live ledger/state 与 M0 覆盖。没有把历史 R5/R3 台账当当前任务。

本次 R6 authority 校验通过：源 CRLF SHA256 为 `dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529`，仓库 LF SHA256 为 `788c5d50b5953d21eb9f67587d5406d37ad2e5457c2ca3b991399d9988e5951b`；两种身份没有混用。

Rust Core 独占 vNext 写者、Python worker 不持数据库、C#/Avalonia 为正式桌面、协议目录单源这些静态守卫通过。但 F04 表明“静态语言门通过”不能代替字段/权限/路径语义的跨语言一致性。

`.project/tasks/issued/` 与 `.project/leases/issued/` 当前受跟踪文件只有 README；配置声明的签发/授权体系没有实际实例。这里登记实施缺口，不因它替本次用户的明确审计指令制造新审批，也不自行生成授权。治理分支只是文档，不能被视作治理系统已经落地。

后端聚合 diff 的真实 GatePlan 要求 **11 个 gate**：`ci-verdict`、`contracts-vnext`、`desktop-build`、`desktop-fast`、`desktop-vnext`、`installer-lifecycle`、`lint`、`py-primary`、`rust-vnext`、`static`、`workers-vnext`；没有 unknown paths。CI 文件改动会触发桌面/安装门，不得因“本轮叫后端”自行忽略。此处只读取要求，没有执行安装、发布或前端修改。

新增 `scripts/release/backend_launcher.py`、`stage_backend_runtime.py`、`check_runtime_isolation.py` 在当前分类中落入 `scripts-other`；若以后只改这些打包入口，分类不一定要求对应 runtime/安装资格。建议归入已有打包风险类，避免另造第二套治理体系。

## 后端闭环逐段判断

| 链路 | 当前可证明 | 尚不能证明 |
| --- | --- | --- |
| P0 / Authority、插件与模型资源 | R6 完整性、静态边界、路由能力注册 | 正式宿主启停/健康/default/fallback/replacement；A02、P0-H01 的局部决策仍未冻结 |
| P1 / Source → worker → Knowledge | Rust API、worker、loss/quality、事务/重启等测试存在且运行 | 全部常用真实格式语义质量、真实库验收；合成文本环不能替代 |
| P2 / Search → Plan → Course | FTS5 与 General 契约/确定性课件投影 | 正式 Rust search 每次查询仍 rebuild FTS，未形成 vector/rerank 生产链；Plan/Course 不在 M0 探针完整实际链中 |
| P3 / Assessment → FSRS | Rust 状态、真实调度 worker 测试、答案与重启回读测试 | 真人学习与评估有效性、完整适应性学习；`mastery.closed=false` 是明确保留语义，不可改 true 来“闭环” |
| P4 / Machine → Correction → Retest | 引用绑定、权限、纠正/重测/重启的局部测试 | 探针明确 `model_version=stub/local-stub`，没有真实推理与用户观察的错误；F01 还允许纠正缺失被掩盖 |
| P5 / Backup、Restore、Migration | Rust 存储/恢复/迁移相关测试；已有历史迁移记录 | 当前最终候选的真实 Legacy 业务语义 diff、完整同身份读回；未读取真实 Legacy 重新跑探针 |
| P6 / Candidate → Green → rollback | 可暂存后端的代码与历史候选说明 | 新启动器有 F02–F04/F07；当前最终聚合候选、前端保持下的完整 journey、Owner Gate、原位替换与回滚均未验证 |

项目 `R6-STATE.json` 仍为 `IN_PROGRESS`、release `FROZEN`。后端分支最新审计索引自己列出插件内部面、多格式深度、Search、学习/领域/课件、undo/revert、模型登记、迁移语义、最终资格及 Green 集成等工程剩余项。不能将这些全部归为 Owner 阻塞；可独立工程修复应继续，只有真正的资源/合同业务决策才交 Owner。

## 本次执行证据

| 检查 | 本次结果与界限 |
| --- | --- |
| SSH fetch / heads | PASS，main=`43c2cafa`，11 个远端 heads |
| PR / Actions API | BLOCKED，`gh pr list`、`gh run list` 均 HTTP 401；仅检查 GH_TOKEN 是否存在，未读取值或修改登录 |
| 架构、语言、路径规范、HEAD 文本规范 | PASS；路径归属 2283/2283 |
| vNext contracts、vocabulary drift | PASS；生成 drift=[] |
| R6 authority | PASS；源摘要与 LF 摘要分别核验 |
| workers-vnext 脚本 | FAIL；linked worktree 输出根与检查器边界不一致（F05） |
| Rust `test --workspace --offline` | PASS，干净 r5 SHA；有编译警告。不把潜在测试内条件跳过当真实格式验收 |
| Rust `fmt --all -- --check` | PASS，execution receipt exit=0 |
| 同次 Rust journey receipt | PASS，schema v3、commit/run/dirty/patch 绑定有效；其 scope 明写 in-process、worker receipt simulated、非 installed qualification |
| Python 全集 `tests integration-tests knowledge_base/tests -q` | **3397 passed / 14 failed / 34 skipped / 137 subtests passed / exit 1**，246.45 秒；不是全绿 |
| 主检出路径相关对照 | **40 passed**；用于确认 linked worktree 差异，不替代后端分支全测 |
| 短 run ID 主链复核 | `--run-id a1` 后 `integration-tests/test_axw_main_chain_e2e.py` **6 passed**；原全集其中 5 个失败是 Windows 长路径触发，不是已证明的业务算法错误 |
| 剩余 Python 失败分类 | 7 个共享运行根约定问题；1 个截图环境断言在全集中失败、主检出定向通过，隔离/顺序影响未完全定位；1 个真实截图 profile cleanup 遇 Windows 文件锁，未判定为稳定产品回归 |
| 最初 Python 探测环境 | UI 测试解释器缺 pymupdf/pptx/openpyxl，结果为 227 passed/2 failed/4 errors/4 skipped；归类环境不匹配，随后用项目既有 .venv 做上述全集，没有安装依赖 |
| 隔离反例 | F01–F04 的逻辑反例可复现；未启动真实模型、未访问真实数据、未生成真实认证凭据 |
| GUI、原位 Green、真实模型、真实 Legacy | NOT_EXECUTED；保持前端与真实数据边界，且探针当前判定不足以签发闭环 |

Rust 的原始 `cargo_test.bat` 本次报 cargo 不在 PATH；直接调用已登记 Cargo 后又遇 SDK `kernel32.lib` 缺少搜索路径。确认工具和 SDK 文件存在后，使用仅本次子进程有效的审计 wrapper 设置已登记 MSVC/SDK 路径，再实际跑通完整 Rust 测试；没有安装软件、改全局 PATH 或修改产品脚本。因此“Rust 测试通过”与“默认 launcher 在当前 shell 一次启动成功”分开记账。

## 可复核位置与后续合并顺序

本次证据根：`.project-local/runs/32a18f7418/`。下列为本次新生成文件，不是历史回执：

- `audit-r5-guards-20260927/artifacts/branch-inventory.json`：全部 refs、SHA、差额、前端路径、patch 等价、合并模拟完整输出和 worktree 提交关系。
- 同目录 `audit_probes.py`、`negative-probes.json`：隔离反例与逐项结果；`branch_inventory.py`：Git 清单复核工具；`audit_cargo.cmd`：本次 Rust 环境 wrapper。
- `audit-r5-full-20260927/artifacts/execution.json`：Python 全集 exit=1 与干净源码身份。测试数量来自本次 pytest 终端结果；该 execution JSON 本身不包含完整 pytest 日志，不能单独证明数量。
- `audit-r5-rust-sdk-20260927/artifacts/execution.json`、`vnext-journey.json`：Rust 成功与同次 journey。
- `audit-r5-fmt-20260927/artifacts/execution.json`：格式检查。
- `a1/artifacts/execution.json`：短运行目录的 6 项主链复核。
- 主检出对照位于 `.project-local/runs/be268a2d33/aroot0927/artifacts/execution.json`。

建议顺序：

1. 以 `dsh/backend-r5` 作为后端唯一候选，先修复 F01–F05/F07，校正 F06；保持前端路径 diff 为零。
2. 将纯格式化、运行时修复、证据门禁与治理说明按可审查写集整理；不要以“全部分支清空”为合并目标。
3. 在最新 main 上形成候选，重跑失败门与受影响测试；最后按真实 GatePlan 验证聚合结果。不能把本报告对 r5 的本地测试转移为未测试合并 tree 的资格。
4. 恢复 API 的正常认证读回后，检查最终 exact-SHA PR、必需检查、保护规则；没有证据时保持 UNVERIFIED。本报告没有授权或执行修改凭据。
5. 已吸收分支不重复并；历史治理、命名、发布分支只做有针对性的差额择取。治理文档若保留，应明确“测量时点/分支”，不反向覆盖 R6/M0。
6. 功能合并与 Local Green Owner 验收分开；Release/tag/真实 Green 替换继续受原边界约束。

回退：本次没有产品代码、提交或远端变化，无需产品回滚。若不保留报告，可单独移除这份新增 Markdown；审计运行产物保留在已忽略目录，不自动清理，尤其不连带清理已有历史资料或共享进程。

最终证据等级：**STRUCTURAL + TESTED_LOCAL（部分通过、存在明确失败）**；不是 `CI_VERIFIED_EXACT_SHA`、新的 `MERGED_MAIN` 或 `INSTALLED_RUNTIME_VERIFIED`。
