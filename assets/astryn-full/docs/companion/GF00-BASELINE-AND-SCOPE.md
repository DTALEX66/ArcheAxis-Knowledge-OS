# GF00 ASTRYN 独立分支接手：基线与范围

计划：`ASTRYN-COMPANION-20261013`（任务包 03-ASTRYN-Companion）｜分支：`feat/astryn-learning-companion-v1`｜日期：2026-10-13

任务包要求（TASKS.json GF00）：读取本仓 AUTHORITY、PROJECT_CONTRACT 与当前 STATUS，核实真实源码和 Git 状态；保持人格、表现与八类端口归 ASTRYN；模型、记忆、任务和权限归主项目；独立任务包与分支，Dev Host 保留为开发工具。产物：**astryn baseline and scope**（本文件）与 **source-ports-readback.json**（同目录）。

## 1. 现场基线（本轮实测，勿从历史推断）

| 项 | 实测值 |
| --- | --- |
| 分支点 | `a21495a29298f0019ac2872f1ddf685071a30630`，`git ls-remote origin refs/heads/main` 与本地 HEAD 逐字符一致 |
| 执行分支 | `feat/astryn-learning-companion-v1`（本轮由 `a21495a` 新建；创建前仓库只有 `main`，工作树干净、无 dirty/untracked） |
| tracked 文件 | 106（`git ls-files \| wc -l`） |
| 远端 | `https://github.com/DTALEX66/ASTRYN`，public |
| CI（main 全量 10 次） | 6 绿 4 红；最新绿 `38394262275 @ a21495a`（Node 20.19 / 22.12 双矩阵）。红：`b42eee2`（38324323712）、`6aa9785`（38325380117）、`ce07148`（38325423442）、`eb1f4b5`（38325589197），逐次归因见 `M0-ACCEPTANCE-TRACKER.md` A18 |
| 门禁 | 收尾重跑 lint/typecheck/test/build；回执 `docs/verification/gates.json`（绑定源码树内容哈希） |
| M0 判定 | 整体 **PARTIAL**（A05 NOT_TESTED、A17 UNVERIFIED、A19 NOT_EXECUTED） |

## 2. 任务包身份与完整性

- 来源：`D:\All projects\Record\03-ASTRYN-Companion-Taskpack.zip`，**6,023,444 字节**，SHA-256 `553db575f2e41c4ae3f20298f4c9c92bb6c11f4d654827cae6a016679e0f94f4`，共 58 条目。
- 解压位置（本地，不入库）：`.project-local/runs/taskpack-03/03-ASTRYN-Companion/`。
- 完整性：随包 `CHECKSUMS.json` 57 个文件逐一比对 SHA-256 与尺寸，**57/57 通过、0 错误**（`.project-local/runs/verify-taskpack-03.mjs` 输出 `verdict: PASS`；包内 `VERIFY_PACKAGE.py` 需要 python3，本机未安装，用 node 等价实现替代）。
- 包内 8 份 `references/astryn-contracts/*.ts` 与本仓 `contracts/` **逐字节一致**：8/8 文件的 git blob sha 与包内 `SOURCE-INDEX.json` 记录相等（`host 0aa5edbf…`、`conversation 67c711a6…`、`memory 83ca8bd1…`、`action 497485c7…`、`context 357c1a36…`、`avatar 5e77ef12…`、`presentation e3e6ef6f…`、`character 29ebf2fa…`）。**包的基线锚定在本仓已推送的 M0 契约上，不引入第二套契约。**

## 3. 范围与所有权登记

- **AST RYN 持有**：人格、陪伴互动、角色表达、渲染呈现、八类 Port 契约（`AstrynHostPort`、`AstrynConversationPort`、`AstrynMemoryPort`、`AstrynActionPort`、`AstrynContextPort`、`AstrynAvatarRenderer`、`AstrynPresentationMode`、`AstrynCharacterProfile`，readback 见 `source-ports-readback.json`）。
- **主项目（ArcheAxis／星环知识系统，内部代号 AAOS）持有**：模型服务、长期记忆、上下文、任务、权限与权威写入。
- **禁止**（继承 PROJECT_CONTRACT.yaml，本分支不放开）：直接写 AAOS SQLite/CAS；第二套正式前端；ASTRYN 侧第二长期记忆主库。Dev Host（`dev-host/`）是开发工具，不是第二正式前端。
- **跨仓边界**：本包 BE01、BE03、BE05、BE06、BE07、BE12 及 FE00–FE25 全部位于 `DTALEX66/ArcheAxis-Knowledge-OS`（`shared/SOURCE-BASELINE.json` 记录主仓基线 `be79ff90…`）。**本分支只写 `DTALEX66/ASTRYN`，不改对方仓库**；宿主逻辑合同由 BE01 统一正式登记（`shared/UI-HOST-CONTRACT-PROPOSAL.json` 现为 `PROPOSED_REQUIRES_BE01_FORMAL_ADMISSION`，33 个逻辑操作均未变成正式 DTO）。
- **执行规则**（按 EXECUTOR_PROMPT）：按依赖拓扑推进；外部任务未完成时继续做不依赖它的资产、组件和视图工作；真实接入记 `BLOCKED_BY_HOST_CONTRACT` / `BLOCKED_BY_BExx` 并指出准确依赖；**不以合成流补齐正式结果**；不为同一用途新建第二套模型中心、记忆库或泛用执行桥。

