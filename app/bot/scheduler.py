from __future__ import annotations

import asyncio
import logging
import time

from telegram.ext import Application, ContextTypes

from app.core.config import AppConfig
from app.storage.repo import Repository
from app.bot.formatting import format_top_message, format_zero_ping_message

logger = logging.getLogger(__name__)


async def publish_rating_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    app = context.application
    repo = context.job.data["repo"]
    cfg = context.job.data["cfg"]

    now_ts = int(time.time())

    chat_ids = repo.list_active_chats()
    for chat_id in chat_ids:
        st = repo.get_chat_state(chat_id=chat_id)
        if not getattr(st, "ratings_enabled", True):
            continue
        if st.last_circle_ts <= st.last_rating_ts:
            continue

        top = repo.get_top(chat_id=chat_id, limit=cfg.top_limit)
        rating_text = format_top_message(top)
        await app.bot.send_message(chat_id=chat_id, text=rating_text, parse_mode=cfg.parse_mode)

        zero_users = repo.get_zero_users(chat_id=chat_id, criteria=cfg.zero_criteria, limit=cfg.zero_ping_limit)
        zero_text = format_zero_ping_message(zero_users, criteria=cfg.zero_criteria)
        if zero_text:
            await app.bot.send_message(chat_id=chat_id, text=zero_text, parse_mode=cfg.parse_mode)

        repo.set_last_rating_ts(chat_id=chat_id, ts=now_ts)


async def rating_scheduler_loop(*, app: Application, repo: Repository, cfg: AppConfig) -> None:
    """
    Every cfg.rating_interval_sec:
      - for each active chat:
          if last_circle_ts > last_rating_ts:
             publish /top-like rating
             publish zero ping message (optional)
             set last_rating_ts = now
    """
    while True:
        try:
            await asyncio.sleep(cfg.rating_interval_sec)
            now_ts = int(time.time())

            chat_ids = repo.list_active_chats()
            for chat_id in chat_ids:
                st = repo.get_chat_state(chat_id=chat_id)
                if not getattr(st, "ratings_enabled", True):
                    continue
                if st.last_circle_ts <= st.last_rating_ts:
                    continue

                top = repo.get_top(chat_id=chat_id, limit=cfg.top_limit)
                rating_text = format_top_message(top)
                await app.bot.send_message(chat_id=chat_id, text=rating_text, parse_mode=cfg.parse_mode)

                zero_users = repo.get_zero_users(chat_id=chat_id, criteria=cfg.zero_criteria, limit=cfg.zero_ping_limit)
                zero_text = format_zero_ping_message(zero_users, criteria=cfg.zero_criteria)
                if zero_text:
                    await app.bot.send_message(chat_id=chat_id, text=zero_text, parse_mode=cfg.parse_mode)

                repo.set_last_rating_ts(chat_id=chat_id, ts=now_ts)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler loop failure")
