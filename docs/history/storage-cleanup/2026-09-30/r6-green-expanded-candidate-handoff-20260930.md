# R6 绿色版候选展开目录：交接审计（2026-09-30）

> 后续状态更新：三个展开目录在本轮重新逐载荷核对长度/SHA-256后已删除，三个同名 ZIP 均保留。删除回读和恢复说明见 `verified-duplicate-prune-20260930.md`。下文“未删除/0 B”为此前轮次历史状态。

## 当前决定

`NONE_PROVEN_THIS_TURN`：本轮没有删除三个 R6 候选展开目录。既有只读子审计曾报告 ZIP 成员哈希和 CRC 一致、额外项为可再生 `.pyc`；但本轮复核脚本的逐成员 SHA 重算在结束前被停止。为避免将历史报告误说成当前回读，三个目录及 ZIP 均保留。可以在后续专门回合用一次流式 ZIP CRC+SHA 校验，随后以精确 allowlist 折叠展开副本。

## 路径和之前审计记录

| 候选 | 展开路径 | ZIP 路径 | ZIP SHA-256 | 上次只读审计结论 |
|---|---|---|---|---|
| `vr6-0e934f33-x64` | `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-0e934f33-x64/` | 同目录同名 `.zip` | `6AB6C5ECAEAFABFCF4A91131A9F20D2510BDCF5EE0CABD31D4D844344BD2A087` | ZIP 2,515 成员，展开 2,544 文件；差异为 29 个 `.pyc` |
| `vr6-452b5d0c-x64` | `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-452b5d0c-x64/` | 同目录同名 `.zip` | `441F67BE549CAB0AC2A9F1A9391FA4E2192E0129D2F26AFBAC9321B42546663C` | ZIP 2,538 成员，展开 2,540 文件；差异为 2 个 `.pyc` |
| `vr6-6f0b4cc-x64` | `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-6f0b4cc-x64/` | 同目录同名 `.zip` | `FAAAF92B4117F067C8A38BAC3E1EBE38FE189CF...` | ZIP 2,515 成员，展开 2,553 文件；差异为 38 个 `.pyc` |

上次审计的展开逻辑字节分别为 275,169,533、270,107,101、275,328,860，总计约 820,605,494 B。请将这些数字视作上一轮读数，删除前重新读取。

## 本轮尝试与限制

- 读取当前目录和 ZIP SHA 后，使用 Python `zipfile.testzip()` 并按成员流式比对 SHA；首版比较误将 ZIP 顶级包名前缀重复计算，产生假性 mismatch。修正版在长时间重算中被停止。
- 其间未删除、移动或覆盖任何候选内容。`.project-local/mig/r6-green-expanded-dedupe-20260930/` 中保留 preflight 和 verification 尝试凭据；它们不是成功验收证据，不能用于授权删除。
- 以后继续时须修正脚本，先按 ZIP 单一顶层目录裁掉 package prefix；逐成员比较相对路径/长度/SHA、执行 CRC 检查，确认锁进程与 reparse 点为零，写入恢复说明和 delete-ready manifest，再操作。不要直接重用本轮失败 receipt。
- 其中 `452b5d0c` 与 `6f0b4cc` 被 R6 历史报告/候选 JSON 引用，恢复时提取 ZIP 至上列原展开路径并对照 manifest；`0e934f33` 是已判定旧/失败的候选。清理只回收展开副本，不等同于产品候选资格或 release PASS。

## 范围与归属

以上文件是 AAOS 自有历史 build/candidate 产物，不是其他项目外溢。三个 ZIP 留在其原属 `.project-local/build/green-candidates-r6/`。没有跨仓库迁移、branch、commit 或 push。当前及 Green 注册 worktree、user data、SQLite/WAL/SHM/lock、`.hermes` 均不在此审计范围。

## 更新：独立全量重验完成（2026-09-30）

修正的流式重验现已完成：三个 ZIP 均完整读取到 EOF，`ZipFile.testzip()` 无坏成员；逐成员规范化包根前缀后，ZIP 与展开树的相对路径、长度、SHA-256 全部匹配，无 reparse；全部展开额外项为 `.pyc`。JSON 逐成员机器回执见 `.project-local/mig/r6-green-expanded-dedupe-20260930/verified-recheck.json`。

| 包 | 展开文件/字节 | ZIP 成员/归档 SHA-256 | 额外可重建文件 | 校验 |
|---|---:|---|---|---|
| `vr6-0e934f33-x64` | 2,544 / 275,169,533 B | 2,515 / `6AB6C5ECAEAFABFCF4A91131A9F20D2510BDCF5EE0CABD31D4D844344BD2A087` | 29 `.pyc` / 683,742 B | PASS |
| `vr6-452b5d0c-x64` | 2,540 / 270,107,101 B | 2,538 / `441F67BE549CAB0AC2A9F1A9391FA4E2192E0129D2F26AFBAC9321B42546663C` | 2 `.pyc` / 6,392 B | PASS |
| `vr6-6f0b4cc-x64` | 2,553 / 275,328,860 B | 2,515 / `FAAAF92B4117F067C8A38BAC3E1EBE38FE189CF141E5AD650AEC0567DF5EBBA6` | 38 `.pyc` / 843,676 B | PASS |
| **Total** | **7,637 / 820,605,494 B** | **ZIP 合计 284,939,129 B，全部原位保留** | **69 / 1,533,810 B** | **PASS** |

本轮只完成验证并生成回执，没有删除展开目录。此前对另一个 4.71 GB Cargo 目录和 C: WER 原件目录的精确递归删除都被执行策略拦截；不使用逐文件删除或其他工具绕过。R6 候选目录自身本轮未尝试删除；其仍保留在表列原路径，删除状态 `NOT_EXECUTED`。若后续执行策略允许，对这三目录可仅删除表列展开目录并保留同名 ZIP；恢复时解压 sibling ZIP 到该展开路径，再生成 29/2/38 个 pycache（不属于分发载荷）；`452b5d0c`、`6f0b4cc` 历史验证前按原 R6 manifest/receipt 比较。

恢复关系已由本报告显式记录；`docs/current/R6-EXECUTION.md` 的历史引用保留为历史记录，不改写旧验收数据。清理回收空间仍为 0 B（本轮没有删除）。
