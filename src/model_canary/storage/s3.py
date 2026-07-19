from __future__ import annotations

from typing import Any

from model_canary.core.interfaces import StorageBackend
from model_canary.core.models import CanaryRunResult, DriftReport, Fingerprint


class S3Storage(StorageBackend):
    def __init__(self, connection_string: str = "", extra: dict[str, Any] | None = None) -> None:
        self._bucket = extra.get("bucket", "model-canary") if extra else "model-canary"
        self._prefix = extra.get("prefix", "data/") if extra else "data/"
        self._client = None

    async def initialize(self) -> None:
        try:
            import boto3
            self._client = boto3.client("s3")
        except ImportError:
            raise ImportError("S3 storage requires 'boto3'. Install with: pip install boto3")

    async def close(self) -> None:
        self._client = None

    async def save_run_result(self, result: CanaryRunResult) -> None:
        key = f"{self._prefix}runs/{result.id}.json"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=result.model_dump_json(indent=2),
            ContentType="application/json",
        )

    async def save_drift_report(self, report: DriftReport) -> None:
        key = f"{self._prefix}drifts/{report.id}.json"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=report.model_dump_json(indent=2),
            ContentType="application/json",
        )

    async def save_fingerprint(self, fingerprint: Fingerprint) -> None:
        key = f"{self._prefix}fingerprints/{fingerprint.id}.json"
        data = fingerprint.model_dump(mode='json')
        import json
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(data, indent=2, default=str),
            ContentType="application/json",
        )

    async def get_run_result(self, run_id: str) -> CanaryRunResult | None:
        key = f"{self._prefix}runs/{run_id}.json"
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            import json
            data = json.loads(response["Body"].read().decode())
            return CanaryRunResult(**data)
        except Exception:
            return None

    async def get_latest_fingerprint(self, prompt_name: str, model: str, provider: str) -> Fingerprint | None:
        return None

    async def get_drift_reports(
        self,
        prompt_name: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DriftReport]:
        return []

    async def get_fingerprint_history(
        self, prompt_name: str, model: str, provider: str, limit: int = 100
    ) -> list[Fingerprint]:
        return []
