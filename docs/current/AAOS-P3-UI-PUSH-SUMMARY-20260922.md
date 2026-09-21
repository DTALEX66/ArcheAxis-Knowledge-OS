# AAOS P3 UI 推送摘要

日期：2026-09-22

## 本次范围

本分支提交的是 ArcheAxis Knowledge OS 的 Avalonia canonical desktop shell P3 UI 收敛，不包含 Green 覆盖、外置资料库、发布、安装、签名或 Core 数据库改造。

主要内容：

- 吸收 `D:\All projects\UI套件` 中已审计的 AAOS UI token、信息架构和交互模式。
- 完成 Home、Library、Source Reader、Knowledge V3、Learning、Jobs、Settings、Recovery 的前端投影收敛。
- 增加窄屏 Inspector overlay drawer、Command Palette 结果筛选与键盘选择、当前会话 Activity Dock / Job Receipt 选择。
- 统一 loading、empty、error、permission、unknown 状态语义，避免 UNKNOWN 被显示为成功或零值。
- 保持 Rust Core 为 canonical truth；UI 不新增第二套数据库、学习真相、任务真相或模型真相。

## 验证摘要

- `NAVIGATION_CONTRACT_PASS=118`
- `ROUTES_CONTRACT_PASS=6`
- `LEARNING_REVIEW_CONTRACT_PASS=16`
- Avalonia Debug build：0 warnings / 0 errors
- `git diff --check`：仅存在 `docs/current/R6-EXECUTION.md` 的既存 CRLF normalization warning

## 证据边界

当前证据等级为 `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC / TESTED_LOCAL_BUILD`。

Native GUI 五档窗口截图、DPI 行为、真实 Core HTTP 响应、点击/键盘读回、安装运行和 restart readback 仍为 `UNVERIFIED`；本地 `sky` trusted RPC 未配置。

## 提交边界

本分支只包含本轮 AAOS P3 UI 的 task-owned 文件。以下保留在工作树，不纳入本次提交：

- `docs/history/**`
- `docs/current/SESSION-RESTART-2026-09-12.md`
- 其他无法由当前 P3 UI 任务证明归属的历史/未知资产

本摘要不代表 CI 通过、主分支合并、发布完成或运行时安装完成。
