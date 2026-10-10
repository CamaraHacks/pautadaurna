# Publicação: GitHub Pages + GitHub Actions (pautadaurna.com.br)

O site é um único HTML estático, então não precisa de servidor:
- **Hospedagem:** o GitHub Pages serve a página com HTTPS e domínio próprio. Nenhum IP pessoal fica exposto.
- **Atualização:** o workflow `.github/workflows/atualiza.yml` roda todo dia às 06h de Brasília. Ele coleta as buscas (SerpApi), refaz a página, faz commit e publica.

## Como funciona
| Evento | O que o workflow faz |
|---|---|
| Agendado (diário) ou manual (Actions → "Atualiza e publica" → Run workflow) | Roda `06_group_trends.py` e `04_export.py`, faz commit das mudanças e publica |
| Perfil de comparecimento 2026 publicado pelo TSE | Na execução diária seguinte, também roda 01→03 e troca os grupos para 2026 |
| Push no `master` | Publica a página que está no repositório, sem coletar nada |

## 1. Chave da SerpApi
Crie a conta em serpapi.com (plano grátis, 100 buscas/mês) e guarde a chave como *secret* do repositório:
```sh
gh secret set SERPAPI_KEY --repo CamaraHacks/pautadaurna   # o comando pede a chave sem mostrá-la
```
Sem a chave, o workflow continua publicando, só que com as buscas guardadas em `data/trends_store.json`.

O script gasta no máximo 6 buscas por dia (3 temas em rodízio) e 5 aos domingos, e para ao chegar a 95 por mês.

## 2. DNS no registro.br
No painel do domínio, em **DNS → Editar zona**, crie os registros abaixo:

| Tipo | Nome | Valor |
|---|---|---|
| A | (vazio, raiz) | 185.199.108.153 |
| A | (vazio, raiz) | 185.199.109.153 |
| A | (vazio, raiz) | 185.199.110.153 |
| A | (vazio, raiz) | 185.199.111.153 |
| AAAA | (vazio, raiz) | 2606:50c0:8000::153 |
| AAAA | (vazio, raiz) | 2606:50c0:8001::153 |
| AAAA | (vazio, raiz) | 2606:50c0:8002::153 |
| AAAA | (vazio, raiz) | 2606:50c0:8003::153 |
| CNAME | www | camarahacks.github.io |

A propagação leva de minutos a algumas horas. Depois, em **Settings → Pages**, marque **Enforce HTTPS**. O certificado é emitido sozinho, quando o DNS já aponta para o GitHub.

**Recomendado:** verificar o domínio em **GitHub → Settings (da conta) → Pages → Add a domain**. O GitHub pede um registro TXT `_github-pages-challenge-camarahacks`. Isso impede que outra conta use o seu domínio se o Pages for desligado um dia.

## 3. Conferência
```sh
dig +short pautadaurna.com.br                  # deve listar os 4 IPs 185.199.x.153
curl -I https://pautadaurna.com.br             # deve responder 200
gh run list --repo CamaraHacks/pautadaurna -L 3   # últimas execuções do workflow
```

## Observações
- O GitHub pode atrasar alguns minutos as execuções agendadas.
- O GitHub desliga workflows agendados depois de 60 dias sem atividade no repo. Até 25/out isso não importa; se o site ficar no ar por mais tempo, confira em Actions se o agendamento continua ativo.
- Alternativa com servidor próprio: veja `deploy/OCI.md`.
