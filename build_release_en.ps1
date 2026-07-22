# AlphaScanner Auto Build Script (English Version)
# This script will install PyInstaller and package the app into a standalone exe

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   AlphaScanner Auto Build Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not (Test-Path "$projectRoot\venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/5] Activating virtual environment..." -ForegroundColor Green
& "$projectRoot\venv\Scripts\activate.ps1"

Write-Host ""
Write-Host "[2/5] Installing PyInstaller..." -ForegroundColor Green
pip install pyinstaller -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller installation failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[3/5] Cleaning old build files..." -ForegroundColor Green
if (Test-Path "$projectRoot\dist") { Remove-Item -Recurse -Force "$projectRoot\dist" }
if (Test-Path "$projectRoot\build") { Remove-Item -Recurse -Force "$projectRoot\build" }
if (Test-Path "$projectRoot\AlphaScanner.spec") { Remove-Item -Force "$projectRoot\AlphaScanner.spec" }

Write-Host ""
Write-Host "[4/5] Building executable (single file mode)..." -ForegroundColor Green
Write-Host "This may take 3-5 minutes, please wait..." -ForegroundColor Yellow
Write-Host ""

pyinstaller --onefile `
    --name="AlphaScanner" `
    --add-data "data;data" `
    --add-data ".streamlit;.streamlit" `
    --hidden-import=pandas `
    --hidden-import=numpy `
    --hidden-import=mplfinance `
    --hidden-import=matplotlib `
    --collect-all streamlit `
    --log-level=WARN `
    app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Build failed! Please check error messages above" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[5/5] Preparing release package..." -ForegroundColor Green

# Create release directory
$releaseDir = "$projectRoot\AlphaScanner_Release"
if (Test-Path $releaseDir) { Remove-Item -Recurse -Force $releaseDir }
New-Item -ItemType Directory -Path $releaseDir | Out-Null

# Copy main executable
Copy-Item "$projectRoot\dist\AlphaScanner.exe" "$releaseDir\"

# Create start script
$startBat = @"
@echo off
cd /d "%~dp0"

echo ========================================
echo    Starting AlphaScanner...
echo ========================================
echo.

start "" /MIN AlphaScanner.exe

echo [OK] AlphaScanner started successfully
echo.
echo Access URL: http://localhost:8501
echo.
echo Tips: 
echo   - First startup may be slow, please wait patiently
echo   - Open the URL above in your browser to access the app
echo   - To stop the service, end AlphaScanner.exe in Task Manager
echo.
timeout /t 3 >nul
"@
[System.IO.File]::WriteAllText("$releaseDir\start.bat", $startBat, [System.Text.Encoding]::Default)

# Create stop script
$stopBat = @"
@echo off
echo ========================================
echo    Stopping AlphaScanner Service...
echo ========================================
echo.

taskkill /F /IM AlphaScanner.exe 2>nul
if %errorlevel% == 0 (
    echo [OK] Service stopped
) else (
    echo [INFO] No running service found
)

echo.
timeout /t 2 >nul
"@
[System.IO.File]::WriteAllText("$releaseDir\stop.bat", $stopBat, [System.Text.Encoding]::Default)

# Copy user manual if exists
if (Test-Path "$projectRoot\README_使用说明.md") {
    Copy-Item "$projectRoot\README_使用说明.md" "$releaseDir\"
}

# Create quick start guide (English)
$quickStart = @"
# AlphaScanner Quick Start Guide

## First Time Use
1. Extract this folder to any location (avoid C drive)
2. Double-click **start.bat** to launch the program
3. Wait 3-5 seconds, then open your browser to: http://localhost:8501
4. Start using!

## Daily Use
- Start: Double-click start.bat
- Stop: Double-click stop.bat

## Important Notes
- First startup is slower (10-30 seconds), subsequent startups are faster
- The program runs in background; closing the browser won't stop it
- To completely stop, double-click stop.bat or end AlphaScanner.exe in Task Manager

## FAQ
Q: Browser doesn't open after startup?
A: Manually enter http://localhost:8501 in your browser's address bar

Q: Port already in use?
A: Double-click stop.bat first, then restart

Q: Data not updating?
A: Click "Refresh Market Data" button in the left sidebar

## Support
If you encounter issues, contact the provider or refer to README_使用说明.md
"@
[System.IO.File]::WriteAllText("$releaseDir\Quick_Start.md", $quickStart, [System.Text.UTF8Encoding]::new($true))

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   BUILD COMPLETED!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Release Location: $releaseDir\" -ForegroundColor Green
Write-Host ""
Write-Host "Package Contents:" -ForegroundColor Yellow
Write-Host "  - AlphaScanner.exe      (Main application)"
Write-Host "  - start.bat             (Start script)"
Write-Host "  - stop.bat              (Stop script)"
Write-Host "  - Quick_Start.md        (Quick guide)"
Write-Host "  - README_使用说明.md    (Full documentation)"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Test: Go to AlphaScanner_Release folder, double-click start.bat"
Write-Host "  2. Compress: Right-click AlphaScanner_Release -> Send to -> Compressed (zipped) folder"
Write-Host "  3. Share: Send the ZIP file to your friends"
Write-Host ""

Read-Host "Press Enter to exit"
