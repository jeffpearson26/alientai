param(
    [Parameter(ParameterSetName = "One", Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_.-]+$")]
    [string]$IncidentId,

    [Parameter(ParameterSetName = "All", Mandatory = $true)]
    [switch]$All
)

$ErrorActionPreference = "Stop"
$stateRoot = Join-Path $env:LOCALAPPDATA "AlienTAI\CriticalAlerts"
[System.IO.Directory]::CreateDirectory($stateRoot) | Out-Null
$timestamp = [DateTime]::UtcNow.ToString("o") + [Environment]::NewLine

if ($All) {
    $stateFiles = Get-ChildItem -LiteralPath $stateRoot -Filter "*.json" -File
    foreach ($stateFile in $stateFiles) {
        $target = Join-Path $stateRoot "$($stateFile.BaseName).ack"
        [System.IO.File]::WriteAllText(
            $target,
            $timestamp,
            [System.Text.UTF8Encoding]::new($false)
        )
    }
    [pscustomobject]@{
        acknowledged = $stateFiles.Count
        scope = "all"
    }
    exit 0
}

$ackPath = Join-Path $stateRoot "$IncidentId.ack"
[System.IO.File]::WriteAllText(
    $ackPath,
    $timestamp,
    [System.Text.UTF8Encoding]::new($false)
)
[pscustomobject]@{
    acknowledged = 1
    incident_id = $IncidentId
}
