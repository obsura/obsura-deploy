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
$PostgresPassword = $Vars["POSTGRES_PASSWORD"]
$StorageVolume = if ($Vars.ContainsKey("OBSURA_STORAGE_VOLUME")) { $Vars["OBSURA_STORAGE_VOLUME"] } else { "obsura-storage" }
$ApiImage = Get-ObsuraStackApiImage -ComposeFile $ComposeFile

if (-not $PostgresUser -or -not $PostgresDb -or -not $PostgresPassword) {
    throw "POSTGRES_USER, POSTGRES_DB, and POSTGRES_PASSWORD must be set in env/postgres.env."
}

Assert-ObsuraRealImageReference -ImageRef $ApiImage

$ComposeArgs = Get-ObsuraComposeArgs -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv
Show-ObsuraStackContext -Environment $Environment -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -ApiEnv $ApiEnv -PostgresEnv $PostgresEnv -ImageRef $ApiImage
Write-Host "Restore source: $BackupDir"
Write-Host "Storage volume: $StorageVolume"
Write-Host "Restore will replace the current database and the full contents of $StorageVolume."

$MetadataPath = Join-Path $BackupDir "metadata.txt"
if (Test-Path $MetadataPath) {
    Write-Host "Backup metadata:"
    Get-Content $MetadataPath | ForEach-Object { Write-Host "  $_" }
}

Ensure-ObsuraDockerVolume -VolumeName $StorageVolume

Write-Host "Stopping API before restore..."
docker @ComposeArgs stop api *> $null

Write-Host "Starting postgres for restore..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("up", "-d", "postgres")) -Context "docker compose up postgres for restore"

Write-Host "Waiting for postgres readiness..."
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker @ComposeArgs exec -T -e PGPASSWORD=$PostgresPassword postgres pg_isready -U $PostgresUser -d postgres *> $null
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
Invoke-ObsuraNative -FilePath "docker" -ArgumentList @(
    "run"
    "--rm"
    "--mount", "type=volume,source=$StorageVolume,target=/target"
    "--mount", "type=bind,source=$BackupDir,target=/backup,readonly"
    "alpine:3.20"
    "sh"
    "-ec"
    "find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/obsura-data.tgz -C /target"
) -Context "storage restore"

Write-Host "Resetting database..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("exec", "-T", "-e", "PGPASSWORD=$PostgresPassword", "postgres", "psql", "-U", $PostgresUser, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "DROP DATABASE IF EXISTS `"$PostgresDb`";")) -Context "drop database for restore"
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("exec", "-T", "-e", "PGPASSWORD=$PostgresPassword", "postgres", "psql", "-U", $PostgresUser, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "CREATE DATABASE `"$PostgresDb`";")) -Context "create database for restore"

Write-Host "Loading PostgreSQL dump..."
Get-Content -Raw $DumpPath | docker @ComposeArgs exec -T -e PGPASSWORD=$PostgresPassword postgres psql -U $PostgresUser -d $PostgresDb -v ON_ERROR_STOP=1
Assert-ObsuraLastExitCode -Context "restore PostgreSQL dump"

Write-Host "Re-applying storage permissions..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("run", "--rm", "--no-deps", "volume-init")) -Context "reapply storage permissions"

Write-Host "Starting full stack..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("up", "-d")) -Context "docker compose up after restore"

Write-Host "Waiting for API health..."
$Healthy = Wait-ObsuraServiceHealth -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv -Service "api" -TimeoutSeconds 180
if (-not $Healthy) {
    Write-Host "API did not become healthy within 180 seconds after restore. Recent logs:"
    docker @ComposeArgs logs --tail 200 api postgres
    exit 1
}

Write-Host "Running API container:"
Show-ObsuraRunningServiceState -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv -Service "api"

Write-Host "Restore complete."
