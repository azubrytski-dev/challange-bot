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
from app.bot.handlers import cmd_top, cmd_me, cmd_rules, on_message, on_reaction
from app.bot.scheduler import rating_scheduler_loop


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


async def _post_init(app: Application, *, repo: SQLiteRepository, cfg: AppConfig) -> None:
    # start scheduler task
    app.create_task(rating_scheduler_loop(app=app, repo=repo, cfg=cfg))
    logger.info("Scheduler started. Interval=%s sec", cfg.rating_interval_sec)


def build_app(*, cfg: AppConfig) -> Application:
    db_path = _sqlite_path_from_db_url(cfg.db_url)
    repo = SQLiteRepository(db_path=db_path, migrations_sql_path="app/storage/migrations.sql")

    application = Application.builder().token(cfg.bot_token).build()

    # Commands
    application.add_handler(CommandHandler("top", lambda u, c: cmd_top(u, c, repo=repo, cfg=cfg)))
    application.add_handler(CommandHandler("me", lambda u, c: cmd_me(u, c, repo=repo, cfg=cfg)))
    application.add_handler(CommandHandler("rules", lambda u, c: cmd_rules(u, c, cfg=cfg)))

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
    app = build_app(cfg=cfg)

    # Polling mode
    app.run_polling(
        allowed_updates=list(cfg.allowed_updates),
        close_loop=False,
    )


if __name__ == "__main__":
    main()
