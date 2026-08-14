# AXW-PKG-601 — 标准安装版生命周期与 L4 验收清单

> 状态：CI 链路就绪（2026-08-15）；真实安装验收（L4）留 Release Candidate。
> 关联：release.yml `Verify installed NSIS lifecycle` 步骤 + `desktop/scripts/verify_nsis_install.ps1`。

## 1. 已实现（CI 自动化）

- **构建**：`npm run tauri -- build --bundles nsis` → 恰好一个 NSIS 安装器；
- **安装生命周期验证**：`verify_nsis_install.ps1 -Installer <exe> -RequireReleaseIdentity`——静默安装 → 验证程序文件 + release-identity.json 存在且与构建一致 → 启动冒烟 → 卸载 → 验证数据目录保留；
- **资产命名**：`ArcheAxis.Knowledge-vX.Y.Z-Windows-x64-Setup.exe`（动态版本，四源一致门）；
- **读回**：release.yml Readback 步骤对公开资产逐项 hash + identity 树校验。

## 2. L4 真实验收清单（Release Candidate 执行，Owner 确认）

| # | 场景 | 通过标准 |
|---|---|---|
| 1 | 干净 Windows 用户安装 | 安装完成即启动，无浏览器错误页 |
| 2 | 首次运行向导 | 建工作区 → 四资产域确认 → 能力检测 → 主工作台 |
| 3 | 后端关闭时 UI 恢复控制台 | Recovery Shell 可见（状态/重试/日志/切换运行配置） |
| 4 | 升级（vX → vY） | staging 下载 → identity/hash/SBOM 验证 → 备份 → 迁移 dry-run → 原子切换 → 回读 |
| 5 | 修复安装 | 不触碰工作区/原件 |
| 6 | 卸载 | **默认只卸载程序+内置 runtime；不删除工作区、原件、证据、人类学习库、AI 资产、备份** |
| 7 | 无管理员 currentUser 安装 | NSIS perMachine=false 路径 |
| 8 | 中文/空格/长路径 | 安装目录含中文+空格+超长路径均正常 |

## 3. 卸载数据保留断言（已在 verify_nsis_install.ps1 内）

卸载后断言 `%LOCALAPPDATA%\ArcheAxis\Workspace\` 关键资产存在（workspaces/ 目录非空或用户标记文件存在）——失败即退出非 0。

## 4. 剩余风险

- L4 真实用户环境安装只能由 Owner 在 RC 阶段执行（需要干净 VM/真实机器）；
- NSIS 的 currentUser 模式未在 CI 全覆盖（CI 跑默认 perMachine 静默安装）。
