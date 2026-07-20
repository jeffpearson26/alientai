$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stages = @(
    "run_alpha_vantage_month_harvest.ps1",
    "run_alpha_vantage_month_harvest_phase2.ps1",
    "run_alpha_vantage_month_harvest_phase3.ps1",
    "run_alpha_vantage_month_harvest_phase4.ps1",
    "run_alpha_vantage_month_harvest_phase5.ps1"
)

Set-Location $Root
foreach ($Stage in $Stages) {
    $Path = Join-Path $Root $Stage
    Write-Output "MASTER START $Stage $((Get-Date).ToUniversalTime().ToString('o'))"
    & $Path
    if ($LASTEXITCODE -ne 0) {
        throw "$Stage failed with exit code $LASTEXITCODE"
    }
    Write-Output "MASTER DONE $Stage $((Get-Date).ToUniversalTime().ToString('o'))"
}
Write-Output "ALPHA VANTAGE MASTER QUEUE COMPLETE $((Get-Date).ToUniversalTime().ToString('o'))"
