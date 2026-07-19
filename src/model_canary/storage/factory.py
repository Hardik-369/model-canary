from __future__ import annotations

from model_canary.core.interfaces import StorageBackend
from model_canary.core.models import StorageConfig


def create_storage(config: StorageConfig) -> StorageBackend:
    backend = config.backend.lower()

    if backend == "sqlite":
        from model_canary.storage.sqlite import SQLiteStorage

        return SQLiteStorage(config.connection_string)
    if backend == "postgres":
        from model_canary.storage.postgres import PostgresStorage

        return PostgresStorage(config.connection_string)
    if backend == "duckdb":
        from model_canary.storage.duckdb import DuckDBStorage

        return DuckDBStorage(config.connection_string)
    if backend == "local_json":
        from model_canary.storage.local_json import LocalJSONStorage

        return LocalJSONStorage()
    if backend == "mongodb":
        try:
            from model_canary.storage.mongodb import MongoDBStorage

            return MongoDBStorage(config.connection_string)
        except ImportError:
            raise ImportError(
                "MongoDB storage requires 'motor'. Install with: pip install model-canary[mongo]"
            )
    elif backend == "s3":
        from model_canary.storage.s3 import S3Storage

        return S3Storage(config.connection_string, config.extra)
    else:
        raise ValueError(f"Unknown storage backend: {backend}")
