# Phase 0 测试基线

> Git 基线：`469c39dcedf187e4c99d816728a2b38524881694`。结果由本次真实命令执行生成，不复用历史测试数字。
>
> 隔离：所有子进程在导入项目前设置每次运行唯一且自动删除的 `COGNITIVE_DATA_DIR`、`PYTHONDONTWRITEBYTECODE=1`，pytest 使用 `-p no:cacheprovider`。

## 门禁结果

| 项目 | 结果 |
|---|---|
| `root-tests` | **passed** — 146 passed, 5 warnings in 3.89s |
| `knowledge-base-tests` | **passed** — 28 passed in 0.97s |
| `integration-tests` | **passed** — 1 passed in 0.18s |
| `inspiration-research-tests` | **observed-failure** — 1 error in 0.12s |
| `ruff` | **passed** — All checks passed! |
| `mypy-config-preflight` | **observed-failure** — 1 error across 1 file; exit code 2 |
| `mypy-python-3.13-diagnostic` | **observed-failure** — 42 errors across 18 files; exit code 1 |
| `worktree-diff-check` | **passed** — warning: in the working copy of 'migrations/reports/phase-0/TEST_BASELINE.md', CRLF will be replaced by LF the next time Git touches it |

## 执行命令

### root-tests

工作目录：`.`

```bash
python -m pytest tests -q --tb=short -W default -p no:cacheprovider
```

观测到的告警：

- ResourceWarning: unclosed database in <sqlite3.Connection object>
- StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

### knowledge-base-tests

工作目录：`knowledge_base`

```bash
python -m pytest tests -q --tb=short -p no:cacheprovider
```


### integration-tests

工作目录：`.`

```bash
python -m pytest integration-tests -q --tb=short -p no:cacheprovider
```


### inspiration-research-tests

工作目录：`.`

```bash
python -m pytest Inspiration-Research/tests -q --tb=short -p no:cacheprovider
```


### ruff

工作目录：`.`

```bash
python -m ruff check app shared knowledge_base Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts --no-cache
```


### mypy-config-preflight

工作目录：`.`

```bash
python -m mypy app shared knowledge_base --ignore-missing-imports --no-error-summary
```


### mypy-python-3.13-diagnostic

工作目录：`.`

```bash
python -m mypy app shared knowledge_base --ignore-missing-imports --python-version 3.13 --no-error-summary
```


### worktree-diff-check

工作目录：`.`

```bash
git diff --check
```

## 解释规则

- `passed` 只表示该命令本次退出码为 0。
- `observed-failure` 是非阻断诊断基线，必须保留真实错误规模，不能改写为通过。
- `failed` 表示阻断门禁失败，保留真实摘要，不能改写为完成。
- `worktree-diff-check` 只检查生成开始时的 worktree↔index；最终 staged diff 必须在暂存后另跑 `git diff --cached --check`。
- Docker 未在本地执行时不得声称容器实机通过。
- GitHub Actions 状态必须在推送后单独核对。
