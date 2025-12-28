from __future__ import annotations

import asyncio
import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    MessageReactionHandler,
    filters,
)

from app.core.config import AppConfig
from app.storage.sqlite_repo import SQLiteRepository
from app.storage.pg_repo import PostgresRepository
from app.bot.handlers import cmd_top, cmd_me, cmd_rules, on_message, on_reaction, cmd_enable_ratings, cmd_disable_ratings, send_greeting
from app.bot.scheduler import publish_rating_job


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _sqlite_path_from_db_url(db_url: str) -> str:
    # Expected: sqlite:///data/bot.db
    if not db_url.startswith("sqlite:///"):
        raise RuntimeError("Only sqlite:///... is supported in this version.")
    return db_url.replace("sqlite:///", "", 1)


def _is_postgres(db_url: str) -> bool:
    """Check if DB_URL is a PostgreSQL connection string."""
    return db_url.startswith("postgresql://") or db_url.startswith("postgres://")


def _build_repo(cfg: AppConfig):
    """Build the appropriate repository based on DB_URL."""
    if _is_postgres(cfg.db_url):
        logger.info("Using PostgreSQL repository: %s", cfg.db_url)
        return PostgresRepository(
            dsn=cfg.db_url,
            migrations_sql_path="app/storage/mg_postgre_init.sql",
        )

    # Default to SQLite
    logger.info("Using SQLite repository: %s", cfg.db_url)
    db_path = _sqlite_path_from_db_url(cfg.db_url)
    return SQLiteRepository(db_path=db_path, migrations_sql_path="app/storage/mg_sqllite_init.sql")


async def _post_init(app: Application, *, repo: SQLiteRepository, cfg: AppConfig) -> None:
    # Send greeting message on startup
    await send_greeting(app, cfg)

    # Schedule periodic rating publishing using PTB JobQueue (no create_task warning)
    app.job_queue.run_repeating(
        callback=publish_rating_job,
        interval=cfg.rating_interval_sec,
        first=cfg.rating_interval_sec,
        data={"repo": repo, "cfg": cfg},
        name="rating_scheduler",
    )
    logger.info("Scheduler started. Interval=%s sec", cfg.rating_interval_sec)


def build_app(*, cfg: AppConfig) -> Application:
    repo = _build_repo(cfg)

    application = Application.builder().token(cfg.bot_token).build()

    # Commands
    application.add_handler(CommandHandler("top", lambda u, c: cmd_top(u, c, repo=repo, cfg=cfg)))
    application.add_handler(CommandHandler("me", lambda u, c: cmd_me(u, c, repo=repo, cfg=cfg)))
    application.add_handler(CommandHandler("rules", lambda u, c: cmd_rules(u, c, cfg=cfg)))
    application.add_handler(CommandHandler("enable_ratings", lambda u, c: cmd_enable_ratings(u, c, repo=repo, cfg=cfg)))
    application.add_handler(CommandHandler("disable_ratings", lambda u, c: cmd_disable_ratings(u, c, repo=repo, cfg=cfg)))

    # Circle messages (video_note)
    application.add_handler(
        MessageHandler(filters.VIDEO_NOTE & filters.ChatType.GROUPS, lambda u, c: on_message(u, c, repo=repo, cfg=cfg))
    )

    # Reaction updates
    application.add_handler(
        MessageReactionHandler(lambda u, c: on_reaction(u, c, repo=repo, cfg=cfg))
    )

    application.post_init = lambda app: _post_init(app, repo=repo, cfg=cfg)

    return application


def main() -> None:
    cfg = AppConfig.from_env()

    # Reduce verbosity for noisy third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Replace root handlers with one that redacts the bot token from output
    class RedactingFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            msg = super().format(record)
            try:
                return msg.replace(cfg.bot_token, "<BOT_TOKEN_REDACTED>")
            except Exception:
                return msg

    root = logging.getLogger()
    # remove existing handlers created by basicConfig
    for h in list(root.handlers):
        root.removeHandler(h)

    stream_h = logging.StreamHandler()
    stream_h.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
    root.addHandler(stream_h)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    app = build_app(cfg=cfg)

    # Polling mode
    app.run_polling(
        allowed_updates=list(cfg.allowed_updates),
        close_loop=False,
    )


if __name__ == "__main__":
    main()
