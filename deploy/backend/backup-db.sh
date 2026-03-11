#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-docker-compose.yml}"
env_file="${ENV_FILE:-.env}"
backup_dir="${BACKUP_DIR:-./backups}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
timestamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
backup_file="${backup_dir}/postgres_${timestamp}.dump"

compose_cmd=(docker compose -f "$compose_file" --env-file "$env_file")

mkdir -p "$backup_dir"

if ! "${compose_cmd[@]}" exec -T db sh -lc 'pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
  echo "Database container is unavailable; skipping backup"
  exit 0
fi

"${compose_cmd[@]}" exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_file"

find "$backup_dir" -type f -name 'postgres_*.dump' -mtime "+${retention_days}" -delete

echo "Backup saved to ${backup_file}"
