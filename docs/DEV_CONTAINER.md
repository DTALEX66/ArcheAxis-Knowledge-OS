# Reusable Development Container

This repository has one source of truth: the Git checkout on the host. The
development container is only a reproducible toolchain. It does not contain a
second application checkout, does not mount the production data volume, and does
not expose the Docker socket.

## First use on any computer

Requirements:

- Git
- Docker Desktop with Compose
- PowerShell 7 on Windows, or Docker Compose on Linux/macOS

```powershell
git clone git@github.com:DTALEX66/Cognitive-Loop-OS.git
cd Cognitive-Loop-OS
git switch -c agent/<task-name>

# Build the locked development environment and open a shell.
./run_dev_container.ps1
```

The repository is mounted at `/workspace`. Changes made by an agent in the
container are changes in the host Git checkout, so they are immediately visible
to `git diff`, review tools, and the next computer. The dependency environment
is built from `pyproject.toml` and `uv.lock`; rebuild after changing either file.

## Task loop

Inside the development container:

```bash
git status --short
pytest tests/test_<affected_area>.py -q
ruff check app shared knowledge_base inspiration_research shared-contracts/adapters
python scripts/check_architecture.py
python scripts/check_repository_conventions.py --source worktree
git diff --check
```

When the task is complete:

```bash
git add -A
git diff --cached --check
git commit -m "type(scope): short task result"
git push -u origin HEAD
```

The main computer reviews and merges the branch. Never copy source files out of
a container and never commit generated databases, logs, virtual environments, or
build output.

## Commands from Windows PowerShell 7

```powershell
./run_dev_container.ps1 pytest
./run_dev_container.ps1 pytest tests/test_dev_container_contract.py -q
./run_dev_container.ps1 ruff check app shared
./run_dev_container.ps1 bash
```

The script rebuilds before every command, so dependency changes are picked up.
For an interactive session, use `./run_dev_container.ps1` with no arguments.

## Production versus development

| Path | Purpose | Source mount | Data |
| --- | --- | --- | --- |
| `docker-compose.dev.yml` | agent/developer toolchain | `.:/workspace` | `cognitive-dev-data` |
| `docker-compose.yml` | production-like deployment | no source mount | `cognitive-sqlite` |
| `docker-compose.ci.yml` | CI smoke override | no source mount | disposable CI volumes |

The production stack remains immutable and non-root. The development stack is
not a production deployment and must not be used as one.

## Recovery on another computer

```powershell
git clone git@github.com:DTALEX66/Cognitive-Loop-OS.git
cd Cognitive-Loop-OS
git fetch origin
git switch -c agent/<task-name>
./run_dev_container.ps1
```

If a task was already pushed from another computer:

```powershell
git fetch origin
git switch --track origin/agent/<task-name>
```

The branch and commit are the handoff. The container image is disposable and can
be rebuilt from the repository at any time.
