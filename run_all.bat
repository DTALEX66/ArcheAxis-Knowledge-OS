@echo off
REM archeaxis-workspace — migrate once, then launch the unified single-writer runtime.
setlocal
pushd "%~dp0"

call .venv\Scripts\activate
if errorlevel 1 exit /b 1

echo Running one-shot schema migration...
python -m app.runtime_entrypoint migrate
if errorlevel 1 exit /b 1

echo Starting unified Core + Knowledge-Base + internal Research on port 8000
echo   Core docs:      http://127.0.0.1:8000/docs
echo   Knowledge docs: http://127.0.0.1:8000/kb/docs
python -m app.runtime_entrypoint core

popd
endlocal
