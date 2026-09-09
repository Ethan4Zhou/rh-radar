#!/usr/bin/env python3
"""Inline data.json into the page. One self-contained file for both GitHub Pages
and the Claude artifact."""
from pathlib import Path
S = Path(__file__).resolve().parent
head = (S / "template.head.html").read_text()
js   = (S / "app.js").read_text()
data = (S / "data.json").read_text().replace("</", "<\\/")
shared_path = S.parent / "data" / "excluded.json"
shared = shared_path.read_text().replace("</", "<\\/") if shared_path.exists() else '{"items":{}}'
out  = (head + "<script>const DATA=" + data + ";\n"
        + "const SHARED_EXCLUDED=" + shared + ";\n"
        + js.replace("</", "<\\/") + "</script>")
(S / "index.html").write_text(out)
print(f"index.html {len(out)//1024} KB")
