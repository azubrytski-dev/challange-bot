from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

GREETING_IMG_NAME = "greeting.png"
RATING_IMG_NAME = "rating.png"
ME_IMG_NAME = "me.png"
INFO_EVENT_IMG_NAME = "info_event.png"
INFO_SCHEDULED_IMG_NAME = "info_scheduled.png"

ASSET_BY_KEY: dict[str, str] = {
    "greeting": GREETING_IMG_NAME,
    "rating": RATING_IMG_NAME,
    "me": ME_IMG_NAME,
    "info_event": INFO_EVENT_IMG_NAME,
    "info_scheduled": INFO_SCHEDULED_IMG_NAME,
}


def asset_path(asset_key: str) -> Path:
    filename = ASSET_BY_KEY[asset_key]
    path = ASSETS_DIR / filename
    if not path.exists():
        # Fallback to greeting image if requested asset doesn't exist
        fallback_filename = ASSET_BY_KEY["greeting"]
        fallback_path = ASSETS_DIR / fallback_filename
        if fallback_path.exists():
            return fallback_path
        else:
            raise FileNotFoundError(f"Asset not found: {path} and fallback greeting asset also missing")
    return path