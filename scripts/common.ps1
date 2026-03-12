[CmdletBinding()]
param()

function Get-ObsuraRepoRoot {
    param([string]$ScriptPath)
    $scriptDir = Split-Path -Parent $ScriptPath
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Assert-ObsuraEnvironment {
    param([string]$Environment)

    if ($Environment -notin @("local", "production")) {
        throw "Unsupported environment '$Environment'. Expected 'local' or 'production'."
    }
}

function Assert-ObsuraFiles {
    param([string[]]$Paths)

    foreach ($Path in $Paths) {
        if (-not (Test-Path $Path)) {
            throw "Missing required file: $Path"
        }
    }
}

function Assert-ObsuraDocker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is required but was not found on PATH."
    }

    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose v2 plugin is required."
    }
}

function Assert-ObsuraLastExitCode {
    param([string]$Context)

    if ($LASTEXITCODE -ne 0) {
        throw "$Context failed with exit code $LASTEXITCODE."
    }
}

function Invoke-ObsuraNative {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$Context
    )

    & $FilePath @ArgumentList
    $label = if ($Context) { $Context } else { "$FilePath $($ArgumentList -join ' ')" }
    Assert-ObsuraLastExitCode -Context $label
}

function Get-ObsuraEnvMap {
    param([string[]]$Paths)

    $vars = @{}
    foreach ($Path in $Paths) {
        foreach ($Line in Get-Content $Path) {
            if (-not $Line) {
                continue
            }

            $Trimmed = $Line.Trim()
            if (-not $Trimmed -or $Trimmed.StartsWith("#")) {
                continue
            }

            $Name, $Value = $Trimmed -split "=", 2
            if (-not $Name) {
                continue
            }

            $Value = $Value.Trim()
            if ($Value.Length -ge 2) {
                if (($Value.StartsWith('"') -and $Value.EndsWith('"')) -or ($Value.StartsWith("'") -and $Value.EndsWith("'"))) {
                    $Value = $Value.Substring(1, $Value.Length - 2)
                }
            }

            $vars[$Name.Trim()] = $Value
        }
    }

    return $vars
}

function Assert-ObsuraRealImageReference {
    param([string]$ImageRef)

    if (-not $ImageRef -or $ImageRef -match "replace-with-|change-me|placeholder|example") {
        throw "Set the api image in the compose file to a real published tag or digest before continuing."
    }
}

function Assert-ObsuraConfirmation {
    param([bool]$Confirmed)

    if (-not $Confirmed) {
        throw "This action is destructive. Re-run with -Yes after confirming the target backup set and environment."
    }
}

function Show-ObsuraStackContext {
    param(
        [string]$Environment,
        [string]$ComposeFile,
        [string]$GlobalEnv,
        [string]$ApiEnv,
        [string]$PostgresEnv,
        [string]$ImageRef
    )

    Write-Host "Environment: $Environment"
    Write-Host "Compose file: $ComposeFile"
    Write-Host "Env files:"
    Write-Host "  - $GlobalEnv"
    Write-Host "  - $ApiEnv"
    Write-Host "  - $PostgresEnv"
    if ($ImageRef) {
        Write-Host "API image: $ImageRef"
    }
}

function Get-ObsuraComposeServiceImage {
    param(
        [string]$ComposeFile,
        [string]$Service
    )

    $lines = Get-Content $ComposeFile
    $inTarget = $false
    foreach ($line in $lines) {
        if ($line -match "^  ([A-Za-z0-9_-]+):$") {
            $inTarget = ($Matches[1] -eq $Service)
            continue
        }

        if ($inTarget -and $line -match "^    image:\s*(.+)$") {
            return $Matches[1].Trim()
        }
    }

    return $null
}

function Set-ObsuraComposeServiceImage {
    param(
        [string]$ComposeFile,
        [string]$Service,
        [string]$ImageRef
    )

    $lines = Get-Content $ComposeFile
    $updated = $false
    $inTarget = $false
    $output = New-Object System.Collections.Generic.List[string]

    foreach ($line in $lines) {
        if ($line -match "^  ([A-Za-z0-9_-]+):$") {
            $inTarget = ($Matches[1] -eq $Service)
            $output.Add($line)
            continue
        }

        if ($inTarget -and $line -match "^    image:\s*(.+)$") {
            $output.Add("    image: $ImageRef")
            $updated = $true
            continue
        }

        $output.Add($line)
    }

    if (-not $updated) {
        throw "Failed to update image for service '$Service' in $ComposeFile"
    }

    Set-Content -Path $ComposeFile -Value $output
}

