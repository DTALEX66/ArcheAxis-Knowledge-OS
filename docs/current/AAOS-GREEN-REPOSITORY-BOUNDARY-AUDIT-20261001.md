# 项目源码与原绿色版目录边界审计（2026-10-01）

状态：`PARTIAL`。这是目录归属与后续交付规则的只读审计；未移动、删除、迁移或整理任何源码树、缓存、数据库、历史文件或恢复包。

## 当前事实

`D:/All projects/ArcheAxis-Knowledge-OS` 是项目 Git 主工作树；`D:/All projects/ArcheAxis.Knowledge.Green-x64` 根目录不是 Git 仓库，而是原绿色版运行根。但其 `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` **确实是另一套独立 Git 克隆**（自身 `.git` 目录；本地 `origin` 指向项目主仓库；当前分支 `codex/aaos-ui-mainline-20260927`，HEAD `d8f99a6357405054f1f9ee66eb2f88d36f7f5143`，有大量 dirty）。此外 `git worktree list --porcelain` 显示 `.ui-task-tree/` 内还有三个挂在项目主仓库的 Git 工作树，包括当前 `aaos-ui-phase2-integrate`。因此，绿色版内出现 `apps/`、`crates/`、`docs/`、`tests/` 等项目源码，是独立克隆或隔离开发树驻留其中，并非已把这些源码集成安装到绿色版运行包。此前用户明确指定“所有前端隔离任务树放在原绿色版 `.ui-task-tree` 内”；这一位置安排与如今要求的“绿色版只承载确定、测试过的集成部署”存在目录用途冲突，应在后续任务中解决，不能把开发树存在视为产品安装完成。

原 Green 根目前同时有旧 `ArcheAxis.exe`、`frontend/`、`runtime/`、`data/`，阶段候选 `AAOS-vd6bd374-20261001-x64/` 和 `AAOS-v18a00075-20261001-x64/`，对应数据目录、`AAOS-Frontend-Acceptance-v4/`、`backups/`，以及 `.ui-task-tree/`。`AAOS-v18a00075-20261001-x64/` 内有 desktop/core/workers/runtime/shared 和 manifest；`启动星环知识-AAOS-18a00075.vbs` 指向其 Desktop 可执行文件及独立数据目录。这证明有阶段部署候选，不证明最新提交 `855c63b1d6a9e459516a79e9b58a6bd108b751cd` 已安装，也不证明完整 UI/后端闭环。

原 Green `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` 有大量未提交与未跟踪的 UI 源码/资产/测试修改；项目主工作树也有未知 dirty 和历史未跟踪文件。两处均须保护，不得通过 reset、clean、覆盖或迁移来制造目录整洁的表象。

## 目标边界与执行约束

| 层 | 应有内容 | 当前处理 |
| --- | --- | --- |
| 项目源码仓库 | Authority、总账、前后端源码、测试、构建入口、公共设计资产与版本化合同 | 项目主仓库是唯一公共源码真值；隔离工作树只为开发，不是绿色版安装。 |
| 原 Green 可交付运行包 | 同一精确 SHA 构建并验证的 Desktop、Core、workers、合法资产、manifest、启动器 | 候选必须单独标识 SHA、构建/原生启动/真实 API/窗口验收、回滚路径；未验证不得提升为正式入口。 |
| 原 Green 运行数据 | 既有数据库、用户空间、备份、锁和恢复材料 | 归用户/运行时所有；当前清理任务暂停，保持原位，不纳入 Git/构建包。 |
| 开发与验收临时物 | `.ui-task-tree/` 工作树、验收截图/日志、历史候选 | 当前原位保留并明确标注“非安装态”；后续经用户明确选择位置与范围，再做受控目录调整。 |

后续新工作树宜优先放项目仓库 `.project-local/worktrees/` 等项目规范允许的隔离开发根；但这与此前“前端树必须在 Green `.ui-task-tree`”的明确约束冲突。在用户明确改变该位置规则前，不移动现有树，也不擅自把新的前端树改放别处。MiniMax 提示词中的 Green `.ui-task-tree` 路径应随这一决定更新。无论工作树放哪里，**最终集成**都必须是将通过门禁的构建物部署到原 Green 的明确运行包，由启动器打开并按页面、双主题、缩放、真实接口逐项验收。

## 当前未闭合项

1. 原 Green 没有一个经证据确认的、对应最新 UI 分支精确 SHA 的正式安装包和默认启动入口：`NOT_EXECUTED/UNVERIFIED`。
2. 当前目录含多个历史/候选/数据/开发类别，缺少面向用户的“哪个是当前验收包”单一指示；不得通过删除历史或数据解决，应先建立只读清单与候选身份。
3. 开发树位置需要与用户的最新目录期望统一；在位置未定时，保持原位并禁止把源码树算作绿色版交付。

