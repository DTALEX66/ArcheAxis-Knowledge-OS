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
rem   ARCHEAXIS_CARGO_TARGET_DIR  override for the sealed target directory
rem
rem Defaults: cargo must already be on PATH, and the target directory is pinned to
rem <repo>\.project-local\build\cargo so a worktree cannot mix artefacts with the
rem main checkout (the trap recorded in HANDOFF pitfall 3).
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
  set "PATH=%CARGO_HOME%\bin;%PATH%"
)

if not defined ARCHEAXIS_CARGO_TARGET_DIR set "ARCHEAXIS_CARGO_TARGET_DIR=%REPO%\.project-local\build\cargo"
set "CARGO_TARGET_DIR=%ARCHEAXIS_CARGO_TARGET_DIR%"

where cargo >nul 2>&1
if errorlevel 1 (
  echo cargo_test: cargo is not on PATH; set ARCHEAXIS_RUST_TOOLCHAINS or install the Rust toolchain 1>&2
  exit /b 2
)

set "ARGS=%*"
if "%ARGS%"=="" set "ARGS=test --workspace --offline"

rem If the caller did not name a cargo subcommand, assume "test", so that
rem "cargo_test.bat -p archeaxis-domain" means what a reader expects.
set "FIRST="
for /f "tokens=1" %%A in ("%ARGS%") do set "FIRST=%%A"
set "SUBCOMMAND="
for %%S in (test build check run bench clippy fmt tree metadata doc) do (
  if /I "%FIRST%"=="%%S" set "SUBCOMMAND=1"
)
if not defined SUBCOMMAND set "ARGS=test %ARGS%"

echo cargo_test: repo=%REPO%
echo cargo_test: target=%CARGO_TARGET_DIR%
echo cargo_test: cargo %ARGS%
pushd "%REPO%"
cargo %ARGS%
set "STATUS=%ERRORLEVEL%"
popd
exit /b %STATUS%
