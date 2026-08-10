# ArcheAxis OS 验证闭环提速 × WORK-LAB 全局兼容：HERMES 增量任务包

> 仓库：`DTALEX66/Cognitive-Loop-OS`
> 审计基线：`main@ff667d1450e17bc5469902ec2415d756df8209a6`
> 编制日期：2026-08-07
> 文档性质：OS 主任务包的 MS00 横切增量，不替代 MS00–MS11 产品路线
> 执行者：HERMES 为唯一 writer；Codex 只读复审
> 目标：保持发布级可信度，同时消除普通 PR、main 和重复审计中的无效重跑
> 兼容：WORK-LAB 未升级时 OS 可独立运行；升级后可无损进入受管模式

---

## 0. 执行摘要

### 0.1 定位校验头

本任务包开始前必须重复确认：

```text
产品定位：Human–AI Learning & Knowledge System
当前最小闭环：全面兼容、吸收同类软件的成熟能力
第一高保真纵切：Obsidian Vault / Markdown / JSON Canvas
实施原则：合法依赖、SDK/API/CLI、fork/vendor、Adapter/sidecar 优先；自研最后
延期：通用 Agent Runtime、多 Agent、Marketplace、3D/VR、企业协作等重型蓝图
```

本任务包只优化开发、审计、CI 和 Release 证据链，不改变产品定位，不进入 OS Runtime，不替代 Obsidian/开放格式兼容主线。

### 0.2 一页结论

当前规则不是“不安全”，而是把 Release 级门禁错误地应用到每一个 PR 和每一次 main push：

- 每个 PR 和 main push 都无条件执行完整 9-job。
- 同一批 1115 项 Python 测试在 3.11、3.12、3.13 上重复为 3345 项。
- `desktop-shell` 约 11.1 分钟，是整条 CI 的关键路径。
- 样本 PR 约 11 分 49 秒；相同 tree 合并 main 后又约 11 分 53 秒，总闭环约 23 分 42 秒。
- Python 单版本全部测试本体约 45 秒，并不是当前主瓶颈。
- 仓库文档已经规定“最少但足够验证”和“禁止为了放心重复相同门禁”，CI 实现却没有执行该政策。

最终策略：

```text
强门禁保留
  + 按变更风险选择执行频率
  + TaskPack 显式门禁只能追加
  + 未知/高风险自动 full
  + PR 已验证 merge tree 可向 main 转移证据
  + Release 永远执行 exact-SHA 完整资格验证
```

### 0.3 预期结果

基于当前样本，不作为 SLA：

| 变更类型 | 当前典型闭环 | 改造后目标区间 |
| --- | ---: | ---: |
| 普通 Python/后端 | 约 23–24 分钟 | 约 3–5 分钟 |
| UI/Windows | 约 23–24 分钟 | 约 4–6 分钟 |
| Rust/Tauri 非安装器 | 约 23–24 分钟 | 目标低于完整 NSIS 路径 |
| Installer/Release | 约 8–12 分钟以上 | 保持完整门禁，不以速度换证据 |

普通变更预期减少约 75%–90% 的闭环等待；最终只认上线后的真实 queue/setup/test/build 数据。

---

## 1. 与既有主任务包的关系

### 1.1 必须继续继承

1. OS 不是旧“认知闭环系统”，也不是通用 Agent OS。
2. 当前最小面是全面兼容吸收；Obsidian 是第一纵切，不是整个阶段边界。
3. MS04 的 C3 往返、MS05 的真实 browser/Tauri 主路径、MS10 的恢复/安全/性能、MS11 的安装器与正式发布证据不得削弱。
4. HERMES 单 writer、Codex 只读审查；一次只执行一个 TaskPack。
5. 禁止 `reset --hard`、force push、移动历史 tag、覆盖他人提交、扫描个人 Vault/E 盘或项目外目录。
6. 源码复用阶梯、许可证、SBOM、NOTICE、精确 upstream commit、升级与回滚记录继续生效。
7. 外部输入先进入 staging/candidate，不得自动晋升 verified truth。
8. 真实运行、往返 fixture、重启读回、冲突、回滚、安装器与下载哈希仍是完成证据。

### 1.2 本文件覆盖的旧表述

| 旧表述 | 新解释 |
| --- | --- |
| 每个 TaskPack 都跑 unit/integration/browser/Tauri/restart/roundtrip | 执行“路径风险门禁 ∪ TaskPack 显式门禁 ∪ 全局不可绕过门禁” |
| PR 和 main merge SHA 都重复完整 CI | PR prospective merge tree 执行所需门禁；main 有同 tree 有效证明时只绑定，无证明时 full |
| 完整 CI 等于固定 9-job | 使用逻辑 profile `full-qualification`；job 数允许演进 |
| exact-SHA 就等于重新跑完整矩阵 | 区分 exact identity binding、selective validation、full qualification |
| `a0-gates` 静态要求所有 job success | 稳定 `ci-verdict` 校验“必跑成功、合法非必跑可 skipped” |

### 1.3 插入产品路线的位置

```text
当前仍在执行的 MS00 子任务先收口
  → TP-MS00-CI-00～04（本任务包 P0）
  → 立即返回 MS01–MS04 兼容主线
  → TP-MS00-CI-05 可作为专项优化插入
  → WORK-LAB 后期执行 WL-VERIFY 系列
```

如果 `feat/ms00-b-version-state` 或其他 OS writer 任务仍在执行，本任务包不得并行写入；先完成、合并或明确关闭当前任务，再从最新 main 建分支。

---

## 2. 当前事实与根因

### 2.1 当前工作流事实

当前 `.github/workflows/ci.yml` 只监听 `pull_request → main` 和 `push → main`，没有：

- changed-path 风险分类器；
- PR concurrency 和 stale-run cancellation；
- schedule/nightly；
- manual full；
- `merge_group`；
- main tree 证据复用。

每次均运行：Python 3.11/3.12/3.13、lint、wheel-smoke、browser-smoke、windows-runtime-smoke、desktop-shell、a0-gates。

### 2.2 真实成本排序

| 项目 | 审计事实 | 处理方向 |
| --- | --- | --- |
| desktop-shell | 约 11.1 分钟，决定关键路径 | 分 desktop-fast/build/installer-lifecycle |
| Tauri release + NSIS | desktop 中占比过半 | 只在 bundle/installer/RC/Release 触发 |
| Python 三版本 | 同一 1115 项重复三次 | 普通 PR 主版本全量；兼容矩阵按风险/nightly |
| Chromium | 真正 smoke 很短，安装可达约 123 秒 | UI 才触发并缓存浏览器版本 |
| `ci` 依赖组 | test×3、lint、browser、Windows 重复安装 | 拆最小依赖组 |
| main push | 同 tree 再跑完整矩阵 | 有条件 tree proof → main bind |
| PR 连续更新 | 旧运行不取消 | PR-only concurrency cancellation |

### 2.3 实现与政策冲突

`docs/VERIFICATION_POLICY.md` 已要求最少但足够验证、禁止重复相同门禁、普通开发按影响面验证、阶段/RC/Release 才累计完整验证。当前 CI、`tests/test_ci_a0_gates.py` 和 `tests/test_verification_performance.py` 却把“所有 PR 全量”锁死。

本任务包的性质是 **policy-to-CI parity 修复**，不是降低安全标准。

### 2.4 隐性债务

以下文件名称像 pytest 测试，但当前没有实际 pytest 测试函数：

- `tests/test_workspace_browser_delivery.py`
- `tests/test_workspace_browser_failure_retry_replay.py`
- `tests/test_workspace_delivery_lifecycle.py`

前两个在收集时导入 Playwright，却不执行对应浏览器场景。HERMES 必须先确认用途，再迁到 `scripts/`、改名或转换为真实测试；禁止直接删除而丢失意图。

### 2.5 必须保留的安全优点

