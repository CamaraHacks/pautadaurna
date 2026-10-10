"""Regions, city sectors and polling places for the "Onde agir" view.

Inputs: data/locais.csv (07_secoes.py), data/municipios.csv and data/segmentos.csv (02_build.py),
IBGE immediate regions (API) and municipal seat coordinates (kelvins/municipios-brasileiros).

Outputs:
- site/regioes.json   immediate regions (Regiões Geográficas Imediatas, IBGE 2017) and sectors of large cities
- site/locais/<UF>.json  every polling place, compact, loaded on demand by the page

Metrics per unit:
- mobilizáveis: abstainers minus the 70+ share of the municipality (voluntary voting, often health-related)
- saldo: mobilizáveis x (Lula% - Flávio%) of valid votes where they vote. Ecological assumption: abstainers would
  vote like the voters of their own polling place. Positive = net gain for Lula if they turn out.
"""
import json
import math
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CIDADE_GRANDE = 500_000  # registered voters; these cities get Centro/Norte/Sul/Leste/Oeste sectors
# colloquial names where the IBGE immediate region matches a well-known region
APELIDOS = {"Santos": "Baixada Santista"}


def fetch(name, url):
    f = RAW / name
    if not f.exists():
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        f.write_bytes(r.content)
    return f


def setor(lat, lon, lat0, lon0, raio_centro):
    dx = (lon - lon0) * 111.32 * math.cos(math.radians(lat0))
    dy = (lat - lat0) * 110.57
    if math.hypot(dx, dy) < raio_centro:
        return "Centro"
    ang = (math.degrees(math.atan2(dx, dy)) + 360) % 360  # 0 = north, clockwise
    return ["Norte", "Leste", "Sul", "Oeste"][int(((ang + 45) % 360) // 90)]


def agrega(g):
    pl = 100 * g.v_lula.sum() / max(1, g.validos.sum())
    pf = 100 * g.v_flavio.sum() / max(1, g.validos.sum())
    mob = g.mob.sum()
    return {"aptos": int(g.aptos.sum()), "abst": int(g.abst.sum()), "mob": int(round(mob)),
            "pl": round(pl, 1), "pf": round(pf, 1), "saldo": int(round(g.saldo.sum()))}


def main():
    ibge = json.loads(fetch("ibge_municipios.json",
                            "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado").read_text())
    rgi = pd.DataFrame([{"cd_ibge": m["municipio-id"], "rgi": m["regiao-imediata-id"],
                         "rgi_nome": m["regiao-imediata-nome"], "rgi_uf": m["UF-sigla"]} for m in ibge])
    sedes = pd.read_csv(fetch("sedes.csv", "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"))
    sedes = sedes.rename(columns={"codigo_ibge": "cd_ibge", "latitude": "lat0", "longitude": "lon0"})[["cd_ibge", "lat0", "lon0"]]

    mun = pd.read_csv(ROOT / "data" / "municipios.csv")[["cd_tse", "cd_ibge"]]
    seg = pd.read_csv(ROOT / "data" / "segmentos.csv")
    share70 = (seg[seg.segmento == "idosos"].set_index("cd_tse").abst / seg.groupby("cd_tse").abst.sum()).rename("s70")

    loc = pd.read_csv(ROOT / "data" / "locais.csv").merge(mun, on="cd_tse").merge(rgi, on="cd_ibge", how="left")
    loc = loc.merge(sedes, on="cd_ibge", how="left").join(share70, on="cd_tse")
    loc["s70"] = loc.s70.fillna(share70.median())
    loc["mob"] = loc.abst * (1 - loc.s70)
    val = loc.validos.clip(lower=1)
    loc["pl"], loc["pf"] = 100 * loc.v_lula / val, 100 * loc.v_flavio / val
    loc["saldo"] = loc.mob * (loc.pl - loc.pf) / 100

    # sectors for large cities, relative to the municipal seat
    aptos_mun = loc.groupby("cd_ibge").aptos.sum()
    grandes = set(aptos_mun[aptos_mun >= CIDADE_GRANDE].index)
    loc["setor"] = None
    for cid in grandes:
        m = loc.cd_ibge == cid
        lat0, lon0 = loc.loc[m, "lat0"].iloc[0], loc.loc[m, "lon0"].iloc[0]
        d = [math.hypot((lo - lon0) * 111.32 * math.cos(math.radians(lat0)), (la - lat0) * 110.57)
             for la, lo in zip(loc.loc[m, "lat"], loc.loc[m, "lon"])]
        raio = max(3.0, 0.18 * pd.Series(d).quantile(0.9))
        loc.loc[m, "setor"] = [setor(la, lo, lat0, lon0, raio) for la, lo in zip(loc.loc[m, "lat"], loc.loc[m, "lon"])]

    regioes = {}
    for (rid, nome, uf), g in loc.groupby(["rgi", "rgi_nome", "rgi_uf"]):
        regioes[str(int(rid))] = {"nome": APELIDOS.get(nome, nome), "nome_ibge": nome, "uf": uf,
                                  "municipios": int(g.cd_ibge.nunique()), **agrega(g)}
    setores = {str(cid): {s: agrega(g) for s, g in loc[loc.cd_ibge == cid].groupby("setor")} for cid in grandes}
    out = {"regioes": regioes, "mun_rgi": {str(k): str(v) for k, v in rgi.set_index("cd_ibge").rgi.items()},
           "setores": setores, "cidade_grande": CIDADE_GRANDE,
           # per municipality: [mobilizáveis, saldo, Lula%, Flávio%]
           "mun": {str(int(k)): [int(round(g.mob.sum())), int(round(g.saldo.sum())),
                                 round(100 * g.v_lula.sum() / max(1, g.validos.sum()), 1),
                                 round(100 * g.v_flavio.sum() / max(1, g.validos.sum()), 1)]
                   for k, g in loc.groupby("cd_ibge")}}
    (ROOT / "site" / "regioes.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))

    # polling places per UF: [ibge, zona, setor, nome, bairro, aptos, abst, pl, pf, saldo]
    pasta = ROOT / "site" / "locais"
    pasta.mkdir(exist_ok=True)
    siglas = {"EE", "EEF", "EEM", "EMEF", "EMEI", "EMEB", "CEU", "USP", "UFRJ", "UFMG", "UFBA", "UNESP", "UNICAMP", "ETEC",
              "FATEC", "SESI", "SENAI", "SESC", "SENAC", "CIEP", "CIEE", "CEI", "CEMEI", "CMEI", "EM", "EEEFM", "EEEF", "IF",
              "IFSP", "IFBA", "UNIP", "FAM", "PUC", "UFPE", "UFC", "UNB", "CAIC", "CEMEB", "CED", "CEF", "CEM", "EEFM", "II", "III", "IV"}
    menores = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "na", "no"}

    def tit(s):
        out = []
        for i, w in enumerate(str(s).split()):
            core = w.strip(".,-()")
            if core.upper() in {"DR", "DRA", "SR", "SRA"}:
                out.append(w[:1].upper() + w[1:].lower())
            elif core.upper() in siglas or (core.isalpha() and len(core) <= 3 and not any(v in core.upper() for v in "AEIOU")):
                out.append(w.upper())
            elif i and w.lower() in menores:
                out.append(w.lower())
            else:
                out.append(w[:1].upper() + w[1:].lower())
        return " ".join(out)
    for uf, g in loc.groupby("uf"):
        rows = [[int(r.cd_ibge), int(r.zona), r.setor, tit(r.nome),
                 tit(r.bairro) if isinstance(r.bairro, str) else "", int(r.aptos), int(r.abst), round(r.pl, 1), round(r.pf, 1),
                 int(round(r.saldo))] for r in g.sort_values("saldo", ascending=False).itertuples()]
        (pasta / f"{uf}.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))

    print(f"{len(regioes)} immediate regions · {len(grandes)} large cities with sectors · {len(loc):,} places")
    top = sorted(regioes.values(), key=lambda r: -r["saldo"])[:5]
    print("top saldo regions:", [(r["nome"], r["uf"], r["saldo"]) for r in top])
    bs = next(r for r in regioes.values() if r["nome"] == "Baixada Santista")
    print("Baixada Santista:", bs)
    print("São Paulo sectors:", setores.get("3550308"))


if __name__ == "__main__":
    main()
