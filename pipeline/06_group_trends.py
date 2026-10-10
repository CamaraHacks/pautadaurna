"""Google Trends per abstainer group, refreshed daily through SerpApi -> site/trends_grupos.json.

Google Trends has no age or class breakdown, so each group is read through five search terms drawn from its themes
(site/grupos.json, "termos_busca") and through geography: a term's interest by state is weighted by where the group's
abstainers live (index vs. all abstainers), and rising queries come from the state where the group weighs most.

Budget (SerpApi free plan, 100 searches/month): each day refreshes 3 terms x 2 searches (rising queries in the group's
state + interest by state); on Sundays it refreshes the relative volume of each group's five terms instead (5 searches).
State lives in data/trends_store.json (per-term data, rotation pointer, monthly counter); the first run seeds it from
the 10/10/2026 pytrends cache in data/raw/trends/. Without SERPAPI_KEY the page JSON is rebuilt from the store only.

Usage: SERPAPI_KEY=... python pipeline/06_group_trends.py [--dry-run]
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "trends"
STORE = ROOT / "data" / "trends_store.json"
OUT = ROOT / "site" / "trends_grupos.json"
TEMAS_POR_DIA = 3
LIMITE_MES = 95  # stop before the 100 free searches

UF_NOME = {"Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
           "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
           "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
           "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
           "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
           "Sergipe": "SE", "Tocantins": "TO"}

# Rising queries that name candidates or politicians are dropped to keep the kit nonpartisan; so are queries about
# other years, long-tail queries, and off-topic ones (films, brands, lotteries) found when reviewing the 10/10 run.
POLITICA = ("flavio", "flávio", "bolsonaro", "lula", "haddad", "alckmin", "cury", "renan", "caiado", "zema", "samara",
            "tarcisio", "tarcísio", "moraes", "michelle", "janja", "careca", "portinho", "prado", "ciro", "marina",
            "partido", " pt", " pl", "deputad", "senador", "governador", "prefeit", "ministr", "presidente", "stf", "cpi",
            "candidat", "governo", "quem criou", "roubo", "corrupção", "rui costa", "patrus", "ruas", "congelamento",
            "congelar", "escandalo", "escândalo", "rombo", "inventou")
FORA = ("filme", "firefox", "mega sena", "disney", "cabelo maluco", "fantasia", "kovi", "maquininha", "wiki", "chuca",
        "quality", "alo motorista", "dívida de sangue", "itapetininga", "são gonçalo", "brooklin", "carrefour", "g1 ",
        "gloria", "unidas", "boc", "assalto ao", "se acalme", "grande assalto", "marido de aluguel")


def limpa(q):
    ql = " " + q.lower().replace(".", " ")
    if any(w in ql for w in POLITICA + FORA):
        return False
    if any(y != "2026" for y in re.findall(r"\b20\d\d\b", ql)):
        return False
    return len(q.split()) <= 4


# ---------- SerpApi ----------
def serpapi(params):
    r = requests.get("https://serpapi.com/search.json", timeout=60, params={
        "engine": "google_trends", "hl": "pt-BR", "date": "today 1-m", "api_key": os.environ["SERPAPI_KEY"], **params})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data


def rising(term, uf):
    d = serpapi({"q": term, "geo": f"BR-{uf}", "data_type": "RELATED_QUERIES"})
    return [q["query"] for q in d.get("related_queries", {}).get("rising", [])][:10]


def by_state(term):
    d = serpapi({"q": term, "geo": "BR", "data_type": "GEO_MAP_0"})
    out = {}
    for x in d.get("interest_by_region", []):
        uf = (x.get("geo") or "").replace("BR-", "") or UF_NOME.get(x.get("location"))
        if uf:
            out[uf] = int(x.get("extracted_value") or 0)
    return out


def volumes(terms):
    d = serpapi({"q": ",".join(terms), "geo": "BR", "data_type": "TIMESERIES"})
    rows = d.get("interest_over_time", {}).get("timeline_data", [])
    tot = {t: 0.0 for t in terms}
    for row in rows:
        for v in row.get("values", []):
            if v.get("query") in tot:
                tot[v["query"]] += float(v.get("extracted_value") or 0)
    return {t: round(tot[t] / max(1, len(rows)), 1) for t in terms}


# ---------- store ----------
def seed(grupos):
    """First run: build the store from the 10/10/2026 pytrends cache."""
    st = {"termos": {}, "volumes": {}, "fila": 0, "uso": {"mes": "", "buscas": 0}, "ultima_coleta": ""}
    for g in grupos:
        gid = g["id"]
        base = CACHE / f"{gid}.json"
        if base.exists():
            st["volumes"][gid] = {"valores": json.loads(base.read_text())["volume"], "atualizado_em": "10/10/2026"}
        uf_files = list(CACHE.glob(f"{gid}_*.json"))
        uf_ref = uf_files[0].stem.split("_")[1] if uf_files else None
        em_uf = json.loads(uf_files[0].read_text())["em_alta"] if uf_files else {}
        for t in g["termos_busca"]:
            f = CACHE / f"uf_{t}.json"
            st["termos"][t] = {
                "uf": json.loads(f.read_text()) if f.exists() else {},
                "uf_ref": uf_ref,
                "em_alta_uf": [q["query"] for q in em_uf.get(t, [])],
                "atualizado_em": "10/10/2026",
            }
    return st


def coleta(st, grupos, uf_grupo, dry):
    hoje = date.today()
    mes = hoje.strftime("%Y-%m")
    if st["uso"]["mes"] != mes:
        st["uso"] = {"mes": mes, "buscas": 0}
    if st["ultima_coleta"] == hoje.isoformat():
        print("already collected today; rebuilding page data only")
        return
    if hoje.weekday() == 6:  # Sunday: relative volumes per group
        plano = [("volume", g["id"], g["termos_busca"]) for g in grupos]
        custo = len(plano)
    else:
        termos = [(g["id"], t) for g in grupos for t in g["termos_busca"]]
        pick = [termos[(st["fila"] + i) % len(termos)] for i in range(TEMAS_POR_DIA)]
        plano = [("termo", gid, t) for gid, t in pick]
        custo = 2 * len(plano)
    print(f"plan for {hoje}: {[(p[0], p[1], p[2]) for p in plano]} · cost {custo} · used {st['uso']['buscas']}/{LIMITE_MES}")
    if st["uso"]["buscas"] + custo > LIMITE_MES:
        print("monthly budget reached; skipping collection")
        return
    if dry:
        return
    stamp = hoje.strftime("%d/%m/%Y")
    for kind, gid, x in plano:
        if kind == "volume":
            st["volumes"][gid] = {"valores": volumes(x), "atualizado_em": stamp}
            st["uso"]["buscas"] += 1
        else:
            uf = uf_grupo[gid]
            st["termos"][x] = {"uf": by_state(x), "uf_ref": uf, "em_alta_uf": rising(x, uf), "atualizado_em": stamp}
            st["uso"]["buscas"] += 2
            st["fila"] += 1
    st["ultima_coleta"] = hoje.isoformat()


# ---------- page data ----------
def main():
    dry = "--dry-run" in sys.argv
    g = json.loads((ROOT / "site" / "grupos.json").read_text())
    data = json.loads((ROOT / "site" / "data.json").read_text())
    ids = data["grupos_ordem"]

    # group weight per UF: share of the group among the UF's abstainers vs. the Brazil share
    rows = [(r[2], r[11]) for r in data["municipios"] if r[11]]
    abst = pd.DataFrame([[uf] + [s[2 * i + 1] for i in range(len(ids))] for uf, s in rows], columns=["uf"] + ids)
    uf_tot = abst.groupby("uf").sum()
    peso = (uf_tot.div(uf_tot.sum(axis=1), axis=0)) / (uf_tot.sum() / uf_tot.sum().sum())
    # state where the group weighs most, among states holding >= 2% of its abstainers
    uf_grupo = {gid: peso[gid][uf_tot[gid] >= 0.02 * uf_tot[gid].sum()].idxmax() for gid in ids}

    st = json.loads(STORE.read_text()) if STORE.exists() else seed(g["grupos"])
    if os.environ.get("SERPAPI_KEY"):
        coleta(st, g["grupos"], uf_grupo, dry)
    else:
        print("SERPAPI_KEY not set; rebuilding page data from the store")
    if not dry:
        STORE.write_text(json.dumps(st, ensure_ascii=False, indent=1))

    out = {"periodo": "últimos 30 dias", "grupos": {}}
    datas = []
    for grp in g["grupos"]:
        gid = grp["id"]
        w_g, w_all = uf_tot[gid], uf_tot.sum(axis=1)
        vol = st["volumes"].get(gid, {}).get("valores", {})
        termos = {}
        for t in grp["termos_busca"]:
            d = st["termos"].get(t)
            if not d:
                continue
            it = pd.Series(d["uf"], dtype=float).reindex(uf_tot.index).fillna(0)
            base = float((it * w_all).sum() / w_all.sum())
            termos[t] = {
                "volume": vol.get(t, 0),
                "indice": round(float((it * w_g).sum() / w_g.sum()) / base, 2) if base else 1.0,
                "top_uf": [u for u, _ in sorted(d["uf"].items(), key=lambda x: -x[1])[:3]],
                "em_alta_uf": [q for q in d["em_alta_uf"] if limpa(q)][:4],
                "uf_ref": d["uf_ref"],
                "atualizado_em": d["atualizado_em"],
            }
            datas.append(d["atualizado_em"])
        out["grupos"][gid] = {"uf_grupo": uf_grupo[gid], "peso_uf_grupo": round(float(peso[gid][uf_grupo[gid]]), 2),
                              "termos": termos}
    out["atualizado_em"] = max(datas, key=lambda s: s[6:] + s[3:5] + s[:2]) if datas else None
    if not dry:
        OUT.write_text(json.dumps(out, ensure_ascii=False))
    print(f"{OUT.name}: {sum(len(v['termos']) for v in out['grupos'].values())} terms · latest {out['atualizado_em']}")


if __name__ == "__main__":
    main()
