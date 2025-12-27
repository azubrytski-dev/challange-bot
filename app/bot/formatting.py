from __future__ import annotations

from typing import Sequence, Optional
from html import escape

from app.core.models import TopRow, UserStats


def format_user_label(display_name: str, username: Optional[str]) -> str:
    if username:
        return f"{escape(display_name)} (@{escape(username)})"
    return escape(display_name)


def format_top_message(rows: Sequence[TopRow]) -> str:
    if not rows:
        return "No stats yet. Record a circle (video note) to start the game 🎤"

    lines = ["🏆 <b>Top</b>"]
    for r in rows:
        label = format_user_label(r.display_name, r.username)
        lines.append(f"{r.rank}. {label} — <b>{r.points}</b> pts · 🎥 {r.circles} · ❤️ {r.reactions}")
    return "\n".join(lines)


def mention_user(user_id: int, display_name: str) -> str:
    # tg://user?id=... works in HTML parse_mode
    return f'<a href="tg://user?id={user_id}">{escape(display_name)}</a>'


def format_zero_ping_message(zero_users: Sequence[UserStats], criteria: str) -> Optional[str]:
    if not zero_users:
        return None

    if criteria == "points":
        reason = "0 points"
    else:
        reason = "0 circles"

    mentions = ", ".join([mention_user(u.user_id, u.display_name) for u in zero_users])
    return (
        f"🎮 <b>Side quest</b>: we need you on the board!\n"
        f"Condition: <b>{escape(reason)}</b>\n"
        f"Players: {mentions}\n"
        f"Drop a circle and farm points 😄"
    )
