# Pauta da Urna: quem não votou no 1º turno de 2026

Quem deixou de votar no 1º turno da eleição presidencial de 2026 (4 de outubro), onde vive e como chegar até essas pessoas antes do 2º turno (25 de outubro).

O site é para **criadores de conteúdo** que querem trazer eleitores ausentes de volta à urna. Ele cruza dados do TSE com o Censo 2022 do IBGE para os 5.571 municípios, desce até a zona eleitoral nas cidades grandes e divide os ausentes em cinco grupos. Cada grupo tem um kit com redes, formatos, palavras-chave, temas e mensagens prontas para copiar.

**Tem lado: defendemos a democracia e, por isso, apoiamos Lula no 2º turno.** Isso não muda os números: cada dado vem de fonte oficial, com link, e as propostas dos dois candidatos são citadas dos planos de governo registrados no TSE, com a página. Quando um plano não trata de um tema, o site diz isso, sem atribuir intenção.

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
  - ranking de cidades ou de regiões (Regiões Imediatas do IBGE, como a Baixada Santista), com ausentes, mobilizáveis e saldo pró-Lula;
  - visão da cidade, com o peso de cada grupo, os setores (Centro, Norte, Sul, Leste, Oeste) nas cidades com mais de 500 mil eleitores, os locais de votação ordenados por saldo e as zonas eleitorais.
- **Kit de redes:** por grupo, dores em destaque, pautas que comparam os planos de Lula e Flávio (com fato oficial e página do plano), imagem pronta para post, redes e formatos, mensagens cívicas e um carrossel de temas com buscas do Google Trends.
- **Postar:** peças prontas para Instagram, TikTok e WhatsApp, com os números da cidade ou do estado escolhido:
  - imagem do dado local (post e story);
  - carrossel de 5 imagens por pauta;
  - imagem 9:16;
  - legendas por rede, roteiro de 30 s para gravar e botão "Abrir no WhatsApp";
  - galeria de vídeos curtos enviados ao projeto;
  - calendário e regras do TSE.
- **Método** e **Sobre:** limites, posição editorial, regras e autoria.

O sistema visual está documentado em `DESIGN.md`.

