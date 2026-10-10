"""Build data/municipios.csv (one row per municipality) and data/perfil.csv (national abstention profile).

Abstention comes from TSE detalhe_votacao_munzona (Presidente, 1º turno), joined to Censo 2022 by IBGE code.
"""
import json
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
X = RAW / "x"  # extracted CSVs


def extract(zname, member_filter):
    with zipfile.ZipFile(RAW / zname) as z:
        names = [n for n in z.namelist() if member_filter(n)]
        for n in names:
            if not (X / n).exists():
                z.extract(n, X)
    return [X / n for n in names]


def votacao(year):
    (csv,) = extract(f"detalhe_votacao_munzona_{year}.zip", lambda n: n.endswith("_BRASIL.csv"))
    return duckdb.sql(f"""
        select cast(CD_MUNICIPIO as int) cd_tse, SG_UF uf,
               sum(QT_APTOS) aptos_{year}, sum(QT_ABSTENCOES) abst_{year}
        from read_csv('{csv}', delim=';', encoding='latin-1', all_varchar=true,
                      types={{'QT_APTOS':'BIGINT','QT_ABSTENCOES':'BIGINT'}})
        where DS_CARGO = 'Presidente' and NR_TURNO = '1' and SG_UF <> 'ZZ'
        group by all
    """).df()


def sidra(name, value_col, pick=None):
    """Flatten a SIDRA v3 response to {ibge_code: value}; `pick` selects one category tuple."""
    out = {}
    for var in json.load(open(RAW / name)):
        for res in var["resultados"]:
            cats = tuple(list(c["categoria"].values())[0] for c in res["classificacoes"])
            if pick and not pick(var["id"], cats):
                continue
            for s in res["series"]:
                v = s["serie"]["2022"]
                out[int(s["localidade"]["id"])] = float(v) if v not in ("-", "...", "X") else None
    return pd.Series(out, name=value_col)


def censo():
    renda_media = sidra("censo_renda.json", "renda_pc_media", lambda v, c: v == "13431")
    renda_mediana = sidra("censo_renda.json", "renda_pc_mediana", lambda v, c: v == "13534")
    pop = sidra("censo_situacao.json", "pop", lambda v, c: v == "93" and c[1] == "Total")
    urb = sidra("censo_situacao.json", "pop_urbana", lambda v, c: v == "93" and c[1] == "Urbana")
    alf = sidra("censo_alfabetizacao.json", "alfabetizacao")
    p14 = sidra("censo_ocupacao.json", "p14", lambda v, c: v == "140" and c[0] == "Total")
    ocup = sidra("censo_ocupacao.json", "ocupadas", lambda v, c: v == "140" and c[0] == "Ocupadas")
    df = pd.concat([pop, urb, renda_media, renda_mediana, alf, p14, ocup], axis=1)
    df["pct_urbana"] = 100 * df.pop_urbana / df["pop"]
    df["pct_ocupadas"] = 100 * df.ocupadas / df.p14
    return df.drop(columns=["pop_urbana", "p14", "ocupadas"]).rename_axis("cd_ibge").reset_index()


def build_municipios():
    v26, v22 = votacao(2026), votacao(2022)
    m = v26.merge(v22.drop(columns="uf"), on="cd_tse", how="left")
    codes = pd.read_csv(RAW / "tse_ibge.csv").rename(
        columns={"codigo_tse": "cd_tse", "codigo_ibge": "cd_ibge", "nome_municipio": "nome", "capital": "capital"}
    )[["cd_tse", "cd_ibge", "nome", "capital"]]
    # Installed in 2025, after the Censo and the code table: no census data, kept for vote totals
    codes.loc[len(codes)] = [73709, 5101837, "BOA ESPERANÇA DO NORTE", 0]
    m = m.merge(codes, on="cd_tse", how="left")
    unmatched = m[m.cd_ibge.isna()]
    assert unmatched.empty, f"TSE codes without IBGE match:\n{unmatched}"
    m["cd_ibge"] = m.cd_ibge.astype(int)
    m = m.merge(censo(), on="cd_ibge", how="left")
    m["tx_abst_2026"] = 100 * m.abst_2026 / m.aptos_2026
    m["tx_abst_2022"] = 100 * m.abst_2022 / m.aptos_2022
    return m


def build_perfil():
    """National abstention profile from TSE perfil_comparecimento_abstencao (2026 if published, else 2022)."""
    year = 2026 if (RAW / "perfil_comparecimento_abstencao_2026.zip").exists() else 2022
    csvs = extract(f"perfil_comparecimento_abstencao_{year}.zip", lambda n: n.endswith(".csv"))
    files = [str(c) for c in csvs if not c.name.endswith(("_BR.csv", "_BRASIL.csv"))]
    rel = duckdb.sql(f"select * from read_csv({files}, delim=';', encoding='latin-1', all_varchar=true)")
    dims = {"genero": "DS_GENERO", "faixa_etaria": "DS_FAIXA_ETARIA", "escolaridade": "DS_GRAU_ESCOLARIDADE",
            "estado_civil": "DS_ESTADO_CIVIL"}
    parts = []
    for dim, col in dims.items():
        d = duckdb.sql(f"""
            select '{dim}' dimensao, {col} categoria, min(CD_{col[3:]}) ordem,
                   sum(cast(QT_APTOS as bigint)) aptos, sum(cast(QT_ABSTENCAO as bigint)) abst
            from rel where NR_TURNO = '1' and SG_UF <> 'ZZ' group by all
        """).df()
        parts.append(d)
    p = pd.concat(parts)
    p["ano"] = year
    p["tx_abst"] = 100 * p.abst / p.aptos
    p["share_abst"] = 100 * p.abst / p.groupby("dimensao").abst.transform("sum")
    return p.sort_values(["dimensao", "ordem"])


