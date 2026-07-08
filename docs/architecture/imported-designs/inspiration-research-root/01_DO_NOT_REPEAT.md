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

# Do Not Repeat

1. Don't write .py files through PowerShell echo - use Python open() or script files
2. Don't use triple-quoted strings inside Python -c in PowerShell
3. Don't commit db_backup_*/error_*/integration_* junk files
4. Don't use @router without defining router = APIRouter()
5. Don't import from __init__ chains that cause circular imports
