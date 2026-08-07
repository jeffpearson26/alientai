# AlienTAI Critical Blocker Alarm

AlienTAI has a local audible alarm for exceptional failures that stop research
testing or require Jeff's action. It is research infrastructure only and has
no trading or order capability.

Raise an alarm with a unique incident ID:

```powershell
.\scripts\raise_alientai_critical_alarm.ps1 `
  -IncidentId "d_drive_missing_20260807T1131Z" `
  -Message "D:\AlientAI is unavailable. Reconnect the external SSD."
```

The worker:

- shows a topmost AlienTAI incident window;
- plays both the Windows exclamation sound and a two-tone beep every five
  seconds;
- keeps sounding until Jeff clicks **Acknowledge**;
- prevents duplicate alarm windows for the same incident ID with a named
  mutex; and
- stores only small non-secret state files under
  `%LOCALAPPDATA%\AlienTAI\CriticalAlerts`.

Acknowledgment means only that Jeff saw the alert. It never marks the
underlying data, timing, credential, collector, disk, or model problem as
fixed. The normal fail-closed audit must pass before work resumes.

An alarm can also be acknowledged from PowerShell:

```powershell
.\scripts\acknowledge_alientai_critical_alarm.ps1 `
  -IncidentId "d_drive_missing_20260807T1131Z"
```

Use `-All` only when Jeff intentionally acknowledges every active incident.

## Alarm threshold

Raise the audible alarm when a new event:

- makes the D-drive research store unavailable or violates its free-space
  gate;
- stops all promising-model testing or a required singular collector;
- risks missing a frozen pre-entry decision window;
- requires Jeff to renew credentials or physically restore hardware; or
- reveals corruption, hash mismatch, duplicate live collectors, or another
  fail-closed integrity condition requiring Jeff's prompt action.

Do not alarm for honest model abstentions, ordinary pending horizons,
scheduled wait states, negative validation results, or a model-specific
blocker when unaffected programs can continue and Jeff need not act.

Never include credentials, tokens, API keys, account details, or other secrets
in an alarm message.
