"""Snapshot of Google's daily trending searches in Brazil (public RSS) -> site/trends.json.

Interest-over-time for specific keywords needs the unofficial pytrends API, which Google rate-limits (HTTP 429);
the page links each keyword to Google Trends instead.
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
NS = {"ht": "https://trends.google.com/trending/rss"}

xml = requests.get("https://trends.google.com/trending/rss?geo=BR", timeout=30).content
itens = []
for it in ET.fromstring(xml).iter("item"):
    news = it.find("ht:news_item", NS)
    itens.append({
        "termo": it.findtext("title"),
        "buscas": it.findtext("ht:approx_traffic", namespaces=NS),
        "noticia": news.findtext("ht:news_item_title", namespaces=NS) if news is not None else None,
        "fonte": news.findtext("ht:news_item_source", namespaces=NS) if news is not None else None,
        "url": news.findtext("ht:news_item_url", namespaces=NS) if news is not None else None,
    })
out = {"coletado_em": datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M"), "itens": itens}
(ROOT / "site" / "trends.json").write_text(json.dumps(out, ensure_ascii=False))
print(f"{len(itens)} trending searches; first: {[i['termo'] for i in itens[:8]]}")
