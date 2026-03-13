@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM Disease Analysis Agent Startup Script (Conda Version)

echo ========================================
echo 疾病分析智能体启动脚本
echo ========================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 conda 命令
    echo 请确保 Anaconda 或 Miniconda 已安装并添加到 PATH
    echo.
    pause
    exit /b 1
)

REM Activate conda environment
echo [1/2] 激活 Conda 环境 thesis_env...
call conda activate thesis_env
if %errorlevel% neq 0 (
    echo [错误] 无法激活环境 thesis_env
    echo 请确保环境已创建: conda create -n thesis_env python=3.9
    echo.
    pause
    exit /b 1
)
echo     [OK] 环境已激活

REM Load environment variables from .env file
echo [2/2] 加载环境变量...
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        REM Skip empty lines and comments
        if not "%%a"=="" if not "%%a"=="#" (
            set "%%a=%%b"
        )
    )
    echo     [OK] API Key 已从 .env 文件加载
) else (
    echo     [警告] 未找到 .env 文件
)

REM Verify API Key
if defined DASHSCOPE_API_KEY (
    echo     [OK] DASHSCOPE_API_KEY 已设置
    goto env_ready
)

REM If API Key not set, prompt user
echo     [错误] DASHSCOPE_API_KEY 未设置
echo.
echo 请选择:
echo   1. 创建 .env 文件
echo   2. 手动输入 API Key (临时)
echo   3. 退出
echo.
set /p choice="请输入选项 (1-3): "

if "!choice!"=="1" (
    echo.
    set /p api_key="请输入您的 DashScope API Key: "
    echo DASHSCOPE_API_KEY=!api_key!> .env
    echo     [OK] .env 文件已创建
    set "DASHSCOPE_API_KEY=!api_key!"
) else if "!choice!"=="2" (
    echo.
    set /p api_key="请输入您的 DashScope API Key: "
    set "DASHSCOPE_API_KEY=!api_key!"
    echo     [OK] API Key 已设置 (临时)
) else (
    echo 退出中...
    pause
    exit /b 0
)

:env_ready
echo.
echo ========================================
echo 环境准备完成
echo ========================================
echo.
echo 可用命令:
echo   python test_geo_downloader.py          - 测试数据下载
echo   python run_auto_analysis.py --mode single  - 单次分析
echo   python run_auto_analysis.py --mode batch   - 批量分析
echo.
echo Conda 环境已激活，API Key 已设置
echo 现在可以运行任何命令！
echo.
echo ========================================
echo.

REM Keep command prompt open with conda environment
cmd /k
