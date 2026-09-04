@echo off
cd /d "%~dp0backend"
if exist venv\Scripts\activate.bat (
  call venv\Scripts\activate.bat
)
uvicorn app.main:app --port %1 --reload
