# v0.5.0 历史安装包

这两个 2026-08 历史安装包已于 2026-10-15 从当前源码树归档；它们不是当前 Tauri/Core 候选，也不构成当前安装资格。全部 4,638,139 字节及 SHA-256 已完整读回，详见[归档回执](../../docs/history/repository-consolidation-20261019/current/receipts/AAOS-LEGACY-INSTALLER-ARCHIVE-20261015.json)。

本机保全位置为主项目根下 `.project-local/archives/installers-0.5.0-20261015/`。其他检出和历史正文未改，Git 历史仍保留原始二进制；没有安装、覆盖 Green 或重写历史。

需要恢复历史文件时，可从本机归档复制并核对回执中的完整 SHA-256，或仅恢复这两个路径：

```powershell
git restore --source=8fc22a40a425340bcf8d3ecfd95b87b9477b9ae3 -- packaging/release-0.5.0/ArcheAxis_0.5.0_x64-setup.exe packaging/release-0.5.0/ArcheAxis_0.5.0_x64_en-US.msi
```

恢复文件不等于授权执行旧安装包。当前构建和验收入口继续按活动执行指针及正式 `src-tauri/`、`desktop/` 生命周期脚本读取。
