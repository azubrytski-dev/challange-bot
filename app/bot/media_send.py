from __future__ import annotations

from telegram import InputFile
from telegram.ext import ExtBot

from app.bot.media_assets import asset_path


async def send_themed_photo(
    *,
    bot: ExtBot,
    chat_id: int,
    asset_key: str,
    caption: str,
    parse_mode: str | None,
) -> None:
    path = asset_path(asset_key)
    with path.open("rb") as f:
        await bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(f),
            caption=caption,
            parse_mode=parse_mode,
        )