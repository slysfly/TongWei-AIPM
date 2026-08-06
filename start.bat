@echo off
chcp 65001 >nul
title 通维AI项目管理系统

echo ==========================================
echo   通维AI项目管理系统 - 安装启动
echo ==========================================

cd /d "%~dp0backend"

:: 1. 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)
echo [OK] Python 检查通过

:: 2. 检查/创建虚拟环境
if not exist "venv" (
    echo [..] 创建虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate.bat

:: 3. 安装依赖
echo [..] 安装依赖...
pip install -r requirements.txt -q 2>nul
echo [OK] 依赖安装完成

:: 4. 配置环境
if not exist ".env" (
    echo [..] 从 .env.example 创建 .env...
    copy .env.example .env >nul
    echo [WARN] 请编辑 backend\.env 修改 SECRET_KEY 和 LLM API Keys
)

:: 5. 初始化数据库
echo [..] 初始化数据库...
python -c "import asyncio; from app.core.migrate import apply_migrations; asyncio.run(apply_migrations())"
echo [OK] 数据库初始化完成

:: 6. 启动服务
echo.
echo ==========================================
echo   🚀 启动服务...
echo   访问: http://localhost:8000
echo ==========================================
python serve.py

pause
