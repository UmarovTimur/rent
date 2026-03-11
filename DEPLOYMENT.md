# Deployment Guide

## Topology
- `frontend + backend + bot + postgres + redis` are deployed on the same cloud server with one `docker compose`.
- `frontend` runs in an `nginx` container and serves the built Vite app.
- Requests to `/api`, `/media`, and `/admin` are proxied from `nginx` to the internal `backend` container.
- External HTTPS should terminate at your cloud load balancer or host-level reverse proxy, or you can extend the frontend `nginx` config for TLS later.

## GitHub Actions Workflows
- `.github/workflows/ci.yml`: lint/build/syntax checks on PR and push to `main`.
- `.github/workflows/deploy-backend.yml`: build/push `frontend + backend + bot` images to GHCR and deploy the full stack on the server over SSH.

## Required GitHub Secrets

### Production deploy (`deploy-backend.yml`)
- `BACKEND_SSH_HOST`
- `BACKEND_SSH_PORT` (optional, defaults to `22`)
- `BACKEND_SSH_USER`
- `BACKEND_SSH_KEY` (private key in PEM/OpenSSH format)
- `BACKEND_DEPLOY_PATH` (example: `/opt/shawa-bear`)
- `BACKEND_ENV_FILE` (full `.env` content for the compose stack)
- `GHCR_USERNAME` (required if GHCR packages are private)
- `GHCR_TOKEN` (PAT with `read:packages`, required if GHCR packages are private)
- `FRONTEND_VITE_API_BASE_URL` (optional, defaults to `/`)

Minimal `BACKEND_ENV_FILE` example:
```env
API_TOKEN=...
BACKEND_HOST=http://backend:8000
DB_HOST=db
DB_PORT=5432
DB_NAME=rent
DB_USER=admin
DB_PASSWORD=strong-password
REDIS_HOST=redis
REDIS_PORT=6379
SERVER_CORS_ORIGINS=https://app.example.com
```

Required for production compose interpolation:
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

These must exist in `BACKEND_ENV_FILE`, because `docker compose` reads them while rendering the stack. Image tags are not stored in `.env`; the workflow injects `FRONTEND_IMAGE`, `BACKEND_IMAGE`, and `BOT_IMAGE` at deploy time.

If frontend and backend share one public domain, you can omit `FRONTEND_VITE_API_BASE_URL` and keep the default `/`.

## Database Persistence
- Local development Postgres uses the named volume `postgres_data_dev`, so data survives container recreation.
- Production Postgres uses the named volume `postgres_data`, so application deploys do not remove existing data.
- Do not run `docker compose down -v` on environments where you want to keep the database.

## Database Backups
- Every production deploy runs `backup-db.sh` before updating containers and stores dumps in `${BACKEND_DEPLOY_PATH}/backups`.
- Old backups older than 14 days are removed automatically.
- To create a manual backup on the server:

```bash
cd "$BACKEND_DEPLOY_PATH"
./backup-db.sh
```

- To restore a backup on the server:

```bash
cd "$BACKEND_DEPLOY_PATH"
./restore-db.sh ./backups/postgres_YYYY-MM-DDTHH-MM-SSZ.dump
```

Recommended workflow:
1. Keep separate databases for `dev` and `prod`.
2. Move schema changes with Alembic migrations, not by copying the whole production database into development.
3. Restore a production dump into development only when you explicitly need realistic data, and anonymize sensitive records first.

## Server Bootstrap
1. Install Docker Engine + Docker Compose plugin.
2. Create deploy directory from `BACKEND_DEPLOY_PATH`.
3. Open inbound ports `80` and optionally `443` on the server/firewall.
4. Point your domain to the server IP.
5. Trigger `Deploy Production Stack` workflow.

## Security Baseline
- Never expose `5432`/`6379` to the internet.
- Do not publish the backend container port; reach it only through the frontend `nginx` proxy.
- Restrict CORS to exact frontend domains using `SERVER_CORS_ORIGINS` if the API may still be called cross-origin.
- Rotate bot/API tokens and DB passwords before production.
- Store all secrets only in GitHub Secrets (not in repo).
- Add host firewall rules: open only `22`, `80`, `443`.
- Enable automatic security updates on both servers.
- Run regular DB backups (`pg_dump`) to off-server storage.
