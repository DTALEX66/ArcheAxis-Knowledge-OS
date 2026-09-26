# ArcheAxis 本机共享资源与数据路径索引

> 本项目本机资源路径的唯一登记入口。来源：用户 2026-09-07 明确指定；路径不是猜测、扫描推断或旧任务包默认值。
> 本文件登记执行时如何找到资源，**不修改产品运行配置，也不证明软件已经读取这些路径**。配置文件、环境和启动参数仍遵循配置权威索引。

## 固定路径与职责

| 资源 ID | 用户确认的绝对路径 | 职责 | 操作边界 |
| --- | --- | --- | --- |
| `shared_models` | `D:\All projects\Model library` | 多项目共用本地模型库；转换优先用现有本地模型，GPT 辅助审计 | 使用前核实项目指定模型/profile；不因本项目任务重组、清理或重复下载共享权重 |
| `shared_tools` | `D:\All projects\OS External Configuration` | 多项目共用外置工具链/工具资源库，不是本项目，也不是 WORK-LAB | 先在明确工具目录定位需要的程序；禁止复制整库到项目或修改其他项目配置 |
| `green_application` | `D:\All projects\ArcheAxis.Knowledge.Green-x64` | 本地现有绿色版本软件位置 | 保留现有软件和数据；本轮 DP 不替换、不清理、不启动它做测试、不发布新版本 |
| `green_material_library` | `D:\All projects\资料库` | 用户说明的绿色版本已设置资料库，属于真实产品资料 | 不是测试临时目录、不是缓存、不是 ceshi；本轮仅登记/核实路径元数据，不读取内容、不写入、不清理、不迁移 |
| `project_test_corpus` | `D:\All projects\ceshi` | ArcheAxis 专属测试学习资料库/学习资料副本 | 测试按已授权的精确样例范围只读消费；保留原件，输出进项目 `.project-local`；不上传资料正文或复制进 Git |

项目源码根：`D:\All projects\ArcheAxis-Knowledge-OS`。
开发产物：由 `scripts/runtime/dev.py` 管理 `<repo>/.project-local/` 中的 worktree/run 路径。
已核实的工具链子目录：`D:\All projects\OS External Configuration\10-toolchains`。它是 `shared_tools` 的子目录，不是第六个相互竞争的工具库。

## 2026-09-23 AAOS 前端构建工具链与 Candidate 记录

本节只记录本次实际调用的路径与可复核元数据；外置工具链和缓存不复制进本项目，Green 目录不因本记录被覆盖。

