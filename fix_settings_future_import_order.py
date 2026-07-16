from pathlib import Path

path = Path("alientai_v2/settings.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/settings_BACKUP_FIX_FUTURE_IMPORT_ORDER.py")
backup.write_text(text, encoding="utf-8")

lines = text.splitlines()

# Remove duplicate import lines we may have inserted in the wrong place.
cleaned = []
future_lines = []
normal_imports = []

for line in lines:
    stripped = line.strip()

    if stripped == "from __future__ import annotations":
        future_lines.append("from __future__ import annotations")
        continue

    if stripped in {"import json", "from pathlib import Path"}:
        normal_imports.append(stripped)
        continue

    cleaned.append(line)

# Deduplicate.
future_lines = list(dict.fromkeys(future_lines))
normal_imports = list(dict.fromkeys(normal_imports))

# If file originally had no future import, don't add one.
# But your file does have it, so preserve it first.
new_lines = []

if future_lines:
    new_lines.extend(future_lines)
    new_lines.append("")

# Put regular imports after future import.
for imp in ["import json", "from pathlib import Path"]:
    if imp in normal_imports:
        new_lines.append(imp)

if normal_imports:
    new_lines.append("")

# Remove leading blank lines from remaining original content.
while cleaned and cleaned[0].strip() == "":
    cleaned.pop(0)

new_lines.extend(cleaned)

path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

print("Fixed settings.py import order.")
