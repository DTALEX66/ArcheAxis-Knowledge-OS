> ARCHIVED 2026-08-12 — 历史验证快照（2026-08-09），来源分支
> `docs/verification-summary-2026-08-09`（git 对象无损保留）。
> 含当时 NO-GO 结论与旧名（ArcheAxis OS/Cognitive-Loop-OS），为历史记录；
> 当前状态以 docs/truth/EXECUTION_STATUS_LOG.md 为准。
>
# Cognitive-Loop-OS 验证摘要与问题总表

> 日期：2026-08-09
>
> 本文是当前验证结果的云端交接摘要，不是任务包完成声明，也不是正式发布声明。所有结论按证据层级区分：真实执行/回读、源码实现、构建产物、声明性文档。

## 1. 版本与仓库基线

| 项目 | 当前值 |
|---|---|
| canonical 项目 | `D:/All projects/Cognitive-Loop-OS` |
| 公开产品名 | ArcheAxis OS |
| 开发仓库名 | Cognitive-Loop-OS |
| 本次云端文档基线 | `origin/main` at `492fac5982c693eb668d31cc51a6a59bac83b7a1` |
| 本地开发分支 | `feat/p1-compat-kernel-hardening` |
| 本地开发分支 HEAD | `84a0dfdb9c3493421d7a4864065278bb06b51275` |
| 受保护用户 WIP | `tests/fixtures/readability_article.html` |
| 公开 Release | `v0.5.0`，public / non-draft / non-prerelease |
| 当前发布结论 | `NO-GO` |

本次云端同步只上传本文，不上传 `.hermes/` 运行数据、真实资料、用户 WIP 或未审计的本地分叉提交。

## 2. 已验证的工程与产品能力

### 2.1 Compatibility Kernel 与数据边界

- 已建立多格式摄取、Research、Knowledge、Learning、Workspace、任务和审计相关的代码路径。
- Obsidian Markdown / JSON Canvas 适配器已实现安全边界：只解析 Canvas text 节点，保留 file/link/group 标签；不打开附件、不跟随链接、不请求 URL、不执行节点内容；非法节点类型失败。
- 内部运行时查询允许 query-only live-WAL 读取；外部/离线读取保持 checkpoint-only fail-closed。
- 真实资料源 `D:/All projects/ceshi/Obsidian知识库` 只读使用，不写回。
- 资料源盘点历史结果：总文件 22051、Markdown 5600、Canvas 22、图片 1287、学习资料候选 6923。

### 2.2 后端真实闭环

已对 `10_课程库` 的 1161 个真实候选资料完成后端 HTTP/intake 闭环：

```text
文件级结果：1161
HTTP 200：1161
HTTP 422：0
请求异常：0
Markdown：1140
Canvas：20
TXT：1
durable jobs：1072
succeeded jobs：1072
outbox delivered：1072
receipts：1072
pending：0
missing receipt：0
restart readback：PASS
```

1072 个 durable jobs 与 1161 个文件的差异来自内容/来源幂等合并，不能解释为漏测。

真实课程样本还完成过：

```text
HTTP intake
→ job succeeded
→ delivery
→ receipt
→ Research candidate
→ Learning artifact
→ practice ×3
→ mastery=true
→ machine candidate
→ runtime restart
→ durable readback
```

### 2.3 内部未发布 Windows NSIS 候选

测试目录：

```text
D:/All projects/ceshi/ArcheAxis-OS-internal-preview
```

候选安装器：

```text
ArcheAxis OS_0.5.0_x64-setup.exe
```

已回读：

```text
Version=0.5.0
SHA-256=a0d012530c2815ae2442dc8c5ca3716ce31f99d83f0a63e9b5f12c06dd4b07e2
```

安装生命周期结果：

```json
{
  "Version": "0.5.0",
  "WorkspaceStatus": 200,
  "PycGrowth": 0,
  "GracefulShutdown": true,
  "ForcedTreeCleanup": true,
  "CleanUninstall": true
}
```

安装版单实例最终重启读回：

```text
jobs：7
outbox：7 delivered
receipts：7 recorded
release：0.5.0 / unreleased / development
结论：PASS
```

测试过程中曾出现 `restart port missing`。根因是前一轮脚本留下了本次测试创建的 shell/backend 进程树，后续重启形成了无 backend 的第二个 shell。清理了明确属于本次测试的 PID tree 后，单实例重启读回通过。该历史失败必须保留，不能删除为“从未发生”。