- GitHub Actions 固定完整 commit SHA；
- `persist-credentials:false`；
- 依赖锁和 hash 校验；
- 最小 workflow 权限；
- wheel 外部安装、Windows、Tauri/NSIS 生命周期和 Release 资产回读。

优化目标是减少错误触发，不是删除这些能力。

---

## 3. OS × WORK-LAB 兼容架构

### 3.1 控制平面—项目平面边界

```text
WORK-LAB 控制平面
  全局策略 / TaskPack / 通用风险词汇 / 证据 Schema / 审查编排 / 指标
            ↓ 只交换版本化声明、符号化 Gate ID 和证明
OS 项目平面
  路径映射 / 真实测试命令 / 项目 fixture / Windows/Tauri / Release / 产品运行时
```

硬边界：

- WORK-LAB 不进入 OS wheel、Tauri bundle、installer 或用户数据目录。
- WORK-LAB 不读取、保存或上传用户 Vault、笔记、附件和真实本机路径。
- WORK-LAB 不能向 OS 远程注入任意 shell，只能选择 OS 预登记的 Gate ID。
- OS 的 Obsidian C3、冲突、回滚、重启读回等项目门禁永远由 OS 定义。
- HERMES 仍是唯一 source writer；WORK-LAB 不成为第二 writer。
- WORK-LAB 只能增加门禁，不能削弱 OS 本地或 Release 要求。

有效门禁：

```text
effective_gates
= global_non_bypassable_gates
∪ OS_project_required_gates
∪ taskpack_explicit_gates
∪ event_or_release_mandatory_gates
```

### 3.2 Standalone / Managed 双模式

#### Standalone（强制存在）

- WORK-LAB 不存在、离线或升级失败时，OS 仍能完成分类、PR、main、full qualification 和 Release。
- OS 产品运行时从不依赖 WORK-LAB 登录或在线状态。
- 本地 project profile 是 OS 最终风险真相源。

#### Managed（后期可选）

- WORK-LAB 读取 OS 的版本化 profile。
- WORK-LAB 计算建议 Gate 集并聚合证据。
- OS 受信 CI 使用本地 profile 再算一次并保留最终否决权。
- 同一变更在 managed 模式下必须等于或严格大于 standalone Gate 集。

失败时：

```text
WORK-LAB 不可用/不兼容/少选 Gate
  → OS 本地重算
  → 普通 PR 回 standalone
  → 分类不确定回 full-qualification
  → Release 阻断或在 exact SHA 完整重跑
```

### 3.3 责任矩阵

| 能力 | WORK-LAB | OS |
| --- | --- | --- |
| 通用风险类别 | 定义词汇与最低线 | 将真实路径映射到类别 |
| 测试命令 | 不持有、不注入 | 定义并执行 |
| Gate ID | 提供跨项目注册规范 | 登记本项目实现 |
| 全局政策升级 | 版本化发布 | 通过显式 PR 固定版本/digest |
| 证据格式 | 定义 Schema | 受信 CI 生成原始证据 |
| 汇总 | 跨项目聚合 | `ci-verdict` 最终校验 |
| Release | 核验前置证明 | 构建、安装、下载回读和发布 |
| 用户资料 | 禁止接触 | 在本地安全边界内处理 |

### 3.4 OS 仓库兼容声明

建议建立：

```text
.worklab/
  project-validation.v1.yaml
  gate-registry.v1.yaml
  ci-impact.v1.yaml
  schema-lock.json
```

这些文件只保存项目声明和固定 schema digest：

- 不复制 WORK-LAB 状态机、数据库或 Agent 工程设施；
- 不包含凭据、用户路径和用户内容；
- 明确排除出 wheel、Tauri resources 和 installer；
- WORK-LAB 未完成时由 OS 本地最小执行器读取；
- WORK-LAB 完成后由 reusable workflow/控制面读取同一份声明。

建议合同：`GlobalValidationPolicyV1`、`ProjectValidationProfileV1`、`GatePlanV1`、`EvidenceEnvelopeV1`、`TreeProofV1`。

### 3.5 版本和能力协商

```yaml
contract_version: "1.0"
project_id: "DTALEX66/Cognitive-Loop-OS"
controller_protocol: ">=1.0,<2.0"

modes:
  standalone: required
  managed: optional

required_capabilities:
  - risk-routing.v1
  - evidence-envelope.v1
  - tree-proof.v1
  - exact-sha-release.v1

fallback:
  unknown_change: full-qualification
  controller_unavailable: standalone
  invalid_evidence: full-qualification
```

- major：破坏性字段或语义变化；不认识的 major 必须 full/阻断。
- minor：向后兼容的可选字段或风险类别。
- patch：校验/文档修正，不改变 Gate 选择。
- 未知 optional 字段可忽略；未知 `required_feature`、Gate 或路径必须 fail closed。
- Schema、Global Policy、reusable workflow 必须固定完整 commit/digest，不跟随 `main`。
- 破坏性升级必须经历 shadow 双读和至少一个完整 release train。

### 3.6 稳定 Gate ID

| Gate ID | 语义 |
| --- | --- |
| `static` | convention、architecture、静态规则 |
| `lint` | Ruff/JS syntax/项目扫描器 |
| `py-primary` | 主 Python 版本完整 OS/KB/integration |
| `py-compat` | 支持版本兼容矩阵 |
| `browser-smoke` | 真实 Chromium 工作区 smoke |
| `windows-runtime` | Windows migration/runtime/HTTP |
| `desktop-fast` | cargo fmt/test、快速 backend lifecycle |
| `desktop-build` | Tauri release build |
| `installer-lifecycle` | NSIS 构建、安装、退出、升级/卸载 |
| `wheel-smoke` | wheel 构建、外部安装和 package-data |
| `obsidian-roundtrip` | 后续 MS04 项目专属 C3 fixture |
| `ci-verdict` | 始终出现的 required aggregator |
| `main-bind` | main SHA/tree 证据绑定 |
| `full-qualification` | 当前注册表中全部强制资格门禁 |
| `release-verify` | tag/asset/installer/download readback |

当前外部 required check 可暂时保留 `a0-gates` 名称，内部语义改为 `ci-verdict`；仓库 owner 更新 branch protection 并验证新 context 后再正式改名。

`full-qualification` 是逻辑 profile，不以“9-job”作为永久合同。未来增加 Python 3.14 或拆分 desktop 后，profile 可以升级而不破坏 WORK-LAB 接口。

---

## 4. 风险分类与目标门禁矩阵

| 风险类别 | 典型范围 | 必跑 Gate |
| --- | --- | --- |
| docs/mechanical | 文档、账本、无运行语义格式 | `static + ci-verdict` |
| ordinary-python | 普通 Python 业务 | `static + lint + py-primary + ci-verdict` |
| ui | UI 资源、交互、UI 消费的 BFF/API | ordinary-python 基线 + `browser-smoke` |
| windows-runtime | Windows 存储、迁移、进程、路径 | ordinary-python 基线 + `windows-runtime` |
| rust-tauri | Rust/Tauri 非打包逻辑 | `static + desktop-fast`；按调用面追加 Python |
| desktop-build | Tauri build/config/resources | `desktop-fast + desktop-build` |
| installer | bundle、stage、NSIS、退出/卸载 | `desktop-fast + desktop-build + installer-lifecycle` |
| wheel-packaging | package-data、entry point、wheel 配置 | ordinary-python 基线 + `wheel-smoke` |
| python-compat | `pyproject`、`uv.lock`、公共 Python 合同 | `lint + py-compat + wheel-smoke` |
| cargo/npm-deps | 对应 lockfile/生态依赖 | 对应 Rust/npm Gate；不机械触发 Python matrix |
| db/migration | schema、迁移、数据恢复 | `full-qualification` + 独立审查 |
| security/permissions | 权限、secret、SSRF、路径边界 | `full-qualification` + 独立审查 |
| ci-policy | `.github/**`、`.worklab/**`、分类器、Gate 脚本 | `full-qualification` |
| unknown | 未识别、缺 diff、无法判定的 rename/delete | `full-qualification` |
| nightly/manual/RC | 定时、手动 full、发布候选 | `full-qualification` |
| formal-release | 正式 tag | exact-SHA full + `release-verify` |

