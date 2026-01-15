from __future__ import annotations

from typing import Sequence, Optional, Literal
from html import escape

from app.core.models import TopRow, UserStats
from app.bot.messages import (
    get_message,
    MSG_TOP_EMPTY,
    MSG_TOP_HEADER,
    MSG_TOP_ROW,
    MSG_ZERO_PING,
    MSG_ZERO_POINTS,
    MSG_ZERO_CIRCLES,
)

SupportedLocale = Literal["en", "ru"]


def format_user_label(display_name: str, username: Optional[str]) -> str:
    if username:
        return f"{escape(display_name)} (@{escape(username)})"
    return escape(display_name)


def format_top_message(rows: Sequence[TopRow], locale: SupportedLocale = "en") -> str:
    """
    Format top users leaderboard message.

    Args:
        rows: Sequence of TopRow objects
        locale: Language code ('en' or 'ru'). Defaults to 'en'

    Returns:
        Formatted HTML message string
    """
    if not rows:
        return get_message(MSG_TOP_EMPTY, locale=locale)

    lines = [get_message(MSG_TOP_HEADER, locale=locale)]
    for r in rows:
        label = format_user_label(r.display_name, r.username)
        text = get_message(
            MSG_TOP_ROW,
            locale=locale,
            rank=r.rank,
            label=label,
            points=r.points,
            circles=r.circles,
            reactions=r.reactions,
        )
        lines.append(text)
    return "\n".join(lines)


def mention_user(user_id: int, display_name: str) -> str:
    # tg://user?id=... works in HTML parse_mode
    return f'<a href="tg://user?id={user_id}">{escape(display_name)}</a>'


def format_zero_ping_message(zero_users: Sequence[UserStats], criteria: str, locale: SupportedLocale = "en") -> Optional[str]:
    """
    Format zero ping message for users with zero points or circles.

    Args:
        zero_users: Sequence of UserStats for users with zero points/circles
        criteria: Criteria type ('points' or 'circles')
        locale: Language code ('en' or 'ru'). Defaults to 'en'

    Returns:
        Formatted HTML message string, or None if no zero users
    """
    if not zero_users:
        return None

    if criteria == "points":
        reason = get_message(MSG_ZERO_POINTS, locale=locale)
    else:
        reason = get_message(MSG_ZERO_CIRCLES, locale=locale)

    mentions = ", ".join([mention_user(u.user_id, u.display_name) for u in zero_users])
    return get_message(
        MSG_ZERO_PING,
        locale=locale,
        reason=reason,
        mentions=mentions,
    )
