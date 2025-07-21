@echo off
echo.
echo ========================================
echo  HarvestBot Authentication API Starter
echo ========================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

echo Python is installed ✓
echo.

echo Installing/updating dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo The API might still work with existing packages
    echo.
)

echo.
echo Starting HarvestBot Authentication API...
echo.
echo API will be available at: http://localhost:5000
echo API Documentation: http://localhost:5000/docs
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python start_auth_api.py

echo.
echo Server stopped.
pause
