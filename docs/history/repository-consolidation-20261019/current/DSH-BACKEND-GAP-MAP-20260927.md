# DSH 后端差额表（增量，一次性建立）— 2026-09-27

> 用途：对照现行 R6 / M0 与上一轮完整后端任务，把每一项的**当前实现、本轮已验证、
> 仍缺功能、真实依赖、下一项动作**写成一份可续接的差额表。此后只按变更增量更新，
> 不再重复"列缺口—重写总结—再列缺口"。
>
> 基线：后端分支 `dsh/backend-20260927`，本文件写入时的受测提交见 §0。
> 证据：`docs/current/DSH-BACKEND-EVIDENCE-20260927.json`。
>
> **状态词只用项目允许值**：`TESTED_LOCAL` / `TESTED_LOCAL_PARTIAL` /
> `BLOCKED_BY_OWNER_DECISION` / `STRUCTURAL` / `NOT_EXECUTED` / `NOT_VERIFIED`。
> 局部测试通过不写成整体完成。

---

## 0. 源码身份（本轮修正后的唯一读法）

| 概念 | 值 | 说明 |
| --- | --- | --- |
| 授权/任务基线 | `69a3baed13be061f2f8283c6efd4b0e5e80c4d23` | R6 冻结包之后的接续起点 |
| 本轮受测源码 | 见 §0.1 | **不再**把 69a3baed 当作本轮受测源码 |
| runner 自身身份 | `scripts/runtime/dev.py` 属受测源码的一部分，其摘要已进入 `source_patch_sha256` | |
| 执行二进制身份 | M0 回执记录 `core_binary.sha256` | 本轮为 `ce3d8a3e6dc013bd3db59724dd5570e7de07bf093bb64a6bf674d8de2a3d7717` |
| run 身份 | `ARCHEAXIS_RUN_ID` = run 目录名 | 与 receipt 的 `run_id` 必须相等 |

### 0.1 上一轮身份不一致的实测更正

对 12 个 run 的 `execution.json` 逐一核对后确认：

| run | 记录 commit | 实际 dirty | 真实受测对象 |
| --- | --- | --- | --- |
| `5f6db1c05e1c`、`b06fe548b448`、`7c87cb2bd173` | 69a3baed | clean | 69a3baed（成立） |
| `dsh-m0-loop-1/2/3`、`dsh-post-format2`、`dsh-local-receipt-1`、`c85d391a3f03`、`d51f234899d4`、`dsh-post-format` | 69a3baed | **dirty** | 69a3baed＋未提交补丁 |
| `2df5e12b4334` | 9d7a19d0 | clean | 9d7a19d0（成立） |

因此上一轮报告中"M0 正例、receipt 正例、runtime-paths 42、受影响回归 273 绑定
69a3baed"的说法**不成立**：它们实际跑在 69a3baed＋补丁上，而 receipt 只写了 commit，
gate 也接受了。该缺陷已修（§0.2），受影响项已在干净提交上重跑（§0.3）。
**历史回执未改写、未替换**，上面这张表就是更正说明。

### 0.2 已实施的绑定修复

- `dev.py` 新增 `worktree_identity()`：`git diff HEAD --binary` ＋ 未跟踪非忽略文件的
  SHA-256；导出 `ARCHEAXIS_SOURCE_DIRTY`、`ARCHEAXIS_SOURCE_PATCH_SHA256`、
  `ARCHEAXIS_SOURCE_TREE`、`ARCHEAXIS_WORKTREE_ROOT`，并写入 `execution.json`。
- `v01_journey.rs` 的 receipt 升至 `schema_version 3`，携带
  `source_tree`、`source_dirty`、`source_patch_sha256`、`worktree_root`。
- `check_vnext_receipt.py` 逐条检查并按**各自原因**拒绝：schema 身份、schema 版本、
  commit/run 身份、工作区状态、补丁身份、步骤完整性。干净运行打印 `committed <sha>`；
  脏运行打印 `UNCOMMITTED … not a committed-source qualification`。
- **身份冲突不再静默**：环境变量与 run 文件对同一身份名取值不同时直接拒绝
  （普通配置仍然操作者优先）。
