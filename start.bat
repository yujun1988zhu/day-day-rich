@echo off
REM AlphaScanner 后台运行脚本
REM 此脚本会在后台启动 Streamlit 服务

cd /d "%~dp0"

echo ========================================
echo    AlphaScanner 正在后台启动...
echo ========================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先安装依赖
    echo 请运行: python -m venv venv && venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM 在后台启动 Streamlit
start "" /MIN venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.headless true

echo [成功] AlphaScanner 已在后台启动
echo.
echo 访问地址: http://localhost:8501
echo.
echo 提示: 
echo   - 可在浏览器中打开上述地址访问应用
echo   - 如需停止服务，请在任务管理器中结束 python.exe 进程
echo   - 或使用本目录下的 stop.bat 脚本停止服务
echo.
timeout /t 3 >nul
