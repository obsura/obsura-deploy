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
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("config")) -Context "docker compose config for $Environment" | Out-Null

Write-Host "Pulling updated images..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("pull")) -Context "docker compose pull for $Environment"

Write-Host "Recreating services with the current image references..."
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("up", "-d", "--remove-orphans")) -Context "docker compose up for $Environment"

Write-Host "Waiting for API health..."
$Healthy = Wait-ObsuraServiceHealth -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv -Service "api" -TimeoutSeconds 180
if (-not $Healthy) {
    Write-Host "API did not become healthy within 180 seconds. Recent logs:"
    docker @ComposeArgs logs --tail 200 api postgres
    exit 1
}

Write-Host "Current service state:"
Invoke-ObsuraNative -FilePath "docker" -ArgumentList ($ComposeArgs + @("ps")) -Context "docker compose ps for $Environment"

Write-Host "Running API container:"
Show-ObsuraRunningServiceState -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv -Service "api"
