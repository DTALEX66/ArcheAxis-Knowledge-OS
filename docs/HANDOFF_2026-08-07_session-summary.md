# Handoff — archeaxis-workspace 会话交接与信息摘要（2026-08-07）

> 仓库：`DTALEX66/archeaxis-workspace`（public）
> 交接基线：`main@f555b0560a1443b1ba385d106de3536becaf2bb9`
> 编制：2026-08-07（UTC 收尾）
> 性质：信息摘要 + 错误复盘 + 完整交付证据 + 后续路线

---

## 1. 当前项目真实状态

### 1.1 代码与发布

```text
main HEAD     f555b0560a1443b1ba385d106de3536becaf2bb9（本地 == 云端，工作树 clean）
开发线版本    0.5.0
发布状态      unreleased / development / public=false
历史 Release  v0.4.0、v0.4.4 公开；v0.4.2 draft；tags v0.4.0–v0.4.4（保留不重写）
```

### 1.2 已合并里程碑（本阶段全部闭环）

| TaskPack | PR | merge SHA | main CI |
|---|---|---|---|
| R0-RELEASE（identity schema v2） | #42 | `d49aa3d4` | `31183343446` ✅ |
| R0-CI-SHADOW（GatePlan 分类器） | #43 | `13c5e451` | ✅ |
| R0-CI-SELECTIVE（选择性门禁） | #44 | `ba3b200c` | `31188385075` 10/10 ✅ |
| R0-CI 修复1（tests/** 归类） | #46 | `d9d8833a` | `31191909052` ✅ |
| R0-CI 修复2（根目录 **/*.md） | #47 | `22a61fe` | `31193479622` ✅ |
| K0 Truth Reset（产品真相 + 501） | #45 | `ed0888f` | `31195559570` ✅ |
| 交接文档 | — | `f555b05` | `31199163649` ✅ |

### 1.3 选择性 CI 成果（已真实验证）

普通 Python/docs 变更走**轻量路由**：desktop-shell / windows-runtime / wheel-smoke / browser-smoke 全部 skip，关键路径从 ~23 分钟降至 ~3 分钟。desktop WM_CLOSE flaky 不再阻塞轻量 PR。main push 因无 base diff 走保守 full（安全默认）。

---

## 2. 审计与清理结果

### 2.1 云端分支

- 审计前 30 个非 main 分支 → 删除 27 个（全部已合并/被取代，无 open PR、无唯一未吸收 WIP）
- 保留 4 个：`main` + `feat/archeaxis-desktop-a1-migration` + `feat/archeaxis-desktop-a1-violet-core` + `release/v0.4.0-contract`（superseded 历史，安全起见保留）

### 2.2 本地分支

- 删除 27 个已合并进 main 的本地分支 + `git fetch --prune`
- 保留 17 个未合并本地分支（`work/tp12-facades`、`fast/*`、`agent/*` 等含独特提交，需独立审查）

### 2.3 本地项目瘦身：13.8G → 7.0G（释放约 6.8G）

| 删除项 | 大小 | 理由 |
|---|---|---|
| `desktop/src-tauri/target/debug` | 1.9G | Cargo 构建产物，可再生 |
| `.hermes/task-runtime/cache/cargo-target` | 4.0G | Cargo 构建产物，可再生 |
| `.hermes/task-runtime/pycache` | 115M | Python 字节码，可再生 |
| `.hermes/task-runtime/tmp/pytest-of-ALEX` | 128M | pytest 临时，可再生 |
| 根 `.pytest_cache`/`.ruff_cache`/`__pycache__` | ~150K | 测试缓存，可再生 |

**保留项**：VS Build Tools 工具链 3.4G、任务证据（desktop-dev DB / artifacts / evidence / handoff）、desktop-attachments（交接输入）、uv/playwright 缓存、便携运行时。

### 2.4 Hermes 根目录区分

**结论：`C:/Users/ALEX/AppData/Local/hermes/` 内无任何 archeaxis-workspace 项目 spill。** 全部为 Hermes 全局基础设施（backups 4.5G、hermes-agent 4.1G、state.db 2.5G、skills/sessions/cron/config 等），**全部保留，未删除任何全局 state**。

### 2.5 外置配置区审计

- **`D:\All projects\OS configuration`（8.7G）→ 必需保留**。活跃工具链（scoop 4.2G / rust 1.8G / playwright 690M）+ 已注册 WSL2 Ubuntu-24.04 VHD（2.2G）+ 激活脚本。当前 shell 环境变量全部指向此区。未来成品状态仍需要。
- **`C:\Users\ALEX\scoop` → 已是 Junction**（指向 D 盘 OS configuration），C 盘无真实数据可回收。删除会破坏旧路径兼容，保持现状。

---

