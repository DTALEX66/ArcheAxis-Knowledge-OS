# ArcheAxis OS 云端全量审计与整合执行任务包

> 审计日期：2026-08-07 UTC
> 审计对象：`DTALEX66/Cognitive-Loop-OS` 云端公开仓库
> 冻结基线：`main@9fefcfcae8380c84447e48fcf71cabeeab00f726`
> tree：`a532c3097d9b6a53b96a796ce52c5ab44cf22640`
> 文档性质：只读审计、纠错、路线重排、HERMES 单写者任务包
> 继承并更新：2026-08-06 Minimum Surface Master TaskPack、2026-08-07 CI Acceleration TaskPack、22 项 OS/WORK-LAB 验真清单
> 当前写入状态：本次审计未修改云端仓库、PR、Issue、分支、Release 或仓库设置

---

## 0. 决策摘要

### 0.1 正确的项目定位与范围校验

本任务包冻结以下范围，直到用户再次明确改变：

```text
产品定位：本地优先、证据驱动、面向人与 AI 的学习与知识系统
当前最小面：全面兼容、吸收同类软件成熟能力的开放工作台
第一高保真纵切：Obsidian Vault / Markdown / JSON Canvas
实现原则：合法依赖、API/SDK/CLI、fork/vendor、Adapter/sidecar 优先；自研最后
延期：通用 Agent Runtime、多 Agent、Marketplace、3D/VR、企业协作等重型蓝图
工作流边界：HERMES 是 OS 唯一 writer；Codex 只读审计；WORK-LAB 是控制面而非 OS Runtime
```

Obsidian 是第一条完整纵切，不是整个“全面兼容吸收”阶段的边界。当前最小闭环应同时做到：

- Compatibility Kernel 可承载后续 Logseq、Joplin、SiYuan、AFFiNE、Zotero、Anki 等 Adapter；
- Obsidian/Markdown/JSON Canvas 先达到可证明的高保真往返；
- 文件树、编辑、属性、链接、搜索、画布、引用问答、轻复习形成真实用户路径；
- 安装、重启读回、冲突、回滚和开放格式导出有行为证据。

### 0.2 本轮最终判断

仓库不是空壳，也不应推倒重来。它已经有一套较强的后端与发布底盘：FastAPI、SQLite、Tauri、MigrationOperator、approved roots、Safe HTTP、Research/Evidence/Knowledge 合同、FTS/sqlite-vec、Job/Outbox/Receipt、Chromium、Windows/NSIS 和 Release 资产回读。

但它当前仍不是用户决定的最小闭环：

```text
当前真实产品链
文件/URL 导入
→ Research Candidate
→ 人工批准
→ Knowledge Candidate
→ 学习/掌握后端对象

目标最小闭环
Vault/资料
→ 文件树/Reader/Editor/Properties/Links/Search/Canvas
→ 安全保存
→ 有引用 AI 使用与轻学习
→ 原格式/开放格式导出
→ Obsidian/独立解析器重开
→ semantic diff / conflict / rollback
```

按纵向闭环验收，Obsidian 第一纵切当前为 **0/1**；按零散底层能力估算约 **20%**。不能宣称“全面兼容 Obsidian”，更不能把 9-job CI 全绿当作产品闭环完成。

### 0.3 GO / STOP

**GO：**

- 修复 Release/version truth、main 保护和 CI 选择性执行；
- 执行一次 Truth Reset；
- 隔离旧 Obsidian apply 路径；
- 建立 Compatibility Kernel、真实 Vault fixture 和主工作区；
- 复用许可兼容的上游源码、依赖和接口。

**STOP：**

- 当前不得直接合并 `feat/ms00-c-release-identity`；
- 当前不得发布 `v0.4.5`；
- 当前不得宣称 Obsidian C2/C3、双向同步或完整日常工作区；
- 当前不得把 WORK-LAB 代码复制进 OS wheel/Tauri/installer；
- 当前不得继续优先扩展 Agent、Runtime、SSE、3D、企业协作等延期蓝图。

---

## 1. 云端仓库事实

### 1.1 仓库、提交与权限

| 项目 | 当前事实 |
| --- | --- |
| 仓库 | `DTALEX66/Cognitive-Loop-OS` |
| 可见性 | Public |
| 默认分支 | `main` |
| main commit | `9fefcfcae8380c84447e48fcf71cabeeab00f726` |
| main tree | `a532c3097d9b6a53b96a796ce52c5ab44cf22640` |
| 最新合并 | PR #41，MS00-B development version truth |
| 最新 main CI | run `31174593430`，9/9 success |
| Codex 连接权限 | pull/read；无 push/admin |
| 本次审计 clone | clean；未修改源码 |

仓库公开 description 已改为 Human–AI learning/knowledge，但仍带 `cognitive-governance desktop`，尚未完全传播新定位。

### 1.2 main 保护事实

公开 Branch API 返回：

```json
{
  "name": "main",
  "protected": false,
  "protection": {
    "enabled": false,
    "required_status_checks": {
      "enforcement_level": "off",
      "contexts": [],
      "checks": []
    }
  }
}
```

因此文档中的“受保护 main”目前不是真实云端事实。现阶段技术上可以绕过 PR/CI 直接更新 main；在保护规则建立前，不得启用 main tree proof 自动放行。

### 1.3 PR、Issue 与分支

- PR 总计 41：39 merged、1 closed-unmerged（#14）、1 stale open（#15）。
- 独立 Issue 为 0；当前没有云端权威 backlog、milestone 或阶段出口账本。
- 非 main 远端分支共 24 个。
- 18 个已是 main 祖先；5 个已被 squash、关闭或后续实现替代。
- 唯一真实待处理分支是 `feat/ms00-c-release-identity`。

#### 唯一待处理分支

| 项目 | 事实 |
| --- | --- |
| branch | `feat/ms00-c-release-identity` |
| commit | `01e794d1070114c6a55142fae2032bc010b9946e` |
| 与 main | 0 behind / 1 ahead |
| PR | 无 |
| CI/checks | 无 |
| 当前决定 | 保留，但不得按现状合并 |

#### 陈旧开放 PR

PR #15 `feat/archeaxis-desktop-a1-violet-core` 最后更新于 2026-07-28，已被 PR #20 和后续 main 工作替代。应先关闭 PR，再删除分支。

#### 分支清理目标

在记录所有分支 SHA、确认无未归属内容后，目标只保留：

```text
main
当前正在审查/实现的单一 TaskPack branch
```

仓库 owner 应启用 merge 后自动删除 head branch。分支删除是云端写操作，不在本次只读审计中执行。

### 1.4 Tag 与 Release

