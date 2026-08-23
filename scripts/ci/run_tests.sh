#!/usr/bin/env bash
# run_tests.sh — ArcheAxis Knowledge (ArcheAxis-Knowledge-OS) 项目内测试入口
#
# 固定 pytest basetemp / 临时目录到项目本地运行时根，防止测试产物溢出到
# D:\clo-*、D:\tmp、C:\tmp 等外部路径（历史溢出根因修复，2026-08-12）。
#
# 用法：
#   scripts/ci/run_tests.sh                 # 默认测试集（tests）
#   scripts/ci/run_tests.sh --full          # 全量（tests + knowledge_base/tests）
#   scripts/ci/run_tests.sh -- -k smoke     # 透传其余 pytest 参数
set -euo pipefail

# 项目根（本脚本位于 <repo>/scripts/ci/ 下两层）
# pwd -W 返回 Windows 路径（D:/...），避免 MSYS /d/... 路径传给 Windows Python/uv 失效
ROOT_UNIX="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROOT_WIN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -W | sed 's|\\\\|/|g')"

# 断言项目根：必须含 pyproject.toml + .git，防止目录索引错误扩大范围
if [ ! -f "$ROOT_UNIX/pyproject.toml" ] || [ ! -e "$ROOT_UNIX/.git" ]; then
  echo "FATAL: 不是有效的项目根: $ROOT_WIN" >&2
  exit 2
fi

# A linked worktree can itself live under the canonical repository's ignored
# runtime tree. Anchor pytest data at the Git common-dir owner so that Windows
# paths do not duplicate `.hermes/task-runtime/<worktree>/...`.
GIT_COMMON_DIR="$(git -C "$ROOT_UNIX" rev-parse --path-format=absolute --git-common-dir)"
PROJECT_DATA_ROOT="$(dirname "$GIT_COMMON_DIR")"
RUNTIME="$PROJECT_DATA_ROOT/.hermes/task-runtime"
TMPDIR_RUNTIME="$RUNTIME/tmp"
UV_CACHE_DIR="$PROJECT_DATA_ROOT/.hermes/cache/uv"
mkdir -p "$TMPDIR_RUNTIME" "$UV_CACHE_DIR"
export UV_CACHE_DIR

# 项目内 basetemp：保持名称短，避免深层 Windows worktree 叠加测试名后
# 超过传统 Win32 260 字符路径上限。Bash PID 足以隔离并发启动的测试进程。
BASETEMP="$RUNTIME/t-$BASHPID"
mkdir -p "$BASETEMP"

# 完整测试集（--full 加 knowledge_base/tests；记忆/惯例：uv run --frozen --group ci --group ci-adapters）
TESTS="tests"

# bash 调用非内建脚本时，前导 "--" 会作为参数透传进来（如 run_tests.sh -- -k x），剥掉它
if [ "${1:-}" = "--" ]; then
  shift
fi

if [ "${1:-}" = "--full" ]; then
  TESTS="tests knowledge_base/tests"
  shift
fi

echo "[run_tests] root=$ROOT_WIN"
echo "[run_tests] basetemp=$BASETEMP (项目内, 防溢出)"
echo "[run_tests] pytest targets: $TESTS"

# 注入项目内环境（与 hermes-project-data.py 相同的映射原则）
export TMP="$TMPDIR_RUNTIME"
export TEMP="$TMPDIR_RUNTIME"
export TMPDIR="$TMPDIR_RUNTIME"
export PYTHONPYCACHEPREFIX="$RUNTIME/pycache"

cd "$ROOT_UNIX"
exec uv run --frozen --group ci --group ci-adapters pytest \
  --basetemp="$BASETEMP" \
  $TESTS \
  "$@"
