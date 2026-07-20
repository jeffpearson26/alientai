$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Archive = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026"
$Report = Join-Path $Root "data_v2\rcef_research\matched_premarket_ablation\premarket_ablation_report.json"
$UniverseRows = Join-Path $Root "data_v2\rcef_research\sp500_full_rows_with_complete_insider_roles.jsonl"
$NaturalArchive = Join-Path $Archive "natural_universe_premarket_5min"

Set-Location $Root
if (-not (Test-Path $Report)) {
    throw "Premarket ablation report is required before natural-universe collection."
}

$Result = Get-Content $Report -Raw | ConvertFrom-Json
$GateStatus = [string]$Result.premarket_promotion_gate.status
if ($GateStatus -ne "RESEARCH_PASS") {
    Write-Output "PHASE 6 RESEARCH HOLD: premarket promotion gate status is $GateStatus"
    Write-Output "No natural-universe premarket API calls were made."
    exit 0
}

Write-Output "START natural_universe_premarket_history $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_matched_premarket.py" `
    "--events" $UniverseRows `
    "--output" $NaturalArchive `
    "--role" "all" `
    "--delay-seconds" "0.75" `
    "--minimum-free-gb" "8.0"
if ($LASTEXITCODE -ne 0) { throw "natural_universe_premarket_history failed with exit code $LASTEXITCODE" }

Write-Output "START natural_universe_premarket_features $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\build_matched_premarket_features.py" `
    "--events" $UniverseRows `
    "--archive" $NaturalArchive `
    "--output" ".\data_v2\rcef_research\natural_universe_premarket_features.jsonl"
if ($LASTEXITCODE -ne 0) { throw "natural_universe_premarket_features failed with exit code $LASTEXITCODE" }

Write-Output "START natural_universe_premarket_labels $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\build_matched_premarket_labels.py" `
    "--events" $UniverseRows `
    "--archive" $NaturalArchive `
    "--output" ".\data_v2\rcef_research\natural_universe_premarket_open_entry_labels.jsonl" `
    "--exceptional-threshold-pct" "10.0"
if ($LASTEXITCODE -ne 0) { throw "natural_universe_premarket_labels failed with exit code $LASTEXITCODE" }

Write-Output "ALPHA VANTAGE PHASE 6 COMPLETE $((Get-Date).ToUniversalTime().ToString('o'))"
