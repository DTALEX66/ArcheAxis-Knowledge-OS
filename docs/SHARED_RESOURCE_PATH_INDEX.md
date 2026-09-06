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
- [当前交接](authority/taskpack-0906/HANDOFF.md)
- [DeepSeek 全量低风险工程执行包](authority/taskpack-0906/DEEPSEEK-BULK-EXECUTION-2026-09-07.md)

登记根路径不是授权读取全部内容；不得由此扩大到真实用户数据迁移、共享库清理或私有代理状态访问。
