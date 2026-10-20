# Handoff — archeaxis-workspace 完整交接与阶段总结（2026-08-07 续）

> 仓库：`DTALEX66/archeaxis-workspace`（public）
> 交接基线：`main@bef99eea6a52e4f5a43eb58cdcc1499a43e3f5db`
> 编制：2026-08-07（UTC 收尾）
> 性质：阶段总结 + 交接 + 当前真实状态（含进行中 K2 与待查 CI）

---

## 1. 当前项目真实状态

```text
main HEAD     bef99eea6a52e4f5a43eb58cdcc1499a43e3f5db（本地 == 云端，工作树 clean）
开发线版本    0.5.0
发布状态      unreleased / development / public=false
对外定位      ArcheAxis Knowledge / Human–AI Learning Workspace（云端 + 本地描述已统一）
机器身份      ArcheAxis-Knowledge-OS（按用户决定保留，0.5.0 收口窗口再改）
历史 Release  v0.4.0、v0.4.4 公开；v0.4.2 draft；tags v0.4.0–v0.4.4（保留不重写）
```

## 2. 已闭环阶段

| 阶段 | TaskPack | PR | merge SHA | main CI |
|---|---|---|---|---|
| R0-RELEASE | Release identity schema v2 | #42 | `d49aa3d4` | `31183343446` ✅ |
| R0-CI-SHADOW | GatePlan 分类器 + concurrency | #43 | `13c5e451` | ✅ |
| R0-CI-SELECTIVE | 选择性门禁 + ci-verdict | #44 | `ba3b200c` | `31188385075` 10/10 ✅ |
| R0-CI 修复1 | tests/** 归类 | #46 | `d9d8833a` | `31191909052` ✅ |
| R0-CI 修复2 | 根目录 **/*.md | #47 | `22a61fe` | `31193479622` ✅ |
| K0 | Truth Reset（AGENTS + 501） | #45 | `ed0888f` | `31195559570` ✅ |
| K1 | P0 上游选型 ADR + spike | #48 | `bef99eea` | `31203668524` 运行中 |
| 审计清理 | 分支/缓存/交接上传 | — | `2698736` | `31199163649` ✅ |

**已完成 = 7 个 TaskPack + 审计清理**，全部 exact-head + merge-SHA 真实证据闭环（K1 merge-SHA main CI 运行中，属收尾）。

## 3. 进行中

| 阶段 | 状态 | 详情 |
|---|---|---|
| K2 Compatibility Kernel v1 | 分支 `feat/k2-compatibility-kernel`，commit `59a7ddb`，PR #49 已创建 | VaultFile 模型 / 导入事务 / revision 回滚，本地 7 passed + 全量 1078 passed |
| K1 merge-SHA main CI | `31203668524` 运行中 | docs push 验证，等 desktop-shell |

### K2 PR #49 CI 待查（重要，如实记录）

PR #49 exact-head CI `31203965454`：
- `gh run view` 最终 **conclusion=failure, attempt=1**
- 但 job 日志尾部显示 `1085 passed, 1 skipped` / `38 passed` / `35 passed`，且 a0-gates pass
- **矛盾**：watcher 显示 test(3.11/3.12/3.13) fail，但日志显示全部通过
- **不能放行**：必须查明为何 run 判 failure 而测试实际通过（可能某测试在 CI 失败而本地跳过/通过，或日志截取问题）
- **下一步**：读 test job 完整日志找 `exit code`/失败点，修复后 push 新 commit 重验

## 4. 错误复盘与经验（跨 TaskPack）

| # | 错误 | 根因 | 修复 |
|---|---|---|---|
| 1 | desktop WM_CLOSE flaky | 非确定性生命周期竞态 | 重跑失败 job；选择性 CI 隔离 |
| 2 | backend_lifecycle 启动竞态 | 非确定性 | 重跑 |
| 3 | CI runner/apt 卡顿 | GitHub 基础设施 | 取消重跑 |
| 4 | PowerShell 跨 step 变量泄漏 | Actions 每 step 独立进程 | `$GITHUB_OUTPUT` 传递 |
| 5 | full 折叠致重型 job 误 skip | required_gates 折叠为 ci-verdict | `if` 加 full_qualification 条件 |
| 6 | tests/** 归类 unknown→full | classifier 路径未覆盖 | profile 加 tests/** |
| 7 | 根 .md 归类 unknown→full | `**/*.md` 不匹配根文件 | `_path_matches` 支持 `**/` 前缀 |
| 8 | gateplan 目录不存在 | fresh checkout 无 .hermes | `os.makedirs(exist_ok=True)` |
| 9 | YAML linter 误报 | 注释未加 # + **/ 被当 alias | heredoc + 每行注释 |

## 5. 审计与清理结果

- **云端分支**：30 → 4（删 27 个已合并/被取代；保留 main + 3 superseded）
- **本地分支**：删 27 个已合并 + prune；保留 17 个未合并（`work/tp12-facades`/`fast/*` 等需独立审查）
- **本地项目瘦身**：13.8G → 7.0G（删 target 1.9G、cargo-target 4.0G、pycache、pytest-tmp）
- **Hermes 根目录**：无项目 spill，全部全局基础设施保留
- **外置配置区**：`OS configuration`（8.7G）必需保留（活跃工具链 + WSL2）；C 盘 scoop 为 junction 兼容
- **描述统一**：云端 About + README + pyproject 对齐 `Human–AI Learning Workspace`

## 6. 执行边界（全程遵守）

- ✅ E 盘全程未触碰
- ✅ Hermes 全局基础设施未修改/删除
- ✅ 未创建/删除 tag 或 Release
- ✅ 未访问凭据/auth/密钥
- ✅ 分支删除前确认无 open PR、无唯一未吸收 WIP
- ✅ 项目 git 工作树 clean

## 7. 待办

| 优先级 | 事项 | 说明 |
|---|---|---|
| P0 | K2 PR #49 CI 查明 | test fail 与日志通过矛盾，必须定位根因后放行 |
| P1 | K1 merge-SHA main CI 闭环 | 等 desktop-shell |
| P1 | K3 Obsidian C3 | 纵切主瓶颈（roundtrip、JSON Canvas、conflict/rollback） |
| P2 | K4 Workspace UI | 文件树/Reader/Editor/搜索/画布 |
| P2 | K5 Citation + Card/Review | 引用问答、复习调度 |
| P3 | K6 Installed C3 + R1 0.5.0 | 总门禁 + 发布（含命名收口窗口） |
| Owner | branch protection 启用 | R0 已稳定，待用户确认 |

## 8. 后续路线

```text
K2（CI 待查→合并）→ K3 Obsidian C3 → K4 UI → K5 Citation/Card
→ K6 Installed C3 → R1 0.5.0 Alpha（含命名收口）
```

现实闭环估算：约 5–7 周（K3/K4 Obsidian 高保真 C3 + 工作台 UI 为主瓶颈）。

## 9. 交接速览

**已完成**：R0 全套（Release identity + 选择性 CI）+ K0 Truth Reset + K1 选型 + 审计清理 + 描述统一 + 交接上传。7 个 TaskPack exact-head 全部绿。

**进行中**：K2（实现完成，CI 待查）；K1 main CI 收尾。

**边界**：E 盘未碰；Hermes 全局未动；无新 tag/Release；工作树 clean；本地==云端（`bef99eea`）。

**工具链**：`OS configuration` 活跃必需；C 盘 scoop 为 junction 兼容保留。
