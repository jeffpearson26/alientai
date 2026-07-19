$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Output = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\event_transcripts_winners_10pct"

Set-Location $Root
Write-Output "START matched_event_transcripts $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_event_transcripts.py" `
    "--events" ".\data_v2\rcef_research\matched_winners_10pct_50.jsonl" `
    "--earnings" ".\data_v2\earnings_history\earnings_events.jsonl" `
    "--output" $Output `
    "--role" "all" `
    "--availability-buffer-days" "1" `
    "--delay-seconds" "0.75"
if ($LASTEXITCODE -ne 0) { throw "matched_event_transcripts failed with exit code $LASTEXITCODE" }
Write-Output "ALPHA VANTAGE PHASE 4 COMPLETE $((Get-Date).ToUniversalTime().ToString('o'))"
