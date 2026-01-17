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
        MSG_NO_STATS: "No numbers yet. Drop a circle (video note) and step into the cypher.",
        MSG_USER_STATS: "<b>{label}</b>\nPoints: <b>{points}</b>\nCircles: {circles}\nReactions: {reactions}",
        MSG_RULES: (
            "<b>House Rules</b>\n"
            "Rules are simple: drop circles, earn respect, climb the board.\n\n"
            "Circle (video note): +{points_per_circle} point(s)\n"
            "Reaction on a circle: +{points_per_reaction} point(s)\n"
            "Board check & summary: every {rating_interval_sec} sec\n"
            "Who’s off the board: {zero_criteria}\n"
            "How many we call out at once: {zero_ping_limit}\n"
            "Board size: top {top_limit}"
        ),
        MSG_ADMINS_ONLY: "Hold up. Admins handle this move.",
        MSG_RATINGS_ENABLED: "Board checks are back on. Numbers stay watched.",
        MSG_RATINGS_DISABLED: "Board checks paused. Quiet before the next run.",
        MSG_GREETING: (
            "<b>My name is: The Notorious B.O.T.</b>\n"
            "Mic is live. Cypher is open.\n\n"
            "Rules are simple: drop circles, earn respect, climb the board.\n\n"
            "Moves you can make:\n"
            "  /top — who’s on the board\n"
            "  /me — your own numbers\n"
            "  /rules — how the game works\n"
            "  /enable_ratings — resume board checks (admins)\n"
            "  /disable_ratings — pause board checks (admins)"
        ),
        MSG_TOP_EMPTY: "Board’s empty. First circle sets the rhythm.",
        MSG_TOP_HEADER: "<b>The Board</b>",
        MSG_TOP_ROW: "{rank}. {label} — <b>{points}</b> pts : {circles} / {reactions}",
        MSG_ZERO_PING: (
            "<b>Callout</b>: still no noise here.\n"
            "Reason: <b>{reason}</b>\n"
            "Names: {mentions}\n"
            "Drop a circle. Make it count."
        ),
        MSG_ZERO_POINTS: "0 points",
        MSG_ZERO_CIRCLES: "0 circles",
        MSG_LANG_CHANGED: "Language switched to {language}.",
        MSG_LANG_INVALID: "Wrong code. Supported: en, ru",
    },
    "ru": {
        MSG_NO_STATS: "Пока пусто. Запиши круг и залетай в сайфер.",
        MSG_USER_STATS: "<b>{label}</b>\nОчки: <b>{points}</b>\nКруги: {circles}\nРеакции: {reactions}",
        MSG_RULES: (
            "<b>Правила района</b>\n"
            "Всё просто: записывай круги, зарабатывай уважение района и выходи в топ.\n\n"
            "Круг (видеосообщение): +{points_per_circle} очко(ов)\n"
            "Реакция на круг: +{points_per_reaction} очко(ов)\n"
            "Проверка доски и саммари: каждые {rating_interval_sec} сек\n"
            "Кто вне доски: {zero_criteria}\n"
            "Сколько зовём за раз: {zero_ping_limit}\n"
            "Размер доски: топ {top_limit}"
        ),
        MSG_ADMINS_ONLY: "Стоп. Этот ход только для админов.",
        MSG_RATINGS_ENABLED: "Проверка доски включена. Цифры под контролем.",
        MSG_RATINGS_DISABLED: "Проверка доски на паузе. Тишина перед следующим заходом.",
        MSG_GREETING: (
            "<b>Хей. Я - The Notorious B.O.T.</b>\n"
            "Микрофон включён. Сайфер открыт.\n\n"
            "Cypher — это круг, где люди по очереди читают фристайл.\n"
            "Без сцены. Без жюри. Только круг, ритм и уважение.\n\n"
            "Всё просто: записывай круги, зарабатывай уважение района и выходи в топ.\n\n"
            "Команды:\n"
            "  /top — кто на доске\n"
            "  /me — твои цифры\n"
            "  /rules — как тут всё работает\n"
            "  /enable_ratings — включить проверку доски (админы)\n"
            "  /disable_ratings — поставить на паузу (админы)"
        ),
        MSG_TOP_EMPTY: "Доска пустая. Первый круг задаёт ритм.",
        MSG_TOP_HEADER: "<b>Доска</b>",
        MSG_TOP_ROW: "{rank}. {label} — <b>{points}</b> очков : {circles} / {reactions}",
        MSG_ZERO_PING: (
            "<b>Вызов</b>: тут пока тихо.\n"
            "Причина: <b>{reason}</b>\n"
            "Игроки: {mentions}\n"
            "Запиши круг. Дай шум."
        ),
        MSG_ZERO_POINTS: "0 очков",
        MSG_ZERO_CIRCLES: "0 кругов",
        MSG_LANG_CHANGED: "Язык переключён на {language}.",
        MSG_LANG_INVALID: "Неверный код. Доступно: en, ru",
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
