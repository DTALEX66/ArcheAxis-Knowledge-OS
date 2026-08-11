# Legacy → ArcheAxis Naming Migration Plan V1（AXW-1208）

> 权威：任务包 v1 2026-08-11 §2.3/§6.2 + NAMING_CONTRACT_V1
> 状态：**plan（required_current）；执行需 Owner 分阶段授权**
> 规则：无 bulk rename；本地数据不会因改名丢失；历史 repo/tags/releases 可回溯。

## 1. 五阶段迁移

| 阶段 | 范围 | 前置 | 兼容 alias | 回滚 |
|---|---|---|---|---|
| 1. 文档 | README、docs、About 文案 | 任务包批准 | 旧名保留在 Legacy 语境 | revert |
| 2. UI | 窗口标题、导航、无障碍标签 | 阶段 1 完成 | 旧名不在 UI | revert |
| 3. 打包产物 | 安装器名、Tauri 配置、Bundle ID | 阶段 2 完成 | 双版本兼容窗口 | 保留旧 installer |
| 4. 仓库 | GitHub repo 名、远端 URL | Owner 授权 + 迁移/回滚证据 | redirect/别名 | GitHub 改名可回退 |
| 5. 底层模块 | Python dist/import、CLI、env、URI、事件 | 阶段 4 完成 | 至少两个稳定版本 alias | 分步回滚 |

## 2. 技术身份目标（§2.3）

| 对象 | 目标 | prereq | migration | rollback | 验证 |
|---|---|---|---|---|---|
| GitHub 仓库 | `DTALEX66/archeaxis-workspace` | Owner 授权 + NAME-READINESS | GitHub 改名 | 改回 | URL/SHA 回读 |
| Machine ID / dist | `archeaxis-workspace` | 包名可用性 | uv 迁移 | 版本回滚 | 安装验证 |
| Python 导入 / CLI | `archeaxis` | 模块冲突检查 | 兼容 alias | 分步回滚 | import 测试 |
| 环境变量 | `ARCHEAXIS_*` | 无冲突 | 双写过渡 | 移除 | 配置读回 |
| 配置/URI | `archeaxis.*` / `archeaxis://` | URI 协议注册 | 协议别名 | 移除 | 往返测试 |
| API 根 | `/api/v1/` | 路由兼容 | 双路由 | 移除 | 端点测试 |
| 事件 | `archeaxis.<domain>.<event>.v1` | 消费者迁移 | 双发 | 移除 | 事件测试 |
| Tauri Bundle ID | `com.archeaxis.workspace` | 数据根迁移 | 迁移器 | 保留旧数据 | restart readback |
| Windows 数据根 | `%LOCALAPPDATA%\ArcheAxis\Workspace` | 数据迁移器 + 回滚 | junction/迁移 | 回滚 | 数据完整性 |
| 可执行文件 | `ArcheAxis.exe` | 安装器 | 双名 | 旧版保留 | 安装验证 |
| 本地服务 | `archeaxis-local-service` | 服务注册 | 双服务 | 移除 | 健康检查 |

## 3. NAME-READINESS 清单（Owner Action gate）

- [ ] 商标/域名检索（未核验 → Owner Action）
- [ ] PyPI 名称可用性
- [ ] CLI 命令冲突检查
- [ ] GitHub repo 名可用性
- [ ] 应用商店检索
- [ ] 签名/更新通道
- [ ] 数据迁移状态

## 4. 兼容 guard

- 任何名称迁移至少保留两个稳定版本的兼容 alias（除非安全/法律要求提前撤销）
- 本地数据不会因 Bundle ID/目录改名丢失
- 历史 repo/tags/releases 可回溯
- 不主动执行远端 rename、发布、签名、权限提升

## 5. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V1 | 2026-08-12 | 命名迁移计划冻结（AXW-1208） | Owner 任务包 |