| 对象 | 云端事实 |
| --- | --- |
| tags | `v0.4.0` 至 `v0.4.4` 均在 main 历史 |
| GitHub Releases | 只有 `v0.4.0`、`v0.4.4` |
| `v0.4.1`–`v0.4.3` | remediation tags；无公开 Release |
| 当前开发版本 | `0.4.5`，无 tag、无 Release |

`v0.4.4` 是真实公开 stable Release：

- Release run：`30839451084`；
- exact-SHA verification CI：`30837105199`；
- 4 个公开资产；
- installer、wheel、release identity 均进入 `SHA256SUMS.txt`；
- 下载后 SHA-256 与 GitHub provider digest 一致。

但公开 `release-identity.json` 的 `source.ci_run` 指向 Release run `30839451084`，不是验证 CI `30837105199`。因此资产哈希成立，但 provenance 字段语义错误。历史 tag/Release 必须保留，不原地改写；在 changelog/发布账本中记录已知错误。

### 1.5 版本真相仍有一处漏网

大部分机器版本已升级为 `0.4.5`，但：

```toml
# desktop/src-tauri/Cargo.lock
name = "archeaxis-desktop-shell"
version = "0.4.4"
```

现有 meta-test 只检查 `Cargo.toml`，未检查 Cargo.lock 根包。MS00-B 因此不是完整版本真相闭环。

---

## 2. 旧判断和协作错误复盘

### E1：让仓库名和旧文档覆盖了用户最新定位

此前把项目继续称为“认知闭环系统”，是事实源优先级错误。仓库名、AGENTS 和历史蓝图不能覆盖用户最新决定与 `PRODUCT_POSITIONING.md`。

### E2：没有在回答前重新冻结云端基线

旧审计曾停留在 `f06c840`、`ff667d1`。当前 main 已推进到 `9fefcfc`。以后每次报告必须同时写 commit、tree、云端 run 和采样时间；旧报告只能作为历史证据。

### E3：把后端构件、计划和字符串测试计成产品完成

Research、Knowledge、Canvas、Review 等文件或 API 存在，不等于用户可以完成工作。今后完成度只认真实用户动作、持久化读回和跨应用 fixture。

### E4：把 CI 全绿误当产品闭环

当前 exact-main 9/9 全绿，但三个导出路由仍引用不存在的函数，Obsidian 导入仍截断正文，JSON Canvas 完全不存在。CI 证明的是现有测试合同，不是未建模行为。

### E5：把全面兼容吸收缩成“复刻 Obsidian”

Obsidian 是第一纵切，不是阶段全部。正确目标是通用兼容内核 + Obsidian C3 样板 + 后续其他软件 Adapter。

### E6：混淆研究台账与可复用源码台账

101 项 registry/ledger 不等于具备上游 URL、commit、license、fixture 和 rollback。源码复用不能仅凭项目名或 `candidate` 状态开始。

### E7：沿用与新定位不兼容的旧评分

旧“Agent 执行闭环”高权重会重新拉回已延期的通用 Agent 蓝图。当前阶段保留其历史分数，但不把它作为 0.5 最小面 release-driving KPI。

### 后续强制防错头

每个审计、TaskPack、PR 描述先输出：

```text
repo / branch / commit / tree
产品定位 / 当前最小闭环 / 第一纵切
本包非目标 / 延期内容
writer / 权限 / 用户数据边界
证据 profile / Release eligibility
```

---

## 3. 文档与路线真相审计

### 3.1 正确事实源

`docs/PRODUCT_POSITIONING.md` 已正确说明：

- local-first、evidence-driven；
- 面向人与 AI 的学习与知识系统；
- Agent 是 AI 使用层，不是产品中心；
- 对外推荐 `Human–AI Learning Workspace`。

### 3.2 最高风险漂移

| 文件 | 当前问题 | 处理 |
| --- | --- | --- |
| `AGENTS.md` | 仍是 Cognitive-OS Agent Guide；使命仍是 Knowledge Base + Inspiration Research + cognition loop | 作为最高代理入口，P0 重写 |
| `README.md` | 首页定位已修，但主体仍以 Research/A0/Runtime 为主；称外部能力吸收已结束 | 改成兼容主线和真实 release table |
| `PROJECT_STATUS.md` | 更新时间/Job Center/路线过期；遗漏 v0.4.4 | 只保留当前机器事实和限制 |
| `NAMING_ALIGNMENT_MATRIX.md` | 仍写 ArcheAxis Cognitive Workspace | 改为 Human–AI Learning Workspace |
| `SYSTEM_BOUNDARY.md` | 仍描述 echo planner、binary eval、无 migration runner 等历史状态 | 重写或归档历史 |
| `HERMES_HANDOFF.md` | 根目录仍指向 7/23 旧 Windows 分支/benchmark | 移出当前入口，保留为历史 |
| `ABSORPTION_EXECUTION_MATRIX.md` | 强制 A0→H→I→J；Obsidian 仅单向 J-001 | 重排为 Compatibility Kernel/Obsidian 先行 |
| `FUTURE_EXECUTION_BLUEPRINT.md` | 重型 Runtime/Agent 内容仍可覆盖当前路线 | 标记 deferred/historical |
| `CHANGELOG.md` | 只有 Unreleased 和 v0.4.0 | 补 v0.4.1–v0.4.4 的 tag/release真相 |

### 3.3 旧测试正在反向锁定旧真相

- `tests/test_phase7_runtime_vertical_slice.py` 强制 AGENTS 旧标题/语义；
- `tests/test_release_manifest.py` 锁定旧 handoff 文案；
- `tests/test_product_truth_contract.py` 只扫 README 少量行和少数文件，漏掉 AGENTS、状态、边界、命名、路线图；
- 因此 CI 全绿也不能阻止定位回退。

### 3.4 历史蓝图污染

仓库约有 171 个 Markdown 文件；约 66 个仍含 Cognitive Loop、Agent OS、A/B/C 线等历史表达，而直接表达新定位/兼容主线的文档很少。历史证据不应删除，但必须：

1. 集中到 `legacy/historical_reference` 或等价目录；
2. 在 docs index 标记 `historical/non-authoritative`；
3. 从默认 Agent 发现和当前路线导航中排除；
4. 禁止旧 TaskPack 被新 writer 当作活动计划。

### 3.5 文档中的安全禁令需要拆分

以下两类规则不能继续混在一起：

- 必须保留：不得扫描个人 Vault、不得默认访问 E 盘、不得外写用户数据；
- 必须取消旧绝对禁令：不能声称 Obsidian/PKM 吸收已结束，也不能禁止对已授权、许可兼容的公开源码进行研究/复用。

---

## 4. 产品实现全量审计

### 4.1 当前可复用底盘

应保留并复用：

