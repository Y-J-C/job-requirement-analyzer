$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment is missing. Create .venv and install apps/api[dev] first."
}

Push-Location $repoRoot
$previousAppEnv = $env:APP_ENV
$previousPublicAppEnv = $env:NEXT_PUBLIC_APP_ENV
$previousApiBaseUrl = $env:NEXT_PUBLIC_API_BASE_URL
$previousE2eApiBaseUrl = $env:E2E_API_BASE_URL
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:18000"
$env:E2E_API_BASE_URL = "http://localhost:18000"
if ($env:RUN_DEEPSEEK_E2E -eq "1") {
    $env:APP_ENV = "development"
    $env:NEXT_PUBLIC_APP_ENV = "development"
}
else {
    $env:APP_ENV = "e2e"
    $env:NEXT_PUBLIC_APP_ENV = "e2e"
}
try {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    docker info *> $null
    $dockerInfoExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    if ($dockerInfoExitCode -ne 0) {
        throw "Docker Desktop is unavailable. Start Docker Desktop and retry."
    }

    $existingWorkers = @(
        Get-CimInstance Win32_Process |
            Where-Object { $_.CommandLine -match '\s-m\s+app\.worker(?:\s|$)' }
    )
    if ($existingWorkers.Count -gt 0) {
        $workerIds = ($existingWorkers | ForEach-Object { $_.ProcessId }) -join ", "
        throw "An existing app.worker process can steal E2E jobs (PID: $workerIds). Stop pnpm dev and retry."
    }

    docker compose up -d --wait postgres minio
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL or MinIO did not become healthy."
    }

    & $python -m alembic -c apps/api/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed."
    }

    corepack pnpm exec playwright test @args
    exit $LASTEXITCODE
}
finally {
    if ($null -eq $previousAppEnv) {
        Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue
    }
    else {
        $env:APP_ENV = $previousAppEnv
    }
    if ($null -eq $previousPublicAppEnv) {
        Remove-Item Env:NEXT_PUBLIC_APP_ENV -ErrorAction SilentlyContinue
    }
    else {
        $env:NEXT_PUBLIC_APP_ENV = $previousPublicAppEnv
    }
    if ($null -eq $previousApiBaseUrl) {
        Remove-Item Env:NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
    }
    else {
        $env:NEXT_PUBLIC_API_BASE_URL = $previousApiBaseUrl
    }
    if ($null -eq $previousE2eApiBaseUrl) {
        Remove-Item Env:E2E_API_BASE_URL -ErrorAction SilentlyContinue
    }
    else {
        $env:E2E_API_BASE_URL = $previousE2eApiBaseUrl
    }
    Pop-Location
}