### 2.4 安装版真实格式 smoke

当前已在安装后的真实 runtime 通过 Workspace HTTP 入口验证：

| 格式 | 检测 | 引擎 | 结果 |
|---|---|---|---|
| Markdown | `md` | `passthrough` | PASS |
| JSON Canvas | `canvas` | `json-canvas` | PASS |
| TXT | `txt` | `passthrough` | PASS |
| CSV | `csv` | `markitdown` | PASS |
| HTML | `html` | `trafilatura` | PASS |
| PNG | `image` | `pillow` | PASS |
| JPG | `image` | `pillow` | PASS |

这是 HTTP intake 证据，不等同于 WebView 文件选择器点击级证据。

### 2.5 桌面壳与生命周期

- Release EXE 已验证为 Windows GUI subsystem。
- Tauri shell → bundled Python runtime → loopback Core readiness 路径已有实现。
- 安装版启动、Workspace API 200、正常关闭、owned PID tree 清理、卸载均有实测。
- Python runtime 使用 `-B -I`，安装资源目录没有预期 `.pyc` 增长。
- NSIS 仍是正式分发候选；便携版只作为 `internal preview`，不能替代正式 Release Qualification。

## 3. 当前明确未完成与阻塞项

### P0：正式发布仍 NO-GO

1. **公开 `v0.5.0` 不是当前全部任务范围的完成版。** 不修改 immutable tag，不覆盖旧 Release。
2. **PDF 公开安装版故障曾被真实复现。** 原因是 `markitdown` 主包没有包含 PDF extra；候选修复使用 `markitdown[pdf]>=0.1`，但必须继续证明依赖进入最终 bundle/installer，并通过真实 PDF 转换和重启读回。
3. **版本身份存在 `0.4.5/0.5.0` 漂移风险。** 必须修复源 manifest、构建注入、wheel、portable、NSIS 和发布回读链。
4. **签名/公开发行链未关闭。** 未签名安装器只能作为本地 Alpha/internal preview 证据。

### P1：安装版能力矩阵尚未闭合

以下格式尚无完整“真实二进制 → 安装 runtime → 转换/识别 → durable job → delivery/receipt → 重启读回”证据：

```text
PDF
DOCX
PPTX
XLSX
MP3
WAV
MP4
```

特别限制：

- 图片 OCR 需要实际 Tesseract 依赖并验证 executable/bundle；不能把 Pillow 图像识别当作 OCR。
- 音频/视频不能仅因文件 picker 接受扩展名就称为已支持。
- ASR 当前保持 `unavailable / not_implemented`。
- HTML/URL 的可用范围必须按真实 adapter、外部依赖和安装包内容分别记录。
- 二进制格式必须使用真实二进制样本；不能将改名的纯文本 fixture 当作 PDF/DOCX/PPTX/XLSX 证据。

### P1：用户级 UI 证据不足

- 已有安装版 HTTP intake 证据。
- 尚未完成 WebView 文件选择器的点击级导入证据。
- 尚未证明普通用户从安装版界面完成全格式选择、导入、错误显示、重试和结果回读。
- 前端布局仍在演进时，前后端必须绑定同一 exact-SHA，并保持兼容 DTO/API；未验证组合不得标正式发行。

### P1：CI/PR/候选治理

- PR #68（PDF 依赖修复）和 PR #69（Release GUI subsystem）必须重新回读 exact-head CI、合并状态、merge-SHA main CI。
- release-candidate worktree 中的 `prepare_bundle.py`、`tauri.conf.json`、requirements/test gate 变更仍需审阅，不能因内部构建成功自动进入正式分支。
- 本地开发分支相对远端同名分支存在分叉：本地有 8 个额外提交，远端有 15 个本地未包含提交。本次云端同步不自动合并它们。

### P2：已知适配器回归

适配器较大回归曾得到：

```text
118 passed, 1 skipped, 4 failed
```

失败来自可选适配器：

```text
trafilatura
newspaper4k
youtube-transcript-api
readabilipy
```

这些不能写成全绿；应分别归类为可选依赖缺失、外部服务限制、适配器故障或产品缺陷，并重新执行当前 exact tree 的定向测试。

## 4. B/C/R TaskPack 后续顺序

权威任务包：

```text
codex-taskpacks/B线_CODEX任务包.md
codex-taskpacks/C线_CODEX任务包.md
codex-taskpacks/定时推送与项目雷达_CODEX任务包.md
```

严格顺序：

