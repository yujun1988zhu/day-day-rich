@echo off
REM AlphaScanner 一键压缩脚本
REM 此脚本会将 AlphaScanner_Release 文件夹压缩成 ZIP 文件

cd /d "%~dp0"

echo ========================================
echo    AlphaScanner 压缩打包工具
echo ========================================
echo.

REM 检查发布目录是否存在
if not exist "AlphaScanner_Release" (
    echo [错误] 未找到 AlphaScanner_Release 文件夹！
    echo 请先运行 build_release_en.ps1 进行打包
    pause
    exit /b 1
)

REM 删除旧的 ZIP 文件（如果存在）
if exist "AlphaScanner_Release.zip" (
    echo [提示] 发现旧的 ZIP 文件，正在删除...
    del /q AlphaScanner_Release.zip
)

echo [1/2] 正在压缩文件夹...
echo.

REM 使用 PowerShell 进行压缩
powershell -Command "Compress-Archive -Path AlphaScanner_Release -DestinationPath AlphaScanner_Release.zip -Force"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 压缩失败！
    pause
    exit /b 1
)

echo.
echo [2/2] 压缩完成！
echo.

REM 获取文件大小
for %%A in ("AlphaScanner_Release.zip") do set size=%%~zA
set /a sizeMB=%size%/1048576

echo ========================================
echo    压缩成功！
echo ========================================
echo.
echo 文件位置: %CD%\AlphaScanner_Release.zip
echo 文件大小: 约 %sizeMB% MB
echo.
echo 下一步操作:
echo   1. 将 ZIP 文件发送给朋友
echo   2. 告诉朋友解压后双击 start.bat 即可使用
echo   3. 查看"分发指南.md"获取更多帮助
echo.
pause
