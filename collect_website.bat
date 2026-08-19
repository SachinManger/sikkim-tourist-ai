@echo off
call .venv\Scripts\activate.bat
python -m agent.collector %1
pause
