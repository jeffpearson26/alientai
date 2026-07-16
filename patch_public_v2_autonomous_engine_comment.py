from pathlib import Path

path = Path("alientai_v2/public_v2_page.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/public_v2_page_BACKUP_BEFORE_ENGINE_COMMENT.py")
backup.write_text(text, encoding="utf-8")

engine_comment = '''
    <div style="
      margin:12px 0 20px 0;
      padding:14px 16px;
      border:1px solid rgba(96,165,250,0.28);
      border-radius:16px;
      background:rgba(30,64,175,0.16);
      color:#dbeafe;
      line-height:1.45;
      max-width:980px;
    ">
      <div style="font-size:15px;font-weight:800;margin-bottom:6px;">
        Autonomous Trading System
      </div>
      <div style="font-size:14px;color:#bfdbfe;">
        AlientAI V2 is an autonomous experimental paper-trading system. Four trading engines are currently active from a planned total of eight.
      </div>
      <div style="font-size:13px;color:#93c5fd;margin-top:8px;">
        Active engines: <strong>prediction_20day</strong>, <strong>momentum_5min</strong>, <strong>similarity_engine</strong>, and <strong>transformer_20day</strong>.
      </div>
    </div>
'''

if "Autonomous Trading System" in text:
    print("Autonomous Trading System comment is already on the public page.")
else:
    # Best placement: right after Built by JEP26 if present.
    if "Built by JEP26" in text:
        pos = text.find("Built by JEP26")
        close_pos = text.find("</div>", pos)
        if close_pos == -1:
            raise SystemExit("Found Built by JEP26, but could not find closing div.")

        close_pos = close_pos + len("</div>")
        text = text[:close_pos] + "\n" + engine_comment + text[close_pos:]

    # Backup placement: right below page title.
    elif "<h1>Public V2 Research Monitor</h1>" in text:
        text = text.replace(
            "<h1>Public V2 Research Monitor</h1>",
            "<h1>Public V2 Research Monitor</h1>\n" + engine_comment,
            1,
        )

    # Last backup: near read-only description.
    elif "Read-only experimental market intelligence monitor" in text:
        text = text.replace(
            "Read-only experimental market intelligence monitor",
            engine_comment + "\n    Read-only experimental market intelligence monitor",
            1,
        )
    else:
        raise SystemExit("Could not find a safe location to insert the autonomous system comment.")

    path.write_text(text, encoding="utf-8")
    print("Added autonomous trading system comment to public V2 page.")
