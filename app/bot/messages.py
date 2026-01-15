"""
Message localization service for bot messages.

Supports English ('en') and Russian ('ru') languages.
All messages are stored as templates with placeholders that are substituted at runtime.
"""

from __future__ import annotations

from typing import Literal, Final, Any

# Message type constants
MSG_NO_STATS: Final[str] = "no_stats"
MSG_USER_STATS: Final[str] = "user_stats"
MSG_RULES: Final[str] = "rules"
MSG_ADMINS_ONLY: Final[str] = "admins_only"
MSG_RATINGS_ENABLED: Final[str] = "ratings_enabled"
MSG_RATINGS_DISABLED: Final[str] = "ratings_disabled"
MSG_GREETING: Final[str] = "greeting"
MSG_TOP_EMPTY: Final[str] = "top_empty"
MSG_TOP_HEADER: Final[str] = "top_header"
MSG_TOP_ROW: Final[str] = "top_row"
MSG_ZERO_PING: Final[str] = "zero_ping"
MSG_ZERO_POINTS: Final[str] = "zero_points"
MSG_ZERO_CIRCLES: Final[str] = "zero_circles"
MSG_LANG_CHANGED: Final[str] = "lang_changed"
MSG_LANG_INVALID: Final[str] = "lang_invalid"

# Supported locales
SupportedLocale = Literal["en", "ru"]

# Translation dictionaries
_TRANSLATIONS: dict[SupportedLocale, dict[str, str]] = {
    "en": {
        MSG_NO_STATS: "No stats yet. Record a circle (video note) to join",
        MSG_USER_STATS: "<b>{label}</b>\nPoints: <b>{points}</b>\nCircles: {circles}\nReactions: {reactions}",
        MSG_RULES: "<b>Rules</b>\nCircle (video note): +{points_per_circle} point(s)\nReaction on a circle: +{points_per_reaction} point(s)\nAuto rating interval: {rating_interval_sec} sec\nZero criteria: {zero_criteria}\nZero ping limit: {zero_ping_limit}\nTop limit: {top_limit}",
        MSG_ADMINS_ONLY: "Admins only.",
        MSG_RATINGS_ENABLED: "Auto ratings enabled.",
        MSG_RATINGS_DISABLED: "Auto ratings disabled.",
        MSG_GREETING: "<b>Circles Ranking Bot</b>\nApplication started successfully!\n\nAvailable commands:\n  /top — top users\n  /me — your stats\n  /rules — config & rules\n  /enable_ratings — start auto ratings (admins)\n  /disable_ratings — stop auto ratings (admins)",
        MSG_TOP_EMPTY: "No stats yet. Record a circle (video note) to start the game",
        MSG_TOP_HEADER: "<b>Top</b>",
        MSG_TOP_ROW: "{rank}. {label} — <b>{points}</b> pts · {circles} · {reactions}",
        MSG_ZERO_PING: "<b>Side quest</b>: we need you on the board!\nCondition: <b>{reason}</b>\nPlayers: {mentions}\nDrop a circle and farm points",
        MSG_ZERO_POINTS: "0 points",
        MSG_ZERO_CIRCLES: "0 circles",
        MSG_LANG_CHANGED: "Language changed to {language}.",
        MSG_LANG_INVALID: "Invalid language code. Supported: en, ru",
    },
    "ru": {
        MSG_NO_STATS: "Пока нет статистики. Запишите круг (видеосообщение), чтобы присоединиться",
        MSG_USER_STATS: "<b>{label}</b>\Очки: <b>{points}</b>\Круги: {circles}\nРеакции: {reactions}",
        MSG_RULES: "<b>Правила</b>\nКруг (видеосообщение): +{points_per_circle} очко(ов)\nРеакция на круг: +{points_per_reaction} очко(ов)\nИнтервал авто-рейтинга: {rating_interval_sec} сек\nКритерий нуля: {zero_criteria}\nЛимит упоминаний нуля: {zero_ping_limit}\nЛимит топа: {top_limit}",
        MSG_ADMINS_ONLY: "Только для администраторов.",
        MSG_RATINGS_ENABLED: "Авто-рейтинги включены.",
        MSG_RATINGS_DISABLED: "Авто-рейтинги выключены.",
        MSG_GREETING: "<b>Бот Рейтинга Кругов</b>\nПриложение успешно запущено!\n\Доступные команды:\n  /top — топ пользователей\n  /me — ваша статистика\n  /rules — конфиг и правила\n  /enable_ratings — запустить авто-рейтинги (админы)\n  /disable_ratings — остановить авто-рейтинги (админы)",
        MSG_TOP_EMPTY: "Пока нет статистики. Запишите круг (видеосообщение), чтобы начать игру",
        MSG_TOP_HEADER: "<b>Топ</b>",
        MSG_TOP_ROW: "{rank}. {label} — <b>{points}</b> очков · {circles} · {reactions}",
        MSG_ZERO_PING: "<b>Побочный квест</b>: вы нам нужны на доске!\nУсловие: <b>{reason}</b>\nИгроки: {mentions}\nЗапишите круг и зарабатывайте очки",
        MSG_ZERO_POINTS: "0 очков",
        MSG_ZERO_CIRCLES: "0 кругов",
        MSG_LANG_CHANGED: "Язык изменён на {language}.",
        MSG_LANG_INVALID: "Неверный код языка. Поддерживаются: en, ru",
    },
}


def get_message(msg_type: str, locale: SupportedLocale = "en", **kwargs: Any) -> str:
    """
    Get a localized message by type and locale.

    Args:
        msg_type: Message type constant (e.g., MSG_NO_STATS)
        locale: Language code ('en' or 'ru'). Defaults to 'en'
        **kwargs: Placeholder values to substitute in the message template

    Returns:
        Localized message string with placeholders substituted

    Raises:
        KeyError: If msg_type is not found in translations
        ValueError: If locale is not supported (falls back to 'en' but logs warning)

    Example:
        >>> get_message(MSG_USER_STATS, "en", label="John", points=100, circles=5, reactions=10)
        '<b>John</b>\\nPoints: <b>100</b>\\nCircles: 5\\nReactions: 10'
    """
    # Fallback to English if locale not found
    if locale not in _TRANSLATIONS:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Unsupported locale: %s, falling back to 'en'", locale)
        locale = "en"

    # Get translations for locale
    translations = _TRANSLATIONS.get(locale, _TRANSLATIONS["en"])

    # Get message template
    if msg_type not in translations:
        raise KeyError(f"Message type '{msg_type}' not found in translations for locale '{locale}'")

    template = translations[msg_type]

    # Substitute placeholders
    try:
        return template.format(**kwargs)
    except KeyError as e:
        missing_key = str(e).strip("'")
        raise ValueError(f"Missing required placeholder '{missing_key}' for message type '{msg_type}'") from e