```text
G0 任务包身份/基线
→ B1 + R1 schema
→ C1 validator
→ B2 → B3 → B4 → B5 → B6
→ R2 → R3 → R4 → R5 → R6
→ C2 → C3 → C4 → C5
→ C6 联调报告
```

### B线任务

- **B1**：三个项目引用同一 shared schema，全部 fixtures 通过。
- **B2**：IR 生成 IntakeCard，验证 `why / what_to_absorb / what_not_to_absorb / risk_level`。
- **B3**：IntakeCard 生成 EngineeringContract，验证 `goal / deliverables / acceptance_criteria / blocked_actions`。
- **B4**：EngineeringContract + evidence 生成 ContextPack，验证 `goal / sources / evidence / constraints`。
- **B5**：ContextPack 生成 TaskPack，验证 `steps / allowed_tools / blocked_tools / success_criteria / risk_level`。
- **B6**：Cognitive-OS 执行 mock TaskPack，低风险 success、高风险 blocked、所有步骤有 trace，并回读 MachineLesson。

### C线任务

- **C1**：公共 schema validation 脚本，合法 fixture 全通过，非法字段具体报错。
- **C2**：B → A TaskPack 投影，`target_path` 合法且 `write_policy=dry_run`。
- **C3**：B → A Trace，`trace_id / task_id / status / steps` 完整。
- **C4**：B → A MachineLesson，`lesson / anti_pattern / next_constraint` 非空。
- **C5**：A → B CoursePack，`course_id / sections / cards / review_items` 完整。
- **C6**：生成 `reports/B_C_integration_report.md`，列出通过、失败、blocked 和下一步。

### R线任务

- **R1**：新增并验证 `daily_brief`、`github_project_candidate`、`open_source_project_profile` schemas。
- **R2**：建立 Project Radar 的 collectors/scoring/outputs/filters 骨架，不自动 clone、安装或执行项目。
- **R3**：生成 CSV/Markdown 筛选表，字段完整且输出稳定。
- **R4**：实现 `token_saving / efficiency_gain / local_first / system_fit / risk_penalty / total` 评分。
- **R5**：仅对 `total >= 3.5`、非 critical、允许 absorption mode 的项目生成 IntakeCard。
- **R6**：生成包含 `gold / design / technology / ai / github_ai_projects / recommended_intake_cards` 的日报 JSON/Markdown；不负责真正发送通知。

任务包声明、模块存在、历史报告或 CI 绿色均不能替代每一项真实验收。

## 5. 下一执行批次

下一批应按以下顺序执行，不跨越阻塞：

1. 复核 PR #68/#69 exact-head 和 merge/main 状态。
2. 审阅 release-candidate worktree 的完整 diff，确认哪些候选修改进入修复 PR。
3. 完成 PDF extra 的 bundle/installer 内容清单和真实 PDF 安装版闭环。
4. 建立全格式真实二进制样本 manifest；缺样本的格式保持 `UNVERIFIED`。
5. 完成 WebView 文件选择器点击级导入和错误/retry UI 证据。
6. 完成安装版格式矩阵逐项的 job/delivery/receipt/restart readback。
7. 完成 B1/R1/C1 schema 与 validator 的当前 exact-tree 验收。
8. 按 B2-B6、R2-R6、C2-C6 顺序补齐缺失证据。
9. 修复版本身份漂移，重建候选并重新做 exact-SHA 资格链。
10. 只有所有发布门禁和 TaskPack 项目均达到 `VERIFIED`，才重新评估正式 NSIS Release。

## 6. 云端一致性规则

- 本文的云端提交只代表“摘要与问题总表已上传”，不代表代码、安装器或公开 Release 已完成。
- 每次后续修复必须绑定 exact commit SHA、PR head SHA、CI run、merge SHA 和 main 回读。
- 远端文件回读内容必须与本地提交树一致；任何差异都标记为 `DRIFT`，停止发布结论。
- 本地 dirty WIP、`.hermes/task-runtime`、真实资料源和 Hermes 全局状态永远不进入云端同步。
- 历史 handoff 保留历史性质；当前 normative 文档只能写入已验证的现状。

## 7. 当前总判定

```text
后端最小闭环：PASS（有真实批量与重启证据）
内部 NSIS 生命周期：PASS
内部安装版已验证格式：PARTIAL
安装版全格式支持：UNVERIFIED / BLOCKED
WebView 点击级导入：UNVERIFIED
B/C/R TaskPack：未完成逐项验收
公开正式发布：NO-GO
```
