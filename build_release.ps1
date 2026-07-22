# AlphaScanner 自动打包脚本 (PowerShell)
# 此脚本会自动安装 PyInstaller 并打包程序为独立 exe 文件

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   AlphaScanner 自动打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境
if (-not (Test-Path "$projectRoot\venv\Scripts\python.exe")) {
    Write-Host "[错误] 未找到虚拟环境！" -ForegroundColor Red
    Write-Host "请先运行: python -m venv venv" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "[1/5] 激活虚拟环境..." -ForegroundColor Green
& "$projectRoot\venv\Scripts\activate.ps1"

Write-Host ""
Write-Host "[2/5] 安装 PyInstaller..." -ForegroundColor Green
pip install pyinstaller -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] PyInstaller 安装失败" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "[3/5] 清理旧的打包文件..." -ForegroundColor Green
if (Test-Path "$projectRoot\dist") { Remove-Item -Recurse -Force "$projectRoot\dist" }
if (Test-Path "$projectRoot\build") { Remove-Item -Recurse -Force "$projectRoot\build" }
if (Test-Path "$projectRoot\AlphaScanner.spec") { Remove-Item -Force "$projectRoot\AlphaScanner.spec" }

Write-Host ""
Write-Host "[4/5] 开始打包（单文件模式）..." -ForegroundColor Green
Write-Host "这可能需要 3-5 分钟，请耐心等待..." -ForegroundColor Yellow
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
    Write-Host "[错误] 打包失败！请检查上方错误信息" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "[5/5] 整理发布包..." -ForegroundColor Green

# 创建发布目录
$releaseDir = "$projectRoot\AlphaScanner_Release"
if (Test-Path $releaseDir) { Remove-Item -Recurse -Force $releaseDir }
New-Item -ItemType Directory -Path $releaseDir | Out-Null

# 复制主程序
Copy-Item "$projectRoot\dist\AlphaScanner.exe" "$releaseDir\"

# 创建启动脚本
$startBat = @"
@echo off
cd /d "%~dp0"

echo ========================================
echo    AlphaScanner 正在启动...
echo ========================================
echo.

start "" /MIN AlphaScanner.exe

echo [成功] AlphaScanner 已启动
echo.
echo 访问地址: http://localhost:8501
echo.
echo 提示: 
echo   - 首次启动较慢，请耐心等待
echo   - 可在浏览器中打开上述地址访问应用
echo   - 如需停止服务，请在任务管理器中结束 AlphaScanner.exe 进程
echo.
timeout /t 3 >nul
"@
[System.IO.File]::WriteAllText("$releaseDir\start.bat", $startBat, [System.Text.Encoding]::Default)

# 创建停止脚本
$stopBat = @"
@echo off
echo ========================================
echo    正在停止 AlphaScanner 服务...
echo ========================================
echo.

taskkill /F /IM AlphaScanner.exe 2>nul
if %errorlevel% == 0 (
    echo [成功] 已停止服务
) else (
    echo [提示] 未找到正在运行的服务
)

echo.
timeout /t 2 >nul
"@
[System.IO.File]::WriteAllText("$releaseDir\stop.bat", $stopBat, [System.Text.Encoding]::Default)

# 复制使用说明
if (Test-Path "$projectRoot\README_使用说明.md") {
    Copy-Item "$projectRoot\README_使用说明.md" "$releaseDir\"
}

# 创建快速上手说明
$quickStart = @"
# AlphaScanner 快速上手

## 第一次使用
1. 解压本文件夹到任意位置（建议不要放在C盘）
2. 双击 **start.bat** 启动程序
3. 等待 3-5 秒后，浏览器会自动打开或手动访问: http://localhost:8501
4. 开始使用！

## 日常使用
- 启动: 双击 start.bat
- 停止: 双击 stop.bat

## 注意事项
- 首次启动较慢（约10-30秒），后续启动会快很多
- 程序会在后台运行，关闭浏览器不会停止服务
- 如需彻底停止，请双击 stop.bat 或在任务管理器结束 AlphaScanner.exe

## 常见问题
Q: 启动后浏览器打不开？
A: 手动在浏览器地址栏输入 http://localhost:8501

Q: 提示端口被占用？
A: 先双击 stop.bat 停止旧服务，再重新启动

Q: 数据不更新？
A: 点击左侧边栏的 "刷新全市场数据" 按钮

## 技术支持
如遇问题，请联系程序提供者或查看完整文档 README_使用说明.md
"@
[System.IO.File]::WriteAllText("$releaseDir\快速上手.md", $quickStart, [System.Text.UTF8Encoding]::new($true))

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   打包完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "发布包位置: $releaseDir\" -ForegroundColor Green
Write-Host ""
Write-Host "包含文件:" -ForegroundColor Yellow
Write-Host "  - AlphaScanner.exe      (主程序)"
Write-Host "  - start.bat             (启动脚本)"
Write-Host "  - stop.bat              (停止脚本)"
Write-Host "  - 快速上手.md           (简易说明)"
Write-Host "  - README_使用说明.md    (完整文档)"
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "  1. 测试运行: 进入 AlphaScanner_Release 目录，双击 start.bat"
Write-Host "  2. 压缩分发: 右键 AlphaScanner_Release 文件夹 → 发送到 → 压缩(zipped)文件夹"
Write-Host "  3. 分享给朋友: 发送压缩后的 ZIP 文件"
Write-Host ""

Read-Host "按回车键退出"
