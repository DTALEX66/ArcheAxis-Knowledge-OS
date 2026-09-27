# DeepSeek Post-Audit Full Execution TaskPack v1

> TaskPack ID：`AXW-DEEPSEEK-POST-AUDIT-v1-2026-08-11`
>
> 目标仓库：`D:/All projects/Cognitive-Loop-OS`
>
> 当前候选 worktree：`.hermes/task-runtime/execution-reliability-standards`
>
> 执行上限：H0 重新资格、H1、H2、H3、H4、H5、Web Addendum、KLC Addendum。H6–H10 继续 `DEFERRED`。

## 1. 权威边界

本文件是审计后的可执行队列，不新增或改写冻结任务。发生冲突时依次服从：

1. 当前所有者最新指令；
2. `docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`；
3. Web/KLC 两个批准增补包；
4. `docs/truth/EXECUTION_STATUS_LOG.md` 最新追加记录；
5. `AGENTS.md`、`docs/VERIFICATION_POLICY.md`、`docs/CODEX_EXECUTION_RELIABILITY.md`；
6. 本任务包。

原 `DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md` 的任务选择算法、单任务状态机、RED→GREEN、开源复用、corpus、Windows 和证据协议继续有效。

禁止读取凭据、用户级 Codex/Hermes/OpenHuman 私有状态、`.env`、session、cookie、token 和 prompt/response body。禁止访问 `E:/` 和已排除的 `Obsidian-Assistance`。临时状态只能进入已忽略的 `.hermes/task-runtime/`。

## 2. 2026-08-11 起始事实

```text
origin/main                         ae59790f64541cb3d759d2f0955d33e0db7417b1
origin/axw/execution-h1             1c688c71eace449be2972acc538c0a8eb31dab89
main...H1                           main-only=1, H1-only=16
origin/codex/frozen-roadmap-*       978f11bcdaa9e9c6c75d0e95fb279660529cb86e
PR #73 squash merge SHA             ae59790f64541cb3d759d2f0955d33e0db7417b1
H1 exact-head CI record             run 31326205396, head 1c688c7, PASS
PDF local qualification             project root .venv, 3 passed
legacy ignored residue              BLOCKED_RUNTIME_CLEANUP
```

上述 ref 必须在每次 `git fetch` 后重新解析。不得把这个静态快照当实时 readback。

当前候选 worktree 含所有者要求的未提交治理修改。DeepSeek 必须把它视为用户 WIP：先读取 diff、确认没有第二 writer，再继续；不得 reset、restore、clean 或从旧功能分支覆盖。

## 3. 审计裁决

| 范围 | 状态 | 后续动作 |
| --- | --- | --- |
| 规划权威、Web/KLC 任务定义 | `PASS / PLANNED` | 保持只读，不冒充运行实现 |
| H0 功能恢复、PDF 安装态历史证据 | `PASS` | 保留历史 PASS |
| H0 冻结治理/供应链严格闭环 | `PARTIAL` | 重新资格既有 H0 任务并追加纠正 |
| H1 后端核心 | `PASS` on remote branch | 集成到最新 main 后重新验证 |
| AXW-022A 前端、AXW-022B、H1 EXIT | `PARTIAL/BLOCKED` | 当前实现主线 |
| H2–H5 | `UNASSESSED` | 按依赖执行 |
| Web/KLC 运行实现 | `UNASSESSED` | 规划发布不是实现证据 |
| H6–H10 | `DEFERRED` | 无所有者激活不得执行 |

H0 重新资格原因：`AXW-004A`、`AXW-006A`、`AXW-006B`、`AXW-007B` 缺少独立任务关闭记录；`AXW-010A` 缺少真实目标环境的 availability/quality/fidelity probe；LOG-019 同时写“AXW-006C PASS”和“payload SBOM 待正式 release”，不能作为严格供应链闭环。

## 4. 总执行规则

1. 每轮读取 `AGENTS.md`、三个 truth 入口、当前任务行、相关增补包、状态日志尾部和验证政策。
2. 从第一个“依赖全部 PASS 且自身非 PASS”的冻结 ID 开始；已有 `IN_PROGRESS` 优先续接。
3. 一个 checkout 一个 writer。并行 reviewer 只能只读；并行实现必须独立 worktree，由唯一集成 writer 吸收。
4. 每个行为执行 RED→GREEN→定向回归→该风险级门禁；文档任务至少运行链接检查、convention、`git diff --check`。
5. 使用开源候选时先固定 canonical URL、revision、license、Windows/CPU/offline 状态和 rollback；能力优先，品牌可替换，能力不能删除。
6. 状态日志只追加。发现旧 PASS 证据不足时追加 `CORRECTION`/`REQUALIFICATION`，不修改历史行。
7. commit、push、PR、merge、release、签名和发布均需所有者对该动作的明确授权。实现授权不自动等于发布授权。
8. 分别报告 `IMPLEMENTED_LOCAL`、`TESTED_LOCAL`、`BRANCH_PUBLISHED`、`CI_PASS_EXACT_SHA`、`MERGED` 和 `INSTALLED_RUNTIME_VERIFIED`。

