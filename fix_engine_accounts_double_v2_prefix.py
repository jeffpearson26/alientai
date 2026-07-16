from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_ENGINE_ACCOUNTS_PREFIX_FIX.py")
backup.write_text(text, encoding="utf-8")

old = '@router.get("/v2/engine-accounts")'
new = '@router.get("/engine-accounts")'

if old in text:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("Fixed route decorator:")
    print(old, "->", new)
    print("Backup:", backup)
else:
    print("Did not find:", old)
    print("Checking current engine route lines...")
    for line in text.splitlines():
        if "engine-accounts" in line:
            print(line)
