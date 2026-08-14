# ArcheAxis Knowledge — Final Architecture（任务包 2026-08-14 收敛声明）

> 对应《星环知识平台（ArcheAxis Knowledge）最终架构、外置能力仓与多形态发布任务包》§0/§2/§3。
> 状态：2026-08-15 R0-R8 批次执行中（LOG-175 起逐批入账）。

## 0.1 总体架构

> **一个可信产品内核、一个独立前端壳、一个可切换后端运行时、四个用户资产域、一个能力资源仓、两个系统辅助区、四种运行配置、三类公开发布产物。**

```text
Presentation Plane      Tauri Shell + Recovery Shell + (React/TS 渐进迁移)
        │ versioned local API / events
Trusted Product Plane   Identity/Source/Asset/Document/Evidence/Knowledge/
                        Human Learning/AI Assets/Job-Outbox-Receipt/Policy
        │ Capability Gateway
Capability Plane        Plugins/Engines/Models/Runtimes/Connectors
```

不是"一切皆插件"：可信知识与双向学习语义不可替换；能力实现、运行环境可替换；
前端与后端可独立开发；用户数据永远不依赖某个插件或某个发布形态。

## 0.2 后端运行时（Backend Supervisor 语义）

```text
Tauri 前端壳常驻
    └─ Backend Supervisor 选择运行配置
        ├─ Bundled Stable Backend    正式安装版（不可变）
        ├─ Bundled Green Backend     绿色免安装版
        ├─ Bundled Portable Backend  随身便携版
        └─ External Dev Backend      可热重载源码后端（隔离测试数据）
```

## 0.3 四种 Runtime Profile（AXW-RUN-202）

| profile | backend | data_policy | reload |
|---|---|---|---|
| installed-stable | bundled | installed-user-data | false |
| green-stable | bundled | selected-user-data | false |
| portable-stable | bundled | portable-root-only | false |
| external-dev | external-source | isolated-test-workspace | true |

实现：`config/profiles/<name>.yaml` + `shared/runtime_profile.py`（fail-closed 加载）。

## 0.4 一工作区、四资产域、一能力仓、两系统区（AXW-DATA-401）

```text
Workspace
├─ Source Archive              原始资料库（原件只读、哈希登记；可指向大容量磁盘）
├─ Evidence & Knowledge Ledger SQLite 事务真相源（页面/bbox 锚点、Claim/EvidenceBundle）
├─ Human Learning Vault       Markdown/Canvas/课程/练习/复习（开放文件为主）
└─ AI Asset Vault             memory/rule/skill/standard/context（人工审阅 + 机器执行层）

能力资源仓：Capability Store（插件/引擎/模型/公共资源，系统级）
系统辅助区：Derived & Cache（可删除重建） / Backup & Recovery（快照/增量/恢复 manifest）
```

实现：`contracts/workspace/workspace-manifest.schema.json` + `shared/workspace_manifest.py`
（四资产域目录创建 + manifest 校验 fail-closed）。

## 0.5 Capability Store v1（AXW-CAP-501/502）

- 分区：registry / installed / disabled / staging / quarantine / packages
- 流程：stage（复制 + manifest/hash 校验）→ activate（hash 验证后原子 os.replace）→
  disable/enable → quarantine（记录原因）
- Plugin Manifest v1：`contracts/plugin/plugin-manifest.schema.json`（版本/contract/权限/
  平台/资源/license/数据所有权/health/rollback/UI contribution）
- 自动下载规则：禁止静默首次下载；stage → 验证 → 原子激活；失败进 quarantine

## 0.6 环境变量（AXW-RUN-205）

- canonical：`ARCHEAXIS_*`（Rust launcher 与便携脚本均设 canonical + legacy 镜像双写）
- legacy：`COGNITIVE_*` 只作受测回退（Python 侧一次性迁移提示）
- 开发机会话注入：`Enter-ArcheAxisDev.ps1`（不写注册表、不用 setx）

## 0.7 发布形态与资产矩阵（AXW-PKG-60x / AXW-SUP-70x）

