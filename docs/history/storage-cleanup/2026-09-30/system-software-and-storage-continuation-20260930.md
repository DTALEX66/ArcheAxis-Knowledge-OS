# C/D 系统软件与 AAOS 存储清理续审 — 2026-09-30

> 历史多轮审计记录：下文各“本轮/当前/最新”仅指对应记录阶段，不能作为 2026-10-01 实时状态。VS Code 缺失登记已由本文记录的签名安装及静态回读关闭，GUI/runtime 仍 `UNVERIFIED`；最新存储状态应查当前清理交接。E/F 容量元数据越界事件保留于下文，不声明整个执行期间从未访问 E/F。

## Latest read-only software inventory

- **C:** 29 C-linked uninstall entries and 96 current-user AppX packages were observed. Representative signed components included Chrome 154.0.8037.58, Edge/WebView2 154.0.4258.37, Weixin 4.1.13.65, Logitech 39.1.2 and Visual Studio Installer 4.8.60.55523. This is a sampled inventory, not proof that every C application is healthy. Photoshop 26.7.0.15 and Illustrator 29.5.1 still report Authenticode `HashMismatch`; official Adobe repair/reinstall and signature recheck remain required. `C:\Program Files\KMSpico` is present; its KMSELDI executable has `UnknownError` signature status. Treat it as untrusted until Microsoft/approved endpoint scanning and the licensed activation path are confirmed; do not infer malware from signature status alone. Defender reports `Not running` while Windows Security Center lists 360 and Defender; verify 360 protection/freshness in the vendor UI. Elevated DISM returned 740, so fresh system-file verification remains unverified. Event logs include unexpected shutdowns, Intel service startup errors and Codex update error `0x80073D02`.
- **D:** 16 D-linked uninstall registrations were observed. The missing VS Code user installation was repaired with Microsoft's official 1.131.0 signed installer at its recorded path `D:\Programs\Microsoft VS Code`; installer exit code 0, post-install Authenticode `Valid`, file/product version and HKCU registration all match 1.131.0. An audit launch unexpectedly restored a window; it was closed, so the app's GUI runtime is still `UNVERIFIED`. Installer/log cleanup was rejected by execution policy and these temporary files remain at `.project-local/tmp/vscode-repair-20260930/`. LibreOffice MSI install path incorrectly points into `D:\All projects\Obsidian-Assistance\Obsidian - Backend Assistance\`, where `soffice.exe` is absent. DSH Desktop registry version 2.0.5 differs from installed 2.0.13. DSH app data, games, Eagle libraries and `D:\iFontsClientFileCache` were preserved. The latter is 2,122,923,450 B under `font-cache`; no official cache-reset procedure was verified, so it may contain downloadable/licensed font material and is not deleted. Other sampled signatures were valid for major apps including Feishu 7.70.10, Steam, QQ, Eagle, Obsidian, 360 and Baidu Netdisk; version lag remains for Baidu/360. This sample does not certify all D software.
- **Scope incident:** the C subagent's initial `Get-PSDrive` returned E:/F: capacity metadata, and a later registry-driven path check queried D-path existence. It did not enumerate/read/write E:/F: contents or scan/change D contents. The subagent was stopped from further cross-scope reads. This deviation is disclosed; the root agent did not inspect E:/F: paths or contents.
- The software inventory pass itself made no repair, install, uninstall, service change or registry edit. The separate official VS Code installation and its registration readback are recorded above; this is not GUI/runtime verification. Adobe repair needs an authenticated vendor installer; fresh DISM/SFC verification requires an approved administrator context. Overall C/D software health remains `UNVERIFIED/PARTIAL`.

## 本轮只读事实

- 当前 Formal 工作树仍有大量用户 UI 修改；没有触碰产品源文件、没有 stage/commit/push。C/D 卷为 NTFS `Healthy/OK`；当前 C: 可用 262,087,462,912 B，D: 可用 173,537,624,064 B。此为卷级动态读数，不代表本项目清理回收量。E:/F: 未访问。
- `.project-local` 已有元数据库存于 `.project-local/mig/post-dotnet-dedupe-inventory-20260930.json`：状态 `partial`，成功观测到 85,974,144,668 B / 628,262 文件，491 项拒绝访问，86 个 reparse 被跳过，不能作为项目完整尺寸。单独按第一层目录只读复核的 `.project-local` 可读逻辑数据约 84,235,809,438 B / 606,691 文件（目录扫描存在 errors，口径与前项不同，不应相加或互相替代）。最大一级目录为 `build` 37,490,953,027 B、`runs` 25,038,600,852 B、`worktrees` 9,942,964,550 B、`staging` 7,328,730,703 B、`cache` 3,307,235,734 B；均为可读下界，禁止当作精确总量。
- `.project-local/build/4260083704/cargo` 的既存逐文件 manifest 有 10,109 项、4,714,734,941 B。本轮重新读回全部 10,109 个文件，大小和 SHA-256 全匹配；没有数据库/WAL/SHM/lock 或活动进程的先前审计仍适用，旧 run receipt 保留。针对这个精确目录的递归删除命令再次被执行策略拒绝，源目录仍在。未逐文件删除或换工具绕过。证据：`.project-local/mig/cargo-orphan-target-4260083704-20260930/preflight.json`；状态为 hash-verified but deletion NOT EXECUTED。
- `.project-local/build/green-candidates-r6` 的三个展开候选复核仍未完成，保留。`C:\EDTemp` 有两份未签名 SQLite DLL，各 2,166,784 B、SHA 相同；公司/产品字段为 SQLite Development Team / SQLite，归属到具体安装源未知，保留。`C:\SoftInst` 无文件，只有两个空目录。`C:\symbols` 约 24,602,104 B，包括 Microsoft 签名有效的 `ntkrnlmp.exe` 和对应 kernel PDB；属于系统调试材料，不迁入 AAOS。

## C/D 软件健康与问题

| 范围 | 证据 | 状态与下一步 |
|---|---|---|
| C:、D: 文件系统 | `Get-Volume`: NTFS Healthy / OK | PASS（卷报告状态，不等于全软件功能通过） |
| Windows 系统文件 | 同日先前 DISM RestoreHealth、SFC scannow、DISM CheckHealth、SFC verifyonly 均退出码 0 | 既有证据 PASS；本轮未重复运行 |
| Defender / 360 | Defender cmdlet 与 WinDefend 服务均显示未活动；360 的 `ZhuDongFangYu` 服务 Running/Auto，签名有效，且安全中心登记 360 | 360 主动防御组件运行证据 PASS；整体 active provider、病毒库新鲜度与全覆盖仍 UNKNOWN，需在 Windows 安全中心核实；未更改服务和安全策略 |
| Adobe Illustrator 2025、Photoshop 2025 | 两个产品主程序 Authenticode `HashMismatch`；各自抽样其他程序及卸载器有效；无恶意或篡改来源定论 | FAIL/待官方修复：在 Adobe Creative Cloud 中修复/重装后重新验签；本轮未写入软件目录 |
| ArcheAxis Desktop | Application 日志在 2026-09-26 有两起事件，异常码 `e0434352` 与 `c0000005`，模块 KERNELBASE.dll；WER 原件已复制入 Record | 故障根因和当前运行状态 UNKNOWN；归档不是修复或复现证明 |
| D: VS Code 1.131.0 | 早期快照：登记目录、`Code.exe`、卸载器缺失。后续官方安装后已回读存在、1.131.0 与 Microsoft 签名 `Valid` | 早期缺失静态发现已关闭；GUI/runtime 仍 `UNVERIFIED`，没有据此认证全部软件健康 |
| LibreOffice | D 卸载登记的 InstallLocation 指向 Obsidian-Assistance 项目源目录，不能据此把该仓库归属给软件；D 遍历不完整 | UNKNOWN；保持软件登记和项目内容不动 |
| DSH Desktop | 卸载登记程序与入口存在；目录含用户数据、备份、pnpm store、迁移资料 | 属 DSH owner，不是 AAOS 垃圾；保留，等待 DSH owner handoff |
| `D:\All` / `D:\END` | `D:\All` SQLite 主库及 WAL/SHM/lock；AAOS 精确文档引用未命中，归属未知；`END` 小型 JSON-like 文件 | UNKNOWN；禁止移动/删除 SQLite 族 |

C: WER 中两份明确属于 ArcheAxis 的 `Report.wer` 已复制到 `D:\All projects\Record\AAOS-project-archives\2026-09-30\windows-wer\`；单文件 SHA/字节回读均 PASS。迁移索引 SHA-256 为 `CB64D4B57C25BF73840BD8B0A5368982C49004398527F4E6D1C0C7DB78202985`。删除这两个 C: WER 源目录的命令被策略拒绝；原件仍在 C:，未尝试任何旁路，故源迁移回收空间为 0 B。Archive README 同目录记录路径、事件、归属与限制。

## 本轮操作状态

- 无新清理/删除；无注册表、ACL、安全服务或软件程序更改。
- 无产品构建/测试。`git diff --check` 已运行；工作树有大量既存 UI 修改与未跟踪产物，均保留。
- C/D 广义软件检查不等于每个程序 runtime PASS；当前系统存在 Adobe signature failures 与 endpoint protection UNKNOWN，故“全部软件没问题”不成立。
- 后续只对有精确可读权限、明确归属、可恢复或可重建、且能通过执行策略的目标继续做单路径操作。被策略拒绝的 C: WER、Cargo 递归清理均不通过逐文件或换 Shell 绕过。

## 并行审计补充：候选目录与缓存

- `green-candidates-r6` 的 3 个展开副本逐成员 SHA/CRC 全量 PASS，共 820,605,494 B；本轮未删除，恢复路径见本目录的 R6 候选审计与 `.project-local/mig/r6-green-expanded-dedupe-20260930/verified-recheck.json`。
- 当前源候选展开包 801,672,850 B，与保留 ZIP 的 18,247 个成员逐项匹配，CRC PASS；当前 R6 记录仍引用展开路径，因此保留。详情见 `current-candidate-expanded-dedupe-review-20260930.md`。
- 正式 `green-candidates`：`vcurrent8`（883,400,061 B）保留；既有 manifest 审计发现 sibling ZIP 比 manifest 多 225 个成员，且部分历史 runs 引用仍 UNKNOWN，不能判定与展开目录完全相同。`vcurrent13`（883,436,692 B）保留：ZIP payload 可按成员恢复，但展开树多两个空目录，且被 DSH 回读文档引用。`vcurrent6` 的 ZIP 缺 1,308 个展开文件并被当前索引引用；`va5de4b13` 为当前官方候选；都保留。无 sibling ZIP 的旧展开树没有精确归档证据，保留。
- `.project-local/cache` 可读至少 3,242,568,004 B / 47,643 文件；NuGet、UV、UV Desktop、Cargo、UV Python、pip 均被离线构建/打包/运行时引用。UV Python 是 managed CPython trampoline；先前移除会令活动解释器失效。pytest cache 路径受 ACL 拒绝读取。并行审计没有发现可证明删除安全且能精确回退的缓存，故保留且不改 ACL。
- `runs/be268a2d33` 可读下界约 17.15 GB，存在数据库 sidecar、ACL 错误及 reparse；无足够大的归档映射支持整批清理。保留。

## 追加安全状态证据

360 的 `ZhuDongFangYu` 主动防御服务为 Running/Auto，程序 v3.2.2.3110 和托盘程序 v12.0.0.2001 的 Authenticode 均 Valid，签署者为 Beijing Qihu Technology Co., Ltd.；Windows Security Center 登记了 360。Defender 服务为 Stopped/Manual，`Get-MpComputerStatus` 实时防护为 false、签名时间为空。证据支持 360 的签名主动防御进程正在运行，但不证明病毒库新鲜度/全面保护；官方建议从 Windows Security 的 Virus & threat protection → Who's protecting me? → Manage providers 确认当前 active provider（[Microsoft 支持说明](https://support.microsoft.com/en-us/windows/security/scan-an-item-with-windows-security-d1c8c01d-12ed-e768-cbb8-830ea8ccf8e6)）。本轮没有更改安全服务。

LibreOffice MSI product registration 和 `C:\Windows\Installer\5cf0725.msi` 存在，source 为 `D:\All projects\`；但 `InstallLocation` 指向 Obsidian-Assistance 源码根目录，且该路径及常见 C/D Program Files 下未找到 `soffice.exe`。项目、MSI 和注册保持原状，不擅自修复或卸载。该软件运行状态 UNKNOWN。

## 2026-09-30 后续复核补遗

以下实时复核修正或补充上文的旧快照结论，完整清理续审见同目录 `continuation-audit-blockers-20260930.md`：

- C: 360 压缩登记版本 4.0.0.1680；当前登记路径下 `360zip.exe` 与 `UnInstaller.exe` 均存在、Authenticode `Valid`，但文件版本分别为 4.0.0.1590 与 4.0.0.1130。此读回覆盖本文件早先记录的缺失判断，仍需解释版本残留。
- Adobe Illustrator 主程序实际位于注册安装目录的 `Support Files\Contents\Windows` 子目录，存在但签名为 `HashMismatch`；Photoshop 主程序同为 `HashMismatch`。二者均未修复。
- R6 三个 ZIP-backed 展开副本的复核现已完成：三份 ZIP/manifest SHA 与展开文件逐项匹配，可恢复 820,605,494 B；本轮未删除，早先递归删除仍被策略拒绝，也没有尝试替代删除方式。
- 41 条 C/D 卸载登记按主程序存在性、签名及组件边界完成分类（19 PASS / 4 FAIL / 18 UNKNOWN）；PASS 只表示静态路径/签名检查，不代表启动或 runtime 健康。分项见 `c-d-registered-software-inventory-20260930.md`。
- 另生成并验证 DSH detached commit handoff bundle（`.project-local/mig/dsh-detached-handoff-20260930.bundle`，SHA-256 `A0D70082D9E6B38D7FC3A34FF7FAB04E51BD93BA6CCD00CD8AB144B85BA2C1B9`）；DSH owner 仓库仍缺失，没有在 AAOS 建 DSH 分支。
- 当前非管理员会话的 DISM 扫描返回 error 740，SFC 输出不可可靠解码；这与此前有单独 PASS 收据的系统检查是不同时间/执行上下文。系统完整性当前应视为旧证据存在、最新状态未确认，不能声明 C 盘所有系统组件均健康。

## 2026-09-30 最新只读系统与软件复核

本节 supersede 本文更早关于 SecurityCenter2 没有 provider、D 盘登记数为 15、DSH task worktrees 属于独立 DSH backend 仓库等结论。

- C:、D: 文件卷仍报告 NTFS `Healthy/OK`，本次动态空闲空间 C: 261,992,194,048 B、D: 173,954,248,704 B。Formal 最新目录扫描为 86,561,404,232 B / 660,469 files / 256,307 dirs，1,136 次访问/枚举错误、86 个 reparse 跳过；Green 为 16,960,578,768 B / 144,040 files / 20,336 dirs、80 次错误、无 reparse。均为可读下界，不是完整磁盘占用。
- C 的 CBS 记录显示同日修复 1,506 项 corruption、操作结果 0；另一会话记录 `RepairNeeded:no` / `S_OK`。本次未执行新的管理员 DISM/SFC 验证，因此系统组件是“有成功修复日志，当前独立复验未执行”。
- SecurityCenter2 当前返回 360 Security 与 Windows Defender 两个 provider。WinDefend 为 Stopped/Manual，`Get-MpComputerStatus` 启用状态为 false、签名/扫描日期为空；360 签名组件和服务运行，但防护新鲜度与完整有效性仍 UNKNOWN。
- C Adobe Photoshop、Illustrator EXE 均继续 `HashMismatch`；未修复。事件日志包括 09-30 OpenAI.Codex 更新错误 `0x80073D02`、非正常关机 Kernel-Power 41/EventLog 6008、快速启动失败 `0xC00000D4`，以及 Intel 服务 7023/7009。
- D 盘登记清单复核为 16 条：静态 PASS 10 / FAIL 2 / UNKNOWN 4；Feishu 新增核实 PASS（7.70.10，签名有效）。FAIL 为缺失的 VS Code 登记路径和指向 Obsidian-Assistance 源树、缺少 `soffice.exe` 的 LibreOffice 路径。DSH Desktop 文件版本 2.0.13 与登记 2.0.5 不同且未签名；其他若干应用存在版本差异或无签名，详见登记表。
- 因此，当前只能说卷 metadata 健康、部分系统修复有历史成功证据、部分应用静态校验通过；不能说 C 盘全部系统/软件或 D 盘全部软件已确认无问题。

同回合清理已通过 Git worktree 生命周期移除三个干净路径：`verify-0c9c` 32,854,287 B、`dsh-governance-20260927` 41,598,549 B、`dsh-backend-r5` 354,721,074 B；均保留可达提交。治理 worktree 忽略文件 11,334 B 与 SHA 清单回执 1,335 B 已迁入 `.project-local/mig/dsh-governance-worktree-state-20260930/`。另删除已被正式 refs 冗余保护的 46,095,363 B Git bundle。毛回收 475,269,273 B；保留副本/回执 12,669 B；净逻辑缩减 475,256,604 B。动态卷空闲变化不作为归因值。准确 owner 修订见 `cross-project-owner-handoff-20260930.md`。
