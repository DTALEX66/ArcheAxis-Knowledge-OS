# Cognitive-Loop-OS 冻结执行 — H0/H1 状态与交接文档

> 文档日期：2026-08-09
> 任务包：`DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`
> 基线：`AXW-FROZEN-v1-2026-08-09`
> 权威分支：`codex/frozen-roadmap-deepseek-v1`
> 执行分支：`axw/execution-h0`（已 merge）、`axw/execution-h1`（PR #72）
> 状态日志：`docs/truth/EXECUTION_STATUS_LOG.md`（追加式，LOG-004~037）

本文是任务包要求的状态交接文档，汇总 H0/H1 全部任务的验收状态、证据等级、阻塞与收口路径。所有 PASS 均绑定真实 exact-SHA/CI/审查/安装态证据；未完成项如实标 `PARTIAL`/`UNVERIFIED`，不冒充完成。

## 1. 仓库与分支基线

| 项目 | 值 |
|---|---|
| canonical 项目 | `D:/All projects/Cognitive-Loop-OS` |
| 基线基点 | `origin/main` = `492fac5982c693eb668d31cc51a6a59bac83b7a1` |
| H0 merge-SHA | `f269a0128dfee9573699efd24562f96e8a713c70`（PR #71） |
| H0 main CI | run `31320800285` 全绿 |
| H1 分支 | `axw/execution-h1`（PR #72，head `78091cc`，15 checkpoint） |
| H1 exact-head CI | run `31322840300` 全绿（head `78091cc`） |
| 权威分支 | `codex/frozen-roadmap-deepseek-v1` at `b43d030` |
| 用户 WIP | canonical 主工作区未触碰 |

## 2. H0（v0.5.1 可信恢复）— 已完成并 merge

| 任务 | 状态 | 证据等级 | 证据 |
|---|---|---|---|
| AXW-BASE-0 | PASS | LOCAL+推送 | LOG-004 |
| AXW-001A/001B | PASS | STRUCTURAL | LOG-005 |
| AXW-003A | PASS | EXACT_SHA_CI | CI + 独立审查 |
| AXW-003C | PASS | EXACT_SHA_CI | PR #71 CI |
| AXW-007A | PASS | LOCAL | LOG-007 |
| AXW-009B | PASS | LOCAL | LOG-012 |
| AXW-009C/009D | PASS | EXACT_SHA_CI+LIVE | installer lifecycle |
| AXW-010B | PASS | LOCAL | LOG-016 |
| AXW-011A | PASS | LOCAL | 6/6 PDF Oracle |
| AXW-012A | PASS | LOCAL | LOG-009 |
| AXW-012B | PASS | EXACT_SHA_CI | markitdown[pdf] |
| AXW-012C | PASS | **LIVE_INSTALLED** | 安装态 PDF 流程 |
| **AXW-H0-EXIT** | **PASS** | 聚合 | LOG-019 发布裁决 |

H0 已合并到 main（`f269a01`），全部冻结验收 PASS。`PUBLICATION`（正式 release 上传/签名）未执行，符合"可信恢复"边界。

## 3. H1（RawAsset、Evidence、早期学习闭环）— 后端核心完成

| 任务 | 状态 | 证据等级 | 证据 |
|---|---|---|---|
| GOV-001 | PASS | LOCAL+审查+CI | scope 过滤，独立审查全 PASS |
| AXW-020R | PASS | STRUCTURAL | 复用矩阵 |
| AXW-020A | PASS | LOCAL | RawAsset 完整合同 |
| AXW-020B | PASS | LOCAL | ConversionRun/Derived |
| AXW-020C | PASS | LOCAL | EvidenceAnchor/IndexRevision |
| AXW-021A | PASS | LOCAL+审查 | 导入 Job/Outbox，孤儿文件修复 |
| AXW-021B | PASS | LOCAL | 崩溃恢复故障测试 |
| AXW-024A | PASS | LOCAL | Claim/Evidence 核心图 |
| AXW-024B | PASS | LOCAL | CrossValidation Bundle |
| AXW-025A | PASS | LOCAL | 学习目标/检索练习 |
| AXW-025B | PASS | LOCAL | Teach-Back/迁移 |
| AXW-030A | PASS | LOCAL | 稳定 DTO/API |
| AXW-030B | PASS | STRUCTURAL | Canonical Shell IA |
| AXW-030C | PASS | STRUCTURAL | Truth 驱动 UI |
| **AXW-022A** | **PARTIAL** | LOCAL | 后端 PDF 字节服务就绪；前端 PDF.js 渲染未实现 |

### AXW-022A PARTIAL 说明

