from __future__ import annotations

from model_canary.storage.base import SQLAlchemyStorage


class PostgresStorage(SQLAlchemyStorage):
    def __init__(self, connection_string: str = "postgresql+asyncpg://localhost:5432/model_canary") -> None:
        super().__init__(connection_string)
