from __future__ import annotations

import logging
from typing import Optional, List

from telegram import Update, User
from telegram.ext import ContextTypes
from telegram.constants import ChatType
from telegram.error import TelegramError

from app.core.config import AppConfig
from app.core.models import UserIdentity, CircleMessage
from app.core.scoring import compute_reaction_delta
from app.storage.repo import Repository
from app.bot.formatting import format_top_message

logger = logging.getLogger(__name__)


def _display_name(u: User) -> str:
    name = (u.full_name or "").strip()
    return name if name else (u.first_name or "User")


def _emoji_key(reaction_obj) -> str:
    """
    PTB reaction objects:
      - ReactionTypeEmoji: has .emoji
      - ReactionTypeCustomEmoji: has .custom_emoji_id
    We normalize to:
      - unicode emoji -> "🔥"
      - custom -> "custom:<id>"
    """
    # None -> unknown
    if reaction_obj is None:
        return "unknown"

    # If the update already gives us a plain string (common), use it directly
    if isinstance(reaction_obj, str):
        return reaction_obj

    # Try known PTB object attributes
    emoji = getattr(reaction_obj, "emoji", None)
    if emoji:
        return str(emoji)

    custom_id = getattr(reaction_obj, "custom_emoji_id", None)
    if custom_id:
        return f"custom:{custom_id}"

    # Fallback to string conversion (best-effort)
    try:
        return str(reaction_obj)
    except Exception:
        return "unknown"


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    repo.ensure_chat_state(chat_id=chat_id)

    rows = repo.get_top(chat_id=chat_id, limit=cfg.top_limit)
    text = format_top_message(rows)
    await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    if not update.effective_chat or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user

    stats = repo.get_user_stats(chat_id=chat_id, user_id=user.id)
    if not stats:
        await update.effective_message.reply_text(
            "No stats yet. Record a circle (video note) to join 🎤",
            parse_mode=cfg.parse_mode,
        )
        return

    label = stats.display_name + (f" (@{stats.username})" if stats.username else "")
    text = (
        f"👤 <b>{label}</b>\n"
        f"Points: <b>{stats.points}</b>\n"
        f"Circles: 🎥 {stats.circles}\n"
        f"Reactions: ❤️ {stats.reactions}"
    )
    await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE, *, cfg: AppConfig) -> None:
    text = (
        "📜 <b>Rules</b>\n"
        f"Circle (video note): +{cfg.points_per_circle} point(s)\n"
        f"Reaction on a circle: +{cfg.points_per_reaction} point(s)\n"
        f"Auto rating interval: {cfg.rating_interval_sec} sec\n"
        f"Zero criteria: {cfg.zero_criteria}\n"
        f"Zero ping limit: {cfg.zero_ping_limit}\n"
        f"Top limit: {cfg.top_limit}"
    )
    await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False