统一规则：

1. 多类别修改取 Gate 并集，不允许只选一个最轻类别。
2. TaskPack 可以追加 Gate，不能删除分类器或全局要求。
3. `full` 必须展开为当时 registry 中明确 Gate 列表，不能只写一个字符串后默认成功。
4. 普通 Python 先跑完整主版本，不急于建设复杂 affected-test 图谱；当前收益太低、漏测风险更高。
5. OCR/FFmpeg 等系统行为普通情况下只在主版本真实验证一次；其他 Python 版本聚焦语言和依赖兼容。
6. 项目当前 `requires-python >=3.11` 无上限，却只测到 3.13；必须在兼容/nightly 中增加 3.14，或明确限制 `<3.14`。
7. Desktop lifecycle 已存在非确定性记录；在稳定性门禁完成前，desktop/installer tree proof 不进入复用白名单。

### 4.1 GatePlan 的确定性要求

分类器输入必须来自真实 base/head diff，并支持：

- 新增、修改、删除、重命名；
- 混合类别变更；
- base 缺失或浅克隆补全失败；
- CI/分类器自修改；
- TaskPack 显式 Gate；
- owner 触发的 `CI_FORCE_FULL=true`。

禁止使用 LLM 自由判断作为合并门禁。LLM 可以给出风险提示，但最终 GatePlan 必须由版本化规则、真实路径、合同语义和显式 TaskPack 字段确定性生成。

### 4.2 OS 产品专属门禁的后续扩展

进入 MS03/MS04 后，以下变化必须由 OS profile 追加专项 Gate：

| 项目范围 | 追加 Gate |
| --- | --- |
| Compatibility Kernel contracts/schema | contract + migration + roundtrip fixture |
| Obsidian/Markdown parser/exporter | `obsidian-roundtrip` |
| JSON Canvas | Canvas import/export semantic diff |
| approved roots/路径安全 | security + Windows path fixtures |
| import/export/rollback | crash/resume/rollback fixtures |
| Release manifest/版本身份 | full qualification + release contract |

WORK-LAB 只理解这些 Gate ID 和结果，不拥有其真实命令与 fixture。

---

## 5. 目标 GitHub 工作流

### 5.1 四种语义完全分离

1. `PR Selective CI`
2. `Main Evidence Bind`
3. `Full Exact-SHA CI`
4. `Release`

不得继续用一个模糊名称 `CI` 同时表达轻量合并门禁和完整发布资格。

### 5.2 稳定聚合门禁

`ci-verdict` 必须始终创建，并使用 `if: always()` 语义校验：

- GatePlan 可读取且 digest 正确；
- required Gate 全部 `success`；
- 只有明确 `not-required` 的 Gate 才能 `skipped`；
- required Gate 的 skipped/cancelled/failure/missing 均失败；
- 分类器错误、未知合同、证据缺失均失败；
- 不对 required workflow 使用会让整个 check 消失的顶层 `paths`。

### 5.3 Concurrency

只对同一 PR 的旧运行启用取消：

```text
pull_request synchronize → cancel older run for same PR
main / Full Exact-SHA / RC / Release → never auto-cancel
```

失败后优先重跑失败 job；禁止通过关闭/重开 PR 无差别重启完整 workflow。

### 5.4 Tree proof 与 main bind

当前仓库暂不把 Merge Queue 当作前置条件：

1. 优先使用 GitHub `pull_request` 的 prospective merge ref；
2. 仓库未来迁移组织且启用 Merge Queue 后，再兼容 `merge_group`；
3. 禁止只证明普通 PR head。

`TreeProofV1` 至少绑定：

```text
repository / event / PR number
base_sha / head_sha / tested_commit_sha / tested_tree_sha
changed_paths_digest
global_policy_version + digest
project_profile_version + digest
classifier/workflow digest
risk classes / required gates / reason codes
每个 Gate 的 conclusion / run / artifact digest
runner labels/environment epoch
producer workflow/run/attempt/time/expiry
privacy flags / proof digest
```

main push 算法：

```text
计算 main commit/tree
  → 找成功且受信的 PR merge-ref/merge-group proof
  → 校验 tree、base/head、policy、workflow、Gate 集、来源、有效期
  → 全部一致：执行 Main Evidence Bind
  → 任一不一致：自动 Full Exact-SHA CI
```

个人仓库初期采用 merge-commit 强约束时，应额外核对：

```text
after^1 == push.before == proof.base_sha
after^2 == proof.head_sha
after^{tree} == proof.tested_tree_sha
```

若使用 squash/rebase 或父关系无法证明，先 full fallback，后续另建兼容 TaskPack。

### 5.5 Tree 复用不能覆盖

- commit message、父提交、tag、ref、commit count；
- `git describe` 和 commit-sensitive 版本逻辑；
- secrets、repository variables、ruleset；
- runner image、时间、外部网络服务；
- 正式 Release；
- 当前未稳定的 desktop lifecycle。

所以 `main-bind` 只能称为证据绑定，不能写成 full exact-SHA test。

### 5.6 启用 main bind 的仓库前置条件

仓库 owner 必须人工确认：

- main 要求分支保持 up-to-date；
- 禁止直接 push、force push；
- 尽可能禁止 admin bypass；
- required check 指向稳定 aggregator；
- `.github/**`、`.worklab/**`、分类器、锁文件、Release 脚本有 CODEOWNERS/强审查；
- 合并策略与 proof 算法一致。

无法确认任一关键条件时，证明可以生成，但 main bind 保持关闭并自动 full。

### 5.7 Release 硬边界

当前 `release.yml` 不能继续只查“同 SHA、workflowName=CI、success”。必须核验：

```text
qualification profile == full-qualification
qualification exact SHA == tag target == 发布 main SHA
required Gate 列表与结论完整
proof/attestation digest 正确
```

Release identity 必须分开：

- `verification_ci_run_id/url`
- `release_run_id/url`

正式发布继续保留 installer、asset 集合、provider digest、SHA256SUMS、下载后复算、manifest readback、安装/启动/重启/退出/卸载和回滚证据。

---

## 6. 统一证据合同

### 6.1 GatePlanV1 示例

```json
{
  "schema": "dtalex.verification/gate-plan/v1",
  "repository": "DTALEX66/Cognitive-Loop-OS",
  "event": "pull_request",
  "base_sha": "...",
  "head_sha": "...",
  "tested_commit_sha": "...",
  "tested_tree_sha": "...",
  "policy_digest": "sha256:...",
  "workflow_digest": "sha256:...",
  "changed_paths_digest": "sha256:...",
  "risk_classes": ["ordinary-python"],
  "required_gates": ["static", "lint", "py-primary", "ci-verdict"],
  "unknown_paths": [],
  "reason_codes": ["PATH_APP_PYTHON"],
  "mode": "standalone",
  "force_full": false,
  "fallback_reason": null
}
```

### 6.2 EvidenceEnvelopeV1 示例

```json
{
  "schema": "dtalex.verification/evidence-envelope/v1",
  "subject": {
    "repository": "DTALEX66/Cognitive-Loop-OS",
    "event": "pull_request_merge_ref",
    "tested_commit_sha": "...",
    "tested_tree_sha": "...",
    "base_sha": "...",
    "head_sha": "...",
    "pull_request": 0
  },
  "policy": {
    "global_policy_version": "standalone-v1",
    "global_policy_digest": "sha256:...",
    "project_profile_version": "1.0",
    "project_profile_digest": "sha256:...",
    "classifier_digest": "sha256:..."
  },
  "decision": {
    "risk_classes": [],
    "required_gates": [],
    "reason_codes": []
  },
  "results": [],
  "producer": {
    "workflow_name": "PR Selective CI",
    "workflow_ref": "...",
    "workflow_run_id": "...",
    "run_attempt": 1,
    "generated_at": "..."
  },
  "privacy": {
    "contains_user_content": false,
    "paths_redacted": true
  },
  "integrity": {
    "canonicalization": "RFC8785",
    "digest": "sha256:...",
    "attestation": "optional-v1-required-in-managed"
  }
}
```

