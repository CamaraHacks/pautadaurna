"""Google Trends per abstainer group -> site/trends_grupos.json.

Google Trends has no age or class breakdown, so each group is represented by five search terms drawn from its
themes and pains (site/grupos.json, "termos_busca"). For each group we fetch, over the last 30 days in Brazil:
relative volume of the five terms, interest by state (UF), and rising related queries (used as hashtag ideas).
The unofficial API is rate-limited, so every response is cached in data/raw/trends/ and the script can be rerun
until it completes.
"""
import json
import time
from pathlib import Path

import pandas as pd
from pytrends.request import TrendReq

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "trends"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
UF_NOME = {"Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
           "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
           "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
           "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
           "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
           "Sergipe": "SE", "Tocantins": "TO"}
# Rising queries that name candidates or politicians are dropped to keep the kit nonpartisan; so are queries
# about other years and long-tail queries that make poor hashtags.
POLITICA = ("flavio", "flávio", "bolsonaro", "lula", "haddad", "alckmin", "cury", "renan", "caiado", "zema", "samara",
            "tarcisio", "tarcísio", "moraes", "michelle", "janja", "careca", "portinho", "prado", "ciro", "marina",
            "partido", " pt", " pl", "deputad", "senador", "governador", "prefeit", "ministr", "presidente", "stf", "cpi",
            "candidat", "governo", "quem criou", "roubo", "corrupção", "rui costa", "patrus", "ruas", "congelamento", "congelar", "escandalo", "escândalo", "rombo", "inventou")
# Off-topic rising queries (films, brands, lotteries...) found when reviewing the 10/10/2026 run
FORA = ("filme", "firefox", "mega sena", "disney", "cabelo maluco", "fantasia", "kovi", "maquininha", "wiki", "chuca",
        "quality", "alo motorista", "dívida de sangue", "itapetininga", "são gonçalo", "brooklin", "carrefour", "g1 ", "gloria", "unidas", "boc", "assalto ao", "se acalme", "grande assalto", "marido de aluguel")


def limpa(q):
    import re
    ql = " " + q.lower().replace(".", " ")
    if any(w in ql for w in POLITICA + FORA):
        return False
    if any(y != "2026" for y in re.findall(r"\b20\d\d\b", ql)):
        return False
    return len(q.split()) <= 4


pt = TrendReq(hl="pt-BR", tz=180, requests_args={"headers": {"User-Agent": UA}})


def fetch(key, terms, geo="BR"):
    """Volume, by-UF interest and rising related queries for up to 5 terms, cached as JSON."""
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(4):
        try:
            pt.build_payload(terms, geo=geo, timeframe="today 1-m")
            iot = pt.interest_over_time()
            time.sleep(4)
            reg = pt.interest_by_region(resolution="REGION", inc_low_vol=True)
            time.sleep(4)
            rel = pt.related_queries()
            break
        except Exception as e:  # 429 or transient
            wait = 30 * (attempt + 1)
            print(f"  {key}: {type(e).__name__}, waiting {wait}s")
            time.sleep(wait)
    else:
        raise SystemExit(f"Google Trends kept refusing '{key}'; rerun later (cached results are kept).")
    out = {
        "termos": terms,
        "volume": {t: round(float(iot[t].mean()), 1) for t in terms},
        "uf": {UF_NOME[n]: {t: int(r[t]) for t in terms} for n, r in reg.iterrows() if n in UF_NOME},
        "em_alta": {t: (rel[t]["rising"].head(6).to_dict("records") if rel.get(t) and rel[t]["rising"] is not None else [])
                    for t in terms},
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, ensure_ascii=False))
    time.sleep(6)
    return out


def fetch_uf(term):
    """Interest by state for a single term (0-100 across states). Multi-term payloads return each term's share
    among the terms instead, which is useless for comparing states."""
    f = CACHE / f"uf_{term}.json"
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(5):
        try:
            pt.build_payload([term], geo="BR", timeframe="today 1-m")
            reg = pt.interest_by_region(resolution="REGION", inc_low_vol=True)
            break
        except Exception as e:
            wait = 30 * (attempt + 1)
            print(f"  uf {term}: {type(e).__name__}, waiting {wait}s")
            time.sleep(wait)
    else:
        raise SystemExit(f"Google Trends kept refusing '{term}'; rerun later (cached results are kept).")
    out = {UF_NOME[n]: int(r[term]) for n, r in reg.iterrows() if n in UF_NOME}
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, ensure_ascii=False))
    time.sleep(8)
    return out


