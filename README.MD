# Telegram Circles Ranking Bot (Video Notes + Reactions)

A Telegram group/supergroup bot that:
- awards points for **video circles** (`video_note`);
- awards points for **reactions** on those circles (idempotent via `reactions_log`);
- publishes **Top** every N minutes **only if new circles appeared** since last publish;
- after publishing, mentions “zero” users (by `points<=0` or `circles==0`) in a friendly game style.

## Features
- ✅ Circle scoring: `POINTS_PER_CIRCLE`
- ✅ Reaction scoring: `POINTS_PER_REACTION`
- ✅ Idempotent reaction accounting (add/remove/replace)
- ✅ Commands: `/top`, `/me`, `/rules`
- ✅ Scheduler: every `RATING_INTERVAL_SEC`, only posts if `last_circle_ts > last_rating_ts`
- ✅ Storage: SQLite (default), repository interface allows swapping to PostgreSQL later
- ✅ Storage: SQLite (default) and PostgreSQL (via `DB_URL`) with automatic selection

---

## Requirements
- Python **3.10+** (recommended 3.12)
- [uv](https://github.com/astral-sh/uv) - Modern Python package manager
- A Telegram bot token from **@BotFather**
- The bot must be added to a **Group/Supergroup** and made **Admin** (required to receive reaction updates)
- PostgreSQL is optional for production use when `DB_URL` points to a Postgres server

---

## Modern Development Setup

This project uses **uv** for fast, reliable Python package management and virtual environment handling.

### Installation
```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup project
git clone <repository-url>
cd freestyle-challenge

# Install all dependencies (creates virtual environment automatically)
uv sync
```

### Running the Bot
```bash
# Start the bot (automatically loads .env)
uv run python -m app.main

# Stop with Ctrl+C
```

### Development Commands
```bash
# Add new dependency
uv add package-name

# Update all dependencies
uv sync --upgrade

# Rebuild from scratch
uv sync --reinstall

# Run tests (when implemented)
uv run pytest

# Run with different Python version
uv sync --python 3.11
```

---

## Project structure

repo/
	app/
		bot/
			handlers.py
			scheduler.py
			formatting.py
		core/
			config.py
			scoring.py
			models.py
		storage/
			repo.py
			sqlite_repo.py
			pg_repo.py
			migrations.sql
	pyproject.toml
	uv.lock
	.env.example
	README.md

---

## Setup (local run)

### 1) Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

Dependencies are managed with [uv](https://github.com/astral-sh/uv) and `pyproject.toml`:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

**Note**: uv automatically creates and manages the virtual environment for you.

### 3) Create .env
Copy example:
cp .env.example .env
.env.example (repo root):

BOT_TOKEN=PUT_YOUR_TOKEN_HERE
# For SQLite (default):
DB_URL=sqlite:///data/bot.db
# For PostgreSQL (example):
# DB_URL=postgresql://postgres:password@localhost:5432/freestyle_bot

POINTS_PER_CIRCLE=1
POINTS_PER_REACTION=1
RATING_INTERVAL_SEC=1200

ZERO_CRITERIA=points
ZERO_PING_LIMIT=10
TOP_LIMIT=10

LOG_LEVEL=INFO

### 4) Ensure data/ exists

mkdir -p data

### 5) Run the bot (polling)

```bash
# With uv (recommended - automatically loads .env)
uv run python -m app.main

# Or with traditional Python
source .venv/bin/activate
set -a && source .env && set +a
python -m app.main
```


⸻

## Telegram setup checklist
	1.	Add the bot to your group/supergroup.
	2.	Promote bot to Admin.
	3.	In the group:
		•	send a video note (circle) → author should gain points
		•	react to that circle → author should gain points
		•	remove reaction → author should lose points
		•	replace emoji reaction → net points should stay same

## Commands in group:
	•	/top → top users (points/circles/reactions)
	•	/me → your stats
	•	/rules → current config values
	•	/enable_ratings (admins only)
	•	/disable_ratings (admins only)

⸻

## How scoring works

### Circles (video notes)

On each message with video_note:
	•	store (chat_id, message_id) -> author_id in circle_messages
	•	increment author:
	•	circles += 1
	•	points += POINTS_PER_CIRCLE
	•	update chat_state.last_circle_ts

### Reactions

On each reaction update:
	•	only applies if the message is a tracked circle
	•	compare old vs new reactions for that reactor:
	•	added emoji → insert into reactions_log → +POINTS_PER_REACTION
	•	removed emoji → delete from reactions_log → -POINTS_PER_REACTION
	•	replacement becomes -1 +1 = 0 automatically by delta logic

⸻

## Scheduler behavior

Every RATING_INTERVAL_SEC:
	•	for each chat in chat_state:
	•	if last_circle_ts > last_rating_ts: publish rating + zero pings, then update last_rating_ts
	•	otherwise: do nothing (anti-spam)

⸻

## Troubleshooting

Bot doesn’t receive reactions
	•	Make sure bot is Admin in the group.
	•	Reactions are received via message_reaction updates; polling must include allowed_updates.
	•	Some groups may restrict reactions or have unusual settings; test in a clean group.

/top shows empty
	•	You need at least one circle message to create user rows and stats.

DB issues
	•	Delete data/bot.db to reset:

rm -f data/bot.db

Then rerun; schema will be created automatically from app/storage/migrations.sql.

---

## Advanced Troubleshooting

### Environment & Dependencies
```bash
# Check if BOT_TOKEN is loaded
uv run python -c "import os; print('BOT_TOKEN:', 'SET' if os.getenv('BOT_TOKEN') else 'MISSING')"

# Test Telegram API connection
uv run python -c "from telegram import Bot; import asyncio; asyncio.run(Bot(os.getenv('BOT_TOKEN')).get_me())"

# Clear cache and reinstall dependencies
uv cache clean
uv sync --reinstall

# Check installed packages
uv pip list
```

### Database Issues
```bash
# Test SQLite connection
uv run python -c "import sqlite3; sqlite3.connect('data/test.db').close(); print('SQLite OK')"

# Test PostgreSQL connection (if using)
uv run python -c "import psycopg; psycopg.connect(os.getenv('DB_URL')).close(); print('PostgreSQL OK')"

# Reset database
rm -f data/bot.db
```

### Permission & Telegram Issues
- Ensure the bot is **Administrator** in your Telegram group
- Check that `ADMIN_CHAT_ID` is set correctly for startup messages
- Verify bot has permission to send messages and reactions

---

## Recent Improvements

### v1.1 - Modern Python Tooling (January 2026)
- ✅ **Migrated to uv**: Fast, reliable package management replacing pip
- ✅ **pyproject.toml**: Modern dependency management with reproducible builds
- ✅ **Automatic .env loading**: Added python-dotenv for seamless configuration
- ✅ **Updated Dockerfile**: Uses uv for faster container builds
- ✅ **Cleanup**: Removed legacy files (requirements.txt, old scripts)
- ✅ **Enhanced documentation**: Comprehensive setup and troubleshooting guides

### Planned Features
- 🌟 **Bot Mechanic V1**: Themed messages with images and AI-generated content
- 🌍 **Multi-language Support**: Russian/English localization system
- 📊 **Enhanced Analytics**: Better tracking and reporting features

---

## Optional: Docker run
Dockerfile (repo root)
```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies using uv
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "-m", "app.main"]
```

docker-compose.yml (repo root)

services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped

Run:

docker compose up --build


⸻

## Notes
 	•	Storage: the app supports SQLite by default and PostgreSQL via `DB_URL` (the code includes `pg_repo.py`).
 	•	When `DB_URL` points to Postgres the `PostgresRepository` implementation (requires `psycopg`) is used automatically.
