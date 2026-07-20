$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Chains = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\historical_options_winners_10pct"

Set-Location $Root
Write-Output "START final_option_feature_build $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\build_historical_option_features.py" `
    "--events" ".\data_v2\rcef_research\matched_winners_10pct_50.jsonl" `
    "--chains" $Chains `
    "--output" ".\data_v2\rcef_research\historical_option_features_matched.jsonl"
if ($LASTEXITCODE -ne 0) { throw "final_option_feature_build failed with exit code $LASTEXITCODE" }

Write-Output "START final_call_evaluation $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\evaluate_historical_calls.py" `
    "--events" ".\data_v2\rcef_research\matched_winners_10pct_50.jsonl" `
    "--chains" $Chains `
    "--output" ".\data_v2\rcef_research\historical_call_trades_matched.jsonl" `
    "--summary-output" ".\data_v2\rcef_research\historical_call_summary_matched.json"
if ($LASTEXITCODE -ne 0) { throw "final_call_evaluation failed with exit code $LASTEXITCODE" }

Write-Output "START earnings_supabase_upload $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\upload_earnings_to_supabase.py" `
    "--rows" ".\data_v2\earnings_history\earnings_events.jsonl" `
    "--batch-size" "500"
if ($LASTEXITCODE -ne 0) { throw "earnings_supabase_upload failed with exit code $LASTEXITCODE" }

Write-Output "ALPHA VANTAGE PHASE 5 COMPLETE $((Get-Date).ToUniversalTime().ToString('o'))"
