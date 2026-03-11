[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Environment = "production",
    [Parameter(Mandatory = $true)]
    [string]$BackupDir
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")
$ComposeFile = Join-Path $RootDir "compose/$Environment/docker-compose.yaml"
$GlobalEnv = Join-Path $RootDir "env/global.env"
$ApiEnv = Join-Path $RootDir "env/api.env"
$PostgresEnv = Join-Path $RootDir "env/postgres.env"

foreach ($Path in @($ComposeFile, $GlobalEnv, $ApiEnv, $PostgresEnv)) {
    if (-not (Test-Path $Path)) {
        throw "Missing required file: $Path"
    }
}

$BackupDir = [System.IO.Path]::GetFullPath($BackupDir)
$DumpPath = Join-Path $BackupDir "postgres.sql"
$DataArchive = Join-Path $BackupDir "obsura-data.tgz"

foreach ($Path in @($DumpPath, $DataArchive)) {
    if (-not (Test-Path $Path)) {
        throw "Missing required backup artifact: $Path"
    }
}

$Vars = @{}
foreach ($Line in Get-Content $GlobalEnv, $PostgresEnv) {
    if (-not $Line -or $Line.Trim().StartsWith("#")) {
        continue
    }

    $Name, $Value = $Line -split "=", 2
    if (-not $Name) {
        continue
    }

    $Vars[$Name.Trim()] = $Value.Trim().Trim('"')
}

$ComposeArgs = @(
    "compose"
    "--env-file", $GlobalEnv
    "--env-file", $PostgresEnv
    "--env-file", $ApiEnv
    "-f", $ComposeFile
)

$PostgresUser = $Vars["POSTGRES_USER"]
$PostgresDb = $Vars["POSTGRES_DB"]
$StorageVolume = if ($Vars.ContainsKey("OBSURA_STORAGE_VOLUME")) { $Vars["OBSURA_STORAGE_VOLUME"] } else { "obsura-storage" }

Write-Host "Stopping API before restore..."
docker @ComposeArgs stop api | Out-Null

Write-Host "Starting postgres for restore..."
docker @ComposeArgs up -d postgres

Write-Host "Waiting for postgres readiness..."
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker @ComposeArgs exec -T postgres pg_isready -U $PostgresUser -d postgres *> $null
    if ($LASTEXITCODE -eq 0) {
        $Ready = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $Ready) {
    throw "Postgres did not become ready in time."
}

Write-Host "Restoring Obsura storage volume..."
docker run --rm `
    --mount "type=volume,source=$StorageVolume,target=/target" `
    --mount "type=bind,source=$BackupDir,target=/backup,readonly" `
    alpine:3.20 `
    sh -ec "find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/obsura-data.tgz -C /target"

Write-Host "Resetting database..."
docker @ComposeArgs exec -T postgres psql -U $PostgresUser -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS `"$PostgresDb`";"
docker @ComposeArgs exec -T postgres psql -U $PostgresUser -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE `"$PostgresDb`";"

Write-Host "Loading PostgreSQL dump..."
Get-Content -Raw $DumpPath | docker @ComposeArgs exec -T postgres psql -U $PostgresUser -d $PostgresDb -v ON_ERROR_STOP=1

Write-Host "Re-applying storage permissions..."
docker @ComposeArgs run --rm --no-deps volume-init

Write-Host "Starting full stack..."
docker @ComposeArgs up -d

Write-Host "Restore complete."
