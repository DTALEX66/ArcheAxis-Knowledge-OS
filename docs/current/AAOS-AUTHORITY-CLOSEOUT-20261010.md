# 权威漂移、离线检出与 CI 修复收口

本记录承接 Owner 2026-10-10“解决这些问题”的治理维护授权；产品执行仍 PAUSED_BY_OWNER，冻结增量不启动。当前状态 PARTIAL，完整 CI 以具体 SHA 的实际结果为准。

## 已修复

- 原全仓工作区格式检查的 41 项问题已经处理：普通文本统一 LF、末尾换行；13 个原始任务包成员、ZIP 文本和修复前快照保持 manifest 登记的原字节。
- `.gitattributes` 对这些精确文件使用 `-text`；格式门禁按精确 SHA-256 核验，修改任何原字节仍失败，没有目录通配豁免。Git 索引中旧的换行转换已经修复。原件的 BOM、CRLF、Markdown hard break 是保全内容，不是新源码格式规范。
- 修复提交 `0036c51212755c2e2abfc0b38694e353b1e0bb6d` 已普通推送 main、codex/Audit、codex/aaos-gov-ui-20261008。主检出、gov-ui 检出和干净的 f15-folder-ingest 检出已快进。
- 对 7 个历史检出的 AGENTS.md、README.md 共 14 个公开入口加入历史隔离提示，指向主仓库当前权威。原正文与未知未提交修改保留，修改前字节备份在主项目 `.project-local/runs/be268a2d33/authority-ci-cache-closeout-20261010/offline-entry-before/`。这些本地提示不上传历史分支，不把历史源码升级为当前实现。

## 云端 CI 发现与修复

`b335755f` 的 CI 因 14 项格式问题失败；第一次完整 dispatch `38060495592` 的格式门禁通过，随后发现 13 项架构问题。修复脚本新增的 sys.path 修改，使用正常包导入；运行环境从 SystemRoot/WINDIR 读取，归档根从实际 Git 共同目录定位，写入来源必须显式指定。架构门禁保留，不新增白名单。

历史失败运行保留，不能以 push 或定向本地测试替代完整资格。安装、发布及用户软件重启均未执行。

第二次完整运行 `38061145272` 的格式、架构、语言、路径、Ruff 均通过，document-authority 在 Linux 因把 `crates/README.md` 当 crate 目录而抛出 NotADirectoryError。已修复为先验证安全 crate 路径且确为目录，再检查测试目标；缺失测试仍按缺失报告，不放宽门禁。新增回归覆盖 README 干扰和真实目标存在两种情况，权威测试 37 PASS，run `be268a2d33/087fccb88c88`。最终导入调整另有 41 PASS，run `be268a2d33/e3db7ccaaf82`。

第三次完整运行 `38061364888` 基础 lint、wheel、格式、迁移、安全专项、Python 3.11/3.13、workers、desktop-vnext、Windows runtime 均通过；整轮仍失败。发现学习契约元数据缺失、浏览器导航旧 21 页断言、Rust 格式失败、前端原始字节校验和异步测试串扰、历史 secret scan 20 项告警。契约补齐 schema 标识，导航严格核对 22 个 ID；测试串扰通过等待第二次回答完成修复，不改变产品授权逻辑。原始能力 fixture 恢复原 SHA `fc55ef3c996287f13bf6eb3711159ded1a228e2d27e928eb879d71dd24e4cf4f`，纳入精确字节保全；此前给该 fixture 添加末尾换行的修复不适用，已撤回。

本地 MachineAnswerPanelAssets 16 PASS；UiCapabilityIntent 本地 suite 因已有 node_modules 缺少锁定的 Radix 包而未运行，不计 PASS。本机 Rust formatter 的路径访问被拒绝，不提权或改 ACL；CI 保留失败结果并产生 exact-SHA 格式修复补丁，供正常项目文件编辑应用。secret scan 只保留路径、行号、RuleID、Fingerprint、Commit 元数据用于审计，不下载或回显 Secret/Match，不未经证据放行告警。

## 离线与软件加载证据边界

