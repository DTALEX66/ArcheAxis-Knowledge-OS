# AXR Current Reality Matrix — R2 install baseline

- TaskPack：`AXR-FINAL-20260826-R2-OSS-FAST-TRACK`
- Captured：2026-08-27（中国标准时间）
- Qualification baseline：`229e99580c6e5440fede682cb3e4a74b0987d9ab`；该树与 `origin/main` 对齐并完成全部产品/发布门；本状态真值更新后的 live HEAD 必须从 Git 读取并重新资格验证
- Canonical branch：`main`
- 产品源码版本：`0.6.11 candidate`
- 最新公开 Release：`v0.6.10`（2026-08-23，非当前 candidate）

## 分层事实

| 证据层 | 状态 | 当前证据 | 不能推出 |
|---|---|---|---|
| Structural | PASS | R2 已进入 `docs/taskpacks/` 并成为唯一 current forward pack；对象/任务/禁止项已落盘 | 不等于 DeepTutor 已安装或黄金流程已迁移 |
| Local runtime | PASS（R2 candidate） | Python `2070 passed / 7 skipped`；前端 Vitest/Vite build PASS；双 Tauri `cargo check --all-targets` PASS；A0 Chromium browser smoke PASS；DeepTutor `qwen3:8b` 教学→答题反馈→无效答案恢复→reload PASS，console errors=0 | 不等于公开 Release 已创建 |
| exact-SHA CI | PASS（qualification baseline `229e995`） | GitHub Actions CI run `32998319094`：15 个 required jobs 全 success，含 desktop-build、installer-lifecycle、browser-smoke、a0-gates | 状态真值更新提交仍需新 exact-SHA CI；不等于 tag/公开资产已发布 |
| Installed Windows | PASS（CI candidate） | exact-SHA Setup 候选经 Windows NSIS install→launch→upgrade→forced-exit→uninstall→reinstall 生命周期验证；下载候选逐文件 hash PASS | 仍不是公开下载回读 |
| Public release | RELEASED v0.6.10 / NOT RELEASED v0.6.11 | GitHub Latest=`v0.6.10`；v0.6.11 仍 candidate | 不得声称 R2/DeepTutor 已发布 |

## R2 基线差异

Owner 任务包审计基线为 `bf0c4839`。当前 candidate `229e995` 已在该基线上完成 R2 Safety/Truth/Product/Projection 实现、Linux Chromium 短路径修复和 release-gate 修复；差异不能由旧审计快照推导，必须以当前 exact-SHA 测试、CI 与运行读回为准。

## Safety 波次重新核验

| 任务 | 2026-08-27 开工状态 | 已确认事实 |
|---|---|---|
| AXR-000 | DONE（结构层） | current pack/index/reality matrix 落盘；远端、Release、CI 已回读 |
| AXR-010 | PASS | PDF.js 升至 6.2.108 ESM，禁 eval/文档脚本；SBOM 覆盖 uv、canonical/recovery npm+cargo、PDF.js 和 Magika；Recovery 壳改独立 identifier 且禁止打包 |
| AXR-020 | PASS | 已修最高已达到 K、无源=`NONE`、默认 unverified、`/tick` 拒绝客户端自报三轴、sqlite Row 字典化、人类掌握只产 unverified DistillationCandidate；新增 `axr_learning_truth_v2` 增量 migration，旧机器值标 `UNMIGRATED`，机器 K 只从 verified EvidenceBundle 的连续 receipt 推导；LearningEvent 已可 append/replay |
| AXR-030 | PASS | `axr_source_truth_v2` 增量 migration 已新增 Source/Anchor/PROV/archive receipt；Source version 追加式、rights/fixity 可回读，新版本自动使旧 Anchor `STALE`；OCFL 1.1 export/fixity/tamper 校验通过 |
| AXR-040 | PASS | DeepTutor v1.5.17（commit `bd80a4d…`，archive SHA-256 `95f651…`）源码/venv 已安装在共用外置依赖库，运行数据固定在项目 `.hermes/task-runtime/deeptutor-home`；本地 Ollama `qwen3:8b` 配置后 online doctor 的 llm_config/credentials/endpoint/storage/online required checks 全 PASS；真实 Chromium 教学→答题反馈→无效答案恢复→reload PASS，console errors=0；canonical bridge 保持投影可删/可重建 |
| AXR-050 | PASS | docx/pptx/xlsx/OCR/HTML/media 等结构化 adapter 与主链 real fixture 29 passed；缺依赖和空内容继续 fail-closed |
| AXR-060 | PASS | append-only LearningEvent、replay、FSRS due queue/BKT evidence 13 passed；人类学习事件不直接写机器 K |
| AXR-070 | PASS | migration 18 增加 append-only review 与 machine candidate；无 verified EvidenceBundle 审核无法批准，批准仍只生成 `CANDIDATE`，可 revoke 回滚；5 passed |
| AXR-080 | PASS | `qwen3:8b` 真实生成教学内容和选择题；答题反馈、无效答案 `Z` 的显式失败恢复建议、三轮会话重载读回均通过，浏览器 console 0 error |
| AXR-100 | PASS | Job Center/outbox/import job/ASR/取消恢复相关 36 passed；本机未安装模型的 ASR 路径按合同显式 fail/skip |
| AXR-110 | PASS（retention-safe） | 结构化供应链与 SBOM 7 passed；DeepTutor/PDF.js 已锁 commit/hash/license；旧 `pdf.min.js`/worker 与 3.11.174 引用为零；Recovery 壳已独立 identifier 且不打包；三份旧 TaskPack 保留为历史证据并改指 R2/NAMING V2。其余历史资产无两项独立冗余证据，按保留优先原则不删除 |
| AXR-120 | PASS | ArcheAxis federation/record/router security 22 passed；没有进入或修改 DESIGN-LAB 仓库，外部系统不能写核心真值 |
| AXR-130 | PASS | exact-SHA CI `32998319094` 全 15 jobs success；Setup 候选下载后 manifest/lock/payload hash PASS；Green/Portable 由同一 runtime/identity 本地组装并完成结构、candidate identity、SHA-256 读回 |

## 当前硬门

1. 本状态真值更新形成新 commit 后，必须取得该新 exact-SHA 的完整 CI 与 release candidate；
2. 任何外部产品数据只能是可删除投影；核心真值与项目运行数据留在本项目边界；
3. `v0.6.11` tag 必须绑定新的状态真值 commit，Release workflow 成功后再做公开 9 资产下载/hash/identity 回读；
4. GitHub Latest、README、PROJECT_STATUS、RELEASE_LEDGER 和公开 Release identity 必须一致后才能宣称发布完成。