## 5. Phase A — 治理补洞与 H0 重新资格

严格按以下顺序执行；不得直接再次写 `AXW-H0-EXIT PASS`：

| 顺序 | 冻结任务 | 必须补齐的交付 |
| --- | --- | --- |
| A1 | `AXW-004A` | 稳定 Evidence Index，连接 task/commit/test/CI/bundle/installer/live readback，不复制易过期日志 |
| A2 | `AXW-006A` | Upstream ledger 增加 canonical URL、revision、license、integration mode、owner、状态；registry 不得冒充 integrated |
| A3 | `AXW-007B` | Windows 启动、loopback/token、Job Object、关闭、残留进程、端口冲突的可复现诊断和失败证据 |
| A4 | `AXW-010A` | 在目标环境分别探测 availability、extraction quality、evidence fidelity；禁止只看 import/spec/静态 manifest |
| A5 | `AXW-006B` | 对真实 bundle 生成 SPDX/CycloneDX SBOM 和 RDR，绑定实际 payload、版本、来源 revision 和许可证 |
| A6 | `AXW-006C` | 用实际 payload 对齐 NOTICE；禁止不可追溯 binary/vendor 代码 |
| A7 | `AXW-004B`, `AXW-010B` | 重新投影当前版本与能力 truth；未验证能力明确 unavailable/degraded |
| A8 | `AXW-009C`, `AXW-009D` | 仅在依赖变化后重新做 exact-tree bundle 与 Windows 生命周期资格 |
| A9 | `AXW-H0-EXIT` | 同一 exact SHA 聚合 CI、bundle、安装态、生命周期、SBOM/NOTICE；否则保持 `PARTIAL/NO-GO` |

`AXW-003B/003C` 已有 main exact-SHA CI 记录，但任何 gate/schema 变化都必须重新资格。A1–A9 完成后在状态日志追加 H0 `REQUALIFICATION`，明确功能恢复与供应链治理两个维度。

## 6. Phase B — H1 集成与 PDF 证据闭环

### B1. 集成基线

- 从执行时最新 `origin/main` 创建新的 H1 integration worktree。
- 保留 `origin/axw/execution-h1@1c688c7` 的 16 个独有提交；merge/cherry-pick/rebase 方案先给出风险和回滚，历史重写必须单独授权。
- 集成后重新运行 13 个 H1 定向测试组、architecture、convention 和依赖影响分类；旧 CI 只证明旧 head。

### B2. `AXW-022A` PDF.js 阅读器

- 选用官方可追溯 PDF.js build，固定 revision/license，更新 upstream ledger、SBOM、NOTICE 和 package-data。
- 提供内容寻址只读 PDF API；不得暴露任意本地路径。
- 前端完成分页、缩放、搜索、重开、加载/失败/降级状态和 `prefers-reduced-motion`。
- browser smoke 与 Windows WebView 点击级验证必须真实加载 PDF，不只 mock 后端。

### B3. `AXW-022B` 阅读器证据与批注

- 文本和区域选择生成稳定 `EvidenceAnchor`；支持 Claim/Evidence 回跳。
- 源 revision 变化时明确迁移、失效、复核和 supersedes；不得静默漂移。
- 覆盖重启恢复、损坏 PDF、无文本层、搜索失败和撤销路径。

### B4. `AXW-H1-EXIT`

同一真实 PDF 在 Windows 安装态完成 RawAsset→Derived Block→可回跳 Evidence→人类学习记录→受控 AI candidate，重启后成立。随后才可请求 exact-head CI、merge 授权、merge-SHA CI 和 H1 EXIT 裁决。

## 7. Phase C — Web 与 KLC 基础层

Capability-first Addendum 对旧 Web 品牌任务具有较新解释权：必须交付 `static/dynamic/site` 能力 profile，但不得为了满足旧名称强绑未经 benchmark 的 provider。

### C1. 可在 H0/H1 后尽早执行

