# Formal 历史 run build 归档与去重 — 2026-09-30

状态：PASS（归档完整性与源路径清理回读）。完成时间：2026-09-30T00:55:30.0361820+08:00

本批限定为五个经过独立只读审计的生成构建目录。删除前重新计算完整源树清单并对照先前审计 SHA；确认没有数据库/WAL/SHM/writer-lock 文件名、reparse 或读取错误。没有修改产品代码、当前 Core、Green、用户数据库或 E/F。

总计移除 1,015 个展开文件 / 1,468,732,984 逻辑字节；四个新 ZIP 合计 423,551,386 字节。按源逻辑字节减新增档案计算净减少 1,045,181,598 字节；不是磁盘全局自由空间增量（存在 hardlink、分配粒度及其他活动）。第五组复用原有 ZIP，无新副本。

## 恢复映射

| 原始绝对路径 | 文件 / 原始字节 | 恢复档案 | ZIP 字节 | ZIP SHA-256 |
|---|---:|---|---:|---|
| `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\frontend-responsive\desktop-build-absolute` | 229 / 219127815 | `D:\All projects\Record\AAOS-project-archives\2026-09-30\formal-run-builds\frontend-responsive-desktop-build-absolute.zip` | 76522014 | `596de0dd9869725d4c7391bca466a32709614a39fc81a247dc0ea76b874df557` |
| `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\frontend-responsive\desktop-build-railfix` | 229 / 219127883 | `D:\All projects\Record\AAOS-project-archives\2026-09-30\formal-run-builds\frontend-responsive-desktop-build-railfix.zip` | 76522155 | `5a5d1c5c3fc7009aee0bfb4b34064635cb5980024790cb1c3cb985ec8d42d7f4` |
| `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\r6-a12-build` | 79 / 591288191 | `D:\All projects\Record\AAOS-project-archives\2026-09-30\formal-run-builds\r6-a12-build.zip` | 190562228 | `7b799dc6b5e88dba14433e53e50d601c4e77b0f7faa66147d65b8ec65bbbfc36` |
| `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\ui-finalbuild3` | 249 / 222330884 | `D:\All projects\Record\AAOS-project-archives\2026-09-30\formal-run-builds\ui-finalbuild3.zip` | 79944989 | `2a258308a68694a1198ea35c2df1f43407834aa199f4c1daa17c13e2b0fb0799` |
| `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\r6-a12-release` | 229 / 216858211 | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates-r6\ArcheAxis.Knowledge.Green-vr6-0e934f33-x64.zip` | 95386113 | `6ab6c5ecaeafabfcf4a91131a9f20d2510bdcf5ee0cabd31d4d844344bd2a087` |

四个新 ZIP 成员直接相对于表中的原始目录；恢复时创建该原始目录并将 ZIP 解压至其中。`r6-a12-release` 使用原有 ZIP 的 `ArcheAxis.Knowledge.Green-vr6-0e934f33-x64/desktop/*` 成员，恢复为 `r6-a12-release/Release/net10.0/win-x64/*`。恢复后根据 preflight.json 逐文件路径、长度、SHA-256 验证；重现历史运行前按当时契约重新验收。

## 验证与消费关系

- 全部 archive 成员集合、长度、SHA-256 与 source 一致；完整读取所选成员验证 CRC。四个新 ZIP 全成员经过验证；既有 ZIP 的完整 SHA 与预期一致，并对需要恢复的 desktop 子树逐成员验证。
- 删除前第二次重新读取所有源文件哈希、所有 archive 哈希、进程状态，解析后精确路径均位于 Formal `.project-local/runs` 内；使用 PowerShell `Remove-Item -LiteralPath` 删除五个指定目录。
- 删除后五个源目录均不存在；四个新档案和复用档案 SHA-256 再回读一致。
- 进程检查为可见 dotnet/ArcheAxis.Desktop/cargo/rustc 与 runs 下 executable path；未发现活动进程。不等同于受保护进程句柄穷尽检查。
- `R6-EXECUTION.md` 与 `AAOS-UI-SUITE-COVERAGE-20260923.md` 原先引用 frontend-responsive/desktop-build-absolute；`R6-DESKTOP-BUILD-20260919.json`、`R6-DESKTOP-SMOKE-20260919.json`、`R6-GREEN-CANDIDATE-20260919.json` 引用 r6-a12-release。这些历史路径现在由本表档案支持，历史正文不改写；原路径不再是可直接运行的现存输出。
- 对 docs/current、scripts、config、.worklab、apps 搜索未发现 r6-a12-build 或 ui-finalbuild3 的直接消费者；私人会话和数据库内容未检查。

## 机读证据与限制

证据目录：`.project-local/mig/formal-run-builds-archive-20260930/`。`preflight.json` 保存源文件逐项哈希，`verification.json` 保存 ZIP 校验及恢复映射，`delete-ready.json` 保存即时二次核验，`final.json` 保存删除后回读。`archive_verify.py` 是本次执行工具。

本批未运行构建、产品测试或 UI，不能将存储完整性 PASS 宣称为产品运行 PASS。含 DB 的其他 runs 目录保持原样。

## 回退

仅通过上述档案按恢复映射恢复五个生成目录，不回退或覆盖任何产品源码。