| 资源 ID | 精确路径 | 现场读回 | 用途/边界 |
| --- | --- | --- | --- |
| `shared_dotnet_sdk` | `D:\All projects\OS External Configuration\10-toolchains\dotnet\dotnet.exe` | .NET SDK `10.0.400`，Host/Runtime `10.0.11` | AAOS `net10.0` Avalonia 构建；会话级显式调用，不修改系统 PATH |
| `shared_aaos_ui_python` | `D:\All projects\OS External Configuration\10-toolchains\python\venv-aaos-ui-312\Scripts\python.exe` | CPython `3.12.13`，pytest `9.1.1`；独立 AAOS UI 测试环境 | AAOS 桌面/Candidate pytest；隔离于既有失效 uv trampoline 环境，不写入项目、用户 Home 或 Green |
| `shared_nuget_cache` | `D:\All projects\OS External Configuration\60-cache\nuget` | 已恢复 AAOS Avalonia `12.1.2` 与 DiagnosticsSupport `2.2.3` 依赖 | 共享依赖缓存；不提交缓存内容，不清理其他项目包 |
| `aaos_frontend_candidate` | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates\ArcheAxis.Knowledge.Green-va64788c4-x64` | 225 files / 216,503,711 bytes；self-contained win-x64 publish exit `0` | Avalonia Desktop built from source HEAD `a64788c4a7087c452db31df15ef733d6ad2ae353`；isolated Candidate, not Green installation |
| `aaos_frontend_executable_sha256` | Candidate 内 `ArcheAxis.Desktop.exe` | `9AC4ECA515CF0DEAD3F530FF75199FD1FAAE06484E6B25E31A74F91DD5ED9393` | Candidate readback；需继续经过 staging、Owner Gate、备份、替换和回滚验收 |

## 2026-09-24 Rust / Windows Native Build Toolchain Readback

The statements below describe the earlier toolchain investigation snapshot. Current exact-source-SHA verification and Candidate evidence are recorded in the 2026-09-24 continuation section that follows.

| 资源 ID | 精确路径 | 现场读回 | 用途/边界 |
| --- | --- | --- | --- |
| `shared_cargo` | `D:\All projects\OS External Configuration\10-toolchains\cargo\bin\cargo.exe` | Cargo `1.97.1` | 通过 `scripts/runtime/dev.py` 执行；Rust MSVC target |
| `shared_rustc` | `D:\All projects\OS External Configuration\10-toolchains\cargo\bin\rustc.exe` | rustc `1.97.1` | 与 Cargo 同一 stable MSVC toolchain |
| `shared_rustfmt_home` | `D:\All projects\OS External Configuration\toolchains\rust\rustup` | `rustup show home` 实际返回；组件安装前只有 cargo/rust-std/rustc | 位于共用外置库根下，但不在 `10-toolchains` 子目录；不要误报为 Cargo 丢失 |
| `shared_rustfmt` | 由上述 rustup home 管理的 `stable-x86_64-pc-windows-msvc` toolchain | 本轮按官方 rustup component 管理安装 `rustfmt 1.9.0-stable (8bab26f4f6)`；`cargo fmt --version` 回读通过 | 不复制代理 EXE 或整个 toolchain；可用于 Rust formatting gate |
| `shared_msvc_environment` | `D:\All projects\OS External Configuration\10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat` | 文件存在；初始化后 `link.exe` 解析到 MSVC `14.44.35207` Hostx64/x64 | MSVC 本体存在；本次通过项目 dev runner 的 Cargo linker 环境仍未成功验证 |
| `windows_sdk_26100` | `C:\Program Files (x86)\Windows Kits\10` | `10.0.26100.0` 的 `Windows.h`、UCRT header、x64 `kernel32.lib`/`ucrt.lib`、`rc.exe` 精确路径元数据存在 | 当前在系统 SDK 根，不在外置共用库；`vcvars64.bat` 未回读出 `WindowsSDKVersion`，`rc.exe` 也未进入其 PATH。是环境绑定缺口，不应误报为 SDK 未安装或擅自重复下载 |

本轮 Rust `source_jobs_api` 测试仍为 `NOT_VERIFIED`：直接调用时缺少 MSVC linker 环境；通过 `vcvars64.bat` 的受管调用遇到进程环境/launcher 传递问题，尚未形成 Cargo 测试 PASS。Avalonia Debug build 已使用外置 .NET SDK `10.0.400` 成功，239 项受影响 Python 合同通过。Native GUI automation/readback tooling 仍未形成可用的受支持窗口接管与 UIA 验证链；不得用静态合同替代。

本次构建证据：外置 SDK `.NET 10.0.400` Release self-contained `win-x64` publish 通过；桌面导航与路由无参数静态合约 `182 passed`；Debug build 为 `0 warnings / 0 errors`；`git diff --check` 通过。机器运行时/Launch pytest suites 在当前 Candidate Python 缺少 pytest 的情况下未执行。原生 GUI/CUA 当前无可接管窗口，截图、点击、焦点、冷启动和 Green 原位替换仍为 `UNVERIFIED`/`NOT_READY`。

## 2026-09-24 当前源码 SHA Candidate readback

| 资源 ID | 精确路径 | 现场读回 | 用途/边界 |
| --- | --- | --- | --- |
| `aaos_current_candidate` | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates\ArcheAxis.Knowledge.Green-va5de4b13-x64` | source commit `a5de4b13474c217e7a9dd34b8cbfa402e8297780`; tree `a4156ed65d50675822321b9d63eec932b1e76af3`; verifier `ok=true`, 21474 files, no problems | Exact-source isolated Candidate; not installed into Green |
| `aaos_current_candidate_zip` | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates\ArcheAxis.Knowledge.Green-va5de4b13-x64.zip` | 314318323 bytes; SHA-256 `B103452DFABDF86F54D833EEDF7E55BB7A72A44544EC76BA7FC324DB869FAA4E` | Transfer artifact; no upload/publish performed |
| `aaos_current_candidate_manifest` | Candidate `manifest.json` | 3919845 bytes; SHA-256 `4B11B6853143E48B2F24A98839639535902A5BF914FA09DEF79BBD5C6F54392B` | Manifest/provenance readback; runtime/workers required checks passed |
| `aaos_current_candidate_desktop_exe` | Candidate `ArcheAxis.Desktop.exe` | SHA-256 `8191FBF2781EC57544917831FBBC62A67A12E3B6F077FDFFD60C65B670D9B1DE` | Exact-source Desktop executable |
| `aaos_current_candidate_core_exe` | Candidate `archeaxis-api.exe` | SHA-256 `19E136F806FEEC67CC9EC7A41ED9761A23014D53B039E480F9F373D5C66449FA` | Exact-source canonical Core executable |

验证边界：本地 226 项聚焦 UI/权限合同、1 项 source-job API 测试、Desktop self-contained Release publish、Core Release build 与 Candidate manifest/runtime/workers/provenance 核验通过。全量受影响测试和 Candidate GUI Golden Journey 尚未完成；当前 CUA 没有 AAOS 窗口，首次启动、UIA、屏幕阅读器、DPI、冷重启和 Green 激活均为 `NOT_EXECUTED / UNVERIFIED`。Green 未改动。

**三个不同边界不能合并：** 绿色软件安装目录、绿色版真实资料库、项目测试资料库。严禁把测试的输出、删除或迁移动作路由到真实资料库。

## 2026-09-07 核验范围

- 以 PowerShell 7 `Get-Item -LiteralPath` 查询上述五个根目录及 `10-toolchains`：均存在，均为目录；所查项目的 LinkType/Target 均为空，Attributes 无 ReparsePoint。
- 查询共同父目录 `D:\All projects`：为普通目录，未见 ReparsePoint。
- 未递归枚举库内容，未读取资料/模型/认证文件，未核验软件内部已保存配置。因此“绿色版使用资料库”是用户确认的配置事实，不是读取软件私有配置后的实测。
- 目录存在不等于具体工具可执行、模型可推理或资料可被某引擎准确转换；这些需对应能力探针和实际测试。
- 未访问 E 盘，未修改五个资源目录、系统配置或共享工具库。

## 以后每次接手的解析规则

1. 从本项目 `AGENTS.md` → `docs/CONFIGURATION_AUTHORITY_INDEX.md` → 本索引读取资源位置；不要从旧交接、旧截图、当前工作目录或 PATH 猜根路径。
2. 对本次要用的精确根/子路径做存在性、类型、父路径和 reparse 元数据检查。不跟随重定向到 E 盘/其他未知域的路径。
3. 路径缺失、不可读、子程序/模型未找到时，报告资源 ID、已检查的精确路径和错误类别；**不得自动改用同名目录、用户主目录或另一个项目**。
4. 工具/模型先复用该库中已有且明确的版本，记录实际 executable/profile；缺失时登记能力缺口，不据此擅自全局安装或换架构。
5. 本机测试读取 `project_test_corpus`，写入仅到当前项目 dev.py 分配的运行目录；默认不碰 `green_material_library`。
6. 只有用户明确更新资源映射后才修改本表；其他文档引用本表，不增另一个“默认资源根”。手交任务包可带本表路径快照，但必须声明本索引为准并在接手时重查。

## 相关入口

- [配置权威索引](CONFIGURATION_AUTHORITY_INDEX.md)
- [目录权威索引](DIRECTORY_AUTHORITY_INDEX.md)
- [文档权威索引](DOCUMENTATION_AUTHORITY_INDEX.md)
- [当前执行入口](authority/taskpack-0919-r6/EXECUTOR-START.md)
- [当前进度台账](current/R6-EXECUTION.md)
- [M0 优先级覆盖](current/M0-DIRECTION-OVERRIDE-20260920.md)

登记根路径不是授权读取全部内容；不得由此扩大到真实用户数据迁移、共享库清理或私有代理状态访问。

## 2026-09-25 dirty-working-tree Candidate with source snapshot

| Resource ID | Exact path | Readback | Purpose/boundary |
| --- | --- | --- | --- |
| `aaos_dirty_tree_candidate` | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates\ArcheAxis.Knowledge.Green-vcurrent6-20260925\ArcheAxis.Knowledge.Green-vcurrent6-20260925-x64` | base commit `a5de4b13474c217e7a9dd34b8cbfa402e8297780`; base tree `a4156ed65d50675822321b9d63eec932b1e76af3`; source snapshot `4f72520d91d295171fd4306e7ecb5d75c0598bcb36017a5e6c794cec672750b0`; verifier `ok=true`, 21,474 files | Isolated local Candidate bound to current dirty worktree inventory; not installed into Green |
| `aaos_dirty_tree_candidate_zip` | Candidate `.zip` | 298,686,214 bytes; SHA-256 `0FB51470850AAA4DFB5E0221AFE25FC7E5453871D6B85183C7E107DC027504F6` | Local transfer artifact; no upload/publish |
| `aaos_dirty_tree_candidate_manifest` | Candidate `candidate-manifest.json` | 3,920,215 bytes; SHA-256 `C7AF463B8DFA188904C3EBEC886C8BDFE1F877E14986804D61F50F9082B8A240` | Manifest file hashes and source snapshot provenance |
| `aaos_dirty_tree_candidate_desktop` | Candidate `desktop/ArcheAxis.Desktop.exe` | SHA-256 `50B524A4483BE74A924244C019CD942E24B0AB23C7A79F344C49351FAAE2C42B` | Current-source self-contained Desktop |
| `aaos_dirty_tree_candidate_core` | Candidate `core/archeaxis-api.exe` | SHA-256 `E7C91DC8DE1AA0A6885E4F77A735892F6F8B67685F67299EFE5126AF48520085` | Current-source canonical Core |

Candidate learning smoke passed with synthetic content, persisted answer and FSRS readback after Core restart; `Mastery closed=false`. Native GUI acceptance and all Green installation gates remain open.
