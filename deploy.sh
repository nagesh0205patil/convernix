#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
TARGET="${1:-all}"

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [all|frontend|backend|database|help]

Targets:
  all        Build and deploy database, Redis, backend, worker, and frontend.
  frontend   Build and deploy only the frontend container.
  backend    Build and deploy backend and worker, including database and Redis.
  database   Deploy only the PostgreSQL database container.
  help       Display this help message.

Examples:
  ./deploy.sh all
  ./deploy.sh frontend
  ./deploy.sh backend
  ./deploy.sh database
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or is not available in PATH."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is not available."
[[ -f "${COMPOSE_FILE}" ]] || fail "Compose file not found: ${COMPOSE_FILE}"

cd "${SCRIPT_DIR}"

if [[ "${TARGET}" == "all" || "${TARGET}" == "backend" ]]; then
  [[ -f Backend/.env ]] || fail "Backend/.env is missing. Copy Backend/.env.example and configure it before deployment."
fi

if [[ "${TARGET}" == "all" || "${TARGET}" == "frontend" ]]; then
  [[ -f Frontend/.env ]] || fail "Frontend/.env is missing. Copy Frontend/.env.example and configure it before deployment."
fi

compose() {
  docker compose --file "${COMPOSE_FILE}" "$@"
}

deploy_database() {
  log "Deploying PostgreSQL database"
  compose up --detach --no-deps whatsapp-database-service
  log "Waiting for PostgreSQL health check"
  compose up --detach --wait --no-deps whatsapp-database-service
}

deploy_backend() {
  log "Deploying backend dependencies"
  compose up --detach whatsapp-database-service whatsapp-redisdbs-service

  log "Building Django backend and Celery worker"
  compose build whatsapp-backend-service whatsapp-worker-service

  log "Deploying Django backend and Celery worker"
  compose up --detach --wait whatsapp-backend-service whatsapp-worker-service
}

deploy_frontend() {
  log "Building frontend"
  compose build whatsapp-frontend-service

  log "Deploying frontend only"
  compose up --detach --no-deps whatsapp-frontend-service
}

deploy_all() {
  log "Building the complete application"
  compose build whatsapp-backend-service whatsapp-worker-service whatsapp-frontend-service

  log "Deploying PostgreSQL, Redis, Django, Celery, and React frontend"
  compose up --detach --wait whatsapp-database-service whatsapp-redisdbs-service whatsapp-backend-service whatsapp-worker-service whatsapp-frontend-service
}

case "${TARGET}" in
  all)
    deploy_all
    ;;
  frontend)
    deploy_frontend
    ;;
  backend)
    deploy_backend
    ;;
  database|db)
    deploy_database
    ;;
  help|-h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    fail "Unknown deployment target: ${TARGET}"
    ;;
esac

log "Deployment completed for target: ${TARGET}"
compose ps