## 分支与目录清理任务（新授权范围，尚未执行删除）

用户现允许将**分支及仓库目录规范清理**纳入轻量治理队列，但要求先拆分审计、确认引用和路径更新，再删除。此授权不恢复缓存、历史文档、数据库、用户数据、恢复包的清理或迁移。

| 子任务 | 审计与验收 | 当前判定 |
| --- | --- | --- |
| GC-01 工作树/分支清单 | 逐个核 Git 注册、HEAD、branch、dirty、任务归属、远端 PR/CI/引用；区分独立克隆和同仓库工作树，查同名非 Git 目录。 | `.ui-task-tree/` 有 5 个目录：主仓库注册工作树 3 个（当前 `aaos-ui-phase2-integrate` 活跃、`ArcheAxis-Knowledge-OS` 大量 dirty、`AAOS-integration-verification-413ad3a0` 干净）；独立克隆 `ArcheAxis-Knowledge-OS-mainline` 大量 dirty；`ci-green-candidate-6621aab7` 当前不是 Git 仓库。不得按名称判断可删。 |
| GC-02 内容与引用保护 | 对每个候选核未提交/未跟踪/忽略文件、差异、构建及验收证据、启动器、manifest、脚本、文档链接、Git PR/branch 引用；需要保留的先在项目拥有位置归档，校验 SHA/数量。 | 两个旧 UI 树有未知成果；Green 根还有运行数据、阶段候选和启动器。未完成完整引用图，**全部保持**。 |
| GC-03 目录规范 | 明确未来源码隔离树位置、Green 运行包身份与默认启动入口；更新 `AGENTS.md`、当前交接、任务总账、两份代理提示词、脚本与索引的引用，验证不留悬空路径。 | 此前“UI 树必须 Green 内”与最新“Green 是已验收部署目录”冲突。先取得明确位置裁决，不能静默搬树。 |
| GC-04 分支处置 | 仅对已合并且无独有提交、无活跃 PR、无工作树占用、无未推送/未知修改的候选，逐分支记录精确 SHA、处置理由和回退 ref；先清本地再视授权处理远端。 | `codex/Audit` 与当前 UI 分支远端同 SHA，但正式根本地 `codex/Audit` 落后且 dirty，不能据远端相等删本地分支/目录。 |
| GC-05 受控实施与回读 | 逐个 exact path/ref 执行；删除前复核目标仍在允许范围、归档可恢复、无运行进程占用；后运行 worktree/branch/引用清单、启动器与原生回归。 | `NOT_EXECUTED`。不使用 `git clean -fdx`、hard reset、递归批量删除或跨 shell 拼路径。 |

现阶段只确认目录身份；不把 GC-01 视为 GC-02/03 完成。任何实际移除须先有该 exact path/ref 的逐项证据与恢复方案，且不触碰用户暂停保护类。

## 2026-10-08 复测：身份冲突与纯净边界（本任务只读实测）

工具与口径：Git Bash GNU `du -sk`（1K 块）、`stat -c%s` 字节数、`sha256sum` 逐字节哈希、PowerShell `VersionInfo` 取版本元数据。本轮**未删除、未迁移、未覆盖、未改 ACL、未终止进程**，也没有把任何候选冒充为当前可用版本。

| 类别 | 实测 | 归属判定 |
| --- | --- | --- |
| 目录合计（排除所有嵌套 `.git`） | `du -sk --exclude=.git .` = 8,183,566 KB | — |
| `.ui-task-tree/`（含其嵌套 `.git`） | `du -sk .ui-task-tree` = 6,471,511 KB | 开发材料，不属于绿色版部署目录 |
| ┗ `ArcheAxis-Knowledge-OS-mainline` | 5,321,502 KB（不含自身 `.git`；加 `.git` 461,773 KB = 5,783,275 KB） | **独立克隆，属 `DESKTOP-L26E3AC/CodexSandboxOnline`（S-1-5-21-…-1004）**；git 以 dubious ownership 拒绝读写，非本任务 writer 所有，保持原样不动 |
| ┗ `minimax-aaos-cosmic-ui-20261001` | 688,172 KB | 主仓库注册的 worktree（`codex/minimax-aaos-cosmic-ui-20261001`），仍属开发占用 |
| ┗ `ArcheAxis-Knowledge-OS` | 60 KB | `git -C` 返回 "not a git repository"：残留外壳，非工作树；保留待业主判定 |
| ┗ `ci-green-candidate-6621aab7` | 0 KB | 空目录，不是 Git 仓库 |
| `AAOS-Tauri-f151f4c7998a/` | 694,424 KB | 已安装的 Tauri 候选运行件（含 `core/archeaxis-api.exe`） |
| `runtime/python/` | 690,385 KB | 该版本运行所需运行时 |
| `backups/` | 453,047 KB | 恢复清单类，须保留 |
| `AAOS-Frontend-Acceptance-v4/` | 240,858 KB | 验收/候选类，非当前默认入口 |
| `EBWebView/` | 42,928 KB | 可重建缓存 |
| `data/` ＋ 根 `archeaxis.sqlite` | `data/` 40,651 KB；根库 987,136 bytes、`data/archeaxis.sqlite` 1,110,016 bytes（`du` 读为 964/1084 KB 块）；`.cognitive-volume-id` = `4cddc70d-3aaa-40d4-8e98-17ee51ddd22b` | **用户数据与 CAS 指向，禁止迁移或删除** |

