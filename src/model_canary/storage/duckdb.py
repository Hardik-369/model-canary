from __future__ import annotations

from model_canary.storage.base import SQLAlchemyStorage


class DuckDBStorage(SQLAlchemyStorage):
    def __init__(self, connection_string: str = "duckdb:///model_canary.duckdb") -> None:
        super().__init__(connection_string)
