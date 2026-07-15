@echo off
REM Cognitive-Loop-OS — Launch unified runtime + research service
setlocal
pushd "%~dp0"
echo Starting Cognitive-Loop-OS services...

echo [1/2] Cognitive-OS + Knowledge-Base on port 8000
start "Cognitive-OS" cmd /c "call .venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers"

echo [2/2] Inspiration-Research on port 8001
start "IR" cmd /c "call .venv\Scripts\activate && python -m uvicorn inspiration_research.api:app --host 127.0.0.1 --port 8001"

echo.
echo All services launched:
echo   Cognitive-OS         http://127.0.0.1:8000/docs
echo   Inspiration-Research http://127.0.0.1:8001/docs
echo   Knowledge-Base       http://127.0.0.1:8000/kb/docs
echo.
popd
pause
