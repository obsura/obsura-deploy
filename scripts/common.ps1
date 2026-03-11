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
    param([hashtable]$Vars)

    if (-not $Vars.ContainsKey("OBSURA_API_IMAGE") -or [string]::IsNullOrWhiteSpace($Vars["OBSURA_API_IMAGE"]) -or $Vars["OBSURA_API_IMAGE"] -match "replace-with-") {
        throw "Set OBSURA_API_IMAGE in env/global.env to a real published tag or digest before continuing."
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

function Set-ObsuraEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $pattern = "^{0}=" -f [regex]::Escape($Key)
    $updated = $false
    $lines = foreach ($Line in Get-Content $Path) {
        if ($Line -match $pattern) {
            $updated = $true
            "$Key=$Value"
        }
        else {
            $Line
        }
    }

    if (-not $updated) {
        $lines += "$Key=$Value"
    }

    Set-Content -Path $Path -Value $lines
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