| 队列 | 任务 |
| --- | --- |
| Provider 治理 | `AXW-KLC-000`（确认既有冻结）→ `AXW-KLC-001` → `AXW-KLC-002` |
| Web 候选 | `AXW-WEB-000A`, `AXW-WEB-000B` 按 KLC provider-neutral 解释形成候选账本，不直接判入选 |
| Web 安全基线 | `AXW-WEB-001` → `AXW-WEB-003` |
| Web 对象 | `AXW-WEB-002` → `AXW-WEB-004`，复用 RawAsset/Job/Outbox/EvidenceAnchor |
| 搜索 | `AXW-KLC-004` → `AXW-KLC-005`；无 key 时可降级，不能伪造实时结果 |
| Source 基础 | H1 EXIT 后执行 `AXW-KLC-009`、`AXW-KLC-010` |

`AXW-KLC-003` 依赖 H4 的 `AXW-054A`，因此完整 blind benchmark、
`AXW-KLC-006`、`AXW-KLC-007`、`AXW-KLC-008`、`AXW-KLC-033`、
`AXW-KLC-034`、`AXW-KLC-035` 不得提前伪造 PASS。Web 可先完成
安全合同和候选适配，但最终 provider 资格等待 corpus。

## 8. Phase D — H2 多格式与 Web 全闭环

### D1. H2 Adapter

H1 EXIT 后可分别执行：

1. `AXW-023A` DOCX；
2. `AXW-023B` PPTX；
3. `AXW-023C` XLSX/CSV；
4. `AXW-023D` OCR；
5. `AXW-023E` HTML/Web；
6. `AXW-023F` 音视频转写。

每个格式独立建立真实 licensed corpus、人工 Oracle、LossReport、缺依赖降级、anchor、bundle、SBOM/NOTICE 和 Windows 安装态证据。一个格式 PASS 不得外推其他格式。

### D2. Web DAG

依赖安全顺序：

```text
AXW-WEB-003 + AXW-WEB-004
  -> AXW-WEB-005 static provider
  -> AXW-WEB-006 dynamic provider
  -> AXW-WEB-007 site provider
AXW-WEB-005 + AXW-WEB-006 + AXW-WEB-007 -> AXW-WEB-008 router
AXW-WEB-002 + AXW-WEB-008 + AXW-021B -> AXW-WEB-010 resumable crawl
AXW-WEB-008 + AXW-H1-EXIT -> AXW-WEB-009 MIME/signature routing
AXW-WEB-009 + AXW-WEB-010 -> AXW-WEB-011 API
AXW-WEB-011 + AXW-030A -> AXW-WEB-012 UI
AXW-WEB-009 + AXW-024B -> AXW-WEB-013 evidence
AXW-WEB-003 -> AXW-WEB-014 corpus
AXW-WEB-006 + AXW-WEB-007 + AXW-WEB-014 -> AXW-WEB-015 Windows/supply chain
AXW-WEB-012 + AXW-WEB-013 + AXW-WEB-015 -> AXW-WEB-016 installed E2E
AXW-WEB-016 -> AXW-WEB-EXIT
```

安全验收必须覆盖 SSRF、每次 redirect 重验、loopback/private/link-local、robots/ToS 可见性、page/depth/bytes/time/concurrency、prompt injection、429/5xx、取消、恢复和浏览器进程回收。

### D3. H2 EXIT

`AXW-H2-EXIT` 必须同时满足 6 个格式任务和 `AXW-WEB-EXIT`。每个格式需要独立 exact-SHA/安装态证据，bundle/SBOM/NOTICE 与真实 payload 一致。

## 9. Phase E — H3 Obsidian / Markdown / JSON Canvas C4

```text
AXW-040
  -> AXW-041
     -> AXW-042 -> AXW-044A -> AXW-044B
     -> AXW-043A --------------------+
AXW-043A + AXW-044B -> AXW-043B -> AXW-045 -> AXW-H3-EXIT
```

- 只读取用户批准 Vault root；外部 `Obsidian-Assistance` 永久排除。
- C0–C4 分别验证发现、Markdown/YAML/link、只读 Workbench、revision-safe write、冲突/回滚、JSON Canvas round-trip 和 Windows 安装态 Obsidian 重开。
- 写入必须 expected revision + 临时文件/原子替换 + 备份 + 审计；未知 Canvas 字段不得丢失。

## 10. Phase F — H4 与 KLC 全生命周期

### F1. H4 前置链

```text
AXW-024C -> AXW-024D -> AXW-050A -> AXW-050B
AXW-051A -> AXW-051B
AXW-024D + GOV-001 -> AXW-052A -> AXW-052B
AXW-050B + AXW-051B + AXW-052B -> AXW-053
AXW-024D -> AXW-054A
AXW-050B + AXW-051B + AXW-053 + AXW-054A -> AXW-054B
```

