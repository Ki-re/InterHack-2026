$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail {
    param([string]$Message)
    Write-Host ""
    Write-Host "Startup failed: $Message" -ForegroundColor Red
    exit 1
}

function Invoke-Docker {
    param(
        [string[]]$Arguments,
        [string]$FailureMessage
    )

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

try {
    & docker --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker check failed."
    }
}
catch {
    Fail "Docker is not installed or is not available on PATH."
}

try {
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose check failed."
    }
}
catch {
    Fail "Docker Compose v2 is not available. Install Docker Desktop or enable the Compose plugin."
}

if (-not (Test-Path ".env")) {
    if (-not (Test-Path ".env.example")) {
        Fail ".env.example is missing."
    }

    Copy-Item ".env.example" ".env"
    Write-Step "Created .env from .env.example"
}

$dbPath = Join-Path $root "back\app.db"

Write-Step "Building backend image and running Alembic migrations"

try {
    Invoke-Docker -Arguments @("compose", "build", "backend") -FailureMessage "Could not build the backend image."
    Invoke-Docker -Arguments @("compose", "run", "--rm", "backend", "alembic", "upgrade", "head") -FailureMessage "Alembic migrations failed."
}
catch {
    if (-not (Test-Path $dbPath)) {
        # Only clean up if the DB was never created (avoid wiping existing data on partial failure)
    }

    Fail $_.Exception.Message
}

Write-Host ""
Write-Host "Frontend:     http://localhost:5173" -ForegroundColor Green
Write-Host "Backend:      http://localhost:8000" -ForegroundColor Green
Write-Host "FastAPI docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

Write-Step "Starting Docker Compose"

try {
    Invoke-Docker -Arguments @("compose", "up", "--build") -FailureMessage "docker compose up --build exited with an error."
}
catch {
    Fail $_.Exception.Message
}