async def cmd_enable_ratings(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    if not await _is_admin(update, context):
        await update.effective_message.reply_text("Admins only.", parse_mode=cfg.parse_mode)
        return

    chat_id = update.effective_chat.id
    repo.set_ratings_enabled(chat_id=chat_id, enabled=True)
    await update.effective_message.reply_text("✅ Auto рейтинги включены.", parse_mode=cfg.parse_mode)


async def cmd_disable_ratings(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    if not await _is_admin(update, context):
        await update.effective_message.reply_text("Admins only.", parse_mode=cfg.parse_mode)
        return

    chat_id = update.effective_chat.id
    repo.set_ratings_enabled(chat_id=chat_id, enabled=False)
    await update.effective_message.reply_text("🛑 Auto рейтинги выключены.", parse_mode=cfg.parse_mode)


async def send_greeting(app, cfg: AppConfig) -> None:
    """Send a greeting message to admin chat on application startup."""
    if not cfg.admin_chat_id:
        logger.info("✅ Application started. (No ADMIN_CHAT_ID configured.)")
        return

    try:
        greeting_text = (
            "🤖 <b>Circles Ranking Bot</b>\n"
            "✅ Application started successfully!\n\n"
            "📝 Available commands:\n"
            "  /top — top users\n"
            "  /me — your stats\n"
            "  /rules — config & rules\n"
            "  /enable_ratings — start auto ratings (admins)\n"
            "  /disable_ratings — stop auto ratings (admins)"
        )
        await app.bot.send_message(chat_id=cfg.admin_chat_id, text=greeting_text, parse_mode=cfg.parse_mode)
        logger.info("✅ Application started. Greeting sent to admin chat %s.", cfg.admin_chat_id)
    except Exception as e:
        logger.warning("Failed to send greeting to admin chat %s: %s", cfg.admin_chat_id, e)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    """
    Handles circles (video_note).
    """
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user:
        return

    # Only groups/supergroups (optional hard rule)
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if msg.video_note is None:
        return

    repo.ensure_chat_state(chat_id=chat.id)

    identity = UserIdentity(
        chat_id=chat.id,
        user_id=user.id,
        username=user.username,
        display_name=_display_name(user),
    )
    repo.upsert_user(identity)
    logger.info("User upserted: chat=%s user=%s (%s)", chat.id, user.id, _display_name(user))

    created_ts = int(msg.date.timestamp()) if msg.date else 0
    circle = CircleMessage(
        chat_id=chat.id,
        message_id=msg.message_id,
        author_id=user.id,
        created_at_ts=created_ts,
    )

    is_new_circle = repo.insert_circle_message(circle)
    
    # Get or verify the circle author (in case message was already processed)
    author_id = repo.try_get_circle_author_id(chat_id=chat.id, message_id=msg.message_id)
    if author_id is None:
        logger.error("Circle not found in DB: chat=%s msg=%s", chat.id, msg.message_id)
        return

    # Verify user was inserted before adding points
    user_stats = repo.get_user_stats(chat_id=chat.id, user_id=author_id)
    if not user_stats:
        logger.error("Author not found after upsert! chat=%s user=%s. Cannot add points.", chat.id, author_id)
        return

    # Only add points if this is a NEW circle (idempotent)
    if is_new_circle:
        repo.add_circle_points(chat_id=chat.id, user_id=author_id, points=cfg.points_per_circle)
        logger.info("Circle points added: chat=%s user=%s points=%s (total points now: %s)", 
                    chat.id, author_id, cfg.points_per_circle, user_stats.points + cfg.points_per_circle)
        repo.set_last_circle_ts(chat_id=chat.id, ts=created_ts)
        logger.info("Circle recorded chat=%s msg=%s author=%s", chat.id, msg.message_id, author_id)
    else:
        logger.info("Circle already processed: chat=%s msg=%s author=%s (no points added)", chat.id, msg.message_id, author_id)


async def on_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    """
    Handles reaction updates on circle messages using reactions_log for idempotency.
    """
    mr = update.message_reaction
    if not mr:
        return

    chat = mr.chat
    if not chat:
        return

    chat_id = chat.id
    message_id = mr.message_id

    repo.ensure_chat_state(chat_id=chat_id)

    author_id = repo.try_get_circle_author_id(chat_id=chat_id, message_id=message_id)
    if author_id is None:
        return  # not a circle message we track

    reactor = mr.user
    if not reactor:
        return

    # Normalize reaction sets
    old_set: List[str] = [_emoji_key(x.type) for x in (mr.old_reaction or [])]
    new_set: List[str] = [_emoji_key(x.type) for x in (mr.new_reaction or [])]

    delta = compute_reaction_delta(old_set=old_set, new_set=new_set)

    # Ensure author exists in users (can be missing if DB was reset mid-chat)
    # We cannot reliably fetch author identity here from update, so just ensure row exists if present.
    # (If missing, points update will affect 0 rows; acceptable, but you can add a "create placeholder" policy.)
    logger.info(
        "on_reaction: Processing deltas: added=%s removed=%s for author=%s",
        list(delta.added), list(delta.removed), author_id,
    )

    for emoji in delta.added:
        logger.info("on_reaction: Attempting to insert reaction: chat=%s msg=%s reactor=%s emoji=%s", chat_id, message_id, reactor.id, emoji)
        inserted = repo.try_insert_reaction(chat_id=chat_id, message_id=message_id, reactor_id=reactor.id, emoji=emoji)
        logger.info("on_reaction: Insertion result: inserted=%s", inserted)
        if inserted:
            logger.info("on_reaction: Adding points for added reaction: chat=%s author=%s points=%s", chat_id, author_id, cfg.points_per_reaction)
            repo.add_reaction_points(chat_id=chat_id, user_id=author_id, points=cfg.points_per_reaction)
        else:
            logger.info("on_reaction: Reaction already existed, skipping points")

    for emoji in delta.removed:
        logger.info("on_reaction: Attempting to delete reaction: chat=%s msg=%s reactor=%s emoji=%s", chat_id, message_id, reactor.id, emoji)
        deleted = repo.try_delete_reaction(chat_id=chat_id, message_id=message_id, reactor_id=reactor.id, emoji=emoji)
        logger.info("on_reaction: Deletion result: deleted=%s", deleted)
        if deleted:
            logger.info("on_reaction: Removing points for removed reaction: chat=%s author=%s points=%s", chat_id, author_id, -cfg.points_per_reaction)
            repo.add_reaction_points(chat_id=chat_id, user_id=author_id, points=-cfg.points_per_reaction)
        else:
            logger.info("on_reaction: Reaction didn't exist, skipping points removal")
