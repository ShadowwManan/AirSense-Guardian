@echo off
echo ========================================
echo     AirSense Guardian - Starting Up
echo ========================================
echo.

echo [1/2] Starting Backend Server...
start "AirSense Backend" cmd /k "cd /d %~dp0backend && python main.py"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Frontend Server...
start "AirSense Frontend" cmd /k "cd /d %~dp0frontend && python server.py"

echo.
echo ========================================
echo  Backend  ->  check the Backend window
echo  Frontend ->  http://localhost:3000
echo ========================================
echo.
echo Both servers are starting in separate windows.
echo Close those windows to stop the servers.
pause
