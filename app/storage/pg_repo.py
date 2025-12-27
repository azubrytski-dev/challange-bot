from __future__ import annotations

from app.storage.repo import Repository


class PostgresRepository(Repository):
    """
    Stub: implement later using psycopg / asyncpg + SQL migrations.
    Keep same Repository methods to avoid touching business logic.
    """
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError("PostgresRepository is not implemented yet.")
