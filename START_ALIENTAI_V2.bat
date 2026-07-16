@echo off
cd /d C:\Users\jeffp\AlientAI_Start_Over_8010
call .venv\Scripts\activate.bat
python -m uvicorn main:app --host 0.0.0.0 --port 8010
pause
