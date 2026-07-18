$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LightGbmTrainer = Join-Path $ProjectRoot "train_v2_lightgbm_5day_sp500_from_supabase.py"
$CurrentTransformerReport = Join-Path $ProjectRoot "data_v2\transformer_5day_sp500_supabase_training\transformer_5day_sp500_metrics.json"
$CurrentTransformerLog = Join-Path $ProjectRoot "transformer_5day_sp500_training.log"
$QueueLog = Join-Path $ProjectRoot "overnight_training_queue.log"
$QueueSummary = Join-Path $ProjectRoot "overnight_training_queue_summary.json"

function Write-QueueMessage {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -LiteralPath $QueueLog -Value $line -Encoding UTF8
}

function Test-CurrentTransformerFailure {
    if (-not (Test-Path -LiteralPath $CurrentTransformerLog)) {
        return $false
    }
    $failure = Select-String -LiteralPath $CurrentTransformerLog `
        -Pattern "Traceback|checkpoint selection failed|RuntimeError:|FAILED \(errors=" `
        -Quiet
    return [bool]$failure
}

function Invoke-TrainingJob {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [string]$LogFile,
        [string]$ExpectedReport
    )

    if (Test-Path -LiteralPath $ExpectedReport) {
        Write-QueueMessage "SKIP: $Name already has a completed report: $ExpectedReport"
        return [pscustomobject]@{
            name = $Name
            status = "skipped_existing_report"
            report = $ExpectedReport
            finished_at = (Get-Date).ToString("s")
        }
    }

    Write-QueueMessage "START: $Name"
    # Native programs legitimately write progress and tracebacks to stderr.
    # Capture the entire stream and inspect the exit code instead of allowing
    # ErrorActionPreference=Stop to truncate the diagnostic at its first line.
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Python -u $LightGbmTrainer @Arguments 2>&1 | Tee-Object -FilePath $LogFile
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0) {
        throw "$Name exited with code $exitCode. See $LogFile"
    }
    if (-not (Test-Path -LiteralPath $ExpectedReport)) {
        throw "$Name exited without creating its expected report: $ExpectedReport"
    }

    Write-QueueMessage "COMPLETE: $Name"
    return [pscustomobject]@{
        name = $Name
        status = "complete"
        report = $ExpectedReport
        finished_at = (Get-Date).ToString("s")
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "AlienTAI virtual-environment Python was not found: $Python"
}
if (-not (Test-Path -LiteralPath $LightGbmTrainer)) {
    throw "Five-day LightGBM trainer was not found: $LightGbmTrainer"
}

Set-Content -LiteralPath $QueueLog -Value "" -Encoding UTF8
Write-QueueMessage "Overnight queue initialized. Jobs run sequentially and remain research-only."

$waitStarted = Get-Date
$maximumWaitHours = 8
while (-not (Test-Path -LiteralPath $CurrentTransformerReport)) {
    if (Test-CurrentTransformerFailure) {
        throw "Current five-day Transformer log contains a failure. Queue stopped before starting another job."
    }
    $elapsedHours = ((Get-Date) - $waitStarted).TotalHours
    if ($elapsedHours -ge $maximumWaitHours) {
        throw "Timed out after $maximumWaitHours hours waiting for the current Transformer report."
    }
    Write-QueueMessage "WAIT: current five-day Transformer is still running."
    Start-Sleep -Seconds 60
}

Write-QueueMessage "Current five-day Transformer report detected. Beginning queued LightGBM experiments."

$commonSp500 = @(
    "--symbols-file", ".\sp500_expanded_symbols.txt",
    "--table", "v2_daily_candles",
    "--candle-limit", "10000",
    "--sequence-length", "60",
    "--horizon-days", "5",
    "--min-history-days", "260",
    "--step-days", "1",
    "--train-fraction", "0.60",
    "--validation-fraction", "0.20",
    "--split-embargo-calendar-days", "12",
    "--round-trip-cost-pct", "0.25",
    "--non-overlapping-calendar-days", "9",
    "--num-boost-round", "1500",
    "--early-stopping-rounds", "100",
    "--delay", "0.05",
    "--fetch-attempts", "4",
    "--fetch-retry-delay", "2.0"
)

$jobs = @(
    [pscustomobject]@{
        Name = "S&P 500 LightGBM five-day +2 percent target"
        Arguments = $commonSp500 + @(
            "--target-return-pct", "2.0",
            "--output-dir", "data_v2/lightgbm_5day_sp500_target_2pct_training"
        )
        Log = Join-Path $ProjectRoot "lightgbm_5day_sp500_target_2pct_training.log"
        Report = Join-Path $ProjectRoot "data_v2\lightgbm_5day_sp500_target_2pct_training\lightgbm_5day_training_report.json"
    },
    [pscustomobject]@{
        Name = "S&P 500 LightGBM five-day +3 percent target"
        Arguments = $commonSp500 + @(
            "--target-return-pct", "3.0",
            "--output-dir", "data_v2/lightgbm_5day_sp500_target_3pct_training"
        )
        Log = Join-Path $ProjectRoot "lightgbm_5day_sp500_target_3pct_training.log"
        Report = Join-Path $ProjectRoot "data_v2\lightgbm_5day_sp500_target_3pct_training\lightgbm_5day_training_report.json"
    },
    [pscustomobject]@{
        Name = "Russell 2000 LightGBM five-day +2 percent target"
        Arguments = @(
            "--symbols-file", ".\russell_2000_symbols.txt",
            "--table", "v2_daily_candles",
            "--candle-limit", "10000",
            "--sequence-length", "60",
            "--horizon-days", "5",
            "--target-return-pct", "2.0",
            "--min-history-days", "260",
            "--step-days", "2",
            "--train-fraction", "0.60",
            "--validation-fraction", "0.20",
            "--split-embargo-calendar-days", "12",
            "--round-trip-cost-pct", "0.35",
            "--non-overlapping-calendar-days", "9",
            "--num-boost-round", "1500",
            "--early-stopping-rounds", "100",
            "--delay", "0.05",
            "--output-dir", "data_v2/lightgbm_5day_russell2000_target_2pct_training"
        )
        Log = Join-Path $ProjectRoot "lightgbm_5day_russell2000_target_2pct_training.log"
        Report = Join-Path $ProjectRoot "data_v2\lightgbm_5day_russell2000_target_2pct_training\lightgbm_5day_training_report.json"
    }
)

$results = @()
try {
    foreach ($job in $jobs) {
        $results += Invoke-TrainingJob `
            -Name $job.Name `
            -Arguments $job.Arguments `
            -LogFile $job.Log `
            -ExpectedReport $job.Report
    }
    $summary = [ordered]@{
        status = "complete"
        finished_at = (Get-Date).ToString("s")
        current_transformer_report = $CurrentTransformerReport
        jobs = $results
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $QueueSummary -Encoding UTF8
    Write-QueueMessage "ALL COMPLETE: overnight training queue finished successfully."
}
catch {
    $summary = [ordered]@{
        status = "failed_closed"
        finished_at = (Get-Date).ToString("s")
        error = $_.Exception.Message
        completed_jobs = $results
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $QueueSummary -Encoding UTF8
    Write-QueueMessage "STOPPED: $($_.Exception.Message)"
    throw
}
