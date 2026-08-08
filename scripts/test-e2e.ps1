$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment is missing. Create .venv and install apps/api[dev] first."
}

Push-Location $repoRoot
try {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    docker info *> $null
    $dockerInfoExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    if ($dockerInfoExitCode -ne 0) {
        throw "Docker Desktop is unavailable. Start Docker Desktop and retry."
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
    Pop-Location
}