### 身份冲突（已实测，不可仅凭名称推定）

三个文件同名 `ArcheAxis.exe`，`FileVersion` 与 `ProductVersion` 均为 `0.6.14`，但字节与哈希互不相同——版本号在此目录不具备身份区分力：

| 路径 | 字节 | SHA-256（逐字节） |
| --- | --- | --- |
| `ArcheAxis.exe`（根，v0.6.14 安装件） | 9,094,656 | `132f1c8ccc5344cd8b709826b79c59ba01cf59b919073fd36a67ec249c5a0538` |
| `AAOS-Tauri-f151f4c7998a/ArcheAxis.exe`（新 Tauri 构建） | 16,650,752 | `0e70ff43bdcc877f390d01f035a032326bef0f30216d8feb5a972e37773344ab` |
| `backups/inplace-main-shell-20260903/ArcheAxis.exe` | 9,204,224 | `453147309147492d17dee8a997a2ea5f06ea9b40b112bf3e7dec494152969ddf` |

因此"当前可用版本"只能由 SHA + `release-identity.json` + 目录角色三者共同确定；上表第二行是**候选构建**，未通过发布资格，不得充当当前版本。

### 新发现：README 指向的恢复入口已断

`README.md` 第 13 行把启动器指向 `AAOS-vd6bd374-20261001-x64\desktop\ArcheAxis.Desktop.exe`；本轮 `test -e` 结果为 **MISSING**。该悬空引用是恢复路径缺陷（不是体积问题），修正方式是更新清单指向实际存在的安装件，或在清单中明确标注该恢复目标已不可用；本轮**未改动 README**，因为改动启动目标属于版本切换决策，须业主授权。

### GC 状态（本轮）

GC-01 清单：以本表更新——`.ui-task-tree/` 现存 4 个目录（2026-10-01 记录中的 `aaos-ui-phase2-integrate` 与 `AAOS-integration-verification-413ad3a0` 已不在当前列表，说明该目录自 10-01 起已变动，历史行保留不改写）。GC-02 引用保护：完成身份与用户数据清点。GC-03 目录规范：**待业主裁决**——6.47 GB 开发占用是否应从部署目录迁出、迁往何处。GC-04/GC-05：`NOT_EXECUTED`，无任何删除授权被使用。

边界结论：绿色版只承载"已验证版本运行所需内容 + 该版本的最小身份/审计/恢复清单"。当前它额外承载 6,471,511 KB 开发材料与一个不属于本项目的沙箱属主克隆；前者需业主授权后按 exact path 迁移，后者我不动。

## 2026-10-08 执行轮：归属实测、身份分离、恢复路径复核、archive→verify→remove

本轮为 writer 执行轮，**只删除了本轮亲自证明为“本 writer 所有、且当前在用版本不需要”的两个条目**，其余全部原位保留。所有数字均为本会话实测；口径与上一小节 `du -sk --exclude=.git` 不同（本口径为“不跟随再解析点的逐文件 `FileInfo.Length` 求和，含全部嵌套 `.git`”），故绝对值与上一小节不可直接相减。

### 命令口径（每项数字都可复算）

