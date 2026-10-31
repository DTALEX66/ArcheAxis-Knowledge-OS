# 剩余白名单：管理员手动执行入口

Owner后继授权“给你授权，如果还不行给我命令行”。当前ALEX进程未提升（Administrators deny-only/Medium）；五个旧pytest scope与旧conflict target代表根/叶已有Administrators FullControl，无需先修改ACL。旧target精确递归命令再次在创建进程前被工具执行策略拒绝，blocked by policy且未给具体原因。未用另一工具执行这些真实目标。

已准备本仓ignored bundle：`.project-local/runs/be268a2d33/adminrem-09ea3c41/`。仅原target编译缓存及五个9月pytest run的tmp/pytest、pytest-tmp、pytest-cache、pycache，冻结18,756个可读公共普通文件、3,921,430,366逻辑B。130个保护名、5个reparse及10个只读核验失败不入清单；原件、source.tar/contracts.tar/原执行receipt、最新候选及其他工作区均不入清单。不是全仓清理命令。

默认使用PowerShell 7（`pwsh.exe`）。当前执行环境已核实为7.6.5；下列命令使用已验证的完整路径，不依赖管理员终端的PATH。在“以管理员身份运行”的PowerShell粘贴：

```powershell
& "C:\Users\ALEX\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe" -NoProfile -File "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\be268a2d33\adminrem-09ea3c41\tmp\Remove-ReviewedRemainingOutputs.ps1" -Action Apply
```

入口先核管理员令牌、Python脚本/plan完整SHA及编译进程；既有管理员ACL下按冻结WinID/size/mtime与同句柄DELETE清理，post缺失后计数，最后只处理同身份空目录。不会takeown、icacls、修改ACL或杀进程。锁/拒绝/变化保留。旧目录中被保护或非空项可能仍在，COMPLETE_REVIEWED_PUBLIC_FILES仅指白名单文件完成。实际结果写bundle的artifacts/apply-*-result.json，终端打印实际计数、HOLD和路径。

PowerShell7.6.5实际Review退出0，返回18,756文件、3,921,430,366B及最终plan SHA；此前5.1 Review仅作兼容性记录，执行入口已纠正为7。Python语法/plan原文件与目录集合不变、18,756路径范围及4个越界/保护负例通过；原review/v2未执行记录保留。最终修正封存空目录CloseHandle失败并明确目录剩余。仅准备和有限检查，不是管理员Apply或额外3.92GB已删除；本轮实际删除0，原62.04GB checkpoint不滚动。

最终绑定：

- Python SHA-256：`5ba7bf7f7596eb6ca6db9b5caf412e6bab7b4ce9e42eb1d74de45967c4f5e003`
- Plan SHA-256：`4c388943fc10127fd4b4f43c3b93a45d21fb1d22d760d8fcdc44b8519edede35`
- 准备/验证身份：`.project-local/runs/be268a2d33/adminrem-09ea3c41/artifacts/validation.json`，SHA-256 `37d5e42f0a55e114910c3a9b1eaa0ecc48305ab066ba8df6c9dd4cc5c807059f`。

无上传、UI实施、全局设置、Green或真实库变更；实际进度沿唯一执行记录。