## Como reproduzir

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python pipeline/01_download.py      # TSE + IBGE SIDRA + malha municipal -> data/raw (com cache)
.venv/bin/python pipeline/02_build.py         # -> data/municipios.csv, perfil.csv, segmentos.csv, zonas.csv, votos.csv
.venv/bin/python pipeline/03_analyze.py       # -> site/data.json
.venv/bin/python pipeline/06_group_trends.py  # Google Trends por grupo via SerpApi (SERPAPI_KEY; rodízio diário, até 95/mês)
.venv/bin/python pipeline/07_secoes.py        # seções 2026 (comparecimento + votos + locais) -> data/locais.csv (~350 MB de download)
.venv/bin/python pipeline/08_regioes.py       # regiões imediatas, setores das cidades grandes, saldo -> site/regioes.json, site/locais/<UF>.json
.venv/bin/python pipeline/04_export.py        # -> site/index.html
```

Sem a variável `SERPAPI_KEY`, o passo 06 apenas remonta os dados das buscas a partir de `data/trends_store.json`.

`pipeline/05_trends.py`, opcional, guarda uma foto dos assuntos brasileiros em alta no Google.

Quando o TSE publicar `perfil_comparecimento_abstencao_2026.zip`, rodar de novo os passos 01 a 04 troca os grupos para 2026 automaticamente.

## Vídeos curtos

Os vídeos gravados por pessoas entram pela pasta `videos/entrada/`, que não vai para o git, e pela lista `videos/videos.csv`, com uma linha por vídeo: arquivo, título, grupo, pauta, autor, autorização e fontes.

```sh
.venv/bin/python pipeline/09_videos.py   # -> site/videos/<id>.mp4 + capa, site/videos.json
```

O script:
- recusa vídeos sem autorização do autor e vídeos que afirmam dados sem fonte;
- converte para MP4 H.264 9:16, com faststart e cerca de 3 Mbps;
- acrescenta 1,5 s de cartela final do Pauta da Urna, com crédito ao autor.

Exige ffmpeg e Pillow. As fontes da cartela (licença OFL) estão em `assets/fonts/`.

## Material de terceiros: Acervo da Vitória

`pipeline/10_acervo.py` lê todo dia o índice aberto do [Acervo da Vitória](https://acervodavitoria.pages.dev). O site linka os arquivos no Drive deles, sem hospedar cópias, e mostra os itens embaixo da pauta do mesmo tema, no Kit e na aba Postar.

Regras de curadoria:
- entram vídeos, artes, selfies do Lula e guias;
- ficam de fora os conteúdos feitos com IA ("Novelinha IA", "Memes IA") e as acusações de crime sem condenação;
- os selfies são reais e entram com o selo "fala de campanha do Lula";
- cada item leva o selo "material de terceiros".

Para barrar ou aprovar um item específico, inclua uma linha em `acervo/regras.csv` com `id,acao,motivo`, onde a ação é `barrar` ou `aprovar`.

## Regras para as peças

- As imagens e os textos foram produzidos com apoio de IA, então trazem o aviso exigido pela Res. TSE 23.755/2026.
- Esse tipo de conteúdo só pode ser publicado ou republicado até 72 horas antes do pleito: **até 21/10**.
- Vídeos gravados por pessoas podem circular até 24/10.
- Impulsionamento pago é exclusivo de campanhas.
- No dia 25, nada novo.

## Publicação

GitHub Pages com domínio próprio, atualizado todo dia por GitHub Actions: veja `deploy/README.md`. A alternativa com servidor próprio (Oracle Cloud) está em `deploy/OCI.md`.

## Fontes

- **TSE, dados abertos:**
  - `detalhe_votacao_munzona` 2022 e 2026;
  - `votacao_candidato_munzona` 2026;
  - `perfil_comparecimento_abstencao` 2022.
- **IBGE, SIDRA:** tabelas do Censo 2022 10295 (renda), 10211 (situação do domicílio), 9543 (alfabetização) e 10253 (ocupação), e a malha municipal.
- **Tabela TSE ↔ IBGE:** [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE), mais Boa Esperança do Norte (MT), instalado em 2025 e incluído à mão.
- **TSE, por seção (2026):** `detalhe_votacao_secao`, `votacao_secao_2026_BR` e `eleitorado_local_votacao`.
- **IBGE:** Regiões Geográficas Imediatas (API de localidades). Coordenadas das sedes municipais: [kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros).
- **Planos de governo registrados no TSE:** cópias integrais publicadas pelo Poder360.
- **Fatos oficiais das pautas:** IBGE (PNAD Contínua), Planalto (Decreto 12.797/2025 e Lei 15.270/2025), Secom e Ministério da Saúde (Farmácia Popular), MDS (FAO/SOFI 2025) e Agência Brasil (PEC da escala 6x1).
- **Pesquisas:**
  - Datafolha 2–3/out/2026 (BR-01708/2026), por idade e renda;
  - Datafolha 6–7/out/2026 (BR-02949/2026), motivos da abstenção;
  - Quaest, sobre os principais problemas do país;
  - Avaaz e Datafolha, Termômetro do Bem Viver.
- **Uso de redes:** Reuters Institute, Digital News Report 2025, Brasil.
- **Análise de contexto:** Jairo Nicolau.
- **Buscas:** Google Trends, via SerpApi.

### Saldo pró-Lula

Para cada local de votação, calcula-se: ausentes mobilizáveis × (Lula% − Flávio%) dos votos válidos daquele local no 1º turno. Os mobilizáveis são os ausentes sem a fatia de 70+ do município. A conta supõe que quem faltou votaria como os vizinhos de seção, então serve para priorizar onde agir, não como previsão. Os totais por seção batem com os do município (157.828.968 aptos e 32.894.899 ausentes).

### Medição de uso

O site conta visitas e ações (copiar, baixar imagem, compartilhar) com o [GoatCounter](https://www.goatcounter.com): sem cookies e sem dado pessoal. Para ativar, defina a variável `GOATCOUNTER` do repositório com o código do site (Settings → Secrets and variables → Actions → Variables). Sem ela, nada é medido.

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