- FastAPI + SQLite + Tauri 模块化单体；
- MigrationOperator、多 owner schema、backup/restore；
- approved roots、Safe HTTP、loopback workspace；
- Source/Claim/Evidence/Research/Knowledge/Learning 合同；
- Job/Outbox/Receipt、lease/retry/readback；
- FTS、sqlite-vec、NetworkX；
- MarkItDown、Trafilatura、OCR/FFmpeg 基础；
- LiteLLM Adapter；
- browser smoke、wheel smoke、Windows runtime、Tauri/NSIS 生命周期；
- BFF `public_ref` 与内部 ID 隐藏。

### 4.2 目标能力逐项状态

| 能力 | 当前状态 | 审计结论 |
| --- | --- | --- |
| Vault 文件树 | 未实现 | `scan_vault` 只是分类 inventory，不是可操作树 |
| Markdown Editor | 未实现 | 无 open/update/save API 和真实编辑器 |
| Reader | 未实现 | 只有短预览，无 Markdown/附件阅读和定位 |
| Properties | 底层部分 | 无笔记属性面板；无法保留全部原始 YAML |
| Tags | 部分 | 有字段/自动标签，无用户级浏览编辑筛选 |
| Wikilinks | 部分且脱节 | parser 存在，但 import 不建立 link index |
| Backlinks | 部分且不可闭环 | literal note name 与随机 `doc_*` ID 不稳定匹配 |
| Search | 后端可用，UI 未接 | `/kb/search` 可用；顶部 search 明确 readonly/尚未接入 |
| Canvas | 内部模型 | 不是 JSON Canvas；无 `.canvas` import/export |
| Attachment | 未实现 | 不复制、不索引、不报告缺失附件 |
| Obsidian import | 低保真单向 | 只读 `.md`、硬编码目录、截断、随机 ID |
| Obsidian export | 部分且有坏路由 | Daily/TaskPack/Trace/Lesson 有投影；Card/Review/MKU 路由坏 |
| Roundtrip | 未实现 | 模块自述 one-way；无目标工具重开验收 |
| Conflict | 未实现 | 无 expected hash、外部修改检测、三方冲突 |
| Rollback | 通用能力未接入 Vault | Obsidian write 直接覆盖；无 revision/restore |
| 引用问答 | 未实现 | 有检索/Evidence 合同，无 ask/answer/citation UI |
| Cards | 后端部分 | 无真实正反面、编辑、确认和学习页面 |
| Review | 后端部分且有 bug | UI 固定 `quality:5`；调度历史查询存在卡片串扰 |

### 4.3 Obsidian importer 的阻断问题

`shared/obsidian_importer.py` 当前：

- 文件头错误称 bidirectional；
- 硬编码 `02_课程库`、`03_知识卡片` 等特定旧 Vault 目录；
- 手写单行 YAML parser，不支持多行数组、嵌套值、类型和注释保真；
- card/MKU 正文截断到 5,000 字，document 截断到 10,000 字；
- 每次生成随机 ID，重复 import 不幂等；
- 不保存稳定相对路径身份、hash、mtime、cursor、rename/delete；
- 不复制 attachment，不读取 `.canvas`；
- 不建立链接/反链索引；
- `machine_knowledge` 直接写 `active=1`、`confidence=0.7`，绕过当前 candidate/review 语义；
- scan/import/apply 路由只要求非空字符串，未使用 approved-root/realpath/symlink containment。

该 importer 不适合继续直接堆叠功能。正确做法是先将真实 apply 路由 fail closed/feature-gated，再在 Compatibility Kernel 上建立新版本 Adapter。

### 4.4 已确认的坏路由

`knowledge_base/api.py` 动态导入：

- `render_card`
- `render_review_card`
- `render_machine_knowledge`

但 `shared/obsidian_projection.py` 没有这三个函数。三个 endpoint 在进入对应分支后会产生运行时错误。当前 CI 未覆盖这一行为。

### 4.5 Vault 写回并不安全

`write_projection()` 虽用 ApprovedRoots 解析目标路径，但最终仍直接 `Path.write_text()`：

- 非原子写；
- 无 expected-hash；
- 无外部修改检测；
- 无 revision；
- 无 write-ahead backup；
- 未使用已有 SafeWriter/backup manifest。

因此“项目有 SafeWriter”不能被计作“Vault 已有冲突和回滚”。

### 4.6 Review 算法缺陷

当前复习实现先取得全库最新 Review，再判断是否属于当前 card。若最新记录属于另一张 card，当前 card 的真实历史可能被忽略并按首次复习计算；从未 review 的新卡也不会自然进入现有 due 查询。进入学习闭环前必须修复并增加多卡行为测试。

### 4.7 当前最短真实用户路径

当前能证明的路径是：

```text
本地文件上传
→ Research/Job/Outbox 同事务
→ on-demand dispatch
→ Receipt
→ UI reload readback
```

它证明底盘可用，但不是知识工作区，也不是 Obsidian 兼容闭环。

---

## 5. 源码复用与供应链审计

### 5.1 101 项账本的真实含义

现有 registry/ledger：

- 101 项；
- 8 implemented；
- 27 adapter contract pending；
- 38 deferred review；
- 28 reference only。

但机器字段只有项目名、类别、目标、风险、状态、note 和少量 implementation evidence。当前 101/101 均没有完整的：

```text
canonical repository URL
exact upstream commit/tag
SPDX/license hash
selected source files/components
network/scripts/secrets profile
fixture/tests
upgrade strategy
rollback handle
```

而且存在重复候选和风险状态冲突。它是研究清单，不是可直接复制源码的供应链账本。

### 5.2 强制复用阶梯

每个功能按下列顺序决策，只有前一层不适用时才进入下一层：

1. 直接依赖成熟且许可兼容的包；
2. 官方 SDK/API/CLI；
3. 固定 commit 的 fork/vendor/组件嵌入；
4. Adapter/sidecar 隔离；
5. clean-room 自研。

任何 TaskPack 直接进入第 5 层，必须在 PR 中证明前四层为何不可用，否则不合并。

### 5.3 Obsidian 相关上游边界

- Obsidian 桌面应用本体不是可复制的开源源码；
- 可复用的是公开 Markdown/JSON Canvas 格式、开放插件生态和许可兼容桥接项目；
- 22 项验真文档中 `obsidian-codex-mcp`、`mcp-obsidian` 可作为文件发现、search、patch/append、REST/MCP 边界参考；
- 在真正复制/依赖前仍必须登记 exact commit、LICENSE、选定文件、修改记录和升级路径；
- MCP 连接成功不等于 OS 已兼容 Obsidian。

### 5.4 当前 P0 不做“全量 369/101 整理”

为了加快闭环，不先耗时补齐所有候选。先只为最小面选定的编辑器、Markdown AST、YAML roundtrip、文件树、JSON Canvas、附件、搜索和 FSRS/卡片候选建立完整 upstream ledger。其余候选保持 deferred，不阻断首条纵切。

