[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Environment = "production"
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

$Vars = Get-ObsuraEnvMap -Paths @($GlobalEnv)
Assert-ObsuraRealImageReference -Vars $Vars

$ComposeArgs = Get-ObsuraComposeArgs -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv
Show-ObsuraStackContext -Environment $Environment -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -ApiEnv $ApiEnv -PostgresEnv $PostgresEnv -ImageRef $Vars["OBSURA_API_IMAGE"]

Write-Host "Validating compose configuration for $Environment..."
docker @ComposeArgs config | Out-Null

Write-Host "Pulling updated images..."
docker @ComposeArgs pull

Write-Host "Recreating services with the current image references..."
docker @ComposeArgs up -d --remove-orphans

Write-Host "Current service state:"
docker @ComposeArgs ps
