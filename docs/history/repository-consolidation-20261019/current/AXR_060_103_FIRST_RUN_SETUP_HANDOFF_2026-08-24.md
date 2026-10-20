# AXR-060-103 首次启动向导交接（2026-08-24）

## 状态

`IMPLEMENTED_LOCAL` / `TESTED_LOCAL`。本记录对应分支
`codex/first-run-setup`；尚未获得该分支的 exact-SHA CI 或干净安装机证据，
因此不把本地验证表述为已合并、已发布或已安装验证。

## 已实现的闭环

- `POST /api/v1/setup/preflight`：复用与初始化相同的路径规则，校验 quick/
  advanced 四库布局、可写父目录与可用空间，但不创建工作区或目录。
- Settings 首次启动界面：欢迎页 → quick/advanced 模式 → 四库路径输入 →
  真实健康预检 → 创建完成；路径异常留在当前步骤中供用户修改。
- 健康页逐库显示绝对路径、可用空间、只读/可写状态、文件系统和介质类别。
- 初始化成功与状态刷新失败分离：创建成功不会被随后的读回失败误报为创建失败。
  备份校验与桌面后端重试仍通过原有真实 API 保留。

## 已验证证据

- 后端：`tests/test_axw_data402_setup.py`，7 passed；包含预检不创建目录的回归。
- 前端：`npm test`，7 files / 56 tests passed；包含 quick、advanced、预检、
  创建后刷新失败与健康字段展示回归。
- 前端：`npm run build`（`tsc --noEmit && vite build`）通过。

## 未执行 / 下一步

- 该候选分支的 GitHub Actions exact-SHA CI；当前 GitHub token 只读/创建 PR
  与 workflow dispatch 均被 403 拒绝，需有相应权限的凭据或人工触发。
- 干净 Windows 安装包中的首次启动点击旅程与 Golden Journey；当前环境未具备
  Rust/NSIS 打包链，不以源码构建或单元测试替代安装态证据。
- 合并到 `main`、版本标签与 Release；均需在 exact-SHA CI 通过后单独执行。