### 5.5 对 22 项文档的采用结论

**直接采用：**

- OS/WORK-LAB 边界；
- Obsidian 高保真往返作为 OS P0；
- 源码/API/Adapter 优先和许可证门禁；
- WORK-LAB 只提供 TaskPack/证据/CI/回滚控制面；
- OpenCodeReview 等只在 WORK-LAB/CI 侧作为可选能力。

**调整优先级：**

- Scrapling 静态 Research Adapter、RAG 治理增强不再与 Obsidian 最小面并列阻断；移到首条兼容纵切之后；
- OpenMAIC、EDUKG、3D、Agent Runtime、客户端生态继续延期。

---

## 6. 测试真相

### 6.1 现有 CI 的真实覆盖

最新 main run `31174593430` 成功：

- Python 3.11/3.12/3.13；
- lint；
- wheel-smoke；
- browser-smoke；
- Windows runtime；
- desktop-shell/NSIS；
- a0-gates。

主 Python 版本当前报告：

- OS：1045 passed；
- KB：38 passed；
- Integration：35 passed；
- 单版本合计 1118；
- 三版本合计重复 3354。

本次只读审计还定向执行 Obsidian projection/vault/hardening 测试：**120 passed**。这些测试通过，但只证明现有静态/投影/权限合同。

### 6.2 三个“伪 pytest 测试”

以下文件名以 `test_` 开头，却没有 pytest test function/class：

- `tests/test_workspace_browser_delivery.py`
- `tests/test_workspace_browser_failure_retry_replay.py`
- `tests/test_workspace_delivery_lifecycle.py`

前两个仅因 pytest collection/import 迫使普通 test group 安装 Playwright，但对应 main() 场景并未由 pytest 执行。应迁到 `scripts/`/smoke 目录或改造成真实测试；不能继续让“被收集”冒充“被验证”。

### 6.3 Obsidian 行为缺口

现有测试没有证明：

- 全量 Vault import；
- 重复 import 幂等；
- 未知 frontmatter 字段/类型/注释保留；
- attachments 和目录结构；
- JSON Canvas；
- UI edit/save；
- 外部同时修改；
- conflict/revision/rollback；
- Obsidian 或独立 parser 重新打开；
- Windows/Tauri 点击级 roundtrip。

### 6.4 新完成度证据规则

任何能力达到 8+ 或标记 complete，必须同时有：

1. 用户可操作的真实产品路径；
2. 跨应用/独立 parser fixture import/export/roundtrip；
3. exact-SHA CI；
4. 安装 artifact；
5. 关闭/重启读回；
6. 冲突/失败/回滚证据。

计划、文件名、对象模型、静态字符串、模型自评和一次 happy path 不加到 8 分。

---

## 7. CI、门禁与 Release 全量审计

### 7.1 当前规则是否过重

结论：安全意图合理，但执行频率明显过重，且与仓库自己的 Verification Policy 冲突。

当前每个 PR 和每次 main push均无条件运行完整 9-job；没有 path classifier、GatePlan、schedule/manual full、merge_group、concurrency 或 main tree proof。

### 7.2 最新真实成本

最新 main exact-SHA run `31174593430`：

| job | 总时间 |
| --- | ---: |
| desktop-shell | 652 秒 |
| Python 3.12 | 102 秒 |
| Python 3.13 | 83 秒 |
| Python 3.11 | 70 秒 |
| wheel-smoke | 54 秒 |
| Windows runtime | 47 秒 |
| browser-smoke | 43 秒 |
| lint | 13 秒 |
| a0-gates | 2 秒 |

- 关键路径约 11 分 03 秒；
- 累计 runner 时间约 17 分 46 秒；
- desktop-shell 占 runner 时间约 61%；
- desktop 中 NSIS build 318 秒、Rust cache 83 秒、npm install 71 秒、installed lifecycle 67 秒。

### 7.3 PR→main 完全重复

PR #41：

```text
PR synthetic merge tree
PR head tree
main merge tree
= a532c3097d9b6a53b96a796ce52c5ab44cf22640
```

内容完全相同，却先后运行：

- PR full 9-job 约 11–12 分钟；
- main full 9-job 约 11 分钟。

一次普通合并因此约支付 22–24 分钟关键路径。

### 7.4 Desktop 不是稳定的可复用门禁

同一 PR #41、同一 SHA：attempt 1 因 WM_CLOSE 失败，attempt 2 无代码变化成功。自 8 月 3 日以来至少 4 个 main run 是其他 job 全绿、仅 installer lifecycle 失败。

因此：

- main 重跑曾充当随机 flake detector；
- 不能简单删除所有 main 验证；
- deterministic gates 可逐步复用；
- desktop/installer proof 在连续稳定样本前不能进入复用白名单；
- nightly 应保留 lifecycle 稳定性重复采样。

### 7.5 现有 meta-test 会阻止选择性 CI

`tests/test_ci_a0_gates.py` 硬编码三 Python 版本、全部 job 和静态 needs；`tests/test_verification_performance.py` 甚至断言 `uv export ... ci` 至少出现三次。直接给重型 job 加 `if` 会让 `a0-gates` 因 skipped 而失败。

必须把这些测试改为：classifier 真值表、unknown→full、mixed 取并集、required success、not-required 可 skip、release eligibility 分离。

### 7.6 MS00-C 当前致命问题

分支在一个 GitHub Actions step 中设置：

```powershell
$verificationRun = $successfulRuns[0]
```

随后在另一个独立 step 中直接使用：

```powershell
--verification-ci-run $verificationRun.databaseId
```

PowerShell 变量不跨 step 保留，第二个 step 将拿到空值。必须通过带 `id` 的 step 和 `$GITHUB_OUTPUT` 传递。

此外，该分支删除 v1 的 `ci_run/ci_url`，改成 verification/release 四字段，却保持 `schema_version: 1.0.0`，属于未声明的破坏性合同变更。正确做法：发布 identity schema v2，并保留 v1 reader/migration compatibility。

### 7.7 目标最小安全矩阵

| 变更类别 | 必跑 Gate |
| --- | --- |
| docs/mechanical | static + verdict |
| ordinary Python | static + lint + Python 主版本完整 OS/KB/integration + verdict |
| UI 或 UI 消费的 BFF/API | ordinary baseline + browser smoke |
| Windows runtime/storage/process | ordinary baseline + Windows smoke |
| Rust/Tauri 非打包逻辑 | static + desktop-fast；按调用面追加 Python |
| Tauri build/resources | desktop-fast + desktop-build |
| installer/NSIS | desktop-fast + build + installer lifecycle |
| wheel/package-data | ordinary baseline + wheel-smoke |
| Python public contract/dependency | Python compatibility matrix + wheel |
| Cargo/npm dependency | 对应生态 matrix/audit；不机械触发 Python matrix |
| schema/migration/security/CI/classifier/unknown | full-qualification + 独立审查 |
| nightly/manual/RC | full-qualification |
| formal Release | exact-SHA full + installer/assets/download readback |

