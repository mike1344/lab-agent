param(
    [switch]$SkipInstall,
    [switch]$SkipFrontend
)

# ASCII-only output: Windows PowerShell 5.1 may mis-parse non-BOM UTF-8 scripts.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "fronted"

function Assert-ExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

Write-Host "== backend ==" -ForegroundColor Cyan
Set-Location $Backend

if (-not (Test-Path ".venv")) {
    Write-Host "create virtualenv .venv"
    python -m venv .venv
    Assert-ExitCode "venv creation"
}

$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not $SkipInstall) {
    Write-Host "install dependencies (requirements.txt lock)"
    & $Python -m pip install --upgrade pip
    Assert-ExitCode "pip upgrade"
    if (Test-Path "requirements.txt") {
        & $Python -m pip install -r requirements.txt
        Assert-ExitCode "pip install"
    }
    else {
        & $Python -m pip install -r requirements-all.txt
        Assert-ExitCode "pip install"
    }
}

Write-Host "ruff check / format"
& $Python -m ruff check .
Assert-ExitCode "ruff check"
& $Python -m ruff format --check .
Assert-ExitCode "ruff format"

Write-Host "backend tests (isolated sqlite, no dev mysql)"
& $Python -m unittest discover -s tests
Assert-ExitCode "backend tests"

Write-Host "alembic migrations (temporary sqlite, from zero)"
& $Python scripts\check_migrations.py
Assert-ExitCode "migration check"

Write-Host "RAG evaluation (current provider)"
& $Python scripts\eval_rag.py
Assert-ExitCode "RAG evaluation"

if (-not $SkipFrontend) {
    Write-Host "== frontend ==" -ForegroundColor Cyan
    Set-Location $Frontend
    if (-not $SkipInstall) {
        npm ci
        Assert-ExitCode "npm ci"
    }
    npm test
    Assert-ExitCode "frontend tests"
    npm run build
    Assert-ExitCode "frontend build"
    Write-Host "icon import guard"
    & $Python (Join-Path $Backend "scripts\check_icon_imports.py")
    Assert-ExitCode "icon import guard"
}

Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
exit 0
