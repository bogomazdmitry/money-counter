---
name: server-deploy
description: 'Deploy money-counter Telegram bot to production server. Use when: deploying code, rebuilding containers, updating production, pushing changes to server, redeploy.'
---

# Server Deploy

## Server Info

| Property | Value |
|----------|-------|
| Host | `173.212.212.36` |
| User | `root` |
| OS | Ubuntu 24.04 LTS |
| Project dir | `/opt/money-counter` |

## SSH Connection

Password auth only. Use sshpass with `-e` flag (set `SSHPASS` env var) and disable pubkey:

```bash
SSHPASS='<password>' sshpass -e ssh \
  -o StrictHostKeyChecking=no \
  -o PubkeyAuthentication=no \
  root@173.212.212.36 'COMMAND'
```

**Ask the user for the password before connecting.**

## Architecture

```
Docker Compose (/opt/money-counter/docker-compose.yml):
  └── bot (Python 3.13, Telegram long-polling, no ports exposed)
```

- **No nginx/domain needed** — bot uses Telegram long-polling, no incoming connections
- **No database** — state stored in Telegram bot_data via `ContextTypes`

## Deploy Procedure

1. Sync files:
```bash
SSHPASS='<password>' sshpass -e rsync -az \
  -e 'ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no' \
  --exclude='.git' --exclude='.env' --exclude='__pycache__' --exclude='.venv' \
  ./ root@173.212.212.36:/opt/money-counter/
```

2. Build and restart:
```bash
ssh ... 'cd /opt/money-counter && docker compose build --no-cache && docker compose up -d'
```

## Verification

```bash
# Container status
docker compose -f /opt/money-counter/docker-compose.yml ps

# Logs (should show "Application started")
docker logs money-counter-bot --tail 20
```

## Production .env

Located at `/opt/money-counter/.env` (chmod 600). Contains:
- `TELEGRAM_BOT_KEY` — Telegram bot API token

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | `docker logs money-counter-bot` — check for errors |
| Container restarting | Check `TELEGRAM_BOT_KEY` is valid in `.env` |
| Conflict with webhook | Bot auto-deletes webhook on start (`deleteWebhook`), uses polling |
