[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Environment = "production",
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

Assert-ObsuraEnvironment -Environment $Environment
Assert-ObsuraDocker

$RootDir = Get-ObsuraRepoRoot -ScriptPath $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $RootDir "compose/$Environment/docker-compose.yaml"
$GlobalEnv = Join-Path $RootDir "env/global.env"
$ApiEnv = Join-Path $RootDir "env/api.env"
$PostgresEnv = Join-Path $RootDir "env/postgres.env"

Assert-ObsuraFiles -Paths @($ComposeFile, $GlobalEnv, $ApiEnv, $PostgresEnv)

$Vars = Get-ObsuraEnvMap -Paths @($GlobalEnv, $PostgresEnv)
$PostgresUser = $Vars["POSTGRES_USER"]
$PostgresDb = $Vars["POSTGRES_DB"]
$PostgresPassword = $Vars["POSTGRES_PASSWORD"]
$StorageVolume = if ($Vars.ContainsKey("OBSURA_STORAGE_VOLUME")) { $Vars["OBSURA_STORAGE_VOLUME"] } else { "obsura-storage" }
$BackupRoot = if ($Vars.ContainsKey("BACKUP_ROOT")) { $Vars["BACKUP_ROOT"] } else { "./backups" }
$ApiImage = if ($Vars.ContainsKey("OBSURA_API_IMAGE")) { $Vars["OBSURA_API_IMAGE"] } else { "unknown" }

if (-not $PostgresUser -or -not $PostgresDb -or -not $PostgresPassword) {
    throw "POSTGRES_USER, POSTGRES_DB, and POSTGRES_PASSWORD must be set in env/postgres.env."
}

if (-not $OutputDir) {
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    if ([System.IO.Path]::IsPathRooted($BackupRoot)) {
        $OutputDir = Join-Path $BackupRoot "$Environment/$Timestamp"
    }
    else {
        $RelativeBackupRoot = $BackupRoot.TrimStart('.', '/', '\')
        if (-not $RelativeBackupRoot) {
            $RelativeBackupRoot = "backups"
        }
        $OutputDir = Join-Path $RootDir $RelativeBackupRoot
        $OutputDir = Join-Path $OutputDir "$Environment/$Timestamp"
    }
}

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$ComposeArgs = Get-ObsuraComposeArgs -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv
Show-ObsuraStackContext -Environment $Environment -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -ApiEnv $ApiEnv -PostgresEnv $PostgresEnv -ImageRef $ApiImage
Write-Host "Backup output: $OutputDir"
Write-Host "Storage volume: $StorageVolume"
Assert-ObsuraDockerVolume -VolumeName $StorageVolume

Write-Host "Ensuring postgres is running..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("up", "-d", "postgres")) -Context "docker compose up postgres for backup"

Write-Host "Waiting for postgres readiness..."
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker @ComposeArgs exec -T -e PGPASSWORD=$PostgresPassword postgres pg_isready -U $PostgresUser -d $PostgresDb *> $null
    if ($LASTEXITCODE -eq 0) {
        $Ready = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $Ready) {
    throw "Postgres did not become ready in time."
}

Write-Host "Writing PostgreSQL logical backup..."
$DumpPath = Join-Path $OutputDir "postgres.sql"
& docker @ComposeArgs exec -T -e PGPASSWORD=$PostgresPassword postgres pg_dump -U $PostgresUser -d $PostgresDb --clean --if-exists --no-owner --no-privileges > $DumpPath
Assert-ObsuraLastExitCode -Context "pg_dump backup"

Write-Host "Archiving Obsura storage volume..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList @(
    "run"
    "--rm"
    "--mount", "type=volume,source=$StorageVolume,target=/source,readonly"
    "--mount", "type=bind,source=$OutputDir,target=/backup"
    "alpine:3.20"
    "sh"
    "-ec"
    "cd /source && tar -czf /backup/obsura-data.tgz ."
) -Context "storage archive backup"

$MetadataPath = Join-Path $OutputDir "metadata.txt"
@(
    "environment=$Environment"
    "created_at=$((Get-Date).ToUniversalTime().ToString('s'))Z"
    "api_image=$ApiImage"
    "storage_volume=$StorageVolume"
    "postgres_db=$PostgresDb"
    "postgres_user=$PostgresUser"
    "compose_file=$ComposeFile"
) | Set-Content -Path $MetadataPath

Write-Host "Backup created at $OutputDir"
