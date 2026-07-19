$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Archive = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026"
$OptionsOutput = Join-Path $Archive "historical_options_winners_10pct"
$FundamentalOutput = Join-Path $Archive "fundamental_snapshots_2026-07-19"

function Invoke-HarvestStage {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $started = (Get-Date).ToUniversalTime().ToString("o")
    Write-Output "START $Name $started"
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
    $finished = (Get-Date).ToUniversalTime().ToString("o")
    Write-Output "DONE $Name $finished"
}

Set-Location $Root

Invoke-HarvestStage "winner_options" @(
    ".\download_alpha_vantage_historical_options.py",
    "--events", ".\data_v2\rcef_research\matched_winners_10pct_50.jsonl",
    "--output", $OptionsOutput,
    "--role", "winner",
    "--delay-seconds", "0.75"
)

Invoke-HarvestStage "russell_earnings" @(
    ".\download_alpha_vantage_earnings.py",
    "--symbols-file", ".\russell_2000_symbols.txt",
    "--limit-symbols", "0",
    "--delay-seconds", "0.75"
)

Invoke-HarvestStage "russell_snapshots" @(
    ".\download_alpha_vantage_fundamental_snapshots.py",
    "--symbols-file", ".\russell_2000_symbols.txt",
    "--output", $FundamentalOutput,
    "--endpoints", "EARNINGS_ESTIMATES", "SHARES_OUTSTANDING", "INSTITUTIONAL_HOLDINGS",
    "--delay-seconds", "0.75"
)

Invoke-HarvestStage "sp500_earnings" @(
    ".\download_alpha_vantage_earnings.py",
    "--symbols-file", ".\sp500_expanded_symbols.txt",
    "--limit-symbols", "0",
    "--delay-seconds", "0.75"
)

Invoke-HarvestStage "sp500_snapshots" @(
    ".\download_alpha_vantage_fundamental_snapshots.py",
    "--symbols-file", ".\sp500_expanded_symbols.txt",
    "--output", $FundamentalOutput,
    "--endpoints", "EARNINGS_ESTIMATES", "SHARES_OUTSTANDING", "INSTITUTIONAL_HOLDINGS",
    "--delay-seconds", "0.75"
)

Write-Output "ALPHA VANTAGE MONTH HARVEST QUEUE COMPLETE"
