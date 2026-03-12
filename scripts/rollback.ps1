[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("local", "production")]
    [string]$Environment,
    [Parameter(Mandatory = $true)]
    [string]$TargetImage
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
$CurrentImage = if ($Vars.ContainsKey("OBSURA_API_IMAGE")) { $Vars["OBSURA_API_IMAGE"] } else { $null }
if (-not $TargetImage -or $TargetImage -match "replace-with-|change-me|placeholder|example") {
    throw "TargetImage must be a real published tag or digest, not a placeholder value."
}

Show-ObsuraStackContext -Environment $Environment -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -ApiEnv $ApiEnv -PostgresEnv $PostgresEnv -ImageRef $CurrentImage
Write-Host "Target rollback image: $TargetImage"
Write-Host "Updating OBSURA_API_IMAGE in $GlobalEnv..."
try {
    Set-ObsuraEnvValue -Path $GlobalEnv -Key "OBSURA_API_IMAGE" -Value $TargetImage

    Write-Host "Recreating services with the rollback image..."
    & (Join-Path $ScriptDir "update.ps1") -Environment $Environment
    Write-Host "Rollback complete."
}
catch {
    if ($CurrentImage) {
        Write-Warning "Rollback failed. Restoring OBSURA_API_IMAGE in $GlobalEnv back to $CurrentImage."
        Set-ObsuraEnvValue -Path $GlobalEnv -Key "OBSURA_API_IMAGE" -Value $CurrentImage
    }
    throw
}
