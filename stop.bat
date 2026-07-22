@echo off
REM AlphaScanner 停止脚本
REM 此脚本会停止所有正在运行的 Streamlit/Python 服务

echo ========================================
echo    正在停止 AlphaScanner 服务...
echo ========================================
echo.

REM 查找并终止 python.exe 进程（运行 streamlit 的）
taskkill /F /FI "WINDOWTITLE eq *streamlit*" /IM python.exe 2>nul
if %errorlevel% == 0 (
    echo [成功] 已停止 Streamlit 服务
) else (
    echo [提示] 未找到正在运行的 Streamlit 服务
)

echo.
echo 服务已停止
timeout /t 2 >nul
