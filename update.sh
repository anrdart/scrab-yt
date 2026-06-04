#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

cd "$(dirname "$0")"

# --- Pull latest code ---
if git rev-parse --is-inside-work-tree &>/dev/null; then
    info "Pulling latest code..."
    git pull --ff-only || warn "Git pull failed. Continuing with local code."
fi

# --- Rebuild and restart ---
info "Rebuilding images..."
docker compose build

info "Restarting services..."
docker compose down
docker compose up -d --remove-orphans

info "Waiting for backend health check..."
timeout=120
elapsed=0
until docker compose exec -T backend python -c "import httpx; httpx.get('http://localhost:8001/api/health').raise_for_status()" 2>/dev/null; do
    sleep 2
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge "$timeout" ]; then
        warn "Health check timeout after ${timeout}s"
        echo ""
        echo "Logs:"
        docker compose logs --tail=20
        exit 1
    fi
done

# --- Cleanup old images ---
info "Cleaning up dangling images..."
docker image prune -f 2>/dev/null || true

echo ""
info "=== ytdupe backend updated successfully ==="
info "Backend: http://localhost:8001"
