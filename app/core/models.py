from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UserIdentity:
    chat_id: int
    user_id: int
    username: Optional[str]
    display_name: str


@dataclass(frozen=True)
class UserStats:
    chat_id: int
    user_id: int
    username: Optional[str]
    display_name: str
    circles: int
    reactions: int
    points: int


@dataclass(frozen=True)
class TopRow:
    rank: int
    user_id: int
    username: Optional[str]
    display_name: str
    circles: int
    reactions: int
    points: int


@dataclass(frozen=True)
class ChatState:
    chat_id: int
    last_circle_ts: int
    last_rating_ts: int


@dataclass(frozen=True)
class CircleMessage:
    chat_id: int
    message_id: int
    author_id: int
    created_at_ts: int