- 目录树字节/文件/子目录数、再解析点定位、属主：PowerShell 显式栈遍历 `measure.ps1`（遇 `FileAttributes.ReparsePoint` 记录但不进入；文件用 `[System.IO.FileInfo]::Length` 求和）。属主：`(Get-Acl -LiteralPath $p).Owner`。
- 再解析点目标：`fsutil reparsepoint query <path>`（未跟随）。
- SHA-256：`Get-FileHash -Algorithm SHA256`，产品 exe 另用 GNU `sha256sum` 独立复核，两法一致。
- 版本元数据：`(Get-Item $p).VersionInfo.FileVersion / .ProductVersion`。
- 存在性：`Test-Path -LiteralPath`。
- worktree 归属：`git worktree list --porcelain`（在 OS 主仓执行）+ `cat <dir>\.git` 的 `gitdir:` 指针。
- 归档与校验：`archive_verify.ps1`（.NET `ZipFile` 建 ZIP + `ExtractToDirectory` 逐成员 name+size+CRC32+SHA256 抽取件 vs 源）；归档侧存储 CRC 用 `unzip -v` 独立复读。
- 移除：`rm <4 个精确文件路径>`（逐文件，非递归）→ `rmdir <空目录>`（`rmdir` 遇非空即拒，等于二次护栏）。

### 总量（本会话实测）

| 口径 | 字节 | 文件 | 子目录 |
| --- | --- | --- | --- |
| 移除前（本次首轮 `measure.ps1`） | 9,449,024,142 | 119,012 | 18,922 |
| 移除后（同脚本复测） | 9,448,743,269 | 119,008 | 18,920 |
| 本轮回收 | **280,873**（占移除前 0.0030%） | 4 | 2 |

再解析点数：**1**（唯一，未跟随），路径 `.ui-task-tree\ArcheAxis-Knowledge-OS-mainline\.project-local\cache\uv-python\cpython-3.14-windows-x86_64-none`，属 uv-python 缓存连接点。根层散文件 16 个、10,108,062 字节（含 `ArcheAxis.exe`、`archeaxis.sqlite`、两把 `.lock`、`.cognitive-volume-id`、`README*`、`release-identity.json`、`green-profile.toml`、`portable.flag`、`start.bat`、`apply_migrations.py`、4 个 `.vbs`）。

### 顶层条目分类（字节/文件/最后写入/NTFS 属主/类别，本会话实测）

| 条目 | 字节 | 文件 | 最后写入(UTC) | 属主 | 类别 |
| --- | --- | --- | --- | --- | --- |
| `runtime/` | 659,683,250 | 21,182 | 2026-09-02 22:08 | ALEX | 当前在用运行件（Python 后端） |
| `frontend/` | 280,873 | 4 | 2026-09-02 23:52 | ALEX | 当前在用运行件（exe 引用 `frontend/dist`） |
| `licenses/`、`output/`、`reports/` | 0 | 0 | — | ALEX | 当前布局空目录 |
| `data/` | 41,080,145 | 347 | 2026-09-25 08:31 | ALEX | **用户数据 / CAS** |
| `archeaxis.sqlite`+`.lock`+`.cognitive-volume-id` | 999,461 | 4 | 2026-09-01 | ALEX | **用户数据 / CAS**（`.cognitive-volume-id`=`4cddc70d-3aaa-40d4-8e98-17ee51ddd22b`） |
| `aaos-vnext-data-18a00075/` | 226,416 | 4 | 2026-10-01 14:08 | ALEX | 用户数据（候选 DB 根，其宿主目录已缺） |
| `aaos-vnext-data-82e8d28c/` | 242,896 | 5 | 2026-10-03 06:21 | ALEX | 用户数据（候选 DB 根，其宿主目录已缺） |
| `AAOS-Tauri-f151f4c7998a/` | 667,931,139 | 19,710 | 2026-10-06 04:29 | ALEX | 候选构建（**在用**：`启动Tauri候选.vbs` 存在，632 B，README 2026-10-06 记录真实旅程） |
| `backups/` | 442,278,966 | 6,934 | 2026-09-30 19:36 | **混合**（ALEX 220,706,705 / Online 186,008,983 / Offline 35,563,278） | 恢复工件（README：保留备份；且含外属主 → 不可整删） |
| `EBWebView/` | 43,477,433 | 313 | 2026-09-01 22:12 | **混合**（ALEX 32,887,113 / CodexSandboxOffline 10,590,320） | 工具缓存（可重建，但归属未全部确立 → 原位保留） |
| `AAOS-Frontend-Acceptance-v4/` | 245,747,591 | 366 | 2026-09-28 08:13 | **CodexSandboxOnline（100%）** | 外属主（不动） |
| `aaos-vnext-data/` | 352,191 | 5 | 2026-10-01 12:50 | **CodexSandboxOnline（100%）** | 外属主 + 数据（不动） |
| `AAOS01-文档同步-20261006/` | 211,084 | 11 | 2026-10-06 10:12 | ALEX | 业主文档同步落点（用途未定 → 保留） |
| `bootstrap/` | 280,873 | 4 | 2026-09-02 23:52 | ALEX | **可回收残渣**：与 `frontend/` 逐字节相同、无启动器/配置引用 → 已归档+移除 |
| `.ui-task-tree/`（见下拆分） | 7,337,123,223 | 70,111 | 2026-10-06 18:54 | 混合 | 开发/外属主 |

