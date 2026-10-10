# 权威漂移、离线检出与 CI 修复收口

本记录承接 Owner 2026-10-10“解决这些问题”的治理维护授权；产品执行仍 PAUSED_BY_OWNER，冻结增量不启动。当前状态 PARTIAL，完整 CI 以具体 SHA 的实际结果为准。

## 已修复

- 原全仓工作区格式检查的 41 项问题已经处理：普通文本统一 LF、末尾换行；13 个原始任务包成员、ZIP 文本和修复前快照保持 manifest 登记的原字节。
- `.gitattributes` 对这些精确文件使用 `-text`；格式门禁按精确 SHA-256 核验，修改任何原字节仍失败，没有目录通配豁免。Git 索引中旧的换行转换已经修复。原件的 BOM、CRLF、Markdown hard break 是保全内容，不是新源码格式规范。
- 修复提交 `0036c51212755c2e2abfc0b38694e353b1e0bb6d` 已普通推送 main、codex/Audit、codex/aaos-gov-ui-20261008。主检出、gov-ui 检出和干净的 f15-folder-ingest 检出已快进。
- 对 7 个历史检出的 AGENTS.md、README.md 共 14 个公开入口加入历史隔离提示，指向主仓库当前权威。原正文与未知未提交修改保留，修改前字节备份在主项目 `.project-local/runs/authority-ci-cache-closeout-20261010/offline-entry-before/`。这些本地提示不上传历史分支，不把历史源码升级为当前实现。

## 云端 CI 发现与修复

`b335755f` 的 CI 因 14 项格式问题失败；第一次完整 dispatch `38060495592` 的格式门禁通过，随后发现 13 项架构问题。修复脚本新增的 sys.path 修改，使用正常包导入；运行环境从 SystemRoot/WINDIR 读取，归档根从实际 Git 共同目录定位，写入来源必须显式指定。架构门禁保留，不新增白名单。

历史失败运行保留，不能以 push 或定向本地测试替代完整资格。安装、发布及用户软件重启均未执行。

第二次完整运行 `38061145272` 的格式、架构、语言、路径、Ruff 均通过，document-authority 在 Linux 因把 `crates/README.md` 当 crate 目录而抛出 NotADirectoryError。已修复为先验证安全 crate 路径且确为目录，再检查测试目标；缺失测试仍按缺失报告，不放宽门禁。新增回归覆盖 README 干扰和真实目标存在两种情况，权威测试 37 PASS，run `be268a2d33/087fccb88c88`。最终导入调整另有 41 PASS，run `be268a2d33/e3db7ccaaf82`。

## 离线与软件加载证据边界

已登记并实测 10 个 Git 检出，3 个在修复 SHA；其余 7 个明确为历史，其中 6 个原本有未提交修改。历史检出须先读取顶部隔离提示，不能从旧路径、旧完成记录或旧包自动执行当前任务。没有扫描其他磁盘或用户目录。

仓库内 AGENTS、CLAUDE、GEMINI、Copilot 项目入口统一指向 AUTHORITY 和活动路由。存在这些文件属于项目入口证据；某个软件实际加载了什么，需要该软件的加载记录才能判断。

此前“私人缓存未验证”表示缺少证据，不表示发现了缓存故障。本轮未发现可确认的私人缓存漂移，不要求 Owner 无依据清理缓存，也不读取私人会话、凭据或全局配置。任何软件、任何模型必然遵循新权威不能由仓库文件保证；使用旧离线数据的审计必须注明所用 SHA，不能宣称当前审计。

## 本地证据

格式/原件回归及权威路由测试 89 PASS，run `be268a2d33/2aae90ab4038`。全仓 worktree 与 index 格式门禁 PASS，严格暂存 diff 空白检查 PASS，Ruff CI 规则 PASS。修复后架构门禁 PASS；语言边界、历史格式矩阵、路径门禁 PASS。

架构相关回归首轮 79 PASS、6 FAIL、2 skipped：包含 Windows 环境变量大小写回归、沙箱硬链接拒绝和本机真实工具探测失败。大小写问题已修复；后续定向 82 PASS、2 skipped、3 deselected，run `be268a2d33/43979fc22b32`。三项未纳入本机定向通过结论，需要完整 CI 或有对应能力的运行环境验证。脚本原有直接 CLI 帮助入口已另行验证；测试退出的 pyreadline 清理警告保留。

本地明细：`.project-local/runs/authority-ci-cache-closeout-20261010/FORMAT-WRITESET.json`、`OFFLINE-CHECKOUT-READBACK.json`、`OFFLINE-ENTRY-FENCES.json`。本记录需要随后补齐新提交的云端结果，不能提前标 PASS。
