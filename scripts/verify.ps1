param(
    [switch]$SkipInstall,
    [switch]$SkipFrontend
)

# ASCII-only output: Windows PowerShell 5.1 may mis-parse non-BOM UTF-8 scripts.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "fronted"

Write-Host "== backend ==" -ForegroundColor Cyan
Set-Location $Backend

if (-not (Test-Path ".venv")) {
    Write-Host "create virtualenv .venv"
    python -m venv .venv
}

$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not $SkipInstall) {
    Write-Host "install dependencies (requirements.txt lock)"
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

Write-Host "backend tests (isolated sqlite, no dev mysql)"
& $Python -m unittest discover -s tests

Write-Host "alembic migrations (temporary sqlite, from zero)"
& $Python scripts\check_migrations.py

Write-Host "RAG evaluation (current provider)"
& $Python scripts\eval_rag.py

if (-not $SkipFrontend) {
    Write-Host "== frontend ==" -ForegroundColor Cyan
    Set-Location $Frontend
    if (-not $SkipInstall) {
        npm ci
    }
    npm test
    npm run build
    Write-Host "icon import guard"
    & $Python (Join-Path $Backend "scripts\check_icon_imports.py")
}

Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