- `dev.py --require-worktree PATH`：解析出的工作树根不是指定路径就拒绝运行。

### 0.3 干净身份重跑（提交 `ee015075`，tree `857a2513`）

| 项 | 结果 |
| --- | --- |
| journey receipt（同次运行） | `PASS (committed ee015075fe40)`，`source_dirty=false` |
| M0 全链 26 阶段 | `ok: true`、`chain_stages_verified: true`、`fsrs_schedule_observed: true` |
| Rust 全 workspace | 240 passed / 0 failed / exit 0 |
| `tests/runtime-paths/` | 47 passed / 9 subtests |
| 负例（真实运行） | 谎报 dirty → 拒绝；环境身份冲突 → 拒绝；旧 v2 回执 → `schema_version 2 is not 3` |

---

## 1. M0 26 阶段逐项

来源：`m0-loop-receipt.json`（干净提交运行）＋ `crates/archeaxis-api/src/lib.rs`、
`src/runtime/mod.rs`。**证据类别**列说明该阶段证明的是什么，`fixture` 表示合成输入，
`测试审核动作` 表示审核者身份来自探针而非真人。

| # | 阶段 | 正式服务/命令 | 输入 | 写入/读回 | 断言 | 证据类别 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | import_source | `POST /api/v1/imports` | fixture 文本（合成） | sources 表 / `source_id`+`sha256` | 202 且返回身份 | fixture |
| 2 | enqueue | `POST /api/v1/jobs` | source_id | jobs 表 | 202 且 `job_id` | fixture |
| 3 | execute | `POST /api/v1/jobs/:id/executions` | job_id | attempts/outputs | 202 | fixture + 真实 Python worker |
| 4 | job_settled | 同上，轮询 | — | jobs.state | `succeeded` | fixture |
| 5 | transform_readback | `GET /api/v1/sources/:sid/jobs/:jid/transform` | — | transforms | 200 且 `text_chars>0` | fixture |
| 6 | promote_anchored_knowledge | `POST /api/v1/knowledge-items/from-transform` | transform+anchor | knowledge/anchors | 201，`status=candidate`，`requires_human_review=true` | fixture |
| 7 | knowledge_v3_readback | `GET /api/v1/knowledge-items/:id/v3` | — | 读投影 | 200，`schema_version=3.0.0` | fixture |
| 8 | search | `GET /api/v1/search` | 中文查询串 | 读投影 | 200 且 `count>=1` | fixture |
| 9 | human_accept | `POST /api/v1/knowledge-items/:id/review-decisions` | action=accepted | knowledge.status | 200 | **测试审核动作**（reviewer 由探针提供） |
| 10 | knowledge_v3_after_accept | `GET .../v3` | — | — | `status=accepted`、`owner=human` | fixture |
| 11 | learning_reference | `POST /api/v1/learning/items/:k/references` | knowledge_id | card_references | 201 | fixture |
| 12 | learning_event | `POST /api/v1/learning/events` | 无卡状态 | learning_events | 201，`authority=placeholder_ladder` | fixture |
| 13 | learning_event_replay | 同 12，同 `client_event_id` | — | — | 200 且 `duplicate=true`（幂等） | fixture |
| 14 | assessment | `POST /api/v1/learning/items/:k/assessment` | knowledge_id | assessments | 201，绑定 `knowledge_version` | fixture |
| 15 | answer_recorded | `POST /api/v1/learning/reviews` | 答案＋assessment | learning_events＋fsrs 状态 | 201，`authority=fsrs`，`schedule_state` 非空 | fixture + **真实 FSRS worker** |
| 16 | learning_state | `GET /api/v1/learning/items/:k/state` | — | 读投影 | 200，answer/next_review 一致 | fixture |
| 17 | machine_task_failed | `POST /api/v1/machine/tasks` | 机器身份 | machine_tasks | 201，`outcome=failed` | fixture（**非真实模型**：`model_version=stub/local-stub`） |
| 18 | human_correction | `POST /api/v1/knowledge-items/:id/review-decisions` | action=modified | 后继 knowledge | 200 且返回 `successor_id` | **测试审核动作** |
| 19 | accept_successor | 同 18，action=accepted | — | — | 200 | **测试审核动作** |
| 20 | machine_retest | `POST /api/v1/machine/tasks`（带 `retest_of`） | — | machine_tasks | 201，`outcome=succeeded` | fixture |
| 21 | machine_readback | `GET /api/v1/machine/tasks/:id` | — | — | 200 且 `retest_of` 指回原失败 | fixture |
| 22 | restart_learning_state | 重启 Core，`GET .../state` | 同一 workspace | 跨进程读回 | answer/next_review 保持 | fixture |
| 23 | restart_knowledge_v3 | 重启 Core，`GET .../v3` | — | 跨进程读回 | anchor_id 保持 | fixture |
| 24 | online_backup | `archeaxis-api --maintenance-backup` | 活动库 | 备份文件＋objects | exit 0，`schema_version=6` | 真实二进制 |
| 25 | online_restore | `archeaxis-api --maintenance-restore` | 备份 | 恢复＋`verify_counts` | `verified=true`，计数回到恢复前 | 真实二进制 + 负例（先删 learning_events） |
| 26 | legacy_migration | `app.workspace.migrate`（经探针） | 获批 legacy 副本 | 迁移工作区 | `status=ok`、`legacy_db_kept`、`original_untouched`、`unreadable_tables=[]` | 真实副本（`cognitive_os.sqlite` 一致性副本，sha256 `b318c99e…`） |