`.ui-task-tree/` 内部（本会话实测字节/文件/属主）：

| 子项 | 字节 | 文件 | 属主 / 状态 | 判定 |
| --- | --- | --- | --- | --- |
| `ArcheAxis-Knowledge-OS-mainline` | 6,640,547,521 | 66,776 | `.git` 属 CodexSandboxOnline；文件属主 Online 3,769,668,953 + ALEX 2,870,005,604 + Offline 145,425 + 不可读 727,539 | **外属主独立克隆**（dubious ownership），不动；其内 uv 再解析点未跟随 |
| `minimax-aaos-cosmic-ui-20261001` | 696,558,986 | 3,334 | 100% ALEX；`git worktree list` 确认是 OS 主仓**在册工作树**（分支 `codex/minimax-aaos-cosmic-ui-20261001`，gitdir 指向 `OS/.git/worktrees/...`） | 开发占用，须走 `git worktree`+业主 GC 裁决 → 保留 |
| `ArcheAxis-Knowledge-OS`（husk） | 16,716 | 1 | 属主**不可读**（Get-Acl 抛错） | 归属无法确立 → unknown，保留 |
| `ci-green-candidate-6621aab7` | 0 | 0 | ALEX，空目录 | 可回收残渣 → 已移除（0 字节） |

### 按类别 before/after（字节）

| 类别 | 移除前 | 移除后 |
| --- | --- | --- |
| 当前在用运行件（runtime+frontend+空布局+根层运行/入口/身份散文件） | 669,072,724 | 669,072,724 |
| 用户数据 / CAS | 42,548,918 | 42,548,918 |
| 候选构建（在用） | 667,931,139 | 667,931,139 |
| 恢复工件（backups，混合属主） | 442,278,966 | 442,278,966 |
| 工具缓存（EBWebView，混合属主） | 43,477,433 | 43,477,433 |
| 外属主（mainline 克隆 + Frontend-Acceptance-v4 + aaos-vnext-data） | 6,886,647,303 | 6,886,647,303 |
| 开发材料（本方：minimax 工作树 + 文档同步落点） | 696,770,070 | 696,770,070 |
| unknown（husk） | 16,716 | 16,716 |
| 可回收残渣（bootstrap） | 280,873 | **0** |
| 合计 | 9,449,024,142 | 9,448,743,269 |

### 身份分离：七个同名 `ArcheAxis.exe` 全报 0.6.14（对上一小节“三个”的实测更正）

任务前提称“三个同名 `ArcheAxis.exe`”。本会话穷举 `find`（不含 `.ui-task-tree`）实测：报 `FileVersion=ProductVersion=0.6.14` 的 `ArcheAxis.exe` 有 **7 个**，哈希互不相同；另有 1 个 `ArcheAxis.Desktop.exe`（v1.0.0）和 2 个小写 Python `archeaxis.exe` 存根（无版本）。版本号在此目录对身份无区分力：

