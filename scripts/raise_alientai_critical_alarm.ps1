param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_.-]+$")]
    [string]$IncidentId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Message,

    [ValidateRange(2, 60)]
    [int]$IntervalSeconds = 5,

    [switch]$SilentSelfTest
)

$ErrorActionPreference = "Stop"

$alarmScript = Join-Path $PSScriptRoot "start_alientai_critical_alarm.ps1"
if (-not (Test-Path -LiteralPath $alarmScript -PathType Leaf)) {
    throw "Critical alarm worker is missing: $alarmScript"
}

$encodedMessage = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes($Message)
)
$stateRoot = Join-Path $env:LOCALAPPDATA "AlienTAI\CriticalAlerts"
[System.IO.Directory]::CreateDirectory($stateRoot) | Out-Null
$stdoutPath = Join-Path $stateRoot "$IncidentId.stdout.log"
$stderrPath = Join-Path $stateRoot "$IncidentId.stderr.log"
$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $alarmScript,
    "-IncidentId",
    $IncidentId,
    "-MessageBase64",
    $encodedMessage,
    "-IntervalSeconds",
    [string]$IntervalSeconds
)
if ($SilentSelfTest) {
    $arguments += "-SilentSelfTest"
}

$process = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $arguments `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -PassThru

[pscustomobject]@{
    incident_id = $IncidentId
    alarm_process_id = $process.Id
    state_root = $stateRoot
    stdout_log = $stdoutPath
    stderr_log = $stderrPath
    silent_self_test = [bool]$SilentSelfTest
}