普通 Python 先保留主版本完整 1118 tests；当前不建设复杂 affected-test 图谱，因为测试本体不是关键瓶颈。

### 7.8 Release 必须拆语义

必须区分：

1. `PR Selective CI`
2. `Main Evidence Bind`
3. `Full Exact-SHA CI`
4. `Release`

Release 不能继续只搜索“同 SHA、名称 CI、success”。它必须核验 full profile、workflow/policy digest、required Gate 明细、exact commit/tree 和 attestation。Main bind 永远不具备 release eligibility。

---

## 8. WORK-LAB 后期兼容架构

### 8.1 Standalone / Managed 双模式

**Standalone 必须永久存在：** WORK-LAB 缺席、离线或升级失败时，OS 仍能独立分类、验证、Full Qualification 和 Release。

**Managed 后期可选：** WORK-LAB 读取版本化项目 profile，建议 GatePlan 并聚合证据；OS 在受信 CI 中本地重算并保留最终否决权。

```text
effective gates
= global non-bypassable floor
∪ OS project profile
∪ TaskPack explicit extras
∪ event/release mandatory gates
```

WORK-LAB 只能增加 Gate，不能删除 OS Gate。

### 8.2 OS 仓库声明层

建议后续建立：

```text
.worklab/
  project-validation.v1.yaml
  gate-registry.v1.yaml
  ci-impact.v1.yaml
  schema-lock.json
```

它们只包含版本化声明、符号化 Gate ID 和 schema digest：

- 不包含任意 shell；
- 不包含凭据、Vault 内容或绝对用户路径；
- 明确排除出 wheel、Tauri resources 和 installer；
- WORK-LAB 只能选择 OS 预登记 Gate；
- OS 的 Obsidian roundtrip、Windows/Tauri、Release 命令仍由 OS 定义。

### 8.3 兼容合同

- `GlobalValidationPolicyV1`
- `ProjectValidationProfileV1`
- `GatePlanV1`
- `EvidenceEnvelopeV1`
- `TreeProofV1`

证据至少绑定：repo、base/head、实际 checkout commit/tree、changed-path digest、policy/profile/workflow/classifier digest、required Gate、结论、run/attempt、环境 epoch、TTL 和 proof digest。

### 8.4 版本协商和降级

| 情况 | 强制行为 |
| --- | --- |
| WORK-LAB 不可用 | standalone |
| unknown path / 缺 diff | full |
| managed Gate 少于 OS | verdict fail/full |
| unknown required feature/major | managed stop；standalone/full |
| proof 缺失/过期/损坏 | main exact-SHA full |
| workflow/policy/profile 变化 | full |
| Release 只有 main-bind | Release 拒绝 |

WORK-LAB 后期必须先 shadow 一个完整 release train，再进入 canary/enforce；不能要求 OS 同时修改产品 Runtime。

---

## 9. 评分重算

### 9.1 之前的最后三个维度

历史重审分数为：

- 人类学习增强：6.5/10；
- Agent 执行能力：4.2/10；
- 日常可用性：6.2/10。

这些分数曾把后端对象、局部链路和计划计入较多。按后来确定的严格证据规则，当前重新计算：

| 维度 | 当前严格分 | 原因 | 本阶段目标 |
| --- | ---: | --- | --- |
| 人类学习知识闭环 | 4.0 | cards/review/mastery 后端存在，但 Reader/Editor/真实复习/往返不存在 | 8.2 |
| Agent 执行闭环 | 4.2 | 受限 runtime/Job/Receipt 有基础；通用 Agent 已延期 | 本阶段不追 8 |
| 日常可使用程度 | 5.0 | 有真实 Windows release 和导入/投递 UI，但没有核心知识工作区与 C3 往返 | 8.2 |

### 9.2 与新定位兼容的替代 KPI

不通过改名“刷分”，但当前 0.5 阶段应将 release-driving 的 Agent 维度替换为：

| 当前 KPI | 当前分 | 8+ 条件 |
| --- | ---: | --- |
| Evidence-bound AI 使用闭环 | 2.5 | 来源集合→问答→逐条 citation→点击回原文→反馈/重启读回→无证据拒答 |

通用 Agent 执行闭环只有在用户以后重新启用该阶段时，才单独建设到 8+。当前强行追 8 会违反“重型 Agent 内容延期”的决定。

### 9.3 8 分硬门槛

人类学习和日常可用性达到 8+ 必须完成：

```text
安装应用
→ 导入真实 fixture Vault
→ 文件树打开笔记
→ 编辑正文/属性/链接/Canvas
→ 保存并关闭
→ 重启读回
→ 有引用问答
→ 从选区建卡/真实评分复习
→ 导出新 Vault
→ 独立解析器/Obsidian 重开
→ semantic diff
→ 外部修改冲突
→ rollback
```

---

## 10. 整合执行路线

### 10.1 总顺序

为了同时提速和避免 CI 工程吞掉产品主线，执行顺序调整为：

```text
R0-OWNER 云端保护/清理动作
→ R0-RELEASE Release v2 与版本真相
→ R0-CI-SHADOW 分类合同 + concurrency（仍全量）
→ R0-CI-SELECTIVE 选择性 PR + Full Release 隔离
→ 立即返回产品主线

K0 Truth Reset + Legacy Importer Freeze
→ K1 P0 Upstream Selection
→ K2 Compatibility Kernel
→ K3 Obsidian/Markdown/JSON Canvas C3 backend
→ K4 Core Workspace UI
→ K5 Citation + Card/Review
→ K6 Installed Roundtrip/Conflict/Rollback
→ R1 0.5.0 Minimum-Surface Alpha

CI-TREE-PROOF 和更深缓存优化为 P1 canary，
不再阻断 K0–K3。
```

这比旧“先完成 CI-01～04 再回产品”更快：先拿到选择性 CI 的主要收益，tree reuse 等 main 保护与 desktop 稳定后再启用。

### 10.2 单 writer 规则

- 一次一个 TaskPack、一个 branch、一个 PR、一个冻结 head/tree；
- HERMES 是唯一 source writer；
- Codex 对冻结 tree 只读复审；
- 发布后的 PR branch 不 amend/rebase 已审历史，只追加修复 commit；
- 无代码变化不重复全仓审计或完整门禁；
- 失败优先重跑失败 Gate；
- 回滚使用 `git revert` 或 kill switch，不 reset/force push。

---

## 11. 原子 TaskPack

## TP-R0-OWNER｜云端治理与分支清理

**执行者：** repository owner；不是普通代码 writer。

