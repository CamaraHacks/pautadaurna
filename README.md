# Abstention Map — Brazil 2026, 1st round

Who didn't vote in the first round of Brazil's 2026 presidential election (4 Oct 2026), and where they live.
Municipal turnout data from the Superior Electoral Court (TSE) joined to the 2022 Census (IBGE) for all 5,571 municipalities,
plus the TSE individual-level abstention profile (age, schooling, sex, marital status).

The page (`site/index.html`, in Portuguese) is a single self-contained file: data and map are inlined, so it works on
GitHub Pages and offline.

## Findings (domestic electorate, President, 1st round)

- 32.9M of 157.8M eligible voters abstained: **20.84%**, vs 20.79% in 2022. The rate is flat; the record is in absolute numbers.
- At the municipal level, Census indicators barely correlate with abstention (Spearman ρ: median income 0.00, literacy 0.03, employment 0.04, urban share 0.20).
- The **change** 2022→2026 does correlate with income (ρ = 0.34): abstention fell in the poorest municipalities and the North/Northeast, and rose in the Southeast, South and the largest cities.
- Individually (TSE profile, 2022 until the 2026 file is published), abstention is driven by age (voting is optional at 70+; 27% of all abstainers) and schooling (52% among illiterate voters vs 12% with a college degree).
- 835 municipalities have more registered voters (2026) than residents (2022 Census), a sign that the voter rolls are out of date.

## Reproduce

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python pipeline/01_download.py   # TSE + IBGE SIDRA + mesh -> data/raw (cached)
.venv/bin/python pipeline/02_build.py      # -> data/municipios.csv, data/perfil.csv
.venv/bin/python pipeline/03_analyze.py    # -> site/data.json
.venv/bin/python pipeline/05_trends.py     # optional: Google daily trending snapshot -> site/trends.json
.venv/bin/python pipeline/06_group_trends.py # optional: Google Trends per group (slow, rate-limited, cached) -> site/trends_grupos.json
.venv/bin/python pipeline/04_export.py     # -> site/index.html
```

When TSE publishes `perfil_comparecimento_abstencao_2026.zip`, rerun all four steps; the profile switches to 2026 automatically.

## Site structure

One self-contained page with four views and a global filter (city, state, group) kept in the URL:
**Panorama** (national story), **Onde agir** (ranking, city detail, electoral zones, group weights, abstainers vs. vote margin),
**Kit de redes** (per-group channels, formats, keywords, ready civic messages), **Método**. See `DESIGN.md`.

## Sources

- TSE open data: `detalhe_votacao_munzona` 2022/2026, `perfil_comparecimento_abstencao` 2022
- IBGE SIDRA, 2022 Census tables 10295 (household income per capita), 10211 (urban/rural), 9543 (literacy), 10253 (employment); municipal mesh API
- TSE↔IBGE code table: [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE) (+ Boa Esperança do Norte/MT, installed 2025, added by hand)
- Stated reasons for abstaining: Datafolha, 6–7 Oct 2026 (BR-02949/2026); context from Jairo Nicolau and Avaaz/Datafolha

## Limitations

- **Ecological fallacy:** the Census join is municipal. It says nothing about whether *richer people* abstain more.
- Rates exclude voters abroad (TSE official figure including them: 21.08%).
- The link between stated reasons and data groups on the page is interpretation, and is labelled as such.
