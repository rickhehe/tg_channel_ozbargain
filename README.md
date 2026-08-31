# tg_channel_ozbargain

Run-and-exit OzBargain to Telegram notifier designed for cron and container jobs.

## Environment

1. Copy env template:

```bash
cp .env.example .env
```

2. Set required values in `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional:

- `ANCHOR_FILE` (optional override)

Default anchor path behavior:

- local `uv run`: `./anchor.txt`
- docker-compose: `/data/anchor.txt`

## Run Locally

```bash
uv run python -m main
```

This will persist state to `./anchor.txt` unless `ANCHOR_FILE` is explicitly set.

## Run with Docker Compose (One Shot)

```bash
mkdir -p data
docker compose build
docker compose run --rm notifier
```

Anchor state is stored in `./data/anchor.txt` on the host.

## Cron on Raspberry Pi

Add to crontab (assume your user is `pi` and project is in `/home/pi/project/tg_channel_ozbargain`):

```bash
mkdir -p /home/pi/logs
crontab -e
*/5 * * * * cd /home/pi/project/tg_channel_ozbargain && /usr/bin/docker compose run --rm notifier >> /home/pi/logs/tg_channel_ozbargain.log 2>&1
```

Logs are centralized under `~/logs/` (shared across cron jobs) rather than kept per-project.

## CI Image Build

The workflow in `.github/workflows/deploy.yml` builds and pushes a multi-arch image (`linux/amd64`, `linux/arm64`) to GHCR on pushes to `master` or `main`.