## 4. 通过条件核对（GF00 acceptance）

| 条件 | 判定 | 证据 |
| --- | --- | --- |
| 不直接写主项目数据库 | PASS | `package.json` 无任何 sqlite/ORM 依赖；`grep -rniE "sqlite\|better-sqlite\|\.db\b" src contracts dev-host` 零命中；唯一出站面是 dev 代理（只绑 `127.0.0.1`，见 `dev-host/server/dev-model-proxy.mjs:167`），M0 对 AAOS 实测为零写入（`docs/architecture/AAOS-HOST-CAPABILITY-MAP.md`） |
| 不把开发夹具当真实集成 | PASS | 合成适配器独立文件（`src/adapters/synthetic-*.ts`）且标注 `SYNTHETIC`；dev-host 与产品入口分离；三类边（权威/观测/合成）由守卫与 `isTaskAuthoritative()` 强制；宿主缺合同处以显式 `BLOCKED_BY_HOST_CONTRACT` 表达，无"用夹具冒充集成"路径 |

## 5. 证据块

- **source_sha**：分支点 `a21495a29298f0019ac2872f1ddf685071a30630`（== 远端 main）；GF00 提交 SHA 见 Git 历史（本文件不自我绑定）。
- **changed_paths**（GF00 净新增／修改）：`docs/companion/GF00-BASELINE-AND-SCOPE.md`、`docs/companion/source-ports-readback.json`、`docs/companion/PROGRESS.json`、`PROJECT_CONTRACT.yaml`（登记本包范围并修正滞后字段）、`docs/verification/gates.json`（收尾重跑刷新）。
- **commands_and_exit_codes**（本轮实际执行）：`git checkout -b feat/astryn-learning-companion-v1` → 0；`node .project-local/runs/verify-taskpack-03.mjs` → 0（PASS 57/57）；`node .project-local/runs/gf00-ports-readback.mjs` → 0；`git hash-object contracts/*.ts`（8 个）→ 0；边界 grep（sqlite/db 依赖与引用）→ 0（无命中）；`gh run list --limit 15` → 0；门禁链 lint 0 / typecheck 0 / test 0 / build 0 / record 0，回执 `docs/verification/gates.json`：`stages {lint:0,typecheck:0,test:0,build:0}`、`allGreen=true`、64 文件、树锚 `04540a6075adae41…`（因 `PROJECT_CONTRACT.yaml` 属回执 rootFiles，本任务编辑后重跑刷新）。本地日志 `.project-local/runs/gate-20261013-215517.log`。另：锚点校验器首跑红（把字节计数 `6023444` 误认为 7 位短 SHA），已修正启发式（纯数字串跳过）后复跑 → 0。
- **artifact_hashes**：`source-ports-readback.json`（8/8 端口，包身份核验 `true`）；任务包 zip sha256 `553db575…94f4`；8 个契约 git blob sha 见 §2。
- **limitations**：① `VERIFY_PACKAGE.py` 未运行（无 python3），以 node 等价校验替代；② 逻辑操作合同未正式化（BE01 未登记），GF04 起的真实宿主接入只能到"适配器 + 负面测试 + 明确 BLOCKED 原因"；③ 真实模型（A05）仍需凭据；④ CI 只对 main 有历史可引，本分支首推后需以新 run 记录。
- **rollback_handle**：本分支从 `a21495a` 线性推进，未改写任何已发布历史；回退 = 停止使用该分支（`git push origin --delete` 需另行授权）或 `git revert` 相应提交；不涉及主仓与远端既有 ref。

## 6. 与既有权威的关系

- `PROJECT_CONTRACT.yaml`：本轮登记 `companion_program`（本包 ID、分支、来源与完整性）并修正三处滞后字段（`git_head`、`remote_ci`、`m0_acceptance` 计数与 A18 状态）。
- 执行进度账本：`docs/companion/PROGRESS.json`（按包内 `PROGRESS-TEMPLATE.json` 模式逐任务回填）。
- 本文件不推翻任何既有权威；与 `docs/current/STATUS.md` 冲突处，以 STATUS 的"现场事实"节与本文件 §1 实测表为准并随后续回填刷新。
