@echo off
cd /d C:\Users\jeffp\AlientAI_Start_Over_8010
call .venv\Scripts\activate.bat
python -m uvicorn main:app --host 127.0.0.1 --port 8010
pause
