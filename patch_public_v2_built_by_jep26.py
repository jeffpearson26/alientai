from pathlib import Path

path = Path("alientai_v2/public_v2_page.py")
text = path.read_text(encoding="utf-8-sig")

badge = '''
    <div style="
      display:inline-flex;
      align-items:center;
      gap:8px;
      margin:10px 0 18px 0;
      padding:8px 14px;
      border:1px solid rgba(255,255,255,0.18);
      border-radius:999px;
      background:rgba(255,255,255,0.08);
      color:#dbeafe;
      font-size:14px;
      font-weight:700;
      letter-spacing:0.3px;
    ">
      Built by JEP26
    </div>
'''

if "Built by JEP26" in text:
    print("Built by JEP26 is already on the public page.")
else:
    # Best location: right below the public page h1.
    if "<h1>Public V2 Research Monitor</h1>" in text:
        text = text.replace(
            "<h1>Public V2 Research Monitor</h1>",
            "<h1>Public V2 Research Monitor</h1>" + badge,
            1,
        )
    # Backup location: near first paragraph if h1 text changes.
    elif "Read-only experimental market intelligence monitor" in text:
        text = text.replace(
            "Read-only experimental market intelligence monitor",
            badge + "\n    Read-only experimental market intelligence monitor",
            1,
        )
    else:
        raise SystemExit("Could not find a safe place to insert Built by JEP26.")

    path.write_text(text, encoding="utf-8")
    print("Added Built by JEP26 to public V2 page.")