**这张表不能替代的结论**：`chain_stages_verified=true` 只说明 26 个阶段都跑过且持久化成立。
它**不**说明：真实语料质量、真实模型推理、真人审核。第 9/18/19 阶段的审核者身份由探针提供，
属于**测试操作**，不得当作真人证据。

---

## 2. 差额映射（A–H）

### A. 资源与插件

| 项 | 当前实现 | 本轮已验证 | 仍缺 | 真实依赖 | 下一动作 |
| --- | --- | --- | --- | --- | --- |
| 外置工具链解析 | `dev.py::external_toolchain()` | 本机实测：MSVC/rustup/tesseract/ffmpeg 全部被正确发现并注入；缺外置根时返回 `{}`（CI 不受影响） | 无 | — | 收敛 |
| 能力/插件注册 | Rust `route_capabilities`（按扩展名选路由与能力） | 8 个路由能力测试通过（拒绝未命名扩展名、二进制容器、未知 kind） | 插件**启停/health** 的 HTTP 面 | `P0-H01` 未冻结 | 保持现状，不新增第二套 provider |
| `/plugins*`、`/models*` 路由 | 不存在 | 契约测试断言其不存在 | 上述路由是否需要，取决于 P0-H01/A02 | Owner 决策 | 局部等待（**不影响**其余 A 项） |

**更正**：上一轮把 `/plugins*` 不存在写成"插件能力不存在/永久不可用"。准确说法是：
Rust Core 有路由能力注册表且已测；**插件生命周期的 HTTP 面**尚未建模，其语义属 P0-H01。

### B. Source / Knowledge / 任务核心

| 项 | 当前实现 | 本轮已验证 | 仍缺 | 下一动作 |
| --- | --- | --- | --- | --- |
| 原始字节身份 | `imports` 返回 `sha256`，重复导入幂等 | M0 阶段 1：`duplicate=true`、同一 `source_id` | 无 | 收敛 |
| 知识版本/锚点/人工接受 | `knowledge-items` + `review-decisions` | M0 阶段 6–10、18–19；`knowledge_v3_projection` 5 项 | 无（语义完整） | 收敛 |
| 任务持久化/幂等/重试/取消 | `runtime_jobs`、`attempts`、`job_atomicity` | Rust 侧 5+3+15 项通过（含取消后迟到结果拒收、重复完成持久化、并发 open 只迁移一次） | 无 | 收敛 |
| 数据库/对象/派生索引一致性 | `backup_safety` 10 项（含 same-count-different-content、FK 损伤、schema 漂移） | 全部通过 | 无 | 收敛 |
| Rust 为唯一 Canonical 写入者 | `check_language_boundaries.py` | 通过：`database owner = crates/ only; workers and desktop shell hold no database handle` | 迁移 Python 入口的写入链见 §H | 见 §H |

