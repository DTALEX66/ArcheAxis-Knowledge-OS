# 2026-09-30 归档副本、重复候选与安装缓存清理

用户继续授权清理后，实际删除以下项目自有目录，全部回读不存在。合计 **2,568,549,459 逻辑字节**（约 2.57 GB）；不是物理磁盘释放量或最新项目总体积。

| 项目相对路径 | 删除字节 | 保留与恢复 |
| --- | ---: | --- |
| `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-0e934f33-x64` | 275,169,533 | 同级同名 ZIP |
| `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-452b5d0c-x64` | 270,107,101 | 同级同名 ZIP |
| `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-6f0b4cc-x64` | 275,328,860 | 同级同名 ZIP |
| `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vheadd1bb2b99-x64` | 883,353,639 | 同级同名 ZIP；四个运行文件保留于所属 run 的 data |
| `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vcurrent2-20260925` | 631,138,811 | 保留同级 `ArcheAxis.Knowledge.Green-vcurrent-20260925` |
| `.project-local/tmp/vscode-repair-20260930` | 233,451,515 | 下载缓存及安装日志；历史安装修复报告保留 |

## 本轮证据

三个 R6 ZIP 当前 SHA 与既有完整校验凭据一致；本轮重新读取所有 ZIP 载荷并比对展开文件长度、SHA-256，全部匹配；额外文件仅为 69 个可生成 pyc。此次没有重新执行独立 CRC API 检查，不以历史 CRC 结果冒充本轮检查。精确清单及回读：`.project-local/mig/r6-green-expanded-dedupe-20260930/live-verified.json`、`live-deletion-readback.json`。

vhead ZIP 当前 SHA 与先前凭据一致；全部归档载荷重新比对长度与 SHA-256一致。99 个额外项为 95 个 pyc 与四个 workspace.sqlite/SHM/WAL/writer.lock 文件；四文件与 `.project-local/runs/green-smoke-current-20260916/data/` 已迁回副本再次核对长度和 SHA-256一致，移除的是重复原件。数据库状态不解释为新的产品运行验证。凭据：`.project-local/mig/vhead-expanded-prune-20260930/verified.json`、`readback.json`。

vcurrent 两份展开候选由并行只读审计剥除各自内层包名前缀后比对 6,412 对文件，相对路径、长度、SHA-256全一致，无数据库或 sidecar；保留 vcurrent 为此次去重 canonical。唯一现行文档命中为明确标记历史快照的 `docs/current/dsh-review/dp-ui-01-readiness.md:44–45`，该历史记录未改写。VS Code 两文件为已完成修复的下载与日志，非安装运行依赖。删除前清单、安装包与日志哈希和回读在 `.project-local/mig/duplicate-and-installer-prune-20260930/`。

删除目标无 Git 跟踪文件、无 reparse；Get-Process 未发现候选程序或路径匹配进程。系统中 Hermes 的 Python 进程路径在其他软件目录，未终止。未改 ACL、Git 安全配置或其他软件配置。未访问 E/F。

## 恢复映射及边界

如需重跑历史候选，先把对应 ZIP 解压到其原父目录，恢复 ZIP 中的包名顶层目录，再按历史 receipt 验证。pyc由 Python 重新生成。vcurrent2 可从保留的 vcurrent 复制到原外层目录，并把内层 `ArcheAxis.Knowledge.Green-vcurrent-20260925-x64` 改回 `ArcheAxis.Knowledge.Green-vcurrent2-20260925-x64`；复制前仍应核对保留副本未变。

当前候选、用户 UI 修改、Green 运行程序/数据/备份和依赖环境保留。本轮没有产品重建、启动测试、commit 或 push。此次清理与上一轮 `incremental-prune-20260930.md` 合计 **7,775,968,326 逻辑字节**，不与其他历史轮次重复累计。

状态：精确清理与回读 PASS；整体存储治理 PARTIAL；重建/历史候选重跑 NOT_EXECUTED。
