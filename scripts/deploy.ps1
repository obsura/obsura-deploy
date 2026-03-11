[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Environment = "local"
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

if (-not $Vars.ContainsKey("OBSURA_API_IMAGE") -or $Vars["OBSURA_API_IMAGE"] -match "replace-with-") {
    throw "Set OBSURA_API_IMAGE in env/global.env to a published tag or digest before deploying."
}

$ComposeArgs = @(
    "compose"
    "--env-file", $GlobalEnv
    "--env-file", $PostgresEnv
    "--env-file", $ApiEnv
    "-f", $ComposeFile
)

Write-Host "Validating compose configuration for $Environment..."
docker @ComposeArgs config | Out-Null

Write-Host "Pulling images..."
docker @ComposeArgs pull

Write-Host "Starting stack..."
docker @ComposeArgs up -d --remove-orphans

Write-Host "Current service state:"
docker @ComposeArgs ps