**目标：** 让 PR/CI 证据真正具有强制力。

**动作：**

1. 保护 main：require PR、require up-to-date、禁止 force push/delete、尽可能禁止 admin bypass。
2. 过渡期要求稳定 `a0-gates`；新 `ci-verdict` 验证后迁移 required context。
3. 关闭 stale PR #15。
4. 取消 queued run `31117656711`。
5. 记录分支 SHA 后删除 23 个 merged/superseded 分支。
6. 启用 merge 后自动删除 head branch。
7. 建立 0.5 milestone 和本任务包 Issue，不再让根目录 handoff 充当 backlog。

**验收：** Branch API `protected:true`；required check 非空；direct/force push 负控被拒；PR #15 closed；分支只剩 main + 当前活动分支。

**停止条件：** 当前账号无 admin 权限时只输出 Owner Action，不模拟已完成。

---

## TP-R0-RELEASE｜Release identity v2 与版本真相

**起点：** 从最新 main 新建 branch；可 cherry-pick/复用 MS00-C 的正确部分，但不得直接合并现状。

**目标：** 修复 0.4.5 版本、verification/release 身份和历史发布文档。

**RED：**

- verification run 未跨 step 传递必须失败；
- selective/main-bind run 不能满足 Release；
- identity v1/v2 解析兼容 fixture；
- Cargo.lock 根包版本漂移必须失败；
- verification/release run 混用必须失败。

**实现：**

1. 用 step `id` + `$GITHUB_OUTPUT` 传递 run ID/URL。
2. release identity 升级到 schema v2；保留 v1 reader 和迁移/诊断兼容。
3. `verification_ci_run_id/url` 与 `release_run_id/url` 分开。
4. Release 只接受 `profile=full-qualification`、exact SHA/tree、Gate 明细和 digest。
5. 更新 Cargo.lock 根包到 0.4.5，并统一 cargo `--locked` 合同。
6. 补 v0.4.1–v0.4.4 tag/release ledger；记录 v0.4.4 provenance 字段已知错误，不改历史资产。
7. 修正 README/STATUS/CHANGELOG/THIRD_PARTY_NOTICES 的 release truth。

**GREEN：** targeted contracts + full exact-SHA CI；workflow step-scope 行为测试；不创建正式 v0.4.5 Release。

**回滚：** revert commit；Release 保持阻断，不能退回“任意名为 CI 的 success”。

---

## TP-R0-CI-SHADOW｜分类合同、WORK-LAB v1 与陈旧运行取消

**目标：** 建立选择性 CI 的确定性合同，但本包仍跑完整现有矩阵。

**范围：** `.github/**`、`.worklab/**`、验证脚本、验证政策、CI meta-tests；不改产品 Runtime。

**RED fixture：** docs、Python、UI、Windows、Rust、installer、wheel、dependency、schema/security、CI self-change、unknown、mixed、rename/delete、缺 base、TaskPack extra。

**实现：**

1. 建 Gate Registry、ProjectValidationProfileV1、GatePlanV1、EvidenceEnvelopeV1 schema。
2. 确定性 changed-path classifier；LLM 只能提示，不能决定 required Gate。
3. `unknown/CI/security/schema` fail closed 到 full。
4. 多类别取并集；TaskPack 只能增加 Gate。
5. PR-only concurrency：同 PR 新 synchronize 取消旧 run；main/full/release 不取消。
6. 输出 job setup/test/build/cache 指标和 GatePlan artifact。
7. 重写静态 meta-tests 为 classifier/verdict 合同测试。
8. 将三个伪 pytest 文件改成真实 test 或迁到 scripts；保留原意。
9. `.worklab/**` 明确排除出 wheel/Tauri/installer。

**GREEN：** classifier fixtures 全绿；完整 9-job 仍绿；连续 push 可见旧 PR run 被取消；OS 在没有 WORK-LAB 时正常。

---

## TP-R0-CI-SELECTIVE｜选择性 PR 与 Full Qualification 隔离

**依赖：** SHADOW 历史回放无 false-negative。

**目标：** 普通 PR 不再支付 browser/Windows/wheel/desktop/兼容矩阵的无关成本。

**实现：**

1. 按第 7.7 节矩阵运行 Gate。
2. stable aggregator 始终出现；required success，合法 not-required 才可 skipped。
3. 独立 `Full Exact-SHA CI` 支持 nightly/manual/RC/Release。
4. Release eligibility 只来自 full profile。
5. 普通 Python 保留主版本 1118 tests；3.11/3.13/未来 3.14 进入 compat/nightly/依赖接口变更。
6. OCR/FFmpeg 真行为只在主版本验证一次。
7. browser 只随 UI/BFF 消费面变化。
8. desktop 拆为 fast/build/installer；普通 Rust 不构建 NSIS。
9. Cargo audit 只随 Cargo.lock、nightly/RC/Release。
10. 设置 `CI_FORCE_FULL=true` kill switch，只能增加验证。

**历史回放：** 最近至少 20 个 PR；必须覆盖所有风险类。CI/self-change 本包自身必须 full 一次。

**收益验收：** ordinary Python 目标关键路径 3–5 分钟；UI 目标 4–6 分钟。只认上线后的中位数/P95，不作 SLA。

**回滚：** `CI_FORCE_FULL=true` + revert；保留 shadow 证据用于诊断。

---

## TP-K0-TRUTH-FREEZE｜产品 Truth Reset 与旧 Obsidian 路径隔离

**目标：** 让所有 writer 从正确路线出发，并停止不安全的 legacy apply。

**实现：**

1. 重写 AGENTS 的 mission/scope checksum。
2. 对齐 README、PRODUCT_POSITIONING、STATUS、SYSTEM_BOUNDARY、naming、docs index。
3. 当前 roadmap 改为 Compatibility Kernel → Obsidian C3 → Core Workspace。
4. 重型蓝图标 `deferred/historical_reference`，从默认 agent discovery 排除。
5. legacy Obsidian `/import/apply` 和 course apply fail closed/feature-gated；保留 dry-run inventory 仅作迁移参考。
6. 三个坏 projection endpoint 在实现前返回明确 `501 capability_unavailable`，不能运行时 ImportError。
7. 删除 API/描述中“已吸收 Obsidian/Tana/Notion/Logseq...”的过度声明。
8. truth-drift test 覆盖 AGENTS/README/STATUS/BOUNDARY/naming/roadmap/release table。

**RED：** 恢复旧 cognition-loop mission、错误 release 状态、双向兼容声明或 unrestricted apply 时测试失败。

**GREEN：** 全部事实入口一致；历史内容仍可追溯但不再具备当前指令权。

---

## TP-K1-UPSTREAM｜P0 上游选型与 Reuse Decision Record

**目标：** 先复用，不从零写编辑器、AST、YAML、Canvas、文件树和调度。

