# AAOS Desktop 启动稳定性回读（2026-10-01）

状态：`PARTIAL / TESTED_LOCAL`。本记录只涉及项目内合成 SQLite 工作区；不代表绿色版安装或全页面验收。

## 真实 Windows 崩溃证据

- Application EventLog `.NET Runtime` 1026，2026-09-26 23:06:51：旧候选 `archeaxis.desktop.exe` 抛出 `System.InvalidOperationException: ResourceInclude.Source must be set`，栈定位 `ThemePalette.Apply`（当时源码第 25 行）；配对 `Application Error` 1000 为 `0xe0434352`。
- Application EventLog `.NET Runtime` 1026，2026-09-26 23:37:27：绿色版 `.ui-task-tree` 旧候选抛出 `System.NullReferenceException`，栈定位 `MainWindow.OnThemePaletteChanged`（当时源码第 1100 行），由 XAML `SelectionChanged` 在 `EndInit` 中触发；配对 1000 事件将出错可执行文件定位在绿色版旧验收目录。历史文档已记录对应修复，但不能将旧事件当作最新源码的无崩溃证明。

## 本次隔离运行

- 旧 Debug DLL：`D:/All projects/ArcheAxis-Knowledge-OS/.project-local/build/dotnet/ArcheAxis.Desktop/bin/Debug/net10.0/ArcheAxis.Desktop.dll`，SHA-256 `A85ACD7DA0D0002DE21918161CB572275C95E6CC890560DD9C9D51C0823E0804`，构建时间为 2026-09-30。当前 Core：`.project-local/build/cargo/debug/archeaxis-api.exe`，SHA-256 `EA09B3B4270FA425EB768B030FD3B37C8A7EFCEC3E3FAD00703A29473734ADFE`。
- 项目 `.venv/Scripts/python.exe` 的 uv trampoline 被权限拒绝；使用现有共享 Python 3.12 直接调用 `scripts/launch/desktop_launch.py --fresh-workspace`。Debug apphost 要求 .NET 10.0.12，本机旧共享运行时为 10.0.11；因此使用已存在的 SDK 10.0.401 `dotnet.exe` 启动 DLL，未安装依赖或修改系统配置。
- 对当前工作树，经 `scripts/runtime/dev.py` 使用 SDK 10.0.401 重建 Debug，构建退出 0、0 error、1 个 NU1900 NuGet 漏洞索引不可达警告。新 DLL：`.project-local/build/be268a2d33/dotnet/ArcheAxis.Desktop/bin/Debug/net10.0/ArcheAxis.Desktop.dll`。第一次构建 SHA-256 `0CF2D36EF098E49B3D44EC8FE39985E3302B2BB6F611CAE0CC4B75E6D42537D7`；加入 CoreSupervisor 安全诊断和 capture 释放修复后再次构建的 SHA-256 为 `8B46166F536BAFFCE3AC0E31B368B6AA722BCA84E856E114B50149470EC29275`。
- 新 DLL 与上述 Core 在 `desktop-launch.json` 收据指定的全新合成工作区执行 `--smoke`：exit 0，`owned core handshake ok`，SQLite 4096 字节。原生 `--ui-capture home 1280 900 aurora` 且 `AAOS_UI_CAPTURE_WAIT_CORE=1`：exit 0，PNG 169282 字节，画面显示 Core 回应、空 Evidence 结果。收据与图片位于 `.project-local/runs/be268a2d33/02004f01ad9b/artifacts/desktop-launch/71504b7863b5455e834771da21aac29e/`。

## 本次普通 GUI 的启动失败及修复方向

原生 capture 分支在 `MainWindow.OnLoaded` 完成截图后直接 `Environment.Exit(0)`。该路径绕过 `CoreSupervisor.Dispose`，遗留本次合成工作区的 Core 子进程和 `workspace.sqlite.writer.lock`。随后的普通 GUI 在同一个合成工作区显示 `core offline`；诊断后的 Core stderr 分别为 `failed to initialize execution workspace`（传递文本 worker）或 `failed to open workspace`（无 worker）。这不是 9 月 26 日两次 UI 初始化异常，也不是仅凭错误码作出的推测。

只终止本次测试所生、路径精确匹配 `.project-local/build/cargo/debug/archeaxis-api.exe` 且启动时间对应 capture 的 PID 23120、30712 后，同一合成数据库、完整 worker profile 的普通 GUI 显示 `星环知识平台 — 已连接`，保持运行，关闭窗口后 exit 0，Core 随之退出。诊断收据 `normal-startup-diagnostic.txt`、成功回读 `normal-startup-readback.txt` 位于上述隔离目录。

