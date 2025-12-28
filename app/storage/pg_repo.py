from __future__ import annotations

from typing import Optional, Sequence, List
import logging

from app.core.models import UserIdentity, UserStats, TopRow, ChatState, CircleMessage
from app.storage.repo import Repository

logger = logging.getLogger(__name__)


class PostgresRepository(Repository):
    def __init__(self, *, dsn: str, migrations_sql_path: str) -> None:
        # Import psycopg only when PostgreSQL repo is instantiated
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "psycopg is not installed. Install it with: pip install 'psycopg[binary]>=3.1'"
            )
        
        self._psycopg = psycopg
        self._dict_row = dict_row
        self._dsn = dsn
        self._migrations_sql_path = migrations_sql_path
        self._init_db()

    def _connect(self):
        return self._psycopg.connect(self._dsn, row_factory=self._dict_row)

    def _init_db(self) -> None:
        with open(self._migrations_sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(sql)
            con.commit()

    # --- chat state ---
    def ensure_chat_state(self, *, chat_id: int) -> None:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_state(chat_id,last_circle_ts,last_rating_ts,ratings_enabled)
                    VALUES(%s,%s,%s,%s)
                    ON CONFLICT (chat_id) DO NOTHING
                    """,
                    (chat_id, 0, 0, True),
                )
            con.commit()

    def get_chat_state(self, *, chat_id: int) -> ChatState:
        self.ensure_chat_state(chat_id=chat_id)
        with self._connect() as con:
            with con.cursor() as cur:
                row = cur.execute(
                    "SELECT chat_id,last_circle_ts,last_rating_ts,ratings_enabled FROM chat_state WHERE chat_id=%s",
                    (chat_id,),
                ).fetchone()
        return ChatState(
            chat_id=row["chat_id"],
            last_circle_ts=row["last_circle_ts"],
            last_rating_ts=row["last_rating_ts"],
            ratings_enabled=bool(row["ratings_enabled"]),
        )

    def set_last_circle_ts(self, *, chat_id: int, ts: int) -> None:
        self.ensure_chat_state(chat_id=chat_id)
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute("UPDATE chat_state SET last_circle_ts=%s WHERE chat_id=%s", (ts, chat_id))
            con.commit()

    def set_last_rating_ts(self, *, chat_id: int, ts: int) -> None:
        self.ensure_chat_state(chat_id=chat_id)
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute("UPDATE chat_state SET last_rating_ts=%s WHERE chat_id=%s", (ts, chat_id))
            con.commit()

    def set_ratings_enabled(self, *, chat_id: int, enabled: bool) -> None:
        self.ensure_chat_state(chat_id=chat_id)
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute("UPDATE chat_state SET ratings_enabled=%s WHERE chat_id=%s", (enabled, chat_id))
            con.commit()

    def list_active_chats(self) -> Sequence[int]:
        with self._connect() as con:
            with con.cursor() as cur:
                rows = cur.execute("SELECT chat_id FROM chat_state").fetchall()
        return [int(r["chat_id"]) for r in rows]

    # --- users ---
    def upsert_user(self, identity: UserIdentity) -> None:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users(chat_id,user_id,username,display_name,circles,reactions,points)
                    VALUES(%s,%s,%s,%s,0,0,0)
                    ON CONFLICT (chat_id,user_id) DO UPDATE SET
                      username=EXCLUDED.username,
                      display_name=EXCLUDED.display_name
                    """,
                    (identity.chat_id, identity.user_id, identity.username, identity.display_name),
                )
                logger.info("upsert_user executed: chat=%s user=%s rows_affected=%s", 
                            identity.chat_id, identity.user_id, cur.rowcount)
                
                # Verify the user exists after upsert
                cur.execute(
                    "SELECT chat_id, user_id, points FROM users WHERE chat_id=%s AND user_id=%s",
                    (identity.chat_id, identity.user_id),
                )
                row = cur.fetchone()
                if row:
                    logger.info("User verified in DB: chat=%s user=%s current_points=%s", 
                               identity.chat_id, identity.user_id, row["points"])
                else:
                    logger.error("User NOT found in DB after upsert! chat=%s user=%s", 
                                identity.chat_id, identity.user_id)
            con.commit()

    def get_user_stats(self, *, chat_id: int, user_id: int) -> Optional[UserStats]:
        with self._connect() as con:
            with con.cursor() as cur:
                row = cur.execute(
                    """
                    SELECT chat_id,user_id,username,display_name,circles,reactions,points
                    FROM users
                    WHERE chat_id=%s AND user_id=%s
                    """,
                    (chat_id, user_id),
                ).fetchone()
        if not row:
            return None
        return UserStats(**row)

    def add_circle_points(self, *, chat_id: int, user_id: int, points: int) -> None:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    "UPDATE users SET circles=circles+1, points=points+%s WHERE chat_id=%s AND user_id=%s",
                    (points, chat_id, user_id),
                )
                rows_updated = cur.rowcount
                logger.info("add_circle_points: chat=%s user=%s points=%s rows_updated=%s", 
                           chat_id, user_id, points, rows_updated)
            con.commit()

    def add_reaction_points(self, *, chat_id: int, user_id: int, points: int) -> None:
        # points is +N or -N; reactions counter changes by +1 or -1 accordingly
        delta = 1 if points > 0 else -1
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    "UPDATE users SET reactions=reactions+%s, points=points+%s WHERE chat_id=%s AND user_id=%s",
                    (delta, points, chat_id, user_id),
                )
                rows_updated = cur.rowcount
                logger.info("add_reaction_points: chat=%s user=%s points=%s delta=%s rows_updated=%s", 
                           chat_id, user_id, points, delta, rows_updated)
            con.commit()

    # --- circles ---
    def insert_circle_message(self, circle: CircleMessage) -> bool:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO circle_messages(chat_id,message_id,author_id,created_at_ts)
                    VALUES(%s,%s,%s,%s)
                    ON CONFLICT (chat_id,message_id) DO NOTHING
                    RETURNING 1
                    """,
                    (circle.chat_id, circle.message_id, circle.author_id, circle.created_at_ts),
                )
                result = cur.fetchone() is not None
                logger.info(
                    "insert_circle_message: chat=%s msg=%s author=%s inserted=%s",
                    circle.chat_id,
                    circle.message_id,
                    circle.author_id,
                    result,
                )
            con.commit()
            return result

    def try_get_circle_author_id(self, *, chat_id: int, message_id: int) -> Optional[int]:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT author_id FROM circle_messages WHERE chat_id=%s AND message_id=%s",
                    (chat_id, message_id),
                )
                row = cur.fetchone()
        author_id = int(row["author_id"]) if row else None
        logger.info("try_get_circle_author_id: chat=%s msg=%s found_author=%s", chat_id, message_id, author_id)
        return author_id

    # --- reactions log ---
    def try_insert_reaction(self, *, chat_id: int, message_id: int, reactor_id: int, emoji: str) -> bool:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO reactions_log(chat_id,message_id,reactor_id,emoji)
                    VALUES(%s,%s,%s,%s)
                    ON CONFLICT (chat_id,message_id,reactor_id,emoji) DO NOTHING
                    RETURNING 1
                    """,
                    (chat_id, message_id, reactor_id, emoji),
                )
                inserted = cur.fetchone() is not None
            con.commit()
            return inserted

    def try_delete_reaction(self, *, chat_id: int, message_id: int, reactor_id: int, emoji: str) -> bool:
        with self._connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM reactions_log
                    WHERE chat_id=%s AND message_id=%s AND reactor_id=%s AND emoji=%s
                    RETURNING 1
                    """,
                    (chat_id, message_id, reactor_id, emoji),
                )
                deleted = cur.fetchone() is not None
            con.commit()
            return deleted

    # --- leaderboards ---
    def get_top(self, *, chat_id: int, limit: int) -> Sequence[TopRow]:
        with self._connect() as con:
            with con.cursor() as cur:
                rows = cur.execute(
                    """
                    SELECT user_id,username,display_name,circles,reactions,points
                    FROM users
                    WHERE chat_id=%s
                    ORDER BY points DESC, circles DESC, reactions DESC, user_id ASC
                    LIMIT %s
                    """,
                    (chat_id, limit),
                ).fetchall()

        return [
            TopRow(
                rank=i,
                user_id=r["user_id"],
                username=r["username"],
                display_name=r["display_name"],
                circles=r["circles"],
                reactions=r["reactions"],
                points=r["points"],
            )
            for i, r in enumerate(rows, start=1)
        ]

    def get_zero_users(self, *, chat_id: int, criteria: str, limit: int) -> Sequence[UserStats]:
        if criteria == "points":
            where = "points <= 0"
        elif criteria == "circles":
            where = "circles = 0"
        else:
            raise ValueError("criteria must be 'points' or 'circles'")

        with self._connect() as con:
            with con.cursor() as cur:
                rows = cur.execute(
                    f"""
                    SELECT chat_id,user_id,username,display_name,circles,reactions,points
                    FROM users
                    WHERE chat_id=%s AND {where}
                    ORDER BY points ASC, circles ASC, reactions ASC, user_id ASC
                    LIMIT %s
                    """,
                    (chat_id, limit),
                ).fetchall()

        return [UserStats(**r) for r in rows]