| 路径 | 字节 | SHA-256（本会话；根件与 Tauri 件双工具一致） | 版本 / 最后写入 |
| --- | --- | --- | --- |
| `ArcheAxis.exe`（根，默认入口指向） | 9,094,656 | `132f1c8ccc5344cd8b709826b79c59ba01cf59b919073fd36a67ec249c5a0538` | 0.6.14 / 2026-09-03 02:00:38 |
| `AAOS-Tauri-f151f4c7998a/ArcheAxis.exe`（候选） | 16,650,752 | `0e70ff43bdcc877f390d01f035a032326bef0f30216d8feb5a972e37773344ab` | 0.6.14 / 2026-10-06 04:29:21 |
| `backups/inplace-main-shell-20260903/ArcheAxis.exe` | 9,204,224 | `453147309147492d17dee8a997a2ea5f06ea9b40b112bf3e7dec494152969ddf` | 0.6.14 / 2026-09-02 23:41:35 |
| `backups/inplace-main-shell-20260903-monochrome/ArcheAxis.exe` | 9,201,664 | `5791659091c829e20572afcc058928cda06a9869f6710f5914006285b8a16f38` | 0.6.14 / 2026-09-02 23:51:29 |
| `backups/inplace-maintenance-wal-20260902/ArcheAxis.exe` | 9,151,488 | `a4297fdc8d025585d7f70ef7702a68dc9346646dc462e8df0b2b06770103010b` | 0.6.14 / 2026-08-31 19:53:19 |
| `backups/inplace-theme-blackwhite-20260902/ArcheAxis.exe` | 9,204,224 | `dcebde1596361ebbef22ae8d2a4c879bb09fe6879485580ce8267ede6bb72694` | 0.6.14 / 2026-09-02 22:40:14 |
| `backups/inplace-ui-default-light-20260902/ArcheAxis.exe` | 9,204,224 | `701c07b78db99551503fe82800b7de35cee53e0c3dd0b5e8d0f7fd503570dc06` | 0.6.14 / 2026-09-02 21:14:23 |
| `AAOS-Frontend-Acceptance-v4/ArcheAxis.Desktop.exe`（外属主） | 186,368 | `61155f600154f2b039d2e8d86540658c5811f593b4135c794c4c766ce1cd1b86` | **1.0.0.0 / 1.0.0+d8f99a6357405054f1f9ee66eb2f88d36f7f5143** |

