"""Aggregate data/municipios.csv + data/perfil.csv into site/data.json (everything the page draws)."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REGIOES = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}
PORTES = ["até 10 mil", "10–50 mil", "50–200 mil", "200 mil–1 mi", "mais de 1 mi"]


def taxa(g):
    return pd.Series({
        "aptos_2026": int(g.aptos_2026.sum()), "abst_2026": int(g.abst_2026.sum()),
        "tx_2026": round(100 * g.abst_2026.sum() / g.aptos_2026.sum(), 2),
        "tx_2022": round(100 * g.abst_2022.sum() / g.aptos_2022.sum(), 2),
        "municipios": len(g),
    })


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
        "perfil": {d: g[["categoria", "aptos", "abst", "tx_abst", "share_abst"]].round(2).to_dict("records")
                   for d, g in perfil.groupby("dimensao", sort=False)},
        # compact per-municipality rows for map + scatter: [ibge, nome, uf, aptos, tx26, tx22, renda, urb, alf]
        "municipios": [
            [int(r.cd_ibge), r.nome.title(), r.uf, int(r.aptos_2026), round(r.tx_abst_2026, 1),
             None if pd.isna(r.tx_abst_2022) else round(r.tx_abst_2022, 1),
             None if pd.isna(r.renda_pc_mediana) else round(r.renda_pc_mediana),
             None if pd.isna(r.pct_urbana) else round(r.pct_urbana, 1),
             None if pd.isna(r.alfabetizacao) else round(r.alfabetizacao, 1)]
            for r in m.itertuples()
        ],
    }
    (ROOT / "site" / "data.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(json.dumps({k: v for k, v in out.items() if k not in ("municipios", "perfil")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
