# AXR Current Reality Matrix — R2 install baseline

- TaskPack：`AXR-FINAL-20260826-R2-OSS-FAST-TRACK`
- Captured：2026-08-27（中国标准时间）
- Baseline HEAD：`e8571b9d`；`origin/main` 同 SHA；工作树在本任务执行中
- Canonical branch：`main`
- 产品源码版本：`0.6.11 candidate`
- 最新公开 Release：`v0.6.10`（2026-08-23，非当前 candidate）

## 分层事实

| 证据层 | 状态 | 当前证据 | 不能推出 |
|---|---|---|---|
| Structural | PASS | R2 已进入 `docs/taskpacks/` 并成为唯一 current forward pack；对象/任务/禁止项已落盘 | 不等于 DeepTutor 已安装或黄金流程已迁移 |
| Local runtime | PASS（R2 Safety candidate） | Python `2053 passed / 7 skipped`；前端 Vitest `65 passed` + Vite build；双 Tauri `cargo check --all-targets`；A0 Chromium browser smoke PASS，PDF.js runtime=`6.2.108`、console errors=`[]` | 尚未证明 DeepTutor 全黄金流程或新 exact-SHA CI |
| exact-SHA CI | PASS（`e8571b9`） | GitHub Actions CI run `32986477421` success | 新工作树尚无 exact-SHA CI |
| Installed Windows | PARTIAL | v0.6.10 历史安装/恢复证据已公开；0.6.11/R2/DeepTutor 尚未完成干净安装读回 | 不能把历史安装证明迁移给新树 |
| Public release | RELEASED v0.6.10 / NOT RELEASED v0.6.11 | GitHub Latest=`v0.6.10`；v0.6.11 仍 candidate | 不得声称 R2/DeepTutor 已发布 |

## R2 基线差异

Owner 任务包审计基线为 `bf0c4839`。当前 `e8571b9` 比基线多 1 个提交：Linux GitHub runner 下 Chromium singleton Unix-socket 路径过长修复；本地 Web E2E 3 passed，exact-SHA CI success。该提交不改变 R2 产品裁决。

## Safety 波次重新核验

| 任务 | 2026-08-27 开工状态 | 已确认事实 |
|---|---|---|
| AXR-000 | DONE（结构层） | current pack/index/reality matrix 落盘；远端、Release、CI 已回读 |
| AXR-010 | LOCAL PASS / CI PENDING | PDF.js 升至 6.2.108 ESM，禁 eval/文档脚本；SBOM 覆盖 uv、canonical/recovery npm+cargo、PDF.js 和 Magika；Recovery 壳改独立 identifier 且禁止打包 |
| AXR-020 | PARTIAL | 已修最高已达到 K、无源=`NONE`、默认 unverified、`/tick` 拒绝客户端自报三轴、sqlite Row 字典化、人类掌握只产 unverified DistillationCandidate；MachineCompetence V2 数据迁移/receipt 仍待增量 migration |

## 当前硬门

1. 新改动必须跑完整 Python/DB/security/frontend/浏览器/Tauri 组合门并取得新 exact-SHA CI；
2. DeepTutor 当前 stable 必须先锁 immutable tag/commit/hash/SPDX，再进入本机独立 workspace；
3. 任何外部产品数据只能是可删除投影；核心真值与项目运行数据留在本项目边界；
4. `v0.6.11` tag/Release 只有在 AXR-130 证据门满足后才允许创建。
