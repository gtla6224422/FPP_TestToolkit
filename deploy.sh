#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
IMAGE_NAME="fpp-test-toolkit:local"
APP_CONTAINER_NAME="fpp-test-toolkit"
CONTAINER_PREFIX="fpp-test-toolkit"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "未找到 docker-compose.yml：$COMPOSE_FILE" >&2
  exit 1
fi

cd "$PROJECT_DIR"

if [[ ! -f ".env" && -f ".env.example" ]]; then
  log "检测到 .env 不存在，自动从 .env.example 复制"
  cp .env.example .env
fi

log "停止并移除当前项目容器"
docker compose down --remove-orphans || true

mapfile -t matched_containers < <(docker ps -a --format '{{.Names}}' | grep "^${CONTAINER_PREFIX}" || true)

if [[ ${#matched_containers[@]} -gt 0 ]]; then
  log "清理项目相关历史容器：${matched_containers[*]}"
  docker rm -f "${matched_containers[@]}" >/dev/null
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$APP_CONTAINER_NAME"; then
  log "强制清理应用容器：$APP_CONTAINER_NAME"
  docker rm -f "$APP_CONTAINER_NAME" >/dev/null
fi

if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  log "删除旧镜像：$IMAGE_NAME"
  docker rmi "$IMAGE_NAME" >/dev/null || true
fi

log "重新构建并启动服务"
docker compose up --build -d

log "当前容器状态"
docker compose ps

log "部署完成，访问地址：http://<服务器IP>:5003"
