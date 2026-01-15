from __future__ import annotations

from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    bot_token: str

    db_url: str = "sqlite:///data/bot.db"

    points_per_circle: int = 1
    points_per_reaction: int = 1

    rating_interval_sec: int = 1200

    zero_ping_limit: int = 10
    zero_criteria: str = "points"  # "points" | "circles"

    top_limit: int = 10

    allowed_updates: tuple[str, ...] = (
        "message",
        "message_reaction",
        "message_reaction_count",
        "my_chat_member",
    )

    parse_mode: str = "HTML"

    admin_chat_id: int = 0  # Optional: set to send greeting to this chat on startup

    @staticmethod
    def from_env() -> "AppConfig":
        load_dotenv()  # Load .env file
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required.")

        def _int(name: str, default: int) -> int:
            raw = os.getenv(name, str(default)).strip()
            try:
                return int(raw)
            except ValueError as ex:
                raise RuntimeError(f"{name} must be int. Got '{raw}'.") from ex

        zero_criteria = os.getenv("ZERO_CRITERIA", "points").strip().lower()
        if zero_criteria not in ("points", "circles"):
            raise RuntimeError("ZERO_CRITERIA must be 'points' or 'circles'.")

        return AppConfig(
            bot_token=bot_token,
            db_url=os.getenv("DB_URL", "sqlite:///data/bot.db").strip(),
            points_per_circle=_int("POINTS_PER_CIRCLE", 1),
            points_per_reaction=_int("POINTS_PER_REACTION", 1),
            rating_interval_sec=_int("RATING_INTERVAL_SEC", 1200),
            zero_ping_limit=_int("ZERO_PING_LIMIT", 10),
            zero_criteria=zero_criteria,
            top_limit=_int("TOP_LIMIT", 10),
            admin_chat_id=_int("ADMIN_CHAT_ID", 0),
        )
