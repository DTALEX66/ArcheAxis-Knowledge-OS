# HANDOFF — T12 Avalonia 完整工作台（CODEX）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：高 · 目标代理：CODEX · 依赖：T02/T04/T18

## 目标
- 依据 T18 设计从现有壳增量或从零重建 Avalonia 界面，接真实 API（Core loopback HTTP），最终验收禁止 mock 成功；
- 网页/文件拖放/截图；阅读/转换/核查比较；学习/机器反馈及设置恢复全流程；覆盖加载/空态/失败/冲突；
- 无开发终端实际操作核心链；无入口是占位欢迎页；错状态响应不显示成功；不直接 SQL。

## 上下文
- 现有壳：apps/ArcheAxis.Desktop（App.axaml/MainWindow.axaml + CoreSupervisor spawn/handshake/Stop + Program --smoke），
  CI 已验 dotnet build 与 --smoke（vnext-ci.yml 同款步骤）。
- 真实 API：本地 Rust core（crates/archeaxis-api，port 默认 47831/ARCHAXIS_VNEXT_PORT）——以 T04 冻结的 API 为界；
  UI 不得触库（PROJECT_CONTRACT 禁 ui-direct-sql）。
- 设计输入：T18 交付（docs/design/vnext/**）。

## 允许路径（任务包 T12）
apps/ArcheAxis.Desktop/Views/**、ViewModels/**、Services/**、MainWindow.axaml(.cs)、App.axaml(.cs)、tests/journey/desktop/**。

## 验收（任务包 T12）
- 无开发终端实际操作核心链；无入口是占位欢迎页；错状态响应不显示成功；不直接 SQL。

## 环境事实
- .NET 10.0.400（外置 dotnet）；dotnet build apps/ArcheAxis.Desktop 须绿；
- 本地真实验证：启动 core（cargo run -p archeaxis-api 或已编译 target/debug/archeaxis-api.exe）+ dotnet run 手工旅程；
- 截图/UI 自动化仅用于证据，成功判定以真实 API 状态为准。

## 切片建议
1. 壳→设计 token 接入 + 导航/空态；2. 导入（拖放/截图）+ 转换视图接真实 API；3. 核查比较视图；
4. 学习/机器反馈流程；5. 失败/冲突/加载状态与设置恢复；6. 无头旅程（--smoke 扩展）证据。

## 输出契约
切片证据（真实 API 会话输出/截图）+ 收据 docs/authority/taskpack-0905/T12/；报告 commit SHA 与验收对照。
