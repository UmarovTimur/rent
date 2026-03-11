<!-- 🎉 Welcome Banner -->
<p align="center">
  <img src="https://img.shields.io/badge/ShawaBear-🐻-brightgreen?style=for-the-badge" alt="ShawaBear" />
  <img src="https://img.shields.io/badge/Telegram–Mini%20App-blue?style=for-the-badge" alt="Telegram Mini App" />
</p>

# 🐻 ShawaBear – Telegram Mini-App Food Ordering

ShawaBear is a **Telegram Mini-App** that lets users browse a menu 🌮, add items to cart 🛒, and place food orders 🍔—all without leaving Telegram!

## 📦 Tech Stack

<table>
  <thead>
    <tr>
      <th>Layer</th>
      <th colspan="2">Technology</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Client</strong></td>
      <td>React + TypeScript</td>
      <td align="right">⚛️</td>
    </tr>
    <tr>
      <td></td>
      <td>Chakra UI</td>
      <td align="right">🎨</td>
    </tr>
    <tr>
      <td><strong>Server</strong></td>
      <td>FastAPI</td>
      <td align="right">🚀</td>
    </tr>
    <tr>
      <td></td>
      <td>PostgreSQL</td>
      <td align="right">🐘</td>
    </tr>
    <tr>
      <td></td>
      <td>SQLAlchemy (ORM)</td>
      <td align="right">📦</td>
    </tr>
    <tr>
      <td><strong>Bot</strong></td>
      <td>Aiogram 3</td>
      <td align="right">🤖</td>
    </tr>
    <tr>
      <td><strong>Dev Tools</strong></td>
      <td>Docker & Docker Compose</td>
      <td align="right">📦</td>
    </tr>
  </tbody>
</table>

## ✨ Main Features

### Client (Frontend)
- 🎨 Interactive UI with Chakra UI components
- 📄 Menu Browsing: View categories, dishes & details
- 🛒 Cart Management: Add, remove, update quantities
- 📝 Order Form: Submit delivery info & payment options

### Server (Backend)
- 🔐 Auth & Sessions (if needed)
- 📋 Menu API: CRUD endpoints for categories & dishes
- 🧾 Order API: Create, list & track orders
- ⚙️ Error Handling: Consistent JSON error responses

### Telegram Bot
- 🪄 /start Command: Welcomes user & provides menu link
- 🖥️ WebApp Launch: Opens the React mini-app in chat
- 📣 Order Notifications: Sends order confirmations & status

## 📂 Folder Structure

```
├── .gitignore            # Git ignore rules (e.g., node_modules, __pycache__, .env)
├── docker-compose.yml    # Orchestrates backend API, Postgres DB, and Telegram bot containers
├── README.md             # Project overview, tech stack, setup & usage instructions
├── backend/              # FastAPI service
│   ├── server/           # Routers (menu, orders) & global error handlers
│   ├── services/         # Business‑logic modules (menu_service, order_service)
│   └── settings/         # Configuration (Pydantic models for env vars, DB URL, etc.)
├── bot/                  # Aiogram 3 Telegram‑bot code
│   ├── handlers/         # Command and callback query handlers
│   └── keyboards/        # Inline and reply keyboard definitions
└── frontend/             # React + TypeScript Web App (Telegram Mini‑App)
    ├── src/              # Application code: pages, components, API client, theme
    └── public/           # Static assets (HTML template, favicon, etc.)
```

## 🚀 Quick Start

### 1. Clone Repo

```bash
git clone https://github.com/uselessBit/shawa-bear-tg-mini-app.git
cd shawa-bear-tg-mini-app
```

### 2. Environment Variables

Create a .env at project root:

```bash
API_TOKEN=your_telegram_bot_token
BACKEND_HOST=http://backend:8000
DB_HOST=db
DB_PORT=5432
DB_NAME=rent
DB_USER=admin
DB_PASSWORD=strong-password
```

### 3. Launch with Docker

```bash
docker compose up --build
```

All services (API, Bot, Postgres) will start automatically.
Postgres data is stored in the named Docker volume `postgres_data_dev`, so it survives container recreation.

### 4. (Optional) Front-End Dev Mode

```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:5173 and configure your bot’s Web App URL to this address.
