"""Aggregate data/municipios.csv + data/perfil.csv into site/data.json (everything the page draws)."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REGIOES = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}
GRUPOS = ["idosos", "jovens", "base", "media", "superior"]
PORTES = ["até 10 mil", "10–50 mil", "50–200 mil", "200 mil–1 mi", "mais de 1 mi"]


def taxa(g):
    return pd.Series({
        "aptos_2026": int(g.aptos_2026.sum()), "abst_2026": int(g.abst_2026.sum()),
        "tx_2026": round(100 * g.abst_2026.sum() / g.aptos_2026.sum(), 2),
        "tx_2022": round(100 * g.abst_2022.sum() / g.aptos_2022.sum(), 2),
        "municipios": len(g),
    })


def nome(s):
    """'FEIRA DE SANTANA' -> 'Feira de Santana' (Portuguese connectors stay lowercase)."""
    small = {"de", "da", "do", "das", "dos", "e", "d'"}
    words = s.lower().split()
    cap = lambda w: "'".join(p[:1].upper() + p[1:] for p in w.split("'"))  # d'oeste -> D'Oeste
    return " ".join(w if (i and w in small) else cap(w) for i, w in enumerate(words))


def spearman(a, b):
    return round(a.rank().corr(b.rank()), 3)


def main():
    m = pd.read_csv(ROOT / "data" / "municipios.csv")
    m["regiao"] = m.cd_ibge.astype(str).str[0].map(REGIOES)
    m["delta"] = m.tx_abst_2026 - m.tx_abst_2022
    c = m.dropna(subset=["renda_pc_mediana"]).copy()  # municipalities with Censo 2022 data
    c["quintil"] = pd.qcut(c.renda_pc_mediana.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    c["porte"] = pd.cut(c["pop"], [0, 1e4, 5e4, 2e5, 1e6, 1e9], labels=PORTES)

    quintis = c.groupby("quintil").apply(taxa, include_groups=False)
    quintis["renda_mediana"] = c.groupby("quintil").renda_pc_mediana.agg(["min", "max"]).apply(
        lambda r: f"R$ {r['min']:,.0f}–{r['max']:,.0f}".replace(",", "."), axis=1)

    # abstainer groups per municipality: {cd_tse: [aptos, abst] x GRUPOS}
    seg = pd.read_csv(ROOT / "data" / "segmentos.csv")
    seg_mun = {k: [int(v) for gr in GRUPOS for v in g.set_index("segmento").reindex([gr]).fillna(0)[["aptos", "abst"]].iloc[0]]
               for k, g in seg.groupby("cd_tse")}
    seg_br = seg.groupby("segmento")[["aptos", "abst"]].sum()
    seg_br["tx"] = 100 * seg_br.abst / seg_br.aptos
    seg_br["share"] = 100 * seg_br.abst / seg_br.abst.sum()

    # 1st-round valid-vote share of the two national leaders, per municipality
    votos = pd.read_csv(ROOT / "data" / "votos.csv")
    top2 = votos.groupby("candidato").votos.sum().nlargest(2).index.tolist()
    vt = votos.pivot_table(index="cd_tse", columns="candidato", values="votos", aggfunc="sum", fill_value=0)
    share = (100 * vt[top2].div(vt.sum(axis=1), axis=0)).round(1)
    # ecological lean: abstainer-weighted average share where each group's abstainers live
    lean = {}
    for gr in GRUPOS:
        w = seg[seg.segmento == gr].set_index("cd_tse").abst.reindex(share.index).fillna(0)
        lean[gr] = {c: round(float((share[c] * w).sum() / w.sum()), 1) for c in top2}

    # margin between the two national leaders (absolute votes), per municipality and per UF
    vabs = vt[top2]
    margem_mun = (vabs.iloc[:, 0] - vabs.iloc[:, 1]).abs()
    by_uf = m.set_index("cd_tse").uf
    vuf = vabs.join(by_uf).groupby("uf")[top2].sum()
    ufs = m.groupby("uf")[["aptos_2026", "abst_2026"]].sum().join((vuf.iloc[:, 0] - vuf.iloc[:, 1]).abs().rename("margem"))
    margem_br = int(abs(vabs.iloc[:, 0].sum() - vabs.iloc[:, 1].sum()))

    # electoral zones (municipalities with more than one zone), keyed by IBGE code
    zonas = pd.read_csv(ROOT / "data" / "zonas.csv").merge(m[["cd_tse", "cd_ibge"]], on="cd_tse")
    zonas_out = {str(k): [[int(r.zona), int(r.aptos_2026), int(r.abst_2026), r.pct_1, r.pct_2] for r in g.itertuples()]
                 for k, g in zonas.groupby("cd_ibge")}

    perfil = pd.read_csv(ROOT / "data" / "perfil.csv")
    perfil = perfil[~perfil.categoria.isin(["NÃO INFORMADO", "Inválido"])]

    out = {
        "total": {
            "aptos": int(m.aptos_2026.sum()), "abst": int(m.abst_2026.sum()),
            "tx_2026": round(100 * m.abst_2026.sum() / m.aptos_2026.sum(), 2),
            "tx_2022": round(100 * m.abst_2022.sum() / m.aptos_2022.sum(), 2),
        },
        # registered voters (2026) above resident population (Censo 2022): sign of outdated rolls
        "mais_aptos_que_habitantes": int((c.aptos_2026 > c["pop"]).sum()),
        "correlacoes": {k: {"nivel": spearman(c[k], c.tx_abst_2026), "variacao": spearman(c[k], c.delta)}
                        for k in ["renda_pc_mediana", "alfabetizacao", "pct_urbana", "pct_ocupadas"]},
        "quintis": quintis.reset_index().to_dict("records"),
        "regioes": c.groupby("regiao").apply(taxa, include_groups=False).reset_index().to_dict("records"),
        "portes": c.groupby("porte", observed=True).apply(taxa, include_groups=False).reset_index()
                   .astype({"porte": str}).to_dict("records"),
        "perfil_ano": int(perfil.ano.iloc[0]),
        "grupos_ordem": GRUPOS,
        "segmentos_br": {gr: {"aptos": int(seg_br.aptos[gr]), "abst": int(seg_br.abst[gr]), "tx": round(seg_br.tx[gr], 2),
                              "share": round(seg_br.share[gr], 2)} for gr in seg_br.index},
        "candidatos": [c.title() for c in top2],
        "voto_br": [round(100 * votos[votos.candidato == c].votos.sum() / votos.votos.sum(), 2) for c in top2],
        "lean": lean,
        "margem_br": margem_br,
        "ufs": {u: {"aptos": int(r.aptos_2026), "abst": int(r.abst_2026), "margem": int(r.margem)} for u, r in ufs.iterrows()},
        "zonas": zonas_out,
        "perfil": {d: g[["categoria", "aptos", "abst", "tx_abst", "share_abst"]].round(2).to_dict("records")
                   for d, g in perfil.groupby("dimensao", sort=False)},
        # compact rows: [ibge, nome, uf, aptos, tx26, tx22, renda, urb, alf, abst26, abst22, [aptos,abst] x grupos, [top2 %]]
        "municipios": [
            [int(r.cd_ibge), nome(r.nome), r.uf, int(r.aptos_2026), round(r.tx_abst_2026, 1),
             None if pd.isna(r.tx_abst_2022) else round(r.tx_abst_2022, 1),
             None if pd.isna(r.renda_pc_mediana) else round(r.renda_pc_mediana),
             None if pd.isna(r.pct_urbana) else round(r.pct_urbana, 1),
             None if pd.isna(r.alfabetizacao) else round(r.alfabetizacao, 1),
             int(r.abst_2026), None if pd.isna(r.abst_2022) else int(r.abst_2022),
             seg_mun.get(r.cd_tse), share.loc[r.cd_tse].tolist() if r.cd_tse in share.index else None,
             int(margem_mun.get(r.cd_tse, 0))]
            for r in m.itertuples()
        ],
    }
    (ROOT / "site" / "data.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(json.dumps({k: v for k, v in out.items() if k not in ("municipios", "perfil", "segmentos_br", "zonas", "ufs")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
