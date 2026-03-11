[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Environment = "production",
    [string]$OutputDir
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

if (-not $OutputDir) {
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $BackupRoot = if ($Vars.ContainsKey("BACKUP_ROOT")) { $Vars["BACKUP_ROOT"] } else { "./backups" }
    $OutputDir = Join-Path $RootDir $BackupRoot
    $OutputDir = Join-Path $OutputDir "$Environment/$Timestamp"
}

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

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

Write-Host "Ensuring postgres is running..."
docker @ComposeArgs up -d postgres

Write-Host "Waiting for postgres readiness..."
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker @ComposeArgs exec -T postgres pg_isready -U $PostgresUser -d $PostgresDb *> $null
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
& docker @ComposeArgs exec -T postgres pg_dump -U $PostgresUser -d $PostgresDb --clean --if-exists --no-owner --no-privileges | Set-Content -Path $DumpPath

Write-Host "Archiving Obsura storage volume..."
docker run --rm `
    --mount "type=volume,source=$StorageVolume,target=/source,readonly" `
    --mount "type=bind,source=$OutputDir,target=/backup" `
    alpine:3.20 `
    sh -ec "cd /source && tar -czf /backup/obsura-data.tgz ."

$MetadataPath = Join-Path $OutputDir "metadata.txt"
@(
    "environment=$Environment"
    "created_at=$(Get-Date -AsUTC -Format s)Z"
    "api_image=$($Vars['OBSURA_API_IMAGE'])"
) | Set-Content -Path $MetadataPath

Write-Host "Backup created at $OutputDir"
