from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from model_canary.core.interfaces import StorageBackend
from model_canary.core.models import (
    CanaryRunResult,
    DriftReport,
    Fingerprint,
)


class LocalJSONStorage(StorageBackend):
    def __init__(self, base_path: str = "./.model-canary/data") -> None:
        self._base_path = Path(base_path)
        self._runs_path = self._base_path / "runs"
        self._fingerprints_path = self._base_path / "fingerprints"
        self._drift_reports_path = self._base_path / "drift_reports"

    async def initialize(self) -> None:
        self._runs_path.mkdir(parents=True, exist_ok=True)
        self._fingerprints_path.mkdir(parents=True, exist_ok=True)
        self._drift_reports_path.mkdir(parents=True, exist_ok=True)

    async def close(self) -> None:
        pass

    async def save_run_result(self, result: CanaryRunResult) -> None:
        self._write_json(self._runs_path / f"{result.id}.json", result.model_dump(mode='json'))

    async def save_drift_report(self, report: DriftReport) -> None:
        self._write_json(self._drift_reports_path / f"{report.id}.json", report.model_dump(mode='json'))

    async def save_fingerprint(self, fingerprint: Fingerprint) -> None:
        data = fingerprint.model_dump(mode='json')
        if data.get("embedding"):
            del data["embedding"]
        self._write_json(self._fingerprints_path / f"{fingerprint.id}.json", data)

    async def get_run_result(self, run_id: str) -> CanaryRunResult | None:
        path = self._runs_path / f"{run_id}.json"
        if not path.exists():
            return None
        data = self._read_json(path)
        return CanaryRunResult(**data) if data else None

    async def get_latest_fingerprint(self, prompt_name: str, model: str, provider: str) -> Fingerprint | None:
        fingerprints = await self._list_fingerprints()
        matching = [
            f for f in fingerprints
            if f.prompt_name == prompt_name and f.model == model and f.provider == provider
        ]
        if not matching:
            return None
        matching.sort(key=lambda x: x.timestamp, reverse=True)
        return matching[0]

    async def get_drift_reports(
        self,
        prompt_name: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DriftReport]:
        reports = await self._list_drift_reports()
        if prompt_name:
            reports = [r for r in reports if r.prompt_name == prompt_name]
        if model:
            reports = [r for r in reports if r.model == model]
        if provider:
            reports = [r for r in reports if r.provider == provider]
        if severity:
            reports = [r for r in reports if r.severity.value == severity]
        reports.sort(key=lambda x: x.timestamp, reverse=True)
        return reports[offset:offset + limit]

    async def get_fingerprint_history(
        self, prompt_name: str, model: str, provider: str, limit: int = 100
    ) -> list[Fingerprint]:
        fingerprints = await self._list_fingerprints()
        matching = [
            f for f in fingerprints
            if f.prompt_name == prompt_name and f.model == model and f.provider == provider
        ]
        matching.sort(key=lambda x: x.timestamp, reverse=True)
        return matching[:limit]

    async def _list_fingerprints(self) -> list[Fingerprint]:
        results = []
        for path in self._fingerprints_path.glob("*.json"):
            data = self._read_json(path)
            if data:
                results.append(Fingerprint(**data))
        return results

    async def _list_drift_reports(self) -> list[DriftReport]:
        results = []
        for path in self._drift_reports_path.glob("*.json"):
            data = self._read_json(path)
            if data:
                results.append(DriftReport(**data))
        return results

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
