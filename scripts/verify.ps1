# ============================================================
# 一键验证：从空环境安装依赖 → lint → 后端回归测试 → 前端构建
#
# 用法（仓库根目录）：
#   pwsh -File scripts/verify.ps1             # 全量
#   pwsh -File scripts/verify.ps1 -SkipFrontend
#   pwsh -File scripts/verify.ps1 -SkipInstall   # 依赖已装好时只跑检查
# ============================================================
param(
    [switch]$SkipInstall,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "fronted"

Write-Host "== 后端 ==" -ForegroundColor Cyan
Set-Location $Backend

if (-not (Test-Path ".venv")) {
    Write-Host "创建虚拟环境 .venv"
    python -m venv .venv
}

$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not $SkipInstall) {
    Write-Host "安装依赖（requirements.txt 为完整锁定版本）"
    & $Python -m pip install --upgrade pip
    if (Test-Path "requirements.txt") {
        & $Python -m pip install -r requirements.txt
    }
    else {
        & $Python -m pip install -r requirements-all.txt
    }
}

Write-Host "ruff check / format"
& $Python -m ruff check .
& $Python -m ruff format --check .

Write-Host "后端回归测试（独立 SQLite，不会连接开发 MySQL）"
& $Python -m unittest discover -s tests

if (-not $SkipFrontend) {
    Write-Host "== 前端 ==" -ForegroundColor Cyan
    Set-Location $Frontend
    if (-not $SkipInstall) {
        npm ci
    }
    npm test
    npm run build
}

Write-Host "全部检查通过 ✅" -ForegroundColor Green
