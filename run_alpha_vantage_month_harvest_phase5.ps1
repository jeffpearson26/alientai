$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Chains = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\historical_options_winners_10pct"
$Snapshots = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\fundamental_snapshots_2026-07-19"

Set-Location $Root
Write-Output "START final_premarket_feature_build $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\build_matched_premarket_features.py" `
    "--events" ".\data_v2\rcef_research\sp500_matched_winners_10pct.jsonl" `
    "--archive" "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\matched_premarket_5min" `
    "--output" ".\data_v2\rcef_research\matched_premarket_features.jsonl"
if ($LASTEXITCODE -ne 0) { throw "final_premarket_feature_build failed with exit code $LASTEXITCODE" }

Write-Output "START final_premarket_label_build $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\build_matched_premarket_labels.py" `
    "--events" ".\data_v2\rcef_research\sp500_matched_winners_10pct.jsonl" `
    "--archive" "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\matched_premarket_5min" `
    "--output" ".\data_v2\rcef_research\matched_premarket_open_entry_labels.jsonl" `
    "--exceptional-threshold-pct" "10.0"
if ($LASTEXITCODE -ne 0) { throw "final_premarket_label_build failed with exit code $LASTEXITCODE" }

Write-Output "START premarket_ablation_training $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\train_matched_winner_premarket_ablation.py" `
    "--base-rows" ".\data_v2\rcef_research\sp500_matched_winners_10pct.jsonl" `
    "--premarket-features" ".\data_v2\rcef_research\matched_premarket_features.jsonl" `
    "--premarket-labels" ".\data_v2\rcef_research\matched_premarket_open_entry_labels.jsonl" `
    "--output-dir" ".\data_v2\rcef_research\matched_premarket_ablation" `
    "--embargo-calendar-days" "12" `
    "--round-trip-cost-pct" "0.25"
if ($LASTEXITCODE -ne 0) { throw "premarket_ablation_training failed with exit code $LASTEXITCODE" }

Write-Output "START final_fundamental_feature_build $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\compile_fundamental_snapshot_features.py" `
    "--snapshots" $Snapshots `
    "--output" ".\data_v2\rcef_research\current_fundamental_snapshot_features.jsonl"
if ($LASTEXITCODE -ne 0) { throw "final_fundamental_feature_build failed with exit code $LASTEXITCODE" }

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

Write-Output "START conditional_phase6 $((Get-Date).ToUniversalTime().ToString('o'))"
& (Join-Path $Root "run_alpha_vantage_month_harvest_phase6.ps1")
if ($LASTEXITCODE -ne 0) { throw "conditional_phase6 failed with exit code $LASTEXITCODE" }