### C. 检索与证据

| 项 | 当前实现 | 本轮已验证 | 仍缺 |
| --- | --- | --- | --- |
| 词法检索 `/search` | FTS5 | M0 阶段 8：`count>=1` | 过滤/分页/排序/空结果语义的**逐项**核对；知识修订后索引重建 |
| 向量/rerank/图谱 | **未接线** | — | 需已批准实现与资源；`sqlite-vec` 已在依赖中但检索未用 |
| Research | 明确 unavailable | — | DTO/Provider 未冻结（Owner） |

**更正**：上一轮把"FTS-only"当作检索范围已完成的依据。准确说法：FTS 覆盖
**词法检索**；向量/混合/图谱不在已完成范围内，且其阻塞仅限该调用。

### D. 学习、领域包与课件

| 项 | 当前实现 | 本轮已验证 | 仍缺 |
| --- | --- | --- | --- |
| 知识版本→计划→artifact→题项→答案→Assessment→Mastery/FSRS | 全链存在 | M0 阶段 11–16、22 通过；FSRS 真实调度已观测 | 领域差异内容；CourseManifest 逐条内容审计 |
| `mastery_projection.closed` | **恒 false，合同规定**（`learning.rs:144`："deliberately marked open: review observations and FSRS scheduling do not establish Knowledge truth or a closed mastery claim"） | 源码读取 | 一个**经批准**的 mastery 判定契约（A08 Owner 范围）。**不得**直接改 `true` |
| 课件 artifact | general-only manifest + 确定性渲染投影 | 渲染契约测试通过 | 真实领域内容、可消费 artifact 的有内容验证 |

### E. 机器评估与纠错

| 项 | 当前实现 | 本轮已验证 | 仍缺 |
| --- | --- | --- | --- |
| 失败任务→Correction→Retest→历史关联 | 全链存在 | M0 阶段 17–21；`machine_correction_loop`、`machine_loop_restart` 通过 | **真实模型执行**；真人审核（当前是测试审核动作） |
| 机器身份边界 | `knowledge_actor_guard` 3 项 | 机器不能自我接受、不能写人类学习结果 | 无 |

### F. 模型池与索引

| 项 | 状态 | 说明 |
| --- | --- | --- |
| `/models*` 路由 | **不存在** | 不能据此宣布"模型范围完成"或"永久不可用" |
| 共享模型库 | `D:\All projects\Model library` 已登记 | 本轮**未扫描、未搬迁、未下载**（授权边界） |
| 已批准本地模型真实调用 | `NOT_EXECUTED` | 无真实调用授权/预算；不伪造调用、不切服务 |
| 索引对账/readiness/漂移 | `STRUCTURAL` | 需先确定正式机制，不新增第二套模型系统 |

### G. Research

四项语义（能力边界、`source_revision`、Provider/version、结果状态）**仍无 Owner 决策**。
已生效部分（来源追溯、错误行为、底层检索复用）可继续；未冻结 DTO 不发布。
`unavailable` 是诚实的当前事实，**不是**最终交付。

### H. 备份、恢复、迁移与安装运行

| 项 | 本轮已验证 | 仍缺 |
| --- | --- | --- |
| 在线备份/恢复 | M0 阶段 24–25：真实二进制、`verified=true`、含负例 | 无 |
| 受支持旧库迁移 | 隔离一致性副本上 `MigrationOperator.apply("core.sqlite")` **成功**，`validate` 由拒绝转为 accepted，缺失对象 2→0；原库未写 | **原库升级**需 Owner 单独授权（§4） |
| 迁移写入链 | `app.runtime_entrypoint migrate` 走 `MigrationOperator`，Rust 侧不参与该 Python 基线 | 需明确该 Python 入口是否属"迁移专用例外"；`check_language_boundaries` 通过说明 worker/desktop 不持库句柄 |
| wheel 构建/安装后运行 | 见 §3 | 依赖锁定安装需要 `uv`（本机未安装）；`services/python-workers` 不在 wheel 内 |

---