已登记并实测 10 个 Git 检出，3 个在修复 SHA；其余 7 个明确为历史，其中 6 个原本有未提交修改。历史检出须先读取顶部隔离提示，不能从旧路径、旧完成记录或旧包自动执行当前任务。没有扫描其他磁盘或用户目录。

仓库内 AGENTS、CLAUDE、GEMINI、Copilot 项目入口统一指向 AUTHORITY 和活动路由。存在这些文件属于项目入口证据；某个软件实际加载了什么，需要该软件的加载记录才能判断。

此前“私人缓存未验证”表示缺少证据，不表示发现了缓存故障。本轮未发现可确认的私人缓存漂移，不要求 Owner 无依据清理缓存，也不读取私人会话、凭据或全局配置。任何软件、任何模型必然遵循新权威不能由仓库文件保证；使用旧离线数据的审计必须注明所用 SHA，不能宣称当前审计。

## 本地证据

格式/原件回归及权威路由测试 89 PASS，run `be268a2d33/2aae90ab4038`。全仓 worktree 与 index 格式门禁 PASS，严格暂存 diff 空白检查 PASS，Ruff CI 规则 PASS。修复后架构门禁 PASS；语言边界、历史格式矩阵、路径门禁 PASS。

架构相关回归首轮 79 PASS、6 FAIL、2 skipped：包含 Windows 环境变量大小写回归、沙箱硬链接拒绝和本机真实工具探测失败。大小写问题已修复；后续定向 82 PASS、2 skipped、3 deselected，run `be268a2d33/43979fc22b32`。三项未纳入本机定向通过结论，需要完整 CI 或有对应能力的运行环境验证。脚本原有直接 CLI 帮助入口已另行验证；测试退出的 pyreadline 清理警告保留。

本地明细：`.project-local/runs/be268a2d33/authority-ci-cache-closeout-20261010/FORMAT-WRITESET.json`、`OFFLINE-CHECKOUT-READBACK.json`、`OFFLINE-ENTRY-FENCES.json`。本记录需要随后补齐新提交的云端结果，不能提前标 PASS。

## 后续完整运行与证据修复

完整运行 `38062260418` 对应 `febdcfdd743de3e2e44836b87c87b9d76a4bd7a4`：desktop-build 已通过，包括完整前端测试；原 fixture 字节和异步测试修复得到云端验证。仍有 Rust/正式宿主格式、资源来源引用、浏览器导航和秘密扫描失败，不计完整通过。

秘密扫描 20 项均逐一与告警所属历史提交的公开源码字节核验，确认是 SHA-256 来源摘要。证据在 `receipts/GITLEAKS-SOURCE-DIGEST-AUDIT-20261010.json`；精确例外只匹配 generic-api-key 规则下的 4 个回执路径且值为 8 个已验证摘要。路径和值必须同时满足，其他值和其他路径不放行，新增回归验证该边界。配置语义依据 Gitleaks v8.30.1 官方说明，未下载或保存 Secret/Match 字段。

对该 SHA 云端生成的 rustfmt 补丁核对路径、原索引和应用检查后，正常应用到 66 个 crates Rust 文件。此处只做 formatter 产生的格式修复，正式 src-tauri 宿主的补丁另由 CI 采集；本机访问拒绝未通过提权绕过。

资源资格登记的 core-contract.ts 来源引用原已漂移，另有 document.rs 的格式变化。更新这两项实际字节摘要并重生成投影；68 项运行状态仍为 NOT_RUN，资格仍为 INHERITED_ONLY，摘要刷新不授予产品资格。

导航验收以新布局源码为依据：主入口为五个日常分组和两个固定入口，知识分组另展示三个子页面，22 个页面登记不等于 22 个同时可见按钮。已修复沿用旧扁平布局的断言，保留内容、几何和焦点验收。尚需新 SHA 的完整 CI 验证；不改变布局、配色或 Owner 冻结状态。

完整运行 `38063427110` 对应 `ad9312eb58f31c4867c2051d6e1f95fc74fe3e15`：秘密扫描和资源契约通过，根 Rust 格式通过；Python 主套件 4561 PASS、9 FAIL、68 skipped、12 ERROR，不能视为通过。正式宿主 exact-SHA 格式补丁已正常应用到 core_bridge.rs、main.rs、recovery.rs。