**仅审查 P0 候选：**

- Vault file/search/patch 边界；
- Markdown AST/Obsidian extensions；
- YAML roundtrip；
- editor/reader；
- virtual file tree；
- JSON Canvas；
- attachment preview；
- FSRS/card exchange。

**每个候选必须记录：** canonical URL、exact commit/tag、SPDX/hash、维护状态、selected components、scripts/network/secrets、bundle size、Tauri offline/CSP、tests、upgrade、rollback、rejected reason。

**输出：** 选型 ADR + 最小 spike；不得把 demo 标成产品完成。

**GREEN：** 至少验证 1,000 notes tree、1 MB Markdown open/edit/save/restart、Canvas serialization；许可证未知即阻断。

---

## TP-K2-KERNEL｜Compatibility Kernel v1

**目标：** 建立所有软件 Adapter 共用的数据和事务内核。

**核心模型：**

```text
RawAssetV1
VaultSourceV1 / VaultFileV1 / AttachmentRefV1 / VaultLinkV1
ImportSessionV1 / ImportItemV1 / ImportReceiptV1
SyncCursorV1 / RevisionV1 / ConflictV1 / LossReportV1
ExportSessionV1 / RollbackHandleV1
```

**数据流：**

```text
Raw read-only assets
→ staging/parser output + unknown fields
→ canonical compatibility model
→ governed knowledge/learning projection
→ UI/BFF
→ exporter/sync adapter
```

**实现原则：**

- stable ID 基于 vault + normalized relative path/version，不用随机 UUID；
- raw bytes/text、frontmatter、unknown fields 可回读；
- source hash、mtime、size、encoding、parser version；
- import/export dry-run、resume、idempotency；
- Adapter 不直写核心 Knowledge/MKU 表；
- 复用 MigrationOperator、Job/Outbox/Receipt、approved roots、backup；
- UI 只用 public_ref。

**RED：** path escape、symlink/junction、duplicate batch、crash/resume、silent unknown-field loss、direct core write、rollback 不一致。

**GREEN：** 中途崩溃可 resume；同一 source 重跑不重复；rollback 后 DB、export tree、receipt 一致；重启读回相同。

---

## TP-K3-OBSIDIAN-C3｜Obsidian / Markdown / JSON Canvas 高保真纵切

**目标：** 首条真实兼容纵切，不复制 Obsidian 私有 UI/源码。

**导入：**

- 完整目录、Markdown、frontmatter；
- heading/list/task/table/code/math；
- wikilink/alias/embed/heading/block ref；
- tags/callout/properties；
- attachments、missing attachment report；
- JSON Canvas file/text/link/group/edge、位置、尺寸、颜色、未知字段。

**导出：**

- 默认导出到新目录，不覆盖源 Vault；
- 保留路径、文件名、附件、相对链接；
- expected source hash 和 external modification detection；
- 原子写、revision snapshot、backup manifest；
- 无法表达内容进入机器可读 LossReport；silent loss 为阻断。

**fixture：** 中英文、Unicode、空格、长路径、大小写冲突、重复文件名、broken link、循环 embed、多类型 YAML、alias/date/array、Canvas 全节点、100/1k/10k files。

**C3 gate：**

```text
Fixture Vault A
→ import
→ edit one note/property/link/canvas position
→ restart
→ export Vault B
→ independent parser / Obsidian reopen
→ semantic diff within declared tolerance
→ external modification conflict
→ rollback
```

---

## TP-K4-WORKSPACE｜日常核心知识工作台

**目标布局：**

```text
左：Vault / file tree / tags / favorites
中：Reader / Markdown Editor / Canvas
右：Properties / Outlinks / Backlinks / Citations / AI context
顶：Global Search / Command Palette / Create / Import
底：Import/Export/Sync/Conflict/Background status
```

**范围：** open/read/create/update、rename/move/trash、autosave、Properties/Tags、link completion、backlinks、search jump、attachment preview、Canvas edit、conflict UI。

**非目标：** Agent builder、workflow builder、多人协作、移动端、3D。

**GREEN：** 用户从安装启动到 import/search/edit/link/canvas/save/close/restart 全程无需 CLI；Playwright + Tauri WebView 点击级测试。

---

## TP-K5-EVIDENCE-LEARN｜引用 AI 使用与轻量学习

**目标：** 让人与 AI 使用同一份可回链证据，不建设通用 autonomous Agent。

**范围：**

1. 用户选择 Source/Notes 形成 Context Pack。
2. 问答/摘要/对比的关键结论逐条绑定 citation。
3. citation 可点击回原笔记/页/块/附件位置。
4. 无证据时拒答或明确不足。
5. 从选中文本创建 Candidate Card，用户确认后入组。
6. 真实正反面、评分交互和复习历史。
7. 修复多卡 Review 调度和新卡 due。
8. 模型不可用时保留搜索/阅读/复习降级。

**GREEN：** 固定问答集的 citation 命中、拒答、重启读回；多卡 scheduling fixture；Anki/FSRS 组件只在 K1 许可证/选型后接入。

---

## TP-K6-INSTALLED-C3｜安装、重启、冲突、回滚总门禁

**目标：** 从“能演示”升级到“可迁移真实知识库”。

**矩阵：**

- clean installer / upgrade from 0.4.x / uninstall data policy；
- installed Tauri click path；
- import/export/roundtrip/restart；
- crash/resume/rollback；
- Windows path、symlink/junction、非法字符、长路径；
- conflict/concurrent external edit；
- 1k/10k/50k notes performance；
- offline/no-model/no-network；
- no silent loss；
- download artifact digest/readback。

**GREEN：** 所有 Wave A fixture 可复现；silent loss=0；阻断安全问题=0；失败可回滚。

---

## TP-R1-ALPHA｜0.5.0 Minimum-Surface Public Alpha

**前置：** K0–K6 全部达到 Gate，不以合并 PR 数量替代。

**发布：**

- exact tag/commit/tree/full qualification identity；
- Windows installer；
- wheel；
- SBOM、THIRD_PARTY_NOTICES、license report；
- checksums/provider digest/download recompute；
- install/start/import/restart/export/uninstall evidence；
- Compatibility Matrix 和已知 LossReport；
- 0.4.x migration/backup/rollback guide。

**禁止：** 任一 identity、C3 fixture、installer 或回滚证据缺失时宣布 Alpha 完成。

---

## TP-CI-TREE-PROOF｜后续 main evidence bind canary

**优先级：** P1，不阻断 K0–K3。

**前置：** main protected；Release 已只认 Full Exact-SHA；classifier/verdict稳定；desktop lifecycle 达到连续至少 10 次相关成功且零同类 flaky。

**阶段：**

1. 只产出 TreeProof，main 仍 full；
2. docs-only canary；
3. ordinary Python/UI；
4. Windows；
5. desktop/installer 最后评估。

