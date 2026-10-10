"""Curated third-party material from Acervo da Vitória -> site/acervo.json.

The collection (https://acervodavitoria.pages.dev, files on Google Drive) publishes an open index (catalog.json) with no
stated authorship or license and no review (thematicReview = pending). We link to the files; we do not rehost them.

Curation rules:
- categories: videos, artes, selfie (real videos recorded by Lula), guias
- out: "novelinha" and "memes" (AI-generated, often with the candidates' image; Res. TSE 23.755/2026) and anything
  else that says it is AI-made
- out: accusations of crimes without a conviction (theft, corruption, militia...), except Lula's own selfie videos,
  which are kept with the label "fala de campanha do Lula"
- in only when the item matches one of our pautas (or general turnout mobilization)
- acervo/regras.csv (id,acao,motivo) lets the editor force "aprovar" or "barrar" single items; AI items stay out

Usage: python pipeline/10_acervo.py
"""
import csv
import json
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://acervodavitoria.pages.dev"
CATEGORIAS = {"videos": "Vídeo", "artes": "Arte", "selfie": "Selfie do Lula", "guias": "Guia"}
IA = re.compile(r"\bIA\b|intelig[eê]ncia artificial|gerad[oa] por ia|animação ia", re.I)
ACUSACAO = re.compile(r"roub|ladr|corrup|rachad|mans[aã]o|mil[ií]cia|bandid|banco master|vorcaro|propina|lavagem|desvio"
                      r"|esquema|queiroz|den[uú]ncia|crime organizado|escând|escand", re.I)
# (grupo, índice da pauta em site/pautas.json) -> tema
TEMAS = {
    ("idosos", 0): r"farm[aá]cia|rem[eé]dio",
    ("idosos", 1): r"aposentad|sal[aá]rio m[ií]nimo|previd[eê]n",
    ("idosos", 2): r"\bINSS\b",
    ("jovens", 0): r"6x1|escala|jornada",
    ("jovens", 1): r"emprego|aprendiz",
    ("jovens", 2): r"\benem\b|educa|universidade|p[eé]-de-meia|ensino",
    ("base", 0): r"fome|comida|alimenta|bolsa fam|cesta b|fila do osso",
    ("base", 1): r"\bg[aá]s\b|botij",
    ("base", 2): r"sal[aá]rio m[ií]nimo|poder de compra",
    ("media", 0): r"6x1|escala|jornada",
    ("media", 1): r"d[ií]vida|desenrola|juros|endivid",
    ("media", 2): r"seguran[cç]a|viol[eê]ncia|pol[ií]cia|armas",
    ("superior", 0): r"imposto de renda|isen[cç][aã]o",
    ("superior", 1): r"democracia|constitui|\bSTF\b|golpe|institui",
    ("superior", 2): r"desemprego|economia|\bPIB\b",
}
GERAL = re.compile(r"mobiliza|participa[cç][aã]o eleitoral|absten|virada|2º turno|segundo turno", re.I)
POR_PAUTA = 8


def regras():
    f = ROOT / "acervo" / "regras.csv"
    if not f.exists():
        return {}
    with open(f, newline="", encoding="utf-8") as h:
        return {r["id"].strip(): r["acao"].strip().lower() for r in csv.DictReader(h) if r.get("id", "").strip() and not r["id"].startswith("#")}


def main():
    cat = requests.get(f"{BASE}/catalog.json", timeout=60).json()
    forca = regras()
    out, fora = [], {"ia": 0, "acusacao": 0, "categoria": 0, "sem_pauta": 0, "barrado": 0}
    for x in cat["files"]:
        texto = " ".join([x["title"], x["file"], x["theme"], x["summary"], " ".join(x["tags"])])
        acao = forca.get(x["id"])
        if x["category"] in ("novelinha", "memes") or IA.search(texto):
            fora["ia"] += 1
            continue
        if acao == "barrar":
            fora["barrado"] += 1
            continue
        if x["category"] not in CATEGORIAS:
            fora["categoria"] += 1
            continue
        selfie = x["category"] == "selfie"
        if ACUSACAO.search(texto) and not selfie and acao != "aprovar":
            fora["acusacao"] += 1
            continue
        pautas = [f"{g}:{i}" for (g, i), rx in TEMAS.items() if re.search(rx, texto, re.I)]
        if not pautas and GERAL.search(texto):
            pautas = ["geral"]
        if not pautas:
            fora["sem_pauta"] += 1
            continue
        out.append({
            "id": x["id"], "titulo": x["title"], "tipo": CATEGORIAS[x["category"]], "tema": x["theme"],
            "resumo": x["summary"], "mime": x["mime"], "mb": round(x["size"] / 1e6, 1), "data": x["modified"][:10],
            "capa": f"{BASE}/{x['thumbnail']}" if x.get("thumbnail") else None,
            "ver": x["url"], "baixar": f"https://drive.google.com/uc?export=download&id={x['id']}",
            "selo": "Fala de campanha do Lula" if selfie else "Material de terceiros",
            "pautas": pautas,
        })
    # cap per pauta: videos and selfies first, then newest
    ordem = {"Selfie do Lula": 0, "Vídeo": 1, "Arte": 2, "Guia": 3}
    out.sort(key=lambda v: (ordem[v["tipo"]], v["data"]), reverse=False)
    out.sort(key=lambda v: ordem[v["tipo"]])
    cont, final = {}, []
    for v in out:
        keep = [p for p in v["pautas"] if cont.get(p, 0) < POR_PAUTA]
        if not keep:
            continue
        for p in keep:
            cont[p] = cont.get(p, 0) + 1
        final.append({**v, "pautas": keep})
    res = {"fonte": BASE, "atualizado": cat.get("updated"), "itens": final}
    (ROOT / "site" / "acervo.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")))
    print(f"acervo: {len(cat['files'])} itens no índice · {len(final)} publicados · fora: {fora}")
    print("por pauta:", dict(sorted(cont.items())))


if __name__ == "__main__":
    main()
