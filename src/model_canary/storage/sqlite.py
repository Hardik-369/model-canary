from __future__ import annotations

from model_canary.storage.base import SQLAlchemyStorage


class SQLiteStorage(SQLAlchemyStorage):
    def __init__(self, connection_string: str = "sqlite+aiosqlite:///model_canary.db") -> None:
        super().__init__(connection_string)
