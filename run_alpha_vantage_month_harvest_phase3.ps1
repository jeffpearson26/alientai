$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Archive = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026"
$Events = ".\data_v2\rcef_research\matched_winners_10pct_50.jsonl"
$FullEvents = ".\data_v2\rcef_research\sp500_matched_winners_10pct.jsonl"

Set-Location $Root

Write-Output "START matched_premarket_history $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_matched_premarket.py" `
    "--events" $FullEvents `
    "--output" (Join-Path $Archive "matched_premarket_5min") `
    "--role" "all" `
    "--delay-seconds" "0.75" `
    "--minimum-free-gb" "6.0"
if ($LASTEXITCODE -ne 0) { throw "matched_premarket_history failed with exit code $LASTEXITCODE" }

Write-Output "START matched_options $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_historical_options.py" `
    "--events" $Events `
    "--output" (Join-Path $Archive "historical_options_winners_10pct") `
    "--role" "all" `
    "--delay-seconds" "0.75"
if ($LASTEXITCODE -ne 0) { throw "matched_options failed with exit code $LASTEXITCODE" }

Write-Output "START matched_event_news $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_event_news.py" `
    "--events" $Events `
    "--output" (Join-Path $Archive "event_news_winners_10pct") `
    "--role" "all" `
    "--lookback-days" "14" `
    "--limit-per-request" "1000" `
    "--delay-seconds" "0.75"
if ($LASTEXITCODE -ne 0) { throw "matched_event_news failed with exit code $LASTEXITCODE" }

Write-Output "ALPHA VANTAGE PHASE 3 COMPLETE $((Get-Date).ToUniversalTime().ToString('o'))"