### F2. KLC 转换、课程、学习、检索与 AI

按依赖分组执行：

1. Benchmark：`AXW-KLC-003` → `AXW-KLC-006`, `AXW-KLC-007`,
   `AXW-KLC-033` → `AXW-KLC-008`。
2. 转换：`AXW-KLC-011`；结合 H2 执行
   `AXW-KLC-012`、`AXW-KLC-013`、`AXW-KLC-014`、`AXW-KLC-015` →
   `AXW-KLC-016` → `AXW-KLC-017` →
   `AXW-KLC-018`。
3. 知识/课程：`AXW-KLC-019` → `AXW-KLC-020` →
   `AXW-KLC-021`、`AXW-KLC-022` → `AXW-KLC-023` → `AXW-KLC-024`。
4. 人类学习：`AXW-KLC-025` → `AXW-KLC-026`、`AXW-KLC-027` →
   `AXW-KLC-028`。
5. 检索/AI：`AXW-KLC-029` → `AXW-KLC-030` → `AXW-KLC-031` →
   `AXW-KLC-032`。
6. 差分/门禁：`AXW-KLC-034` → `AXW-KLC-035`。
7. 产品集成：`AXW-KLC-036` → `AXW-KLC-037`；`AXW-KLC-038` 在
   H2 EXIT 后做 Windows/供应链资格。
8. 安装态：`AXW-KLC-035 + AXW-KLC-037 + AXW-KLC-038 + AXW-WEB-EXIT + AXW-H2-EXIT`
   → `AXW-KLC-039` → `AXW-KLC-EXIT`。

不得遗漏 `AXW-KLC-009`、`AXW-KLC-010` 的非网页来源和 SourceEnvelope。全部格式最终
落到共享 block/region/time/cell/symbol anchor，转换 engine、fallback、loss、
rights 和 source revision 可回放。

### F3. H4 EXIT

`AXW-055` 除冻结依赖 `AXW-H2-EXIT + AXW-H3-EXIT + AXW-054B` 外，
还必须满足 `AXW-WEB-EXIT + AXW-KLC-EXIT`。完成单主题真实安装态闭环后
才能裁决 `AXW-H4-EXIT`。

## 11. Phase G — H5 稳定 v1.0

```text
AXW-H4-EXIT -> AXW-094A -> AXW-094B -> AXW-095
AXW-H4-EXIT -> AXW-096A
AXW-H4-EXIT -> AXW-096B
AXW-021B + AXW-096A -> AXW-096C
AXW-095 + AXW-096C -> AXW-097
AXW-006C + AXW-095 + AXW-096B + AXW-097
  + AXW-WEB-EXIT + AXW-KLC-EXIT -> AXW-060 -> AXW-H5-EXIT
```

H5 需验证开放导出、备份恢复、升级/降级、CPU-only 大库性能、无障碍、长任务恢复、隐私诊断包、exact-SHA Windows bundle/installer、SBOM/NOTICE 和现场 readback。`AXW-H5-EXIT` 只表示“可发布候选”；实际 release、签名和公开发布仍需所有者单独授权。

## 12. H6–H10 停止线

`AXW-070` 至 `AXW-180` 及 H6–H10 EXIT 全部保持 `DEFERRED`。没有所有者明确激活、独立 TaskPack 和风险审查时，DeepSeek 必须在 H5 EXIT 后停止，不得顺手实现 Agent Runtime、多智能体、Marketplace、3D/VR、企业多租户或通用执行沙箱。

## 13. 每轮输出与停止条件

每轮必须输出：

```text
TASK_ID:
BASE_SHA / CANDIDATE_TREE:
DEPENDENCIES:
IMPLEMENTATION:
TARGETED_TESTS:
FULL_GATE:
RUNTIME_RESIDUE:
COMMIT:
PUSH:
CI_EXACT_SHA:
MERGE:
INSTALLED_RUNTIME:
STATUS: PASS/PARTIAL/FAIL/BLOCKED/NOT_EXECUTED
NEXT_ELIGIBLE_TASK:
ROLLBACK:
```

仅在以下情况停止：

- H5 EXIT 完成且 H6–H10 未激活；
- 需要所有者授权的 commit/push/merge/release 等外部副作用；
- 凭据、许可证、权利、真实 corpus、Windows 安装态或外部服务构成真实阻塞；
- 同一阻塞按项目规则达到可报告的 blocked 条件。

不得因为上下文长度、单轮时间、测试较慢或某一候选失败而宣称全量任务完成。使用状态日志和 checkpoint 续接。
