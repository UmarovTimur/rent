# rent

A Telegram Mini-App for browsing, ordering, and renting products — all inside Telegram.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Chakra UI + Panda CSS |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, Celery |
| Bot | Python 3.11, Aiogram 3 |
| Data | PostgreSQL 15, Redis 7 |
| Infra | Docker / Docker Compose, Nginx |

## Features

- Menu browsing by category with product detail pages
- Cart management and order placement
- Product rental with date-range slot selection
- JWT auth via Telegram WebApp init data
- Admin panel (SQLAdmin at `/admin`) for managing products, orders, rentals
- Order notifications sent back through the Telegram bot

## Services

| Service | Port | Description |
|---|---|---|
| `frontend` | 5173 | React Vite dev server (via Nginx) |
| `backend` | 8000 | FastAPI REST API + admin |
| `bot` | 8001 | Aiogram 3 Telegram bot |
| `db` | 5438 | PostgreSQL 15 |
| `redis` | 6379 | Redis 7 |
| `adminer` | 8083 | DB browser |

## Quick start

### 1. Clone

```bash
git clone <repo-url>
cd rent
```

### 2. Configure

```bash
cp .env.example .env
# Fill in at minimum: BOT_TOKEN, JWT_SECRET
```

Key env vars:

| Variable | Description |
|---|---|
| `BOT_TOKEN` | BotFather token |
| `JWT_SECRET` | Random secret — `openssl rand -hex 32` |
| `VITE_API_BASE_URL` | Backend URL visible to the Mini-App (use tunnel URL for Telegram) |
| `DB_*` | Postgres connection (defaults work with Docker) |
| `REDIS_*` | Redis connection (defaults work with Docker) |
| `BACKEND_HOST` | Backend URL for the bot container |
| `SERVER_CORS_INCLUDE_LOCAL_DEV` | Set `true` to allow localhost origins in dev |

### 3. Run

```bash
docker compose up --build
```

Migrations run automatically on backend startup (`alembic upgrade head`). Frontend and backend source are bind-mounted — changes apply without rebuilding.

### 4. Frontend only (optional)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Set `VITE_API_BASE_URL=http://localhost:8000` and run the backend separately or via Docker.

## Project layout

```
backend/            FastAPI service (API, admin, Alembic migrations)
bot/                Aiogram 3 Telegram bot
frontend/           React + TypeScript Mini-App
deploy/backend/     Production compose file, backup/restore scripts
docker-compose.yml  Local dev stack
.github/workflows/  CI and deploy pipelines
```