### 6.3 兼容与隐私规则

- v1 本地 proof 只接受同仓库、受信 workflow、成功 run、短有效期，建议不超过 24 小时。
- WORK-LAB managed 阶段升级为固定 reusable workflow 生成的签名 attestation。
- PR 中的任意脚本不能控制签名身份或伪造必跑结果。
- 禁止用 `pull_request_target` 以高权限执行未受信 PR 代码。
- Evidence 只包含 repo 级路径 digest 和脱敏指标，不包含 Vault 内容、文件正文、凭据或本机绝对路径。
- 旧 Evidence 缺少 tree、policy digest、Gate 明细时只可展示，不能用于 main reuse 或 Release。

---

## 7. 全局故障降级矩阵

| 故障 | 强制行为 |
| --- | --- |
| WORK-LAB 不可用 | OS standalone 继续 |
| Controller major 不兼容 | 拒绝 managed，回本地 profile |
| Schema 获取失败 | 使用固定 digest 离线副本；仍失败则 full |
| Work-Lab 选择 Gate 少于 OS | `ci-verdict` 失败 |
| 未知路径/分类冲突/缺 diff | full-qualification |
| Tree proof 缺失、过期、损坏 | main exact-SHA full |
| 只有 PR head proof | 禁止复用 |
| workflow/policy/classifier 变化 | full-qualification |
| runner/browser/Windows 故障 | 相关变更保持阻断，不伪造通过 |
| Nightly 发现选择性漏测 | 启动 kill switch，普通 PR 临时 full |
| Release 只有 main-bind | Release 拒绝 |
| Release 资产回读失败 | 保持 draft，不发布 |
| 缓存异常/污染 | cache miss 重建；资格验证不信任发布缓存产物 |

统一 kill switch：

```text
CI_FORCE_FULL=true
```

它只能增加验证，不能绕过 Gate。

---

## 8. OS 原子执行 TaskPack

唯一允许顺序：

```text
TP-MS00-CI-00 只读基线
  → TP-MS00-CI-01 合同/Shadow/取消陈旧运行
  → TP-MS00-CI-02 选择性 PR 门禁
  → TP-MS00-CI-03 Release 与 Full Qualification 隔离
  → TP-MS00-CI-04 Tree Proof 与 Main Bind
  → 返回 MS01–MS04 产品主线
  → TP-MS00-CI-05 Desktop/依赖专项优化（按需要插入）
  → TP-MS00-CI-06 affected-tests（条件触发，默认延期）
```

`CI-03` 必须早于 `CI-04`，否则轻量 main binder 可能被 Release 错认成完整资格验证。

### TP-MS00-CI-00｜基线冻结与执行前置

**性质**：只读预检；不创建代码 PR。

**目标**：从最新云端事实开始，不把 2026-08-07 的审计 SHA 偷换成执行基线。

**动作**：

1. `fetch origin`，记录最新 main commit/tree、工作树 dirty 状态和活动分支。
2. 核对是否仍有 `feat/ms00-b-version-state` 或其他 writer 任务。
3. 记录当前 required check、branch protection、merge/squash/rebase 策略。
4. 记录 `.github/workflows/ci.yml`、`release.yml`、验证政策和 meta-tests 当前 hash。
5. 读取最近有代表性的 PR/main run，记录每个 job 的 queue/setup/test/build 时间、cache hit、重跑和失败原因。
6. 确认 Actions artifact 读取能力、main proof 可用来源和当前账号能否使用 Merge Queue。
7. 输出当前完整 Gate 注册表，不以“9”作为永久真相。

**验收证据**：

- exact base commit/tree；
- required checks 与仓库合并规则的 API 输出或截图；
- workflow run URL/ID 和 job timing 表；
- 活动 writer/分支结论；
- 本任务是否允许开始的明确 `GO/STOP`。

**停止条件**：

- 另一个 writer 正在修改 OS；
- main 与审计基线存在无法解释的 CI/Release 变化；
- 工作树含本任务外未归属修改；
- required checks/合并策略无法确认；
- 执行需要跨仓库写入或额外权限。

停止只报告 blocker，不擅自修改仓库设置。

---

### TP-MS00-CI-01｜验证合同、Shadow 分类与陈旧运行取消

**建议分支**：`chore/ms00-ci-01-contract-shadow`

**目标**：建立确定性 GatePlan 和 WORK-LAB 兼容输出，先不减少任何现有门禁。

**允许范围**：

- `.github/workflows/ci.yml`
- `docs/VERIFICATION_POLICY.md`
- `tests/test_ci_a0_gates.py`
- `tests/test_verification_performance.py`
- 新增 `.worklab/**`
- 新增 `scripts/ci/**` 或仓库既有同类工具目录，二选一，不建立平行实现
- 新增验证合同、classifier 与 fixture 测试

**禁止范围**：

- OS 应用 Runtime；
- 数据库/产品迁移；
- Tauri 产品行为；
- Obsidian/Compatibility Kernel 功能；
- WORK-LAB 仓库写入。

**先写 RED**：

1. docs-only 被错误识别为 full；
2. ordinary Python 漏掉 `py-primary`；
3. UI 漏 browser；
4. Windows 漏 Windows smoke；
5. Desktop/Installer 漏对应 Gate；
6. packaging/dependency 漏 wheel/compat；
7. `.github/**`、`.worklab/**`、分类器自身未触发 full；
8. unknown path 被轻量放行；
9. mixed change 没取并集；
10. rename/delete 漏分类；
11. 缺 base SHA 或完整 diff 时未 full；
12. 未知合同 major 未 fail closed；
13. TaskPack 显式 Gate 被分类器删减。

**实现**：

1. 增加同 PR stale-run cancellation；main/full/release 不取消。
2. 建立 `.worklab/project-validation.v1.yaml`、Gate Registry、impact policy 和 schema lock。
3. 建立确定性 classifier，输出 GatePlanV1 artifact 和 Job Summary。
4. 当前仍运行完整现有矩阵，classifier 只处于 `shadow`。
5. 将 `tests/test_ci_a0_gates.py` 从“硬编码所有 job/版本”改成合同真值测试。
6. 将 `tests/test_verification_performance.py` 从“要求重复安装 ci 组”改为验证分层依赖和性能政策。
7. 记录每个 job 的 setup/test/build/total、cache hit、risk class、selected gates。
8. 确保 `.worklab/**` 不进入 wheel/Tauri/installer。

**GREEN 验收**：

- 全部 classifier fixtures 通过；
- workflow 语法与项目 convention 通过；
- 当前完整 CI 仍全绿；
- GatePlan 可下载、digest 可复算；
- 连续更新同一 PR 时旧运行被取消；
- standalone 不需要 WORK-LAB 在线；
- 本包没有实际跳过任何现有 Gate。

**最终证据**：

```text
base/head/tree
RED/GREEN 命令与输出
GatePlan 示例与 digest
workflow run / required job conclusions
stale-run cancellation 证据
wheel/installer exclusion 证据
回滚方式
```

**回滚**：设置 `CI_FORCE_FULL=true`；随后用新 commit revert，不 reset/force push。

---

### TP-MS00-CI-02｜选择性 PR 门禁切换

**建议分支**：`feat/ms00-ci-02-selective-pr`

**依赖**：CI-01 已合并；shadow fixture 和历史 diff replay 无漏分类。

**目标**：普通 PR 不再支付发布级全套成本，同时保持稳定 required verdict。

**实施规则**：

