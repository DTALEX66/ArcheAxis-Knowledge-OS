python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
python -m app.container_entrypoint core
