@echo off
echo.
echo ============================================
echo  HarvestBot Complete API Server Starter
echo ============================================
echo This includes authentication and bot management endpoints.
echo Port: 5001 (can be changed in .env file)
echo.

echo Checking Python installation...
"C:\Users\acer\AppData\Local\Programs\Python\Python310\python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not found at expected location
    echo Please check Python installation
    pause
    exit /b 1
)

echo Python is installed ✓
echo.

echo Starting HarvestBot Complete API Server...
echo This server provides:
echo - Authentication endpoints (/api/auth/*)
echo - Bot management endpoints (/api/bots/*)
echo - Memory management endpoints (/api/bots/memories/*)
echo - Dashboard stats endpoints (/api/bots/dashboard/*)
echo.
echo Press Ctrl+C to stop the server
echo.

"C:\Users\acer\AppData\Local\Programs\Python\Python310\python.exe" start_complete_api.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start the API server
    echo Check the error messages above for details
)

echo.
echo Server has stopped
pause
