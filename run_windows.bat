python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --no-proxy-headers
