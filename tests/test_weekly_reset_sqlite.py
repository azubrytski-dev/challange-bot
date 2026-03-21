from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.models import UserIdentity
from app.storage.sqlite_repo import SQLiteRepository


class SQLiteWeeklyResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "bot.db"
        self.repo = SQLiteRepository(db_path=str(db_path))
        self.chat_id = 1001

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_top_user_uses_existing_leaderboard_ordering(self) -> None:
        self.repo.upsert_user(UserIdentity(self.chat_id, 1, "alice", "Alice"))
        self.repo.upsert_user(UserIdentity(self.chat_id, 2, "bob", "Bob"))
        self.repo.add_circle_points(chat_id=self.chat_id, user_id=1, points=3)
        self.repo.add_reaction_points(chat_id=self.chat_id, user_id=2, points=3)
        self.repo.add_circle_points(chat_id=self.chat_id, user_id=2, points=3)

        winner = self.repo.get_top_user(chat_id=self.chat_id)

        self.assertIsNotNone(winner)
        self.assertEqual(winner.user_id, 2)
        self.assertEqual(winner.points, 6)

    def test_increment_weekly_wins_and_reset_weekly_stats(self) -> None:
        self.repo.upsert_user(UserIdentity(self.chat_id, 1, "alice", "Alice"))
        self.repo.add_circle_points(chat_id=self.chat_id, user_id=1, points=5)
        self.repo.add_reaction_points(chat_id=self.chat_id, user_id=1, points=2)

        self.repo.increment_weekly_wins(chat_id=self.chat_id, user_id=1)
        self.repo.reset_weekly_stats(chat_id=self.chat_id)

        stats = self.repo.get_user_stats(chat_id=self.chat_id, user_id=1)
        self.assertIsNotNone(stats)
        self.assertEqual(stats.points, 0)
        self.assertEqual(stats.circles, 0)
        self.assertEqual(stats.reactions, 0)

        with self.repo._connect() as con:  # noqa: SLF001 - verifying persisted migration-backed column
            row = con.execute(
                "SELECT weekly_wins FROM users WHERE chat_id=? AND user_id=?",
                (self.chat_id, 1),
            ).fetchone()
        self.assertEqual(row["weekly_wins"], 1)


if __name__ == "__main__":
    unittest.main()
