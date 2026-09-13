@echo off
setlocal
pushd "%~dp0"
set "REPO=%CD%"
set "RUNTIME=%REPO%\.project-local\task-runtime"
set "CACHE=%REPO%\.project-local\cache"
if not exist "%RUNTIME%\tmp" mkdir "%RUNTIME%\tmp"
if not exist "%CACHE%\pip" mkdir "%CACHE%\pip"
if not exist "%CACHE%\uv" mkdir "%CACHE%\uv"
set "TEMP=%RUNTIME%\tmp"
set "TMP=%TEMP%"
set "TMPDIR=%TEMP%"
set "PIP_CACHE_DIR=%CACHE%\pip"
set "UV_CACHE_DIR=%CACHE%\uv"
where uv >nul 2>&1
if not errorlevel 1 set "UV=uv"
if not defined UV if exist "%LOCALAPPDATA%\hermes\bin\uv.exe" set "UV=%LOCALAPPDATA%\hermes\bin\uv.exe"
if not defined UV echo uv executable is required; add uv to PATH or install the approved project toolchain>&2 & exit /b 1
if not exist ".venv\Scripts\python.exe" "%UV%" venv ".venv"
if errorlevel 1 exit /b 1
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
"%UV%" pip install --python "%PYTHON%" -r "%REPO%\requirements.txt"
if errorlevel 1 exit /b 1
"%PYTHON%" "%REPO%\scripts\runtime\dev.py" -- "%PYTHON%" -m app.runtime_entrypoint core
set "STATUS=%ERRORLEVEL%"
popd
endlocal & exit /b %STATUS%