## 3. 错误总结与经验（本次会话关键失败模式）

### 3.1 desktop WM_CLOSE 生命周期 flaky（最高频）

- **症状**：`verify_nsis_install.ps1:132` — `desktop shell did not exit after WM_CLOSE`
- **性质**：已知非确定性。同一 tree 多次出现"某次通过、某次失败"（PR #42 exact-head 20m3s 成功 vs 后续 main 重跑失败）。
- **处置**：重跑失败 job（`gh run rerun <run> --failed`）。不归因于代码，不改代码。已通过 R0-CI-SELECTIVE 使轻量 PR 不再触发 desktop。
- **未来**：K 阶段需拆分 desktop-fast/build/installer-lifecycle + 稳定性门槛根治。

### 3.2 backend_lifecycle 启动竞态 flaky

- **症状**：`launches_token_bound_core_and_shuts_down_cleanly FAILED`（backend launch failed）
- **性质**：非确定性启动竞态，同 tree 在另一 run 通过。重跑解决。

### 3.3 CI runner / apt 基础设施卡顿

- **症状**：`test(3.12)` 卡在 OCR apt-get 安装 21 分钟（正常 45s）；run 长时间 pending 无 job。
- **性质**：GitHub runner 调度/网络问题，非代码。取消重跑解决。

### 3.4 PowerShell 跨 step 变量泄漏（R0-RELEASE 已修）

- **症状**：`$verificationRun` 在一个 step 定义、另一 step 使用 → 空值。
- **根因**：GitHub Actions 每个 step 独立进程，PowerShell 变量不跨 step。
- **修复**：`id: require_ci` + `$GITHUB_OUTPUT` 传递。

### 3.5 classifier full-qualification 折叠导致重型 job 误 skip（R0-CI-SELECTIVE 已修）

- **症状**：full 模式把 required_gates 折叠为 `[ci-verdict]`，重型 job `contains()` 为 false → 全部 skip。
- **修复**：重型 job `if` 增加 `full_qualification == 'true'` 条件。

### 3.6 classifier 路径归类缺陷（真实 CI 暴露，已修×2）

- **`tests/**` 未归类 → unknown → full**（PR #46 修复：加入 ordinary-python）
- **根目录 `**/*.md` 不匹配根文件（AGENTS.md）→ unknown → full**（PR #47 修复：`_path_matches` 支持 `**/` 前缀）

### 3.7 gateplan 目录不存在（R0-CI-SHADOW 已修）

- `fresh checkout` 无 `.hermes/task-runtime/` → 写入 `FileNotFoundError`。修复：`os.makedirs(exist_ok=True)`。

### 3.8 YAML 写入 linter 误报（本地经验）

- write_file 对 `.worklab/*.yaml` 的 `schema_version: 1.0` 误报"mapping values not allowed"。
- 根因：多行注释未加 `#` 前缀 + `**/` 被当 YAML alias。用 terminal heredoc + 每行注释规避。

---

## 4. 执行边界（全程遵守）

- ✅ E 盘全程未触碰
- ✅ Hermes 全局基础设施未修改/删除
- ✅ 未创建/删除 tag 或 Release
- ✅ 未访问凭据、auth、密钥
- ✅ 分支删除前均确认无 open PR、无唯一未吸收 WIP
- ✅ 项目 git 工作树全程 clean

---

## 5. 未完成 / 保留项

- 17 个未合并本地分支 + 3 个 superseded 远端分支（待独立审查，非本次范围）
- R0-OWNER：branch protection 待用户确认后启用（R0 已稳定，具备条件）
- desktop lifecycle 稳定性根治（K 阶段拆分 desktop）

---

## 6. 后续路线

```text
K1 P0 上游选型（编辑器/Markdown AST/YAML/JSON Canvas/文件树/FSRS）
→ K2 Compatibility Kernel v1
→ K3 Obsidian/Markdown/JSON Canvas C3
→ K4 Workspace UI
→ K5 Citation + Card/Review
→ K6 Installed C3/Conflict/Rollback
→ R1 0.5.0 Minimum-Surface Alpha
```

现实闭环估算：约 5–7 周（K3/K4 Obsidian 高保真 C3 + 工作台 UI 为主瓶颈）。

---

## 7. 交接摘要（速览）

**已完成**：R0 全套（Release identity v2 + 选择性 CI）+ K0 Truth Reset + 审计清理（云端分支 30→4、本地 13.8G→7.0G）+ 交接文档上传。全部 main CI 闭环。

**边界**：E 盘未触碰；Hermes 全局未动；无新 tag/Release；工作树 clean；本地==云端（`f555b05`）。

**工具链**：`D:\All projects\OS configuration` 活跃必需（激活脚本 + WSL2）；C 盘 scoop 为 junction 兼容保留。
