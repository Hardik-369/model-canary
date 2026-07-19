# Storage

Model Canary supports multiple storage backends.

## Backends

| Backend | ID | Connection String |
|---------|-----|-------------------|
| SQLite | `sqlite` | `sqlite+aiosqlite:///model_canary.db` |
| PostgreSQL | `postgres` | `postgresql+asyncpg://user:pass@host/db` |
| DuckDB | `duckdb` | `duckdb:///model_canary.duckdb` |
| Local JSON | `local_json` | (file-based) |

## Configuration

```yaml
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///model_canary.db
  pool_size: 10
  max_overflow: 20
```
