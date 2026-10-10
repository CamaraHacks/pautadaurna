# Publicação na Oracle Cloud (OCI): pautadaurna.com.br

Uma VM do plano Always Free serve a página estática com o Caddy e atualiza as buscas do Google Trends todo dia, via SerpApi.

## 1. VM
- Crie uma instância **Ubuntu 24.04, Ampere A1 (ARM)**. 1 OCPU e 6 GB bastam. Atribua um IP público.
- Em VCN → Security List, crie regras de entrada para TCP **80** e **443** a partir de `0.0.0.0/0`.
- As imagens Ubuntu da OCI também bloqueiam portas no iptables:
  ```sh
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
  sudo netfilter-persistent save
  ```

## 2. Domínio
No registro.br, no DNS de `pautadaurna.com.br`, crie um registro **A** para `@` e outro para `www`, apontando para o IP público da VM.

## 3. Programas
```sh
sudo apt update && sudo apt install -y git python3-venv curl debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
sudo mkdir -p /var/www/pautadaurna && sudo chown "$USER" /var/www/pautadaurna
```

## 4. Projeto
```sh
git clone https://github.com/CamaraHacks/pautadaurna.git ~/abstencao-2026 && cd ~/abstencao-2026
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp deploy/.env.example .env && chmod 600 .env   # coloque a chave da SerpApi no .env
deploy/atualiza.sh --completo                   # a primeira execução baixa TSE/IBGE (~250 MB) e publica
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

## 5. Atualização diária
```sh
crontab -e
# 06h de Brasília (o relógio da VM está em UTC: 09h)
0 9 * * * /home/ubuntu/abstencao-2026/deploy/atualiza.sh
```

## Orçamento e conferência
- **Orçamento da SerpApi:** `pipeline/06_group_trends.py` gasta no máximo 6 buscas por dia (3 temas, em rodízio) e 5 aos domingos (volumes relativos). Para ao chegar a 95 por mês. Com `--dry-run`, mostra o plano do dia sem gastar.
- **Perfil de 2026:** quando o TSE publicar o perfil de comparecimento, o `atualiza.sh` percebe e refaz os grupos sozinho.
- **Logs e checagem:** os logs ficam em `logs/atualiza.log`. Para conferir se o site está no ar: `curl -I https://pautadaurna.com.br`.
