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


SP_ZONAS = {
    "Norte": ["PERUS", "PIRITUBA-JARAGUA", "FREGUESIA-BRASILANDIA", "CASA VERDE-CACHOEIRINHA", "SANTANA-TUCURUVI",
              "JACANA-TREMEMBE", "VILA MARIA-VILA GUILHERME"],
    "Sul": ["SANTO AMARO", "CIDADE ADEMAR", "CAMPO LIMPO", "M'BOI MIRIM", "CAPELA DO SOCORRO", "PARELHEIROS",
            "VILA MARIANA", "JABAQUARA", "IPIRANGA"],
    "Leste": ["MOOCA", "ARICANDUVA-FORMOSA-CARRAO", "VILA PRUDENTE", "SAPOPEMBA", "PENHA", "ERMELINO MATARAZZO",
              "SAO MIGUEL", "ITAIM PAULISTA", "GUAIANASES", "ITAQUERA", "CIDADE TIRADENTES", "SAO MATEUS"],
    "Oeste": ["LAPA", "BUTANTA", "PINHEIROS"],
    "Centro": ["SE"],
}
RIO_AP = {"1": "Centro", "2": "Zona Sul e Tijuca", "3": "Zona Norte", "4": "Barra e Jacarepaguá", "5": "Zona Oeste"}
SAO_PAULO, RIO, SALVADOR = 3550308, 3304557, 2927408


