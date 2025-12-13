# ORYTH — Personal Cyber Risk Dashboard

Self-hosted, free, real-time monitoring of your home network and identity.

**Features**
- Live Censys scan of your public IP (open ports, risk score)
- Daily breach check for your emails (Firefox Monitor)
- Beautiful Grafana dashboard

**One-command setup**
```bash
git clone https://github.com/Anandhasasidharan/ORYTH.git
cd ORYTH
cp config/.env.example .env
# Add your Censys token, public IP, emails
docker compose up -d
