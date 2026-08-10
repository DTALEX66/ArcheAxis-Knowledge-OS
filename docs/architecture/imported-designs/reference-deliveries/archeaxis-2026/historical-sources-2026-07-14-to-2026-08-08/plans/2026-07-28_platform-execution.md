# Cognitive-Loop-OS 跨平台后续执行计划

**Goal:** 在 Windows 原生与 WSL2/Linux 两条环境中分别完成各自负责的验证，并以 exact-SHA GitHub CI 作为最终聚合门禁，继续推进 A0/A1 前端与桌面闭环。

**Architecture:** Core、Knowledge Base、Inspiration Research、Integration、wheel、lint 与 Linux Chromium 属于 Linux CI lane；Windows runtime、Rust/Tauri、WebView2、NSIS 与 Windows 生命周期属于 Windows native lane。WSL2 只复现 Linux lane，不能替代 Windows 桌面验收；GitHub Actions 的 exact-SHA 结果才是发布门禁证据。

**Tech Stack:** Python/uv/pytest/Ruff/Playwright、FastAPI/SQLite、Rust 1.88 MSVC、Tauri 2.11、WebView2、NSIS、GitHub Actions。

---

## 当前基线与边界

- 项目：`D:/All projects/Cognitive-Loop-OS`
- 分支：`feat/archeaxis-desktop-a1-violet-core`
- 当前 HEAD：`f1702990f808da1074a4aac461b24e6268ec9ec7`
- 当前工作树包含 A1 前端 WIP 与 smoke 修复，尚未 commit/push。
- WSL2：`2.7.11.0`，默认版本 2，Ubuntu-24.04 已初始化。
- WSL 发行版数据：`D:/All projects/OS configuration/wsl2/Ubuntu-24.04/ext4.vhdx`
- 禁止访问 E 盘、真实 Vault、旧仓库、凭据和 Hermes 受保护运行时。
- 所有测试数据、缓存、日志、wheel、Playwright 产物必须使用项目 `.hermes/task-runtime/` 下的忽略目录。
- 远端写入（commit 后 push、PR、merge）必须单独获得明确授权；旧 CI run 不能替代新候选 SHA 的验证。

## 平台职责矩阵

| 任务域 | WSL2 / Linux | Windows 原生 | 最终证据 |
|---|---|---|---|
| Core `tests/` | 主运行环境，复现 Ubuntu CI | 可做定向回归 | Linux CI exact SHA + 本地结果 |
| Knowledge Base tests | 主运行环境 | 可选兼容检查 | Linux CI exact SHA |
| Integration tests | 主运行环境 | 可选兼容检查 | Linux CI exact SHA |
| Ruff / repository conventions / architecture | 主运行环境，复现 lint | Windows 本地可跑语法/约定 | exact SHA lint |
| wheel-smoke / 仓库外安装 | 主运行环境 | 可选 | Linux wheel job |
| Chromium browser-smoke | Linux Chromium + deps | 本地 Windows Chromium 可做补充 | Linux browser-smoke exact SHA |
| HTTP runtime smoke | 可跑跨平台定向版本 | Windows runtime smoke 必须跑 | 两平台分别记录 |
| Rust library | 不承担 Windows 桌面验收 | `cargo fmt/test/check/build` | Windows desktop-shell |
| Tauri/WebView2 | 不可替代 | 必须 Windows 原生 | native click/readback |
| NSIS installer | 不承担 | 必须 Windows 原生 | build + install lifecycle |
| 前端 API/SQLite/Job/Outbox | 可做 Linux API 回归 | 可做 Windows API 回归 | 定向测试 + browser |
| exact-SHA aggregate | GitHub Ubuntu 汇总 job | GitHub Windows jobs | `a0-gates` success |

---

## 阶段 0：冻结当前前端候选并修复旧 CI 阻断

### Task 0.1：确认当前候选差异

**Files:**
- Review: `app/workspace/ui/index.html`
- Review: `app/workspace/ui/assets/app.js`
- Review: `app/workspace/ui/assets/styles.css`
- Review: `scripts/a0_browser_smoke.py`
- Review: `workspace/intake/2026-07-28-archeaxis-pack-analysis.md`

**Checks:**

```bash
git status --short --branch
git diff --check
node --check app/workspace/ui/assets/app.js
python -m py_compile scripts/a0_browser_smoke.py
python scripts/check_architecture.py
```

### Task 0.2：验证 smoke 根因修复

保持真实隔离数据目录：

```bash
mkdir -p '.hermes/task-runtime/a1-browser-smoke-next/data'
env 'COGNITIVE_DATA_DIR=D:/All projects/Cognitive-Loop-OS/.hermes/task-runtime/a1-browser-smoke-next/data' \
  python scripts/a0_browser_smoke.py
```

必须确认输出：

```text
A0 Chromium browser smoke passed
```

旧 run `30361028569` 失败于旧的跨页面 `#capability-summary` 断言；修复后的 smoke 只验证诊断页自身 fail-closed 状态。

### Task 0.3：前端/API 定向回归