def norm(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().upper()
    return " ".join(t.replace("-", " ").replace("'", " ").split())


def titulo_sub(t):
    return " ".join(w.capitalize() if w not in ("DE", "DA", "DO") else w.lower() for w in t.replace("-", " - ").split()).replace(" - ", "-")


def por_poligono(loc, mask, geojson, campo):
    """Assign each polling place (lat/lon) to the feature that contains it; returns a Series of feature values."""
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree
    feats = json.loads(Path(geojson).read_text())["features"]
    geoms = [shape(f["geometry"]) for f in feats]
    tree = STRtree(geoms)
    vals = {}
    for idx, la, lo in zip(loc.index[mask], loc.loc[mask, "lat"], loc.loc[mask, "lon"]):
        pt = Point(lo, la)
        hit = [i for i in tree.query(pt) if geoms[i].contains(pt)]
        if not hit:  # on the border or slightly outside (coastline): nearest polygon
            hit = [min(range(len(geoms)), key=lambda i: geoms[i].distance(pt))]
        vals[idx] = campo(feats[hit[0]]["properties"])
    return pd.Series(vals, dtype=object)


def sub_regioes(loc):
    """Official intra-city regions where open data exists; the compass sector stays elsewhere."""
    loc["sub"] = None
    sp = loc.cd_ibge == SAO_PAULO
    zona_de = {sub: z for z, subs in SP_ZONAS.items() for sub in subs}
    subp = por_poligono(loc, sp, RAW / "regioes" / "sp_distritos.geojson", lambda pr: pr["ds_subpref"])
    loc.loc[sp, "setor"] = ["Zona " + zona_de[v] if zona_de[v] != "Centro" else "Centro" for v in subp]
    loc.loc[sp, "sub"] = [titulo_sub(v) for v in subp]
    rio = loc.cd_ibge == RIO
    ap = por_poligono(loc, rio, RAW / "regioes" / "rio_bairros.geojson", lambda pr: (pr["area_plane"], pr["rp"]))
    loc.loc[rio, "setor"] = [RIO_AP[a] for a, _ in ap]
    loc.loc[rio, "sub"] = [r for _, r in ap]
    pb = json.loads((ROOT / "regioes" / "salvador_prefeituras_bairro.json").read_text())["prefeituras_bairro"]
    bairro_pb = {}
    for nome, bairros in pb.items():
        for b in bairros:
            for alias in [b] + b.split("/"):
                bairro_pb[norm(alias)] = nome
    # TSE spellings and sub-areas that are not in the Prefeitura-Bairro lists (ambiguous ones such as "Campinas" stay out)
    alias = {"CAJAZEIRAS": "Cajazeiras", "JARDIM CAJAZEIRA": "Pau da Lima", "MUSSURUNGA I": "Itapuã / Ipitanga",
             "MUSSURUNGA II": "Itapuã / Ipitanga", "PARQUE SAO CRISTOVAO": "Itapuã / Ipitanga", "PRAIA DO FLAMENGO": "Itapuã / Ipitanga",
             "ARMACAO": "Barra / Pituba", "CHAME CHAME": "Barra / Pituba", "CAMPINAS DE BROTAS": "Centro / Brotas",
             "PELOURINHO": "Centro / Brotas", "CAMPO GRANDE": "Centro / Brotas", "PIEDADE": "Centro / Brotas", "SAO PEDRO": "Centro / Brotas",
             "MERCES": "Centro / Brotas", "AFLITOS": "Centro / Brotas", "ALTO DE COUTOS": "Subúrbio / Ilhas",
             "BOM JESUS DOS PASSOS": "Subúrbio / Ilhas", "TUBARAO": "Subúrbio / Ilhas", "SAO GONCALO DO RETIRO": "Cabula / Tancredo Neves",
             "CAPELINHA DE SAO CAETANO": "Liberdade / São Caetano", "SAN MARTIN": "Liberdade / São Caetano",
             "BOA VISTA DO LOBATO": "Cidade Baixa", "VILA RUI BARBOSA": "Cidade Baixa"}
    bairro_pb.update(alias)
    for k in [b for b in loc.loc[loc.cd_ibge == SALVADOR, "bairro"].fillna("").map(norm).unique() if b.startswith("CASTELO BRANCO")]:
        bairro_pb[k] = "Cajazeiras"
    ssa = loc.cd_ibge == SALVADOR
    loc.loc[ssa, "setor"] = [bairro_pb.get(norm(b), "Outros bairros") for b in loc.loc[ssa, "bairro"].fillna("")]
    for cid, nome in ((SAO_PAULO, "São Paulo"), (RIO, "Rio de Janeiro"), (SALVADOR, "Salvador")):
        m = loc.cd_ibge == cid
        print(f"  {nome}: {loc.loc[m, 'setor'].value_counts().to_dict()}")
    return loc


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
            "margem": int(abs(g.v_lula.sum() - g.v_flavio.sum())),
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

    loc = sub_regioes(loc)

    regioes = {}
    for (rid, nome, uf), g in loc.groupby(["rgi", "rgi_nome", "rgi_uf"]):
        regioes[str(int(rid))] = {"nome": APELIDOS.get(nome, nome), "nome_ibge": nome, "uf": uf,
                                  "municipios": int(g.cd_ibge.nunique()), **agrega(g)}
    setores = {str(cid): {s: agrega(g) for s, g in loc[loc.cd_ibge == cid].groupby("setor")} for cid in grandes}
    # region filter: curated groups of municipalities, official intra-city regions, compass sectors, IBGE regions
    import csv
    import unicodedata
    slug = lambda t: "-".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().replace("/", " ").split())
    nome_ibge = {(m["municipio-nome"], m["UF-sigla"]): m["municipio-id"] for m in ibge}
    nome_mun = {m["municipio-id"]: m["municipio-nome"] for m in ibge}
    filtro = []
    with open(ROOT / "regioes" / "regioes.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["nome"] or r["nome"].startswith("#"):
                continue
            cods = [nome_ibge[(n.strip(), r["uf"])] for n in r["municipios"].split(";") if (n.strip(), r["uf"]) in nome_ibge]
            g = loc[loc.cd_ibge.isin(cods)]
            filtro.append({"id": slug(r["nome"]), "nome": r["nome"], "uf": r["uf"], "tipo": "municipios", "municipios": cods, **agrega(g)})
    for cid in sorted(grandes):
        g0 = loc[loc.cd_ibge == cid]
        cidade, uf = nome_mun[cid], g0.uf.iloc[0]
        tipo = "oficial" if cid in (SAO_PAULO, RIO, SALVADOR) else "aproximado"
        for setor_nome, g in g0.groupby("setor"):
            filtro.append({"id": f"{slug(cidade)}-{slug(setor_nome)}", "nome": setor_nome, "cidade": cidade, "uf": uf, "ibge": int(cid),
                           "tipo": tipo, "campo": "setor", "valor": setor_nome, **agrega(g)})
        for sub_nome, g in g0[g0["sub"].notna()].groupby("sub"):
            filtro.append({"id": f"{slug(cidade)}-{slug(sub_nome)}", "nome": sub_nome, "cidade": cidade, "uf": uf, "ibge": int(cid),
                           "tipo": "oficial", "campo": "sub", "valor": sub_nome, **agrega(g)})
    for rid, x in regioes.items():
        filtro.append({"id": f"rgi-{rid}", "nome": f"Região de {x['nome']}" if x["nome"] == x["nome_ibge"] else x["nome"], "uf": x["uf"], "tipo": "ibge",
                       "municipios": [int(k) for k, v in rgi.set_index("cd_ibge").rgi.items() if str(v) == rid],
                       **{k: x[k] for k in ("aptos", "abst", "mob", "pl", "pf", "saldo")}})

    out = {"regioes": regioes, "filtro": filtro, "mun_rgi": {str(k): str(v) for k, v in rgi.set_index("cd_ibge").rgi.items()},
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
                 int(round(r.saldo)), r.sub if isinstance(r.sub, str) else None] for r in g.sort_values("saldo", ascending=False).itertuples()]
        (pasta / f"{uf}.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))

    print(f"{len(regioes)} immediate regions · {len(grandes)} large cities with sectors · {len(loc):,} places")
    top = sorted(regioes.values(), key=lambda r: -r["saldo"])[:5]
    print("top saldo regions:", [(r["nome"], r["uf"], r["saldo"]) for r in top])
    bs = next(r for r in regioes.values() if r["nome"] == "Baixada Santista")
    print("Baixada Santista:", bs)
    print("São Paulo sectors:", setores.get("3550308"))


if __name__ == "__main__":
    main()
