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

# Lessons Learned

## Architecture & Design

| # | Principle | Context |
|---|-----------|---------|
| 1 | Agent markdown files must use underscores in Python module names, not hyphens | convert-agents.py cannot be imported as convert_agents; kept both as aliases |
| 2 | Codex skills from DTALEX66/Skill-Integration are MCP-based (openai.yaml), not traditional SKILL.md | Each skill needs a minimal SKILL.md for Codex to recognize it |
| 3 | GitHub network from China requires alternative transport | ZIP via API is more reliable than git clone over SSH/HTTPS |
| 4 | All .py files must be written by Python, not PowerShell heredoc | PowerShell's parser conflicts with Python's syntax in inline scripts |
| 5 | File paths with spaces cause issues in PowerShell | Use proper quoting and -C flag for git commands |

## Agent Role System

| # | Lesson |
|---|--------|
| 1 | Frontmatter parser must handle both inline values (key: val) and list values (key:\n  - item) |
| 2 | TOML output needs developer_instructions section with markdown body (minus title line) |
| 3 | dry-run must not write to output directory; all scripts must support it |
| 4 | Test files should import from the underscore-aliased module name |
| 5 | Install scripts should check source directory exists before proceeding |

## Git

| # | Lesson |
|---|--------|
| 1 | Remote URL must use SSH for authentication with gh CLI |
| 2 | After zip-based restore, re-init git and force push to sync |
