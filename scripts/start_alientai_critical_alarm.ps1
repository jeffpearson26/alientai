param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_.-]+$")]
    [string]$IncidentId,

    [Parameter(Mandatory = $true)]
    [string]$MessageBase64,

    [ValidateRange(2, 60)]
    [int]$IntervalSeconds = 5,

    [switch]$SilentSelfTest
)

$ErrorActionPreference = "Stop"

function ConvertFrom-Base64Utf8 {
    param([Parameter(Mandatory = $true)][string]$Value)

    try {
        return [System.Text.Encoding]::UTF8.GetString(
            [System.Convert]::FromBase64String($Value)
        )
    }
    catch {
        throw "MessageBase64 must contain valid base64-encoded UTF-8 text."
    }
}

function Write-AlertState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Incident
    )

    $payload = [ordered]@{
        schema_version = 1
        incident_id = $Incident
        status = $Status
        message = $Message
        process_id = $PID
        updated_at_utc = [DateTime]::UtcNow.ToString("o")
    }
    $json = $payload | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText(
        $Path,
        $json + [Environment]::NewLine,
        [System.Text.UTF8Encoding]::new($false)
    )
}

$message = ConvertFrom-Base64Utf8 -Value $MessageBase64
if ([string]::IsNullOrWhiteSpace($message)) {
    throw "The critical-alert message may not be empty."
}

$stateRoot = Join-Path $env:LOCALAPPDATA "AlienTAI\CriticalAlerts"
[System.IO.Directory]::CreateDirectory($stateRoot) | Out-Null
$statePath = Join-Path $stateRoot "$IncidentId.json"
$ackPath = Join-Path $stateRoot "$IncidentId.ack"

$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $mutexDigest = $sha256.ComputeHash(
        [System.Text.Encoding]::UTF8.GetBytes($IncidentId)
    )
}
finally {
    $sha256.Dispose()
}
$mutexSuffix = -join (
    $mutexDigest[0..11] | ForEach-Object { $_.ToString("x2") }
)
$mutex = [System.Threading.Mutex]::new(
    $false,
    "Local\AlienTAI_CriticalAlert_$mutexSuffix"
)
$ownsMutex = $false

try {
    $ownsMutex = $mutex.WaitOne(0)
    if (-not $ownsMutex) {
        exit 0
    }

    if (Test-Path -LiteralPath $ackPath -PathType Leaf) {
        exit 0
    }

    Write-AlertState `
        -Path $statePath `
        -Status "ACTIVE" `
        -Message $message `
        -Incident $IncidentId

    if ($SilentSelfTest) {
        [System.IO.File]::WriteAllText(
            $ackPath,
            [DateTime]::UtcNow.ToString("o") + [Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false)
        )
        Write-AlertState `
            -Path $statePath `
            -Status "SELF_TEST_COMPLETE" `
            -Message $message `
            -Incident $IncidentId
        exit 0
    }

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = [System.Windows.Forms.Form]::new()
    $form.Text = "AlienTAI - Critical Research Blocker"
    $form.Size = [System.Drawing.Size]::new(720, 360)
    $form.StartPosition = "CenterScreen"
    $form.TopMost = $true
    $form.ShowInTaskbar = $true
    $form.ControlBox = $false
    $form.BackColor = [System.Drawing.Color]::FromArgb(22, 27, 34)
    $form.ForeColor = [System.Drawing.Color]::White

    $title = [System.Windows.Forms.Label]::new()
    $title.Text = "AlienTAI needs your attention"
    $title.Font = [System.Drawing.Font]::new(
        "Segoe UI",
        19,
        [System.Drawing.FontStyle]::Bold
    )
    $title.ForeColor = [System.Drawing.Color]::FromArgb(255, 193, 7)
    $title.Location = [System.Drawing.Point]::new(28, 24)
    $title.Size = [System.Drawing.Size]::new(650, 44)
    $form.Controls.Add($title)

    $incidentLabel = [System.Windows.Forms.Label]::new()
    $incidentLabel.Text = "Incident: $IncidentId"
    $incidentLabel.Font = [System.Drawing.Font]::new("Segoe UI", 9)
    $incidentLabel.ForeColor = [System.Drawing.Color]::FromArgb(173, 181, 189)
    $incidentLabel.Location = [System.Drawing.Point]::new(30, 72)
    $incidentLabel.Size = [System.Drawing.Size]::new(645, 22)
    $form.Controls.Add($incidentLabel)

    $messageLabel = [System.Windows.Forms.Label]::new()
    $messageLabel.Text = $message
    $messageLabel.Font = [System.Drawing.Font]::new("Segoe UI", 12)
    $messageLabel.Location = [System.Drawing.Point]::new(30, 105)
    $messageLabel.Size = [System.Drawing.Size]::new(645, 116)
    $messageLabel.AutoEllipsis = $true
    $form.Controls.Add($messageLabel)

    $instruction = [System.Windows.Forms.Label]::new()
    $instruction.Text = (
        "The alarm repeats until you acknowledge it. " +
        "Acknowledging does not mark the underlying blocker as fixed."
    )
    $instruction.Font = [System.Drawing.Font]::new("Segoe UI", 9)
    $instruction.ForeColor = [System.Drawing.Color]::FromArgb(173, 181, 189)
    $instruction.Location = [System.Drawing.Point]::new(30, 228)
    $instruction.Size = [System.Drawing.Size]::new(645, 36)
    $form.Controls.Add($instruction)

    $acknowledgeButton = [System.Windows.Forms.Button]::new()
    $acknowledgeButton.Text = "Acknowledge"
    $acknowledgeButton.Font = [System.Drawing.Font]::new(
        "Segoe UI",
        11,
        [System.Drawing.FontStyle]::Bold
    )
    $acknowledgeButton.Location = [System.Drawing.Point]::new(500, 270)
    $acknowledgeButton.Size = [System.Drawing.Size]::new(175, 42)
    $acknowledgeButton.BackColor = [System.Drawing.Color]::FromArgb(13, 110, 253)
    $acknowledgeButton.ForeColor = [System.Drawing.Color]::White
    $acknowledgeButton.FlatStyle = "Flat"
    $form.Controls.Add($acknowledgeButton)

    $timer = [System.Windows.Forms.Timer]::new()
    $timer.Interval = $IntervalSeconds * 1000

    $playAlarm = {
        try {
            [System.Media.SystemSounds]::Exclamation.Play()
        }
        catch {
            # Continue to the independent console-beep fallback.
        }
        try {
            [Console]::Beep(1250, 450)
            [Console]::Beep(900, 300)
        }
        catch {
            # Some sound drivers do not implement Console.Beep.
        }
    }

    $acknowledge = {
        if (-not (Test-Path -LiteralPath $ackPath -PathType Leaf)) {
            [System.IO.File]::WriteAllText(
                $ackPath,
                [DateTime]::UtcNow.ToString("o") + [Environment]::NewLine,
                [System.Text.UTF8Encoding]::new($false)
            )
        }
        Write-AlertState `
            -Path $statePath `
            -Status "ACKNOWLEDGED" `
            -Message $message `
            -Incident $IncidentId
        $timer.Stop()
        $form.Close()
    }

    $acknowledgeButton.Add_Click($acknowledge)
    $timer.Add_Tick({
        if (Test-Path -LiteralPath $ackPath -PathType Leaf) {
            & $acknowledge
            return
        }
        & $playAlarm
    })
    $form.Add_Shown({
        & $playAlarm
        $timer.Start()
        $form.Activate()
    })

    [System.Windows.Forms.Application]::Run($form)
}
finally {
    if ($ownsMutex) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
