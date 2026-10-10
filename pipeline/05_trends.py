"""Snapshot of Google's daily trending searches in Brazil (public RSS) -> site/trends.json.

The geo=BR feed mixes in foreign topics (European football, US news) that Brazilians search for. We keep a topic
only when every news item Google attaches to it comes from a Brazilian outlet, and show the first Brazilian story.
Interest-over-time for specific keywords needs the unofficial pytrends API, which Google rate-limits (HTTP 429);
the page links each keyword to Google Trends instead.
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
NS = {"ht": "https://trends.google.com/trending/rss"}
# Brazilian outlets whose domain does not end in .br
BR_HOSTS = ("globo.com", "uol.com", "brasil247.com", "metropoles.com", "r7.com", "exame.com", "gazetaesportiva.com",
            "aloalobahia.com", "cartacapital.com", "infomoney.com", "sbt.com", "band.com", "ig.com", "terra.com",
            "poder360.com", "cnnbrasil.com", "jovempan.com", "lance.com", "ge.globo.com")


def brasileiro(url):
    host = urlparse(url or "").netloc.lower()
    return host.endswith(".br") or any(host == h or host.endswith("." + h) for h in BR_HOSTS)


def main():
    xml = requests.get("https://trends.google.com/trending/rss?geo=BR&hours=48", timeout=30).content
    itens, descartados = [], []
    for it in ET.fromstring(xml).iter("item"):
        news = [{"titulo": n.findtext("ht:news_item_title", namespaces=NS), "fonte": n.findtext("ht:news_item_source", namespaces=NS),
                 "url": n.findtext("ht:news_item_url", namespaces=NS)} for n in it.findall("ht:news_item", NS)]
        termo = it.findtext("title")
        if not news or not all(brasileiro(n["url"]) for n in news):
            descartados.append(termo)
            continue
        itens.append({"termo": termo, "buscas": it.findtext("ht:approx_traffic", namespaces=NS),
                      "noticia": news[0]["titulo"], "fonte": news[0]["fonte"], "url": news[0]["url"]})
    out = {"coletado_em": datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M"), "itens": itens}
    (ROOT / "site" / "trends.json").write_text(json.dumps(out, ensure_ascii=False))
    print(f"kept {len(itens)}: {[i['termo'] for i in itens]}")
    print(f"dropped {len(descartados)} (non-Brazilian sources): {descartados}")


if __name__ == "__main__":
    main()
