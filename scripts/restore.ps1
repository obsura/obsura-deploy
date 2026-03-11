[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Environment = "production",
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

Assert-ObsuraEnvironment -Environment $Environment
Assert-ObsuraDocker
Assert-ObsuraConfirmation -Confirmed $Yes.IsPresent

$RootDir = Get-ObsuraRepoRoot -ScriptPath $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $RootDir "compose/$Environment/docker-compose.yaml"
$GlobalEnv = Join-Path $RootDir "env/global.env"
$ApiEnv = Join-Path $RootDir "env/api.env"
$PostgresEnv = Join-Path $RootDir "env/postgres.env"

Assert-ObsuraFiles -Paths @($ComposeFile, $GlobalEnv, $ApiEnv, $PostgresEnv)

$BackupDir = [System.IO.Path]::GetFullPath($BackupDir)
$DumpPath = Join-Path $BackupDir "postgres.sql"
$DataArchive = Join-Path $BackupDir "obsura-data.tgz"
Assert-ObsuraFiles -Paths @($DumpPath, $DataArchive)

$Vars = Get-ObsuraEnvMap -Paths @($GlobalEnv, $PostgresEnv)
$PostgresUser = $Vars["POSTGRES_USER"]
$PostgresDb = $Vars["POSTGRES_DB"]
$StorageVolume = if ($Vars.ContainsKey("OBSURA_STORAGE_VOLUME")) { $Vars["OBSURA_STORAGE_VOLUME"] } else { "obsura-storage" }

if (-not $PostgresUser -or -not $PostgresDb) {
    throw "POSTGRES_USER and POSTGRES_DB must be set in env/postgres.env."
}

$ComposeArgs = Get-ObsuraComposeArgs -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv
Show-ObsuraStackContext -Environment $Environment -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -ApiEnv $ApiEnv -PostgresEnv $PostgresEnv -ImageRef $null
Write-Host "Restore source: $BackupDir"
Write-Host "Storage volume: $StorageVolume"

Write-Host "Stopping API before restore..."
docker @ComposeArgs stop api *> $null

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
