"""Download raw TSE and IBGE files into data/raw (cached: existing files are skipped)."""
import sys
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele"

FILES = {
    "detalhe_votacao_munzona_2026.zip": f"{TSE}/detalhe_votacao_munzona/detalhe_votacao_munzona_2026.zip",
    "detalhe_votacao_munzona_2022.zip": f"{TSE}/detalhe_votacao_munzona/detalhe_votacao_munzona_2022.zip",
    "perfil_comparecimento_abstencao_2026.zip": f"{TSE}/perfil_comparecimento_abstencao/perfil_comparecimento_abstencao_2026.zip",
    "perfil_comparecimento_abstencao_2022.zip": f"{TSE}/perfil_comparecimento_abstencao/perfil_comparecimento_abstencao_2022.zip",
    # TSE municipality code -> IBGE code (5570 rows)
    "tse_ibge.csv": "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv",
    # IBGE municipal mesh, TopoJSON, lowest quality
    "malha_municipios.topojson": "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=municipio&formato=application/json&qualidade=minima",
}

# Censo 2022 via SIDRA API v3, municipal level (N6). name -> (table, variables, classifications)
SIDRA = "https://servicodados.ibge.gov.br/api/v3/agregados/{t}/periodos/2022/variaveis/{v}?localidades=N6[all]&classificacao={c}"
CENSO = {
    "censo_renda.json": (10295, "13431|13534", "2[6794]|86[95251]|58[95253]"),  # renda domiciliar per capita média/mediana
    "censo_situacao.json": (10211, "93", "2661[32776]|1[all]"),  # população urbana/rural
    "censo_alfabetizacao.json": (9543, "2513", "2[6794]|86[95251]|287[100362]"),  # taxa alfabetização 15+
    "censo_ocupacao.json": (10253, "140", "12085[all]|2[6794]|86[95251]|58[82072]"),  # ocupadas 14+
}
for _name, (_t, _v, _c) in CENSO.items():
    FILES[_name] = SIDRA.format(t=_t, v=_v, c=_c)


def fetch(name, url):
    dest = RAW / name
    if dest.exists():
        print(f"cached  {name}")
        return True
    r = requests.get(url, stream=True, timeout=60)
    if r.status_code != 200:
        print(f"MISSING {name} (HTTP {r.status_code})", file=sys.stderr)
        return False
    tmp = dest.with_suffix(".part")
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    print(f"fetched {name}")
    return True


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        fetch(name, url)
