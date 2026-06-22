# CLAUDE.md

This file gives Claude Code (and other contributors) the architectural map of this repo. For setup/quick-start see `README.md`; for production topology, secrets, and ops see `DEPLOYMENT.md`.

## Project overview

**ShawaBear** is a Telegram Mini-App for food ordering: browse a menu, add items to a cart, place orders — all inside Telegram. The codebase has since grown a second domain, **product rentals** (`ProductRental` / `ProductRentalSlot` models, `rental` service, `RentalService` on the frontend), bolted onto the original food-ordering app. The Postgres database is still named `rent`, a holdover from before the rental feature existed — that's just legacy naming, not a hint about scope.

The system has three deployable components that talk to each other over HTTP/Telegram:

- **`backend/`** — FastAPI REST API + admin panel, source of truth for data
- **`bot/`** — Aiogram 3 Telegram bot; launches the Mini-App and sends order notifications
- **`frontend/`** — React Mini-App the user interacts with inside Telegram

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, `dependency-injector`, SQLAdmin, Celery |
| Bot | Python 3.11, Aiogram 3 |
| Frontend | React 19, TypeScript, Vite, Chakra UI + Panda CSS, Axios, `@telegram-apps/sdk` |
| Data | PostgreSQL 15, Redis 7 |
| Infra | Docker / Docker Compose, Nginx, GitHub Actions → GHCR → SSH deploy |
| Backend/bot package manager | Poetry |

## Repository layout

```
backend/            FastAPI service (API, admin, migrations)
bot/                Aiogram 3 Telegram bot
frontend/           React + TS Telegram Mini-App
deploy/backend/     Production compose file, backup/restore scripts
docker-compose.yml  Local dev stack (frontend, backend, bot, db, redis, adminer)
.github/workflows/  CI (ci.yml) and deploy (deploy-backend.yml)
README.md           Feature overview & local quick-start
DEPLOYMENT.md       Production topology, secrets, backups
```

## Backend (`backend/src/`)

Layered, dependency-injected architecture:

```
clients/database/models/   SQLAlchemy ORM models (User, Category, Product, ProductRental,
                            Basket, BasketItem, Order, OrderItem)
services/<domain>/         Business logic, one folder per domain: user, product, category,
                            basket, order, rental — each has interface.py + service.py + schemas.py
server/routers/v1/         FastAPI routers, one per domain (e.g. order_router.py),
                            aggregated in routers.py
server/app.py               create_application() factory: CORS, SQLAdmin mount at /admin,
                            exception handlers (handle_erros.py), /media static mount
admin/models/                SQLAdmin view definitions
settings/                     Pydantic settings per concern (database.py, redis.py, uvicorn.py)
container.py                  dependency-injector container wiring sessions/services into routers
```

Request flow: router → service (interface-typed, injected via `container.py`) → SQLAlchemy model/session.

Startup (`entrypoint.sh`): run `alembic upgrade head`, then `python -m src` to launch uvicorn. Migrations live in `backend/migrations/versions/` (30+ revisions).

## Bot (`bot/`)

Entry point `bot/server.py` → `src/app.py` builds the Aiogram `Dispatcher` (in-memory FSM storage) and starts polling. `handlers/` holds command/callback handlers (`/start`, WebApp launch, admin order-notification callbacks); `keyboards/` holds inline/reply keyboard builders. The bot calls the backend over HTTP (`BACKEND_HOST`) and the backend calls back into the bot for order notifications (`services/bot_notification.py`).

## Frontend (`frontend/src/`)

- `api/` — one service class per backend domain (`ProductService`, `OrderService`, `BasketService`, `UserService`, `RentalService`), mirroring `backend/src/services/`
- `assets/` — feature folders: `header/`, `mainList/`, `product/`, `basket/` (cart + order confirmation flow), `profile/`
- `contexts/` — React Context state: `BasketContext`, `OrderContext`, `UserContext`, `TripDatesContext`, `ConstructorContext`, `DrawerContext`
- `components/ui/` — shared Chakra UI primitives (color mode, tooltip, toaster)
- `hooks/`, `types/`, `utils/` — data fetching hooks, TS types, helpers (price/rental formatting)
- `main.tsx` / `App.tsx` — app bootstrap and Telegram WebApp SDK init

## Configuration

Env vars are read via Pydantic settings classes (`backend/src/settings/{database,redis,uvicorn}.py`, prefixed e.g. `DB_*`) loaded from a root `.env`. See `.env.example` for the full list: `DB_*` (Postgres), `REDIS_*`, `BOT_TOKEN`, `BACKEND_HOST`, `VITE_API_BASE_URL` (baked into the frontend build), `SERVER_CORS_INCLUDE_LOCAL_DEV`, `SERVER_RELOAD`.

## Development workflow

```bash
cp .env.example .env   # fill in BOT_TOKEN etc.
docker compose up --build
```

This starts `frontend` (Vite dev server), `backend`, `bot`, `db` (Postgres, volume `postgres_data_dev`), `redis`, and `adminer` (DB browser at `http://localhost:8080`). Backend/bot source is bind-mounted for hot reload (`SERVER_RELOAD=true` enables backend autoreload). Frontend alone: `cd frontend && npm install && npm run dev` → `http://localhost:5173`.

## CI/CD

- **`.github/workflows/ci.yml`** — on PR/push to `main`: frontend lint+build, backend/bot poetry install + syntax check, Docker smoke build (no push).
- **`.github/workflows/deploy-backend.yml`** — on push to `main`: builds frontend/backend/bot images, pushes to GHCR, SSHes into the production host, backs up the DB, and runs `docker compose up -d` with `deploy/backend/docker-compose.prod.yml` + `frontend/deploy/nginx.conf`.

Full secrets list, network topology, and backup/restore procedure are in `DEPLOYMENT.md` — don't duplicate that here, just be aware it exists when touching deploy-related files.

## Testing

`pytest` is configured in `backend/pyproject.toml` (async mode auto), but **no tests exist yet** and CI does not run a test suite — only syntax checks. There is no test suite to run or extend until one is added.
