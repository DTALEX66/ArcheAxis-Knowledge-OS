@echo off
rem ArcheAxis tracked Rust test runner (R14 reproducibility).
rem
rem The per-run wrappers under .project-local\runs\ are generated and ignored, so a
rem fresh checkout had no way to run the Rust suites at all. This script is the tracked
rem entry point the evidence index cites.
rem
rem Environment it reads (all optional, each with a named failure instead of a guess):
rem   ARCHEAXIS_MSVC_VCVARS   full path to vcvars64.bat (MSVC toolchain import)
rem   ARCHEAXIS_RUST_TOOLCHAINS  parent directory holding cargo\ and rustup\
rem   ARCHEAXIS_PYTHON        interpreter the worker tests must use
rem   ARCHEAXIS_CARGO_HOME      cargo home holding registry\; the canonical dev.py
rem                             cache. Without it the dependency cache is the
rem                             toolchain's own, which may not hold the locked crates
rem                             and makes an offline resolution fail on a crate the
rem                             canonical cache has. Setting it is what lets this
rem                             tracked script reproduce dev.py's offline build.
rem   ARCHEAXIS_CARGO_TARGET_DIR  override for the sealed target directory
rem   CARGO_TARGET_DIR          inherited canonical dev.py worktree build root
rem
rem Prefer running through scripts/runtime/dev.py, which sets the canonical
rem common-repository, per-worktree CARGO_TARGET_DIR. An explicit ARCHEAXIS override
rem wins; otherwise preserve that inherited directory. Direct standalone invocation
rem without either variable retains the checkout-local .project-local\build\cargo
rem fallback for compatibility; it does not provide dev.py's canonical isolation.
rem
rem Usage: scripts\ci\cargo_test.bat [cargo arguments...]
rem        with no arguments: cargo test --workspace --offline

setlocal EnableDelayedExpansion
set "REPO=%~dp0..\.."
for %%I in ("%REPO%") do set "REPO=%%~fI"

if defined ARCHEAXIS_MSVC_VCVARS (
  if not exist "%ARCHEAXIS_MSVC_VCVARS%" (
    echo cargo_test: ARCHEAXIS_MSVC_VCVARS points at a file that does not exist: "%ARCHEAXIS_MSVC_VCVARS%" 1>&2
    exit /b 2
  )
  call "%ARCHEAXIS_MSVC_VCVARS%" >nul 2>&1
  if errorlevel 1 (
    echo cargo_test: importing the MSVC environment failed: "%ARCHEAXIS_MSVC_VCVARS%" 1>&2
    exit /b 2
  )
)

if defined ARCHEAXIS_RUST_TOOLCHAINS (
  set "CARGO_HOME=%ARCHEAXIS_RUST_TOOLCHAINS%\cargo"
  set "RUSTUP_HOME=%ARCHEAXIS_RUST_TOOLCHAINS%\rustup"
  rem Delayed expansion is required here: a %CARGO_HOME% reference inside this
  rem parenthesised block is expanded when the block is parsed, before the line
  rem above has run, so PATH became "\bin;<old PATH>" and the "where cargo" check
  rem below could never pass from ARCHEAXIS_RUST_TOOLCHAINS alone.
  set "PATH=!CARGO_HOME!\bin;%PATH%"
)

rem The canonical dependency cache. Applied after the toolchain default above so an
rem explicit cache root wins, and only when the directory actually holds a registry.
if defined ARCHEAXIS_CARGO_HOME (
  if not exist "%ARCHEAXIS_CARGO_HOME%\registry" (
    echo cargo_test: ARCHEAXIS_CARGO_HOME holds no registry: "%ARCHEAXIS_CARGO_HOME%" 1>&2
    exit /b 2
  )
  set "CARGO_HOME=%ARCHEAXIS_CARGO_HOME%"
)

if defined ARCHEAXIS_CARGO_TARGET_DIR set "CARGO_TARGET_DIR=%ARCHEAXIS_CARGO_TARGET_DIR%"
if not defined CARGO_TARGET_DIR set "CARGO_TARGET_DIR=%REPO%\.project-local\build\cargo"

rem PATH may contain only the explicitly supplied toolchain. Resolve the Windows
rem lookup utility independently so its absence from PATH is not called missing cargo.
"%SystemRoot%\System32\where.exe" cargo >nul 2>&1
if errorlevel 1 (
  echo cargo_test: cargo is not on PATH; set ARCHEAXIS_RUST_TOOLCHAINS or install the Rust toolchain 1>&2
  exit /b 2
)

set "ARGS=%*"
set "FIRST=%~1"
if not defined FIRST (
  set "ARGS=test --workspace --offline"
  set "FIRST=test"
)

rem If the caller did not name a cargo subcommand, assume "test", so that
rem "cargo_test.bat -p archeaxis-domain" means what a reader expects.
set "SUBCOMMAND="
for %%S in (test build check run bench clippy fmt tree metadata doc) do (
  if /I "%FIRST%"=="%%S" set "SUBCOMMAND=1"
)
if not defined SUBCOMMAND set "ARGS=test %ARGS%"

echo cargo_test: repo=%REPO%
echo cargo_test: target=%CARGO_TARGET_DIR%
echo cargo_test: cargo %ARGS%
pushd "%REPO%"
call cargo %ARGS%
set "STATUS=%ERRORLEVEL%"
popd
exit /b %STATUS%
