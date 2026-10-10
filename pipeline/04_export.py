"""Inline site/data.json and the municipal TopoJSON into site/template.html -> site/index.html.

One self-contained file serves both GitHub Pages and the Claude artifact (which blocks runtime fetches).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

html = (SITE / "template.html").read_text()
html = html.replace("/*__DATA__*/null", (SITE / "data.json").read_text())
html = html.replace("/*__TOPO__*/null", (ROOT / "data" / "raw" / "malha_municipios.topojson").read_text())
html = html.replace("/*__GRUPOS__*/null", (SITE / "grupos.json").read_text())
tg = SITE / "trends_grupos.json"  # optional, from 06_group_trends.py
html = html.replace("/*__TRENDS_GRUPOS__*/null", tg.read_text() if tg.exists() else "null")
assert "/*__" not in html, "unfilled placeholder"
(SITE / "index.html").write_text(html)
print(f"site/index.html: {len(html) / 1e6:.2f} MB")