def main():
    g = json.loads((ROOT / "site" / "grupos.json").read_text())
    data = json.loads((ROOT / "site" / "data.json").read_text())
    ids = data["grupos_ordem"]

    # group weight per UF: share of the group among the UF's abstainers vs. the Brazil share (profile year)
    rows = [(r[2], r[11]) for r in data["municipios"] if r[11]]
    abst = pd.DataFrame([[uf] + [s[2 * i + 1] for i in range(len(ids))] for uf, s in rows], columns=["uf"] + ids)
    uf_tot = abst.groupby("uf").sum()
    share_uf = uf_tot.div(uf_tot.sum(axis=1), axis=0)
    share_br = uf_tot.sum() / uf_tot.sum().sum()
    peso = share_uf / share_br

    out = {"coletado_em": time.strftime("%d/%m/%Y"), "periodo": "últimos 30 dias", "grupos": {}}
    for grp in g["grupos"]:
        print(f"group {grp['id']}: {grp['termos_busca']}")
        r = fetch(grp["id"], grp["termos_busca"])
        por_termo = {t: fetch_uf(t) for t in r["termos"]}
        # Group-specific reading of each term: state interest weighted by where THIS group's abstainers live,
        # relative to the same weighting over all abstainers (Trends has no age/class breakdown; geography is the proxy)
        w_g, w_all = uf_tot[grp["id"]], uf_tot.sum(axis=1)
        indice = {}
        for t in r["termos"]:
            it = pd.Series(por_termo[t]).reindex(uf_tot.index).fillna(0)
            indice[t] = round(float((it * w_g).sum() / w_g.sum()) / max(1e-9, float((it * w_all).sum() / w_all.sum())), 2)
        interesse = pd.DataFrame(por_termo).mean(axis=1)  # mean of each term's 0-100 interest per UF
        cruz = pd.DataFrame({"peso": peso[grp["id"]], "interesse": interesse}).dropna()
        # states where the group weighs more among abstainers AND its topics are searched more than the median
        cruz["prioridade"] = (cruz.peso >= 1.0) & (cruz.interesse >= cruz.interesse.median())
        cruz["score"] = cruz.peso.rank(pct=True) + cruz.interesse.rank(pct=True)
        em_alta_t = {t: [q["query"] for q in qs if limpa(q["query"])] for t, qs in r["em_alta"].items()}
        top_uf = {t: [u for u, _ in sorted(por_termo[t].items(), key=lambda x: -x[1])[:3]] for t in r["termos"]}
        # rising queries in the state where the group weighs most (among states holding >= 2% of its abstainers)
        big = uf_tot[grp["id"]] >= 0.02 * uf_tot[grp["id"]].sum()
        uf_grupo = peso[grp["id"]][big].idxmax()
        re_ = fetch(f"{grp['id']}_{uf_grupo}", grp["termos_busca"], geo=f"BR-{uf_grupo}")
        em_alta_uf = {t: [q["query"] for q in qs if limpa(q["query"])][:4] for t, qs in re_["em_alta"].items()}
        em_alta = sorted({q for qs in list(em_alta_uf.values()) + list(em_alta_t.values()) for q in qs if len(q.split()) <= 3}, key=str.lower)
        out["grupos"][grp["id"]] = {
            "volume": r["volume"],
            "uf": {u: {"peso": round(float(x.peso), 2), "interesse": round(float(x.interesse), 1), "prioridade": bool(x.prioridade)}
                   for u, x in cruz.sort_values("score", ascending=False).iterrows()},
            "uf_grupo": uf_grupo,
            "peso_uf_grupo": round(float(peso[grp["id"]][uf_grupo]), 2),
            "termos": {t: {"volume": r["volume"][t], "indice": indice[t], "top_uf": top_uf[t], "em_alta": em_alta_t[t][:4],
                           "em_alta_uf": em_alta_uf[t]} for t in r["termos"]},
            "hashtags": ["#" + "".join(w.capitalize() for w in q.split()) for q in em_alta][:12],
        }
    (ROOT / "site" / "trends_grupos.json").write_text(json.dumps(out, ensure_ascii=False))
    for k, v in out["grupos"].items():
        print(k, v["uf_grupo"], {t: (x["indice"], x["em_alta_uf"][:2]) for t, x in v["termos"].items()})


if __name__ == "__main__":
    main()