**校验：** 实际 checkout merge ref tree、base/head、policy/profile/workflow/classifier digest、Gate 结论、producer、TTL、artifact digest。任一不匹配自动 full。

**Release：** main bind 永远不可满足 Release。

---

## 12. 避免反复审计和验证的规则

### 12.1 审计触发

| 事件 | 审计范围 |
| --- | --- |
| 普通 PR | changed paths + TaskPack + required Gate |
| CI/security/schema/architecture | 专项审计 + full qualification |
| 新阶段 | 一次 frozen-tree 阶段审计 |
| nightly | full profile + flaky/dependency 观察 |
| RC/Release | exact-SHA full + artifact readback |
| 无代码/策略变化 | 不重复相同审计 |

### 12.2 证据复用

只有 subject tree、policy/profile/workflow/classifier digest、required Gate、环境 epoch 和有效期均匹配才能复用。计划、自评和文档声明不能替代运行证据。

### 12.3 每包只做必要验证

默认：

1. 一次 RED；
2. 一次实现后 GREEN；
3. 一次最终相关本地 Gate；
4. 一次 GitHub CI。

代码未变不重复；失败优先重跑失败 Gate；最终 frozen tree 变化后再更新相应证据。

### 12.4 CI 指标账本

固定输出：event、commit/tree、profile/policy、risk class、required/not-required Gate、queue/setup/test/build、cache hit、rerun/cancel/fallback、duplicate tree、runner failure/product failure、Release eligibility。

---

## 13. 统一完成报告模板

每个 HERMES TaskPack 完成时输出：

```text
taskpack_id
scope checksum / non-goals
base commit/tree
head commit/tree
branch / PR
changed files / diffstat
reused upstream / exact revision / license / integration mode
contracts / schema / migration
RED command + expected failure
GREEN command + result
final local gate
GitHub run ID/URL
GatePlan/Evidence/TreeProof digest
required gates + actual conclusions
fixture / semantic diff / loss report
install/restart/conflict/rollback evidence
rollback steps
remaining risks
next TaskPack
```

---

## 14. 最终 Definition of Done

### 产品

- 用户无需 CLI 完成 import/read/edit/link/search/canvas/AI Q&A/review/export；
- 主导航不以 planned Agent 页面为中心；
- 新定位在所有当前事实入口一致。

### 兼容

- Obsidian/Markdown/JSON Canvas 达到 C3 fixture；
- Compatibility Kernel 能承载第二个 PKM Adapter；
- unknown/unsupported 内容都有 LossReport；silent loss=0。

### 工程

- P0 复用组件都有 exact upstream/license/NOTICE/SBOM/upgrade/rollback；
- source adapter 不直写治理核心；
- import/export 可 resume、restart、rollback；
- 用户源数据默认只读，覆盖需显式授权和 backup。

### 验证/发布

- selective PR、full exact-SHA、main bind、Release 身份完全分离；
- browser、Tauri、Windows、installer 和 C3 roundtrip 全绿；
- main 受保护；
- 0.5.0 tag/asset/digest/download/install/readback 完整；
- WORK-LAB 缺席时 OS 仍独立验证和发布。

### 评分

- 人类学习知识闭环 ≥ 8.0；
- Evidence-bound AI 使用闭环 ≥ 8.0；
- 日常可使用程度 ≥ 8.0；
- 通用 Agent 执行闭环保持 deferred，除非用户另行解冻。

---

## 15. 立即执行的五个动作

1. Owner 保护 main、关闭 PR #15、取消遗留 queued run；暂不删除任何未记录 SHA 的分支。
2. 不直接合并 MS00-C；以其为参考新建/修复 Release v2 TaskPack，补 GITHUB_OUTPUT、v1 reader、Cargo.lock 和 release ledger。
3. 落地 CI Shadow → Selective 两包；Full Release 隔离后立即返回产品主线，不等待 tree proof。
4. 执行 K0 Truth Reset，fail-close legacy Obsidian apply 和坏 projection endpoints。
5. 执行 K1/K2：只审 P0 上游，建立 Compatibility Kernel，然后进入真实 Obsidian C3 fixture。

---

## 16. 证据入口

- 仓库：<https://github.com/DTALEX66/Cognitive-Loop-OS>
- 审计 main：<https://github.com/DTALEX66/Cognitive-Loop-OS/commit/9fefcfcae8380c84447e48fcf71cabeeab00f726>
- 最新 main CI：<https://github.com/DTALEX66/Cognitive-Loop-OS/actions/runs/31174593430>
- PR #41：<https://github.com/DTALEX66/Cognitive-Loop-OS/pull/41>
- stale PR #15：<https://github.com/DTALEX66/Cognitive-Loop-OS/pull/15>
- MS00-C branch：<https://github.com/DTALEX66/Cognitive-Loop-OS/tree/feat/ms00-c-release-identity>
- v0.4.4 Release：<https://github.com/DTALEX66/Cognitive-Loop-OS/releases/tag/v0.4.4>
- v0.4.4 verification CI：<https://github.com/DTALEX66/Cognitive-Loop-OS/actions/runs/30837105199>
- v0.4.4 Release run：<https://github.com/DTALEX66/Cognitive-Loop-OS/actions/runs/30839451084>
- Product positioning：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/9fefcfcae8380c84447e48fcf71cabeeab00f726/docs/PRODUCT_POSITIONING.md>
- CI workflow：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/9fefcfcae8380c84447e48fcf71cabeeab00f726/.github/workflows/ci.yml>
- Release workflow：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/9fefcfcae8380c84447e48fcf71cabeeab00f726/.github/workflows/release.yml>
- Verification policy：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/9fefcfcae8380c84447e48fcf71cabeeab00f726/docs/VERIFICATION_POLICY.md>

---

## 17. 最终冻结决策

1. 项目不是旧认知闭环系统，也不是通用 Agent OS。
2. 当前最小面是全面兼容吸收；Obsidian/Markdown/JSON Canvas 是第一高保真纵切。
3. 现有后端底盘保留，产品表面和 Compatibility Kernel 优先补齐。
4. 复用许可兼容的依赖/API/源码优先，自研最后。
5. MS00-C 当前不可直接合并；必须修复 step scope、schema v2 和 backward compatibility。
6. main 未保护前不开启 tree bind。
7. CI 先完成选择性 PR 与 Full Release 隔离；tree proof 后置 canary，不继续阻断产品主线。
8. 正式 Release 永远需要 exact-SHA full、installer、资产、下载哈希和身份读回。
9. WORK-LAB 后期只消费版本化声明和证据，不进入 OS Runtime，不降低 OS Gate。
10. 完成只认真实用户路径、跨应用 roundtrip、安装/重启、冲突和回滚证据。
