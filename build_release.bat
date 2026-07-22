@echo off
REM AlphaScanner 自动打包脚本
REM 此脚本会自动安装 PyInstaller 并打包程序为独立 exe 文件

cd /d "%~dp0"

echo ========================================
echo    AlphaScanner 自动打包工具
echo ========================================
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境！
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

echo [1/5] 激活虚拟环境...
call venv\Scripts\activate.bat

echo.
echo [2/5] 安装 PyInstaller...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo.
echo [3/5] 清理旧的打包文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "AlphaScanner.spec" del /q AlphaScanner.spec

echo.
echo [4/5] 开始打包（单文件模式）...
echo 这可能需要 3-5 分钟，请耐心等待...
echo.

pyinstaller --onefile ^
    --name="AlphaScanner" ^
    --add-data "data;data" ^
    --add-data ".streamlit;.streamlit" ^
    --hidden-import=pandas ^
    --hidden-import=numpy ^
    --hidden-import=mplfinance ^
    --hidden-import=matplotlib ^
    --collect-all streamlit ^
    --log-level=WARN ^
    app.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败！请检查上方错误信息
    pause
    exit /b 1
)

echo.
echo [5/5] 整理发布包...

REM 创建发布目录
set RELEASE_DIR=AlphaScanner_Release
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"

REM 复制主程序
copy "dist\AlphaScanner.exe" "%RELEASE_DIR%\" >nul

REM 复制启动脚本
(
echo @echo off
echo cd /d "%%~dp0"
echo.
echo echo ========================================
echo echo    AlphaScanner 正在启动...
echo echo ========================================
echo echo.
echo start "" /MIN AlphaScanner.exe
echo.
echo echo [成功] AlphaScanner 已启动
echo echo.
echo echo 访问地址: http://localhost:8501
echo echo.
echo echo 提示: 
echo echo   - 首次启动较慢，请耐心等待
echo echo   - 可在浏览器中打开上述地址访问应用
echo echo   - 如需停止服务，请在任务管理器中结束 AlphaScanner.exe 进程
echo echo.
echo timeout /t 3 ^>nul
) > "%RELEASE_DIR%\start.bat"

REM 复制停止脚本
(
echo @echo off
echo echo ========================================
echo echo    正在停止 AlphaScanner 服务...
echo echo ========================================
echo echo.
echo taskkill /F /IM AlphaScanner.exe 2^>nul
echo if %%errorlevel%% == 0 ^(
echo     echo [成功] 已停止服务
echo ^) else ^(
echo     echo [提示] 未找到正在运行的服务
echo ^)
echo echo.
echo timeout /t 2 ^>nul
) > "%RELEASE_DIR%\stop.bat"

REM 复制使用说明
copy "README_使用说明.md" "%RELEASE_DIR%\" >nul

REM 创建快速上手说明
(
echo # AlphaScanner 快速上手
echo.
echo ## 第一次使用
echo 1. 解压本文件夹到任意位置（建议不要放在C盘）
echo 2. 双击 **start.bat** 启动程序
echo 3. 等待 3-5 秒后，浏览器会自动打开或手动访问: http://localhost:8501
echo 4. 开始使用！
echo.
echo ## 日常使用
echo - 启动: 双击 start.bat
echo - 停止: 双击 stop.bat
echo.
echo ## 注意事项
echo - 首次启动较慢（约10-30秒），后续启动会快很多
echo - 程序会在后台运行，关闭浏览器不会停止服务
echo - 如需彻底停止，请双击 stop.bat 或在任务管理器结束 AlphaScanner.exe
echo.
echo ## 常见问题
echo Q: 启动后浏览器打不开？
echo A: 手动在浏览器地址栏输入 http://localhost:8501
echo.
echo Q: 提示端口被占用？
echo A: 先双击 stop.bat 停止旧服务，再重新启动
echo.
echo Q: 数据不更新？
echo A: 点击左侧边栏的 "刷新全市场数据" 按钮
echo.
echo ## 技术支持
echo 如遇问题，请联系程序提供者或查看完整文档 README_使用说明.md
) > "%RELEASE_DIR%\快速上手.md"

echo.
echo ========================================
echo    打包完成！
echo ========================================
echo.
echo 发布包位置: %CD%\%RELEASE_DIR%\
echo.
echo 包含文件:
echo   - AlphaScanner.exe      ^(主程序^)
echo   - start.bat             ^(启动脚本^)
echo   - stop.bat              ^(停止脚本^)
echo   - 快速上手.md           ^(简易说明^)
echo   - README_使用说明.md    ^(完整文档^)
echo.
echo 下一步操作:
echo   1. 测试运行: 进入 %RELEASE_DIR% 目录，双击 start.bat
echo   2. 压缩分发: 右键 %RELEASE_DIR% 文件夹 → 发送到 → 压缩(zipped)文件夹
echo   3. 分享给朋友: 发送压缩后的 ZIP 文件
echo.
pause
