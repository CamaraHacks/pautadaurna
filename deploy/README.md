# Deploy on Oracle Cloud (OCI) — pautadaurna.com.br

One Always Free VM serves the static page with Caddy and refreshes Google Trends data daily through SerpApi.

## 1. VM
- Create an instance: **Ubuntu 24.04, Ampere A1 (ARM)**, 1 OCPU / 6 GB is plenty. Assign a public IP.
- VCN → Security List: add ingress rules for TCP **80** and **443** from `0.0.0.0/0`.
- Ubuntu images on OCI also block ports in iptables:
  ```sh
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
  sudo netfilter-persistent save
  ```

## 2. Domain
At registro.br, DNS for `pautadaurna.com.br`: an **A** record for `@` and for `www` pointing to the VM public IP.

## 3. Software
```sh
sudo apt update && sudo apt install -y git python3-venv curl debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
sudo mkdir -p /var/www/pautadaurna && sudo chown "$USER" /var/www/pautadaurna
```

## 4. Project
```sh
git clone <repo-url> ~/abstencao-2026 && cd ~/abstencao-2026
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp deploy/.env.example .env && chmod 600 .env   # put the SerpApi key in .env
deploy/atualiza.sh --completo                   # first run downloads TSE/IBGE (~250 MB) and publishes
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

## 5. Daily job
```sh
crontab -e
# 06:00 Brasília (the VM clock is UTC: 09:00)
0 9 * * * /home/ubuntu/abstencao-2026/deploy/atualiza.sh
```

## Budget and checks
- `pipeline/06_group_trends.py` spends at most 6 SerpApi searches a day (3 themes, rotating) and 5 on Sundays
  (relative volumes), and stops at 95 per month. `--dry-run` prints the plan without spending.
- When TSE publishes the 2026 turnout profile, `atualiza.sh` detects it and rebuilds the groups automatically.
- Logs: `logs/atualiza.log`. Check: `curl -I https://pautadaurna.com.br`.
