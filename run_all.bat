@echo off
REM Cognitive-Loop-OS — Launch all 3 B-line services
echo Starting Cognitive-Loop-OS services...

echo [1/3] Cognitive-OS on port 8000
start "Cognitive-OS" cmd /c "cd /d D:\All projects\Cognitive-Loop-OS && .venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Inspiration-Research on port 8001
start "IR" cmd /c "cd /d D:\All projects\Cognitive-Loop-OS && .venv\Scripts\activate && python -m uvicorn Inspiration-Research.api:app --host 127.0.0.1 --port 8001"

echo [3/3] Knowledge-Base on port 8002
start "KB" cmd /c "cd /d D:\All projects\Cognitive-Loop-OS && .venv\Scripts\activate && python -m uvicorn Knowledge-Base.api:app --host 127.0.0.1 --port 8002"

echo.
echo All services launched:
echo   Cognitive-OS        http://127.0.0.1:8000/docs
echo   Inspiration-Research http://127.0.0.1:8001/docs
echo   Knowledge-Base       http://127.0.0.1:8002/docs
echo.
pause
