from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional, Sequence, List

from app.core.models import UserIdentity, UserStats, TopRow, ChatState, CircleMessage
from app.storage.repo import Repository


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


class SQLiteRepository(Repository):
    def __init__(self, *, db_path: str, migrations_sql_path: str) -> None:
        _ensure_dir(db_path)
        self._db_path = db_path
        self._migrations_sql_path = migrations_sql_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db_path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        return con

    def _init_db(self) -> None:
        with open(self._migrations_sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        with self._connect() as con:
            con.executescript(sql)

    @contextmanager
    def _tx(self):
        con = self._connect()
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    # --- chat state ---
    def ensure_chat_state(self, *, chat_id: int) -> None:
        with self._tx() as con:
            con.execute(
                "INSERT OR IGNORE INTO chat_state(chat_id,last_circle_ts,last_rating_ts) VALUES(?,?,?)",
                (chat_id, 0, 0),
            )

    def get_chat_state(self, *, chat_id: int) -> ChatState:
        self.ensure_chat_state(chat_id=chat_id)
        with self._connect() as con:
            row = con.execute(
                "SELECT chat_id,last_circle_ts,last_rating_ts FROM chat_state WHERE chat_id=?",
                (chat_id,),
            ).fetchone()
        if row is None:
            return ChatState(chat_id=chat_id, last_circle_ts=0, last_rating_ts=0)
        return ChatState(chat_id=row["chat_id"], last_circle_ts=row["last_circle_ts"], last_rating_ts=row["last_rating_ts"])

    def set_last_circle_ts(self, *, chat_id: int, ts: int) -> None:
        self.ensure_chat_state(chat_id=chat_id)
        with self._tx() as con:
            con.execute("UPDATE chat_state SET last_circle_ts=? WHERE chat_id=?", (ts, chat_id))

    def set_last_rating_ts(self, *, chat_id: int, ts: int) -> None:
        self.ensure_chat_state(chat_id=chat_id)
        with self._tx() as con:
            con.execute("UPDATE chat_state SET last_rating_ts=? WHERE chat_id=?", (ts, chat_id))

    def list_active_chats(self) -> Sequence[int]:
        with self._connect() as con:
            rows = con.execute("SELECT chat_id FROM chat_state").fetchall()
        return [int(r["chat_id"]) for r in rows]

    # --- users ---
    def upsert_user(self, identity: UserIdentity) -> None:
        with self._tx() as con:
            con.execute(
                """
                INSERT INTO users(chat_id,user_id,username,display_name,circles,reactions,points)
                VALUES(?,?,?,?,0,0,0)
                ON CONFLICT(chat_id,user_id) DO UPDATE SET
                  username=excluded.username,
                  display_name=excluded.display_name
                """,
                (identity.chat_id, identity.user_id, identity.username, identity.display_name),
            )

    def get_user_stats(self, *, chat_id: int, user_id: int) -> Optional[UserStats]:
        with self._connect() as con:
            row = con.execute(
                "SELECT chat_id,user_id,username,display_name,circles,reactions,points FROM users WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            ).fetchone()
        if row is None:
            return None
        return UserStats(
            chat_id=row["chat_id"],
            user_id=row["user_id"],
            username=row["username"],
            display_name=row["display_name"],
            circles=row["circles"],
            reactions=row["reactions"],
            points=row["points"],
        )

    def add_circle_points(self, *, chat_id: int, user_id: int, points: int) -> None:
        with self._tx() as con:
            con.execute(
                "UPDATE users SET circles=circles+1, points=points+? WHERE chat_id=? AND user_id=?",
                (points, chat_id, user_id),
            )

    def add_reaction_points(self, *, chat_id: int, user_id: int, points: int) -> None:
        with self._tx() as con:
            con.execute(
                "UPDATE users SET reactions=reactions+CASE WHEN ? > 0 THEN 1 ELSE -1 END, points=points+? WHERE chat_id=? AND user_id=?",
                (points, points, chat_id, user_id),
            )

    # --- circles ---
    def insert_circle_message(self, circle: CircleMessage) -> bool:
        with self._tx() as con:
            cur = con.execute(
                "INSERT OR IGNORE INTO circle_messages(chat_id,message_id,author_id,created_at_ts) VALUES(?,?,?,?)",
                (circle.chat_id, circle.message_id, circle.author_id, circle.created_at_ts),
            )
            return cur.rowcount == 1

    def try_get_circle_author_id(self, *, chat_id: int, message_id: int) -> Optional[int]:
        with self._connect() as con:
            row = con.execute(
                "SELECT author_id FROM circle_messages WHERE chat_id=? AND message_id=?",
                (chat_id, message_id),
            ).fetchone()
        return int(row["author_id"]) if row else None

    # --- reactions log ---
    def try_insert_reaction(self, *, chat_id: int, message_id: int, reactor_id: int, emoji: str) -> bool:
        with self._tx() as con:
            cur = con.execute(
                "INSERT OR IGNORE INTO reactions_log(chat_id,message_id,reactor_id,emoji) VALUES(?,?,?,?)",
                (chat_id, message_id, reactor_id, emoji),
            )
            return cur.rowcount == 1

    def try_delete_reaction(self, *, chat_id: int, message_id: int, reactor_id: int, emoji: str) -> bool:
        with self._tx() as con:
            cur = con.execute(
                "DELETE FROM reactions_log WHERE chat_id=? AND message_id=? AND reactor_id=? AND emoji=?",
                (chat_id, message_id, reactor_id, emoji),
            )
            return cur.rowcount == 1

    # --- leaderboards ---
    def get_top(self, *, chat_id: int, limit: int) -> Sequence[TopRow]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT user_id,username,display_name,circles,reactions,points
                FROM users
                WHERE chat_id=?
                ORDER BY points DESC, circles DESC, reactions DESC, user_id ASC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()

        top: List[TopRow] = []
        for i, r in enumerate(rows, start=1):
            top.append(
                TopRow(
                    rank=i,
                    user_id=r["user_id"],
                    username=r["username"],
                    display_name=r["display_name"],
                    circles=r["circles"],
                    reactions=r["reactions"],
                    points=r["points"],
                )
            )
        return top

    def get_zero_users(self, *, chat_id: int, criteria: str, limit: int) -> Sequence[UserStats]:
        if criteria == "points":
            where = "points <= 0"
        elif criteria == "circles":
            where = "circles = 0"
        else:
            raise ValueError("criteria must be 'points' or 'circles'.")

        with self._connect() as con:
            rows = con.execute(
                f"""
                SELECT chat_id,user_id,username,display_name,circles,reactions,points
                FROM users
                WHERE chat_id=? AND {where}
                ORDER BY points ASC, circles ASC, reactions ASC, user_id ASC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()

        return [
            UserStats(
                chat_id=r["chat_id"],
                user_id=r["user_id"],
                username=r["username"],
                display_name=r["display_name"],
                circles=r["circles"],
                reactions=r["reactions"],
                points=r["points"],
            )
            for r in rows
        ]