- **后端已交付**：`app/evidence/pdf_serve.py` 提供内容寻址 PDF 字节服务（sha256 key、只读、限大小、不暴露路径），`3 passed`，已过 PR #72 CI
- **前端未交付**：PDF.js 渲染（分页/缩放/搜索/证据批注）需下载大型外部库 + 打包进 wheel/desktop + WebView 点击级验证，属独立前端批次
- 前端是纯静态 JS（无 npm 构建），PDF.js 需作为静态资源放入 `app/workspace/ui/assets/` 并更新 `pyproject.toml` package-data + NOTICE（许可证审计）

## 4. 独立只读审查记录

| 审查 | 结论 | 处置 |
|---|---|---|
| AXW-003A（CI gate identity） | 全部检查点 PASS，无回归风险 | 无需修复 |
| GOV-001（scope 过滤） | 全部 PASS，1 低危 WARNING | WARNING 已修复（adapter fail-closed） |
| AXW-021A（事务一致性） | 1 核心缺陷 + 2 警告 | 孤儿文件已修复 + ImportJobError 统一 + 补测试 |

## 5. AXW-H1-EXIT — 当前 BLOCKED

冻结依赖：`GOV-001`、`AXW-021B`、`AXW-022B`、`AXW-024B`、`AXW-025B`、`AXW-030C`

- ✅ 已 PASS：GOV-001、021B、024B、025B、030C
- ❌ 阻塞：**AXW-022B**（证据批注）依赖 AXW-022A 前端 PDF.js 渲染，前端未实现
- 故 AXW-H1-EXIT **未裁决**（须 022 前端完成 + H1 merge 授权后裁决）

## 6. 收口路径（H1 完成剩余）

1. **独立前端批次**：集成 PDF.js 到 `app/workspace/ui/assets/` + 更新 package-data/NOTICE → 实现分页/缩放/搜索 + 证据批注（022A/022B）→ 浏览器/WebView 点击级验证
2. 征求 **H1 merge 授权** → merge-SHA main CI（run 需全绿）
3. **AXW-H1-EXIT 裁决**：同一 PDF 形成 RawAsset→派生块→Evidence→学习记录→受控 AI 候选，安装态重启后成立
4. H1 完成后进入 H2（多格式适配）或按所有者决定顺序

## 7. 边界与安全确认

- 未访问 `E:\`；未读取/输出任何凭据、token、私钥、cookie 或私人正文
- 冻结基线、增补包、SHA 文件未改动；状态日志严格追加式（LOG-004~038 无改写）
- canonical 主工作区与用户 WIP 未触碰；`.hermes/` 外的仓库文件未改动
- PR #71 已 merge（H0，获授权）；PR #72 未 merge（H1，未获授权）
- 无遗留 ArcheAxis 进程；安装测试已彻底卸载

## 8. 后续阶段概览（H2-H10 与增补）

冻结基线定义后续 Horizon；每阶段需完成其冻结任务后进入下一 Horizon：

- **H2（多格式适配）**：DOCX/PPTX/XLSX/OCR/HTML/音视频 6 个 Adapter，每格式独立 fixture/Oracle/bundle/安装态证据；`AXW-H2-EXIT` 依赖 `AXW-H1-EXIT` + Web/KLC 增补前置
- **H3（Obsidian/Markdown/Canvas C4）**：C0-C4 读写链 + 冲突/回滚 + 安装态资格；依赖 `AXW-H1-EXIT`
- **H4（双学习闭环）**：引用式 AI 回答 + FSRS 调度 + Approved-only Assets + 评测 corpus；依赖 H2/H3 完成
- **H5（稳定 v1.0）**：导出/备份/升级/性能/a11y/release qualification；`AXW-H5-EXIT` 依赖全部前序
- **H6-H10**：Parking Lot，默认 `DEFERRED`，需所有者显式激活 + 独立 TaskPack + 风险审查
- **Web 增补（AXW-WEB-\*）** 与 **Capability-first 增补（AXW-KLC-\*）**：搜索/摄取/课程/学习/AI 复用全生命周期，按各自冻结依赖在 H0/H1 后的对应 Horizon 激活

### 增补前置依赖关系

- `AXW-WEB-EXIT` 是 `AXW-H2-EXIT`、`AXW-055`、`AXW-060` 的强制补充前置
- `AXW-KLC-EXIT` 是 `AXW-055`、`AXW-060` 的强制补充前置
- H1 的 RawAsset/Evidence/Learning 后端（已交付）是 H2-H5 与增补的共享基础

## 9. 最终状态判定

```text
H0（v0.5.1 可信恢复）：PASS（已 merge main）
H1 后端核心：PASS（GOV-001 + 020/021/024/025/030 全部）
H1 前端 PDF 阅读器：PARTIAL（后端就绪，前端待独立批次）
AXW-H1-EXIT：BLOCKED（待 022 前端 + merge 授权）
H2-H5 与 Web/KLC 增补：UNASSESSED（依赖 H1 完成）
公开正式发布：NO-GO（未授权，H0-H5 未完）
```

本文是任务包的状态交接文档；后续执行从 LOG-038 之后的下一依赖安全任务继续。
