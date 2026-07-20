$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Archive = "C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026"
$Output = Join-Path $Archive "fundamental_snapshots_2026-07-19"

function Invoke-Stage {
    param([string]$Name, [string]$SymbolsFile)
    Write-Output "START $Name $((Get-Date).ToUniversalTime().ToString('o'))"
    & $Python ".\download_alpha_vantage_fundamental_snapshots.py" `
        "--symbols-file" $SymbolsFile `
        "--output" $Output `
        "--endpoints" "INCOME_STATEMENT" "BALANCE_SHEET" "CASH_FLOW" "OVERVIEW" `
        "--delay-seconds" "0.75"
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
    Write-Output "DONE $Name $((Get-Date).ToUniversalTime().ToString('o'))"
}

Set-Location $Root
Invoke-Stage "russell_statements" ".\russell_2000_symbols.txt"
Invoke-Stage "sp500_statements" ".\sp500_expanded_symbols.txt"

Write-Output "START market_regime_archive $((Get-Date).ToUniversalTime().ToString('o'))"
& $Python ".\download_alpha_vantage_market_regimes.py" `
    "--output" (Join-Path $Archive "market_regimes")
if ($LASTEXITCODE -ne 0) {
    throw "market_regime_archive failed with exit code $LASTEXITCODE"
}
Write-Output "DONE market_regime_archive $((Get-Date).ToUniversalTime().ToString('o'))"

Write-Output "ALPHA VANTAGE PHASE 2 COMPLETE"
