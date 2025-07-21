# HarvestBot Authentication API Starter (PowerShell)
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " HarvestBot Authentication API Starter" -ForegroundColor Cyan  
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python is installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python and try again" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`nInstalling/updating dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some dependencies may have failed to install" -ForegroundColor Yellow
    Write-Host "The API might still work with existing packages`n" -ForegroundColor Yellow
}

Write-Host "`nStarting HarvestBot Authentication API..." -ForegroundColor Green
Write-Host "`nAPI will be available at: http://localhost:5000" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:5000/docs" -ForegroundColor Cyan
Write-Host "React Frontend should use: http://localhost:5000/api" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Start the API
try {
    python start_auth_api.py
} catch {
    Write-Host "`nError starting the API server" -ForegroundColor Red
    Write-Host "Please check the error messages above" -ForegroundColor Red
}

Write-Host "`nServer stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
