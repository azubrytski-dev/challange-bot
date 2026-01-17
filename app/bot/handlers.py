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
from app.bot.media_send import send_themed_photo
from app.bot.messages import (
    get_message,
    MSG_NO_STATS,
    MSG_USER_STATS,
    MSG_RULES,
    MSG_ADMINS_ONLY,
    MSG_RATINGS_ENABLED,
    MSG_RATINGS_DISABLED,
    MSG_GREETING,
    MSG_LANG_CHANGED,
    MSG_LANG_INVALID,
)

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
    """Display top users leaderboard."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    repo.ensure_chat_state(chat_id=chat_id)

    locale = repo.get_chat_language(chat_id=chat_id)
    rows = repo.get_top(chat_id=chat_id, limit=cfg.top_limit)
    text = format_top_message(rows, locale=locale)
    await send_themed_photo(
        bot=context.bot,
        chat_id=chat_id,
        asset_key="rating",
        caption=text,
        parse_mode=cfg.parse_mode,
    )


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    """Display user's own statistics."""
    if not update.effective_chat or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user

    locale = repo.get_chat_language(chat_id=chat_id)
    stats = repo.get_user_stats(chat_id=chat_id, user_id=user.id)
    if not stats:
        text = get_message(MSG_NO_STATS, locale=locale)
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)
        return

    label = stats.display_name + (f" (@{stats.username})" if stats.username else "")
    text = get_message(
        MSG_USER_STATS,
        locale=locale,
        label=label,
        points=stats.points,
        circles=stats.circles,
        reactions=stats.reactions,
    )
    await send_themed_photo(
        bot=context.bot,
        chat_id=chat_id,
        asset_key="me",
        caption=text,
        parse_mode=cfg.parse_mode,
    )


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    """Display bot rules and configuration."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    locale = repo.get_chat_language(chat_id=chat_id)
    text = get_message(
        MSG_RULES,
        locale=locale,
        points_per_circle=cfg.points_per_circle,
        points_per_reaction=cfg.points_per_reaction,
        rating_interval_sec=cfg.rating_interval_sec,
        zero_criteria=cfg.zero_criteria,
        zero_ping_limit=cfg.zero_ping_limit,
        top_limit=cfg.top_limit,
    )
    await send_themed_photo(
        bot=context.bot,
        chat_id=chat_id,
        asset_key="info_event",
        caption=text,
        parse_mode=cfg.parse_mode,
    )


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
    """Enable auto ratings (admin only)."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    locale = repo.get_chat_language(chat_id=chat_id)

    if not await _is_admin(update, context):
        text = get_message(MSG_ADMINS_ONLY, locale=locale)
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)
        return

    repo.set_ratings_enabled(chat_id=chat_id, enabled=True)
    text = get_message(MSG_RATINGS_ENABLED, locale=locale)
    await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)


async def cmd_disable_ratings(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    """Disable auto ratings (admin only)."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    locale = repo.get_chat_language(chat_id=chat_id)

    if not await _is_admin(update, context):
        text = get_message(MSG_ADMINS_ONLY, locale=locale)
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)
        return

    chat_id = update.effective_chat.id
    repo.set_ratings_enabled(chat_id=chat_id, enabled=False)
    text = get_message(MSG_RATINGS_DISABLED, locale=locale)
    await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)


async def send_greeting(app, cfg: AppConfig, *, repo: Repository) -> None:
    """Send a greeting message to admin chat on application startup."""
    if not cfg.admin_chat_id:
        logger.info("✅ Application started. (No ADMIN_CHAT_ID configured.)")
        return

    try:
        # Use English for admin greeting (or get from admin chat if it exists)
        locale = "en"
        if cfg.admin_chat_id:
            try:
                locale = repo.get_chat_language(chat_id=cfg.admin_chat_id)
            except Exception:
                pass  # Fallback to English if chat doesn't exist yet

        greeting_text = get_message(MSG_GREETING, locale=locale)
        await send_themed_photo(
            bot=app.bot,
            chat_id=cfg.admin_chat_id,
            asset_key="greeting",
            caption=greeting_text,
            parse_mode=cfg.parse_mode,
        )
        logger.info("✅ Application started. Greeting sent to admin chat %s.", cfg.admin_chat_id)
    except Exception as e:
        logger.warning("Failed to send greeting to admin chat %s: %s", cfg.admin_chat_id, e)


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE, *, repo: Repository, cfg: AppConfig) -> None:
    """Set chat language preference."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    current_locale = repo.get_chat_language(chat_id=chat_id)

    # Get language code from command arguments
    if not context.args or len(context.args) == 0:
        # Show current language
        text = get_message(MSG_LANG_CHANGED, locale=current_locale, language=current_locale.upper())
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)
        return

    language_code = context.args[0].lower()
    if language_code not in ("en", "ru"):
        text = get_message(MSG_LANG_INVALID, locale=current_locale)
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)
        return

    try:
        repo.set_chat_language(chat_id=chat_id, language=language_code)
        # Use new language for success message
        text = get_message(MSG_LANG_CHANGED, locale=language_code, language=language_code.upper())
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)
    except ValueError as e:
        text = get_message(MSG_LANG_INVALID, locale=current_locale)
        await update.effective_message.reply_text(text=text, parse_mode=cfg.parse_mode)

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