修复已由 MainWindow 写集 owner 在 capture 分支加入 `try/finally` 释放 owned Core。`CoreSupervisor.cs` 新增的启动 stderr 诊断只允许前四条已知的固定 Core 错误类别进入 UI；其他原始输出统一标为 `unclassified Core startup error`。该机制不记录 launch token，也不读取绿色版真实数据库。

修复后再次使用全新合成数据库（收据目录 `.project-local/runs/be268a2d33/f5f5cc6b06db/artifacts/desktop-launch/2c083e046109472993d1fac1bec8dd09/`）：`--ui-capture home 1280 900 aurora` 且等待 Core，exit 0、PNG 169282 字节；截图退出后同一路径的 Core 进程数为 0。随后正常 GUI 使用该数据库和完整 worker profile，窗口标题 `星环知识平台 — 已连接`，保持运行；关闭后 exit 0、Core 进程数为 0、SQLite 文件 4096 字节。此回读证明本次合成场景的锁不再残留，不证明长期运行或真实用户库。

限制：未在绿色版根目录安装或运行新构建；未证明所有页面、主题、DPI、长期稳定性或真实用户库闭环。此次运行的 Desktop 与 Core 均在项目开发构建目录中，合成工作区位于 `.project-local`。

## Green `.ui-task-tree` mainline 候选回读

目标为 `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline`，HEAD `d8f99a6357405054f1f9ee66eb2f88d36f7f5143`，存在事先的前端未提交修改。只将 `CoreSupervisor.cs` 的同一小补丁经 `git apply --check` 后应用到该文件；没有整文件覆盖或改绿色版根目录。该候选与 Formal 源码不完全相同，单独记录。

在该工作树的 `scripts/runtime/dev.py` 下，首次 `dotnet build --no-restore` 因缺 `project.assets.json` 报 `NETSDK1004`；项目本地 `dotnet restore --ignore-failed-sources` 成功后重建 Debug：exit 0、0 error、1 个 NU1900 警告。DLL 位于该工作树 `.project-local/build/8af23851c3/dotnet/ArcheAxis.Desktop/bin/Debug/net10.0/ArcheAxis.Desktop.dll`，SHA-256 `58D1AEBE85B6C6BDB30230EEAA335C5C9E3A1070D07BD0664106B868A4D10799`。

此工作树没有当前 Rust Core 构建产物；为了只做合成验证，将 Formal 的 Core exe 按 SHA-256 相等回读后复制至该工作树 `.project-local/build/8af23851c3/cargo/debug/archeaxis-api.exe`。来源与目标 SHA-256 均为 `EA09B3B4270FA425EB768B030FD3B37C8A7EFCEC3E3FAD00703A29473734ADFE`。标准 `desktop_launch.py --fresh-workspace` 的资源 preflight 因 `resource index drift or missing entry: shared_models` 阻断；未更改资源索引。改以显式环境变量和该工作树 `.project-local/runs/green-stability-manual-20261001/` 中的合成数据库与 worker profile 运行 DLL。

Green mainline `--ui-capture home 1280 900 aurora` 且等待 Core：exit 0、PNG 171299 字节，截图 `.project-local/runs/green-stability-manual-20261001/home-green.png`；capture 后该 Core 路径进程数 0。同库、完整 worker profile 的普通 GUI 窗口标题 `星环知识平台 — 已连接`，关闭 exit 0、该 Core 路径进程数 0、SQLite 4096 字节。此时标准 launcher preflight 尚未修复；其后续修复见下一节。

## Green 标准 launcher preflight 修复与再次回读

Green mainline 的旧 `scripts/maintenance/check_resource_boundaries.py` 将资源根推为当前 checkout 的父目录。嵌套在 `.ui-task-tree` 后，该目录不再是共享资源父目录，造成 `shared_models` 假性 drift。对照 Formal 已验证的 `62f23189`，仅在 Green 脚本加入资源索引绝对路径解析及 E/F/UNC、相对路径、重复项拒绝，并在该树 `tests/maintenance/test_check_resource_boundaries.py` 增加嵌套 checkout 和无效路径回归。定向测试 `9 passed, 1 warning`，警告为现有 pytest `cache_dir` 配置项。

Green 标准 `scripts/launch/desktop_launch.py --fresh-workspace` 再运行成功，收据状态 `PREPARED_NOT_LAUNCHED`、`resource_boundary_target=project_test_corpus`；收据位于 `.project-local/runs/8af23851c3/912b437881c1/artifacts/desktop-launch/261188db9715465aa949047da9d3a397/desktop-launch.json`。从该收据读回全部隔离环境变量，使用共享 SDK 10.0.401 `dotnet.exe` 启动相同 Debug DLL：`--ui-capture home 1280 900 aurora` 且等待 Core，exit 0、PNG 171299 字节；capture 后 Core 进程数 0。同库完整 worker profile 的普通 GUI 标题 `星环知识平台 — 已连接`，关闭 exit 0、Core 进程数 0、SQLite 4096 字节。截图为同一收据目录下 `home-standard-preflight.png`。标准脚本的 `--launch` 仍调用 Debug apphost；本机未安装其要求的 .NET 10.0.12 系统运行时，故实际 GUI 用 SDK host 启动 DLL。Green 根目录安装仍未执行。

