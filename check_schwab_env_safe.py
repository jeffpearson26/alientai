import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

keys = [
    "SCHWAB_API_KEY",
    "SCHWAB_APP_KEY",
    "SCHWAB_CLIENT_ID",
    "SCHWAB_CONSUMER_KEY",
    "CHARLES_SCHWAB_API_KEY",
]

secrets = [
    "SCHWAB_APP_SECRET",
    "SCHWAB_CLIENT_SECRET",
    "SCHWAB_SECRET",
    "CHARLES_SCHWAB_APP_SECRET",
]

callbacks = [
    "SCHWAB_CALLBACK_URL",
    "SCHWAB_REDIRECT_URI",
    "SCHWAB_REDIRECT_URL",
]

print("Schwab env check")
print("-" * 80)

for name in keys:
    v = os.getenv(name)
    if v:
        print(f"{name}: present length={len(v.strip())} starts={v.strip()[:5]} ends={v.strip()[-5:]} raw_has_outer_space={v != v.strip()}")

for name in secrets:
    v = os.getenv(name)
    if v:
        print(f"{name}: present length={len(v.strip())} raw_has_outer_space={v != v.strip()}")

for name in callbacks:
    v = os.getenv(name)
    if v:
        clean = v.strip()
        print(f"{name}: {clean}")
        print("  trailing slash:", clean.endswith("/"))
        print("  raw_has_outer_space:", v != clean)

print("-" * 80)
print("Token file:")
p = Path("old_system_reference/token.json")
print("exists:", p.exists())
if p.exists():
    print("size:", p.stat().st_size)
    print("modified:", p.stat().st_mtime)
