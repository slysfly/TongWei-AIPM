@echo off
chcp 65001 >nul 2>&1
title AI-PM v1.0.0 - 通维AI项目管理系统

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   AI-PM v1.0.0 - 通维AI项目管理系统           ║
echo  ║     开箱即用 · 自动安装依赖 · 同源托管前后端   ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0backend"

set PY=
where py >nul 2>&1 && set PY=py
if not defined PY ( where python >nul 2>&1 && set PY=python )
if not defined PY ( where python3 >nul 2>&1 && set PY=python3 )
if not defined PY (
    echo [错误] 未找到 Python。请先安装 Python 3.11+ 并勾选 "Add to PATH"。
    pause
    exit /b 1
)

set PYVER=
for /f "tokens=2" %%v in ('%PY% --version 2^>^&1') do set PYVER=%%v
echo [环境] 使用 %PY% (版本 %PYVER%)

if not exist "venv" (
    echo [1/3] 首次运行，正在创建虚拟环境...
    %PY% -m venv venv
    if errorlevel 1 ( echo [错误] 无法创建虚拟环境。 & pause & exit /b 1 )
    echo 虚拟环境创建完成
) else (
    echo [1/3] 虚拟环境已存在，跳过创建
)

call venv\Scripts\activate.bat

REM 检查依赖是否已安装（预构建的 venv 中已有全部依赖）
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [2/3] 安装依赖（首次约 2-5 分钟，需联网）...
    pip install --upgrade pip -q
    pip install -r requirements.txt -q 2>nul
    if errorlevel 1 (
        echo 正在使用默认源重试安装依赖...
        pip install -r requirements.txt
        if errorlevel 1 ( echo [错误] 依赖安装失败。 & pause & exit /b 1 )
    )
    echo 依赖安装完成
) else (
    echo [2/3] 依赖已就绪，跳过安装
)

echo [3/3] 启动系统...
echo.
echo  ┌──────────────────────────────────────────────┐
echo  │  系统启动中（首次会自动建库并创建管理员）...   │
echo  │  启动成功后请访问: http://localhost:8000      │
echo  │  API文档: http://localhost:8000/docs          │
echo  │  首次启动前请在 backend/.env 设置强管理员密码   │
echo  │  （≥12位，含大小写字母+数字+特殊字符）          │
echo  │  按 Ctrl+C 停止服务                          │
echo  └──────────────────────────────────────────────┘
echo.

start "" cmd /c "timeout /t 6 /nobreak >nul && start http://localhost:8000"
REM 使用已激活虚拟环境内的 python 启动服务（避免系统 python 缺少依赖导致 ImportError）
python serve.py
pause