| 类别 | PR 实际运行 |
| --- | --- |
| docs/mechanical | static + verdict |
| ordinary Python | static + lint + Python 主版本完整 OS/KB/integration + verdict |
| UI | ordinary 基线 + browser |
| Windows runtime | ordinary 基线 + Windows smoke |
| Rust/Tauri | static + desktop-fast；拆分前临时使用 desktop-shell |
| Installer/bundle/NSIS | 完整 desktop/installer lifecycle |
| wheel/package-data | ordinary 基线 + wheel |
| Python dependency/public contracts | 兼容矩阵 + wheel/contract |
| CI/security/db/migration/unknown | full qualification |

**聚合器兼容迁移**：

1. 外部 check context 初期继续叫 `a0-gates`，内部执行 `ci-verdict` 语义。
2. 所有重型 job 可依据 GatePlan skip，但 aggregator 始终出现。
3. aggregator 展开并核对 required gates；合法 not-required 才允许 skipped。
4. owner 更新 branch protection 后，才将外部名称迁移到 `ci-verdict`。

**历史回放门禁**：

- 对最近至少 20 个 PR 的 changed-file 清单做 classifier replay；不足 20 则使用全部可用样本。
- 必须包含 docs、Python、UI、Windows、Desktop、Installer、dependency、mixed、unknown。
- 发现 false-negative 时不得 enforce；修复规则并重新从冻结 fixture 执行一次。

**RED**：

- 普通 Python 仍错误触发 browser/Windows/wheel/desktop/全矩阵；
- 合法 skip 被 aggregator 判失败；
- required Gate skipped 却被判成功；
- unknown 或 CI 自改进入轻量 lane；
- `full` 未展开真实 Gate 列表。

**GREEN**：

- 本包因修改 CI 自身，必须完整资格验证一次；
- docs、Python、UI、Windows 等 replay 的 Gate 集与真值表一致；
- aggregator 在所有路径都存在；
- fork/外部 PR 不获得 Release secret 或写权限；
- 无 `pull_request_target` 执行不可信代码；
- schedule/manual full 能展开当前全部 Gate。

**收益验收**：

- ordinary Python 不再启动 browser、Windows、wheel、desktop 和副版本全量；
- UI 不再启动 NSIS/Windows/Python 兼容矩阵；
- 实际普通 PR 关键路径中位数开始接近 3–5 分钟，而不是用预测代替测量。

**回滚**：

1. 启用 `CI_FORCE_FULL=true`；
2. 保留 GatePlan 产出用于诊断；
3. 用 revert commit 恢复全量路由；
4. 不删除历史 Evidence。

---

### TP-MS00-CI-03｜Full Qualification 与 Release 隔离

**建议分支**：`fix/ms00-ci-03-release-evidence`

**目标**：在 main 变轻之前，保证任何轻量检查都不能被正式 Release 误认为完整资格验证。

**允许范围**：

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- 新增独立 full qualification workflow
- release identity/checksum/readback 脚本
- Release/CI 合同测试

**实现**：

1. 明确分名 `PR Selective CI`、`Main Evidence Bind`、`Full Exact-SHA CI`、`Release`。
2. `Full Exact-SHA CI` 支持 nightly、manual、RC 和正式 Release 前置调用。
3. Release 只接受同一 exact SHA 的 `full-qualification` profile 和完整 Gate 明细。
4. 修复身份字段：
   - `verification_ci_run_id/url`
   - `release_run_id/url`
5. 保留 tag target 等于当前受保护 main 的断言。
6. 保留清洁构建、installer/wheel、asset/provider digest、下载 SHA-256 回读和生命周期。
7. `full-qualification` profile 包含 profile ID/version/digest，不能靠 workflow 名称或 job 数推断。

**RED**：

- 只有 selective/main-bind 成功时 Release 必须拒绝；
- qualification SHA 与 tag 不同必须拒绝；
- tag 不指向发布 main 必须拒绝；
- verification/release run ID 混用必须失败；
- required Gate 缺失、profile digest 不同、下载 hash 不同必须失败。

**GREEN**：

- Release 合同测试全绿；
- full qualification 名称和 profile 唯一；
- 本包 exact-SHA 完整 CI 通过；
- 可用 dry-run/fixture 验证，无需创建正式 Release；
- Release 原有强度没有下降。

**回滚与停止**：

- 禁止回滚成“任意名为 CI 的成功 run”。
- 若拆分未完成，main 暂时继续完整 CI，Release 默认停止。
- 只能用修复/revert commit，不修改历史 tag。

---

### TP-MS00-CI-04｜PR Merge Tree 证明与 Main SHA 轻量绑定

**建议分支**：`feat/ms00-ci-04-main-tree-bind`

**依赖**：CI-01～03 全部完成；Release 已只认 Full Exact-SHA CI。

**目标**：相同内容已经在 prospective merge tree 上通过时，main 不再重复完整资格验证。

**实现阶段**：

#### 阶段 A：只产出证明

- PR Selective CI checkout 并记录实际 merge-ref commit/tree。
- 生成 GatePlanV1、EvidenceEnvelopeV1、TreeProofV1。
- main 继续 full，不使用证明放行。
- 验证 artifact 来源、digest、TTL、workflow/policy/profile hash。

#### 阶段 B：docs/mechanical canary

- 仅 docs/mechanical 且证明完整时启用 main-bind。
- 任一字段不匹配自动 Full Exact-SHA CI。
- 收集 bind 命中、fallback 原因和误判。

#### 阶段 C：扩展普通 Python/UI

- 只有 Nightly 和回放没有漏测，才扩展到普通 Python/UI。
- Windows 可在稳定样本后单独开启。
- Desktop/Installer 在已知 lifecycle flaky 清零前保持 full/relevant rerun。

**main 验证动作**：

1. 读取 push `before/after` 与 `after^{tree}`。
2. 确认非 force push，base 连续。
3. 查找成功、未取消、未过期的同仓库 PR merge-ref proof。
4. 校验 base/head/tree、policy/workflow/classifier/profile digest。
5. 校验所有 required Gate 明确 success。
6. 校验证明 producer、run/attempt、artifact digest。
7. 检查 commit-sensitive/CI-policy-sensitive exclusion。
8. 全部成立才产生 `main-bind`。
9. 任何异常必须 full fallback；不得“找不到证据仍绿色”。

**RED fixture**：

- commit SHA 不同、tree 相同、其余证据一致：允许 bind；
- tree 不同：full；
- tree 相同、policy/profile/workflow digest 不同：full；
- 只测 PR head、未测 merge tree：full；
- required Gate skipped/cancelled：full；
- artifact 来自其他 repo/workflow：full；
- proof 缺失、过期、损坏：full；
- base/parent 不连续：full；
- binder 内部异常：失败或 full，不能放行；
- Release 只看到 binder：拒绝。

**GREEN**：

- proof artifact 可复算 digest；
- docs canary 合并后 main 只运行 binder；
- 人为 tree/policy mismatch 确实触发 full；
- binder 输出 main commit→tree→source proof 的完整链；
- Release 合同确认 binder 永远不具备 release eligibility。

**Owner 手动前置**：

- branch up-to-date/strict；
- 禁止 direct/force push；
- required aggregator 稳定；
- CODEOWNERS/强审查覆盖工作流、策略、分类器、锁文件；
- 合并策略与父提交校验一致。

HERMES 无权确认或修改这些设置时必须输出 Owner Action 清单，并保持 binder 关闭。

**回滚**：

- `CI_FORCE_FULL=true`；
- 关闭 reuse，保留 proof 产出；
- revert binder commit；
- 不删除历史证明。

**收益验收**：相同 tree main 重复完整运行趋近于零；所有 fallback 都有机器 reason code。

---

### TP-MS00-CI-05｜Desktop、依赖安装和缓存专项优化

**建议分支**：`perf/ms00-ci-05-heavy-lanes`

**性质**：P1 专项；CI-04 后可返回产品主线，再按实际数据决定插入时间。

**目标**：处理剩余关键路径，不把所有 Tauri 变化都当安装器发布。

**允许范围**：

