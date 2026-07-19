from __future__ import annotations

from typing import Any

from model_canary.core.interfaces import StorageBackend
from model_canary.core.models import CanaryRunResult, DriftReport, Fingerprint


class MongoDBStorage(StorageBackend):
    def __init__(self, connection_string: str = "mongodb://localhost:27017") -> None:
        self._connection_string = connection_string
        self._client = None
        self._db = None

    async def initialize(self) -> None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            self._client = AsyncIOMotorClient(self._connection_string)
            self._db = self._client["model_canary"]
        except ImportError:
            raise ImportError(
                "MongoDB storage requires 'motor'. Install with: pip install model-canary[mongo]"
            )

    async def close(self) -> None:
        if self._client:
            self._client.close()

    async def save_run_result(self, result: CanaryRunResult) -> None:
        await self._db.runs.insert_one(result.model_dump(mode='json'))

    async def save_drift_report(self, report: DriftReport) -> None:
        await self._db.drifts.insert_one(report.model_dump(mode='json'))

    async def save_fingerprint(self, fingerprint: Fingerprint) -> None:
        data = fingerprint.model_dump(mode='json')
        await self._db.fingerprints.insert_one(data)

    async def get_run_result(self, run_id: str) -> CanaryRunResult | None:
        doc = await self._db.runs.find_one({"id": run_id})
        return CanaryRunResult(**doc) if doc else None

    async def get_latest_fingerprint(self, prompt_name: str, model: str, provider: str) -> Fingerprint | None:
        doc = await self._db.fingerprints.find_one(
            {"prompt_name": prompt_name, "model": model, "provider": provider},
            sort=[("timestamp", -1)],
        )
        return Fingerprint(**doc) if doc else None

    async def get_drift_reports(
        self,
        prompt_name: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DriftReport]:
        query: dict[str, Any] = {}
        if prompt_name:
            query["prompt_name"] = prompt_name
        if model:
            query["model"] = model
        if provider:
            query["provider"] = provider
        if severity:
            query["severity"] = severity
        cursor = self._db.drifts.find(query).sort("timestamp", -1).skip(offset).limit(limit)
        return [DriftReport(**doc) async for doc in cursor]

    async def get_fingerprint_history(
        self, prompt_name: str, model: str, provider: str, limit: int = 100
    ) -> list[Fingerprint]:
        cursor = (
            self._db.fingerprints.find(
                {"prompt_name": prompt_name, "model": model, "provider": provider}
            )
            .sort("timestamp", -1)
            .limit(limit)
        )
        return [Fingerprint(**doc) async for doc in cursor]
