"""Section-level 2026 data -> polling places and neighborhoods (data/locais.csv, data/bairros.csv).

Joins, per electoral section (município, zona, seção), 1st-round President:
- turnout: detalhe_votacao_secao_2026 (aptos, abstenções)
- votes: votacao_secao_2026_BR (President is a federal election: national file, not the per-UF ones)
- place: eleitorado_local_votacao_2026 (local name, address, neighborhood, coordinates)
and aggregates to polling place and to neighborhood within each zone.

Usage: python pipeline/07_secoes.py [--download-only]
"""
import sys
import zipfile
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
X = RAW / "x"
TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
FILES = {
    "detalhe_votacao_secao_2026.zip": f"{TSE}/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip",
    "eleitorado_local_votacao_2026.zip": f"{TSE}/eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip",
    "votacao_secao_2026_BR.zip": f"{TSE}/votacao_secao/votacao_secao_2026_BR.zip",
}


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = RAW / name
        if dest.exists():
            continue
        tmp = dest.with_suffix(".part")
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        tmp.rename(dest)
        print(f"fetched {name}", flush=True)


def csvs(zname, keep=lambda n: n.endswith(".csv")):
    with zipfile.ZipFile(RAW / zname) as z:
        names = [n for n in z.namelist() if keep(n)]
        for n in names:
            if not (X / n).exists():
                z.extract(n, X)
    return [str(X / n) for n in names]


if __name__ == "__main__":
    download()
    if "--download-only" in sys.argv:
        sys.exit()

    loc_csv, = csvs("eleitorado_local_votacao_2026.zip", lambda n: n.endswith("_BRASIL.csv"))
    det_csv, = csvs("detalhe_votacao_secao_2026.zip", lambda n: n.endswith("_BR.csv"))
    vot_csv, = csvs("votacao_secao_2026_BR.zip", lambda n: n.endswith(".csv"))
    rd = lambda f: f"read_csv('{f}', delim=';', encoding='latin-1', all_varchar=true)"
    con = duckdb.connect()
    # turnout per section (President, 1st round); the polling place comes from this file
    con.sql(f"""create table comp as
        select cast(CD_MUNICIPIO as int) cd_tse, cast(NR_ZONA as int) zona, cast(NR_SECAO as int) secao,
               any_value(cast(NR_LOCAL_VOTACAO as int)) id_local,
               sum(cast(QT_APTOS as int)) aptos, sum(cast(QT_ABSTENCOES as int)) abst
        from {rd(det_csv)} where DS_CARGO ilike 'presidente' and NR_TURNO = '1' and SG_UF <> 'ZZ' group by all""")
    # valid votes per section: 22 = Flávio, 13 = Lula, 95/96 = blank/null. Joined by section, the stable key
    # (a few sections carry a different place number in the two files)
    con.sql(f"""create table vot as
        select cast(CD_MUNICIPIO as int) cd_tse, cast(NR_ZONA as int) zona, cast(NR_SECAO as int) secao,
               sum(case when NR_VOTAVEL = '22' then cast(QT_VOTOS as int) else 0 end) v_flavio,
               sum(case when NR_VOTAVEL = '13' then cast(QT_VOTOS as int) else 0 end) v_lula,
               sum(case when NR_VOTAVEL not in ('95', '96') then cast(QT_VOTOS as int) else 0 end) validos
        from {rd(vot_csv)} where DS_CARGO ilike 'presidente' and NR_TURNO = '1' and SG_UF <> 'ZZ' group by all""")
    # polling place attributes (one row per place)
    con.sql(f"""create table loc as
        select cast(CD_MUNICIPIO as int) cd_tse, cast(NR_ZONA as int) zona, cast(NR_LOCAL_VOTACAO as int) id_local,
               any_value(SG_UF) uf, any_value(NM_LOCAL_VOTACAO) nome, any_value(NM_BAIRRO) bairro,
               any_value(DS_ENDERECO) endereco,
               try_cast(replace(any_value(NR_LATITUDE), ',', '.') as double) lat,
               try_cast(replace(any_value(NR_LONGITUDE), ',', '.') as double) lon
        from {rd(loc_csv)} where SG_UF <> 'ZZ' and NR_TURNO = '1' group by all""")
    out = con.sql("""select cd_tse, zona, id_local, any_value(l.uf) uf, any_value(l.nome) nome, any_value(l.bairro) bairro,
               any_value(l.endereco) endereco, any_value(l.lat) lat, any_value(l.lon) lon,
               sum(c.aptos) aptos, sum(c.abst) abst, sum(coalesce(v.v_flavio, 0)) v_flavio,
               sum(coalesce(v.v_lula, 0)) v_lula, sum(coalesce(v.validos, 0)) validos
        from comp c left join vot v using (cd_tse, zona, secao) left join loc l using (cd_tse, zona, id_local)
        group by cd_tse, zona, id_local""").df()
    out.to_csv(ROOT / "data" / "locais.csv", index=False)
    print(f"locais: {len(out):,} places · aptos {out.aptos.sum():,} · abst {out.abst.sum():,} "
          f"· Flávio {out.v_flavio.sum():,} · Lula {out.v_lula.sum():,} · sem coordenada {out.lat.isna().sum():,}")