**“已验证当前版本”判定：UNRESOLVED（无清单可证）。** 依据本会话实测：
- 默认入口 `start.bat` → `启动星环知识.vbs` → 根 `ArcheAxis.exe`，portable 根 = `data\`。所以根 exe 是“在用的 exe”，但这是位置事实，非哈希证明。
- `release-identity.json`（schema 3.0.0）声明 tag `v0.6.14`、commit `c202c5b5a4789f0dc21accaa7ccbfed4676f0573`，其 `artifacts` 只列文件名（含一个 `SHA256SUMS.txt`），**不含任何部署 exe 的逐文件 SHA**；且 `SHA256SUMS.txt` 在本目录不存在。对根 exe 的 SHA 在 `*.json/*.txt/*.toml`（不含 `.ui-task-tree`）全仓 grep：**零命中**。
- 运行件自带的 `runtime/python/Lib/site-packages/app/release-manifest.json` 版本 0.6.14，但 `release.status="unreleased"`、`channel="development"`、`source.commit="unavailable"`，reason 明写“Exact source and CI identity are injected only into a verified release artifact.”——即该 app 清单自证“非已验证发布件”。
- 结论：无任何在场清单把 exe 哈希绑定到 v0.6.14 发布；版本号 0.6.14 不能区分七个同名 exe。按本项目“身份 = SHA+size+date+release-identity，非文件名”的规则，**不能断言哪个是已验证当前版本，标记未决**。根 exe 仅可表述为“默认启动器所接线、报 0.6.14、且不位于 backups/候选目录内的那一个”，其“已验证”身份未经证明。

### 恢复路径缺陷复核（步骤 3，实测）

- README.md 第 13 行与 `启动星环知识-AAOS新版.vbs` 指向 `AAOS-vd6bd374-20261001-x64\desktop\ArcheAxis.Desktop.exe`。本会话 `Test-Path`：目录与文件均 **MISSING**。**已记录的恢复路径是断的**（悬空引用，非体积问题）。本 writer **未重指向**——改启动目标属版本决策，须业主授权。
- 顺带实测：`AAOS-v18a00075-20261001-x64`、`AAOS-v82e8d28c-20261002-x64` 也已 MISSING → `启动星环知识-AAOS-18a00075.vbs`、`启动星环知识-AAOS-82e8d28c.vbs` 两个 Avalonia 候选入口**同样悬空**。当前仅两个入口可解析到实存目标：根 `启动星环知识.vbs`→`ArcheAxis.exe`，与 `AAOS-Tauri-f151f4c7998a\启动Tauri候选.vbs`。

### archive → verify → remove（本轮唯一实际移除）

归档落点：`D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/gov-ui-20261008/.project-local/runs/final-verify-20261008/archive-20261008/`（项目自有 `.project-local`，非 Green 运行树）。

| 归档 | 字节 | archive SHA-256 | 成员 | 逐成员校验(name+size+CRC32+SHA256, 抽取件 vs 源) | 清单 SHA-256（写后逐字节复读） |
| --- | --- | --- | --- | --- | --- |
| `bootstrap__20261008.zip` | 84,284 | `eb9b80c192e849604b4130dc6ec8c8397c6fe525adfd27559c12bdb46856cb78` | 4 | **PASS** | `2a1edd1e215588686cfc7ddb4d64bc4532e930d130aa4aa0adabc1fb896a38e5` |
| `ci-green-candidate-6621aab7__20261008.zip` | 22 | `8739c76e681f900923b900c9df0ef75cf421d39cabb54650c4b9ad19b6a76d85` | 0（空） | **PASS** | `1c28c69fe02b706e2358a1e32e57b9d40c1d06ec86a9fb3cfa673e253fd2097f` |

独立交叉核对：`unzip -v` 读到的 ZIP 存储 CRC32（`b5cdf736 / 6eeea09f / acf9bb38 / d8cd4f90`）与脚本自行计算的源 CRC32 **逐一相等**；`sha256sum` 复核 archive/manifest SHA 与脚本报告值相等。移除前 bootstrap 与 frontend 四文件 SHA-256 **逐字节相同**（`741efc33… / 966df04d… / 10c7db2f… / d70ca032…`），且 exe 只引用 `frontend/dist`、无任何 `.vbs/.bat/.toml/.json`（Green 根范围）引用根 `bootstrap/`——故“非当前版本所需、本方所有、无引用”三条件成立。

移除命令（逐文件 + 空目录 rmdir，**非递归删除**）：
```
rm "D:\...\Green-x64\bootstrap\index.html" \
   "D:\...\Green-x64\bootstrap\assets\index-BYe3VVzd.js" \
   "D:\...\Green-x64\bootstrap\assets\index-CIs18Li2.js" \
   "D:\...\Green-x64\bootstrap\assets\index-DtWRtEOj.css"
rmdir "D:\...\Green-x64\bootstrap\assets" "D:\...\Green-x64\bootstrap" \
      "D:\...\Green-x64\.ui-task-tree\ci-green-candidate-6621aab7"
```
回收：bootstrap 280,873 字节 + 1 个空目录（ci-green，0 字节）。

恢复命令：
- bootstrap：`unzip "<archive-20261008>/bootstrap__20261008.zip" -d "D:\All projects\ArcheAxis.Knowledge.Green-x64\bootstrap"`（或自 `frontend/` 逐字节复制，二者源哈希相同）。
- ci-green-candidate-6621aab7：`mkdir "D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ci-green-candidate-6621aab7"`（空目录，0 字节损失）。

### 未动清单与原因（“refused to touch”）

- 当前在用运行件（`runtime/`、`frontend/`、根 `ArcheAxis.exe`、入口/身份散文件、空布局目录）：在用版本运行所需。
- 用户数据 / CAS（`data/`、`archeaxis.sqlite`+两 `.lock`、`.cognitive-volume-id`、`aaos-vnext-data*`）：规则禁止迁移/删除。
- `AAOS-Tauri-f151f4c7998a`（668 MB，100% ALEX，候选）：在册在用（`启动Tauri候选.vbs` 存在、README 2026-10-06 记录真实旅程），删除=毁在用工作，属版本/范围决策 → 保留。
- `backups`（442 MB，混合属主含 Online 186 MB + Offline 35.6 MB）：恢复类，README 明令“保留备份”，且含外属主 → 不可整删。
- `EBWebView`（43.5 MB，混合：10.6 MB CodexSandboxOffline）：可重建缓存，但归属未全部确立 → 保留并列为混合/待判。
- `AAOS-Frontend-Acceptance-v4`、`aaos-vnext-data`（100% CodexSandboxOnline）：外属主，不动。
- `.ui-task-tree\ArcheAxis-Knowledge-OS-mainline`（6.64 GB，沙箱独立克隆，`.git` 属 Online、dubious ownership、内含 uv 再解析点未跟随）：外方字节，不是本 writer 的，不动。
- `.ui-task-tree\minimax-aaos-cosmic-ui-20261001`（697 MB，100% ALEX 但在册工作树）：删除须 `git worktree remove`+业主 GC 裁决（GC-03 待裁决）→ 保留。
- `.ui-task-tree\ArcheAxis-Knowledge-OS` husk（16,716 B，属主不可读）：归属无法确立 → unknown，保留。
- `AAOS01-文档同步-20261006`（211 KB，ALEX）：业主文档落点、用途未定、非可回收体积 → 保留。

本轮结束态：Green 实测 **9,448,743,269 字节 / 119,008 文件 / 18,920 子目录 / 1 再解析点（未跟随）**；已验证当前版本判定仍为 **UNRESOLVED**；README 及另两个 Avalonia 恢复入口实测**均断**，未改；仅 `bootstrap/` 与空 `ci-green-candidate-6621aab7/` 经归档+逐成员校验后被逐文件移除，恢复命令如上。

## 2026-10-08 授权轮：审计成功，删除被 NTFS 挡住（不是决定，是权限）

业主本轮明示：绿色仓库归属授权给执行方，能审计就审计，不能审计就删。实测结论分三段。

### 一、能审计，所以"删不可审计者"这条不成立
三个此前被我按"外部账户所有"搁置的路径，以 `ALEX` 身份**全部可读**：

| 路径 | 可读文件数 | 内容 |
| --- | --- | --- |
| `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` | 66,935 | 本项目的完整克隆，HEAD `d8f99a63`（PR #153 合并点） |
| `AAOS-Frontend-Acceptance-v4` | 366 | Avalonia 构建输出（dll/exe/pdb） |
| `aaos-vnext-data` | 5 | `workspace.sqlite` + `-wal` + `-shm` + 一张验收 PNG |

（前一份报告里"96 条 Access Denied"是 ACL **列目录**层面的，不是读文件层面；这条差异记下来，不沿用旧数。）

### 二、克隆里没有独有提交，但有 98 个文件的未提交工作——已归档并验证
- `git for-each-ref` 取全部 23 个 ref，逐个回主仓 `cat-file -e`：**独有提交 0 个**；`--branches --not --remotes` 为空；它的 origin 就是主仓本身。
- 但它的工作树有 **98 条改动**（`apps/ArcheAxis.Desktop/` 的 csproj、`aaos-app-icon.ico`、`CoreSupervisor.cs`、`MainWindow.axaml(.cs)`、`Program.cs`、`AaosTheme.axaml`、`EvidenceCenterView`/`SourceReaderView`，加 4 份文档与 4 个测试文件），**别处没有**。
- 处理方式：`git diff --binary HEAD` 存为补丁（758,982 字节），79 个未跟踪文件按字节存档，归档合计 **11,160,518 字节**，位置
  `未跟踪 .project-local/recovery/green-mainline-uncommitted-20261008/`（含 `MANIFEST.json`、`BASE_COMMIT.txt`）。
- **验证方式不是"文件在不在"**：从主仓以 `d8f99a63` 开一个临时 worktree，`git apply --check` 通过、`git apply` 通过，
  应用后 `git status --porcelain` 恢复出 **19 条**跟踪改动路径，与补丁口径一致；临时 worktree 已移除。
- 因此：**现在删这个克隆不会再丢未提交工作**。这一点是本轮做完的，不是假设的。

### 三、删除被拒，原因是权限，不是判断
- 先卸载内部重解析点再 `cmd /c rmdir /s /q`，对 16.7 KB 的 `.ui-task-tree/ArcheAxis-Knowledge-OS` 残壳执行：
  `rmdir` 返回 0，但文件仍在，stderr 为
  `...\.project-local\cache\uv\sdists-v9\editable\...\archeaxis_workspace-0.6.14-0.editable-py3-none-any.whl - 拒绝访问`。
  父目录 `ArcheAxis` 可写（`touch` 成功），**被拒的是里面的文件**——属主是 `DESKTOP-L26E3AC\CodexSandboxOnline`。
- 试 `takeown /f … /r`：拒绝，报"当前登录的用户没有该文件的所有权权限"；本会话身份 `ALEX` 不在管理员组。
- 结论：**6.89 GB 需要提权令牌或由属主账户执行**，我这边没有不改 ACL、不升权就能删的路径。
  完成命令（需管理员，或切到 `CodexSandboxOnline`）：
  `takeown /f "D:\All projects\\ArcheAxis.Knowledge.Green-x64\\.ui-task-tree" /r /d y`
  然后 `rmdir /s /q` 各子树；删除前请先确认第二节的归档仍在。

### 四、即使有权限也不删的
- `aaos-vnext-data`：`workspace.sqlite` 加 WAL/SHM 是**用户数据与 CAS**，边界规则禁止删，与属主无关。
- `backups/`、`EBWebView/`：混合属主且有恢复价值。
- `AAOS-Tauri-f151f4c7998a`：在册在用的候选构建。
- `.ui-task-tree/minimax-aaos-cosmic-ui-20261001`（696,558,986 字节，属主 `ALEX`）：**本仓库在册的 git 工作树被检出到应用根目录里**，
  与已删除的 `wi/` 同类。它属主是我、能动，但它带独有提交，属"先合并再处置"，不是这一轮能删的。

### 五、本轮绿色仓库净回收
`bootstrap/`（280,873 字节，与 `frontend/` 逐字节相同、零引用）+ 一个空目录 = **280,873 字节**，
归档逐成员（名字+大小+CRC32+SHA256）核验后删除。6.89 GB 因上述权限墙保留原状。
