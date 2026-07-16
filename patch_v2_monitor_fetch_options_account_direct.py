from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_OPTIONS_MONITOR_DIRECT_FETCH.py")
backup.write_text(text, encoding="utf-8")

old = '''    const res = await fetch("/v2/status?t=" + Date.now());
    const data = await res.json();

    const account = data.options_paper_account || {};
'''

new = '''    const statusRes = await fetch("/v2/status?t=" + Date.now());
    const data = await statusRes.json();

    const accountRes = await fetch("/v2/options-paper-account?t=" + Date.now());
    const accountPayload = await accountRes.json();

    const account = accountPayload.account || data.options_paper_account || {};
'''

if old not in text:
    raise SystemExit("Could not find the existing options monitor fetch block.")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Patched monitor to fetch /v2/options-paper-account directly.")
