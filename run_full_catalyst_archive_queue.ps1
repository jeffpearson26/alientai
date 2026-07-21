$ErrorActionPreference = "Stop"

# Sequential research-only collector queue. It never starts options unless the
# full time-valid news archive completed successfully; this prevents competing
# Alpha Vantage jobs and keeps all large archives on the external SSD.
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Events = Join-Path $Root "data_v2\rcef_research\sp500_matched_winners_10pct.jsonl"
$NewsArchive = "D:\AlientAI\Data\AlphaVantage_2026\event_news_sp500_full"
$OptionsArchive = "D:\AlientAI\Data\AlphaVantage_2026\historical_options_sp500_full"
$NewsManifest = Join-Path $NewsArchive "manifest.json"

Set-Location $Root
while ($true) {
    if (-not (Test-Path $NewsManifest)) {
        Start-Sleep -Seconds 60
        continue
    }
    $manifest = Get-Content $NewsManifest -Raw | ConvertFrom-Json
    if ($manifest.status -eq "complete") {
        break
    }
    if ($manifest.status -eq "failed_closed") {
        throw "News collection failed closed; options collection was not started."
    }
    Start-Sleep -Seconds 60
}

Write-Output "START full historical options $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_historical_options.py" `
    "--events" $Events `
    "--output" $OptionsArchive `
    "--role" "all" `
    "--delay-seconds" "0.75"
if ($LASTEXITCODE -ne 0) { throw "full historical options failed with exit code $LASTEXITCODE" }
Write-Output "COMPLETE full historical options $((Get-Date).ToUniversalTime().ToString('o'))"
