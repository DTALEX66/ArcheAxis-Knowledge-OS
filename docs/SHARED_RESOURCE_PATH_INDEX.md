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
