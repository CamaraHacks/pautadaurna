"""Inline site/data.json and the municipal TopoJSON into site/template.html -> site/index.html.

One self-contained file serves both GitHub Pages and the Claude artifact (which blocks runtime fetches).
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

html = (SITE / "template.html").read_text()
html = html.replace("/*__DATA__*/null", (SITE / "data.json").read_text())
# municipal mesh is versioned in data/ so CI can export without downloading the TSE files
malha = ROOT / "data" / "malha_municipios.topojson"
if not malha.exists():
    malha = ROOT / "data" / "raw" / "malha_municipios.topojson"
html = html.replace("/*__TOPO__*/null", malha.read_text())
html = html.replace("/*__GRUPOS__*/null", (SITE / "grupos.json").read_text())
tg = SITE / "trends_grupos.json"  # optional, from 06_group_trends.py
html = html.replace("/*__TRENDS_GRUPOS__*/null", tg.read_text() if tg.exists() else "null")
html = html.replace("/*__REGIOES__*/null", (SITE / "regioes.json").read_text())
html = html.replace("/*__PAUTAS__*/null", (SITE / "pautas.json").read_text())
acv = SITE / "acervo.json"  # from 10_acervo.py
html = html.replace("/*__ACERVO__*/null", acv.read_text() if acv.exists() else "null")
vids = SITE / "videos.json"  # from 09_videos.py
html = html.replace("/*__VIDEOS__*/[]", vids.read_text() if vids.exists() else "[]")
# GoatCounter site code (e.g. "pautadaurna"), from the environment; empty disables measurement
html = html.replace('/*__GC__*/""', json.dumps(os.environ.get("GOATCOUNTER", "")))
assert "/*__" not in html, "unfilled placeholder"
(SITE / "index.html").write_text(html)
print(f"site/index.html: {len(html) / 1e6:.2f} MB")
