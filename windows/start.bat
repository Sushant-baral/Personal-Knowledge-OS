@echo off
REM Personal Knowledge OS launcher (Windows).
REM Put this file, run_backend.bat, and run_frontend.bat in the SAME
REM folder that contains your "backend" and "frontend" folders, then
REM double-click this file. No path editing needed — it uses its own
REM location automatically.

set BACKEND_PORT=8000
set FRONTEND_PORT=5173

echo Starting backend...
start "PKOS Backend" cmd /k "%~dp0run_backend.bat" %BACKEND_PORT%

echo Starting frontend...
start "PKOS Frontend" cmd /k "%~dp0run_frontend.bat" %FRONTEND_PORT%

echo Waiting for the app to be ready...
timeout /t 6 /nobreak > nul

start http://localhost:%FRONTEND_PORT%

echo.
echo Personal Knowledge OS is running.
echo Close the two server windows to stop it.
pause