function Get-ObsuraStackApiImage {
    param([string]$ComposeFile)

    return Get-ObsuraComposeServiceImage -ComposeFile $ComposeFile -Service "api"
}

function Set-ObsuraStackApiImage {
    param(
        [string]$ComposeFile,
        [string]$ImageRef
    )

    Set-ObsuraComposeServiceImage -ComposeFile $ComposeFile -Service "volume-init" -ImageRef $ImageRef
    Set-ObsuraComposeServiceImage -ComposeFile $ComposeFile -Service "api" -ImageRef $ImageRef
}

function Get-ObsuraComposeServiceContainerId {
    param(
        [string]$ComposeFile,
        [string]$GlobalEnv,
        [string]$PostgresEnv,
        [string]$ApiEnv,
        [string]$Service
    )

    $composeArgs = Get-ObsuraComposeArgs -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv
    $containerId = (& docker @composeArgs ps -q $Service | Out-String).Trim()
    return $containerId
}

function Wait-ObsuraServiceHealth {
    param(
        [string]$ComposeFile,
        [string]$GlobalEnv,
        [string]$PostgresEnv,
        [string]$ApiEnv,
        [string]$Service,
        [int]$TimeoutSeconds = 180
    )

    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $containerId = Get-ObsuraComposeServiceContainerId -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv -Service $Service
        if ($containerId) {
            $state = (& docker inspect --format "{{.State.Status}}" $containerId | Out-String).Trim()
            $health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $containerId | Out-String).Trim()
            if ($health -eq "healthy" -or ($health -eq "none" -and $state -eq "running")) {
                return $true
            }
        }

        Start-Sleep -Seconds 2
        $elapsed += 2
    }

    return $false
}

function Show-ObsuraRunningServiceState {
    param(
        [string]$ComposeFile,
        [string]$GlobalEnv,
        [string]$PostgresEnv,
        [string]$ApiEnv,
        [string]$Service = "api"
    )

    $containerId = Get-ObsuraComposeServiceContainerId -ComposeFile $ComposeFile -GlobalEnv $GlobalEnv -PostgresEnv $PostgresEnv -ApiEnv $ApiEnv -Service $Service
    if (-not $containerId) {
        Write-Host "Service '$Service' does not currently have a container."
        return
    }

    $configImage = (& docker inspect --format "{{.Config.Image}}" $containerId | Out-String).Trim()
    $imageId = (& docker inspect --format "{{.Image}}" $containerId | Out-String).Trim()
    $state = (& docker inspect --format "{{.State.Status}}" $containerId | Out-String).Trim()
    $health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $containerId | Out-String).Trim()

    Write-Host "Service: $Service"
    Write-Host "  Container id: $containerId"
    Write-Host "  State: $state"
    Write-Host "  Health: $health"
    if ($configImage) {
        Write-Host "  Configured image: $configImage"
    }
    if ($imageId) {
        Write-Host "  Image id: $imageId"
    }
}

function Assert-ObsuraDockerVolume {
    param([string]$VolumeName)

    docker volume inspect $VolumeName *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Required Docker volume not found: $VolumeName"
    }
}

function Ensure-ObsuraDockerVolume {
    param([string]$VolumeName)

    docker volume inspect $VolumeName *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Creating Docker volume: $VolumeName"
        docker volume create $VolumeName *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Docker volume: $VolumeName"
        }
    }
}

function Get-ObsuraComposeArgs {
    param(
        [string]$ComposeFile,
        [string]$GlobalEnv,
        [string]$PostgresEnv,
        [string]$ApiEnv
    )

    return @(
        "compose"
        "--env-file", $GlobalEnv
        "--env-file", $PostgresEnv
        "--env-file", $ApiEnv
        "-f", $ComposeFile
    )
}
