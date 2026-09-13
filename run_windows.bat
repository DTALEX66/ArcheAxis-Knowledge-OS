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
if not exist ".venv\Scripts\python.exe" python -m venv ".venv"
if errorlevel 1 exit /b 1
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
uv pip install --python "%PYTHON%" -r "%REPO%\requirements.txt"
if errorlevel 1 exit /b 1
"%PYTHON%" "%REPO%\scripts\runtime\dev.py" -- "%PYTHON%" -m app.runtime_entrypoint core
set "STATUS=%ERRORLEVEL%"
popd
endlocal & exit /b %STATUS%