- CI workflow；
- CI-only dependency groups；
- `pyproject.toml`、`uv.lock`；
- npm/cargo/browser cache 配置；
- desktop CI 脚本及合同测试；
- 三个当前未真正执行的 `test_workspace_*` 文件的受控迁移。

**禁止**：借性能优化修改产品业务、数据库或 installer 用户行为。

**Desktop 拆分**：

| Gate | 内容 | 触发 |
| --- | --- | --- |
| `desktop-fast` | cargo fmt/test、快速 backend/process lifecycle | Rust/Tauri 普通逻辑 |
| `desktop-build` | Tauri release build、bundle 输入校验 | Tauri build/config/resources |
| `installer-lifecycle` | NSIS build/install/start/WM_CLOSE/upgrade/uninstall | bundle/NSIS/installer/RC/Release |

**其他优化**：

1. lint 使用最小 `ci-lint` 依赖，不装完整 Playwright/OCR/test stack。
2. Windows runtime 只安装自身所需依赖。
3. browser 依赖与普通 Python 测试解耦。
4. FFmpeg/Tesseract 系统验证在主 Python 版本运行一次。
5. Cargo audit 只在 Cargo.lock/依赖、Nightly、RC、Release 运行。
6. 增加 npm cache；Playwright 浏览器按 Playwright 版本缓存。
7. Cargo cache key 纳入 toolchain/lockfile，并允许命中后更新，不长期恢复无效巨型 target。
8. 缓存不得包含凭据、Release identity 或未经校验的发布 artifact。
9. 缓存 miss 必须能从清洁环境完成构建。
10. 三个伪测试先做用途 ADR，再改为真实测试或迁入 scripts；不得静默丢弃。

**Desktop 稳定性前置**：

- 对 WM_CLOSE/进程退出建立确定性 contract test；
- desktop 相关 tree reuse 至少要求连续 10 次相关成功运行且零同类 flaky；
- Nightly 保留 lifecycle 重复稳定性采样；
- 未达门槛前不把 main 重跑当随机 flaky 探测器，也不复用 desktop proof。

**RED/GREEN**：

- 纯 Rust/Tauri 变更不得触发 NSIS；
- installer/config 变更必须触发 fast/build/lifecycle 并集；
- Cargo.lock 必须触发 audit；
- lint 不得安装完整 browser/OCR；
- browser cache miss 仍可运行；
- cache key 错误不得形成假绿；
- Full Qualification 展开后仍含完整 installer lifecycle；
- Release 始终从可信清洁输入构建。

**回滚**：强制 full、关闭缓存、临时把所有 desktop 类重新映射到 installer lifecycle，再用 revert commit 回滚。

---

### TP-MS00-CI-06｜Affected Tests 优化（默认延期）

当前 Python 主版本完整 1115 项测试本体约 45 秒，不是关键路径。现在不得为了形式上的“affected tests”建立高维护、低召回的复杂系统。

**仅在以下任一条件持续成立时启动**：

- `py-primary` 占普通 PR 关键路径中位数 30% 以上；
- 测试本体中位数超过 3 分钟；
- 测试规模增长导致普通 PR 无法达到目标区间。

**启动后仍必须**：

1. 先以 coverage/dependency 映射 shadow 选择 targeted set；
2. shadow 期间继续跑完整主版本并比较漏选；
3. unknown/mixed/测试基础变化 full；
4. 保留核心合同、迁移、启动 smoke 作为 sentinel；
5. 只有冻结 fixture 和历史 replay 无 false-negative 才能另包 enforce。

若完整主版本仍约 45 秒，本 TaskPack 直接标记 `DEFERRED_NOT_JUSTIFIED`，不写代码。

---

## 9. 每个 OS TaskPack 的统一执行合同

### 9.1 单 writer 与分支

- 一次一个 TaskPack、一个分支、一个 PR、一个冻结 head/tree。
- PR 发布后只追加修复 commit，不 amend/rebase 已发布历史。
- Codex 只对冻结 head/tree 做一次只读复审；代码变化后旧结论失效。
- 不把 CI 重构与 MS00-B、Obsidian 功能或 Runtime 改动混在同一 PR。

### 9.2 验证次数

每包默认只执行：

1. 一次预期失败的 RED；
2. 一次实现后的 GREEN；
3. 一次最终相关本地 Gate；
4. 一次 GitHub CI。

如果代码没有变化，不得为了放心重复相同门禁。失败后只重跑失败 job 或受影响 Gate；只有证据失效、环境变化或代码变化才重新运行更大范围。

### 9.3 统一交付证据

```text
taskpack_id
scope checksum / non-goals
base_sha / base_tree
head_sha / head_tree
branch / PR URL
changed_files / diffstat
RED command + expected failure
GREEN command + result
final local gate
GitHub run ID/URL
GatePlan / Evidence / TreeProof digest
required gates 与实际 conclusions
queue/setup/test/build/cache 指标
rollback steps
remaining risks / stop conditions
next TaskPack
```

### 9.4 允许的回滚

1. `CI_FORCE_FULL=true`，只增加验证；
2. 关闭 managed/reuse，返回 standalone/full；
3. 使用新 commit `git revert`；
4. 禁止 reset、force push、删除历史证明或移动 tag。

---

## 10. WORK-LAB 后期全局升级任务包

这些任务属于 `DTALEX66/WORK-LAB`，不得与 OS PR 混合，不得在当前 WORK-LAB 尚未完成既有升级时抢占活动 writer。

启动前，OS 必须已经产出以下真实 golden evidence：

- docs-only；
- ordinary Python；
- UI；
- Windows；
- Rust/Tauri；
- Installer；
- dependency/public contract；
- mixed/unknown fallback；
- main tree match；
- main tree mismatch；
- Full Qualification；
- Release dry-run/rehearsal。

### WL-VERIFY-00｜Contract Kit v1

**目标**：把 OS 已验证的中立合同正式化，而不是在 WORK-LAB 中重新发明一套平行状态机。

**输出**：

1. `GlobalValidationPolicyV1`
2. `ProjectValidationProfileV1`
3. `GatePlanV1`
4. `EvidenceEnvelopeV1`
5. `TreeProofV1`
6. Gate ID Registry
7. Schema validator 与兼容矩阵
8. observe → warn → enforce 策略生命周期

**硬规则**：

- Gate 使用语义 ID，不绑定 GitHub job 名。
- WORK-LAB 只接受项目登记 Gate，不接受任意远程 shell。
- OS 提供 golden fixtures，不复制 OS workflow/测试实现进 WORK-LAB Core。
- 同 major 新增 optional 字段向前兼容；未知 required feature/major fail closed。
- 所有发布物固定 tag、commit、digest，不通过 mutable `main` 消费。

**验收**：同一项目 profile 可被当前 minor 和前一兼容 minor 正确读取；未知 major 明确拒绝。

---

### WL-VERIFY-01｜全局安全下限与项目策略并集

**目标**：定义跨项目最低安全线，但不硬编码 OS 的 Python、Windows、Tauri 或 Obsidian 命令。

全局不可绕过类别至少包含：

- CI/workflow/classifier/policy 自修改；
- security/permissions/secrets；
- migration/schema/data compatibility；
- dependency/public interface；
- unknown classification；
- formal Release exact-SHA。

合并算法：

```text
effective = global floor ∪ project profile ∪ TaskPack extras ∪ event mandatory
```

必须证明：

- WORK-LAB 少选一个 OS Gate 时，OS `ci-verdict` 会拒绝；
- WORK-LAB 新增 Gate 时，OS 能显示 reason code；
- TaskPack 只能加 Gate；
- 项目可以定义比全局更严格的 Release、fixture 和平台矩阵。

---

### WL-VERIFY-02｜Reusable Workflow 与 Provider Adapter

**目标**：把 GitHub Actions 作为第一个 Provider，同时保留未来其他 CI Provider 的中立合同。

**范围**：

- 读取 project profile；
- 计算/复核 GatePlan；
- 调度符号化 Gate；
- 生成 EvidenceEnvelope/TreeProof；
- 聚合 run/job/artifact；
- 输出 queue/setup/test/build/cache/rerun 指标；
- 提供 local/standalone fallback 协议。

