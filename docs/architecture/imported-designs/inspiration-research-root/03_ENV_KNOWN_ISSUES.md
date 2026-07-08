> ---
> 📋 **交叉引用**：操作本项目时必须同时遵守以下四份文件：
> 
> | # | 文件 | 内容 |
> |---|------|------|
> | 1 | [`00_铁律.md`](../00_铁律.md) | 28条操作铁律（六篇章：Paper/Data/Workflow/Boundary/Tech/Behavior） |
> | 2 | [`01_DO_NOT_REPEAT.md`](../01_DO_NOT_REPEAT.md) | 永不重复的技术红线 |
> | 3 | [`02_LESSONS_LEARNED.md`](../02_LESSONS_LEARNED.md) | 架构/Agent/Git 错误教训 |
> | 4 | [`03_ENV_KNOWN_ISSUES.md`](../03_ENV_KNOWN_ISSUES.md) | 环境已知问题 |
> > **来源**：源自 [DTALEX66/Knowledge-Base](https://github.com/DTALEX66/Knowledge-Base) 的经验教训，已直接合并到本仓库。
> ---

# ENV Known Issues

| Date | Issue | Workaround | Status |
|------|-------|-----------|--------|
| 2026-06-23 | PowerShell quoting breaks Python -c multi-line strings | Use script files or cmd.exe /c echo | Active |
| 2026-06-23 | Network to PyPI/GitHub unstable | Use SSH git, pip --no-deps, retry logic | Active |
| 2026-06-23 | node_modules on Windows causes path length issues | Keep under .gitignore, use npm ci | Active |
