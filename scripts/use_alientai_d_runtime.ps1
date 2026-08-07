$ErrorActionPreference = "Stop"

$runtimeRoot = "D:\AlientAI"
$minimumFreeBytes = 20GB

if (-not (Test-Path -LiteralPath $runtimeRoot -PathType Container)) {
    throw "AlienTAI D-drive runtime root is unavailable: $runtimeRoot"
}

$drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='D:'"
if ($null -eq $drive -or [int64]$drive.FreeSpace -lt $minimumFreeBytes) {
    $freeGiB = if ($null -eq $drive) { 0 } else { [math]::Round([int64]$drive.FreeSpace / 1GB, 2) }
    throw "AlienTAI D-drive free-space gate failed: ${freeGiB} GiB available; 20 GiB required."
}

$paths = @{
    Data = Join-Path $runtimeRoot "Data"
    Models = Join-Path $runtimeRoot "Models"
    Logs = Join-Path $runtimeRoot "Logs"
    Temp = Join-Path $runtimeRoot "Temp"
}

foreach ($path in $paths.Values) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

$env:ALIENTAI_RUNTIME_ROOT = $runtimeRoot
$env:ALIENTAI_DATA_ROOT = $paths.Data
$env:ALIENTAI_MODEL_ROOT = $paths.Models
$env:ALIENTAI_LOG_ROOT = $paths.Logs
$env:TEMP = $paths.Temp
$env:TMP = $paths.Temp
$env:JOBLIB_TEMP_FOLDER = Join-Path $paths.Temp "joblib"
$env:PYTHONPYCACHEPREFIX = Join-Path $paths.Temp "pycache"

foreach ($path in @($env:JOBLIB_TEMP_FOLDER, $env:PYTHONPYCACHEPREFIX)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}