**安全**：

- reusable workflow 固定完整 SHA；
- 最小 permissions；
- 不使用高权限 `pull_request_target` 运行不可信代码；
- 签名/attestation 逻辑不调用 PR 可修改脚本；
- 不读取项目 secret 之外的控制面凭据；
- 不接触 OS 用户数据。

**非目标**：不写 OS 产品源码，不保存 HERMES/Studio/Codex session，不成为模型网关或第四个产品。

---

### WL-VERIFY-03｜Managed Shadow Conformance

**目标**：WORK-LAB 只读观察，同一 diff 由 OS standalone 与 WORK-LAB managed 各计算一次。

**执行**：

1. `mode=shadow`，managed 结果不决定合并。
2. 对全部 golden fixtures 和真实 PR 比较 Gate 集、risk class、reason code。
3. 记录 false-negative、false-positive、unknown 和 policy version 差异。
4. managed 结果少于 standalone 时自动 full，并形成阻断证据。
5. 连续覆盖一个完整 release train，不允许静默差异。

**进入 enforce 的必要条件**：

- false-negative = 0；
- unknown 都按 full 处理；
- managed Gate 集始终等于或严格大于 standalone；
- WORK-LAB 离线/超时/版本不兼容的 fallback 已真实演练；
- OS Release 在 WORK-LAB 离线时仍能独立执行 exact-SHA full。

---

### WL-VERIFY-04｜签名证明、Managed Enforce 与 Canary

**目标**：升级 tree proof 的供应链可信度，并逐项目启用 managed 模式。

**实现**：

- 由受信、固定 SHA 的 reusable workflow 生成 attestation；
- 证明绑定 repo、source workflow、source SHA/ref、policy/profile/workflow digest；
- OS 本地仍重算 GatePlan 并保留否决权；
- 先 OS 单项目 canary，不全项目同时强推；
- Global Policy 升级按 observe → warn → enforce；
- 任意项目可切回上一 policy digest 或 standalone。

**回滚**：

```text
WORKLAB_MODE=standalone
CI_FORCE_FULL=true
pin previous compatible policy/workflow digest
```

任何回滚只能增加验证，不能让缺证据的 PR/Release 通过。

---

### WL-VERIFY-05｜全局推广

只有 OS canary 通过一个完整 release train 后，才向其他项目推广：

1. 每个项目独立 profile；
2. 全局不复制项目命令；
3. 每个项目先 shadow；
4. 每个项目独立 canary/rollback；
5. 项目之间不共享未经脱敏的 changed paths、artifact 或用户数据；
6. 全局指标按项目和 profile version 分组，禁止用一个速度目标覆盖所有项目。

---

## 11. OS 与 WORK-LAB 迁移兼容路线

| 阶段 | OS | WORK-LAB | 合并决定 |
| --- | --- | --- | --- |
| A：现在 | standalone 本地 v1 | 未完成/不参与 | OS 本地 `ci-verdict` |
| B：合同发布 | 继续 standalone | 读取 profile，校验 schema | OS 本地 |
| C：Shadow | 本地正式计算 | 并行建议 GatePlan | OS 本地；差异 full |
| D：Managed Canary | 本地复核与否决 | 调度/聚合/签名 | Gate 并集 |
| E：Managed Stable | 永久保留 fallback | 全局控制面 | Gate 并集；Release 仍由项目执行 |

### 11.1 兼容判定

| 情况 | 结果 |
| --- | --- |
| WORK-LAB 缺席 | standalone 正常 |
| 同 major、支持 minor | managed 可用 |
| 新 optional 字段 | 允许忽略并记录 |
| 未知 required feature | full/阻断 |
| WORK-LAB Gate 少于 OS | verdict 失败 |
| 旧 Evidence 无 tree/policy digest | 只展示，不复用 |
| 新 Global Policy 更严格 | 取并集并显示原因 |
| 新 Global Policy major 不兼容 | managed 停止，回 standalone |
| reusable workflow 权限失败 | 本地 workflow/full fallback |

### 11.2 双写/双读期限

- 旧 `a0-gates` 与新 `ci-verdict` 在 required check 迁移期使用 alias，不永久维持两套逻辑。
- Evidence V0/V1 只在迁移期双读；新证明只写 V1。
- 新 major 必须提供明确迁移器、兼容期、回滚 policy digest 和历史 evidence reader。
- 不允许 WORK-LAB 升级要求 OS 同时改产品 Runtime。

---

## 12. 避免再次反复审计的运行规则

### 12.1 审计触发层级

| 事件 | 审计范围 |
| --- | --- |
| 普通 PR | changed paths + TaskPack + 对应 Gate |
| CI/策略/架构/安全/迁移变化 | 高风险专项/完整资格验证 |
| Nightly | 完整 profile、依赖与 flaky 观察 |
| 新阶段开始 | 一次冻结 tree 的阶段审计 |
| RC/Release | exact-SHA 完整资格和资产读回 |
| 无代码变化 | 不重复相同审计 |

### 12.2 证据复用规则

- 只有 subject、tree、policy/profile/workflow digest、Gate 集和环境 epoch 均匹配才复用。
- 计划、自评、文档声明不能替代运行证据。
- 冻结 head 后的审查只对该 head 有效；新增 commit 只做增量复审和受影响 Gate。
- 相同失败不得反复全仓搜索；先使用已有 Evidence reason code 和失败 job 定位。
- Nightly 发现选择性漏测时，打开 full kill switch，修规则后再恢复。

### 12.3 CI 指标账本

每个 run 固定输出：

- event、commit/tree、profile/policy version；
- risk class、selected/required/not-required gates；
- queue、setup、test、build、artifact 时间；
- cache hit/miss 与 key digest；
- rerun/cancel/fallback reason；
- duplicate tree 是否避免；
- runner failure 与 product failure 分离；
- Release eligibility。

每个阶段只根据账本优化，不再凭感觉重复全仓审计。

---

## 13. 验收矩阵

### 13.1 分类安全

- docs、Python、UI、Windows、Tauri、Installer、wheel、依赖、迁移、安全、CI、unknown fixture 全覆盖。
- rename/delete/mixed 取 Gate 并集。
- `.github/**`、`.worklab/**`、分类器/锁文件自修改自动 full。
- TaskPack extras 无法被删除。

### 13.2 聚合与分支保护

- required aggregator 始终出现。
- required skipped/cancelled/missing 必须失败。
- 合法 not-required 才允许 skip。
- branch protection 名称迁移有 alias 和 Owner Action 证据。

### 13.3 Standalone/Managed

- 关闭或删除 WORK-LAB 接入后，OS CI 与 Release 仍独立工作。
- 同一 fixture managed Gate 集等于或严格大于 standalone。
- schema/controller 不兼容时自动 standalone/full。
- OS wheel/Tauri/installer 中不存在 WORK-LAB 包、状态机、凭据或 profile 执行器。

### 13.4 Tree Proof

- 证明 prospective merge tree，不是普通 PR head。
- tree/base/policy/profile/workflow/Gate 任一变化均拒绝复用。
- proof 缺失、过期、取消或来源不可信自动 full。
- main-bind 只建立 SHA→tree→source proof 关系。
- desktop/installer 在稳定性门槛前不复用。

### 13.5 Full Qualification 与 Release

- full profile 由 Gate Registry 展开，不依赖固定 job 数。
- Nightly/manual/RC 能执行完整 profile。
- Release 只接受同 exact SHA 的 Full Exact-SHA CI。
- binder/selective success 无法满足 Release。
- installer、资产集合、provider digest、下载复算、identity 和生命周期仍完整。

### 13.6 效率

- 普通 PR 不再支付无关 browser/Windows/wheel/desktop/installer/兼容矩阵。
- 同一 PR 旧 synchronize run 自动取消。
- 有效相同 tree 合并 main 不重复完整矩阵。
- 失败优先重跑失败 Gate，不关闭/重开 PR 重跑全部。
- 以实际中位数和 P95 验收，不把预计 75%–90% 写成 SLA。

