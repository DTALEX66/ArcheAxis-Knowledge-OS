# R5 连续执行收据：Task 0 基线与候选修复裁决（2026-09-15）

## 基线

- 项目：ArcheAxis-Knowledge-OS
- 分支：`codex/full-loop-0906`
- HEAD：`0dd8ff37b670ae98fac4be35720194434e82191e`
- 远端基线：`0dd8ff37b670ae98fac4be35720194434e82191e`
- 工作树既有未跟踪路径：`docs/current/SESSION-RESTART-2026-09-12.md`、`docs/history/` 迁移资产；本任务不纳入。
- 候选补丁：`ArcheAxis-first-use-fixes.patch`
- 候选补丁 SHA-256：`f20a8616de14b6a08f2d25b009c460ed734d4d771b83c20335d1365b2cd111d7`
- `git apply --check`：PASS（未修改当前树）。
- 执行预检：PASS；使用项目缓存解释器 3.13.14，542 个 Markdown 链接无断链，2 个夹具预期缺失。

## 逐文件裁决

| 文件 | 裁决 | 理由 |
| --- | --- | --- |
| `.github/workflows/ci.yml` | ADOPT | 补全历史 checkout；与 R5 CI 止错一致，需远端同 SHA 验证 |
| `AGENTS.md` | ADOPT | 修正当前入口与首次闭环边界；保留安全边界 |
| `Cargo.toml` | ADOPT | 明确 legacy Tauri 排除，保持 Avalonia/Rust 正式链 |
| `LESSONS_LEARNED.md` | ADOPT | 记录可复现的首次使用失败边界 |
| `docs/current/R5-DESKTOP-START.md` | ADOPT | 补充稳定 TEST 启动说明 |
| `docs/current/R5-EXECUTION.md` | ADOPT | 追加本轮证据索引；不替代冻结任务包 |
| `docs/current/R5-FIRST-USE-REPAIR-20260915.md` | ADOPT | 新增修复说明与限制 |
| `docs/current/R5-STATE.json` | ADOPT-WITH-REVIEW | 仅接受与实际测试一致的状态变更，逐项复核后保留 |
| `scripts/launch/desktop_launch.py` | ADOPT | 稳定 TEST workspace 与显式 fresh 隔离 |
| `scripts/maintenance/bulk_fixture_factory.py` | ADOPT | 根内绝对路径和完整输出路径安全校验 |
| `scripts/probes/r10_host_panel_smoke.py` | ADOPT | 移除空库自动学习假成功 |
| `shared/core_client.py` | ADOPT | 空结果不再写入学习/引用或自动答对 |
| `tests/maintenance/test_bulk_fixture_factory.py` | ADOPT | 覆盖越界与目录链接回归 |
| `tests/test_core_client.py` | ADOPT | 覆盖 adapter probe 与闭环标记 |
| `tests/test_desktop_launch.py` | ADOPT | 覆盖稳定 workspace / fresh workspace |

## 执行边界

本收据先记录裁决和基线；后续应用补丁必须逐文件检查 diff，运行 Task 1–3 的定向测试。若测试显示候选与当前正式架构冲突，使用单文件回退或 `git revert`，不覆盖用户数据、不删除 TEST 库。

包内 68c81a39 的测试只对其原环境和 SHA 有效；本次会重新绑定当前提交和实际命令。远端 CI、Windows GUI、Green、真实资料和 Q00/Q01 仍未通过。

## Task 1–2 本地复核

- `tests/test_core_client.py`、`tests/test_desktop_launch.py`、`tests/maintenance/test_bulk_fixture_factory.py`：26 passed、2 skipped。
- CI/发布/预检相关测试：104 passed。
- Core/桌面运行时/fixture 组合：50 passed、2 skipped。
- `scripts/check_repository_conventions.py --source worktree`：PASS。
- `scripts/check_path_conventions.py`：2019/2019 tracked paths owned，0 unowned，0 ambiguous。
- 本机未发现 `cargo`、`dotnet`、`rustc`；Rust/C# 构建和 Windows GUI 验证为 NOT RUN，需 Windows/CI runner。
- 当前实现提交：`19f9ac1a28917fd670ada214ca6260013f2ecf98`；远端同名分支已回读同 SHA。

## Task 8 模型外置接线

- `shared/file_detection.py` 现优先读取 `ARCHEAXIS_MAGIKA_MODEL_DIR` 中同时存在的 `model.onnx` 与 `config.min.json`；外置目录不可用时回退仓库副本，保留离线能力。
- `config/environment/capability-requirements.yaml` 与 `docs/environment/EXTERNAL_DEPENDENCIES.md` 已同步声明该优先级。
- `tests/test_file_detection.py`、`tests/test_capabilities.py`、`tests/test_mfx010_honest_capability.py` 与环境注册测试：21 passed（1 个既有警告）。
- 本次未读取或修改 `D:\\All projects\\Model library`；外置消费者和实际 Windows profile 仍需在 Task 7/8 的 Windows 验收中核实，故未删除仓库副本。
