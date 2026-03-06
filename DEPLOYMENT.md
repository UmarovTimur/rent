# Deployment Guide

## Topology
- `frontend` is deployed to a dedicated static server.
- `backend + bot + postgres + redis` are deployed to a separate backend server with Docker Compose.
- External HTTPS should terminate at your reverse proxy (Caddy or Nginx).

## GitHub Actions Workflows
- `.github/workflows/ci.yml`: lint/build/syntax checks on PR and push to `main`.
- `.github/workflows/deploy-backend.yml`: build/push backend+bot images to GHCR and deploy on backend server over SSH.
- `.github/workflows/deploy-frontend.yml`: build Vite frontend and upload `dist/` to the frontend server over SSH.

## Required GitHub Secrets

### Backend deploy (`deploy-backend.yml`)
- `BACKEND_SSH_HOST`
- `BACKEND_SSH_PORT` (optional, defaults to `22`)
- `BACKEND_SSH_USER`
- `BACKEND_SSH_KEY` (private key in PEM/OpenSSH format)
- `BACKEND_DEPLOY_PATH` (example: `/opt/shawa-bear`)
- `BACKEND_ENV_FILE` (full `.env` content for backend stack)
- `GHCR_USERNAME` (required if GHCR packages are private)
- `GHCR_TOKEN` (PAT with `read:packages`, required if GHCR packages are private)

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

### Frontend deploy (`deploy-frontend.yml`)
- `FRONTEND_SSH_HOST`
- `FRONTEND_SSH_PORT` (optional, defaults to `22`)
- `FRONTEND_SSH_USER`
- `FRONTEND_SSH_KEY`
- `FRONTEND_DEPLOY_PATH` (example: `/var/www/app.example.com`)
- `FRONTEND_ENV_FILE` (optional, content of `frontend/.env.production`)
- `FRONTEND_POST_DEPLOY_CMD` (optional, example: `sudo systemctl reload nginx`)

## Backend Server Bootstrap
1. Install Docker Engine + Docker Compose plugin.
2. Create deploy directory from `BACKEND_DEPLOY_PATH`.
3. Ensure reverse proxy forwards `https://api.example.com` to `127.0.0.1:8000`.
4. Trigger `Deploy Backend And Bot` workflow.

## Frontend Server Bootstrap
1. Configure Nginx/Caddy to serve files from `FRONTEND_DEPLOY_PATH`.
2. Set cache headers for static assets and no-cache for `index.html`.
3. Trigger `Deploy Frontend` workflow.

## Security Baseline
- Never expose `5432`/`6379` to the internet.
- Keep backend bound to localhost (`127.0.0.1:8000`) behind reverse proxy.
- Restrict CORS to exact frontend domains using `SERVER_CORS_ORIGINS`.
- Rotate bot/API tokens and DB passwords before production.
- Store all secrets only in GitHub Secrets (not in repo).
- Add host firewall rules: open only `22`, `80`, `443`.
- Enable automatic security updates on both servers.
- Run regular DB backups (`pg_dump`) to off-server storage.