---

## 14. Definition of Done

本增量任务包只有同时满足以下条件才完成：

### OS P0 完成

- GatePlanV1、project profile、Gate Registry 有版本和测试。
- 普通 PR 已按风险选择 Gate。
- stable verdict 始终存在，unknown fail closed。
- Full Exact-SHA CI 与 Release 完全隔离。
- main proof 在安全前置满足后 canary 上线，不匹配自动 full。
- `CI_FORCE_FULL` 与 standalone 回退真实演练。
- meta-tests 不再硬编码“所有 PR 必须 9-job”。

### WORK-LAB 兼容完成

- WORK-LAB 可以读取 OS v1 profile/evidence，而不复制 OS 命令和 Runtime。
- standalone 与 managed Gate 集一致或 managed 更严格。
- Global Policy 固定版本/digest，升级先 shadow。
- WORK-LAB 离线或 major 不兼容不会阻断 OS 自主开发；Release 仍有项目侧完整路径。

### 安全与发布不降级

- 安全、迁移、CI 自改、unknown 仍 full。
- Release exact-SHA、installer、资产、下载哈希、重启/卸载证据全部保留。
- main-bind 永远不能冒充 full qualification。
- 没有使用高权限事件执行不可信 PR 代码。

### 产品目标未漂移

```text
Obsidian/Markdown/JSON Canvas C3
→ 文件树/编辑/属性/链接/搜索/画布
→ 证据回链与有引用问答
→ 开放格式导出
→ 冲突、回滚、重启读回
```

CI P0 收口后必须返回这条产品主线；不得借 WORK-LAB 兼容继续建设通用 Agent 平台。

---

## 15. 明确非目标

本任务包不得顺带实施：

- OpenCodeReview Adapter；
- ContextLine、agency-agents、Hermes Studio/Cherry Studio 客户端生态；
- WORK-LAB 第二套状态机或平行 Evidence/Gate Registry；
- 复杂 affected-test 图谱（未达触发阈值前）；
- Merge Queue 专属实现；当前先用 PR merge ref；
- Obsidian、Scrapling、RAG 产品功能；
- OpenMAIC、EDUKG、3D、Agent Runtime 等延期内容；
- 产品 Runtime 重构或 UI 设计调整；
- 任何跨项目、跨磁盘或用户 Vault 访问。

---

## 16. 风险清单与阻断条件

| 风险 | 阻断措施 |
| --- | --- |
| PR 修改分类器绕过自身门禁 | 受保护基线规则 + CI/policy change 自动 full |
| 把 PR head 当 merge tree | proof 必须记录 tested merge commit/tree |
| binder 被 Release 误认 | 工作流/profile/eligibility 完全分离 |
| skipped required check 消失 | 始终存在的 stable verdict |
| 路径分类漏 TaskPack 语义 | Gate 并集；TaskPack 只增不减 |
| 缓存导致假绿 | lock/toolchain/runner key；miss 可清洁重建 |
| WORK-LAB 在线单点 | standalone 永久保留 |
| 全局升级再次拖住产品 | OS 先 local v1；WORK-LAB 后期替换控制面 |
| Desktop flaky 被 tree reuse 隐藏 | 稳定门槛前排除复用；Nightly 采样 |
| 预计收益被当 SLA | 只认实际 CI 指标账本 |
| 修改仓库设置需要新权限 | 停止并输出 Owner Action，不擅自扩大授权 |

---

## 17. HERMES 主执行指令

以下内容可直接交给 HERMES：

```text
你是 DTALEX66/Cognitive-Loop-OS 的唯一 writer。

本任务包是 MS00 横切增量，只优化 CI、验证、证据复用与 WORK-LAB 后期兼容；不改变 OS 的 Human–AI Learning & Knowledge System 定位，不进入 Obsidian/Compatibility Kernel 产品实现，不把 WORK-LAB 复制进 OS Runtime。

开始前：
1. fetch origin，记录最新 main commit/tree、dirty、活动分支、PR、CI、required checks 和合并策略。
2. 若 feat/ms00-b-version-state 或任何其他 writer 任务仍活动，停止本任务并报告，不并行写入。
3. 不得 reset --hard、force push、移动 tag、覆盖他人提交、扫描项目外目录、个人 Vault 或 E 盘。
4. 无法确认 branch protection、权限或 tree proof 前置时，只生成证据，不启用 main bind。

严格按顺序执行：
TP-MS00-CI-00
→ TP-MS00-CI-01
→ TP-MS00-CI-02
→ TP-MS00-CI-03
→ TP-MS00-CI-04
→ 返回 OS MS01–MS04 主线。

TP-MS00-CI-05 按真实指标另行插入；TP-MS00-CI-06 默认延期。

每个 TaskPack：
- 一个分支、一个 PR、一个冻结 head/tree。
- 先 RED，再最小实现，再 GREEN，再一次最终相关 Gate，再一次 GitHub CI。
- 无代码变化不得重复相同审计或门禁。
- 失败优先重跑失败 Gate，不通过关闭/重开 PR 重跑全部。
- 所有分类未知、合同不兼容、CI/安全/迁移自改均 fail closed/full。
- effective gates = 全局安全下限 ∪ OS profile ∪ TaskPack extras ∪ event mandatory。
- WORK-LAB 只能增加 Gate，不能删除 OS 或 Release Gate。
- Release 只接受同 exact SHA 的 Full Exact-SHA CI；main-bind 永远不可替代。

每包完成报告必须包含：
scope checksum、base/head/tree、文件、RED/GREEN、GatePlan、Evidence/TreeProof digest、required/actual Gate、CI run、真实时间指标、回滚、剩余风险、下一包。

若任务需要跨仓库写入 WORK-LAB、修改 branch protection、扩大权限、访问外部个人数据或修改本任务允许范围，立即停止并请求用户决定。
```

---

## 18. 最终决策记录

本任务包冻结以下决定，直到用户再次明确修改：

1. 保留强门禁，改变错误执行频率。
2. 普通 Python 当前使用主版本完整测试，不优先建设复杂 affected-test。
3. Desktop/Tauri/Installer 必须拆层，不能长期共用一个发布级 job。
4. 同 tree 证据复用必须绑定 policy、workflow、Gate 和来源；不一致自动 full。
5. main-bind 只是 identity/evidence binding，不是 full exact-SHA qualification。
6. 正式 Release 永远执行完整资格、installer、资产和下载哈希回读。
7. OS 先实现 standalone v1，不等待 WORK-LAB 升级完成。
8. WORK-LAB 后期只接控制平面和版本化合同，不能降低 OS Gate 或进入 Runtime。
9. CI P0 完成后立即返回全面兼容吸收最小面，其他重型蓝图继续延期。
10. 完成只认真实运行、可复现证据、回退和精确身份，不认计划、自评和重复审计次数。

---

## 19. 证据入口

- OS 仓库：<https://github.com/DTALEX66/Cognitive-Loop-OS>
- 审计基线：<https://github.com/DTALEX66/Cognitive-Loop-OS/commit/ff667d1450e17bc5469902ec2415d756df8209a6>
- CI workflow：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/ff667d1450e17bc5469902ec2415d756df8209a6/.github/workflows/ci.yml>
- Verification Policy：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/ff667d1450e17bc5469902ec2415d756df8209a6/docs/VERIFICATION_POLICY.md>
- Release workflow：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/ff667d1450e17bc5469902ec2415d756df8209a6/.github/workflows/release.yml>
- WORK-LAB：<https://github.com/DTALEX66/WORK-LAB>
- 既有主任务包：`ArcheAxis_OS_Minimum_Surface_Master_TaskPack_2026-08-06.md`
- 22 项验真与边界文档：`Agent_FullStack_22_Verified_OS_WORKLAB_Integration_2026-08-07.md`
