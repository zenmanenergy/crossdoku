#!/usr/bin/env bash
# Crossdoku deploy: run ON the server from the repo folder (/opt/games/crossdoku).
#   ./deploy.sh
# nginx serves Client/ straight from this folder, so there is no build or copy step.
set -euo pipefail

# ---- settings: check these match your server ----
APP_DIR="/opt/games/crossdoku"
BRANCH="main"
SERVICE="crossdoku"          # systemd unit name (docs/crossdoku.service)
VENV_NAME="venv"
HEALTH_URL="http://127.0.0.1:9010/api/health"
# -------------------------------------------------

cd "$APP_DIR"

echo "==> Pulling $BRANCH"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "==> Python environment"
cd Server
if [ ! -d "$VENV_NAME" ]; then
	python3 -m venv "$VENV_NAME"
fi
"$VENV_NAME/bin/pip" install -q --upgrade pip
"$VENV_NAME/bin/pip" install -q -r requirements.txt pytest

if [ ! -f .env ]; then
	echo "!! Server/.env is missing. Copy .env.example to .env and fill it in, then run deploy.sh again."
	exit 1
fi

echo "==> Puzzle storage"
# Shared puzzles are saved as JSON files here. The service runs as www-data, so it must own this folder.
# (If you set DATA_DIR in .env to somewhere else, create and chown that folder yourself.)
mkdir -p data/puzzles
chown -R www-data:www-data data

echo "==> Tests"
"$VENV_NAME/bin/python" -m pytest -q Tests

echo "==> Restarting $SERVICE"
sudo systemctl restart "$SERVICE"
sleep 2
if curl -fsS "$HEALTH_URL" > /dev/null; then
	echo "==> Deployed. Health check OK."
else
	echo "!! Health check failed. See: sudo journalctl -u $SERVICE -n 50"
	exit 1
fi