```bash
python -m pytest \
  tests/test_workspace_api.py \
  tests/test_workspace_job_center.py \
  tests/test_ci_a0_gates.py -q
```

当前已验证：`32 passed, 1 warning`。

---

## 阶段 1：WSL2/Linux lane

### Task 1.1：初始化 Linux 工作环境

**Environment:** Ubuntu-24.04 in WSL2。

首次进入后检查：

```bash
uname -a
python3 --version
python3 -c 'import sys; print(sys.platform, sys.executable)'
```

建议使用项目内隔离环境，不写入用户 Home cache：

```bash
cd '/mnt/d/All projects/Cognitive-Loop-OS'
mkdir -p .hermes/task-runtime/wsl2/{venv,tmp,cache,logs,artifacts}
uv venv .hermes/task-runtime/wsl2/venv --python 3.11
source .hermes/task-runtime/wsl2/venv/bin/activate
export COGNITIVE_DATA_DIR='/mnt/d/All projects/Cognitive-Loop-OS/.hermes/task-runtime/wsl2/data'
export UV_CACHE_DIR='/mnt/d/All projects/Cognitive-Loop-OS/.hermes/task-runtime/wsl2/cache/uv'
```

不要把 WSL2 数据或项目测试数据库写入 `/tmp`、`~/.cache` 或其他项目。

### Task 1.2：安装与 CI 相同的 Linux 依赖层

先按 workflow 检查：`.github/workflows/ci.yml:35-55`、`:328-338`。

```bash
uv pip install -r requirements-ci.txt
uv pip install -r requirements-ci-adapters.txt
sudo apt-get update
sudo apt-get install --yes --no-install-recommends \
  ffmpeg tesseract-ocr tesseract-ocr-eng fonts-dejavu-core
python -m playwright install --with-deps chromium
```

Linux lane 的系统依赖安装只作用于 Ubuntu/WSL2，不应改 Windows 工具链或项目锁文件。

### Task 1.3：运行 Linux Core / KB / Integration

```bash
cd '/mnt/d/All projects/Cognitive-Loop-OS'
source .hermes/task-runtime/wsl2/venv/bin/activate
python -m pytest tests/ -q --tb=short
(
  cd knowledge_base && python -m pytest tests/ -q --tb=short
)
python -m pytest integration-tests/ -q --tb=short
```

结果分别记录为 `passed / failed / blocked`。可选依赖缺失不能伪装为通过；若失败，保存完整输出到 `.hermes/task-runtime/wsl2/logs/`。

### Task 1.4：运行 Linux lint / architecture / conventions

```bash
python scripts/check_repository_conventions.py --source worktree
python scripts/check_architecture.py
python -m ruff check \
  app shared knowledge_base inspiration_research Inspiration-Research \
  shared-contracts/adapters app/workflow integration-tests scripts
```

### Task 1.5：运行 Linux wheel-smoke

严格按 `.github/workflows/ci.yml:101-311` 复现，关键步骤：

```bash
uv export --frozen --only-group build --no-emit-project \
  --format requirements-txt --output-file .hermes/task-runtime/wsl2/locked-build.txt
uv build --python "$(command -v python)" --wheel --no-build-isolation \
  --out-dir .hermes/task-runtime/wsl2/wheels
```

然后在项目外的临时工作目录安装 wheel，验证：

- wheel 必须含 `app/workspace/ui/index.html`、`app.js`、`styles.css`；
- 不得含 tests/cache/pyc/db；
- 安装后 Core、KB、Workspace health 与 migration 可读；
- `COGNITIVE_DATA_DIR` 必须位于项目任务 runtime 或明确的隔离目录。

### Task 1.6：运行 Linux Chromium smoke

```bash
export COGNITIVE_DATA_DIR='/mnt/d/All projects/Cognitive-Loop-OS/.hermes/task-runtime/wsl2/browser-data'
python scripts/a0_browser_smoke.py
```

必须独立记录 Linux Chromium 结果；不能用 Windows Chromium 结果替代 Linux job，也不能用 Linux 结果替代 Windows Tauri 结果。

---

## 阶段 2：Windows native lane

### Task 2.1：Windows runtime smoke

在 Windows Git-Bash 或 PowerShell 运行：

```bash
python -m app.runtime_entrypoint migrate
env 'COGNITIVE_DATA_DIR=D:/All projects/Cognitive-Loop-OS/.hermes/task-runtime/windows-runtime' \
  python scripts/runtime_http_smoke.py
```

验证 Windows 路径、进程关闭、HTTP health、Workspace 路由和 project-local data root。

### Task 2.2：Windows Rust library

```bash
cd 'D:/All projects/Cognitive-Loop-OS/desktop/src-tauri'
cargo fmt --all -- --check
cargo check --locked
cargo test --lib
cargo build --locked
```

当前已验证 `cargo check` 与 `cargo build` 通过，并生成 `target/debug/archeaxis-desktop-shell.exe`。

### Task 2.3：Windows backend lifecycle

