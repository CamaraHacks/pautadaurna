# Pauta da Urna: quem não votou no 1º turno de 2026

Quem deixou de votar no 1º turno da eleição presidencial de 2026 (4 de outubro), onde vive e como chegar até essas pessoas antes do 2º turno (25 de outubro).

O site é para **criadores de conteúdo** que querem trazer eleitores ausentes de volta à urna. Ele cruza dados do TSE com o Censo 2022 do IBGE para os 5.571 municípios, desce até a zona eleitoral nas cidades grandes e divide os ausentes em cinco grupos. Cada grupo tem um kit com redes, formatos, palavras-chave, temas e mensagens prontas para copiar.

**É apartidário.** As mensagens explicam como e onde votar e não pedem voto em ninguém. Os candidatos aparecem em cores neutras, sem relação com partidos.

A página (`site/index.html`) é um único arquivo com dados e mapa embutidos: funciona offline, em qualquer servidor estático e no GitHub Pages.

## O que os dados mostram (eleitorado no Brasil, Presidente, 1º turno)

- **A taxa não mudou; o número absoluto é recorde.** 32,9 milhões de 157,8 milhões de aptos não votaram: **20,84%**, contra 20,79% em 2022.
- **A ausência é maior que a diferença.** Os dois primeiros ficaram separados por 2,24 milhões de votos: são cerca de **15 ausentes para cada voto de diferença**. Na cidade de São Paulo, a proporção é de 7,3 para 1.
- **Região:** o Nordeste faltou menos (18,4%) e o Sudeste mais (22,7%). Desde 2022, a abstenção caiu no Norte e no Nordeste e subiu no Sudeste, no Sul e nas maiores cidades.
- **Quem falta tem idade e escolaridade** (perfil do TSE de 2022, até sair o de 2026):
  - quem tem 70 anos ou mais, com voto facultativo, é 27% dos ausentes;
  - a abstenção é de 52% entre analfabetos e de 12% entre quem tem superior completo.
- **Cinco grupos de ausentes:**

  | Grupo | Peso entre os ausentes |
  |---|---|
  | Idosos com voto facultativo (70+) | 27% |
  | Trabalhadores de baixa escolaridade (30–69 anos, até o fundamental) | 25% |
  | Jovens obrigados a votar (18–29) | 24% |
  | Escolaridade média (30–69 anos, ensino médio) | 19% |
  | Superior completo (30–69 anos) | 4% |
- **Cadastro desatualizado:** 835 municípios têm mais eleitores aptos em 2026 do que moradores no Censo 2022.

## Estrutura do site

Uma página com quatro abas e um filtro global (cidade, estado e grupo) que fica salvo no endereço, para compartilhar exatamente o que se está vendo:

- **Panorama:** a história nacional, com mapa por município, perfil por idade e escolaridade e os motivos declarados para não votar.
- **Onde agir:**
  - ranking de cidades por número de ausentes, com a comparação entre ausentes e a diferença de votos;
  - visão da cidade, com o peso de cada grupo e as zonas eleitorais.
- **Kit de redes:** por grupo, redes e formatos, palavras-chave, mensagens cívicas, dores em destaque e um carrossel de temas com buscas do Google Trends.
- **Método:** limites e guia de uso.

O sistema visual está documentado em `DESIGN.md`.

## Como reproduzir

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python pipeline/01_download.py      # TSE + IBGE SIDRA + malha municipal -> data/raw (com cache)
.venv/bin/python pipeline/02_build.py         # -> data/municipios.csv, perfil.csv, segmentos.csv, zonas.csv, votos.csv
.venv/bin/python pipeline/03_analyze.py       # -> site/data.json
.venv/bin/python pipeline/06_group_trends.py  # Google Trends por grupo via SerpApi (SERPAPI_KEY; rodízio diário, até 95/mês)
.venv/bin/python pipeline/04_export.py        # -> site/index.html
```

Sem a variável `SERPAPI_KEY`, o passo 06 apenas remonta os dados das buscas a partir de `data/trends_store.json`.

`pipeline/05_trends.py`, opcional, guarda uma foto dos assuntos brasileiros em alta no Google.

Quando o TSE publicar `perfil_comparecimento_abstencao_2026.zip`, rodar de novo os passos 01 a 04 troca os grupos para 2026 automaticamente.

## Publicação

GitHub Pages com domínio próprio, atualizado todo dia por GitHub Actions: veja `deploy/README.md`. A alternativa com servidor próprio (Oracle Cloud) está em `deploy/OCI.md`.

## Fontes

- **TSE, dados abertos:**
  - `detalhe_votacao_munzona` 2022 e 2026;
  - `votacao_candidato_munzona` 2026;
  - `perfil_comparecimento_abstencao` 2022.
- **IBGE, SIDRA:** tabelas do Censo 2022 10295 (renda), 10211 (situação do domicílio), 9543 (alfabetização) e 10253 (ocupação), e a malha municipal.
- **Tabela TSE ↔ IBGE:** [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE), mais Boa Esperança do Norte (MT), instalado em 2025 e incluído à mão.
- **Pesquisas:**
  - Datafolha 2–3/out/2026 (BR-01708/2026), por idade e renda;
  - Datafolha 6–7/out/2026 (BR-02949/2026), motivos da abstenção;
  - Quaest, sobre os principais problemas do país;
  - Avaaz e Datafolha, Termômetro do Bem Viver.
- **Uso de redes:** Reuters Institute, Digital News Report 2025, Brasil.
- **Análise de contexto:** Jairo Nicolau.
- **Buscas:** Google Trends, via SerpApi.

## Limites

- **Falácia ecológica:** resultados por município ou zona descrevem lugares, não pessoas.
- **Classe social:** a escolaridade é usada como aproximação, porque o TSE não registra renda.
- **Inclinação política dos grupos:** é uma estimativa. O voto de quem se absteve não é observável.
- **Google Trends:** não separa buscas por idade ou classe. O kit lê cada grupo por onde os ausentes dele vivem.
- **Exterior:** as taxas não incluem eleitores no exterior. O número oficial do TSE, com eles, é 21,08%.
- **Dados pessoais:** tudo é agregado; não há dado de nenhum eleitor individual (LGPD).
- **Impulsionamento:** impulsionamento pago de conteúdo eleitoral é exclusivo de candidatos e partidos (Res. TSE 23.610/2019).

## Autor

Criado por **Gustavo Câmara**: [LinkedIn](https://www.linkedin.com/in/camarahacks/) · [GitHub](https://github.com/CamaraHacks)