## Green self-contained Release EXE

现有 Green mainline `ArcheAxis.Desktop.csproj` 对 Release 声明 `RuntimeIdentifier=win-x64`、`SelfContained=true`。使用 `scripts/runtime/dev.py` + 共享 SDK 10.0.401 在该工作树 `.project-local` 执行 `dotnet publish --configuration Release --runtime win-x64 --self-contained true`：exit 0，NU1900 漏洞索引网络警告。发布目录为 `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline/.project-local/build/8af23851c3/dotnet/ArcheAxis.Desktop/bin/Release/net10.0/win-x64/publish/`；`runtimeconfig.json` 声明 `includedFrameworks` 中的 `Microsoft.NETCore.App 10.0.12`。EXE SHA-256 `6077437EEF832EC193CAC2537356D26CBA41B0D6596F97357A1A17F6A692867B`，DLL SHA-256 `40C22D1C664194C85E73DF2D9A0EFA26CE17E8C265D24DE9D15C6AB548289241`，测试所用 Core SHA-256 `EA09B3B4270FA425EB768B030FD3B37C8A7EFCEC3E3FAD00703A29473734ADFE`。

以标准 `desktop_launch.py --fresh-workspace` 为该发布 EXE 创建全新合成环境收据：`.project-local/runs/8af23851c3/509a8713acf4/artifacts/desktop-launch/c4179d45cdab401eb498f552a01a70f8/desktop-launch.json`。直接运行 EXE 自身，移除进程环境中的 `DOTNET_ROOT` 后，原生 Home capture 产出 `home-release-exe.png`（182251 字节，SHA-256 `931205A3D4B6F1C3C99BD680900B5851F31E8328B6412425F15230AD145B769C`）；WinExe 的 PowerShell 调用为异步返回，不能从空白 `LASTEXITCODE` 推断退出码，随后回读 PNG 与进程状态。普通 GUI 的独立启动保持运行，窗口标题 `星环知识平台 — 已连接`；正常关闭 exit 0，发布 EXE 与该 Core 路径的进程数均为 0，合成 SQLite 4096 字节。这排除了该 self-contained EXE 在本机依赖系统 .NET 10.0.12 才能启动的疑点，仍未证明绿色版根目录部署或其他机器运行。

同一 Release EXE 的后续原生双尺寸回读：标准 launcher 新收据 `.project-local/runs/8af23851c3/ca74e323aed2/artifacts/desktop-launch/51fa9c9a31d24d0fb4a1ca6d62ee3a73/desktop-launch.json`。`--ui-capture home 1280 900 aurora` 与 `720 900 aurora` 各经 `Start-Process -Wait` 返回 exit 0，PNG 分别 184774 与 100105 字节，截图为同一收据目录的 `home-1280.png` 和 `home-720.png`。目视回读：1280 DIP 下 Memory Graph 与节点详情双列并排；720 DIP 下首页卡片单列且底部移动导航出现，Graph 位于首屏以下。两次退出后该 Core 路径进程数 0。

## 完整候选包输入评估

`scripts/release/assemble_green_candidate.py` 可将 `desktop`、Core、可选独立 `runtime` 与 `workers` 组包，并生成根目录启动 VBS；严格 `verify_green_candidate.py --require-runtime --require-workers` 要求完整运行时与 worker。当前 Green mainline 有新编译的 self-contained Desktop、从 Formal 当前开发构建按哈希复制的 Core、以及源码中的 worker 脚本，但该工作树没有已核实的独立 Python runtime 包。现用共享 `venv-aaos-ui-312` 是依赖外部 base Python 的 venv，`importlib.util.find_spec('fsrs')` 为 `None`；它不能作为完整绿色包的 `runtime/python.exe`。共享 base CPython 3.12.13 的 `Lib/site-packages/fsrs` 不存在。没有从历史候选目录复制来源不明的 runtime，也没有生成一个会让严格 verifier 误以为完整的候选包。因此完整组包、严格 verifier 和候选原位 EXE 无开发环境变量启动均为 `BLOCKED / NOT_EXECUTED`，缺口是有来源与依赖证明的独立 Python runtime（含 FSRS 等项目所需包）。