主套件后续修复：补登记当前源码实际挂载的 21 个 HTTP 方法/路径，完整目录为 83 对；projection-only 62 对、text-worker 83 对，保留历史运行计数；README 恢复带 development 限定的源码版本；夜间测试断言跟随现有已锁定 Python 命令；空环境变量按 UNKNOWN/空值处理；两个探针和 handshake 回执改用 launcher 的身份/run 层级，不复用并删除旧目录；OSS 派生表以 LF 归一化后的大小和摘要比较，原 Windows raw 大小/摘要仍保留。上述定向回归 43 PASS，run `be268a2d33/d6b9005658d5`。

资源投影中的原始来源记录和旧 ledger 是完整保留的历史数据；路径门禁仅对这两个已由生成投影回归核验的历史字段作区分，当前声明字段仍检查，未增加整个文件或目录豁免。

H01 原始容器属于 Owner 本地保全来源，现有测试声明其不是默认云端 Gate；云端未提供 AAOS_H01_REPO 时明确 skipped，不报告 H01 PASS。显式提供原件时仍强制原字节与行覆盖验证，没有上传本地原件或伪造云端副本。

浏览器模板夹具跟随 Core 的 create_request_id → SHA-256 文档身份、稳定块 ID、完整 ACK/版本读回和当前成功提示；仍为 SYNTHETIC 文档桥接，真实渲染单独记录。安装旅程先验证当前分组入口，既有导入、模板与核验行为使用产品声明的公开 #space 兼容路由，回执明确不将兼容路线视为新页面布局资格。Rust 实际 worker 测试发现云端缺少 OCR 引擎，使用项目已有的固定版本、摘要校验和项目内解压流程准备 OCR，不跳过真实 OCR 测试。新 SHA 的完整 CI 仍待验证。

完整运行 `38064586894` 对应 `f938e171d9b83c056e5d48f819c3f9ae3de91261`：Rust 全工作区含真实 OCR 测试通过；Python 主套件 4567 PASS、2 FAIL、81 skipped、166 subtests PASS。剩余失败是新增 HTTP 章节未登记检查入口，以及云端错误要求本机 NTFS 历史目录存在。章节已登记路由/数量回归；NTFS 例外只用于 baseline.repository 对应的真实 Git owning root，其他检出使用空例外，不继承本机路径豁免。新增负控验证此边界，相关定向回归 27 PASS，run `be268a2d33/35e0c84a837e`。

浏览器模板保存的另一条旧提示已修复，并等待实际 v2 列表行以排除旧成功提示串扰；正式宿主复用的 desktop backend 模块唯一格式差异按云端原始 diff 修复。格式失败补丁采集覆盖该精确复用模块。此前本轮证据目录已同盘移动到 launcher 身份/run 层级，RUN-LOCATION.json 登记原址与现址；14 份原正文的备份哈希和后缀 readback 再次全部通过。当前三检出在 f938e171 同步；后续提交须再次回读，完整资格仍待最终 SHA。

完整运行 `38065487542` 对应 `4b939c5aecdeb301c60befb04027b01534a877f8`：Python 作业（OS/KB/integration）、Rust 全工作区与新版浏览器完整回归均 PASS。正式宿主格式已 PASS，随后 build.rs 因 routed frontend/TAURI_CONFIG 缺失失败；未取消路径一致性校验。desktop-fast 补齐锁文件依赖、在现有 canonical run 中实际构建前端，并显式把该 run 的有效 Tauri 配置传入 cargo test。构建上下文/配置顺序和本地 CI 回归 6 PASS，run `be268a2d33/31df3f1c02a5`；新 SHA 仍须完整验证。

同步回读另发现本地 main 引用仍指向 `59498723a8d4e94c6314e490473ba6d60847c247`，虽云端与当前工作区已更新，切回该本地分支会重现旧权威。确认它是新 HEAD 的祖先且没有 main 检出后，使用带旧值核验的正常快进更新；本地与远端 main、codex/Audit、gov-ui 已一致为 4b939c5a，三当前检出干净。未改写历史或上传历史检出的未知修改。远端默认分支为 main，公开描述已回读为当前 Tauri/React、Rust 单写者、统一主题、唯一权威路由和 Owner 暂停状态。