| 资产 | 面向用户 | 数据默认位置 | WebView2 | 公开 |
|---|---|---|---|---|
| Setup x64 | 普通用户 | LocalAppData/自选工作区 | Evergreen bootstrap | 是 |
| Green x64 ZIP | 免安装/多版本 | LocalAppData/自选 | Evergreen | 是 |
| Portable x64 ZIP | USB/整体搬迁 | portable root（禁回退用户目录） | Evergreen | 是 |
| Portable Offline ZIP | 断网环境 | portable root | Fixed Version（可选，+250MB 不默认） | 可选 |
| Developer Kit | 开发测试 | isolated test root | 系统 WebView2 | 否 |
| Core Wheel | 技术/验证 | — | — | 可选 |
| Capability Packs | 按需能力 | Capability Store | — | 分阶段 |

标准文件名（tag 派生，版本一致性门已验证）：`ArcheAxis.Knowledge-vX.Y.Z-Windows-x64-{Setup,Green,Portable}.exe/.zip`、
`archeaxis_workspace-X.Y.Z-py3-none-any.whl`、`release-identity.json`、`SHA256SUMS.txt`、`SBOM.cdx.json`。

## 0.8 安全基线（AXW-RUN-206）

- Tauri CSP：`default-src 'self'; script-src 'self'; connect-src http://127.0.0.1:*; ...`
  （bootstrap 外置资源，无 inline）
- Loopback API：只绑 127.0.0.1、随机端口、launch token 内存传递（IPC，不写 localStorage）、
  导航白名单（app:// 本地资源 + 精确 workspace origin）、拒绝新窗口/下载
- 后端响应头：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、
  `Referrer-Policy: no-referrer`、`Permissions-Policy`（空）
- CORS：仅 loopback origin（`http://127.0.0.1:<port>` / localhost），非 loopback 拒绝

## 0.9 验收标准映射（任务包 §19，18 条）

| # | 验收 | 状态 |
|---|---|---|
| 1 | main CI 与 Nightly 全绿 | ✅ CI 524-583 连续绿 + nightly Run 8 ✅ |
| 2 | 产品/仓库/版本/发布命名一致 | ✅ 动态版本门 + SUP-704 品牌标记 |
| 3 | Setup/Green/Portable 同一 commit+verified runtime | ✅ 组装脚本同一 runtime 源（发布验证待 RC） |
| 4 | 安装完成直接打开 Recovery Shell/前端 | ✅ RUN-201（窗口先 Recovery Shell） |
| 5 | 后端启动/迁移/失败/重启可从前端看见 | 🟡 Recovery Shell 状态机 + handshake（Supervisor 集成中） |
| 6 | external-dev 热重载前端不关闭 | 🟡 Profile/隔离测试已就绪（DEV-302 热重载待集成） |
| 7 | external-dev 默认隔离测试工作区 | ✅ data_policy=isolated-test-workspace |
| 8 | 四资产域/能力仓路径、所有权、迁移规则明确 | ✅ DATA-401 manifest + §3 文档 |
| 9 | 安装版不依赖 OS External Configuration | ✅ 安装版只依赖 bundled runtime |
| 10 | 绿色版不需要安装 | ✅ ZIP 组装 + profile |
| 11 | 便携版不向用户目录泄漏运行数据 | ✅ portable-root-only + fail-closed 路径策略 |
| 12 | 卸载不删除用户资产 | ✅ 卸载规则文档化（§5.3） |
| 13 | 模型/引擎不静默下载 | ✅ ENV-105 治理脚本 + 规则文档 |
| 14 | CSP/loopback token/origin/插件权限 fail-closed | ✅ RUN-206 + 导航白名单 + 权限枚举 |
| 15 | 旧库升级、回滚、长路径验证 | 🟡 DATA-403 迁移设计（回滚回读待实现） |
| 16 | 公开资产 identity/checksum/SBOM/license/回读 | ✅ SUP-701/702/703（v3 identity + 6 资产 checksums + SBOM） |
| 17 | 多格式摄取主链可运行 | ✅ 现有全量 1619 passed 覆盖 |
| 18 | LER/动画/模拟/3D/VR/AR 保留为插件蓝图 | ✅ 能力平面声明 + 不删除（§2.3） |