## 3. 独立后端打包与安装后运行（本轮完成）

| 项 | 结果 |
| --- | --- |
| 构建来源 | 提交 `ee015075`，工作树干净 |
| 构建前端 | 锁定的 PEP 517 后端 `setuptools==83.0.0`（`[build-system].requires` 与 `build` 依赖组一致）。**本机未安装 `uv`**，故未使用 CI 的 `uv build`；未下载任何工具 |
| wheel 身份 | `archeaxis_workspace-0.6.14-py3-none-any.whl`，sha256 `a97d326127e3d5b7e49710d671626853376649e24a7de84d09d33b918aebbfc4`，728,030 字节，367 成员 |
| 内容核验 | 12 项必需成员齐全；禁止项（tests/cache/pyc/.env/sqlite）0；复用仓库既有 wheel-smoke 规则 |
| 元数据 | `Name=archeaxis-workspace`、`Version=0.6.14`、`entry_points: archeaxis = app.cli:main`、`Requires-Dist` 36 条（含 `pyyaml`、`fastapi`、`sqlite-vec`、`fsrs`） |
| 隔离位置 | `D:\All projects\AAOS-DSH-WHEEL-QUAL\ee015075\`（**仓库之外**，临时资质目录，非第二正式安装） |
| 遮蔽核验 | 隔离 venv 中 `app`/`shared`/`config`/`knowledge_base`/`inspiration_research` 全部解析到隔离 site-packages；**发现**项目 venv 存在指向根 checkout 的 editable 安装（`__editable__.archeaxis_workspace-0.6.14.pth`）——已隔离，未生效 |
| 安装后运行 | `python -m app.runtime_entrypoint migrate` exit 0，创建 999,424 字节工作区；**第二次 migrate 幂等**（同指纹、同备份、无重复应用）；`archeaxis health` exit 0 |
| 安装产物读回 | 97 表、`kb_attachment_facts` 存在、`integrity_check=ok`、0 外键违规、6 个 owner `applied`、schema 基线 = `python_compatibility` |
| 依赖来源 | 从**已批准的本地项目环境**以纯路径 `.pth` 供给（无下载）。完整的锁定依赖安装需要 `uv export`，本机无 `uv` |
| `release-manifest.json` 的 `source.commit` | `unavailable` — **符合设计**：`release_inject_identity.py` 明确"tracked manifest 永远 unavailable，只有 release artifact 注入真实身份"，且需要 tag/Release URL/CI run。发布 FROZEN，**未伪造**发布身份；候选源码身份由资质记录承载 |
| 明确缺口 | `services/python-workers/**` **不是** wheel 成员，因此"从 wheel 跑完整 M0"当前不可行；M0 由源码构建的 Core＋worker 资质，安装资质覆盖 Python 后端基线 |

---

## 4. 仅剩的 Owner 决策 / 授权（互相独立，不合并）

1. **A02** 资源根 / schema 语义。
2. **P0-H01** Provider/Host 身份与生命周期 D1–D6。
3. **DP-F01** typed loss receipt D1–D5。
4. **DP-A11 / Research** D1–D5 与 DTO 冻结。
5. **是否授权把已验证的 baseline 修复应用到 Owner 原库**（隔离副本已证明成功）。
6. **原库中 2026-09-27T05:40:12Z 的 failed apply** 由谁发起（调查线索：该时间与
   `data/archeaxis.sqlite` 的 mtime 13:40:12+08:00 和锁文件一致；无命令回执可归因，
   因此**记为未知**，不默认归因某个 Agent）。
7. **远端 push / CI 触发**授权（本分支未推送）。
8. **原 Green 替换**授权；公开 release 解冻。
9. **真实语料**、**真实模型/Provider 调用**、**付费 API** 的授权与资源。
10. 若要让"从 wheel 跑 M0"成为事实，需要决定 `services/python-workers/**` 是否纳入打包范围。

---

## 5. 本轮未执行（不得升级为通过）

真实语料逐格式验收；真实模型推理；GUI/UIA/键盘/DPI（Codex）；原 Green 替换；
远端 CI；受支持旧库的**原库**升级；向量/混合检索与图谱；Research 实现。
