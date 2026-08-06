$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     AI-PM v1.0.0 - 通维AI项目管理系统          ║" -ForegroundColor Cyan
Write-Host "  ║     开箱即用 · 自动安装依赖 · 同源托管前后端   ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$backendDir = Join-Path $PSScriptRoot "backend"
Set-Location $backendDir

$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }
if (-not $py) {
    Write-Host "[错误] 未找到 Python。" -ForegroundColor Red
    Read-Host "按回车退出"; exit 1
}
Write-Host "[环境] 使用 $py ($(& $py --version 2>&1))" -ForegroundColor Green

if (-not (Test-Path "venv")) {
    Write-Host "[1/3] 首次运行，正在创建虚拟环境..." -ForegroundColor Yellow
    & $py -m venv venv
    if ($LASTEXITCODE -ne 0) { Write-Host "[错误] 无法创建虚拟环境。" -ForegroundColor Red; Read-Host "按回车退出"; exit 1 }
    Write-Host "虚拟环境创建完成" -ForegroundColor Green
} else {
    Write-Host "[1/3] 虚拟环境已存在，跳过创建" -ForegroundColor Green
}

Write-Host "[2/3] 激活虚拟环境并安装依赖..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
pip install --upgrade pip -q
pip install -r requirements.txt -q 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在使用默认源重试安装依赖..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "[错误] 依赖安装失败。" -ForegroundColor Red; Read-Host "按回车退出"; exit 1 }
}
Write-Host "依赖安装完成" -ForegroundColor Green

Write-Host "[3/3] 启动系统..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ┌──────────────────────────────────────────────┐" -ForegroundColor Green
Write-Host "  │  系统启动中（首次会自动建库并创建管理员）...   │" -ForegroundColor Green
Write-Host "  │  启动成功后请访问: http://localhost:8000      │" -ForegroundColor Green
Write-Host "  │  API文档: http://localhost:8000/docs          │" -ForegroundColor Green
Write-Host "  │  首次启动前请在 backend/.env 设置强管理员密码   │" -ForegroundColor Green
Write-Host "  │  （≥12位，含大小写字母+数字+特殊字符）          │" -ForegroundColor Green
Write-Host "  │  按 Ctrl+C 停止服务                          │" -ForegroundColor Green
Write-Host "  └──────────────────────────────────────────────┘" -ForegroundColor Green
Write-Host ""

Start-Process cmd -ArgumentList "/c","timeout /t 6 /nobreak >nul && start http://localhost:8000" -WindowStyle Hidden
# 使用已激活虚拟环境内的 python 启动服务（$py 为系统发现路径，需用 venv 内 python 避免缺少依赖导致 ImportError）
& ".\venv\Scripts\python.exe" serve.py