def build_zonas():
    """Turnout and top-2 vote share per electoral zone, for municipalities with more than one zone."""
    z = {}
    for year in (2026, 2022):
        (csv,) = extract(f"detalhe_votacao_munzona_{year}.zip", lambda n: n.endswith("_BRASIL.csv"))
        z[year] = duckdb.sql(f"""
            select cast(CD_MUNICIPIO as int) cd_tse, cast(NR_ZONA as int) zona,
                   sum(cast(QT_APTOS as bigint)) aptos_{year}, sum(cast(QT_ABSTENCOES as bigint)) abst_{year}
            from read_csv('{csv}', delim=';', encoding='latin-1', all_varchar=true)
            where DS_CARGO = 'Presidente' and NR_TURNO = '1' and SG_UF <> 'ZZ' group by all
        """).df()
    (csv,) = extract("votacao_candidato_munzona_2026.zip", lambda n: n.endswith("_BRASIL.csv"))
    v = duckdb.sql(f"""
        select cast(CD_MUNICIPIO as int) cd_tse, cast(NR_ZONA as int) zona, NM_URNA_CANDIDATO candidato,
               sum(cast(QT_VOTOS_NOMINAIS_VALIDOS as bigint)) votos
        from read_csv('{csv}', delim=';', encoding='latin-1', all_varchar=true)
        where DS_CARGO = 'Presidente' and NR_TURNO = '1' and SG_UF <> 'ZZ' group by all
    """).df()
    vt = v.pivot_table(index=["cd_tse", "zona"], columns="candidato", values="votos", aggfunc="sum", fill_value=0)
    top2 = v.groupby("candidato").votos.sum().nlargest(2).index
    sh = vt[top2].div(vt.sum(axis=1), axis=0).mul(100).round(1)
    sh.columns = ["pct_1", "pct_2"]
    out = z[2026].merge(z[2022], on=["cd_tse", "zona"], how="left").merge(sh.reset_index(), on=["cd_tse", "zona"], how="left")
    n = out.groupby("cd_tse").zona.transform("size")
    return out[n > 1]


SEGMENTO = """
    case
        when cast(CD_FAIXA_ETARIA as int) >= 7074 then 'idosos'
        when cast(CD_FAIXA_ETARIA as int) between 1800 and 2529 then 'jovens'
        when cast(CD_FAIXA_ETARIA as int) between 3034 and 6569 then case
            when CD_GRAU_ESCOLARIDADE in ('1', '2', '3', '4') then 'base'
            when CD_GRAU_ESCOLARIDADE in ('5', '6', '7') then 'media'
            when CD_GRAU_ESCOLARIDADE = '8' then 'superior'
            else 'outros' end
        else 'outros'
    end"""


def build_segmentos():
    """Abstainer groups (age x schooling as class proxy) per municipality, from the TSE profile."""
    year = 2026 if (RAW / "perfil_comparecimento_abstencao_2026.zip").exists() else 2022
    csvs = extract(f"perfil_comparecimento_abstencao_{year}.zip", lambda n: n.endswith(".csv"))
    files = [str(c) for c in csvs if not c.name.endswith(("_BR.csv", "_BRASIL.csv"))]
    return duckdb.sql(f"""
        select cast(CD_MUNICIPIO as int) cd_tse, {SEGMENTO} segmento,
               sum(cast(QT_APTOS as bigint)) aptos, sum(cast(QT_ABSTENCAO as bigint)) abst
        from read_csv({files}, delim=';', encoding='latin-1', all_varchar=true)
        where NR_TURNO = '1' and SG_UF <> 'ZZ' group by all order by all
    """).df()


def build_votos():
    """Presidente, 1º turno 2026: valid-vote share per candidate and municipality (top candidates nationally)."""
    (csv,) = extract("votacao_candidato_munzona_2026.zip", lambda n: n.endswith("_BRASIL.csv"))
    return duckdb.sql(f"""
        select cast(CD_MUNICIPIO as int) cd_tse, NM_URNA_CANDIDATO candidato, SG_PARTIDO partido,
               sum(cast(QT_VOTOS_NOMINAIS_VALIDOS as bigint)) votos
        from read_csv('{csv}', delim=';', encoding='latin-1', all_varchar=true)
        where DS_CARGO = 'Presidente' and NR_TURNO = '1' and SG_UF <> 'ZZ'
        group by all
    """).df()


if __name__ == "__main__":
    m = build_municipios()
    m.to_csv(ROOT / "data" / "municipios.csv", index=False)
    print(f"municipios: {len(m)} rows; abst 2026 = {m.abst_2026.sum():,} / {m.aptos_2026.sum():,}"
          f" = {100 * m.abst_2026.sum() / m.aptos_2026.sum():.2f}%; missing censo: {m.renda_pc_media.isna().sum()}")
    p = build_perfil()
    p.to_csv(ROOT / "data" / "perfil.csv", index=False)
    print(p.to_string())
    seg = build_segmentos()
    seg.to_csv(ROOT / "data" / "segmentos.csv", index=False)
    print(seg.groupby("segmento")[["aptos", "abst"]].sum().assign(tx=lambda d: 100 * d.abst / d.aptos,
                                                                   share=lambda d: 100 * d.abst / d.abst.sum()))
    z = build_zonas()
    z.to_csv(ROOT / "data" / "zonas.csv", index=False)
    print(f"zonas: {len(z)} rows in {z.cd_tse.nunique()} municipalities")
    v = build_votos()
    v.to_csv(ROOT / "data" / "votos.csv", index=False)
    print(v.groupby(["candidato", "partido"]).votos.sum().sort_values(ascending=False)
          .pipe(lambda s: (100 * s / s.sum()).round(2)).head(5))
