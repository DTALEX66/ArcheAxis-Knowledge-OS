# Desktop close lifecycle handoff — 2026-08-06

## 当前结论

本次 Windows NSIS 生命周期问题已完成根因修复并提交到 PR #38，但合并后的 main CI 尚未完成最终回读。按 fail-closed 规则，本次不宣称 main Green、不创建 Release。

- PR: https://github.com/DTALEX66/Cognitive-Loop-OS/pull/38
- 修复 commit: `9ffd72a888eda804093a7f933878fc3eade1cb4c`
- PR exact-head CI: `31057717871`
- PR exact-head head SHA: `9ffd72a888eda804093a7f933878fc3eade1cb4c`
- PR exact-head 结果：9/9 Green，包含 `desktop-shell` 和 `a0-gates`
- PR merge SHA: `f06c840d0abac3ae9e46bc1bf8f745cf474f3da2`
- 合并后 main CI: `31058511430`
- main CI 截止本交接：其他 job 已 Green，`desktop-shell` 仍在 NSIS 生命周期验证；watch 等待超时，不等同于失败，也未取得最终结论。

## 原始错误

此前 main CI `31027699926` 的失败日志为：

```text
desktop/scripts/verify_nsis_install.ps1:132
desktop shell did not exit after WM_CLOSE
pid=3776 handle=393688 main_window=393688
```

随后 `a0-gates` 因 `DESKTOP_RESULT=failure` 失败。失败发生在已安装 ArcheAxis OS NSIS 包的正常关闭路径；构建、安装器名称、Python runtime smoke、浏览器 smoke 和三版本 Python 测试均通过。

同一失败曾在此前 main/PR run 复现，说明不能只当作一次 watcher 超时处理。

## 根因判断

旧关闭链在 `WindowEvent::CloseRequested` 中：

1. 再次调用 `window.close()`；
2. 启动线程等待 500ms；
3. 再调用 `app_handle.exit(0)`。

这会在 Windows 原生 `WM_CLOSE` 已经进入处理回调时重新进入 close 语义，并把 native window close 与 Tauri event-loop exit 交给延迟线程，导致 NSIS 门禁等待 15 秒后仍观察到 shell alive。

## 修复内容

`desktop/src-tauri/src/lib.rs` 的 `CloseRequested` 现在：

1. 使用 `window.destroy()` 销毁已经收到 `WM_CLOSE` 的 native window，避免重新触发 `CloseRequested`；
2. 立即调用 `window.app_handle().exit(0)`；
3. 保留现有 `RunEvent::ExitRequested` → `BackendProcess::shutdown()`，由唯一的 backend 生命周期钩子回收 Python 子进程。

新增 `tests/test_ci_a0_gates.py::test_desktop_close_request_destroys_native_window_before_exit`，锁定以下契约：

- 必须存在 `WindowEvent::CloseRequested`；
- 必须调用 `window.destroy()`；
- 必须调用 `window.app_handle().exit(0)`；
- 不得在该 handler 中再次调用 `window.close()`；
- 不得使用延迟 sleep 线程完成退出。

## 已完成验证

本地：

```text
cargo fmt --all -- --check       passed
cargo test --lib                 13 passed
pytest tests/test_ci_a0_gates.py tests/test_desktop_staging.py  16 passed
git diff --check                 passed
```

远端 PR exact-head：

```text
31057717871 — 9/9 Green
```

## 未完成与恢复动作

当前唯一未闭环项是合并后 main CI `31058511430` 的最终状态。恢复时只做以下动作：

1. 回读 `gh run list --branch main`，确认 run `31058511430` 的 `status/conclusion/headSha`；
2. 若 `success` 且 head 为 `f06c840d0abac3ae9e46bc1bf8f745cf474f3da2`，记录 main 9/9 Green；
3. 若失败，只读取 `gh run view 31058511430 --log-failed`，不得先猜测或重复改源码；
4. 在 main exact-SHA Green 前，不创建 tag、不创建 public Release；
5. 保持 `app/release-manifest.json` 为 `development/private`。

## 边界与安全

- 未访问 `E:\`。
- 未修改 Hermes 全局配置、Gateway、认证、cron、sessions 或 memories。
- 未清理、覆盖或合并用户 WIP。
- 本交接只描述仓库代码、CI 和恢复动作；不包含任何凭据、token 或私密路径。
