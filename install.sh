#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- Check dependencies ---
info "Checking dependencies..."

if ! command -v docker &>/dev/null; then
    error "Docker not found. Install: https://docs.docker.com/engine/install/"
fi

if ! docker compose version &>/dev/null; then
    error "Docker Compose v2 not found. Install: https://docs.docker.com/compose/install/"
fi

if ! docker info &>/dev/null 2>&1; then
    error "Docker daemon not running or no permission. Try: sudo systemctl start docker"
fi

info "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+')"
info "Compose $(docker compose version --short)"

# --- Build and start ---
cd "$(dirname "$0")"

info "Building images..."
docker compose build --no-cache

info "Starting services..."
docker compose up -d

info "Waiting for backend health check..."
timeout=60
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

echo ""
info "=== ytdupe backend installed successfully ==="
info "Backend: http://localhost:8001"
info "Health:  http://localhost:8001/api/health"
echo ""
info "Commands:"
info "  docker compose logs -f        # view logs"
info "  docker compose down            # stop"
info "  docker compose up -d           # start"
info "  bash update.sh                 # update"