```bash
cd 'D:/All projects/Cognitive-Loop-OS/desktop/src-tauri'
cargo test --test backend_lifecycle -- --ignored --nocapture
```

重点验证：

- backend 启动与 readiness；
- 正常关闭；
- 强制关闭时 Windows Job Object 回收；
- WebView 子进程不残留；
- runtime 数据目录读回一致。

### Task 2.4：Tauri Windows build / NSIS

```bash
cd 'D:/All projects/Cognitive-Loop-OS/desktop'
npm ci --ignore-scripts --no-audit --no-fund
npm run tauri -- build --bundles nsis
```

验证：

```powershell
Test-Path 'desktop/src-tauri/target/release/archeaxis-desktop-shell.exe'
Get-ChildItem 'desktop/src-tauri/target/release/bundle/nsis/*.exe'
./desktop/scripts/verify_nsis_install.ps1 -Installer <exact-installer-path>
```

必须分开记录：

1. release executable build；
2. NSIS installer existence；
3. install/start/health/close；
4. forced cleanup；
5. uninstall/no-residue。

### Task 2.5：原生 WebView 点击级证据

不能用浏览器 smoke 替代。使用 Windows 原生 Tauri/WebView2 和 UIAutomation/CUA：

- 冷启动桌面壳；
- 发现实际 backend loopback port；
- 点击真实 Workspace 页面入口；
- exercise pending → failed → retry/pending → delivered；
- refresh/reload 后读回同一 Job/Delivery/Receipt；
- 关闭后确认进程树和端口释放；
- 再启动并读回持久化状态。

截图、trace 和日志只写入 `.hermes/task-runtime/windows-desktop/`。

---

## 阶段 3：双环境共享任务

### Task 3.1：合同/API/数据边界回归

涉及路径：

- `app/workspace/router.py`
- `app/workspace/job_outbox.py`
- `app/workspace/ui/assets/app.js`
- `tests/test_workspace_api.py`
- `tests/test_workspace_job_center.py`
- `tests/test_ci_a0_gates.py`

Linux 与 Windows 都应运行定向 API/Job 测试；Windows 额外关注路径、进程和 WebView2；Linux 额外关注 POSIX 文件/进程和 wheel 安装边界。

### Task 3.2：前端路线继续推进

当前已完成 A1 壳层增强。后续按依赖顺序：

1. 真实失败 → retry → replay UI/CI 矩阵；
2. Tauri WebView 点击级投递回读；
3. 更完整交互式 Job Center；
4. SSE audit timeline；
5. asynchronous Worker；
6. ASR / timestamp / content-match Evidence；
7. public release assets。

不得先填充 Planned 页面或使用 mock 数据伪造完成状态。

### Task 3.3：阶段 Release Train

在本地候选 tree 冻结后运行一次完整门禁：

```bash
python -m pytest tests/ -q --tb=short
cd knowledge_base && python -m pytest tests/ -q --tb=short
cd ..
python -m pytest integration-tests/ -q --tb=short
python -m ruff check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts
python scripts/check_architecture.py
python scripts/check_repository_conventions.py --source worktree
```

然后：

1. 只 stage 明确源文件和 intake/plan 文档；
2. 检查 `git diff --cached --name-status`、`git diff --cached --check`、`git write-tree`；
3. 获得远端写入授权后 commit/push；
4. 查询新 commit 的 exact-SHA workflow/run/job 结论；
5. 只有 `test/lint/wheel/browser/windows-runtime/desktop-shell/a0-gates` 全部 success 才能称 CI 通过；
6. 未授权或 CI 未绿时保持 PR 未发布/未合并。

---

## 风险与判定规则

- **WSL2 可用不等于 Linux lane 已通过**：必须真实执行 Linux 命令并保存输出。
- **Linux lane 通过不等于 Windows 桌面通过**：Tauri/WebView2/NSIS 证据必须在 Windows 原生取得。
- **Windows 本地 build 通过不等于 CI 通过**：CI 仍需验证 exact candidate SHA。
- **旧 run `30361028569` 只属于旧 SHA**：不能用作修复后候选证据。
- **本地全量测试缺依赖时**：先按 Linux CI 安装依赖；如果仍失败，分类为真实测试失败，不用 `|| true` 隐藏。
- **WSL 挂载项目路径**：避免 Linux 与 Windows 两个 writer 同时修改同一工作树；保持单 writer 串行。
- **Windows path / Linux path**：Linux 命令使用 `/mnt/d/...`，Windows 命令使用 `D:/...`；不要把一方路径原样传给另一方工具。
- **发行版数据位置**：只接受 `D:/All projects/OS configuration/wsl2/Ubuntu-24.04/ext4.vhdx` 作为当前 WSL 数据位置；不迁移、不删除未确认的其他发行版数据。

## 当前下一步

1. 在 Ubuntu-24.04 中完成 Linux 工具链初始化；
2. 运行 Task 1.3–1.6，得到本机 Linux lane 结果；
3. Windows native lane 保持原生执行；
4. 完成当前候选 tree 的 staged review；
5. 待用户明确授权后进入 commit → push → exact-SHA CI。
